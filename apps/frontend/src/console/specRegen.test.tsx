import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SpecRegenPanel } from "./rendering";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import type { GameplaySpec, PromptRequest } from "../shared/types";

/**
 * The console's "regenerate & compare" panel.
 *
 * The comparison rules themselves are pinned in `shared/specDiff.test.ts`; what
 * is left for this file is the panel's own contract, and it has four parts that
 * are easy to lose in a refactor:
 *
 *   1. **The prompt caveat ships with the request.** `promptRequestFromPlan`
 *      reconstructs the request from the plan, and the plan never stored the
 *      prompt -- so the prompt sent is a reconstruction, and the panel has to say
 *      so. Without it an operator reads a diff between two unrelated specs as a
 *      drift report, which is the one reading that would make them distrust a
 *      healthy backend.
 *   2. **The button is dead until a plan arrives.** A cold console has nothing to
 *      regenerate from.
 *   3. **A drift chip, never a silent list.** "No drift" and "7 fields drifted"
 *      are the two answers, and both must be on screen.
 *   4. **Non-zero drift renders a row per field, with both sides.** The `->`
 *      between them is the whole point.
 *
 * Every assertion goes through `consoleI18n`, so a panel reaching for a key the
 * console dictionary lacks renders the raw key name and fails here.
 */

const t = makeTranslator("en", consoleI18n);

afterEach(() => cleanup());

const request: PromptRequest = {
  prompt: "Neon Rooftops. Deliver packages across a collapsing skyline.",
  target_minutes: 10,
  engine_version: "Godot 4.5",
  platforms: ["Windows"],
  output_locales: ["en", "zh-CN"]
};

function spec(overrides: Partial<GameplaySpec> = {}): GameplaySpec {
  return {
    title: "Neon Rooftops",
    target_session_minutes: 10,
    win_state: "reach the drop zone",
    core_verbs: ["wall-run"],
    ...overrides
  };
}

function renderPanel(overrides: Partial<Parameters<typeof SpecRegenPanel>[0]> = {}) {
  return render(
    <SpecRegenPanel
      request={request}
      baseline={spec()}
      regenerated={null}
      regenerating={false}
      error={null}
      onRegenerate={() => {}}
      onClear={() => {}}
      t={t}
      {...overrides}
    />
  );
}

