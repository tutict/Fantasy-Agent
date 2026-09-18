import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ToolCatalogPanel } from "./StudioShell";
import { makeTranslator, studioI18n } from "../shared/i18n";
import type { ToolCatalog } from "../shared/types";

/**
 * The Studio's tool catalog panel -- the only place an operator can see what the
 * agent is allowed to do before they grant it anything.
 *
 * Five things here are load-bearing user-facing claims, and each is asserted
 * because getting it wrong misleads rather than merely looks off:
 *
 *   1. **A permission tier per tool.** "read-only" and "execute" are the
 *      difference between a preview and a process launch; a row that renders
 *      without its tier reads as unclassified.
 *   2. **`executable_args` are named as overwritten, not merely hidden.** Hidden
 *      only removes an argument from the advertised schema -- the value is still
 *      discarded per call. Collapsing the two into one label would imply a
 *      weaker guarantee than the backend actually gives.
 *   3. **The planning and engine groups stay separate.** Only the engine half
 *      derives its tier from MCP annotations; one merged list would read as a
 *      claim that the four planning tools have annotation-derived tiers too.
 *   4. **Declared-but-unimplemented is shown, not swallowed.** It is the only
 *      user-visible trace of a contract with no bridge behind it.
 *   5. **The counts summary is a real translation, not a leaked placeholder.**
 *      The translator substitutes `{total}` and friends positionally; a missing
 *      arg leaks the literal `{total}` onto the screen.
 *
 * Everything is driven off one mocked fetch of `getToolCatalog`, so a panel that
 * stops reading a field fails here instead of silently rendering less.
 */

vi.mock("../shared/api", () => ({
  getToolCatalog: vi.fn()
}));

import { getToolCatalog } from "../shared/api";

const t = makeTranslator("en", studioI18n);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const catalog: ToolCatalog = {
  tools: [
    {
      name: "design_gameplay",
      source: "planning",
      permission: "read_only",
      description: "Deterministic spec from a prompt."
    },
    {
      name: "preview_blender_script",
      source: "engine",
      server: "blender",
      permission: "read_only",
      description: "Render the Python without running it.",
      plan_key: "blender_plan",
      hidden_args: ["project_dir"],
      executable_args: ["blender_bin"]
    },
    {
      name: "generate_asset_batch",
      source: "engine",
      server: "comfyui",
      permission: "execute",
      description: "Launch generation.",
      confirm_field: "confirmed_side_effects",
      executable_args: ["comfy_bin"]
    }
  ],
  permission_counts: { read_only: 2, write: 0, execute: 1 },
  declared_without_implementation: ["publish_prototype_branch"]
};

async function openPanel(payload: ToolCatalog = catalog) {
  vi.mocked(getToolCatalog).mockResolvedValue(payload);
  const view = render(<ToolCatalogPanel t={t} />);
  // Collapsed until asked: the panel must not fetch on mount.
  expect(getToolCatalog).not.toHaveBeenCalled();
  view.container.querySelector<HTMLButtonElement>("#tool-catalog-toggle")?.click();
  await waitFor(() => expect(screen.getByText("Planning tools")).toBeTruthy());
  return view;
}

