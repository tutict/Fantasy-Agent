import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  BuildPanel,
  OverviewPanel,
  PipelinePanel,
  QaPanel,
  TasksPanel,
  VisualsPanel
} from "./rendering";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import type { DirectorBuildPlan, PipelineStage } from "../shared/types";

/**
 * Safety net for F1: the six panels the console shares with the planning
 * workbench (overview / pipeline / tasks / build / visuals / qa) are about to
 * be lifted into `shared/panels/` so they exist once instead of twice. This
 * file pins what the console half renders *today* so the lift cannot quietly
 * change it, and names the fields the console half does not render yet but
 * will once the two implementations are merged into the union field set.
 *
 * Why the console side needs its own net: workbench coverage rides on a heavy
 * interaction chain (send -> fillSeed -> confirmButton -> toolButton ->
 * panelTab), so `PlanningWorkbench.test.tsx` would stay green even if the lift
 * broke this entry point. Before this file the console had two panel
 * assertions total, both about the pipeline panel.
 *
 * Every assertion goes through `consoleI18n`, so a panel that reaches for a
 * key only `workbenchI18n` defines renders the raw key name (see
 * `makeTranslator`'s `|| key` fallback) and fails here instead of shipping.
 */

const t = makeTranslator("en", consoleI18n);

afterEach(() => cleanup());

function stage(overrides: Partial<PipelineStage> = {}): PipelineStage {
  return {
    id: "godot_quick_play",
    order: 1,
    title: "Godot quick play",
    status: "ready",
    purpose: "assemble the playable greybox",
    owner_agent: "godot",
    ...overrides
  };
}

function plan(overrides: Partial<DirectorBuildPlan> = {}): DirectorBuildPlan {
  return {
    production_pipeline: {
      project_name: "neon-rooftops",
      goal: "ship a 10 minute slice",
      current_stage: "godot_quick_play",
      next_stage: "creative_review",
      stages: [stage()]
    },
    ...overrides
  };
}

describe("console overview panel", () => {
  it("renders the union field set, not just the console half", () => {
    render(
      <OverviewPanel
        locale="en"
        t={t}
        plan={plan({
          gameplay_spec: {
            title: "Neon Rooftops",
            target_session_minutes: 10,
            win_state: "reach the drop zone",
            design_pillars: ["momentum", "readable risk"],
            failure_states: ["fall", "timeout"],
            core_loop: [{ action: "wall-run", player_decision: "commit or drop" }],
            systems: [{ name: "momentum", purpose: "reward uninterrupted routes" }],
            // Fields only the workbench used to render; the merged panel shows
            // them here too.
            logline: "Deliver packages across a collapsing skyline.",
            core_verbs: ["wall-run", "vault"],
            asset_needs: ["rooftop kit"],
            qa_focus: ["frame time"]
          },
          next_actions: ["run the Godot greybox"]
        })}
      />
    );

    // Console-original fields.
    expect(screen.getByText("Target session")).toBeTruthy();
    expect(screen.getByText("reach the drop zone")).toBeTruthy();
    expect(screen.getByText("Design pillars")).toBeTruthy();
    expect(screen.getByText("Systems")).toBeTruthy();
    expect(screen.getByText("Next actions")).toBeTruthy();
    expect(screen.getByText("run the Godot greybox")).toBeTruthy();
    expect(screen.getByText("timeout")).toBeTruthy();
    // The loop step is one string, action then decision, as the workbench had
    // it; the console used to break the pair across two lines.
    expect(screen.getByText("wall-run -- commit or drop")).toBeTruthy();

    // Workbench-original fields, now part of the same panel.
    expect(screen.getByText("Logline")).toBeTruthy();
    expect(screen.getByText("Deliver packages across a collapsing skyline.")).toBeTruthy();
    expect(screen.getByText("Core verbs")).toBeTruthy();
    expect(screen.getByText("vault")).toBeTruthy();
    expect(screen.getByText("Asset needs")).toBeTruthy();
    expect(screen.getByText("rooftop kit")).toBeTruthy();
    expect(screen.getByText("QA focus")).toBeTruthy();
    expect(screen.getByText("frame time")).toBeTruthy();

    // Every label must come from the console dictionary, not the key name.
    for (const label of ["Logline", "Core verbs", "Pacing", "Asset needs", "QA focus", "Pacing"]) {
      expect(screen.getByText(label), label).toBeTruthy();
    }
  });

  it("renders the shell with placeholders rather than a broken layout when the spec is missing", () => {
    // The two halves disagreed here: the workbench rendered a labelled shell,
    // the console rendered nothing. The union keeps the labelled shell -- an
    // operator can see which fields the plan owes.
    const { container } = render(<OverviewPanel locale="en" t={t} plan={plan()} />);

    expect(container.querySelector("#overview-content")).toBeTruthy();
    expect(screen.getByText("Logline")).toBeTruthy();
    expect(screen.getByText("Target session")).toBeTruthy();
  });

  it("says so when there is no plan and no seed at all", () => {
    render(<OverviewPanel locale="en" t={t} plan={null} />);
    expect(screen.getByText(/No plan yet/)).toBeTruthy();
  });

  it("falls back to the idea seed while the plan is still being captured", () => {
    render(
      <OverviewPanel
        locale="en"
        t={t}
        plan={null}
        seed={{ player_fantasy: "become the courier", core_action: "wall-run" }}
      />
    );

    expect(screen.getByText("Player fantasy")).toBeTruthy();
    expect(screen.getByText("become the courier")).toBeTruthy();
    expect(screen.getByText("Core action")).toBeTruthy();
    expect(screen.getByText("wall-run")).toBeTruthy();
  });
});

