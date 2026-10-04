import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The focus ring, measured rather than declared.
 *
 * The ring used to be `box-shadow: 0 0 0 3px rgba(20, 63, 56, .28)`. A
 * translucent shadow composites with whatever is behind it, and on this project's
 * light theme -- a warm paper at luminance ~0.93 -- that composite came out at
 * **1.34:1** against every surface it could land on. WCAG 2.2 SC 1.4.11 asks 3:1
 * for a focus indicator, so the ring failed by more than half, on the theme
 * almost every session uses.
 *
 * Raising the alpha does not rescue it. Sweeping 0.28 -> 0.80 against five light
 * surfaces: 1.34, 1.56, 1.96, 2.71, 3.46. It clears 3:1 only at 0.80, which is a
 * solid slab rather than a ring, and six darker ring colours at three alphas
 * were no better -- the bright background simply does not move much when
 * something translucent is laid over it.
 *
 * So the ring is an `outline` now, and an outline is solid: `--focus-ring-color`
 * clears the bar by a wide margin in both themes.
 *
 * The assertion below computes the composite rather than reading the literal,
 * which is the whole point -- the literal is what made this invisible for a
 * round. WCAG non-text threshold is 3:1.
 */

// This file sits in `src/shared/ui/`, so the stylesheets are two levels up --
// `shared/` and then `src/`. `accessibility.test.ts` in this same directory
// spells it `../../styles/ui.css`; the two must agree or one of them reads a
// path that does not exist.
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const tokens = readFileSync(resolve(root, "styles/tokens.css"), "utf8");
const [light, dark] = tokens.split(':root[data-theme="dark"]');
const uiCss = readFileSync(resolve(root, "styles/ui.css"), "utf8");

/** `--name: <value>;` declared exactly once in a block. */
function declared(block: string, name: string): string {
  const matches = [...block.matchAll(new RegExp(`^\\s*${name}\\s*:\\s*([^;]+)`, "gm"))];
  expect(matches.length, `${name} should be declared once in this block`).toBe(1);
  return matches[0][1].trim();
}

function channels(value: string): [number, number, number] {
  const hex = value.replace("#", "");
  return [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16)) as [
    number,
    number,
    number
  ];
}

