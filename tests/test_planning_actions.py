"""Planning actions are the only way a tool name becomes a plan."""

from __future__ import annotations

from pathlib import Path

from fantasy_agent.api_settings import LLMApiSettings, save_settings
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.planning_actions import (
    MODEL_PLANNING_TOOLS,
    PLANNING_TOOL_NAMES,
    UnknownPlanningTool,
    run_planning_action,
)
from fantasy_agent.tool_registry import ToolRegistry, default_registry
from fantasy_agent.workflows import run_director_workflow

PROMPT = "rooftop parkour chase with wall-runs, vaults, and checkpoints"


def test_every_named_tool_returns_the_field_it_owns():
    args = PromptRequest(
        prompt=PROMPT, target_minutes=10, engine_version="Godot 4.6"
    ).model_dump(mode="json")
    seed = run_planning_action(
        "extract_idea_seed",
        {"raw_idea": "a cat burglar on the roofs"},
        use_llm=False,
    )
    assert seed.seed is not None
    assert seed.prompt_request is not None
    assert seed.kind == "idea_seed"
    assert seed.message.startswith("IdeaSeed: core action '")

    expected_kinds = {
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
    assert set(expected_kinds) | {"extract_idea_seed"} == set(PLANNING_TOOL_NAMES)
    for name, kind in expected_kinds.items():
        action = run_planning_action(name, args, use_llm=False)
        assert action.kind == kind
        assert action.plan is not None
        if name == "decompose_production_tasks":
            assert action.task_breakdown is not None


def test_slice_tools_match_the_director_plan_instead_of_repreparing():
    godot_request = PromptRequest(
        prompt=PROMPT, target_minutes=10, engine_version="Godot 4.6"
    )
    direct = run_director_workflow(godot_request, use_llm=False)
    args = godot_request.model_dump(mode="json")
    godot = run_planning_action("prepare_godot_plan", args, use_llm=False)
    unreal = run_planning_action("prepare_unreal_plan", args, use_llm=False)
    tasks = run_planning_action("decompose_production_tasks", args, use_llm=False)
    assert godot.require_plan().godot_plan == direct.godot_plan
    assert unreal.require_plan().unreal_plan == direct.unreal_plan
    assert godot.require_plan().godot_plan.engine_version == "Godot 4.6"
    assert unreal.require_plan().unreal_plan.engine_version == "UE5"
    assert tasks.require_breakdown() == direct.task_breakdown

    unreal_request = PromptRequest(prompt=PROMPT, target_minutes=10, engine_version="UE5.4")
    unreal_direct = run_director_workflow(unreal_request, use_llm=False)
    unreal_args = unreal_request.model_dump(mode="json")
    assert (
        run_planning_action("prepare_godot_plan", unreal_args, use_llm=False)
        .require_plan()
        .godot_plan.engine_version
        == unreal_direct.godot_plan.engine_version
        == "Godot 4"
    )
    assert (
        run_planning_action("prepare_unreal_plan", unreal_args, use_llm=False)
        .require_plan()
        .unreal_plan.engine_version
        == "UE5.4"
    )


def test_unknown_planning_tool_names_the_real_list():
    try:
        run_planning_action("does_not_exist", {"prompt": PROMPT})
    except UnknownPlanningTool as exc:
        assert "does_not_exist" in str(exc)
        assert "prepare_qa_plan" in str(exc)
    else:
        raise AssertionError("unknown tool was accepted")


def test_registry_keeps_the_four_model_payloads_and_hides_slices(monkeypatch):
    monkeypatch.setattr("fantasy_agent.api_settings.llm_enabled", lambda: False)
    registry = default_registry()
    names = set(registry.names())
    assert MODEL_PLANNING_TOOLS <= names
    assert "prepare_unreal_plan" not in names
    assert "prepare_godot_plan" not in names

    plan = registry.call("generate_game_production_plan", {"prompt": PROMPT})
    assert plan.status == "ok"
    assert plan.content.startswith("Production plan for '")
    assert set(plan.data) == {"summary"}
    registry.remember_plan(plan.data)
    for key in (
        "godot_plan",
        "unreal_plan",
        "blender_plan",
        "comfyui_plan",
        "gameplay_spec",
        "production_spec_bundle",
    ):
        assert registry.artifacts[key], key

    tasks = registry.call("decompose_production_tasks", {"prompt": PROMPT})
    assert tasks.content.endswith(".")
    assert "production tasks; recommended next:" in tasks.content
    assert set(tasks.data) == {"task_breakdown"}

    gdd = registry.call("render_gdd", {"prompt": PROMPT})
    assert gdd.content.startswith("GDD rendered for '")
    assert set(gdd.data) == {"gdd"}

    seed = registry.call("extract_idea_seed", {"raw_idea": "a cat burglar on the roofs"})
    assert seed.content.startswith("IdeaSeed: core action '")
    assert set(seed.data) == {"idea_seed"}


def test_registry_forwards_the_saved_llm_switch(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FANTASY_AGENT_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("FANTASY_AGENT_USE_LLM", raising=False)
    save_settings(LLMApiSettings(enabled=True))
    seen: dict[str, object] = {}

    def spy(request, *, use_llm=None):
        seen["use_llm"] = use_llm
        return run_director_workflow(request, use_llm=False)

    monkeypatch.setattr("fantasy_agent.planning_actions.run_director_workflow", spy)
    outcome = default_registry().call("render_gdd", {"prompt": PROMPT})
    assert seen["use_llm"] is True
    assert outcome.status == "ok"
    assert set(outcome.data) == {"gdd"}


def test_registry_stays_deterministic_without_settings(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FANTASY_AGENT_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("FANTASY_AGENT_USE_LLM", raising=False)
    seen: dict[str, object] = {}

    def spy(request, *, use_llm=None):
        seen["use_llm"] = use_llm
        return run_director_workflow(request, use_llm=False)

    monkeypatch.setattr("fantasy_agent.planning_actions.run_director_workflow", spy)
    default_registry().call("render_gdd", {"prompt": PROMPT})
    assert seen["use_llm"] is False


def test_remember_plan_is_not_confused_by_an_empty_registry():
    """A fresh registry has no artifacts until a plan tool runs."""

    assert ToolRegistry().artifacts == {}
