/**
 * The six plan panels the flow console and the planning workbench share.
 *
 * These existed twice: once in `console/rendering.tsx` and once in
 * `workbench/PlanPanels.tsx`. The two copies did not render the same fields --
 * the console's overview showed `target_session_minutes` and `next_actions`
 * and the workbench's showed `logline` and `level_beats`, sharing only four of
 * ten -- so "one panel implemented once" could not be reached by deleting
 * either copy. The agreed shape is the union: every panel renders everything
 * both entries used to show.
 *
 * Because of that union, a panel here may call a translation key that only one
 * of the two dictionaries defines. `shared/panelI18n.test.ts` holds the exact
 * list of those keys and fails when it grows, which is what keeps a merged
 * panel from rendering a raw key name to an operator.
 */

import type {
  ComfyPlan,
  CreativeReview,
  DirectorBuildPlan,
  IdeaSeed,
  Locale,
  PipelineStage,
  QaPlan,
  TaskBreakdown,
  TaskItem
} from "../types";
import { localizedTitle, usesGodotEngine } from "../planModel";
import { Block, ListBlock, Pill, PillRow, TextBlock } from "./primitives";

export type Translator = (key: string, args?: Record<string, unknown>) => string;

/**
 * The overview is the one panel that has to work before a plan exists: the
 * workbench shows the captured idea seed while the console shows nothing,
 * because the console only ever receives a finished handoff.
 */
export function OverviewPanel({
  plan,
  seed,
  locale,
  t
}: {
  plan?: DirectorBuildPlan | null;
  seed?: IdeaSeed | null;
  locale: Locale;
  t: Translator;
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
    const decision = step.player_decision ? ` -- ${step.player_decision}` : "";
    return `${action}${decision}`;
  });
  const beats = (spec?.level_beats ?? []).map((beat) => {
    const minutes = beat.duration_minutes ? `${beat.duration_minutes}m` : "";
    return [beat.name, minutes, beat.gameplay_focus].filter(Boolean).join(" / ");
  });

  return (
    <div className="wb-block-grid" id="overview-content">
      <TextBlock title={t("logline")} body={spec?.logline} wide />
      <TextBlock title={t("session")} body={`${spec?.target_session_minutes ?? "-"} ${t("minutes")}`} />
      <ListBlock title={t("gameplayLoop")} items={loop} wide />
      <ListBlock title={t("coreVerbs")} items={spec?.core_verbs ?? []} />
      <ListBlock title={t("pillars")} items={spec?.design_pillars ?? []} />
      <ListBlock
        title={t("systems")}
        items={(spec?.systems ?? []).map((system) => system.name ?? "")}
      />
      <ListBlock title={t("pacing")} items={beats} wide />
      <TextBlock title={t("win")} body={spec?.win_state} />
      <ListBlock title={t("failure")} items={spec?.failure_states ?? []} />
      <ListBlock title={t("assetNeeds")} items={spec?.asset_needs ?? []} />
      <ListBlock title={t("qaFocus")} items={spec?.qa_focus ?? []} />
      <ListBlock title={t("next")} items={plan.next_actions ?? []} wide />
    </div>
  );
}

function StageRow({ stage, locale, t }: { stage: PipelineStage; locale: Locale; t: Translator }) {
  return (
    <div className="wb-row">
      <h4>{`${String(stage.order ?? 0).padStart(2, "0")} ${localizedTitle(stage, locale)}`}</h4>
      <p>{stage.purpose}</p>
      <PillRow>
        <Pill>{stage.status}</Pill>
        {stage.kind === "human" ? <Pill variant="human">{t("humanGate")}</Pill> : null}
        {stage.owner_agent ? <Pill>{`${t("owner")}: ${stage.owner_agent}`}</Pill> : null}
        {stage.requires_confirmation ? <Pill variant="warn">{t("confirmation")}</Pill> : null}
        {stage.depends_on?.length ? (
          <Pill>{`${t("dependencies")}: ${stage.depends_on.join(", ")}`}</Pill>
        ) : null}
        {stage.mcp_tools?.length ? (
          <Pill>{`${t("tools")}: ${stage.mcp_tools.join(", ")}`}</Pill>
        ) : null}
      </PillRow>
      {stage.quality_gates?.length ? (
        <PillRow>
          <Pill>{`${t("quality")}: ${stage.quality_gates.join(" / ")}`}</Pill>
        </PillRow>
      ) : null}
      {stage.risks?.length ? (
        <PillRow>
          <Pill>{`${t("risks")}: ${stage.risks.join(" / ")}`}</Pill>
        </PillRow>
      ) : null}
    </div>
  );
}

