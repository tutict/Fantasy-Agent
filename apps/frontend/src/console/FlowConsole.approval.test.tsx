import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JourneyProvider } from "../shared/journeyContext";
import { FlowConsole } from "./FlowConsole";
import { LocaleThemeProvider } from "../shared/localeTheme";
import { ORCHESTRATION_ENGINE_KEY, ORCHESTRATION_SESSION_KEY } from "../shared/storage";

/**
 * The approval gate lives in the UI: opening a correction target spawns a
 * local editor, so the backend refuses unless the caller passes
 * `confirmed_side_effects: true` -- and the console may only pass `true` after
 * the human confirmed. These tests mount the real console so that deleting the
 * confirmation (or hardcoding `true` again) fails the suite.
 */
const { openMock } = vi.hoisted(() => ({ openMock: vi.fn() }));

vi.mock("../shared/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../shared/api")>();
  return { ...actual, openManualCorrectionTarget: openMock };
});

const OPENABLE_TARGET = "generated";

function emptyJsonFetch() {
  return vi.fn().mockImplementation(() =>
    Promise.resolve(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }))
  );
}

async function renderConsole() {
  const view = render(
    <LocaleThemeProvider>
      <JourneyProvider><FlowConsole /></JourneyProvider>
    </LocaleThemeProvider>
  );
  const button = await waitFor(() => {
    const found = view.container.querySelector<HTMLButtonElement>(
      `[data-manual-target="${OPENABLE_TARGET}"]`
    );
    if (!found || found.disabled) throw new Error("open button not ready");
    return found;
  });
  return { view, button };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  localStorage.clear();
  openMock.mockReset();
  openMock.mockResolvedValue({ status: "started" });
  vi.stubGlobal("fetch", emptyJsonFetch());
});

describe("manual correction approval gate", () => {
  it("does not call the backend when the user cancels the confirmation", async () => {
    const { button } = await renderConsole();
    fireEvent.click(button);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(openMock).not.toHaveBeenCalled();
  });

  it("passes confirmation through only after the user accepts", async () => {
    const { button } = await renderConsole();
    fireEvent.click(button);
    const dialog = await screen.findByRole("dialog");
    expect(openMock).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Open" }));
    await waitFor(() => expect(openMock).toHaveBeenCalledWith(OPENABLE_TARGET, expect.any(String), true));
  });

  it("names the target in the confirmation prompt", async () => {
    const { button } = await renderConsole();
    fireEvent.click(button);
    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain("Generated");
    expect(dialog.textContent?.toLowerCase()).toContain("open");
  });

  it("never approves without asking", async () => {
    const { button } = await renderConsole();
    fireEvent.click(button);
    await screen.findByRole("dialog");
    expect(openMock.mock.calls.filter((call) => call[2] === true)).toHaveLength(0);
  });

  it("marks console lifecycle errors with the shared status attribute", async () => {
    const { view } = await renderConsole();
    fireEvent.click(view.container.querySelector<HTMLButtonElement>("#load-handoff-button")!);

    await waitFor(() => {
      expect(view.container.querySelector("#status-chip")?.getAttribute("data-status")).toBe("error");
    });
  });

  it("offers a live approval status link to the orchestration step", async () => {
    localStorage.setItem(
      "fantasy-agent-planning-handoff",
      JSON.stringify({
        plan: {
          gameplay_spec: { title: "Status link fixture", target_session_minutes: 10 },
          production_pipeline: { stages: [{ id: "creative_review" }] }
        }
      })
    );
    localStorage.setItem(ORCHESTRATION_SESSION_KEY, "session-status-link");
    localStorage.setItem(ORCHESTRATION_ENGINE_KEY, "godot");
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      if (String(input).includes("/api/orchestration/session-status-link")) {
        return Promise.resolve(Response.json({
          found: true,
          session_id: "session-status-link",
          pending_confirmations: ["creative_review"],
          stages: [{ stage_id: "creative_review", title: "Creative review", status: "awaiting_confirmation", confirmed: false }]
        }));
      }
      return Promise.resolve(Response.json({}));
    }));
    const onNavigateStep = vi.fn();
    render(
      <LocaleThemeProvider>
        <JourneyProvider><FlowConsole onNavigateStep={onNavigateStep} /></JourneyProvider>
      </LocaleThemeProvider>
    );

    const link = await screen.findByRole("button", { name: /orchestrate/i });
    fireEvent.click(link);
    expect(onNavigateStep).toHaveBeenCalledWith("orchestrate");
  });
});
