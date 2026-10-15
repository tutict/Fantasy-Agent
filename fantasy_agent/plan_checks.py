"""Exit checks: the machine-settable half of a stage's ``quality_gates``.

``ProductionPipelineStage.quality_gates`` is prose -- "Core loop has at least
three testable decisions", "Every prompt includes a gameplay constraint". A
human reads those. ``exit_checks`` names read-only tools instead, and the
orchestrator runs them itself once a stage's agent has finished; a check that
reports a problem makes the stage ``failed`` rather than ``done``.

This module holds the checks for the three stages whose output is a *plan*
rather than a file on disk. Each one is a pure function over the plan the run
already produced, and each assertion is the machine form of one quality gate
that was previously only prose:

- ``verify_gameplay_spec``  <- ``gameplay_orchestration``
- ``verify_blender_plan``   <- ``blender_modeling``
- ``verify_comfyui_plan``   <- ``comfyui_visual_production``

What these deliberately do **not** do, and why it matters:

- **No network.** ``probe_comfyui_capabilities`` is the one read-only tool that
  takes no arguments, and it is tempting for exactly that reason. It also fails
  when ComfyUI is not running, which is the degraded state AGENTS.md promises
  to support -- so using it as a check would turn "the reference worker is not
  installed" into a failed production stage.
- **No filesystem.** A check that reads ``generated/`` judges the workspace by
  whatever an earlier run left there. The plan in the artifact store is what
  *this* run produced.
- **No re-derivation.** Nothing here calls ``prepare_*`` a second time; the
  plan is read out of the registry's store, so the check and the stage cannot
  disagree about what was planned.

Every problem is returned as a sentence rather than raised, because the caller
turns the list into one tool result the orchestrator reads as pass/fail.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fantasy_agent.contracts import (
    BlenderAssetPlan,
    BlenderPlanCheckRequest,
    ComfyUIPlanCheckRequest,
    ComfyUIVisualPlan,
    GameplaySpec,
    GameplaySpecCheckRequest,
)

#: How many distinct player decisions a core loop must name before it counts as
#: "at least three testable decisions". The same number the stage's prose gate
#: uses, spelled once so the two cannot drift apart.
MIN_TESTABLE_DECISIONS = 3


def _under(path: str, prefix: str) -> bool:
    """``resolve_workspace_path``'s prefix rule, without the filesystem.

    The Blender and ComfyUI bridges confine a job's paths with
    ``required_prefix``; this is the same comparison over the same normalised
    parts, so a check and the bridge it mirrors cannot disagree about what
    "confined" means. ``startswith`` would accept ``generated/assets-evil``
    and a ``..``-leading path, both of which the bridge rejects -- and a check
    looser than the thing it claims to mirror is a check that passes what
    execution will refuse.
    """

    parts = Path(path.replace("\\", "/")).parts
    wanted = Path(prefix).parts
    return parts[: len(wanted)] == wanted


def check_gameplay_spec(spec: GameplaySpec) -> list[str]:
    """Everything about a ``GameplaySpec`` a machine can settle.

    The gates this mirrors, in order: a core loop with at least three
    *testable* decisions, a first minute that teaches the loop, and win/failure
    states that can be validated without final art. The last one is four
    assertions rather than one -- ``win_state``, ``failure_states``,
    ``level_beats`` and each beat's ``success_condition`` -- because a route
    with no measurable end states is the same gap wearing a different hat.

    "Testable" is the part the model constraints cannot express: three loop
    steps whose ``player_decision`` is the same sentence is one decision written
    three times, and pydantic is perfectly happy with it. So the count is over
    *distinct* decisions, and an empty one is a missing decision rather than a
    short one.
    """

    problems: list[str] = []

    decisions = [step.player_decision.strip() for step in spec.core_loop]
    if any(not decision for decision in decisions):
        problems.append("a core loop step names no player decision to test")
    distinct = {decision.casefold() for decision in decisions if decision}
    if len(distinct) < MIN_TESTABLE_DECISIONS:
        problems.append(
            f"core loop has {len(distinct)} distinct player decision(s); "
            f"{MIN_TESTABLE_DECISIONS} are needed for the loop to be testable"
        )

    if not spec.progression.first_minute.strip():
        problems.append("progression.first_minute is empty, so nothing teaches the loop")

    if not spec.win_state.strip():
        problems.append("win_state is empty, so no run can be measured as a win")
    if not spec.failure_states:
        problems.append("failure_states is empty, so no run can be measured as a failure")
    if not spec.level_beats:
        problems.append("level_beats is empty, so there is no route to validate")
    else:
        unnamed = [beat.name for beat in spec.level_beats if not beat.success_condition.strip()]
        if unnamed:
            problems.append(
                "level beats with no success condition: " + ", ".join(repr(n) for n in unnamed)
            )

    return problems


def check_blender_plan(plan: BlenderAssetPlan) -> list[str]:
    """Everything about a ``BlenderAssetPlan`` a machine can settle.

    Mirrors "Assets use UE centimeter scale", "Each gameplay mesh has a UCX
    collision object", and the export-path confinement the Blender bridge
    already enforces on execution -- checked here at the node that planned
    them, so a bad path is a planning failure rather than a launch failure.

    ``python_entrypoint`` is deliberately *not* checked: it names the repo's own
    runner (``fantasy_agent/blender_procedural_job.py``), not a generated
    artifact, so a "must be under generated/" rule would fail every real plan.
    The generated side of that handoff is ``handoff_artifacts``.
    """

    problems: list[str] = []

    if plan.scene_units != "centimeters":
        problems.append(f"scene_units is {plan.scene_units!r}; Unreal ingest expects centimeters")
    if not plan.jobs:
        problems.append("no mesh jobs planned, so this stage produced nothing to model")

    for job in plan.jobs:
        if not _under(job.export_path, "generated/assets"):
            problems.append(f"{job.asset_name}: export path is not under generated/assets")
        # The UCX *object name*, not the hint: the hint is prose that is always
        # filled in, and a check that accepts prose would pass a mesh with no
        # collision object at all.
        if not (job.collision_name or "").strip():
            problems.append(f"{job.asset_name}: no UCX collision object name")

    return problems


def check_comfyui_plan(plan: ComfyUIVisualPlan) -> list[str]:
    """Everything about a ``ComfyUIVisualPlan`` a machine can settle.

    Mirrors "Every prompt includes a gameplay constraint" and the output-path
    confinement the ComfyUI bridge enforces on execution. The constraint field
    is the one that keeps a reference from being decoration: a pretty image
    with no gameplay constraint is the failure mode this stage exists to
    prevent, and it is a string the planner either filled in or did not.
    """

    problems: list[str] = []

    if not plan.jobs:
        problems.append("no reference jobs planned, so this stage produced nothing to review")

    templates = set(plan.workflow_templates)
    for job in plan.jobs:
        if not job.gameplay_constraint.strip():
            problems.append(f"{job.job_id}: prompt carries no gameplay constraint")
        if not _under(job.output_path, "generated/comfyui"):
            problems.append(f"{job.job_id}: output path is not under generated/comfyui")
        # Unconditional on purpose. Guarding this with ``if templates`` would
        # make a plan that declares no templates pass every job's template --
        # a check that cannot find its input must fail, not pass. The planner
        # always fills three, so this only bites a hand-built plan, which is
        # exactly the plan that has not been thought about.
        if job.workflow_template not in templates:
            problems.append(
                f"{job.job_id}: workflow template {job.workflow_template!r} is not one "
                "this plan declares"
            )

    return problems


# ── registry wiring ─────────────────────────────────────────────────────────

_CHECK_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

_CHECKS: dict[str, tuple[str, str, Any]] = {
    "verify_gameplay_spec": (
        "gameplay_spec",
        (
            "Check the gameplay spec this run produced for the things a machine can "
            "settle: at least three distinct player decisions in the core loop, a "
            "first minute that teaches the loop, and win and failure states that "
            "can be measured. Read-only; nothing is written or launched."
        ),
        GameplaySpecCheckRequest,
    ),
    "verify_blender_plan": (
        "blender_plan",
        (
            "Check the Blender asset plan this run produced: centimetre scene units, "
            "at least one mesh job, a UCX collision object name per job, and export "
            "paths confined to generated/assets. Read-only."
        ),
        BlenderPlanCheckRequest,
    ),
    "verify_comfyui_plan": (
        "comfyui_plan",
        (
            "Check the ComfyUI visual plan this run produced: at least one reference "
            "job, a gameplay constraint on every prompt, declared workflow templates, "
            "and output paths confined to generated/comfyui. Read-only; the endpoint "
            "is not probed."
        ),
        ComfyUIPlanCheckRequest,
    ),
}


def register_check_tools(registry: Any) -> None:
    """Add the three exit-check tools to ``registry``.

    Each is registered with the ``plan_key`` of the plan it checks, which is
    what makes a no-argument call work: the registry fills ``plan`` from this
    run's artifact store and refuses the call when the run never produced one.
    A check that cannot find its input must fail, not pass -- "this run has no
    gameplay spec" is exactly the state the ``gameplay_orchestration`` stage
    would otherwise report as verified.
    """

    from fantasy_agent.tool_registry import READ_ONLY, ToolSpec

    for name, (plan_key, description, request_model) in _CHECKS.items():
        registry.register(
            ToolSpec(
                name=name,
                description=description,
                input_schema=_CHECK_SCHEMA,
                handler=_handler(name, request_model),
                permission=READ_ONLY,
                plan_key=plan_key,
            )
        )


def _handler(name: str, request_model: Any):
    def handler(arguments: dict[str, Any]) -> Any:
        from fantasy_agent.tool_registry import ToolOutcome

        try:
            request = request_model.model_validate(arguments or {})
        except Exception as exc:  # noqa: BLE001 - a bad artifact is a failed check
            return ToolOutcome(name, "error", f"{type(exc).__name__}: {exc}")
        if request.plan is None:
            # Unreachable through the registry, which refuses first. Reachable
            # by a direct call, and "no plan" is a failed check rather than a
            # pass -- see register_check_tools.
            return ToolOutcome(name, "error", f"{name} was given no plan to check")

        problems = _run_check(name, request.plan)
        if problems:
            return ToolOutcome(
                name,
                "error",
                f"{name} found {len(problems)} problem(s): " + "; ".join(problems),
                {"problems": problems},
            )
        return {
            "message": f"{name}: no problems found",
            "data": {"problems": []},
        }

    return handler


def _run_check(name: str, plan: Any) -> list[str]:
    if name == "verify_gameplay_spec":
        return check_gameplay_spec(plan)
    if name == "verify_blender_plan":
        return check_blender_plan(plan)
    return check_comfyui_plan(plan)
