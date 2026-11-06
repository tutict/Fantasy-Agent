import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EvolutionPanel } from "../console/evolution/EvolutionPanel";
import { FlowConsole } from "../console/FlowConsole";
import { OrchestrationBoard } from "../orchestration/OrchestrationBoard";
import { consoleI18n, makeTranslator, studioI18n } from "./i18n";
import { JourneyProvider } from "./journeyContext";
import { LocaleThemeProvider } from "./localeTheme";
import { projectStore } from "./projectStore";
import type { ProjectSnapshot, ProjectWorkflow } from "./projectTypes";
import type { EvolutionReport } from "./types";

const plan = {
  gameplay_spec: { title: "屋顶路线" }, godot_plan: { engine_version: "Godot 4" },
  production_spec_bundle: { numeric: { pressure_clock_seconds: 600 } },
  production_pipeline: { stages: [{ id: "creative_review", title: "创意审阅", kind: "human", order: 1 },
    { id: "godot_quick_play", title: "快速试玩", kind: "agent", order: 2 }] }
};
const snapshot = (id = "p", version = 1): ProjectSnapshot => ({ project_id: id, plan_version: version, name: id,
  plan, tasks: [], jobs: [], sessions: [], resources: [], decisions: [], authorizations: [], created_at: 0, updated_at: version });
let backend: ProjectSnapshot;
let workflow: ProjectWorkflow;
let requests: Array<{ url: string; body?: Record<string, unknown>; method: string }>;
const report: EvolutionReport = { experiment_id: "experiment", status: "improved", original_plan: plan,
  best_iteration: 1, adopted_iteration: null, elapsed_seconds: 5, notes: [], iterations: [
    { index: 1, session_id: "candidate", plan, report: null, eligible: true, improved: true, changes: [], notes: [] }
  ] };
beforeEach(() => {
  localStorage.clear(); projectStore.reset(); backend = snapshot();
  workflow = { project_id: "p", plan_version: 1, session_id: "project-session", engine: "godot", status: "blocked",
    stages: [{ stage_id: "creative_review", title: "创意审阅", kind: "human", order: 1, status: "awaiting_human" }] };
  requests = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    requests.push({ url, body, method: init?.method ?? "GET" });
    let data: unknown = {};
    if (url === "/api/projects") data = { projects: [backend] };
    else if (/\/api\/projects\/[^/]+$/.test(url)) data = backend;
    else if (url.endsWith("/workflow")) data = workflow;
    else if (url === "/api/evolution/run") data = body?.confirmed
      ? { status: "running", experiment_id: "experiment", job_id: "job" }
      : { status: "confirmation_required", planned_side_effects: ["生成候选"] };
    else if (url === "/api/evolution/experiment") data = { status: "done", report };
    else if (url.endsWith("/adopt")) data = { ...snapshot("p", 2), status: "adopted", plan: {
      ...plan, production_spec_bundle: { numeric: { pressure_clock_seconds: 720 } }
    }, experience: {} };
    else if (url.includes("/decision")) data = { ...workflow, error: "需要重新授权" };
    return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); projectStore.reset(); });