describe("spec regen panel", () => {
  it("keeps the regenerate button dead until a plan arrives", () => {
    // There is nothing to regenerate from, so the button must not be clickable
    // -- and the panel must say why rather than leaving an inert control.
    const { container } = renderPanel({ request: null });

    expect(screen.getByText("Load a planning handoff to regenerate its spec.")).toBeTruthy();
    const button = container.querySelector<HTMLButtonElement>("#spec-regen-button");
    expect(button?.disabled).toBe(true);
    expect(container.querySelector(".spec-regen-request")).toBeNull();
  });

  it("shows the request it will send, with the prompt caveat attached", () => {
    // The caveat is the reason this block is collapsible-but-present rather than
    // a tooltip: it has to be readable at the moment of deciding to press.
    const { container } = renderPanel();

    expect(screen.getByText("Request this sends")).toBeTruthy();
    expect(container.querySelector(".spec-regen-request code")?.textContent).toBe(request.prompt);
    expect(screen.getByText("Prompt")).toBeTruthy();
    expect(screen.getByText("Scope")).toBeTruthy();
    // Scope renders as one line: minutes / engine / platforms / locales. Asserted
    // on the element that holds it (`<dd>`), because the surrounding `<details>`
    // matches a text-content predicate too.
    const scope = container.querySelectorAll(".spec-regen-request dd")[1];
    expect(scope?.textContent).toContain("Godot 4.5");
    expect(scope?.textContent).toContain("Windows");
    expect(scope?.textContent).toContain("en, zh-CN");
    expect(
      screen.getByText(/Reconstructed from the plan, not the original prompt/)
    ).toBeTruthy();
    expect(container.querySelector<HTMLButtonElement>("#spec-regen-button")?.disabled).toBe(false);
  });

  it("says the engine and platforms only count when LLM generation is on", () => {
    // The scope line lists engine and platforms alongside minutes, which reads as
    // "all of these shaped the result". Only the prompt and the target length do
    // so on the offline path, and the note has to be on screen next to the line
    // it qualifies -- not behind a tooltip, and not only in the docs.
    renderPanel();

    expect(screen.getByText(/only read when LLM generation is on/)).toBeTruthy();
  });

  it("says no drift rather than rendering an empty list when every field matches", () => {
    // An empty diff region is indistinguishable from a payload that failed to
    // arrive; the explicit line is the difference. The container keeps its `id`
    // so a caller can scroll to it, but it is a `<p>` rather than the row list.
    const { container } = renderPanel({ regenerated: spec() });

    expect(screen.getByText("No drift")).toBeTruthy();
    expect(screen.getByText("Every field matches the frozen snapshot.")).toBeTruthy();
    expect(container.querySelector(".spec-diff-row")).toBeNull();
    expect(container.querySelector("#spec-diff-list")?.tagName).toBe("P");
  });

  it("counts the drifted fields and lists one row per difference", () => {
    const { container } = renderPanel({
      regenerated: spec({ win_state: "survive 10 minutes", core_verbs: ["wall-run", "vault"] })
    });

    expect(screen.getByText("2 fields drifted")).toBeTruthy();

    const rows = [...container.querySelectorAll(".spec-diff-row")];
    const fields = rows.map((row) => row.querySelector("code")?.textContent);
    expect(fields).toEqual(["win_state", "core_verbs"]);
    // Both sides of each difference, so the operator sees the movement not just
    // that there was one.
    expect(screen.getByText("reach the drop zone")).toBeTruthy();
    expect(screen.getByText("survive 10 minutes")).toBeTruthy();
    expect(container.querySelectorAll(".spec-diff-before")).toHaveLength(2);
    expect(container.querySelectorAll(".spec-diff-after")).toHaveLength(2);
  });

  it("renders a summary of the regenerated spec without dumping the diff", () => {
    // `specDigest` counts the groups the operator tunes, so the panel can say
    // "2 loop steps, 1 system" without a row per field. Asserted on the digest's
    // own text because each entry is a label plus a `<strong>` value.
    const { container } = renderPanel({
      regenerated: spec({
        core_loop: [{ action: "wall-run" }, { action: "vault" }],
        systems: [{ name: "momentum" }],
        level_beats: [{ name: "intro" }],
        enemies: [{ name: "drone" }]
      })
    });

    const digest = container.querySelector("#spec-regen-digest");
    expect(digest).toBeTruthy();
    for (const label of ["Title", "Target", "Verbs", "Loop steps", "Systems", "Beats", "Enemies"]) {
      expect(digest?.textContent, label).toContain(label);
    }
    // The counted values, read off the digest rather than the whole document.
    expect(digest?.textContent).toContain("Neon Rooftops");
    expect(digest?.textContent).toContain("2"); // loop steps
  });

  it("shows the backend's own failure text instead of a stale comparison", () => {
    renderPanel({ regenerated: null, error: "prompt 为空" });

    expect(screen.getByText(/Regeneration failed/)).toBeTruthy();
    expect(screen.getByText(/prompt 为空/)).toBeTruthy();
    // No digest and no diff: nothing was produced to compare.
    expect(screen.queryByText("No drift")).toBeNull();
    expect(screen.queryByText("Title")).toBeNull();
  });

  it("shows the running label while the request is in flight", () => {
    const { container } = renderPanel({ regenerating: true });

    expect(screen.getByText("Regenerating...")).toBeTruthy();
    expect(container.querySelector<HTMLButtonElement>("#spec-regen-button")?.disabled).toBe(true);
  });

  it("offers the clear control only once there is something to clear", () => {
    expect(renderPanel({ regenerated: null }).container.querySelector("#spec-regen-clear")).toBeNull();
    cleanup();
    expect(renderPanel({ regenerated: spec() }).container.querySelector("#spec-regen-clear")).toBeTruthy();
  });

  it("tolerates a cold start where the baseline itself is missing", () => {
    // First generation: there is no snapshot, so every field reads as new. The
    // panel must not throw on a null baseline.
    const { container } = renderPanel({ baseline: null, regenerated: spec() });

    expect(screen.getByText(/fields drifted/)).toBeTruthy();
    expect(container.querySelectorAll(".spec-diff-before").length).toBeGreaterThan(0);
  });
});
