import type {
  AgentRunRequest,
  AgentRunResult,
  ApprovalManifestResponse,
  AssetExecuteJob,
  AssetExecutePreview,
  AssetExecuteStart,
  BlenderPlan,
  BlenderScriptArtifact,
  CreativeReview,
  ExecuteJob,
  ExecutePreview,
  ExecuteStart,
  GameplaySpec,
  IdeaDiscoveryRequest,
  JobCancelResponse,
  LlmApiSettings,
  LlmApiSettingsInput,
  LlmApiTestResult,
  ManualTargetsPayload,
  McpStatus,
  OrchestrationRunRequest,
  OrchestrationSession,
  ProductionSpecBundle,
  PromptRequest,
  SessionState,
  SpecBundlePreviewResponse,
  ToolCatalog,
  WorkbenchToolResult
} from "./types";
import type { DirectorBuildPlan, EnemyPressureTuning } from "./types";

/**
 * FastAPI answers failures with ``{"detail": ...}``. ``detail`` is a plain
 * string for ``HTTPException`` (the backend writes its messages in Chinese,
 * e.g. "resume_from 需要同时提供 session_id") but a list of
 * ``{loc, msg, type}`` entries for 422 validation errors, so both shapes are
 * unwrapped here. Without this the user only ever sees "HTTP 400".
 */
export function errorMessageFromPayload(payload: unknown, status: number): string {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const detail = record.detail ?? record.error;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => {
          if (entry && typeof entry === "object") {
            const item = entry as Record<string, unknown>;
            const location = Array.isArray(item.loc) ? item.loc.join(".") : "";
            return location ? `${location}: ${String(item.msg ?? "")}` : String(item.msg ?? "");
          }
          return String(entry);
        })
        .filter(Boolean);
      if (messages.length) {
        return messages.join("; ");
      }
    }
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message;
    }
  }
  return `HTTP ${status}`;
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers
    },
    ...init
  });
  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new Error(errorMessageFromPayload(payload, response.status));
  }
  return (await response.json()) as T;
}

export function getManualCorrectionTargets(engine: string): Promise<ManualTargetsPayload> {
  const query = new URLSearchParams({ engine });
  return jsonRequest<ManualTargetsPayload>(`/api/manual-correction/targets?${query.toString()}`);
}

/**
 * Opening a target spawns a local editor/Explorer process, so the backend
 * refuses unless ``confirmed_side_effects`` is true. That flag is the approval
 * gate -- it is never hardcoded here. The caller has to ask the human first.
 */
export function openManualCorrectionTarget(
  targetId: string,
  engine: string,
  confirmedSideEffects: boolean
): Promise<Record<string, string>> {
  return jsonRequest<Record<string, string>>("/api/manual-correction/open", {
    method: "POST",
    body: JSON.stringify({
      target_id: targetId,
      engine,
      confirmed_side_effects: confirmedSideEffects
    })
  });
}

/**
 * Run a planning tool on the local Studio server.
 *
 * The workbench tools are pure planning calls: they never write files or spawn
 * processes, so unlike ``openManualCorrectionTarget`` there is no approval flag
 * to thread through. Execution stays in the flow console.
 */
