/**
 * Workbench-specific panel wiring.
 *
 * The five plan panels the workbench shares with the flow console now live
 * once, in `shared/panels/PlanPanels.tsx`, and are re-exported here so this
 * entry point's imports stay put. What remains is the workbench's own surface:
 * the GDD and DSL views, the tool-action grid, and the panel key order.
 *
 * The pipeline panel is not here any more. It was a stage *snapshot* -- the plan
 * as authored, with a status column that never moves -- and the orchestration
 * board (`src/orchestration/`) is where stages are rendered now, with the
 * runtime state the snapshot could not show. That is why `pipeline` is also
 * gone from `PANEL_KEYS`: a tab that opens a second, differently-wrong view of
 * the same object is worse than no tab.
 *
 * Every backend string lands in JSX text position, so React escapes it. The
 * retired static page hand-rolled `escapeHtml` for this; React makes that
 * unnecessary, which is the point of the rewrite.
 */

import type { IdeaSeed, DirectorBuildPlan } from "../shared/types";

export {
  BuildPanel,
  OverviewPanel,
  QaPanel,
  TasksPanel,
  VisualsPanel,
  type Translator
} from "../shared/panels/PlanPanels";

type Translator = (key: string, args?: Record<string, unknown>) => string;

export function GddPanel({
  plan,
  t,
  locale
}: {
  plan: DirectorBuildPlan | null;
  t: Translator;
  locale: "en" | "zh-CN";
}) {
  const gdd = plan?.gdd;
  const markdown =
    (locale === "zh-CN" ? gdd?.markdown_by_locale?.["zh-CN"] : undefined) ??
    gdd?.markdown_by_locale?.en ??
    gdd?.markdown ??
    "";
  if (!markdown) return <p className="wb-empty">{t("noPlan")}</p>;
  return <pre className="wb-pre">{markdown}</pre>;
}

export function DslPanel({
  plan,
  seed,
  t
}: {
  plan: DirectorBuildPlan | null;
  seed: IdeaSeed | null;
  t: Translator;
}) {
  const payload = plan?.gameplay_spec ?? seed;
  if (!payload) return <p className="wb-empty">{t("noPlan")}</p>;
  return <pre className="wb-pre">{JSON.stringify(payload, null, 2)}</pre>;
}

/**
 * Re-exported rather than defined here: `workbenchModel.resultPanel` validates
 * a tool result's panel against this list, and a second copy would be a second
 * answer to "which tabs exist".
 */
export { PANEL_KEYS } from "./workbenchModel";

/** Tools that share the plan payload; the retired page only wired three of these. */
export const PLAN_TOOLS: Array<{ tool: string; labelKey: string }> = [
  { tool: "generate_game_production_plan", labelKey: "toolGeneratePlan" },
  { tool: "decompose_production_tasks", labelKey: "toolDecomposeTasks" },
  { tool: "prepare_production_pipeline", labelKey: "toolPreparePipeline" },
  { tool: "render_gdd", labelKey: "toolRenderGdd" },
  { tool: "prepare_godot_plan", labelKey: "toolGodotPlan" },
  { tool: "prepare_unreal_plan", labelKey: "toolUnrealPlan" },
  { tool: "prepare_blender_plan", labelKey: "toolBlenderPlan" },
  { tool: "prepare_comfyui_plan", labelKey: "toolComfyuiPlan" },
  { tool: "prepare_creative_review_plan", labelKey: "toolCreativeReview" },
  { tool: "prepare_qa_plan", labelKey: "toolQaPlan" }
];

export function ToolActions({
  t,
  enabled,
  busy,
  running,
  onRun
}: {
  t: Translator;
  enabled: boolean;
  busy: boolean;
  running: string | null;
  onRun: (tool: string) => void;
}) {
  return (
    <section className="wb-card" aria-label={t("toolActions")}>
      <header className="wb-card-head">
        <div>
          <h2>{t("toolActions")}</h2>
          <p>{t("toolActionsHint")}</p>
        </div>
      </header>
      <div className="wb-card-body">
        <div className="wb-tool-grid">
          {PLAN_TOOLS.map(({ tool, labelKey }) => (
            <button
              key={tool}
              type="button"
              className={`wb-button${running === tool ? " active" : ""}`}
              data-tool={tool}
              disabled={busy || !enabled}
              onClick={() => onRun(tool)}
            >
              {t(labelKey)}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
