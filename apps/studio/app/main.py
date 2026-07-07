from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from glob import glob
from pathlib import Path
import re
import shutil
from typing import Any
from urllib import error, request

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fantasy_agent.chatgpt_app import (
    SERVER_NAME,
    SERVER_VERSION,
    WIDGET_MIME_TYPE,
    WIDGET_URI,
    call_workbench_tool,
    tool_descriptors,
    widget_resource,
    widget_resource_meta,
)
from fantasy_agent.contracts import (
    AssetApprovalManifest,
    CreativeReviewReport,
    DirectorBuildPlan,
    DirectorTaskBreakdown,
    EnemyPressureTuning,
    PromptRequest,
    default_comfyui_endpoint_candidates,
)
from fantasy_agent.local_tools import manual_correction_targets, open_manual_correction_target
from fantasy_agent.workflows import (
    build_asset_approval_manifest,
    decompose_production_tasks,
    run_director_workflow,
)

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
STATIC_DIR = APP_DIR / "static"
WEB_CONSOLE_STATIC_DIR = REPO_ROOT / "apps" / "web-console" / "static"
CHATGPT_WORKBENCH_STATIC_DIR = REPO_ROOT / "apps" / "chatgpt-workbench" / "static"
FRONTEND_DIST_DIR = REPO_ROOT / "apps" / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"
WORKBENCH_PATH = CHATGPT_WORKBENCH_STATIC_DIR / "workbench.html"

app = FastAPI(
    title="Fantasy Agent Studio",
    version=SERVER_VERSION,
    description="Single local desktop-style panel for Fantasy Agent production workflows.",
)

app.mount("/studio-static", StaticFiles(directory=str(STATIC_DIR)), name="studio_static")
app.mount("/assets", StaticFiles(directory=str(WEB_CONSOLE_STATIC_DIR)), name="web_console_assets")
if FRONTEND_DIST_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIST_DIR)), name="frontend_assets")
app.mount(
    "/static",
    StaticFiles(directory=str(CHATGPT_WORKBENCH_STATIC_DIR)),
    name="chatgpt_workbench_static",
)


class ManualCorrectionOpenRequest(BaseModel):
    target_id: str
    engine: str = "UE5"
    confirmed_side_effects: bool = False




class ApprovalManifestRequest(BaseModel):
    review: CreativeReviewReport
    decisions: dict[str, str] = Field(default_factory=dict)


class ApprovalManifestResponse(BaseModel):
    status: str
    manifest_path: str
    manifest: AssetApprovalManifest


class AssetExecutionRequest(BaseModel):
    plan: DirectorBuildPlan
    with_assets: bool = False
    with_visuals: bool = False
    confirmed: bool = False


class ExecuteDemoRequest(BaseModel):
    plan: DirectorBuildPlan
    engine: str = ""  # inferred from plan when empty
    with_assets: bool = False
    with_visuals: bool = False
    with_gameplay: bool = False
    enemy_tuning: EnemyPressureTuning = Field(default_factory=EnemyPressureTuning)
    approval_manifest_path: str | None = None
    confirmed: bool = False


# DirectorBuildPlan is imported from another module; ensure the forward
# reference is resolved so this model is fully defined.
ApprovalManifestRequest.model_rebuild()
ApprovalManifestResponse.model_rebuild()
AssetExecutionRequest.model_rebuild()
ExecuteDemoRequest.model_rebuild()


# In-memory execution job registry. Jobs run on a single worker so we never
    # launch two engines at once. Not persisted - studio is a local dev tool.