export function callWorkbenchTool(
  toolName: string,
  payload: IdeaDiscoveryRequest | PromptRequest
): Promise<WorkbenchToolResult> {
  return jsonRequest<WorkbenchToolResult>(`/api/tools/${encodeURIComponent(toolName)}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export interface ExecuteRunOptions {
  /** Reuse a previous run's session so finished stages can be skipped. */
  sessionId?: string;
  /** Node to resume at; earlier stages that succeeded are skipped. */
  resumeFrom?: string;
}

export function previewExecute(
  plan: DirectorBuildPlan,
  engine: string,
  withAssets: boolean,
  withVisuals: boolean,
  withGameplay: boolean,
  enemyTuning: EnemyPressureTuning,
  approvalManifestPath?: string,
  options: ExecuteRunOptions = {}
): Promise<ExecutePreview> {
  return jsonRequest<ExecutePreview>("/api/execute", {
    method: "POST",
    body: JSON.stringify({
      plan,
      engine,
      with_assets: withAssets,
      with_visuals: withVisuals,
      with_gameplay: withGameplay,
      enemy_tuning: enemyTuning,
      approval_manifest_path: approvalManifestPath || undefined,
      session_id: options.sessionId || undefined,
      resume_from: options.resumeFrom || undefined,
      confirmed: false
    })
  });
}

export function startExecute(
  plan: DirectorBuildPlan,
  engine: string,
  withAssets: boolean,
  withVisuals: boolean,
  withGameplay: boolean,
  enemyTuning: EnemyPressureTuning,
  approvalManifestPath?: string,
  options: ExecuteRunOptions = {}
): Promise<ExecuteStart> {
  return jsonRequest<ExecuteStart>("/api/execute", {
    method: "POST",
    body: JSON.stringify({
      plan,
      engine,
      with_assets: withAssets,
      with_visuals: withVisuals,
      with_gameplay: withGameplay,
      enemy_tuning: enemyTuning,
      approval_manifest_path: approvalManifestPath || undefined,
      session_id: options.sessionId || undefined,
      resume_from: options.resumeFrom || undefined,
      confirmed: true
    })
  });
}

export function getSessionState(sessionId: string, engine = "godot"): Promise<SessionState> {
  const query = new URLSearchParams({ engine });
  return jsonRequest<SessionState>(
    `/api/sessions/${encodeURIComponent(sessionId)}/state?${query.toString()}`
  );
}

export function getExecuteJob(jobId: string): Promise<ExecuteJob> {
  return jsonRequest<ExecuteJob>(`/api/execute/${encodeURIComponent(jobId)}`);
}

export function cancelExecuteJob(jobId: string): Promise<JobCancelResponse> {
  return jsonRequest<JobCancelResponse>(`/api/execute/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST"
  });
}

/**
 * The bounded loop. Unlike /api/execute this is synchronous -- a run is a
 * handful of model round-trips, not a multi-minute build -- so the response
 * is the whole result. Failures come back as status="error", never an HTTP 500.
 */
