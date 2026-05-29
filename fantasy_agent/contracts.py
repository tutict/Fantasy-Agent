from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LocaleCode = Literal["en", "zh-CN"]
BlenderAssetKind = Literal[
    "modular_wall",
    "door",
    "ramp",
    "hazard_marker",
    "objective_prop",
    "exit_gate",
    "ui_proxy_mesh",
    "generic_greybox",
]
BlenderMaterialKey = Literal[
    "neutral",
    "safe",
    "hazard",
    "objective",
    "exit",
    "ui",
    "door",
    "ramp",
]
UnrealCommandletName = Literal["DataValidation"]
UnrealAssetIngestSource = Literal["blender", "comfyui"]
UnrealAssetIngestType = Literal["static_mesh", "texture_reference"]
UnrealLevelPlacementRole = Literal[
    "route_floor",
    "traversal",
    "obstacle",
    "hazard",
    "checkpoint",
    "objective",
    "exit",
    "ui",
    "lighting",
]
ComfyUICapabilityStatus = Literal["ready", "degraded", "unavailable"]
CreativeReviewSource = Literal["comfyui", "blender"]
CreativeReviewStatus = Literal[
    "pending_user_review",
    "approved",
    "needs_revision",
    "rejected",
    "approved_for_unreal_ingest",
]
CreativeReviewDimension = Literal[
    "gameplay_readability",
    "style_alignment",
    "silhouette_clarity",
    "cohesion_with_gameplay",
    "technical_usability",
]
ProductionTaskStatus = Literal["pending", "ready", "blocked", "done"]
ProductionTaskAgent = Literal[
    "director-agent",
    "gameplay-agent",
    "gdd-writer",
    "level-director",
    "blender-worker",
    "comfyui-worker",
    "creative-review-agent",
    "unreal-builder",
    "qa-agent",
]
ProductionPipelineStageId = Literal[
    "gameplay_orchestration",
    "comfyui_visual_production",
    "blender_modeling",
    "creative_review",
    "asset_integration",
    "unreal_production",
    "optimization_testing",
]


def default_comfyui_endpoint_candidates() -> list[str]:
    return [
        "http://127.0.0.1:8188",
        "http://localhost:8188",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
    ]


def default_comfyui_required_nodes() -> list[str]:
    return [
        "CheckpointLoaderSimple",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    ]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PromptRequest(StrictModel):
    prompt: str = Field(min_length=8, description="Raw gameplay idea from the user or director.")
    target_minutes: int = Field(default=10, ge=5, le=15)
    engine_version: str = Field(default="UE5")
    platforms: list[str] = Field(default_factory=lambda: ["Windows"])
    jam_scope: bool = True
    constraints: list[str] = Field(default_factory=list)
    source_locale: LocaleCode = "en"
    output_locales: list[LocaleCode] = Field(default_factory=lambda: ["en", "zh-CN"])


class I18nBundle(StrictModel):
    source_locale: LocaleCode = "en"
    output_locales: list[LocaleCode] = Field(default_factory=lambda: ["en", "zh-CN"])
    field_translations: dict[str, dict[LocaleCode, str]] = Field(default_factory=dict)
    term_translations: dict[str, dict[LocaleCode, str]] = Field(default_factory=dict)


class IdeaDiscoveryAnswer(StrictModel):
    question_id: str
    question: str = ""
    answer: str = Field(min_length=1)


class IdeaDiscoveryRequest(StrictModel):
    raw_idea: str = Field(min_length=4, description="Unstructured initial game idea.")
    answers: list[IdeaDiscoveryAnswer] = Field(default_factory=list)
    target_minutes: int = Field(default=10, ge=5, le=15)
    engine_version: str = Field(default="UE5")
    platforms: list[str] = Field(default_factory=lambda: ["Windows"])
    constraints: list[str] = Field(default_factory=list)
    source_locale: LocaleCode = "en"
    output_locales: list[LocaleCode] = Field(default_factory=lambda: ["en", "zh-CN"])


class IdeaSeed(StrictModel):
    source: str = "idea-discovery-agent"
    schema_version: str = "0.1"
    raw_idea: str
    player_fantasy: str
    emotional_target: str
    core_action: str
    tension_source: str
    must_keep: list[str]
    can_cut: list[str]
    reference_feel: str
    playable_loop_candidate: str
    constraints: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_prompt: str
    i18n: I18nBundle | None = None


class LoopStep(StrictModel):
    order: int = Field(ge=1)
    action: str
    player_decision: str
    feedback: str


