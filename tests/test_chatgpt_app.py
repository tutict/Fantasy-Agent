from fantasy_agent.chatgpt_app import WIDGET_URI, call_workbench_tool, tool_descriptors, widget_resource


def _request() -> dict[str, object]:
    return {
        "prompt": "a stealth courier escapes a haunted train station",
        "target_minutes": 10,
        "source_locale": "en",
        "output_locales": ["en", "zh-CN"],
    }


def test_chatgpt_tool_descriptors_are_read_only_and_widget_backed():
    tools = tool_descriptors()

    assert {tool["name"] for tool in tools} >= {
        "decompose_production_tasks",
        "generate_game_production_plan",
        "prepare_production_pipeline",
        "render_gdd",
        "prepare_unreal_plan",
        "prepare_blender_plan",
        "prepare_comfyui_plan",
        "prepare_qa_plan",
    }
    for tool in tools:
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["destructiveHint"] is False
        assert tool["_meta"]["openai/outputTemplate"] == WIDGET_URI
        assert tool["_meta"]["openai/widgetAccessible"] is True


def test_generate_game_production_plan_returns_structured_widget_payload():
    result = call_workbench_tool("generate_game_production_plan", _request())

    assert "isError" not in result
    assert result["structuredContent"]["kind"] == "director_build_plan"
    plan = result["structuredContent"]["plan"]
    assert plan["gameplay_spec"]["target_session_minutes"] == 10
    assert plan["task_breakdown"]["recommended_next_task"] == "gameplay_spec_review"
    assert plan["production_pipeline"]["next_stage"] == "comfyui_visual_production"
    assert result["structuredContent"]["production_pipeline"] == plan["production_pipeline"]
    assert plan["gdd"]["markdown_by_locale"]["zh-CN"]
    assert result["_meta"]["plan"] == plan
    assert result["_meta"]["productionPipeline"] == plan["production_pipeline"]
    assert result["_meta"]["activePanel"] == "overview"


def test_decompose_production_tasks_returns_task_board_payload():
    result = call_workbench_tool("decompose_production_tasks", _request())

    assert "isError" not in result
    assert result["structuredContent"]["kind"] == "director_task_breakdown"
    breakdown = result["structuredContent"]["task_breakdown"]
    assert breakdown["recommended_next_task"] == "gameplay_spec_review"
    assert any(task["requires_confirmation"] for task in breakdown["tasks"])
    assert result["_meta"]["activePanel"] == "tasks"


def test_prepare_production_pipeline_returns_pipeline_payload():
    result = call_workbench_tool("prepare_production_pipeline", _request())

    assert "isError" not in result
    assert result["structuredContent"]["kind"] == "production_pipeline"
    pipeline = result["structuredContent"]["production_pipeline"]
    assert [stage["id"] for stage in pipeline["stages"]] == [
        "gameplay_orchestration",
        "comfyui_visual_production",
        "blender_modeling",
        "asset_integration",
        "unreal_production",
        "optimization_testing",
    ]
    assert pipeline["next_stage"] == "comfyui_visual_production"
    assert result["_meta"]["productionPipeline"] == pipeline
    assert result["_meta"]["activePanel"] == "pipeline"


def test_focused_chatgpt_tools_return_subplans_without_side_effects():
    unreal = call_workbench_tool("prepare_unreal_plan", _request())
    blender = call_workbench_tool("prepare_blender_plan", _request())
    comfyui = call_workbench_tool("prepare_comfyui_plan", _request())
    qa = call_workbench_tool("prepare_qa_plan", _request())

    assert unreal["structuredContent"]["unreal_plan"]["maps"] == [
        "M_Prototype_Greybox",
        "M_Prototype_TestGym",
    ]
    assert blender["structuredContent"]["blender_plan"]["jobs"]
    assert comfyui["structuredContent"]["comfyui_plan"]["jobs"][0]["gameplay_constraint"]
    assert "average_session_minutes" in qa["structuredContent"]["qa_plan"]["metrics"]


def test_widget_resource_uses_mcp_app_mime_type():
    resource = widget_resource()

    assert resource["uri"] == WIDGET_URI
    assert resource["mimeType"] == "text/html;profile=mcp-app"
    assert resource["_meta"]["openai/widgetPrefersBorder"] is True

