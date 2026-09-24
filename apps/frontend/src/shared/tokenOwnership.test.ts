import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Guard for "a custom property is defined in more than one place".
 *
 * Until F2 landed, `console.css`, `workbench.css` and `studio.css` each carried a
 * full `:root` block. All three are reachable from `main.tsx`, so all three
 * applied at once on every route, and for a token defined twice the winner was
 * whichever sheet the bundler emitted last. Measured on the built CSS,
 * `studio.css` won -- so the values users saw came from bundle order, not from a
 * decision anyone made. Four tokens had already drifted apart (`--chrome` in
 * both themes, plus `--code-bg`, `--surface-muted` and `--muted-strong` in dark).
 *
 * Nothing caught it. Every sheet is valid CSS, every route looks fine, and the
 * divergence is invisible until someone compares two files -- which is exactly
 * why it survived: consistency here was a coincidence, not a mechanism.
 *
 * The stylesheets are read from disk, not via `?raw`. In this Vitest version
 * `?raw` on a `.css` module resolves to an empty string without throwing, so
 * every comparison below would pass vacuously. The floor assertion exists to
 * catch that if someone switches it back.
 */
const SRC_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const STYLES_DIR = resolve(SRC_DIR, "styles");

const TOKENS_FILE = "tokens.css";
const TOKEN_DEFINITION = /(^|[\s;{])(--[a-z0-9-]+)\s*:/g;

function sheetNames(): string[] {
  return readdirSync(STYLES_DIR)
    .filter((name) => name.endsWith(".css"))
    .sort();
}

function readStylesheet(name: string): string {
  return readFileSync(resolve(STYLES_DIR, name), "utf8");
}

/** Custom properties a stylesheet defines, with comments stripped first. */
function definedTokens(css: string): string[] {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  return [...withoutComments.matchAll(TOKEN_DEFINITION)].map((match) => match[2]);
}

/**
 * Custom properties defined at *document-root* scope.
 *
 * The defect F2 fixed was global duplication: three `:root` blocks, all live at
 * once, the winner decided by bundle order. A custom property under a component
 * selector is a different thing entirely -- `--sidebar-width` is set per instance
 * by `StudioShell` and overridden by `.studio-shell.sidebar-collapsed`, so it is
 * local state and legitimately belongs in the component's own sheet. Only root
 * scope is checked, so this guard does not forbid that pattern.
 */
function rootScopedTokens(css: string): string[] {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const found: string[] = [];
  for (const declaration of withoutComments.matchAll(TOKEN_DEFINITION)) {
    // Walk back to the block this declaration sits in, then to its selector.
    const before = withoutComments.slice(0, declaration.index);
    const openBrace = before.lastIndexOf("{");
    if (openBrace === -1) continue;
    const selector = before.slice(before.lastIndexOf("}", openBrace - 1) + 1, openBrace);
    if (/:root|^(?:html|:where\(html\))\b|\[data-theme/.test(selector.trim())) {
      found.push(declaration[2]);
    }
  }
  return found;
}

/**
 * Every non-test source file, as text, so "who imports tokens.css" can be
 * answered for the whole app rather than for the one file we thought of.
 */
const sources = import.meta.glob(["../**/*.{ts,tsx}", "!../**/*.test.{ts,tsx}"], {
  query: "?raw",
  import: "default",
  eager: true
}) as Record<string, string>;

const tokensStylesheet = readStylesheet(TOKENS_FILE);

/** Splits a stylesheet into its `:root` (light) and `:root[data-theme="dark"]` blocks. */
function blockFor(css: string, dark: boolean): string {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const selector = dark ? /:root\[data-theme="dark"\]\s*\{([\s\S]*?)\}/ : /(?<!\[data-theme):root\s*\{([\s\S]*?)\}/;
  return selector.exec(withoutComments)?.[1] ?? "";
}

describe("design token ownership", () => {
  it("still reads the token block from disk", () => {
    // Floor, not exact count: fails loudly if the disk read or the regex stops
    // working, instead of letting every assertion below pass on an empty string.
    expect(definedTokens(tokensStylesheet).length, "custom properties in tokens.css").toBeGreaterThan(
      20
    );
    expect(sheetNames().length, "stylesheets found on disk").toBeGreaterThan(2);
  });

  it("defines every root-scoped custom property in tokens.css and nowhere else", () => {
    // The rule F2 exists to establish: one definition, one file. A second root
    // definition is not "harmless duplication" -- with three globally applied
    // sheets the value that wins is decided by bundle order, and nothing reports
    // that. Four tokens had already drifted before this guard existed.
    const offenders = sheetNames()
      .filter((name) => name !== TOKENS_FILE)
      .map((name) => ({ name, tokens: rootScopedTokens(readStylesheet(name)) }))
      .filter((entry) => entry.tokens.length > 0);
    expect(
      offenders,
      "these stylesheets define a root-scoped custom property again; with more " +
        "than one global sheet the applied value follows bundle order, not intent"
    ).toEqual([]);
    // The other half: a guard that scans for root scope would pass vacuously if
    // it stopped recognising `:root` at all.
    expect(
      rootScopedTokens(tokensStylesheet).length,
      "root-scoped tokens found in tokens.css"
    ).toBeGreaterThan(20);
  });

  it("imports tokens.css once, from the app root", () => {
    // The other half. The check above would still pass if tokens.css were never
    // imported at all -- every sheet would just render with no custom properties
    // resolved, and no comparison of two files can see a missing import.
    const importers = Object.entries(sources)
      .filter(([, text]) => text.includes("styles/tokens.css"))
      .map(([path]) => path.replace(/^\.\.\//, ""));
    expect(importers, "exactly one module may import tokens.css").toHaveLength(1);
    expect(importers[0], "the importer must be the app root, which every route loads").toBe(
      "main.tsx"
    );
    const uiImporters = Object.entries(sources)
      .filter(([, source]) => source.includes("styles/ui.css"))
      .map(([path]) => path.replace(/^\.\.\//, ""));
    expect(uiImporters).toEqual(["main.tsx"]);
  });

  it("does not leave a token with a dark value and no light value", () => {
    // Anything that appears in the dark block and not the light block is a token
    // that renders with a stale value when the theme is switched back.
    const light = new Set(definedTokens(blockFor(tokensStylesheet, false)));
    const dark = new Set(definedTokens(blockFor(tokensStylesheet, true)));
    expect(dark.size, "tokens in the dark block").toBeGreaterThan(20);
    const darkOnly = [...dark].filter((token) => !light.has(token));
    expect(darkOnly, "these tokens have a dark value but no light value").toEqual([]);
  });
});
