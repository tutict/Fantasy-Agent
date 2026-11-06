"""External Studio workflow uses real planning and bridges, never app LLMs."""

from importlib import import_module, util

import pytest

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from fantasy_agent.studio_projects import StudioProjectStore
from fantasy_agent.workflow_authorization import WorkflowAuthorizationStore
from fantasy_agent.workflows import run_director_workflow


class QueuedPool:
    def __init__(self):
        self.work = []

    def submit(self, fn, *args):
        self.work.append(lambda: fn(*args))

    def run(self):
        self.work.pop(0)()


@pytest.fixture
def context(tmp_path, request):
    assert util.find_spec("fantasy_agent.studio_workflow"), "external workflow missing"
    mod = import_module("fantasy_agent.studio_workflow")
    store = StudioProjectStore(tmp_path)
    plan = run_director_workflow(
        PromptRequest(
            prompt=getattr(request, "param", "a courier escapes a haunted station"),
            engine_version="Godot 4",
        ),
        use_llm=False,
    )
    store.create("测试", project_id="demo", plan=plan)
    now = [1000.0]
    auth = WorkflowAuthorizationStore(store, clock=lambda: now[0])
    pool, play_pool = QueuedPool(), QueuedPool()
    registries = {
        key: InMemoryJobRegistry(play_pool if key == "playtest" else pool)
        for key in ("execute", "assets", "playtest", "evolution")
    }
    service = mod.StudioWorkflowService(
        store,
        auth,
        execute_jobs=registries["execute"],
        asset_jobs=registries["assets"],
        playtest_jobs=registries["playtest"],
        evolution_jobs=registries["evolution"],
        clock=lambda: now[0],
    )
    return mod, service, store, auth, pool, play_pool, now


@pytest.fixture
def completed_evolution(context, monkeypatch):
    from fantasy_agent.contracts import PlaytestReport, PlaytestSample

    mod, service, _, _, pool, _, _ = context
    real_evolution = mod.run_evolution
    calls = []

    def measured(*_args):
        calls.append(True)
        return PlaytestReport(
            runs_requested=3,
            samples=[
                PlaytestSample(
                    run_index=index,
                    outcome="fail" if len(calls) == 1 else "win",
                    reason="Route timer expires before extraction" if len(calls) == 1 else "",
                    session_seconds=12,
                    player_moved_distance=80,
                    playable=True,
                    axis="parkour",
                    held=["sprint"],
                    taps={"vault": 5, "slide": 2},
                )
                for index in range(3)
            ],
        )

    monkeypatch.setattr(
        mod,
        "run_evolution",
        lambda request, **kwargs: real_evolution(request, **kwargs, run_iteration=measured),
    )
    job = execute(service, approve(service, "run_evolution"), "run_evolution")
    pool.run()
    assert service.get_job("demo", job["job_id"])["status"] == "done"
    return job


def approve(service, name="create_godot_project_structure", arguments=None, node_id=""):
    intent = service.request_authorization(
        "demo",
        plan_version=1,
        actions=[{"tool_name": name, "arguments": arguments or {}, "node_id": node_id}],
        ttl_seconds=100,
    )
    return service.apply_authorization("demo", intent["intent_id"], approved=True)["grant_id"]


def execute(
    service,
    grant_id,
    name="create_godot_project_structure",
    arguments=None,
    request_id="first",
    node_id="",
):
    return service.execute_tool(
        "demo",
        plan_version=1,
        tool_name=name,
        arguments=arguments or {},
        grant_id=grant_id,
        request_id=request_id,
        node_id=node_id,
    )


def test_all_planning_projections_are_deterministic_without_key(context, monkeypatch):
    from fantasy_agent import llm
    from fantasy_agent.planning_actions import PLANNING_TOOL_NAMES

    _, service, _, _, _, _, _ = context
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: pytest.fail("app LLM used"))
    for name in PLANNING_TOOL_NAMES:
        args = (
            {"raw_idea": "逃出闹鬼车站，收集钥匙"}
            if name == "extract_idea_seed"
            else {"prompt": "a courier escapes a haunted station"}
        )
        result = service.call(name, args)
        assert result.status == "ok", (name, result)
        assert result.data


@pytest.mark.parametrize(
    "field,value",
    [
        ("confirmed", True),
        ("confirmed_side_effects", True),
        ("write_files", True),
        ("workspace_root", "outside"),
        ("plan", {}),
        ("gameplay_scripts", {"evil.gd": "bad"}),
        ("godot_executable", "evil"),
        ("project_dir", "outside"),
    ],
)
def test_hidden_production_arguments_are_rejected_before_claim(context, field, value):
    _, service, store, _, pool, _, _ = context
    grant = approve(service)
    with pytest.raises(ValueError):
        execute(service, grant, arguments={field: value})
    assert store.snapshot("demo").jobs == []
    assert pool.work == []


def test_authorization_intent_is_not_a_grant_and_cannot_be_replayed(context):
    _, service, store, _, pool, _, _ = context
    intent = service.request_authorization(
        "demo", plan_version=1, actions=[{"tool_name": "create_godot_project_structure"}]
    )
    with pytest.raises(ValueError):
        execute(service, intent["intent_id"])
    assert not store.snapshot("demo").jobs and not pool.work
    assert (
        service.apply_authorization("demo", intent["intent_id"], approved=False)["status"]
        == "declined"
    )
    with pytest.raises(ValueError):
        service.apply_authorization("demo", intent["intent_id"], approved=True)


def test_claim_then_queue_real_bridge_and_idempotent_original_job(context):
    _, service, store, _, pool, _, _ = context
    grant = approve(service)
    queued = execute(service, grant)
    assert queued["status"] == "queued"
    original = store.snapshot("demo").jobs[0]
    assert original.status == "queued" and original.grant_id == grant
    assert len(pool.work) == 1
    assert execute(service, grant, request_id="alias")["job_id"] == queued["job_id"]
    assert len(pool.work) == 1
    pool.run()
    result = service.get_job("demo", queued["job_id"])
    assert result["status"] == "done", result
    assert result["resources"]
    resource = result["resources"][0]
    assert service.read_resource("demo", resource["resource_id"])["data"]
    restarted = type(service)(
        store,
        service.authorization,
        execute_jobs=service.execute_jobs,
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
        clock=service.clock,
    )
    assert restarted.get_job("demo", queued["job_id"])["status"] == "done"
    assert execute(service, grant, request_id="later")["job_id"] == queued["job_id"]


@pytest.mark.parametrize("expire", [True, False])
def test_queued_worker_rechecks_deadline_and_plan_version(context, expire):
    _, service, store, _, pool, _, now = context
    grant = approve(service)
    queued = execute(service, grant)
    if expire:
        now[0] += 100
    else:
        store.update_plan("demo", store.snapshot("demo").plan, expected_version=1)
    pool.run()
    assert service.get_job("demo", queued["job_id"])["status"] == "failed"
    assert not list(store.production_workspace("demo").rglob("project.godot"))


def test_cancel_queued_task_never_calls_bridge(context):
    _, service, store, _, pool, _, _ = context
    queued = execute(service, approve(service))
    assert service.cancel_job("demo", queued["job_id"])["status"] == "cancelling"
    pool.run()
    assert service.get_job("demo", queued["job_id"])["status"] == "cancelled"
    assert not list(store.production_workspace("demo").rglob("project.godot"))


