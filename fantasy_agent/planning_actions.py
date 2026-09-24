"""One planning action for every workbench tool and the agent registry.

The workbench, the REST plan routes, and ``default_registry`` used to call
the workflows themselves. Slice tools then called ``prepare_*`` a second
time, so engine versions could drift from the director plan. This module
runs the director once and projects the field the tool asked for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fantasy_agent.contracts import (
    DirectorBuildPlan,
    DirectorTaskBreakdown,
    IdeaDiscoveryRequest,
    IdeaSeed,
    PromptRequest,
)
from fantasy_agent.idea_discovery import extract_idea_seed, prompt_request_from_seed
from fantasy_agent.workflows import run_director_workflow

# Order is the workbench error string. Do not sort it.
PLANNING_TOOL_NAMES: tuple[str, ...] = (
    "extract_idea_seed",
    "decompose_production_tasks",
    "generate_game_production_plan",
    "render_gdd",
    "prepare_production_pipeline",
    "prepare_unreal_plan",
    "prepare_godot_plan",
    "prepare_blender_plan",
    "prepare_comfyui_plan",
    "prepare_creative_review_plan",
    "prepare_qa_plan",
)

# Offered to the model. The other names are workbench projections of a plan
# the model can already ask for in full, and listing them would widen the
# tool list without adding a capability.
MODEL_PLANNING_TOOLS: frozenset[str] = frozenset(
    {
        "extract_idea_seed",
        "generate_game_production_plan",
        "decompose_production_tasks",
        "render_gdd",
    }
)

_KINDS: dict[str, str] = {
    "extract_idea_seed": "idea_seed",
    "decompose_production_tasks": "director_task_breakdown",
    "generate_game_production_plan": "director_build_plan",
    "render_gdd": "gdd_document",
    "prepare_production_pipeline": "production_pipeline",
    "prepare_unreal_plan": "unreal_project_plan",
    "prepare_godot_plan": "godot_project_plan",
    "prepare_blender_plan": "blender_asset_plan",
    "prepare_comfyui_plan": "comfyui_visual_plan",
    "prepare_creative_review_plan": "creative_review_report",
    "prepare_qa_plan": "qa_plan",
}


class UnknownPlanningTool(LookupError):
    """The tool name is not one of ``PLANNING_TOOL_NAMES``."""

    def __init__(self, name: str) -> None:
        self.name = name
        available = ", ".join(PLANNING_TOOL_NAMES)
        super().__init__(
            f"Unknown Studio planning tool '{name}'. Available tools: {available}."
        )


@dataclass(frozen=True)
class PlanningAction:
    """Domain result of one planning tool.

    This is not the workbench envelope. Callers that speak HTTP or the agent
    registry project these objects into the shape they already return.
    """

    name: str
    message: str
    kind: str
    seed: IdeaSeed | None = None
    prompt_request: PromptRequest | None = None
    plan: DirectorBuildPlan | None = None
    task_breakdown: DirectorTaskBreakdown | None = None

    def require_plan(self) -> DirectorBuildPlan:
        if self.plan is None:
            raise RuntimeError(f"{self.name} did not produce a plan")
        return self.plan

    def require_breakdown(self) -> DirectorTaskBreakdown:
        if self.task_breakdown is None:
            raise RuntimeError(f"{self.name} did not produce a task breakdown")
        return self.task_breakdown


def run_planning_action(
    name: str,
    arguments: dict[str, Any],
    *,
    use_llm: bool | None = None,
) -> PlanningAction:
    """Run one named planning tool.

    ``use_llm=None`` keeps ``run_director_workflow`` on its env-flag default
    so library and test calls stay deterministic. Studio and the agent
    registry pass ``llm_enabled()`` explicitly.
    """

    if name not in _KINDS:
        raise UnknownPlanningTool(name)
    if name == "extract_idea_seed":
        request = IdeaDiscoveryRequest.model_validate(arguments)
        seed = extract_idea_seed(request)
        return PlanningAction(
            name=name,
            message=f"IdeaSeed: core action '{seed.core_action}'.",
            kind=_KINDS[name],
            seed=seed,
            prompt_request=prompt_request_from_seed(seed, request),
        )

    plan = run_director_workflow(PromptRequest.model_validate(arguments), use_llm=use_llm)
    breakdown = plan.task_breakdown
    if name == "decompose_production_tasks" and breakdown is None:
        raise RuntimeError("director workflow did not produce a task breakdown")
    return PlanningAction(
        name=name,
        message=_model_message(name, plan, breakdown),
        kind=_KINDS[name],
        plan=plan,
        task_breakdown=breakdown,
    )


def registry_payload(action: PlanningAction) -> dict[str, Any]:
    """The historical ``data`` object the four model-visible tools return.

    ``generate_game_production_plan`` keeps the whole plan under ``summary``.
    ``remember_plan`` reads engine sub-plans and the gameplay spec from there.
    """

    if action.name == "extract_idea_seed":
        if action.seed is None:
            raise RuntimeError("extract_idea_seed did not produce a seed")
        return {"idea_seed": action.seed.model_dump(mode="json")}
    if action.name == "generate_game_production_plan":
        return {"summary": action.require_plan().model_dump(mode="json")}
    if action.name == "decompose_production_tasks":
        return {"task_breakdown": action.require_breakdown().model_dump(mode="json")}
    if action.name == "render_gdd":
        return {"gdd": action.require_plan().gdd.model_dump(mode="json")}
    raise UnknownPlanningTool(action.name)


def _model_message(
    name: str,
    plan: DirectorBuildPlan,
    breakdown: DirectorTaskBreakdown | None,
) -> str:
    """Model-visible sentences. The four registry tools keep their old text."""

    spec = plan.gameplay_spec
    if name == "generate_game_production_plan":
        return (
            f"Production plan for '{spec.title}': {len(spec.core_loop)} loop steps, "
            f"{len(spec.level_beats)} level beats, {len(spec.systems)} systems. "
            f"Win: {spec.win_state}"
        )
    if name == "decompose_production_tasks":
        if breakdown is None:
            raise RuntimeError("director workflow did not produce a task breakdown")
        return (
            f"{len(breakdown.tasks)} production tasks; "
            f"recommended next: {breakdown.recommended_next_task}."
        )
    if name == "render_gdd":
        return f"GDD rendered for '{spec.title}'."
    return f"Prepared {name} for '{spec.title}'."
