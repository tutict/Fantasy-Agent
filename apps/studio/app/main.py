from __future__ import annotations

import ipaddress
import json
import logging
import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, nullcontext
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, model_validator

from apps.studio.app.mcp_connection import MCPConnection, local_request_allowed
from apps.studio.app.mcp_server import StudioMCPTransport
from fantasy_agent import api_settings, local_tools
from fantasy_agent.api_settings import llm_enabled, public_settings
from fantasy_agent.asset_library import (
    AssetLibraryError,
    ingest_asset,
    library_overview,
    remove_asset,
)
from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.blender_codegen import build_blender_script_artifact
from fantasy_agent.contracts import (
    AssetApprovalManifest,
    AssetLibraryEntry,
    AssetLibraryOverview,
    BlenderAssetPlan,
    BlenderScriptArtifact,
    ComfyUIVisualPlan,
    CompiledSpecArtifact,
    CreativeReviewReport,
    CreativeReviewRequest,
    DirectorBuildPlan,
    DirectorTaskBreakdown,
    EnemyPressureTuning,
    ExecutableQAReport,
    GameplaySpec,
    GDDDocument,
    GodotProjectPlan,
    IdeaDiscoveryRequest,
    IdeaSeed,
    PlaytestRequest,
    ProductionPipeline,
    ProductionSpecBundle,
    PromptRequest,
    QAPlan,
    SpecTraceRecord,
    SpecValidationReport,
    StrictModel,
    UnrealProjectPlan,
)
from fantasy_agent.corrections import inspect_corrections, summarize_corrections
from fantasy_agent.demo_launch import (
    DemoEngine,
    DemoLaunch,
    DemoLaunchError,
    infer_demo_engine,
    launch_demo,
    new_session_id,
    normalize_demo_resume,
    validate_session_id,
)
from fantasy_agent.evolution.contracts import EvolutionRequest
from fantasy_agent.evolution.controller import adopt_evolution, run_evolution, suggest_evolution
from fantasy_agent.evolution.library import EvolutionLibraryError, list_experiences, load_report
from fantasy_agent.generation import design_from_prompt
from fantasy_agent.godot_playtest import PlaytestResult
from fantasy_agent.local_tools import manual_correction_targets, open_manual_correction_target
from fantasy_agent.mcp import initial_mcp_contracts
from fantasy_agent.path_safety import WorkspacePathError, resolve_workspace_path
from fantasy_agent.planning_actions import PlanningAction, UnknownPlanningTool, run_planning_action
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from fantasy_agent.studio_projects import ProjectVersionConflict, StudioProjectStore
from fantasy_agent.studio_workflow import StudioWorkflowService
from fantasy_agent.tool_registry import tool_catalog
from fantasy_agent.workflow_authorization import WorkflowAuthorizationStore
from fantasy_agent.workflows import (
    build_asset_approval_manifest,
    prepare_blender_assets,
    prepare_comfyui_visuals,
    prepare_creative_review,
    prepare_godot_project,
    prepare_qa_plan,
    prepare_unreal_project,
)

STUDIO_NAME = "fantasy-agent-studio"
STUDIO_VERSION = "0.1.0"

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
FRONTEND_DIST_DIR = REPO_ROOT / "apps" / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"

#: For the degradations that are correct behaviour but invisible otherwise --
#: an orchestration snapshot that cannot be adopted reads as "no session" to the
#: board, so without this the only trace would be an empty stage list.
logger = logging.getLogger(__name__)


@asynccontextmanager
async def studio_lifespan(host: FastAPI):
    service = studio_workflow_service()
    # Loading/GET never reconciles jobs. A live service is reconciled once even
    # when test/application lifespan contexts are entered more than once.
    if getattr(host.state, "reconciled_service", None) is not service:
        service.recover_interrupted()
        host.state.reconciled_service = service
    transport = StudioMCPTransport(service, studio_mcp_connection())
    host.state.mcp_transport = transport
    async with transport.manager.run():
        yield
    host.state.mcp_transport = None


app = FastAPI(
    title="Fantasy Agent Studio",
    version=STUDIO_VERSION,
    description="Standalone local workbench for Fantasy Agent production workflows.",
    lifespan=studio_lifespan,
)

# The hand-written pages under `apps/studio/static/` are gone, along with the
# `/studio-static` and `/assets` mounts that served them. Every view -- `/`,
# `/workbench`, `/web-console` -- is a route inside the Vite bundle, and the
# bundle is the only thing served. Nothing here mounts a second UI or an HTML
# fallback: a missing dist is a loud 503, not a stale page.
if FRONTEND_DIST_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIST_DIR)), name="frontend_assets")


class ManualCorrectionOpenRequest(StrictModel):
    target_id: str
    engine: str = "UE5"
    confirmed_side_effects: bool = False


class ProjectBinding(StrictModel):
    project_id: str | None = Field(default=None, min_length=1)
    plan_version: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def paired_reference(self):
        if (self.project_id is None) != (self.plan_version is None):
            raise ValueError("项目和计划版本必须同时提供。")
        return self


class ReviewSubject(StrictModel):
    resource_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ApprovalManifestRequest(ProjectBinding):
    review: CreativeReviewReport
    target: str = "unreal"
    decisions: dict[str, str] = Field(default_factory=dict)
    production_spec_bundle: ProductionSpecBundle | None = None
    subjects: list[ReviewSubject] = Field(default_factory=list)


class ApprovalManifestResponse(BaseModel):
    status: str
    manifest_path: str
    manifest: AssetApprovalManifest
    production_spec_bundle: ProductionSpecBundle | None = None


class SpecBundlePreviewRequest(StrictModel):
    production_spec_bundle: ProductionSpecBundle
    target: str = "godot"


class SpecBundlePreviewResponse(BaseModel):
    validation: SpecValidationReport
    artifacts: list[CompiledSpecArtifact] = Field(default_factory=list)
    traces: list[SpecTraceRecord] = Field(default_factory=list)
    executable_qa: ExecutableQAReport


class AssetExecutionRequest(ProjectBinding):
    plan: DirectorBuildPlan
    with_assets: bool = False
    with_visuals: bool = False
    confirmed: bool = False


class AssetIngestRequest(ProjectBinding):
    """Ingest one local open-source asset file into the library.

    ``source_path`` points at a file on this machine -- the product is
    local-first and this endpoint never fetches from the network (see
    ``fantasy_agent/asset_library.py``'s module docstring). An absolute path is
    taken as the user pointing at a download they already have; a relative one
    resolves against the workspace.
    """

    name: str = Field(min_length=1, max_length=120)
    source_path: str = Field(min_length=1)
    license: str = ""
    author: str = ""
    source_url: str = ""
    notes: str = ""
    tags: list[str] = Field(default_factory=list)


class AssetIngestResponse(BaseModel):
    status: str
    entry: AssetLibraryEntry


class AssetRemoveResponse(BaseModel):
    status: str
    removed_id: str


class ExecuteDemoRequest(ProjectBinding):
    plan: DirectorBuildPlan
    engine: str = ""  # inferred from plan when empty
    with_assets: bool = False
    with_visuals: bool = False
    with_gameplay: bool = False
    enemy_tuning: EnemyPressureTuning = Field(default_factory=EnemyPressureTuning)
    approval_manifest_path: str | None = None
    confirmed: bool = False
    session_id: str = ""  # reuse an existing session when resuming
    resume_from: str = ""  # node to resume at; earlier done stages are skipped


# DirectorBuildPlan is imported from another module; ensure the forward
# reference is resolved so this model is fully defined.
ApprovalManifestRequest.model_rebuild()
ApprovalManifestResponse.model_rebuild()
SpecBundlePreviewRequest.model_rebuild()
SpecBundlePreviewResponse.model_rebuild()
AssetExecutionRequest.model_rebuild()
AssetIngestRequest.model_rebuild()
AssetIngestResponse.model_rebuild()
AssetRemoveResponse.model_rebuild()
ExecuteDemoRequest.model_rebuild()


# Jobs run on a single worker so we never launch two engines at once.
# They are intentionally in-memory because Studio is a local dev tool.
_EXECUTE_POOL = ThreadPoolExecutor(max_workers=1)
_EXECUTE_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)
_ASSET_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)
# A playtest holds an engine process for up to max_wall_seconds (3600 by
# contract). Sharing the one worker with execute/asset would let a single
# long playtest starve both other queues, so it gets its own pool: slow
# instead of blocking, which is the honest failure mode for a measurement job.
_PLAYTEST_POOL = ThreadPoolExecutor(max_workers=1)
_PLAYTEST_JOB_REGISTRY = InMemoryJobRegistry(_PLAYTEST_POOL)
_EVOLUTION_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)
_EVOLUTION_JOBS: dict[str, str] = {}


def studio_workflow_service() -> StudioWorkflowService:
    service = getattr(app.state, "workflow_service", None)
    if service is None:
        projects = StudioProjectStore(REPO_ROOT)
        service = StudioWorkflowService(
            projects,
            WorkflowAuthorizationStore(projects),
            execute_jobs=_EXECUTE_JOB_REGISTRY,
            asset_jobs=_ASSET_JOB_REGISTRY,
            playtest_jobs=_PLAYTEST_JOB_REGISTRY,
            evolution_jobs=_EVOLUTION_JOB_REGISTRY,
        )
        app.state.workflow_service = service
    return service


def studio_mcp_connection() -> MCPConnection:
    connection = getattr(app.state, "mcp_connection", None)
    if connection is None:
        connection = MCPConnection(REPO_ROOT)
        app.state.mcp_connection = connection
    return connection


class _MCPApplication:
    async def __call__(self, scope, receive, send):
        transport = getattr(app.state, "mcp_transport", None)
        if transport is None:
            await JSONResponse({"detail": "Studio 连接尚未就绪。"}, status_code=503)(
                scope, receive, send
            )
            return
        await transport(scope, receive, send)


# Exact path, no mount redirect and no second port or role-level endpoint.
app.add_route("/mcp", _MCPApplication(), methods=["GET", "POST", "DELETE"])


@app.middleware("http")
async def protect_local_workflow(request: Request, call_next):
    try:
        if request.client is None or not ipaddress.ip_address(request.client.host).is_loopback:
            return JSONResponse({"detail": "Studio 只允许本机访问。"}, status_code=403)
    except ValueError:
        return JSONResponse({"detail": "Studio 只允许本机访问。"}, status_code=403)
    if request.url.path.startswith(("/api/mcp/", "/api/projects")):
        if not local_request_allowed(
            request.scope, require_origin=request.method not in {"GET", "HEAD"}
        ):
            return JSONResponse({"detail": "仅允许同源本机操作。"}, status_code=403)
        body = await request.body()
        connection = studio_mcp_connection()
        try:
            decoded = json.loads(body) if body else None
        except (ValueError, UnicodeDecodeError):
            decoded = None
        if connection.contains_secret(body) or connection.contains_secret(decoded):
            return JSONResponse({"detail": "连接凭据不能写入项目数据。"}, status_code=400)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response
    return await call_next(request)


