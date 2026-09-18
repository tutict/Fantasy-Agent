export type Locale = "en" | "zh-CN";
export type Theme = "light" | "dark";

export type StatusState = "idle" | "ready" | "running" | "error";
export type CorrectionMode = "gameplay" | "visuals" | "scope" | "import";
export type ManualTargetId = "planning" | "comfyui" | "blender" | "unreal" | "godot" | "generated" | "engine";

export type EnemyBehavior = "patrol" | "chase" | "stationary" | "ranged";

export interface EnemySpec {
  name?: string;
  behavior?: EnemyBehavior;
  hp?: number;
  count?: number;
}

export interface EnemyPressureTuning {
  enemy_count_multiplier: number;
  move_speed_multiplier: number;
  detection_radius_multiplier: number;
  patrol_radius_multiplier: number;
  ranged_interval_multiplier: number;
}

export interface GameplaySpec {
  title?: string;
  logline?: string;
  target_session_minutes?: number;
  player_fantasy?: string;
  design_pillars?: string[];
  core_verbs?: string[];
  win_state?: string;
  failure_states?: string[];
  core_loop?: Array<{ order?: number; action?: string; player_decision?: string; feedback?: string }>;
  systems?: Array<{
    name?: string;
    purpose?: string;
    inputs?: string[];
    outputs?: string[];
    failure_pressure?: string;
  }>;
  progression?: {
    first_minute?: string;
    midpoint_shift?: string;
    final_minutes?: string;
    unlocks?: string[];
  };
  level_beats?: Array<{
    name?: string;
    duration_minutes?: number;
    gameplay_focus?: string;
    required_assets?: string[];
    success_condition?: string;
  }>;
  asset_needs?: string[];
  qa_focus?: string[];
  enemies?: EnemySpec[];
  i18n?: {
    field_translations?: {
      title?: Partial<Record<Locale, string>>;
    };
  };
}

export interface PipelineStage {
  id?: string;
  order?: number;
  title?: string;
  title_i18n?: Partial<Record<Locale, string>>;
  status?: string;
  owner_agent?: string;
  purpose?: string;
  quality_gates?: string[];
  risks?: string[];
  requires_confirmation?: boolean;
  mcp_tools?: string[];
  /** `"human"` marks a gate no tool may run in; the contract defaults to `"agent"`. */
  kind?: string;
  /**
   * Stage ids that must reach `done` before this stage becomes `ready`. The
   * backend has always sent this and the type silently dropped it, so no panel
   * could render the one field an orchestrator gates on.
   */
  depends_on?: string[];
}

export interface ProductionPipeline {
  project_name?: string;
  goal?: string;
  current_stage?: string;
  next_stage?: string;
  stages?: PipelineStage[];
}

export interface TaskItem {
  id?: string;
  agent?: string;
  title?: string;
  title_i18n?: Partial<Record<Locale, string>>;
  purpose?: string;
  status?: string;
  requires_confirmation?: boolean;
  depends_on?: string[];
  side_effects?: string[];
}

export interface TaskBreakdown {
  goal?: string;
  goal_i18n?: Partial<Record<Locale, string>>;
  recommended_next_task?: string;
  tasks?: TaskItem[];
}

export interface CreativeReviewItem {
  asset_id?: string;
  approval_status?: string;
  user_prompt?: string;
  asset_path?: string;
  source?: string;
  gameplay_role?: string;
}

export interface CreativeReview {
  items?: CreativeReviewItem[];
  art_direction?: {
    visual_intent?: string;
    user_review_questions?: string[];
  };
  required_user_decisions?: string[];
  approval_gate?: string;
}

export interface ApprovalManifestResponse {
  status?: string;
  manifest_path?: string;
  production_spec_bundle?: ProductionSpecBundle;
  manifest?: {
    approved_asset_ids?: string[];
    revision_asset_ids?: string[];
    rejected_asset_ids?: string[];
    pending_asset_ids?: string[];
  };
}

export interface UnrealPlan {
  engine_version?: string;
  maps?: string[];
  gameplay_classes?: string[];
  folders?: string[];
  automation_steps?: string[];
}

