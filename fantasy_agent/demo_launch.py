"""The one demo launch both the CLI and Studio call.

Godot and Unreal keep their own executors. This module only decides which
one runs, resolves executables, and rejects a resume that would otherwise
be silently ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fantasy_agent.contracts import DirectorBuildPlan, EnemyPressureTuning
from fantasy_agent.executor import ExecutionResult
from fantasy_agent.godot_mcp import DEFAULT_WORKSPACE_ROOT
from fantasy_agent.pipeline_state import normalize_resume_from

DemoEngine = Literal["godot", "unreal"]


class DemoLaunchError(ValueError):
    """A launch that must not start.

    ``message`` is the CLI sentence. Studio maps ``code`` to its own HTTP
    detail so the library does not raise ``HTTPException``.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedExecutables:
    """Paths a launch will actually pass to an executor."""

    godot_exe: str
    godot_found: bool
    blender_exe: str
    blender_found: bool
    unreal_cmd: str
    unreal_found: bool


@dataclass(frozen=True)
class DemoLaunch:
    """Inputs shared by the CLI and Studio. Transports fill only what they know."""

    plan: DirectorBuildPlan
    engine: str = ""
    confirmed: bool = False
    session_id: str = ""
    resume_from: str | None = None
    with_assets: bool = False
    with_visuals: bool = False
    with_gameplay: bool = False
    enemy_tuning: EnemyPressureTuning | None = None
    approval_manifest_path: str | None = None
    godot_exe: str | None = None
    blender_exe: str | None = None
    unreal_cmd: str | None = None
    run_import: bool = True
    comfyui_endpoint: str | None = None
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT
    resolved: ResolvedExecutables | None = None


def new_session_id() -> str:
    """Session ids are timestamps so a later resume can name the same run."""

    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


_ENGINE_TOKEN = re.compile(r"[a-z0-9]+")


def _engine_tokens(text: str) -> list[str]:
    return _ENGINE_TOKEN.findall(text.casefold())


def _names_godot(text: str) -> bool:
    return any(token == "godot" or token.startswith("godot") for token in _engine_tokens(text))


def _names_unreal(text: str) -> bool:
    for token in _engine_tokens(text):
        if token == "unreal" or token.startswith("unreal"):
            return True
        # "ue" and "ue5" / "ue5.4", not the letters inside "value", "rescue", or "queue".
        if token == "ue" or (token.startswith("ue") and token[2:].isdigit()):
            return True
    return False


def infer_demo_engine(plan: DirectorBuildPlan, override: str = "") -> DemoEngine:
    """Pick the executor.

    This is not ``workflows._is_godot_engine``. That helper only stamps a
    version onto each engine plan. An empty override here falls through to
    ``engine_choice`` when a spec has one, then to Godot. Matching is by
    token, so a word that merely contains "ue" does not select Unreal.
    """

    for text in (override or "", getattr(plan.gameplay_spec, "engine_choice", "") or ""):
        if _names_godot(text):
            return "godot"
        if _names_unreal(text):
            return "unreal"
    return "godot"


def resolve_demo_executables(
    *,
    godot_exe: str | None = None,
    blender_exe: str | None = None,
    unreal_cmd: str | None = None,
) -> ResolvedExecutables:
    """Resolve each binary once. An explicit path wins and skips the probe."""

    from fantasy_agent import local_tools

    godot = godot_exe or local_tools._find_godot()
    blender = blender_exe or local_tools._find_blender()
    if unreal_cmd:
        unreal = unreal_cmd
    else:
        unreal = local_tools._unreal_cmd_executable(local_tools._find_unreal())
    return ResolvedExecutables(
        godot_exe=godot or "godot",
        godot_found=bool(godot),
        blender_exe=blender or "blender",
        blender_found=bool(blender),
        unreal_cmd=unreal or "UnrealEditor-Cmd",
        unreal_found=bool(unreal),
    )


def normalize_demo_resume(
    plan: DirectorBuildPlan,
    override: str = "",
    *,
    session_id: str = "",
    resume_from: str | None = None,
) -> str | None:
    """Return the execution stage to resume from, or None when not resuming.

    A minted session id must not be passed here. An empty ``session_id`` with
    a resume point is the caller's failure to name the run, not an invitation
    to start a new one.
    """

    if not resume_from:
        return None
    engine = infer_demo_engine(plan, override)
    if engine != "godot":
        raise DemoLaunchError(
            "resume_not_supported",
            "Unreal resume is not wired; --from-stage cannot be ignored "
                "on the Unreal path.",
        )
    if not session_id:
        raise DemoLaunchError(
            "resume_needs_session",
            "--from-stage needs --session-id to know which run to resume.",
        )
    try:
        return normalize_resume_from(resume_from)
    except ValueError as exc:
        raise DemoLaunchError("bad_stage", str(exc)) from exc


def launch_demo(request: DemoLaunch) -> ExecutionResult:
    """Run the Godot or Unreal executor. Does not print, exit, or enqueue a job."""

    from fantasy_agent import executor

    resume_from = normalize_demo_resume(
        request.plan,
        request.engine,
        session_id=request.session_id,
        resume_from=request.resume_from,
    )
    session_id = request.session_id or new_session_id()
    tools = request.resolved or resolve_demo_executables(
        godot_exe=request.godot_exe,
        blender_exe=request.blender_exe,
        unreal_cmd=request.unreal_cmd,
    )
    engine = infer_demo_engine(request.plan, request.engine)
    if engine == "unreal":
        return executor.execute_unreal_demo(
            request.plan,
            session_id=session_id,
            confirmed=request.confirmed,
            unreal_cmd=tools.unreal_cmd,
            workspace_root=request.workspace_root,
            run_validation=request.run_import,
        )
    return executor.execute_godot_demo(
        request.plan,
        session_id=session_id,
        confirmed=request.confirmed,
        godot_exe=tools.godot_exe,
        workspace_root=request.workspace_root,
        run_import=request.run_import,
        with_assets=request.with_assets,
        blender_exe=tools.blender_exe,
        with_visuals=request.with_visuals,
        comfyui_endpoint=request.comfyui_endpoint,
        with_gameplay=request.with_gameplay,
        enemy_tuning=request.enemy_tuning,
        approval_manifest_path=request.approval_manifest_path,
        resume_from=resume_from,
    )
