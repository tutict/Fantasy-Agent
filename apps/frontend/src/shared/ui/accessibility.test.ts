import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("interaction accessibility", () => {
  it("keeps focus visible and disables motion when requested", () => {
    const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../../styles/ui.css"), "utf8");
    expect(css).toContain(":focus-visible");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
