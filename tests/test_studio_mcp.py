from __future__ import annotations

import asyncio
import base64
import json
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from apps.studio.app.mcp_connection import MCPConnection, local_request_allowed
from apps.studio.app.mcp_server import StudioMCPTransport
from fantasy_agent.studio_projects import StudioProjectStore
from fantasy_agent.studio_workflow import StudioWorkflowService
from fantasy_agent.workflow_authorization import WorkflowAuthorizationStore


@pytest.fixture
def setup(tmp_path):
    projects = StudioProjectStore(tmp_path)
    jobs = SimpleNamespace()
    service = StudioWorkflowService(
        projects,
        WorkflowAuthorizationStore(projects),
        execute_jobs=jobs,
        asset_jobs=jobs,
        playtest_jobs=jobs,
        evolution_jobs=jobs,
    )
    connection = MCPConnection(tmp_path)
    return service, connection, StudioMCPTransport(service, connection)


def scope(peer="127.0.0.1", host="127.0.0.1:8042", origin=None):
    headers = [(b"host", host.encode())]
    if origin:
        headers.append((b"origin", origin.encode()))
    return {
        "type": "http",
        "client": (peer, 123),
        "server": ("127.0.0.1", 8042),
        "scheme": "http",
        "headers": headers,
    }


@pytest.mark.parametrize(
    "peer,host,origin",
    [
        ("8.8.8.8", "127.0.0.1:8042", None),
        ("127.0.0.1", "attacker.example:8042", None),
        ("127.0.0.1", "127.0.0.1:8042", "https://attacker.example"),
        ("127.0.0.1", "127.0.0.1:8042", "http://localhost:8042"),
    ],
)
def test_rebinding_and_cross_origin_are_rejected(peer, host, origin):
    assert not local_request_allowed(scope(peer, host, origin))


def test_connection_default_private_persistent_and_explicit_copy(setup):
    _, connection, _ = setup
    token = connection.copy_token()
    assert len(token) >= 40
    assert not connection.state("http://127.0.0.1:8042")["enabled"]
    assert token not in json.dumps(connection.state("http://127.0.0.1:8042"))
    connection.set_enabled(True)
    assert MCPConnection(connection.workspace_root).matches(token)
    connection.rotate()
    assert not connection.matches(token)
    assert connection.copy_token() not in connection.config("http://127.0.0.1:8042")["toml"]


def test_disabled_bearer_and_secret_body_rejected_before_sdk(setup):
    _, connection, transport = setup
    with TestClient(
        transport, client=("127.0.0.1", 123), base_url="http://127.0.0.1:8042"
    ) as client:
        assert client.post("/mcp", json={}).status_code == 503
        connection.set_enabled(True)
        assert client.post("/mcp", json={}).status_code == 401
        token = connection.copy_token()
        response = client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {token}"},
            json={"params": {"invalid": token}},
        )
        assert response.status_code == 400
        assert token not in response.text


def test_registry_projection_and_result_secret_redaction(setup):
    service, connection, transport = setup
    tools = asyncio.run(transport.list_tools(None, None)).tools
    assert {t.name for t in tools} == set(service.registry.names())
    assert not any("apply_" in t.name for t in tools)
    token = connection.copy_token()
    result = transport.result({"status": "ok", "summary": token, "nested": {"text": token}})
    assert token not in result.model_dump_json()
    assert {
        "summary",
        "status",
        "resources",
        "blockers",
        "next_actions",
    } <= result.structured_content.keys()


@pytest.mark.parametrize("action,approved", [("accept", True), ("decline", None), ("cancel", None)])
def test_only_native_accept_and_explicit_option_apply_intent(setup, monkeypatch, action, approved):
    service, connection, transport = setup
    connection.set_enabled(True)
    project = service.projects.create("测试项目")
    intent = {
        "kind": "authorization",
        "intent_id": "intent-test",
        "project_id": project.project_id,
        "plan_version": 1,
        "actions": [],
        "ttl_seconds": 60,
        "allowed_asset_paths": [],
    }
    applied = []
    monkeypatch.setattr(
        service,
        "apply_authorization",
        lambda *a, **kw: applied.append(kw) or {"status": "approved"},
    )

    class Session:
        client_capabilities = SimpleNamespace(elicitation=SimpleNamespace(form=SimpleNamespace()))

        async def elicit_form(self, message, requested_schema):
            assert "测试项目" in message and "60" in message
            return SimpleNamespace(action=action, content={"approved": True})

    result = asyncio.run(transport.elicit(SimpleNamespace(session=Session()), intent))
    if approved is None:
        assert result["status"] == "awaiting_authorization" and not applied
    else:
        assert applied[0]["approved"] is approved


def test_unsupported_or_invalid_accept_never_approves(setup, monkeypatch):
    service, connection, transport = setup
    connection.set_enabled(True)
    project = service.projects.create("测试项目")
    intent = {
        "kind": "authorization",
        "intent_id": "intent-test",
        "project_id": project.project_id,
        "plan_version": 1,
        "actions": [],
        "ttl_seconds": 60,
        "allowed_asset_paths": [],
    }
    applied = []
    monkeypatch.setattr(service, "apply_authorization", lambda *a, **kw: applied.append(kw) or {})
    session = SimpleNamespace(client_capabilities=None)
    result = asyncio.run(transport.elicit(SimpleNamespace(session=session), intent))
    assert result["status"] == "awaiting_authorization" and not applied

    class Session:
        client_capabilities = SimpleNamespace(elicitation=SimpleNamespace(form=SimpleNamespace()))

        async def elicit_form(self, message, requested_schema):
            return SimpleNamespace(action="accept", content={"approved": "true"})

    result = asyncio.run(transport.elicit(SimpleNamespace(session=Session()), intent))
    assert result["status"] == "awaiting_authorization" and not applied


def test_binary_resource_does_not_encode_actual_secret(setup, monkeypatch):
    service, connection, transport = setup
    token = connection.copy_token()
    monkeypatch.setattr(
        service,
        "read_resource",
        lambda *a: {
            "data": base64.b64encode(b"\xff" + token.encode()).decode(),
            "encoding": "base64",
            "mime_type": "application/octet-stream",
        },
    )
    result = asyncio.run(
        transport.read_resource(None, SimpleNamespace(uri="studio://projects/p/r"))
    )
    assert token not in result.model_dump_json()
    assert not isinstance(
        result.contents[0],
        __import__("mcp.types", fromlist=["BlobResourceContents"]).BlobResourceContents,
    )
