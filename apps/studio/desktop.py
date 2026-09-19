"""灵构工坊（Fantasy Agent Studio）的桌面外壳。

This is the double-click entry point: it starts the Studio backend as a child
process, waits for it to become healthy, and shows the UI in a native window
instead of handing a URL to the system browser.

Why this exists separately from ``scripts/start-fantasy-agent.ps1``
--------------------------------------------------------------------
The PowerShell script is *not* reused here, and that is deliberate. Its final
statement is a foreground ``uvicorn`` call that occupies the shell until the
user presses Ctrl+C, so a Python process that invokes it would block instead of
regaining control to open a window. The two entry points therefore implement
the same startup sequence independently:

  * ``scripts/start-fantasy-agent.ps1`` -- console entry point, runs uvicorn in
    the foreground, opens the system browser. Used for debugging and for
    headless/smoke runs.
  * ``apps/studio/desktop.py`` (this file) -- owns the backend as a child
    process and renders it in a WebView window.

Keeping the venv check, port probe and health wait on both paths is the cost of
that split. If you change one, check the other.

WebView2 note
-------------
``private_mode=False`` plus an explicit ``storage_path`` is required on this
platform. pywebview's default ephemeral user-data folder is created
incompletely, which leaves WebView2 able to fetch the document but unable to
start its renderer: the window opens blank and no sub-resource is ever
requested. Verified by A/B probe -- the default mode fetched 0 assets, the
persistent profile fetched the stylesheet, image, script and favicon.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from apps.studio.tray import TrayController

logger = logging.getLogger(__name__)

# The window title is user-facing, and AGENTS.md asks for Chinese in anything
# meant for people. "Fantasy Agent" remains the repository/package identifier.
STUDIO_TITLE = "灵构工坊"
DEFAULT_PORT = 7860
PORT_SEARCH_SPAN = 50
HEALTH_TIMEOUT_SECONDS = 90.0
HEALTH_POLL_INTERVAL = 0.5

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
FRONTEND_DIST_INDEX = REPO_ROOT / "apps" / "frontend" / "dist" / "index.html"
# WebView2 profile lives under generated/ so it is gitignored with the rest of
# the run output rather than cluttering the repo root.
WEBVIEW_PROFILE_DIR = REPO_ROOT / "generated" / "desktop" / "webview2-profile"


@dataclass(frozen=True)
class StartupPlan:
    """Everything the shell needs in order to launch and reach the backend."""

    python_exe: Path
    app_dir: Path
    repo_root: Path
    port: int
    open_url: str
    health_url: str
    skipped_install: bool
    skipped_build: bool


def port_is_open(port: int, host: str = "127.0.0.1", timeout: float = 0.2) -> bool:
    """True when something already accepts connections on the port.

    SO_LINGER with a zero timeout makes the probe close with RST instead of a
    normal FIN handshake. Without it the half-closed connection lingers in the
    listener's backlog, and probing the same port again immediately can report
    it as free -- measured on Windows, where a `listen(1)` backlog gave True on
    the first probe and False on the second. Port selection has to be stable
    across repeated calls, or a busy port reads as free and uvicorn fails to
    bind.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        return sock.connect_ex((host, port)) == 0


def find_free_port(preferred: int, span: int = PORT_SEARCH_SPAN) -> int:
    """First free port at or after ``preferred``.

    Mirrors ``Get-FreePort`` in the PowerShell script so a busy 7860 keeps both
    entry points on the same fallback port.
    """
    for candidate in range(preferred, preferred + span):
        if not port_is_open(candidate):
            return candidate
    raise RuntimeError(f"No free port found in {preferred}..{preferred + span - 1}.")


