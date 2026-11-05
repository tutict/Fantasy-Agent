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

import type { DirectorBuildPlan, GameplaySpec, Locale } from "./types";
import displayZhCn from "../../../../fantasy_agent/display_zh_cn.json";

const chineseTexts = new Map(Object.entries({ ...displayZhCn.labels, ...displayZhCn.phrases }));
const titleTerms = displayZhCn.title_terms.map((term) => ({ ...term, pattern: new RegExp(term.pattern, "i"), removePattern: new RegExp(term.pattern, "gi") }));
const ignoredTitleWords = new Set(displayZhCn.title_ignored_words);
const planningTemplates = displayZhCn.templates.map((template) => ({ ...template, pattern: new RegExp(template.pattern) }));
const containsCjk = (value: string) => /[\u3400-\u9fff]/.test(value);

/** Known planning prose and enum labels; paths and tool identifiers stay literal. */
export function planningText(value: string | null | undefined, locale: Locale): string {
  const text = value ?? "";
  if (locale !== "zh-CN") return text;
  const translated = chineseTexts.get(text);
  if (translated !== undefined) return translated;
  const template = planningTemplates.find((item) => item.pattern.test(text));
  return template ? text.replace(template.pattern, template.text) : text;
}

function chineseTitle(value: string): string {
  const matched = titleTerms.filter((term) => term.pattern.test(value));
  const remaining = titleTerms.reduce((text, term) => text.replace(term.removePattern, " "), value);
  if ((remaining.match(/[A-Za-z0-9]+/g) ?? []).some((word) => !ignoredTitleWords.has(word.toLowerCase()))) return "";
  return matched.some((term) => term.mechanic) ? [...new Set(matched.map((term) => term.text))].join("") : "";
}

export function specFieldText(spec: GameplaySpec | null | undefined, path: string, fallback: string | undefined, locale: Locale): string {
  const original = fallback ?? "";
  const entry = spec?.i18n?.field_translations?.[path];
  const translated = locale === "zh-CN" && (!entry?.en || entry.en === original) ? entry?.["zh-CN"] : undefined;
  if (translated) {
    // Earlier bundles embedded an untranslated English prompt in the Chinese
    // summary. Repair that display only; the saved spec remains untouched.
    return path === "logline" ? translated.replace(/围绕「([^」]+)」/g, (match, topic: string) =>
      containsCjk(topic) ? match : `围绕「${chineseTitle(topic) || displayZhCn.default_title}」`
    ) : translated;
  }
  return planningText(original, locale);
}

export function specDisplayTitle(spec: GameplaySpec | null | undefined, locale: Locale): string {
  if (!spec) return "";
  const title = spec.title ?? "";
  if (locale === "en") return title;
  const entry = spec.i18n?.field_translations?.title;
  const translated = (!entry?.en || entry.en === title) ? entry?.["zh-CN"]?.trim() : undefined;
  if (translated && containsCjk(translated) && translated !== `${title} 原型`) return translated;
  if (containsCjk(title)) return title;
  // Unknown proper names are retained; only known generated descriptors change.
  return chineseTitle(title) || title;
}

type LocalizedValue = string | { en?: string; "zh-CN"?: string } | null | undefined;

/** Plan lists may hold either a plain string or an ``{en, "zh-CN"}`` pair. */
export function localizedValue(value: LocalizedValue, locale: Locale): string {
  if (value == null) return "";
  if (typeof value === "string") return planningText(value, locale);
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
  return planningText(item.title, locale);
}

export function planDisplayTitle(plan: DirectorBuildPlan | null | undefined, locale: Locale): string {
  return specDisplayTitle(plan?.gameplay_spec, locale);
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