function relativeLuminance(value: string): number {
  const [r, g, b] = channels(value);
  const linear = [r, g, b].map((item) => {
    const scaled = item / 255;
    return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(first: string, second: string): number {
  const [lighter, darker] = [
    relativeLuminance(first),
    relativeLuminance(second)
  ].sort((left, right) => right - left);
  return (lighter + 0.05) / (darker + 0.05);
}

/** `rgba(r, g, b, a)` flattened over an opaque backdrop, as the browser does. */
function composite(rgba: string, backdrop: string): string {
  const parts = rgba
    .replace(/^rgba?\(/, "")
    .replace(")", "")
    .split(",")
    .map((part) => Number.parseFloat(part.trim()));
  const [r, g, b, alpha] = parts;
  const back = channels(backdrop);
  const blend = (foreground: number, behind: number) =>
    Math.round(foreground * alpha + behind * (1 - alpha));
  return `#${[blend(r, back[0]), blend(g, back[1]), blend(b, back[2])]
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("")}`;
}

/**
 * The surfaces a focus ring can land on, per theme.
 *
 * Both lists are the same names on purpose: `tokens.css` declares every one of
 * them in both blocks, and a name that existed in only one theme would make the
 * other theme's `declared()` call fail with a confusing "expected 1 to be 1"
 * instead of naming the token that is missing from one theme.
 *
 * Ten entries, not eight. `--surface-strong` and `--chrome-strong` were left out
 * of the first version and a mutation that deleted or recoloured either of them
 * left the guard green -- they are real surfaces (a raised card, a pinned
 * header), so a ring on one of them has to clear 3:1 too. Measured minima with
 * the current ring: light 11.61 on `--surface-muted`, dark 5.31 on
 * `--surface-muted`.
 */
const FOCUS_SURFACES = [
  "--bg", "--surface", "--surface-strong", "--surface-muted",
  "--chrome", "--chrome-strong",
  "--field", "--code-bg", "--tab-bg", "--pill-bg"
];

/**
 * The list is not allowed to shrink silently.
 *
 * Both surface regressions this review found were the same shape: a name left
 * out of the list, so a mutation that deleted or recoloured that token left the
 * guard green. An assertion on the names' *content* cannot catch that -- the
 * token is simply not asked about. Asserting the count is what makes removing an
 * entry a visible change rather than a quieter guard.
 */
const EXPECTED_SURFACE_COUNT = 10;

/** The seven state colours, which a ring must not be mistaken for. */
const STATUS_TOKENS = [
  "--status-running", "--status-success", "--status-waiting", "--status-warning",
  "--status-danger", "--status-human", "--status-info"
];

describe("the focus ring", () => {
  it("declares a solid ring colour in both themes", () => {
    for (const [theme, block] of [["light", light], ["dark", dark]] as const) {
      const value = declared(block, "--focus-ring-color");
      expect(value, `--focus-ring-color (${theme}) must be an opaque hex`).toMatch(
        /^#[0-9a-f]{6}$/
      );
    }
  });

  it("is drawn as an outline, not only as a shadow", () => {
    // A shadow-only ring is the regression this whole check exists for. The
    // selector list itself is asserted by `accessibility.test.ts`; what matters
    // here is that the declaration is an outline and it is not suppressed.
    const shared = uiCss.match(
      /\.ui-button:focus-visible,[\s\S]*?\{([^}]*)\}/
    );
    expect(shared, "ui.css must have one rule listing the focusable elements").toBeTruthy();
    const body = shared![1];
    expect(body).toMatch(/outline:\s*2px solid var\(--focus-ring-color\)/);
    expect(body).not.toMatch(/outline:\s*none/);
    // The soft glow stays, so the ring reads as a ring and not as a border.
    expect(body).toMatch(/box-shadow:[^;]*var\(--focus-soft\)/);
  });

  it("clears 3:1 against every surface in both themes", () => {
    // Guards the list as well as the colour: a name dropped from `FOCUS_SURFACES`
    // is a surface nobody checks, and that is exactly how `--surface-strong` and
    // `--chrome-strong` escaped the first version of this file.
    expect(FOCUS_SURFACES.length).toBe(EXPECTED_SURFACE_COUNT);
    expect(new Set(FOCUS_SURFACES).size).toBe(EXPECTED_SURFACE_COUNT);

    for (const [theme, block, surfaces] of [
      ["light", light, FOCUS_SURFACES],
      ["dark", dark, FOCUS_SURFACES]
    ] as const) {
      const ring = declared(block, "--focus-ring-color");
      for (const surface of surfaces) {
        const against = declared(block, surface);
        expect(
          contrast(ring, against),
          `focus ring ${ring} on ${surface} ${against} (${theme}) -- WCAG 2.2 SC 1.4.11 wants 3:1`
        ).toBeGreaterThanOrEqual(3);
      }
    }
  });

  it("records the one place the ring and a focused border are the same colour", () => {
    // Focusing a text field raises its border to `--line-strong` (see the
    // `input[type="text"]:focus-visible` rule in ui.css), so the ring ends up
    // next to a border rather than next to the bare surface. In the dark theme
    // the two are 1.08:1 -- the same warm family at similar lightness.
    //
    // Six candidate ring colours were measured against that. Every one that
    // separated from the warm `--line-strong` collided with a *status* colour
    // instead: cyan #8adcee is 1.00 from `status-human` and 1.03 from both
    // `status-success` and `status-danger`, lime #b6d94a is 1.01 from
    // `status-danger`. Trading "looks like a thicker border" for "looks like a
    // status" is the worse of the two, so the colour stays.
    //
    // What makes it readable anyway is the geometry, not the ratio: the ring is
    // an outline at `outline-offset: 1px`, so the pixels are
    //
    //     [ ring 2px ][ 1px of surface ][ border 1px ][ field interior ]
    //
    // -- two lines with a surface-coloured gap between them, never touching.
    // And the ring is not competing on the border's terms: measured against
    // `--surface` it is 6.45:1 while the border is 7.43:1, so both are plainly
    // visible and the reader sees three bands rather than one thick line.
    //
    // So this asserts the *measured* ratio rather than a hope, with the floor
    // set where it is. A future colour change that makes this worse fails here,
    // which is the point: the trade is now written down instead of implicit.
    //
    // Two assertions, and the order matters. "Not the same value" is the one
    // with teeth: a ring painted in exactly `--line-strong` is indistinguishable
    // from a focused border by construction, and **no threshold above 1.0 can
    // catch it** -- identical colours score exactly 1.00, so a floor of 1.02
    // would catch it only by accident of where the current value happens to sit
    // (1.08). The numeric floor is the loose one: it records what we measured and
    // would object to a colour that made the two overlap properly.
    //
    // The second half is what the first version of this test left out. It
    // checked the ring against the border but not the border against the
    // surface, so moving `--line-strong` anywhere near the ring passed. A
    // focused border that vanishes into the background is worse than one that
    // matches the ring, because the ring alone then carries the whole signal.
    for (const [theme, block, floor] of [
      ["light", light, 1.5],
      ["dark", dark, 1.0]
    ] as const) {
      const ring = declared(block, "--focus-ring-color");
      const border = declared(block, "--line-strong");
      expect(
        ring.toLowerCase(),
        `--focus-ring-color is --line-strong (${theme}) -- a ring painted in the`
          + " border's colour is indistinguishable from it, and no contrast"
          + " threshold can catch that. Pick another colour."
      ).not.toBe(border.toLowerCase());

      expect(
        contrast(ring, border),
        `ring vs --line-strong (${theme}) fell below ${floor} -- the ring and a focused`
          + " border are now closer than this, and the geometry note above no longer"
          + " carries it. Re-run the six-candidate sweep before changing the colour."
      ).toBeGreaterThanOrEqual(floor);

      for (const surface of FOCUS_SURFACES) {
        const against = declared(block, surface);
        expect(
          contrast(border, against),
          `--line-strong ${border} on ${surface} (${theme}) -- a focused border that`
            + " disappears into the background leaves the ring carrying everything"
        ).toBeGreaterThanOrEqual(1.3);
      }
    }
  });

  it("does not reuse a status colour, which is where the alternatives all went", () => {
    // Six candidate dark ring colours were measured against the focused border
    // and each family failed somewhere different. Warm ones (#cf9a4a, #e8863a)
    // land on the warm `--line-strong` at 1.08-1.14. The ones that escaped that
    // -- cyan #8adcee, lime #b6d94a -- landed on a *status* colour instead:
    // 1.00 from `status-human`, 1.03 from `status-success`, 1.01 from
    // `status-danger`. Trading "reads as a thicker border" for "reads as a
    // state" is the worse of the two, because a ring is a persistent frame
    // around whatever the operator is typing while a badge is a label beside
    // it, and conflating the two is how a warning gets read as "fine".
    //
    // The threshold is 1.25 rather than 3:1 on purpose. A ring does not have to
    // be identifiable as "not a status" by contrast alone -- it is a different
    // shape in a different place -- but landing *on* a status colour is the one
    // failure mode with a real cost, so that is what gets a threshold.
    for (const [theme, block] of [["light", light], ["dark", dark]] as const) {
      const ring = declared(block, "--focus-ring-color");
      for (const status of STATUS_TOKENS) {
        const value = declared(block, status);
        expect(
          contrast(ring, value),
          `focus ring ${ring} is ${contrast(ring, value).toFixed(2)}:1 from ${status}`
            + ` ${value} (${theme}) -- a ring that reads as a state label is worse`
            + " than one that reads as a thicker border. Re-run the sweep."
        ).toBeGreaterThanOrEqual(1.25);
      }
    }
  });

  it("keeps the soft glow visible too, so the ring is not a hard border", () => {
    // The glow is allowed to be subtle -- it is not the indicator any more --
    // but it still has to be *something*. Asserting a floor catches both a
    // `--focus-soft` that lost its alpha and one that was deleted outright.
    for (const [theme, block, surfaces] of [
      ["light", light, FOCUS_SURFACES],
      ["dark", dark, FOCUS_SURFACES]
    ] as const) {
      const soft = declared(block, "--focus-soft");
      const alpha = Number.parseFloat(soft.replace(/^rgba?\([^,]+,[^,]+,[^,]+,\s*/, "").replace(")", ""));
      expect(alpha, `--focus-soft (${theme}) needs some transparency to read as a glow`).toBeGreaterThan(0);

      for (const surface of surfaces) {
        const against = declared(block, surface);
        expect(
          contrast(composite(soft, against), against),
          `focus glow on ${surface} (${theme}) -- it is decoration now, but not invisible`
        ).toBeGreaterThanOrEqual(1.1);
      }
    }
  });

  it("does not reuse the brand colour verbatim", () => {
    // A ring painted in exactly `--brand` is indistinguishable from a selected
    // state by construction -- same pixels, so no threshold can separate them.
    // That is the case worth asserting.
    //
    // A *contrast* requirement against the brand was tried here and dropped
    // because it is unreachable, not merely unmet: clearing 3:1 against the
    // palest surface (`#fffdf8`, luminance 0.97) forces the ring's luminance to
    // 0.294 or below, and `--brand` sits at 0.086, so the best any compliant
    // ring can reach is about 2.2:1. There is no colour that satisfies both.
    //
    // What is left is the honest form: not the same value, and enough chroma to
    // read as an indicator rather than as a grey border. WCAG 1.4.11 asks the
    // indicator to be distinguishable from adjacent colours -- the surface --
    // which the previous assertion covers; it does not ask it to separate from
    // every other coloured element on screen, and a ring around a text field is
    // a different shape in a different place from a filled button.
    for (const [theme, block] of [["light", light], ["dark", dark]] as const) {
      const ring = declared(block, "--focus-ring-color");
      const brand = declared(block, "--brand");
      expect(ring, `--focus-ring-color (${theme}) must not be the brand colour verbatim`).not.toBe(brand);
      expect(ring, `--focus-ring-color (${theme}) must not be the brand colour verbatim`).not.toBe(
        brand.toLowerCase()
      );

      // Chroma: a pure grey ring reads as a border, not as "you are here".
      const [r, g, b] = channels(ring);
      const high = Math.max(r, g, b);
      const low = Math.min(r, g, b);
      const chroma = high === 0 ? 0 : (high - low) / high;
      expect(chroma, `--focus-ring-color ${ring} (${theme}) is a grey; it reads as a border`).toBeGreaterThan(0.3);
    }
  });

  it("keeps the high-contrast fallback, which now agrees with the ring", () => {
    // Windows high-contrast mode drops box-shadow, so the outline is what
    // survives there. It was the fallback before; now it is the same mechanism
    // the ring uses, which is why the two cannot drift apart silently.
    expect(uiCss).toContain("@media (forced-colors: active)");
    expect(uiCss).toMatch(/forced-colors: active[\s\S]*?outline:[^;]*CanvasText/);
  });
});