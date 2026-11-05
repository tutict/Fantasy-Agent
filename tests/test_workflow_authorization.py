"""Authorization cannot become execution merely by supplying an id."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module, util

import pytest

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.workflows import run_director_workflow


def setup_store(tmp_path):
    assert util.find_spec("fantasy_agent.workflow_authorization") is not None, (
        "bounded server authorization is not implemented"
    )
    mod = import_module("fantasy_agent.workflow_authorization")
    projects = import_module("fantasy_agent.studio_projects").StudioProjectStore(tmp_path)
    plan = run_director_workflow(PromptRequest(prompt="courier escape"), use_llm=False)
    projects.create("demo", project_id="demo", plan=plan)
    now = [1000.0]
    auth = mod.WorkflowAuthorizationStore(projects, clock=lambda: now[0])
    action = mod.WorkflowAction(
        tool_name="build_godot", arguments={"quality": "greybox"}, node_id="godot"
    )
    return mod, projects, auth, action, now


def issue(auth, action, **kwargs):
    return auth.issue("demo", plan_version=1, actions=[action], **kwargs)


def claim(auth, grant, action, request_id="request-1", **kwargs):
    return auth.claim(
        "demo",
        grant_id=grant.grant_id,
        plan_version=1,
        request_id=request_id,
        action=action,
        **kwargs,
    )


def test_claim_persists_job_before_start_and_restart_never_replays(tmp_path):
    mod, projects, auth, action, now = setup_store(tmp_path)
    grant = issue(auth, action)
    assert grant.issued_at == 1000
    assert grant.expires_at == 2800
    first = claim(auth, grant, action)
    assert first.reused is False
    assert first.job.status == "queued"
    fresh = mod.WorkflowAuthorizationStore(projects, clock=lambda: now[0])
    second = claim(fresh, grant, action)
    assert second.reused is True
    assert second.job.job_id == first.job.job_id
    assert fresh.start_job("demo", first.job.job_id) is True
    assert fresh.start_job("demo", first.job.job_id) is False
    assert fresh.projects.snapshot("demo").jobs[0].status == "running"
    projects.mark_interrupted_jobs("demo")
    restored = claim(fresh, grant, action)
    assert restored.reused is True
    assert restored.job.status == "interrupted"
    assert fresh.start_job("demo", first.job.job_id) is False


def test_same_action_cannot_be_executed_twice_under_new_request(tmp_path):
    _, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    first = claim(auth, grant, action)
    duplicate = claim(auth, grant, action, request_id="request-2")
    assert duplicate.reused is True
    assert duplicate.job.job_id == first.job.job_id
    assert len(projects.snapshot("demo").jobs) == 1
    projects.update_job("demo", first.job.job_id, status="cancelled")
    assert claim(auth, grant, action).job.status == "cancelled"
    assert claim(auth, grant, action, request_id="request-3").job.status == "cancelled"
    assert auth.start_job("demo", first.job.job_id) is False


def test_request_id_reuse_with_different_content_is_rejected(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    claim(auth, grant, action)
    altered = action.model_copy(deep=True)
    altered.arguments["quality"] = "polished"
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, altered)
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, rework=True)
    assert len(projects.snapshot("demo").jobs) == 1


@pytest.mark.parametrize("change", ["missing", "tool", "arguments", "version", "path", "expired"])
def test_grant_scope_is_revalidated_for_every_claim(tmp_path, change):
    mod, projects, auth, action, now = setup_store(tmp_path)
    grant = issue(auth, action, allowed_asset_paths=["generated/assets/a.fbx"])
    kwargs = {"asset_paths": ["generated/assets/a.fbx"]}
    if change == "missing":
        grant.grant_id = "forged"
    elif change == "tool":
        action.tool_name = "run_blender"
    elif change == "arguments":
        action.arguments["quality"] = "polished"
    elif change == "version":
        projects.update_plan("demo", projects.snapshot("demo").plan, expected_version=1)
    elif change == "path":
        kwargs["asset_paths"] = ["generated/assets/b.fbx"]
    elif change == "expired":
        now[0] = 2800.0
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, **kwargs)
    assert projects.snapshot("demo").jobs == []


def test_even_idempotent_reuse_rechecks_expiry_and_current_version(tmp_path):
    mod, projects, auth, action, now = setup_store(tmp_path)
    grant = issue(auth, action, ttl_seconds=10)
    claim(auth, grant, action)
    now[0] = 1010
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action)
    now[0] = 1001
    projects.update_plan("demo", projects.snapshot("demo").plan, expected_version=1)
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action)


def test_explicit_node_rework_is_bounded_to_three_additional_attempts(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    claim(auth, grant, action)
    for n in range(3):
        claim(auth, grant, action, request_id=f"rework-{n}", rework=True)
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, request_id="rework-4", rework=True)
    assert len(projects.snapshot("demo").jobs) == 4


def test_rework_requires_a_prior_normal_claim_and_explicit_node(tmp_path):
    mod, _, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, rework=True)
    action.node_id = ""
    grant = issue(auth, action)
    claim(auth, grant, action)
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, request_id="retry", rework=True)


@pytest.mark.parametrize("ttl", [0, -1, 1801, float("inf"), float("nan")])
def test_authorization_duration_cannot_expand_budget(tmp_path, ttl):
    _, _, auth, action, _ = setup_store(tmp_path)
    with pytest.raises(ValueError):
        issue(auth, action, ttl_seconds=ttl)


@pytest.mark.parametrize("limit", [-1, 4, True])
def test_rework_limit_cannot_expand_budget(tmp_path, limit):
    _, _, auth, action, _ = setup_store(tmp_path)
    with pytest.raises(ValueError):
        issue(auth, action, max_reworks=limit)


def test_parameters_and_paths_have_deterministic_normalization(tmp_path):
    mod, _, auth, _, _ = setup_store(tmp_path)
    action = mod.WorkflowAction(tool_name="import", arguments={"b": 2, "a": {"x": 1}})
    grant = issue(auth, action, allowed_asset_paths=["generated\\assets\\a.fbx"])
    reordered = mod.WorkflowAction(tool_name="import", arguments={"a": {"x": 1}, "b": 2})
    first = claim(auth, grant, reordered, asset_paths=["generated/assets/a.fbx"])
    assert first.job.asset_paths == [str((tmp_path / "generated/assets/a.fbx").resolve())]
    assert claim(auth, grant, action, asset_paths=["generated\\assets\\a.fbx"]).reused


def test_concurrent_duplicate_claims_register_only_one_job(tmp_path):
    _, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: claim(auth, grant, action), range(8)))
    assert len({c.job.job_id for c in results}) == 1
    assert sum(not c.reused for c in results) == 1
    assert len(projects.snapshot("demo").jobs) == 1


def test_failed_atomic_claim_consumes_nothing_and_registers_no_job(tmp_path, monkeypatch):
    _, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    module = import_module("fantasy_agent.studio_projects")
    real_write = module.write_atomic

    def refused(*args, **kwargs):
        raise OSError("publish refused")

    monkeypatch.setattr(module, "write_atomic", refused)
    with pytest.raises(OSError):
        claim(auth, grant, action)
    assert projects.snapshot("demo").jobs == []
    monkeypatch.setattr(module, "write_atomic", real_write)
    assert claim(auth, grant, action).reused is False


def test_corrupted_grant_fails_loudly_without_a_job(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    path = projects.record_path("demo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["grants"][grant.grant_id]["expires_at"] = "unbounded"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action)


def test_job_terminal_result_and_execution_time_survive_file_reload(tmp_path):
    _, projects, auth, action, _ = setup_store(tmp_path)
    first = claim(auth, issue(auth, action), action)
    auth.start_job("demo", first.job.job_id)
    projects.update_job(
        "demo", first.job.job_id, status="done", result={"passed": True}, session_id="run-1"
    )
    loaded = (
        import_module("fantasy_agent.studio_projects").StudioProjectStore(tmp_path).snapshot("demo")
    )
    assert loaded.jobs[0].started_at == 1000
    assert loaded.jobs[0].finished_at is not None
    assert loaded.jobs[0].result == {"passed": True}
    assert loaded.sessions == ["run-1"]


@pytest.mark.parametrize("change", ["expiry", "version"])
def test_queue_delay_cannot_start_after_authorization_becomes_invalid(tmp_path, change):
    mod, projects, auth, action, now = setup_store(tmp_path)
    first = claim(auth, issue(auth, action), action)
    if change == "expiry":
        now[0] = 2800
    else:
        projects.update_plan("demo", projects.snapshot("demo").plan, expected_version=1)
    with pytest.raises(mod.AuthorizationError):
        auth.start_job("demo", first.job.job_id)
    assert projects.snapshot("demo").jobs[0].status == "queued"


def test_narrower_duration_and_rework_budget_are_enforced_after_reload(tmp_path):
    mod, projects, auth, action, now = setup_store(tmp_path)
    grant = issue(auth, action, ttl_seconds=20, max_reworks=1)
    claim(auth, grant, action)
    restarted = mod.WorkflowAuthorizationStore(projects, clock=lambda: now[0])
    claim(restarted, grant, action, request_id="retry-1", rework=True)
    assert claim(restarted, grant, action, request_id="retry-1", rework=True).reused
    with pytest.raises(mod.AuthorizationError):
        claim(restarted, grant, action, request_id="retry-2", rework=True)
    now[0] = 1020
    with pytest.raises(mod.AuthorizationError):
        claim(restarted, grant, action)


def test_a_grant_from_another_project_or_version_is_refused(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    projects.create("other", project_id="other", plan=projects.snapshot("demo").plan)
    with pytest.raises(mod.AuthorizationError):
        auth.claim(
            "other", grant_id=grant.grant_id, plan_version=1, request_id="request", action=action
        )
    with pytest.raises(mod.AuthorizationError):
        auth.claim(
            "demo", grant_id=grant.grant_id, plan_version=2, request_id="request", action=action
        )
    assert projects.snapshot("other").jobs == []


def test_issue_requires_current_saved_plan_and_never_accepts_boolean_confirmation(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    projects.create("empty", project_id="empty")
    with pytest.raises(mod.AuthorizationError):
        auth.issue("empty", plan_version=0, actions=[action])
    with pytest.raises(mod.AuthorizationError):
        auth.issue("demo", plan_version=99, actions=[action])
    with pytest.raises(TypeError):
        issue(auth, action, confirmed=True)


def test_public_snapshot_excludes_grants_and_refusals_do_not_echo_parameters(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    action.arguments["extra"] = "secret-connection-value"
    with pytest.raises(mod.AuthorizationError) as caught:
        claim(auth, grant, action)
    assert "secret-connection-value" not in str(caught.value)
    assert "grants" not in projects.snapshot("demo").model_dump()


def test_multiple_actions_on_the_same_node_share_the_rework_budget(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    other = mod.WorkflowAction(tool_name="import_godot", node_id="godot")
    grant = auth.issue("demo", plan_version=1, actions=[action, other])
    claim(auth, grant, action)
    claim(auth, grant, other, request_id="import-1")
    claim(auth, grant, action, request_id="retry-build-1", rework=True)
    claim(auth, grant, other, request_id="retry-import-1", rework=True)
    claim(auth, grant, action, request_id="retry-build-2", rework=True)
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, other, request_id="retry-import-2", rework=True)
    assert len(projects.snapshot("demo").jobs) == 5


def test_missing_grant_ledger_with_surviving_production_jobs_is_corruption(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    claim(auth, issue(auth, action), action)
    path = projects.record_path("demo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["grants"] = {}
    path.write_text(json.dumps(payload), encoding="utf-8")
    project_error = import_module("fantasy_agent.studio_projects").ProjectStoreError
    with pytest.raises(project_error):
        projects.snapshot("demo")
    with pytest.raises(mod.AuthorizationError):
        auth.start_job("demo", next(iter(payload["jobs"])))


def test_invalid_issuance_errors_never_echo_action_parameters(tmp_path):
    _, _, auth, action, _ = setup_store(tmp_path)
    action.arguments["extra"] = "secret-connection-value"
    with pytest.raises(ValueError) as caught:
        auth.issue("demo", plan_version=1, actions=[action, action])
    assert "secret-connection-value" not in str(caught.value)


def test_explicit_external_local_asset_is_allowed_but_another_source_is_refused(tmp_path):
    mod, projects, auth, action, _ = setup_store(tmp_path / "studio")
    source = tmp_path / "downloaded.fbx"
    source.write_bytes(b"local asset")
    other = tmp_path / "other.fbx"
    other.write_bytes(b"different local asset")
    grant = issue(auth, action, allowed_asset_paths=[str(source)])
    first = claim(auth, grant, action, asset_paths=[str(source)])
    assert first.job.asset_paths == [str(source.resolve())]
    assert auth.start_job("demo", first.job.job_id) is True
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, request_id="different-source", asset_paths=[str(other)])
    assert len(projects.snapshot("demo").jobs) == 1
    project_error = import_module("fantasy_agent.path_safety").WorkspacePathError
    with pytest.raises(project_error):
        projects.register_resource("demo", resource_id="external-output", path=str(source))


@pytest.mark.parametrize(
    "source", ["https://example.test/a.fbx", "file:///C:/a.fbx", "\\\\server\\share\\a.fbx"]
)
def test_asset_input_rejects_urls_and_network_sources(tmp_path, source):
    mod, _, auth, action, _ = setup_store(tmp_path)
    with pytest.raises(mod.AuthorizationError):
        issue(auth, action, allowed_asset_paths=[source])


class _ObservedLock:
    """Observe the acquire attempt while retaining the real shared RLock."""

    def __init__(self, lock, attempted):
        self.lock = lock
        self.attempted = attempted

    def __enter__(self):
        self.attempted.set()
        return self.lock.__enter__()

    def __exit__(self, *args):
        return self.lock.__exit__(*args)


@pytest.mark.parametrize("operation", ["issue", "claim", "start"])
def test_authorization_reads_clock_after_waiting_for_the_real_lock(tmp_path, operation):
    mod, projects, auth, action, now = setup_store(tmp_path)
    grant = issue(auth, action, ttl_seconds=5)
    job = claim(auth, grant, action).job if operation == "start" else None
    original_lock = projects._lock
    attempted = threading.Event()
    projects._lock = _ObservedLock(original_lock, attempted)

    def invoke():
        if operation == "issue":
            return issue(auth, action, ttl_seconds=5)
        if operation == "claim":
            return claim(auth, grant, action)
        return auth.start_job("demo", job.job_id)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with original_lock:
            future = pool.submit(invoke)
            assert attempted.wait(timeout=5), "worker never attempted the real lock"
            now[0] = 1005
        if operation == "issue":
            new_grant = future.result(timeout=5)
            assert new_grant.issued_at == 1005
            assert new_grant.expires_at == 1010
        else:
            with pytest.raises(mod.AuthorizationError):
                future.result(timeout=5)
    if operation == "start":
        assert projects.snapshot("demo").jobs[0].status == "queued"
    elif operation == "claim":
        assert projects.snapshot("demo").jobs == []


def test_authorization_reads_clock_after_the_record_has_loaded(tmp_path, monkeypatch):
    mod, projects, auth, action, now = setup_store(tmp_path)
    first = claim(auth, issue(auth, action, ttl_seconds=5), action)
    original_load = projects._load

    def load_then_advance(project_id):
        record = original_load(project_id)
        now[0] = 1005
        return record

    monkeypatch.setattr(projects, "_load", load_then_advance)
    with pytest.raises(mod.AuthorizationError):
        auth.start_job("demo", first.job.job_id)
    assert projects.snapshot("demo").jobs[0].status == "queued"


@pytest.mark.parametrize(
    "damage", ["missing_entry", "missing_ledger", "misdirected", "empty_original_id"]
)
def test_damaged_original_rework_request_mapping_is_rejected_not_rebuilt(tmp_path, damage):
    mod, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    first = claim(auth, grant, action)
    retry = claim(auth, grant, action, request_id="retry", rework=True)
    path = projects.record_path("demo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if damage == "missing_entry":
        del payload["request_jobs"]["retry"]
    elif damage == "missing_ledger":
        del payload["request_jobs"]
    elif damage == "misdirected":
        payload["request_jobs"]["retry"] = first.job.job_id
    else:
        payload["jobs"][retry.job.job_id]["request_id"] = ""
    damaged = json.dumps(payload)
    path.write_text(damaged, encoding="utf-8")
    project_error = import_module("fantasy_agent.studio_projects").ProjectStoreError
    with pytest.raises(project_error):
        projects.snapshot("demo")
    with pytest.raises(mod.AuthorizationError):
        claim(auth, grant, action, request_id="retry", rework=True)
    assert path.read_text(encoding="utf-8") == damaged


def test_request_alias_cannot_reference_an_unapproved_background_job(tmp_path):
    _, projects, auth, action, _ = setup_store(tmp_path)
    claim(auth, issue(auth, action), action)
    projects.register_job("demo", job_id="background", plan_version=1, tool_name="validate")
    path = projects.record_path("demo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["request_jobs"]["alias"] = "background"
    path.write_text(json.dumps(payload), encoding="utf-8")
    project_error = import_module("fantasy_agent.studio_projects").ProjectStoreError
    with pytest.raises(project_error):
        projects.snapshot("demo")


@pytest.mark.parametrize(
    "arguments",
    [
        {"connection_token": "credential-sentinel"},
        {"connectionToken": "credential-sentinel"},
        {"nested": [{"Authorization": "credential-sentinel"}]},
        {"api_key": "credential-sentinel"},
        {"connection": {"token": "credential-sentinel"}},
    ],
)
def test_action_parameters_cannot_carry_connection_credentials(tmp_path, arguments):
    mod, projects, _, _, _ = setup_store(tmp_path)
    with pytest.raises(ValueError) as rejected_action:
        mod.WorkflowAction(tool_name="build", arguments=arguments)
    assert "credential-sentinel" not in str(rejected_action.value)
    with pytest.raises(ValueError) as rejected_job:
        projects.register_job(
            "demo", job_id="bad", plan_version=1, tool_name="build", arguments=arguments
        )
    assert "credential-sentinel" not in str(rejected_job.value)
    assert projects.snapshot("demo").jobs == []


def test_completed_job_public_result_excludes_credentials_and_keeps_gameplay_flags(tmp_path):
    mod, projects, auth, _, _ = setup_store(tmp_path)
    action = mod.WorkflowAction(
        tool_name="build",
        arguments={
            "confirmed_side_effects": False,
            "quality": "greybox",
            "token_count": 3,
        },
    )
    first = claim(auth, issue(auth, action), action)
    auth.start_job("demo", first.job.job_id)
    finished = projects.update_job(
        "demo",
        first.job.job_id,
        status="done",
        result={
            "connection_token": "credential-sentinel",
            "nested": [{"accessToken": "credential-sentinel", "score": 7}],
            "confirmed": False,
        },
    )
    snapshot = projects.snapshot("demo")
    for job in (finished, snapshot.jobs[0]):
        assert "credential-sentinel" not in job.model_dump_json()
        assert job.result == {"nested": [{"score": 7}], "confirmed": False}
        assert job.arguments == {
            "confirmed_side_effects": False,
            "quality": "greybox",
            "token_count": 3,
        }
    assert "credential-sentinel" not in projects.record_path("demo").read_text(encoding="utf-8")


@pytest.mark.parametrize("reader", ["snapshot", "claim"])
def test_legacy_result_credentials_are_removed_from_every_public_job_projection(tmp_path, reader):
    _, projects, auth, action, _ = setup_store(tmp_path)
    grant = issue(auth, action)
    first = claim(auth, grant, action)
    path = projects.record_path("demo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["jobs"][first.job.job_id]["result"] = {
        "connection": {"token": "credential-sentinel", "duration": 1},
        "score": 7,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    job = (
        projects.snapshot("demo").jobs[0]
        if reader == "snapshot"
        else claim(auth, grant, action).job
    )
    assert "credential-sentinel" not in job.model_dump_json()
    assert job.result == {"connection": {"duration": 1}, "score": 7}