describe("project-bound UI results", () => {
  it("adopts the saved backend version without saving its bundle a second time", async () => {
    await projectStore.refresh();
    const t = makeTranslator("zh-CN", consoleI18n);
    const view = render(<EvolutionPanel plan={plan} binding={{ project_id: "p", plan_version: 1 }} t={t}
      onAdoptBundle={() => { throw new Error("重复保存已采纳的计划"); }} />);
    fireEvent.click(view.container.querySelector("summary")!);
    fireEvent.click(screen.getByRole("button", { name: t("evolutionPreview") }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: t("evolutionConfirmStart") }));
    fireEvent.click(await screen.findByRole("button", { name: t("evolutionAdopt") }));
    await waitFor(() => expect(projectStore.getSnapshot().active?.plan_version).toBe(2));
    expect(projectStore.getSnapshot().active?.plan?.production_spec_bundle?.numeric?.pressure_clock_seconds).toBe(720);
    expect(requests.filter((request) => request.method === "PUT")).toEqual([]);
  });

  it("sends a project gate decision to the workflow's session and engine", async () => {
    await projectStore.refresh();
    render(<LocaleThemeProvider><JourneyProvider><OrchestrationBoard active locale="zh-CN"
      t={makeTranslator("zh-CN", studioI18n)} onOpenConsole={() => undefined} /></JourneyProvider></LocaleThemeProvider>);
    await waitFor(() => expect(document.querySelector('[data-stage="creative_review"]')?.getAttribute("data-status")).toBe("awaiting_human"));
    fireEvent.click(screen.getByRole("button", { name: "批准放行" }));
    await waitFor(() => expect(requests.some((request) => request.url.includes("/decision"))).toBe(true));
    expect(requests.find((request) => request.url.includes("/decision"))?.url).toBe("/api/orchestration/project-session/stages/creative_review/decision?engine=godot");
  });
  it("renders the authoritative synchronized workflow immediately", async () => {
    await projectStore.refresh();
    const normalFetch = fetch;
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => url === "/api/orchestration/run"
      ? Promise.resolve(new Response(JSON.stringify({ ...workflow, status: "done", stages: workflow.stages!.map((stage) => ({ ...stage, status: "done" })) })))
      : normalFetch(url, init));
    const view = render(<LocaleThemeProvider><JourneyProvider><OrchestrationBoard active locale="zh-CN"
      t={makeTranslator("zh-CN", studioI18n)} onOpenConsole={() => undefined} /></JourneyProvider></LocaleThemeProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "同步流程" }));
    await waitFor(() => expect(view.container.querySelector('[data-stage="creative_review"]')?.getAttribute("data-status")).toBe("done"));
    expect(projectStore.getSnapshot().workflow?.status).toBe("done");
  });

  it("does not show an old workflow after a project version changes", async () => {
    await projectStore.refresh();
    const view = render(<LocaleThemeProvider><JourneyProvider><OrchestrationBoard active locale="zh-CN"
      t={makeTranslator("zh-CN", studioI18n)} onOpenConsole={() => undefined} /></JourneyProvider></LocaleThemeProvider>);
    await waitFor(() => expect(view.container.querySelector('[data-stage="creative_review"]')?.getAttribute("data-status")).toBe("awaiting_human"));
    backend = snapshot("p", 2);
    await act(() => projectStore.refresh());
    expect(view.container.querySelector('[data-stage="creative_review"]')?.getAttribute("data-status")).toBe("pending");
  });
  it("does not adopt a late response into another project with the same plan", async () => {
    await projectStore.refresh();
    const normalFetch = fetch;
    let finish!: (response: Response) => void;
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => url.endsWith("/adopt")
      ? new Promise<Response>((resolve) => { finish = resolve; }) : normalFetch(url, init));
    const t = makeTranslator("zh-CN", consoleI18n);
    const view = render(<EvolutionPanel plan={plan} binding={{ project_id: "p", plan_version: 1 }} t={t}
      onAdoptBundle={() => { throw new Error("旧项目候选串入新项目"); }} />);
    fireEvent.click(view.container.querySelector("summary")!);
    fireEvent.click(screen.getByRole("button", { name: t("evolutionPreview") }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: t("evolutionConfirmStart") }));
    fireEvent.click(await screen.findByRole("button", { name: t("evolutionAdopt") }));
    await waitFor(() => expect(finish).toBeTypeOf("function"));
    backend = snapshot("q"); workflow = { ...workflow, project_id: "q", session_id: "q-session" };
    await act(() => projectStore.select("q"));
    view.rerender(<EvolutionPanel plan={plan} binding={{ project_id: "q", plan_version: 1 }} t={t}
      onAdoptBundle={() => { throw new Error("旧项目候选串入新项目"); }} />);
    await act(async () => { finish(new Response(JSON.stringify({ ...snapshot("p", 2), status: "adopted", experience: {} }))); await Promise.resolve(); });
    expect(projectStore.getSnapshot().active?.project_id).toBe("q");
    expect(projectStore.getSnapshot().active?.plan_version).toBe(1);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button", { name: t("evolutionAdopt") })).toBeNull();
  });
  it("renders the report nested in a completed MCP evolution job", async () => {
    const job = { project_id: "p", plan_version: 1, job_id: "evolution-job", tool_name: "run_evolution", status: "done" };
    backend = { ...backend, jobs: [job] };
    const normalFetch = fetch;
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => url.endsWith("/jobs/evolution-job")
      ? Promise.resolve(new Response(JSON.stringify({ ...job, summary: "实验已完成。", result: { status: "done", kind: "run_evolution", data: { status: "done", report } } })))
      : normalFetch(url, init));
    await projectStore.refresh();
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    render(<LocaleThemeProvider><JourneyProvider><FlowConsole journeyStep="qa" /></JourneyProvider></LocaleThemeProvider>);
    expect(await screen.findByText("候选 1")).toBeTruthy();
    expect(screen.getByText("待采纳：比较实验结果后再采纳。")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "采用最佳候选" })).toBeNull();
  });
});
