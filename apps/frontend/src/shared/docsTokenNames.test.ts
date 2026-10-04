import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The token names and values written in `docs/ui/*.md` have to exist.
 *
 * These documents are what the next person -- or the next agent -- reads before
 * touching a stylesheet, and they are the only place the design system's rules
 * are explained in prose. Nothing read them, so they drifted: `css-conventions.md`
 * listed five font sizes when `tokens.css` declares four, still named a
 * `--text-2xl` that was deleted a round earlier, and gave a paragraph of reasons
 * for "box-shadow rather than outline" for a focus ring that is now an outline.
 * The last one is the dangerous shape: a reader following that paragraph would
 * write back `var(--focus-ring)`, a variable that no longer exists, and the
 * focus ring would disappear silently. No test would have reported it.
 *
 * So the check is narrow on purpose. It does not try to read English or judge
 * whether a sentence is still true -- that is a reviewer's job and it does not
 * belong in a test. It checks the one thing a machine can check and a reader
 * cannot: every `--token` the documents name, and every `<number>px` value in
 * the scale table, is something `tokens.css` actually declares.
 */

// This file sits in `apps/frontend/src/shared/`, so:
//   `..`    -> src/
//   `../..` -> apps/frontend/   (where the stylesheets are)
//   `../../..` -> the repository root (where docs/ lives)
// The first attempt went up one level short and read `apps/docs/`, which does
// not exist -- a wrong `repoRoot` fails as ENOENT rather than as a clear
// assertion, so it is worth stating the arithmetic.
const here = dirname(fileURLToPath(import.meta.url));
const appRoot = resolve(here, "..", "..");
const repoRoot = resolve(appRoot, "..", "..");
const tokens = readFileSync(resolve(appRoot, "src/styles/tokens.css"), "utf8");
const [light, dark] = tokens.split(':root[data-theme="dark"]');

/** Every `--name` declared in a block, lowercased. */
function declared(block: string): Set<string> {
  return new Set(
    [...block.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((match) => match[1].toLowerCase())
  );
}

const DECLARED = new Set([...declared(light), ...declared(dark)]);

const DOCUMENTS = [
  "docs/ui/tokens.md",
  "docs/ui/css-conventions.md",
  "docs/ui/architecture.md",
  "docs/ui/web-console.md"
] as const;

function read(relative: string): string {
  return readFileSync(resolve(repoRoot, relative), "utf8");
}

describe("the token documentation", () => {
  it("names only tokens that tokens.css declares", () => {
    // Every `--name` in backticks, which is how the documents refer to a token
    // throughout.
    //
    // The exception is a name the sentence is *retiring*. Two documents have to
    // keep naming removed tokens to explain why they are gone -- "this used to
    // list `--text-2xl`" and "the debt table used to list `--field-bg`" are the
    // only record that those names were ever there. A guard that flagged those
    // would be telling the documentation to delete its own history, and the
    // next person would re-introduce the same token.
    //
    // So a name is exempt when the sentence around it says so. `--ok` and
    // `--warn` were not exempt, and should not have been: the document called
    // them "compatibility aliases", which is a claim that they work.
    const RETIRED = /已删|已移除|曾经|曾经列|曾列|那一版|旧版|不再是|不存在|已从|退役/;
    const unknown: string[] = [];
    for (const document of DOCUMENTS) {
      const source = read(document);
      const lines = source.split("\n");
      lines.forEach((line, index) => {
        for (const match of line.matchAll(/`(--[a-z0-9-]+)`/g)) {
          const name = match[1].toLowerCase();
          if (DECLARED.has(name)) continue;
          if (RETIRED.test(line)) continue;
          unknown.push(`${document}:${index + 1}: ${name}  "${line.trim().slice(0, 90)}"`);
        }
      });
    }
    expect(
      unknown,
      "these token names are presented as if they exist, but tokens.css does not declare"
        + " them. Either the token was removed and the sentence still describes it as"
        + " usable, or the document invented it. The second shape is the dangerous one:"
        + " a reader following the doc writes back a variable that does not exist, and an"
        + " invalid var() in CSS is silent -- the element just has no colour."
        + " (A sentence that says the token was removed is exempt.)"
    ).toEqual([]);
  });

  it("gives the font scale that tokens.css actually declares", () => {
    // The scale table is a hand-maintained mirror of four declarations, and it
    // was wrong twice in two directions: it listed a `--text-2xl` that was
    // deleted, and a `--text-m` that was deleted later. Both times the count in
    // the prose ("5 steps", "6 steps") drifted with it.
    //
    // So this reads the table row and compares the values, not the count --
    // a count is the thing that has been wrong most often.
    const conventions = read("docs/ui/css-conventions.md");
    const row = conventions.match(/^\|\s*字号\s*\|(.+?)\|/m);
    expect(row, "css-conventions.md must have a 字号 row in its scale table").toBeTruthy();

    const documented = [...row![1].matchAll(/(\d+(?:\.\d+)?)px/g)].map((match) => match[1]);
    const actual = [...light.matchAll(/^\s*--text-[a-z0-9]+\s*:\s*(\d+(?:\.\d+)?)px/gm)]
      .map((match) => match[1])
      .sort((left, right) => Number(left) - Number(right));

    expect(
      documented,
      "the 字号 row lists sizes tokens.css does not declare, or in a different set"
    ).toEqual(actual);
  });

  it("describes the focus ring the way ui.css draws it", () => {
    // The specific failure this exists for: the document argued for
    // "box-shadow rather than outline" with three bullets of reasoning, while
    // `ui.css` had been changed to an outline and `--focus-ring` deleted. A
    // reader trusting that paragraph reintroduces a shadow ring at 1.64:1.
    const conventions = read("docs/ui/css-conventions.md");
    const focusSection = conventions.slice(
      conventions.indexOf("## 3. 焦点环"),
      conventions.indexOf("## 4.")
    );
    expect(focusSection, "css-conventions.md must have a focus-ring section").toBeTruthy();
    expect(
      focusSection!.match(/`--focus-ring`/),
      "the focus-ring section still refers to --focus-ring, which tokens.css no longer"
        + " declares. It is now --focus-ring-color, and the ring is an outline."
    ).toBeNull();
    expect(focusSection).toMatch(/outline/);

    // And the same for the token reference table.
    const tokenDoc = read("docs/ui/tokens.md");
    expect(
      tokenDoc.match(/`--focus-ring`/),
      "tokens.md's focus group still lists --focus-ring; it should list --focus-ring-color"
    ).toBeNull();
  });
});