import type { DirectorBuildPlan, Locale, PlanningHandoff, Theme } from "./types";

export const HANDOFF_KEY = "fantasy-agent-planning-handoff";
export const THEME_KEY = "fantasy-agent-theme";
/**
 * The only locale key. The console and the workbench each used to carry their
 * own, because each was its own document; `LocaleThemeProvider` is the single
 * owner now, so one key is the whole truth. A locale chosen in the old console
 * or workbench is not migrated -- it costs one click to re-pick.
 */
export const STUDIO_LOCALE_KEY = "fantasy-agent-studio-locale";
export const STUDIO_SIDEBAR_WIDTH_KEY = "fantasy-agent-studio-sidebar-width";
export const STUDIO_SIDEBAR_COLLAPSED_KEY = "fantasy-agent-studio-sidebar-collapsed";
/**
 * The orchestration board's session id.
 *
 * The board picks the id itself and posts it with every pass, so it has to
 * survive a reload: the server keeps a session's stage outcomes in memory, and
 * a board that forgot its id would ask for a fresh one and show the plan as if
 * nothing had run -- while the outcomes it actually paid for sat in the server
 * under the old id.
 */
export const ORCHESTRATION_SESSION_KEY = "fantasy-agent-orchestration-session";

/** The stored session id, or null when there is none or storage is unavailable. */
export function readOrchestrationSessionId(): string | null {
  try {
    return localStorage.getItem(ORCHESTRATION_SESSION_KEY);
  } catch {
    return null;
  }
}

export function saveOrchestrationSessionId(sessionId: string): void {
  try {
    localStorage.setItem(ORCHESTRATION_SESSION_KEY, sessionId);
  } catch {
    // A read-only storage costs the board its session across a reload, which is
    // a smaller loss than failing the pass.
  }
}

export function initialLocale(storageKey: string): Locale {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("locale") || localStorage.getItem(storageKey);
  if (requested === "zh-CN" || requested === "en") return requested;
  return navigator.language?.startsWith("zh") ? "zh-CN" : "en";
}

export function initialTheme(): Theme {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("theme") || localStorage.getItem(THEME_KEY);
  if (requested === "light" || requested === "dark") return requested;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * The four states the stored handoff can be in, decoded once.
 *
 * Split out because two readers need different halves of it: the console wants
 * the whole handoff, the shell only wants the plan inside it (to pick a default
 * engine version). The shell used to `JSON.parse` the key itself to get at the
 * plan, which meant a second decoder that also lost the distinction between
 * "nothing stored" and "stored but unreadable" -- it answered "UE5" to both.
 */
type StoredHandoff =
  | { state: "empty" }
  | { state: "invalid" }
  | { state: "handoff"; handoff: PlanningHandoff }
  | { state: "plan"; plan: DirectorBuildPlan };

function decodeStoredHandoff(): StoredHandoff {
  let raw: string | null;
  try {
    raw = localStorage.getItem(HANDOFF_KEY);
  } catch {
    return { state: "invalid" };
  }

  if (!raw) return { state: "empty" };

  try {
    const parsed = JSON.parse(raw) as PlanningHandoff | DirectorBuildPlan;
    if ("plan" in parsed && parsed.plan?.gameplay_spec) {
      return { state: "handoff", handoff: parsed };
    }
    if ("gameplay_spec" in parsed && parsed.gameplay_spec) {
      return { state: "plan", plan: parsed };
    }
  } catch {
    return { state: "invalid" };
  }

  return { state: "invalid" };
}

/** The plan inside the stored handoff, or `null` when there is no usable one. */
export function readHandoffPlan(): DirectorBuildPlan | null {
  const stored = decodeStoredHandoff();
  if (stored.state === "handoff") return stored.handoff.plan ?? null;
  if (stored.state === "plan") return stored.plan;
  return null;
}

export function readPlanningHandoff(preferredTitle: (plan: DirectorBuildPlan) => string): PlanningHandoff | null {
  const stored = decodeStoredHandoff();

  if (stored.state === "empty") return null;
  if (stored.state === "invalid") return { invalid: true };
  if (stored.state === "handoff") return stored.handoff;

  return {
    schemaVersion: "0.1",
    source: "direct-plan",
    savedAt: null,
    title: preferredTitle(stored.plan),
    plan: stored.plan
  };
}

export function savePlanningHandoff(plan: DirectorBuildPlan, title: string, source = "planning-workbench"): PlanningHandoff {
  const handoff = {
    schemaVersion: "0.1",
    source,
    savedAt: new Date().toISOString(),
    title,
    plan
  };
  localStorage.setItem(HANDOFF_KEY, JSON.stringify(handoff));
  return handoff;
}
