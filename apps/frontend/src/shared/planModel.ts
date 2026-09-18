/**
 * Pure helpers for reading a plan.
 *
 * These began in `workbench/workbenchModel.ts`, but the shared plan panels need
 * them too, and a module under `shared/` may not import from an entry point's
 * folder -- the dependency only ever points the other way. They are pure and
 * have no entry-point knowledge, so `shared/` is where they belong.
 *
 * `workbenchModel.ts` re-exports them, so callers and tests that learned the
 * old path keep working and there is still exactly one implementation.
 */

import type { DirectorBuildPlan, Locale } from "./types";

type LocalizedValue = string | { en?: string; "zh-CN"?: string } | null | undefined;

/** Plan lists may hold either a plain string or an ``{en, "zh-CN"}`` pair. */
export function localizedValue(value: LocalizedValue, locale: Locale): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return (locale === "zh-CN" ? value["zh-CN"] : value.en) ?? value.en ?? value["zh-CN"] ?? "";
}

export function localizedArray(items: unknown, locale: Locale): string[] {
  if (!Array.isArray(items)) return [];
  return items.map((item) => localizedValue(item as LocalizedValue, locale));
}

/**
 * Pipeline stages and task items carry ``title_i18n`` instead of a localized
 * array, so they need their own helper.
 */
export function localizedTitle(
  item: { title?: string; title_i18n?: Partial<Record<Locale, string>> } | null | undefined,
  locale: Locale
): string {
  if (!item) return "";
  const translated = item.title_i18n?.[locale];
  if (translated) return translated;
  return item.title ?? "";
}

export function planDisplayTitle(plan: DirectorBuildPlan | null | undefined, locale: Locale): string {
  const spec = plan?.gameplay_spec;
  if (!spec) return "";
  const translations = (
    spec as { i18n?: { field_translations?: Record<string, Partial<Record<Locale, string>>> } }
  ).i18n?.field_translations;
  if (locale === "zh-CN") {
    const translated = translations?.title?.["zh-CN"];
    if (translated) return translated;
  }
  return spec.title ?? "";
}

/**
 * True when the pipeline was planned for Godot. Drives which engine plan the
 * build panel shows.
 */
export function usesGodotEngine(plan: DirectorBuildPlan | null | undefined): boolean {
  return Boolean(
    plan?.production_pipeline?.stages?.some((stage) => stage.id === "godot_quick_play")
  );
}

export function selectedEngineVersion(plan: DirectorBuildPlan | null): string {
  if (!plan) return "UE5";
  return usesGodotEngine(plan)
    ? plan.godot_plan?.engine_version || "Godot 4"
    : plan.unreal_plan?.engine_version || "UE5";
}