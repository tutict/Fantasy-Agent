import { installProjectFixture } from "../../test-support/projectBackend";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FlowConsole } from "./FlowConsole";
import { JourneyProvider } from "../shared/journeyContext";
import { LocaleThemeProvider } from "../shared/localeTheme";
import { ORCHESTRATION_ENGINE_KEY, ORCHESTRATION_SESSION_KEY } from "../shared/storage";
import type { OrchestrationSession } from "../shared/types";

/**
 * The plan rail is four panels of input and queues, and it folds: one body on
 * screen, the other three reduced to a title bar. What is pinned here is not
 * how that looks but the three properties that make it safe, none of which a
 * stylesheet can express:
 *
 *   1. exactly one card is open, so the rail cannot drift back to four bodies;
 *   2. clicking a title MOVES the fold rather than adding to it -- two open
 *      cards is the state the rail exists to prevent;
 *   3. the run rail is never folded. It owns the in-flight jobs, and a fold is
 *      the one edit that would tempt somebody into unmounting them. It stays
 *      `<section>`, which is what the check below reads.
 *
 * The gates card is the deliberate exception to (1): it forces itself open
 * while something is waiting on the operator. That rule is NOT covered here --
 * it needs a plan with pending confirmations, which this file's empty fetch
 * cannot produce. It is recorded as an unguarded invariant in the plan
 * document's outstanding debts rather than left looking covered.
 */
function emptyJsonFetch(sessionState: OrchestrationSession = {
  found: false,
  session_id: "session-1",
  pending_confirmations: [],
  stages: []
}) {
  return vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/orchestration/session-1?")) {
      return Promise.resolve(Response.json(sessionState));
    }
    return Promise.resolve(Response.json({}));
  });
}

const HANDOFF_KEY = "fantasy-agent-planning-handoff";

const PLAN_WITH_FUTURE_CONFIRMATIONS = {
  gameplay_spec: { title: "Gate fixture", target_session_minutes: 10 },
  task_breakdown: {
    tasks: [
      { id: "planned-blender", title: "Planned Blender task", status: "pending", requires_confirmation: true },
      { id: "future-review", title: "Future blocked review", status: "blocked", requires_confirmation: true }
    ]
  },
  production_pipeline: {
    stages: [
      { id: "blender_modeling", order: 1, title: "Blender stage", status: "pending", requires_confirmation: true },
      { id: "creative_review", order: 2, title: "Creative review", status: "blocked", requires_confirmation: true }
    ]
  }
};

function storePlanAndSession() {
  localStorage.setItem(HANDOFF_KEY, JSON.stringify({ title: "Gate fixture", plan: PLAN_WITH_FUTURE_CONFIRMATIONS }));
  localStorage.setItem(ORCHESTRATION_SESSION_KEY, "session-1");
  localStorage.setItem(ORCHESTRATION_ENGINE_KEY, "godot");
}

function mountConsole() {
  return render(
    <LocaleThemeProvider>
      <JourneyProvider><FlowConsole /></JourneyProvider>
    </LocaleThemeProvider>
  );
}

function rail(container: HTMLElement, which: "plan" | "run") {
  return container.querySelector<HTMLElement>(`.${which}-rail`)!;
}

function openCards(container: HTMLElement) {
  return Array.from(rail(container, "plan").querySelectorAll<HTMLDetailsElement>("details[open]"));
}

describe("the plan rail's fold", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", emptyJsonFetch());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("opens exactly one card at a time", async () => {
    const view = mountConsole();
    await waitFor(() => expect(rail(view.container, "plan").querySelectorAll("details").length).toBe(4));
    expect(openCards(view.container)).toHaveLength(1);
  });

  it("moves the fold instead of adding to it", async () => {
    const view = mountConsole();
    await waitFor(() => expect(rail(view.container, "plan").querySelectorAll("details").length).toBe(4));
    const summary = rail(view.container, "plan").querySelector<HTMLElement>('[data-panel="correction"] > summary')!;
    fireEvent.click(summary);
    await waitFor(() =>
      expect(openCards(view.container).map((card) => card.getAttribute("data-panel"))).toEqual(["correction"])
    );
  });

  it("never folds the run rail, which owns the in-flight jobs", async () => {
    const view = mountConsole();
    await waitFor(() => expect(rail(view.container, "run").querySelectorAll("section").length).toBeGreaterThan(0));
    expect(rail(view.container, "run").querySelectorAll("details")).toHaveLength(0);
  });

  it("does not count plan-time confirmations as active approvals", async () => {
    storePlanAndSession();
    const view = mountConsole();
    const operator = rail(view.container, "plan").querySelector<HTMLDetailsElement>('[data-panel="operator"]')!;

    await waitFor(() => expect(operator.getAttribute("aria-busy")).toBe("false"));

    expect(operator.open).toBe(false);
    expect(view.container.querySelector("#gate-count")).toBeNull();
    expect(screen.queryByText("Planned Blender task")).toBeNull();
    expect(screen.queryByText("Future blocked review")).toBeNull();
  });

  it("opens for runtime-pending approvals and omits already confirmed stages", async () => {
    storePlanAndSession();
    vi.stubGlobal("fetch", emptyJsonFetch({
      found: true,
      session_id: "session-1",
      status: "running",
      pending_confirmations: ["blender_modeling", "creative_review"],
      stages: [
        {
          stage_id: "blender_modeling",
          title: "Blender approval is waiting",
          status: "awaiting_confirmation",
          confirmed: false
        },
        {
          stage_id: "creative_review",
          title: "Creative review already approved",
          status: "blocked",
          confirmed: true
        }
      ]
    }));
    const view = mountConsole();
    const operator = rail(view.container, "plan").querySelector<HTMLDetailsElement>('[data-panel="operator"]')!;

    await waitFor(() => expect(operator.textContent).toContain("Blender approval is waiting"));

    expect(operator.open).toBe(true);
    expect(view.container.querySelector("#gate-count")?.textContent).toBe("1");
    expect(operator.textContent).toContain("Blender approval is waiting");
    expect(operator.textContent).not.toContain("Creative review already approved");
    expect(operator.textContent).not.toContain("Planned Blender task");
  });
});

installProjectFixture();
