import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JourneyProvider } from "../shared/journeyContext";
import { LocaleThemeProvider } from "../shared/localeTheme";
import { StudioShell, panelHref } from "./StudioShell";

/**
 * The workbench throws on demand.
 *
 * `ErrorBoundary` exists for exactly one situation -- a panel that throws
 * during render -- and no test could produce it before: the real panels are
 * built to degrade rather than crash, so there was nothing to point the guard
 * at. This wraps the real component and turns the throw on for one test, so
 * every other test in this file still gets the genuine workbench.
 *
 * `vi.hoisted` because a `vi.mock` factory runs while the module graph is
 * still loading, before any test body has had the chance to set a flag.
 */
const crash = vi.hoisted(() => ({ workbench: false }));

vi.mock("../workbench/PlanningWorkbench", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../workbench/PlanningWorkbench")>();
  return {
    PlanningWorkbench: function PlanningWorkbench() {
      if (crash.workbench) throw new Error("probe: the workbench panel throws on purpose");
      return <actual.PlanningWorkbench />;
    }
  };
});

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
  crash.workbench = false;
  vi.unstubAllGlobals();
});

function navButton(panel: string) {
  return document.querySelector(`[data-target="${panel}"]`) as HTMLButtonElement;
}

function renderShell() {
  return render(
    <LocaleThemeProvider><JourneyProvider><StudioShell /></JourneyProvider></LocaleThemeProvider>
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

  it("keeps the shell standing when one panel's render throws", () => {
    // The whole reason `ErrorBoundary` is in the tree. These frames stay
    // mounted for the session (§1.1 -- unmounting would abandon an in-flight
    // job's polling), so a panel that throws during render used to be a white
    // window for the rest of it, sidebar and nav included. What has to survive
    // is the shell, and what has to be replaced is only the panel.
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    crash.workbench = true;

    const { container } = renderShell();

    // The frame itself stays: it owns the `data-panel` attribute and the class
    // the visibility rules read, so a boundary that replaced the section
    // instead of its contents would break panel switching as a side effect.
    const frame = container.querySelector('[data-panel="workbench"]');
    expect(frame, "the crashed panel's frame must stay in the tree").not.toBeNull();
    expect(frame?.textContent).toContain("这个面板出错了");

    // And the shell around it is still alive. Switching panels is the part a
    // white window takes away, so it is what proves the rest survived.
    expect(container.querySelector('[data-frame="console"]')).toBeNull();
    fireEvent.click(navButton("console"));
    expect(container.querySelector('[data-frame="console"]')).not.toBeNull();

    logged.mockRestore();
  });

  it("keeps the shell standing when the tool-status payload is malformed", async () => {
    // The boundary's second shape, and the more realistic one: the crash is not
    // a bug in the panel but a contract violation -- a `null` where the backend
    // promised a service object. Every field on `McpService` is optional, so
    // nothing in the type system forbids it, `jsonRequest` casts the payload
    // straight through, and `McpCard` reads `service.status` on its first line.
    // Before the boundary that was a white window.
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ services: [null] }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          })
        )
      )
    );

    renderShell();
    fireEvent.click(navButton("mcp"));

    // The fallback lands where the grid was...
    await waitFor(() => {
      expect(screen.getByText("这个面板出错了")).toBeTruthy();
    });
    // ...and the panel's own chrome survives it, which is why the boundary wraps
    // the grid rather than the whole section: the refresh button is the panel's
    // recovery and has to outlive a crash in the cards.
    expect(document.getElementById("mcp-refresh")).not.toBeNull();

    logged.mockRestore();
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


  it("keeps the six-step journey and its header while the view changes", () => {
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    renderShell();
    for (const label of ["点子", "计划", "编排", "执行", "审阅", "质量"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("还没有项目")).toBeTruthy();
    expect((document.querySelector('[data-journey="idea"]') as HTMLButtonElement).dataset.state).toBe("current");
    fireEvent.click(document.querySelector('[data-journey="execute"]') as HTMLButtonElement);
    expect(screen.getByText("还没有项目")).toBeTruthy();
    expect(screen.getByText("设置")).toBeTruthy();
  });

  it("restores the handed-off project into the journey on a fresh render", () => {
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    localStorage.setItem(
      "fantasy-agent-planning-handoff",
      JSON.stringify({
        plan: {
          gameplay_spec: { title: "Rooftop Chase", target_session_minutes: 12 },
          production_pipeline: { stages: [{ id: "godot_quick_play" }] },
          godot_plan: { engine_version: "Godot 4.6" }
        }
      })
    );
    renderShell();
    expect(document.querySelector(".journey-header h2")?.textContent).toBe("Rooftop Chase");
    expect(screen.getByText("Godot 4.6")).toBeTruthy();
    const activeSteps = [...document.querySelectorAll(".studio-nav button.active")].map((button) => button.getAttribute("data-journey"));
    expect(activeSteps).toEqual(["plan"]);
    expect(document.querySelector('[data-journey="plan"]')?.getAttribute("aria-current")).toBe("step");

    fireEvent.click(document.querySelector('[data-journey="execute"]') as HTMLButtonElement);
    expect(document.querySelector(".journey-header h2")?.textContent).toBe("Rooftop Chase");
    const viewedSteps = [...document.querySelectorAll(".studio-nav button.active")].map((button) => button.getAttribute("data-journey"));
    expect(viewedSteps).toEqual(["execute"]);
    expect(document.querySelector('[data-journey="plan"]')?.getAttribute("aria-current")).toBe("step");
    expect(document.querySelector('[data-journey="review"]')?.classList.contains("active")).toBe(false);
    expect(document.querySelector('[data-journey="qa"]')?.classList.contains("active")).toBe(false);
  });
  it("writes the theme to the document once, from the provider", async () => {
    renderShell();

    fireEvent.click(document.querySelector('[data-theme-choice="light"]') as HTMLButtonElement);

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  });
});
