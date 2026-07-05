import type {
  ExecuteJob,
  ExecutePreview,
  ExecuteStart,
  ManualTargetsPayload,
  McpStatus
} from "./types";
import type { DirectorBuildPlan } from "./types";

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
  withVisuals: boolean
): Promise<ExecutePreview> {
  return jsonRequest<ExecutePreview>("/api/execute", {
    method: "POST",
    body: JSON.stringify({
      plan,
      engine,
      with_assets: withAssets,
      with_visuals: withVisuals,
      confirmed: false
    })
  });
}

export function startExecute(
  plan: DirectorBuildPlan,
  engine: string,
  withAssets: boolean,
  withVisuals: boolean
): Promise<ExecuteStart> {
  return jsonRequest<ExecuteStart>("/api/execute", {
    method: "POST",
    body: JSON.stringify({
      plan,
      engine,
      with_assets: withAssets,
      with_visuals: withVisuals,
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