export function PipelinePanel({
  plan,
  locale,
  t
}: {
  plan?: DirectorBuildPlan | null;
  locale: Locale;
  t: Translator;
}) {
  const pipeline = plan?.production_pipeline;
  if (!pipeline) return <p className="wb-empty">{t("noPlan")}</p>;

  return (
    <div className="wb-block-grid" id="pipeline-output">
      <TextBlock title={t("projectGoal")} body={pipeline.goal} wide />
      <TextBlock title={t("recommended")} body={pipeline.next_stage ?? "-"} wide />
      <PillRow>
        <Pill>{pipeline.project_name}</Pill>
        <Pill>{`${t("currentStage")}: ${pipeline.current_stage ?? "-"}`}</Pill>
        <Pill>{`${t("nextStage")}: ${pipeline.next_stage ?? "-"}`}</Pill>
        <Pill>{t("stagesCount", { count: (pipeline.stages ?? []).length })}</Pill>
      </PillRow>
      {(pipeline.stages ?? []).map((stage) => (
        <StageRow key={stage.id ?? stage.title ?? stage.order} stage={stage} locale={locale} t={t} />
      ))}
    </div>
  );
}

function TaskRow({ task, locale, t }: { task: TaskItem; locale: Locale; t: Translator }) {
  return (
    <div className="wb-row">
      <h4>{localizedTitle(task, locale)}</h4>
      <p>{task.purpose}</p>
      <PillRow>
        <Pill>{task.status}</Pill>
        {task.id ? <Pill>{task.id}</Pill> : null}
        {task.agent ? <Pill>{task.agent}</Pill> : null}
        {task.requires_confirmation ? <Pill variant="warn">{t("confirmation")}</Pill> : null}
        {task.depends_on?.length ? (
          <Pill>{`${t("dependencies")}: ${task.depends_on.join(", ")}`}</Pill>
        ) : null}
        {task.side_effects?.length ? (
          <Pill>{`${t("sideEffects")}: ${task.side_effects.join(", ")}`}</Pill>
        ) : null}
      </PillRow>
    </div>
  );
}

/**
 * The console passes the breakdown it was handed, the workbench passes the
 * whole plan and reads the breakdown off it. Both are accepted so neither
 * entry point has to reshape its payload.
 */
export function TasksPanel({
  plan,
  breakdown,
  locale,
  t
}: {
  plan?: DirectorBuildPlan | null;
  breakdown?: TaskBreakdown | null;
  locale: Locale;
  t: Translator;
}) {
  const resolved = breakdown ?? plan?.task_breakdown;
  if (!resolved) return <div className="wb-block-grid" id="tasks-output" />;

  const goal = localizedTitle({ title: resolved.goal }, locale) || resolved.goal || "";
  return (
    <div className="wb-block-grid" id="tasks-output">
      <TextBlock
        title={t("recommended")}
        body={`${goal} -> ${resolved.recommended_next_task ?? "-"}`}
        wide
      />
      {(resolved.tasks ?? []).map((task) => (
        <TaskRow key={task.id ?? task.title} task={task} locale={locale} t={t} />
      ))}
    </div>
  );
}

/**
 * `locale` is optional: only the panels that localize a stage or task title
 * need it, and the console passes its own locale only where it matters. Panels
 * that do need it fall back to `en`, which is the same default the translator
 * uses.
 *
 * The engine list is the union of what both halves listed. The console split
 * the Unreal plan into four labelled blocks and the workbench folded it into
 * one, and the console's set is the larger one -- dropping `folders` or
 * `engine_version` would have quietly lost data the operator used to see.
 */
