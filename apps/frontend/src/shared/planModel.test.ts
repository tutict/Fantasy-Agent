import { describe, expect, it } from "vitest";
import { planningText, planDisplayTitle, specFieldText } from "./planModel";

describe("Chinese project titles", () => {
  it("localizes a saved English prototype title without rewriting the plan", () => {
    const plan = {
      gameplay_spec: {
        title: "Rooftop Parkour Chase Across Neon",
        i18n: { field_translations: { title: { "zh-CN": "Rooftop Parkour Chase Across Neon 原型" } } }
      }
    };
    expect(planDisplayTitle(plan, "zh-CN")).toBe("屋顶跑酷追逐");
    expect(planDisplayTitle(plan, "en")).toBe("Rooftop Parkour Chase Across Neon");
    expect(plan.gameplay_spec.title).toBe("Rooftop Parkour Chase Across Neon");
  });

  it("uses the saved Chinese translation and preserves unknown proper names", () => {
    expect(planDisplayTitle({ gameplay_spec: { title: "Neon Rooftops", i18n: { field_translations: { title: { "zh-CN": "霓虹屋顶" } } } } }, "zh-CN")).toBe("霓虹屋顶");
    expect(planDisplayTitle({ gameplay_spec: { title: "Project Aurora" } }, "zh-CN")).toBe("Project Aurora");
    expect(planDisplayTitle({ gameplay_spec: { title: "Aurelia Combat" } }, "zh-CN")).toBe("Aurelia Combat");
  });
});

describe("Chinese planning copy", () => {
  it("repairs the English idea embedded in an old Chinese summary", () => {
    const spec = {
      logline: "A rooftop parkour chase.",
      i18n: { field_translations: { logline: { "zh-CN": "一个 10 分钟的可玩原型，围绕「rooftop parkour chase across neon towers」展开。" } } }
    };
    expect(specFieldText(spec, "logline", spec.logline, "zh-CN")).toBe("一个 10 分钟的可玩原型，围绕「屋顶跑酷追逐」展开。");
    expect(spec.logline).toBe("A rooftop parkour chase.");
  });

  it("does not show a stale translation after a gameplay field was edited", () => {
    const spec = { i18n: { field_translations: { win_state: { en: "Reach the exit", "zh-CN": "抵达出口" } } } };
    expect(specFieldText(spec, "win_state", "Collect three keys", "zh-CN")).toBe("Collect three keys");
  });

  it("keeps counts while translating a generated planning instruction", () => {
    expect(planningText("Prepare 11 modular greybox asset jobs for readable play.", "zh-CN")).toBe("准备 11 项模块化灰盒资产任务，保证玩法可读。");
    expect(planningText("Prepare 11 modular greybox asset jobs for readable play.", "en")).toBe("Prepare 11 modular greybox asset jobs for readable play.");
  });
});