class SystemSpec(StrictModel):
    name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    failure_pressure: str


class ProgressionSpec(StrictModel):
    first_minute: str
    midpoint_shift: str
    final_minutes: str
    unlocks: list[str] = Field(default_factory=list)


class LevelBeat(StrictModel):
    name: str
    duration_minutes: int = Field(ge=1, le=15)
    gameplay_focus: str
    required_assets: list[str]
    success_condition: str


class GameplaySpec(StrictModel):
    schema_version: str = "0.1"
    title: str
    logline: str
    target_session_minutes: int = Field(ge=5, le=15)
    player_fantasy: str
    design_pillars: list[str] = Field(min_length=3, max_length=5)
    core_verbs: list[str] = Field(min_length=3)
    core_loop: list[LoopStep] = Field(min_length=3)
    systems: list[SystemSpec] = Field(min_length=3)
    progression: ProgressionSpec
    win_state: str
    failure_states: list[str]
    level_beats: list[LevelBeat]
    asset_needs: list[str]
    qa_focus: list[str]
    notes_for_unreal: list[str]
    notes_for_blender: list[str]
    notes_for_comfyui: list[str]
    i18n: I18nBundle | None = None


class GDDDocument(StrictModel):
    title: str
    markdown: str
    source_schema_version: str
    primary_locale: LocaleCode = "en"
    available_locales: list[LocaleCode] = Field(default_factory=lambda: ["en"])
    markdown_by_locale: dict[LocaleCode, str] = Field(default_factory=dict)


class UnrealProjectPlan(StrictModel):
    project_name: str
    engine_version: str
    template: Literal["blank", "third-person", "top-down", "first-person"] = "third-person"
    plugins: list[str]
    folders: list[str]
    gameplay_classes: list[str]
    blueprints: list[str]
    maps: list[str]
    automation_steps: list[str]
    handoff_artifacts: list[str]


class UnrealContentManifest(StrictModel):
    schema_version: str = "0.1"
    generated_by: str = "fantasy-agent.unreal-builder"
    project_name: str
    engine_version: str
    template: str
    plugins: list[str]
    content_folders: list[str]
    gameplay_classes: list[str]
    blueprints: list[str]
    maps: list[str]
    automation_steps: list[str]
    import_manifests: list[str] = Field(default_factory=list)


class UnrealProjectArtifact(StrictModel):
    project_name: str
    project_dir: str
    project_file: str
    content_manifest_path: str
    setup_script_path: str
    config_files: list[str]
    content_folders: list[str]
    side_effects: list[str]


class UnrealAssetIngestJob(StrictModel):
    job_id: str
    source: UnrealAssetIngestSource
    asset_type: UnrealAssetIngestType
    source_file: str
    destination_path: str
    asset_name: str
    gameplay_role: str
    source_manifest: str
    import_settings: dict[str, str | bool | float] = Field(default_factory=dict)
    review_required: bool = False


class UnrealAssetIngestManifest(StrictModel):
    schema_version: str = "0.1"
    generated_by: str = "fantasy-agent.unreal-asset-ingest"
    project_file: str
    import_script_path: str
    jobs: list[UnrealAssetIngestJob]
    source_manifests: list[str]
    risks: list[str] = Field(default_factory=list)


class UnrealLevelPlacement(StrictModel):
    actor_name: str
    asset_name: str
    asset_path: str
    gameplay_role: UnrealLevelPlacementRole
    location_cm: tuple[float, float, float]
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    beat: str
    notes: str = ""


class UnrealPlayerStartPlacement(StrictModel):
    actor_name: str = "FA_PlayerStart"
    location_cm: tuple[float, float, float] = (-450.0, 0.0, 160.0)
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)


class UnrealLevelAssemblyManifest(StrictModel):
    schema_version: str = "0.1"
    generated_by: str = "fantasy-agent.unreal-level-assembly"
    project_file: str
    map_name: str
    map_path: str
    assembly_script_path: str
    playtest_report_path: str
    source_ingest_manifest: str
    player_start: UnrealPlayerStartPlacement = Field(default_factory=UnrealPlayerStartPlacement)
    placements: list[UnrealLevelPlacement]
    playtest_checks: list[str]
    risks: list[str] = Field(default_factory=list)


class UnrealMCPCreateProjectRequest(StrictModel):
    plan: UnrealProjectPlan | None = None
    plan_path: str | None = None
    project_dir: str | None = None
    content_manifest_path: str | None = None
    import_manifest_paths: list[str] = Field(default_factory=list)
    write_files: bool = False


