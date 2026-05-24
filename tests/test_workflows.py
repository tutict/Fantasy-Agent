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
    assert "average_session_minutes" in plan.qa_plan.metrics
