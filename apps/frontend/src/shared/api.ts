import type {
  ApprovalManifestResponse,
  AssetExecuteJob,
  AssetExecutePreview,
  AssetExecuteStart,
  CreativeReview,
  ExecuteJob,
  ExecutePreview,
  ExecuteStart,
  JobCancelResponse,
  LlmApiSettings,
  LlmApiSettingsInput,
  LlmApiTestResult,
  ManualTargetsPayload,
  McpStatus,
  ProductionSpecBundle,
  SpecBundlePreviewResponse
} from "./types";
import type { DirectorBuildPlan, EnemyPressureTuning } from "./types";

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
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getManualCorrectionTargets(engine: string): Promise<ManualTargetsPayload> {
  const query = new URLSearchParams({ engine });
  return jsonRequest<ManualTargetsPayload>(`/api/manual-correction/targets?${query.toString()}`);
}

export function openManualCorrectionTarget(targetId: string, engine: string): Promise<Record<string, string>> {
  return jsonRequest<Record<string, string>>("/api/manual-correction/open", {
    method: "POST",
    body: JSON.stringify({
      target_id: targetId,
      engine,
      confirmed_side_effects: true
    })
  });
}

export function previewExecute(
  plan: DirectorBuildPlan,
  engine: string,
  withAssets: boolean,
  withVisuals: boolean,
  withGameplay: boolean,
  enemyTuning: EnemyPressureTuning,
  approvalManifestPath?: string
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
  approvalManifestPath?: string
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
      confirmed: true
    })
  });
}

export function getExecuteJob(jobId: string): Promise<ExecuteJob> {
  return jsonRequest<ExecuteJob>(`/api/execute/${encodeURIComponent(jobId)}`);
}

export function cancelExecuteJob(jobId: string): Promise<JobCancelResponse> {
  return jsonRequest<JobCancelResponse>(`/api/execute/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST"
  });
}

export function getMcpStatus(engine: string): Promise<McpStatus> {
  const query = new URLSearchParams({ engine });
  return jsonRequest<McpStatus>(`/api/tool-status?${query.toString()}`);
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