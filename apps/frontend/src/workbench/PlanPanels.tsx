/**
 * Plan panels for the workbench.
 *
 * Every backend string lands in JSX text position, so React escapes it. The
 * retired static page hand-rolled `escapeHtml` for this; React makes that
 * unnecessary, which is the point of the rewrite.
 */

import type {
  DirectorBuildPlan,
  IdeaSeed,
  Locale,
  PipelineStage,
  TaskItem,
  WorkbenchPanelKey
} from "../shared/types";
import { localizedTitle, usesGodotEngine } from "./workbenchModel";

export type Translator = (key: string, args?: Record<string, unknown>) => string;

function Block({ title, wide, children }: { title: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <section className={`wb-block${wide ? " wide" : ""}`}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function ListBlock({
  title,
  items,
  wide
}: {
  title: string;
  items: string[];
  wide?: boolean;
}) {
  return (
    <Block title={title} wide={wide}>
      {items.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>-</p>
      )}
    </Block>
  );
}

function TextBlock({ title, body, wide }: { title: string; body?: string; wide?: boolean }) {
  return (
    <Block title={title} wide={wide}>
      <p>{body || "-"}</p>
    </Block>
  );
}

export function OverviewPanel({
  plan,
  seed,
  t,
  locale
}: {
  plan: DirectorBuildPlan | null;
  seed: IdeaSeed | null;
  t: Translator;
  locale: Locale;
}) {
  if (!plan) {
    if (!seed) {
      return <p className="wb-empty">{t("noPlan")}</p>;
    }
    return (
      <div className="wb-block-grid">
        <TextBlock title={t("playerFantasy")} body={seed.player_fantasy} />
        <TextBlock title={t("coreAction")} body={seed.core_action} />
        <TextBlock
          title={t("confirmRequired")}
          body={seed.next_prompt || t("confirmRequired")}
          wide
        />
      </div>
    );
  }

  const spec = plan.gameplay_spec;
  const loop = (spec?.core_loop ?? []).map((step) => {
    const action = step.action ?? "";
    const decision = step.player_decision ? ` — ${step.player_decision}` : "";
    return `${action}${decision}`;
  });
  const beats = (spec?.level_beats ?? []).map((beat) => {
    const minutes = beat.duration_minutes ? `${beat.duration_minutes}m` : "";
    return [beat.name, minutes, beat.gameplay_focus].filter(Boolean).join(" · ");
  });

  return (
    <div className="wb-block-grid">
      <TextBlock title={t("logline")} body={spec?.logline} wide />
      <ListBlock title={t("gameplayLoop")} items={loop} wide />
      <ListBlock title={t("coreVerbs")} items={spec?.core_verbs ?? []} />
      <ListBlock title={t("designPillars")} items={spec?.design_pillars ?? []} />
      <ListBlock
        title={t("systems")}
        items={(spec?.systems ?? []).map((system) => system.name ?? "")}
      />
      <ListBlock title={t("pacing")} items={beats} wide />
      <TextBlock title={t("winState")} body={spec?.win_state} />
      <ListBlock title={t("failureStates")} items={spec?.failure_states ?? []} />
      <ListBlock title={t("assetNeeds")} items={spec?.asset_needs ?? []} />
      <ListBlock title={t("qaFocus")} items={spec?.qa_focus ?? []} />
    </div>
  );
}

function StageRow({ stage, t, locale }: { stage: PipelineStage; t: Translator; locale: Locale }) {
  return (
    <div className="wb-row">
      <h4>
        {String(stage.order ?? 0).padStart(2, "0")} {localizedTitle(stage, locale)}
      </h4>
      <p>{stage.purpose}</p>
      <div className="wb-meta">
        <span className="wb-pill">{stage.status}</span>
        {stage.kind === "human" ? <span className="wb-pill human">{t("humanGate")}</span> : null}
        {stage.owner_agent ? <span className="wb-pill">{stage.owner_agent}</span> : null}
        {stage.requires_confirmation ? (
          <span className="wb-pill warn">{t("confirmation")}</span>
        ) : null}
        {stage.depends_on?.length ? (
          <span className="wb-pill">
            {t("dependencies")}: {stage.depends_on.join(", ")}
          </span>
        ) : null}
        {stage.mcp_tools?.length ? (
          <span className="wb-pill">
            {t("tools")}: {stage.mcp_tools.join(", ")}
          </span>
        ) : null}
      </div>
      {stage.quality_gates?.length ? (
        <div className="wb-meta">
          <span className="wb-pill">
            {t("quality")}: {stage.quality_gates.join(" / ")}
          </span>
        </div>
      ) : null}
      {stage.risks?.length ? (
        <div className="wb-meta">
          <span className="wb-pill">
            {t("risks")}: {stage.risks.join(" / ")}
          </span>
        </div>
      ) : null}
    </div>
  );
}

export function PipelinePanel({
  plan,
  t,
  locale
}: {
  plan: DirectorBuildPlan | null;
  t: Translator;
  locale: Locale;
}) {
  const pipeline = plan?.production_pipeline;
  if (!pipeline) return <p className="wb-empty">{t("noPlan")}</p>;

  return (
    <>
      <TextBlock title={t("projectGoal")} body={pipeline.goal} wide />
      <TextBlock title={t("recommended")} body={pipeline.next_stage ?? "-"} wide />
      <div className="wb-meta">
        <span className="wb-pill">{pipeline.project_name}</span>
        <span className="wb-pill">
          {t("currentStage")}: {pipeline.current_stage ?? "-"}
        </span>
        <span className="wb-pill">{t("stagesCount", { count: (pipeline.stages ?? []).length })}</span>
      </div>
      {(pipeline.stages ?? []).map((stage) => (
        <StageRow key={stage.id ?? stage.title ?? stage.order} stage={stage} t={t} locale={locale} />
      ))}
    </>
  );
}

function TaskRow({ task, t, locale }: { task: TaskItem; t: Translator; locale: Locale }) {
  return (
    <div className="wb-row">
      <h4>{localizedTitle(task, locale)}</h4>
      <p>{task.purpose}</p>
      <div className="wb-meta">
        <span className="wb-pill">{task.status}</span>
        {task.agent ? <span className="wb-pill">{task.agent}</span> : null}
        {task.requires_confirmation ? (
          <span className="wb-pill warn">{t("confirmation")}</span>
        ) : null}
        {task.depends_on?.length ? (
          <span className="wb-pill">
            {t("dependencies")}: {task.depends_on.join(", ")}
          </span>
        ) : null}
        {task.side_effects?.length ? (
          <span className="wb-pill">
            {t("sideEffects")}: {task.side_effects.join(", ")}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function TasksPanel({
  plan,
  t,
  locale
}: {
  plan: DirectorBuildPlan | null;
  t: Translator;
  locale: Locale;
}) {
  const breakdown = plan?.task_breakdown;
  if (!breakdown) return <p className="wb-empty">{t("noPlan")}</p>;

  return (
    <>
      <TextBlock
        title={t("recommended")}
        body={`${localizedTitle({ title: breakdown.goal }, locale) || breakdown.goal || ""} → ${
          breakdown.recommended_next_task ?? "-"
        }`}
        wide
      />
      {(breakdown.tasks ?? []).map((task) => (
        <TaskRow key={task.id ?? task.title} task={task} t={t} locale={locale} />
      ))}
    </>
  );
}

export function BuildPanel({
  plan,
  t,
  locale
}: {
  plan: DirectorBuildPlan | null;
  t: Translator;
  locale: Locale;
}) {
  if (!plan) return <p className="wb-empty">{t("noPlan")}</p>;
  const godot = usesGodotEngine(plan);
  const engineItems = godot
    ? [
        ...(plan.godot_plan?.scenes ?? []),
        ...(plan.godot_plan?.scripts ?? []),
        ...(plan.godot_plan?.automation_steps ?? [])
      ]
    : [
        ...(plan.unreal_plan?.maps ?? []),
        ...(plan.unreal_plan?.gameplay_classes ?? []),
        ...(plan.unreal_plan?.automation_steps ?? [])
      ];

  return (
    <div className="wb-block-grid">
      <ListBlock title={godot ? t("godot") : t("unreal")} items={engineItems} wide />
      <ListBlock
        title={t("blender")}
        items={(plan.blender_plan?.jobs ?? []).map((job) =>
          [job.asset_name, job.purpose, job.export_path].filter(Boolean).join(" · ")
        )}
        wide
      />
    </div>
  );
}

export function VisualsPanel({ plan, t }: { plan: DirectorBuildPlan | null; t: Translator }) {
  if (!plan) return <p className="wb-empty">{t("noPlan")}</p>;
  const review = plan.creative_review;

  return (
    <div className="wb-block-grid">
      <TextBlock title={t("approvalGate")} body={review?.approval_gate} wide />
      <ListBlock
        title={t("creativeReview")}
        items={(review?.items ?? []).map((item) =>
          [item.asset_id, item.source, item.approval_status, item.asset_path]
            .filter(Boolean)
            .join(" · ")
        )}
        wide
      />
      <ListBlock
        title={t("reviewQuestions")}
        items={review?.art_direction?.user_review_questions ?? []}
        wide
      />
      <ListBlock
        title={t("comfyui")}
        items={(plan.comfyui_plan?.jobs ?? []).map((job) =>
          [job.job_id, job.gameplay_constraint, job.workflow_template].filter(Boolean).join(" · ")
        )}
        wide
      />
    </div>
  );
}

export function GddPanel({
  plan,
  t,
  locale
}: {
  plan: DirectorBuildPlan | null;
  t: Translator;
  locale: Locale;
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

export function QaPanel({ plan, t }: { plan: DirectorBuildPlan | null; t: Translator }) {
  const qa = plan?.qa_plan;
  if (!qa) return <p className="wb-empty">{t("noPlan")}</p>;
  return (
    <div className="wb-block-grid">
      <ListBlock title={t("smoke")} items={qa.smoke_tests ?? []} />
      <ListBlock title={t("playability")} items={qa.playability_checks ?? []} />
      <ListBlock title={t("failure")} items={qa.failure_checks ?? []} />
      <ListBlock title={t("packaging")} items={qa.packaging_checks ?? []} />
    </div>
  );
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

export const PANEL_KEYS: WorkbenchPanelKey[] = [
  "overview",
  "pipeline",
  "tasks",
  "build",
  "visuals",
  "gdd",
  "qa",
  "dsl"
];

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

