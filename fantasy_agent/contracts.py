from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LocaleCode = Literal["en", "zh-CN"]


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


class BlenderAssetJob(StrictModel):
    asset_name: str
    purpose: str
    primitive_strategy: str
    export_path: str
    collision_hint: str


class BlenderAssetPlan(StrictModel):
    job_name: str
    scene_units: Literal["centimeters", "meters"] = "centimeters"
    jobs: list[BlenderAssetJob]
    python_entrypoint: str
    export_format: Literal["fbx", "glb"] = "fbx"
    handoff_artifacts: list[str]


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
    jobs: list[ComfyUIPromptJob]
    workflow_templates: list[str]
    handoff_artifacts: list[str]
    usage_rules: list[str]


class QAPlan(StrictModel):
    target_session_minutes: int = Field(ge=5, le=15)
    smoke_tests: list[str]
    playability_checks: list[str]
    failure_checks: list[str]
    packaging_checks: list[str]
    metrics: list[str]


class DirectorBuildPlan(StrictModel):
    gameplay_spec: GameplaySpec
    gdd: GDDDocument
    unreal_plan: UnrealProjectPlan
    blender_plan: BlenderAssetPlan
    comfyui_plan: ComfyUIVisualPlan
    qa_plan: QAPlan
    next_actions: list[str]


class MCPToolContract(StrictModel):
    name: str
    server: Literal["unreal-mcp", "blender-mcp", "comfyui-mcp", "github-mcp"]
    input_schema_ref: str
    output_schema_ref: str
    side_effects: list[str]
    safety_checks: list[str]
