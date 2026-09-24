import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { studioI18n, makeTranslator } from "../shared/i18n";
import { HANDOFF_KEY } from "../shared/storage";
import type { DirectorBuildPlan, OrchestrationSession } from "../shared/types";
import { JourneyProvider } from "../shared/journeyContext";
import { OrchestrationBoard } from "./OrchestrationBoard";

/**
 * Behaviour of the board, with `fetch` stubbed at the boundary the component
 * actually uses (there is no server in jsdom, and a mocked `api.ts` would test
 * the mock).
 *
 * The assertions it exists for are the two that are easy to get wrong and
 * invisible when wrong:
 *
 *   - **the plan travels with the run request.** The board renders one plan;
 *     posting a prompt instead would let the server advance a different one and
 *     nothing on screen would say so.
 *   - **no approval is sent that a person did not give.** `confirm_stages` and
 *     `rewind_stage` are user actions; a defaulted value would take the backend
 *     gate off, which is the one thing AGENTS.md is explicit about.
 */

const t = makeTranslator("en", studioI18n);

const PIPELINE = {
  project_name: "neon-rooftops",
  goal: "ship a 10 minute slice",
  stages: [
    {
      id: "blender_modeling" as const,
      order: 1,
      title: "Blender modelling",
      status: "pending" as const,
      purpose: "cut the hero props",
      owner_agent: "blender-worker" as const,
      kind: "agent" as const,
      depends_on: ["gameplay_orchestration" as const],
      mcp_tools: ["blender-mcp"],
      quality_gates: ["props load under budget"],
      risks: ["approval blocks the import"],
      requires_confirmation: true
    },
    {
      id: "creative_review" as const,
      order: 2,
      title: "Creative review",
      status: "blocked" as const,
      purpose: "a person signs off the look",
      owner_agent: "creative-review-agent" as const,
      kind: "human" as const,
      requires_confirmation: true
    }
  ]
};

/**
 * A plan shaped like the shared decoder expects.
 *
 * `gameplay_spec` is not decoration: `decodeStoredHandoff` uses it to tell a
 * real plan from an unreadable blob, so a fixture without one decodes as
 * `invalid` and the board renders its empty state. That is a feature of the
 * decoder, and it is why this fixture carries it.
 */
type Stage = (typeof PIPELINE)["stages"][number];

function handedOffPlan(stages: Stage[] = [...PIPELINE.stages]): DirectorBuildPlan {
  return {
    gameplay_spec: { title: "Neon Rooftops" },
    production_pipeline: { ...PIPELINE, stages }
  } as DirectorBuildPlan;
}

function handoff(stages: Stage[] = [...PIPELINE.stages]): string {
  return JSON.stringify({
    schemaVersion: "0.1",
    source: "test",
    title: "Neon Rooftops",
    plan: handedOffPlan(stages)
  });
}

const TRANSLATION = { blender_modeling: ["blender", "blender_validate"], creative_review: [] };

function sessionPayload(overrides: Partial<OrchestrationSession> = {}): OrchestrationSession {
  return {
    session_id: "orch-test",
    status: "error",
    error: "gameplay_orchestration failed",
    pending_confirmations: ["blender_modeling"],
    confirmed: [],
    stage_translation: TRANSLATION,
    stages: [
      {
        stage_id: "blender_modeling",
        order: 1,
        title: "Blender modelling",
        kind: "agent",
        plan_status: "pending",
        status: "awaiting_confirmation",
        requires_confirmation: true,
        confirmed: false,
        purpose: "cut the hero props",
        owner_agent: "blender-worker",
        depends_on: [],
        mcp_tools: ["blender-mcp"],
        quality_gates: ["props load under budget"],
        risks: ["approval blocks the import"],
        exit_checks: [],
        executor_stages: ["blender", "blender_validate"],
        tool_calls: 3,
        refusals: ["blender_launch"],
        checks: [],
        answer: ""
      },
      {
        stage_id: "creative_review",
        order: 2,
        title: "Creative review",
        kind: "human",
        plan_status: "blocked",
        status: "blocked",
        requires_confirmation: true,
        confirmed: false,
        executor_stages: [],
        tool_calls: 0,
        refusals: [],
        checks: [],
        detail: "",
        answer: ""
      }
    ],
    ...overrides
  };
}

