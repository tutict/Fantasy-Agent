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

import json
from datetime import UTC, datetime
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

# Execution order for the Unreal chain. This is the `order` argument
# `stages_before` is meant to take for an Unreal session; it is pinned to what
# `execute_unreal_demo` actually emits by
# `test_unreal_stage_order_covers_every_stage_the_executor_emits`, so a stage
# the executor emits cannot go missing from it (the Godot equivalent drifted
# the same way once).
#
# Not wired to resume yet: unlike the Godot path, `execute_unreal_demo` never
# calls `record_stage`, so no Unreal session writes `_pipeline_state.json` and
# `--from-stage` does nothing for it. The tuple is here so that wiring resume
# later starts from a list that matches reality.
UNREAL_STAGE_ORDER: tuple[str, ...] = (
    "spec_validation",
    "preflight",
    "create",
    "spec_compile",
    "spec_qa",
    "prepare_ingest",
    "prepare_level",
    "validate",
)


# Rework targets and execution stages are two different vocabularies. A
# pre-flight issue names the *authoring* node to fix ("spec"); `--from-stage`
# and `resume_from` name an *execution* stage ("comfyui"). Before this table
# existed the two were never connected: a user who followed the hint and typed
# "spec" hit `stages_before`, which treats unknown names as "skip nothing" and
# silently degraded to a full replay of every expensive node.
#
# The value is the earliest stage that must re-run once the fix lands, so
# anything derived from the fixed input is rebuilt and only genuinely
# independent work is reused. Written as literals rather than importing
# `preflight.REWORK_*` to avoid an import cycle; `test_preflight.py` asserts
# the two stay in sync.
REWORK_TARGET_STAGES: dict[str, str] = {
    # A new idea regenerates the spec, the plan and every handoff, so nothing
    # downstream survives.
    "prompt": "spec_validation",
    # The spec feeds ComfyUI notes, Blender notes, the Godot route and gameplay
    # codegen. Rebuild all of them rather than risk stale artifacts.
    "spec": "comfyui",
    # A malformed handoff plan only affects the project structure; visuals,
    # assets and gameplay scripts do not depend on it.
    "godot_plan": "create",
    # The plan itself is fine; only a run switch was wrong. Re-run the stage
    # that switch gates and keep everything before it.
    "flags": "blender",
}

# Per-issue overrides for cases where the rework target alone is too coarse.
# `flags` covers two unrelated switches, and resuming from the wrong one either
# wastes a node or skips the one that needed to run.
REWORK_CODE_STAGES: dict[str, str] = {
    "assets_declared_not_enabled": "blender",
    "enemies_declared_not_generated": "gameplay",
}


# The second translation layer. `REWORK_TARGET_STAGES` above connects an
# authoring node to an *execution* stage; this connects an execution stage to
# the *orchestration* stage that owns it, so a rework hint can be turned into
# "resume from this card on the board".
#
# Two vocabularies, not one, and the split is deliberate. The three layers
# answer different questions: a rework target says *what to fix*, an execution
# stage says *which process step to re-run*, an orchestration stage says *which
# production card is being redone*. Merging the last two would leak process
# details (preflight, copy_refs) into the production semantics the board shows.
#
# An empty tuple is legal and means "this stage has no process step of its own"
# -- exactly one stage qualifies, `creative_review`, because it is a person
# reading art direction rather than a node that runs.
#
# Every value was checked against what `execute_godot_demo` /
# `execute_unreal_demo` actually emit, not read off the source: `GODOT_STAGE_ORDER`
# had drifted from its executor once already. The measured order is
# `spec_validation, preflight, comfyui, blender, approval_gate, gameplay, create,
# enemy_metrics, copy_assets, copy_refs, validate, import` for Godot and
# `preflight, create, spec_compile, spec_qa, prepare_ingest, prepare_level,
# validate` for Unreal, with `spec_validation` and the copy steps conditional.
#
# The plan for this work predicted `gameplay_orchestration` would be empty too.
# Measurement says otherwise: the first two executor steps read the spec and
# plan that stage produces, and leaving it empty would give a `prompt`-target
# rework nowhere to land.
ORCHESTRATION_TO_EXECUTOR_STAGES: dict[str, tuple[str, ...]] = {
    "gameplay_orchestration": ("spec_validation", "preflight"),
    "comfyui_visual_production": ("comfyui",),
    "blender_modeling": ("blender",),
    "creative_review": (),
    "asset_integration": ("approval_gate", "copy_assets", "copy_refs"),
    "godot_quick_play": ("gameplay", "create", "enemy_metrics", "validate", "import"),
    "unreal_production": (
        "create",
        "spec_compile",
        "spec_qa",
        "prepare_ingest",
        "prepare_level",
        "validate",
    ),
    "optimization_testing": ("validate",),
}


def executor_stages_for(stage_id: str) -> tuple[str, ...]:
    """Execution stages an orchestration stage stands for.

    Raises:
        ValueError: for an id that is not in the table. The alternative --
            returning an empty tuple -- would make a typo indistinguishable
            from ``creative_review``, which legitimately has no process step.
    """

    try:
        return ORCHESTRATION_TO_EXECUTOR_STAGES[stage_id]
    except KeyError:
        known = ", ".join(sorted(ORCHESTRATION_TO_EXECUTOR_STAGES))
        raise ValueError(
            f"unknown orchestration stage {stage_id!r}; known stages: {known}"
        ) from None


def orchestration_stages_for(executor_stage: str) -> tuple[str, ...]:
    """Orchestration stages whose translation contains ``executor_stage``.

    More than one can match, and that is not a defect in the table: `create`,
    `validate` and `preflight` happen on both routes, and `validate` is reached
    from both a playable-verification card and an optimisation one. The caller
    picks using the plan in hand -- see ``Orchestrator.rewind_for_rework`` --
    rather than this module guessing which route the caller meant.

    An empty result means "no orchestration stage claims this name", which is a
    lookup that found nothing rather than a broken input, so it does not raise.
    """

    return tuple(
        stage_id
        for stage_id, executor_stages in ORCHESTRATION_TO_EXECUTOR_STAGES.items()
        if executor_stage in executor_stages
    )


def normalize_resume_from(
    value: str,
    order: tuple[str, ...] = GODOT_STAGE_ORDER,
) -> str:
    """Turn a user-supplied resume point into a real execution stage.

    Accepts either an execution stage name or a re-work target, so both
    `--from-stage blender` and `--from-stage spec` behave sensibly.

    Raises:
        ValueError: when the value is neither, instead of silently replaying
            the whole chain. A typo must surface as an error, not as a slow run.
    """

    candidate = value.strip()
    if candidate in order:
        return candidate
    mapped = REWORK_TARGET_STAGES.get(candidate) or REWORK_CODE_STAGES.get(candidate)
    if mapped and mapped in order:
        return mapped
    known = ", ".join(sorted(order))
    targets = ", ".join(sorted(REWORK_TARGET_STAGES))
    raise ValueError(
        f"未知的续跑节点 {value!r}；可用阶段：{known}；可用的返工目标：{targets}"
    )


def resume_stage_for(rework_target: str, code: str = "") -> str | None:
    """Execution stage to resume from after fixing an issue.

    Returns None for an unrecognised target so callers can fall back to the
    existing behaviour instead of inventing a mapping.
    """

    if code and code in REWORK_CODE_STAGES:
        return REWORK_CODE_STAGES[code]
    return REWORK_TARGET_STAGES.get(rework_target)


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
    return datetime.now(UTC).isoformat(timespec="seconds")


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


