"""显式授权后在 OS 临时工作区运行 Studio MCP/Godot 开发验收。

SDK 表单 callback 仅代表开发验收客户端，不是 Codex 用户点击。真实 Codex
CLI 的只读连接另行保存证据；本脚本不改 Codex 全局配置，也不清理实测文件。
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))


def codex_provider_overrides(config: dict[str, Any], environment: dict[str, str]):
    """Reuse only the client's model provider; credentials stay in child env."""
    environment.pop("CODEX_API_KEY", None)
    arguments: list[str] = []
    secrets: list[str] = []
    if model := config.get("model"):
        arguments.extend(["--config", f"model={json.dumps(model)}"])
    provider_id = config.get("model_provider", "openai")
    if not isinstance(provider_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", provider_id):
        raise ValueError("Codex 客户端模型服务标识无效。")
    provider = config.get("model_providers", {}).get(provider_id, {})
    if address := provider.get("base_url"):
        parsed = urlsplit(address)
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or parsed.query
        ):
            raise ValueError("客户端模型服务地址不能包含凭据或查询参数；请使用独立环境变量认证。")
    if provider.get("auth") or provider.get("gateway_oauth"):
        raise ValueError("验收不重放客户端认证命令或登录流程；请先完成客户端认证。")
    arguments.extend(["--config", f"model_provider={json.dumps(provider_id)}"])
    fields = {
        key: provider[key]
        for key in ("name", "base_url", "wire_api", "requires_openai_auth", "env_key")
        if key in provider
    }
    if secret := provider.get("experimental_bearer_token"):
        if provider.get("requires_openai_auth"):
            raise ValueError("客户端同时配置两种认证方式，请先核对。")
        if not isinstance(secret, str):
            raise ValueError("客户端认证配置无效。")
        environment["FANTASY_STUDIO_CODEX_PROVIDER_TOKEN"] = secret
        fields.update(env_key="FANTASY_STUDIO_CODEX_PROVIDER_TOKEN", requires_openai_auth=False)
        secrets.append(secret)
    elif key := fields.get("env_key"):
        if not environment.get(key):
            raise ValueError("Codex 客户端模型服务的环境变量未设置。")
        secrets.append(environment[key])
    for key, value in fields.items():
        arguments.extend(["--config", f"model_providers.{provider_id}.{key}={json.dumps(value)}"])
    return arguments, secrets


