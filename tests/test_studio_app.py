from __future__ import annotations

import importlib.util
from pathlib import Path

from fantasy_agent.contracts import PromptRequest


def _load_studio_app():
    module_path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_studio_serves_combined_desktop_panel():
    module = _load_studio_app()
    paths = {route.path for route in module.app.routes}

    assert module.health()["agent"] == "fantasy-agent-studio"
    assert {"/", "/web-console", "/workbench", "/health", "/api/plan", "/mcp"} <= paths
    assert module.STATIC_DIR.joinpath("index.html").exists()
    assert module.WEB_CONSOLE_STATIC_DIR.joinpath("index.html").exists()
    assert module.WORKBENCH_PATH.exists()
    assert module.mcp_info()["endpoint"] == "/mcp"


def test_studio_shell_includes_bilingual_ui_controls():
    module = _load_studio_app()
    html = module.STATIC_DIR.joinpath("index.html").read_text(encoding="utf-8")
    workbench_html = module.WORKBENCH_PATH.read_text(encoding="utf-8")

    assert 'data-locale="en"' in html
    assert 'data-locale="zh-CN"' in html
    assert "sidebar-resizer" in html
    assert 'id="sidebar-toggle"' in html
    assert 'data-target="console"' in html
    assert 'data-target="workbench"' in html
    assert html.index('data-target="workbench"') < html.index('data-target="console"')
    assert 'let activePanel = "workbench"' in html
    assert "Flow Console" in html
    assert "流程控制台" in html
    assert "Planning Workbench" in html
    assert "策划工作台" in html
    assert "fantasy-agent-studio-locale" in html
    assert "fantasy-agent-planning-handoff" in workbench_html


def test_studio_routes_plan_and_workbench_tools_through_one_server():
    module = _load_studio_app()
    request = PromptRequest(
        prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
        target_minutes=10,
    )

    plan = module.plan(request)
    assert plan.production_pipeline is not None
    assert plan.production_pipeline.next_stage == "comfyui_visual_production"

    tool = module._handle_rpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "prepare_production_pipeline",
                "arguments": request.model_dump(mode="json"),
            },
        }
    )
    assert tool is not None
    assert tool["result"]["structuredContent"]["kind"] == "production_pipeline"