describe("tool catalog panel", () => {
  it("stays collapsed and fetches nothing until the operator asks", () => {
    render(<ToolCatalogPanel t={t} />);

    expect(screen.getByText("Show tools")).toBeTruthy();
    expect(getToolCatalog).not.toHaveBeenCalled();
  });

  it("labels every tool with its permission tier", async () => {
    // The tier is the whole point of the panel: without it an operator cannot
    // tell a preview from a process launch.
    const { container } = await openPanel();

    const rows = [...container.querySelectorAll(".tool-row")];
    expect(rows.map((row) => row.getAttribute("data-permission"))).toEqual([
      "read_only",
      "read_only",
      "execute"
    ]);
    // And the tier is visible as text, not only as an attribute the styling reads.
    expect(container.querySelector('[data-permission="execute"] .tool-tier')?.textContent).toBe("execute");
  });

  it("says executable args are overwritten, not merely hidden", async () => {
    // Two separate labels on purpose. "Hidden" would imply the model's value is
    // simply not offered; the backend also discards it.
    const { container } = await openPanel();

    // Each flag renders as `<p>Label: <code>args</code></p>`, so the label and
    // the args are separate text nodes and neither is matchable as whole text.
    const flags = [...container.querySelectorAll(".tool-row-flag")].map((node) => node.textContent);
    const hidden = flags.find((text) => text?.includes("Hidden"));
    expect(hidden).toContain("project_dir");

    const danger = [...container.querySelectorAll(".tool-row-flag-danger")].map((n) => n.textContent);
    expect(danger).toHaveLength(2);
    for (const text of danger) expect(text).toContain("overwritten");
    // The overwritten ones name the binaries, and none of them claim to be mere
    // "hidden" args -- the distinction is the point of the second class.
    expect(danger.join(" ")).toContain("blender_bin");
    expect(danger.join(" ")).toContain("comfy_bin");
  });

  it("keeps the planning and engine tools in separate groups", async () => {
    // Only the engine half derives its tier from MCP annotations. Merging the
    // lists would present the planning tools' constant `read_only` as if it were
    // annotation-derived too.
    const { container } = await openPanel();

    const groups = [...container.querySelectorAll(".tool-catalog-group")];
    expect(groups).toHaveLength(2);

    const namesIn = (group: Element) =>
      [...group.querySelectorAll(".tool-row code")].map((code) => code.textContent);

    // First `<code>` of each row is the tool name; later ones are arg lists.
    expect(namesIn(groups[0])).toContain("design_gameplay");
    expect(namesIn(groups[0])).not.toContain("generate_asset_batch");
    expect(namesIn(groups[1])).toContain("preview_blender_script");
    expect(namesIn(groups[1])).toContain("generate_asset_batch");
  });

  it("surfaces the tools that are declared but have no implementation", async () => {
    const { container } = await openPanel();

    const gap = container.querySelector("#tool-catalog-gap");
    expect(gap?.textContent).toContain("Declared but not implemented");
    expect(gap?.textContent).toContain("publish_prototype_branch");
  });

  it("shows the confirm field a tool needs before it has any effect", async () => {
    // The confirm field is what stands between a granted tool and its side
    // effect; an operator granting a run needs to see its name.
    const { container } = await openPanel();

    expect(container.querySelector("#tool-catalog-summary")?.textContent).toContain(
      "3 tools - 2 read-only, 0 write, 1 execute"
    );
    const confirm = [...container.querySelectorAll(".tool-row-flag")].map((n) => n.textContent);
    expect(confirm.some((text) => text?.includes("Confirm"))).toBe(true);
    expect(confirm.join(" ")).toContain("confirmed_side_effects");
  });

  it("omits the unimplemented line rather than showing an empty one", async () => {
    const { container } = await openPanel({ tools: [], permission_counts: {} });

    expect(container.querySelector("#tool-catalog-gap")).toBeNull();
  });

  it("reports a failed load instead of rendering an empty catalog", async () => {
    // An empty catalog and a failed request look identical on screen unless the
    // failure is said out loud.
    vi.mocked(getToolCatalog).mockRejectedValue(new Error("connect ECONNREFUSED"));
    const { container } = render(<ToolCatalogPanel t={t} />);
    container.querySelector<HTMLButtonElement>("#tool-catalog-toggle")?.click();

    await waitFor(() =>
      expect(container.querySelector("#tool-catalog-error")?.textContent).toContain(
        "Tool catalog failed to load:"
      )
    );
    expect(container.querySelector("#tool-catalog-error")?.textContent).toContain("ECONNREFUSED");
  });

  it("substitutes every summary placeholder rather than leaking one", () => {
    // The translator replaces `{name}` positionally and leaves an unmatched
    // placeholder verbatim, so a misnamed key argument reaches the screen as
    // literal `{readOnly}` -- and nothing about the call site is type-checked,
    // because `args` is typed as `unknown`.
    const rendered = t("toolsSummary", { total: 20, readOnly: 8, write: 6, execute: 6 });

    expect(rendered).toBe("20 tools - 8 read-only, 6 write, 6 execute");
    expect(rendered).not.toMatch(/\{\w+\}/);
  });
});
