"""UI requests keep their explicit user action and exact backend project reference."""

import hashlib

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from apps.studio.app import main
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from fantasy_agent.studio_projects import StudioProjectStore
from fantasy_agent.studio_workflow import StudioWorkflowService
from fantasy_agent.workflow_authorization import WorkflowAuthorizationStore
from fantasy_agent.workflows import run_director_workflow


@pytest.mark.parametrize(
    "model", [main.ExecuteDemoRequest, main.AssetExecutionRequest, main.EvolutionPlanRequest]
)
def test_ui_plan_requests_accept_the_project_version_the_panel_shows(model):
    plan = run_director_workflow(
        PromptRequest(prompt="a courier escapes a haunted station", engine_version="Godot 4"),
        use_llm=False,
    )
    request = model.model_validate(
        {"plan": plan.model_dump(mode="json"), "project_id": "project-test", "plan_version": 1}
    )
    assert request.project_id == "project-test" and request.plan_version == 1


def test_partial_project_reference_is_not_a_legacy_unbound_request():
    plan = run_director_workflow(
        PromptRequest(prompt="a courier escapes a haunted station", engine_version="Godot 4"),
        use_llm=False,
    )
    with pytest.raises(ValidationError):
        main.ExecuteDemoRequest.model_validate(
            {"plan": plan.model_dump(mode="json"), "project_id": "project-test"}
        )


def test_any_remote_peer_is_refused_even_at_the_health_endpoint():
    client = TestClient(main.app, client=("192.0.2.5", 1234))
    try:
        assert client.get("/health").status_code == 403
    finally:
        client.close()


def test_ui_review_refuses_content_that_changed_since_the_panel_rendered():
    from fantasy_agent.studio_projects import ProjectResource, ProjectSnapshot

    snapshot = ProjectSnapshot(
        project_id="project-test",
        plan_version=1,
        name="项目",
        resources=[
            ProjectResource(
                resource_id="mesh",
                path="versions/v1/generated/assets/mesh.glb",
                kind="asset",
                plan_version=1,
                sha256="a" * 64,
            )
        ],
    )
    with pytest.raises(ValueError, match="版本"):
        main._validate_ui_subjects(
            snapshot, [main.ReviewSubject(resource_id="mesh", sha256="b" * 64)]
        )


class NoProductionPool:
    def submit(self, *_args, **_kwargs):
        pytest.fail("同步与审阅不得启动生产任务")


