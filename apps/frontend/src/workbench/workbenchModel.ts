/**
 * Pure model for the planning workbench.
 *
 * Everything here is a plain function with no DOM and no React: the interview
 * state machine, how an edited idea becomes an ``IdeaSeed``, how a seed becomes
 * the ``PromptRequest`` every plan tool expects, and how a tool envelope is
 * unpacked. Keeping it out of the component makes the behaviour testable
 * without mounting anything.
 */

import type {
  DirectorBuildPlan,
  IdeaDiscoveryRequest,
  IdeaSeed,
  InterviewAnswer,
  Locale,
  PromptRequest,
  WorkbenchConfig,
  WorkbenchMeta,
  WorkbenchStructured,
  WorkbenchToolResult
} from "../shared/types";

export { type WorkbenchConfig } from "../shared/types";

/** Backend bounds for ``PromptRequest.target_minutes`` (5..15 inclusive). */
export const MIN_TARGET_MINUTES = 5;
export const MAX_TARGET_MINUTES = 15;

/** ``PromptRequest.prompt`` must be at least this long. */
export const MIN_PROMPT_LENGTH = 8;
/** ``IdeaDiscoveryRequest.raw_idea`` must be at least this long. */
export const MIN_RAW_IDEA_LENGTH = 4;

export const MAX_CHAT_LENGTH = 2000;

export interface InterviewQuestion {
  id: string;
  text: string;
}

/** Raw textarea values collected by the seed inspector. */
export interface SeedEditorFields {
  rawIdea: string;
  playerFantasy: string;
  emotionalTarget: string;
  coreAction: string;
  tensionSource: string;
  mustKeep: string;
  canCut: string;
  referenceFeel: string;
  playableLoop: string;
}

export const EMPTY_SEED_FIELDS: SeedEditorFields = {
  rawIdea: "",
  playerFantasy: "",
  emotionalTarget: "",
  coreAction: "",
  tensionSource: "",
  mustKeep: "",
  canCut: "",
  referenceFeel: "",
  playableLoop: ""
};

export function defaultConfig(): WorkbenchConfig {
  return {
    targetMinutes: 10,
    engineVersion: "UE5",
    platform: "Windows",
    sourceLocale: "en",
    constraints: []
  };
}

export function clampTargetMinutes(value: number | string | undefined | null): number {
  const parsed = typeof value === "number" ? value : Number(value ?? 10);
  if (!Number.isFinite(parsed)) return 10;
  return Math.min(MAX_TARGET_MINUTES, Math.max(MIN_TARGET_MINUTES, Math.round(parsed)));
}

