"""Studio previews, grants, adoption and cold reads use the same evolution rules."""

import asyncio
import importlib.util
import json as jsonlib
from concurrent.futures import Future
from pathlib import Path

import pytest

from fantasy_agent.evolution import controller
from fantasy_agent.evolution.library import load_report, save_report
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from tests.test_evolution_controller import _plan, _report


class InlinePool:
    def submit(self, fn, *args):
        future = Future()
        future.set_result(fn(*args))
        return future


class AsgiClient:
    """Exercise the real app without an optional HTTP client dependency."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, json=None):
        messages = []
        body = jsonlib.dumps(json).encode() if json is not None else b""

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(self.app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
            "query_string": b"", "root_path": "", "server": ("test", 80),
            "client": ("127.0.0.1", 1), "headers": [(b"content-type", b"application/json")],
        }, receive, send))
        status = next(item["status"] for item in messages if item["type"] == "http.response.start")
        content = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")

        class Response:
            status_code = status

            def json(self):
                return jsonlib.loads(content)

        return Response()

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, json=None):
        return self.request("POST", path, json)


@pytest.fixture
def studio(tmp_path, monkeypatch):
    path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("evolution_studio_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_EVOLUTION_JOB_REGISTRY", InMemoryJobRegistry(InlinePool()), raising=False)
    return module, AsgiClient(module.app), tmp_path


def _start(client, monkeypatch):
    attempts = []

    def factory(**kwargs):
        assert kwargs["confirmed"]

        def measured(*args):
            attempts.append(args)
            return _report(0 if len(attempts) == 1 else 3)

        return measured

    monkeypatch.setattr(controller, "make_iteration_runner", factory)
    response = client.post("/api/evolution/run", json={"plan": _plan().model_dump(mode="json"), "confirmed": True})
    assert response.status_code == 200
    return response.json()["experiment_id"], attempts


def test_preview_does_not_create_a_record_or_launch_a_worker(studio, monkeypatch):
    _module, client, root = studio

    def forbidden(**_):
        pytest.fail("preview started engine work")

    monkeypatch.setattr(controller, "make_iteration_runner", forbidden)
    response = client.post("/api/evolution/run", json={"plan": _plan().model_dump(mode="json")})
    assert response.status_code == 200
    assert response.json()["status"] == "confirmation_required"
    assert response.json()["planned_side_effects"]
    assert not (root / "generated").exists()


def test_confirmed_experiment_is_pollable_but_requires_a_separate_adoption(studio, monkeypatch):
    _, client, root = studio
    experiment_id, attempts = _start(client, monkeypatch)
    payload = client.get(f"/api/evolution/{experiment_id}").json()
    assert payload["status"] == "done"
    assert payload["report"]["status"] == "improved"
    assert {"source", "schema_version", "inputs", "outputs", "risks", "next_actions"} <= payload["report"].keys()
    assert len(attempts) == 2
    assert client.get("/api/evolution/experiences").json() == {"experiences": []}
    adopted = client.post(f"/api/evolution/{experiment_id}/adopt", json={
        "plan": _plan().model_dump(mode="json"), "feedback": "人工确认路线可完成",
    })
    assert adopted.status_code == 200
    assert adopted.json()["plan"]["production_spec_bundle"]["numeric"]["pressure_clock_seconds"] > _plan().production_spec_bundle.numeric.pressure_clock_seconds
    assert len(client.get("/api/evolution/experiences").json()["experiences"]) == 1
    suggestion = client.post("/api/evolution/suggest", json={"plan": _plan().model_dump(mode="json")})
    assert suggestion.status_code == 200
    assert suggestion.json()["changes"]
    assert load_report(experiment_id, workspace_root=root).adopted_iteration == 1


def test_cold_running_record_is_interrupted_and_never_restarts(studio, monkeypatch):
    module, client, root = studio
    experiment_id, _ = _start(client, monkeypatch)
    report = load_report(experiment_id, workspace_root=root)
    report.status = "running"
    save_report(report, workspace_root=root)
    module._EVOLUTION_JOBS.clear()
    response = client.get(f"/api/evolution/{experiment_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "interrupted"
    assert response.json()["report"]["status"] == "interrupted"
    assert load_report(experiment_id, workspace_root=root).status == "running", "GET must not write decisions"


def test_an_old_experiment_cannot_overwrite_a_changed_plan(studio, monkeypatch):
    _, client, _ = studio
    experiment_id, _ = _start(client, monkeypatch)
    plan = _plan()
    plan.gameplay_spec.title = "new idea"
    response = client.post(f"/api/evolution/{experiment_id}/adopt", json={"plan": plan.model_dump(mode="json")})
    assert response.status_code == 409
    assert client.get("/api/evolution/experiences").json() == {"experiences": []}


def test_budget_contract_is_validated_at_the_http_edge(studio):
    _, client, root = studio
    response = client.post("/api/evolution/run", json={
        "plan": _plan().model_dump(mode="json"), "confirmed": True, "max_iterations": 4,
    })
    assert response.status_code == 422
    assert not (root / "generated").exists()


def test_unknown_experiments_are_readable_and_cannot_be_adopted(studio):
    _, client, root = studio
    assert client.get("/api/evolution/missing").json()["status"] == "unknown"
    response = client.post("/api/evolution/missing/adopt", json={"plan": _plan().model_dump(mode="json")})
    assert response.status_code == 404
    assert client.post("/api/evolution/missing/cancel").json()["status"] == "unknown"
    assert not (root / "generated").exists()