_EXECUTE_POOL = ThreadPoolExecutor(max_workers=1)
_EXECUTE_JOBS: dict[str, dict[str, Any]] = {}
_ASSET_JOBS: dict[str, dict[str, Any]] = {}


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _initialize(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    protocol_version = params.get("protocolVersion") or "2024-11-05"
    return _jsonrpc_result(
        request_id,
        {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        },
    )


def _read_widget() -> str:
    return WORKBENCH_PATH.read_text(encoding="utf-8")


def _frontend_index_or(static_path: Path) -> FileResponse:
    if FRONTEND_INDEX_PATH.exists():
        return FileResponse(FRONTEND_INDEX_PATH)
    return FileResponse(static_path)


def _mcp_status_item(
    *,
    service_id: str,
    label: str,
    status: str,
    target: str,
    detail: str,
    next_action: str,
    detail_key: str,
    next_action_key: str,
    detail_args: dict[str, Any] | None = None,
    next_action_args: dict[str, Any] | None = None,
    required: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": service_id,
        "label": label,
        "status": status,
        "target": target,
        "detail": detail,
        "detail_key": detail_key,
        "detail_args": detail_args or {},
        "next_action": next_action,
        "next_action_key": next_action_key,
        "next_action_args": next_action_args or {},
        "required": required,
        "metadata": metadata or {},
    }


def _http_json(url: str, timeout: float = 0.75) -> dict[str, Any] | list[Any]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload) if payload else {}


def _probe_comfyui() -> dict[str, Any]:
    env_candidates = [
        value
        for value in [os.environ.get("COMFYUI_URL"), os.environ.get("COMFYUI_ENDPOINT")]
        if value
    ]
    candidates = [*env_candidates, *default_comfyui_endpoint_candidates()]
    failures: list[str] = []
    executor = ThreadPoolExecutor(max_workers=max(1, len(candidates)))
    futures = {
        executor.submit(_http_json, f"{endpoint.rstrip('/')}/system_stats"): endpoint
        for endpoint in candidates
    }
    handled_futures = set()
    try:
        completed = as_completed(futures, timeout=1.25)
        for future in completed:
            handled_futures.add(future)
            endpoint = futures[future]
            try:
                stats = future.result()
            except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
                failures.append(f"{endpoint}: {exc}")
                continue
            system = stats.get("system", {}) if isinstance(stats, dict) else {}
            version = system.get("comfyui_version") or "reachable"
            return _mcp_status_item(
                service_id="comfyui",
                label="ComfyUI",
                status="ready",
                target=endpoint,
                detail=f"Connected to ComfyUI ({version}).",
                next_action="Run capability probe before submitting visual reference jobs.",
                detail_key="mcpDetailComfyReady",
                detail_args={"version": version},
                next_action_key="mcpNextComfyReady",
                metadata={"version": version},
            )
    except FutureTimeoutError:
        failures.append("Timed out probing local ComfyUI endpoints.")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    for future, endpoint in futures.items():
        if future in handled_futures or not future.done():
            continue
        try:
            future.result()
        except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {exc}")
    return _mcp_status_item(
        service_id="comfyui",
        label="ComfyUI",
        status="unavailable",
        target=", ".join(candidates),
        detail="No local ComfyUI endpoint responded.",
        next_action="Start ComfyUI and confirm it is listening on 127.0.0.1:8188.",
        detail_key="mcpDetailComfyMissing",
        next_action_key="mcpNextComfyMissing",
        metadata={"failures": failures[-3:]},
    )


