"""真实 SDK Streamable HTTP 往返；表单 callback 是测试客户端，不是 Codex 用户。"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import socket
from contextlib import asynccontextmanager

import httpx2
import pytest
import uvicorn
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient

from apps.studio.app.mcp_connection import MCPConnection, local_request_allowed
from apps.studio.app.mcp_server import INSTRUCTIONS, StudioMCPTransport
from fantasy_agent.contracts import PlaytestReport, PlaytestSample, PromptRequest
from fantasy_agent.evolution.candidates import apply_changes
from fantasy_agent.evolution.contracts import EvolutionIteration, EvolutionReport, NumericChange
from fantasy_agent.evolution.library import load_report, save_report
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from fantasy_agent.studio_projects import StudioProjectStore
from fantasy_agent.studio_workflow import StudioWorkflowService
from fantasy_agent.workflow_authorization import WorkflowAuthorizationStore
from fantasy_agent.workflows import run_director_workflow
from mcp import ClientSession, types

ENVELOPE = {"summary", "status", "resources", "blockers", "next_actions"}


class QueuedPool:
    def __init__(self):
        self.work = []

    def submit(self, fn, *args):
        self.work.append(lambda: fn(*args))


@pytest.fixture
def protocol_context(tmp_path):
    store = StudioProjectStore(tmp_path)
    pool = QueuedPool()
    jobs = {
        name: InMemoryJobRegistry(pool) for name in ("execute", "assets", "playtest", "evolution")
    }
    service = StudioWorkflowService(
        store,
        WorkflowAuthorizationStore(store),
        execute_jobs=jobs["execute"],
        asset_jobs=jobs["assets"],
        playtest_jobs=jobs["playtest"],
        evolution_jobs=jobs["evolution"],
    )
    connection = MCPConnection(tmp_path)
    connection.set_enabled(True)
    return service, connection, StudioMCPTransport(service, connection), pool


def saved_project(service):
    plan = run_director_workflow(
        PromptRequest(
            prompt="快递员在闹鬼车站逃生，收集三份证据开启出口", engine_version="Godot 4"
        ),
        use_llm=False,
    )
    return service.projects.create("协议验收项目", plan=plan)


@asynccontextmanager
async def http_server(app):
    """只在测试进程绑定 loopback 随机端口，不开启引擎或外部服务。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False, lifespan="on"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:

        async def started():
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("测试服务器未启动。")
                await asyncio.sleep(0.01)

        await asyncio.wait_for(started(), 10)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, 10)
        finally:
            sock.close()


@asynccontextmanager
async def sdk_session(base_url, connection, callback=None):
    async with (
        httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {connection.copy_token()}"},
            timeout=10,
            trust_env=False,
        ) as client,
        streamable_http_client(base_url + "/mcp", http_client=client) as streams,
        ClientSession(*streams, elicitation_callback=callback, read_timeout_seconds=10) as session,
    ):
        initialized = await session.initialize()
        # A real tool-using client discovers the registry before acting. The
        # SDK otherwise lazily lists tools after a result, which cannot work
        # after the user deliberately disables the connection or rotates its key.
        await session.list_tools()
        yield session, initialized


