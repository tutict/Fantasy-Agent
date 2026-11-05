"""Real-file contracts for persistent Studio projects."""

import json
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module, util

import pytest

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.path_safety import WorkspacePathError
from fantasy_agent.workflows import run_director_workflow


@pytest.fixture
def plan():
    return run_director_workflow(
        PromptRequest(prompt="a courier escapes a haunted station"), use_llm=False
    )


def project_module():
    assert util.find_spec("fantasy_agent.studio_projects") is not None, (
        "persistent Studio projects are not implemented"
    )
    return import_module("fantasy_agent.studio_projects")


def test_empty_projects_round_trip_independent_snapshots(tmp_path):
    mod = project_module()
    store = mod.StudioProjectStore(tmp_path)
    assert store.list_projects() == []
    assert store.snapshot("missing") is None
    created = store.create("我的项目", project_id="demo")
    assert created.plan_version == 0
    assert created.plan is None
    created.sessions.append("fake")
    loaded = mod.StudioProjectStore(tmp_path).snapshot("demo")
    assert loaded.name == "我的项目"
    assert loaded.sessions == []
    assert [p.project_id for p in store.list_projects()] == ["demo"]


def test_plan_versions_are_validated_immutable_and_cas_checked(tmp_path, plan):
    mod = project_module()
    store = mod.StudioProjectStore(tmp_path)
    store.create("demo", project_id="demo")
    first = store.update_plan("demo", plan, expected_version=0)
    second_plan = plan.model_copy(deep=True)
    second_plan.gameplay_spec.title = "Second"
    second = store.update_plan("demo", second_plan, expected_version=1)
    assert (first.plan_version, second.plan_version) == (1, 2)
    assert store.snapshot("demo", plan_version=1).plan.gameplay_spec.title != "Second"
    second.plan.gameplay_spec.title = "caller mutation"
    assert store.snapshot("demo").plan.gameplay_spec.title == "Second"
    with pytest.raises(mod.ProjectVersionConflict) as caught:
        store.update_plan("demo", plan, expected_version=1)
    assert caught.value.latest.plan_version == 2
    with pytest.raises(ValueError):
        store.update_plan("demo", {"not": "a plan"}, expected_version=2)
    assert store.snapshot("demo").plan_version == 2
    assert store.snapshot("demo", plan_version=99) is None


def test_same_root_instances_cas_only_one_concurrent_writer(tmp_path, plan):
    mod = project_module()
    mod.StudioProjectStore(tmp_path).create("demo", project_id="demo", plan=plan)

    def update(_):
        try:
            return (
                mod.StudioProjectStore(tmp_path)
                .update_plan("demo", plan, expected_version=1)
                .plan_version
            )
        except mod.ProjectVersionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(update, range(8)))
    assert results.count(2) == 1
    assert results.count("conflict") == 7


def test_legacy_import_is_once_even_when_concurrent_or_plan_changes(tmp_path, plan):
    mod = project_module()
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(
            pool.map(lambda _: mod.StudioProjectStore(tmp_path).import_legacy(plan), range(5))
        )
    assert len({p.project_id for p in results}) == 1
    changed = plan.model_copy(deep=True)
    changed.gameplay_spec.title = "Changed handoff"
    imported = mod.StudioProjectStore(tmp_path).import_legacy(changed)
    assert imported.plan.gameplay_spec.title != "Changed handoff"
    assert len(mod.StudioProjectStore(tmp_path).list_projects()) == 1


def test_jobs_pin_history_and_concurrent_registration_keeps_all_jobs(tmp_path, plan):
    mod = project_module()
    store = mod.StudioProjectStore(tmp_path)
    store.create("demo", project_id="demo", plan=plan)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(
            pool.map(
                lambda n: mod.StudioProjectStore(tmp_path).register_job(
                    "demo",
                    job_id=f"job-{n}",
                    plan_version=1,
                    tool_name="validate",
                    session_id=f"session-{n}",
                ),
                range(6),
            )
        )
    store.update_plan("demo", plan, expected_version=1)
    loaded = mod.StudioProjectStore(tmp_path).snapshot("demo")
    assert len(loaded.jobs) == 6
    assert len(loaded.sessions) == 6
    assert {j.plan_version for j in loaded.jobs} == {1}
    with pytest.raises(ValueError):
        store.register_job("demo", job_id="no-version", plan_version=9, tool_name="x")


def test_resources_stay_in_the_project_production_workspace(tmp_path):
    mod = project_module()
    store = mod.StudioProjectStore(tmp_path)
    store.create("demo", project_id="demo")
    root = store.production_workspace("demo")
    assert root == tmp_path / "generated/studio/projects/demo/workspace"
    store.register_resource(
        "demo", resource_id="asset", path="generated/assets/a.fbx", kind="asset"
    )
    loaded = store.snapshot("demo")
    assert loaded.resources[0].path == "generated/assets/a.fbx"
    loaded.resources[0].path = "changed"
    assert store.snapshot("demo").resources[0].path == "generated/assets/a.fbx"
    with pytest.raises(WorkspacePathError):
        store.register_resource("demo", resource_id="escape", path="../outside", kind="asset")
    with pytest.raises(WorkspacePathError):
        store.register_resource(
            "demo", resource_id="escape", path=str(tmp_path / "outside"), kind="asset"
        )


@pytest.mark.parametrize("bad_id", ["victim.", "victim ", "../outside", "a\nb", ""])
def test_project_identifiers_are_safe_segments(tmp_path, bad_id):
    with pytest.raises(WorkspacePathError):
        project_module().StudioProjectStore(tmp_path).create("demo", project_id=bad_id)


@pytest.mark.parametrize("content", [b"{half", b"[]", b"\xff", b'{"project_id":"another"}'])
def test_corrupt_projects_fail_loudly_instead_of_looking_missing(tmp_path, content):
    mod = project_module()
    store = mod.StudioProjectStore(tmp_path)
    store.create("demo", project_id="demo")
    store.record_path("demo").write_bytes(content)
    with pytest.raises(mod.ProjectStoreError):
        store.snapshot("demo")
    with pytest.raises(mod.ProjectStoreError):
        store.list_projects()


def test_atomic_publish_failure_keeps_old_plan(tmp_path, plan, monkeypatch):
    mod = project_module()
    store = mod.StudioProjectStore(tmp_path)
    store.create("demo", project_id="demo", plan=plan)
    old = json.loads(store.record_path("demo").read_text(encoding="utf-8"))

    def refused(*args, **kwargs):
        raise OSError("publish refused")

    monkeypatch.setattr(mod, "write_atomic", refused)
    with pytest.raises(OSError):
        store.update_plan("demo", plan, expected_version=1)
    assert json.loads(store.record_path("demo").read_text(encoding="utf-8")) == old


def test_cas_returns_the_published_update_time(tmp_path, plan):
    store = project_module().StudioProjectStore(tmp_path)
    store.create("demo", project_id="demo")
    changed = store.update_plan("demo", plan, expected_version=0)
    assert changed.updated_at == store.snapshot("demo").updated_at
