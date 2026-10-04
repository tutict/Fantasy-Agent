import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tokens = readFileSync(resolve(root, "styles/tokens.css"), "utf8");
const [light, dark] = tokens.split(':root[data-theme="dark"]');
const COLOR = /(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})/g;

function hexes(block: string): Map<string, string> {
  return new Map([...block.matchAll(COLOR)].map((match) => [match[1], match[2].toLowerCase()]));
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
    const steps = [...light.matchAll(/^\s*--text-[a-z0-9]+\s*:\s*(\d+(?:\.\d+)?)px\s*;/gm)]
      .map((match) => Number(match[1]))
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
    const stylesDir = resolve(root, "styles");
    const sources = readdirSync(stylesDir)
      .filter((name) => name.endsWith(".css") && name !== "tokens.css")
      .map((name) => readFileSync(resolve(stylesDir, name), "utf8"))
      .join("\n");
    const declared = [...light.matchAll(/^\s*(--text-[a-z0-9]+)\s*:/gm)].map((match) => match[1]);

    expect(declared.length).toBeGreaterThanOrEqual(3);
    const orphans = declared.filter(
      (token) => !sources.includes(`var(${token})`) && !token.includes("placeholder")
    );
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