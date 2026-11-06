import { beforeEach, vi } from "vitest";
import { projectClient } from "../src/shared/projectClient";
import { projectStore } from "../src/shared/projectStore";
import type { DirectorBuildPlan } from "../src/shared/types";
import type { ProjectSnapshot } from "../src/shared/projectTypes";

let current: ProjectSnapshot | null = null;
let previousFixture: string | null = null;
function snapshot(plan: DirectorBuildPlan | null, name = "Test project", version = 1): ProjectSnapshot {
  return { project_id: "fixture-project", name, plan_version: version, plan, tasks: [], jobs: [], sessions: [], resources: [], decisions: {}, authorizations: [], created_at: 0, updated_at: version };
}
/** Old test handoffs seed a simulated backend; production components never read them. */
function readFixture() {
  const raw = localStorage.getItem("fantasy-agent-planning-handoff");
  if (raw && raw !== previousFixture) {
    previousFixture = raw;
    try { const data = JSON.parse(raw); const plan = data.plan ?? data; if (plan.gameplay_spec) current = snapshot(plan, data.title ?? plan.gameplay_spec.title); } catch { /* Invalid fixture stays invalid. */ }
  }
  return current;
}
export const projectBackend = { read: () => current };
export function installProjectFixture() {
  beforeEach(async () => {
    current = null; previousFixture = null; projectStore.reset();
    vi.spyOn(projectClient, "list").mockImplementation(async () => ({ projects: readFixture() ? [current!] : [] }));
    vi.spyOn(projectClient, "get").mockImplementation(async () => readFixture()!);
    vi.spyOn(projectClient, "importLegacy").mockImplementation(async (plan) => { current = readFixture() ?? snapshot(plan); return current; });
    vi.spyOn(projectClient, "create").mockImplementation(async (name, plan) => { current = snapshot(plan ?? null, name, plan ? 1 : 0); return current; });
    vi.spyOn(projectClient, "save").mockImplementation(async (_, plan) => { current = snapshot(plan, current?.name, (current?.plan_version ?? 0) + 1); return current; });
    vi.spyOn(projectClient, "workflow").mockImplementation(async (id) => ({ project_id: id, plan_version: current?.plan_version ?? 0, stages: [] }));
    await projectStore.refresh();
  });
}