type Call = { url: string; body: Record<string, unknown> | null };

let calls: Call[];

function stubFetch(handler: (url: string, body: Record<string, unknown> | null) => unknown) {
  calls = [];
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : null;
    calls.push({ url, body });
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(handler(url, body))
    });
  });
}

function board(overrides: Partial<Parameters<typeof OrchestrationBoard>[0]> = {}) {
  return (
    <JourneyProvider><OrchestrationBoard
      active
      locale="en"
      t={t}
      onOpenConsole={() => undefined}
      {...overrides}
     /></JourneyProvider>
  );
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(HANDOFF_KEY, handoff());
  stubFetch(() => ({ found: false, stage_translation: TRANSLATION, stages: [] }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("before a run", () => {
  it("renders the handed-off plan's stages, in plan order", async () => {
    render(board());

    // The mount also reads the session, which resolves asynchronously; wait for
    // the cards rather than asserting on the first paint.
    await waitFor(() => expect(document.querySelectorAll(".or-card")).toHaveLength(2));
    const ids = [...document.querySelectorAll(".or-card")].map((node) =>
      node.getAttribute("data-stage")
    );
    expect(ids).toEqual(["blender_modeling", "creative_review"]);
  });

  it("shows the plan-time status as context, not as the runtime one", () => {
    render(board());

    const card = document.querySelector('[data-stage="creative_review"]')!;
    expect(card.getAttribute("data-plan-status")).toBe("blocked");
    // Nothing has been reached, so the runtime status is `pending` even though
    // the plan says `blocked`.
    expect(card.getAttribute("data-status")).toBe("pending");
  });

  it("renders the whole field set the plan carries", async () => {
    // The field-coverage assertions used to live in the console's panel tests
    // and in the workbench's pipeline tab. Both renderers are gone; this is the
    // one place a stage is drawn now, so this is where they belong.
    render(board());
    await waitFor(() => expect(document.querySelectorAll(".or-card")).toHaveLength(2));

    expect(screen.getByText("Blender modelling")).toBeTruthy();
    expect(screen.getByText("cut the hero props")).toBeTruthy();
    expect(screen.getByText("Role: blender-worker")).toBeTruthy();
    expect(screen.getByText("Tools: blender-mcp")).toBeTruthy();
    expect(screen.getByText("Quality gates: props load under budget")).toBeTruthy();
    expect(screen.getByText("Risks: approval blocks the import")).toBeTruthy();
    // The one field the orchestrator actually gates on, which no panel rendered
    // before this one.
    expect(screen.getByText("Depends on: gameplay_orchestration")).toBeTruthy();
    expect(screen.getByText("Human gate")).toBeTruthy();
  });

  it("says there is no plan instead of rendering an empty board", () => {
    localStorage.clear();
    render(board());

    expect(screen.getByText(/No plan yet/)).toBeTruthy();
  });

  it("re-reads the handoff when it becomes the visible view", async () => {
    // The shell mounts a view once and keeps it mounted, so a mount-time read
    // alone would show the plan as it was the first time this view was opened.
    const { rerender } = render(board({ active: true }));
    expect(document.querySelectorAll(".or-card")).toHaveLength(2);

    localStorage.setItem(HANDOFF_KEY, handoff([PIPELINE.stages[0]]));

    rerender(board({ active: false }));
    rerender(board({ active: true }));

    await waitFor(() => expect(document.querySelectorAll(".or-card")).toHaveLength(1));
  });
});

describe("running a pass", () => {
  it("posts the plan it is showing, not a prompt", async () => {
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() => expect(calls.some((call) => call.url.includes("/api/orchestration/run"))).toBe(true));
    const run = calls.find((call) => call.url.includes("/api/orchestration/run"))!;

    expect(run.body?.plan).toMatchObject({ production_pipeline: expect.any(Object) });
    expect(run.body).not.toHaveProperty("prompt");
    expect(run.body).not.toHaveProperty("engine_version");
  });

  it("sends no approval and no rework that nobody asked for", async () => {
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() => expect(calls.some((call) => call.url.includes("/api/orchestration/run"))).toBe(true));
    const run = calls.find((call) => call.url.includes("/api/orchestration/run"))!;
    expect(run.body?.confirm_stages).toEqual([]);
    expect(run.body?.rewind_stage).toBe("");
    expect(run.body?.allow_write).toBe(false);
    expect(run.body?.allow_execute).toBe(false);
  });

  it("sends only the approval the operator clicked", async () => {
    render(board());

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() => expect(calls.some((call) => call.url.includes("/api/orchestration/run"))).toBe(true));
    const run = calls.find((call) => call.url.includes("/api/orchestration/run"))!;
    expect(run.body?.confirm_stages).toEqual(["blender_modeling"]);
  });

  it("sends the rework target from the card's own button", async () => {
    stubFetch(() => sessionPayload());
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));
    await waitFor(() => expect(document.querySelectorAll(".or-card")).toHaveLength(2));

    const rework = document.querySelector('[data-rework="blender_modeling"]') as HTMLButtonElement;
    fireEvent.click(rework);

    await waitFor(() =>
      expect(calls.filter((call) => call.url.includes("/api/orchestration/run"))).toHaveLength(2)
    );
    const second = calls.filter((call) => call.url.includes("/api/orchestration/run"))[1];
    expect(second.body?.rewind_stage).toBe("blender_modeling");
  });

  it("reports a failed pass without losing the cards", async () => {
    stubFetch(() => sessionPayload());
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() => expect(screen.getByText(/gameplay_orchestration failed/)).toBeTruthy());
    expect(document.querySelectorAll(".or-card")).toHaveLength(2);
    // The runtime statuses arrived with the payload, so the card is not blank.
    expect(
      document.querySelector('[data-stage="blender_modeling"]')?.getAttribute("data-status")
    ).toBe("awaiting_confirmation");
  });

  it("surfaces a transport failure instead of rendering nothing", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new Error("offline")));
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() => expect(screen.getByText(/offline/)).toBeTruthy());
  });
});

