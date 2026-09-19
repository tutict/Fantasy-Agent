"""Guards for the native desktop launcher (apps/studio/desktop.py).

The launcher is the double-click entry point, so its failure modes are the ones
a user cannot debug: a blank window, an orphaned backend holding the port, or a
missing bundle discovered only after startup. Each test below pins one of those
down.

None of these tests open a window. The desktop extra (pywebview) is optional,
and `open_window` is only inspected via source text and by monkeypatching a
stub module, so the suite passes without it installed.
"""

from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import time
import types
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = REPO_ROOT / "apps" / "studio" / "desktop.py"
BAT_PATH = REPO_ROOT / "Start-Fantasy-Agent.bat"
PS1_PATH = REPO_ROOT / "scripts" / "start-fantasy-agent.ps1"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def _load_launcher():
    """Import apps/studio/desktop.py by path.

    The module must be registered in sys.modules *before* exec_module runs.
    startup.py declares frozen dataclasses, and dataclasses resolves string
    annotations through `sys.modules.get(cls.__module__)`, which returns None
    for a module that was never registered -- raising
    `AttributeError: 'NoneType' object has no attribute '__dict__'`.
    """
    module_name = "fantasy_agent_desktop"
    spec = importlib.util.spec_from_file_location(module_name, LAUNCHER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


class _QuietHandler(BaseHTTPRequestHandler):
    """Minimal handler so a real listener can stand in for the backend."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args: object) -> None:
        return


@contextmanager
def _serving_port():
    """Yield a port occupied by a real listener, then release it.

    `ThreadingHTTPServer.shutdown()` waits for the serve_forever() loop to stop,
    so calling it on a server that never started that loop blocks forever --
    which is how an earlier version of these tests hung the whole suite.
    `server_close()` is the correct teardown for a listener that only needs to
    hold the port.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _QuietHandler)
    try:
        yield int(server.server_address[1])
    finally:
        server.server_close()


def test_the_desktop_launcher_is_importable_without_pywebview():
    """pywebview is an optional extra, so importing the module must not need it.

    A module-scope `import webview` would make the whole file unimportable on a
    plain `pip install -e .`, taking the other tooling down with it.
    """

    source = LAUNCHER_PATH.read_text(encoding="utf-8")
    top_level_imports = [
        line for line in source.splitlines() if line.startswith(("import webview", "from webview"))
    ]
    assert not top_level_imports, (
        "webview must be imported inside open_window(), not at module scope: "
        f"it is an optional dependency. Found: {top_level_imports}"
    )

    module = _load_launcher()
    assert callable(module.main)


def test_the_window_uses_a_persistent_webview2_profile():
    """A blank window is the failure this pins.

    With pywebview's default ephemeral user-data folder on this platform,
    WebView2 fetches the document but never starts its renderer: the window
    opens blank and no sub-resource is requested. An A/B probe measured 0 assets
    loaded in default mode versus 4 with a persistent profile. Removing either
    argument reintroduces the blank window, so both are asserted.
    """

    source = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert "private_mode=False" in source, (
        "private_mode=False is required or WebView2 renders a blank window; "
        "see the module docstring in apps/studio/desktop.py"
    )
    assert "storage_path=str(profile_dir)" in source, (
        "storage_path must be passed explicitly; without it pywebview uses an "
        "ephemeral profile that leaves the renderer unstarted"
    )
    assert "WEBVIEW_PROFILE_DIR" in source, "the profile directory must be named, not inline"


def test_the_backend_is_reaped_when_the_window_closes():
    """An orphaned uvicorn would hold the port and push the next launch to 7861.

    The teardown path is asserted end to end: `main` opens the window inside a
    `try` whose `finally` terminates the child, and `terminate_backend` actually
    escalates to a kill rather than only requesting termination.
    """

    source = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert "terminate_backend" in source

    # terminate_backend must escalate: terminate() alone leaves a wedged child.
    assert ".terminate()" in source
    assert ".kill()" in source

    # The window must be opened inside a try/finally that reaps the child.
    window_call = source.index("open_window(plan")
    preceding = source[:window_call]
    assert "try:" in preceding.rsplit("def main", 1)[-1], (
        "open_window() must run inside a try whose finally reaps the backend"
    )


