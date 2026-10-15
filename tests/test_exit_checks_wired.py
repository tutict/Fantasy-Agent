"""``exit_checks`` is wired, and the checks can actually fail.

Two different things are proved here, and both were missing before 2026-10-13:

1. **The plumbing.** ``ProductionPipelineStage.exit_checks`` existed, the
   orchestrator had a complete consumer for it, and ``_pipeline_stage`` had no
   parameter to fill it -- so every stage declared an empty list and the
   consumer was dead code. ``test_pipeline_contract`` pins the table; this file
   pins that a check *runs* and * bites*.
2. **The checks themselves.** A check that cannot fail is worse than no check,
   because it reads as coverage. Each of the four is exercised against a real
   generated plan (which must pass -- a check that fails a good run is the
   failure mode that would make the whole mechanism useless) and against a
   degraded copy of the same plan (which must fail, naming the problem).

The Godot project check is called the way the orchestrator calls it: with no
arguments at all. That is the whole reason ``validate_godot_project`` resolves
its target from the run's own plan -- a check that needed a path from a caller
would be a check that never runs.
"""

from __future__ import annotations

from pathlib import Path

from fantasy_agent.contracts import (
    GodotMCPCreateProjectRequest,
    GodotMCPValidateProjectRequest,
    ProductionPipelineStage,
    PromptRequest,
)
from fantasy_agent.godot_mcp import GodotMCPBridge
from fantasy_agent.orchestrator import DONE, FAILED, Orchestrator, StageOutcome
from fantasy_agent.tool_registry import combined_registry
from fantasy_agent.workflows import run_director_workflow

PROMPT = "a stealth courier escapes a haunted train station in ten minutes"


def _plan():
    return run_director_workflow(
        PromptRequest(prompt=PROMPT, engine_version="Godot 4"), use_llm=False
    )


def _stage(*exit_checks: str) -> ProductionPipelineStage:
    return ProductionPipelineStage(
        id="godot_quick_play",
        order=1,
        title="Godot production",
        purpose="build the slice",
        owner_agent="godot-builder",
        inputs=["GodotProjectPlan"],
        outputs=["project.godot"],
        mcp_tools=[],
        exit_checks=list(exit_checks),
    )


def _run_checks(
    workspace_root: Path, names: tuple[str, ...], *, artifacts: dict | None = None
) -> StageOutcome:
    """Run the named checks the way ``Orchestrator._advance`` does.

    Through the private seam on purpose: it is the one place the orchestrator
    reads a stage's own output back, and going through ``run()`` here would
    spend a model turn proving nothing about the check.
    """

    registry = combined_registry(workspace_root)
    if artifacts:
        registry.remember_plan(artifacts)
    orchestrator = Orchestrator(
        session_id="checks", workspace_root=workspace_root, registry=registry
    )
    outcome = StageOutcome("godot_quick_play", DONE)
    orchestrator._run_exit_checks(_stage(*names), outcome)
    return outcome


# ── the Godot project check ─────────────────────────────────────────────────


def test_a_workspace_with_no_project_fails_the_godot_check(tmp_path: Path):
    """The vacuous gate, closed from the other side.

    Before this, a stage could report itself done with no project on disk at
    all. Now the check looks for the project the run's own plan names and finds
    nothing, which is a failed stage rather than a verified one.
    """

    outcome = _run_checks(tmp_path, ("validate_godot_project",), artifacts=_plan().model_dump(mode="json"))

    assert outcome.status == FAILED
    assert "validate_godot_project" in outcome.detail
    assert outcome.checks == []


def test_a_generated_project_passes_the_godot_check(tmp_path: Path):
    """The positive control, and the reason the check resolves its own path.

    The project is written by the same tool a real run uses, and the plan is
    remembered the way ``run_agent`` remembers one -- so the check finds the
    project by derivation rather than by being handed a path.
    """

    plan = _plan()
    registry = combined_registry(tmp_path)
    registry.remember_plan(plan.model_dump(mode="json"))
    created = registry.call(
        "create_godot_project_structure",
        {"write_files": True},
        allow_write=True,
    )
    assert created.status == "ok", created.content

    outcome = _run_checks(
        tmp_path, ("validate_godot_project",), artifacts=plan.model_dump(mode="json")
    )

    assert outcome.status == DONE
    assert outcome.checks == ["validate_godot_project"]


