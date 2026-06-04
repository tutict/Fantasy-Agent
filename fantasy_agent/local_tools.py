from __future__ import annotations

import json
import os
from glob import glob
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib import error, parse, request
import webbrowser

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
    for name in names:
        value = os.environ.get(name)
        if value and Path(value).exists():
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


def _find_blender() -> str | None:
    return _find_executable(
        env_names=["BLENDER_EXECUTABLE"],
        commands=["blender"],
        path_patterns=[
            "C:/Program Files/Blender Foundation/Blender */blender.exe",
            "C:/Program Files/Blender Foundation/Blender/blender.exe",
        ],
    )


def _find_unreal() -> str | None:
    return _find_executable(
        env_names=["UNREAL_EDITOR", "UE_EDITOR"],
        commands=["UnrealEditor.exe", "UnrealEditor-Cmd.exe"],
        path_patterns=[
            "C:/Program Files/Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor.exe",
            "C:/Program Files/Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor-Cmd.exe",
        ],
    )


def _find_godot() -> str | None:
    return _find_executable(
        env_names=["GODOT_EXECUTABLE"],
        commands=["godot", "godot4", "godot-console"],
        path_patterns=[
            "C:/Program Files/Godot/Godot*.exe",
            "C:/Users/*/AppData/Local/Programs/Godot/Godot*.exe",
        ],
    )


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
    candidates = [*env_candidates, *default_comfyui_endpoint_candidates()]
    failures: list[str] = []
    for endpoint in candidates:
        if not _is_local_http_endpoint(endpoint):
            continue
        try:
            stats = _http_json(f"{endpoint.rstrip('/')}/system_stats")
        except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {exc}")
            continue
        system = stats.get("system", {}) if isinstance(stats, dict) else {}
        version = system.get("comfyui_version") or "reachable"
        return _target(
            target_id="comfyui",
            status="ready",
            target=endpoint,
            openable=True,
            detail_key="manualComfyReady",
            metadata={"version": version},
        )
    return _target(
        target_id="comfyui",
        status="degraded",
        target=default_comfyui_endpoint_candidates()[0],
        openable=True,
        detail_key="manualComfyMissing",
        metadata={"failures": failures[-3:]},
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
    except FileNotFoundError as exc:
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