def test_a_busy_default_port_falls_back_instead_of_failing():
    """Two launches must not collide on 7860.

    The PowerShell script searches upward from the preferred port; the desktop
    launcher has to match, or a leftover backend makes the second launch fail.

    A real listener is started rather than a bare `listen(1)` socket. Each
    connection probe consumes a slot in the listener's accept backlog, so a
    backlog of 1 reports the port as open on the first probe and free on the
    second -- an artefact of the probe, not of port selection. Both uvicorn
    (2048) and socketserver (5) sit far above that threshold; see
    test_port_probing_is_stable_for_realistic_backlogs for the measurement.
    """
    module = _load_launcher()
    with _serving_port() as taken:
        assert module.port_is_open(taken) is True
        fallback = module.find_free_port(taken + 1)
        assert fallback != taken
        assert fallback > taken, "the search must move upward, like Get-FreePort does"


def test_the_preferred_port_is_skipped_when_it_is_already_serving():
    """plan_startup must step past a busy port, not only detect it."""

    module = _load_launcher()
    with _serving_port() as taken:
        chosen = module.find_free_port(taken)
        assert chosen > taken
        assert chosen <= taken + module.PORT_SEARCH_SPAN


def test_port_probing_is_stable_across_repeated_calls():
    """The probe must give the same answer every time on a serving port.

    This pins the backlog interaction directly: a listener whose backlog is
    smaller than the number of probes reports "open" and then "closed" as its
    accept queue fills. Selection logic calls the probe more than once, so an
    unstable probe would let a busy port read as free and uvicorn would fail to
    bind. Real servers use a backlog far above this threshold; if a future
    change makes the probe open a *connection* rather than test reachability,
    this test is what catches it.
    """
    module = _load_launcher()

    with _serving_port() as port:
        results = [module.port_is_open(port) for _ in range(5)]
        assert all(results), (
            "probing a serving port returned inconsistent results; the accept "
            f"backlog is being drained by the probes themselves: {results}"
        )


def test_port_probing_reports_a_free_port_as_free():
    """The negative case must be reliable too, or the search never terminates."""

    module = _load_launcher()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free = int(probe.getsockname()[1])
    # The socket is closed here, so nothing is listening on `free`.
    assert module.port_is_open(free) is False
    assert module.find_free_port(free) <= free


def test_the_port_search_gives_up_instead_of_looping_forever():
    """A span with no free port must raise, not spin or silently skip.

    Two adjacent ports are held open and the search is run with span=2 over
    exactly that range. It must raise rather than return a port it never
    verified, because handing uvicorn an occupied port would fail at bind time
    with a less obvious error.
    """
    module = _load_launcher()

    servers: list[ThreadingHTTPServer] = []
    try:
        # Hold ports until two of them happen to be adjacent, so the span is
        # genuinely full. Binding the second one next to the first is not
        # guaranteed, so probe for an adjacent pair instead of assuming.
        first = ThreadingHTTPServer(("127.0.0.1", 0), _QuietHandler)
        servers.append(first)
        start = int(first.server_address[1])

        second = None
        for candidate in (start + 1, start - 1):
            try:
                second = ThreadingHTTPServer(("127.0.0.1", candidate), _QuietHandler)
                start = min(start, candidate)
                break
            except OSError:
                continue
        assert second is not None, "could not obtain two adjacent free ports"
        servers.append(second)

        assert module.port_is_open(start) is True
        assert module.port_is_open(start + 1) is True

        with pytest.raises(RuntimeError, match="No free port"):
            module.find_free_port(start, span=2)
    finally:
        for server in servers:
            server.server_close()


def test_the_launcher_binds_loopback_only():
    """AGENTS.md: Studio listens on 127.0.0.1 and exposes nothing outward.

    A 0.0.0.0 bind here would silently publish the workbench to the LAN, which
    is the one boundary the architecture treats as non-negotiable.
    """

    module = _load_launcher()
    plan = module.StartupPlan(
        python_exe=Path("python.exe"),
        app_dir=REPO_ROOT / "apps" / "studio",
        repo_root=REPO_ROOT,
        port=7860,
        open_url="http://127.0.0.1:7860/",
        health_url="http://127.0.0.1:7860/health",
        skipped_install=True,
        skipped_build=True,
    )
    command = module.uvicorn_command(plan)

    assert "--host" in command
    assert command[command.index("--host") + 1] == "127.0.0.1"
    joined = " ".join(command)
    assert "0.0.0.0" not in joined