describe("console pipeline panel", () => {
  it("marks the human gate and names what the stage waits for", () => {
    render(
      <PipelinePanel
        locale="en"
        t={t}
        plan={plan({
          production_pipeline: {
            project_name: "neon-rooftops",
            goal: "ship a 10 minute slice",
            current_stage: "creative_review",
            next_stage: "asset_integration",
            stages: [
              stage({
                id: "creative_review",
                order: 4,
                title: "Creative review",
                status: "blocked",
                owner_agent: "creative-review-agent",
                kind: "human",
                depends_on: ["comfyui_visual_production", "blender_modeling"],
                requires_confirmation: true
              })
            ]
          }
        })}
      />
    );

    expect(screen.getByText("Human gate")).toBeTruthy();
    expect(screen.getByText("Dependencies: comfyui_visual_production, blender_modeling")).toBeTruthy();
    // Still the executor's own pills, so the gate reads alongside its status.
    expect(screen.getByText("blocked")).toBeTruthy();
    expect(screen.getByText("Owner: creative-review-agent")).toBeTruthy();
  });

  it("shows no gate marker when every stage is an agent stage", () => {
    render(
      <PipelinePanel
        locale="en"
        t={t}
        plan={plan({
          production_pipeline: {
            project_name: "neon-rooftops",
            goal: "ship a 10 minute slice",
            current_stage: "godot_quick_play",
            next_stage: "creative_review",
            stages: [stage()]
          }
        })}
      />
    );

    expect(screen.queryByText("Human gate")).toBeNull();
    expect(screen.queryByText(/^Dependencies:/)).toBeNull();
  });

  it("shows the quality gates and the risks that block the stage", () => {
    render(
      <PipelinePanel
        locale="en"
        t={t}
        plan={plan({
          production_pipeline: {
            project_name: "neon-rooftops",
            goal: "ship a 10 minute slice",
            current_stage: "godot_quick_play",
            next_stage: "creative_review",
            stages: [
              stage({
                quality_gates: ["runs at 60fps", "no missing scripts"],
                risks: ["approval blocks the import"],
                mcp_tools: ["godot-mcp"]
              })
            ]
          }
        })}
      />
    );

    // The merged panel folds each list into one pill, the workbench's shape:
    // the console used to explode them into <ul> bullets.
    expect(screen.getByText("Quality gates: runs at 60fps / no missing scripts")).toBeTruthy();
    expect(screen.getByText("Risks: approval blocks the import")).toBeTruthy();
    expect(screen.getByText("Tools: godot-mcp")).toBeTruthy();
  });

  it("renders the header and no stage rows when the pipeline has no stages", () => {
    const { container } = render(
      <PipelinePanel
        locale="en"
        t={t}
        plan={plan({
          production_pipeline: {
            project_name: "neon-rooftops",
            goal: "ship a 10 minute slice",
            current_stage: "godot_quick_play",
            next_stage: "creative_review",
            stages: []
          }
        })}
      />
    );

    expect(within(container).getByText("neon-rooftops")).toBeTruthy();
    expect(container.querySelectorAll(".stage-row")).toHaveLength(0);
    expect(container.querySelector("#pipeline-output")).toBeTruthy();
  });

  it("names the current and next stage and counts the stages", () => {
    render(
      <PipelinePanel
        locale="en"
        t={t}
        plan={plan({
          production_pipeline: {
            project_name: "neon-rooftops",
            goal: "ship a 10 minute slice",
            current_stage: "godot_quick_play",
            next_stage: "creative_review",
            stages: [stage(), stage({ id: "creative_review", order: 2, title: "Creative review" })]
          }
        })}
      />
    );

    expect(screen.getByText("Current stage: godot_quick_play")).toBeTruthy();
    expect(screen.getByText("Next stage: creative_review")).toBeTruthy();
    expect(screen.getByText("2 stages")).toBeTruthy();
    expect(screen.getByText("Project goal")).toBeTruthy();
  });

  it("says there is no plan rather than rendering an empty board", () => {
    // Was a bare shell with no text; the union keeps the workbench's message,
    // which is the one an operator can act on.
    render(<PipelinePanel locale="en" t={t} plan={{}} />);
    expect(screen.getByText(/No plan yet/)).toBeTruthy();
  });
});