def _mcp_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _project_response(value: Any, *, status_code: int = 200) -> JSONResponse:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return JSONResponse(studio_mcp_connection().sanitize(value), status_code=status_code)


def _project_operation(operation: Callable[[], Any]) -> JSONResponse:
    try:
        return _project_response(operation())
    except ProjectVersionConflict as exc:
        return _project_response(
            {
                "status": "version_conflict",
                "summary": "计划版本已变化，请读取最新项目。",
                "latest": exc.latest.model_dump(mode="json"),
            },
            status_code=409,
        )
    except (ValueError, OSError):
        return _project_response(
            {"status": "blocked", "summary": "项目参数无效、产物已变化或状态无法读取。"},
            status_code=400,
        )


def _require_project(project_id: str) -> StudioWorkflowService:
    service = studio_workflow_service()
    try:
        found = service.projects.snapshot(project_id)
    except (ValueError, OSError):
        raise HTTPException(400, "项目标识或项目状态无效。") from None
    if found is None:
        raise HTTPException(404, "项目不存在。")
    return service


def _bound_request(req: ProjectBinding):
    if req.project_id is None:
        return None
    service = _require_project(req.project_id)
    snapshot = service.projects.snapshot(req.project_id)
    if snapshot.plan_version != req.plan_version:
        raise HTTPException(
            409,
            detail={
                "status": "version_conflict",
                "summary": "计划已变化，请刷新后确认。",
                "latest": service.snapshot(req.project_id),
            },
        )
    if snapshot.plan is None:
        raise HTTPException(400, detail="项目尚未保存计划。")
    if hasattr(req, "plan") and req.plan.model_dump(mode="json") != snapshot.plan.model_dump(
        mode="json"
    ):
        raise HTTPException(
            409,
            detail={
                "status": "version_conflict",
                "summary": "请先保存当前草稿再执行。",
                "latest": service.snapshot(req.project_id),
            },
        )
    return service, snapshot, service._root(req.project_id, req.plan_version)


def _request_root(req: ProjectBinding) -> Path:
    if req.project_id is None:
        return REPO_ROOT
    return studio_workflow_service()._root(req.project_id, req.plan_version)


def _durable_job_response(job_id: str):
    service = studio_workflow_service()
    found = service.locate_job(job_id)
    if found is None:
        return None
    project_id, job = found
    payload = service.get_job(project_id, job.job_id)
    result = payload.get("result", {})
    if isinstance(result, dict) and "data" in result and "kind" in result:
        payload["result"] = result["data"]
    if payload["status"] == "queued":
        payload["status"] = "running"
    return studio_mcp_connection().sanitize(payload)


def _validate_ui_subjects(snapshot, subjects: list[ReviewSubject]) -> list[str]:
    if not subjects:
        raise ValueError("尚无被审阅的产物版本，请先生成并刷新资产。")
    known = {
        resource.resource_id: resource
        for resource in snapshot.resources
        if resource.plan_version == snapshot.plan_version
    }
    for subject in subjects:
        resource = known.get(subject.resource_id)
        if resource is None or resource.sha256 != subject.sha256:
            raise ValueError("被审阅的资产版本已变化，请刷新后重新审阅。")
    return list(dict.fromkeys(subject.resource_id for subject in subjects))


class StudioProjectCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    plan: DirectorBuildPlan | None = None


class StudioProjectPlanRequest(StrictModel):
    plan: DirectorBuildPlan
    expected_version: int = Field(ge=0)


class StudioProjectImportRequest(StrictModel):
    plan: DirectorBuildPlan
    import_key: str = "legacy-handoff"


@app.get("/api/mcp/connection")
def mcp_connection_state(request: Request):
    return studio_mcp_connection().state(_mcp_base(request))


@app.post("/api/mcp/connection/enable")
def mcp_connection_enable(request: Request):
    studio_mcp_connection().set_enabled(True)
    return mcp_connection_state(request)


@app.post("/api/mcp/connection/disable")
def mcp_connection_disable(request: Request):
    studio_mcp_connection().set_enabled(False)
    return mcp_connection_state(request)


@app.post("/api/mcp/connection/token")
def mcp_connection_copy_token():
    return JSONResponse(
        {"token": studio_mcp_connection().copy_token()}, headers={"Cache-Control": "no-store"}
    )


@app.post("/api/mcp/connection/rotate")
def mcp_connection_rotate(request: Request):
    studio_mcp_connection().rotate()
    return mcp_connection_state(request)


@app.get("/api/mcp/connection/config")
def mcp_connection_config(request: Request):
    return studio_mcp_connection().config(_mcp_base(request))


@app.get("/api/projects")
def studio_projects_list():
    return _project_operation(
        lambda: {
            "projects": [
                studio_workflow_service().snapshot(p.project_id)
                for p in studio_workflow_service().projects.list_projects()
            ]
        }
    )


@app.post("/api/projects")
def studio_projects_create(payload: StudioProjectCreateRequest):
    def create():
        service = studio_workflow_service()
        project = service.projects.create(payload.name)
        if payload.plan is not None:
            service.save_plan(project.project_id, payload.plan, 0)
        return service.snapshot(project.project_id)

    return _project_operation(create)


@app.post("/api/projects/import")
def studio_projects_import(payload: StudioProjectImportRequest):
    def import_plan():
        service = studio_workflow_service()
        project = service.projects.import_legacy(payload.plan, import_key=payload.import_key)
        return service.snapshot(project.project_id)

    return _project_operation(import_plan)


@app.get("/api/projects/{project_id}")
def studio_project_get(project_id: str, plan_version: int | None = None):
    service = _require_project(project_id)
    return _project_operation(lambda: service.snapshot(project_id, plan_version))


@app.put("/api/projects/{project_id}/plan")
def studio_project_update_plan(project_id: str, payload: StudioProjectPlanRequest):
    service = _require_project(project_id)
    return _project_operation(
        lambda: service.save_plan(project_id, payload.plan, payload.expected_version)
    )


@app.get("/api/projects/{project_id}/workflow")
def studio_project_workflow(project_id: str, plan_version: int | None = None):
    service = _require_project(project_id)
    return _project_operation(lambda: service.workflow_state(project_id, plan_version))


@app.get("/api/projects/{project_id}/jobs/{job_id}")
def studio_project_job(project_id: str, job_id: str):
    service = _require_project(project_id)
    return _project_operation(lambda: service.get_job(project_id, job_id))


@app.post("/api/projects/{project_id}/jobs/{job_id}/cancel")
def studio_project_job_cancel(project_id: str, job_id: str):
    service = _require_project(project_id)
    return _project_operation(lambda: service.cancel_job(project_id, job_id))


@app.get("/api/projects/{project_id}/resources/{resource_id}")
def studio_project_resource(project_id: str, resource_id: str):
    service = _require_project(project_id)
    return _project_operation(lambda: service.read_resource(project_id, resource_id))


def _frontend_index_or() -> FileResponse:
    """Serve the Vite bundle's entry document, or fail loudly.

    This used to fall back to a hand-written static page when the bundle was
    absent. That fallback is what let two UIs drift apart unnoticed: the server
    answered 200 with the old page, so nothing looked broken, and the drift only
    surfaced when someone compared the two by hand.

    There is one UI now. If its build output is missing, say so with a 503 and
    the command that fixes it, rather than serving a page that is no longer
    maintained.
    """

    if not FRONTEND_INDEX_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Frontend bundle not found at {FRONTEND_INDEX_PATH}. "
                "Run `npm run frontend:build` from the repository root, then reload."
            ),
        )
    return FileResponse(FRONTEND_INDEX_PATH)


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


def _probe_comfyui() -> dict[str, Any]:
    """Report the ComfyUI service a run would actually talk to.

    Resolved through ``local_tools._comfyui_target()`` rather than probed
    again here. ComfyUI was the last target still probed twice: this module
    built its own candidate list from ``COMFYUI_URL`` / ``COMFYUI_ENDPOINT``
    without the local-only check ``_comfyui_target`` applies, so a panel
    pointed at a remote endpoint reported ``ready`` while every run refused
    the same endpoint -- the drift ``_probe_executable`` exists to prevent,
    and the reason its resolver is passed in instead of searched for again.

    The vocabulary stays the panel's (``ready`` / ``unavailable``); the
    resolver reports ``degraded`` because it also serves callers that need to
    distinguish "missing" from "broken".
    """

    target = local_tools._comfyui_target()
    if target["status"] == "ready":
        version = str(target["metadata"].get("version") or "reachable")
        return _mcp_status_item(
            service_id="comfyui",
            label="ComfyUI",
            status="ready",
            target=str(target["target"]),
            detail=f"Connected to ComfyUI ({version}).",
            next_action="Run capability probe before submitting visual reference jobs.",
            detail_key="mcpDetailComfyReady",
            detail_args={"version": version},
            next_action_key="mcpNextComfyReady",
            metadata={"version": version},
        )
    return _mcp_status_item(
        service_id="comfyui",
        label="ComfyUI",
        status="unavailable",
        target=str(target["target"]),
        detail="No local ComfyUI endpoint responded.",
        next_action="Start ComfyUI and confirm it is listening on 127.0.0.1:8188.",
        detail_key="mcpDetailComfyMissing",
        next_action_key="mcpNextComfyMissing",
        metadata={"failures": target["metadata"].get("failures", [])},
    )


def _probe_executable(
    *,
    service_id: str,
    label: str,
    candidates: str,
    resolver: Callable[[], str | None],
    next_action_ready: str,
    next_action_missing: str,
    next_action_ready_key: str,
    next_action_missing_key: str,
    required: bool = True,
) -> dict[str, Any]:
    """Report a local engine, resolving the path through ``local_tools``.

    The resolver is passed in rather than reimplemented here on purpose.
    Executables used to be probed twice -- once in ``local_tools``, which the
    executor actually launches, and once in this module -- and the two drifted:
    an engine installed to a custom Launcher root was found by the executor
    while the status panel still reported ``unavailable``. One resolver, one
    answer, so the panel cannot disagree with what a run would start.
    """

    executable = resolver()
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
        target=candidates,
        detail="No executable was found on PATH, in configured environment variables, or common install folders.",
        next_action=next_action_missing,
        detail_key="mcpDetailExecutableMissing",
        next_action_key=next_action_missing_key,
        required=required,
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
    return _probe_executable(
        service_id="godot",
        label="Godot",
        candidates="godot-console, godot4, godot, GODOT_EXECUTABLE",
        resolver=local_tools._find_godot,
        next_action_ready="Use Godot MCP validation for Godot-selected quick-play projects.",
        next_action_missing="Install Godot 4 or set GODOT_EXECUTABLE to the Godot executable.",
        next_action_ready_key="mcpNextGodotReady",
        next_action_missing_key="mcpNextGodotMissing",
        required=required,
    )