export interface GodotPlan {
  engine_version?: string;
  scenes?: string[];
  scripts?: string[];
  automation_steps?: string[];
}

export interface BlenderPlan {
  jobs?: Array<{ asset_name?: string; purpose?: string; export_path?: string }>;
}

export interface ComfyPlan {
  jobs?: Array<{ job_id?: string; gameplay_constraint?: string; workflow_template?: string }>;
  usage_rules?: string[];
}

export interface QaPlan {
  smoke_tests?: string[];
  playability_checks?: string[];
  failure_checks?: string[];
  packaging_checks?: string[];
}

export interface GddDocument {
  markdown_by_locale?: Partial<Record<Locale | "en", string>>;
  markdown?: string;
}

export interface SpecValidationIssue {
  severity?: "error" | "warning";
  spec?: string;
  field?: string;
  message?: string;
}

export interface SpecValidationReport {
  status?: "passed" | "warning" | "failed";
  issues?: SpecValidationIssue[];
  coverage?: Record<string, boolean>;
}

export interface ProductionSpecBundle {
  schema_version?: string;
  gameplay_spec_title?: string;
  combat?: {
    encounters?: Array<{ encounter_id?: string; beat?: string; enemy_roles?: string[] }>;
    enemy_roles?: string[];
    damage_model?: Record<string, number>;
  } | null;
  level?: {
    teaching_segment?: { name?: string; duration_minutes?: number };
    mid_segments?: Array<{ name?: string; duration_minutes?: number }>;
    final_test?: { name?: string; duration_minutes?: number };
    objective_gates?: string[];
  };
  numeric?: {
    player_move_speed?: number;
    player_hp?: number;
    target_session_minutes?: number;
    pressure_clock_seconds?: number;
    qa_risks?: string[];
  };
  narrative?: {
    premise?: string;
    beats?: Array<{ beat_id?: string; level_beat?: string; objective_copy?: string }>;
    hud_text?: Record<string, string>;
  };
  config_tables?: {
    tables?: Array<{ table_id?: string; format?: string; primary_key?: string; export_path?: string; rows?: Array<Record<string, unknown>> }>;
  };
  resource_pipeline?: {
    assets?: Array<{ asset_id?: string; approval_status?: string; engine_destination?: string; blocked_reason?: string | null }>;
    blocked_assets?: string[];
    approval_manifest_path?: string;
  };
  validation?: SpecValidationReport | null;
  handoff_artifacts?: string[];
}

export interface CompiledSpecArtifact {
  path?: string;
  media_type?: string;
  content?: string;
}

export interface SpecTraceRecord {
  spec_field?: string;
  artifact_path?: string;
  consumer?: string;
}

export interface ExecutableQAResult {
  assertion_id?: string;
  metric_key?: string;
  passed?: boolean;
  actual?: unknown;
  expected?: unknown;
  severity?: "error" | "warning";
  message?: string;
}

export interface SpecBundlePreviewResponse {
  validation?: SpecValidationReport;
  artifacts?: CompiledSpecArtifact[];
  traces?: SpecTraceRecord[];
  executable_qa?: {
    status?: "passed" | "warning" | "failed";
    results?: ExecutableQAResult[];
  };
}

export interface DirectorBuildPlan {
  gameplay_spec?: GameplaySpec;
  production_spec_bundle?: ProductionSpecBundle;
  production_pipeline?: ProductionPipeline;
  task_breakdown?: TaskBreakdown;
  creative_review?: CreativeReview;
  unreal_plan?: UnrealPlan;
  godot_plan?: GodotPlan;
  blender_plan?: BlenderPlan;
  comfyui_plan?: ComfyPlan;
  qa_plan?: QaPlan;
  gdd?: GddDocument;
  next_actions?: string[];
}

export interface PlanningHandoff {
  schemaVersion?: string;
  source?: string;
  savedAt?: string | null;
  title?: string;
  plan?: DirectorBuildPlan;
  invalid?: boolean;
}

export interface ManualCorrectionTarget {
  id: ManualTargetId;
  label?: string;
  status?: "ready" | "degraded" | "unavailable" | string;
  target?: string;
  openable?: boolean;
  detail?: string;
  detail_key?: string;
}