describe("console tasks panel", () => {
  const breakdown = {
    goal: "ship the greybox",
    recommended_next_task: "wire the drop zone",
    tasks: [
      {
        id: "task-1",
        title: "Wire the drop zone",
        purpose: "end the loop",
        status: "ready",
        agent: "godot",
        requires_confirmation: true,
        depends_on: ["task-0"],
        side_effects: ["write project file"]
      }
    ]
  };

  it("renders the goal, the recommended next task and the task's gate pills", () => {
    render(<TasksPanel breakdown={breakdown} locale="en" t={t} />);

    expect(screen.getByText("Recommended")).toBeTruthy();
    expect(screen.getByText("ship the greybox -> wire the drop zone")).toBeTruthy();
    expect(screen.getByText("Wire the drop zone")).toBeTruthy();
    expect(screen.getByText("end the loop")).toBeTruthy();
    expect(screen.getByText("task-1")).toBeTruthy();
    expect(screen.getByText("godot")).toBeTruthy();
    expect(screen.getByText("Confirmation required")).toBeTruthy();
    // Spelled out, not counted: the union keeps the workbench's form, which
    // names what a stage waits on instead of only how many things it waits on.
    expect(screen.getByText("Dependencies: task-0")).toBeTruthy();
    expect(screen.getByText("Tool operations: write project file")).toBeTruthy();
  });

  it("reads the breakdown off the plan when the console did not pass one in", () => {
    // The workbench hands in the whole plan; accepting both shapes is what let
    // the two call sites keep their own.
    render(<TasksPanel plan={plan({ task_breakdown: breakdown })} locale="en" t={t} />);
    expect(screen.getByText("Wire the drop zone")).toBeTruthy();
  });

  it("renders an empty shell when no breakdown has arrived", () => {
    const { container } = render(<TasksPanel locale="en" t={t} />);
    expect(container.querySelector("#tasks-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });
});

describe("console build panel", () => {
  it("renders the Unreal plan when the pipeline has no Godot stage", () => {
    render(
      <BuildPanel
        t={t}
        plan={plan({
          // The engine choice is read off the pipeline, so this branch only
          // opens when no stage claims the Godot quick-play slot.
          production_pipeline: {
            project_name: "neon-rooftops",
            goal: "ship a 10 minute slice",
            current_stage: "unreal_import",
            next_stage: "creative_review",
            stages: [stage({ id: "unreal_import", title: "Unreal import" })]
          },
          unreal_plan: {
            maps: ["L_Rooftops"],
            gameplay_classes: ["AMomentumPlayer"],
            folders: ["/Game/Rooftops"],
            automation_steps: ["run headless import"]
          },
          blender_plan: { jobs: [{ asset_name: "Rooftop kit", purpose: "level art", export_path: "/out/rooftop.fbx" }] }
        })}
      />
    );

    // One titled list per engine, as the workbench had it; the console used to
    // split the same data into four blocks (maps / classes / folders /
    // automation) under its own labels.
    expect(screen.getByText("Unreal")).toBeTruthy();
    expect(screen.getByText("L_Rooftops")).toBeTruthy();
    expect(screen.getByText("AMomentumPlayer")).toBeTruthy();
    expect(screen.getByText("/Game/Rooftops")).toBeTruthy();
    expect(screen.getByText("run headless import")).toBeTruthy();
    expect(screen.getByText("Blender")).toBeTruthy();
    expect(screen.getByText("Rooftop kit / level art / /out/rooftop.fbx")).toBeTruthy();
  });

  it("swaps to the Godot plan when the pipeline does declare a Godot stage", () => {
    render(
      <BuildPanel
        t={t}
        plan={plan({
          godot_plan: {
            engine_version: "Godot 4.5",
            scenes: ["res://main.tscn"],
            scripts: ["res://player.gd"],
            automation_steps: ["run headless verify"]
          },
          unreal_plan: { maps: ["L_Rooftops"] }
        })}
      />
    );

    expect(screen.getByText("Godot")).toBeTruthy();
    expect(screen.getByText("res://main.tscn")).toBeTruthy();
    expect(screen.getByText("res://player.gd")).toBeTruthy();
    expect(screen.getByText("run headless verify")).toBeTruthy();
    // The Unreal branch must not leak in alongside it.
    expect(screen.queryByText("L_Rooftops")).toBeNull();
  });

  it("renders no engine blocks when the plan carries no engine plan", () => {
    const { container } = render(<BuildPanel t={t} plan={plan()} />);
    expect(container.querySelector("#build-output")).toBeTruthy();
    // The shell and its two empty list headers remain, each showing a dash.
    expect(screen.getAllByText("-")).toHaveLength(2);
  });
});

describe("console visuals panel", () => {
  const comfy = {
    jobs: [{ job_id: "job-1", gameplay_constraint: "keep wall-run routes readable", workflow_template: "rooftop-kit" }],
    usage_rules: ["never ship unapproved output"]
  };
  const review = {
    required_user_decisions: ["sign off the rooftop kit"],
    approval_gate: "creative_review",
    items: [
      { asset_id: "rooftop-kit", source: "comfyui", approval_status: "pending", asset_path: "/out/kit.png" }
    ],
    art_direction: { user_review_questions: ["are the routes readable?"] }
  };

  it("renders both halves: the review side and the ComfyUI side", () => {
    render(<VisualsPanel comfy={comfy} review={review} t={t} />);

    // Console-original fields.
    expect(screen.getByText("ComfyUI")).toBeTruthy();
    expect(screen.getByText("job-1 / keep wall-run routes readable / rooftop-kit")).toBeTruthy();
    expect(screen.getByText("Usage rules")).toBeTruthy();
    expect(screen.getByText("never ship unapproved output")).toBeTruthy();
    expect(screen.getByText("Required decisions")).toBeTruthy();
    expect(screen.getByText("sign off the rooftop kit")).toBeTruthy();

    // Review fields the workbench rendered and the console did not.
    expect(screen.getByText("Approval gate")).toBeTruthy();
    expect(screen.getByText("creative_review")).toBeTruthy();
    expect(screen.getByText("Creative review")).toBeTruthy();
    expect(screen.getByText("rooftop-kit / comfyui / pending / /out/kit.png")).toBeTruthy();
    expect(screen.getByText("Review questions")).toBeTruthy();
    expect(screen.getByText("are the routes readable?")).toBeTruthy();
  });

  it("reads both halves off the plan when handed a whole plan", () => {
    // The workbench's call shape: it passes the plan and nothing else.
    render(<VisualsPanel plan={plan({ comfyui_plan: comfy, creative_review: review })} t={t} />);
    expect(screen.getByText("ComfyUI")).toBeTruthy();
    expect(screen.getByText("Creative review")).toBeTruthy();
  });

  it("renders the shell with no blocks when neither half arrived", () => {
    const { container } = render(<VisualsPanel t={t} />);
    expect(container.querySelector("#visuals-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });
});

describe("console qa panel", () => {
  it("renders all four check groups", () => {
    render(
      <QaPanel
        t={t}
        qa={{
          smoke_tests: ["boots to the drop zone"],
          playability_checks: ["loop closes in under 10 minutes"],
          failure_checks: ["falling resets the route"],
          packaging_checks: ["export runs on the CI runner"]
        }}
      />
    );

    expect(screen.getByText("Smoke tests")).toBeTruthy();
    expect(screen.getByText("boots to the drop zone")).toBeTruthy();
    expect(screen.getByText("Playability checks")).toBeTruthy();
    expect(screen.getByText("loop closes in under 10 minutes")).toBeTruthy();
    expect(screen.getByText("Failure states")).toBeTruthy();
    expect(screen.getByText("falling resets the route")).toBeTruthy();
    expect(screen.getByText("Packaging checks")).toBeTruthy();
    expect(screen.getByText("export runs on the CI runner")).toBeTruthy();
  });

  it("reads the QA plan off the plan when handed a whole plan", () => {
    render(<QaPanel plan={plan({ qa_plan: { smoke_tests: ["boots"] } })} t={t} />);
    expect(screen.getByText("boots")).toBeTruthy();
  });

  it("renders the shell with no blocks when no QA plan arrived", () => {
    const { container } = render(<QaPanel t={t} />);
    expect(container.querySelector("#qa-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });
});

/**
 * Cross-panel invariant. The merged panels render a dash for an empty list
 * (the workbench's shape) rather than the console's "No items" paragraph. Both
 * say the same thing -- "this list is genuinely empty" -- and the point of the
 * assertion is that an empty list never renders as a blank region, which an
 * operator cannot tell apart from a payload that never arrived.
 */
describe("console panel list fallbacks", () => {
  it("marks each empty list rather than rendering a blank region", () => {
    render(
      <QaPanel
        t={t}
        qa={{ smoke_tests: [], playability_checks: [], failure_checks: [], packaging_checks: [] }}
      />
    );
    // One dash per empty list, and every group heading still present.
    expect(screen.getAllByText("-")).toHaveLength(4);
    expect(screen.getByText("Smoke tests")).toBeTruthy();
    expect(screen.getByText("Packaging checks")).toBeTruthy();
  });

  it("keeps a section visible when its list is empty instead of dropping the heading", () => {
    render(
      <PipelinePanel
        locale="en"
        t={t}
        plan={plan({
          production_pipeline: {
            project_name: "p",
            goal: "g",
            current_stage: "c",
            next_stage: "n",
            stages: [stage({ quality_gates: [] })]
          }
        })}
      />
    );
    // The stage declares no quality gates, so the quality pill is absent --
    // but the stage row itself and its status pill are still there.
    expect(screen.queryByText(/^Quality gates:/)).toBeNull();
    expect(screen.getByText("ready")).toBeTruthy();
  });
});