def _probe_unreal(required: bool) -> dict[str, Any]:
    """Report Unreal, naming the binary a tool call would actually start.

    ``local_tools._find_unreal`` returns ``UnrealEditor.exe``, but headless
    commandlets run through the sibling ``-Cmd`` build. Reporting only the
    editor would make a "ready" panel disagree with the process that gets
    launched, so the target is resolved exactly the way the executor does it.
    """

    editor = local_tools._find_unreal()
    if editor:
        return _mcp_status_item(
            service_id="unreal",
            label="Unreal Engine",
            status="ready",
            target=local_tools._unreal_cmd_executable(editor) or editor,
            detail="Executable found. MCP execution still requires explicit confirmation.",
            next_action="Use Unreal MCP validation before editor commandlets or PIE/package tests.",
            detail_key="mcpDetailExecutableReady",
            next_action_key="mcpNextUnrealReady",
            required=required,
            metadata={"editor": editor},
        )
    return _mcp_status_item(
        service_id="unreal",
        label="Unreal Engine",
        status="unavailable",
        target="UNREAL_EDITOR, UE_EDITOR, UnrealEditor-Cmd.exe, Epic Launcher manifest",
        detail="No executable was found on PATH, in configured environment variables, or common install folders.",
        next_action="Install UE5 or set UNREAL_EDITOR to UnrealEditor-Cmd.exe.",
        detail_key="mcpDetailExecutableMissing",
        next_action_key="mcpNextUnrealMissing",
        required=required,
    )


def _is_godot_engine(engine: str) -> bool:
    return "godot" in engine.casefold()


