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
  target_session_minutes?: number;
  design_pillars?: string[];
  win_state?: string;
  failure_states?: string[];
  core_loop?: Array<{ action?: string; player_decision?: string }>;
  systems?: Array<{ name?: string; purpose?: string }>;
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

export interface DirectorBuildPlan {
  gameplay_spec?: GameplaySpec;
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
}

export interface ExecuteStage {
  name?: string;
  status?: string;
  detail?: string;
  artifacts?: string[];
  logs?: string[];
}

export interface ExecuteResult {
  status?: string;
  project_dir?: string;
  stages?: ExecuteStage[];
}

export interface ExecuteJob {
  job_id?: string;
  status?: string;
  result?: ExecuteResult;
  error?: string;
}

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
}

export interface McpStatus {
  status?: string;
  engine?: string;
  engine_kind?: string;
  required_ready?: number;
  required_total?: number;
  services?: McpService[];
}
