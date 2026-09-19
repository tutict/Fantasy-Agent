import { beforeEach, describe, expect, it } from "vitest";
import { HANDOFF_KEY, readHandoffPlan, readPlanningHandoff } from "./storage";
import type { DirectorBuildPlan, PlanningHandoff } from "./types";

/**
 * `decodeStoredHandoff` has four states and every reader depends on the
 * distinctions: "nothing stored" must not read as "stored but unreadable"
 * (the shell used to answer "UE5" to both). Only the handoff and empty states
 * were exercised elsewhere, indirectly; the invalid and bare-plan decodes are
 * pinned here.
 */

const PLAN = {
  title: "迷雾之外",
  gameplay_spec: { title: "迷雾之外" }
} as unknown as DirectorBuildPlan;

function store(value: unknown): void {
  localStorage.setItem(HANDOFF_KEY, JSON.stringify(value));
}

beforeEach(() => {
  localStorage.clear();
});

describe("readHandoffPlan", () => {
  it("answers null for empty storage", () => {
    expect(readHandoffPlan()).toBeNull();
  });

  it("reads the plan out of a stored handoff", () => {
    store({ schemaVersion: "0.1", source: "planning-workbench", plan: PLAN });
    expect(readHandoffPlan()).toEqual(PLAN);
  });

  it("reads a bare plan stored without a handoff wrapper", () => {
    store(PLAN);
    expect(readHandoffPlan()).toEqual(PLAN);
  });

  it("answers null for a plan without a gameplay spec", () => {
    store({ title: "not a plan" });
    expect(readHandoffPlan()).toBeNull();
  });

  it("answers null for unreadable JSON", () => {
    localStorage.setItem(HANDOFF_KEY, "{not json");
    expect(readHandoffPlan()).toBeNull();
  });
});

describe("readPlanningHandoff", () => {
  it("answers null for empty storage", () => {
    expect(readPlanningHandoff(() => "t")).toBeNull();
  });

  it("passes a stored handoff through unchanged", () => {
    const handoff: PlanningHandoff = {
      schemaVersion: "0.1",
      source: "planning-workbench",
      savedAt: "2026-09-19T00:00:00.000Z",
      title: "迷雾之外",
      plan: PLAN
    };
    store(handoff);
    expect(readPlanningHandoff(() => "t")).toEqual(handoff);
  });

  it("wraps a bare plan into a direct-plan handoff", () => {
    store(PLAN);
    const result = readPlanningHandoff(() => "preferred title");
    expect(result).toMatchObject({
      source: "direct-plan",
      title: "preferred title",
      plan: PLAN
    });
  });

  it("reports the invalid state instead of guessing", () => {
    localStorage.setItem(HANDOFF_KEY, "{not json");
    expect(readPlanningHandoff(() => "t")).toEqual({ invalid: true });
  });

  it("reports the invalid state for a shape nobody wrote", () => {
    store({ schemaVersion: "0.1", plan: { title: "no gameplay_spec" } });
    expect(readPlanningHandoff(() => "t")).toEqual({ invalid: true });
  });
});