class UnrealMCPPrepareAssetIngestRequest(StrictModel):
    project_file: str
    blender_import_manifest_path: str | None = None
    comfyui_run_manifest_path: str | None = None
    import_script_path: str | None = None
    ingest_manifest_path: str | None = None
    write_files: bool = False
    require_existing_sources: bool = False


class UnrealMCPValidateAssetIngestRequest(StrictModel):
    ingest_manifest_path: str
    require_existing_sources: bool = True


class UnrealMCPPrepareLevelAssemblyRequest(StrictModel):
    project_file: str
    ingest_manifest_path: str
    map_name: str = "M_Prototype_Greybox"
    assembly_script_path: str | None = None
    level_manifest_path: str | None = None
    write_files: bool = False


class UnrealMCPValidateLevelAssemblyRequest(StrictModel):
    level_manifest_path: str
    require_imported_assets: bool = True
    require_playtest_route: bool = True


class UnrealMCPRunAssetIngestRequest(StrictModel):
    project_file: str
    import_script_path: str
    unreal_editor_cmd: str = "UnrealEditor-Cmd"
    timeout_seconds: int = Field(default=600, ge=30, le=3600)
    confirmed_side_effects: bool = False


class UnrealMCPEditorCommandletRequest(StrictModel):
    project_file: str
    commandlet: UnrealCommandletName
    unreal_editor_cmd: str = "UnrealEditor-Cmd"
    timeout_seconds: int = Field(default=300, ge=30, le=1800)
    confirmed_side_effects: bool = False


class UnrealAssetIngestValidationReport(StrictModel):
    ingest_manifest_path: str
    project_file: str
    job_count: int
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UnrealLevelAssemblyValidationReport(StrictModel):
    level_manifest_path: str
    project_file: str
    map_path: str
    placement_count: int
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UnrealMCPRunLevelAssemblyRequest(StrictModel):
    project_file: str
    assembly_script_path: str
    unreal_editor_cmd: str = "UnrealEditor-Cmd"
    timeout_seconds: int = Field(default=600, ge=30, le=3600)
    confirmed_side_effects: bool = False


class UnrealMCPResult(StrictModel):
    status: Literal["planned", "written", "executed", "failed", "blocked"]
    artifact: UnrealProjectArtifact | None = None
    manifest: UnrealContentManifest | UnrealAssetIngestManifest | UnrealLevelAssemblyManifest | None = None
    validation_report: (
        UnrealAssetIngestValidationReport | UnrealLevelAssemblyValidationReport | None
    ) = None
    command: list[str] = Field(default_factory=list)
    created_paths: list[str] = Field(default_factory=list)
    written_files: list[str] = Field(default_factory=list)
    log_paths: list[str] = Field(default_factory=list)
    return_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    risks: list[str] = Field(default_factory=list)


class BlenderAssetJob(StrictModel):
    asset_name: str
    purpose: str
    primitive_strategy: str
    export_path: str
    collision_hint: str
    asset_kind: BlenderAssetKind = "generic_greybox"
    dimensions_cm: tuple[float, float, float] = (100.0, 100.0, 100.0)
    material_key: BlenderMaterialKey = "neutral"
    collection: str = "GameplayGreybox"
    unreal_path: str = "/Game/Art/Generated"
    collision_name: str | None = None


class BlenderAssetPlan(StrictModel):
    job_name: str
    scene_units: Literal["centimeters", "meters"] = "centimeters"
    jobs: list[BlenderAssetJob]
    python_entrypoint: str
    export_format: Literal["fbx", "glb"] = "fbx"
    handoff_artifacts: list[str]


class UnrealImportAsset(StrictModel):
    asset_name: str
    asset_kind: BlenderAssetKind
    source_file: str
    destination_path: str
    collision_object: str
    material_key: BlenderMaterialKey
    dimensions_cm: tuple[float, float, float]
    gameplay_role: str


class UnrealImportManifest(StrictModel):
    schema_version: str = "0.1"
    generated_by: str = "fantasy-agent.blender-worker"
    scene_units: Literal["centimeters", "meters"] = "centimeters"
    import_settings: dict[str, str | bool | float]
    assets: list[UnrealImportAsset]


class BlenderScriptArtifact(StrictModel):
    plan_name: str
    script_path: str
    script: str
    import_manifest_path: str
    import_manifest: UnrealImportManifest
    execution_notes: list[str]
    side_effects: list[str]


