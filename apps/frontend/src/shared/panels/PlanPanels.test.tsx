import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { makeTranslator, consoleI18n, workbenchI18n } from "../i18n";
import { OverviewPanel, QaPanel, TasksPanel } from "./PlanPanels";
import type { DirectorBuildPlan } from "../types";

afterEach(() => cleanup());

const plan: DirectorBuildPlan = {
  gameplay_spec: {
    title: "Rooftop Parkour Chase Across Neon",
    target_session_minutes: 10,
    logline: "Run across neon rooftops.",
    core_loop: [{ action: "wall-run", player_decision: "commit or drop" }],
    core_verbs: ["wall-run"],
    design_pillars: ["momentum"],
    systems: [{ name: "route timer" }],
    level_beats: [{ name: "Warmup Rooftop", duration_minutes: 2, gameplay_focus: "learn the route" }],
    win_state: "reach the exit",
    failure_states: ["fall off the roof"],
    asset_needs: ["rooftop kit"],
    qa_focus: ["clear failure feedback"],
    i18n: { field_translations: {
      logline: { "zh-CN": "穿过霓虹屋顶，逃离追兵。" },
      "core_loop.0.action": { "zh-CN": "蹬墙奔跑" },
      "core_loop.0.player_decision": { "zh-CN": "继续前进或落地" },
      "core_verbs.0": { "zh-CN": "蹬墙" },
      "design_pillars.0": { "zh-CN": "保持动量" },
      "systems.0.name": { "zh-CN": "路线计时" },
      "level_beats.0.name": { "zh-CN": "屋顶热身" },
      "level_beats.0.gameplay_focus": { "zh-CN": "熟悉路线" },
      win_state: { "zh-CN": "抵达出口" },
      "failure_states.0": { "zh-CN": "从屋顶坠落" },
      "asset_needs.0": { "zh-CN": "屋顶组件" },
      "qa_focus.0": { "zh-CN": "清楚说明失败原因" }
    } }
  },
  task_breakdown: {
    goal: "Build the prototype.",
    goal_i18n: { "zh-CN": "为 Rooftop Parkour Chase Across Neon 制作可玩切片。" },
    recommended_next_task: "gameplay_spec_review",
    tasks: [{ id: "gameplay_spec_review", title: "Gameplay spec review", title_i18n: { "zh-CN": "玩法方案审阅" }, status: "ready", agent: "gameplay-agent" }]
  },
  qa_plan: {
    smoke_tests: ["Project opens without missing plugin or asset errors"],
    playability_checks: ["Primary objective is visible within 10 seconds"],
    failure_checks: ["fall off the roof"],
    packaging_checks: ["Generated assets have valid collision"]
  }
};

describe.each([consoleI18n, workbenchI18n])("Chinese plan panels", (dictionary) => {
  it("renders the supplied Chinese gameplay fields throughout the overview", () => {
    const { container } = render(<OverviewPanel plan={plan} locale="zh-CN" t={makeTranslator("zh-CN", dictionary)} />);
    const content = container.querySelector("#overview-content")!.textContent!;
    for (const text of ["穿过霓虹屋顶", "蹬墙奔跑", "继续前进或落地", "蹬墙", "保持动量", "路线计时", "屋顶热身", "熟悉路线", "2 分钟", "抵达出口", "从屋顶坠落", "屋顶组件", "清楚说明失败原因"]) {
      expect(content).toContain(text);
    }
    expect(content).not.toMatch(/[A-Za-z]/);
  });

  it("shows task recommendations and roles in Chinese", () => {
    const { container } = render(<TasksPanel plan={plan} locale="zh-CN" t={makeTranslator("zh-CN", dictionary)} />);
    expect(container.textContent).toContain("为 屋顶跑酷追逐 制作可玩切片。");
    expect(container.textContent).toContain("玩法方案审阅");
    expect(screen.getByText("就绪")).toBeTruthy();
    expect(screen.getByText("玩法策划")).toBeTruthy();
  });

  it("localizes the generated QA checklist and the spec failure conditions", () => {
    const { container } = render(<QaPanel plan={plan} locale="zh-CN" t={makeTranslator("zh-CN", dictionary)} />);
    expect(container.textContent).toContain("工程打开时没有插件或资产缺失错误");
    expect(container.textContent).toContain("10 秒内能看见主要目标");
    expect(container.textContent).toContain("从屋顶坠落");
    expect(container.textContent).toContain("生成资产的碰撞有效");
    expect(container.textContent).not.toMatch(/[A-Za-z]/);
  });
});
