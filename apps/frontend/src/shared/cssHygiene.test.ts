import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * Style-sheet hygiene: the rules a stylesheet has to follow even when nobody is
 * looking at the rendered page.
 *
 * These four checks exist because the same four things went wrong, and none of
 * them was caught by anything:
 *
 *  1. **Hardcoded colors in CSS.** `visualSystem.test.ts` checked `.tsx` and one
 *     file (`ui.css`), which left `console.css` / `studio.css` /
 *     `workbench.css` / `orchestration.css` completely unguarded. The result
 *     was five `var(--accent, #6ea8fe)`-style fallbacks in `studio.css`: the
 *     variables *are* defined, so the hex never renders, but a reader cannot
 *     tell that from a real color and concludes the focus ring is that blue.
 *     Dead code that reads as live code is worse than no code.
 *  2. **Values off the scale.** `gap: 10px` 24 times, `font-size: 12px` 40
 *     times and `13px` 36 times -- 12 and 13 are visually indistinguishable yet
 *     both in use, which renders the same screen at two qualities. The scales
 *     are read from `tokens.css` rather than written here, so adding a step to
 *     the token file widens the guard without touching the test.
 *  3. **Tokens nobody reads.** 17 of 86 tokens had zero `var(--x)` references.
 *     A token that nothing uses is a claim nobody kept; a growing pile of them
 *     is how "we have a design system" stops meaning anything. `--size-sidebar`
 *     is the clearest case: it says 292px, the components hardcode 282px and
 *     82px, and nothing noticed for months.
 *  4. **Breakpoints drifting apart.** Six of them, with 900 and 860 applying to
 *     unrelated panels 40px apart. They cannot be tokens -- `@media` does not
 *     accept `var()` -- so they are a documented convention with a check.
 *
 * Every exemption is an explicit, named list. An unnamed skip is a silent hole
 * with a comment on top.
 */

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const stylesDir = resolve(root, "styles");
const tokensSource = readFileSync(resolve(stylesDir, "tokens.css"), "utf8");

/** Every stylesheet except the token file, which is the one allowed to hold values. */
function styleSheets(): { name: string; source: string }[] {
  return readdirSync(stylesDir)
    .filter((name) => name.endsWith(".css") && name !== "tokens.css")
    .map((name) => ({ name: `styles/${name}`, source: readFileSync(resolve(stylesDir, name), "utf8") }));
}

