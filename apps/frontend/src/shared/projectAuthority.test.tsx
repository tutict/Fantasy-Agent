import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StudioShell } from "../studio/StudioShell";
import { JourneyProvider } from "./journeyContext";
import { LocaleThemeProvider } from "./localeTheme";
import { projectStore } from "./projectStore";
import type { ProjectSnapshot } from "./projectTypes";
import { DraftActions } from "./DraftActions";
import { useState } from "react";
const snapshot = (version: number, title: string): ProjectSnapshot => ({ project_id: "p", plan_version: version, name: "共享项目", plan: { gameplay_spec: { title }, production_pipeline: { project_name: "shared", stages: [] } }, jobs: [], tasks: [], sessions: [], resources: [], decisions: {}, authorizations: [], created_at: 0, updated_at: version });
let backend: ProjectSnapshot;
beforeEach(() => {
  localStorage.clear(); localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
  window.history.replaceState({}, "", "/workbench?step=plan");
  backend = snapshot(1, "第一版玩法"); projectStore.reset();
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const value = url === "/api/projects" ? { projects: [backend] } : url.endsWith("/workflow") ? { project_id: "p", plan_version: backend.plan_version, stages: [] } : url === "/api/projects/p" ? backend : init?.method === "PUT" ? { latest: backend } : {};
    return new Response(JSON.stringify(value), { status: init?.method === "PUT" ? 409 : 200, headers: { "Content-Type": "application/json" } });
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); projectStore.reset(); });
describe("one project across visited workspaces", () => {
  it("propagates a Codex plan change to the shell, workbench, console and board", async () => {
    const view = render(<LocaleThemeProvider><JourneyProvider><StudioShell /></JourneyProvider></LocaleThemeProvider>);
    await waitFor(() => expect(view.container.querySelector(".journey-heading h2")?.textContent).toBe("第一版玩法"));
    fireEvent.click(view.container.querySelector('[data-target="pipeline"]')!);
    fireEvent.click(view.container.querySelector('[data-target="console"]')!);
    await waitFor(() => expect(view.container.querySelector("#plan-title")?.textContent).toBe("第一版玩法"));
    const workbench = view.container.querySelector('[data-testid="planning-workbench"]');
    const consoleView = view.container.querySelector('[data-frame="console"]');
    backend = snapshot(2, "Codex 更新后的玩法");
    await act(() => projectStore.refresh());
    expect(view.container.querySelector(".journey-heading h2")?.textContent).toBe("Codex 更新后的玩法");
    fireEvent.click(view.container.querySelector('[data-journey="plan"]')!);
    await waitFor(() => expect(view.container.querySelector('[data-testid="plan-title"]')?.textContent).toBe("Codex 更新后的玩法"));
    expect(view.container.querySelector("#plan-title")?.textContent).toBe("Codex 更新后的玩法");
    expect(view.container.querySelector(".or-plan-meta")?.textContent).toContain("Codex 更新后的玩法");
    expect(view.container.querySelector('[data-testid="planning-workbench"]')).toBe(workbench);
    expect(view.container.querySelector('[data-frame="console"]')).toBe(consoleView);
  });
  it("keeps the conflict draft visible until the user reviews the latest version", async () => {
    await projectStore.refresh();
    projectStore.setDraft({ gameplay_spec: { title: "保留的本地草稿" } });
    function Editor() { const [latest, setLatest] = useState(false); return <DraftActions showLatest={latest} onShowLatest={setLatest} />; }
    render(<LocaleThemeProvider><Editor /></LocaleThemeProvider>);
    backend = snapshot(2, "后台更新");
    fireEvent.click(screen.getByRole("button", { name: "保存计划" }));
    await screen.findByText("后台已有新版本。你的草稿已保留，请先核对最新计划。");
    expect(projectStore.getSnapshot().draft?.plan.gameplay_spec?.title).toBe("保留的本地草稿");
    expect((screen.getByRole("button", { name: "将此草稿保存为新版本" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "查看后台最新计划" }));
    expect((screen.getByRole("button", { name: "将此草稿保存为新版本" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