def test_a_broken_project_fails_the_godot_check_with_the_reason(tmp_path: Path):
    """Not just "failed" -- which file and what is wrong with it.

    A stage that fails without saying why sends the rework to the wrong node.
    """

    plan = _plan()
    registry = combined_registry(tmp_path)
    registry.remember_plan(plan.model_dump(mode="json"))
    registry.call("create_godot_project_structure", {"write_files": True}, allow_write=True)

    # Break the one thing the check reads first: the main scene pointer.
    project_file = tmp_path / "generated/godot" / _slug_of(plan.godot_plan.project_name) / "project.godot"
    project_file.write_text(
        project_file.read_text(encoding="utf-8").replace(
            'run/main_scene="res://scenes/main.tscn"', 'run/main_scene="res://scenes/missing.tscn"'
        ),
        encoding="utf-8",
    )

    outcome = _run_checks(
        tmp_path, ("validate_godot_project",), artifacts=plan.model_dump(mode="json")
    )

    assert outcome.status == FAILED
    assert "Main scene does not exist" in outcome.detail


def test_a_check_with_no_plan_to_read_fails_rather_than_passes(tmp_path: Path):
    """"This run never planned a Godot project" is a failed check, not a pass.

    The registry refuses the call before the bridge sees it, which is the same
    answer for a different reason: the stage claims to have built something the
    run never planned.
    """

    outcome = _run_checks(tmp_path, ("validate_godot_project",))

    assert outcome.status == FAILED
    assert "godot_plan" in outcome.detail


def _slug_of(project_name: str) -> str:
    from fantasy_agent.godot_mcp import _slug

    return _slug(project_name)


# ── the three plan checks ───────────────────────────────────────────────────


def test_the_gameplay_spec_check_passes_a_generated_spec():
    from fantasy_agent.plan_checks import check_gameplay_spec

    assert check_gameplay_spec(_plan().gameplay_spec) == []


def test_the_gameplay_spec_check_fails_a_spec_nobody_could_test():
    """One decision written three times is one decision.

    ``GameplaySpec`` enforces ``min_length=3`` on ``core_loop`` and says nothing
    about the decisions being distinct, so this is the shape that reaches a
    generated plan intact and is still untestable.
    """

    from fantasy_agent.plan_checks import check_gameplay_spec

    spec = _plan().gameplay_spec
    degraded = spec.model_copy(
        update={
            "core_loop": [
                step.model_copy(update={"player_decision": "press the only button"})
                for step in spec.core_loop
            ],
            "win_state": "",
            "failure_states": [],
        }
    )

    problems = check_gameplay_spec(degraded)

    assert any("distinct player decision" in problem for problem in problems)
    assert any("win_state" in problem for problem in problems)
    assert any("failure_states" in problem for problem in problems)


def test_the_blender_plan_check_passes_a_generated_plan():
    from fantasy_agent.plan_checks import check_blender_plan

    assert check_blender_plan(_plan().blender_plan) == []


def test_the_blender_plan_check_fails_a_plan_that_exports_nowhere_safe():
    from fantasy_agent.plan_checks import check_blender_plan

    plan = _plan().blender_plan
    degraded = plan.model_copy(
        update={
            "scene_units": "meters",
            "jobs": [
                job.model_copy(
                    update={"export_path": "elsewhere/mesh.fbx", "collision_name": None}
                )
                for job in plan.jobs
            ],
        }
    )

    problems = check_blender_plan(degraded)

    assert any("generated/assets" in problem for problem in problems)
    assert any("collision" in problem for problem in problems)
    assert any("centimeters" in problem for problem in problems)


def test_the_plan_checks_reject_a_path_that_merely_starts_with_the_prefix():
    """``generated/assets-evil`` is not ``generated/assets``.

    Both path checks mirror the bridges' ``required_prefix`` rule, which
    compares path *segments*. ``startswith`` would wave this through and the
    Blender or ComfyUI bridge would then refuse the export -- a check looser
    than the thing it claims to mirror, which is the failure mode that makes a
    gate decorative. Both call sites are pinned so reverting either one alone
    is visible.
    """

    from fantasy_agent.plan_checks import check_blender_plan, check_comfyui_plan

    plan = _plan()
    blender = plan.blender_plan.model_copy(
        update={
            "jobs": [
                job.model_copy(update={"export_path": "generated/assets-evil/mesh.fbx"})
                for job in plan.blender_plan.jobs
            ]
        }
    )
    comfyui = plan.comfyui_plan.model_copy(
        update={
            "jobs": [
                job.model_copy(update={"output_path": "generated/comfyui-evil/ref.png"})
                for job in plan.comfyui_plan.jobs
            ]
        }
    )

    assert check_blender_plan(blender), "a path that only looks confined passed"
    assert check_comfyui_plan(comfyui), "a path that only looks confined passed"


