import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { consoleI18n, makeTranslator } from "../../shared/i18n";
import type { DirectorBuildPlan, ProductionSpecBundle } from "../../shared/types";

const t = makeTranslator("zh-CN", consoleI18n);
const PLAN: DirectorBuildPlan = {
  gameplay_spec: { title: "屋顶路线", target_session_minutes: 10 },
  godot_plan: { engine_version: "Godot 4" },
  production_pipeline: { stages: [{ id: "godot_quick_play", order: 1 }] },
  production_spec_bundle: { numeric: { player_move_speed: 8, pressure_clock_seconds: 600 } }
};
const WINNER: DirectorBuildPlan = {
  ...PLAN, production_spec_bundle: { numeric: { player_move_speed: 8, pressure_clock_seconds: 720 } }
};
const REPORT = {
  experiment_id: "evolution-test", status: "improved", original_plan: PLAN,
  best_iteration: 1, adopted_iteration: null, notes: [], elapsed_seconds: 5,
  iterations: [
    { index: 0, session_id: "baseline", plan: PLAN, eligible: false, improved: false, changes: [], notes: [],
      report: { aggregate: { runs: 3, wins: 0, session_seconds_p50: 12 } } },
    { index: 1, session_id: "candidate", plan: WINNER, eligible: true, improved: true, notes: [],
      changes: [{ field: "numeric.pressure_clock_seconds", before: 600, after: 720, reason: "计时余量" }],
      report: { aggregate: { runs: 3, wins: 3, session_seconds_p50: 12 } } }
  ]
};
type RequestRecord = { path: string; method: string; body?: Record<string, unknown> };
let requests: RequestRecord[];

function fetchFixture(failure = false) {
  vi.stubGlobal("fetch", async (input: string, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : undefined;
    requests.push({ path: String(input), method: init?.method ?? "GET", body });
    if (failure) return { ok: false, status: 503, json: async () => ({ detail: "记录无法读取" }) };
    let data: unknown = {};
    if (String(input).endsWith("/run")) data = body?.confirmed
      ? { status: "running", job_id: "job-test", experiment_id: "evolution-test" }
      : { status: "confirmation_required", planned_side_effects: ["启动 Godot 并生成独立候选"] };
    else if (String(input).endsWith("/adopt")) data = { status: "adopted", plan: WINNER, experience: { id: "lesson" } };
    else if (String(input).endsWith("/cancel")) data = { status: "cancelling" };
    else if (String(input).endsWith("/experiences")) data = { experiences: [{ id: "lesson", axis: "parkour", changes: [] }] };
    else if (String(input).endsWith("/suggest")) data = { plan: WINNER, changes: REPORT.iterations[1].changes, experience_id: "lesson", notes: [] };
    else data = { status: "done", report: REPORT };
    return { ok: true, json: async () => data };
  });
}

async function mount(plan = PLAN, onAdoptBundle: (bundle: ProductionSpecBundle) => void = () => undefined) {
  const { EvolutionPanel } = await import("./EvolutionPanel");
  const view = render(<EvolutionPanel plan={plan} t={t} active onAdoptBundle={onAdoptBundle} />);
  fireEvent.click(screen.getByText(t("evolutionTitle")).closest("summary")!);
  return { ...view, EvolutionPanel };
}

