"""同一 Studio 端口上的本机 MCP；工作流和执行池由宿主共享。"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import anyio
from jsonschema import Draft202012Validator
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from apps.studio.app.mcp_connection import MCPConnection, local_request_allowed
from fantasy_agent.studio_workflow import StudioWorkflowService
from mcp import types

INSTRUCTIONS = (
    "灵构工坊是 Studio 单进程的本机游戏生产工作流。先创建或读取项目、保存并检查计划，"
    "再请求本轮明确动作与预算的生产授权。授权、资产审阅和候选采纳均须用户通过原生表单确认；"
    "模型不能批准自己。生产工具只使用服务端已保存计划，长任务返回 job_id，由任务工具轮询。"
    "每次读回版本后再行动，版本冲突时重新读取。资产须审阅后导入，质量检查先于打包。"
    "资源仅能通过项目内登记引用读取。所有范围和风险须明确呈现；尚未实现的操作返回阻塞。"
)
ELICIT_HELP = "客户端需要支持原生 MCP 表单确认，并允许 approval_policy.granular.mcp_elicitations；请由用户在客户端设置中调整，不能自动批准。"
ELICIT_TIMEOUT_SECONDS = 120


class StudioMCPTransport:
    def __init__(self, service: StudioWorkflowService, connection: MCPConnection) -> None:
        self.service, self.connection = service, connection
        self.server = Server(
            "fantasy-studio",
            version="0.1.0",
            title="灵构工坊",
            instructions=INSTRUCTIONS,
            on_list_tools=self.list_tools,
            on_call_tool=self.call_tool,
            on_list_resources=self.list_resources,
            on_read_resource=self.read_resource,
            # Schema errors belong to our fixed-message layer, rather than the SDK's
            # default validator, which may echo arbitrary client input.
        )
        self.manager = StreamableHTTPSessionManager(
            self.server,
            stateless=False,
            json_response=False,
            max_sessions=16,
            session_idle_timeout=1800,
            max_request_body_size=4 * 1024 * 1024,
            security_settings=TransportSecuritySettings(
                allowed_hosts=[
                    "127.0.0.1:*",
                    "localhost:*",
                    "[::1]:*",
                    "127.0.0.1",
                    "localhost",
                    "[::1]",
                ],
                allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
            ),
        )

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            async with self.manager.run():
                await receive()
                await send({"type": "lifespan.startup.complete"})
                await receive()
                await send({"type": "lifespan.shutdown.complete"})
            return
        if not local_request_allowed(scope):
            await JSONResponse({"detail": "仅允许同源本机连接。"}, status_code=403)(
                scope, receive, send
            )
            return
        if not self.connection.enabled:
            await JSONResponse({"detail": "MCP 连接尚未开启。"}, status_code=503)(
                scope, receive, send
            )
            return
        auth = [v.decode("latin-1") for k, v in scope["headers"] if k.lower() == b"authorization"]
        if (
            len(auth) != 1
            or not auth[0].startswith("Bearer ")
            or not self.connection.matches(auth[0][7:])
        ):
            await JSONResponse({"detail": "本机连接凭据无效。"}, status_code=401)(
                scope, receive, send
            )
            return
        protocol_headers = [v for k, v in scope["headers"] if k.lower() != b"authorization"]
        if (
            self.connection.contains_secret(protocol_headers)
            or self.connection.contains_secret(scope.get("path", ""))
            or self.connection.contains_secret(scope.get("query_string", b""))
        ):
            await JSONResponse({"detail": "连接凭据不能作为协议内容。"}, status_code=400)(
                scope, receive, send
            )
            return
        # Inspect decoded JSON before SDK parsing, including clientInfo and malformed
        # method/argument shapes. Neither SDK protocol errors nor logs may echo a key.
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > 4 * 1024 * 1024:
                await JSONResponse({"detail": "请求过大。"}, status_code=413)(scope, receive, send)
                return
            chunks.append(body)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        try:
            decoded = json.loads(body) if body else None
        except (ValueError, UnicodeDecodeError):
            decoded = None
        if self.connection.contains_secret(body) or self.connection.contains_secret(decoded):
            await JSONResponse({"detail": "连接凭据不能作为协议内容。"}, status_code=400)(
                scope, receive, send
            )
            return
        consumed = False

        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.manager.handle_request(scope, replay, send)

    def result(self, data: dict[str, Any], *, error: bool = False) -> types.CallToolResult:
        envelope = {
            "summary": "操作已完成。",
            "status": "ok",
            "resources": [],
            "blockers": [],
            "next_actions": [],
            **data,
        }
        envelope = self.connection.sanitize(envelope)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(envelope, ensure_ascii=False))],
            structured_content=envelope,
            is_error=error,
        )

    async def list_tools(self, ctx, params) -> types.ListToolsResult:
        tools = []
        for name in self.service.registry.names():
            spec = self.service.registry.get(name)
            tools.append(
                types.Tool(
                    name=self.connection.sanitize(name),
                    title=self.connection.sanitize(spec.title),
                    description=self.connection.sanitize(spec.description),
                    input_schema=self.connection.sanitize(spec.input_schema),
                    annotations=types.ToolAnnotations(
                        read_only_hint=spec.permission == "read_only",
                        destructive_hint=spec.effect_scope == "production",
                        open_world_hint=False,
                    ),
                )
            )
        self.connection.record("读取工具清单", "ok")
        return types.ListToolsResult(tools=tools)

    async def call_tool(self, ctx, params) -> types.CallToolResult:
        spec = self.service.registry.get(params.name)
        arguments = params.arguments or {}
        if (
            not spec
            or self.connection.contains_secret(arguments)
            or list(Draft202012Validator(spec.input_schema).iter_errors(arguments))
        ):
            return self.result(
                {"status": "blocked", "summary": "工具不存在或参数不符合声明的范围。"}, error=True
            )
        try:
            outcome = await anyio.to_thread.run_sync(
                lambda: self.service.call(params.name, arguments)
            )
            data = {"summary": outcome.content, "status": outcome.status, **outcome.data}
            if data.get("intent_id") and data.get("kind") in {
                "authorization",
                "asset_review",
                "candidate_adoption",
            }:
                data = await self.elicit(ctx, data)
            self.connection.record(
                spec.title or "调用工作流工具", str(data.get("status", outcome.status)), params.name
            )
            return self.result(
                data,
                error=outcome.status != "ok"
                or data.get("status") in {"blocked", "failed", "version_conflict", "unsupported"},
            )
        except Exception:  # noqa: BLE001 - 外部协议异常不能回显参数或连接凭据
            self.connection.record(spec.title or "调用工作流工具", "error", params.name)
            return self.result(
                {"status": "failed", "summary": "工作流操作失败，请在 Studio 检查项目状态。"},
                error=True,
            )

    async def elicit(self, ctx, intent: dict[str, Any]) -> dict[str, Any]:
        waiting = {
            **intent,
            "status": "awaiting_authorization"
            if intent["kind"] == "authorization"
            else "awaiting_review",
            "summary": "等待用户原生确认。",
            "next_actions": [ELICIT_HELP],
        }
        caps = ctx.session.client_capabilities
        if not caps or not caps.elicitation or caps.elicitation.form is None:
            return waiting
        revision = self.connection.approval_revision()
        if revision is None:
            return waiting
        project = self.service.projects.snapshot(intent["project_id"])
        description = {
            "项目": project.name if project else intent["project_id"],
            "项目标识": intent["project_id"],
            "计划版本": intent["plan_version"],
            "项目工作目录": str(self.service.projects.production_workspace(intent["project_id"])),
        }
        labels = {
            "actions": "生产动作",
            "allowed_asset_paths": "可读取本机资产路径",
            "ttl_seconds": "时间预算（秒）",
            "subjects": "待审阅实际产物",
            "subject_sha256": "候选内容标识",
            "job_id": "实测任务",
            "candidate_index": "候选序号",
            "changes": "候选修改",
            "measurement": "实测结果",
            "risks": "未解决风险",
        }
        description.update({label: intent[key] for key, label in labels.items() if key in intent})
        message = "请核对本轮范围后决定是否批准：\n" + json.dumps(
            self.connection.sanitize(description), ensure_ascii=False, indent=2
        )
        schema = {
            "type": "object",
            "properties": {"approved": {"type": "boolean", "title": "批准此处完整展示的本轮范围"}},
            "required": ["approved"],
        }

        async def connection_changed():
            while self.connection.approval_revision() == revision:
                await asyncio.sleep(0.05)

        confirmation = asyncio.create_task(ctx.session.elicit_form(message, schema))
        revision_watch = asyncio.create_task(connection_changed())
        try:
            completed, _ = await asyncio.wait(
                {confirmation, revision_watch},
                timeout=ELICIT_TIMEOUT_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if revision_watch in completed:
                return {**waiting, "summary": "连接已关闭或凭据已更新，请重新连接后发起确认。"}
            if confirmation not in completed:
                return waiting
            reply = confirmation.result()
        except Exception:  # noqa: BLE001 - 客户端不支持、策略拒绝、超时均不能隐式批准
            return waiting
        finally:
            for task in (confirmation, revision_watch):
                if not task.done():
                    task.cancel()
            await asyncio.gather(confirmation, revision_watch, return_exceptions=True)
        content = reply.content or {}
        if (
            reply.action != "accept"
            or not isinstance(content, dict)
            or set(content) != {"approved"}
            or type(content.get("approved")) is not bool
            or self.connection.approval_revision() != revision
        ):
            return waiting
        approved = content["approved"]
        apply = {
            "authorization": self.service.apply_authorization,
            "asset_review": self.service.apply_asset_review,
            "candidate_adoption": self.service.apply_candidate_adoption,
        }[intent["kind"]]
        try:
            return await anyio.to_thread.run_sync(
                lambda: apply(intent["project_id"], intent["intent_id"], approved=approved)
            )
        except ValueError:
            return {
                "status": "blocked",
                "summary": "项目版本或产物内容已变化，请重新读取后发起确认。",
                "resources": [],
                "blockers": ["旧审阅请求已失效。"],
                "next_actions": ["重新读取项目快照。"],
            }

    async def list_resources(self, ctx, params) -> types.ListResourcesResult:
        resources = []
        for project in self.service.projects.list_projects():
            for resource in self.service.resources(project.project_id):
                safe = self.connection.sanitize(resource)
                resources.append(
                    types.Resource(
                        uri=safe["uri"],
                        name=safe["resource_id"],
                        title=f"{self.connection.sanitize(project.name)} · {safe['resource_id']}",
                        mime_type=safe["mime_type"],
                    )
                )
        self.connection.record("读取项目资源清单", "ok")
        return types.ListResourcesResult(resources=resources)

    async def read_resource(self, ctx, params) -> types.ReadResourceResult:
        uri = str(params.uri)
        public_uri = self.connection.sanitize(uri)
        try:
            parsed = urlsplit(uri)
            parts = parsed.path.split("/")
            if (
                self.connection.contains_secret(uri)
                or parsed.scheme != "studio"
                or parsed.netloc != "projects"
                or len(parts) != 3
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("invalid resource")
            raw = await anyio.to_thread.run_sync(
                lambda: self.service.read_resource(parts[1], parts[2])
            )
            data = self.connection.sanitize(raw)
            envelope = {
                "summary": "项目产物已读取。",
                "status": "ok",
                "resources": [{"uri": public_uri}],
                "blockers": [],
                "next_actions": [],
            }
            if data.get("encoding") == "base64":
                content = types.BlobResourceContents(
                    uri=public_uri,
                    mime_type=data["mime_type"],
                    blob=data["data"],
                    meta={"studio": envelope},
                )
            else:
                payload = data.get("data", data)
                # Text resources use the same Chinese envelope as tool results;
                # binary resources carry it in metadata while retaining their bytes.
                envelope.update({"data": payload})
                if data.get("status") == "blocked":
                    envelope.update(
                        {
                            "status": "blocked",
                            "summary": data["summary"],
                            "blockers": [data["summary"]],
                        }
                    )
                content = types.TextResourceContents(
                    uri=public_uri,
                    mime_type="application/json",
                    text=json.dumps(envelope, ensure_ascii=False),
                )
            self.connection.record("读取项目产物", "ok")
        except Exception:  # noqa: BLE001 - 资源异常只返回固定中文错误，不公开本机路径
            content = types.TextResourceContents(
                uri=public_uri,
                mime_type="application/json",
                text=json.dumps(
                    {
                        "status": "blocked",
                        "summary": "产物不属于项目、已变化或无法公开。",
                        "resources": [],
                        "blockers": ["资源引用无效。"],
                        "next_actions": ["重新读取项目资源清单。"],
                    },
                    ensure_ascii=False,
                ),
            )
        return types.ReadResourceResult(contents=[content])
