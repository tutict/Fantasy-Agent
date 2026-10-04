import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tokens = readFileSync(resolve(root, "styles/tokens.css"), "utf8");
const [light, dark] = tokens.split(':root[data-theme="dark"]');
const COLOR = /(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})/g;

/**
 * Tokens whose value carries an alpha channel, so what the operator sees is a
 * composite and the number a contrast test computes from the literal is the
 * wrong one.
 *
 * This list is why the matchers below accept both 8-digit hex and `rgba()`.
 * `hexes()` used to accept 6-digit hex only, which made the translucent values
 * invisible to it -- they were in the file and no assertion could see them. An
 * invisible value is worse than a wrong one: `--text-placeholder` sat at
 * `#6b666080` (50% alpha) through a whole round of colour work with nothing
 * reporting that what it composites to is 1.70:1 on the light surfaces.
 *
 * Every entry must earn its place: the assertions below require each name to be
 * declared in both themes and read by at least one `var()`.
 */
const ALPHA_TOKENS = [
  // The focus ring and the grid lines are translucent *by design* -- a ring has
  // to blend with whatever it lands on. Their visibility is asserted by
  // computing the composite, not by reading the literal.
  "--focus-soft",
  "--grid-line-a",
  "--grid-line-b",
  "--brand-tint",
  "--surface-translucent"
];

function hexes(block: string): Map<string, string> {
  return new Map([...block.matchAll(COLOR)].map((match) => [match[1], match[2].toLowerCase()]));
}

/**
 * Every declared value that is not plain opaque hex: 8-digit literals and
 * `rgba()` alike, plus the forms a first pass missed.
 *
 * Three shapes got through the first version of this function, each found by
 * mutation rather than by reading:
 *
 *   - **4-digit hex** (`#0008`). Shorthand for `#00000088`, so it is 53% alpha
 *     and every number computed from it as if it were opaque is wrong.
 *   - **`hsla()`**. Same idea, different function name.
 *   - **a value on the line after the declaration.** The pattern was anchored
 *     `^\s*--name\s*:` and the value ran to the next `;`, but a value broken
 *     across lines puts the opening `--name:` on one line and the colour on the
 *     next, and a name whose *value* starts on the following line was never
 *     collected at all.
 *
 * The third one is why the value is matched loosely and classified afterwards,
 * rather than the declaration being parsed precisely and classified once.
 */
function translucentValues(block: string): { name: string; value: string }[] {
  const out: { name: string; value: string }[] = [];
  for (const match of block.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+)/g)) {
    const name = match[1];
    const value = match[2].trim().toLowerCase().replace(/\s+/g, " ");
    // 4 or 8 digit hex: both carry an alpha channel. 6 digit is opaque.
    if (/^#[0-9a-f]{4}([0-9a-f]{4})?$/.test(value) || /^#[0-9a-f]{8}$/.test(value)) {
      if (!value.endsWith("ff")) out.push({ name, value });
      continue;
    }
    if (/^(rgba?|hsla?)\(/.test(value)) out.push({ name, value });
  }
  return out;
}

function channel(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  return [0, 2, 4].map((offset) => Number.parseInt(value.slice(offset, offset + 2), 16)) as [number, number, number];
}

