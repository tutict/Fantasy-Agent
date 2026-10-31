import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeTranslator, studioI18n } from "./i18n";
import { AssetLibrary } from "../assets/AssetLibrary";
import { FlowConsole } from "../console/FlowConsole";
import { JourneyProvider } from "./journeyContext";
import { LocaleThemeProvider } from "./localeTheme";
import { OrchestrationBoard } from "../orchestration/OrchestrationBoard";
import { PlanningWorkbench } from "../workbench/PlanningWorkbench";
import { getAssetLibrary } from "./api";
import { ORCHESTRATION_ENGINE_KEY, ORCHESTRATION_SESSION_KEY } from "./storage";
import type { AssetLibraryOverview } from "./types";

/**
 * Information density, measured at runtime.
 *
 * Every other guard in this repo reads source text, and information density is
 * the one thing source text cannot tell you: a view's weight is not how many
 * selectors it has but how much a reader is asked to take in at once, which is
 * a property of the rendered tree. `ui_metrics.py` can count `grid-template`
 * values; it cannot count "eleven panels competing for one screen".
 *
 * So each view is mounted in jsdom and measured on four axes:
 *
 *   sections   the blocks competing for attention -- the console redesign's
 *              whole subject
 *   controls   things the reader might press, which is the real cost of a busy
 *              screen: an unpressed button is still a decision offered
 *   headings   the labels the reader scans for "where am I"
 *   chars      visible text, as a proxy for how much there is to read
 *
 * The budgets are MEASURED, not aspirational: each one is what the view renders
 * on the day it was added. A budget you cannot meet today is a plan, and plans
 * in a guard file go stale quietly -- they fail on the first run, get raised to
 * whatever the code does, and stop meaning anything. Raise one of these only by
 * changing the view on purpose, and say why in the entry's reason.
 *
 * What this is for: a twelfth `<section>` in the console's right rail used to
 * be free. It is the regression `FE15-1` mutates in.
 */

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return { ...actual, getAssetLibrary: vi.fn(), ingestAsset: vi.fn(), removeAsset: vi.fn() };
});

function jsonFetch() {
  return vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/tools/extract_idea_seed")) {
      return Promise.resolve(Response.json({
        structuredContent: {
          kind: "idea_seed",
          idea_seed: DENSITY_SEED,
          prompt_request: { prompt: DENSITY_SEED.next_prompt }
        },
        content: [{ type: "text", text: "Extracted the measured rooftop idea." }],
        _meta: { toolName: "extract_idea_seed", ideaSeed: DENSITY_SEED, activePanel: "overview" }
      }));
    }
    if (url.includes("/api/tools/generate_game_production_plan")) {
      return Promise.resolve(Response.json({
        structuredContent: {
          kind: "director_build_plan",
          plan: DENSITY_PLAN,
          task_breakdown: DENSITY_PLAN.task_breakdown,
          production_pipeline: DENSITY_PLAN.production_pipeline
        },
        content: [{ type: "text", text: "Generated the measured rooftop plan." }],
        _meta: { toolName: "generate_game_production_plan", plan: DENSITY_PLAN }
      }));
    }
    if (url.includes("/api/orchestration/")) {
      const waitingForApproval = url.includes("density-approval-session");
      return Promise.resolve(Response.json({
        found: true,
        session_id: "density-session",
        status: waitingForApproval ? "running" : "done",
        pending_confirmations: waitingForApproval ? ["creative_review"] : [],
        pending_human_gates: [],
        confirmed: [],
        stages: [
          {
            stage_id: waitingForApproval ? "creative_review" : "density-stage",
            order: waitingForApproval ? 4 : 1,
            title: waitingForApproval ? "Measured Creative Review approval" : "Measured runtime stage",
            kind: waitingForApproval ? "human" : "agent",
            plan_status: "ready",
            requires_confirmation: waitingForApproval,
            confirmed: false,
            status: waitingForApproval ? "awaiting_confirmation" : "done",
            executor_stages: []
          }
        ],
        stage_translation: {}
      }));
    }
    return Promise.resolve(Response.json({}));
  });
}

const DENSITY_SEED = {
  source: "idea-discovery-agent",
  schema_version: "0.1",
  raw_idea: "rooftop parkour courier",
  player_fantasy: "A courier who never touches the ground.",
  emotional_target: "mastery",
  core_action: "Wall-run across collapsing rooftops.",
  tension_source: "The skyline is collapsing.",
  must_keep: ["wall-run", "deliveries"],
  can_cut: ["open world"],
  reference_feel: "Readable greybox.",
  playable_loop_candidate: "Run, vault, deliver, repeat.",
  constraints: [],
  open_questions: [],
  next_prompt: "Create a 10-minute Godot playable prototype."
};

