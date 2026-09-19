import { describe, expect, it } from "vitest";

import { consoleI18n, makeTranslator, studioI18n, workbenchI18n } from "./i18n";
// Vite inlines these at transform time. Reading the source text beats calling
// `toString()` on a transformed component: esbuild rewrites the JSX and does not
// reliably preserve the `t("...")` calls, so a runtime extractor under-reports
// silently -- and a guard that under-reports is worse than none.
import consoleSource from "../console/rendering.tsx?raw";
import flowConsoleSource from "../console/FlowConsole.tsx?raw";
import studioSource from "../studio/StudioShell.tsx?raw";
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

/**
 * Keys with no caller that predate the entry-point guard.
 *
 * These came from earlier merges (the manual-correction flow was rewritten and
 * its `manual*` strings were left behind). They are *not* sanctioned -- they are
 * recorded so the guard can be strict about new orphans without failing on old
 * ones. Removing them is a separate change; adding to this list is not the way
 * to silence a failure, deleting the key is.
 */
const KNOWN_DEAD = new Set([
  "toggleLog",
  "loop",
  "maps",
  "classes",
  "folders",
  "automation",
  "jobs",
  "manualChecking",
  "manualComfyReady",
  "manualBlenderReady",
  "manualUnrealReady",
  "manualGodotReady",
  "manualOpenNeedsConfirmation",
  "manualOpenUnknownTarget",
  "manualOpenUnavailable",
  "winState",
  "failureStates"
]);

/**
 * `workbenchI18n` keys that a `t(...)` call cannot name.
 *
 * Two groups, and the distinction matters because it decides what to do when the
 * guard fails:
 *
 *   - **Composed at the call site.** `ToolActions` renders `t(labelKey)` from the
 *     `PLAN_TOOLS` table, so `toolExtractSeed` is reached through a variable.
 *   - **Resolved at runtime by the backend.** Nothing in the frontend ever said
 *     `apiTestConnected`; `fantasy_agent/api_settings.py` sends it as
 *     `detail_key` and `ApiSettingsPanel` calls `t(payload.detail_key)`. If the
 *     backend renamed one of these while the dictionary kept the old spelling,
 *     the panel would print the raw key and no test would notice -- which is
 *     exactly the failure mode this file exists to catch, so the list is spelled
 *     out rather than derived from the same files it is meant to check.
 *
 * A key in neither group is dead: delete it, do not add it here.
 */
const RUNTIME_NAMED_KEYS = new Set([
  // Composed: `toolExtractSeed` is not in PLAN_TOOLS (that table drives the ten
  // plan-refinement buttons); the extract action lives in SeedInspector and
  // labels itself `extractSeed`. Kept so a future table entry resolves.
  "toolExtractSeed",
  // Composed: PLAN_TOOLS label keys, looked up by `t(labelKey)`.
  "toolGeneratePlan",
  "toolDecomposeTasks",
  "toolPreparePipeline",
  "toolRenderGdd",
  "toolGodotPlan",
  "toolUnrealPlan",
  "toolBlenderPlan",
  "toolComfyuiPlan",
  "toolCreativeReview",
  "toolQaPlan",
  // Backend-named: `detail_key` values from `api_settings.test_connection`.
  "apiTestConnected",
  "apiTestMissingKey",
  "apiTestHttpError",
  "apiTestUnreachable",
  "apiTestBadResponse",
  "apiTestInvalid"
]);

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
  // `PipelinePanel` used to be on this list. It is gone rather than shared:
  // stage rows belong to the orchestration board, which renders the runtime
  // status a plan-time row cannot. `orchestrationOwnership.test.ts` is what
  // keeps them from coming back.
  const SHARED_PANELS = ["OverviewPanel", "TasksPanel", "BuildPanel", "VisualsPanel", "QaPanel"];

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