describe("after a run", () => {
  beforeEach(() => stubFetch(() => sessionPayload()));

  it("shows the runtime status and the exit detail the plan could not", async () => {
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() =>
      expect(
        document.querySelector('[data-stage="blender_modeling"]')?.getAttribute("data-status")
      ).toBe("awaiting_confirmation")
    );
    expect(screen.getByText(/Waiting for approval/)).toBeTruthy();
    expect(screen.getByText(/Tool calls: 3/)).toBeTruthy();
    expect(screen.getByText(/Refused: blender_launch/)).toBeTruthy();
  });

  it("lists the stages still waiting on a person", async () => {
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));

    await waitFor(() => expect(screen.getByText(/1 stage\(s\) waiting for your approval/)).toBeTruthy());
  });

  it("offers no approve button on the human gate", async () => {
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));
    await waitFor(() => expect(document.querySelectorAll(".or-card")).toHaveLength(2));

    const gate = document.querySelector('[data-stage="creative_review"]')!;
    expect(gate.querySelector('[data-approve]')).toBeNull();
    expect(gate.querySelector('[data-drilldown]')).toBeNull();
    expect(gate.textContent).toContain("Creative review");
  });

  it("drills from a card into the execution steps behind it", async () => {
    render(board());
    fireEvent.click(screen.getByRole("button", { name: /^Run$/ }));
    await waitFor(() => expect(document.querySelectorAll(".or-card")).toHaveLength(2));

    const drill = document.querySelector('[data-drilldown="blender_modeling"]') as HTMLButtonElement;
    fireEvent.click(drill);

    const steps = document.querySelector('[data-steps="blender_modeling"]')!;
    expect([...steps.querySelectorAll("li")].map((item) => item.textContent)).toEqual([
      "blender",
      "blender_validate"
    ]);
  });
});

describe("the human gate's route out", () => {
  it("reaches the approval screen from the gate list and from the card", async () => {
    const onOpenConsole = vi.fn();
    stubFetch(() => sessionPayload());
    render(board({ onOpenConsole }));

    // Two entry points, both on the same screen: the summary list above the
    // cards, and the gate's own card. Neither is an approve button -- approving
    // a gate does not make it run.
    const links = screen.getAllByRole("button", { name: "Open the approval screen" });
    links.forEach((link) => fireEvent.click(link));
    expect(onOpenConsole).toHaveBeenCalledTimes(links.length);
    expect(links.length).toBeGreaterThanOrEqual(2);
  });
});