/** Split a textarea into a clean list. Accepts newline, half/full-width comma and semicolon. */
export function splitLines(value: string | undefined | null): string[] {
  return String(value ?? "")
    .split(/[\n,，;；]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function joinLines(items: string[] | undefined | null): string {
  return (items ?? []).join("\n");
}

/**
 * The six interview questions. They are local, not server-driven: the backend
 * only consumes them as ``IdeaDiscoveryRequest.answers``.
 */
export function interviewQuestions(locale: Locale): InterviewQuestion[] {
  if (locale === "zh-CN") {
    return [
      { id: "player_fantasy", text: "玩家在这个游戏里最想成为谁，或者最想完成什么幻想？" },
      { id: "core_action", text: "玩家进入游戏前 30 秒，应该立刻做的第一个动作是什么？" },
      { id: "emotional_target", text: "你希望玩家主要感受到紧张、掌控、探索、破坏、解谜，还是表演？" },
      { id: "tension_source", text: "失败来自哪里？时间压力、空间危险、敌人、资源，还是判断错误？" },
      { id: "must_keep", text: "哪些机制或表达必须保留？用逗号分隔即可。" },
      { id: "can_cut", text: "为了 5 到 15 分钟 demo，哪些内容可以先砍掉？" }
    ];
  }
  return [
    {
      id: "player_fantasy",
      text: "Who should the player feel they are becoming, or what fantasy must they perform?"
    },
    {
      id: "core_action",
      text: "What is the first concrete action the player should perform in the first 30 seconds?"
    },
    {
      id: "emotional_target",
      text: "Should the player mainly feel tension, mastery, exploration, destruction, puzzle-solving, or performance?"
    },
    {
      id: "tension_source",
      text: "Where does failure come from: time pressure, spatial danger, enemies, resources, or misreading the situation?"
    },
    { id: "must_keep", text: "Which mechanics or expressions must be preserved? A comma-separated list is fine." },
    { id: "can_cut", text: "For a 5 to 15 minute demo, what can be cut first?" }
  ];
}

/** The question the user is currently on, or null once every question is answered. */
export function currentInterviewQuestion(
  answers: InterviewAnswer[],
  locale: Locale
): InterviewQuestion | null {
  return interviewQuestions(locale)[answers.length] ?? null;
}

export function isInterviewComplete(answers: InterviewAnswer[], locale: Locale): boolean {
  return currentInterviewQuestion(answers, locale) === null;
}

/**
 * Fold one chat message into the answer list. Answers beyond the scripted six
 * are still kept (capped at 10) and tagged ``extra_context`` so the backend
 * can use them as free-form context.
 */
export function appendInterviewAnswer(
  answers: InterviewAnswer[],
  question: InterviewQuestion | null,
  answer: string,
  locale: Locale
): InterviewAnswer[] {
  const trimmed = answer.trim();
  if (!trimmed) return answers;
  const entry: InterviewAnswer = {
    question_id: question?.id ?? "extra_context",
    question: question?.text ?? interviewQuestions(locale)[0]?.text ?? "",
    answer: trimmed
  };
  return [...answers, entry].slice(0, 10);
}

const DEFAULT_REFERENCE_FEEL =
  "Readable dark techno greybox with clear routes, hazards, objectives, and feedback.";

const DEFAULT_CAN_CUT = ["large open world", "AAA art polish", "online multiplayer"];

export function inferredLoop(coreAction: string, tensionSource: string, playerFantasy: string, rawIdea: string): string {
  const action = coreAction || "perform the core movement";
  const tension = tensionSource || "read risk, recover quickly, and retry";
  const fantasy = playerFantasy || rawIdea || "the player fantasy";
  return `${fantasy}: ${action}; face ${tension}; reach the objective, learn from failure, and improve the next attempt.`;
}

/** Rebuild an ``IdeaSeed`` from whatever is currently in the editor. */
export function seedFromEditor(
  fields: SeedEditorFields,
  config: WorkbenchConfig,
  previous?: IdeaSeed | null
): IdeaSeed {
  const rawIdea = fields.rawIdea.trim();
  const playerFantasy = fields.playerFantasy.trim();
  const emotionalTarget = fields.emotionalTarget.trim();
  const coreAction = fields.coreAction.trim();
  const tensionSource = fields.tensionSource.trim();
  const mustKeep = splitLines(fields.mustKeep);
  const canCut = splitLines(fields.canCut);
  const referenceFeel = fields.referenceFeel.trim() || DEFAULT_REFERENCE_FEEL;
  const playableLoop =
    fields.playableLoop.trim() || inferredLoop(coreAction, tensionSource, playerFantasy, rawIdea);
  const constraints = config.constraints ?? [];
  const keep = mustKeep.length ? mustKeep : splitLines(coreAction || rawIdea);
  const cut = canCut.length ? canCut : DEFAULT_CAN_CUT;
  const minutes = clampTargetMinutes(config.targetMinutes);

  return {
    ...(previous ?? {}),
    source: "idea-discovery-agent",
    schema_version: "0.1",
    raw_idea: rawIdea || playerFantasy,
    player_fantasy: playerFantasy,
    emotional_target: emotionalTarget,
    core_action: coreAction,
    tension_source: tensionSource,
    must_keep: keep,
    can_cut: cut,
    reference_feel: referenceFeel,
    playable_loop_candidate: playableLoop,
    constraints,
    open_questions: previous?.open_questions ?? [],
    next_prompt: [
      `Create a ${minutes}-minute ${config.engineVersion || "UE5"} playable prototype from this idea seed.`,
      `Player fantasy: ${playerFantasy}.`,
      `Emotional target: ${emotionalTarget}.`,
      `Core action: ${coreAction}.`,
      `Tension source: ${tensionSource}.`,
      `Playable loop: ${playableLoop}.`,
      `Must keep: ${keep.join(", ")}.`,
      `Can cut: ${cut.join(", ")}.`,
      `Reference feel: ${referenceFeel}.`,
      "Prioritize a coherent greybox loop over visual polish."
    ].join(" ")
  };
}

/** A confirmed seed is the source of the prompt; otherwise the raw chat text is. */
export function requestPayload(
  fields: SeedEditorFields,
  config: WorkbenchConfig,
  seed: IdeaSeed | null,
  seedConfirmed: boolean
): PromptRequest {
  if (seed && seedConfirmed) {
    return promptRequestFromEditor(seed, config);
  }
  return {
    prompt: fields.rawIdea.trim(),
    target_minutes: clampTargetMinutes(config.targetMinutes),
    engine_version: config.engineVersion || "UE5",
    platforms: [config.platform || "Windows"],
    jam_scope: true,
    constraints: config.constraints ?? [],
    source_locale: config.sourceLocale ?? "en",
    output_locales: ["en", "zh-CN"]
  };
}

export function promptRequestFromEditor(seed: IdeaSeed, config: WorkbenchConfig): PromptRequest {
  return {
    prompt: seed.next_prompt ?? "",
    target_minutes: clampTargetMinutes(config.targetMinutes),
    engine_version: config.engineVersion || "UE5",
    platforms: [config.platform || "Windows"],
    jam_scope: true,
    constraints: seed.constraints ?? [],
    source_locale: config.sourceLocale ?? "en",
    output_locales: ["en", "zh-CN"]
  };
}

export function ideaDiscoveryPayload(
  request: PromptRequest,
  rawIdea: string,
  answers: InterviewAnswer[]
): IdeaDiscoveryRequest {
  return {
    raw_idea: rawIdea.trim(),
    answers,
    target_minutes: request.target_minutes,
    engine_version: request.engine_version,
    platforms: request.platforms,
    constraints: request.constraints,
    source_locale: request.source_locale,
    output_locales: request.output_locales
  };
}

/** The seed is only complete enough to confirm once the three core fields exist. */
export function canConfirmSeed(fields: SeedEditorFields): boolean {
  return Boolean(
    fields.playerFantasy.trim() && fields.coreAction.trim() && fields.tensionSource.trim()
  );
}

export function canGenerate(seed: IdeaSeed | null, seedConfirmed: boolean): boolean {
  return Boolean(seed && seedConfirmed);
}

type LocalizedValue = string | { en?: string; "zh-CN"?: string } | null | undefined;

/** Plan lists may hold either a plain string or an ``{en, "zh-CN"}`` pair. */
export function localizedValue(value: LocalizedValue, locale: Locale): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return (locale === "zh-CN" ? value["zh-CN"] : value.en) ?? value.en ?? value["zh-CN"] ?? "";
}

export function localizedArray(items: unknown, locale: Locale): string[] {
  if (!Array.isArray(items)) return [];
  return items.map((item) => localizedValue(item as LocalizedValue, locale));
}

/**
 * Pipeline stages and task items carry ``title_i18n`` instead of a localized
 * array, so they need their own helper.
 */
export function localizedTitle(
  item: { title?: string; title_i18n?: Partial<Record<Locale, string>> } | null | undefined,
  locale: Locale
): string {
  if (!item) return "";
  const translated = item.title_i18n?.[locale];
  if (translated) return translated;
  return item.title ?? "";
}

export function planDisplayTitle(plan: DirectorBuildPlan | null | undefined, locale: Locale): string {
  const spec = plan?.gameplay_spec;
  if (!spec) return "";
  const translations = (
    spec as { i18n?: { field_translations?: Record<string, Partial<Record<Locale, string>>> } }
  ).i18n?.field_translations;
  if (locale === "zh-CN") {
    const translated = translations?.title?.["zh-CN"];
    if (translated) return translated;
  }
  return spec.title ?? "";
}

/**
 * True when the pipeline was planned for Godot. Drives which engine plan the
 * build panel shows.
 */
export function usesGodotEngine(plan: DirectorBuildPlan | null | undefined): boolean {
  return Boolean(
    plan?.production_pipeline?.stages?.some((stage) => stage.id === "godot_quick_play")
  );
}

export interface NormalizedToolResult {
  structured: WorkbenchStructured;
  meta: WorkbenchMeta;
  text: string;
  toolName: string;
}

/**
 * Unwrap a tool envelope. Over REST the backend answers with a flat
 * ``{structuredContent, content, _meta}`` object, but an embedding host may
 * wrap that under ``result``, so both shapes are accepted.
 */
export function normalizeToolResult(result: WorkbenchToolResult | null | undefined): NormalizedToolResult {
  const wrapped = (result?.result ?? result ?? {}) as Omit<WorkbenchToolResult, "result">;
  const structured = wrapped.structuredContent ?? {};
  const meta = wrapped._meta ?? {};
  const text = (wrapped.content ?? [])
    .map((entry) => entry?.text ?? "")
    .filter(Boolean)
    .join("\n");
  return { structured, meta, text, toolName: meta.toolName ?? structured.kind ?? "" };
}

/**
 * Which panel a result should jump to. The backend says so in ``_meta``; each
 * tool also has a sensible fallback so a result never lands on a blank panel.
 */
export const TOOL_FALLBACK_PANEL: Record<string, string> = {
  extract_idea_seed: "overview",
  generate_game_production_plan: "overview",
  decompose_production_tasks: "tasks",
  render_gdd: "gdd",
  prepare_production_pipeline: "pipeline",
  prepare_unreal_plan: "build",
  prepare_godot_plan: "build",
  prepare_blender_plan: "build",
  prepare_comfyui_plan: "visuals",
  prepare_creative_review_plan: "visuals",
  prepare_qa_plan: "qa"
};

export function resultPanel(toolName: string, meta: WorkbenchMeta): string {
  return meta.activePanel ?? TOOL_FALLBACK_PANEL[toolName] ?? "overview";
}
