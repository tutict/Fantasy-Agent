import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const uiPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../styles/ui.css");
const ui = readFileSync(uiPath, "utf8");

/**
 * Two things a stylesheet can look correct and still fail a keyboard user.
 *
 * Both assertions here are substring checks on one file, which is a weak form
 * of evidence on purpose: they cannot tell whether a rule applies to anything.
 * What they do catch is deletion -- a focus ring with no fallback, a motion
 * preference with no opt-out -- and those are the failures that ship, because
 * nobody notices a missing thing by looking at the page.
 *
 * The stronger structural checks live in `shared/cssHygiene.test.ts`, which
 * compares class names against the sheets that style them.
 */
describe("interaction accessibility", () => {
  it("keeps focus visible and disables motion when requested", () => {
    expect(ui).toContain(":focus-visible");
    expect(ui).toContain("@media (prefers-reduced-motion: reduce)");
  });

  it("keeps a focus ring in high-contrast mode", () => {
    // The ring is a box-shadow, and Windows high-contrast mode drops
    // box-shadow entirely. Without an outline fallback it disappears in exactly
    // the mode where a keyboard user is relying on it most.
    expect(ui).toContain("@media (forced-colors: active)");
    // `CanvasText` is a system color keyword: it resolves to whatever the OS
    // uses for text, which is the right thing to outline with here. It also
    // keeps `visualSystem.test.ts`'s no-hardcoded-color rule satisfied, since
    // the rule looks for `#hex` / `rgb(` / `hsl(`.
    expect(ui).toMatch(/forced-colors: active[\s\S]*?outline:[^;]*CanvasText/);
  });

  it("gives every focusable element the ring, not just some of them", () => {
    // A ring that skips `select` or `summary` leaves those reachable but
    // invisible. `iframe` is in the list because the studio shell used to
    // cover it separately; that separate rule is gone.
    const rule = ui.match(/\.ui-button:focus-visible,[\s\S]*?\{/);
    expect(rule, "ui.css must have one rule listing the focusable elements").toBeTruthy();
    for (const selector of ["button", "a", "input", "select", "textarea", "summary", "iframe"]) {
      expect(rule![0], `${selector}:focus-visible must be in the shared rule`).toContain(`${selector}:focus-visible`);
    }
  });
});
