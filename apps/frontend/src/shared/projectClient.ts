/** Pure project HTTP client. Keep independent of api.ts: its workflow adapters read the store. */
import type { DirectorBuildPlan } from "./types";
import type { ProjectSnapshot, ProjectWorkflow, WorkflowJobDetail } from "./projectTypes";

export class ProjectConflict extends Error {
  constructor(public latest: ProjectSnapshot) { super("计划版本已改变，请核对最新计划后重试。"); }
}
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) } });
  const payload = await response.json();
  if (!response.ok) {
    if (response.status === 409) {
      const latest = payload.latest ?? payload.detail?.latest;
      if (latest?.project_id) throw new ProjectConflict(latest);
    }
    const message = payload.detail ?? payload.summary ?? payload.error;
    throw new Error(typeof message === "string" ? message : `HTTP ${response.status}`);
  }
  return payload as T;
}
const projectUrl = (id: string) => `/api/projects/${encodeURIComponent(id)}`;
export const projectClient = {
  list: () => request<{ projects: ProjectSnapshot[] }>("/api/projects"),
  get: (id: string) => request<ProjectSnapshot>(projectUrl(id)),
  create: (name: string, plan?: DirectorBuildPlan) => request<ProjectSnapshot>("/api/projects", { method: "POST", body: JSON.stringify({ name, plan }) }),
  importLegacy: (plan: DirectorBuildPlan) => request<ProjectSnapshot>("/api/projects/import", { method: "POST", body: JSON.stringify({ plan, import_key: "legacy-handoff" }) }),
  save: (id: string, plan: DirectorBuildPlan, version: number) => request<ProjectSnapshot>(`/api/projects/${encodeURIComponent(id)}/plan`, { method: "PUT", body: JSON.stringify({ plan, expected_version: version }) }),
  workflow: (id: string) => request<ProjectWorkflow>(`/api/projects/${encodeURIComponent(id)}/workflow`),
  job: (id: string, job: string) => request<WorkflowJobDetail>(`/api/projects/${encodeURIComponent(id)}/jobs/${encodeURIComponent(job)}`),
  cancel: (id: string, job: string) => request(`/api/projects/${encodeURIComponent(id)}/jobs/${encodeURIComponent(job)}/cancel`, { method: "POST" }),
  resource: (id: string, resource: string) => request<{ data: unknown; mime_type: string; encoding?: "base64" }>(`/api/projects/${encodeURIComponent(id)}/resources/${encodeURIComponent(resource)}`)
};
