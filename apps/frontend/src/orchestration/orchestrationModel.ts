/**
 * The board's model: one card shape, fed from either of its two sources.
 *
 * The board is the only thing in the frontend that renders
 * `production_pipeline`. It reads it in two situations, and they carry
 * different amounts of truth:
 *
 *   - **Before a run.** The plan the workbench handed off, straight out of
 *     localStorage. Every card has a `plan_status` written at authoring time and
 *     nothing else -- no run has touched it.
 *   - **After a run.** The server's session payload, where each card carries
 *     that same plan-time status *plus* what this pass actually did.
 *
 * Both are normalised to `BoardCard` here rather than in the component, so the
 * rendering code has exactly one shape to handle and the "which source wins"
 * question is answerable in a unit test instead of by reading JSX.
 *
 * Field names stay snake_case because they mirror the wire. That is deliberate:
 * `localizedTitle()` takes `{ title, title_i18n }` structurally, and a
 * rename-on-the-way-in is one more place a field can be dropped silently --
 * which is the failure mode F0 of the UI replan existed to close.
 */

import type { Locale, OrchestrationSession, OrchestrationStageCard, PipelineStage } from "../shared/types";
import type { DirectorBuildPlan } from "../shared/types";

/**
 * Mirrors `contracts.ProductionStageKind`. A stage of this kind is a gate no
 * tool may run in, so the card offers a way to *reach* the approval screen
 * instead of a tool list -- and never an approve button of its own, because
 * approving a human gate would not make it run.
 */
export const HUMAN_STAGE_KIND = "human";

/**
 * The runtime vocabulary, mirroring `orchestrator.py`.
 *
 * `plan_status` is a different vocabulary (`ProductionTaskStatus`) and is not
 * listed here -- the two are deliberately kept apart, and `RUNTIME_STATUSES` is
 * what the board's status filter is checked against.
 */
export const RUNTIME_STATUSES = [
  "pending",
  "ready",
  "running",
  "blocked",
  "awaiting_human",
  "awaiting_confirmation",
  "done",
  "failed"
] as const;

export type RuntimeStatus = (typeof RUNTIME_STATUSES)[number];

/**
 * Mirrors `contracts.ProductionTaskStatus`: the four states a stage can be
 * authored in. All four names also exist in `RUNTIME_STATUSES` and mean
 * something different there, which is why the two are separate lists even
 * though the labels are shared.
 */
export const PLAN_STATUSES = ["pending", "ready", "blocked", "done"] as const;

/**
 * Status -> translation key.
 *
 * A table rather than a template string so every label is a literal in the
 * source: the i18n orphan guard reads bare quoted strings, and `"orchestration" +
 * capitalise(status)` would leave every one of these looking like a key nothing
 * calls. `plan_status` gets its own prefix because the two vocabularies overlap
 * on `blocked` / `ready` / `done` / `pending` and mean different things by them.
 */
export const STATUS_LABEL_KEYS: Record<RuntimeStatus, string> = {
  pending: "orchestrationStatusPending",
  ready: "orchestrationStatusReady",
  running: "orchestrationStatusRunning",
  blocked: "orchestrationStatusBlocked",
  awaiting_human: "orchestrationStatusAwaitingHuman",
  awaiting_confirmation: "orchestrationStatusAwaitingConfirmation",
  done: "orchestrationStatusDone",
  failed: "orchestrationStatusFailed"
};

export interface BoardCard {
  id: string;
  order: number;
  title: string;
  title_i18n?: Partial<Record<Locale, string>>;
  kind: string;
  purpose: string;
  owner_agent: string;
  depends_on: string[];
  mcp_tools: string[];
  quality_gates: string[];
  risks: string[];
  exit_checks: string[];
  /** Execution-layer steps this card owns; empty for the human gate. */
  executor_stages: string[];
  requires_confirmation: boolean;
  confirmed: boolean;
  /** Written once at authoring time; never moves during a run. */
  plan_status: string;
  /** What this pass actually did. `pending` until something runs. */
  status: string;
  detail: string;
  tools: string[];
  dispatched: boolean;
  tool_calls: number;
  refusals: string[];
  /** Exit checks that ran and passed. */
  checks: string[];
  answer: string;
}

const EMPTY_CARD = {
  kind: "agent",
  purpose: "",
  owner_agent: "",
  depends_on: [] as string[],
  mcp_tools: [] as string[],
  quality_gates: [] as string[],
  risks: [] as string[],
  exit_checks: [] as string[],
  executor_stages: [] as string[],
  requires_confirmation: false,
  confirmed: false,
  plan_status: "pending",
  status: "pending",
  detail: "",
  tools: [] as string[],
  dispatched: false,
  tool_calls: 0,
  refusals: [] as string[],
  checks: [] as string[],
  answer: ""
};

/** Plan order, with a stable tiebreak so two cards at one `order` never swap. */
function byOrder<T extends { order: number; id: string }>(cards: T[]): T[] {
  return [...cards].sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
}