def test_startup_reconciliation_is_explicit_and_never_resubmits(context):
    _, service, store, _, pool, _, _ = context
    queued = execute(service, approve(service))
    assert service.get_job("demo", queued["job_id"])["status"] == "queued"
    service.recover_interrupted()
    assert store.snapshot("demo").jobs[0].status == "interrupted"
    pool.run()
    assert service.get_job("demo", queued["job_id"])["status"] == "interrupted"


def test_restart_settles_the_running_cards_without_replaying_the_worker(context):
    _, service, store, _, _, _, _ = context
    queued = execute(service, approve(service))
    assert service.authorization.start_job("demo", queued["job_id"])
    job = store.snapshot("demo").jobs[0]
    service._begin_job("demo", job)
    assert service.workflow_state("demo")["status"] == "running"
    recovered_pool = QueuedPool()
    restarted = type(service)(
        StudioProjectStore(store.workspace_root),
        service.authorization,
        execute_jobs=InMemoryJobRegistry(recovered_pool),
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
        clock=service.clock,
    )
    restarted.recover_interrupted()
    assert restarted.get_job("demo", queued["job_id"])["status"] == "interrupted"
    state = restarted.workflow_state("demo")
    assert state["status"] != "running"
    assert not any(stage["status"] == "running" for stage in state["stages"])
    assert not recovered_pool.work


def test_creating_a_project_does_not_leave_unstarted_asset_integration_running(context):
    _, service, store, _, pool, _, _ = context
    queued = execute(service, approve(service))
    pool.run()
    assert service.get_job("demo", queued["job_id"])["status"] == "done"
    state = service.workflow_state("demo")
    stages = {stage["stage_id"]: stage for stage in state["stages"]}
    assert stages["godot_quick_play"]["status"] == "done"
    assert stages["asset_integration"]["status"] != "running"
    assert state["status"] != "running"
    restarted = type(service)(
        StudioProjectStore(store.workspace_root),
        service.authorization,
        execute_jobs=service.execute_jobs,
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
        clock=service.clock,
    )
    assert restarted.workflow_state("demo")["status"] != "running"
    assert not pool.work


def test_engine_project_resources_are_readable_text(context):
    _, service, _, _, pool, _, _ = context
    job = execute(service, approve(service))
    pool.run()
    resource = next(
        ref
        for ref in service.get_job("demo", job["job_id"])["resources"]
        if ref["path"].endswith("project.godot")
    )
    result = service.read_resource("demo", resource["resource_id"])
    assert result["mime_type"].startswith("text/")
    assert "config_version=5" in result["data"]


def test_independent_playtest_reports_qa_without_restarting_production(context, monkeypatch):
    from fantasy_agent.contracts import PlaytestReport, PlaytestSample
    from fantasy_agent.godot_mcp import GodotMCPBridge
    from fantasy_agent.godot_playtest import aggregate_samples

    _, service, _, _, pool, play_pool, _ = context
    execute(service, approve(service))
    pool.run()

    def measured(self, request, session_id=""):
        report_path = self.workspace_root / "generated/playtest/qa-fixture/playtest-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        samples = [
            PlaytestSample(run_index=0, outcome="win", playable=True, player_moved_distance=80)
        ]
        report = PlaytestReport(
            status="passed",
            project_dir=request.project_dir,
            runs_requested=1,
            samples=samples,
            aggregate=aggregate_samples(samples),
            artifact_paths=[str(report_path)],
        )
        report_path.write_text(report.model_dump_json(), encoding="utf-8")
        return report

    monkeypatch.setattr(GodotMCPBridge, "playtest_project", measured)
    task = execute(
        service,
        approve(service, "playtest_godot_project"),
        "playtest_godot_project",
        request_id="independent-qa",
    )
    play_pool.run()
    result = service.get_job("demo", task["job_id"])
    assert result["status"] == "done"
    assert any(ref["path"].endswith("playtest-report.json") for ref in result["resources"])
    stages = {stage["stage_id"]: stage for stage in service.workflow_state("demo")["stages"]}
    assert stages["godot_quick_play"]["status"] == "done"
    assert stages["optimization_testing"]["status"] == "done"
    assert stages["godot_quick_play"]["tools"] == ["create_godot_project_structure"]


def test_resource_ids_cannot_cross_projects_or_read_credentials(context):
    _, service, store, _, pool, _, _ = context
    job = execute(service, approve(service))
    pool.run()
    resource = service.get_job("demo", job["job_id"])["resources"][0]
    store.create("other", project_id="other", plan=store.snapshot("demo").plan)
    with pytest.raises(ValueError):
        service.read_resource("other", resource["resource_id"])
    root = store.production_workspace("demo")
    (root / "llm-api.json").write_text('{"key":"secret"}')
    store.register_resource("demo", resource_id="credential", path="llm-api.json")
    with pytest.raises(ValueError):
        service.read_resource("demo", "credential")


def test_new_versions_do_not_reuse_prior_output_locations(context):
    _, service, store, _, pool, _, _ = context
    first = execute(service, approve(service))
    pool.run()
    first_paths = {r["path"] for r in service.get_job("demo", first["job_id"])["resources"]}
    store.update_plan("demo", store.snapshot("demo").plan, expected_version=1)
    intent = service.request_authorization(
        "demo", plan_version=2, actions=[{"tool_name": "create_godot_project_structure"}]
    )
    grant = service.apply_authorization("demo", intent["intent_id"], approved=True)["grant_id"]
    second = service.execute_tool(
        "demo",
        plan_version=2,
        tool_name="create_godot_project_structure",
        arguments={},
        grant_id=grant,
        request_id="second",
    )
    pool.run()
    assert first_paths.isdisjoint(
        {r["path"] for r in service.get_job("demo", second["job_id"])["resources"]}
    )


def test_evolution_budget_and_candidate_limits_before_scheduling(context):
    _, service, _, _, pool, _, _now = context
    with pytest.raises(ValueError):
        approve(service, "run_evolution", {"max_iterations": 4})
    intent = service.request_authorization(
        "demo", plan_version=1, actions=[{"tool_name": "run_evolution"}], ttl_seconds=29
    )
    grant = service.apply_authorization("demo", intent["intent_id"], approved=True)["grant_id"]
    with pytest.raises(ValueError):
        execute(service, grant, "run_evolution")
    assert pool.work == []


@pytest.mark.parametrize("context", ["rooftop parkour chase across neon towers"], indirect=True)
def test_finished_evolution_with_unmet_production_dependencies_is_not_running(
    context, completed_evolution
):
    _, service, _, _, _, _, _ = context
    assert service.get_job("demo", completed_evolution["job_id"])["status"] == "done"
    state = service.workflow_state("demo")
    qa = next(stage for stage in state["stages"] if stage["stage_id"] == "optimization_testing")
    assert qa["status"] == "blocked"
    assert state["status"] != "running"


