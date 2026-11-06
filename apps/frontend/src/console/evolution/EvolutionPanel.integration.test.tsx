import { installProjectFixture } from "../../../test-support/projectBackend";
import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { LocaleThemeProvider } from "../../shared/localeTheme";
import { JourneyProvider } from "../../shared/journeyContext";
import { FlowConsole } from "../FlowConsole";

afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals(); });

it("keeps the visited evolution work mounted when leaving quality", () => {
  localStorage.clear();
  vi.stubGlobal("fetch", async () => ({ ok: true, json: async () => ({ targets: [] }) }));
  const view = (step: "qa" | "review") => (
    <LocaleThemeProvider><JourneyProvider><FlowConsole journeyStep={step} /></JourneyProvider></LocaleThemeProvider>
  );
  const { container, rerender } = render(view("qa"));
  const panel = container.querySelector('[data-panel="evolution"]');
  expect(panel).not.toBeNull();
  rerender(view("review"));
  expect(container.querySelector('[data-panel="evolution"]')).toBe(panel);
  expect(panel?.parentElement?.hasAttribute("hidden")).toBe(true);
});

installProjectFixture();
