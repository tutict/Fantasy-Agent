import { describe, expect, it, vi } from "vitest";
import { createProjectStore } from "./projectStore";
import { ProjectConflict, projectClient } from "./projectClient";
import type { ProjectSnapshot } from "./projectTypes";

const snapshot = (version = 1, title = "后台计划"): ProjectSnapshot => ({ project_id: "p", name: "项目", plan_version: version, plan: { gameplay_spec: { title } }, jobs: [], tasks: [], sessions: [], resources: [], decisions: [], authorizations: [], created_at: "", updated_at: String(version) });
function fixture() {
  const values = new Map<string, string>();
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); } };
  const client = { ...projectClient, list: vi.fn(async () => ({ projects: [snapshot()] })), get: vi.fn(async () => snapshot()), workflow: vi.fn(async () => ({ project_id: "p", plan_version: 1, stages: [] })), job: vi.fn(), importLegacy: vi.fn(async () => snapshot()), save: vi.fn(async () => snapshot(2)) };
  return { values, client, store: createProjectStore(client, storage) };
}
describe("backend project authority", () => {
  it("imports a legacy handoff once and keeps the original draft", async () => {
    const { store, values, client } = fixture();
    values.set("fantasy-agent-planning-handoff", JSON.stringify({ plan: snapshot().plan }));
    await store.refresh(); await store.refresh();
    expect(client.importLegacy).toHaveBeenCalledTimes(1);
    expect(values.has("fantasy-agent-planning-handoff")).toBe(true);
    expect(store.getSnapshot().active?.project_id).toBe("p");
  });
  it("reports backend failure instead of asserting an empty project list", async () => {
    const { store, client } = fixture();
    client.list.mockRejectedValue(new Error("离线"));
    await store.refresh();
    expect(store.getSnapshot().error).toBe("离线");
    expect(store.getSnapshot().loaded).toBe(false);
  });
  it("keeps a draft and the latest snapshot after a CAS conflict", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "本地草稿" } });
    client.save.mockRejectedValue(new ProjectConflict(snapshot(2, "Codex 修改")));
    await store.saveDraft();
    expect(store.getSnapshot().active?.plan?.gameplay_spec?.title).toBe("Codex 修改");
    expect(store.getSnapshot().draft?.plan.gameplay_spec?.title).toBe("本地草稿");
    expect(store.getSnapshot().draft?.baseVersion).toBe(1);
    expect(store.getSnapshot().conflict).toBe(true);
  });
  it("polls external changes while preserving the draft base version", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "未提交" } });
    client.get.mockResolvedValue(snapshot(3, "外部新计划"));
    await store.refresh();
    expect(store.getSnapshot().active?.plan_version).toBe(3);
    expect(store.getSnapshot().draft?.baseVersion).toBe(1);
  });
  it("does not install a late response into a different project", async () => {
    const { store, client } = fixture(); await store.refresh();
    let finish!: (p: ProjectSnapshot) => void;
    client.get.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.refresh(); await Promise.resolve(); await Promise.resolve();
    client.get.mockResolvedValue({ ...snapshot(), project_id: "q" });
    await store.select("q"); finish(snapshot(2)); await pending;
    expect(store.getSnapshot().active?.project_id).toBe("q");
  });
  it("restores the backend project reference and the unsaved draft after a reload", async () => {
    const { store, client, values } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "重启后的草稿" } });
    const restored = createProjectStore(client, { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => { values.set(key, value); } });
    await restored.refresh();
    expect(restored.getSnapshot().active?.project_id).toBe("p");
    expect(restored.getSnapshot().draft?.plan.gameplay_spec?.title).toBe("重启后的草稿");
    expect(restored.getSnapshot().draft?.baseVersion).toBe(1);
  });
  it("retries a failed legacy import without discarding the browser handoff", async () => {
    const { store, client, values } = fixture();
    values.set("fantasy-agent-planning-handoff", JSON.stringify({ plan: snapshot().plan }));
    client.importLegacy.mockRejectedValueOnce(new Error("导入失败"));
    await store.refresh(); expect(store.getSnapshot().error).toBe("导入失败");
    expect(values.has("fantasy-agent-legacy-import-v1")).toBe(false);
    await store.refresh(); expect(client.importLegacy).toHaveBeenCalledTimes(2);
    expect(store.getSnapshot().active?.project_id).toBe("p");
  });
  it("keeps a saved authoritative version when an earlier refresh arrives late", async () => {
    const { store, client } = fixture(); await store.refresh();
    let finish!: (p: ProjectSnapshot) => void;
    client.get.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.refresh(); await Promise.resolve(); await Promise.resolve();
    store.acceptSaved(snapshot(2, "已采纳候选"), { project_id: "p", plan_version: 1 });
    finish(snapshot()); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(2);
    expect(store.getSnapshot().active?.plan?.gameplay_spec?.title).toBe("已采纳候选");
  });
  it("keeps the CAS saved draft version when an earlier refresh arrives late", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "已保存草稿" } });
    let finish!: (p: ProjectSnapshot) => void;
    client.get.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.refresh(); await Promise.resolve(); await Promise.resolve();
    client.save.mockResolvedValue(snapshot(2, "已保存草稿"));
    await store.saveDraft();
    finish(snapshot()); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(2);
    expect(store.getSnapshot().active?.plan?.gameplay_spec?.title).toBe("已保存草稿");
    expect(store.getSnapshot().draft).toBeNull();
  });
  it("keeps the latest conflict version when an earlier refresh arrives late", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "未保存草稿" } });
    let finish!: (p: ProjectSnapshot) => void;
    client.get.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.refresh(); await Promise.resolve(); await Promise.resolve();
    client.save.mockRejectedValue(new ProjectConflict(snapshot(2, "外部新计划")));
    await store.saveDraft();
    finish(snapshot()); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(2);
    expect(store.getSnapshot().active?.plan?.gameplay_spec?.title).toBe("外部新计划");
    expect(store.getSnapshot().draft?.plan.gameplay_spec?.title).toBe("未保存草稿");
    expect(store.getSnapshot().conflict).toBe(true);
  });
  it("accepts a draft save after same-version workflow synchronization", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "同步期间保存" } });
    let finish!: (p: ProjectSnapshot) => void;
    client.save.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.saveDraft();
    store.acceptWorkflow({ project_id: "p", plan_version: 1, stages: [] }, { project_id: "p", plan_version: 1 });
    finish(snapshot(2, "同步期间保存")); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(2);
    expect(store.getSnapshot().draft).toBeNull();
  });
  it("accepts a save conflict after same-version workflow synchronization", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "同步期间的草稿" } });
    let fail!: (error: Error) => void;
    client.save.mockImplementationOnce(() => new Promise((_, reject) => { fail = reject; }));
    const pending = store.saveDraft();
    store.acceptWorkflow({ project_id: "p", plan_version: 1, stages: [] }, { project_id: "p", plan_version: 1 });
    fail(new ProjectConflict(snapshot(2, "最新计划"))); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(2);
    expect(store.getSnapshot().draft?.plan.gameplay_spec?.title).toBe("同步期间的草稿");
    expect(store.getSnapshot().conflict).toBe(true);
    expect(store.getSnapshot().error).toBeTruthy();
  });
  it("does not replace a newer project version with a late saved draft", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "较早保存" } });
    let finish!: (p: ProjectSnapshot) => void;
    client.save.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.saveDraft();
    client.get.mockResolvedValue(snapshot(3, "最新后台版本")); await store.refresh();
    finish(snapshot(2, "较早保存")); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(3);
    expect(store.getSnapshot().active?.plan?.gameplay_spec?.title).toBe("最新后台版本");
  });
  it("does not install a saved result belonging to the project that was left", async () => {
    const { store, client } = fixture(); await store.refresh();
    client.get.mockResolvedValue({ ...snapshot(), project_id: "q" });
    await store.select("q");
    store.acceptSaved(snapshot(2), { project_id: "p", plan_version: 1 });
    expect(store.getSnapshot().active?.project_id).toBe("q");
    expect(store.getSnapshot().active?.plan_version).toBe(1);
  });
  it("does not erase a newer draft when an earlier draft save completes", async () => {
    const { store, client } = fixture(); await store.refresh();
    store.setDraft({ gameplay_spec: { title: "正在保存" } });
    let finish!: (p: ProjectSnapshot) => void;
    client.save.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const pending = store.saveDraft();
    store.setDraft({ gameplay_spec: { title: "保存期间的新草稿" } });
    finish(snapshot(2, "正在保存")); await pending;
    expect(store.getSnapshot().active?.plan_version).toBe(2);
    expect(store.getSnapshot().draft?.plan.gameplay_spec?.title).toBe("保存期间的新草稿");
    expect(store.getSnapshot().conflict).toBe(true);
  });
  it("does not attach a late project creation failure to the new selection", async () => {
    const { store, client } = fixture(); await store.refresh();
    let fail!: (error: Error) => void;
    client.create = vi.fn(() => new Promise<ProjectSnapshot>((_, reject) => { fail = reject; }));
    const pending = store.create("正在创建");
    client.get.mockResolvedValue({ ...snapshot(), project_id: "q" }); await store.select("q");
    fail(new Error("旧项目创建失败")); await pending;
    expect(store.getSnapshot().active?.project_id).toBe("q");
    expect(store.getSnapshot().error).toBe("");
  });
});
