import type { CreativeReview, DirectorBuildPlan, OrchestrationSession } from "./types";

export interface ProjectBinding { project_id: string; plan_version: number }
export interface ProjectResource extends ProjectBinding {
  resource_id: string; name?: string; path?: string; mime_type?: string; job_id?: string;
}
export interface WorkflowJob extends ProjectBinding {
  job_id: string; tool_name: string; status: string; session_id?: string;
  result?: { status?: string; kind?: string; data?: Record<string, unknown> };
}
export interface WorkflowJobDetail extends WorkflowJob {
  detail_read_failed?: boolean;
  summary?: string; resources?: ProjectResource[]; logs?: string[];
  progress?: { stages?: Array<{ name?: string; status?: string; detail?: string }> };
  blockers?: string[];
  next_actions?: Array<string | { tool?: string; arguments?: Record<string, unknown>; summary?: string }>;
}
export interface ProjectSnapshot extends ProjectBinding {
  creative_review?: CreativeReview;
  name: string; plan: DirectorBuildPlan | null; tasks: unknown[]; jobs: WorkflowJob[];
  sessions: unknown[]; resources: ProjectResource[]; decisions: unknown[] | Record<string, unknown>;
  created_at: string | number; updated_at: string | number;
  authorizations: Array<{ grant_id: string; plan_version: number; active: boolean; remaining_seconds: number;
    actions: Array<{ tool_name?: string; [key: string]: unknown }> }>;
}
export interface ProjectWorkflow extends Partial<OrchestrationSession>, ProjectBinding {}
export interface ProjectDraft { plan: DirectorBuildPlan; baseVersion: number }