class BlenderMCPGenerateScriptRequest(StrictModel):
    plan: BlenderAssetPlan
    script_path: str | None = None
    import_manifest_path: str = "generated/import-manifest.yaml"
    write_files: bool = False


class BlenderMCPExecuteRequest(StrictModel):
    plan: BlenderAssetPlan
    script_path: str | None = None
    import_manifest_path: str = "generated/import-manifest.yaml"
    blender_executable: str = "blender"
    timeout_seconds: int = Field(default=300, ge=10, le=1800)
    confirmed_side_effects: bool = False


class BlenderMCPResult(StrictModel):
    status: Literal["planned", "written", "executed", "failed", "blocked"]
    artifact: BlenderScriptArtifact
    command: list[str] = Field(default_factory=list)
    written_files: list[str] = Field(default_factory=list)
    exported_assets: list[str] = Field(default_factory=list)
    import_manifest_path: str
    log_paths: list[str] = Field(default_factory=list)
    return_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    risks: list[str] = Field(default_factory=list)


class ComfyUIPromptJob(StrictModel):
    job_id: str
    purpose: Literal[
        "concept_reference",
        "material_reference",
        "ui_reference",
        "texture_seed",
        "storyboard_frame",
    ]
    prompt: str
    negative_prompt: str
    workflow_template: str
    output_path: str
    gameplay_constraint: str


class ComfyUIVisualPlan(StrictModel):
    plan_name: str
    endpoint: str = "http://127.0.0.1:8188"
    checkpoint_name: str | None = None
    jobs: list[ComfyUIPromptJob]
    workflow_templates: list[str]
    handoff_artifacts: list[str]
    usage_rules: list[str]


class ComfyUIWorkflowArtifact(StrictModel):
    job_id: str
    workflow_template: str
    workflow_path: str
    workflow: dict
    output_path: str
    prompt: str
    negative_prompt: str
    gameplay_constraint: str
    seed: int


class ComfyUIRunManifest(StrictModel):
    schema_version: str = "0.1"
    plan_name: str
    endpoint: str
    jobs: list[ComfyUIWorkflowArtifact]
    prompt_ids: list[str] = Field(default_factory=list)
    generated_images: list[str] = Field(default_factory=list)
    log_paths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ComfyUIMCPGenerateRequest(StrictModel):
    plan: ComfyUIVisualPlan
    output_dir: str = "generated/comfyui"
    checkpoint_name: str | None = None
    write_files: bool = False


class ComfyUIMCPExecuteRequest(StrictModel):
    plan: ComfyUIVisualPlan
    output_dir: str = "generated/comfyui"
    checkpoint_name: str | None = None
    auto_discover_endpoint: bool = True
    endpoint_candidates: list[str] = Field(default_factory=default_comfyui_endpoint_candidates)
    validate_server_capabilities: bool = True
    confirmed_side_effects: bool = False
    wait_for_completion: bool = False
    timeout_seconds: int = Field(default=300, ge=10, le=1800)
    poll_interval_seconds: float = Field(default=2.0, ge=0.2, le=30.0)
    allow_remote_endpoint: bool = False


class ComfyUIMCPResult(StrictModel):
    status: Literal["planned", "written", "queued", "executed", "failed", "blocked"]
    manifest: ComfyUIRunManifest
    workflow_files: list[str] = Field(default_factory=list)
    manifest_path: str
    written_files: list[str] = Field(default_factory=list)
    prompt_ids: list[str] = Field(default_factory=list)
    generated_images: list[str] = Field(default_factory=list)
    log_paths: list[str] = Field(default_factory=list)
    return_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    risks: list[str] = Field(default_factory=list)


class ComfyUICapabilityProbeRequest(StrictModel):
    endpoint: str = "http://127.0.0.1:8188"
    endpoint_candidates: list[str] = Field(default_factory=default_comfyui_endpoint_candidates)
    auto_discover_endpoint: bool = True
    allow_remote_endpoint: bool = False
    required_nodes: list[str] = Field(default_factory=default_comfyui_required_nodes)
    require_checkpoint: bool = True
    preferred_checkpoint_name: str | None = None


class ComfyUICapabilityProbeResult(StrictModel):
    status: ComfyUICapabilityStatus
    endpoint: str
    comfyui_version: str | None = None
    python_version: str | None = None
    pytorch_version: str | None = None
    devices: list[str] = Field(default_factory=list)
    required_nodes: dict[str, bool] = Field(default_factory=dict)
    checkpoints: list[str] = Field(default_factory=list)
    selected_checkpoint: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ArtDirectionBrief(StrictModel):
    source: str = "creative-review-agent"
    schema_version: str = "0.1"
    title: str
    visual_intent: str
    style_keywords: list[str]
    avoid_keywords: list[str]
    gameplay_readability_rules: list[str]
    user_review_questions: list[str]
    i18n: I18nBundle | None = None


