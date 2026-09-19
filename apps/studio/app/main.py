from __future__ import annotations

import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from fantasy_agent import api_settings, local_tools
from fantasy_agent.api_settings import public_settings
from fantasy_agent.blender_codegen import build_blender_script_artifact
from fantasy_agent.contracts import (
    AssetApprovalManifest,
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
    ProductionSpecBundle,
    PromptRequest,
    QAPlan,
    SpecTraceRecord,
    SpecValidationReport,
    StrictModel,
    UnrealProjectPlan,
)
from fantasy_agent.generation import design_from_prompt
from fantasy_agent.idea_discovery import extract_idea_seed, prompt_request_from_seed
from fantasy_agent.local_tools import manual_correction_targets, open_manual_correction_target
from fantasy_agent.mcp import initial_mcp_contracts
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from fantasy_agent.tool_registry import tool_catalog
from fantasy_agent.workflows import (
    build_asset_approval_manifest,
    decompose_production_tasks,
    prepare_blender_assets,
    prepare_comfyui_visuals,
    prepare_creative_review,
    prepare_godot_project,
    prepare_qa_plan,
    prepare_unreal_project,
    run_director_workflow,
)

STUDIO_NAME = "fantasy-agent-studio"
STUDIO_VERSION = "0.1.0"

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
FRONTEND_DIST_DIR = REPO_ROOT / "apps" / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"

app = FastAPI(
    title="Fantasy Agent Studio",
    version=STUDIO_VERSION,
    description="Standalone local workbench for Fantasy Agent production workflows.",
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




class ApprovalManifestRequest(StrictModel):
    review: CreativeReviewReport
    decisions: dict[str, str] = Field(default_factory=dict)
    production_spec_bundle: ProductionSpecBundle | None = None


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


class AssetExecutionRequest(StrictModel):
    plan: DirectorBuildPlan
    with_assets: bool = False
    with_visuals: bool = False
    confirmed: bool = False


class ExecuteDemoRequest(StrictModel):
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
ExecuteDemoRequest.model_rebuild()


# Jobs run on a single worker so we never launch two engines at once.
# They are intentionally in-memory because Studio is a local dev tool.
_EXECUTE_POOL = ThreadPoolExecutor(max_workers=1)
_EXECUTE_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)
_ASSET_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)


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


@app.post("/api/plan", response_model=DirectorBuildPlan)
def plan(request: PromptRequest) -> DirectorBuildPlan:
    return run_director_workflow(request, use_llm=_use_llm())


@app.post("/api/tasks", response_model=DirectorTaskBreakdown)
def tasks(request: PromptRequest) -> DirectorTaskBreakdown:
    return decompose_production_tasks(request)


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


def _use_llm() -> bool:
    """Whether the LLM backend should be attempted for this request.

    Driven by the API access panel in the Studio; falls back to the
    ``FANTASY_AGENT_USE_LLM`` environment flag when it is set.
    """

    return api_settings.llm_enabled()


class IdeaSeedResponse(BaseModel):
    idea_seed: IdeaSeed
    prompt_request: PromptRequest


IdeaSeedResponse.model_rebuild()


@app.post("/api/idea-seed", response_model=IdeaSeedResponse)
def idea_seed(request: IdeaDiscoveryRequest) -> IdeaSeedResponse:
    """Turn interview answers into an IdeaSeed and a ready-to-plan PromptRequest."""

    seed = extract_idea_seed(request)
    return IdeaSeedResponse(
        idea_seed=seed,
        prompt_request=prompt_request_from_seed(seed, request),
    )


@app.post("/api/design", response_model=GameplaySpec)
def design(request: PromptRequest) -> GameplaySpec:
    return design_from_prompt(request, use_llm=_use_llm())


@app.post("/api/gdd", response_model=GDDDocument)
def gdd(request: PromptRequest) -> GDDDocument:
    return run_director_workflow(request, use_llm=_use_llm()).gdd


