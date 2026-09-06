"""Persistent stage state for a pipeline session.

Sessions already wrote their artifacts under
``generated/<engine>/sessions/<session_id>/``, but nothing recorded *how far*
a run got. Any failure therefore meant replaying the whole chain, including the
minute-scale nodes (ComfyUI, Blender, headless import) that had already
succeeded once.

This module writes one small JSON file per session recording every finished
stage, so a later run can skip what already succeeded and resume from a chosen
node instead of starting over.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import Field

from fantasy_agent.contracts import StrictModel
from fantasy_agent.path_safety import resolve_workspace_path

STATE_FILENAME = "_pipeline_state.json"

# Statuses that count as "already done" when resuming.
DONE_STATUSES = frozenset({"done"})

# Execution order for the Godot chain. Resuming from a stage skips every
# stage before it. Unknown stages are never skipped. Keep this in sync with
# `execute_godot_demo`: a stage missing from this tuple can never be resumed.
GODOT_STAGE_ORDER: tuple[str, ...] = (
    "spec_validation",
    "preflight",
    "comfyui",
    "blender",
    "approval_gate",
    "gameplay",
    "create",
    "enemy_metrics",
    "copy_assets",
    "copy_refs",
    "validate",
    "import",
)


# Stages that are safe to skip when resuming. `create` and `validate` are
# excluded on purpose: they are cheap, and every later stage needs the
# project_file they produce.
RESUMABLE_STAGES: frozenset[str] = frozenset(
    {"comfyui", "blender", "approval_gate", "gameplay", "copy_assets", "copy_refs"}
)

UNREAL_STAGE_ORDER: tuple[str, ...] = (
    "preflight",
    "create",
    "spec_compile",
    "prepare_ingest",
    "prepare_level",
    "validate",
)


class StageState(StrictModel):
    """One finished (or skipped) stage, as persisted on disk."""

    name: str
    status: str
    detail: str = ""
    artifacts: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    finished_at: str = ""


class PipelineState(StrictModel):
    """Per-session record of how far a run got."""

    source: str = "fantasy-agent.pipeline-state"
    schema_version: str = "0.1"
    session_id: str
    engine_key: str = "godot"
    project_dir: str = ""
    updated_at: str = ""
    stages: list[StageState] = Field(default_factory=list)

    def done_stages(self) -> set[str]:
        return {stage.name for stage in self.stages if stage.status in DONE_STATUSES}

    def failed_stages(self) -> set[str]:
        return {stage.name for stage in self.stages if stage.status == "failed"}

    def get(self, name: str) -> StageState | None:
        return next((stage for stage in self.stages if stage.name == name), None)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(
    session_id: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> Path:
    """Path of the session state file, kept inside the generated sandbox."""

    relative = f"generated/{engine_key}/sessions/{session_id}/{STATE_FILENAME}"
    return resolve_workspace_path(
        relative,
        workspace_root=workspace_root,
        required_prefix=f"generated/{engine_key}",
    )


def load_state(
    session_id: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> PipelineState | None:
    """Read the session state, or None when there is nothing usable."""

    path = state_path(
        session_id, engine_key=engine_key, workspace_root=workspace_root
    )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        return PipelineState.model_validate(payload)
    except Exception:  # noqa: BLE001 - a corrupt state file must not break a run
        return None


def record_stage(
    session_id: str,
    stage: StageState,
    *,
    engine_key: str = "godot",
    project_dir: str = "",
    workspace_root: Path | str,
) -> PipelineState:
    """Upsert one stage and persist the whole state file.

    Called as each stage finishes, so a crash mid-run still leaves a usable
    record of what had already succeeded.
    """

    state = load_state(
        session_id, engine_key=engine_key, workspace_root=workspace_root
    ) or PipelineState(session_id=session_id, engine_key=engine_key)

    existing = state.get(stage.name)
    if existing is not None:
        state.stages.remove(existing)
    state.stages.append(stage)
    if project_dir:
        state.project_dir = project_dir
    state.updated_at = _now()

    path = state_path(
        session_id, engine_key=engine_key, workspace_root=workspace_root
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return state


def stages_before(target: str, order: tuple[str, ...] = GODOT_STAGE_ORDER) -> set[str]:
    """Stages that come strictly before ``target``.

    An unknown target yields an empty set, so a typo can never silently skip
    work that should have run.
    """

    if target not in order:
        return set()
    return set(order[: order.index(target)])


