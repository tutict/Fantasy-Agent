import { describe, expect, it } from "vitest";
import { journeySnapshot, operationPhase } from "./productionJourney";
import type { DirectorBuildPlan, OrchestrationSession } from "./types";

const plan: DirectorBuildPlan = {
  gameplay_spec: { title: "Rooftop Chase", target_session_minutes: 10 },
  production_pipeline: { project_name: "Rooftop", stages: [{ id: "godot_quick_play" }] },
  godot_plan: { engine_version: "Godot 4" }
};

describe("production journey", () => {
  it("starts at the idea when no plan exists", () => {
    const snapshot = journeySnapshot({ plan: null });
    expect(snapshot.currentStep).toBe("idea");
    expect(snapshot.steps.map((step) => step.state)).toEqual(["current", "upcoming", "upcoming", "upcoming", "upcoming", "upcoming"]);
  });

  it("moves from a handed-off plan to orchestration once a session exists", () => {
    expect(journeySnapshot({ plan }).currentStep).toBe("plan");
    const session: OrchestrationSession = { session_id: "sess", stages: [{ stage_id: "play", status: "ready" }] };
    expect(journeySnapshot({ plan, session }).currentStep).toBe("orchestrate");
  });

  it("surfaces a failed stage as a blocker with rework as the next action", () => {
    const session: OrchestrationSession = { session_id: "sess", stages: [{ stage_id: "blender", title: "Blender", status: "failed", detail: "missing binary" }] };
    const snapshot = journeySnapshot({ plan, session });
    expect(snapshot.currentStep).toBe("orchestrate");
    expect(snapshot.blocker).toBe("missing binary");
    expect(snapshot.nextActionKey).toBe("journeyNextRework");
    expect(snapshot.steps.find((step) => step.id === "orchestrate")?.state).toBe("blocked");
  });

  it("tracks review and QA after execution", () => {
    const session: OrchestrationSession = { session_id: "sess", stages: [{ status: "done" }] };
    expect(journeySnapshot({ plan, session, executionStatus: "done", reviewPending: 2 }).currentStep).toBe("review");
    expect(journeySnapshot({ plan, session, executionStatus: "done", qaStatus: "passed" }).currentStep).toBe("qa");
  });

  it("names every lifecycle a long operation can occupy", () => {
    expect(operationPhase({})).toBe("idle");
    expect(operationPhase({ hasPreview: true })).toBe("preview");
    expect(operationPhase({ confirming: true, hasPreview: true })).toBe("confirming");
    expect(operationPhase({ status: "running", resumable: true })).toBe("cancelable");
    expect(operationPhase({ status: "failed", resumable: true })).toBe("resumable");
    expect(operationPhase({ status: "degraded" })).toBe("degraded");
    expect(operationPhase({ status: "done" })).toBe("succeeded");
  });
});