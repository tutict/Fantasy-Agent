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

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from fantasy_agent import api_settings
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
    GDDDocument,
    GameplaySpec,
    GodotProjectPlan,
    IdeaDiscoveryRequest,
    IdeaSeed,
    PromptRequest,
    ProductionSpecBundle,
    QAPlan,
    SpecTraceRecord,
    SpecValidationReport,
    UnrealProjectPlan,
    default_comfyui_endpoint_candidates,
)
from fantasy_agent.generation import design_from_prompt
from fantasy_agent.idea_discovery import extract_idea_seed, prompt_request_from_seed
from fantasy_agent.local_tools import manual_correction_targets, open_manual_correction_target
from fantasy_agent.mcp import initial_mcp_contracts
from fantasy_agent.studio_jobs import InMemoryJobRegistry
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
STATIC_DIR = APP_DIR / "static"
WEB_CONSOLE_STATIC_DIR = STATIC_DIR / "web-console"
FRONTEND_DIST_DIR = REPO_ROOT / "apps" / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"
WORKBENCH_PATH = STATIC_DIR / "planning-workbench.html"

app = FastAPI(
    title="Fantasy Agent Studio",
    version=STUDIO_VERSION,
    description="Standalone local workbench for Fantasy Agent production workflows.",
)

app.mount("/studio-static", StaticFiles(directory=str(STATIC_DIR)), name="studio_static")
app.mount("/assets", StaticFiles(directory=str(WEB_CONSOLE_STATIC_DIR)), name="web_console_assets")
if FRONTEND_DIST_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIST_DIR)), name="frontend_assets")


class ManualCorrectionOpenRequest(BaseModel):
    target_id: str
    engine: str = "UE5"
    confirmed_side_effects: bool = False




class ApprovalManifestRequest(BaseModel):
    review: CreativeReviewReport
    decisions: dict[str, str] = Field(default_factory=dict)
    production_spec_bundle: ProductionSpecBundle | None = None


class ApprovalManifestResponse(BaseModel):
    status: str
    manifest_path: str
    manifest: AssetApprovalManifest
    production_spec_bundle: ProductionSpecBundle | None = None


class SpecBundlePreviewRequest(BaseModel):
    production_spec_bundle: ProductionSpecBundle
    target: str = "godot"


class SpecBundlePreviewResponse(BaseModel):
    validation: SpecValidationReport
    artifacts: list[CompiledSpecArtifact] = Field(default_factory=list)
    traces: list[SpecTraceRecord] = Field(default_factory=list)
    executable_qa: ExecutableQAReport


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
SpecBundlePreviewRequest.model_rebuild()
SpecBundlePreviewResponse.model_rebuild()
AssetExecutionRequest.model_rebuild()
ExecuteDemoRequest.model_rebuild()


# Jobs run on a single worker so we never launch two engines at once.
# They are intentionally in-memory because Studio is a local dev tool.
_EXECUTE_POOL = ThreadPoolExecutor(max_workers=1)
_EXECUTE_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)
_ASSET_JOB_REGISTRY = InMemoryJobRegistry(_EXECUTE_POOL)


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


@app.get("/")
def index() -> FileResponse:
    return _frontend_index_or(STATIC_DIR / "index.html")


@app.get("/web-console")
def web_console() -> FileResponse:
    return _frontend_index_or(WEB_CONSOLE_STATIC_DIR / "index.html")


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


class LLMApiSettingsRequest(BaseModel):
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
    return FileResponse(WORKBENCH_PATH)


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
    engine = _infer_engine(req.plan, req.engine)
    if not req.confirmed:
        # Confirmation gate: report side effects without writing or executing.
        preview = _build_execution_result(req, confirmed=False)
        return _EXECUTE_JOB_REGISTRY.preview(preview, engine=engine)

    job_id = _EXECUTE_JOB_REGISTRY.submit(lambda: _build_execution_result(req, confirmed=True))
    return {"status": "running", "job_id": job_id, "engine": engine}


@app.get("/api/execute/{job_id}")
def execute_status(job_id: str) -> dict[str, Any]:
    return _EXECUTE_JOB_REGISTRY.status(job_id)


@app.post("/api/execute/{job_id}/cancel")
def execute_cancel(job_id: str) -> dict[str, Any]:
    return _EXECUTE_JOB_REGISTRY.cancel(job_id)