def health_ok(url: str, timeout: float = 1.0) -> bool:
    """True when the health endpoint answers 200.

    ``urlopen`` raises ``HTTPError`` for 4xx/5xx, so anything non-200 lands in
    the except below -- the response path only ever sees 2xx/3xx, and the only
    status ``/health`` answers with is 200.
    """
    try:
        # URL is always a literal 127.0.0.1 health endpoint built by plan_startup.
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for_health(
    url: str,
    timeout: float = HEALTH_TIMEOUT_SECONDS,
    process: subprocess.Popen[bytes] | None = None,
) -> bool:
    """Poll the health endpoint until it answers or the deadline passes.

    ``process`` is the backend child. When it exits before answering, the
    outcome is already decided -- no answer is coming -- so this returns
    immediately instead of spending the remaining budget on a port nobody
    will ever listen on (a crash at startup used to cost the full 90 seconds
    before anyone looked at why).
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            return False
        if health_ok(url):
            return True
        time.sleep(HEALTH_POLL_INTERVAL)
    return False


def resolve_python(repo_root: Path = REPO_ROOT) -> Path:
    """The interpreter that runs uvicorn.

    Prefers the project venv (which is where ``pyproject.toml`` dependencies get
    installed); falls back to the running interpreter so a system-wide install
    still works.
    """
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def dependencies_importable(python_exe: Path, repo_root: Path) -> bool:
    """Cheap probe for the backend's runtime dependencies."""
    result = subprocess.run(
        [str(python_exe), "-c", "import fastapi, uvicorn, fantasy_agent"],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def ensure_dependencies(python_exe: Path, repo_root: Path, skip_install: bool) -> None:
    """Install the project in editable mode when imports are missing."""
    if skip_install or dependencies_importable(python_exe, repo_root):
        return
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "install", "-e", "."],
        cwd=str(repo_root),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("pip install -e . failed.")