const DENSITY_PLAN = {
  gameplay_spec: {
    title: "Measured rooftop courier",
    logline: "Deliver one last package across a collapsing skyline.",
    core_verbs: ["wall-run", "vault", "slide"],
    design_pillars: ["momentum", "readable risk", "short retries"],
    core_loop: [{ order: 1, action: "wall-run", player_decision: "commit or drop", feedback: "speed" }],
    systems: [{ name: "momentum", purpose: "reward uninterrupted routes" }],
    level_beats: [{ name: "warmup rooftop", duration_minutes: 2, gameplay_focus: "learn the verbs" }],
    failure_states: ["fall", "timeout"],
    asset_needs: ["rooftop kit"],
    qa_focus: ["route readability"],
    win_state: "deliver the package",
    target_session_minutes: 10
  },
  task_breakdown: {
    goal: "produce the playable rooftop slice",
    recommended_next_task: "assemble the Godot scene",
    tasks: [
      { id: "density-task-1", title: "Assemble scene", purpose: "connect the route", status: "ready", agent: "godot" }
    ]
  },
  production_pipeline: {
    project_name: "measured-rooftop-courier",
    goal: "build a 10-minute playable slice",
    current_stage: "creative_review",
    next_stage: "godot_quick_play",
    stages: [
      { id: "gameplay_orchestration", order: 1, title: "Gameplay plan", status: "complete", requires_confirmation: false },
      { id: "asset_preparation", order: 2, title: "Prepare rooftop assets", status: "ready", requires_confirmation: true },
      { id: "godot_quick_play", order: 3, title: "Godot quick play", status: "pending", requires_confirmation: true },
      { id: "creative_review", order: 4, title: "Creative Review", status: "blocked", requires_confirmation: true, kind: "human" }
    ]
  },
  next_actions: ["review the rooftop landmark"]
};

const EMPTY_LIBRARY: AssetLibraryOverview = {
  entries: [
    {
      id: "asset-density-001",
      name: "Measured library asset",
      kind: "mesh",
      source: "open_source",
      original_name: "crate.glb",
      path: "generated/asset-library/files/asset-density-001/asset-density-001.glb",
      size_bytes: 2048,
      sha256: "a".repeat(64),
      license: "CC0",
      author: "Fixture",
      source_url: "",
      notes: "",
      tags: ["fixture"],
      ingested_at: "2026-10-27T00:00:00Z"
    }
  ],
  generated: [
    {
      asset_id: "measured-generated-prop",
      source: "blender",
      asset_path: "generated/assets/measured-generated-prop.glb",
      gameplay_role: "route landmark",
      status: "pending_user_review",
      sha256: null
    }
  ],
  library_path: "generated/asset-library/library.yaml",
  generated_manifest_path: "generated/asset-approval-manifest.yaml",
  generated_manifest_present: false
};

/**
 * A folded `<details>` keeps its body in the document -- that is the whole
 * reason the plan rail uses one -- so counting DOM nodes would measure a screen
 * the reader cannot see and would record the rail's folded panels as if they
 * were competing for attention. Everything below therefore asks one question
 * first: is this node actually presented? A node under a closed `<details>` is
 * not, and neither is the text inside it.
 *
 * The fold itself still counts as one block: a collapsed card is a title bar,
 * which is a thing the reader scans. What a fold removes is the body.
 */
function presented(container: HTMLElement, el: Element) {
  let node = el.parentElement;
  while (node && node !== container) {
    if (node.tagName === "DETAILS" && !(node as HTMLDetailsElement).open) {
      // A closed disclosure still shows one thing: its summary, which is the
      // fold's handle and therefore still competing for attention -- the
      // heading inside it included. Everything else below is off screen.
      const handle = Array.from(node.children).find((child) => child.tagName === "SUMMARY");
      return Boolean(handle && (el === handle || handle.contains(el)));
    }
    node = node.parentElement;
  }
  return true;
}

