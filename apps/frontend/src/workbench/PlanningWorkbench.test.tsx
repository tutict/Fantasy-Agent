import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PlanningWorkbench } from "./PlanningWorkbench";

/**
 * These cover the behaviour that the retired static page got right by accident
 * and that a rewrite can silently drop: the interview has to advance one
 * question per answer, no plan tool may run before the idea is confirmed, and
 * a finished plan has to be handed to the flow console through localStorage.
 */

interface CapturedCall {
  url: string;
  body: Record<string, unknown>;
}

let calls: CapturedCall[] = [];
let responder: (url: string, body: Record<string, unknown>) => unknown;

const HANDOFF_KEY = "fantasy-agent-planning-handoff";

const SPEC = {
  title: "Neon Rooftops",
  logline: "Deliver packages across a collapsing skyline.",
  core_verbs: ["wall-run", "vault", "slide"],
  design_pillars: ["momentum", "readable risk", "short retries"],
  core_loop: [{ order: 1, action: "wall-run", player_decision: "commit or drop", feedback: "speed" }],
  systems: [{ name: "momentum", purpose: "reward uninterrupted routes" }],
  level_beats: [{ name: "warmup", duration_minutes: 2, gameplay_focus: "learn the verbs" }],
  failure_states: ["fall", "timeout"],
  asset_needs: ["rooftop kit"],
  qa_focus: ["frame time"],
  win_state: "reach the drop zone",
  target_session_minutes: 10
};

function planPayload() {
  return {
    gameplay_spec: SPEC,
    production_pipeline: {
      project_name: "neon-rooftops",
      goal: "ship a 10 minute slice",
      current_stage: "godot_quick_play",
      next_stage: "comfyui_visual_production",
      stages: [
        {
          id: "godot_quick_play",
          order: 1,
          title: "Godot quick play",
          title_i18n: { "zh-CN": "Godot 快速试玩" },
          status: "ready",
          purpose: "assemble the playable greybox",
          owner_agent: "godot",
          requires_confirmation: true,
          mcp_tools: ["godot-mcp"]
        }
      ]
    },
    task_breakdown: {
      goal: "produce the vertical slice",
      recommended_next_task: "assemble godot scene",
      tasks: [
        {
          id: "t1",
          title: "Assemble scene",
          title_i18n: { "zh-CN": "组装场景" },
          purpose: "get boots on the roof",
          status: "ready",
          agent: "godot",
          depends_on: ["t0"],
          side_effects: ["writes scene file"]
        }
      ]
    },
    gdd: { markdown: "# Neon Rooftops", markdown_by_locale: { en: "# Neon Rooftops", "zh-CN": "# 霓虹屋顶" } },
    qa_plan: { smoke_tests: ["boots to menu"], playability_checks: ["loop closes"], failure_checks: ["fall respawns"], packaging_checks: ["exports"] },
    godot_plan: { scenes: ["Main.tscn"], scripts: ["player.gd"], automation_steps: ["import"] },
    unreal_plan: { maps: ["Rooftop"], gameplay_classes: ["BP_Courier"], automation_steps: ["ingest"] },
    blender_plan: { jobs: [{ asset_name: "rooftop", purpose: "greybox", export_path: "out/rooftop.fbx" }] },
    comfyui_plan: { jobs: [{ job_id: "j1", gameplay_constraint: "readable hazards", workflow_template: "greybox" }] },
    creative_review: {
      approval_gate: "user must approve assets",
      items: [{ asset_id: "a1", source: "comfyui", approval_status: "pending", asset_path: "out/a1.png" }],
      art_direction: { user_review_questions: ["Is the hazard readable?"] }
    },
    next_actions: ["review the creative queue"]
  };
}

function planEnvelope() {
  const plan = planPayload();
  return {
    structuredContent: {
      kind: "director_build_plan",
      plan,
      task_breakdown: plan.task_breakdown,
      production_pipeline: plan.production_pipeline
    },
    content: [{ type: "text", text: "Generated full production plan: Neon Rooftops." }],
    _meta: { toolName: "generate_game_production_plan", plan, activePanel: "overview" }
  };
}