def test_sdk_http_initialize_tools_call_resources_share_service(protocol_context):
    service, connection, transport, pool = protocol_context

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection) as (client, initialized),
        ):
            assert initialized.server_info.name == "fantasy-studio"
            assert initialized.instructions == INSTRUCTIONS
            assert len(INSTRUCTIONS) < 512 and "模型不能批准自己" in initialized.instructions
            tools = (await client.list_tools()).tools
            assert {t.name for t in tools} == set(service.registry.names())
            assert not any(t.name.startswith("apply_") for t in tools)
            for tool in tools:
                assert tool.input_schema == service.registry.get(tool.name).input_schema
                assert tool.annotations.read_only_hint == (
                    service.registry.get(tool.name).permission == "read_only"
                )
            created = await client.call_tool("create_project", {"name": "SDK 创建项目"})
            assert ENVELOPE <= created.structured_content.keys() and not created.is_error
            project_id = created.structured_content["project_id"]
            assert service.projects.snapshot(project_id).name == "SDK 创建项目"
            listed = await client.call_tool("list_projects", {})
            assert any(p["project_id"] == project_id for p in listed.structured_content["projects"])
            resources = (await client.list_resources()).resources
            snapshot = next(
                r for r in resources if str(r.uri) == f"studio://projects/{project_id}/snapshot"
            )
            assert snapshot.mime_type == "application/json"
            resource = await client.read_resource(snapshot.uri)
            data = json.loads(resource.contents[0].text)
            assert ENVELOPE <= data.keys() and data["data"]["project_id"] == project_id
            invalid = await client.call_tool("create_project", {"name": 123})
            assert invalid.is_error and invalid.structured_content["status"] == "blocked"
            injected = await client.call_tool(
                "execute_demo", {"project_id": project_id, "plan_version": 0, "confirmed": True}
            )
            assert injected.is_error and not pool.work
            forbidden = await client.read_resource("file:///C:/Windows/system.ini")
            assert json.loads(forbidden.contents[0].text)["status"] == "blocked"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "reply_action, option, expected",
    [
        ("accept", True, "authorized"),
        ("accept", False, "declined"),
        ("decline", True, "awaiting_authorization"),
        ("cancel", True, "awaiting_authorization"),
        ("accept", "true", "awaiting_authorization"),
        (None, None, "awaiting_authorization"),
        ("policy_denied", None, "awaiting_authorization"),
    ],
)
def test_sdk_native_form_accept_decline_cancel_invalid_unsupported_policy(
    protocol_context, reply_action, option, expected
):
    service, connection, transport, pool = protocol_context
    project = saved_project(service)
    forms = []

    async def callback(ctx, params):
        forms.append(params)
        assert isinstance(params, types.ElicitRequestFormParams)
        assert "协议验收项目" in params.message and project.project_id in params.message
        assert (
            "计划版本" in params.message
            and "生产动作" in params.message
            and "120" in params.message
        )
        assert params.requested_schema["required"] == ["approved"]
        if reply_action == "policy_denied":
            return types.ErrorData(code=types.INVALID_REQUEST, message="客户端策略不允许展示确认")
        return types.ElicitResult(action=reply_action, content={"approved": option})

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection, callback if reply_action else None) as (
                client,
                _,
            ),
        ):
            result = await client.call_tool(
                "request_workflow_authorization",
                {
                    "project_id": project.project_id,
                    "plan_version": 1,
                    "actions": [{"tool_name": "create_godot_project_structure", "arguments": {}}],
                    "ttl_seconds": 120,
                },
            )
            assert result.structured_content["status"] == expected
            if expected == "authorized":
                grants = service.authorization.grants(project.project_id)
                assert (
                    len(grants) == 1
                    and grants[0].actions[0].tool_name == "create_godot_project_structure"
                )
            else:
                assert not service.authorization.grants(project.project_id)
            if expected.startswith("awaiting"):
                assert (
                    "approval_policy.granular.mcp_elicitations"
                    in result.structured_content["next_actions"][0]
                )
            assert not pool.work

    asyncio.run(scenario())
    assert bool(forms) == (reply_action is not None)


@pytest.mark.parametrize("change", ["version", "disable", "rotate"])
def test_sdk_approval_is_rechecked_after_form_response(protocol_context, change):
    service, connection, transport, _ = protocol_context
    project = saved_project(service)

    async def callback(ctx, params):
        if change == "version":
            service.save_plan(project.project_id, project.plan, 1)
        elif change == "disable":
            connection.set_enabled(False)
        else:
            connection.rotate()
        return types.ElicitResult(action="accept", content={"approved": True})

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection, callback) as (client, _),
        ):
            result = await client.call_tool(
                "request_workflow_authorization",
                {
                    "project_id": project.project_id,
                    "plan_version": 1,
                    "actions": [{"tool_name": "create_godot_project_structure", "arguments": {}}],
                },
            )
            assert result.structured_content["status"] == (
                "blocked" if change == "version" else "awaiting_authorization"
            )
            assert not service.authorization.grants(project.project_id)

    asyncio.run(scenario())


