import { useSyncExternalStore } from "react";
import { ProjectConflict, projectClient } from "./projectClient";
import { HANDOFF_KEY } from "./storage";
import type { DirectorBuildPlan } from "./types";
import type { ProjectBinding, ProjectDraft, ProjectSnapshot, ProjectWorkflow, WorkflowJobDetail } from "./projectTypes";

export const ACTIVE_PROJECT_KEY = "fantasy-agent-active-project-v1";
const IMPORT_KEY = "fantasy-agent-legacy-import-v1";
const DRAFT_KEY = "fantasy-agent-project-drafts-v1";
interface State {
  active: ProjectSnapshot | null; projects: ProjectSnapshot[]; workflow: ProjectWorkflow | null;
  jobs: Record<string, WorkflowJobDetail>; draft: ProjectDraft | null;
  loaded: boolean; loading: boolean; saving: boolean; error: string; conflict: boolean;
}
const initial = (): State => ({ active: null, projects: [], workflow: null, jobs: {}, draft: null, loaded: false, loading: false, saving: false, error: "", conflict: false });
type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;

/** Backend snapshots and versioned local drafts share one subscription across all panels. */
export function createProjectStore(client = projectClient, storage: Storage = localStorage) {
  let state = initial();
  const listeners = new Set<() => void>();
  let timer: ReturnType<typeof setInterval> | undefined;
  let refreshing: Promise<void> | null = null;
  let selection = 0;
  const read = (key: string) => { try { return storage.getItem(key); } catch { return null; } };
  const write = (key: string, value: string) => { try { storage.setItem(key, value); } catch { /* Memory remains available in read-only browser profiles. */ } };
  let activeId = read(ACTIVE_PROJECT_KEY);
  let drafts: Record<string, ProjectDraft> = {};
  try { drafts = JSON.parse(read(DRAFT_KEY) || "{}"); } catch { /* Preserve malformed storage until a new draft is created. */ }
  state = { ...state, draft: drafts.unassigned ?? null };
  const emit = (patch: Partial<State>) => { state = { ...state, ...patch }; listeners.forEach((listener) => listener()); };
  const install = (snapshot: ProjectSnapshot) => {
    if (!snapshot?.project_id || !Number.isInteger(snapshot.plan_version)) throw new Error("项目响应无效，请重试连接。");
    activeId = snapshot.project_id; write(ACTIVE_PROJECT_KEY, activeId);
    const unchanged = state.active?.project_id === activeId && JSON.stringify(state.active) === JSON.stringify(snapshot);
    if (state.active?.project_id === activeId && JSON.stringify(state.active.plan) === JSON.stringify(snapshot.plan)) snapshot = { ...snapshot, plan: state.active.plan };
    if (state.active?.project_id === activeId && JSON.stringify(state.active.creative_review) === JSON.stringify(snapshot.creative_review)) snapshot = { ...snapshot, creative_review: state.active.creative_review };
    const draft = drafts[activeId] ?? null;
    emit({ active: unchanged ? state.active : snapshot, draft, conflict: Boolean(draft && draft.baseVersion !== snapshot.plan_version),
      projects: state.projects.some((p) => p.project_id === activeId) ? state.projects.map((p) => p.project_id === activeId ? snapshot : p) : [...state.projects, snapshot] });
  };
  async function loadWorkflow(id: string, epoch: number) {
    const workflow = await client.workflow(id);
    if (epoch !== selection || activeId !== id) return;
    const details = await Promise.all((state.active?.jobs ?? []).map(async (job) => {
      try { return await client.job(id, job.job_id); } catch { return { ...job, project_id: id, detail_read_failed: true }; }
    }));
    if (epoch !== selection || activeId !== id) return;
    emit({ workflow, jobs: Object.fromEntries(details.filter((job) => job !== null).map((job) => [job.job_id, job])) });
  }
  async function refreshWork() {
    const epoch = selection; emit({ loading: !state.loaded });
    try {
      const list = await client.list();
      if (!Array.isArray(list.projects)) throw new Error("项目列表读取失败，请重试连接。");
      if (epoch !== selection) return;
      emit({ projects: list.projects, loaded: true, error: "" });
      if (!read(IMPORT_KEY)) {
        const raw = read(HANDOFF_KEY);
        if (raw) {
          let legacy: DirectorBuildPlan | undefined;
          try { const parsed = JSON.parse(raw); legacy = parsed.plan ?? parsed; } catch { throw new Error("旧计划无法读取；原始草稿已保留，请检查后重试。"); }
          if (!legacy?.gameplay_spec) throw new Error("旧计划缺少玩法规范；原始草稿已保留。");
          const imported = await client.importLegacy(legacy); write(IMPORT_KEY, imported.project_id);
          if (!activeId) install(imported);
        } else write(IMPORT_KEY, "none");
      }
      const id = activeId ?? list.projects[0]?.project_id;
      if (id) {
        const snapshot = await client.get(id);
        if (epoch !== selection) return;
        install(snapshot); await loadWorkflow(id, epoch);
      }
    } catch (error) { if (epoch === selection) emit({ error: error instanceof Error ? error.message : String(error) }); }
    finally { emit({ loading: false }); }
  }
  const refresh = () => { if (!refreshing) refreshing = refreshWork().finally(() => { refreshing = null; }); return refreshing; };
  async function select(id: string) {
    const epoch = ++selection; activeId = id;
    emit({ active: null, workflow: null, jobs: {}, draft: drafts[id] ?? null, loading: true, error: "" });
    try { const snapshot = await client.get(id); if (epoch === selection) { install(snapshot); await loadWorkflow(id, epoch); } }
    catch (error) { if (epoch === selection) emit({ error: String(error instanceof Error ? error.message : error) }); }
    finally { if (epoch === selection) emit({ loading: false }); }
  }
  function setDraft(plan: DirectorBuildPlan, baseVersion = state.draft?.baseVersion ?? state.active?.plan_version ?? 0) {
    if (!state.active) throw new Error("请先建立或选择后台项目。");
    setDraftFor(plan, state.active.project_id, baseVersion);
  }
  function setDraftFor(plan: DirectorBuildPlan, projectId: string, baseVersion: number) {
    const draft = { plan, baseVersion }; drafts = { ...drafts, [projectId]: draft }; write(DRAFT_KEY, JSON.stringify(drafts));
    if (projectId === activeId || (!state.active && projectId === "unassigned")) emit({ draft, conflict: Boolean(state.active && baseVersion !== state.active.plan_version) });
  }
  function discardDraft() {
    delete drafts[state.active?.project_id ?? "unassigned"]; write(DRAFT_KEY, JSON.stringify(drafts)); emit({ draft: null, conflict: false });
  }
  async function saveDraft(rebase = false) {
    const project = state.active; const draft = state.draft;
    if (!project || !draft || state.saving) return;
    emit({ saving: true, error: "" });
    try {
      const saved = await client.save(project.project_id, draft.plan, rebase ? project.plan_version : draft.baseVersion);
      if (drafts[project.project_id] === draft) {
        delete drafts[project.project_id]; write(DRAFT_KEY, JSON.stringify(drafts));
      }
      if (activeId === project.project_id && saved.project_id === project.project_id
        && saved.plan_version > (state.active?.plan_version ?? 0)) {
        const savedEpoch = ++selection;
        emit({ workflow: null, jobs: {} });
        install(saved); await loadWorkflow(project.project_id, savedEpoch);
      } else if (state.active?.project_id === project.project_id) {
        const currentDraft = drafts[project.project_id] ?? null;
        emit({ draft: currentDraft, conflict: Boolean(currentDraft && currentDraft.baseVersion !== state.active.plan_version) });
      }
    } catch (error) {
      if (activeId === project.project_id) {
        if (error instanceof ProjectConflict && error.latest.project_id === project.project_id
          && error.latest.plan_version > (state.active?.plan_version ?? 0)) {
          ++selection; // The conflict response is newer than any outstanding read.
          emit({ workflow: null, jobs: {} });
          install(error.latest);
        }
        emit({ error: error instanceof Error ? error.message : String(error) });
      }
    } finally { emit({ saving: false }); }
  }
  async function create(name: string, plan?: DirectorBuildPlan) {
    const epoch = ++selection;
    if (plan) setDraftFor(plan, "unassigned", 0);
    try {
      const project = await client.create(name, plan);
      delete drafts.unassigned; write(DRAFT_KEY, JSON.stringify(drafts));
      if (epoch === selection) { install(project); emit({ loaded: true, error: "" }); }
    }
    catch (error) { if (epoch === selection) emit({ error: String(error instanceof Error ? error.message : error) }); }
  }
  /** A server operation already performed CAS; installing its response must not save again. */
  function acceptSaved(snapshot: ProjectSnapshot, origin: ProjectBinding) {
    if (state.active?.project_id !== origin.project_id || snapshot.project_id !== origin.project_id
      || state.active.plan_version !== origin.plan_version || snapshot.plan_version < origin.plan_version) return false;
    // Invalidate reads that started before this save, even within the same project.
    ++selection;
    emit({ workflow: null, jobs: {}, error: "" });
    install(snapshot);
    return true;
  }
  function acceptWorkflow(workflow: ProjectWorkflow, origin: ProjectBinding) {
    if (state.active?.project_id !== origin.project_id || state.active.plan_version !== origin.plan_version
      || workflow.project_id !== origin.project_id || workflow.plan_version !== origin.plan_version) return false;
    ++selection;
    emit({ workflow });
    return true;
  }
  return { getSnapshot: () => state, selectedProjectId: () => activeId, refresh, select, create, setDraft, setDraftFor, discardDraft, saveDraft, acceptSaved, acceptWorkflow,
    reset() {
      ++selection; state = initial(); refreshing = null; activeId = read(ACTIVE_PROJECT_KEY);
      try { drafts = JSON.parse(read(DRAFT_KEY) || "{}"); } catch { drafts = {}; }
      state = { ...state, draft: drafts.unassigned ?? null };
    },
    subscribe(listener: () => void) {
      listeners.add(listener);
      if (listeners.size === 1) { void refresh(); timer = setInterval(() => void refresh(), 2500); }
      return () => { listeners.delete(listener); if (!listeners.size && timer) { clearInterval(timer); timer = undefined; } };
    }
  };
}
export const projectStore = createProjectStore();
export function useProject() { return useSyncExternalStore(projectStore.subscribe, projectStore.getSnapshot); }
export function projectBinding() { const active = projectStore.getSnapshot().active; return active ? { project_id: active.project_id, plan_version: active.plan_version } : undefined; }