def _mcp_connectivity_status(engine: str = "UE5") -> dict[str, Any]:
    godot_selected = _is_godot_engine(engine)
    services = [
        _probe_comfyui(),
        _probe_executable(
            service_id="blender",
            label="Blender",
            candidates="BLENDER_EXECUTABLE, blender, C:/Program Files/Blender Foundation/Blender */blender.exe",
            resolver=local_tools._find_blender,
            next_action_ready="Generate Blender Python first, then execute only after confirmation.",
            next_action_missing="Install Blender or set BLENDER_EXECUTABLE to blender.exe.",
            next_action_ready_key="mcpNextBlenderReady",
            next_action_missing_key="mcpNextBlenderMissing",
        ),
        _probe_unreal(required=not godot_selected),
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


@app.get("/")
def index() -> FileResponse:
    return _frontend_index_or()


@app.get("/web-console")
def web_console() -> FileResponse:
    return _frontend_index_or()


@app.get("/pipeline")
def pipeline_board() -> FileResponse:
    """Serve the orchestration board.

    A route inside the SPA bundle like the other two: the board is a whole view,
    so it gets its own URL rather than only being reachable from the sidebar.
    """

    return _frontend_index_or()


@app.get("/assets")
def asset_library_page() -> FileResponse:
    """Serve the asset library.

    A whole view like the board, so it gets its own URL. Note this is *not* the
    ``/assets`` mount that used to serve the retired hand-written pages -- that
    mount is gone, and what answers here is the same SPA bundle as every other
    route. The old assertion "``/assets`` must not exist" therefore became
    wrong the moment the library got a page; the replacement assertion checks
    the bundle, not the path.
    """

    return _frontend_index_or()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": STUDIO_NAME, "version": STUDIO_VERSION, "mode": "standalone"}


@app.get("/api/tool-status")
def mcp_status(engine: str = "UE5") -> dict[str, Any]:
    return _mcp_connectivity_status(engine)


@app.get("/api/settings/llm")
def get_llm_settings() -> dict[str, Any]:
    """Return the saved API settings with the secret masked."""

    return public_settings()


class LLMApiSettingsRequest(StrictModel):
    enabled: bool = False
    provider: str = api_settings.ANTHROPIC
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    timeout_seconds: float = 60.0


LLMApiSettingsRequest.model_rebuild()


@app.put("/api/settings/llm")
def update_llm_settings(req: LLMApiSettingsRequest) -> Any:
    """Save API settings.

    An empty (or still-masked) key keeps the previously stored secret, so
    editing the model or base URL never forces re-entering the key.
    """

    incoming = req.model_dump()
    key = str(incoming.get("api_key") or "").strip()
    if not key or "*" in key:
        incoming["api_key"] = api_settings.load_settings().api_key
    try:
        saved = api_settings.save_settings(api_settings.LLMApiSettings.model_validate(incoming))
    except ValidationError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    return public_settings(saved)


@app.post("/api/settings/llm/test")
def test_llm_settings(req: LLMApiSettingsRequest) -> dict[str, Any]:
    """Probe the endpoint with a minimal request and report the outcome."""

    incoming = req.model_dump()
    key = str(incoming.get("api_key") or "").strip()
    if not key or "*" in key:
        incoming["api_key"] = api_settings.load_settings().api_key
    try:
        candidate = api_settings.LLMApiSettings.model_validate(incoming)
    except ValidationError as exc:
        return api_settings.ApiTestResult(
            ok=False, status="invalid", detail_key="apiTestInvalid", detail=str(exc)
        ).model_dump()
    result = api_settings.test_connection(candidate)
    payload = result.model_dump()
    payload["settings"] = public_settings(candidate)
    return payload


@app.delete("/api/settings/llm")
def delete_llm_settings() -> dict[str, Any]:
    """Forget the stored credentials and return to deterministic-only mode."""

    return public_settings(api_settings.clear_settings())


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


@app.get("/api/corrections/inspect")
def corrections_inspect(project_dir: str) -> dict[str, Any]:
    """Report hand edits in a generated project. Read-only, so no gate.

    The scan starts no process and writes nothing: it compares the artifacts
    against the hashes and anchor values this build recorded, and answers
    "is my edit still there, and can it be saved". That is a question, not an
    action, so it does not take a confirmation -- the two-step gate exists for
    calls that touch the disk, and pretending otherwise would train the
    operator to click through it.
    """

    if not project_dir.strip():
        raise HTTPException(status_code=400, detail="project_dir is required")
    try:
        resolve_workspace_path(project_dir, workspace_root=REPO_ROOT)
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = inspect_corrections(project_dir, workspace_root=REPO_ROOT)
    return {"report": report.model_dump(mode="json"), "summary": summarize_corrections(report)}


def _planning(name: str, request: PromptRequest) -> PlanningAction:
    """Run one prompt-shaped planning action with the Studio LLM switch."""

    return run_planning_action(name, request.model_dump(mode="json"), use_llm=llm_enabled())


@app.post("/api/plan", response_model=DirectorBuildPlan)
def plan(request: PromptRequest) -> DirectorBuildPlan:
    return _planning("generate_game_production_plan", request).require_plan()


@app.post("/api/tasks", response_model=DirectorTaskBreakdown)
def tasks(request: PromptRequest) -> DirectorTaskBreakdown:
    return _planning("decompose_production_tasks", request).require_breakdown()


@app.get("/api/tool-contracts")
def tool_contracts() -> list[Any]:
    """Local tool contracts inspected before any execution side effect."""

    return initial_mcp_contracts()


@app.get("/api/tool-catalog")
def tool_catalog_endpoint() -> dict[str, Any]:
    """Every callable tool with the permission tier the gate will enforce.

    ``/api/tool-contracts`` is the declared inventory; this is the enforced one.
    The Agent panel shows it so an operator can see which tools the model was
    offered and which of them need a grant -- the tiers come from the registry
    that actually gates the call, not from a second hand-typed list.
    """

    return tool_catalog()


class IdeaSeedResponse(BaseModel):
    idea_seed: IdeaSeed
    prompt_request: PromptRequest


IdeaSeedResponse.model_rebuild()


@app.post("/api/idea-seed", response_model=IdeaSeedResponse)
def idea_seed(request: IdeaDiscoveryRequest) -> IdeaSeedResponse:
    """Turn interview answers into an IdeaSeed and a ready-to-plan PromptRequest."""

    action = run_planning_action(
        "extract_idea_seed",
        request.model_dump(mode="json"),
        use_llm=llm_enabled(),
    )
    if action.seed is None or action.prompt_request is None:
        raise RuntimeError("extract_idea_seed did not produce a seed")
    return IdeaSeedResponse(idea_seed=action.seed, prompt_request=action.prompt_request)


@app.post("/api/design", response_model=GameplaySpec)
def design(request: PromptRequest) -> GameplaySpec:
    return design_from_prompt(request, use_llm=llm_enabled())


@app.post("/api/gdd", response_model=GDDDocument)
def gdd(request: PromptRequest) -> GDDDocument:
    return _planning("render_gdd", request).require_plan().gdd


@app.post("/api/pipeline")
def pipeline(request: PromptRequest) -> dict[str, Any]:
    built = _planning("prepare_production_pipeline", request).require_plan()
    return {
        "gameplay_title": built.gameplay_spec.title,
        "production_pipeline": (
            built.production_pipeline.model_dump(mode="json") if built.production_pipeline else None
        ),
    }


@app.post("/api/unreal/plan", response_model=UnrealProjectPlan)
def unreal_plan(spec: GameplaySpec) -> UnrealProjectPlan:
    return prepare_unreal_project(spec)


@app.post("/api/godot/plan", response_model=GodotProjectPlan)
def godot_plan(spec: GameplaySpec) -> GodotProjectPlan:
    return prepare_godot_project(spec)


@app.post("/api/blender/plan", response_model=BlenderAssetPlan)
def blender_plan(spec: GameplaySpec) -> BlenderAssetPlan:
    return prepare_blender_assets(spec)


@app.post("/api/blender/script", response_model=BlenderScriptArtifact)
def blender_script(plan: BlenderAssetPlan) -> BlenderScriptArtifact:
    return build_blender_script_artifact(plan)


@app.post("/api/blender/plan-script", response_model=BlenderScriptArtifact)
def blender_plan_script(spec: GameplaySpec) -> BlenderScriptArtifact:
    return build_blender_script_artifact(prepare_blender_assets(spec))


@app.post("/api/comfyui/plan", response_model=ComfyUIVisualPlan)
def comfyui_plan(spec: GameplaySpec) -> ComfyUIVisualPlan:
    return prepare_comfyui_visuals(spec)


@app.post("/api/creative-review", response_model=CreativeReviewReport)
def creative_review(request: CreativeReviewRequest) -> CreativeReviewReport:
    return prepare_creative_review(
        request.gameplay_spec,
        request.blender_plan,
        request.comfyui_plan,
    )


@app.post("/api/qa", response_model=QAPlan)
def qa(spec: GameplaySpec) -> QAPlan:
    return prepare_qa_plan(spec)


def _plan_summary(plan: DirectorBuildPlan) -> dict[str, Any]:
    """Flatten a build plan into the summary block the workbench UI renders."""

    spec = plan.gameplay_spec
    pipeline = plan.production_pipeline
    return {
        "title": spec.title,
        "logline": spec.logline,
        "target_session_minutes": spec.target_session_minutes,
        "core_verbs": spec.core_verbs,
        "design_pillars": spec.design_pillars,
        "win_state": spec.win_state,
        "failure_states": spec.failure_states,
        "next_actions": plan.next_actions,
        "production_pipeline_stages": [stage.title for stage in pipeline.stages]
        if pipeline
        else [],
    }


def _workbench_result(
    tool_name: str,
    structured_content: dict[str, Any],
    content_text: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shape a planning result for the workbench UI without an external agent bridge."""

    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": content_text}],
        "_meta": {"toolName": tool_name, **(meta or {})},
    }


def _plan_headline(prefix: str, plan: DirectorBuildPlan) -> str:
    spec = plan.gameplay_spec
    next_action = plan.next_actions[0] if plan.next_actions else "Review the generated plan."
    return (
        f"{prefix}: {spec.title}. "
        f"Target session: {spec.target_session_minutes} minutes. "
        f"Core verbs: {', '.join(spec.core_verbs)}. "
        f"Next action: {next_action}"
    )


def _seed_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    if action.seed is None or action.prompt_request is None:
        raise RuntimeError("extract_idea_seed did not produce a seed")
    seed_payload = action.seed.model_dump(mode="json")
    prompt_payload = action.prompt_request.model_dump(mode="json")
    text = (
        "Extracted an IdeaSeed for planning. "
        f"Core action: {action.seed.core_action}. "
        "Next step: generate a production plan from the seed."
    )
    return (
        {"idea_seed": seed_payload, "prompt_request": prompt_payload},
        text,
        {
            "ideaSeed": seed_payload,
            "promptRequest": prompt_payload,
            "activePanel": "discovery",
        },
    )


def _tasks_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    breakdown = action.require_breakdown()
    payload = breakdown.model_dump(mode="json")
    text = (
        f"Prepared {len(breakdown.tasks)} production tasks. "
        f"Recommended next task: {breakdown.recommended_next_task}. "
        "Execution tasks still require explicit confirmation."
    )
    return (
        {"task_breakdown": payload},
        text,
        {"taskBreakdown": payload, "activePanel": "tasks"},
    )


def _full_plan_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    plan_payload = built.model_dump(mode="json")
    task_payload = _json_model(built.task_breakdown)
    pipeline_payload = _json_model(built.production_pipeline)
    return (
        {
            "summary": _plan_summary(built),
            "plan": plan_payload,
            "task_breakdown": task_payload,
            "production_pipeline": pipeline_payload,
        },
        _plan_headline("Generated full production plan", built),
        {
            "plan": plan_payload,
            "taskBreakdown": task_payload,
            "productionPipeline": pipeline_payload,
            "activePanel": "overview",
        },
    )


def _gdd_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    gdd_payload = built.gdd.model_dump(mode="json")
    return (
        {"summary": _plan_summary(built), "gdd": gdd_payload},
        _plan_headline("Rendered GDD", built),
        {"gdd": gdd_payload, "activePanel": "gdd"},
    )


def _pipeline_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    pipeline_payload = _json_model(built.production_pipeline)
    return (
        {"summary": _plan_summary(built), "production_pipeline": pipeline_payload},
        _plan_headline("Prepared production pipeline", built),
        {"productionPipeline": pipeline_payload, "activePanel": "pipeline"},
    )


def _unreal_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    payload = built.unreal_plan.model_dump(mode="json")
    title = built.gameplay_spec.title
    text = f"Prepared Unreal handoff for {title}: {', '.join(built.unreal_plan.maps)}."
    return (
        {"gameplay_title": title, "unreal_plan": payload},
        text,
        {"unrealPlan": payload, "activePanel": "build"},
    )


def _godot_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    payload = built.godot_plan.model_dump(mode="json")
    title = built.gameplay_spec.title
    text = f"Prepared Godot quick-play handoff for {title}: {', '.join(built.godot_plan.scenes)}."
    return (
        {"gameplay_title": title, "godot_plan": payload},
        text,
        {"godotPlan": payload, "activePanel": "build"},
    )


def _blender_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    payload = built.blender_plan.model_dump(mode="json")
    title = built.gameplay_spec.title
    text = f"Prepared {len(built.blender_plan.jobs)} Blender greybox asset jobs for {title}."
    return (
        {"gameplay_title": title, "blender_plan": payload},
        text,
        {"blenderPlan": payload, "activePanel": "build"},
    )


def _comfyui_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    payload = built.comfyui_plan.model_dump(mode="json")
    title = built.gameplay_spec.title
    text = f"Prepared {len(built.comfyui_plan.jobs)} ComfyUI visual reference jobs for {title}."
    return (
        {"gameplay_title": title, "comfyui_plan": payload},
        text,
        {"comfyuiPlan": payload, "activePanel": "visuals"},
    )


def _review_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    payload = built.creative_review.model_dump(mode="json")
    title = built.gameplay_spec.title
    text = (
        f"Prepared {len(built.creative_review.items)} creative review items for {title}. "
        "Unreal ingest remains blocked until user approvals are recorded."
    )
    return (
        {"gameplay_title": title, "creative_review": payload},
        text,
        {"creativeReview": payload, "activePanel": "visuals"},
    )


def _qa_envelope(action: PlanningAction) -> tuple[dict[str, Any], str, dict[str, Any]]:
    built = action.require_plan()
    payload = built.qa_plan.model_dump(mode="json")
    title = built.gameplay_spec.title
    text = (
        f"Prepared QA checks for a {built.qa_plan.target_session_minutes}-minute slice of {title}."
    )
    return (
        {"gameplay_title": title, "qa_plan": payload},
        text,
        {"qaPlan": payload, "activePanel": "qa"},
    )


_ENVELOPE_BUILDERS = {
    "extract_idea_seed": _seed_envelope,
    "decompose_production_tasks": _tasks_envelope,
    "generate_game_production_plan": _full_plan_envelope,
    "render_gdd": _gdd_envelope,
    "prepare_production_pipeline": _pipeline_envelope,
    "prepare_unreal_plan": _unreal_envelope,
    "prepare_godot_plan": _godot_envelope,
    "prepare_blender_plan": _blender_envelope,
    "prepare_comfyui_plan": _comfyui_envelope,
    "prepare_creative_review_plan": _review_envelope,
    "prepare_qa_plan": _qa_envelope,
}


def _json_model(model: Any) -> Any:
    if model is None:
        return None
    return model.model_dump(mode="json")


def _workbench_envelope(action: PlanningAction) -> dict[str, Any]:
    structured, content_text, meta = _ENVELOPE_BUILDERS[action.name](action)
    return _workbench_result(
        action.name,
        {"kind": action.kind, **structured},
        content_text,
        meta,
    )


def _workbench_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Adapt one planning action into the envelope the workbench already reads."""

    try:
        action = run_planning_action(name, arguments, use_llm=llm_enabled())
    except UnknownPlanningTool as exc:
        return {
            "isError": True,
            "content": [{"type": "text", "text": str(exc)}],
        }
    return _workbench_envelope(action)


@app.get("/workbench")
def workbench() -> FileResponse:
    """Serve the React planning workbench.

    ``/workbench`` used to be an unconditional ``FileResponse`` around a
    hand-written static page. That page is gone; the workbench now lives in
    ``apps/frontend/src/workbench`` and is routed by pathname inside the SPA
    bundle, exactly like ``/web-console``.
    """

    return _frontend_index_or()


@app.post("/api/tools/{tool_name}")
async def workbench_tool(tool_name: str, request: Request) -> dict[str, Any]:
    """Data endpoint for the local planning workbench page."""

    arguments = await request.json()
    return _workbench_tool(tool_name, arguments or {})


def _approval_manifest_path() -> Path:
    path = REPO_ROOT / "generated" / "asset-approval-manifest.yaml"
    resolved = path.resolve()
    generated_root = (REPO_ROOT / "generated").resolve()
    if generated_root not in resolved.parents and resolved != generated_root:
        raise RuntimeError("approval manifest path must stay under generated/")
    return resolved


@app.post("/api/specs/preview", response_model=SpecBundlePreviewResponse)
def preview_spec_bundle(req: SpecBundlePreviewRequest) -> SpecBundlePreviewResponse:
    from fantasy_agent.production_spec_runtime import compile_production_spec_bundle
    from fantasy_agent.spec_validation import validate_production_spec_bundle
    from fantasy_agent.unreal_spec_adapter import evaluate_executable_qa

    validation = validate_production_spec_bundle(req.production_spec_bundle)
    bundle = req.production_spec_bundle.model_copy(update={"validation": validation})
    artifacts: list[CompiledSpecArtifact] = []
    traces: list[SpecTraceRecord] = []
    if validation.status != "failed":
        compiled = compile_production_spec_bundle(bundle, target=req.target)
        artifacts = compiled.artifacts
        traces = compiled.traces
    return SpecBundlePreviewResponse(
        validation=validation,
        artifacts=artifacts,
        traces=traces,
        executable_qa=evaluate_executable_qa(bundle),
    )


@app.post("/api/creative-review/approval-manifest", response_model=ApprovalManifestResponse)
def write_approval_manifest(req: ApprovalManifestRequest) -> ApprovalManifestResponse:
    import yaml

    binding = _bound_request(req)
    if binding is not None:
        service, snapshot, _root = binding
        try:
            resource_ids = _validate_ui_subjects(snapshot, req.subjects)
            review = service.asset_review.review_report(snapshot)
            by_resource = {item.resource_id: item for item in review.items}
            for resource_id in resource_ids:
                item = by_resource[resource_id]
                decision = req.decisions.get(item.asset_id, "pending_user_review")
                if decision not in {"approved", "rejected", "needs_revision"}:
                    continue
                intent = service.request_asset_review(
                    req.project_id, plan_version=snapshot.plan_version, resource_ids=[resource_id]
                )
                service.apply_asset_review(
                    req.project_id,
                    intent["intent_id"],
                    approved=decision == "approved",
                    decision=decision,
                )
            manifest = service.asset_review.write_manifest(req.project_id, snapshot.plan_version)
            effective = service.asset_review.effective_plan(req.project_id, snapshot.plan_version)
            return ApprovalManifestResponse(
                status="written",
                manifest_path="generated/asset-approval-manifest.yaml",
                manifest=manifest,
                production_spec_bundle=effective.production_spec_bundle,
            )
        except (ValueError, OSError) as exc:
            raise HTTPException(409, detail=str(exc)) from exc

    try:
        manifest = build_asset_approval_manifest(
            req.review,
            req.decisions,
            target=req.target,
            workspace_root=REPO_ROOT,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Reviewed artifact is missing: {exc.filename or exc}",
        ) from exc
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Reviewed artifact cannot be read: {exc}",
        ) from exc
    path = _approval_manifest_path()
    # Atomic, because this file is a gate: the approval stage reads it back to
    # decide whether writing is allowed. A half-written manifest would parse as
    # a missing gate rather than as a failed save.
    write_atomic(
        path,
        yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
    )
    rel = path.relative_to(REPO_ROOT).as_posix()
    synced_bundle = None
    if req.production_spec_bundle is not None:
        from fantasy_agent.production_spec_runtime import sync_bundle_with_approval_manifest

        synced_bundle = sync_bundle_with_approval_manifest(
            req.production_spec_bundle,
            manifest,
        )
        bundle_path = REPO_ROOT / "generated" / "specs" / "production-spec-bundle.yaml"
        # Same reason as the manifest, and free: the helper is already here.
        write_atomic(
            bundle_path,
            yaml.safe_dump(
                synced_bundle.model_dump(mode="json"),
                sort_keys=False,
                allow_unicode=True,
            ),
        )
    return ApprovalManifestResponse(
        status="written",
        manifest_path=rel,
        manifest=manifest,
        production_spec_bundle=synced_bundle,
    )


def _build_asset_execution_result(
    req: AssetExecutionRequest, *, confirmed: bool, session_id: str = ""
):
    from datetime import UTC, datetime

    from fantasy_agent.executor import execute_asset_pipeline
    from fantasy_agent.local_tools import _find_blender

    session_id = session_id or datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return execute_asset_pipeline(
        req.plan,
        session_id=session_id,
        confirmed=confirmed,
        workspace_root=_request_root(req),
        with_assets=req.with_assets,
        blender_exe=_find_blender() or "blender",
        with_visuals=req.with_visuals,
    )


@app.post("/api/assets/execute")
def execute_assets(req: AssetExecutionRequest) -> dict[str, Any]:
    binding = _bound_request(req)
    if not req.confirmed:
        preview = _build_asset_execution_result(req, confirmed=False)
        return _ASSET_JOB_REGISTRY.preview(preview)

    if binding is not None:
        service, snapshot, _ = binding
        session_id = f"assets-{uuid4().hex}"
        return service.submit_ui_job(
            req.project_id,
            plan_version=snapshot.plan_version,
            tool_name="execute_assets",
            arguments={"with_assets": req.with_assets, "with_visuals": req.with_visuals},
            worker=lambda: _build_asset_execution_result(
                req, confirmed=req.confirmed, session_id=session_id
            ),
            confirmed_by_user=req.confirmed,
            session_id=session_id,
        )

    job_id = _ASSET_JOB_REGISTRY.submit(lambda: _build_asset_execution_result(req, confirmed=True))
    return {"status": "running", "job_id": job_id}


@app.get("/api/assets/execute/{job_id}")
def asset_execute_status(job_id: str) -> dict[str, Any]:
    return _durable_job_response(job_id) or _ASSET_JOB_REGISTRY.status(job_id)


@app.post("/api/assets/execute/{job_id}/cancel")
def asset_execute_cancel(job_id: str) -> dict[str, Any]:
    service = studio_workflow_service()
    if found := service.locate_job(job_id):
        return service.cancel_job(found[0], found[1].job_id)
    return _ASSET_JOB_REGISTRY.cancel(job_id)


@app.get("/api/assets")
def asset_library_overview_endpoint(
    project_id: str | None = None,
    plan_version: int | None = None,
) -> AssetLibraryOverview:
    """Everything the asset panel renders: ingested entries + review decisions.

    Read-only and synchronous -- it reads two YAML files and decides nothing,
    so there is no job to poll and no approval flag to thread. A manifest that
    exists but cannot be parsed answers 400 rather than an empty generated
    list: "nothing was generated" is a claim, and a broken file is not
    evidence for it.
    """

    if (project_id is None) != (plan_version is None):
        raise HTTPException(422, "项目和计划版本必须同时提供。")
    root = REPO_ROOT
    if project_id is not None:
        service = _require_project(project_id)
        try:
            service._snapshot(project_id, plan_version)
            root = service._root(project_id, plan_version)
        except ValueError as exc:
            raise HTTPException(404, "项目计划版本不存在。") from exc
    try:
        return library_overview(workspace_root=root)
    except AssetLibraryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/assets")
def asset_ingest_endpoint(req: AssetIngestRequest) -> AssetIngestResponse:
    """Copy one local file into the library and record its provenance.

    Synchronous on purpose: the work is a single local file copy, seconds at
    most, so a job registry would buy nothing but a polling round-trip. This
    is the one write in the asset surface that needs no two-step confirmation
    -- it copies a file the user explicitly named, launches no process, and
    burns no engine time.
    """

    binding = _bound_request(req)
    try:
        with binding[0].projects._lock if binding else nullcontext():
            if binding:
                _bound_request(req)
            arguments = req.model_dump(exclude={"project_id", "plan_version"})
            if binding:
                arguments = binding[0]._arguments("ingest_asset", arguments)
            entry = ingest_asset(**arguments, workspace_root=binding[2] if binding else REPO_ROOT)
            if binding:
                service, _, root = binding
                service.projects.register_resource(
                    req.project_id,
                    resource_id=entry.id,
                    kind="asset",
                    asset_key=entry.id,
                    path=(root / entry.path)
                    .relative_to(service.projects.production_workspace(req.project_id))
                    .as_posix(),
                    plan_version=req.plan_version,
                    sha256=entry.sha256,
                )
    except AssetLibraryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"资产无法读取：{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AssetIngestResponse(status="ingested", entry=entry)


@app.delete("/api/assets/{asset_id}")
def asset_remove_endpoint(
    asset_id: str,
    project_id: str | None = None,
    plan_version: int | None = None,
) -> AssetRemoveResponse:
    """Remove one library entry and delete its copy inside the library.

    The id is matched as a plain string and never becomes part of a path --
    ``remove_asset`` re-resolves the entry's own recorded path -- so there is
    no segment-safety question here of the kind ``session_id`` has. An unknown
    id is a 404, not a 400: the request was well-formed, the thing is absent.
    """

    if (project_id is None) != (plan_version is None):
        raise HTTPException(422, "项目和计划版本必须同时提供。")
    binding = _bound_request(ProjectBinding(project_id=project_id, plan_version=plan_version))
    try:
        with binding[0].projects._lock if binding else nullcontext():
            if binding:
                _bound_request(ProjectBinding(project_id=project_id, plan_version=plan_version))
            root = binding[2] if binding else REPO_ROOT
            entry = remove_asset(asset_id, workspace_root=root)
            if binding and entry is not None:
                service = binding[0]
                service.projects.remove_asset_resources(
                    project_id,
                    (root / entry.path)
                    .relative_to(service.projects.production_workspace(project_id))
                    .as_posix(),
                    expected_version=plan_version,
                )
                service.asset_review.write_manifest(project_id, plan_version)
    except AssetLibraryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail=f"资产不存在：{asset_id!r}")
    return AssetRemoveResponse(status="removed", removed_id=entry.id)