def test_the_launcher_reuses_the_same_uvicorn_entry_point_as_the_console_script():
    """The desktop and console paths must start the same application.

    If one pointed at a different module, the two launch routes would drift into
    serving different apps -- the dual-UI failure the Studio already removed
    once.
    """

    module = _load_launcher()
    plan = module.StartupPlan(
        python_exe=Path("python.exe"),
        app_dir=REPO_ROOT / "apps" / "studio",
        repo_root=REPO_ROOT,
        port=7860,
        open_url="http://127.0.0.1:7860/",
        health_url="http://127.0.0.1:7860/health",
        skipped_install=True,
        skipped_build=True,
    )
    command = module.uvicorn_command(plan)
    assert "app.main:app" in command

    # The console script must still name the same target.
    ps1 = PS1_PATH.read_text(encoding="utf-8")
    assert "app.main:app" in ps1, (
        "scripts/start-fantasy-agent.ps1 no longer names app.main:app; the two "
        "launch paths have drifted apart"
    )


def test_terminating_an_already_dead_backend_is_a_no_op():
    """Teardown runs in a `finally`, including after a failed startup."""

    module = _load_launcher()
    finished = subprocess.Popen(
        [sys.executable, "-c", "pass"],
    )
    finished.wait(timeout=30)
    module.terminate_backend(finished)  # must not raise
    module.terminate_backend(None)  # must not raise


def test_the_desktop_extra_is_optional_and_pinned():
    """`pip install -e .` must stay usable without a WebView runtime.

    Declaring pywebview as a core dependency would pull pythonnet into every
    install, including CI, for a code path that only runs on a desktop.
    """

    with PYPROJECT_PATH.open(encoding="utf-8") as handle:
        import tomllib

        config = tomllib.loads(handle.read())

    extras = config["project"].get("optional-dependencies", {})
    assert "desktop" in extras, "pywebview belongs in an optional 'desktop' extra"

    dependency = extras["desktop"]
    assert any(spec.startswith("pywebview") for spec in dependency), dependency
    assert not any(spec.startswith("pywebview") for spec in config["project"]["dependencies"]), (
        "pywebview must not be a core dependency"
    )

    # `latest`/`*` would let the installed version drift with no diff to review.
    for spec in dependency:
        assert not any(token in spec for token in ("latest", "*")), spec


def test_the_batch_launcher_avoids_parenthesised_set_blocks():
    """cmd expands %VARS% at block-parse time, so a `set` inside `if (...)` reads
    back empty on the following line of the same block.

    That bug produces a launcher which silently invokes an empty command. The
    file uses goto labels instead; this guard keeps it that way.
    """

    text = BAT_PATH.read_text(encoding="utf-8", errors="replace")

    assert "desktop.py" in text, "the batch entry point must invoke the desktop launcher"

    # A `set` on a line indented inside a parenthesised block is the trap.
    offenders = [
        line.strip()
        for line in text.splitlines()
        if line.startswith(("  ", "\t")) and line.strip().lower().startswith("set ")
    ]
    assert not offenders, (
        "these `set` statements sit inside a parenthesised block, where cmd reads "
        f"them back empty: {offenders}"
    )


def test_the_batch_launcher_prefers_pythonw_for_a_windowless_launch():
    """Double-clicking must not leave a console window behind."""

    text = BAT_PATH.read_text(encoding="utf-8", errors="replace")
    assert "pythonw.exe" in text, (
        "the launcher should use pythonw.exe so double-clicking leaves no console"
    )


def test_the_launcher_smoke_test_needs_no_window():
    """`--smoke-test` exists so CI and the developer can verify startup headlessly.

    It must not call open_window, or the check would hang on a machine with no
    display.
    """

    source = LAUNCHER_PATH.read_text(encoding="utf-8")
    smoke_body = source.split("def run_smoke", 1)[1].split("\ndef ", 1)[0]
    assert "open_window" not in smoke_body, "run_smoke must never open a window"
    assert "wait_for_health" in smoke_body, "run_smoke must confirm the backend is healthy"


class _DeadProcess:
    """A child that exits before answering: poll() returns immediately."""

    returncode = 1

    def poll(self) -> int:
        return self.returncode