function seedEnvelope() {
  const seed = {
    source: "idea-discovery-agent",
    schema_version: "0.1",
    raw_idea: "rooftop parkour courier",
    player_fantasy: "a courier who never touches the ground",
    emotional_target: "mastery",
    core_action: "wall-run across collapsing rooftops",
    tension_source: "the skyline is collapsing",
    must_keep: ["wall-run"],
    can_cut: ["open world"],
    reference_feel: "readable greybox",
    playable_loop_candidate: "run, vault, deliver",
    constraints: [],
    open_questions: [],
    next_prompt: "Create a 10-minute Godot 4 playable prototype from this idea seed."
  };
  return {
    structuredContent: { kind: "idea_seed", idea_seed: seed, prompt_request: { prompt: seed.next_prompt } },
    content: [{ type: "text", text: "Extracted an IdeaSeed." }],
    _meta: { toolName: "extract_idea_seed", ideaSeed: seed, activePanel: "overview" }
  };
}

beforeEach(() => {
  calls = [];
  responder = () => ({});
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
      calls.push({ url, body });
      const payload = responder(url, body) ?? {};
      return Promise.resolve(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );
    })
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function panelTab(panel: string) {
  return document.querySelector(`[data-panel-button="${panel}"]`) as HTMLButtonElement;
}

function chatBox() {
  return screen.getByPlaceholderText("Type your idea or reply to AI...") as HTMLTextAreaElement;
}

function send(text: string) {
  fireEvent.change(chatBox(), { target: { value: text } });
  fireEvent.click(screen.getByText("Initial idea"));
}

function fillSeed() {
  const set = (id: string, value: string) => {
    const node = document.querySelector(`#${id}`) as HTMLTextAreaElement;
    fireEvent.change(node, { target: { value } });
  };
  set("wb-player-fantasy", "a courier who never touches the ground");
  set("wb-core-action", "wall-run across collapsing rooftops");
  set("wb-tension-source", "the skyline is collapsing");
}

function confirmButton() {
  return screen.getByText("Confirm Idea").closest("button") as HTMLButtonElement;
}

function toolButton(tool: string) {
  return document.querySelector(`[data-tool="${tool}"]`) as HTMLButtonElement;
}

describe("planning workbench interview", () => {
  it("treats the first message as the idea and the next ones as answers", async () => {
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    send("a courier");
    send("wall-run");

    const thread = screen.getByTestId("discovery-thread");
    expect(thread.textContent).toContain("rooftop parkour courier");
    expect(thread.textContent).toContain("a courier");
    expect(thread.textContent).toContain("wall-run");
    // Question 3 of 6: the first message became the idea, the next two answers.
    expect(thread.textContent).toContain("Question 3 of 6");
  });

  it("keeps plan tools locked until the idea is confirmed", async () => {
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fillSeed();

    expect(toolButton("generate_game_production_plan").disabled).toBe(true);
    fireEvent.click(confirmButton());

    await waitFor(() => expect(toolButton("generate_game_production_plan").disabled).toBe(false));
  });

  it("exposes every backend planning tool, not just the three the old page wired", () => {
    render(<PlanningWorkbench />);
    const wired = Array.from(document.querySelectorAll("[data-tool]")).map((node) =>
      node.getAttribute("data-tool")
    );
    expect(wired).toEqual([
      "generate_game_production_plan",
      "decompose_production_tasks",
      "prepare_production_pipeline",
      "render_gdd",
      "prepare_godot_plan",
      "prepare_unreal_plan",
      "prepare_blender_plan",
      "prepare_comfyui_plan",
      "prepare_creative_review_plan",
      "prepare_qa_plan"
    ]);
  });
});

