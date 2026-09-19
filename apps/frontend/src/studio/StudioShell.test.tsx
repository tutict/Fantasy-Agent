import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LocaleThemeProvider } from "../shared/localeTheme";
import { StudioShell, panelHref } from "./StudioShell";

/**
 * F4: the shell hosts its views inline, in one document, under one locale.
 *
 * The console and the workbench used to be separate documents inside iframes.
 * That made three things true that are no longer true: the shell had to pass
 * locale and theme across the frame boundary as query parameters, each view
 * wrote `document.documentElement` for its own `<html>`, and each view stayed
 * mounted forever because an iframe is never unmounted.
 *
 * Removing the frames takes all three away at once, so these tests pin what
 * replaced them rather than the removal itself.
 */

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }))
    )
  );
}

beforeEach(() => {
  localStorage.clear();
  window.history.pushState({}, "", "/");
  stubFetch();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function navButton(panel: string) {
  return document.querySelector(`[data-target="${panel}"]`) as HTMLButtonElement;
}

function renderShell() {
  return render(
    <LocaleThemeProvider>
      <StudioShell />
    </LocaleThemeProvider>
  );
}

describe("the shell hosts its views inline", () => {
  it("renders the active view as a component, not as a frame", () => {
    const { container } = renderShell();

    expect(container.querySelector("iframe")).toBeNull();
    expect(screen.getByTestId("planning-workbench")).toBeTruthy();
  });

  it("does not mount the other view until it is first opened", () => {
    const { container } = renderShell();

    // Both frames used to load at startup, so the console's initial requests
    // were paid for even when nobody looked at it.
    expect(container.querySelector('[data-frame="console"]')).toBeNull();

    fireEvent.click(navButton("console"));

    expect(container.querySelector('[data-frame="console"]')).not.toBeNull();
  });

  it("keeps a visited view mounted once the user switches away", () => {
    const { container } = renderShell();

    fireEvent.click(navButton("console"));
    fireEvent.click(navButton("workbench"));

    const frame = container.querySelector('[data-frame="console"]');
    expect(frame, "unmounting the console would abandon an in-flight job's polling").not.toBeNull();
    expect(frame?.classList.contains("active")).toBe(false);
  });

  it("gives the two hosted views their own URL", () => {
    renderShell();

    fireEvent.click(navButton("console"));
    expect(window.location.pathname).toBe("/web-console");

    fireEvent.click(navButton("workbench"));
    expect(window.location.pathname).toBe("/workbench");
  });

  it("opens the view the URL names", () => {
    window.history.pushState({}, "", "/web-console");

    const { container } = renderShell();

    expect(container.querySelector('[data-frame="console"]')?.classList.contains("active")).toBe(true);
  });
});

describe("the panel URL follows the host that will serve it", () => {
  it("carries the dev server's base, and drops it in production", () => {
    // Vite serves the whole app under `BASE_URL`; FastAPI serves the routes at
    // the root and only the assets live under the base. Prefixing the route in
    // production sent the next reload to `/frontend/web-console`, a 404.
    //
    // `dev` and `base` are injected because `import.meta.env.DEV` is substituted
    // at build time: it is `true` in every test environment, so the production
    // branch is unreachable through the module's own import. That is how the
    // prefix shipped in the first place -- no guard could see the branch.
    expect(panelHref("workbench", true, "/frontend")).toBe("/frontend/workbench");
    expect(panelHref("workbench", false, "/frontend")).toBe("/workbench");
    expect(panelHref("console", false, "/frontend")).toBe("/web-console");
  });

  it("leaves the route bare when there is no base to carry", () => {
    // `basePath()` strips the trailing slash, so the production default is "".
    expect(panelHref("workbench", true, "")).toBe("/workbench");
  });

  it("has no URL for a panel that is not a whole view", () => {
    expect(panelHref("mcp", true, "/frontend")).toBeNull();
    expect(panelHref("api", false, "/frontend")).toBeNull();
  });
});

describe("locale and theme have one owner", () => {
  it("refuses to render a view outside the provider", () => {
    // A fallback here would restore the old shape -- two truths about the
    // locale -- in whichever view forgot to mount inside the provider.
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<StudioShell />)).toThrow(/LocaleThemeProvider/);

    logged.mockRestore();
  });

  it("carries a locale chosen in the shell into the hosted view", () => {
    renderShell();

    // Both directions, because the starting locale comes from the environment.
    fireEvent.click(document.querySelector('[data-locale="zh-CN"]') as HTMLButtonElement);

    expect(document.documentElement.lang).toBe("zh-CN");
    // The workbench reads the same provider, so its own strings follow. Before
    // the provider this took a `?locale=` hop through the iframe's `src`.
    expect(screen.getByTestId("planning-workbench").textContent).toContain("策划工作台");

    fireEvent.click(document.querySelector('[data-locale="en"]') as HTMLButtonElement);

    expect(document.documentElement.lang).toBe("en");
  });

  it("writes the theme to the document once, from the provider", async () => {
    renderShell();

    fireEvent.click(document.querySelector('[data-theme-choice="light"]') as HTMLButtonElement);

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  });
});