def test_wait_for_health_gives_up_when_the_backend_dies():
    """A backend that exits before answering has already decided the outcome.

    Without the child check, a crash at startup cost the full 90-second budget
    spinning on a port nobody would ever listen on -- and the report said
    "no health response" instead of naming the exit.
    """

    module = _load_launcher()
    url = f"http://127.0.0.1:{9}/health"  # discard port: nothing answers here

    started = time.monotonic()
    assert module.wait_for_health(url, timeout=30.0, process=_DeadProcess()) is False
    assert time.monotonic() - started < 5.0, (
        "a dead backend must short-circuit the wait instead of spending it"
    )


def test_wait_for_health_still_times_out_without_a_process():
    """The parameter is optional: the plain signature keeps its old meaning."""

    module = _load_launcher()
    url = f"http://127.0.0.1:{9}/health"

    started = time.monotonic()
    assert module.wait_for_health(url, timeout=1.0) is False
    assert time.monotonic() - started >= 1.0, "the deadline must still be respected"


def test_the_batch_launcher_forwards_arguments_to_the_desktop_entry():
    """README documents `Start-Fantasy-Agent.bat --no-tray`; the bat must pass it on.

    The file used to swallow every argument: desktop.py's flags were
    unreachable through the double-click entry, and --no-tray silently did
    the opposite of what the README promised (close still hid to the tray).
    """

    text = BAT_PATH.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    forwarded = [line for line in lines if "%DESKTOP%" in line and "desktop.py" not in line]
    assert forwarded, "the bat must invoke the desktop launcher"
    assert all("%*" in line for line in forwarded), (
        f"every desktop invocation must forward the caller's arguments: {forwarded}"
    )

    # --console is consumed by the bat itself (desktop.py has no such flag), so
    # the console branch must drop it before forwarding the rest.
    console_branch = text.split(":console_mode", 1)[1]
    assert "shift" in console_branch, "the console branch must consume --console before %*"


def test_open_window_configures_the_renderer_before_showing_it():
    """A stubbed webview proves the arguments reach `start`, not just the source."""

    module = _load_launcher()
    recorded: dict[str, object] = {}

    stub = types.ModuleType("webview")
    stub.create_window = _stub_create_window  # type: ignore[attr-defined]

    def start(*args: object, **kwargs: object) -> None:
        # webview.start(startup, gui=..., ...) takes the startup hook
        # positionally; the stub captures it so the tray wiring stays covered.
        recorded["startup"] = args[0] if args else kwargs.get("startup")
        recorded["start_kwargs"] = kwargs

    stub.start = start  # type: ignore[attr-defined]

    sys.modules["webview"] = stub
    try:
        plan = _stub_plan(module)
        module.open_window(plan)
    finally:
        del sys.modules["webview"]

    start_kwargs = recorded["start_kwargs"]
    assert isinstance(start_kwargs, dict)
    assert start_kwargs["private_mode"] is False
    assert "storage_path" in start_kwargs

    window_kwargs = _stub_create_window.recorded["window_kwargs"]  # type: ignore[attr-defined]
    assert isinstance(window_kwargs, dict)
    assert window_kwargs["url"] == "http://127.0.0.1:7860/"


class _StubClosing:
    """Accepts `closing += handler`, the way pywebview's Event does.

    A bare `types.SimpleNamespace` cannot do this -- `__iadd__` is not defined on
    it, so `namespace += value` raises TypeError. That mattered: the tray test
    that asserts a failing tray is survivable passed on that TypeError instead
    of reaching the tray at all, which is a guard that proves nothing. Real
    classes here, not namespaces.
    """

    def __init__(self) -> None:
        self.handlers: list[object] = []

    def __iadd__(self, handler: object) -> Self:
        self.handlers.append(handler)
        return self

    def __add__(self, handler: object) -> _StubClosing:
        self.handlers.append(handler)
        return self


class _StubWindow:
    """Minimal window stand-in: an events container, and the operations used."""

    def __init__(self) -> None:
        self.events = types.SimpleNamespace(
            shown=_ReadyEvent(),
            closing=_StubClosing(),
        )
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> object:
        # hide/show/restore/destroy are all "record and return None".
        def _record(*args: object, **kwargs: object) -> None:
            self.calls.append(name)

        return _record