@app.post("/api/pipeline")
def pipeline(request: PromptRequest) -> dict[str, Any]:
    plan = run_director_workflow(request, use_llm=_use_llm())
    return {
        "gameplay_title": plan.gameplay_spec.title,
        "production_pipeline": (
            plan.production_pipeline.model_dump(mode="json") if plan.production_pipeline else None
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
        "production_pipeline_stages": [stage.title for stage in pipeline.stages] if pipeline else [],
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


def _workbench_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run a workbench planning tool by name against the local workflows."""

    if name == "extract_idea_seed":
        request = IdeaDiscoveryRequest.model_validate(arguments)
        seed = extract_idea_seed(request)
        prompt_request = prompt_request_from_seed(seed, request)
        seed_payload = seed.model_dump(mode="json")
        prompt_payload = prompt_request.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "idea_seed", "idea_seed": seed_payload, "prompt_request": prompt_payload},
            (
                "Extracted an IdeaSeed for planning. "
                f"Core action: {seed.core_action}. Next step: generate a production plan from the seed."
            ),
            {"ideaSeed": seed_payload, "promptRequest": prompt_payload, "activePanel": "discovery"},
        )

    request = PromptRequest.model_validate(arguments)

    if name == "decompose_production_tasks":
        breakdown = decompose_production_tasks(request)
        payload = breakdown.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "director_task_breakdown", "task_breakdown": payload},
            (
                f"Prepared {len(breakdown.tasks)} production tasks. "
                f"Recommended next task: {breakdown.recommended_next_task}. "
                "Execution tasks still require explicit confirmation."
            ),
            {"taskBreakdown": payload, "activePanel": "tasks"},
        )

    plan = run_director_workflow(request, use_llm=_use_llm())
    spec = plan.gameplay_spec
    summary = _plan_summary(plan)

    if name == "generate_game_production_plan":
        plan_payload = plan.model_dump(mode="json")
        task_payload = plan.task_breakdown.model_dump(mode="json") if plan.task_breakdown else None
        pipeline_payload = (
            plan.production_pipeline.model_dump(mode="json") if plan.production_pipeline else None
        )
        return _workbench_result(
            name,
            {
                "kind": "director_build_plan",
                "summary": summary,
                "plan": plan_payload,
                "task_breakdown": task_payload,
                "production_pipeline": pipeline_payload,
            },
            _plan_headline("Generated full production plan", plan),
            {
                "plan": plan_payload,
                "taskBreakdown": task_payload,
                "productionPipeline": pipeline_payload,
                "activePanel": "overview",
            },
        )

    if name == "render_gdd":
        gdd_payload = plan.gdd.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "gdd_document", "summary": summary, "gdd": gdd_payload},
            _plan_headline("Rendered GDD", plan),
            {"gdd": gdd_payload, "activePanel": "gdd"},
        )

    if name == "prepare_production_pipeline":
        pipeline_payload = (
            plan.production_pipeline.model_dump(mode="json") if plan.production_pipeline else None
        )
        return _workbench_result(
            name,
            {"kind": "production_pipeline", "summary": summary, "production_pipeline": pipeline_payload},
            _plan_headline("Prepared production pipeline", plan),
            {"productionPipeline": pipeline_payload, "activePanel": "pipeline"},
        )

    if name == "prepare_unreal_plan":
        unreal_plan = prepare_unreal_project(spec, request.engine_version)
        payload = unreal_plan.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "unreal_project_plan", "gameplay_title": spec.title, "unreal_plan": payload},
            f"Prepared Unreal handoff for {spec.title}: {', '.join(unreal_plan.maps)}.",
            {"unrealPlan": payload, "activePanel": "build"},
        )

    if name == "prepare_godot_plan":
        godot_plan = prepare_godot_project(spec)
        payload = godot_plan.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "godot_project_plan", "gameplay_title": spec.title, "godot_plan": payload},
            f"Prepared Godot quick-play handoff for {spec.title}: {', '.join(godot_plan.scenes)}.",
            {"godotPlan": payload, "activePanel": "build"},
        )

    if name == "prepare_blender_plan":
        blender_plan = prepare_blender_assets(spec)
        payload = blender_plan.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "blender_asset_plan", "gameplay_title": spec.title, "blender_plan": payload},
            f"Prepared {len(blender_plan.jobs)} Blender greybox asset jobs for {spec.title}.",
            {"blenderPlan": payload, "activePanel": "build"},
        )

    if name == "prepare_comfyui_plan":
        comfyui_plan = prepare_comfyui_visuals(spec)
        payload = comfyui_plan.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "comfyui_visual_plan", "gameplay_title": spec.title, "comfyui_plan": payload},
            f"Prepared {len(comfyui_plan.jobs)} ComfyUI visual reference jobs for {spec.title}.",
            {"comfyuiPlan": payload, "activePanel": "visuals"},
        )

    if name == "prepare_creative_review_plan":
        review = prepare_creative_review(
            spec,
            prepare_blender_assets(spec),
            prepare_comfyui_visuals(spec),
        )
        payload = review.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "creative_review_report", "gameplay_title": spec.title, "creative_review": payload},
            (
                f"Prepared {len(review.items)} creative review items for {spec.title}. "
                "Unreal ingest remains blocked until user approvals are recorded."
            ),
            {"creativeReview": payload, "activePanel": "visuals"},
        )

    if name == "prepare_qa_plan":
        qa_plan = prepare_qa_plan(spec)
        payload = qa_plan.model_dump(mode="json")
        return _workbench_result(
            name,
            {"kind": "qa_plan", "gameplay_title": spec.title, "qa_plan": payload},
            f"Prepared QA checks for a {qa_plan.target_session_minutes}-minute slice of {spec.title}.",
            {"qaPlan": payload, "activePanel": "qa"},
        )

    available = (
        "extract_idea_seed, decompose_production_tasks, generate_game_production_plan, render_gdd, "
        "prepare_production_pipeline, prepare_unreal_plan, prepare_godot_plan, prepare_blender_plan, "
        "prepare_comfyui_plan, prepare_creative_review_plan, prepare_qa_plan"
    )
    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Unknown Studio planning tool '{name}'. Available tools: {available}."}],
    }


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


def _build_execution_result(
    req: ExecuteDemoRequest, *, confirmed: bool, session_id: str
):
    """Call the right executor; returns an ExecutionResult."""
    from fantasy_agent.executor import execute_godot_demo, execute_unreal_demo
    from fantasy_agent.local_tools import (
        _find_blender,
        _find_godot,
        _find_unreal,
        _unreal_cmd_executable,
    )

    engine = _infer_engine(req.plan, req.engine)
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
        resume_from=req.resume_from or None,
    )


def _validate_resume_request(req: ExecuteDemoRequest) -> None:
    """Reject a resume that cannot actually resume.

    Two silent-degradation traps: an unknown node name used to fall through to
    "skip nothing" (a full replay of every expensive node), and resuming
    without a session id silently started a brand-new session with no prior
    state to reuse. Both now fail loudly at the boundary.
    """

    if not req.resume_from:
        return
    if not req.session_id:
        raise HTTPException(
            status_code=400,
            detail="resume_from 需要同时提供 session_id，否则无法复用已完成的节点",
        )
    from fantasy_agent.pipeline_state import normalize_resume_from

    try:
        # Accept a re-work target ("spec") as well as a stage name ("blender").
        req.resume_from = normalize_resume_from(req.resume_from)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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

    manifest = build_asset_approval_manifest(req.review, req.decisions)
    path = _approval_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
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
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(
            yaml.safe_dump(
                synced_bundle.model_dump(mode="json"),
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    return ApprovalManifestResponse(
        status="written",
        manifest_path=rel,
        manifest=manifest,
        production_spec_bundle=synced_bundle,
    )


def _build_asset_execution_result(req: AssetExecutionRequest, *, confirmed: bool):
    from datetime import UTC, datetime

    from fantasy_agent.executor import execute_asset_pipeline
    from fantasy_agent.local_tools import _find_blender

    session_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return execute_asset_pipeline(
        req.plan,
        session_id=session_id,
        confirmed=confirmed,
        workspace_root=REPO_ROOT,
        with_assets=req.with_assets,
        blender_exe=_find_blender() or "blender",
        with_visuals=req.with_visuals,
    )


@app.post("/api/assets/execute")
def execute_assets(req: AssetExecutionRequest) -> dict[str, Any]:
    if not req.confirmed:
        preview = _build_asset_execution_result(req, confirmed=False)
        return _ASSET_JOB_REGISTRY.preview(preview)

    job_id = _ASSET_JOB_REGISTRY.submit(lambda: _build_asset_execution_result(req, confirmed=True))
    return {"status": "running", "job_id": job_id}


@app.get("/api/assets/execute/{job_id}")
def asset_execute_status(job_id: str) -> dict[str, Any]:
    return _ASSET_JOB_REGISTRY.status(job_id)


@app.post("/api/assets/execute/{job_id}/cancel")
def asset_execute_cancel(job_id: str) -> dict[str, Any]:
    return _ASSET_JOB_REGISTRY.cancel(job_id)


@app.post("/api/execute")
def execute_demo(req: ExecuteDemoRequest) -> dict[str, Any]:
    from datetime import UTC, datetime

    engine = _infer_engine(req.plan, req.engine)
    # Own the session id here so the caller gets it back immediately and can
    # resume this exact run later instead of starting a new one.
    session_id = req.session_id or datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    _validate_resume_request(req)
    if not req.confirmed:
        # Confirmation gate: report side effects without writing or executing.
        preview = _build_execution_result(req, confirmed=False, session_id=session_id)
        return {**_EXECUTE_JOB_REGISTRY.preview(preview, engine=engine), "session_id": session_id}

    job_id = _EXECUTE_JOB_REGISTRY.submit(
        lambda: _build_execution_result(req, confirmed=True, session_id=session_id)
    )
    return {"status": "running", "job_id": job_id, "engine": engine, "session_id": session_id}


@app.get("/api/execute/{job_id}")
def execute_status(job_id: str) -> dict[str, Any]:
    return _EXECUTE_JOB_REGISTRY.status(job_id)


@app.post("/api/execute/{job_id}/cancel")
def execute_cancel(job_id: str) -> dict[str, Any]:
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
        "steps": [
            {"text": step.text, "calls": step.calls} for step in result.steps
        ],
    }


class OrchestrationRunRequest(StrictModel):
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
        "confirmed": sorted(confirmed),
        "stage_translation": _stage_translation(),
        "stages": entries,
    }


@app.post("/api/orchestration/run")
def run_orchestration(req: OrchestrationRunRequest) -> dict[str, Any]:
    """Advance a plan once, stage by stage, with the caller's approvals attached.

    Never raises, same contract as `/api/agent/run`: a failure is a status the
    caller can branch on, because the board has to keep rendering the stages it
    already has rather than losing them to an error screen.
    """

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
        engine = _infer_engine(req.plan, req.engine)
        session_id = req.session_id.strip() or f"orch-{uuid4().hex[:12]}"
        session = _ORCHESTRATION_SESSIONS.get(session_id)
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


@app.get("/api/orchestration/{session_id}")
def orchestration_state(session_id: str) -> dict[str, Any]:
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
    """

    session = _ORCHESTRATION_SESSIONS.get(session_id)
    if session is None:
        return {
            "session_id": session_id,
            "found": False,
            "status": "pending",
            "pending_confirmations": [],
            "confirmed": [],
            "stage_translation": _stage_translation(),
            "rewound": [],
            "stages": [],
        }
    payload = _orchestration_payload(session)
    payload["found"] = True
    return payload


@app.get("/api/sessions/{session_id}/state")
def session_state(session_id: str, engine: str = "godot") -> dict[str, Any]:
    """Stage state of a previous run, so the UI can offer node-level re-runs."""

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

