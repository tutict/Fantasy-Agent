import { describe, expect, it } from "vitest";

import { journeyStepForPanel, panelOwnsJourneyStep, stepsForPanel, withJourneyStep } from "./journeyRouting";

describe("journey step routing", () => {
  it("keeps only the steps that belong to each routed view", () => {
    expect(stepsForPanel("workbench")).toEqual(["idea", "plan"]);
    expect(stepsForPanel("console")).toEqual(["execute", "review", "qa"]);
    expect(stepsForPanel("pipeline")).toEqual(["orchestrate"]);
  });

  it("falls back to the route's first step when the query is missing or invalid", () => {
    expect(journeyStepForPanel("workbench", null)).toBe("idea");
    expect(journeyStepForPanel("console", "unknown")).toBe("execute");
    expect(journeyStepForPanel("pipeline", "review")).toBe("orchestrate");
  });

  it("writes a step without disturbing the route", () => {
    expect(withJourneyStep("/web-console", "review")).toBe("/web-console?step=review");
    expect(withJourneyStep("/web-console?mode=compact", "qa")).toBe("/web-console?mode=compact&step=qa");
    expect(panelOwnsJourneyStep("console", "review")).toBe(true);
    expect(panelOwnsJourneyStep("workbench", "review")).toBe(false);
  });
});
