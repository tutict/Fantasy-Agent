import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FlowConsole } from "./FlowConsole";
import { LocaleThemeProvider } from "../shared/localeTheme";

/**
 * The approval gate lives in the UI: opening a correction target spawns a
 * local editor, so the backend refuses unless the caller passes
 * `confirmed_side_effects: true` -- and the console may only pass `true` after
 * the human confirmed. These tests mount the real console so that deleting the
 * confirmation (or hardcoding `true` again) fails the suite. `api.test.ts`
 * covers the transport; this covers the decision.
 */
const { openMock } = vi.hoisted(() => ({ openMock: vi.fn() }));

vi.mock("../shared/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../shared/api")>();
  return { ...actual, openManualCorrectionTarget: openMock };
});

// `generated` is openable in the fallback roster, so its button is enabled even
// though no plan is loaded and the targets endpoint is stubbed empty.
const OPENABLE_TARGET = "generated";

function emptyJsonFetch() {
  return vi.fn().mockImplementation(() =>
    Promise.resolve(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }))
  );
}

async function renderConsole() {
  // The console reads locale and theme from the shared provider and throws
  // outside it -- deliberately, so a forgotten provider fails loudly instead of
  // silently growing a second copy of the locale.
  const view = render(
    <LocaleThemeProvider>
      <FlowConsole />
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
    const confirmSpy = vi.fn().mockReturnValue(false);
    vi.stubGlobal("confirm", confirmSpy);

    const { button } = await renderConsole();
    button.click();

    await waitFor(() => expect(confirmSpy).toHaveBeenCalled());
    expect(openMock).not.toHaveBeenCalled();
  });

  it("passes confirmation through only after the user accepts", async () => {
    vi.stubGlobal("confirm", vi.fn().mockReturnValue(true));

    const { button } = await renderConsole();
    button.click();

    await waitFor(() => expect(openMock).toHaveBeenCalled());
    expect(openMock).toHaveBeenCalledWith(OPENABLE_TARGET, expect.any(String), true);
  });

  it("names the target in the confirmation prompt", async () => {
    const confirmSpy = vi.fn().mockReturnValue(false);
    vi.stubGlobal("confirm", confirmSpy);

    const { button } = await renderConsole();
    button.click();

    await waitFor(() => expect(confirmSpy).toHaveBeenCalled());
    const message = confirmSpy.mock.calls[0][0] as string;
    // The prompt has to name what is about to open -- a generic "Are you sure?"
    // would not tell the user which application is being launched.
    expect(message).toContain("Generated");
    expect(message.toLowerCase()).toContain("open");
  });

  it("never approves without asking", async () => {
    const confirmSpy = vi.fn().mockReturnValue(false);
    vi.stubGlobal("confirm", confirmSpy);

    const { button } = await renderConsole();
    button.click();
    await waitFor(() => expect(confirmSpy).toHaveBeenCalled());

    const approvals = openMock.mock.calls.filter((call) => call[2] === true);
    expect(approvals).toHaveLength(0);
  });
});
