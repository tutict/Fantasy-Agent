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
  it("renders the session length, win state and the loop the operator is signing off", () => {
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
            systems: [{ name: "momentum", purpose: "reward uninterrupted routes" }]
          },
          next_actions: ["run the Godot greybox"]
        })}
      />
    );

    expect(screen.getByText("Target session")).toBeTruthy();
    expect(screen.getByText("reach the drop zone")).toBeTruthy();
    // "momentum" is both a design pillar and a system name, so assert on the
    // system's purpose instead of the word that legitimately appears twice.
    expect(screen.getByText("reward uninterrupted routes")).toBeTruthy();
    expect(screen.getByText("Design pillars")).toBeTruthy();
    expect(screen.getByText("Core loop")).toBeTruthy();
    expect(screen.getByText("Next actions")).toBeTruthy();
    expect(screen.getByText("timeout")).toBeTruthy();
    expect(screen.getByText("wall-run")).toBeTruthy();
    expect(screen.getByText("commit or drop")).toBeTruthy();
    expect(screen.getByText("run the Godot greybox")).toBeTruthy();
  });

  it("renders nothing rather than a broken shell when the plan carries no spec", () => {
    const { container } = render(<OverviewPanel locale="en" t={t} plan={plan()} />);
    expect(container.querySelector("#overview-content")).toBeNull();
  });

  /**
   * Union field set. The workbench half already renders these; the console half
   * has to as well once both are one component, or the promise behind "one
   * panel implemented once" is only half kept.
   */
  it.todo("renders the workbench-only spec fields after the lift (logline, core verbs, level beats, asset needs, QA focus)");
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

    expect(screen.getByText("Quality gates")).toBeTruthy();
    expect(screen.getByText("runs at 60fps")).toBeTruthy();
    expect(screen.getByText("no missing scripts")).toBeTruthy();
    expect(screen.getByText("Risks")).toBeTruthy();
    expect(screen.getByText("approval blocks the import")).toBeTruthy();
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
    expect(container.querySelectorAll(".stage-row:not(.wide)")).toHaveLength(0);
    // The dead shell the console shows before a handoff exists.
    expect(container.querySelector("#pipeline-output")).toBeTruthy();
  });

  it("renders an empty shell when there is no pipeline at all", () => {
    const { container } = render(<PipelinePanel locale="en" t={t} plan={{}} />);
    expect(container.querySelector("#pipeline-output")).toBeTruthy();
    expect(container.textContent).toBe("");
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

    expect(screen.getByText("ship the greybox")).toBeTruthy();
    expect(screen.getByText("Recommended: wire the drop zone")).toBeTruthy();
    expect(screen.getByText("Wire the drop zone")).toBeTruthy();
    expect(screen.getByText("end the loop")).toBeTruthy();
    expect(screen.getByText("task-1")).toBeTruthy();
    expect(screen.getByText("godot")).toBeTruthy();
    expect(screen.getByText("Confirmation required")).toBeTruthy();
    // Counts, not ids -- the console deliberately shortens these two.
    expect(screen.getByText("Dependencies: 1")).toBeTruthy();
    expect(screen.getByText("Tool operations: 1")).toBeTruthy();
  });

  it("renders an empty shell when no breakdown has arrived", () => {
    const { container } = render(<TasksPanel locale="en" t={t} />);
    expect(container.querySelector("#tasks-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });

  /** Union field set: the workbench half spells the dependency ids out. */
  it.todo("spells out dependency and side-effect ids after the lift, instead of only counting them");
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

    expect(screen.getByText("Maps")).toBeTruthy();
    expect(screen.getByText("L_Rooftops")).toBeTruthy();
    expect(screen.getByText("AMomentumPlayer")).toBeTruthy();
    expect(screen.getByText("/Game/Rooftops")).toBeTruthy();
    expect(screen.getByText("run headless import")).toBeTruthy();
    expect(screen.getByText("Rooftop kit")).toBeTruthy();
    expect(screen.getByText("/out/rooftop.fbx")).toBeTruthy();
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

    expect(screen.getByText("Godot quick-play")).toBeTruthy();
    expect(screen.getByText("res://main.tscn")).toBeTruthy();
    expect(screen.getByText("res://player.gd")).toBeTruthy();
    expect(screen.getByText("run headless verify")).toBeTruthy();
    // The Unreal branch must not leak in alongside it.
    expect(screen.queryByText("L_Rooftops")).toBeNull();
  });

  it("renders the shell with no blocks when the plan has no engine plan", () => {
    const { container } = render(<BuildPanel t={t} plan={plan()} />);
    expect(container.querySelector("#build-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });
});

describe("console visuals panel", () => {
  const comfy = {
    jobs: [{ job_id: "job-1", gameplay_constraint: "keep wall-run routes readable", workflow_template: "rooftop-kit" }],
    usage_rules: ["never ship unapproved output"]
  };
  const review = { required_user_decisions: ["sign off the rooftop kit"] };

  it("renders the ComfyUI jobs, the usage rules and the review decisions still owed", () => {
    render(<VisualsPanel comfy={comfy} review={review} t={t} />);

    expect(screen.getByText("Jobs")).toBeTruthy();
    expect(screen.getByText("job-1")).toBeTruthy();
    expect(screen.getByText("keep wall-run routes readable")).toBeTruthy();
    expect(screen.getByText("rooftop-kit")).toBeTruthy();
    expect(screen.getByText("Usage rules")).toBeTruthy();
    expect(screen.getByText("never ship unapproved output")).toBeTruthy();
    expect(screen.getByText("sign off the rooftop kit")).toBeTruthy();
  });

  it("renders only the half it was given", () => {
    render(<VisualsPanel comfy={comfy} t={t} />);
    expect(screen.getByText("Jobs")).toBeTruthy();
    expect(screen.queryByText("Creative review")).toBeNull();
  });

  it("renders the shell with no blocks when neither half arrived", () => {
    const { container } = render(<VisualsPanel t={t} />);
    expect(container.querySelector("#visuals-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });

  /** Union field set: the workbench half renders the review items themselves. */
  it.todo("renders the approval gate, the review items and the art-direction questions after the lift");
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

  it("renders the shell with no blocks when no QA plan arrived", () => {
    const { container } = render(<QaPanel t={t} />);
    expect(container.querySelector("#qa-output")).toBeTruthy();
    expect(container.textContent).toBe("");
  });
});

/**
 * Cross-panel invariant. Every console panel renders `t("noItems")` for an
 * empty list, so an empty list must look like an explicit "No items" rather
 * than a blank region -- otherwise the operator cannot tell "nothing here"
 * from "the payload never arrived".
 */
describe("console panel list fallbacks", () => {
  it("says No items rather than rendering a blank list", () => {
    render(
      <QaPanel
        t={t}
        qa={{ smoke_tests: [], playability_checks: [], failure_checks: [], packaging_checks: [] }}
      />
    );
    expect(screen.getAllByText("No items")).toHaveLength(4);
  });
});
