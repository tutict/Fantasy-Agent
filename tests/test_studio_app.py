from __future__ import annotations

import importlib.util
import threading
import time
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
    assert module.health()["mode"] == "standalone"
    assert {
        "/",
        "/web-console",
        "/workbench",
        "/health",
        "/api/plan",
        "/api/tasks",
        "/api/design",
        "/api/gdd",
        "/api/pipeline",
        "/api/idea-seed",
        "/api/qa",
        "/api/tool-contracts",
        "/api/unreal/plan",
        "/api/godot/plan",
        "/api/blender/plan",
        "/api/comfyui/plan",
        "/api/creative-review",
        "/api/tool-status",
        "/api/manual-correction/targets",
        "/api/manual-correction/open",
        "/api/tools/{tool_name}",
    } <= paths
    # The standalone workbench must not expose an inbound MCP endpoint.
    assert "/mcp" not in paths
    assert "/debug/tool/{tool_name}" not in paths
    assert module.STATIC_DIR.joinpath("index.html").exists()
    assert module.STATIC_DIR.joinpath("planning-workbench.html").exists()
    assert module.WEB_CONSOLE_STATIC_DIR.joinpath("index.html").exists()
    assert module.FRONTEND_DIST_DIR.name == "dist"
    assert module.FRONTEND_INDEX_PATH.name == "index.html"
    assert module.WORKBENCH_PATH.exists()
    status = module.mcp_status()
    assert status["engine_kind"] == "unreal"
    assert status["required_total"] >= 3
    assert 0 <= status["required_ready"] <= status["required_total"]
    services = {service["id"]: service for service in status["services"]}
    service_ids = set(services)
    assert {"comfyui", "blender", "unreal", "godot", "github"} <= service_ids
    assert "studio-mcp" not in service_ids
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
    frontend_source = module.REPO_ROOT.joinpath("apps/frontend/src/studio/StudioShell.tsx").read_text(encoding="utf-8")
    frontend_i18n = module.REPO_ROOT.joinpath("apps/frontend/src/shared/i18n.ts").read_text(encoding="utf-8")
    workbench_html = module.WORKBENCH_PATH.read_text(encoding="utf-8")

    assert 'data-locale="en"' in html or 'data-locale="en"' in frontend_source
    assert 'data-locale="zh-CN"' in html or 'data-locale="zh-CN"' in frontend_source
    assert "sidebar-resizer" in html or "sidebar-resizer" in frontend_source
    assert 'id="sidebar-toggle"' in html or 'id="sidebar-toggle"' in frontend_source
    assert 'data-target="console"' in html or 'data-target={key}' in frontend_source
    assert 'data-target="workbench"' in html or 'data-target={key}' in frontend_source
    assert 'id="mcp-refresh"' in html or 'id="mcp-refresh"' in frontend_source
    assert 'id="mcp-status-grid"' in html or 'id="mcp-status-grid"' in frontend_source
    assert "/api/tool-status" in html or "getMcpStatus" in frontend_source
    assert "mcpStatusTitle" in html or "mcpStatusTitle" in frontend_i18n
    assert 'activePanel, setActivePanel] = useState<PanelKey>("workbench")' in frontend_source
    assert "Flow Console" in html or "consoleFrameTitle" in frontend_i18n
    assert "\u6d41\u7a0b\u63a7\u5236\u53f0" in html or "\u6d41\u7a0b\u63a7\u5236\u53f0" in frontend_i18n
    assert "Planning Workbench" in html or "workbenchFrameTitle" in frontend_i18n
    assert "\u7b56\u5212\u5de5\u4f5c\u53f0" in html or "\u7b56\u5212\u5de5\u4f5c\u53f0" in frontend_i18n
    assert "fantasy-agent-studio-locale" in html or "fantasy-agent-studio-locale" in frontend_source
    assert "fantasy-agent-planning-handoff" in workbench_html


