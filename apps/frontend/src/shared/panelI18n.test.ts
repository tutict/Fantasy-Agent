import { describe, expect, it } from "vitest";

import { consoleI18n, makeTranslator, workbenchI18n } from "./i18n";
// Vite inlines these at transform time. Reading the source text beats calling
// `toString()` on a transformed component: esbuild rewrites the JSX and does not
// reliably preserve the `t("...")` calls, so a runtime extractor under-reports
// silently -- and a guard that under-reports is worse than none.
import consolePanelSource from "../console/rendering.tsx?raw";
import workbenchPanelSource from "../workbench/PlanPanels.tsx?raw";

/**
 * Guard for F1 (one panel implemented once).
 *
 * The six panels the console and the planning workbench share currently exist
 * twice, and each entry point injects its own translator:
 *
 *   - `console/rendering.tsx`    is rendered with `consoleI18n`
 *   - `workbench/PlanPanels.tsx` is rendered with `workbenchI18n`
 *
 * The two dictionaries overlap on 19 keys and diverge on the rest. That is
 * harmless while the panels are separate, and silently broken the moment they
 * become one component: `makeTranslator` falls back to `|| key`, so a console
 * operator would read the literal string "logline" or "stagesCount", no
 * exception is raised, and every existing test stays green.
 *
 * This file pins the current key surface of both halves so that:
 *
 *   1. A key a panel calls but a dictionary does not define fails here, naming
 *      the key, instead of shipping as untranslated text.
 *   2. Any *new* divergence between the two halves is caught while the panels
 *      are still separate -- the failure is cheap now and expensive later.
 *
 * The key lists are read from the source text rather than from the imported
 * modules -- see the `?raw` imports below for why.
 */

/**
 * The keys `workbenchI18n` defines and `consoleI18n` does not. Pinned as an
 * exact list on purpose: while the panels are two implementations this gap is
 * the measure of how far apart they are, and F1 is done when it is empty.
 */
const KNOWN_CONSOLE_GAP = [
  "assetNeeds",
  "comfyui",
  "confirmRequired",
  "coreAction",
  "coreVerbs",
  "designPillars",
  "failureStates",
  "gameplayLoop",
  "logline",
  "noPlan",
  "pacing",
  "playerFantasy",
  "projectGoal",
  "qaFocus",
  "stagesCount",
  "toolActions",
  "toolActionsHint",
  "unreal",
  "winState"
].sort();

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

const consoleKeys = panelKeys(consolePanelSource);
const workbenchKeys = panelKeys(workbenchPanelSource);

describe("shared panel translation keys", () => {
  it("keeps both halves calling a real set of keys", () => {
    // A floor, not an exact count: it fails loudly if the extractor stops
    // matching (a rewrite to `translate("...")` would take it to zero) rather
    // than passing vacuously.
    expect(consoleKeys.length, "keys called by the console panels").toBeGreaterThan(30);
    expect(workbenchKeys.length, "keys called by the workbench panels").toBeGreaterThan(20);
  });

  it("shares the orchestration keys that both entries have to agree on", () => {
    const shared = workbenchKeys.filter((key) => consoleKeys.includes(key));

    // These carry the gate semantics -- whether a tool may run here, what must
    // finish first, what quality bar the stage owes. Both entries must show
    // them, or the two consoles disagree about the same pipeline.
    for (const key of ["humanGate", "dependencies", "quality", "risks", "confirmation", "tools"]) {
      expect(shared, `shared key ${key}`).toContain(key);
    }
  });

  it("reports the console dictionary gap as exactly the known list", () => {
    const consoleDefined = dictionaryKeys(consoleI18n);
    const workbenchDefined = dictionaryKeys(workbenchI18n);

    const missingFromConsole = workbenchKeys
      .filter((key) => workbenchDefined.includes(key))
      .filter((key) => !consoleDefined.includes(key))
      .sort();

    expect(
      missingFromConsole,
      "workbench panel keys with no console translation. A new entry here means a panel " +
        "reached for a key only one entry point defines -- the silent breakage F1 exists to " +
        "avoid. Add the key to consoleI18n for both locales, or move it to a shared dictionary."
    ).toEqual(KNOWN_CONSOLE_GAP);
  });

  it("never renders a panel label as a raw key name", () => {
    const translate = makeTranslator("en", consoleI18n);

    const echoed = [...new Set([...consoleKeys, ...workbenchKeys])]
      .filter((key) => !SELF_NAMED_KEYS.has(key))
      .filter((key) => translate(key) === key)
      .sort();

    // Every echo is a real gap: the console translator has no entry for the
    // key, so the operator reads the key itself. After the lift this must be
    // empty, and a lifted panel calling a workbench-only key would otherwise
    // pass every other test in the suite.
    const expectedEchoes = KNOWN_CONSOLE_GAP.filter((key) =>
      [...consoleKeys, ...workbenchKeys].includes(key)
    ).sort();

    expect(echoed, "keys the console translator renders as their own name").toEqual(expectedEchoes);
  });

  it.todo(
    "assert the console dictionary gap is empty once shared/panels/ is the single implementation"
  );
});

/**
 * The third F1 acceptance item: after the lift, no shared panel may still be
 * exported from two files. This is deliberately a todo rather than a live
 * assertion -- it fails today by construction, and a red suite would make the
 * safety net it sits next to indistinguishable from a regression.
 *
 * The exact list of names that must disappear from one side is pinned in the
 * body so the lift has a target it can check itself against.
 */
describe("single implementation", () => {
  const SHARED_PANELS = [
    "OverviewPanel",
    "PipelinePanel",
    "TasksPanel",
    "BuildPanel",
    "VisualsPanel",
    "QaPanel"
  ];

  it.todo(
    `exports each shared panel (${SHARED_PANELS.join(", ")}) from exactly one module`
  );

  it("still finds both implementations, so the todo above is not stale", () => {
    // Records the starting state. When the lift lands, this test flips to
    // failing -- which is the signal to delete it and enable the todo above.
    const inConsole = SHARED_PANELS.filter((name) =>
      new RegExp(`export function ${name}\\b`).test(consolePanelSource)
    );
    const inWorkbench = SHARED_PANELS.filter((name) =>
      new RegExp(`export function ${name}\\b`).test(workbenchPanelSource)
    );

    expect(inConsole, "shared panels still duplicated in the console").toEqual(SHARED_PANELS);
    expect(inWorkbench, "shared panels still duplicated in the workbench").toEqual(SHARED_PANELS);
  });
});