def test_sdk_asset_review_rechecks_actual_content(protocol_context):
    service, connection, transport, _ = protocol_context
    project = saved_project(service)
    root = service.projects.production_workspace(project.project_id)
    asset = root / "versions/v1/generated/assets/model.glb"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"actual-model-content")
    service.projects.register_resource(
        project.project_id,
        resource_id="model",
        path="versions/v1/generated/assets/model.glb",
        kind="asset",
        plan_version=1,
        sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
    )

    shown = []

    async def callback(ctx, params):
        assert "待审阅实际产物" in params.message and "model.glb" in params.message
        shown.append(True)
        asset.write_bytes(b"changed-after-presenting-form")
        return types.ElicitResult(action="accept", content={"approved": True})

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection, callback) as (client, _),
        ):
            result = await client.call_tool(
                "request_asset_review",
                {
                    "project_id": project.project_id,
                    "plan_version": 1,
                    "resource_ids": ["model"],
                },
            )
            assert result.structured_content["status"] == "blocked"
            assert shown == [True]
            assert not service.projects.snapshot(project.project_id).decisions

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "action, approved, expected",
    [
        ("accept", True, "approved"),
        ("accept", False, "rejected"),
        ("decline", True, "awaiting_review"),
        ("cancel", True, "awaiting_review"),
    ],
)
def test_sdk_asset_review_only_accept_records_user_decision(
    protocol_context, action, approved, expected
):
    service, connection, transport, pool = protocol_context
    project = saved_project(service)
    root = service.projects.production_workspace(project.project_id)
    root.mkdir(parents=True, exist_ok=True)
    asset = root / "versions/v1/generated/assets/asset.glb"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"immutable-model-fixture")
    service.projects.register_resource(
        project.project_id,
        resource_id="asset",
        path="versions/v1/generated/assets/asset.glb",
        kind="asset",
        plan_version=1,
        sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
    )

    async def callback(ctx, params):
        assert (
            "asset.glb" in params.message
            and hashlib.sha256(asset.read_bytes()).hexdigest() in params.message
        )
        return types.ElicitResult(action=action, content={"approved": approved})

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection, callback) as (client, _),
        ):
            result = await client.call_tool(
                "request_asset_review",
                {"project_id": project.project_id, "plan_version": 1, "resource_ids": ["asset"]},
            )
            assert result.structured_content["status"] == expected
            decisions = service.projects.snapshot(project.project_id).decisions
            assert len(decisions) == (1 if action == "accept" else 0)
            assert not pool.work

    asyncio.run(scenario())


@pytest.mark.parametrize("reply", ["accept", "decline", "changed"])
def test_sdk_candidate_native_adoption_binds_stored_measurement(protocol_context, reply):
    """测量均为显式测试 fixture，不运行或声称完成引擎试玩。"""
    service, connection, transport, pool = protocol_context
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase across neon towers", engine_version="Godot 4"),
        use_llm=False,
    )
    project = service.projects.create("候选确认测试", plan=plan)
    before = float(plan.production_spec_bundle.numeric.pressure_clock_seconds)
    change = NumericChange(
        field="numeric.pressure_clock_seconds",
        before=before,
        after=float(round(before * 1.2)),
        reason="测试 fixture：给路线增加有限计时余量",
    )
    candidate = apply_changes(plan, [change])

    def measurement(wins):
        return PlaytestReport(
            runs_requested=3,
            samples=[
                PlaytestSample(
                    run_index=i,
                    outcome="win" if i < wins else "fail",
                    reason="" if i < wins else "Route timer expires",
                    session_seconds=12,
                    player_moved_distance=80,
                    playable=True,
                    axis="parkour",
                    held=["sprint"],
                    taps={"vault": 5, "slide": 2},
                )
                for i in range(3)
            ],
        )

    report = EvolutionReport(
        experiment_id="native-candidate",
        status="improved",
        original_plan=plan,
        best_iteration=1,
        iterations=[
            EvolutionIteration(index=0, session_id="base", plan=plan, report=measurement(0)),
            EvolutionIteration(
                index=1,
                session_id="candidate",
                plan=candidate,
                report=measurement(3),
                changes=[change],
                eligible=True,
                improved=True,
            ),
        ],
    )
    root = service._root(project.project_id, 1)
    save_report(report, workspace_root=root)
    service.projects.register_job(
        project.project_id, job_id=report.experiment_id, plan_version=1, tool_name="run_evolution"
    )
    service.projects.update_job(project.project_id, report.experiment_id, status="done")

    async def callback(ctx, params):
        assert "候选确认测试" in params.message and "候选内容标识" in params.message
        assert (
            "候选修改" in params.message
            and "实测结果" in params.message
            and "未解决风险" in params.message
        )
        assert "pressure_clock_seconds" in params.message and "脚本 bot" in params.message
        if reply == "changed":
            report.notes.append("表单展示之后报告内容变化")
            save_report(report, workspace_root=root)
        return types.ElicitResult(
            action="decline" if reply == "decline" else "accept", content={"approved": True}
        )

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection, callback) as (client, _),
        ):
            result = await client.call_tool(
                "request_candidate_adoption",
                {
                    "project_id": project.project_id,
                    "plan_version": 1,
                    "job_id": report.experiment_id,
                },
            )
            assert (
                result.structured_content["status"]
                == {"accept": "adopted", "decline": "awaiting_review", "changed": "blocked"}[reply]
            )
            snapshot = service.projects.snapshot(project.project_id)
            assert snapshot.plan_version == (2 if reply == "accept" else 1)
            assert len(snapshot.decisions) == (1 if reply == "accept" else 0)
            assert load_report(report.experiment_id, workspace_root=root).adopted_iteration == (
                1 if reply == "accept" else None
            )
            assert not pool.work

    asyncio.run(scenario())


