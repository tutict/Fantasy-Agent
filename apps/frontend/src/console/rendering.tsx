import type { ReactElement, ReactNode } from "react";
import type {
  BlenderPlan,
  ComfyPlan,
  CreativeReview,
  CreativeReviewItem,
  DirectorBuildPlan,
  GodotPlan,
  Locale,
  QaPlan,
  TaskBreakdown,
  TaskItem,
  UnrealPlan
} from "../shared/types";

export type Translator = (key: string) => string;

export function preferredTitle(plan: DirectorBuildPlan | undefined, locale: Locale, t: Translator): string {
  const spec = plan?.gameplay_spec;
  if (!spec) return t("emptyTitle");
  return locale === "zh-CN" && spec.i18n?.field_translations?.title?.["zh-CN"]
    ? spec.i18n.field_translations.title["zh-CN"] ?? t("emptyTitle")
    : spec.title ?? t("emptyTitle");
}

export function localizedStageTitle(
  stage: { title?: string; title_i18n?: Partial<Record<Locale, string>> },
  locale: Locale
): string {
  return locale === "zh-CN"
    ? stage.title_i18n?.["zh-CN"] || stage.title || "-"
    : stage.title_i18n?.en || stage.title || "-";
}

export function localizedTaskTitle(task: TaskItem, locale: Locale): string {
  return locale === "zh-CN"
    ? task.title_i18n?.["zh-CN"] || task.title || "-"
    : task.title_i18n?.en || task.title || "-";
}

export function usesGodotEngine(plan: DirectorBuildPlan | null | undefined): boolean {
  return Boolean(plan?.production_pipeline?.stages?.some((stage) => stage.id === "godot_quick_play"));
}

export function selectedEngineVersion(plan: DirectorBuildPlan | null): string {
  if (!plan) return "UE5";
  return usesGodotEngine(plan) ? plan.godot_plan?.engine_version || "Godot 4" : plan.unreal_plan?.engine_version || "UE5";
}

export function statusLabel(status: string | undefined, t: Translator): string {
  if (status === "approved") return t("approved");
  if (status === "needs_revision") return t("needsRevision");
  if (status === "rejected") return t("rejected");
  if (status === "pending_user_review") return t("pendingReview");
  return status || "-";
}

export function list(items: unknown[] | undefined, t: Translator): ReactElement {
  if (!items?.length) return <p>{t("noItems")}</p>;
  return (
    <ul>
      {items.map((item, index) => (
        <li key={`${String(item)}-${index}`}>{String(item)}</li>
      ))}
    </ul>
  );
}

export function numbered<T>(
  items: T[] | undefined,
  t: Translator,
  renderItem: (item: T, index: number) => ReactNode
): ReactElement {
  if (!items?.length) return <p>{t("noItems")}</p>;
  return <ol>{items.map((item, index) => <li key={index}>{renderItem(item, index)}</li>)}</ol>;
}

