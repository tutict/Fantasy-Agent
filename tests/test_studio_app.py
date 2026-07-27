from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.path_safety import WorkspacePathError


def _load_studio_app():
    module_path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _materialize_review_artifacts(review, root: Path, *, target: str = 'unreal'):
    for item in review.items:
        artifact_path = Path(item.asset_path)
        if (
            target == 'godot'
            and item.source == 'blender'
            and artifact_path.suffix.casefold() == '.fbx'
        ):
            artifact_path = artifact_path.with_suffix('.glb')
        artifact_path = root / artifact_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(f'reviewed-{item.asset_id}'.encode())
    return review


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
    assert module.FRONTEND_DIST_DIR.name == "dist"
    assert module.FRONTEND_INDEX_PATH.name == "index.html"
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
    assert "/api/mcp/status" in html or "getMcpStatus" in frontend_source
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


def test_write_approval_manifest_api_writes_generated_yaml(monkeypatch, tmp_path):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    review = _materialize_review_artifacts(
        plan.creative_review,
        tmp_path,
        target='godot',
    )
    first = review.items[0].asset_id
    second = review.items[1].asset_id
    blender_item = next(item for item in review.items if item.source == 'blender')
    req = module.ApprovalManifestRequest(
        review=review,
        target='godot',
        decisions={
            first: "approved",
            second: "needs_revision",
            blender_item.asset_id: "approved",
        },
    )
    assert req.target == 'godot'

    response = module.write_approval_manifest(req)

    assert response.status == "written"
    assert response.manifest_path == "generated/asset-approval-manifest.yaml"
    output = tmp_path / response.manifest_path
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "approved_asset_ids:" in text
    assert first in text
    assert second in response.manifest.revision_asset_ids
    blender_decision = next(
        decision
        for decision in response.manifest.decisions
        if decision.asset_id == blender_item.asset_id
    )
    assert blender_item.asset_path.endswith('.fbx')
    assert blender_decision.asset_path == Path(blender_item.asset_path).with_suffix(
        '.glb'
    ).as_posix()
    assert blender_decision.artifact_identity is not None


@pytest.mark.parametrize(
    ('case', 'expected_error'),
    [
        ('missing', FileNotFoundError),
        ('outside', WorkspacePathError),
        ('traversal', WorkspacePathError),
        ('symlink', WorkspacePathError),
    ],
)
def test_write_approval_manifest_api_rejects_invalid_public_blender_glb(
    case,
    expected_error,
    monkeypatch,
    tmp_path: Path,
):
    from fantasy_agent.workflows import run_director_workflow

    module = _load_studio_app()
    workspace_root = tmp_path / 'workspace'
    workspace_root.mkdir()
    outside_glb = tmp_path / 'outside.glb'
    outside_glb.write_bytes(b'outside-secret')
    monkeypatch.setattr(module, 'REPO_ROOT', workspace_root)
    plan = run_director_workflow(
        PromptRequest(prompt='rooftop parkour chase', target_minutes=10)
    )
    blender_item = next(
        item for item in plan.creative_review.items if item.source == 'blender'
    )
    if case == 'outside':
        review_item = blender_item.model_copy(
            update={'asset_path': (tmp_path / 'outside.fbx').as_posix()}
        )
    elif case == 'traversal':
        review_item = blender_item.model_copy(update={'asset_path': '../outside.fbx'})
    elif case == 'symlink':
        linked_glb = workspace_root / 'linked.glb'
        linked_glb.symlink_to(outside_glb)
        review_item = blender_item.model_copy(update={'asset_path': 'linked.fbx'})
    else:
        review_item = blender_item
    invalid_review = plan.creative_review.model_copy(update={'items': [review_item]})

    with pytest.raises(expected_error):
        module.write_approval_manifest(
            module.ApprovalManifestRequest(
                review=invalid_review,
                target='godot',
                decisions={review_item.asset_id: 'approved'},
            )
        )
    assert not (workspace_root / 'generated' / 'asset-approval-manifest.yaml').exists()


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

    def fake_execute(req, *, confirmed):
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
    review = _materialize_review_artifacts(plan.creative_review, tmp_path)
    item = review.items[0]
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    response = module.write_approval_manifest(
        module.ApprovalManifestRequest(
            review=review,
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
