from fantasy_agent.contracts import PromptRequest
from fantasy_agent.workflows import run_director_workflow


def test_director_workflow_creates_playable_slice_plan():
    request = PromptRequest(
        prompt="a stealth courier escapes a haunted train station",
        target_minutes=10,
    )

    plan = run_director_workflow(request)

    assert plan.gameplay_spec.target_session_minutes == 10
    assert plan.gameplay_spec.i18n is not None
    assert plan.gameplay_spec.i18n.output_locales == ["en", "zh-CN"]
    assert len(plan.gameplay_spec.core_loop) >= 3
    assert len(plan.gameplay_spec.systems) >= 3
    assert plan.gdd.markdown.startswith("# ")
    assert "zh-CN" in plan.gdd.markdown_by_locale
    assert "核心循环" in plan.gdd.markdown_by_locale["zh-CN"]
    assert "M_Prototype_Greybox" in plan.unreal_plan.maps
    assert plan.blender_plan.jobs
    assert plan.comfyui_plan.jobs
    assert plan.comfyui_plan.jobs[0].workflow_template.startswith("templates/comfyui/")
    assert "average_session_minutes" in plan.qa_plan.metrics
    assert plan.task_breakdown is not None
    assert plan.task_breakdown.recommended_next_task == "gameplay_spec_review"
    assert any(task.requires_confirmation for task in plan.task_breakdown.tasks)
    assert any(task.id == "unreal_asset_ingest" and task.status == "blocked" for task in plan.task_breakdown.tasks)


def test_director_workflow_specializes_parkour_prompts():
    request = PromptRequest(
        prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
        target_minutes=10,
    )

    plan = run_director_workflow(request)

    assert plan.gameplay_spec.core_verbs == ["sprint", "vault", "wall-run", "slide"]
    assert "Momentum Chain" in {system.name for system in plan.gameplay_spec.systems}
    assert "Wall-run panel set" in plan.gameplay_spec.asset_needs
    assert any("checkpoint" in beat.gameplay_focus.lower() for beat in plan.gameplay_spec.level_beats)
