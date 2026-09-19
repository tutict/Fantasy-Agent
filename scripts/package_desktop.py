"""Build a distributable desktop bundle for the current platform.

    python scripts/package_desktop.py --target windows

What this produces
------------------
One directory per platform, under ``dist/`` (gitignored):

======================  ==========================================================
target                  output
======================  ==========================================================
``windows``             ``dist/linggou-studio/`` plus ``灵构工坊-Setup-<ver>.exe``
``macos``               ``dist/灵构工坊.app`` plus ``灵构工坊-<ver>.dmg``
``linux``               ``dist/linggou-studio/`` plus ``.AppImage`` and ``.deb``
======================  ==========================================================

Why one script with a ``--target`` flag rather than three scripts
-----------------------------------------------------------------
Two thirds of the work is identical: build the React bundle, stage the Python
interpreter into a bundle-local ``runtime/`` prefix, copy the launcher,
generate the icons, write the version stamp. Splitting that across three files
guarantees the platforms drift. The platform-specific tail (the installer
stub, the .deb control file, the .app wrapper) is where the differences
actually live, and those are isolated in the ``_finalise_*`` functions.

Why this cannot run on Windows for the other two targets
---------------------------------------------------------
A macOS ``.app`` needs a Mach-O Python, and a Linux ``.deb`` needs
``dpkg-deb`` and an ELF interpreter. The staged ``runtime/`` is a copy of the
*current* platform's interpreter, and a copied interpreter does not change
architecture. So the expectation is: run this script on each platform (or let
the CI matrix do it -- see ``.github/workflows/release.yml``), which is why
the script refuses a mismatched target loudly instead of producing a subtly
broken bundle.

Work still to do before a release
---------------------------------
The installers are produced but **not signed**. Keep it that way until there
are certificates: an unsigned bundle that claims to be signed is worse than an
obviously unsigned one, because SmartScreen and Gatekeeper will say so anyway
and a release note that overpromises burns trust. See the report printed at the
end of a run.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ICON_DIR = ROOT / "generated" / "desktop" / "icons"

#: The bundle name is an implementation identifier (paths, the .spec file, the
#: .deb package name). The *display* name is Chinese -- AGENTS.md keeps those
#: two apart deliberately. The ASCII form is what a filesystem and `dpkg` get.
BUNDLE_NAME = "linggou-studio"
DISPLAY_NAME_ZH = "灵构工坊"
APP_ID = "com.fantasyagent.linggou"

SUPPORTED_TARGETS = ("windows", "macos", "linux")

#: Files and directories the bundle needs at runtime. `apps/frontend/dist` is
#: the built React bundle; without it the Studio answers 503 on the UI routes.
PAYLOAD: tuple[str, ...] = (
    "apps/studio",
    "apps/frontend/dist",
    "fantasy_agent",
    "mcp",
    "templates",
    "locales",
    "gameplay-schema.yaml",
    "GAME_DESIGN_PHILOSOPHY.md",
    "README.md",
)


@dataclass
class Report:
    """What happened, so the run can be judged without reading scrollback."""

    target: str
    output_dir: Path
    artefacts: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"  warning: {message}")

    def skip(self, message: str) -> None:
        self.skipped.append(message)
        print(f"  skipped: {message}")


def current_target() -> str:
    """Map the running platform onto one of SUPPORTED_TARGETS."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return "linux"


