/**
 * The five plan panels the flow console and the planning workbench share.
 *
 * These existed twice: once in `console/rendering.tsx` and once in
 * `workbench/PlanPanels.tsx`. The two copies did not render the same fields --
 * the console's overview showed `target_session_minutes` and `next_actions`
 * and the workbench's showed `logline` and `level_beats`, sharing only four of
 * ten -- so "one panel implemented once" could not be reached by deleting
 * either copy. The agreed shape is the union: every panel renders everything
 * both entries used to show.
 *
 * A sixth panel used to live here: `PipelinePanel`, which rendered
 * `production_pipeline.stages` as a list of stage rows. It is not shared any
 * more, it is *gone* -- stage rows are the orchestration board's job
 * (`src/orchestration/`), which renders the run state a plan-time row cannot
 * show. See the F3 section of `docs/superpowers/plans/2026-09-16-frontend-ui-replan.md`.
 *
 * Because of the union, a panel here may call a translation key that only one
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
  QaPlan,
  TaskBreakdown,
  TaskItem
} from "../types";
import { localizedArray, localizedTitle, planningText, planDisplayTitle, specFieldText, usesGodotEngine } from "../planModel";
import { BlenderScriptPanel } from "./BlenderScriptPanel";
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
  const field = (path: string, value: string | undefined) => specFieldText(spec, path, value, locale);
  const fields = (path: string, values: string[] | undefined) =>
    (values ?? []).map((value, index) => field(`${path}.${index}`, value));
  const loop = (spec?.core_loop ?? []).map((step, index) => {
    const action = field(`core_loop.${index}.action`, step.action);
    const decision = step.player_decision ? ` -- ${field(`core_loop.${index}.player_decision`, step.player_decision)}` : "";
    return `${action}${decision}`;
  });
  const beats = (spec?.level_beats ?? []).map((beat, index) => {
    const minutes = beat.duration_minutes ? (locale === "zh-CN" ? `${beat.duration_minutes} ${t("minutes")}` : `${beat.duration_minutes}m`) : "";
    return [field(`level_beats.${index}.name`, beat.name), minutes, field(`level_beats.${index}.gameplay_focus`, beat.gameplay_focus)].filter(Boolean).join(" / ");
  });

  return (
    <div className="wb-block-grid" id="overview-content">
      <TextBlock title={t("logline")} body={field("logline", spec?.logline)} wide />
      <TextBlock title={t("session")} body={`${spec?.target_session_minutes ?? "-"} ${t("minutes")}`} />
      <ListBlock title={t("gameplayLoop")} items={loop} wide />
      <ListBlock title={t("coreVerbs")} items={fields("core_verbs", spec?.core_verbs)} />
      <ListBlock title={t("pillars")} items={fields("design_pillars", spec?.design_pillars)} />
      <ListBlock
        title={t("systems")}
        items={(spec?.systems ?? []).map((system, index) => field(`systems.${index}.name`, system.name))}
      />
      <ListBlock title={t("pacing")} items={beats} wide />
      <TextBlock title={t("win")} body={field("win_state", spec?.win_state)} />
      <ListBlock title={t("failure")} items={fields("failure_states", spec?.failure_states)} />
      <ListBlock title={t("assetNeeds")} items={fields("asset_needs", spec?.asset_needs)} />
      <ListBlock title={t("qaFocus")} items={fields("qa_focus", spec?.qa_focus)} />
      <ListBlock title={t("next")} items={localizedArray(plan.next_actions, locale)} wide />
    </div>
  );
}

function TaskRow({ task, locale, t }: { task: TaskItem; locale: Locale; t: Translator }) {
  return (
    <div className="wb-row">
      <h4>{localizedTitle(task, locale)}</h4>
      <p>{planningText(task.purpose, locale)}</p>
      <PillRow>
        <Pill>{planningText(task.status, locale)}</Pill>
        {task.id ? <Pill>{task.id}</Pill> : null}
        {task.agent ? <Pill>{planningText(task.agent, locale)}</Pill> : null}
        {task.requires_confirmation ? <Pill variant="warning">{t("confirmation")}</Pill> : null}
        {task.depends_on?.length ? (
          <Pill>{`${t("dependencies")}: ${task.depends_on.join(", ")}`}</Pill>
        ) : null}
        {task.side_effects?.length ? (
          <Pill>{`${t("sideEffects")}: ${localizedArray(task.side_effects, locale).join(", ")}`}</Pill>
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

  let goal = localizedTitle({ title: resolved.goal, title_i18n: resolved.goal_i18n }, locale);
  const originalTitle = plan?.gameplay_spec?.title;
  if (locale === "zh-CN" && originalTitle) goal = goal.replaceAll(originalTitle, planDisplayTitle(plan, locale));
  const nextTask = resolved.tasks?.find((task) => task.id === resolved.recommended_next_task);
  const nextTitle = locale === "zh-CN" && nextTask ? localizedTitle(nextTask, locale) : resolved.recommended_next_task;
  return (
    <div className="wb-block-grid" id="tasks-output">
      <TextBlock
        title={t("recommended")}
        body={`${goal} -> ${nextTitle ?? "-"}`}
        wide
      />
      {(resolved.tasks ?? []).map((task) => (
        <TaskRow key={task.id ?? task.title} task={task} locale={locale} t={t} />
      ))}
    </div>
  );
}

/**
 * `locale` is optional for callers inspecting the original plan. Both app
 * entry points pass the interface locale so planning prose can be localized.
 *
 * The engine list is the union of what both halves listed. The console split
 * the Unreal plan into four labelled blocks and the workbench folded it into
 * one, and the console's set is the larger one -- dropping `folders` or
 * `engine_version` would have quietly lost data the operator used to see.
 */
