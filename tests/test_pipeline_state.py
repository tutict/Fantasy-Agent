"""Tests for the persisted stage state and node-level resume.

The waste this prevents: ComfyUI, Blender and headless import each cost
minutes. When only the last node failed, a re-run must not replay the ones that
already succeeded. These tests pin down both halves of that guarantee -- that
finished stages are recorded, and that *only* stages which genuinely succeeded
are skipped (a failed stage is never silently treated as done).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import get_args

import pytest

from fantasy_agent.contracts import ProductionPipelineStageId, PromptRequest
from fantasy_agent.executor import execute_godot_demo
from fantasy_agent.godot_mcp import GodotMCPBridge
from fantasy_agent.pipeline_state import (
    GODOT_STAGE_ORDER,
    ORCHESTRATION_TO_EXECUTOR_STAGES,
    RESUMABLE_STAGES,
    REWORK_TARGET_STAGES,
    UNREAL_STAGE_ORDER,
    PipelineState,
    StageState,
    executor_stages_for,
    load_state,
    normalize_resume_from,
    orchestration_stages_for,
    record_stage,
    stages_before,
)
from fantasy_agent.workflows import run_director_workflow


def _plan(prompt: str = "rooftop parkour chase across neon towers"):
    return run_director_workflow(
        PromptRequest(prompt=prompt, target_minutes=10, engine_version="Godot 4")
    )


def _ok_runner(*args, **kwargs):
    return subprocess.CompletedProcess(
        args=args[0], returncode=0, stdout="import ok", stderr=""
    )


def _run(tmp_path: Path, session_id: str, **kwargs):
    bridge = kwargs.pop("bridge", None) or GodotMCPBridge(tmp_path, runner=_ok_runner)
    return execute_godot_demo(
        _plan(),
        session_id=session_id,
        confirmed=True,
        godot_exe="godot",
        workspace_root=tmp_path,
        bridge=bridge,
        **kwargs,
    )


# ── persistence ──────────────────────────────────────────────────────────────


def test_finished_stages_are_recorded(tmp_path: Path):
    result = _run(tmp_path, "record-basic")

    assert result.ok
    state = load_state("record-basic", workspace_root=tmp_path)
    assert state is not None
    assert state.done_stages() >= {"create", "validate", "import"}
    assert state.project_dir == result.project_dir


def test_state_file_stays_inside_the_generated_sandbox(tmp_path: Path):
    record_stage(
        "sandbox-check",
        StageState(name="create", status="done"),
        workspace_root=tmp_path,
    )

    written = list((tmp_path / "generated").rglob("_pipeline_state.json"))
    assert len(written) == 1
    assert "generated/godot/sessions/sandbox-check" in written[0].as_posix()


def test_record_stage_upserts_instead_of_duplicating(tmp_path: Path):
    record_stage(
        "upsert", StageState(name="gameplay", status="failed"), workspace_root=tmp_path
    )
    record_stage(
        "upsert", StageState(name="gameplay", status="done"), workspace_root=tmp_path
    )

    state = load_state("upsert", workspace_root=tmp_path)
    assert state is not None
    assert [s.name for s in state.stages] == ["gameplay"]
    assert state.get("gameplay").status == "done"
    assert state.done_stages() == {"gameplay"}
    assert state.failed_stages() == set()


def test_corrupt_state_file_is_ignored(tmp_path: Path):
    path = tmp_path / "generated/godot/sessions/corrupt/_pipeline_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    assert load_state("corrupt", workspace_root=tmp_path) is None


# ── resume ───────────────────────────────────────────────────────────────────


def test_resume_skips_earlier_completed_stages(tmp_path: Path):
    """Re-running from `import` must not replay `gameplay`."""

    _run(tmp_path, "resume-skip", with_gameplay=True)

    second = _run(tmp_path, "resume-skip", with_gameplay=True, resume_from="import")

    statuses = {s.name: s.status for s in second.stages}
    # gameplay already succeeded in the first run; replaying it would waste time.
    assert statuses["gameplay"] == "skipped"
    # create/validate are cheap and everything downstream needs their output.
    assert statuses["create"] == "done"
    assert second.ok


def test_resume_does_not_skip_stages_that_never_ran(tmp_path: Path):
    """Only stages recorded as done are skipped -- never merely earlier ones."""

    _run(tmp_path, "resume-cold", with_gameplay=False)

    second = _run(tmp_path, "resume-cold", with_gameplay=True, resume_from="import")

    statuses = {s.name: s.status for s in second.stages}
    # gameplay never succeeded in this session, so it must really run now.
    assert statuses["gameplay"] == "done"


def test_failed_stage_is_never_treated_as_done(tmp_path: Path):
    record_stage(
        "resume-failed",
        StageState(name="blender", status="failed", detail="export crashed"),
        workspace_root=tmp_path,
    )

    second = _run(tmp_path, "resume-failed", resume_from="import")

    # A failed node is exactly what should be re-run, so it must not be skipped.
    assert "blender" not in {s.name for s in second.stages if s.status == "skipped"}


def test_unknown_resume_target_is_rejected_loudly(tmp_path: Path):
    """An unrecognised resume point must fail, not silently replay everything.

    The old contract was "skip nothing", which is safe but degrades a typo into
    a full replay of every minute-scale node -- the exact waste this module
    exists to prevent. Entry points (CLI / Studio) validate before the run
    starts, so this only guards programmatic callers.
    """

    _run(tmp_path, "resume-unknown", with_gameplay=True)

    # The first run leaves real state, so the second one gets as far as
    # resolving the resume point -- and fails there instead of replaying.
    with pytest.raises(ValueError, match="未知的续跑节点"):
        _run(tmp_path, "resume-unknown", with_gameplay=True, resume_from="nope")


def test_resuming_from_a_rework_target_skips_real_work(tmp_path: Path):
    """`godot_plan` fixes only touch the project structure.

    Gameplay codegen does not depend on it, so a plan fix must reuse the
    scripts already generated instead of running the LLM/codegen node again.
    """

    _run(tmp_path, "resume-plan", with_gameplay=True)

    second = _run(tmp_path, "resume-plan", with_gameplay=True, resume_from="godot_plan")

    skipped = {s.name for s in second.stages if s.status == "skipped"}
    assert "gameplay" in skipped


def test_resuming_from_spec_rebuilds_spec_derived_nodes(tmp_path: Path):
    """A spec fix invalidates visuals, assets and gameplay, so nothing skips.

    This is deliberately conservative: the cheaper alternative (skipping
    ComfyUI/Blender) would reuse visuals generated from the *old* spec.
    """

    _run(tmp_path, "resume-spec", with_gameplay=True)

    second = _run(tmp_path, "resume-spec", with_gameplay=True, resume_from="spec")

    assert not [s for s in second.stages if s.status == "skipped"]


def test_rework_targets_are_valid_resume_points():
    """A pre-flight hint must be usable as a resume point verbatim."""

    # "spec" is not a stage, but following the hint has to land somewhere real.
    assert normalize_resume_from("spec") in GODOT_STAGE_ORDER
    assert normalize_resume_from("prompt") in GODOT_STAGE_ORDER
    assert normalize_resume_from("godot_plan") in GODOT_STAGE_ORDER
    assert normalize_resume_from("flags") in GODOT_STAGE_ORDER


def test_stage_names_still_work_as_resume_points():
    assert normalize_resume_from("blender") == "blender"
    assert normalize_resume_from("  create  ") == "create"


def test_every_rework_target_maps_to_a_real_stage():
    from fantasy_agent.preflight import (
        REWORK_FLAGS,
        REWORK_PLAN,
        REWORK_PROMPT,
        REWORK_SPEC,
    )

    # Guards against drift between the two vocabularies: adding a REWORK_*
    # constant without a mapping silently reintroduces the dead hint.
    assert set(REWORK_TARGET_STAGES) == {
        REWORK_PROMPT,
        REWORK_SPEC,
        REWORK_PLAN,
        REWORK_FLAGS,
    }
    for target, stage in REWORK_TARGET_STAGES.items():
        assert stage in GODOT_STAGE_ORDER, f"{target} maps to unknown stage {stage}"


def test_resume_without_a_previous_run_skips_nothing(tmp_path: Path):
    result = _run(tmp_path, "resume-empty", resume_from="import")

    assert not [s for s in result.stages if s.status == "skipped"]
    assert result.ok


# ── orchestration vocabulary ─────────────────────────────────────────────────


def test_every_orchestration_stage_has_a_translation_entry():
    """A stage id the table forgets is a stage rework can never land on.

    Driven off the contract's own Literal rather than a hand-kept list, so
    adding a stage id without a translation fails here instead of at the first
    rework of that stage.
    """

    declared = set(get_args(ProductionPipelineStageId))

    assert set(ORCHESTRATION_TO_EXECUTOR_STAGES) == declared, (
        "the translation table and the stage-id contract have drifted"
    )


def test_every_translated_name_is_a_real_execution_stage():
    """Otherwise the translation sends a rework to a node that does not exist.

    Both routes' tuples are accepted -- `unreal_production` translates to
    Unreal's chain, which shares only some names with Godot's.
    """

    known = set(GODOT_STAGE_ORDER) | set(UNREAL_STAGE_ORDER)
    for stage_id, executor_stages in ORCHESTRATION_TO_EXECUTOR_STAGES.items():
        unknown = sorted(set(executor_stages) - known)
        assert not unknown, f"{stage_id} translates to stages that do not exist: {unknown}"


def test_only_the_human_gate_translates_to_nothing():
    """Empty is a legal, meaningful value -- not a missing entry.

    The measured executor confirms exactly one stage with no process step:
    `creative_review`, because it is a person reading art direction, not a node
    that runs. Its neighbour `approval_gate` is a *manifest filter* that
    happens during `asset_integration`, which is why that stage is not empty
    either.

    The plan for this work predicted two empty stages, `gameplay_orchestration`
    among them. The executor says otherwise: its first two steps --
    `spec_validation` and `preflight` -- read the spec and plan that stage
    produces, so leaving it empty would give a `prompt`-target rework nowhere to
    land and send every prompt fix down the full replay this table exists to
    avoid.
    """

    empty = sorted(
        stage_id for stage_id, stages in ORCHESTRATION_TO_EXECUTOR_STAGES.items() if not stages
    )

    assert empty == ["creative_review"], f"unexpected stages translate to no process step: {empty}"
    assert ORCHESTRATION_TO_EXECUTOR_STAGES["gameplay_orchestration"] == (
        "spec_validation",
        "preflight",
    )


def test_a_translation_is_readable_in_both_directions():
    """Forward is the table; backward is what a failing node needs.

    Both halves carry weight: forward answers "what does this stage actually
    run", backward answers "this node failed, which stage owns it".
    """

    assert executor_stages_for("blender_modeling") == ("blender",)
    assert orchestration_stages_for("blender") == ("blender_modeling",)
    # A name two routes both use maps back to both, so the caller picks by the
    # plan in hand rather than by a notion of "the" route baked into the table.
    assert set(orchestration_stages_for("create")) == {"godot_quick_play", "unreal_production"}
    # A name nothing claims is empty rather than an error: it is a lookup that
    # found nothing, not a broken input.
    assert orchestration_stages_for("no_such_executor_stage") == ()


def test_translating_an_unknown_orchestration_stage_fails_loudly():
    """Unknown id and "translated to nothing" must not read the same."""

    with pytest.raises(ValueError, match="unknown orchestration stage"):
        executor_stages_for("creative_revieww")


# ── ordering helpers ─────────────────────────────────────────────────────────


def test_stages_before_returns_only_earlier_stages():
    assert stages_before("import") == set(
        GODOT_STAGE_ORDER[: GODOT_STAGE_ORDER.index("import")]
    )
    assert "import" not in stages_before("import")


def test_unknown_stage_has_no_predecessors():
    assert stages_before("does-not-exist") == set()


def test_create_and_validate_are_never_resumable():
    """Skipping them would break every later stage that needs project_file."""

    assert "create" not in RESUMABLE_STAGES
    assert "validate" not in RESUMABLE_STAGES
    assert "import" not in RESUMABLE_STAGES


def test_stage_order_covers_every_stage_the_executor_emits(tmp_path: Path):
    """A stage missing from GODOT_STAGE_ORDER could never be resumed."""

    result = _run(tmp_path, "order-cover", with_gameplay=True)

    assert result.ok
    for stage in result.stages:
        assert stage.name in GODOT_STAGE_ORDER, f"{stage.name} is not resumable"


def test_state_model_defaults_to_empty():
    state = PipelineState(session_id="empty")

    assert state.stages == []
    assert state.done_stages() == set()
    assert state.failed_stages() == set()
    assert state.get("nope") is None