describe("entry-point dictionaries have no keys nothing calls", () => {
  /**
   * A key is live if any *non-test* source in the frontend calls it, directly
   * (`t("key")`) or indirectly (a bare `"key"` string, which is how `tabGroups`
   * stores its labels before `{t(label)}` resolves them).
   *
   * Three scoping decisions, each load-bearing:
   *
   *   - **Include `shared/panels/PlanPanels.tsx`.** The console still renders
   *     some of those panels, so their keys must stay. Excluding it made the
   *     check report `systems` / `tools` / `risks` as dead.
   *   - **Exclude test files.** A test may name a key purely to assert on it --
   *     the `removed` list below does exactly that -- and counting those would
   *     make every key look used.
   *   - **Exclude `i18n.ts` itself.** It is where the keys are defined.
   *
   * With that scope the distinction is real: `tabOverview` appears nowhere but
   * this file's own list, while `systems` is called at
   * `shared/panels/PlanPanels.tsx:86`.
   */
  const modules = import.meta.glob(["../**/*.{ts,tsx}", "!../**/*.test.{ts,tsx}"], {
    query: "?raw",
    import: "default",
    eager: true
  }) as Record<string, string>;

  const mentioned = new Set(
    Object.values(modules).flatMap((source) => [
      ...panelKeys(source),
      ...[...source.matchAll(/"([A-Za-z0-9_]+)"/g)].map((match) => match[1])
    ])
  );

  /**
   * Keys with no caller that predate this guard.
   *
   * These came from earlier merges (the manual-correction flow was rewritten and
   * its `manual*` strings were left behind). They are *not* sanctioned -- they
   * are recorded so this guard can be strict about new orphans without failing
   * on old ones. Removing them is a separate change; adding to this list is not
   * the way to silence a failure, deleting the key is.
   */
  const KNOWN_DEAD = new Set([
    "toggleLog",
    "loop",
    "maps",
    "classes",
    "folders",
    "automation",
    "jobs",
    "manualChecking",
    "manualComfyReady",
    "manualBlenderReady",
    "manualUnrealReady",
    "manualGodotReady",
    "manualOpenNeedsConfirmation",
    "manualOpenUnknownTarget",
    "manualOpenUnavailable",
    "winState",
    "failureStates"
  ]);

  /**
   * Keys the *backend* names at runtime instead of the frontend.
   *
   * `StudioShell` renders these as `t(payload.detail_key)`, so the call is
   * `t(someVariable)`, not `t("literal")`, and a source scan cannot see them.
   * Every entry here is a `detail_key=` string emitted from
   * `fantasy_agent/api_settings.py` or `apps/studio/app/main.py`; if one were
   * renamed backend-side while the dictionary kept the old spelling, the panel
   * would print the raw key with no test failing. That is why the list is
   * spelled out rather than derived -- deriving it from the same file it guards
   * would make the guard agree with whatever is there.
   */
  const BACKEND_NAMED_KEYS = new Set([
    "apiTestConnected",
    "apiTestMissingKey",
    "apiTestHttpError",
    "apiTestUnreachable",
    "apiTestBadResponse",
    "apiTestInvalid"
  ]);

  /**
   * The two `studioI18n` halves the MCP card renders.
   *
   * `McpCard` builds these by concatenation -- `"mcpDetail" + key + state` -- so
   * no `t("...")` call names them and a literal scan cannot see them.
   */
  const STUDIO_COMPOSED = new Set(
    [
      "mcpDetail",
      "mcpNext",
      ...[
        "mcpDetailComfyReady",
        "mcpDetailComfyMissing",
        "mcpDetailExecutableReady",
        "mcpDetailExecutableMissing",
        "mcpDetailGithubReady",
        "mcpDetailGithubOptional",
        "mcpNextComfyReady",
        "mcpNextComfyMissing",
        "mcpNextBlenderReady",
        "mcpNextBlenderMissing",
        "mcpNextUnrealReady",
        "mcpNextUnrealMissing",
        "mcpNextGodotReady",
        "mcpNextGodotMissing",
        "mcpNextGithubReady",
        "mcpNextGithubOptional"
      ]
    ].flatMap((entry) => [entry, entry + "Ready", entry + "Missing", entry + "Optional"])
  );

  it("still finds the keys the console calls", () => {
    // Same floor rationale as above: a rewrite that stops the extractor from
    // matching must fail loudly instead of passing on an empty set.
    expect(panelKeys(flowConsoleSource).length, "direct t() calls in FlowConsole.tsx").toBeGreaterThan(
      20
    );
  });

  it("still finds the keys the studio shell calls", () => {
    expect(panelKeys(studioSource).length, "direct t() calls in StudioShell.tsx").toBeGreaterThan(40);
  });

  it("has no orphaned console keys", () => {
    const orphans = dictionaryKeys(consoleI18n)
      .filter((key) => !mentioned.has(key))
      .filter((key) => !KNOWN_DEAD.has(key));
    expect(
      orphans,
      "consoleI18n keys nothing calls. Delete the key rather than adding it to " +
        "KNOWN_DEAD; a key with no caller is a string no screen can ever show."
    ).toEqual([]);
  });

  it("has no orphaned workbench keys", () => {
    const orphans = dictionaryKeys(workbenchI18n)
      .filter((key) => !mentioned.has(key))
      .filter((key) => !RUNTIME_NAMED_KEYS.has(key));
    expect(
      orphans,
      "workbenchI18n keys nothing calls. The workbench's static page is gone, so " +
        "strings only it used must go with it. Delete the key."
    ).toEqual([]);
  });

  it("has no orphaned studio keys either", () => {
    const orphans = dictionaryKeys(studioI18n)
      .filter((key) => !mentioned.has(key))
      .filter((key) => !STUDIO_COMPOSED.has(key))
      .filter((key) => !RUNTIME_NAMED_KEYS.has(key));
    expect(
      orphans,
      "studioI18n keys nothing calls. The shell renders with this dictionary, so an " +
        "orphan means a label was dropped from the panel while its string stayed behind."
    ).toEqual([]);
  });

  it("no longer carries the keys for the removed duplicate tabs", () => {
    // The specific regression this change was about. Named individually so a
    // failure says which tab came back rather than just "an orphan exists".
    const removed = [
      "tabOverview",
      "tabPipeline",
      "tabTasks",
      "tabBuild",
      "tabVisuals",
      "tabQa",
      "tabGdd",
      "tabDsl",
      "tabGroupPlan",
      "tabGroupDelivery",
      "tabGroupDocs",
      "emptyHeading",
      "emptyBody"
    ];
    const keys = dictionaryKeys(consoleI18n);
    const returned = removed.filter((key) => keys.includes(key));
    expect(returned, "keys for the deleted console tabs are back in consoleI18n").toEqual([]);
  });
});