def test_sdk_timeout_never_applies_intent(protocol_context, monkeypatch):
    service, connection, transport, _ = protocol_context
    project = saved_project(service)
    monkeypatch.setattr("apps.studio.app.mcp_server.ELICIT_TIMEOUT_SECONDS", 0.05)

    async def callback(ctx, params):
        await asyncio.sleep(0.2)
        return types.ElicitResult(action="accept", content={"approved": True})

    async def scenario():
        async with (
            http_server(transport) as url,
            sdk_session(url, connection, callback) as (client, _),
        ):
            result = await client.call_tool(
                "request_workflow_authorization",
                {
                    "project_id": project.project_id,
                    "plan_version": 1,
                    "actions": [{"tool_name": "create_godot_project_structure", "arguments": {}}],
                },
            )
            assert result.structured_content["status"] == "awaiting_authorization"
            assert not service.authorization.grants(project.project_id)

    asyncio.run(scenario())


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_transport_auth_disabled_origin_host_and_immediate_close(protocol_context, method):
    _, connection, transport, _ = protocol_context
    with TestClient(
        transport, client=("127.0.0.1", 123), base_url="http://127.0.0.1:8042"
    ) as client:
        token = connection.copy_token()
        assert client.request(method, "/mcp").status_code == 401
        assert (
            client.request(
                method, "/mcp", headers={"Authorization": "Bearer incorrect"}
            ).status_code
            == 401
        )
        assert (
            client.request(
                method,
                "/mcp",
                headers={"Authorization": f"Bearer {token}", "Host": "evil.example:8042"},
            ).status_code
            == 403
        )
        assert (
            client.request(
                method,
                "/mcp",
                headers={"Authorization": f"Bearer {token}", "Origin": "http://evil.example:8042"},
            ).status_code
            == 403
        )
        connection.set_enabled(False)
        assert (
            client.request(method, "/mcp", headers={"Authorization": f"Bearer {token}"}).status_code
            == 503
        )


@pytest.mark.parametrize("peer", ["192.168.1.2", "203.0.113.7", "::ffff:192.168.1.1", "localhost"])
def test_transport_nonloopback_peer_rejected_before_auth(protocol_context, peer):
    _, _, transport, _ = protocol_context
    with TestClient(transport, client=(peer, 123), base_url="http://127.0.0.1:8042") as client:
        assert client.post("/mcp", json={}).status_code == 403


@pytest.mark.parametrize(
    "host, origin",
    [
        ("127.0.0.1:8043", None),
        ("127.0.0.1:8042?fake", None),
        ("127.0.0.1:8042#fake", None),
        ("user@127.0.0.1:8042", None),
        ("127.0.0.1:8042", "http://127.0.0.1:8042/path"),
    ],
)
def test_literal_host_and_same_origin_require_exact_authority(host, origin):
    headers = [(b"host", host.encode())] + ([(b"origin", origin.encode())] if origin else [])
    assert not local_request_allowed(
        {
            "client": ("127.0.0.1", 123),
            "server": ("127.0.0.1", 8042),
            "scheme": "http",
            "headers": headers,
        }
    )