/** `var(--x)` references, with the fallback argument left out of the name. */
function referencedTokens(source: string): Set<string> {
  return new Set([...source.matchAll(/var\(\s*(--[a-z0-9-]+)/g)].map((match) => match[1]));
}

/** Token names declared in a `:root`-scoped block. */
function declaredTokens(block: string): string[] {
  return [...block.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((match) => match[1]);
}

function isExemptValue(line: string): boolean {
  return NOT_SPACING.some((pattern) => pattern.test(line));
}

const [lightBlock] = tokensSource.split(':root[data-theme="dark"]');

/**
 * Tokens a guard is allowed to skip, with the reason it has one. A new entry
 * here should be a decision, not a workaround.
 */
const VALUE_EXEMPT = new Set<string>([
  // `?raw` and the file itself are the token source, not a consumer.
  "--mono",
  // Not a style value: consumed by a GDScript template or a test fixture.
  "--font-mono",
  "--font-ui"
]);

/** Tokens that may be declared without a `var()` reference yet. */
const UNREFERENCED_EXEMPT = new Set<string>([
  // Referenced through the C#-side / GDScript generator rather than CSS.
  "--mono",
  "--font-ui",
  "--font-mono",
  // Chart series and status soft backgrounds: the palette exists ahead of the
  // views that use it, and `visualSystem.test.ts` asserts their contrast --
  // which is the only thing that would notice if they drifted. Deleting them
  // for being unreferenced would remove the only record of their intent.
  "--data-1", "--data-2", "--data-3", "--data-4", "--data-5", "--data-6",
  "--status-success-soft", "--status-waiting-soft", "--status-human-soft", "--status-info-soft",
  "--status-human", "--status-info",
  "--focus",
  // Motion and stacking steps reserved for the transitions and overlays that
  // are being built. Removing a token because its moment has not arrived
  // invites re-adding it by hand, with a different value.
  "--duration-slow", "--layer-sticky", "--layer-overlay", "--shadow-s",
  // Upper spacing bounds: 32px and 48px are the two steps that let a layout
  // breathe without inventing a new step. The ladder is documented as
  // continuous, and a ladder with a hole in it is not a ladder.
  "--space-6", "--space-7"
]);

/** The four breakpoints, mirrored in `docs/ui/css-conventions.md`. */
const BREAKPOINTS = [1360, 1100, 900, 560];

/**
 * Three values that are deliberately not on the spacing ladder, each with the
 * reason it is not spacing.
 *
 * They are listed here rather than papered over with a looser pattern, because
 * the guard is only worth having if every hole in it is a decision on record.
 */
const NOT_SPACING = [
  // `padding: 1px` on a scroll container: makes room for the focus ring so the
  // ring draws inside the box instead of clipping at the scroll edge.
  /padding:\s*1px\s*;/,
  // `gap: 1px` between activity-log rows: that gap is a 1px rule, not breathing
  // room. A token would invite someone to "fix" it to 4px and lose the divider.
  /gap:\s*1px\s*;/,
  // Negative margin pulling a heading back under its section rule. There is no
  // negative step on the ladder, and inventing one would be worse.
  /margin:\s*-\d/
];

describe("stylesheet hygiene", () => {
  it("keeps colors in tokens; a fallback in var() is not an exemption", () => {
    const offenders: string[] = [];
    for (const sheet of styleSheets()) {
      // `var(--x, #abc)` is matched deliberately: the fallback branch renders
      // only when --x is undefined, so writing one at all means the author
      // either expected the token to be missing or copied a color from another
      // theme. Both are worth a look, and the fix is the same -- use the token.
      const lines = sheet.source.split("\n");
      lines.forEach((line, index) => {
        // `white-space` is a property name, not a color -- matching bare `white`
        // flagged 11 lines that never render a color.
        if (/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|\bwhite\s*[:;,)]/.test(line)) {
          const where = `${sheet.name}:${index + 1}`;
          offenders.push(`${where}  ${line.trim()}`);
        }
      });
    }
    expect(offenders).toEqual([]);
  });

  it("keeps font sizes, spacing and radii on the token scale", () => {
    const offenders: string[] = [];
    for (const sheet of styleSheets()) {
      sheet.source.split("\n").forEach((line, index) => {
        if (isExemptValue(line)) return;
        const where = `${sheet.name}:${index + 1}`;
        // Token references and keywords are fine. What is left -- a bare px or
        // em value -- is a value that exists nowhere else in the system.
        const bare = [...line.matchAll(/(?:^|[\s;])(font-size|gap|row-gap|column-gap|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|border-radius):\s*(-?[\d.]+(?:px|em))/g)];
        for (const match of bare) {
          offenders.push(`${where}  ${match[1]}: ${match[2]}`);
        }
      });
    }
    expect(offenders).toEqual([]);
  });

  it("styles the base class a component hangs its modifiers on", () => {
    // Renaming `.mcp-status-card` to `.stage-card` in console.css was silent:
    // nothing compared the class a component emits against the sheet that is
    // supposed to style it, so renaming one side and forgetting the other
    // rendered an unstyled card and every test stayed green. This is the check
    // that would have caught it.
    //
    // **The first class only.** `className="rail-card handoff-panel"` styles
    // from `.rail-card`; `handoff-panel` is a modifier that may legitimately
    // have no rules yet (it marks a panel planned to diverge). A modifier may
    // be aspirational; a base may not.
    //
    // Scoped to the components whose markup is static enough to read and whose
    // styles live in one sheet each. Not swept across every class in the
    // sheet: most of `console.css` is emitted by `rendering.tsx` and by the
    // inline components further down `FlowConsole.tsx`, so a whole-sheet sweep
    // reported 66 phantom "styled but never rendered" classes and would have
    // been turned off within a week.
    //
    // The list is every console component with static `className` literals, not
    // the two it started as. Leaving the extracted cards out was not a scoping
    // decision, it was an oversight: FE6-1 renames a class in
    // `ExecutionStageCard.tsx` and this check did not cover it, so the case
    // passed on the strength of a *different* guard in this same file. Adding a
    // component here is what makes its own mutation bite this guard.
    const pairs: [component: string, sheet: string][] = [
      ["console/FlowConsole.tsx", "console.css"],
      ["console/FlowConsole.parts.tsx", "console.css"],
      ["console/executionStage/ExecutionStageCard.tsx", "console.css"],
      ["console/playtest/PlaytestReportCard.tsx", "console.css"],
      ["console/playtest/PlaytestConfirmBlock.tsx", "console.css"],
      ["console/correction/CorrectionReportCard.tsx", "console.css"],
      ["studio/StudioShell.tsx", "studio.css"]
    ];
    const problems: string[] = [];
    for (const [component, sheetName] of pairs) {
      const source = readFileSync(resolve(root, component), "utf8");
      const sheet = readFileSync(resolve(stylesDir, sheetName), "utf8");
      const bases = new Set(
        [...source.matchAll(/className="([^"{}]+)"/g)].map((match) => match[1].trim().split(/\s+/)[0])
      );
      for (const name of bases) {
        if (!name || name.includes("$")) continue;
        if (!new RegExp(`\\.${name}(?![a-zA-Z0-9_-])`).test(sheet)) {
          problems.push(`${component} renders class "${name}" but ${sheetName} does not define it`);
        }
      }
    }
    expect(problems).toEqual([]);
  });

  it("does not leave a stage-card rule behind after the card is renamed", () => {
    // The other half of the same accident, for the one class whose ownership
    // is unambiguous. FE6-1 renames the emitter and FE6-2 renames the rule; a
    // half-done rename leaves one of them pointing at a name nothing uses, and
    // the forward check above cannot see it because it only looks at classes
    // the component still emits.
    //
    // A whole-sheet reverse sweep was tried and abandoned: 66 of `console.css`'s
    // classes are emitted from `rendering.tsx` or from the inline components
    // below the main function, so "no emitter in this one file" is usually a
    // statement about where the markup lives, not about dead CSS.
    //
    // The emitters are followed across files: the card was split out of
    // `FlowConsole.tsx` after this check was written, and it correctly failed
    // then. What it asserts is that the two sides agree, not which file each
    // happens to be in -- so a move is not a rename.
    const sheet = readFileSync(resolve(stylesDir, "console.css"), "utf8");
    const sources = ["console/FlowConsole.tsx", "console/executionStage/ExecutionStageCard.tsx"].map((file) =>
      readFileSync(resolve(root, file), "utf8")
    );
    const problems: string[] = [];
    for (const name of ["stage-card", "stage-top"]) {
      const styled = new RegExp(`\\.${name}(?![a-zA-Z0-9_-])`).test(sheet);
      const rendered = sources.some((source) => source.includes(`"${name}"`));
      if (styled !== rendered) {
        problems.push(
          rendered
            ? `.${name} is rendered but console.css does not style it`
            : `console.css styles .${name} but nothing renders it`
        );
      }
    }
    expect(problems).toEqual([]);
  });

  it("does not accumulate tokens nothing reads", () => {
    const used = new Set<string>();
    for (const sheet of styleSheets()) {
      for (const token of referencedTokens(sheet.source)) used.add(token);
    }
    // `var(--x)` inside tokens.css itself (alias chains) counts as a read.
    for (const token of referencedTokens(tokensSource)) used.add(token);

    const orphans = declaredTokens(lightBlock).filter(
      (token) => !used.has(token) && !UNREFERENCED_EXEMPT.has(token)
    );
    expect(orphans).toEqual([]);
  });

  it("keeps breakpoints on the documented four-step grid", () => {
    const offenders: string[] = [];
    for (const sheet of styleSheets()) {
      for (const match of sheet.source.matchAll(/@media[^{]*?\((max|min)-width:\s*(\d+)px\)/g)) {
        const width = Number(match[2]);
        // `min-width: 901px` is the mirror of `max-width: 900px`: the pair is how
        // you express "not the narrow layout" without an overlap gap, and
        // studio.css uses it for exactly that. So the grid is closed on one
        // side by one pixel -- that is a convention, not a fifth breakpoint.
        const mirrored = match[1] === "min" && BREAKPOINTS.some((step) => step + 1 === width);
        if (!BREAKPOINTS.includes(width) && !mirrored) {
          offenders.push(`${sheet.name}  @media (${match[1]}-width: ${width}px)`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});