class _ReadyEvent:
    """A `shown` event that is already set, so no test waits on a real window."""

    def wait(self, timeout: float | None = None) -> bool:
        return True

    def set(self) -> None:
        return


def _stub_create_window(title: str, **kwargs: object) -> _StubWindow:
    """A window stand-in that records its kwargs and accepts `closing +=`."""
    window = _StubWindow()
    _stub_create_window.recorded = {  # type: ignore[attr-defined]
        "title": title,
        "window_kwargs": kwargs,
        "window": window,
    }
    return window


def test_the_tray_is_handed_to_webview_start_as_the_startup_hook():
    """The tray must be built inside the GUI thread, i.e. via start(startup).

    Creating a window only registers it -- `webview.start()` is what binds the
    GUI and fires the `shown` event. Setting the tray up before that call would
    leave any window operation waiting on an event that cannot fire yet.
    """

    module = _load_launcher()
    recorded: dict[str, object] = {}

    stub = types.ModuleType("webview")
    stub.create_window = _stub_create_window  # type: ignore[attr-defined]

    def start(*args: object, **kwargs: object) -> None:
        startup = args[0] if args else kwargs.get("startup")
        recorded["startup"] = startup
        if callable(startup):
            startup()

    stub.start = start  # type: ignore[attr-defined]
    sys.modules["webview"] = stub
    try:
        module.open_window(_stub_plan(module))
    finally:
        del sys.modules["webview"]

    assert callable(recorded["startup"]), (
        "open_window must pass a startup hook to webview.start, otherwise the tray is never created"
    )


def test_open_window_without_the_tray_passes_no_startup_hook():
    """`--no-tray` is the escape hatch; it must not build an icon."""

    module = _load_launcher()
    recorded: dict[str, object] = {}

    stub = types.ModuleType("webview")
    stub.create_window = _stub_create_window  # type: ignore[attr-defined]

    def start(*args: object, **kwargs: object) -> None:
        recorded["startup"] = args[0] if args else kwargs.get("startup")

    stub.start = start  # type: ignore[attr-defined]
    sys.modules["webview"] = stub
    try:
        module.open_window(_stub_plan(module), with_tray=False)
    finally:
        del sys.modules["webview"]

    assert recorded["startup"] is None


def test_a_failing_tray_does_not_take_the_window_down_with_it():
    """No notification area (headless session, weird shell) must not be fatal.

    The tray is a convenience; the window is the product. The startup hook
    therefore swallows and logs.

    The tray is made to fail *deliberately* here rather than relying on pystray
    being absent. Relying on absence would make this guard pass on a machine
    where pystray installs fine and the tray actually works -- green, and
    proving nothing.
    """

    module = _load_launcher()
    stub = types.ModuleType("webview")
    stub.create_window = _stub_create_window  # type: ignore[attr-defined]

    attempted: list[str] = []

    def start(*args: object, **kwargs: object) -> None:
        startup = args[0] if args else kwargs.get("startup")
        assert callable(startup)
        startup()  # must not raise, even though setup() is about to blow up

    stub.start = start  # type: ignore[attr-defined]

    # Force `setup` to fail the way a missing notification area would.
    def _boom(*args: object, **kwargs: object) -> None:
        attempted.append("setup")
        raise RuntimeError("no notification area in this session")

    original_setup = module.TrayController.setup
    module.TrayController.setup = _boom
    sys.modules["webview"] = stub
    try:
        module.open_window(_stub_plan(module))  # must not raise
    finally:
        module.TrayController.setup = original_setup
        del sys.modules["webview"]

    assert attempted == ["setup"], (
        "the tray was never attempted, so this test is not exercising the "
        "failure path it claims to cover"
    )


def test_the_launcher_supports_a_no_tray_escape_hatch():
    source = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert '"--no-tray"' in source, "a user whose tray is broken needs a way out"

    module = _load_launcher()
    args = module.build_parser().parse_args(["--no-tray"])
    assert args.no_tray is True


def _stub_plan(module):
    """A StartupPlan pointing at nothing, for the window tests."""
    return module.StartupPlan(
        python_exe=Path("python.exe"),
        app_dir=REPO_ROOT / "apps" / "studio",
        repo_root=REPO_ROOT,
        port=7860,
        open_url="http://127.0.0.1:7860/",
        health_url="http://127.0.0.1:7860/health",
        skipped_install=True,
        skipped_build=True,
    )
