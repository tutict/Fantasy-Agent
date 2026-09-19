import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Source text via `?raw` for the panels, for the same reason
// `panelI18n.test.ts` uses it: a runtime extractor reads the transformed module
// and under-reports silently.
import consoleSource from "../console/rendering.tsx?raw";
import blenderScriptSource from "./panels/BlenderScriptPanel.tsx?raw";
import sharedPrimitivesSource from "./panels/primitives.tsx?raw";
import sharedPanelSource from "./panels/PlanPanels.tsx?raw";

/**
 * Guard for "the panel emits a class name that nothing styles".
 *
 * This is the failure mode the F1 merge walked straight into. Every panel
 * emits `wb-*` names, those rules live in `workbench.css`, and `workbench.css`
 * is imported by `PlanningWorkbench` — which only mounts on `/workbench`. On
 * `/web-console` the console rendered the same panels with `console.css` as its
 * only sheet, so the panels came out unstyled.
 *
 * Nothing caught it. Typecheck cannot see a class name, no test mounts the
 * console's real CSS, and the panels still rendered the right text — they just
 * rendered it as bare HTML. The bundle even contained the `wb-*` rules, because
 * Vite merges every stylesheet into one file; it only injects a module's CSS
 * when that module is in the route's graph, which is a runtime detail no static
 * check was looking at.
 *
 * So this file checks the two halves against each other: every class name the
 * shared panels emit must be styled by a sheet the console route loads, and no
 * panel may carry a class name from the retired console-only namespace.
 *
 * The stylesheets are read from disk, not via `?raw`. In this Vitest version
 * `?raw` on a `.css` module resolves to an empty string — it does not throw,
 * which would have made every assertion below pass vacuously. If you switch
 * this back to `?raw`, `still finds` will catch the empty read for the panels
 * but nothing will catch it for the CSS, so keep the disk read.
 */
const STYLES_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../styles");

function readStylesheet(name: string): string {
  return readFileSync(resolve(STYLES_DIR, name), "utf8");
}

/** Class names emitted by a JSX/TSX source, from both literals and templates. */
function emittedClasses(source: string): string[] {
  const found = new Set<string>();

  // className="a b" and className={`a ${x} b`} — take the static parts.
  for (const match of source.matchAll(/className=(?:"([^"]*)"|\{`([^`]*)`\})/g)) {
    const raw = match[1] ?? match[2] ?? "";
    for (const token of raw.replace(/\$\{[^}]*\}/g, " ").split(/\s+/)) {
      if (token) found.add(token);
    }
  }

  // `wb-button${running ? " active" : ""}` — names built by concatenation.
  for (const match of source.matchAll(/`([a-z][a-z0-9-]*)\$\{/g)) {
    found.add(match[1]);
  }

  return [...found].sort();
}

/** Selector names a stylesheet defines, ignoring comments and property values. */
function styledClasses(css: string): Set<string> {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const names = new Set<string>();
  for (const match of withoutComments.matchAll(/\.(-?[A-Za-z_][A-Za-z0-9_-]*)/g)) {
    names.add(match[1]);
  }
  return names;
}

const sharedClasses = [
  ...new Set([
    ...emittedClasses(sharedPanelSource),
    ...emittedClasses(sharedPrimitivesSource),
    ...emittedClasses(blenderScriptSource)
  ])
].sort();
const workbenchStyles = styledClasses(readStylesheet("workbench.css"));
const consoleStyles = styledClasses(readStylesheet("console.css"));

/**
 * The console-only namespace the merge retired. These were legitimately shared
 * once — both sides rendered the same names and one stylesheet styled both —
 * but the shared panels now emit `wb-*`, so a reappearance here means a panel
 * went back to depending on whichever sheet happened to be loaded.
 */
const RETIRED_CONSOLE_CLASSES = [
  "summary-block",
  "stage-row",
  "task-row",
  "task-board",
  "pipeline-board",
  "overview-grid",
  "stage-pill",
  "stage-meta",
  "task-meta"
];

describe("shared panel styles", () => {
  it("still finds the class names the panels emit", () => {
    // Floor, not exact count: fails loudly if the extractor stops matching
    // (say the panels move to `class=`), instead of passing vacuously.
    expect(sharedClasses.length, "class names emitted by the shared panels").toBeGreaterThan(5);
  });

  it("still finds selectors in both stylesheets", () => {
    // The other half of the same protection. This is the assertion that would
    // have caught `?raw` returning "" — a stylesheet that reads as empty makes
    // every comparison below trivially true.
    expect(workbenchStyles.size, "selectors in workbench.css").toBeGreaterThan(20);
    expect(consoleStyles.size, "selectors in console.css").toBeGreaterThan(50);
  });

  it("styles every class the shared panels emit, in the sheet the console loads", () => {
    // `console/rendering.tsx` imports `workbench.css` alongside the panels it
    // re-exports; that import is what makes this pass. If someone drops it,
    // the console silently loses every panel style again.
    const unstyled = sharedClasses.filter((name) => !workbenchStyles.has(name));
    expect(
      unstyled,
      "the shared panels emit these classes, but workbench.css -- the sheet " +
        "console/rendering.tsx imports for them -- does not define them"
    ).toEqual([]);
  });

  it("keeps console/rendering.tsx importing the sheet the panels are styled by", () => {
    // The assertion above would still pass if this import were deleted, since
    // it only compares the panels to the sheet's contents. This is the half
    // that says the console route actually gets the sheet.
    expect(
      /import\s+"\.\.\/styles\/workbench\.css"/.test(consoleSource),
      "console/rendering.tsx must import ../styles/workbench.css for the " +
        "shared panels it re-exports, or /web-console renders them unstyled"
    ).toBe(true);
  });

  it("does not send the shared panels back to the retired console-only names", () => {
    const revived = RETIRED_CONSOLE_CLASSES.filter((name) => sharedClasses.includes(name));
    expect(
      revived,
      "the shared panels emit a class from the console-only namespace again; " +
        "it is styled per-entry-point, so one of the two routes will lose it"
    ).toEqual([]);
  });

  it("leaves the console's own surface in console.css", () => {
    // Complement of the check above: if a shared panel's classes had leaked
    // into console.css, the previous test would pass while the two sheets were
    // quietly duplicating each other. These belong to the console alone.
    //
    // `stage-strip` was on this list until F3 removed the console's stage track
    // -- it rendered the pipeline's stage rows, which the orchestration board
    // does now. Its selectors went with it.
    const consoleOwned = ["insight-row", "split-output", "review-item", "review-inspector"];
    const missing = consoleOwned.filter((name) => !consoleStyles.has(name));
    expect(missing, "console.css stopped styling the console's own surface").toEqual([]);
  });
});