class PlaytestRunRequest(PlaytestRequest, ProjectBinding):
    """Wire shape of one playtest run.

    It inherits the library contract instead of restating it, so the bounds
    (runs, frame budget, wall clock, input plan) have exactly one definition.
    That also means FastAPI validates them at the edge: an out-of-range
    ``runs`` answers 422 instead of raising inside the job and surfacing as a
    500 the poller cannot explain.
    """

    confirmed: bool = False
    session_id: str = ""


def _playtest_request(req: PlaytestRunRequest) -> PlaytestRequest:
    return PlaytestRequest(
        **req.model_dump(exclude={"confirmed", "session_id", "project_id", "plan_version"})
    )


def _build_playtest_result(req: PlaytestRunRequest, *, confirmed: bool) -> PlaytestResult:
    from fantasy_agent.godot_playtest import (
        planned_playtest_side_effects,
        run_playtest,
        summarize_playtest,
    )

    request = _playtest_request(req)
    if not confirmed:
        return PlaytestResult(
            status="confirmation_required",
            project_dir=req.project_dir,
            planned_side_effects=planned_playtest_side_effects(request),
        )
    report = run_playtest(
        request, workspace_root=_request_root(req), session_id=req.session_id or None
    )
    # "done" is the *job* status the poller understands; the verdict lives in
    # report.status, so a run that measured a failure is still a run that ran.
    return PlaytestResult(
        status="done",
        project_dir=req.project_dir,
        report=report,
        planned_side_effects=planned_playtest_side_effects(request),
        summary=summarize_playtest(report),
    )


@app.post("/api/playtest/run")
def run_playtest_job(req: PlaytestRunRequest) -> dict[str, Any]:
    binding = _bound_request(req)
    if binding is not None:
        resolve_workspace_path(req.project_dir, workspace_root=binding[2], allow_absolute=True)
    if not req.confirmed:
        return _PLAYTEST_JOB_REGISTRY.preview(_build_playtest_result(req, confirmed=False))

    if binding is not None:
        service, snapshot, _ = binding
        request = req.model_copy(update={"session_id": req.session_id or f"playtest-{uuid4().hex}"})
        return service.submit_ui_job(
            req.project_id,
            plan_version=snapshot.plan_version,
            tool_name="playtest_godot_project",
            arguments=_playtest_request(req).model_dump(mode="json"),
            confirmed_by_user=req.confirmed,
            worker=lambda: _build_playtest_result(request, confirmed=request.confirmed),
            session_id=request.session_id,
        )

    job_id = _PLAYTEST_JOB_REGISTRY.submit(lambda: _build_playtest_result(req, confirmed=True))
    return {"status": "running", "job_id": job_id}


@app.get("/api/playtest/{job_id}")
def playtest_status(job_id: str) -> dict[str, Any]:
    return _durable_job_response(job_id) or _PLAYTEST_JOB_REGISTRY.status(job_id)


@app.post("/api/playtest/{job_id}/cancel")
def playtest_cancel(job_id: str) -> dict[str, Any]:
    service = studio_workflow_service()
    if found := service.locate_job(job_id):
        return service.cancel_job(found[0], found[1].job_id)
    return _PLAYTEST_JOB_REGISTRY.cancel(job_id)


class EvolutionPlanRequest(ProjectBinding):
    plan: DirectorBuildPlan


class EvolutionAdoptRequest(EvolutionPlanRequest):
    feedback: str = Field(default="", max_length=4000)


class StudioEvolutionRequest(EvolutionRequest, ProjectBinding):
    pass


EvolutionPlanRequest.model_rebuild(_types_namespace={"DirectorBuildPlan": DirectorBuildPlan})
EvolutionAdoptRequest.model_rebuild(_types_namespace={"DirectorBuildPlan": DirectorBuildPlan})


@app.get("/api/evolution/experiences")
def evolution_experiences() -> dict[str, Any]:
    try:
        experiences = list_experiences(workspace_root=REPO_ROOT)
    except EvolutionLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"experiences": [item.model_dump(mode="json") for item in experiences]}