function measure(container: HTMLElement) {
  const norm = (text: string) => text.replace(/\s+/g, " ").trim();
  const shown = (selector: string) =>
    Array.from(container.querySelectorAll(selector)).filter((el) => presented(container, el)).length;
  // Text is read node by node rather than off `container.textContent`, which
  // would happily include the three folded panels' worth of words.
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let text = "";
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    // Concatenated with no separator, which is what `textContent` does: adding
    // a space between two adjacent text nodes inflates the count by one per
    // boundary and measures the joining, not the words.
    if (node.parentElement && presented(container, node.parentElement)) text += node.nodeValue ?? "";
  }
  return {
    sections: shown("section, details"),
    controls: shown("button, input, select, textarea, summary"),
    headings: shown("h1, h2, h3, h4"),
    chars: norm(text).length
  };
}

type Budget = {
  reason: string;
  sections: number;
  controls: number;
  headings: number;
  chars: number;
};

/**
 * Measured by running this file with the entry's budget at zero and reading the
 * numbers back off the failures. Each entry is the ceiling the view presents
 * today, so a twelfth block in the console fails on the run it is added and not
 * on some future day when somebody remembers to look.
 *
 * `sections` counts every block that competes for attention, `<details>` as
 * well as `<section>`: a folded card is a title bar, which is still a thing the
 * reader scans. That is why the console's 15 did not move when its plan rail
 * folded -- what the fold removed was the body, and the body is what the other
 * three axes measure. Read those instead:
 *
 *   control/heading/text  29 / 15 / 2286 before the rail folded
 *                         20 / 10 / 1316 after
 *
 * The console is still the heaviest view by a wide margin, and its `sections`
 * is still the number to bring down. The remaining 15 are the four folded cards
 * plus eleven blocks that are always on; folding the run rail or the centre pane
 * is the next step, and both are gated on `FlowConsole` having tests of its own
 * (see the plan's outstanding debts).
 */
const BUDGETS: Record<string, Budget> = {
  console: {
    reason: "three columns with a live approval in the plan rail; the run rail and centre pane stay visible",
    sections: 15,
    controls: 20,
    headings: 10,
    chars: 1320
  },
  // Fewer blocks than the console but more controls: one composer plus a tool
  // rail, and every tool is a button. A screen can be light on panels and still
  // heavy, which is why controls is its own axis.
  workbench: {
    reason: "one confirmed plan opened on its task list beside the tool rail and seven plan links",
    sections: 2,
    controls: 40,
    headings: 3,
    chars: 1013
  },
  orchestration: {
    reason: "one restored runtime stage on the board",
    sections: 1,
    controls: 5,
    headings: 2,
    chars: 394
  },
  assets: {
    reason: "one ingested library item and one generated review item after the initial read",
    sections: 4,
    controls: 24,
    headings: 4,
    chars: 1159
  }
};

function mount(node: React.ReactElement) {
  return render(
    <LocaleThemeProvider>
      <JourneyProvider>{node}</JourneyProvider>
    </LocaleThemeProvider>
  );
}

async function check(
  name: string,
  node: React.ReactElement,
  ready: (container: HTMLElement) => Promise<void>,
  measuredBudget?: Budget
) {
  const view = mount(node);
  // A DOM-size check passes on the first loading render. Each view supplies a
  // marker that only appears after its representative initial state is ready.
  await ready(view.container);
  const got = measure(view.container);
  const budget = measuredBudget ?? BUDGETS[name]!;
  expect(got, `${name}: ${budget.reason}`).toMatchObject({
    sections: expect.any(Number),
    controls: expect.any(Number),
    headings: expect.any(Number),
    chars: expect.any(Number)
  });
  // Soft, so one axis going over does not hide the other three: a reader
  // raising this budget needs the whole picture, not the first axis that
  // failed. It still fails the test.
  expect.soft(got.sections, `${name} sections over budget`).toBeLessThanOrEqual(budget.sections);
  expect.soft(got.controls, `${name} controls over budget`).toBeLessThanOrEqual(budget.controls);
  expect.soft(got.headings, `${name} headings over budget`).toBeLessThanOrEqual(budget.headings);
  expect.soft(got.chars, `${name} visible text over budget`).toBeLessThanOrEqual(budget.chars);
  return got;
}

