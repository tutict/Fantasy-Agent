import type { DirectorBuildPlan, Locale, PlanningHandoff, Theme } from "./types";

export const HANDOFF_KEY = "fantasy-agent-planning-handoff";
export const THEME_KEY = "fantasy-agent-theme";
export const CONSOLE_LOCALE_KEY = "fantasy-agent-web-console-locale";
export const STUDIO_LOCALE_KEY = "fantasy-agent-studio-locale";
export const STUDIO_SIDEBAR_WIDTH_KEY = "fantasy-agent-studio-sidebar-width";
export const STUDIO_SIDEBAR_COLLAPSED_KEY = "fantasy-agent-studio-sidebar-collapsed";

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

export function readPlanningHandoff(preferredTitle: (plan: DirectorBuildPlan) => string): PlanningHandoff | null {
  try {
    const raw = localStorage.getItem(HANDOFF_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PlanningHandoff | DirectorBuildPlan;
    if ("plan" in parsed && parsed.plan?.gameplay_spec) return parsed;
    if ("gameplay_spec" in parsed && parsed.gameplay_spec) {
      return {
        schemaVersion: "0.1",
        source: "direct-plan",
        savedAt: null,
        title: preferredTitle(parsed),
        plan: parsed
      };
    }
  } catch {
    return { invalid: true };
  }
  return { invalid: true };
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