class Acceptance:
    def __init__(self, args: argparse.Namespace, workspace: Path, *, client_environment=None):
        self.args, self.workspace = args, workspace
        self.output = workspace / "acceptance"
        if args.serve_only:
            self.output /= f"restart-{int(time.time())}"
        self.output.mkdir(parents=True, exist_ok=True)
        self.token = ""
        self.project_id = ""
        self.plan_version = 0
        self.steps: list[dict[str, Any]] = []
        self.forms: list[dict[str, Any]] = []
        self.last_status: dict[str, str] = {}
        self.started = time.time()
        self.base_url = ""
        self.client_environment = dict(client_environment or os.environ)
        self.client_secrets: list[str] = []

    def safe(self, value: Any) -> Any:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        if self.token:
            serialized = serialized.replace(self.token, "[REDACTED]")
        for secret in self.client_secrets:
            serialized = serialized.replace(secret, "[REDACTED]")
        serialized = re.sub(r"\bsk-[A-Za-z0-9_*-]{5,}", "[REDACTED]", serialized)
        return json.loads(serialized)

    def persist(self, status: str = "running", error: str = "") -> None:
        payload = self.safe(
            {
                "status": status,
                "error": error,
                "workspace": str(self.workspace),
                "code_root": str(CODE_ROOT),
                "base_url": self.base_url,
                "pid": os.getpid(),
                "elapsed_seconds": time.time() - self.started,
                "mcp_version": importlib.metadata.version("mcp"),
                "godot_executable": self.args.godot,
                "project_id": self.project_id,
                "plan_version": self.plan_version,
                "sdk_forms_are_development_callbacks": True,
                "candidate_adoption_is_development_acceptance": self.args.adopt_candidate,
                "codex_native_user_forms_observed": False,
                "steps": self.steps,
                "forms": self.forms,
            }
        )
        (self.output / "report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record(self, name: str, result: Any) -> None:
        self.steps.append({"name": name, "time": time.time(), "result": self.safe(result)})
        self.persist()

    async def form(self, ctx, params):
        from mcp import types

        description = json.loads(params.message.split("\n", 1)[1])
        assert description["项目标识"] == self.project_id
        assert description["计划版本"] == self.plan_version
        assert params.requested_schema["required"] == ["approved"]
        adoption = "候选内容标识" in description
        if adoption:
            assert description["实测任务"] and description["候选内容标识"]
            assert description["实测结果"]["samples"]
            approved = self.args.adopt_candidate
        else:
            assert 0 < description["时间预算（秒）"] <= 1800
            assert description["可读取本机资产路径"] == []
            tools = {item["tool_name"] for item in description["生产动作"]}
            assert tools <= {"execute_demo", "playtest_godot_project", "run_evolution"}
            approved = True
        self.forms.append(
            {
                "client": "official-sdk-development-callback",
                "description": self.safe(description),
                "action": "accept" if approved else "decline",
                "approved": approved,
            }
        )
        self.persist()
        return types.ElicitResult(
            action="accept" if approved else "decline", content={"approved": approved}
        )

    @asynccontextmanager
    async def session(self, *, forms: bool = True):
        import httpx2
        from mcp.client.streamable_http import streamable_http_client

        from mcp import ClientSession, types

        async with (
            httpx2.AsyncClient(
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30,
                trust_env=False,
            ) as http,
            streamable_http_client(self.base_url + "/mcp", http_client=http) as streams,
            ClientSession(
                *streams,
                elicitation_callback=self.form if forms else None,
                read_timeout_seconds=150,
                client_info=types.Implementation(name="studio-development-acceptance", version="1"),
            ) as client,
        ):
            initialized = await client.initialize()
            tools = await client.list_tools()
            self.record(
                "sdk_initialize",
                {
                    "server": initialized.server_info.model_dump(mode="json"),
                    "instructions": initialized.instructions,
                    "tools": [item.name for item in tools.tools],
                },
            )
            yield client

    async def call(self, client, name: str, args: dict[str, Any], *, expect: str = ""):
        result = await client.call_tool(name, args)
        data = result.structured_content
        assert isinstance(data, dict), f"{name}: 缺少结构化结果"
        assert {"summary", "status", "resources", "blockers", "next_actions"} <= data.keys()
        self.record(name, data)
        if expect:
            assert data["status"] == expect, f"{name}: {data['status']}，{data['summary']}"
        return data

    def context(self, **arguments):
        return {"project_id": self.project_id, "plan_version": self.plan_version, **arguments}

    async def wait_job(self, client, job_id: str, *, limit: float = 700):
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            result = await client.call_tool(
                "get_workflow_job", {"project_id": self.project_id, "job_id": job_id}
            )
            data = result.structured_content
            assert isinstance(data, dict)
            state = data["status"]
            if self.last_status.get(job_id) != state:
                print(f"任务 {job_id}: {state}", flush=True)
                self.last_status[job_id] = state
                self.record("job_status", data)
            if state in {"done", "failed", "cancelled", "interrupted"}:
                self.record("job_finished", data)
                return data
            await asyncio.sleep(1)
        await self.call(
            client,
            "cancel_workflow_job",
            {
                "project_id": self.project_id,
                "job_id": job_id,
            },
        )
        raise TimeoutError(f"任务 {job_id} 超出客户端验收等待预算")

    async def resources(self, client):
        listed = await client.list_resources()
        selected = [item for item in listed.resources if self.project_id in str(item.uri)]
        self.record("resources_list", [item.model_dump(mode="json") for item in selected])
        resource_dir = self.output / "resources"
        resource_dir.mkdir(exist_ok=True)
        for index, resource in enumerate(selected):
            result = await client.read_resource(resource.uri)
            payload = self.safe(result.model_dump(mode="json"))
            target = resource_dir / f"{index:04d}.json"
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.record("resources_read", {"count": len(selected), "directory": str(resource_dir)})

    async def scenario(self, main):
        async with self.session() as client:
            created = await self.call(client, "create_project", {"name": "MCP 隔离实测：屋顶跑酷"})
            self.project_id = created["project_id"]
            saved = await self.call(
                client,
                "generate_game_production_plan",
                self.context(
                    prompt=self.args.prompt,
                    target_minutes=5,
                    engine_version="Godot 4.6",
                    source_locale="zh-CN",
                    output_locales=["zh-CN"],
                ),
                expect="saved",
            )
            self.plan_version = saved["plan_version"]
            snapshot = await self.call(client, "get_project_snapshot", self.context())
            await self.call(
                client,
                "save_project_plan",
                {
                    "project_id": self.project_id,
                    "plan_version": 0,
                    "plan": snapshot["plan"],
                },
                expect="version_conflict",
            )
            if self.args.challenging_baseline:
                snapshot = await self.call(client, "get_project_snapshot", self.context())
                plan = snapshot["plan"]
                plan["production_spec_bundle"]["numeric"]["enemy_pressure"][
                    "move_speed_multiplier"
                ] = 3.0
                saved = await self.call(client, "save_project_plan", self.context(plan=plan))
                self.plan_version = saved["plan_version"]
                self.record("challenging_baseline", {"enemy_move_speed_multiplier": 3.0})
            # 验证 schema 不提供确认旗标，且缺授权不能启动生产。
            await self.call(client, "execute_demo", self.context(confirmed=True), expect="blocked")
            await self.call(client, "execute_demo", self.context(), expect="blocked")
            demo_args = {"engine": "godot", "with_gameplay": True}
            playtest_args = {"runs": 3, "max_wall_seconds": 120.0, "max_frames": 36000}
            evolution_args = {
                "max_iterations": 3,
                "max_wall_seconds": self.args.evolution_seconds,
                "use_experience": False,
            }
            actions = [
                {"tool_name": "execute_demo", "arguments": demo_args},
                {"tool_name": "playtest_godot_project", "arguments": playtest_args},
                {"tool_name": "run_evolution", "arguments": evolution_args},
            ]
            grant = await self.call(
                client,
                "request_workflow_authorization",
                self.context(
                    actions=actions,
                    allowed_asset_paths=[],
                    ttl_seconds=1800,
                ),
                expect="authorized",
            )
            grant_id = grant["grant_id"]
            demo_call = self.context(**demo_args, grant_id=grant_id, request_id="acceptance-demo")
            demo = await self.call(client, "execute_demo", demo_call)
            duplicate = await self.call(client, "execute_demo", demo_call)
            assert duplicate["job_id"] == demo["job_id"]
            demo_done = await self.wait_job(client, demo["job_id"])
            self.check_engine_job(demo_done)
            await self.resources(client)
            playtest = await self.call(
                client,
                "playtest_godot_project",
                self.context(
                    **playtest_args,
                    grant_id=grant_id,
                    request_id="acceptance-playtest",
                ),
            )
            playtest_done = await self.wait_job(client, playtest["job_id"], limit=180)
            if playtest_done["status"] != "done":
                assert self.args.challenging_baseline and playtest_done["result"]["data"]["samples"]
                self.record("measured_qa_failure", playtest_done)
            assert playtest_done["resources"], "独立试玩报告没有资源引用"
            rework = await self.call(
                client,
                "rework_node",
                self.context(
                    job_id=demo["job_id"],
                    resume_from="import",
                    grant_id=grant_id,
                    request_id="acceptance-rework",
                ),
            )
            rework_done = await self.wait_job(client, rework["job_id"])
            self.check_engine_job(rework_done)
            assert rework_done["session_id"] == demo_done["session_id"]
            self.record("rework_session_reused", {"session_id": rework_done["session_id"]})
            # 重连后查询保留的原 job，不重放生产。
        async with self.session() as client:
            replay = await self.call(client, "execute_demo", demo_call)
            assert replay["job_id"] == demo["job_id"]
            evolution = await self.call(
                client,
                "run_evolution",
                self.context(
                    **evolution_args,
                    grant_id=grant_id,
                    request_id="acceptance-evolution",
                ),
            )
            done = await self.wait_job(
                client, evolution["job_id"], limit=self.args.evolution_seconds + 60
            )
            assert done["status"] == "done", done["blockers"]
            report = done["result"]["data"]["report"]
            self.record("evolution_measured", report)
            if report["status"] == "improved":
                adopted = await self.call(
                    client,
                    "request_candidate_adoption",
                    self.context(
                        job_id=evolution["job_id"],
                    ),
                )
                if self.args.adopt_candidate:
                    assert adopted["status"] == "adopted", adopted
                    self.plan_version = adopted["plan_version"]
                    assert self.plan_version > demo_call["plan_version"]
                    await self.call(
                        client,
                        "execute_demo",
                        self.context(
                            **demo_args,
                            grant_id=grant_id,
                            request_id="old-grant-new-version",
                        ),
                        expect="blocked",
                    )
                    renewed = await self.call(
                        client,
                        "request_workflow_authorization",
                        self.context(
                            actions=[{"tool_name": "execute_demo", "arguments": demo_args}],
                            allowed_asset_paths=[],
                            ttl_seconds=120,
                        ),
                        expect="authorized",
                    )
                    self.record("new_version_requires_new_authorization", renewed)
            else:
                self.record(
                    "adoption_unavailable",
                    {
                        "status": report["status"],
                        "summary": "实测没有优胜候选，未伪造改进或采纳。",
                    },
                )
            await self.call(client, "get_workflow_state", self.context())
            await self.resources(client)
        if self.args.codex_cli:
            await self.real_codex()
        # UI 和工作流数据根共享；后台读取与 MCP 读取的是同一个项目。
        async with self.session(forms=False) as client:
            await self.call(client, "get_project_snapshot", self.context())
        self.record(
            "studio_same_process",
            {
                "pid": os.getpid(),
                "port": self.base_url,
                "data_root": str(main.REPO_ROOT),
                "frontend_dist": str(main.FRONTEND_DIST_DIR),
            },
        )

    async def real_codex(self):
        executable = shutil.which("codex")
        if not executable:
            self.record("codex_cli", {"status": "unavailable", "reason": "codex 不在 PATH"})
            return
        env = self.client_environment.copy()
        env["FANTASY_STUDIO_ACCEPTANCE_TOKEN"] = self.token
        config_path = Path(env.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
        try:
            config = (
                tomllib.loads(config_path.read_text(encoding="utf-8"))
                if config_path.exists()
                else {}
            )
            provider_arguments, self.client_secrets = codex_provider_overrides(config, env)
        except (OSError, ValueError):
            self.record(
                "codex_cli",
                {
                    "status": "client_authentication_required",
                    "summary": "客户端模型服务认证尚不可用，请先完成客户端认证。",
                },
            )
            return
        prompt = (
            "只做 MCP 只读连接验收。使用 studio MCP 调用 list_projects，"
            f"再调用 get_project_snapshot(project_id={self.project_id!r})，"
            "并读取该项目 snapshot 资源。不要创建或更新项目，不要请求任何授权，"
            "不要执行引擎、命令或其它写操作。最后用中文报告服务名、项目名、版本及已读取资源 URI。"
        )
        command = [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--json",
            "--color",
            "never",
            "--cd",
            str(self.workspace),
            "--config",
            f'mcp_servers.studio.url="{self.base_url}/mcp"',
            "--config",
            'mcp_servers.studio.bearer_token_env_var="FANTASY_STUDIO_ACCEPTANCE_TOKEN"',
            "--config",
            'mcp_servers.studio.enabled_tools=["list_projects","get_project_snapshot","get_workflow_state","read_project_resource"]',
            *provider_arguments,
            prompt,
        ]

        def run():
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    timeout=180,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            except subprocess.TimeoutExpired as exc:
                return {
                    "returncode": None,
                    "status": "timeout",
                    "stdout": str(exc.stdout or ""),
                    "stderr": str(exc.stderr or ""),
                }

        result = self.safe(await asyncio.to_thread(run))
        (self.output / "codex-cli.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.record(
            "codex_cli",
            {
                "returncode": result.get("returncode"),
                "evidence": str(self.output / "codex-cli.json"),
                "native_forms_tested": False,
            },
        )

    def check_engine_job(self, job):
        if job["status"] == "done":
            return
        stages = job["result"]["data"]["stages"]
        completed = {stage["name"] for stage in stages if stage["status"] == "done"}
        failed = {stage["name"] for stage in stages if stage["status"] == "failed"}
        assert (
            self.args.challenging_baseline
            and {"create", "validate", "import"} <= completed
            and failed == {"playtest"}
        ), job["blockers"]
        self.record("expected_baseline_qa_failure", job)


async def run(args: argparse.Namespace):
    import httpx2
    import uvicorn

    from apps.studio.app import main
    from fantasy_agent import local_tools

    if importlib.metadata.version("mcp") != "2.3.0":
        raise RuntimeError("验收要求官方 mcp==2.3.0")
    args.godot = args.godot or local_tools._find_godot() or ""
    if not args.godot or not Path(args.godot).is_file():
        raise FileNotFoundError("指定的 Godot console 可执行文件不存在")
    workspace = (
        Path(args.workspace).resolve()
        if args.workspace
        else Path(tempfile.mkdtemp(prefix="fa-mcp-"))
    )
    workspace.relative_to(Path(tempfile.gettempdir()).resolve())
    workspace.mkdir(parents=True, exist_ok=True)
    os.environ["GODOT_EXECUTABLE"] = str(Path(args.godot).resolve())
    client_environment = os.environ.copy()
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "FANTASY_AGENT_API_KEY"):
        os.environ.pop(key, None)
    main.REPO_ROOT = workspace
    # 静态资源继续使用当前构建；REPO_ROOT 只重定向决策与生产数据。
    main.FRONTEND_DIST_DIR = CODE_ROOT / "apps" / "frontend" / "dist"
    main.FRONTEND_INDEX_PATH = main.FRONTEND_DIST_DIR / "index.html"
    acceptance = Acceptance(args, workspace, client_environment=client_environment)
    connection = main.studio_mcp_connection()
    acceptance.token = connection.copy_token()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", args.port))
    port = sock.getsockname()[1]
    acceptance.base_url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(
        uvicorn.Config(
            main.app, log_level="warning", access_log=False, log_config=None, lifespan="on"
        )
    )
    server_task = asyncio.create_task(server.serve(sockets=[sock]))
    passed = False
    try:

        async def started():
            while not server.started:
                if server_task.done():
                    await server_task
                    raise RuntimeError("Studio 未启动")
                await asyncio.sleep(0.05)

        await asyncio.wait_for(started(), 15)
        print(
            f"隔离 Studio: {acceptance.base_url}，workspace={workspace}，pid={os.getpid()}",
            flush=True,
        )
        async with httpx2.AsyncClient(
            timeout=10, trust_env=False, headers={"Origin": acceptance.base_url}
        ) as http:
            state = await http.get(acceptance.base_url + "/api/mcp/connection")
            if not args.serve_only:
                assert state.json()["enabled"] is False
                disabled = await http.post(acceptance.base_url + "/mcp", json={})
                assert disabled.status_code == 503
            await http.post(acceptance.base_url + "/api/mcp/connection/enable")
            missing = await http.post(acceptance.base_url + "/mcp", json={})
            assert missing.status_code == 401
            bad_bearer = await http.post(
                acceptance.base_url + "/mcp", json={}, headers={"Authorization": "Bearer invalid"}
            )
            assert bad_bearer.status_code == 401
            bad_host = await http.post(
                acceptance.base_url + "/mcp", json={}, headers={"Host": f"attacker.example:{port}"}
            )
            assert bad_host.status_code == 403
            bad_origin = await http.post(
                acceptance.base_url + "/mcp",
                json={},
                headers={"Origin": "https://attacker.example"},
            )
            assert bad_origin.status_code == 403
            acceptance.record(
                "transport_default_and_bearer",
                {
                    "default_enabled": state.json()["enabled"],
                    "without_bearer": missing.status_code,
                    "bad_bearer": bad_bearer.status_code,
                    "bad_host": bad_host.status_code,
                    "bad_origin": bad_origin.status_code,
                },
            )
        if not args.serve_only:
            await acceptance.scenario(main)
            acceptance.persist("development_chain_verified")
            passed = True
            print(f"验收结束，报告：{acceptance.output / 'report.json'}", flush=True)
        if args.keep_alive or args.serve_only:
            print("保留隔离 Studio 供界面验收；Ctrl+C 关闭，文件保留。", flush=True)
            await server_task
    except BaseException as exc:
        if not passed:
            acceptance.persist("failed", f"{type(exc).__name__}: {exc}")
        raise
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(server_task, 15)
        finally:
            sock.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", help="声明已获隔离 Godot 实测授权")
    parser.add_argument("--godot", default="", help="覆盖本机 Godot 自动探测结果")
    parser.add_argument("--workspace", default="", help="既有 OS 临时目录，仅重启模式建议使用")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument(
        "--prompt",
        default="屋顶跑酷（parkour）追逐：冲刺、翻越、滑行，收集关键物品后抵达出口，失败后立即重开。",
        help="真实引擎验收的可玩循环点子",
    )
    parser.add_argument("--evolution-seconds", type=float, default=600)
    parser.add_argument(
        "--challenging-baseline", action="store_true", help="以合法 3 倍追击速度实测数值返工"
    )
    parser.add_argument(
        "--adopt-candidate", action="store_true", help="单独允许开发 callback 采纳实测优胜候选"
    )
    parser.add_argument(
        "--codex-cli", action="store_true", help="追加真实 Codex CLI 一次性只读连接"
    )
    parser.add_argument("--keep-alive", action="store_true")
    parser.add_argument(
        "--serve-only", action="store_true", help="重启保留的隔离数据，供界面/只读验收"
    )
    args = parser.parse_args()
    if not args.authorized:
        parser.error("必须显式传 --authorized；脚本会真正启动 Studio 和无窗口 Godot")
    if not 30 <= args.evolution_seconds <= 1800:
        parser.error("--evolution-seconds 必须在 30 到 1800 秒之间")
    if args.serve_only and not args.workspace:
        parser.error("--serve-only 必须显式提供先前的 --workspace")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