def test_studio_prefers_vite_frontend_dist_when_available(monkeypatch):
    module = _load_studio_app()
    frontend_index = module.STATIC_DIR / "index.html"
    monkeypatch.setattr(module, "FRONTEND_INDEX_PATH", frontend_index)

    assert Path(module.index().path) == frontend_index
    assert Path(module.web_console().path) == frontend_index


def test_studio_routes_plan_and_workbench_tools_through_one_server():
    module = _load_studio_app()
    request = PromptRequest(
        prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
        target_minutes=10,
    )

    plan = module.plan(request)
    assert plan.production_pipeline is not None
    assert plan.production_pipeline.next_stage == "comfyui_visual_production"

    tool = module._workbench_tool(
        "prepare_production_pipeline", request.model_dump(mode="json")
    )
    assert tool["structuredContent"]["kind"] == "production_pipeline"

    unknown = module._workbench_tool("does_not_exist", request.model_dump(mode="json"))
    assert unknown["isError"] is True


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

    monkeypatch.setattr(module, "_build_execution_result", lambda req, *, confirmed, **_kwargs: fake_godot(req.plan, confirmed=confirmed))

    started = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=True))
    assert started["status"] == "running"
    job_id = started["job_id"]

    # Drain the single-worker pool so the background job completes.
    module._EXECUTE_POOL.shutdown(wait=True)

    status = module.execute_status(job_id)
    assert status["status"] == "done"
    assert status["result"]["project_dir"].endswith("demo")
    assert [s["name"] for s in status["result"]["stages"]] == ["create", "import"]


def test_execute_returns_and_reuses_a_session_id(monkeypatch):
    """Node-level rework needs the session id back, or nothing can be resumed."""

    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    seen: list[str] = []

    def fake_execute(req, *, confirmed, session_id, **_kwargs):
        seen.append(session_id)
        if not confirmed:
            return ExecutionResult(
                status="confirmation_required",
                session_id=session_id,
                planned_side_effects=["write project"],
            )
        return ExecutionResult(status="done", session_id=session_id)

    monkeypatch.setattr(module, "_build_execution_result", fake_execute)

    preview = module.execute_demo(
        module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=False)
    )
    assert preview["session_id"], "the UI needs the session id to resume later"

    started = module.execute_demo(
        module.ExecuteDemoRequest(
            plan=plan,
            engine="Godot 4",
            confirmed=True,
            session_id="sess-42",
            resume_from="create",
        )
    )
    module._EXECUTE_POOL.shutdown(wait=True)

    assert started["session_id"] == "sess-42"
    assert seen[-1] == "sess-42"


def test_session_state_endpoint_reads_persisted_stages(monkeypatch, tmp_path):
    """The rework panel reads this to offer one node to re-run."""

    from fantasy_agent.pipeline_state import StageState, record_stage

    module = _load_studio_app()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    record_stage(
        "sess-1", StageState(name="blender", status="failed"), workspace_root=tmp_path
    )
    record_stage(
        "sess-1", StageState(name="create", status="done"), workspace_root=tmp_path
    )

    state = module.session_state("sess-1", engine="godot")
    assert state["found"]
    assert state["done"] == ["create"]
    assert state["failed"] == ["blender"]
    assert "import" in state["stage_order"]

    missing = module.session_state("nope", engine="godot")
    assert missing["found"] is False
    assert missing["stages"] == []


def test_execute_status_unknown_job():
    module = _load_studio_app()
    assert module.execute_status("nope")["status"] == "unknown"


def test_write_approval_manifest_api_writes_generated_yaml(monkeypatch, tmp_path):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    review = plan.creative_review
    first = review.items[0].asset_id
    second = review.items[1].asset_id
    req = module.ApprovalManifestRequest(
        review=review,
        decisions={first: "approved", second: "needs_revision"},
    )

    response = module.write_approval_manifest(req)

    assert response.status == "written"
    assert response.manifest_path == "generated/asset-approval-manifest.yaml"
    output = tmp_path / response.manifest_path
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "approved_asset_ids:" in text
    assert first in text
    assert second in response.manifest.revision_asset_ids