@app.post("/api/evolution/suggest")
def evolution_suggest(req: EvolutionPlanRequest) -> dict[str, Any]:
    binding = _bound_request(req)
    try:
        suggestion = suggest_evolution(
            req.plan,
            workspace_root=(
                binding[0].projects.production_workspace(req.project_id) if binding else REPO_ROOT
            ),
        )
    except EvolutionLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "plan": suggestion.plan.model_dump(mode="json"),
        "changes": [item.model_dump(mode="json") for item in suggestion.changes],
        "experience_id": suggestion.experience_id,
        "notes": suggestion.notes,
    }


@app.post("/api/evolution/run")
def evolution_run(req: StudioEvolutionRequest) -> dict[str, Any]:
    binding = _bound_request(req)
    root = _request_root(req)
    request = EvolutionRequest.model_validate(
        req.model_dump(exclude={"project_id", "plan_version"})
    )
    experiment_id = f"evolution-{uuid4().hex[:12]}"
    try:
        preview = run_evolution(
            request.model_copy(update={"confirmed": False}),
            experiment_id=experiment_id,
            workspace_root=root,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not req.confirmed:
        return _EVOLUTION_JOB_REGISTRY.preview(preview)
    if binding is not None:
        service, snapshot, _ = binding
        started = service.submit_ui_job(
            req.project_id,
            plan_version=snapshot.plan_version,
            tool_name="run_evolution",
            arguments={
                **request.model_dump(mode="json", exclude={"plan", "confirmed"}),
                "experiment_id": experiment_id,
            },
            worker=lambda: run_evolution(
                request,
                experiment_id=experiment_id,
                workspace_root=root,
                experience_workspace_root=service.projects.production_workspace(req.project_id),
            ),
            confirmed_by_user=req.confirmed,
            session_id=experiment_id,
        )
        _EVOLUTION_JOBS[experiment_id] = started["job_id"]
        return {**started, "experiment_id": experiment_id}
    job_id = _EVOLUTION_JOB_REGISTRY.submit(
        lambda: run_evolution(
            request,
            experiment_id=experiment_id,
            workspace_root=REPO_ROOT,
        )
    )
    _EVOLUTION_JOBS[experiment_id] = job_id
    return {"status": "running", "experiment_id": experiment_id, "job_id": job_id}


@app.get("/api/evolution/{experiment_id}")
def evolution_status(experiment_id: str) -> dict[str, Any]:
    durable = _durable_job_response(experiment_id)
    if durable is not None:
        return {
            **durable,
            "experiment_id": experiment_id,
            "report": durable.get("result", {}).get("report"),
        }
    try:
        report = load_report(experiment_id, workspace_root=REPO_ROOT)
    except EvolutionLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job_id = _EVOLUTION_JOBS.get(experiment_id)
    job = _EVOLUTION_JOB_REGISTRY.status(job_id) if job_id else None
    if job is not None:
        payload = {
            "status": job["status"],
            "experiment_id": experiment_id,
            "report": report.model_dump(mode="json") if report else None,
        }
        if job.get("error"):
            payload["error"] = job["error"]
        return payload
    if report is None:
        return {"status": "unknown", "experiment_id": experiment_id, "report": None}
    if report.status == "running":
        # Cold GET only describes the lost worker, never registers or restarts it.
        report = report.model_copy(
            update={
                "status": "interrupted",
                "notes": [*report.notes, "Studio 已重启，实验中断；可明确开始新实验。"],
            }
        )
    status = report.status if report.status in {"cancelled", "failed", "interrupted"} else "done"
    return {
        "status": status,
        "experiment_id": experiment_id,
        "report": report.model_dump(mode="json"),
    }


@app.post("/api/evolution/{experiment_id}/cancel")
def evolution_cancel(experiment_id: str) -> dict[str, Any]:
    service = studio_workflow_service()
    if found := service.locate_job(experiment_id):
        return {**service.cancel_job(found[0], found[1].job_id), "experiment_id": experiment_id}
    job_id = _EVOLUTION_JOBS.get(experiment_id)
    if job_id is None:
        return evolution_status(experiment_id)
    return {**_EVOLUTION_JOB_REGISTRY.cancel(job_id), "experiment_id": experiment_id}


@app.post("/api/evolution/{experiment_id}/adopt")
def evolution_adopt(experiment_id: str, req: EvolutionAdoptRequest) -> dict[str, Any]:
    binding = _bound_request(req)
    if binding is not None:
        service, snapshot, _ = binding
        with service.projects._lock:
            _bound_request(req)
            found = service.locate_job(experiment_id)
            if found is None or found[0] != req.project_id:
                raise HTTPException(404, "该实验不属于当前项目。")
            intent = service.request_candidate_adoption(
                req.project_id,
                plan_version=snapshot.plan_version,
                job_id=found[1].job_id,
            )
            # This REST action is the existing panel's explicit adoption click;
            # the external MCP registry has no apply/confirmed entry point.
            result = service.apply_candidate_adoption(
                req.project_id,
                intent["intent_id"],
                approved=True,
                feedback=req.feedback,
            )
            return {**result, **service.snapshot(req.project_id)}
    try:
        if load_report(experiment_id, workspace_root=REPO_ROOT) is None:
            raise HTTPException(status_code=404, detail="实验不存在。")
        plan, experience = adopt_evolution(
            experiment_id,
            req.plan,
            feedback=req.feedback,
            workspace_root=REPO_ROOT,
        )
    except EvolutionLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "status": "adopted",
        "plan": plan.model_dump(mode="json"),
        "experience": experience.model_dump(mode="json"),
    }


def _resume_http_detail(exc: DemoLaunchError) -> str:
    """Studio keeps its own sentences; the library error speaks CLI English."""

    if exc.code == "resume_needs_session":
        return "resume_from 需要同时提供 session_id，否则无法复用已完成的节点"
    if exc.code == "resume_not_supported":
        return "Unreal 续跑还没接线，不能在 Unreal 上静默忽略 resume_from"
    return str(exc)


def _demo_request(req: ExecuteDemoRequest, *, confirmed: bool, session_id: str) -> DemoLaunch:
    return DemoLaunch(
        plan=req.plan,
        engine=req.engine,
        confirmed=confirmed,
        session_id=session_id,
        resume_from=req.resume_from or None,
        with_assets=req.with_assets,
        with_visuals=req.with_visuals,
        with_gameplay=req.with_gameplay,
        enemy_tuning=req.enemy_tuning,
        approval_manifest_path=req.approval_manifest_path,
        workspace_root=_request_root(req),
    )


@app.post("/api/execute")
def execute_demo(req: ExecuteDemoRequest) -> dict[str, Any]:
    binding = _bound_request(req)
    engine = infer_demo_engine(req.plan, req.engine)
    # Validate against the caller-supplied session id before minting one.
    # A resume with no id must fail here, not start a new session in the worker.
    try:
        normalize_demo_resume(
            req.plan,
            req.engine,
            session_id=req.session_id,
            resume_from=req.resume_from or None,
        )
        # The id becomes a directory name under generated/<engine>/sessions/.
        # Rejecting it here keeps a hostile id a 400 instead of a path that
        # resolves onto another session (see ``validate_session_id``).
        validate_session_id(req.session_id)
    except DemoLaunchError as exc:
        raise HTTPException(status_code=400, detail=_resume_http_detail(exc)) from exc
    session_id = req.session_id or (
        f"{new_session_id()}-{uuid4().hex[:8]}" if binding else new_session_id()
    )
    if not req.confirmed:
        preview = launch_demo(_demo_request(req, confirmed=False, session_id=session_id))
        return {**_EXECUTE_JOB_REGISTRY.preview(preview, engine=engine), "session_id": session_id}

    if binding is not None:
        service, snapshot, _ = binding
        started = service.submit_ui_job(
            req.project_id,
            plan_version=snapshot.plan_version,
            tool_name="execute_demo",
            session_id=session_id,
            arguments={
                **req.model_dump(
                    mode="json",
                    exclude={"plan", "project_id", "plan_version", "confirmed", "session_id"},
                ),
                "engine": engine,
            },
            worker=lambda: launch_demo(
                _demo_request(req, confirmed=req.confirmed, session_id=session_id)
            ),
            confirmed_by_user=req.confirmed,
        )
        return {**started, "engine": engine}

    confirmed = _demo_request(req, confirmed=True, session_id=session_id)
    job_id = _EXECUTE_JOB_REGISTRY.submit(lambda: launch_demo(confirmed))
    return {"status": "running", "job_id": job_id, "engine": engine, "session_id": session_id}


@app.get("/api/execute/{job_id}")
def execute_status(job_id: str) -> dict[str, Any]:
    return _durable_job_response(job_id) or _EXECUTE_JOB_REGISTRY.status(job_id)


@app.post("/api/execute/{job_id}/cancel")
def execute_cancel(job_id: str) -> dict[str, Any]:
    service = studio_workflow_service()
    if found := service.locate_job(job_id):
        return service.cancel_job(found[0], found[1].job_id)
    return _EXECUTE_JOB_REGISTRY.cancel(job_id)


class AgentRunRequest(StrictModel):
    goal: str
    max_turns: int = 8
    include_engine_tools: bool = False
    allow_write: bool = False
    allow_execute: bool = False


@app.post("/api/agent/run")
def run_planning_agent(req: AgentRunRequest) -> dict[str, Any]:
    """Run the bounded planning loop over the configured model.

    Never raises: a loop failure is reported as a status so the caller can fall
    back to the deterministic pipeline instead of showing an error screen.
    """

    from fantasy_agent.agent_loop import DEFAULT_MAX_TURNS, run_agent

    if not req.goal.strip():
        return {"status": "error", "error": "empty goal", "answer": ""}

    try:
        result = run_agent(
            req.goal,
            max_turns=max(1, min(req.max_turns, DEFAULT_MAX_TURNS * 2)),
            allow_write=req.allow_write,
            allow_execute=req.allow_execute,
            include_engine_tools=req.include_engine_tools,
        )
    except Exception as exc:  # noqa: BLE001 - the endpoint must not 500
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}", "answer": ""}

    return {
        "status": result.status,
        "answer": result.answer,
        "tool_calls": result.tool_calls,
        "refusals": result.refusals,
        "error": result.error,
        "steps": [{"text": step.text, "calls": step.calls} for step in result.steps],
    }