def test_the_comfyui_plan_check_passes_a_generated_plan():
    from fantasy_agent.plan_checks import check_comfyui_plan

    assert check_comfyui_plan(_plan().comfyui_plan) == []


def test_the_comfyui_plan_check_fails_a_prompt_with_no_gameplay_constraint():
    """The exact failure the stage exists to prevent, as an assertion.

    A reference with no gameplay constraint is decoration; the plan either
    filled the field in or it did not.
    """

    from fantasy_agent.plan_checks import check_comfyui_plan

    plan = _plan().comfyui_plan
    degraded = plan.model_copy(
        update={
            "jobs": [job.model_copy(update={"gameplay_constraint": "  "}) for job in plan.jobs]
        }
    )

    problems = check_comfyui_plan(degraded)

    assert problems, "a plan whose every prompt lost its gameplay constraint passed"
    assert all("gameplay constraint" in problem for problem in problems)


# ── the checks as tools ─────────────────────────────────────────────────────


def test_the_plan_checks_are_read_only_tools_the_registry_can_resolve():
    """Named by the pipeline table, so an unresolvable name must be impossible.

    Also pins the tier: an exit check is run with no grant, so a name that
    resolved to a writing or launching tool would be a second action disguised
    as a verification.
    """

    from fantasy_agent.tool_registry import READ_ONLY

    registry = combined_registry()
    for name in ("verify_gameplay_spec", "verify_blender_plan", "verify_comfyui_plan"):
        spec = registry.get(name)
        assert spec is not None, f"{name} is not registered"
        assert spec.permission == READ_ONLY, name


def test_a_plan_check_tool_fails_when_the_run_produced_no_such_plan(tmp_path: Path):
    """The registry refuses first, and a refusal is a failed check.

    ``verify_gameplay_spec`` is filled from the artifact store, so a run whose
    planning stage never produced a spec gets "needs a gameplay_spec" rather
    than a check over nothing.
    """

    outcome = _run_checks(tmp_path, ("verify_gameplay_spec",))

    assert outcome.status == FAILED
    assert "gameplay_spec" in outcome.detail


def test_a_plan_check_tool_reports_the_problems_it_found(tmp_path: Path):
    """The tool result has to carry the reasons, not just a status.

    ``_run_exit_checks`` copies ``check.content`` into the stage detail, which
    is what an operator reads to decide what to rework.
    """

    registry = combined_registry(tmp_path)
    spec = _plan().gameplay_spec.model_copy(update={"win_state": ""})
    registry.remember_plan({"summary": {"gameplay_spec": spec.model_dump(mode="json")}})
    orchestrator = Orchestrator(
        session_id="checks", workspace_root=tmp_path, registry=registry
    )

    outcome = StageOutcome("gameplay_orchestration", DONE)
    stage = ProductionPipelineStage(
        id="gameplay_orchestration",
        order=1,
        title="Gameplay orchestration",
        purpose="plan the loop",
        owner_agent="director-agent",
        inputs=["PromptRequest"],
        outputs=["GameplaySpec"],
        exit_checks=["verify_gameplay_spec"],
    )
    orchestrator._run_exit_checks(stage, outcome)

    assert outcome.status == FAILED
    assert "win_state" in outcome.detail


def test_the_godot_check_tool_accepts_an_explicit_path(tmp_path: Path):
    """Direct callers still name their project; only the exit check does not.

    Without this the plan-derived path would be the *only* way in, and a caller
    validating one project out of several would have no way to say which.
    """

    plan = _plan()
    bridge = GodotMCPBridge(tmp_path)
    bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(plan=plan.godot_plan, write_files=True)
    )

    result = bridge.validate_godot_project(
        GodotMCPValidateProjectRequest(
            project_file=f"generated/godot/{_slug_of(plan.godot_plan.project_name)}/project.godot"
        )
    )

    assert result.status == "executed"
    assert result.validation_report is not None
    assert result.validation_report.issues == []


def test_the_godot_check_tool_says_so_when_it_has_neither_a_path_nor_a_plan(tmp_path: Path):
    """Neither input is a pass. Silence would be the vacuous gate again."""

    result = GodotMCPBridge(tmp_path).validate_godot_project(GodotMCPValidateProjectRequest())

    assert result.status == "failed"
    assert result.validation_report is not None
    assert any("godot_plan" in issue for issue in result.validation_report.issues)