export function BuildPanel({
  plan,
  t
}: {
  plan?: DirectorBuildPlan | null;
  t: Translator;
}) {
  if (!plan) return <p className="wb-empty">{t("noPlan")}</p>;
  const godot = usesGodotEngine(plan);
  const engineItems = godot
    ? [
        ...(plan.godot_plan?.engine_version ? [plan.godot_plan.engine_version] : []),
        ...(plan.godot_plan?.scenes ?? []),
        ...(plan.godot_plan?.scripts ?? []),
        ...(plan.godot_plan?.automation_steps ?? [])
      ]
    : [
        ...(plan.unreal_plan?.engine_version ? [plan.unreal_plan.engine_version] : []),
        ...(plan.unreal_plan?.maps ?? []),
        ...(plan.unreal_plan?.gameplay_classes ?? []),
        ...(plan.unreal_plan?.folders ?? []),
        ...(plan.unreal_plan?.automation_steps ?? [])
      ];

  return (
    <div className="wb-block-grid" id="build-output">
      <ListBlock title={godot ? t("godot") : t("unreal")} items={engineItems} wide />
      <ListBlock
        title={t("blender")}
        items={(plan.blender_plan?.jobs ?? []).map((job) =>
          [job.asset_name, job.purpose, job.export_path].filter(Boolean).join(" / ")
        )}
        wide
      />
    </div>
  );
}

/**
 * The console hands in the two payloads it already extracted; the workbench
 * hands in the plan. Reading the plan as the fallback keeps both call shapes
 * working without either side reaching into the other's model.
 */
export function VisualsPanel({
  plan,
  comfy,
  review,
  t
}: {
  plan?: DirectorBuildPlan | null;
  comfy?: ComfyPlan | null;
  review?: CreativeReview | null;
  t: Translator;
}) {
  const resolvedComfy = comfy ?? plan?.comfyui_plan;
  const resolvedReview = review ?? plan?.creative_review;

  if (!resolvedComfy && !resolvedReview) {
    return <div className="wb-block-grid" id="visuals-output" />;
  }

  return (
    <div className="wb-block-grid" id="visuals-output">
      <TextBlock title={t("approvalGate")} body={resolvedReview?.approval_gate} wide />
      <ListBlock
        title={t("creativeReview")}
        items={(resolvedReview?.items ?? []).map((item) =>
          [item.asset_id, item.source, item.approval_status, item.asset_path]
            .filter(Boolean)
            .join(" / ")
        )}
        wide
      />
      <ListBlock
        title={t("reviewQuestions")}
        items={resolvedReview?.art_direction?.user_review_questions ?? []}
        wide
      />
      <ListBlock
        title={t("requiredDecisions")}
        items={resolvedReview?.required_user_decisions ?? []}
        wide
      />
      <ListBlock
        title={t("comfyui")}
        items={(resolvedComfy?.jobs ?? []).map((job) =>
          [job.job_id, job.gameplay_constraint, job.workflow_template].filter(Boolean).join(" / ")
        )}
        wide
      />
      <ListBlock title={t("rules")} items={resolvedComfy?.usage_rules ?? []} wide />
    </div>
  );
}

export function QaPanel({
  plan,
  qa,
  t
}: {
  plan?: DirectorBuildPlan | null;
  qa?: QaPlan | null;
  t: Translator;
}) {
  const resolved = qa ?? plan?.qa_plan;
  if (!resolved) return <div className="wb-block-grid" id="qa-output" />;

  return (
    <div className="wb-block-grid" id="qa-output">
      <ListBlock title={t("smoke")} items={resolved.smoke_tests ?? []} />
      <ListBlock title={t("playability")} items={resolved.playability_checks ?? []} />
      <ListBlock title={t("failure")} items={resolved.failure_checks ?? []} />
      <ListBlock title={t("packaging")} items={resolved.packaging_checks ?? []} />
    </div>
  );
}

export { Block, ListBlock, TextBlock };