def test_asset_execute_confirmation_gate_runs_no_job():
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    req = module.AssetExecutionRequest(plan=plan, with_assets=True, with_visuals=True, confirmed=False)
    result = module.execute_assets(req)

    assert result["status"] == "confirmation_required"
    assert any("Blender" in effect for effect in result["planned_side_effects"])
    assert any("ComfyUI" in effect for effect in result["planned_side_effects"])
    assert "job_id" not in result


def test_asset_execute_starts_job_and_polls(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult, StageResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )

    def fake_assets(req, *, confirmed):
        if not confirmed:
            return ExecutionResult(
                status="confirmation_required", session_id="a", planned_side_effects=["run assets"]
            )
        return ExecutionResult(
            status="done",
            session_id="a",
            stages=[StageResult("comfyui", "done"), StageResult("blender", "done")],
        )

    monkeypatch.setattr(module, "_build_asset_execution_result", fake_assets)

    started = module.execute_assets(
        module.AssetExecutionRequest(plan=plan, with_assets=True, with_visuals=True, confirmed=True)
    )
    second = module.execute_assets(
        module.AssetExecutionRequest(plan=plan, with_assets=True, with_visuals=True, confirmed=True)
    )
    assert started["status"] == "running"
    assert second["status"] == "running"
    assert started["job_id"] != second["job_id"]
    job_id = started["job_id"]

    module._EXECUTE_POOL.shutdown(wait=True)

    status = module.asset_execute_status(job_id)
    assert status["status"] == "done"
    assert [s["name"] for s in status["result"]["stages"]] == ["comfyui", "blender"]


def test_execute_demo_job_ids_do_not_collide(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )

    def fake_execute(req, *, confirmed, **_kwargs):
        return ExecutionResult(status="done", session_id="x")

    monkeypatch.setattr(module, "_build_execution_result", fake_execute)
    first = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="godot", confirmed=True))
    second = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="godot", confirmed=True))

    assert first["job_id"] != second["job_id"]
    module._EXECUTE_POOL.shutdown(wait=True)


def test_asset_execute_status_unknown_job():
    module = _load_studio_app()
    assert module.asset_execute_status("nope")["status"] == "unknown"


def test_approval_manifest_api_returns_synchronized_bundle(monkeypatch, tmp_path):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes a haunted station")
    )
    assert plan.production_spec_bundle is not None
    item = plan.creative_review.items[0]
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    response = module.write_approval_manifest(
        module.ApprovalManifestRequest(
            review=plan.creative_review,
            decisions={item.asset_id: "approved"},
            production_spec_bundle=plan.production_spec_bundle,
        )
    )

    assert response.production_spec_bundle is not None
    synced = next(
        asset
        for asset in response.production_spec_bundle.resource_pipeline.assets
        if asset.asset_id == item.asset_id
    )
    assert synced.approval_status == "approved"
    assert synced.blocked_reason is None
    assert (tmp_path / "generated" / "specs" / "production-spec-bundle.yaml").exists()

def test_spec_bundle_preview_api_returns_validation_artifacts_and_traces():
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena with guards and ranged turrets")
    )
    assert plan.production_spec_bundle is not None

    response = module.preview_spec_bundle(
        module.SpecBundlePreviewRequest(
            production_spec_bundle=plan.production_spec_bundle,
            target="godot",
        )
    )

    assert response.validation.status in {"passed", "warning"}
    assert response.artifacts
    assert response.traces
    # The godot preview must report the same artifact set execution writes:
    # the adapter runtime plus the per-table config exports.
    assert any(artifact.path == "data/production-spec-runtime.json" for artifact in response.artifacts)
    assert any(artifact.path.startswith("data/config/") for artifact in response.artifacts)
    assert any(trace.spec_field.startswith("config_tables.tables.") for trace in response.traces)
    assert response.executable_qa.results
    assert "/api/specs/preview" in {route.path for route in module.app.routes}