describe("planning workbench tool calls", () => {
  it("posts the interview answers when extracting an idea seed", async () => {
    responder = () => seedEnvelope();
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    send("a courier");

    fireEvent.click(screen.getByText("Extract idea"));

    await waitFor(() =>
      expect(calls.some((call) => call.url === "/api/tools/extract_idea_seed")).toBe(true)
    );
    const call = calls.find((entry) => entry.url === "/api/tools/extract_idea_seed");
    expect(call?.body.raw_idea).toBe("rooftop parkour courier");
    expect(call?.body.answers).toHaveLength(1);
  });

  it("fills the editor from a returned seed", async () => {
    responder = () => seedEnvelope();
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fireEvent.click(screen.getByText("Extract idea"));

    await waitFor(() =>
      expect((document.querySelector("#wb-core-action") as HTMLTextAreaElement).value).toBe(
        "wall-run across collapsing rooftops"
      )
    );
  });

  it("generates a plan and hands it to the flow console", async () => {
    responder = (url) => (url.includes("generate_game_production_plan") ? planEnvelope() : {});
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fillSeed();
    fireEvent.click(confirmButton());

    await waitFor(() => expect(toolButton("generate_game_production_plan").disabled).toBe(false));
    fireEvent.click(toolButton("generate_game_production_plan"));

    await waitFor(() => expect(localStorage.getItem(HANDOFF_KEY)).not.toBeNull());
    const handoff = JSON.parse(localStorage.getItem(HANDOFF_KEY) ?? "{}");
    expect(handoff.source).toBe("planning-workbench");
    expect(handoff.title).toBe("Neon Rooftops");
    expect(handoff.plan.gameplay_spec.title).toBe("Neon Rooftops");
    expect(screen.getByTestId("plan-title").textContent).toBe("Neon Rooftops");
  });

  it("renders the pipeline and tasks returned by the backend", async () => {
    responder = (url) => (url.includes("generate_game_production_plan") ? planEnvelope() : {});
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fillSeed();
    fireEvent.click(confirmButton());
    await waitFor(() => expect(toolButton("generate_game_production_plan").disabled).toBe(false));
    fireEvent.click(toolButton("generate_game_production_plan"));

    await waitFor(() => expect(screen.getByTestId("plan-title").textContent).toBe("Neon Rooftops"));

    fireEvent.click(panelTab("pipeline"));
    await waitFor(() => expect(document.body.textContent).toContain("Godot quick play"));
    expect(document.body.textContent).toContain("Confirmation required");

    fireEvent.click(panelTab("tasks"));
    await waitFor(() => expect(document.body.textContent).toContain("Assemble scene"));
    expect(document.body.textContent).toContain("Dependencies: t0");
    expect(document.body.textContent).toContain("Tool operations: writes scene file");
  });

  it("shows the GDD for the active locale", async () => {
    responder = (url) => (url.includes("generate_game_production_plan") ? planEnvelope() : {});
    const { container } = render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fillSeed();
    fireEvent.click(confirmButton());
    await waitFor(() => expect(toolButton("generate_game_production_plan").disabled).toBe(false));
    fireEvent.click(toolButton("generate_game_production_plan"));
    await waitFor(() => expect(screen.getByTestId("plan-title").textContent).toBe("Neon Rooftops"));

    fireEvent.click(panelTab("gdd"));
    await waitFor(() => expect(container.textContent).toContain("Neon Rooftops"));

    fireEvent.click(document.querySelector('[data-locale="zh-CN"]') as HTMLButtonElement);
    fireEvent.click(panelTab("gdd"));
    await waitFor(() => expect(container.textContent).toContain("霓虹屋顶"));
  });

  it("switches to the panel a tool names", async () => {
    responder = (url) =>
      url.includes("prepare_qa_plan")
        ? {
            structuredContent: { kind: "qa_plan", qa_plan: { smoke_tests: ["boots"] } },
            _meta: { toolName: "prepare_qa_plan", activePanel: "qa" }
          }
        : {};
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fillSeed();
    fireEvent.click(confirmButton());
    await waitFor(() => expect(toolButton("prepare_qa_plan").disabled).toBe(false));

    fireEvent.click(toolButton("prepare_qa_plan"));
    await waitFor(() =>
      expect(document.querySelector("[data-panel]")?.getAttribute("data-panel")).toBe("qa")
    );
    expect(document.body.textContent).toContain("boots");
  });

  it("surfaces backend failures instead of swallowing them", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ detail: "prompt 至少需要 8 个字符" }), {
            status: 422,
            headers: { "Content-Type": "application/json" }
          })
        )
      )
    );
    render(<PlanningWorkbench />);
    send("rooftop parkour courier");
    fillSeed();
    fireEvent.click(confirmButton());
    await waitFor(() => expect(toolButton("prepare_qa_plan").disabled).toBe(false));

    fireEvent.click(toolButton("prepare_qa_plan"));
    await waitFor(() => expect(document.body.textContent).toContain("prompt 至少需要 8 个字符"));
    expect(screen.getByTestId("status-chip").className).toContain("error");
  });
});