export function runAgent(request: AgentRunRequest): Promise<AgentRunResult> {
  return jsonRequest<AgentRunResult>("/api/agent/run", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

export function getMcpStatus(engine: string): Promise<McpStatus> {
  const query = new URLSearchParams({ engine });
  return jsonRequest<McpStatus>(`/api/tool-status?${query.toString()}`);
}

/**
 * Advance the orchestration board's plan one pass.
 *
 * Synchronous, like `/api/agent/run`: a pass is a handful of model round-trips
 * rather than a multi-minute engine build, so the response is the whole result.
 * Failures come back as `status: "error"` with the stage cards still attached --
 * never an HTTP 500 -- because the board has to keep rendering the stages it
 * already has instead of losing them to an error screen.
 *
 * The approvals are read off the request and nothing else; see
 * `OrchestrationRunRequest`.
 */
export function runOrchestration(
  request: OrchestrationRunRequest
): Promise<OrchestrationSession> {
  return jsonRequest<OrchestrationSession>("/api/orchestration/run", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/**
 * What a session has done so far, without advancing it.
 *
 * Read-only, so there is no approval flag to thread through. An id the server
 * has never seen answers `found: false` with the stage translation still
 * present, which is what lets the board offer its drill-down before the first
 * run.
 */
export function getOrchestrationState(sessionId: string): Promise<OrchestrationSession> {
  return jsonRequest<OrchestrationSession>(
    `/api/orchestration/${encodeURIComponent(sessionId)}`
  );
}

/**
 * Every tool an agent may call, with the permission tier the gate enforces.
 *
 * Distinct from the contract dump at `tool-contracts`, which serves the
 * *declared* MCP inventory: this one is the registry's own view, so the tiers it
 * reports are the tiers ``ToolRegistry.call`` will apply. Read-only, so no
 * approval flag.
 */
export function getToolCatalog(): Promise<ToolCatalog> {
  return jsonRequest<ToolCatalog>("/api/tool-catalog");
}

/**
 * LLM settings calls deliberately bypass `jsonRequest`: the backend answers
 * with 200 + `ok: false` for a failed probe (and 400 + `{ error }` for an
 * invalid payload), and the panel needs those bodies to explain what happened.
 */
async function settingsRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    ...init
  });
  return (await response.json()) as T;
}

export function getLlmSettings(): Promise<LlmApiSettings> {
  return jsonRequest<LlmApiSettings>("/api/settings/llm");
}

export function putLlmSettings(settings: LlmApiSettingsInput): Promise<LlmApiSettings & { error?: string }> {
  return settingsRequest<LlmApiSettings & { error?: string }>("/api/settings/llm", {
    method: "PUT",
    body: JSON.stringify(settings)
  });
}

export function testLlmSettings(settings: LlmApiSettingsInput): Promise<LlmApiTestResult> {
  return settingsRequest<LlmApiTestResult>("/api/settings/llm/test", {
    method: "POST",
    body: JSON.stringify(settings)
  });
}

export function deleteLlmSettings(): Promise<LlmApiSettings> {
  return jsonRequest<LlmApiSettings>("/api/settings/llm", { method: "DELETE" });
}


export function writeApprovalManifest(
  review: CreativeReview,
  decisions: Record<string, string>,
  productionSpecBundle?: ProductionSpecBundle
): Promise<ApprovalManifestResponse> {
  return jsonRequest<ApprovalManifestResponse>("/api/creative-review/approval-manifest", {
    method: "POST",
    body: JSON.stringify({
      review,
      decisions,
      production_spec_bundle: productionSpecBundle
    })
  });
}


export function previewAssetExecution(
  plan: DirectorBuildPlan,
  withAssets: boolean,
  withVisuals: boolean
): Promise<AssetExecutePreview> {
  return jsonRequest<AssetExecutePreview>("/api/assets/execute", {
    method: "POST",
    body: JSON.stringify({
      plan,
      with_assets: withAssets,
      with_visuals: withVisuals,
      confirmed: false
    })
  });
}

export function startAssetExecution(
  plan: DirectorBuildPlan,
  withAssets: boolean,
  withVisuals: boolean
): Promise<AssetExecuteStart> {
  return jsonRequest<AssetExecuteStart>("/api/assets/execute", {
    method: "POST",
    body: JSON.stringify({
      plan,
      with_assets: withAssets,
      with_visuals: withVisuals,
      confirmed: true
    })
  });
}

export function getAssetExecutionJob(jobId: string): Promise<AssetExecuteJob> {
  return jsonRequest<AssetExecuteJob>(`/api/assets/execute/${encodeURIComponent(jobId)}`);
}

export function cancelAssetExecutionJob(jobId: string): Promise<JobCancelResponse> {
  return jsonRequest<JobCancelResponse>(`/api/assets/execute/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST"
  });
}


export function previewSpecBundle(
  productionSpecBundle: ProductionSpecBundle,
  target: "godot" | "unreal"
): Promise<SpecBundlePreviewResponse> {
  return jsonRequest<SpecBundlePreviewResponse>("/api/specs/preview", {
    method: "POST",
    body: JSON.stringify({
      production_spec_bundle: productionSpecBundle,
      target
    })
  });
}

/**
 * Re-derive the gameplay spec for a prompt.
 *
 * The console shows the spec that was baked into the plan it was handed, so a
 * plan produced under an older prompt is indistinguishable from a current one.
 * This returns what the backend would produce *now*, which is what the spec tab
 * diffs against the snapshot.
 *
 * Deterministic when LLM generation is off, and always read-only -- no approval
 * flag, because nothing is written or launched.
 */
export function previewGameplaySpec(request: PromptRequest): Promise<GameplaySpec> {
  return jsonRequest<GameplaySpec>("/api/design", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/**
 * Render the Blender Python for a plan, without running it.
 *
 * Displaying this is safe: `build_blender_script_artifact` formats a string and
 * returns the side effects a later confirmed run *would* have. The panel labels
 * it as not-executed so the distinction survives in the UI.
 */
export function previewBlenderScript(plan: BlenderPlan): Promise<BlenderScriptArtifact> {
  return jsonRequest<BlenderScriptArtifact>("/api/blender/script", {
    method: "POST",
    body: JSON.stringify(plan)
  });
}