import type {
  ApprovalManifestResponse,
  AssetExecuteJob,
  AssetExecutePreview,
  AssetExecuteStart,
  CreativeReview,
  ExecuteJob,
  ExecutePreview,
  ExecuteStart,
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

export function getMcpStatus(engine: string): Promise<McpStatus> {
  const query = new URLSearchParams({ engine });
  return jsonRequest<McpStatus>(`/api/mcp/status?${query.toString()}`);
}


export function writeApprovalManifest(
  review: CreativeReview,
  decisions: Record<string, string>,
  productionSpecBundle?: ProductionSpecBundle,
  target: 'godot' | 'unreal' = 'unreal'
): Promise<ApprovalManifestResponse> {
  return jsonRequest<ApprovalManifestResponse>("/api/creative-review/approval-manifest", {
    method: "POST",
    body: JSON.stringify({
      review,
      decisions,
      production_spec_bundle: productionSpecBundle,
      target
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