class OrchestrationRunRequest(ProjectBinding):
    """One pass over a plan's stages, carrying the operator's approvals.

    The plan is posted from the board rather than re-derived from a prompt here,
    which is what ``/api/execute`` already does and for the same reason: the
    board renders the stages of *that* plan. Rebuilding it from a prompt would
    mean the cards show plan A while the run advances plan B, and nothing on
    screen would say so.

    The approvals ride with the request rather than being cached from an earlier
    one because they are a *user action* -- AGENTS.md is explicit that
    `confirmed_side_effects` / `confirmed` must come from a click, never from a
    value written at the call site. `confirm_stages` is the same kind of flag,
    so it is read off the request body and nothing else.

    With a project reference this is an evidence refresh only. Production and
    rework use the console or the authorized Agent workflow; this request
    cannot issue production grants or dispatch an application model.
    """

    plan: DirectorBuildPlan
    engine: str = ""  # inferred from the plan when empty
    #: Reuse an earlier session to advance it (`_outcomes` stops finished stages
    #: replaying); empty starts a new one.
    session_id: str = ""
    confirm_stages: list[str] = Field(default_factory=list)
    #: Orchestration stage id to forget, along with everything after it, before
    #: this pass -- the rework button. Empty runs the plan as it stands.
    rewind_stage: str = ""
    allow_write: bool = False
    allow_execute: bool = False
    max_turns: int = 8


# `DirectorBuildPlan` is a forward reference from another module, same as in
# `ExecuteDemoRequest`; resolve it so the model is fully defined.
OrchestrationRunRequest.model_rebuild()


class HumanDecisionRequest(ProjectBinding):
    """A person's decision for one human gate.

    The decision is the only thing in the body, and it is read off the request
    and nothing else -- the same rule ``confirm_stages`` follows, for the same
    reason: a decision a person made has to come from a click, never from a
    value written at a call site. The vocabulary (``approved`` / ``rejected``)
    is the orchestrator's, enforced there rather than here, so the endpoint
    reports a bad value instead of defining a second one.
    """

    decision: str
    subjects: list[ReviewSubject] = Field(default_factory=list)


#: Live orchestrators, one per session id.
#:
#: The object *is* the state, which is why it cannot be rebuilt per request:
#: `_outcomes` is what stops a later pass replaying the stages that already
#: finished, and `_confirmed` is what stops it asking the operator to approve the
#: same stage twice. A fresh instance would reset both and turn "approve stage 5"
#: into a replay of stages 1-4 -- the exact waste the orchestrator exists to
#: remove. Studio is a single process (AGENTS.md), so a module-level registry is
#: the whole mechanism.
_ORCHESTRATION_SESSIONS: dict[str, dict[str, Any]] = {}


def _stage_translation() -> dict[str, list[str]]:
    """Which execution steps each orchestration card owns.

    One definition, shared by the run payload and the "nothing has run yet"
    answer, so the board cannot be told two different things about the same
    route depending on whether it asked before or after a run.
    """

    from fantasy_agent.pipeline_state import ORCHESTRATION_TO_EXECUTOR_STAGES

    return {stage_id: list(stages) for stage_id, stages in ORCHESTRATION_TO_EXECUTOR_STAGES.items()}


def _orchestration_payload(session: dict[str, Any]) -> dict[str, Any]:
    """The board's view of a session: plan, runtime state, and what to do next."""

    from fantasy_agent.pipeline_state import executor_stages_for

    orchestrator = session["orchestrator"]
    plan = session["plan"]
    outcomes = orchestrator.outcomes
    confirmed = orchestrator.confirmed

    entries: list[dict[str, Any]] = []
    for stage in sorted(plan.stages, key=lambda entry: entry.order):
        outcome = outcomes.get(stage.id)
        entries.append(
            {
                "stage_id": stage.id,
                "order": stage.order,
                "title": stage.title,
                "title_i18n": stage.title_i18n,
                "kind": stage.kind,
                # Plan-time status (`pending` / `ready` / ...) is written once
                # when the plan is authored. `status` below is what this run
                # actually did -- a board reading only the first would show a
                # run that never starts.
                "plan_status": stage.status,
                "requires_confirmation": stage.requires_confirmation,
                "confirmed": stage.id in confirmed,
                # The decision stamped onto the plan by the orchestrator, for a
                # human gate. Read off the plan rather than off the browser's
                # copy: the plan is the session's record, and a decision is
                # durable state, not a rendering hint.
                "human_resolution": stage.human_resolution,
                # The plan-time fields the board draws a card from. They are
                # sent rather than merged from the browser's copy of the plan
                # for the same reason the request carries a plan: the card must
                # describe the plan this pass advanced.
                "purpose": stage.purpose,
                "owner_agent": stage.owner_agent,
                "depends_on": list(stage.depends_on),
                "mcp_tools": list(stage.mcp_tools),
                "quality_gates": list(stage.quality_gates),
                "risks": list(stage.risks),
                "exit_checks": list(stage.exit_checks),
                "executor_stages": list(executor_stages_for(stage.id)),
                "status": outcome.status if outcome else "pending",
                "detail": outcome.detail if outcome else "",
                "tools": list(outcome.tools) if outcome else [],
                "dispatched": outcome.dispatched if outcome else False,
                "tool_calls": outcome.tool_calls if outcome else 0,
                "refusals": list(outcome.refusals) if outcome else [],
                "checks": list(outcome.checks) if outcome else [],
                "answer": outcome.answer if outcome else "",
            }
        )

    return {
        "session_id": session["session_id"],
        "engine": session["engine"],
        # Same fold the run response carries, so a board that reloads and
        # adopts the session renders a status instead of the string "undefined"
        # -- this payload used to be the only one without the field.
        "status": orchestrator.run_status,
        "goal": plan.goal,
        "project_name": plan.project_name,
        "pending_confirmations": orchestrator.pending_confirmations(plan),
        # Human gates nobody has decided yet. Separate from
        # `pending_confirmations` because the two ask different things of the
        # operator -- approve a stage so it may run, decide a gate so the plan
        # may continue -- and the board's summary line says which.
        "pending_human_gates": orchestrator.pending_human_gates(plan),
        # Every decision given so far, stage id to decision, so a card can show
        # what was answered rather than asking again.
        "human_decisions": orchestrator.human_decisions,
        "confirmed": sorted(confirmed),
        "stage_translation": _stage_translation(),
        "stages": entries,
    }


def _restore_orchestration(session_id: str, engine: str) -> dict[str, Any] | None:
    """Rebuild a session from its on-disk snapshot, or None if there is none.

    Shared by both orchestration endpoints on purpose: this repo has been bitten
    by a local endpoint existing in two implementations, where the second was
    written later and the first kept working. Two callers reading the same file
    is exactly that shape, so there is one reader.

    The plan is validated here rather than at the model layer, because this is
    the only place that can report it: a snapshot whose plan no longer parses
    degrades to "no snapshot" (the board shows nothing) instead of failing to
    load. Same for a snapshot whose confirmations or gate decisions do not
    validate -- restore refuses the whole thing rather than half-applying it,
    because a board with some stages `done` and the rest silently re-run is the
    worst of the three outcomes.
    """

    from fantasy_agent.orchestration_state import load_state as load_snapshot
    from fantasy_agent.orchestrator import Orchestrator
    from fantasy_agent.path_safety import WorkspacePathError

    try:
        snapshot = load_snapshot(session_id, engine_key=engine, workspace_root=REPO_ROOT)
    except WorkspacePathError as exc:
        # An id that cannot be a directory name addresses no session, and the
        # board asking about it deserves the same answer as asking about one
        # that never ran -- not a 500. The name is echoed through ``%r`` because
        # it is caller-supplied: at ``%s`` a newline in it forges a log line.
        logger.warning("orchestration snapshot id %r is not usable: %s", session_id, exc)
        return None
    if snapshot is None:
        return None
    try:
        plan = ProductionPipeline.model_validate(snapshot.plan)
    except Exception as exc:  # noqa: BLE001 - a stale plan must not break a read
        logger.warning(
            "orchestration snapshot for %r has an unusable plan (schema_version %r): %s",
            session_id,
            snapshot.schema_version,
            exc,
        )
        return None
    try:
        orchestrator = Orchestrator.restore(snapshot, plan=plan, workspace_root=REPO_ROOT)
    except ValueError as exc:
        logger.warning(
            "orchestration snapshot for %r has an unusable confirmation or decision: %s",
            session_id,
            exc,
        )
        return None
    return {
        "session_id": session_id,
        "orchestrator": orchestrator,
        "plan": plan,
        "engine": engine,
    }


@app.post("/api/orchestration/run")
def run_orchestration(req: OrchestrationRunRequest) -> dict[str, Any]:
    """Advance a plan once, stage by stage, with the caller's approvals attached.

    Project-bound requests only synchronize the durable external workflow and
    reject a stale project reference or any production approval/rework flags.
    Legacy requests keep the status-based failure contract of `/api/agent/run`.
    """

    if req.project_id is not None:
        service = _require_project(req.project_id)
        with service.projects._lock:
            _bound_request(req)
            if req.allow_write or req.allow_execute or req.confirm_stages or req.rewind_stage:
                raise HTTPException(
                    400,
                    "项目编排板只同步流程证据；生产执行和节点返工请使用流程控制台或 Agent。",
                )
            try:
                return service.workflow_state(req.project_id, req.plan_version)
            except (ValueError, OSError):
                raise HTTPException(400, "项目流程证据无法读取，请刷新项目后重试。") from None

    from uuid import uuid4

    from fantasy_agent.orchestrator import Orchestrator

    plan = req.plan.production_pipeline
    if plan is None or not plan.stages:
        return {
            "status": "error",
            "error": "the posted plan has no production_pipeline stages",
            "stages": [],
        }

    try:
        engine = infer_demo_engine(req.plan, req.engine)
        session_id = req.session_id.strip() or f"orch-{uuid4().hex[:12]}"
        session = _ORCHESTRATION_SESSIONS.get(session_id)
        if session is None:
            # A restarted Studio has an empty registry but a snapshot on disk.
            # Restoring here is what makes the *next* pass cheap: without the
            # outcomes, confirming the last stage replays every earlier one.
            session = _restore_orchestration(session_id, engine)
        if session is None:
            session = {
                "session_id": session_id,
                "orchestrator": Orchestrator(
                    session_id=session_id,
                    workspace_root=REPO_ROOT,
                    engine_key=engine,
                ),
                "plan": plan,
                "engine": engine,
            }
        # Registered in every case, *including* one just rebuilt from disk.
        # The pass below adds outcomes and approvals to this instance; leaving a
        # restored session unregistered would throw both away on the way out
        # and make the next request restore from the file again.
        _ORCHESTRATION_SESSIONS[session_id] = session
        # Re-point the session at this request's plan: the stage ids are fixed
        # per route, so the outcomes carry over while the board shows the plan
        # the operator is actually looking at.
        session["plan"] = plan
        session["engine"] = engine

        rewound: list[str] = []
        rewind = req.rewind_stage.strip()
        if rewind:
            # Inside the try, but branching on the payload rather than falling
            # through to the outer handler: a mistyped card id is a *user*
            # mistake, and the board should keep its cards and say which id it
            # did not recognise instead of being handed an empty stage list.
            try:
                rewound = session["orchestrator"].rewind_from(plan, rewind)
            except ValueError as exc:
                payload = _orchestration_payload(session)
                payload["status"] = "error"
                payload["error"] = str(exc)
                payload["rewound"] = []
                return payload

        result = session["orchestrator"].run(
            plan,
            allow_write=req.allow_write,
            allow_execute=req.allow_execute,
            max_turns=max(1, min(req.max_turns, 64)),
            confirm_stages=req.confirm_stages,
        )
    except Exception as exc:  # noqa: BLE001 - the endpoint must not 500
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}", "stages": []}

    payload = _orchestration_payload(session)
    payload["status"] = result.status
    payload["error"] = result.error
    payload["rewound"] = rewound
    return payload