/** Cards straight from a handed-off plan: plan-time fields only. */
export function cardsFromPlan(plan: DirectorBuildPlan | null | undefined): BoardCard[] {
  const stages = plan?.production_pipeline?.stages;
  if (!Array.isArray(stages) || !stages.length) return [];

  return byOrder(
    stages.map((stage: PipelineStage, index): BoardCard => ({
      ...EMPTY_CARD,
      id: text(stage.id, `stage-${index + 1}`),
      order: typeof stage.order === "number" ? stage.order : index + 1,
      title: text(stage.title),
      title_i18n: stage.title_i18n,
      kind: text(stage.kind, "agent"),
      purpose: text(stage.purpose),
      owner_agent: text(stage.owner_agent),
      depends_on: strings(stage.depends_on),
      mcp_tools: strings(stage.mcp_tools),
      quality_gates: strings(stage.quality_gates),
      risks: strings(stage.risks),
      exit_checks: strings(stage.exit_checks),
      requires_confirmation: stage.requires_confirmation === true,
      plan_status: text(stage.status, "pending")
    }))
  );
}

/** Cards from a run payload: the same plan-time fields plus the runtime ones. */
export function cardsFromSession(session: OrchestrationSession | null | undefined): BoardCard[] {
  const stages = session?.stages;
  if (!Array.isArray(stages) || !stages.length) return [];

  return byOrder(
    stages.map((stage: OrchestrationStageCard, index): BoardCard => ({
      ...EMPTY_CARD,
      id: text(stage.stage_id, `stage-${index + 1}`),
      order: typeof stage.order === "number" ? stage.order : index + 1,
      title: text(stage.title),
      title_i18n: stage.title_i18n,
      kind: text(stage.kind, "agent"),
      purpose: text(stage.purpose),
      owner_agent: text(stage.owner_agent),
      depends_on: strings(stage.depends_on),
      mcp_tools: strings(stage.mcp_tools),
      quality_gates: strings(stage.quality_gates),
      risks: strings(stage.risks),
      exit_checks: strings(stage.exit_checks),
      executor_stages: strings(stage.executor_stages),
      requires_confirmation: stage.requires_confirmation === true,
      confirmed: stage.confirmed === true,
      plan_status: text(stage.plan_status, "pending"),
      status: text(stage.status, "pending"),
      detail: text(stage.detail),
      tools: strings(stage.tools),
      dispatched: stage.dispatched === true,
      tool_calls: typeof stage.tool_calls === "number" ? stage.tool_calls : 0,
      refusals: strings(stage.refusals),
      checks: strings(stage.checks),
      answer: text(stage.answer)
    }))
  );
}

/**
 * The cards to render.
 *
 * A session wins whenever it has stages, and that is not a preference: the
 * handoff in localStorage is whatever the operator last edited, while the
 * session's stages are the plan the orchestrator actually advanced. Showing the
 * other one would put a run's statuses next to a different plan's cards.
 */
export function boardCards(
  plan: DirectorBuildPlan | null | undefined,
  session: OrchestrationSession | null | undefined
): BoardCard[] {
  const fromSession = cardsFromSession(session);
  return fromSession.length ? fromSession : cardsFromPlan(plan);
}

/** The gates that need a person, and that the board cannot unblock by itself. */
export function humanGates(cards: BoardCard[]): BoardCard[] {
  return cards.filter((card) => card.kind === HUMAN_STAGE_KIND);
}

/**
 * Cards an approve button may be shown on.
 *
 * A human gate is excluded on purpose, and the reason is the orchestrator's own:
 * approving a gate does not make it run, so `pending_confirmations` leaves it
 * out too. A button there would look like a control and do nothing.
 */
export function approvableCards(cards: BoardCard[]): BoardCard[] {
  return cards.filter(
    (card) => card.requires_confirmation && card.kind !== HUMAN_STAGE_KIND && !card.confirmed
  );
}

/** Cards a rework button may be shown on: the ones a pass has actually reached. */
export function reworkableCards(cards: BoardCard[]): BoardCard[] {
  return cards.filter((card) => card.status !== "pending");
}

/**
 * The execution steps behind a card.
 *
 * The session's translation table is route metadata -- the same eight entries
 * whether or not anything has run -- so the drill-down is available from the
 * first render. The plan-time `executor_stages` is the fallback for a board
 * that has not reached the server yet.
 */
export function drilldown(card: BoardCard, translation: Record<string, string[]>): string[] {
  const fromTable = translation?.[card.id];
  return Array.isArray(fromTable) ? fromTable : card.executor_stages;
}

/** The label key for a runtime status, falling back to the raw string. */
export function statusLabelKey(status: string): string {
  return (RUNTIME_STATUSES as readonly string[]).includes(status)
    ? STATUS_LABEL_KEYS[status as RuntimeStatus]
    : "";
}

/**
 * A session id the board can query before it has run anything.
 *
 * Picked client-side rather than by the server so `GET /api/orchestration/{id}`
 * is answerable from the first render -- the drill-down table and any earlier
 * pass's outcomes both arrive through that call. The server honours whatever id
 * it is handed, and the board stores it (`ORCHESTRATION_SESSION_KEY`) so a
 * reload comes back to the same session instead of orphaning the outcomes the
 * server kept under the old one.
 */
export function newSessionId(): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `orch-${Date.now().toString(36)}-${random}`;
}