@pytest.fixture
def bound_workflow(tmp_path, monkeypatch):
    from fantasy_agent import llm

    def no_model(*_args, **_kwargs):
        pytest.fail("项目工作流同步不得调用应用模型")

    monkeypatch.setattr(llm, "complete_json", no_model)
    monkeypatch.setattr(llm, "complete_with_tools", no_model)
    monkeypatch.setattr(main, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(main, "_ORCHESTRATION_SESSIONS", {})
    store = StudioProjectStore(tmp_path)
    plan = run_director_workflow(
        PromptRequest(prompt="a courier escapes a haunted station", engine_version="Godot 4"),
        use_llm=False,
    )
    store.create("测试项目", project_id="project-test", plan=plan)
    service = StudioWorkflowService(
        store,
        WorkflowAuthorizationStore(store),
        execute_jobs=InMemoryJobRegistry(NoProductionPool()),
        asset_jobs=InMemoryJobRegistry(NoProductionPool()),
        playtest_jobs=InMemoryJobRegistry(NoProductionPool()),
        evolution_jobs=InMemoryJobRegistry(NoProductionPool()),
    )
    monkeypatch.setattr(main.app.state, "workflow_service", service, raising=False)
    root = store.production_workspace("project-test")
    mesh = root / "versions/v1/generated/assets/objective.glb"
    mesh.parent.mkdir(parents=True)
    mesh.write_bytes(b"current reviewed mesh")
    digest = hashlib.sha256(mesh.read_bytes()).hexdigest()
    store.register_resource(
        "project-test",
        resource_id="objective-mesh",
        path=mesh.relative_to(root).as_posix(),
        kind="asset",
        plan_version=1,
        sha256=digest,
    )
    client = TestClient(main.app, client=("127.0.0.1", 1234))
    yield client, service, store, plan, mesh, digest
    client.close()


def run_body(plan, **updates):
    return {
        "plan": plan.model_dump(mode="json"),
        "project_id": "project-test",
        "plan_version": 1,
        **updates,
    }


def decision_body(digest, **updates):
    return {
        "project_id": "project-test",
        "plan_version": 1,
        "decision": "approved",
        "subjects": [{"resource_id": "objective-mesh", "sha256": digest}],
        **updates,
    }


def decision_url(session="workflow-v1", stage="creative_review", engine="godot"):
    return f"/api/orchestration/{session}/stages/{stage}/decision?engine={engine}"


def test_asset_form_writes_and_removes_only_the_selected_project_copy(bound_workflow, tmp_path):
    client, service, store, _, _, _ = bound_workflow
    source = tmp_path / "download.png"
    source.write_bytes(b"user-selected local image")
    response = client.post(
        "/api/assets",
        json={
            "name": "项目参考",
            "source_path": str(source),
            "project_id": "project-test",
            "plan_version": 1,
        },
    )
    assert response.status_code == 200, response.text
    entry = response.json()["entry"]
    version_root = service._root("project-test", 1)
    assert (version_root / entry["path"]).read_bytes() == source.read_bytes()
    assert client.get("/api/assets").json()["entries"] == []
    scoped = client.get("/api/assets?project_id=project-test&plan_version=1").json()
    assert [item["id"] for item in scoped["entries"]] == [entry["id"]]
    resource = next(
        item for item in store.snapshot("project-test").resources if item.sha256 == entry["sha256"]
    )
    intent = service.request_asset_review(
        "project-test", plan_version=1, resource_ids=[resource.resource_id]
    )
    service.apply_asset_review("project-test", intent["intent_id"], approved=True)
    removed = client.delete(f"/api/assets/{entry['id']}?project_id=project-test&plan_version=1")
    assert removed.status_code == 200, removed.text
    assert source.read_bytes() == b"user-selected local image"
    assert not (version_root / entry["path"]).exists()
    assert resource.resource_id not in {
        item.resource_id for item in store.snapshot("project-test").resources
    }


def test_asset_form_refuses_a_stale_or_partial_project_reference(bound_workflow, tmp_path):
    client, _, _, _, _, _ = bound_workflow
    source = tmp_path / "download.png"
    source.write_bytes(b"local file")
    body = {"name": "本机参考", "source_path": str(source), "project_id": "project-test"}
    assert client.post("/api/assets", json=body).status_code == 422
    assert client.post("/api/assets", json={**body, "plan_version": 0}).status_code == 409
    assert client.get("/api/assets?project_id=project-test").status_code == 422


def test_bound_run_reads_durable_workflow_evidence_without_another_session(bound_workflow):
    client, service, store, _plan, _mesh, _digest = bound_workflow
    prepared = service.call(
        "generate_game_production_plan",
        {
            "project_id": "project-test",
            "plan_version": 1,
            "prompt": "a courier escapes a haunted station",
            "engine_version": "Godot 4",
        },
    )
    assert prepared.status == "ok"
    latest = store.snapshot("project-test")
    response = client.post("/api/orchestration/run", json=run_body(latest.plan, plan_version=2))
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "project-test"
    assert payload["plan_version"] == 2 and payload["session_id"] == "workflow-v2"
    assert payload["engine"] == "godot"
    assert (
        next(s for s in payload["stages"] if s["stage_id"] == "gameplay_orchestration")["status"]
        == "done"
    )
    assert not main._ORCHESTRATION_SESSIONS
    assert not store.snapshot("project-test").jobs
    assert not service.authorization.grants("project-test")


@pytest.mark.parametrize(
    "updates",
    [
        {"allow_write": True},
        {"allow_execute": True},
        {"confirm_stages": ["godot_quick_play"]},
        {"rewind_stage": "creative_review"},
    ],
)
def test_bound_run_refuses_production_or_rewind_at_the_sync_entry(bound_workflow, updates):
    client, service, store, plan, _mesh, _digest = bound_workflow
    response = client.post("/api/orchestration/run", json=run_body(plan, **updates))
    assert response.status_code == 400
    assert "控制台" in response.text and "Agent" in response.text
    assert not main._ORCHESTRATION_SESSIONS
    assert not store.snapshot("project-test").jobs
    assert not service.authorization.grants("project-test")


def test_bound_run_refuses_a_stale_saved_version(bound_workflow):
    client, _service, store, plan, _mesh, _digest = bound_workflow
    store.update_plan("project-test", plan, expected_version=1)
    response = client.post("/api/orchestration/run", json=run_body(plan))
    assert response.status_code == 409
    assert response.json()["detail"]["latest"]["plan_version"] == 2
    assert not main._ORCHESTRATION_SESSIONS


def test_bound_run_refuses_an_unsaved_draft_even_at_the_current_version(bound_workflow):
    client, _service, _store, plan, _mesh, _digest = bound_workflow
    body = run_body(plan)
    body["plan"]["production_pipeline"]["goal"] = "尚未保存的另一版目标"
    response = client.post("/api/orchestration/run", json=body)
    assert response.status_code == 409
    assert not main._ORCHESTRATION_SESSIONS


@pytest.mark.parametrize("project_id,version,want", [("missing", 1, 404), ("empty", 0, 400)])
def test_bound_run_requires_an_existing_project_with_a_saved_plan(
    bound_workflow, project_id, version, want
):
    client, _service, store, plan, _mesh, _digest = bound_workflow
    store.create("尚未保存计划", project_id="empty")
    response = client.post(
        "/api/orchestration/run",
        json=run_body(plan, project_id=project_id, plan_version=version),
    )
    assert response.status_code == want
    assert not main._ORCHESTRATION_SESSIONS


@pytest.mark.parametrize("decision,want", [("approved", "done"), ("rejected", "failed")])
def test_bound_decision_is_the_same_durable_asset_review_after_restart(
    bound_workflow, decision, want
):
    client, service, store, _plan, mesh, digest = bound_workflow
    response = client.post(decision_url(), json=decision_body(digest, decision=decision))
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "project-test" and payload["session_id"] == "workflow-v1"
    review = next(s for s in payload["stages"] if s["stage_id"] == "creative_review")
    assert review["status"] == want
    saved = StudioProjectStore(store.workspace_root).snapshot("project-test")
    decisions = list(saved.decisions.values())
    assert len(decisions) == 1 and decisions[0]["kind"] == "asset_review"
    assert decisions[0]["status"] == decision
    assert decisions[0]["subjects"][0]["sha256"] == digest
    assert mesh.read_bytes() == b"current reviewed mesh"
    restarted = StudioWorkflowService(
        StudioProjectStore(store.workspace_root),
        service.authorization,
        execute_jobs=service.execute_jobs,
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
    )
    restored = restarted.workflow_state("project-test")
    assert (
        next(s for s in restored["stages"] if s["stage_id"] == "creative_review")["status"] == want
    )
    assert not main._ORCHESTRATION_SESSIONS
    assert not store.snapshot("project-test").jobs


@pytest.mark.parametrize(
    "session,stage,engine,updates",
    [
        ("wrong-session", "creative_review", "godot", {}),
        ("workflow-v1", "creative_review", "unreal", {}),
        ("workflow-v1", "gameplay_orchestration", "godot", {}),
        ("workflow-v1", "another-gate", "godot", {}),
        ("workflow-v1", "creative_review", "godot", {"subjects": []}),
        ("workflow-v1", "creative_review", "godot", {"decision": "invented"}),
        (
            "workflow-v1",
            "creative_review",
            "godot",
            {"subjects": [{"resource_id": "objective-mesh", "sha256": "f" * 64}]},
        ),
        (
            "workflow-v1",
            "creative_review",
            "godot",
            {"subjects": [{"resource_id": "foreign-mesh", "sha256": "f" * 64}]},
        ),
    ],
)
def test_bound_decision_refuses_the_wrong_gate_or_subject(
    bound_workflow, session, stage, engine, updates
):
    client, _service, store, _plan, _mesh, digest = bound_workflow
    response = client.post(
        decision_url(session, stage, engine), json=decision_body(digest, **updates)
    )
    assert response.status_code == 400
    assert not store.snapshot("project-test").decisions
    assert not main._ORCHESTRATION_SESSIONS


def test_bound_decision_refuses_stale_versions_before_saving_any_decision(bound_workflow):
    client, _service, store, plan, _mesh, digest = bound_workflow
    store.update_plan("project-test", plan, expected_version=1)
    response = client.post(decision_url(), json=decision_body(digest))
    assert response.status_code == 409
    assert not store.snapshot("project-test").decisions


def test_bound_decision_rehashes_the_actual_file_before_approval(bound_workflow):
    client, _service, store, _plan, mesh, digest = bound_workflow
    mesh.write_bytes(b"content changed after UI rendering")
    response = client.post(decision_url(), json=decision_body(digest))
    assert response.status_code == 400
    assert not store.snapshot("project-test").decisions


@pytest.mark.parametrize("change,want", [("content", 400), ("plan", 409)])
def test_bound_decision_rechecks_evidence_between_review_request_and_apply(
    bound_workflow, monkeypatch, change, want
):
    client, service, store, plan, mesh, digest = bound_workflow
    request_review = service.request_asset_review

    def prepare_then_change(*args, **kwargs):
        intent = request_review(*args, **kwargs)
        if change == "content":
            mesh.write_bytes(b"changed after review intent")
        else:
            store.update_plan("project-test", plan, expected_version=1)
        return intent

    monkeypatch.setattr(service, "request_asset_review", prepare_then_change)
    response = client.post(decision_url(), json=decision_body(digest))
    assert response.status_code == want
    assert not store.snapshot("project-test").decisions


def test_bound_decision_cannot_redeem_another_projects_resource(bound_workflow):
    client, _service, store, plan, _mesh, digest = bound_workflow
    store.create("另一个项目", project_id="other-project", plan=plan)
    response = client.post(decision_url(), json=decision_body(digest, project_id="other-project"))
    assert response.status_code == 400
    assert not store.snapshot("project-test").decisions
    assert not store.snapshot("other-project").decisions