def test_studio_exposes_job_cancel_endpoints():
    module = _load_studio_app()
    routes = {route.path for route in module.app.routes}

    assert "/api/execute/{job_id}/cancel" in routes
    assert "/api/assets/execute/{job_id}/cancel" in routes
    assert module.execute_cancel("nope") == {"status": "unknown", "job_id": "nope"}
    assert module.asset_execute_cancel("nope") == {"status": "unknown", "job_id": "nope"}


def test_cancel_endpoint_stops_a_running_job(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent import process_runner
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    running = threading.Event()

    def slow_execute(req, *, confirmed, **_kwargs):
        running.set()
        while True:
            event = process_runner.current_cancel_event()
            if event is not None and event.is_set():
                raise process_runner.ProcessCancelled("godot import")
            time.sleep(0.05)

    monkeypatch.setattr(module, "_build_execution_result", slow_execute)

    started = module.execute_demo(
        module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=True)
    )
    job_id = started["job_id"]
    assert running.wait(timeout=5)

    assert module.execute_cancel(job_id) == {"job_id": job_id, "status": "cancelling"}

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and module.execute_status(job_id)["status"] != "cancelled":
        time.sleep(0.05)

    assert module.execute_status(job_id)["status"] == "cancelled"
    module._EXECUTE_POOL.shutdown(wait=True)


def test_frontend_includes_spec_bundle_panel():
    module = _load_studio_app()
    flow_source = module.REPO_ROOT.joinpath(
        "apps/frontend/src/console/FlowConsole.tsx"
    ).read_text(encoding="utf-8")
    rendering_source = module.REPO_ROOT.joinpath(
        "apps/frontend/src/console/rendering.tsx"
    ).read_text(encoding="utf-8")

    assert '["specs", "tabSpecs"]' in flow_source
    assert "SpecBundlePanel" in flow_source
    assert "spec-trace-list" in rendering_source


def test_agent_run_forwards_the_permission_grants(monkeypatch):
    """The panel's toggles must reach the loop.

    Guards a real failure: the call site passed include_engine_tools while the
    request model lacked the field, so Pydantic silently dropped it and every
    run came back as an AttributeError instead of running.
    """

    module = _load_studio_app()
    captured: dict = {}

    def fake_run(goal, **kwargs):
        captured["goal"] = goal
        captured.update(kwargs)
        from fantasy_agent.agent_loop import AgentRunResult

        return AgentRunResult(status="done", answer="ok")

    monkeypatch.setattr("fantasy_agent.agent_loop.run_agent", fake_run)

    response = module.run_planning_agent(
        module.AgentRunRequest(
            goal="build it",
            max_turns=3,
            include_engine_tools=True,
            allow_write=True,
            allow_execute=True,
        )
    )

    assert response["status"] == "done", response.get("error")
    assert captured["include_engine_tools"] is True
    assert captured["allow_write"] is True
    assert captured["allow_execute"] is True


def test_agent_run_rejects_an_empty_goal():
    module = _load_studio_app()

    response = module.run_planning_agent(module.AgentRunRequest(goal="   "))

    assert response["status"] == "error"


def test_frontend_includes_agent_panel():
    module = _load_studio_app()
    shell = module.REPO_ROOT.joinpath(
        "apps/frontend/src/studio/StudioShell.tsx"
    ).read_text(encoding="utf-8")
    api = module.REPO_ROOT.joinpath("apps/frontend/src/shared/api.ts").read_text(encoding="utf-8")

    assert "AgentPanel" in shell
    assert 'data-panel="agent"' in shell
    assert "runAgent" in api
    assert "/api/agent/run" in api