@pytest.mark.parametrize("context", ["rooftop parkour chase across neon towers"], indirect=True)
def test_adoption_updates_the_job_and_preserves_its_original_report_resources(
    context,
    completed_evolution,
):
    mod, service, store, _, pool, _, _ = context
    job_id = completed_evolution["job_id"]
    before = service.get_job("demo", job_id)
    original_resources = {
        ref["resource_id"]: service.read_resource("demo", ref["resource_id"])["data"]
        for ref in before["resources"]
    }
    assert original_resources
    intent = service.request_candidate_adoption("demo", plan_version=1, job_id=job_id)
    assert (
        service.apply_candidate_adoption("demo", intent["intent_id"], approved=True)["status"]
        == "adopted"
    )
    assert store.snapshot("demo").plan_version == 2
    after = service.get_job("demo", job_id)
    assert mod.worker_data(after["result"])["report"]["adopted_iteration"] == 1
    assert not any(
        action.get("tool") == "request_candidate_adoption"
        for action in after["next_actions"]
        if isinstance(action, dict)
    )
    for resource_id, data in original_resources.items():
        assert service.read_resource("demo", resource_id)["data"] == data
    with pytest.raises(ValueError):
        service.request_candidate_adoption("demo", plan_version=1, job_id=job_id)
    assert not pool.work


@pytest.mark.parametrize("context", ["rooftop parkour chase across neon towers"], indirect=True)
def test_failed_adoption_commit_does_not_publish_plan_report_or_experience(
    context,
    completed_evolution,
    monkeypatch,
):
    from fantasy_agent import studio_projects
    from fantasy_agent.evolution.library import list_experiences, load_report

    _, service, store, _, _, _, _ = context
    job_id = completed_evolution["job_id"]
    intent = service.request_candidate_adoption("demo", plan_version=1, job_id=job_id)
    real_write = studio_projects.write_atomic

    def failed_record(path, *args, **kwargs):
        if path == store.record_path("demo"):
            raise OSError("synthetic failed adoption commit")
        return real_write(path, *args, **kwargs)

    monkeypatch.setattr(studio_projects, "write_atomic", failed_record)
    with pytest.raises(OSError, match="failed adoption commit"):
        service.apply_candidate_adoption("demo", intent["intent_id"], approved=True)
    restored = StudioProjectStore(store.workspace_root).snapshot("demo")
    assert restored.plan_version == 1
    assert not any(item.get("kind") == "candidate_adoption" for item in restored.decisions.values())
    assert load_report(job_id, workspace_root=service._root("demo", 1)).adopted_iteration is None
    assert list_experiences(workspace_root=store.production_workspace("demo")) == []


@pytest.mark.parametrize("context", ["rooftop parkour chase across neon towers"], indirect=True)
def test_committed_adoption_repairs_projections_at_restart_without_replaying(
    context,
    completed_evolution,
    monkeypatch,
):
    from fantasy_agent.evolution import library

    mod, service, store, _, pool, _, _ = context
    job_id = completed_evolution["job_id"]
    intent = service.request_candidate_adoption("demo", plan_version=1, job_id=job_id)
    real_write = library.write_atomic

    def failed_index(path, *args, **kwargs):
        if path.name == "experiences.json":
            raise OSError("synthetic failed experience projection")
        return real_write(path, *args, **kwargs)

    monkeypatch.setattr(library, "write_atomic", failed_index)
    applied = service.apply_candidate_adoption("demo", intent["intent_id"], approved=True)
    assert applied["status"] == "adopted"
    assert applied["risks"]
    assert store.snapshot("demo").plan_version == 2
    assert (
        mod.worker_data(service.get_job("demo", job_id)["result"])["report"]["adopted_iteration"]
        == 1
    )
    monkeypatch.setattr(library, "write_atomic", real_write)
    restarted = type(service)(
        StudioProjectStore(store.workspace_root),
        service.authorization,
        execute_jobs=service.execute_jobs,
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
        clock=service.clock,
    )
    restarted.recover_interrupted()
    assert len(library.list_experiences(workspace_root=store.production_workspace("demo"))) == 1
    assert (
        library.load_report(job_id, workspace_root=service._root("demo", 1)).adopted_iteration == 1
    )
    assert not pool.work


@pytest.mark.parametrize("context", ["rooftop parkour chase across neon towers"], indirect=True)
def test_ui_adoption_uses_the_same_atomic_project_decision(
    context, completed_evolution, monkeypatch
):
    from starlette.testclient import TestClient

    from apps.studio.app import main

    mod, service, store, _, _, _, _ = context
    monkeypatch.setattr(main, "REPO_ROOT", store.workspace_root)
    monkeypatch.setattr(main.app.state, "workflow_service", service, raising=False)
    with TestClient(main.app, client=("127.0.0.1", 1234)) as client:
        response = client.post(
            f"/api/evolution/{completed_evolution['job_id']}/adopt",
            json={
                "project_id": "demo",
                "plan_version": 1,
                "plan": store.snapshot("demo").plan.model_dump(mode="json"),
            },
        )
    assert response.status_code == 200, response.text
    assert response.json()["plan_version"] == 2
    assert response.json()["resources"]
    assert any(
        item.get("kind") == "candidate_adoption"
        for item in store.snapshot("demo").decisions.values()
    )
    assert (
        mod.worker_data(service.get_job("demo", completed_evolution["job_id"])["result"])["report"][
            "adopted_iteration"
        ]
        == 1
    )


def test_unsupported_publish_package_and_unreal_resume_are_explicit(context):
    _, service, _, _, _, _, _ = context
    for name in ("publish_prototype_branch", "package_desktop"):
        result = service.call(name, {})
        assert result.status == "refused" and "未实现" in result.content
    with pytest.raises(ValueError):
        approve(service, "execute_demo", {"engine": "unreal", "resume_from": "create"})


def test_legacy_deterministic_codegen_never_attempts_llm(context, monkeypatch):
    from fantasy_agent import executor, gameplay_codegen

    _, _, store, _, _, _, _ = context
    plan = store.snapshot("demo").plan.model_copy(deep=True)
    plan.production_spec_bundle = None
    monkeypatch.setattr(
        gameplay_codegen, "_generate_with_llm", lambda *a, **k: pytest.fail("legacy called app LLM")
    )
    stages = []
    scripts, generated = executor._run_gameplay_codegen(plan, stages, use_llm=False)
    assert scripts and generated is False and stages[0].status == "done"


def test_external_stage_requires_dependencies_real_outputs_and_machine_checks(context):
    from fantasy_agent.orchestrator import Orchestrator
    from fantasy_agent.tool_registry import default_registry

    _, _, store, _, _, _, _ = context
    built = store.snapshot("demo").plan
    registry = default_registry(use_llm=False)
    registry.remember_plan(built.model_dump(mode="json"))
    orchestrator = Orchestrator(
        session_id="external", workspace_root=store.production_workspace("demo"), registry=registry
    )
    result = registry.call(
        "generate_game_production_plan",
        {"prompt": "a courier escapes a haunted station", "engine_version": "Godot 4"},
    )
    with pytest.raises(ValueError):
        orchestrator.accept_external_result(
            built.production_pipeline, "godot_quick_play", result, artifacts=[]
        )
    outcome = orchestrator.accept_external_result(
        built.production_pipeline,
        "gameplay_orchestration",
        result,
        artifacts=[],
        plan_evidence=built,
    )
    assert outcome.status == "done" and outcome.checks == ["verify_gameplay_spec"]
    assert orchestrator.pending_human_gates(built.production_pipeline)
    with pytest.raises(ValueError):
        orchestrator.accept_external_result(
            built.production_pipeline, "creative_review", result, artifacts=[]
        )