def ensure_frontend_bundle(repo_root: Path, skip_build: bool) -> None:
    """Build the React bundle once when ``dist/index.html`` is missing.

    The Studio answers 503 on the UI routes without a bundle, so this is what
    turns "double-click and it works" into a true statement on a fresh clone.
    """
    if (repo_root / "apps" / "frontend" / "dist" / "index.html").exists():
        return
    if skip_build:
        raise RuntimeError(
            "Frontend bundle is missing and --skip-build was passed. "
            "Run `npm run frontend:build` first."
        )
    if not (repo_root / "node_modules").exists():
        raise RuntimeError(
            "Frontend bundle is missing and node_modules is absent. "
            "Run `npm install` and `npm run frontend:build` first."
        )
    result = subprocess.run(
        ["npx", "vite", "build"],
        cwd=str(repo_root),
        shell=(os.name == "nt"),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Frontend build failed (`npx vite build`).")


def plan_startup(
    *,
    port: int = 0,
    repo_root: Path = REPO_ROOT,
    skip_install: bool = False,
    skip_build: bool = False,
) -> StartupPlan:
    """Decide the port and prepare dependencies, without starting anything."""
    python_exe = resolve_python(repo_root)

    preferred = port if port > 0 else DEFAULT_PORT
    selected = preferred
    if port_is_open(selected):
        selected = find_free_port(preferred + 1)

    ensure_dependencies(python_exe, repo_root, skip_install)
    ensure_frontend_bundle(repo_root, skip_build)

    return StartupPlan(
        python_exe=python_exe,
        app_dir=repo_root / "apps" / "studio",
        repo_root=repo_root,
        port=selected,
        open_url=f"http://127.0.0.1:{selected}/",
        health_url=f"http://127.0.0.1:{selected}/health",
        skipped_install=skip_install,
        skipped_build=skip_build,
    )


def uvicorn_command(plan: StartupPlan) -> list[str]:
    """The child process command line, kept separate so tests can assert on it."""
    return [
        str(plan.python_exe),
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        str(plan.app_dir),
        "--host",
        "127.0.0.1",
        "--port",
        str(plan.port),
        "--no-access-log",
        "--log-level",
        "warning",
    ]


def spawn_backend(plan: StartupPlan) -> subprocess.Popen[bytes]:
    """Start uvicorn as a child with no console window of its own."""
    creationflags = 0
    if os.name == "nt":
        # CREATE_NO_WINDOW keeps a console from flashing on a GUI launch.
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    # argv comes from uvicorn_command(), which is fixed except for the port
    # number chosen by find_free_port().
    return subprocess.Popen(
        uvicorn_command(plan),
        cwd=str(plan.repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def terminate_backend(process: subprocess.Popen[bytes] | None) -> None:
    """Stop the backend, escalating to a kill if it ignores the request.

    Reaping the child matters here: without it a closed window would leave an
    orphaned uvicorn holding the port, and the next launch would silently fall
    back to 7861.
    """
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def open_window(
    plan: StartupPlan,
    *,
    profile_dir: Path = WEBVIEW_PROFILE_DIR,
    with_tray: bool = True,
) -> None:
    """Show the Studio in a native WebView window, blocking until it closes.

    With ``with_tray`` the close button hides the window instead of quitting,
    and the tray menu becomes the only way out. See :mod:`apps.studio.tray`.
    """
    # Imported here rather than at module scope so the console entry point and
    # the test suite keep working without the optional desktop extra installed.
    import webview

    profile_dir.mkdir(parents=True, exist_ok=True)

    window = webview.create_window(
        STUDIO_TITLE,
        url=plan.open_url,
        width=1440,
        height=920,
        min_size=(960, 640),
    )

    # The tray is set up inside the GUI thread's startup hook rather than before
    # webview.start(): creating a window only registers it, and start() is what
    # binds the GUI and fires `shown`. Asking the window to hide earlier would
    # block on an event that cannot fire yet.
    def _start_tray() -> None:
        try:
            controller.setup(window)
        except Exception:
            # A missing notification area (some headless sessions) or an absent
            # pystray install should cost the user the tray, not the window.
            logger.exception("托盘初始化失败，改为普通窗口模式")

    controller = TrayController()
    startup = _start_tray if with_tray else None

    try:
        # private_mode=False + storage_path are required, not cosmetic: with the
        # default ephemeral profile WebView2 fetches the document but never
        # starts its renderer, so the window opens blank. See the docstring.
        webview.start(
            startup,
            gui="edgechromium",
            debug=False,
            private_mode=False,
            storage_path=str(profile_dir),
        )
    finally:
        # Covers every exit path: the tray menu, a cancelled close that later
        # went through, and Ctrl+C. Without it the icon thread would outlive the
        # window and keep the process alive.
        controller.request_quit()


def run_smoke(plan: StartupPlan) -> int:
    """Start the backend, confirm health, stop it. Never opens a window."""
    process = spawn_backend(plan)
    try:
        if not wait_for_health(plan.health_url, process=process):
            if process.poll() is not None:
                print(
                    f"冒烟测试失败：后端进程已退出（退出码 {process.returncode}）",
                    file=sys.stderr,
                )
            else:
                print(f"冒烟测试失败：{plan.health_url} 没有健康检查响应", file=sys.stderr)
            return 1
        print(f"冒烟测试通过：{plan.health_url}")
        return 0
    finally:
        terminate_backend(process)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fantasy-agent-desktop",
        description="在原生桌面窗口中启动灵构工坊。",
    )
    parser.add_argument(
        "--port", type=int, default=0, help=f"preferred port (default {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="do not run `pip install -e .` when imports are missing",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="fail instead of building the React bundle when dist is missing",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="close the window normally instead of hiding it to the system tray",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="start the backend, verify /health, stop it, and exit without a window",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="print the resolved startup plan as JSON and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        plan = plan_startup(
            port=args.port,
            skip_install=args.skip_install,
            skip_build=args.skip_build,
        )
    except RuntimeError as exc:
        print(f"灵构工坊启动失败：{exc}", file=sys.stderr)
        return 1

    if args.print_plan:
        print(
            json.dumps(
                {"open_url": plan.open_url, "health_url": plan.health_url, "port": plan.port},
                indent=2,
            )
        )
        return 0

    if args.smoke_test:
        return run_smoke(plan)

    backend = spawn_backend(plan)
    try:
        if not wait_for_health(plan.health_url, process=backend):
            if backend.poll() is not None:
                print(
                    f"灵构工坊启动失败：后端进程已退出（退出码 {backend.returncode}）。",
                    file=sys.stderr,
                )
            else:
                print(
                    f"灵构工坊启动失败：后端在 {HEALTH_TIMEOUT_SECONDS:.0f} 秒内没有响应 "
                    f"{plan.health_url}。",
                    file=sys.stderr,
                )
            return 1
        open_window(plan, with_tray=not args.no_tray)
    finally:
        terminate_backend(backend)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
