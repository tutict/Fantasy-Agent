import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { projectClient } from "./projectClient";
import { LocaleThemeProvider } from "./localeTheme";
import { projectStore } from "./projectStore";
import { WorkflowJobs, currentWorkflowResult } from "./WorkflowJobs";
import { projectI18n } from "./projectI18n";
import type { ProjectSnapshot } from "./projectTypes";
const project: ProjectSnapshot = { project_id: "p", plan_version: 2, name: "后台项目", plan: { gameplay_spec: { title: "玩法" } }, tasks: [], sessions: [], resources: [], decisions: [], authorizations: [], created_at: 0, updated_at: 0,
  jobs: [{ project_id: "p", plan_version: 1, job_id: "old", tool_name: "execute_demo", status: "done" }, { project_id: "p", plan_version: 2, job_id: "new", tool_name: "execute_demo", status: "running" }] };
afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear(); projectStore.reset(); });
describe("project workflow evidence", () => {
  it("does not project a previous version result onto the current plan", () => {
    expect(currentWorkflowResult(project, { old: { ...project.jobs[0]!, result: { data: { project_dir: "old-project" } } } }, "execute_demo")).toBeUndefined();
  });
  it("shows job versions and cancels through the job's own project", async () => {
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN"); projectStore.reset();
    vi.spyOn(projectClient, "list").mockResolvedValue({ projects: [project] }); vi.spyOn(projectClient, "get").mockResolvedValue(project);
    vi.spyOn(projectClient, "workflow").mockResolvedValue({ project_id: "p", plan_version: 2, stages: [] });
    vi.spyOn(projectClient, "job").mockImplementation(async (_, id) => ({ ...project.jobs.find((job) => job.job_id === id)!, summary: id === "old" ? "旧任务" : "正在生产", resources: id === "old" ? [{ project_id: "p", plan_version: 1, resource_id: "html", mime_type: "text/html", path: "report.html" }] : [] }));
    const cancel = vi.spyOn(projectClient, "cancel").mockResolvedValue({ status: "cancelled" });
    await projectStore.refresh();
    expect(projectStore.getSnapshot().error).toBe("");
    expect(projectStore.getSnapshot().active?.jobs).toHaveLength(2);
    render(<LocaleThemeProvider><WorkflowJobs /></LocaleThemeProvider>);
    await screen.findByText("正在生产");
    fireEvent.click(screen.getByRole("button", { name: "取消任务" }));
    await waitFor(() => expect(cancel).toHaveBeenCalledWith("p", "new"));
    expect(screen.getByText("属于计划 v1，当前计划为 v2。请在对应版本查看结果。")).toBeTruthy();
  });
  it("renders HTML as text and never as an active document", async () => {
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN"); projectStore.reset();
    vi.spyOn(projectClient, "list").mockResolvedValue({ projects: [project] }); vi.spyOn(projectClient, "get").mockResolvedValue(project);
    vi.spyOn(projectClient, "workflow").mockResolvedValue({ project_id: "p", plan_version: 2 });
    vi.spyOn(projectClient, "job").mockImplementation(async (_, id) => ({ ...project.jobs.find((job) => job.job_id === id)!, resources: [{ project_id: "p", plan_version: 2, resource_id: id, path: `${id}.html` }] }));
    vi.spyOn(projectClient, "resource").mockResolvedValue({ mime_type: "text/html", data: '<script>window.secret = "leak"</script>' });
    await projectStore.refresh();
    expect(projectStore.getSnapshot().error).toBe("");
    expect(projectStore.getSnapshot().active?.jobs).toHaveLength(2);
    const view = render(<LocaleThemeProvider><WorkflowJobs /></LocaleThemeProvider>);
    await screen.findByText("new.html"); fireEvent.click(screen.getAllByRole("button", { name: "安全预览" })[0]!);
    await screen.findByText('<script>window.secret = "leak"</script>');
    expect(view.container.querySelector("script, iframe")).toBeNull();
  });
  it("keeps connection and workflow dictionary keys aligned", () => {
    expect(Object.keys(projectI18n.en).sort()).toEqual(Object.keys(projectI18n["zh-CN"]).sort());
    for (const values of Object.values(projectI18n)) for (const value of Object.values(values)) expect(value.trim()).not.toBe("");
  });
  it("shows a completed experiment's adoption blocker and next action in Chinese", async () => {
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN"); projectStore.reset();
    const completed = { ...project, jobs: [{ ...project.jobs[1]!, tool_name: "run_evolution", status: "done" }] };
    vi.spyOn(projectClient, "list").mockResolvedValue({ projects: [completed] });
    vi.spyOn(projectClient, "get").mockResolvedValue(completed);
    vi.spyOn(projectClient, "workflow").mockResolvedValue({ project_id: "p", plan_version: 2, stages: [] });
    vi.spyOn(projectClient, "job").mockResolvedValue({ ...completed.jobs[0]!, summary: "实验已完成，等待采纳。",
      result: { status: "done", kind: "run_evolution", data: { status: "done", report: { status: "improved", best_iteration: 1, adopted_iteration: null } } }, blockers: ["候选尚未得到用户批准"],
      progress: { stages: [{ name: "playtest", status: "degraded", detail: "请检查测量报告" }] } });
    await projectStore.refresh(); render(<LocaleThemeProvider><WorkflowJobs /></LocaleThemeProvider>);
    expect(await screen.findByText("待采纳：比较实验结果后再采纳。")).toBeTruthy();
    expect(screen.getByText(/候选尚未得到用户批准/)).toBeTruthy();
    expect(screen.getByText(/降级完成/)).toBeTruthy();
  });
  it("does not attach a late cancellation error to a different project", async () => {
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN"); projectStore.reset();
    vi.spyOn(projectClient, "list").mockResolvedValue({ projects: [project] });
    const get = vi.spyOn(projectClient, "get").mockResolvedValue(project);
    vi.spyOn(projectClient, "workflow").mockResolvedValue({ project_id: "p", plan_version: 2, stages: [] });
    vi.spyOn(projectClient, "job").mockImplementation(async (_, id) => ({ ...project.jobs.find((job) => job.job_id === id)! }));
    let fail!: (error: Error) => void;
    vi.spyOn(projectClient, "cancel").mockImplementation(() => new Promise((_, reject) => { fail = reject; }));
    await projectStore.refresh(); render(<LocaleThemeProvider><WorkflowJobs /></LocaleThemeProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "取消任务" }));
    get.mockResolvedValue({ ...project, project_id: "q" });
    await act(() => projectStore.select("q"));
    await act(async () => { fail(new Error("旧项目取消失败")); await Promise.resolve(); });
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