class CreativeReviewItem(StrictModel):
    asset_id: str
    source: CreativeReviewSource
    asset_path: str
    gameplay_role: str
    intended_use: str
    review_dimensions: list[CreativeReviewDimension]
    approval_status: CreativeReviewStatus = "pending_user_review"
    user_prompt: str
    revision_prompt: str | None = None
    risks: list[str] = Field(default_factory=list)


class CreativeReviewReport(StrictModel):
    source: str = "creative-review-agent"
    schema_version: str = "0.1"
    art_direction: ArtDirectionBrief
    items: list[CreativeReviewItem]
    required_user_decisions: list[str]
    approval_gate: Literal["blocks_unreal_ingest"] = "blocks_unreal_ingest"
    approved_asset_ids: list[str] = Field(default_factory=list)
    revision_asset_ids: list[str] = Field(default_factory=list)
    rejected_asset_ids: list[str] = Field(default_factory=list)
    handoff_artifacts: list[str] = Field(default_factory=list)


class CreativeReviewRequest(StrictModel):
    gameplay_spec: GameplaySpec
    blender_plan: BlenderAssetPlan
    comfyui_plan: ComfyUIVisualPlan


class QAPlan(StrictModel):
    target_session_minutes: int = Field(ge=5, le=15)
    smoke_tests: list[str]
    playability_checks: list[str]
    failure_checks: list[str]
    packaging_checks: list[str]
    metrics: list[str]


class ProductionTask(StrictModel):
    id: str
    title: str
    title_i18n: dict[LocaleCode, str] = Field(default_factory=dict)
    agent: ProductionTaskAgent
    purpose: str
    inputs: list[str]
    outputs: list[str]
    side_effects: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    status: ProductionTaskStatus = "pending"
    requires_confirmation: bool = False
    risks: list[str] = Field(default_factory=list)


class ProductionPipelineStage(StrictModel):
    id: ProductionPipelineStageId
    order: int = Field(ge=1)
    title: str
    title_i18n: dict[LocaleCode, str] = Field(default_factory=dict)
    purpose: str
    owner_agent: ProductionTaskAgent
    participating_agents: list[ProductionTaskAgent] = Field(default_factory=list)
    inputs: list[str]
    outputs: list[str]
    artifacts: list[str] = Field(default_factory=list)
    mcp_tools: list[str] = Field(default_factory=list)
    quality_gates: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    depends_on: list[ProductionPipelineStageId] = Field(default_factory=list)
    status: ProductionTaskStatus = "pending"
    requires_confirmation: bool = False
    risks: list[str] = Field(default_factory=list)


class ProductionPipeline(StrictModel):
    source: str = "director-agent"
    schema_version: str = "0.1"
    project_name: str
    goal: str
    goal_i18n: dict[LocaleCode, str] = Field(default_factory=dict)
    stages: list[ProductionPipelineStage]
    current_stage: ProductionPipelineStageId = "gameplay_orchestration"
    next_stage: ProductionPipelineStageId = "gameplay_orchestration"
    risks: list[str] = Field(default_factory=list)
    i18n: I18nBundle | None = None


class DirectorTaskBreakdown(StrictModel):
    source: str = "director-agent"
    schema_version: str = "0.1"
    source_prompt: str
    goal: str
    goal_i18n: dict[LocaleCode, str] = Field(default_factory=dict)
    tasks: list[ProductionTask]
    recommended_next_task: str
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    confirmation_required: bool = False
    i18n: I18nBundle | None = None


class DirectorBuildPlan(StrictModel):
    gameplay_spec: GameplaySpec
    gdd: GDDDocument
    unreal_plan: UnrealProjectPlan
    blender_plan: BlenderAssetPlan
    comfyui_plan: ComfyUIVisualPlan
    creative_review: CreativeReviewReport
    qa_plan: QAPlan
    task_breakdown: DirectorTaskBreakdown | None = None
    production_pipeline: ProductionPipeline | None = None
    next_actions: list[str]


class MCPToolContract(StrictModel):
    name: str
    server: Literal["unreal-mcp", "blender-mcp", "comfyui-mcp", "github-mcp"]
    input_schema_ref: str
    output_schema_ref: str
    side_effects: list[str]
    safety_checks: list[str]
