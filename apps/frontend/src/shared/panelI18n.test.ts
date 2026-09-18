import { describe, expect, it } from "vitest";

import { consoleI18n, makeTranslator, workbenchI18n } from "./i18n";
// Vite inlines these at transform time. Reading the source text beats calling
// `toString()` on a transformed component: esbuild rewrites the JSX and does not
// reliably preserve the `t("...")` calls, so a runtime extractor under-reports
// silently -- and a guard that under-reports is worse than none.
import consoleSource from "../console/rendering.tsx?raw";
import sharedPanelSource from "./panels/PlanPanels.tsx?raw";
import workbenchSource from "../workbench/PlanPanels.tsx?raw";

/**
 * Guard for the shared plan panels.
 *
 * The six panels the console and the planning workbench share are one
 * implementation now, in `shared/panels/PlanPanels.tsx`, and each entry point
 * still injects its own translator:
 *
 *   - the console renders them with `consoleI18n`
 *   - the workbench renders them with `workbenchI18n`
 *
 * That is the whole risk of the merge. `makeTranslator` falls back to `|| key`,
 * so a panel calling a key its dictionary lacks prints the literal key name --
 * no exception, no type error, and every rendering test stays green. Before the
 * lift the two dictionaries diverged by 19 keys in one direction and 7 in the
 * other; both gaps are closed, and this file is what keeps them closed.
 *
 * The key lists are read from source text via `?raw` rather than from the
 * imported modules -- see the import comment for why.
 */

/**
 * English strings that legitimately equal their own key (`minutes: "minutes"`).
 * Without this, the echo check below would report a correct translation as a
 * missing one.
 */
const SELF_NAMED_KEYS = new Set(["minutes"]);

function panelKeys(source: string): string[] {
  return [...new Set([...source.matchAll(/\bt\("([A-Za-z0-9_]+)"/g)].map((match) => match[1]))].sort();
}

function dictionaryKeys(dictionary: Record<string, Record<string, string>>): string[] {
  return Object.keys(dictionary.en).sort();
}

const sharedKeys = panelKeys(sharedPanelSource);

describe("shared panel translation keys", () => {
  it("still finds the keys the panels call", () => {
    // A floor, not an exact count: it fails loudly if the extractor stops
    // matching (a rewrite to `translate("...")` would take it to zero) rather
    // than passing vacuously.
    expect(sharedKeys.length, "keys called by the shared panels").toBeGreaterThan(30);
  });

  it("defines every key the shared panels call in both dictionaries", () => {
    // This is the assertion the merge exists to satisfy. Both entry points
    // render the same component and inject a different dictionary, so a key
    // defined in only one of them is a string that renders wrong in the other.
    const dictionaries = [
      { name: "consoleI18n", keys: dictionaryKeys(consoleI18n) },
      { name: "workbenchI18n", keys: dictionaryKeys(workbenchI18n) }
    ];

    for (const { name, keys } of dictionaries) {
      const missing = sharedKeys.filter((key) => !keys.includes(key));
      expect(
        missing,
        `${name} has no entry for these keys, so a shared panel would render the raw ` +
          "key name there. Add them to both locales."
      ).toEqual([]);
    }
  });

  it("never renders a panel label as a raw key name", () => {
    const echoed = sharedKeys
      .filter((key) => !SELF_NAMED_KEYS.has(key))
      .filter((key) => makeTranslator("en", consoleI18n)(key) === key)
      .sort();

    expect(echoed, "keys the console translator renders as their own name").toEqual([]);
  });

  it("keeps both locales aligned for the panel keys", () => {
    // `i18n.test.ts` already checks whole-dictionary parity; this narrows it to
    // the panel keys so a failure here points straight at the panels.
    for (const [name, dictionary] of Object.entries({ consoleI18n, workbenchI18n })) {
      const en = dictionary.en as Record<string, string>;
      const zh = dictionary["zh-CN"] as Record<string, string>;
      const missingZh = sharedKeys.filter((key) => key in en && !(key in zh));
      expect(missingZh, `${name}: panel keys present in en but not zh-CN`).toEqual([]);
    }
  });
});

describe("single implementation", () => {
  const SHARED_PANELS = [
    "OverviewPanel",
    "PipelinePanel",
    "TasksPanel",
    "BuildPanel",
    "VisualsPanel",
    "QaPanel"
  ];

  it("exports each shared panel from the shared module", () => {
    const missing = SHARED_PANELS.filter(
      (name) => !new RegExp(`export function ${name}\\b`).test(sharedPanelSource)
    );
    expect(missing, "shared panels not defined in shared/panels/PlanPanels.tsx").toEqual([]);
  });

  it("does not also define them in either entry point", () => {
    // Both entry points re-export the shared panels so their own imports stay
    // put; re-exporting is fine, a second `export function` is the regression.
    const duplicated: string[] = [];
    const entries: Array<readonly [string, string]> = [
      ["console/rendering.tsx", consoleSource],
      ["workbench/PlanPanels.tsx", workbenchSource]
    ];
    for (const [name, source] of entries) {
      for (const panel of SHARED_PANELS) {
        if (new RegExp(`export function ${panel}\\b`).test(source)) {
          duplicated.push(`${panel} in ${name}`);
        }
      }
    }
    expect(duplicated, "shared panels implemented a second time").toEqual([]);
  });
});
