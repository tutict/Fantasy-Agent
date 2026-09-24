import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FlowConsole } from "./FlowConsole";
import { JourneyProvider } from "../shared/journeyContext";
import { LocaleThemeProvider } from "../shared/localeTheme";

const plan = {
  gameplay_spec: { title: "Rooftop", target_session_minutes: 10 },
  creative_review: { items: [{ asset_id: "gate", approval_status: "pending", asset_path: "gate.png", source: "comfyui" }] },
  production_pipeline: { stages: [{ id: "godot_quick_play" }] },
  godot_plan: { engine_version: "Godot 4" }
};

describe("failure recovery and approval return", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    localStorage.setItem("fantasy-agent-planning-handoff", JSON.stringify({ title: "Rooftop", plan }));
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (String(url).includes("/state")) return Response.json({ found: true, stages: [{ name: "blender", status: "failed" }], failed: ["blender"] });
      return Response.json({ planned_side_effects: ["write project"], job_id: "job", session_id: "sess" });
    }));
  });

  it("offers logs, input editing, and a confirmed resume", async () => {
    render(<LocaleThemeProvider><JourneyProvider><FlowConsole reviewStage="gate" /></JourneyProvider></LocaleThemeProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "一键生成可玩 demo" }));
    fireEvent.click(await screen.findByRole("button", { name: "生成" }));
    const resume = await screen.findByRole("button", { name: "从此节点续跑" }, { timeout: 4000 });
    expect(screen.getByRole("link", { name: "查看日志" }).getAttribute("href")).toBe("#activity-drawer");
    expect(screen.getByRole("link", { name: "修改输入" }).getAttribute("href")).toBe("#correction-notes");
    fireEvent.click(resume);
    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain("blender");
    fireEvent.click(within(dialog).getByRole("button", { name: "从此节点续跑" }));
    expect(fetch).toHaveBeenCalled();
  });
});