def test_failed_or_missing_production_evidence_never_advances(context):
    from fantasy_agent.orchestrator import Orchestrator
    from fantasy_agent.tool_registry import ToolOutcome, default_registry

    _, _, store, _, _, _, _ = context
    built = store.snapshot("demo").plan
    pipeline = built.production_pipeline.model_copy(deep=True)
    stage = next(s for s in pipeline.stages if s.id == "blender_modeling")
    stage.depends_on = []
    registry = default_registry(use_llm=False)
    registry.remember_plan(built.model_dump(mode="json"))
    orchestrator = Orchestrator(
        session_id="external", workspace_root=store.production_workspace("demo"), registry=registry
    )
    orchestrator.confirm([stage.id])
    for result, artifacts in [
        (ToolOutcome("generate_blender_script", "error", "failed"), []),
        (ToolOutcome("generate_blender_script", "ok", "claimed done"), []),
    ]:
        outcome = orchestrator.accept_external_result(
            pipeline, stage.id, result, artifacts=artifacts
        )
        assert outcome.status == "failed"


def test_registry_deadline_and_callback_failure_are_observable(context):
    from dataclasses import dataclass

    _, _, _, _, pool, _, now = context
    registry = InMemoryJobRegistry(pool)

    @dataclass
    class Result:
        status: str = "done"

    registry.submit(
        lambda: Result(),
        job_id="reserved",
        deadline=1001,
        clock=lambda: now[0],
        on_complete=lambda job, payload: (_ for _ in ()).throw(OSError("durability failed")),
    )
    pool.run()
    assert registry.status("reserved")["status"] == "failed"
    assert "durability failed" in registry.status("reserved")["error"]


def test_saved_plan_progress_restores_without_model_or_production(context):
    _, service, store, _, pool, _, _ = context
    result = service.call(
        "generate_game_production_plan",
        {
            "project_id": "demo",
            "plan_version": 1,
            "prompt": "a courier escapes a haunted station",
            "engine_version": "Godot 4",
        },
    )
    assert result.status == "ok"
    state = service.workflow_state("demo")
    assert (
        next(s for s in state["stages"] if s["stage_id"] == "gameplay_orchestration")["status"]
        == "done"
    )
    restarted = type(service)(
        store,
        service.authorization,
        execute_jobs=service.execute_jobs,
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
        clock=service.clock,
    )
    restored = restarted.workflow_state("demo")
    assert (
        next(s for s in restored["stages"] if s["stage_id"] == "gameplay_orchestration")["status"]
        == "done"
    )
    assert not pool.work and not store.snapshot("demo").jobs


def test_full_saved_plan_schema_validates_references_and_keeps_cas(context):
    _, service, store, _, _, _, _ = context
    plan = store.snapshot("demo").plan.model_dump(mode="json")
    result = service.call(
        "save_project_plan", {"project_id": "demo", "plan_version": 1, "plan": plan}
    )
    assert result.status == "ok"
    assert store.snapshot("demo").plan_version == 2
    stale = service.call(
        "save_project_plan", {"project_id": "demo", "plan_version": 1, "plan": plan}
    )
    assert stale.status == "refused" and stale.data["latest"]["plan_version"] == 2


