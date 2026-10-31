import type { JourneyPanel, JourneyStepId } from "./productionJourney";

const STEPS_BY_PANEL: Record<JourneyPanel, readonly JourneyStepId[]> = {
  workbench: ["idea", "plan"],
  pipeline: ["orchestrate"],
  console: ["execute", "review", "qa"],
  assets: [],
  mcp: [],
  api: [],
  agent: []
};

const DEFAULT_STEP_BY_PANEL: Partial<Record<JourneyPanel, JourneyStepId>> = {
  workbench: "idea",
  pipeline: "orchestrate",
  console: "execute"
};

export function stepsForPanel(panel: JourneyPanel): readonly JourneyStepId[] {
  return STEPS_BY_PANEL[panel];
}

export function journeyStepForPanel(panel: JourneyPanel, value: string | null | undefined): JourneyStepId | null {
  const steps = stepsForPanel(panel);
  if (value && steps.includes(value as JourneyStepId)) return value as JourneyStepId;
  return DEFAULT_STEP_BY_PANEL[panel] ?? null;
}

export function panelOwnsJourneyStep(panel: JourneyPanel, step: JourneyStepId): boolean {
  return stepsForPanel(panel).includes(step);
}

export function withJourneyStep(path: string, step: JourneyStepId | null | undefined): string {
  if (!step) return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}step=${encodeURIComponent(step)}`;
}