def test_actual_token_in_malformed_protocol_headers_unicode_and_logs_is_hidden(
    protocol_context, caplog
):
    _, connection, transport, _ = protocol_context
    token = connection.copy_token()
    with TestClient(
        transport, client=("127.0.0.1", 123), base_url="http://127.0.0.1:8042"
    ) as client:
        auth = {"Authorization": f"Bearer {token}"}
        cases = [
            {
                "json": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": 1,
                    "params": {"name": "create_project", "arguments": {"name": {"invalid": token}}},
                }
            },
            {"json": {"jsonrpc": "2.0", "method": token, "id": 1}},
            {"content": '{"value":"' + "".join(f"\\u{ord(c):04x}" for c in token) + '"}'},
            {"content": "not-json " + token},
        ]
        for kwargs in cases:
            response = client.post("/mcp", headers=auth, **kwargs)
            assert response.status_code == 400 and token not in response.text
        response = client.post("/mcp", headers={**auth, "Mcp-Session-Id": token}, json={})
        assert response.status_code == 400 and token not in response.text
    assert token not in caplog.text and token not in json.dumps(
        connection.state("http://127.0.0.1:8042")
    )


def test_sdk_actual_token_arbitrary_text_error_and_binary_resources(
    protocol_context, monkeypatch, caplog
):
    service, connection, transport, _ = protocol_context
    project = service.projects.create("数据保护")
    token = connection.copy_token()
    root = service.projects.production_workspace(project.project_id)
    root.mkdir(parents=True, exist_ok=True)
    for name, raw in (
        ("text", ("普通产物 " + token).encode()),
        ("binary", b"\xff" + token.encode()),
        ("clean", b"\xffclean-model"),
    ):
        (root / name).write_bytes(raw)
        service.projects.register_resource(
            project.project_id, resource_id=name, path=name, mime_type="application/octet-stream"
        )
    original_call = service.call

    def call(name, arguments):
        if name == "list_projects":
            raise ValueError("真实 token 不应进入错误 " + token)
        return original_call(name, arguments)

    monkeypatch.setattr(service, "call", call)

    async def scenario():
        async with http_server(transport) as url, sdk_session(url, connection) as (client, _):
            error = await client.call_tool("list_projects", {})
            assert error.is_error and token not in error.model_dump_json()
            for name in ("text", "binary", "clean"):
                result = await client.read_resource(
                    f"studio://projects/{project.project_id}/{name}"
                )
                assert token not in result.model_dump_json()
                content = result.contents[0]
                if name == "clean":
                    assert isinstance(content, types.BlobResourceContents)
                    assert base64.b64decode(content.blob) == b"\xffclean-model"
                    assert ENVELOPE <= content.meta["studio"].keys()
                else:
                    assert isinstance(content, types.TextResourceContents)
                    data = json.loads(content.text)
                    assert ENVELOPE <= data.keys()
                    assert data["status"] == ("blocked" if name == "binary" else "ok")
                    assert token not in content.text

    asyncio.run(scenario())
    assert token not in caplog.text


def test_main_lifespan_sessions_are_new_and_rest_shares_project_pools(
    protocol_context, monkeypatch
):
    from apps.studio.app import main

    service, connection, _, _ = protocol_context
    monkeypatch.setattr(main.app.state, "workflow_service", service, raising=False)
    monkeypatch.setattr(main.app.state, "mcp_connection", connection, raising=False)
    managers = []
    for _ in range(2):
        with TestClient(
            main.app, client=("127.0.0.1", 123), base_url="http://127.0.0.1:8042"
        ) as client:
            managers.append(main.app.state.mcp_transport.manager)
            assert main.app.state.mcp_transport.service is service
            assert client.get("/health").status_code == 200
            response = client.post(
                "/api/projects",
                json={"name": "REST 共享项目"},
                headers={"Origin": "http://127.0.0.1:8042"},
            )
            assert response.status_code == 200
            assert service.projects.snapshot(response.json()["project_id"]).name == "REST 共享项目"
            config = client.get("/api/mcp/connection/config").json()
            assert config["endpoint"] == "http://127.0.0.1:8042/mcp"
            assert (
                "bearer_token_env_var" in config["toml"]
                and connection.copy_token() not in config["toml"]
            )
            workbuddy = json.loads(config["workbuddy_json"])["mcpServers"]["fantasy-studio"]
            assert workbuddy["type"] == "http" and workbuddy["url"] == config["endpoint"]
            assert workbuddy["headers"]["Authorization"] == "Bearer ${FANTASY_STUDIO_MCP_TOKEN}"
            assert connection.copy_token() not in config["workbuddy_json"]
            response = client.post(
                "/api/mcp/connection/token", headers={"Origin": "http://127.0.0.1:8042"}
            )
            assert (
                response.headers["cache-control"] == "no-store"
                and response.json()["token"] == connection.copy_token()
            )
            assert client.post("/api/mcp/connection/token").status_code == 403
    assert managers[0] is not managers[1]