def read_version() -> str:
    """The version, read from pyproject.toml rather than duplicated here.

    A second copy of the version number is a slow-motion bug: the two drift and
    the installer ends up named after a release that never existed.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if in_project and stripped.startswith("version"):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("no version found in pyproject.toml [project]")


def ensure_frontend_built(report: Report) -> None:
    """Build the React bundle when it is missing."""
    index = ROOT / "apps" / "frontend" / "dist" / "index.html"
    if index.exists():
        return
    if not (ROOT / "node_modules").exists():
        raise RuntimeError(
            "frontend bundle missing and node_modules absent; run `npm install` first"
        )
    print("building frontend bundle")
    result = subprocess.run(
        ["npx", "vite", "build"], cwd=ROOT, shell=(os.name == "nt"), check=False
    )
    if result.returncode != 0:
        raise RuntimeError("`npx vite build` failed")


def ensure_icons(report: Report) -> None:
    """Regenerate the icon set, so a stale `generated/` cannot ship."""
    sys.path.insert(0, str(ROOT))
    from apps.studio.icons import ensure_icons as _ensure

    written = _ensure(ICON_DIR)
    print(f"icons ready: {written['ico'].name}")


def _copy_payload(stage: Path) -> None:
    """Copy the runtime payload into ``stage``, preserving layout."""
    # Bytecode caches are noise in a shipped bundle: they are regenerated on
    # first run, and a stale .pyc from the build machine can shadow the source.
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for relative in PAYLOAD:
        source = ROOT / relative
        if not source.exists():
            raise RuntimeError(f"payload entry missing: {relative}")
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)


def _write_launcher(stage: Path, target: str) -> None:
    """The script a human (or Finder) actually runs.

    It sets ``PYTHONPATH`` to the bundled payload and starts the desktop shell,
    which is the same entry point ``Start-Fantasy-Agent.bat`` uses. Keeping the
    bundled launch on the same code path means a fix there is a fix here.
    """
    if target == "windows":
        (stage / "灵构工坊.bat").write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            'set "HERE=%~dp0"\r\n'
            'set "PYTHONPATH=%HERE%"\r\n'
            'set "PYTHONUTF8=1"\r\n'
            '"%HERE%runtime\\pythonw.exe" -m apps.studio.desktop 1>"%TEMP%\\linggou-studio.log" 2>&1\r\n'
            "if errorlevel 1 (\r\n"
            "  echo 启动失败，日志：%TEMP%\\linggou-studio.log\r\n"
            "  pause\r\n"
            ")\r\n",
            encoding="utf-8",
        )
    else:
        launcher = stage / DISPLAY_NAME_ZH
        launcher.write_text(
            "#!/bin/sh\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            'export PYTHONPATH="$HERE"\n'
            "export PYTHONUTF8=1\n"
            'exec "$HERE/runtime/bin/python3" -m apps.studio.desktop "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o755)


def _write_version_stamp(stage: Path, version: str, target: str) -> Path:
    stamp = stage / "BUILD-INFO.json"
    stamp.write_text(
        json.dumps(
            {
                "display_name": DISPLAY_NAME_ZH,
                "bundle_name": BUNDLE_NAME,
                "version": version,
                "target": target,
                "signed": False,
                "built_by": "scripts/package_desktop.py",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return stamp


def _stage_runtime(
    stage: Path,
    *,
    base_prefix: Path | None = None,
    purelib: Path | None = None,
) -> Path:
    """Copy the running interpreter into ``stage/runtime``.

    The launchers reference ``runtime/``, so the bundle has to carry its own
    interpreter -- without this step every entry point pointed at a directory
    the build never created, and the CI artefacts could not start anywhere.
    The layout of ``base_prefix`` is copied verbatim, which is what lets the
    copied interpreter find its own stdlib the way the original does.

    Dependencies arrive in one of two ways:

    * installed into the interpreter itself (a CI runner's
      ``pip install -e ".[desktop]"``): they live inside ``base_prefix`` and
      travel with the copy;
    * installed into a venv (a development machine): the venv's site-packages
      are merged over the copy, minus the ``__editable__*`` finder modules --
      those point back at the build machine's checkout, and the payload
      already carries the code they would import.

    The interpreter source comes in as keyword arguments (defaulting to the
    running process) so a test can stage a fake tree instead of a hundred
    megabytes of the real one.
    """
    base = Path(base_prefix) if base_prefix is not None else Path(sys.base_prefix)
    runtime = stage / "runtime"
    shutil.copytree(
        base,
        runtime,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        dirs_exist_ok=True,
    )

    pure = Path(purelib) if purelib is not None else Path(sysconfig.get_paths()["purelib"])
    if pure.resolve().is_relative_to(base.resolve()):
        # Dependencies live inside the interpreter; the copy already has them.
        return runtime

    site_packages = next(iter(sorted(runtime.rglob("site-packages"))), None)
    if site_packages is None:
        raise RuntimeError(
            "no site-packages in the staged runtime; the bundle would be missing "
            "its dependencies"
        )
    shutil.copytree(
        pure,
        site_packages,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "__editable__*"),
        dirs_exist_ok=True,
    )
    return runtime


def _finalise_windows(stage: Path, version: str, report: Report) -> None:
    """Wrap the bundle in an installer, using Inno Setup when present."""
    script = ROOT / "scripts" / "installer" / "windows.iss"
    if not script.exists():
        report.skip("no Inno Setup script committed; directory bundle is the deliverable")
        return
    compiler = shutil.which("iscc") or shutil.which("ISCC")
    if compiler is None:
        report.skip("Inno Setup (iscc) not found; run it on the release machine")
        return

    output = DIST / f"{DISPLAY_NAME_ZH}-Setup-{version}.exe"
    result = subprocess.run(
        [
            compiler,
            f"/DAppVersion={version}",
            f"/DAppName={DISPLAY_NAME_ZH}",
            f"/DSourceDir={stage}",
            f"/DOutputDir={DIST}",
            f"/DOutputBase={output.stem}",
            str(script),
        ],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Inno Setup compilation failed")
    report.artefacts.append(output)
    report.warn("the installer is UNSIGNED")


def _finalise_macos(stage: Path, version: str, report: Report) -> None:
    """Wrap the bundle in a .app, then a .dmg when hdiutil is available."""
    app = DIST / f"{DISPLAY_NAME_ZH}.app"
    if app.exists():
        shutil.rmtree(app)
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Resources").mkdir(parents=True)
    (contents / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>CFBundleName</key><string>{DISPLAY_NAME_ZH}</string>\n"
        f"  <key>CFBundleDisplayName</key><string>{DISPLAY_NAME_ZH}</string>\n"
        f"  <key>CFBundleIdentifier</key><string>{APP_ID}</string>\n"
        f"  <key>CFBundleShortVersionString</key><string>{version}</string>\n"
        "  <key>CFBundlePackageType</key><string>APPL</string>\n"
        "  <key>CFBundleExecutable</key><string>launch</string>\n"
        "  <key>NSHighResolutionCapable</key><true/>\n"
        "</dict></plist>\n",
        encoding="utf-8",
    )
    executable = contents / "MacOS" / "launch"
    executable.write_text(
        "#!/bin/sh\n"
        'HERE="$(cd "$(dirname "$0")/../../.." && pwd)"\n'
        'export PYTHONPATH="$HERE"\n'
        'exec "$HERE/runtime/bin/python3" -m apps.studio.desktop "$@"\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    icon = ICON_DIR / "fantasy-agent-512.png"
    if icon.exists():
        shutil.copy2(icon, contents / "Resources" / "icon.png")
    report.artefacts.append(app)

    if shutil.which("hdiutil") is None:
        report.skip("hdiutil not found; .dmg must be built on macOS")
        return
    dmg = DIST / f"{DISPLAY_NAME_ZH}-{version}.dmg"
    result = subprocess.run(
        ["hdiutil", "create", "-volname", DISPLAY_NAME_ZH, "-srcfolder", str(app), str(dmg)],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("hdiutil failed")
    report.artefacts.append(dmg)
    report.warn("the .app and .dmg are UNSIGNED and are not notarised")


def _finalise_linux(stage: Path, version: str, report: Report) -> None:
    """Produce an AppImage and a .deb, whichever tools are present."""
    # The .deb layout is fixed by policy; the control file is the only part
    # that is ours to write.
    deb_root = DIST / "deb" / DISPLAY_NAME_ZH
    if deb_root.exists():
        shutil.rmtree(deb_root)
    (deb_root / "DEBIAN").mkdir(parents=True)
    (deb_root / "usr" / "lib" / BUNDLE_NAME).parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(stage, deb_root / "usr" / "lib" / BUNDLE_NAME, dirs_exist_ok=True)
    (deb_root / "usr" / "bin").mkdir(parents=True, exist_ok=True)
    link = deb_root / "usr" / "bin" / BUNDLE_NAME
    link.write_text(
        f'#!/bin/sh\nexec /usr/lib/{BUNDLE_NAME}/runtime/bin/python3 -m apps.studio.desktop "$@"\n',
        encoding="utf-8",
    )
    link.chmod(0o755)
    (deb_root / "DEBIAN" / "control").write_text(
        f"Package: {BUNDLE_NAME}\n"
        f"Version: {version}\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Architecture: amd64\n"
        "Maintainer: Fantasy Agent <noreply@example.invalid>\n"
        "Description: AI-native local game production workbench\n"
        " Single-process local workbench that turns a gameplay idea into a\n"
        " playable 5-15 minute vertical slice.\n",
        encoding="utf-8",
    )

    if shutil.which("dpkg-deb") is None:
        report.skip("dpkg-deb not found; the .deb tree is staged but not built")
    else:
        deb = DIST / f"{BUNDLE_NAME}_{version}_amd64.deb"
        result = subprocess.run(["dpkg-deb", "--build", str(deb_root), str(deb)], check=False)
        if result.returncode != 0:
            raise RuntimeError("dpkg-deb failed")
        report.artefacts.append(deb)

    if shutil.which("appimtool") is None and shutil.which("appimagetool") is None:
        report.skip("appimagetool not found; AppImage needs it (or linuxdeploy)")
    else:
        tool = shutil.which("appimagetool") or shutil.which("appimtool")
        appdir = DIST / f"{DISPLAY_NAME_ZH}.AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        shutil.copytree(stage, appdir, dirs_exist_ok=True)
        (appdir / f"{BUNDLE_NAME}.desktop").write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={DISPLAY_NAME_ZH}\n"
            f"Exec={BUNDLE_NAME}\n"
            "Categories=Development;\n",
            encoding="utf-8",
        )
        appimage = DIST / f"{DISPLAY_NAME_ZH}-{version}.AppImage"
        result = subprocess.run([str(tool), str(appdir), str(appimage)], check=False)
        if result.returncode != 0:
            raise RuntimeError("appimagetool failed")
        appimage.chmod(0o755)
        report.artefacts.append(appimage)


FINALISERS = {
    "windows": _finalise_windows,
    "macos": _finalise_macos,
    "linux": _finalise_linux,
}


def build(target: str, *, version: str | None = None) -> Report:
    """Build the bundle for ``target``. Raises on anything that would ship broken."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unknown target {target!r}; expected one of {SUPPORTED_TARGETS}")

    native = current_target()
    if target != native:
        raise RuntimeError(
            f"cannot build the {target} bundle on {native}: a native interpreter "
            f"and installer toolchain are required, and the staged runtime is a "
            f"copy of *this* platform's interpreter -- it does not change "
            f"architecture. Run this on {target} (or via the CI matrix in "
            f".github/workflows/release.yml)."
        )

    version = version or read_version()
    report = Report(target=target, output_dir=DIST)
    print(f"{DISPLAY_NAME_ZH} {version} -> {target}")

    ensure_frontend_built(report)
    ensure_icons(report)

    stage = DIST / BUNDLE_NAME
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    print("copying payload")
    _copy_payload(stage)
    print("staging runtime")
    _stage_runtime(stage)
    _write_launcher(stage, target)
    _write_version_stamp(stage, version, target)
    report.artefacts.append(stage)

    FINALISERS[target](stage, version, report)

    print()
    print(f"artefacts ({len(report.artefacts)}):")
    for artefact in report.artefacts:
        print(f"  {artefact.relative_to(ROOT)}")
    if report.warnings:
        print("warnings:")
        for warning in report.warnings:
            print(f"  {warning}")
    if report.skipped:
        print("skipped:")
        for line in report.skipped:
            print(f"  {line}")
    print()
    print("Nothing here is code-signed. Do not describe a release as signed or")
    print("notarised until certificates are wired into the release workflow.")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="package-desktop",
        description="为当前平台构建灵构工坊桌面分发包。",
    )
    parser.add_argument(
        "--target",
        choices=SUPPORTED_TARGETS,
        default=None,
        help="platform to build for (defaults to the current one; must match it)",
    )
    parser.add_argument("--version", default=None, help="override the version from pyproject.toml")
    parser.add_argument(
        "--zip",
        action="store_true",
        help="also write a .zip of the directory bundle, for a hand-off without an installer",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = args.target or current_target()
    try:
        report = build(target, version=args.version)
    except (RuntimeError, ValueError) as exc:
        print(f"打包失败：{exc}", file=sys.stderr)
        return 1

    if args.zip:
        archive = DIST / f"{BUNDLE_NAME}-{report.target}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in (DIST / BUNDLE_NAME).rglob("*"):
                if path.is_file():
                    bundle.write(path, path.relative_to(DIST))
        print(f"zip: {archive.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