export interface ManualTargetsPayload {
  engine_kind?: "godot" | "unreal";
  targets?: ManualCorrectionTarget[];
}

export interface ExecutePreview {
  status?: string;
  engine?: string;
  planned_side_effects?: string[];
}

export interface ExecuteStart {
  status?: string;
  job_id?: string;
  engine?: string;
  /** Session this run belongs to; reuse it with `resume_from` to re-run one node. */
  session_id?: string;
}

export interface ApprovalGateMetadata {
  manifest_path?: string;
  report_path?: string;
  approved_assets?: string[];
  skipped_assets?: string[];
  approved_asset_ids?: string[];
  revision_asset_ids?: string[];
  rejected_asset_ids?: string[];
  pending_asset_ids?: string[];
  blocked_reason?: string;
}

export interface ExecuteStage {
  name?: string;
  status?: string;
  detail?: string;
  artifacts?: string[];
  logs?: string[];
  metadata?: ApprovalGateMetadata & Record<string, unknown>;
}

export interface ExecuteResult {
  status?: string;
  session_id?: string;
  project_dir?: string;
  stages?: ExecuteStage[];
}

export interface ExecuteJob {
  job_id?: string;
  status?: string;
  result?: ExecuteResult;
  error?: string;
}

/** One recorded stage of a previous run; the basis for node-level rework. */
export interface SessionStageState {
  name?: string;
  status?: string;
  detail?: string;
  artifacts?: string[];
  logs?: string[];
  finished_at?: string;
}

export interface SessionState {
  session_id?: string;
  engine?: string;
  found?: boolean;
  project_dir?: string;
  updated_at?: string;
  stage_order?: string[];
  stages?: SessionStageState[];
  done?: string[];
  failed?: string[];
}

export interface JobCancelResponse {
  job_id?: string;
  status?: string;
}

export type AssetExecutePreview = ExecutePreview;
export type AssetExecuteStart = ExecuteStart;
export type AssetExecuteJob = ExecuteJob;

export interface McpService {
  id?: string;
  label?: string;
  status?: "ready" | "degraded" | "unavailable" | string;
  target?: string;
  detail?: string;
  next_action?: string;
  detail_key?: string;
  next_action_key?: string;
  detail_args?: Record<string, unknown>;
  next_action_args?: Record<string, unknown>;
  required?: boolean;
  /**
   * Extra backend detail about how the status was reached -- for Unreal this
   * carries the `UnrealEditor.exe` that `target` was resolved from, so a reader
   * can tell a headless `-Cmd` build from a GUI-only install.
   */
  metadata?: Record<string, unknown>;
}

export interface McpStatus {
  status?: string;
  engine?: string;
  engine_kind?: string;
  required_ready?: number;
  required_total?: number;
  services?: McpService[];
}

/** UI-safe view of the LLM API settings: the raw key is never sent to the browser. */
export interface LlmApiSettings {
  enabled?: boolean;
  provider?: string;
  base_url?: string;
  model?: string;
  timeout_seconds?: number;
  api_key_masked?: string;
  api_key_configured?: boolean;
  api_key_source?: string;
  ready?: boolean;
  config_path?: string;
}

export interface LlmApiTestResult {
  ok?: boolean;
  status?: string;
  latency_ms?: number;
  detail?: string;
  detail_key?: string;
  settings?: LlmApiSettings;
}

/** What the settings form sends. An empty key keeps the stored secret. */
export interface LlmApiSettingsInput {
  enabled: boolean;
  provider: string;
  base_url: string;
  model: string;
  api_key: string;
  timeout_seconds: number;
}

/**
 * Every grant defaults to off. The backend refuses tiers it was not given,
 * and only reveals tools up to the granted tier, so the toggles here are the
 * only way a run can write files or launch an engine.
 */
export interface AgentRunRequest {
  goal: string;
  max_turns?: number;
  include_engine_tools?: boolean;
  allow_write?: boolean;
  allow_execute?: boolean;
}

export interface AgentStepCall {
  name: string;
  arguments?: Record<string, unknown>;
  status: string;
  content: string;
}

export interface AgentStep {
  text: string;
  calls: AgentStepCall[];
}