describe("information density per view", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", jsonFetch());
    vi.mocked(getAssetLibrary).mockResolvedValue(EMPTY_LIBRARY);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("waits for its view readiness condition before measuring settled content", async () => {
    let finishLoading!: () => void;
    const loading = new Promise<void>((resolve) => {
      finishLoading = resolve;
    });

    function DelayedView() {
      const [ready, setReady] = useState(false);
      useEffect(() => {
        void loading.then(() => setReady(true));
      }, []);
      return (
        <section>
          {Array.from({ length: 12 }, (_, index) => <span key={index} aria-hidden="true" />)}
          {ready ? <p>Loaded sample marker</p> : null}
        </section>
      );
    }

    const got = await check(
      "delayed readiness fixture",
      <DelayedView />,
      async (container) => {
        expect(container.querySelectorAll("*").length).toBeGreaterThan(10);
        finishLoading();
        await waitFor(() => expect(container.textContent).toContain("Loaded sample marker"));
      },
      { reason: "delayed readiness fixture", sections: 1, controls: 0, headings: 0, chars: 80 }
    );

    expect(got.chars).toBeGreaterThan(0);
  });

  it("keeps the flow console inside its budget", async () => {
    localStorage.setItem("fantasy-agent-planning-handoff", JSON.stringify({ title: "Measured console plan", plan: DENSITY_PLAN }));
    localStorage.setItem(ORCHESTRATION_SESSION_KEY, "density-approval-session");
    localStorage.setItem(ORCHESTRATION_ENGINE_KEY, "godot");
    await check("console", <FlowConsole />, async (container) => {
      await waitFor(() => {
        expect(container.querySelector("#plan-title")?.textContent).toBe("Measured rooftop courier");
        expect(container.querySelector('[data-panel="operator"]')?.getAttribute("aria-busy")).toBe("false");
        expect(container.querySelector("#gate-summary")?.textContent).toContain("Measured Creative Review approval");
      });
    });
  });

  it("keeps the planning workbench inside its budget", async () => {
    await check("workbench", <PlanningWorkbench />, async (container) => {
      const composer = container.querySelector<HTMLTextAreaElement>(".wb-composer textarea");
      expect(composer).not.toBeNull();
      fireEvent.change(composer!, { target: { value: "rooftop parkour courier" } });
      fireEvent.click(screen.getByText("Send"));
      fireEvent.click(screen.getByText("Extract idea"));
      await waitFor(() =>
        expect((container.querySelector("#wb-core-action") as HTMLTextAreaElement | null)?.value).toBe(
          "Wall-run across collapsing rooftops."
        )
      );
      fireEvent.click(screen.getByText("Confirm Idea"));
      fireEvent.click(container.querySelector('[data-tool="generate_game_production_plan"]')!);
      await waitFor(() => expect(container.querySelector("#overview-content")?.textContent).toContain("collapsing skyline"));
      fireEvent.click(container.querySelector('[data-panel-button="tasks"]')!);
      await waitFor(() => expect(container.querySelector("#tasks-output")?.textContent).toContain("Assemble scene"));
    });
  });

  it("keeps the orchestration board inside its budget", async () => {
    // `active` so the board polls and renders its cards rather than its
    // "wake me when visible" state, which would measure an empty screen.
    await check(
      "orchestration",
      <OrchestrationBoard active locale="en" t={makeTranslator("en", studioI18n)} onOpenConsole={() => {}} />,
      async (container) => {
        await waitFor(() => expect(container.querySelector(".or-card h3")?.textContent).toBe("Measured runtime stage"));
      }
    );
  });

  it("keeps the asset library inside its budget", async () => {
    await check("assets", <AssetLibrary t={makeTranslator("en", studioI18n)} />, async (container) => {
      await waitFor(() => expect(container.querySelector("#as-entry-asset-density-001")).not.toBeNull());
      await waitFor(() => expect(container.querySelector('[data-origin="generated"] strong')?.textContent).toBe("measured-generated-prop"));
    });
  });

  it("keeps step-focused views from mounting their unrelated rails", async () => {
    localStorage.setItem("fantasy-agent-planning-handoff", JSON.stringify({ title: "Step focused plan", plan: DENSITY_PLAN }));
    await check(
      "console review step",
      <FlowConsole journeyStep="review" />,
      async (container) => {
        await waitFor(() => expect(container.querySelector("#plan-title")?.textContent).toBe("Measured rooftop courier"));
        expect(container.querySelector(".plan-rail")).toBeNull();
        expect(container.querySelector(".run-rail")).toBeNull();
        expect(container.querySelector(".center-pane")).not.toBeNull();
      },
      { reason: "review keeps the decision surface as the only work area", sections: 8, controls: 12, headings: 8, chars: 900 }
    );
  });
});
