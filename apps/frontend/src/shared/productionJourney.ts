import type { DirectorBuildPlan, OrchestrationSession } from "./types";

export type JourneyStepId = "idea" | "plan" | "orchestrate" | "execute" | "review" | "qa";
export type JourneyPanel = "workbench" | "pipeline" | "console" | "mcp" | "api" | "agent";
export type OperationPhase = "idle" | "preview" | "confirming" | "running" | "cancelable" | "succeeded" | "degraded" | "failed" | "resumable";
export type JourneyStepState = "complete" | "current" | "blocked" | "attention" | "upcoming";

export interface JourneyStep {
  id: JourneyStepId;
  state: JourneyStepState;
  reasonKey: string;
}

export interface JourneySnapshot {
  projectTitle: string;
  engineLabel: string;
  targetMinutes: string;
  currentStep: JourneyStepId;
  blocker: string;
  nextActionKey: string;
  steps: JourneyStep[];
}

const ORDER: JourneyStepId[] = ["idea", "plan", "orchestrate", "execute", "review", "qa"];

export const JOURNEY_PANELS: Record<JourneyStepId, JourneyPanel> = {
  idea: "workbench",
  plan: "workbench",
  orchestrate: "pipeline",
  execute: "console",
  review: "console",
  qa: "console"
};

export const JOURNEY_STEP_KEYS = {
  idea: "journeyIdea",
  plan: "journeyPlan",
  orchestrate: "journeyOrchestrate",
  execute: "journeyExecute",
  review: "journeyReview",
  qa: "journeyQa"
} as const;

export const JOURNEY_STATE_KEYS: Record<JourneyStepState, string> = {
  current: "journeyStateCurrent",
  complete: "journeyStateComplete",
  blocked: "journeyStateBlocked",
  attention: "journeyStateAttention",
  upcoming: "journeyStateUpcoming"
};

export function operationPhase(input: { status?: string; hasPreview?: boolean; confirming?: boolean; resumable?: boolean }): OperationPhase {
  if (input.confirming) return "confirming";
  if (input.hasPreview) return "preview";
  if (input.status === "running") return input.resumable ? "cancelable" : "running";
  if (input.status === "failed" || input.status === "error") return input.resumable ? "resumable" : "failed";
  if (input.status === "degraded") return "degraded";
  if (input.status === "done" || input.status === "passed") return "succeeded";
  return "idle";
}

export function operationReason(phase: OperationPhase): string {
  return {
    idle: "operationIdle",
    preview: "operationPreview",
    confirming: "operationConfirming",
    running: "operationRunning",
    cancelable: "operationCancelable",
    succeeded: "operationSucceeded",
    degraded: "operationDegraded",
    failed: "operationFailed",
    resumable: "operationResumable"
  }[phase];
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function hasPlan(plan: DirectorBuildPlan | null | undefined): boolean {
  return Boolean(plan?.gameplay_spec?.title || plan?.production_pipeline?.stages?.length);
}

function engineLabel(plan: DirectorBuildPlan | null | undefined): string {
  const stages = plan?.production_pipeline?.stages ?? [];
  return stages.some((stage) => stage.id === "godot_quick_play")
    ? text(plan?.godot_plan?.engine_version, "Godot 4")
    : text(plan?.unreal_plan?.engine_version, "UE5");
}

function stateFor(id: JourneyStepId, current: JourneyStepId, blocked: boolean, attention: boolean): JourneyStepState {
  if (id === current) return blocked ? "blocked" : attention ? "attention" : "current";
  return ORDER.indexOf(id) < ORDER.indexOf(current) ? "complete" : "upcoming";
}

export function journeySnapshot(input: {
  plan: DirectorBuildPlan | null | undefined;
  session?: OrchestrationSession | null;
  executionStatus?: string;
  reviewPending?: number;
  qaStatus?: string;
}): JourneySnapshot {
  const plan = input.plan;
  const planned = hasPlan(plan);
  const session = input.session;
  const stages = session?.stages ?? [];
  const failed = stages.find((stage) => stage.status === "failed");
  const waiting = stages.find((stage) => stage.status === "awaiting_confirmation" || stage.status === "awaiting_human");
  const reviewPending = input.reviewPending ?? 0;
  const execution = input.executionStatus ?? "";
  const qa = input.qaStatus ?? "";

  let current: JourneyStepId = "idea";
  let blocker = "";
  let nextActionKey = "journeyNextIdea";
  if (!planned) {
    current = "idea";
  } else if (!session?.session_id) {
    current = "plan";
    nextActionKey = "journeyNextPlan";
  } else if (failed) {
    current = "orchestrate";
    blocker = text(failed.detail, text(failed.title, "failed"));
    nextActionKey = "journeyNextRework";
  } else if (waiting) {
    current = "orchestrate";
    blocker = text(waiting.title, "confirmation");
    nextActionKey = "journeyNextConfirm";
  } else if (reviewPending > 0) {
    current = "review";
    blocker = String(reviewPending);
    nextActionKey = "journeyNextReview";
  } else if (execution === "running" || execution === "failed") {
    current = "execute";
    blocker = execution === "failed" ? execution : "";
    nextActionKey = execution === "failed" ? "journeyNextInspect" : "journeyNextExecute";
  } else if (qa === "failed" || qa === "warning") {
    current = "qa";
    blocker = qa;
    nextActionKey = "journeyNextQa";
  } else if (qa === "passed") {
    current = "qa";
    nextActionKey = "journeyNextDone";
  } else if (execution === "done") {
    current = "review";
    nextActionKey = "journeyNextReview";
  } else {
    current = "orchestrate";
    nextActionKey = "journeyNextOrchestrate";
  }

  const steps = ORDER.map((id) => ({
    id,
    state: stateFor(id, current, Boolean(blocker), execution === "running"),
    reasonKey: id === current ? nextActionKey : id
  }));

  return {
    projectTitle: text(plan?.gameplay_spec?.title, text(plan?.production_pipeline?.project_name, "")),
    engineLabel: planned ? engineLabel(plan) : "",
    targetMinutes: plan?.gameplay_spec?.target_session_minutes ? String(plan.gameplay_spec.target_session_minutes) : "",
    currentStep: current,
    blocker,
    nextActionKey,
    steps
  };
}