export function SummaryBlock({
  title,
  wide,
  children
}: {
  title: string;
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={`summary-block${wide ? " wide" : ""}`}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export function GateItem({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="gate-item">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

export function OverviewPanel({ plan, locale, t }: { plan: DirectorBuildPlan; locale: Locale; t: Translator }) {
  const spec = plan.gameplay_spec;
  if (!spec) return null;
  return (
    <div className="overview-grid" id="overview-content">
      <SummaryBlock title={t("session")}>
        <p>
          {spec.target_session_minutes ?? "-"} {t("minutes")}
        </p>
      </SummaryBlock>
      <SummaryBlock title={t("win")}>
        <p>{spec.win_state || "-"}</p>
      </SummaryBlock>
      <SummaryBlock title={t("pillars")}>{list(spec.design_pillars, t)}</SummaryBlock>
      <SummaryBlock title={t("failure")}>{list(spec.failure_states, t)}</SummaryBlock>
      <SummaryBlock title={t("loop")} wide>
        {numbered(spec.core_loop, t, (step) => (
          <>
            <strong>{step.action || "-"}</strong>
            <br />
            <span>{step.player_decision || "-"}</span>
          </>
        ))}
      </SummaryBlock>
      <SummaryBlock title={t("systems")} wide>
        {numbered(spec.systems, t, (system) => (
          <>
            <strong>{system.name || "-"}</strong>
            <br />
            <span>{system.purpose || "-"}</span>
          </>
        ))}
      </SummaryBlock>
      <SummaryBlock title={t("next")} wide>
        {list(plan.next_actions, t)}
      </SummaryBlock>
    </div>
  );
}

export function PipelinePanel({ plan, locale, t }: { plan: DirectorBuildPlan; locale: Locale; t: Translator }) {
  const pipeline = plan.production_pipeline;
  if (!pipeline) return <div className="pipeline-board" id="pipeline-output" />;
  return (
    <div className="pipeline-board" id="pipeline-output">
      <section className="stage-row wide">
        <h3>{pipeline.project_name}</h3>
        <p>{pipeline.goal}</p>
        <div className="stage-meta">
          <span className="stage-pill">
            {t("currentStage")}: {pipeline.current_stage}
          </span>
          <span className="stage-pill">
            {t("nextStage")}: {pipeline.next_stage}
          </span>
        </div>
      </section>
      {(pipeline.stages || []).map((stage) => (
        <section className="stage-row" key={stage.id || stage.order}>
          <h3>
            {String(stage.order ?? "").padStart(2, "0")} {localizedStageTitle(stage, locale)}
          </h3>
          <p>{stage.purpose}</p>
          <div className="stage-meta">
            <span className={`stage-pill ${stage.status || ""}`}>{stage.status}</span>
            <span className="stage-pill">
              {t("owner")}: {stage.owner_agent}
            </span>
            {stage.requires_confirmation ? <span className="stage-pill">{t("confirmation")}</span> : null}
            {stage.mcp_tools?.length ? (
              <span className="stage-pill">
                {t("tools")}: {stage.mcp_tools.join(", ")}
              </span>
            ) : null}
          </div>
          <h3>{t("quality")}</h3>
          {list(stage.quality_gates, t)}
          {stage.risks?.length ? (
            <>
              <h3>{t("risks")}</h3>
              {list(stage.risks, t)}
            </>
          ) : null}
        </section>
      ))}
    </div>
  );
}

export function TasksPanel({ breakdown, locale, t }: { breakdown?: TaskBreakdown; locale: Locale; t: Translator }) {
  if (!breakdown) return <div className="task-board" id="tasks-output" />;
  const goal = locale === "zh-CN" ? breakdown.goal_i18n?.["zh-CN"] || breakdown.goal : breakdown.goal_i18n?.en || breakdown.goal;
  return (
    <div className="task-board" id="tasks-output">
      <section className="task-row">
        <div>
          <h3>{goal}</h3>
          <p>
            {t("recommended")}: {breakdown.recommended_next_task}
          </p>
        </div>
        <span className="task-pill">{breakdown.tasks?.length || 0}</span>
      </section>
      {(breakdown.tasks || []).map((task) => (
        <section className="task-row" key={task.id}>
          <div>
            <h3>{localizedTaskTitle(task, locale)}</h3>
            <p>{task.purpose}</p>
            <div className="task-meta">
              <span className={`task-pill ${task.status || ""}`}>{task.status}</span>
              <span className="task-pill">{task.id}</span>
              <span className="task-pill">{task.agent}</span>
              {task.requires_confirmation ? <span className="task-pill">{t("confirmation")}</span> : null}
              {task.depends_on?.length ? (
                <span className="task-pill">
                  {t("dependencies")}: {task.depends_on.length}
                </span>
              ) : null}
              {task.side_effects?.length ? (
                <span className="task-pill">
                  {t("sideEffects")}: {task.side_effects.length}
                </span>
              ) : null}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}

export function ReviewPanel({
  review,
  decisions,
  setDecision,
  t
}: {
  review?: CreativeReview;
  decisions: Record<string, string>;
  setDecision: (assetId: string, decision: string) => void;
  t: Translator;
}) {
  const items = review?.items || [];
  return (
    <div className="review-layout">
      <div className="review-board" id="review-output">
        {items.length ? (
          items.map((item) => <ReviewItem key={item.asset_id} item={item} decision={decisions[item.asset_id || ""] || item.approval_status || ""} setDecision={setDecision} t={t} />)
        ) : (
          <section className="review-item">
            <div>
              <h3>{t("creativeReview")}</h3>
              <p>{t("noItems")}</p>
            </div>
          </section>
        )}
      </div>
      <aside className="review-inspector" id="review-inspector">
        {review ? (
          <>
            <h3>{t("artDirection")}</h3>
            <p>{review.art_direction?.visual_intent}</p>
            <h3>{t("reviewQuestions")}</h3>
            {list(review.art_direction?.user_review_questions, t)}
            <h3>{t("requiredDecisions")}</h3>
            {list(review.required_user_decisions, t)}
            <div className="review-meta">
              <span className="review-pill">
                {t("approvalGate")}: {review.approval_gate}
              </span>
            </div>
          </>
        ) : null}
      </aside>
    </div>
  );
}

function ReviewItem({
  item,
  decision,
  setDecision,
  t
}: {
  item: CreativeReviewItem;
  decision: string;
  setDecision: (assetId: string, decision: string) => void;
  t: Translator;
}) {
  const actions: Array<[string, string]> = [
    ["approved", t("approve")],
    ["needs_revision", t("revise")],
    ["rejected", t("reject")]
  ];
  return (
    <section className="review-item">
      <div>
        <h3>{item.asset_id}</h3>
        <p>{item.user_prompt}</p>
        <code>{item.asset_path}</code>
        <div className="review-meta">
          <span className={`review-pill ${decision}`}>{statusLabel(decision, t)}</span>
          <span className="review-pill">{item.source}</span>
          <span className="review-pill">{item.gameplay_role}</span>
        </div>
      </div>
      <div className="review-actions">
        {actions.map(([value, label]) => (
          <button
            className={`review-action ${decision === value ? "active" : ""}`}
            type="button"
            data-asset-id={item.asset_id}
            data-decision={value}
            key={value}
            onClick={() => item.asset_id && setDecision(item.asset_id, value)}
          >
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}

export function BuildPanel({ plan, t }: { plan: DirectorBuildPlan; t: Translator }) {
  const godotIsPrimary = usesGodotEngine(plan);
  const unreal = godotIsPrimary ? undefined : plan.unreal_plan;
  const godot = godotIsPrimary ? plan.godot_plan : undefined;
  return (
    <div className="split-output" id="build-output">
      {unreal ? <UnrealBlocks unreal={unreal} t={t} /> : null}
      {godot ? <GodotBlocks godot={godot} t={t} /> : null}
      {plan.blender_plan ? <BlenderBlocks blender={plan.blender_plan} t={t} /> : null}
    </div>
  );
}

function UnrealBlocks({ unreal, t }: { unreal: UnrealPlan; t: Translator }) {
  return (
    <>
      <SummaryBlock title={t("maps")}>{list(unreal.maps, t)}</SummaryBlock>
      <SummaryBlock title={t("classes")}>{list(unreal.gameplay_classes, t)}</SummaryBlock>
      <SummaryBlock title={t("folders")}>{list(unreal.folders, t)}</SummaryBlock>
      <SummaryBlock title={t("automation")}>{list(unreal.automation_steps, t)}</SummaryBlock>
    </>
  );
}

function GodotBlocks({ godot, t }: { godot: GodotPlan; t: Translator }) {
  return (
    <SummaryBlock title={t("godot")} wide>
      {list(godot.scenes, t)}
      {list(godot.scripts, t)}
      {list(godot.automation_steps, t)}
    </SummaryBlock>
  );
}

function BlenderBlocks({ blender, t }: { blender: BlenderPlan; t: Translator }) {
  return (
    <SummaryBlock title={t("blender")} wide>
      {numbered(blender.jobs, t, (job) => (
        <>
          <strong>{job.asset_name}</strong>
          <br />
          <span>{job.purpose}</span>
          <br />
          <code>{job.export_path}</code>
        </>
      ))}
    </SummaryBlock>
  );
}

export function VisualsPanel({ comfy, review, t }: { comfy?: ComfyPlan; review?: CreativeReview; t: Translator }) {
  return (
    <div className="split-output" id="visuals-output">
      {comfy ? (
        <>
          <SummaryBlock title={t("jobs")} wide>
            {numbered(comfy.jobs, t, (job) => (
              <>
                <strong>{job.job_id}</strong>
                <br />
                <span>{job.gameplay_constraint}</span>
                <br />
                <code>{job.workflow_template}</code>
              </>
            ))}
          </SummaryBlock>
          <SummaryBlock title={t("rules")} wide>
            {list(comfy.usage_rules, t)}
          </SummaryBlock>
        </>
      ) : null}
      {review ? (
        <SummaryBlock title={t("creativeReview")} wide>
          {list(review.required_user_decisions, t)}
        </SummaryBlock>
      ) : null}
    </div>
  );
}

export function QaPanel({ qa, t }: { qa?: QaPlan; t: Translator }) {
  return (
    <div className="split-output" id="qa-output">
      {qa ? (
        <>
          <SummaryBlock title={t("smoke")}>{list(qa.smoke_tests, t)}</SummaryBlock>
          <SummaryBlock title={t("playability")}>{list(qa.playability_checks, t)}</SummaryBlock>
          <SummaryBlock title={t("failure")}>{list(qa.failure_checks, t)}</SummaryBlock>
          <SummaryBlock title={t("packaging")}>{list(qa.packaging_checks, t)}</SummaryBlock>
        </>
      ) : null}
    </div>
  );
}
