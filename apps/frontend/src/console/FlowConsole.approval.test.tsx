import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JourneyProvider } from "../shared/journeyContext";
import { FlowConsole } from "./FlowConsole";
import { LocaleThemeProvider } from "../shared/localeTheme";

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
});