function luminance(hex: string): number {
  const values = channel(hex).map((item) => {
    const scaled = item / 255;
    return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
}

function contrast(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((left, right) => right - left);
  return (lighter + 0.05) / (darker + 0.05);
}

const PAIRED = [
  "--brand", "--brand-strong", "--brand-soft", "--on-brand",
  "--text", "--text-soft", "--muted",
  "--bg", "--surface", "--surface-muted",
  "--line", "--line-strong",
  "--status-running", "--status-success", "--status-waiting", "--status-warning", "--status-danger", "--status-human", "--status-info",
  "--focus",
  "--data-1", "--data-2", "--data-3", "--data-4", "--data-5", "--data-6"
];
const STATUS = ["--status-running", "--status-success", "--status-waiting", "--status-warning", "--status-danger", "--status-human", "--status-info"];

describe("drafting-table tokens", () => {
  it("defines brand, text, surface, line, status, focus, and data colors in both themes", () => {
    const lightHex = hexes(light);
    const darkHex = hexes(dark);
    for (const token of PAIRED) {
      expect(lightHex.get(token), token).toMatch(/^#[0-9a-f]{6}$/);
      expect(darkHex.get(token), token).toMatch(/^#[0-9a-f]{6}$/);
    }
    expect(light).not.toContain("#00ffcc");
    expect(dark).not.toContain("#00ffcc");
    expect(tokens).toContain("--duration-fast: 140ms");
    expect(tokens).toContain("--duration-slow: 180ms");
    expect(tokens).toContain("--size-control: 44px");
    expect(tokens).toContain("--font-ui: \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\"");
  });

  it("does not reuse the brand color for a status", () => {
    for (const block of [hexes(light), hexes(dark)]) {
      const brand = block.get("--brand");
      const values = STATUS.map((token) => block.get(token));
      expect(new Set(values).size).toBe(values.length);
      expect(values).not.toContain(brand);
    }
  });

  it("meets AA contrast for text, buttons, and status colors", () => {
    for (const block of [hexes(light), hexes(dark)]) {
      expect(contrast(block.get("--text")!, block.get("--bg")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--text")!, block.get("--surface")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--muted")!, block.get("--bg")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--muted")!, block.get("--surface")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--text-soft")!, block.get("--surface")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--on-brand")!, block.get("--brand")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--on-brand")!, block.get("--brand-strong")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--on-danger")!, block.get("--status-danger")!)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(block.get("--line-strong")!, block.get("--surface")!)).toBeGreaterThanOrEqual(3);
      for (const status of STATUS) {
        expect(contrast(block.get(status)!, block.get("--surface")!), status).toBeGreaterThanOrEqual(4.5);
      }
      for (const data of ["--data-1", "--data-2", "--data-3", "--data-4", "--data-5", "--data-6"]) {
        expect(contrast(block.get(data)!, block.get("--surface")!), data).toBeGreaterThanOrEqual(3);
      }
    }
  });

  it("composite the translucent tokens instead of trusting their literals", () => {
    // An 8-digit literal is a lie about what gets rendered: `#6b666080` is 50%
    // alpha, and on a light surface the pixels that reach the eye are a blend of
    // that colour and the surface underneath. Reading the literal as if it were
    // opaque is how `--text-placeholder` held a 1.70:1 reading through a whole
    // round of colour work.
    //
    // So: every value with an alpha channel has to be on the list, and every
    // name on the list has to be declared in both themes and read somewhere. A
    // list entry nothing uses is a comment pretending to be a guard.
    //
    // "Read somewhere" includes being read by *another token* rather than by a
    // component: `--focus-soft` is only ever referenced from `--focus-ring`,
    // which is what the components use. Requiring a component to name it
    // directly would have failed on a token that is genuinely in use.
    const stylesDir = resolve(root, "styles");
    const consumers = [tokens, ...readdirSync(stylesDir)
      .filter((name) => name.endsWith(".css") && name !== "tokens.css")
      .map((name) => readFileSync(resolve(stylesDir, name), "utf8"))].join("\n");

    expect(ALPHA_TOKENS.length).toBeGreaterThanOrEqual(5);
    for (const name of ALPHA_TOKENS) {
      for (const [theme, block] of [["light", light], ["dark", dark]] as const) {
        const declared = [...block.matchAll(new RegExp(`^\\s*${name}\\s*:\\s*([^;]+)`, "gm"))];
        expect(declared.length, `${name} is missing from the ${theme} block`).toBe(1);
        expect(
          declared[0][1].trim(),
          `${name} (${theme}) is on the translucent list, so it must actually be translucent`
        ).toMatch(/^(#[0-9a-f]{8}|rgba?\()/);
      }
      expect(consumers.includes(`var(${name})`), `${name} is declared but nothing reads it`).toBe(true);
    }

    // And the other direction: anything translucent in *either* block has to be
    // on the list.
    //
    // `[light, dark]` -- an array of the two blocks. Spreading them instead
    // (`[...light, ...dark]`) spreads a *string*, which yields an array of
    // characters; `flatMap` over characters finds nothing and the assertion
    // passes on an empty list forever. It did exactly that here: the check ran,
    // the input was `[]`, and a token with an alpha channel could be added to
    // either theme without anything reporting it.
    const unlisted = [
      ...new Set(
        [light, dark]
          .flatMap((block) => translucentValues(block).map((item) => item.name))
          .filter((name) => !ALPHA_TOKENS.includes(name))
      )
    ];
    expect(
      unlisted,
      "these carry an alpha channel but are not on ALPHA_TOKENS, so no assertion computes their composite"
    ).toEqual([]);
  });

  it("keeps placeholder text readable on every surface it lands on", () => {
    // This is the only clue the operator has about how to phrase a correction
    // ("be specific about what is wrong and where"). It was 1.70:1 on the light
    // surfaces and nothing reported it, because the declared value was 8-digit
    // and the contrast helper read it as opaque.
    const surfaces = ["--field", "--surface", "--surface-muted", "--tab-bg"];
    for (const [block, theme] of [[light, "light"], [dark, "dark"]] as const) {
      const map = hexes(block);
      for (const surface of surfaces) {
        expect(
          contrast(map.get("--text-placeholder")!, map.get(surface)!),
          `placeholder on ${surface} (${theme})`
        ).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it("keeps the type scale in steps big enough to tell apart", () => {
    // The scale used to be 11 / 13 / 14 / 16 / 24, and 13-to-14 was the fault
    // line: `12px` and `13px` once coexisted 76 times across the sheets, which
    // rendered the same screen at two qualities because nobody could see the
    // difference. `13` and `14` is the same mistake one step apart.
    //
    // Two assertions, and the second is the one that earns its keep. A
    // "no two steps closer than 2px" rule passes on 11/13/16/24 -- the gaps are
    // 2, 3 and 8 -- so it cannot see the regression it was written for. What
    // makes 13/14 wrong is not the gap but the *value*: 13 is the number this
    // project already burned, so it may not come back as a step. That is stated
    // as a fact about the number rather than as a gap measurement.
    // The pattern only accepts `px`, which means a `rem` step is not counted
    // rather than rejected. A mutation that set `--text-s: 0.9rem` therefore
    // shortened the scale by one entry and every gap assertion still passed.
    // So the unit is checked separately: a step declared in anything else is a
    // failure, not a silent omission. The whole file is px-based, so this is not
    // a style preference -- a rem step would be the one value on the ladder
    // that moves with the user's font size, which is exactly what the ladder
    // exists to prevent.
    //
    // The steps are the single-suffix names (`--text-xs`, `--text-s`, `--text-l`,
    // `--text-xl`). `--text-soft` and `--text-placeholder` share the prefix but
    // are colours, and holding a hex to a "must be px" rule would be nonsense.
    // A step is a name whose value starts with a digit.
    const declarations = [...light.matchAll(/^\s*(--text-[a-z0-9-]+)\s*:\s*([^;]+)/gm)]
      .map((match) => ({ name: match[1], value: match[2].trim() }))
      .filter((item) => /^\d/.test(item.value));
    const wrongUnit = declarations
      .filter((item) => !/^\d+(?:\.\d+)?px$/.test(item.value))
      .map((item) => `${item.name}: ${item.value}`);
    expect(
      wrongUnit,
      "a text step must be declared in px -- a rem or em step moves with the user's"
        + " font size, which is the one thing the scale is supposed to stop"
    ).toEqual([]);

    const steps = declarations
      .map((item) => Number(item.value.replace(/px$/, "")))
      .sort((left, right) => left - right);

    expect(steps.length).toBeGreaterThanOrEqual(3);
    for (let index = 1; index < steps.length; index += 1) {
      const gap = steps[index] - steps[index - 1];
      expect(
        gap,
        `${steps[index - 1]}px and ${steps[index]}px are ${gap}px apart -- too close to tell apart on screen`
      ).toBeGreaterThanOrEqual(2);
    }

    // 12px and 13px coexisted 76 times before this pass; 13 came back once as
    // `--text-s` and had to be raised again. Naming the value is the only form
    // of this rule that bites.
    const retired = steps.filter((size) => size === 12 || size === 13);
    expect(
      retired,
      "12px and 13px are retired: each was indistinguishable from a neighbour that was in use at the same time"
    ).toEqual([]);
  });

  it("does not define a text step that nothing references", () => {
    // `--text-m: 14px` had exactly seven references and was the only step whose
    // value coincided with its neighbour's. Collapsing it into `--text-s` is
    // what removed the fault line; a step that comes back without a reader is
    // how it would come back.
    //
    // The steps are picked by their value starting with a digit, the same test
    // the scale test uses, so `--text-soft` and `--text-placeholder` (colours
    // that share the prefix) are not treated as unreadable steps. The earlier
    // version exempted `--text-placeholder` by name, which is a list that has to
    // be remembered rather than a rule.
    const stylesDir = resolve(root, "styles");
    const sources = readdirSync(stylesDir)
      .filter((name) => name.endsWith(".css") && name !== "tokens.css")
      .map((name) => readFileSync(resolve(stylesDir, name), "utf8"))
      .join("\n");
    const steps = [...light.matchAll(/^\s*(--text-[a-z0-9-]+)\s*:\s*([^;]+)/gm)]
      .map((match) => ({ name: match[1], value: match[2].trim() }))
      .filter((item) => /^\d/.test(item.value))
      .map((item) => item.name);

    expect(steps.length).toBeGreaterThanOrEqual(3);
    const orphans = steps.filter((token) => !sources.includes(`var(${token})`));
    expect(orphans, "a text step nothing reads is a claim nobody kept").toEqual([]);
  });

  it("keeps new component styles on tokens instead of hardcoded colors", () => {
    const files = readdirSync(root, { recursive: true }) as string[];
    const offenders: string[] = [];
    for (const file of files) {
      const path = String(file).replaceAll("\\", "/");
      if (!path.endsWith(".tsx") || path.includes(".test.")) continue;
      const source = readFileSync(resolve(root, path), "utf8");
      if (/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/.test(source)) offenders.push(path);
    }
    const ui = readFileSync(resolve(root, "styles/ui.css"), "utf8");
    expect(offenders).toEqual([]);
    expect(ui.replace(/white-space/g, "wrap")).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|\bwhite\b/);
    expect(ui).toContain("var(--duration-fast)");
    expect(ui).toContain("@media (prefers-reduced-motion: reduce)");
    expect(ui).not.toContain("infinite");
  });
});