@app.post("/api/orchestration/{session_id}/stages/{stage_id}/decision")
def decide_orchestration_stage(
    session_id: str,
    stage_id: str,
    req: HumanDecisionRequest,
    engine: DemoEngine = "godot",
) -> dict[str, Any]:
    """Record a person's decision for one human gate, and make it durable.

    The deadlock this closes: a ``kind="human"`` stage could only ever answer
    ``awaiting_human``, so a Godot route stopped at ``order=5`` forever with the
    three stages behind it blocked, and nothing on the REST surface could write
    the decision that unblocks them.

    This endpoint deliberately does **not** advance the plan.
    ``/api/orchestration/run`` stays the single path that dispatches a stage, so
    there is one place where a pass happens and one set of grant semantics --
    the repo has been bitten by a local endpoint existing in two
    implementations, and a second advancing path would be exactly that shape.
    The board chains a run after a successful decision, which is also why the
    response carries the same payload the run does.

    What it *does* persist immediately is the snapshot. A decision lives in the
    orchestrator's map and on the plan it stamped -- both in memory. Without
    the write here, a restart between the click and the next pass would lose a
    decision the operator gave and ask for it again: an approval that never
    takes effect, one verb over from the one AGENTS.md names.

    A project reference instead records a content-bound asset review in the
    shared durable workflow. Invalid/stale references use HTTP 400/409, as the
    other project-bound requests do. Legacy failures remain a status the board
    can branch on, with the cards still attached.

    `engine` is only consulted when the session is not live, to find the
    snapshot a restarted Studio left on disk; a live session already knows
    which directory it wrote to.
    """

    from fantasy_agent.orchestration_state import save_state
    from fantasy_agent.orchestrator import HUMAN_STAGE_KIND

    if req.project_id is not None:
        service = _require_project(req.project_id)
        # Keep CAS, the UI's content identity, and the service's review intent
        # in the same project transaction. request/apply still rehash the file
        # so an external writer cannot replace the user's reviewed contents.
        with service.projects._lock:
            _, snapshot, _ = _bound_request(req)
            try:
                state = service.workflow_state(req.project_id, req.plan_version)
                if session_id != state.get("session_id") or engine != state.get("engine"):
                    raise ValueError("审阅会话或引擎不属于当前项目版本，请刷新流程。")
                pipeline = snapshot.plan.production_pipeline
                stage = (
                    next((item for item in pipeline.stages if item.id == stage_id), None)
                    if pipeline is not None
                    else None
                )
                if stage_id != "creative_review" or stage is None or stage.kind != HUMAN_STAGE_KIND:
                    raise ValueError("项目编排板只能决定当前计划的 Creative Review 人类审阅节点。")
                if req.decision not in {"approved", "rejected"}:
                    raise ValueError("审阅决定必须是批准或拒绝。")
                resource_ids = _validate_ui_subjects(snapshot, req.subjects)
                intent = service.request_asset_review(
                    req.project_id,
                    plan_version=req.plan_version,
                    resource_ids=resource_ids,
                )
                service.apply_asset_review(
                    req.project_id,
                    intent["intent_id"],
                    approved=req.decision == "approved",
                    decision=req.decision,
                )
                return service.workflow_state(req.project_id, req.plan_version)
            except ProjectVersionConflict:
                # Re-read through the common CAS response after an intent was
                # prepared against a version that is no longer current.
                _bound_request(req)
                raise HTTPException(409, "计划版本已变化，请刷新后重新审阅。") from None
            except (ValueError, OSError):
                raise HTTPException(
                    400, "审阅会话、节点或资产版本无效；请刷新当前项目后重新审阅。"
                ) from None

    session = _ORCHESTRATION_SESSIONS.get(session_id)
    if session is None:
        # A restarted Studio has an empty registry but a snapshot on disk, and
        # the operator is clicking on a board rendered from one.
        session = _restore_orchestration(session_id, engine)
    if session is None:
        # A decision attaches to a session, and a board with no session has
        # nothing to attach it to. Answering with the cards would imply the
        # decision landed somewhere.
        return {
            "session_id": session_id,
            "found": False,
            "status": "error",
            "error": (
                "no orchestration session under this id; run the plan first, "
                "because a decision attaches to the session that ran it"
            ),
            "stages": [],
        }
    # Registered in every case, *including* one just rebuilt from disk: the
    # decision below lands on this instance, and leaving a restored session
    # unregistered would throw it away on the way out and make the next run
    # restore from a file that predates the click.
    _ORCHESTRATION_SESSIONS[session_id] = session

    plan = session["plan"]
    stage = next((entry for entry in plan.stages if entry.id == stage_id), None)
    if stage is None:
        payload = _orchestration_payload(session)
        payload["status"] = "error"
        payload["error"] = f"{stage_id!r} is not a stage of this plan"
        return payload
    if stage.kind != HUMAN_STAGE_KIND:
        # Only a gate takes a decision. Accepting one for an agent stage would
        # read as "the operator settled this" on a card that a decision cannot
        # move -- the dead-end control this endpoint exists to replace, wearing
        # the opposite hat.
        payload = _orchestration_payload(session)
        payload["status"] = "error"
        payload["error"] = (
            f"stage {stage_id!r} is kind={stage.kind!r}, not {HUMAN_STAGE_KIND!r}; "
            "only a human gate takes a decision"
        )
        return payload

    try:
        session["orchestrator"].resolve_human_stage(stage_id, req.decision)
    except ValueError as exc:
        # An unknown stage id or a decision outside the vocabulary. Both are
        # reported with the cards still attached: a mistyped decision is a user
        # mistake, and blanking the board over one would lose the run.
        payload = _orchestration_payload(session)
        payload["status"] = "error"
        payload["error"] = str(exc)
        return payload

    try:
        save_state(session["orchestrator"].snapshot(plan), workspace_root=REPO_ROOT)
    # No `noqa: BLE001` here on purpose: a blind handler that only logs is
    # exempt from the directive, so naming it would be flagged unused -- the
    # same shape `Orchestrator._record` uses.
    except Exception:
        # Same trade ``Orchestrator._record`` makes: the person decided, and
        # failing the request would ask them to decide again over a record of
        # it. The log line is what says the file is missing.
        logger.exception(
            "could not snapshot the decision for session %r stage %r",
            session_id,
            stage_id,
        )

    # Not advanced, so the run-level fold is the last pass's -- honest, and the
    # board's follow-up run is what moves it. ``error`` is spelled out as empty
    # for the same reason the run endpoint always carries it: the fold can be
    # "error" on a session whose *earlier* pass failed, and a caller that read
    # the status as "your decision was refused" would refuse to act on a
    # decision that landed. ``error`` non-empty is the only refusal signal.
    payload = _orchestration_payload(session)
    payload["error"] = ""
    return payload


@app.get("/api/orchestration/{session_id}")
def orchestration_state(session_id: str, engine: DemoEngine = "godot") -> dict[str, Any]:
    """What a session has done so far, without advancing it.

    The board polls this after a run so a card's status is read from the same
    place the run wrote it, rather than kept in a second copy in the browser.

    A session that has never run answers with the stage translation, because
    that table is route metadata rather than session state: the eight
    orchestration stage ids and the execution steps each one owns are fixed for
    the whole route. Answering `{}` here said "this route has no execution
    stages", which is a stronger and less true claim than "nothing has run yet"
    -- and it made the board's drill-down vanish exactly when the operator had
    nothing else to read.

    When the registry is empty but a snapshot is on disk -- a restarted Studio,
    which is exactly when the board reloads and asks -- the snapshot is rendered
    as if the session were live. That is the whole point: the board kept this id
    in localStorage precisely so it could find its session, and the old answer
    (`found: false`) threw away a run that had already cost model turns.

    The rebuilt session is deliberately **not** registered. A GET must not have
    side effects: registering here would make a poll create state, so a board
    that merely looked at a stale id would own a live orchestrator from then
    on, and the next POST would inherit its outcome map rather than the
    snapshot's. The cost is re-reading and re-validating a small JSON per poll,
    which is not worth trading for a poll with side effects.

    `engine` is a `DemoEngine`, not a free string, because it selects the
    directory a snapshot is read from: accepting arbitrary text would let a
    caller aim the read at any subtree of `generated/`, and a free string with a
    default is worse still because it hides the choice from the frontend. The
    board passes the engine it recorded when the run was posted rather than
    re-deriving one here.
    """

    session = _ORCHESTRATION_SESSIONS.get(session_id)
    if session is None:
        session = _restore_orchestration(session_id, engine)
    if session is None:
        return {
            "session_id": session_id,
            "found": False,
            "status": "pending",
            "pending_confirmations": [],
            "pending_human_gates": [],
            "human_decisions": {},
            "confirmed": [],
            "stage_translation": _stage_translation(),
            "rewound": [],
            "stages": [],
        }
    payload = _orchestration_payload(session)
    payload["found"] = True
    return payload


@app.get("/api/sessions/{session_id}/state")
def session_state(session_id: str, engine: DemoEngine = "godot") -> dict[str, Any]:
    """Stage state of a previous run, so the UI can offer node-level re-runs.

    `DemoEngine` for the same reason as `/api/orchestration/{session_id}`: the
    value picks the `generated/<engine>/sessions/<id>/` directory being read, so
    it is an enumeration of the two real ones rather than arbitrary text.
    """

    from fantasy_agent.pipeline_state import GODOT_STAGE_ORDER, load_state

    state = load_state(session_id, engine_key=engine, workspace_root=REPO_ROOT)
    if state is None:
        return {
            "session_id": session_id,
            "engine": engine,
            "found": False,
            "stage_order": list(GODOT_STAGE_ORDER),
            "stages": [],
            "done": [],
            "failed": [],
        }
    return {
        "session_id": session_id,
        "engine": engine,
        "found": True,
        "project_dir": state.project_dir,
        "updated_at": state.updated_at,
        "stage_order": list(GODOT_STAGE_ORDER),
        "stages": [stage.model_dump(mode="json") for stage in state.stages],
        "done": sorted(state.done_stages()),
        "failed": sorted(state.failed_stages()),
    }