export function BuildPanel({
  plan,
  locale = "en",
  t
}: {
  plan?: DirectorBuildPlan | null;
  locale?: Locale;
  t: Translator;
}) {
  if (!plan) return <p className="wb-empty">{t("noPlan")}</p>;
  const godot = usesGodotEngine(plan);
  const engineItems = godot
    ? [
        ...(plan.godot_plan?.engine_version ? [plan.godot_plan.engine_version] : []),
        ...(plan.godot_plan?.scenes ?? []),
        ...(plan.godot_plan?.scripts ?? []),
        ...localizedArray(plan.godot_plan?.automation_steps, locale)
      ]
    : [
        ...(plan.unreal_plan?.engine_version ? [plan.unreal_plan.engine_version] : []),
        ...(plan.unreal_plan?.maps ?? []),
        ...(plan.unreal_plan?.gameplay_classes ?? []),
        ...(plan.unreal_plan?.folders ?? []),
        ...localizedArray(plan.unreal_plan?.automation_steps, locale)
      ];

  return (
    <div className="wb-build" id="build-output">
      <div className="wb-block-grid">
        <ListBlock title={godot ? t("godot") : t("unreal")} items={engineItems} wide />
        <ListBlock
          title={t("blender")}
          items={(plan.blender_plan?.jobs ?? []).map((job) =>
            [job.asset_name, planningText(job.purpose, locale), job.export_path].filter(Boolean).join(" / ")
          )}
          wide
        />
      </div>
      <BlenderScriptPanel plan={plan.blender_plan} t={t} />
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
  locale = "en",
  t
}: {
  plan?: DirectorBuildPlan | null;
  comfy?: ComfyPlan | null;
  review?: CreativeReview | null;
  locale?: Locale;
  t: Translator;
}) {
  const resolvedComfy = comfy ?? plan?.comfyui_plan;
  const resolvedReview = review ?? plan?.creative_review;

  if (!resolvedComfy && !resolvedReview) {
    return <div className="wb-block-grid" id="visuals-output" />;
  }

  return (
    <div className="wb-block-grid" id="visuals-output">
      <TextBlock title={t("approvalGate")} body={planningText(resolvedReview?.approval_gate, locale)} wide />
      <ListBlock
        title={t("creativeReview")}
        items={(resolvedReview?.items ?? []).map((item) =>
          [item.asset_id, item.source, planningText(item.approval_status, locale), item.asset_path]
            .filter(Boolean)
            .join(" / ")
        )}
        wide
      />
      <ListBlock
        title={t("reviewQuestions")}
        items={localizedArray(resolvedReview?.art_direction?.user_review_questions, locale)}
        wide
      />
      <ListBlock
        title={t("requiredDecisions")}
        items={localizedArray(resolvedReview?.required_user_decisions, locale)}
        wide
      />
      <ListBlock
        title={t("comfyui")}
        items={(resolvedComfy?.jobs ?? []).map((job) =>
          [job.job_id, planningText(job.gameplay_constraint, locale), job.workflow_template].filter(Boolean).join(" / ")
        )}
        wide
      />
      <ListBlock title={t("rules")} items={localizedArray(resolvedComfy?.usage_rules, locale)} wide />
    </div>
  );
}

export function QaPanel({
  plan,
  qa,
  locale = "en",
  t
}: {
  plan?: DirectorBuildPlan | null;
  qa?: QaPlan | null;
  locale?: Locale;
  t: Translator;
}) {
  const resolved = qa ?? plan?.qa_plan;
  if (!resolved) return <div className="wb-block-grid" id="qa-output" />;

  return (
    <div className="wb-block-grid" id="qa-output">
      <ListBlock title={t("smoke")} items={localizedArray(resolved.smoke_tests, locale)} />
      <ListBlock title={t("playability")} items={localizedArray(resolved.playability_checks, locale)} />
      <ListBlock title={t("failure")} items={(resolved.failure_checks ?? []).map((value) => {
        const index = plan?.gameplay_spec?.failure_states?.indexOf(value) ?? -1;
        return index >= 0 ? specFieldText(plan?.gameplay_spec, `failure_states.${index}`, value, locale) : planningText(value, locale);
      })} />
      <ListBlock title={t("packaging")} items={localizedArray(resolved.packaging_checks, locale)} />
    </div>
  );
}

export { Block, ListBlock, TextBlock };