export interface AgentRunResult {
  status?: string;
  answer?: string;
  tool_calls?: number;
  refusals?: string[];
  error?: string;
  steps?: AgentStep[];
}

/**
 * Planning workbench types.
 *
 * The workbench calls ``POST /api/tools/{tool_name}`` (see
 * ``apps/studio/app/main.py::_workbench_tool``). Every tool answers with the
 * same envelope: a flat ``{structuredContent, content, _meta}`` object when
 * called over REST, though an embedding host may wrap it under ``result``.
 */

export type WorkbenchToolName =
  | "extract_idea_seed"
  | "decompose_production_tasks"
  | "generate_game_production_plan"
  | "render_gdd"
  | "prepare_production_pipeline"
  | "prepare_unreal_plan"
  | "prepare_godot_plan"
  | "prepare_blender_plan"
  | "prepare_comfyui_plan"
  | "prepare_creative_review_plan"
  | "prepare_qa_plan";

export type WorkbenchPanelKey =
  | "overview"
  | "pipeline"
  | "tasks"
  | "build"
  | "visuals"
  | "gdd"
  | "qa"
  | "dsl";

export interface InterviewAnswer {
  question_id: string;
  question: string;
  answer: string;
}

export interface IdeaSeed {
  source?: string;
  schema_version?: string;
  raw_idea?: string;
  player_fantasy?: string;
  emotional_target?: string;
  core_action?: string;
  tension_source?: string;
  must_keep?: string[];
  can_cut?: string[];
  reference_feel?: string;
  playable_loop_candidate?: string;
  constraints?: string[];
  open_questions?: string[];
  next_prompt?: string;
}

/** Editable configuration shared by every plan tool payload. */
export interface WorkbenchConfig {
  targetMinutes: number;
  engineVersion: string;
  platform: string;
  sourceLocale: Locale;
  constraints: string[];
}

/** Payload for ``extract_idea_seed``. Mirrors ``IdeaDiscoveryRequest``. */
export interface IdeaDiscoveryRequest {
  raw_idea: string;
  answers?: InterviewAnswer[];
  target_minutes?: number;
  engine_version?: string;
  platforms?: string[];
  constraints?: string[];
  source_locale?: Locale;
  output_locales?: Locale[];
}

/** Payload for every plan-building tool. Mirrors ``PromptRequest``. */
export interface PromptRequest {
  prompt: string;
  target_minutes?: number;
  engine_version?: string;
  platforms?: string[];
  jam_scope?: boolean;
  constraints?: string[];
  source_locale?: Locale;
  output_locales?: Locale[];
}

export interface WorkbenchStructured {
  kind?: string;
  summary?: Record<string, unknown>;
  idea_seed?: IdeaSeed;
  prompt_request?: PromptRequest;
  plan?: DirectorBuildPlan;
  task_breakdown?: TaskBreakdown;
  production_pipeline?: ProductionPipeline;
  gdd?: GddDocument;
  unreal_plan?: UnrealPlan;
  godot_plan?: GodotPlan;
  blender_plan?: BlenderPlan;
  comfyui_plan?: ComfyPlan;
  creative_review?: CreativeReview;
  qa_plan?: QaPlan;
  gameplay_title?: string;
}

export interface WorkbenchMeta {
  toolName?: string;
  activePanel?: WorkbenchPanelKey;
  ideaSeed?: IdeaSeed;
  promptRequest?: PromptRequest;
  plan?: DirectorBuildPlan;
  taskBreakdown?: TaskBreakdown;
  productionPipeline?: ProductionPipeline;
  gdd?: GddDocument;
  unrealPlan?: UnrealPlan;
  godotPlan?: GodotPlan;
  blenderPlan?: BlenderPlan;
  comfyuiPlan?: ComfyPlan;
  creativeReview?: CreativeReview;
  qaPlan?: QaPlan;
}

export interface WorkbenchToolResult {
  isError?: boolean;
  structuredContent?: WorkbenchStructured;
  content?: Array<{ type?: string; text?: string }>;
  _meta?: WorkbenchMeta;
  /** Present only when an embedding host wraps the envelope. */
  result?: Omit<WorkbenchToolResult, "result">;
}
