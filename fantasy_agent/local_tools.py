from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from glob import glob
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from fantasy_agent.contracts import default_comfyui_endpoint_candidates

REPO_ROOT = Path(__file__).resolve().parents[1]


def _is_godot_engine(engine: str) -> bool:
    return "godot" in engine.casefold()


def _is_local_http_endpoint(endpoint: str) -> bool:
    parsed = parse.urlparse(endpoint)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _http_json(url: str, timeout: float = 0.45) -> dict[str, Any] | list[Any]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload) if payload else {}


def _candidate_paths(patterns: list[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        found.extend(path for path in glob(pattern) if Path(path).exists())
    return found


def _existing_env_path(names: list[str]) -> str | None:
    """The path a variable names, if it names a *file*.

    ``exists()`` was the test, and it let a directory through: told to "set
    ``GODOT_EXECUTABLE`` to the Godot executable", a user pointing it at the
    folder that holds the executable is a natural mistake, and it made the
    status panel report ``ready`` on a folder -- then the launch raised
    ``PermissionError`` instead of the ``FileNotFoundError`` the caller expects.
    Naming a directory is not naming a binary, so it falls through to PATH and
    the install-location search, which is where a usable answer comes from.
    """

    for name in names:
        value = os.environ.get(name)
        if value and Path(value).is_file():
            return value
    return None


def _find_executable(
    *,
    env_names: list[str],
    commands: list[str],
    path_patterns: list[str],
) -> str | None:
    env_path = _existing_env_path(env_names)
    if env_path:
        return env_path
    for command in commands:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    for candidate in _candidate_paths(path_patterns):
        return candidate
    return None


#: Godot's version as it appears in a download name, ``Godot_v4.6.3-stable``.
#: The ``Godot_v`` prefix is what makes a number a version rather than noise.
_GODOT_VERSION_IN_NAME = re.compile(r"Godot_v(\d+(?:\.\d+)*)", re.IGNORECASE)


def _godot_candidate_key(path: str) -> tuple[tuple[int, ...], int, str]:
    """Sort key: the Godot version, the console build, then the whole path.

    The version comes from a ``Godot_v4.6.3``-shaped name -- the file's own name
    first, then its parent directory, which is what carries it for an install
    whose exe was renamed -- rather than from every digit in the path. Taking
    all digits mixed in whatever else happened to hold them:
    ``C:\\Users\\user99\\Downloads\\Godot_v4.5-stable_win64`` keyed as
    ``(99, 4, 5, 64, ...)`` and outranked a clean ``(4, 6, 3, 64, ...)``, so the
    *older* engine won on a machine with two installed -- and ``C:/Users/*/`` is
    a segment the install search itself expands. A candidate with no such name
    sorts below one that has it.

    The console build is the tiebreak rather than the leading term: Windows
    only routes stdout through the captured pipe for that one, but it is still
    worth running a newer GUI build over an older console build.
    """

    candidate = Path(path)
    match = _GODOT_VERSION_IN_NAME.search(candidate.name) or _GODOT_VERSION_IN_NAME.search(
        candidate.parent.name
    )
    version = tuple(int(part) for part in match.group(1).split(".")) if match else ()
    console_score = 1 if "console" in candidate.name.casefold() else 0
    return version, console_score, path.casefold()


def _find_blender() -> str | None:
    return _find_executable(
        env_names=["BLENDER_EXECUTABLE"],
        commands=["blender"],
        path_patterns=[
            "C:/Program Files/Blender Foundation/Blender */blender.exe",
            "C:/Program Files/Blender Foundation/Blender/blender.exe",
        ],
    )


#: Where Epic's Launcher records what it installed. This is the only source
#: that knows about a non-default install root: the engine on this machine
#: lives at ``C:\ue\UE_5.8``, while the conventional ``Program Files`` folder
#: holds nothing but empty Launcher stubs -- so the fixed path patterns below
#: report "not installed" for a machine with a perfectly good engine on it.
_UNREAL_LAUNCHER_MANIFEST = Path("Epic/UnrealEngineLauncher/LauncherInstalled.dat")
_UNREAL_EDITOR_RELATIVE = Path("Engine/Binaries/Win64")


def _program_data_dir() -> Path | None:
    """The ProgramData root, wherever it actually is.

    ``PROGRAMDATA`` is the authority because the folder can be relocated to
    another drive; the conventional path is a fallback for the case where the
    variable is absent from the environment.
    """

    value = os.environ.get("PROGRAMDATA")
    if value:
        candidate = Path(value)
        # A relative value would be resolved against whatever the working
        # directory happens to be, so a manifest planted alongside the process
        # could name an executable anywhere and have the resolver call it the
        # engine. ``PROGRAMDATA`` names an absolute location by definition;
        # anything else is treated as unset rather than followed.
        if candidate.is_absolute():
            return candidate
    conventional = Path("C:/ProgramData")
    return conventional if conventional.exists() else None


def _unreal_launcher_installs() -> list[str]:
    """Editor binaries from Epic's install manifest, in the order recorded.

    ``LauncherInstalled.dat`` lists plugins next to engines, so an entry only
    counts as an engine when its ``ArtifactId`` starts with ``UE_``:
    ``UE_5.8`` is the engine, while ``FabPlugin_5.8`` and ``QuixelBridge_5.7``
    share the same install folder and would otherwise be probed for an editor
    that is not there.
    """

    program_data = _program_data_dir()
    if program_data is None:
        return []
    manifest = program_data / _UNREAL_LAUNCHER_MANIFEST
    if not manifest.exists():
        return []
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []

    installs: list[str] = []
    for entry in payload.get("InstallationList") or []:
        if not isinstance(entry, dict):
            continue
        if not str(entry.get("ArtifactId") or "").startswith("UE_"):
            continue
        location = entry.get("InstallLocation")
        if location:
            installs.append(str(location))
    return [
        str(candidate)
        for location in installs
        for candidate in [Path(location) / _UNREAL_EDITOR_RELATIVE / "UnrealEditor.exe"]
        if candidate.exists()
    ]


#: The engine version as it appears in an install path: Launcher roots are
#: named ``UE_5.8``, and the manifest keys off the same ``UE_`` prefix.
_UNREAL_VERSION_IN_PATH = re.compile(r"UE_(\d+(?:\.\d+)*)", re.IGNORECASE)


def _unreal_candidate_key(path: str) -> tuple[tuple[int, ...], str]:
    """Sort key: the engine version in the path, then the whole path.

    The version is read from a ``UE_5.8``-shaped segment rather than from every
    digit in the path. Taking all digits mixed in whatever else happened to
    contain them: ``C:\\Users\\user99\\UE_5.8`` keyed as ``(99, 5, 8, 64)`` and
    outranked a clean ``(5, 9, 64)``, so the *older* engine won on a machine
    with two installed. A path with no such segment sorts below one that has it.
    """

    match = _UNREAL_VERSION_IN_PATH.search(path)
    version = tuple(int(part) for part in match.group(1).split(".")) if match else ()
    return version, path.casefold()


def _find_unreal() -> str | None:
    """Locate UnrealEditor, preferring the newest engine the Launcher installed.

    ``UNREAL_EDITOR`` / ``UE_EDITOR`` and then ``PATH`` win outright: those are
    explicit choices, and a user who names a binary has already answered the
    question. Only the *discovered* candidates -- the Launcher manifest and the
    fixed patterns -- are version-compared, because those are the ones that can
    turn up several engines at once. They cover different machines and neither
    is a superset: the manifest finds an engine installed to a custom root, and
    the fixed patterns cover one the Launcher never recorded. There is
    deliberately no sweep across drives -- a hand-placed engine is what
    ``UNREAL_EDITOR`` is for, and the CLI already tells the user to pass
    ``--unreal-exe PATH`` when this returns nothing.
    """

    env_path = _existing_env_path(["UNREAL_EDITOR", "UE_EDITOR"])
    if env_path:
        return env_path
    for command in ["UnrealEditor.exe", "UnrealEditor-Cmd.exe"]:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    candidates = [
        *_unreal_launcher_installs(),
        *_candidate_paths(
            [
                "C:/Program Files/Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor.exe",
                "C:/Program Files/Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor-Cmd.exe",
            ]
        ),
    ]
    if not candidates:
        return None
    return max(candidates, key=_unreal_candidate_key)


def _unreal_cmd_executable(editor_path: str | None) -> str | None:
    """Map a UnrealEditor.exe path to the sibling UnrealEditor-Cmd.exe.

    Headless/commandlet runs use the -Cmd variant. If the sibling exists, return
    it; otherwise fall back to the given path (it may already be the Cmd build).
    """
    if not editor_path:
        return editor_path
    path = Path(editor_path)
    if path.stem.endswith("-Cmd"):
        return editor_path
    cmd = path.with_name(f"{path.stem}-Cmd{path.suffix}")
    return str(cmd) if cmd.exists() else editor_path


def _find_godot() -> str | None:
    env_path = _existing_env_path(["GODOT_EXECUTABLE"])
    if env_path:
        return env_path
    for command in ["godot-console", "godot4", "godot"]:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    candidates = _candidate_paths(
        [
            "C:/Program Files/Godot/Godot*.exe",
            "C:/Users/*/AppData/Local/Programs/Godot/Godot*.exe",
            "C:/Users/*/Downloads/Godot*/Godot*.exe",
        ]
    )
    if candidates:
        return max(candidates, key=_godot_candidate_key)
    return None


def _target(
    *,
    target_id: str,
    status: str,
    target: str,
    openable: bool,
    detail_key: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": target_id,
        "status": status,
        "target": target,
        "openable": openable,
        "detail_key": detail_key,
        "metadata": metadata or {},
    }


def _comfyui_target() -> dict[str, Any]:
    env_candidates = [
        value
        for value in [os.environ.get("COMFYUI_URL"), os.environ.get("COMFYUI_ENDPOINT")]
        if value and _is_local_http_endpoint(value)
    ]
    probed = [
        endpoint
        for endpoint in [*env_candidates, *default_comfyui_endpoint_candidates()]
        if _is_local_http_endpoint(endpoint)
    ]
    errors: dict[int, str] = {}
    if probed:
        # Every candidate goes out at once, but the answers are read back in
        # candidate order: the highest-priority endpoint that answers wins,
        # which is what the serial version did. Two things this buys over the
        # obvious "wait for all of them" shape: a healthy first candidate
        # still returns immediately instead of waiting on a stalled later one
        # (a machine with something wedged on 8001 used to answer in 0.02s
        # and would have waited ~0.5s), and a pile of stalled candidates
        # costs one timeout in total rather than one each.
        pool = ThreadPoolExecutor(max_workers=len(probed))
        try:
            futures = {
                index: pool.submit(_http_json, f"{endpoint.rstrip('/')}/system_stats")
                for index, endpoint in enumerate(probed)
            }
            for index in range(len(probed)):
                try:
                    stats = futures[index].result()
                except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
                    errors[index] = f"{probed[index]}: {exc}"
                    continue
                system = stats.get("system", {}) if isinstance(stats, dict) else {}
                version = system.get("comfyui_version") or "reachable"
                return _target(
                    target_id="comfyui",
                    status="ready",
                    target=probed[index],
                    openable=True,
                    detail_key="manualComfyReady",
                    metadata={"version": version},
                )
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    return _target(
        target_id="comfyui",
        status="degraded",
        target=default_comfyui_endpoint_candidates()[0],
        openable=True,
        detail_key="manualComfyMissing",
        metadata={"failures": [errors[index] for index in sorted(errors)][-3:]},
    )


def _latest_file(pattern: str) -> Path | None:
    matches = [path for path in REPO_ROOT.glob(pattern) if path.exists()]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _generated_dir() -> Path:
    return REPO_ROOT / "generated"


def _generated_dir_target() -> dict[str, Any]:
    path = _generated_dir()
    return _target(
        target_id="generated",
        status="ready" if path.exists() else "unavailable",
        target=str(path),
        openable=path.exists(),
        detail_key="manualGeneratedDetail",
    )


def manual_correction_targets(engine: str = "UE5") -> dict[str, Any]:
    engine_kind = "godot" if _is_godot_engine(engine) else "unreal"
    blender = _find_blender()
    engine_executable = _find_godot() if engine_kind == "godot" else _find_unreal()
    engine_target_id = "godot" if engine_kind == "godot" else "unreal"
    return {
        "engine": engine,
        "engine_kind": engine_kind,
        "targets": [
            _target(
                target_id="planning",
                status="ready",
                target="/workbench",
                openable=True,
                detail_key="manualPlanningDetail",
            ),
            _comfyui_target(),
            _target(
                target_id="blender",
                status="ready" if blender else "unavailable",
                target=blender or "BLENDER_EXECUTABLE, blender",
                openable=bool(blender),
                detail_key="manualBlenderReady" if blender else "manualBlenderMissing",
            ),
            _target(
                target_id=engine_target_id,
                status="ready" if engine_executable else "unavailable",
                target=engine_executable
                or (
                    "GODOT_EXECUTABLE, godot"
                    if engine_kind == "godot"
                    else "UNREAL_EDITOR, UnrealEditor.exe"
                ),
                openable=bool(engine_executable),
                detail_key=(
                    "manualGodotReady"
                    if engine_kind == "godot" and engine_executable
                    else "manualGodotMissing"
                    if engine_kind == "godot"
                    else "manualUnrealReady"
                    if engine_executable
                    else "manualUnrealMissing"
                ),
            ),
            _generated_dir_target(),
        ],
    }


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _launch(args: list[str]) -> None:
    subprocess.Popen(
        args,
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _open_comfyui() -> str:
    target = _comfyui_target()["target"]
    webbrowser.open(target, new=2, autoraise=True)
    return target


def _open_blender() -> str:
    executable = _find_blender()
    if not executable:
        raise FileNotFoundError("Blender executable was not found.")
    _launch([executable])
    return executable


def _open_unreal() -> str:
    executable = _find_unreal()
    if not executable:
        raise FileNotFoundError("Unreal Editor executable was not found.")
    uproject = _latest_file("generated/**/*.uproject")
    args = [executable]
    if uproject:
        args.append(str(uproject))
    _launch(args)
    return str(uproject or executable)


def _open_godot() -> str:
    executable = _find_godot()
    if not executable:
        raise FileNotFoundError("Godot executable was not found.")
    project = _latest_file("generated/godot/**/project.godot")
    args = [executable]
    if project:
        args.extend(["--path", str(project.parent)])
    _launch(args)
    return str(project.parent if project else executable)


def _open_generated() -> str:
    path = _generated_dir()
    if not path.exists():
        raise FileNotFoundError("generated directory was not found.")
    _open_path(path)
    return str(path)


def open_manual_correction_target(
    *,
    target_id: str,
    engine: str = "UE5",
    confirmed_side_effects: bool = False,
) -> dict[str, Any]:
    if not confirmed_side_effects:
        return {
            "status": "blocked",
            "target_id": target_id,
            "target": "",
            "detail_key": "manualOpenNeedsConfirmation",
        }

    normalized = target_id.casefold()
    if normalized == "engine":
        normalized = "godot" if _is_godot_engine(engine) else "unreal"

    try:
        if normalized == "planning":
            return {
                "status": "client_route",
                "target_id": "planning",
                "target": "/workbench",
                "detail_key": "manualPlanningDetail",
            }
        if normalized == "comfyui":
            target = _open_comfyui()
        elif normalized == "blender":
            target = _open_blender()
        elif normalized == "unreal":
            target = _open_unreal()
        elif normalized == "godot":
            target = _open_godot()
        elif normalized == "generated":
            target = _open_generated()
        else:
            return {
                "status": "blocked",
                "target_id": target_id,
                "target": "",
                "detail_key": "manualOpenUnknownTarget",
            }
    # ``FileNotFoundError`` alone was too narrow: it is one ``OSError`` among
    # many, and the ones that reach here are all "this cannot be launched" --
    # a directory where an executable was expected (``PermissionError``), a file
    # that is not a runnable image (``WinError 193``). Each of them used to
    # escape this function, and the endpoint that calls it answered 500 instead
    # of reporting an unlaunchable target.
    except OSError as exc:
        return {
            "status": "unavailable",
            "target_id": normalized,
            "target": "",
            "detail_key": "manualOpenUnavailable",
            "detail": str(exc),
        }

    return {
        "status": "started",
        "target_id": normalized,
        "target": target,
        "detail_key": "manualOpenStarted",
    }