beforeEach(() => { localStorage.clear(); requests = []; fetchFixture(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

describe("feedback evolution confirmation", () => {
  it("starts no work until the user confirms the reviewed experiment", async () => {
    const adopted: ProductionSpecBundle[] = [];
    await mount(PLAN, (bundle) => adopted.push(bundle));
    expect(requests).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: t("evolutionPreview") }));
    await screen.findByRole("dialog");
    expect(within(screen.getByRole("dialog")).getByRole("list").textContent).toContain("启动 Godot 并生成独立候选");
    expect(requests.filter((item) => item.body?.confirmed === true)).toEqual([]);
    expect(requests[0].body?.confirmed).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: t("evolutionConfirmStart") }));
    await screen.findByRole("button", { name: t("evolutionAdopt") });
    expect(requests.filter((item) => item.body?.confirmed === true)).toHaveLength(1);
    expect(adopted).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: t("evolutionAdopt") }));
    await waitFor(() => expect(adopted[0]?.numeric?.pressure_clock_seconds).toBe(720));
  });

  it("cancels the confirmation without executing", async () => {
    await mount();
    fireEvent.click(screen.getByRole("button", { name: t("evolutionPreview") }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: t("generateConfirmCancel") }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(requests.filter((item) => item.body?.confirmed === true)).toEqual([]);
  });

  it("invalidates a reviewed experiment when the plan changes", async () => {
    const { rerender, EvolutionPanel } = await mount();
    fireEvent.click(screen.getByRole("button", { name: t("evolutionPreview") }));
    await screen.findByRole("dialog");
    rerender(<EvolutionPanel plan={WINNER} t={t} active onAdoptBundle={() => undefined} />);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(requests.filter((item) => item.body?.confirmed === true)).toEqual([]);
  });

  it("restores a report by reading without replaying the experiment", async () => {
    localStorage.setItem("fantasy-agent.evolution.active-experiment", "evolution-test");
    await mount();
    await screen.findByRole("button", { name: t("evolutionAdopt") });
    expect(requests.length).toBeGreaterThan(0);
    expect(requests.every((item) => item.method === "GET")).toBe(true);
  });

  it("shows a failed read instead of an empty experience library", async () => {
    fetchFixture(true);
    await mount();
    fireEvent.click(screen.getByRole("button", { name: t("evolutionReadExperience") }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("记录无法读取"));
  });

  it("applies a retrieved experience only on the user action", async () => {
    const adopted: ProductionSpecBundle[] = [];
    await mount(PLAN, (bundle) => adopted.push(bundle));
    fireEvent.click(screen.getByRole("button", { name: t("evolutionReadExperience") }));
    await screen.findByRole("button", { name: t("evolutionApplyExperience") });
    expect(adopted).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: t("evolutionApplyExperience") }));
    expect(adopted[0]?.numeric?.pressure_clock_seconds).toBe(720);
    expect(requests.every((item) => !item.body?.confirmed)).toBe(true);
  });

  it("shows the measured failure and project so the operator can rework it", async () => {
    localStorage.setItem("fantasy-agent.evolution.active-experiment", "evolution-test");
    vi.stubGlobal("fetch", async () => ({ ok: true, json: async () => ({
      status: "done", report: { ...REPORT, status: "manual_rework", best_iteration: null,
        iterations: [{ ...REPORT.iterations[0], report: {
          project_dir: "generated/godot/sessions/baseline/roof",
          aggregate: { runs: 0, wins: 0 },
          findings: [{ code: "engine_missing", message: "未找到 Godot，请配置工具环境。", rework_target: "flags" }]
        } }]
      }
    }) }));
    await mount();
    expect(await screen.findByText("未找到 Godot，请配置工具环境。")).toBeTruthy();
    expect(screen.getByText("generated/godot/sessions/baseline/roof")).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("evolutionAdopt") })).toBeNull();
  });

  it("keeps cancellation available when a running job cannot be read", async () => {
    vi.stubGlobal("fetch", async (input: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : undefined;
      requests.push({ path: String(input), method: init?.method ?? "GET", body });
      if (String(input).endsWith("/run")) return { ok: true, json: async () => body?.confirmed
        ? { status: "running", job_id: "job-test", experiment_id: "evolution-test" }
        : { status: "confirmation_required", planned_side_effects: ["启动 Godot"] } };
      if (String(input).endsWith("/cancel")) return { ok: true, json: async () => ({ status: "cancelling" }) };
      return { ok: false, status: 503, json: async () => ({ detail: "连接中断" }) };
    });
    await mount();
    fireEvent.click(screen.getByRole("button", { name: t("evolutionPreview") }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: t("evolutionConfirmStart") }));
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: t("evolutionPreview") })).toHaveProperty("disabled", true);
    fireEvent.click(screen.getByRole("button", { name: t("stopJob") }));
    await waitFor(() => expect(requests.some((item) => item.path.endsWith("/cancel"))).toBe(true));
  });
});