def _candidate_paths(patterns: list[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        found.extend(path for path in glob(pattern) if Path(path).exists())
    return found


def _existing_env_path(names: list[str]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and Path(value).exists():
            return value
    return None


def _find_executable(
    *,
    env_names: list[str],
    commands: list[str],
    path_patterns: list[str],
) -> str | None:
    env_path = _existing_env_path(env_names)
    if env_path:
        return env_path
    for command in commands:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    for candidate in _candidate_paths(path_patterns):
        return candidate
    return None


def _godot_candidate_key(path: str) -> tuple[tuple[int, ...], int, str]:
    version = tuple(int(part) for part in re.findall(r"\d+", path))
    console_score = 1 if "console" in Path(path).name.casefold() else 0
    return version, console_score, path.casefold()


def _find_godot_executable() -> str | None:
    env_path = _existing_env_path(["GODOT_EXECUTABLE"])
    if env_path:
        return env_path
    for command in ["godot-console", "godot4", "godot"]:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    candidates = _candidate_paths(
        [
            "C:/Program Files/Godot/Godot*.exe",
            "C:/Users/*/AppData/Local/Programs/Godot/Godot*.exe",
            "C:/Users/*/Downloads/Godot*/Godot*.exe",
        ]
    )
    if candidates:
        return max(candidates, key=_godot_candidate_key)
    return None


def _probe_executable(
    *,
    service_id: str,
    label: str,
    env_names: list[str],
    commands: list[str],
    path_patterns: list[str],
    next_action_ready: str,
    next_action_missing: str,
    next_action_ready_key: str,
    next_action_missing_key: str,
    required: bool = True,
) -> dict[str, Any]:
    executable = _find_executable(
        env_names=env_names,
        commands=commands,
        path_patterns=path_patterns,
    )
    if executable:
        return _mcp_status_item(
            service_id=service_id,
            label=label,
            status="ready",
            target=executable,
            detail="Executable found. MCP execution still requires explicit confirmation.",
            next_action=next_action_ready,
            detail_key="mcpDetailExecutableReady",
            next_action_key=next_action_ready_key,
            required=required,
        )
    return _mcp_status_item(
        service_id=service_id,
        label=label,
        status="unavailable",
        target=", ".join([*commands, *env_names]),
        detail="No executable was found on PATH, in configured environment variables, or common install folders.",
        next_action=next_action_missing,
        detail_key="mcpDetailExecutableMissing",
        next_action_key=next_action_missing_key,
        required=required,
    )


def _probe_studio_mcp() -> dict[str, Any]:
    tools = tool_descriptors()
    return _mcp_status_item(
        service_id="studio-mcp",
        label="Fantasy Agent MCP",
        status="ready" if tools else "unavailable",
        target="/mcp",
        detail=f"JSON-RPC endpoint is mounted with {len(tools)} planning tools.",
        next_action="Use an HTTPS tunnel when connecting this endpoint to ChatGPT Apps.",
        detail_key="mcpDetailStudioReady",
        detail_args={"tool_count": len(tools)},
        next_action_key="mcpNextStudioReady",
        metadata={"tool_count": len(tools)},
    )


def _probe_github_cli() -> dict[str, Any]:
    git = shutil.which("git")
    gh = shutil.which("gh")
    if git and gh:
        return _mcp_status_item(
            service_id="github",
            label="GitHub CLI",
            status="ready",
            target=gh,
            detail="git and gh are available for future GitHub MCP handoffs.",
            next_action="Run gh auth status before creating PRs or issue automation.",
            detail_key="mcpDetailGithubReady",
            next_action_key="mcpNextGithubReady",
            required=False,
            metadata={"git": git, "gh": gh},
        )
    return _mcp_status_item(
        service_id="github",
        label="GitHub CLI",
        status="degraded" if git else "unavailable",
        target="git, gh",
        detail="GitHub MCP is optional; gh is not required for local prototype generation.",
        next_action="Install GitHub CLI only if you want PR, issue, or repository automation.",
        detail_key="mcpDetailGithubOptional",
        next_action_key="mcpNextGithubOptional",
        required=False,
        metadata={"git": git, "gh": gh},
    )


def _probe_godot(required: bool) -> dict[str, Any]:
    executable = _find_godot_executable()
    if executable:
        return _mcp_status_item(
            service_id="godot",
            label="Godot",
            status="ready",
            target=executable,
            detail="Executable found. MCP execution still requires explicit confirmation.",
            next_action="Use Godot MCP validation for Godot-selected quick-play projects.",
            detail_key="mcpDetailExecutableReady",
            next_action_key="mcpNextGodotReady",
            required=required,
        )
    return _mcp_status_item(
        service_id="godot",
        label="Godot",
        status="unavailable",
        target="godot-console, godot4, godot, GODOT_EXECUTABLE",
        detail="No executable was found on PATH, in configured environment variables, or common install folders.",
        next_action="Install Godot 4 or set GODOT_EXECUTABLE to the Godot executable.",
        detail_key="mcpDetailExecutableMissing",
        next_action_key="mcpNextGodotMissing",
        required=required,
    )


def _is_godot_engine(engine: str) -> bool:
    return "godot" in engine.casefold()


def _mcp_connectivity_status(engine: str = "UE5") -> dict[str, Any]:
    godot_selected = _is_godot_engine(engine)
    services = [
        _probe_studio_mcp(),
        _probe_comfyui(),
        _probe_executable(
            service_id="blender",
            label="Blender",
            env_names=["BLENDER_EXECUTABLE"],
            commands=["blender"],
            path_patterns=[
                "C:/Program Files/Blender Foundation/Blender */blender.exe",
                "C:/Program Files/Blender Foundation/Blender/blender.exe",
            ],
            next_action_ready="Generate Blender Python first, then execute only after confirmation.",
            next_action_missing="Install Blender or set BLENDER_EXECUTABLE to blender.exe.",
            next_action_ready_key="mcpNextBlenderReady",
            next_action_missing_key="mcpNextBlenderMissing",
        ),
        _probe_executable(
            service_id="unreal",
            label="Unreal Engine",
            env_names=["UNREAL_EDITOR", "UE_EDITOR"],
            commands=["UnrealEditor-Cmd.exe", "UnrealEditor.exe"],
            path_patterns=[
                "C:/Program Files/Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor-Cmd.exe",
                "C:/Program Files/Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor.exe",
            ],
            next_action_ready="Use Unreal MCP validation before editor commandlets or PIE/package tests.",
            next_action_missing="Install UE5 or set UNREAL_EDITOR to UnrealEditor-Cmd.exe.",
            next_action_ready_key="mcpNextUnrealReady",
            next_action_missing_key="mcpNextUnrealMissing",
            required=not godot_selected,
        ),
        _probe_godot(required=godot_selected),
        _probe_github_cli(),
    ]
    required = [service for service in services if service["required"]]
    ready_required = [service for service in required if service["status"] == "ready"]
    return {
        "status": "ready" if len(ready_required) == len(required) else "degraded",
        "engine": engine,
        "engine_kind": "godot" if godot_selected else "unreal",
        "required_ready": len(ready_required),
        "required_total": len(required),
        "services": services,
    }


def _handle_rpc(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _initialize(request_id, params)
    if method == "ping":
        return _jsonrpc_result(request_id, {})
    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": tool_descriptors()})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return _jsonrpc_error(request_id, -32602, "tools/call requires params.name")
        return _jsonrpc_result(request_id, call_workbench_tool(name, arguments))
    if method == "resources/list":
        return _jsonrpc_result(request_id, {"resources": [widget_resource()]})
    if method == "resources/read":
        uri = params.get("uri")
        if uri != WIDGET_URI:
            return _jsonrpc_error(request_id, -32002, f"Unknown resource URI: {uri}")
        return _jsonrpc_result(
            request_id,
            {
                "contents": [
                    {
                        "uri": WIDGET_URI,
                        "mimeType": WIDGET_MIME_TYPE,
                        "text": _read_widget(),
                        "_meta": widget_resource_meta(),
                    }
                ]
            },
        )
    return _jsonrpc_error(request_id, -32601, f"Unsupported method: {method}")


@app.get("/")
def index() -> FileResponse:
    return _frontend_index_or(STATIC_DIR / "index.html")


@app.get("/web-console")
def web_console() -> FileResponse:
    return _frontend_index_or(WEB_CONSOLE_STATIC_DIR / "index.html")


@app.get("/workbench")
def workbench() -> FileResponse:
    return FileResponse(WORKBENCH_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "fantasy-agent-studio", "version": SERVER_VERSION}


@app.get("/api/mcp/status")
def mcp_status(engine: str = "UE5") -> dict[str, Any]:
    return _mcp_connectivity_status(engine)


@app.get("/api/manual-correction/targets")
def correction_targets(engine: str = "UE5") -> dict[str, Any]:
    return manual_correction_targets(engine)


@app.post("/api/manual-correction/open")
def correction_open(request: ManualCorrectionOpenRequest) -> dict[str, Any]:
    return open_manual_correction_target(
        target_id=request.target_id,
        engine=request.engine,
        confirmed_side_effects=request.confirmed_side_effects,
    )


@app.post("/api/plan", response_model=DirectorBuildPlan)
def plan(request: PromptRequest) -> DirectorBuildPlan:
    return run_director_workflow(request)


@app.post("/api/tasks", response_model=DirectorTaskBreakdown)
def tasks(request: PromptRequest) -> DirectorTaskBreakdown:
    return decompose_production_tasks(request)


@app.get("/mcp")
def mcp_info() -> dict[str, Any]:
    return {
        "status": "ok",
        "transport": "json-rpc-over-http",
        "endpoint": "/mcp",
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


@app.post("/mcp")
async def mcp(request: Request) -> Response:
    payload = await request.json()
    if isinstance(payload, list):
        responses = [_handle_rpc(message) for message in payload if isinstance(message, dict)]
        responses = [response for response in responses if response is not None]
        if not responses:
            return Response(status_code=202)
        return JSONResponse(responses)
    if not isinstance(payload, dict):
        return JSONResponse(_jsonrpc_error(None, -32600, "Invalid JSON-RPC payload"), status_code=400)

    response = _handle_rpc(payload)
    if response is None:
        return Response(status_code=202)
    return JSONResponse(response)


@app.post("/debug/tool/{tool_name}")
async def debug_tool(tool_name: str, request: Request) -> dict[str, Any]:
    arguments = await request.json()
    return call_workbench_tool(tool_name, arguments)


def _infer_engine(plan: DirectorBuildPlan, override: str) -> str:
    """Return 'godot' or 'unreal' from an explicit override or the plan."""
    text = (override or "").casefold()
    if "godot" in text:
        return "godot"
    if "ue" in text or "unreal" in text:
        return "unreal"
    choice = (getattr(plan.gameplay_spec, "engine_choice", "") or "").casefold()
    if "godot" in choice:
        return "godot"
    if "ue" in choice or "unreal" in choice:
        return "unreal"
    # Default to Godot - the lighter, fully self-contained path.
    return "godot"


def _build_execution_result(req: ExecuteDemoRequest, *, confirmed: bool):
    """Call the right executor; returns an ExecutionResult."""
    from fantasy_agent.executor import execute_godot_demo, execute_unreal_demo
    from fantasy_agent.local_tools import _find_blender, _find_godot, _find_unreal, _unreal_cmd_executable

    from datetime import datetime

    engine = _infer_engine(req.plan, req.engine)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    if engine == "unreal":
        return execute_unreal_demo(
            req.plan,
            session_id=session_id,
            confirmed=confirmed,
            unreal_cmd=_unreal_cmd_executable(_find_unreal()) or "UnrealEditor-Cmd",
        )
    return execute_godot_demo(
        req.plan,
        session_id=session_id,
        confirmed=confirmed,
        godot_exe=_find_godot() or "godot",
        with_assets=req.with_assets,
        blender_exe=_find_blender() or "blender",
        with_visuals=req.with_visuals,
        with_gameplay=req.with_gameplay,
        enemy_tuning=req.enemy_tuning,
        approval_manifest_path=req.approval_manifest_path,
    )


def _approval_manifest_path() -> Path:
    path = REPO_ROOT / "generated" / "asset-approval-manifest.yaml"
    resolved = path.resolve()
    generated_root = (REPO_ROOT / "generated").resolve()
    if generated_root not in resolved.parents and resolved != generated_root:
        raise RuntimeError("approval manifest path must stay under generated/")
    return resolved


@app.post("/api/creative-review/approval-manifest", response_model=ApprovalManifestResponse)
def write_approval_manifest(req: ApprovalManifestRequest) -> ApprovalManifestResponse:
    import yaml

    manifest = build_asset_approval_manifest(req.review, req.decisions)
    path = _approval_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    rel = path.relative_to(REPO_ROOT).as_posix()
    return ApprovalManifestResponse(status="written", manifest_path=rel, manifest=manifest)


def _build_asset_execution_result(req: AssetExecutionRequest, *, confirmed: bool):
    from fantasy_agent.executor import execute_asset_pipeline
    from fantasy_agent.local_tools import _find_blender

    from datetime import datetime

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return execute_asset_pipeline(
        req.plan,
        session_id=session_id,
        confirmed=confirmed,
        workspace_root=REPO_ROOT,
        with_assets=req.with_assets,
        blender_exe=_find_blender() or "blender",
        with_visuals=req.with_visuals,
    )


def _run_asset_execution_job(job_id: str, req: AssetExecutionRequest) -> None:
    from dataclasses import asdict

    try:
        result = _build_asset_execution_result(req, confirmed=True)
        _ASSET_JOBS[job_id] = {"status": result.status, "result": asdict(result)}
    except Exception as exc:  # noqa: BLE001 - surface worker failures to the UI
        _ASSET_JOBS[job_id] = {"status": "failed", "error": str(exc)}


@app.post("/api/assets/execute")
def execute_assets(req: AssetExecutionRequest) -> dict[str, Any]:
    if not req.confirmed:
        preview = _build_asset_execution_result(req, confirmed=False)
        return {
            "status": "confirmation_required",
            "planned_side_effects": preview.planned_side_effects,
        }

    from datetime import datetime

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _ASSET_JOBS[job_id] = {"status": "running"}
    _EXECUTE_POOL.submit(_run_asset_execution_job, job_id, req)
    return {"status": "running", "job_id": job_id}


@app.get("/api/assets/execute/{job_id}")
def asset_execute_status(job_id: str) -> dict[str, Any]:
    job = _ASSET_JOBS.get(job_id)
    if job is None:
        return {"status": "unknown", "job_id": job_id}
    return {"job_id": job_id, **job}


def _run_execution_job(job_id: str, req: ExecuteDemoRequest) -> None:
    from dataclasses import asdict

    try:
        result = _build_execution_result(req, confirmed=True)
        _EXECUTE_JOBS[job_id] = {"status": result.status, "result": asdict(result)}
    except Exception as exc:  # noqa: BLE001 - surface any executor failure to the UI
        _EXECUTE_JOBS[job_id] = {"status": "failed", "error": str(exc)}


@app.post("/api/execute")
def execute_demo(req: ExecuteDemoRequest) -> dict[str, Any]:
    if not req.confirmed:
        # Confirmation gate: report side effects without writing or executing.
        preview = _build_execution_result(req, confirmed=False)
        return {
            "status": "confirmation_required",
            "engine": _infer_engine(req.plan, req.engine),
            "planned_side_effects": preview.planned_side_effects,
        }

    from datetime import datetime

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _EXECUTE_JOBS[job_id] = {"status": "running"}
    _EXECUTE_POOL.submit(_run_execution_job, job_id, req)
    return {"status": "running", "job_id": job_id, "engine": _infer_engine(req.plan, req.engine)}


@app.get("/api/execute/{job_id}")
def execute_status(job_id: str) -> dict[str, Any]:
    job = _EXECUTE_JOBS.get(job_id)
    if job is None:
        return {"status": "unknown", "job_id": job_id}
    return {"job_id": job_id, **job}

