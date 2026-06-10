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
    assert {
        "/",
        "/web-console",
        "/workbench",
        "/health",
        "/api/plan",
        "/api/mcp/status",
        "/api/manual-correction/targets",
        "/api/manual-correction/open",
        "/mcp",
    } <= paths
    assert module.STATIC_DIR.joinpath("index.html").exists()
    assert module.WEB_CONSOLE_STATIC_DIR.joinpath("index.html").exists()
    assert module.WORKBENCH_PATH.exists()
    assert module.mcp_info()["endpoint"] == "/mcp"
    status = module.mcp_status()
    assert status["engine_kind"] == "unreal"
    assert status["required_total"] >= 4
    assert 0 <= status["required_ready"] <= status["required_total"]
    services = {service["id"]: service for service in status["services"]}
    service_ids = set(services)
    assert {"studio-mcp", "comfyui", "blender", "unreal", "godot", "github"} <= service_ids
    for service in services.values():
        assert service["detail_key"].startswith("mcp")
        assert service["next_action_key"].startswith("mcp")
        assert isinstance(service["detail_args"], dict)
        assert isinstance(service["next_action_args"], dict)
    assert services["unreal"]["required"] is True
    assert services["godot"]["required"] is False
    godot_status = module.mcp_status(engine="Godot 4")
    godot_services = {service["id"]: service for service in godot_status["services"]}
    assert godot_status["engine_kind"] == "godot"
    assert godot_services["unreal"]["required"] is False
    assert godot_services["godot"]["required"] is True
    correction_targets = module.correction_targets(engine="Godot 4")
    assert correction_targets["engine_kind"] == "godot"
    assert "godot" in {target["id"] for target in correction_targets["targets"]}
    blocked = module.correction_open(
        module.ManualCorrectionOpenRequest(target_id="godot", confirmed_side_effects=False)
    )
    assert blocked["status"] == "blocked"


def test_studio_detects_downloaded_godot_install(monkeypatch, tmp_path):
    module = _load_studio_app()
    older_godot = tmp_path / "Godot_v4.6.1-stable_win64" / "Godot_v4.6.1-stable_win64.exe"
    godot = tmp_path / "Godot_v4.6.3-stable_win64" / "Godot_v4.6.3-stable_win64_console.exe"
    older_godot.parent.mkdir(parents=True)
    godot.parent.mkdir(parents=True)
    older_godot.write_text("", encoding="utf-8")
    godot.write_text("", encoding="utf-8")

    monkeypatch.delenv("GODOT_EXECUTABLE", raising=False)
    monkeypatch.setattr(module.shutil, "which", lambda _command: None)
    monkeypatch.setattr(
        module,
        "_candidate_paths",
        lambda patterns: [str(older_godot), str(godot)]
        if "C:/Users/*/Downloads/Godot*/Godot*.exe" in patterns
        else [],
    )

    status = module.mcp_status(engine="Godot 4.6")
    services = {service["id"]: service for service in status["services"]}

    assert services["godot"]["status"] == "ready"
    assert services["godot"]["target"] == str(godot)


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
    assert 'id="mcp-refresh"' in html
    assert 'id="mcp-status-grid"' in html
    assert "/api/mcp/status" in html
    assert "mcpStatusTitle" in html
    assert "mcpDetailExecutableMissing" in html
    assert "未在 PATH、已配置环境变量或常见安装目录中找到可执行文件。" in html
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


def test_execute_confirmation_gate_runs_no_job():
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    req = module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=False)
    result = module.execute_demo(req)

    assert result["status"] == "confirmation_required"
    assert result["engine"] == "godot"
    assert result["planned_side_effects"]
    # No job was registered.
    assert "job_id" not in result


def test_execute_starts_job_and_polls(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult, StageResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )

    # Stub the executor so no real engine runs.
    def fake_godot(plan_arg, **kwargs):
        if not kwargs.get("confirmed"):
            return ExecutionResult(
                status="confirmation_required", session_id="x", planned_side_effects=["write project"]
            )
        return ExecutionResult(
            status="done",
            session_id="x",
            project_dir="generated/godot/sessions/x/demo",
            stages=[StageResult("create", "done"), StageResult("import", "done")],
        )

    monkeypatch.setattr(module, "_build_execution_result", lambda req, *, confirmed: fake_godot(req.plan, confirmed=confirmed))

    started = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=True))
    assert started["status"] == "running"
    job_id = started["job_id"]

    # Drain the single-worker pool so the background job completes.
    module._EXECUTE_POOL.shutdown(wait=True)

    status = module.execute_status(job_id)
    assert status["status"] == "done"
    assert status["result"]["project_dir"].endswith("demo")
    assert [s["name"] for s in status["result"]["stages"]] == ["create", "import"]


def test_execute_status_unknown_job():
    module = _load_studio_app()
    assert module.execute_status("nope")["status"] == "unknown"