def test_asset_review_is_durable_and_changed_content_cannot_be_approved(context):
    import hashlib

    _, service, store, _, _, _, _ = context
    root = store.production_workspace("demo")
    path = root / "versions/v1/generated/blender/mesh.glb"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"mesh-version-one")
    store.register_resource(
        "demo",
        resource_id="mesh-one",
        path=path.relative_to(root).as_posix(),
        kind="asset",
        plan_version=1,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    intent = service.request_asset_review("demo", plan_version=1, resource_ids=["mesh-one"])
    approved = service.apply_asset_review(
        "demo", intent["intent_id"], approved=True, feedback="比例合适"
    )
    assert approved["status"] == "approved"
    assert store.snapshot("demo").decisions[intent["intent_id"]]["status"] == "approved"
    pending = service.request_asset_review("demo", plan_version=1, resource_ids=["mesh-one"])
    path.write_bytes(b"mesh-version-two")
    with pytest.raises(ValueError):
        service.apply_asset_review("demo", pending["intent_id"], approved=True)
    assert pending["intent_id"] not in store.snapshot("demo").decisions


def test_generate_assets_and_import_are_separate_user_review_steps(context):
    _, service, _, _, pool, _, _ = context
    with pytest.raises(ValueError):
        approve(service, "execute_demo", {"with_assets": True})
    with pytest.raises(ValueError):
        approve(service, "execute_demo", {"with_visuals": True})
    assert pool.work == []


def test_workflow_resource_tool_preserves_contents_and_mime(context):
    _, service, _, _, pool, _, _ = context
    job = execute(service, approve(service))
    pool.run()
    rid = service.get_job("demo", job["job_id"])["resources"][0]["resource_id"]
    result = service.call("read_project_resource", {"project_id": "demo", "resource_id": rid})
    assert result.status == "ok" and result.data["resource"]["data"]
    assert result.data["resource"]["mime_type"]


def test_only_paths_reported_by_the_worker_belong_to_its_job(context):
    _, service, store, _, pool, _, _ = context
    unrelated = store.production_workspace("demo") / "versions/v1/generated/unrelated.glb"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_bytes(b"output from a different action")
    job = execute(service, approve(service))
    pool.run()
    paths = {item["path"] for item in service.get_job("demo", job["job_id"])["resources"]}
    assert paths
    assert unrelated.relative_to(store.production_workspace("demo")).as_posix() not in paths


def test_new_authorization_starts_a_new_generation_session(context):
    _, service, _, _, pool, _, _ = context
    first = execute(service, approve(service))
    pool.run()
    second = execute(service, approve(service), request_id="second-authorized-run")
    pool.run()
    first_result = service.get_job("demo", first["job_id"])
    second_result = service.get_job("demo", second["job_id"])
    assert first_result["session_id"] != second_result["session_id"]
    assert {item["path"] for item in first_result["resources"]}.isdisjoint(
        {item["path"] for item in second_result["resources"]}
    )


def test_rework_request_identity_includes_its_resume_target(context, monkeypatch):
    from dataclasses import dataclass

    mod, service, store, _, pool, _, _ = context

    @dataclass
    class Finished:
        status: str = "done"

    monkeypatch.setattr(mod, "launch_demo", lambda request: Finished())
    job = execute(service, approve(service, "execute_demo"), "execute_demo")
    pool.run()
    rework = service.rework_node(
        "demo", plan_version=1, job_id=job["job_id"], resume_from="validate", request_id="repair"
    )
    durable = next(item for item in store.snapshot("demo").jobs if item.job_id == rework["job_id"])
    assert durable.execution_context["resume_from"] == "validate"
    with pytest.raises(ValueError, match="不同内容"):
        service.rework_node(
            "demo", plan_version=1, job_id=job["job_id"], resume_from="import", request_id="repair"
        )
    assert len(pool.work) == 1


def generated_mesh(store):
    import hashlib

    root = store.production_workspace("demo")
    path = root / "versions/v1/generated/assets/objective.glb"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"reviewed mesh")
    store.register_resource(
        "demo",
        resource_id="objective-mesh",
        path=path.relative_to(root).as_posix(),
        kind="asset",
        plan_version=1,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    return path


def test_approved_asset_copy_is_registered_and_checks_review_before_claim(context):
    _, service, store, _, pool, _, _ = context
    project = execute(service, approve(service))
    pool.run()
    mesh = generated_mesh(store)
    arguments = {"resource_ids": ["objective-mesh"]}
    grant = approve(service, "copy_approved_godot_assets", arguments)
    with pytest.raises(ValueError, match="审阅"):
        execute(service, grant, "copy_approved_godot_assets", arguments, request_id="copy-assets")
    assert len(store.snapshot("demo").jobs) == 1 and not pool.work
    intent = service.request_asset_review("demo", plan_version=1, resource_ids=["objective-mesh"])
    service.apply_asset_review("demo", intent["intent_id"], approved=True)
    copied = execute(
        service, grant, "copy_approved_godot_assets", arguments, request_id="copy-assets"
    )
    pool.run()
    result = service.get_job("demo", copied["job_id"])
    assert result["status"] == "done", result
    project_file = next(
        resource
        for resource in service.get_job("demo", project["job_id"])["resources"]
        if resource["path"].endswith("project.godot")
    )
    destination = store.production_workspace("demo") / project_file["path"]
    assert (destination.parent / "assets/generated/objective.glb").read_bytes() == mesh.read_bytes()
    assert any(
        resource["path"].endswith("assets/generated/objective.glb")
        for resource in result["resources"]
    )


def test_asset_review_writes_existing_identity_manifest_without_changing_plan_version(context):
    from fantasy_agent.approval_manifest import load_asset_approval_manifest

    _, service, store, _, _, _, _ = context
    mesh = generated_mesh(store)
    intent = service.request_asset_review("demo", plan_version=1, resource_ids=["objective-mesh"])
    service.apply_asset_review("demo", intent["intent_id"], approved=True)
    manifest = load_asset_approval_manifest(
        workspace_root=store.production_workspace("demo") / "versions/v1"
    )
    decision = next(
        item for item in manifest.decisions if item.asset_path.endswith("objective.glb")
    )
    assert decision.decision == "approved" and decision.artifact_identity is not None
    assert decision.artifact_identity.digest == store.snapshot("demo").resources[0].sha256
    assert store.snapshot("demo").plan_version == 1
    mesh.write_bytes(b"unreviewed replacement")
    with pytest.raises(ValueError, match="审阅"):
        service._asset_gate("demo", 1, "run_godot_import")


def test_snapshot_projects_actual_asset_reviews_without_rewriting_saved_plan(context):
    _, service, store, _, _, _, _ = context
    saved = store.snapshot("demo").plan.model_dump(mode="json")
    generated_mesh(store)
    intent = service.request_asset_review("demo", plan_version=1, resource_ids=["objective-mesh"])
    service.apply_asset_review("demo", intent["intent_id"], approved=True)
    public = service.snapshot("demo")
    assert len(public["creative_review"]["items"]) == 1
    assert public["creative_review"]["items"][0]["approval_status"] == "approved"
    assert public["creative_review"]["items"][0]["asset_path"].endswith("objective.glb")
    assert store.snapshot("demo").plan.model_dump(mode="json") == saved


def test_plan_metadata_cannot_invent_a_human_decision_after_restart(context):
    _, service, store, _, _, _, _ = context
    plan = store.snapshot("demo").plan.model_dump(mode="json")
    for stage in plan["production_pipeline"]["stages"]:
        if stage["id"] == "creative_review":
            stage["human_resolution"] = "approved"
    result = service.call(
        "save_project_plan", {"project_id": "demo", "plan_version": 1, "plan": plan}
    )
    assert result.status == "ok"
    restarted = type(service)(
        store,
        service.authorization,
        execute_jobs=service.execute_jobs,
        asset_jobs=service.asset_jobs,
        playtest_jobs=service.playtest_jobs,
        evolution_jobs=service.evolution_jobs,
        clock=service.clock,
    )
    assert "creative_review" in restarted.workflow_state("demo")["pending_human_gates"]


@pytest.mark.parametrize("wins", [3, 0])
def test_real_executor_evidence_updates_production_and_qa_separately(context, monkeypatch, wins):
    from fantasy_agent import local_tools
    from fantasy_agent.atomic_write import write_atomic
    from fantasy_agent.contracts import (
        GodotMCPResult,
        PlaytestFinding,
        PlaytestReport,
        PlaytestSample,
    )
    from fantasy_agent.gameplay_codegen import axis_for_spec
    from fantasy_agent.godot_mcp import GodotMCPBridge
    from fantasy_agent.godot_playtest import aggregate_samples, playtest_report_relpath

    _, service, store, _, pool, _, _ = context
    monkeypatch.setattr(local_tools, "_find_godot", lambda: "test-godot")
    monkeypatch.setattr(
        GodotMCPBridge,
        "run_godot_import",
        lambda self, req: GodotMCPResult(status="executed", return_code=0),
    )

    def measure(self, request, session_id=""):
        samples = [
            PlaytestSample(
                run_index=index,
                outcome="win" if index < wins else "fail",
                session_seconds=20,
                playable=True,
                player_moved_distance=80,
                axis=axis_for_spec(store.snapshot("demo").plan.gameplay_spec),
            )
            for index in range(3)
        ]
        report = PlaytestReport(
            project_dir=request.project_dir,
            runs_requested=3,
            samples=samples,
            aggregate=aggregate_samples(samples),
            findings=[]
            if wins
            else [
                PlaytestFinding(
                    code="no_wins",
                    severity="blocking",
                    message="脚本输入没有达到胜利。",
                    rework_target="spec",
                )
            ],
        )
        write_atomic(
            self.workspace_root / playtest_report_relpath(session_id), report.model_dump_json()
        )
        return report

    monkeypatch.setattr(GodotMCPBridge, "playtest_project", measure)
    job = execute(service, approve(service, "execute_demo"), "execute_demo")
    pool.run()
    state = service.workflow_state("demo")
    produced = next(item for item in state["stages"] if item["stage_id"] == "godot_quick_play")
    quality = next(item for item in state["stages"] if item["stage_id"] == "optimization_testing")
    assert produced["status"] == "done", (
        produced,
        service.get_job("demo", job["job_id"])["blockers"],
    )
    assert produced["tools"] == ["execute_demo"]
    assert quality["status"] == ("done" if wins else "failed")
    assert "validate_godot_project" in produced["checks"]


def test_preparing_a_blender_script_does_not_claim_meshes_have_been_produced(context):
    _, service, _, _, pool, _, _ = context
    job = execute(service, approve(service, "generate_blender_script"), "generate_blender_script")
    pool.run()
    assert service.get_job("demo", job["job_id"])["status"] == "done"
    stage = next(
        item
        for item in service.workflow_state("demo")["stages"]
        if item["stage_id"] == "blender_modeling"
    )
    assert stage["status"] != "done" and stage["detail"]


def test_blender_output_manifest_path_cannot_be_supplied_by_the_model(context):
    _, service, store, _, pool, _, _ = context
    with pytest.raises(ValueError):
        approve(
            service,
            "generate_blender_script",
            {"import_manifest_path": "generated/asset-approval-manifest.yaml"},
        )
    assert not store.snapshot("demo").jobs and not pool.work


def test_asset_review_and_integration_reach_the_same_durable_human_gate(context):
    _, service, store, _, pool, _, _ = context
    execute(service, approve(service))
    pool.run()
    generated_mesh(store)
    intent = service.request_asset_review("demo", plan_version=1, resource_ids=["objective-mesh"])
    service.apply_asset_review("demo", intent["intent_id"], approved=True)
    reviewed = next(
        item
        for item in service.workflow_state("demo")["stages"]
        if item["stage_id"] == "creative_review"
    )
    assert reviewed["status"] == "done"
    args = {"resource_ids": ["objective-mesh"]}
    execute(
        service,
        approve(service, "copy_approved_godot_assets", args),
        "copy_approved_godot_assets",
        args,
        request_id="integrate",
    )
    pool.run()
    integrated = next(
        item
        for item in service.workflow_state("demo")["stages"]
        if item["stage_id"] == "asset_integration"
    )
    assert integrated["status"] == "done", integrated
    assert integrated["tools"] == ["copy_approved_godot_assets"]


def test_generated_plan_conflict_returns_the_latest_saved_snapshot(context):
    _, service, store, _, _, _, _ = context
    args = {
        "project_id": "demo",
        "plan_version": 1,
        "prompt": "a courier escapes a haunted station",
        "engine_version": "Godot 4",
    }
    assert service.call("generate_game_production_plan", args).status == "ok"
    stale = service.call("generate_game_production_plan", args)
    assert stale.status == "refused"
    assert stale.data["status"] == "version_conflict"
    assert stale.data["latest"]["plan_version"] == 2
    assert store.snapshot("demo").plan_version == 2


def test_godot_checks_select_the_latest_registered_engine_project(context):
    _, service, store, _, pool, _, _ = context
    execute(service, approve(service))
    pool.run()
    second = execute(service, approve(service), request_id="new-project")
    pool.run()
    root = store.production_workspace("demo") / "versions/v1"
    unrelated = root / "generated/godot/000-unregistered/project.godot"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("unregistered project must not be checked", encoding="utf-8")
    actual = next(
        r["path"]
        for r in service.get_job("demo", second["job_id"])["resources"]
        if r["path"].endswith("project.godot")
    )
    checked = service.call("validate_godot_project", {"project_id": "demo", "plan_version": 1})
    assert checked.status == "ok" and checked.data["tool_status"] == "ok", checked
    assert checked.data["validation_report"]["project_file"] == actual.removeprefix("versions/v1/")


def test_job_log_summary_does_not_read_another_tasks_log(context):
    _, service, store, _, pool, _, _ = context
    queued = execute(service, approve(service))
    pool.run()
    foreign = store.production_workspace("demo") / "versions/v1/generated/other-job.log"
    foreign.write_text("another tasks private progress", encoding="utf-8")
    result = service.get_job("demo", queued["job_id"])
    assert result["logs"] == []


def test_visual_preparation_does_not_register_a_prior_expected_image(context):
    from pathlib import Path
    from shutil import copytree

    from fantasy_agent.studio_workflow_evidence import worker_data

    _, service, store, _, pool, _, _ = context
    root = store.production_workspace("demo") / "versions/v1"
    copytree(Path(__file__).resolve().parents[1] / "templates/comfyui", root / "templates/comfyui")
    name = "prepare_visual_reference_workflows"
    first = execute(service, approve(service, name), name)
    pool.run()
    job = next(j for j in store.snapshot("demo").jobs if j.job_id == first["job_id"])
    assert job.status == "done", job.result
    expected = worker_data(job.result)["generated_images"][0]
    old_image = store.production_workspace("demo") / "versions/v1" / expected
    old_image.parent.mkdir(parents=True, exist_ok=True)
    old_image.write_bytes(b"image left by a different production attempt")
    second = execute(service, approve(service, name), name, request_id="new-preparation")
    current_expected = root / expected.replace(first["job_id"], second["job_id"])
    current_expected.parent.mkdir(parents=True, exist_ok=True)
    current_expected.write_bytes(b"pre-existing expected output is not a produced image")
    pool.run()
    result = service.get_job("demo", second["job_id"])
    assert result["status"] == "done", result
    assert not any(item["path"].endswith(".png") for item in result["resources"])


def test_visual_preparation_uses_shipped_templates_without_copying_them_to_the_project(context):
    _, service, _, _, pool, _, _ = context
    name = "prepare_visual_reference_workflows"
    queued = execute(service, approve(service, name), name)
    pool.run()
    result = service.get_job("demo", queued["job_id"])
    assert result["status"] == "done", result
    assert any(item["path"].endswith(".json") for item in result["resources"])


def test_new_external_failure_replaces_an_old_success(context):
    from fantasy_agent.orchestrator import Orchestrator
    from fantasy_agent.tool_registry import ToolOutcome, default_registry

    _, _, store, _, _, _, _ = context
    pipeline = store.snapshot("demo").plan.production_pipeline.model_copy(deep=True)
    stage = next(s for s in pipeline.stages if s.id == "blender_modeling")
    stage.depends_on = []
    registry = default_registry(use_llm=False)
    registry.remember_plan(store.snapshot("demo").plan.model_dump(mode="json"))
    orchestrator = Orchestrator(
        session_id="external-attempts",
        workspace_root=store.production_workspace("demo"),
        registry=registry,
    )
    orchestrator.confirm([stage.id])
    mesh = store.production_workspace("demo") / "mesh.glb"
    mesh.parent.mkdir(parents=True, exist_ok=True)
    mesh.write_bytes(b"first actual mesh")
    first = orchestrator.accept_external_result(
        pipeline,
        stage.id,
        ToolOutcome("generate_blender_script", "ok", "produced"),
        artifacts=[str(mesh)],
    )
    assert first.status == "done"
    second = orchestrator.accept_external_result(
        pipeline,
        stage.id,
        ToolOutcome("generate_blender_script", "error", "new attempt failed"),
        artifacts=[],
    )
    assert second.status == "failed" and second.detail == "new attempt failed"


def test_unreal_creation_and_commandlet_use_the_latest_registered_project(context):
    _, service, store, _, pool, _, _ = context
    name = "create_project_structure"
    first = execute(service, approve(service, name), name)
    pool.run()
    second = execute(service, approve(service, name), name, request_id="second-unreal")
    pool.run()
    first_paths = {r["path"] for r in service.get_job("demo", first["job_id"])["resources"]}
    second_paths = {r["path"] for r in service.get_job("demo", second["job_id"])["resources"]}
    assert first_paths.isdisjoint(second_paths)
    root = store.production_workspace("demo") / "versions/v1"
    foreign = root / "generated/unreal/000-old/Old.uproject"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("{}", encoding="utf-8")
    args = service._bridge_arguments("demo", 1, "run_editor_commandlet", {})
    assert args["commandlet"] == "DataValidation"
    assert args["project_file"] in {p.removeprefix("versions/v1/") for p in second_paths}


def test_unreal_ingest_and_assembly_use_actual_production_manifests(context, monkeypatch):
    from subprocess import CompletedProcess

    from fantasy_agent.blender_mcp import BlenderMCPBridge

    _, service, store, _, pool, _, _ = context
    root = store.production_workspace("demo") / "versions/v1"

    def produce(self, command, **_kwargs):
        from pathlib import Path

        import yaml

        script = Path(command[command.index("--python") + 1])
        manifest = yaml.safe_load(
            script.with_name("import-manifest.yaml").read_text(encoding="utf-8")
        )
        for item in manifest["assets"]:
            mesh = root / item["source_file"]
            mesh.parent.mkdir(parents=True, exist_ok=True)
            mesh.write_bytes(b"expensive renderer output")
        return CompletedProcess(command, 0, "assets produced", "")

    monkeypatch.setattr(BlenderMCPBridge, "_run_tool", produce)
    execute(service, approve(service, "create_project_structure"), "create_project_structure")
    pool.run()
    batch = execute(
        service,
        approve(service, "generate_asset_batch"),
        "generate_asset_batch",
        request_id="assets",
    )
    pool.run()
    generated = service.get_job("demo", batch["job_id"])
    assert generated["status"] == "done", generated
    ids = [r["resource_id"] for r in generated["resources"] if r["kind"] == "asset"]
    assert ids
    review = service.request_asset_review("demo", plan_version=1, resource_ids=ids)
    service.apply_asset_review("demo", review["intent_id"], approved=True)
    for name in ("prepare_asset_ingest", "prepare_level_assembly"):
        task = execute(service, approve(service, name), name, request_id=name)
        pool.run()
        result = service.get_job("demo", task["job_id"])
        assert result["status"] == "done", (name, result["blockers"], result["result"])
    for name in ("validate_asset_ingest", "validate_level_assembly"):
        result = service.call(
            name,
            {"project_id": "demo", "plan_version": 1, "require_imported_assets": False}
            if name == "validate_level_assembly"
            else {"project_id": "demo", "plan_version": 1},
        )
        assert result.status == "ok" and result.data["tool_status"] == "ok", result
    ingest = service._bridge_arguments("demo", 1, "run_asset_ingest", {})
    assembly = service._bridge_arguments("demo", 1, "run_level_assembly", {})
    assert (root / ingest["import_script_path"]).is_file()
    assert (root / assembly["assembly_script_path"]).is_file()
    assert ingest["project_file"] == assembly["project_file"]


def test_new_asset_attempt_invalidates_the_approved_dependents(context):
    _, service, store, _, pool, _, _ = context
    execute(service, approve(service))
    pool.run()
    generated_mesh(store)
    review = service.request_asset_review("demo", plan_version=1, resource_ids=["objective-mesh"])
    service.apply_asset_review("demo", review["intent_id"], approved=True)
    args = {"resource_ids": ["objective-mesh"]}
    execute(
        service,
        approve(service, "copy_approved_godot_assets", args),
        "copy_approved_godot_assets",
        args,
        request_id="copy",
    )
    pool.run()
    execute(
        service,
        approve(service, "generate_blender_script"),
        "generate_blender_script",
        request_id="new-assets",
    )
    orchestrator = service._orchestrator("demo", 1, register=True)
    pipeline = service.workflow_pipeline("demo", 1)
    assert orchestrator.outcomes["asset_integration"].status == "done"
    orchestrator.begin_external_attempt(pipeline, ["blender_modeling"])
    state = service.workflow_state("demo")
    assert (
        next(s for s in state["stages"] if s["stage_id"] == "asset_integration")["status"] != "done"
    )
    assert "creative_review" in state["pending_human_gates"]
    assert (
        next(s for s in state["stages"] if s["stage_id"] == "godot_quick_play")["status"] == "done"
    )


def test_failed_worker_surfaces_actual_blockers_and_a_next_step(context, monkeypatch):
    _, service, _, _, pool, _, _ = context
    task = execute(service, approve(service))
    monkeypatch.setattr(
        service, "_run", lambda *a, **k: (_ for _ in ()).throw(ValueError("真实模板损坏"))
    )
    pool.run()
    result = service.get_job("demo", task["job_id"])
    assert result["status"] == "failed"
    assert "真实模板损坏" in result["blockers"]
    assert result["next_actions"]


@pytest.mark.parametrize(
    "kind,folder", [("artifact", "v1"), ("asset", "v2")], ids=["artifact-v1", "asset-v2"]
)
def test_asset_review_intent_refuses_nonassets_and_wrong_version_paths(context, kind, folder):
    import hashlib

    _, service, store, _, _, _, _ = context
    root = store.production_workspace("demo")
    path = root / "versions" / folder / "generated/assets/mesh.glb"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"mesh content")
    store.register_resource(
        "demo",
        resource_id="bad-subject",
        path=path.relative_to(root).as_posix(),
        kind=kind,
        plan_version=1,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    with pytest.raises(ValueError):
        service.request_asset_review("demo", plan_version=1, resource_ids=["bad-subject"])
    assert not store.snapshot("demo").decisions


def test_local_ingest_registers_the_version_scoped_library_copy(context, tmp_path):
    _, service, _, _, pool, _, _ = context
    source = tmp_path / "local.png"
    source.write_bytes(b"existing local artwork")
    args = {"name": "本机参考", "source_path": str(source)}
    task = execute(service, approve(service, "ingest_asset", args), "ingest_asset", args)
    pool.run()
    result = service.get_job("demo", task["job_id"])
    assert result["status"] == "done", result
    assert any(
        ref["kind"] == "asset" and ref["path"].startswith("versions/v1/")
        for ref in result["resources"]
    )
    assert source.read_bytes() == b"existing local artwork"


def test_mcp_ingest_and_review_share_the_project_asset_panel(context, tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    from apps.studio.app import main

    _, service, store, _, pool, _, _ = context
    source = tmp_path / "shared-reference.png"
    source.write_bytes(b"local artwork reviewed by the user")
    args = {"name": "本项目参考", "source_path": str(source)}
    task = execute(service, approve(service, "ingest_asset", args), "ingest_asset", args)
    pool.run()
    resources = service.get_job("demo", task["job_id"])["resources"]
    intent = service.request_asset_review(
        "demo", plan_version=1, resource_ids=[resources[0]["resource_id"]]
    )
    service.apply_asset_review("demo", intent["intent_id"], approved=True)
    monkeypatch.setattr(main, "REPO_ROOT", store.workspace_root)
    monkeypatch.setattr(main.app.state, "workflow_service", service, raising=False)
    client = TestClient(main.app, client=("127.0.0.1", 1234))
    try:
        response = client.get("/api/assets?project_id=demo&plan_version=1")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["entries"][0]["name"] == "本项目参考"
        assert payload["generated"][0]["status"] == "approved"
        assert payload["generated"][0]["sha256"] == resources[0]["sha256"]
        assert client.get("/api/assets").json()["entries"] == []
    finally:
        client.close()


def test_completed_job_logs_survive_a_later_import_of_the_same_project(context, monkeypatch):
    from subprocess import CompletedProcess

    from fantasy_agent.godot_mcp import GodotMCPBridge

    _, service, _, _, pool, _, _ = context
    execute(service, approve(service))
    pool.run()
    messages = iter(["first import log", "second import log"])
    monkeypatch.setattr(
        GodotMCPBridge,
        "_run_tool",
        lambda self, command, **kwargs: CompletedProcess(command, 0, next(messages), ""),
    )
    first = execute(
        service, approve(service, "run_godot_import"), "run_godot_import", request_id="import-one"
    )
    pool.run()
    second = execute(
        service, approve(service, "run_godot_import"), "run_godot_import", request_id="import-two"
    )
    pool.run()
    assert "first import log" in service.get_job("demo", first["job_id"])["logs"]
    assert "second import log" in service.get_job("demo", second["job_id"])["logs"]


def test_cancelled_import_keeps_its_logs_after_a_later_import(context, monkeypatch):
    from subprocess import CompletedProcess

    from fantasy_agent.godot_mcp import GodotMCPBridge
    from fantasy_agent.process_runner import ProcessCancelled

    _, service, _, _, pool, _, _ = context
    execute(service, approve(service))
    pool.run()
    first = {}
    calls = []

    def interrupted_tool(self, command, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["stdout_path"].write_text("FIRST cancelled import output", encoding="utf-8")
            kwargs["stderr_path"].write_text("FIRST cancelled diagnostic", encoding="utf-8")
            service.cancel_job("demo", first["job_id"])
            raise ProcessCancelled(
                command, output="FIRST cancelled import output", stderr="FIRST cancelled diagnostic"
            )
        return CompletedProcess(command, 0, "SECOND completed import output", "")

    monkeypatch.setattr(GodotMCPBridge, "_run_tool", interrupted_tool)
    first.update(
        execute(
            service,
            approve(service, "run_godot_import"),
            "run_godot_import",
            request_id="cancelled-import",
        )
    )
    pool.run()
    cancelled = service.get_job("demo", first["job_id"])
    assert cancelled["status"] == "cancelled"
    assert "FIRST cancelled import output" in cancelled["logs"]
    second = execute(
        service,
        approve(service, "run_godot_import"),
        "run_godot_import",
        request_id="after-cancel-import",
    )
    pool.run()
    assert service.get_job("demo", second["job_id"])["status"] == "done"
    assert "FIRST cancelled import output" in service.get_job("demo", first["job_id"])["logs"]
    assert "FIRST cancelled diagnostic" in service.get_job("demo", first["job_id"])["logs"]


def test_an_asset_worker_cannot_relabel_old_files_as_new_output(context, monkeypatch):
    from subprocess import CompletedProcess

    from fantasy_agent.blender_mcp import BlenderMCPBridge

    _, service, store, _, pool, _, _ = context
    root = store.production_workspace("demo") / "versions/v1"
    for item in store.snapshot("demo").plan.blender_plan.jobs:
        old = root / item.export_path
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_bytes(b"unrelated previous output")
    monkeypatch.setattr(
        BlenderMCPBridge,
        "_run_tool",
        lambda self, command, **kwargs: CompletedProcess(
            command, 0, "returned without producing files", ""
        ),
    )
    task = execute(service, approve(service, "generate_asset_batch"), "generate_asset_batch")
    pool.run()
    result = service.get_job("demo", task["job_id"])
    assert result["status"] == "failed", result
    assert result["blockers"]
    assert not any(ref["kind"] == "asset" for ref in result["resources"])


@pytest.mark.parametrize("name", ["LLM-API.JSON", "MCP-CONNECTION.JSON", "mcp-settings.json."])
def test_private_configuration_aliases_cannot_be_ingested(context, tmp_path, name):
    _, service, store, _, pool, _, _ = context
    source = tmp_path / name
    source.write_text('{"api_key":"private configuration"}', encoding="utf-8")
    with pytest.raises(ValueError):
        approve(service, "ingest_asset", {"name": "configuration", "source_path": str(source)})
    assert not pool.work and not store.snapshot("demo").jobs


def test_resource_configuration_directory_alias_is_not_readable(context):
    _, service, store, _, _, _, _ = context
    root = store.production_workspace("demo")
    source = root / "versions/v1/CONFIG/other.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"private":"configuration"}', encoding="utf-8")
    store.register_resource(
        "demo", resource_id="config-alias", path=source.relative_to(root).as_posix()
    )
    with pytest.raises(ValueError):
        service.read_resource("demo", "config-alias")


def test_expired_rework_requires_explicit_new_authorization_and_preserves_its_session(
    context, monkeypatch
):
    from dataclasses import dataclass

    mod, service, store, _, pool, _, now = context
    seen = []

    @dataclass
    class Finished:
        status: str = "done"

    monkeypatch.setattr(mod, "launch_demo", lambda request: (seen.append(request), Finished())[1])
    original = execute(service, approve(service, "execute_demo"), "execute_demo")
    pool.run()
    now[0] += 101
    refused = service.call(
        "rework_node",
        {
            "project_id": "demo",
            "plan_version": 1,
            "job_id": original["job_id"],
            "resume_from": "validate",
        },
    )
    assert refused.status != "ok" and not pool.work
    new_grant = approve(service, "execute_demo")
    resumed = service.call(
        "rework_node",
        {
            "project_id": "demo",
            "plan_version": 1,
            "job_id": original["job_id"],
            "resume_from": "validate",
            "grant_id": new_grant,
        },
    )
    assert resumed.status == "ok", resumed
    pool.run()
    assert seen[-1].session_id == seen[0].session_id
    assert seen[-1].resume_from == "validate"
    assert store.snapshot("demo").jobs[-1].grant_id == new_grant
    assert store.snapshot("demo").jobs[-1].rework is True


def test_new_authorization_keeps_cross_grant_rework_bounded(context, monkeypatch):
    from dataclasses import dataclass

    mod, service, _, _, pool, _, now = context

    @dataclass
    class Finished:
        status: str = "done"

    monkeypatch.setattr(mod, "launch_demo", lambda request: Finished())
    original = execute(service, approve(service, "execute_demo"), "execute_demo")
    pool.run()
    now[0] += 101
    new_grant = approve(service, "execute_demo")
    for index in range(3):
        outcome = service.call(
            "rework_node",
            {
                "project_id": "demo",
                "plan_version": 1,
                "job_id": original["job_id"],
                "resume_from": "import",
                "grant_id": new_grant,
                "request_id": f"renewed-{index}",
            },
        )
        assert outcome.status == "ok", outcome
        pool.run()
    denied = service.call(
        "rework_node",
        {
            "project_id": "demo",
            "plan_version": 1,
            "job_id": original["job_id"],
            "resume_from": "import",
            "grant_id": new_grant,
            "request_id": "renewed-fourth",
        },
    )
    assert denied.status != "ok" and not pool.work
