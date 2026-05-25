from __future__ import annotations

from fantasy_agent.contracts import (
    BlenderAssetJob,
    BlenderAssetPlan,
    ComfyUIPromptJob,
    ComfyUIVisualPlan,
    DirectorBuildPlan,
    GameplaySpec,
    PromptRequest,
    QAPlan,
    UnrealProjectPlan,
)
from fantasy_agent.gdd import render_gdd
from fantasy_agent.generation import design_from_prompt


def prepare_unreal_project(spec: GameplaySpec, engine_version: str = "UE5") -> UnrealProjectPlan:
    project_slug = "".join(part for part in spec.title.title().split()) or "FantasyPrototype"
    return UnrealProjectPlan(
        project_name=project_slug,
        engine_version=engine_version,
        template="third-person",
        plugins=["EnhancedInput", "GameplayTags", "Niagara"],
        folders=[
            "Content/Blueprints/CoreLoop",
            "Content/Blueprints/Interactables",
            "Content/Maps",
            "Content/UI",
            "Content/Art/Generated",
            "Content/Data",
        ],
        gameplay_classes=[
            "BP_PlayerPrototypePawn",
            "BP_ObjectiveStateComponent",
            "BP_PressureClockComponent",
            "BP_InteractableBase",
            "BP_RunResultSubsystem",
        ],
        blueprints=[
            "BP_ObjectiveDirector",
            "BP_LevelBeatTrigger",
            "BP_HazardPressureSource",
            "WBP_ObjectiveTracker",
            "WBP_RunSummary",
        ],
        maps=["M_Prototype_Greybox", "M_Prototype_TestGym"],
        automation_steps=[
            "Create UE project from template",
            "Enable required plugins",
            "Create content folders",
            "Import generated greybox assets",
            "Create data assets from gameplay DSL",
            "Run map validation commandlet",
        ],
        handoff_artifacts=[
            "generated/gameplay-spec.yaml",
            "generated/gdd.md",
            "generated/unreal-project-plan.yaml",
        ],
    )


def prepare_blender_assets(spec: GameplaySpec) -> BlenderAssetPlan:
    jobs = [
        BlenderAssetJob(
            asset_name=asset.lower().replace(" ", "_"),
            purpose=asset,
            primitive_strategy="modular low-poly mesh with bevels only where readability improves play",
            export_path=f"generated/assets/{asset.lower().replace(' ', '_')}.fbx",
            collision_hint="simple convex collision, authored at UE centimeter scale",
        )
        for asset in spec.asset_needs
    ]
    return BlenderAssetPlan(
        job_name=f"{spec.title} Greybox Asset Pass",
        jobs=jobs,
        python_entrypoint="apps/blender-worker/app/procedural_asset_job.py",
        handoff_artifacts=[
            "generated/assets/*.fbx",
            "generated/blender-asset-plan.yaml",
            "generated/import-manifest.yaml",
        ],
    )


def prepare_comfyui_visuals(spec: GameplaySpec) -> ComfyUIVisualPlan:
    title_slug = spec.title.lower().replace(" ", "_")
    visual_basis = ", ".join(spec.design_pillars[:2])
    return ComfyUIVisualPlan(
        plan_name=f"{spec.title} Visual Reference Pass",
        jobs=[
            ComfyUIPromptJob(
                job_id="concept_readability_reference",
                purpose="concept_reference",
                prompt=(
                    f"Gameplay readability concept art for {spec.title}: {spec.logline} "
                    f"Focus on clear player objective, hazard readability, simple shapes, {visual_basis}."
                ),
                negative_prompt=(
                    "busy composition, photorealistic noise, unreadable silhouettes, cinematic blur, "
                    "AAA marketing render, disconnected decorative detail"
                ),
                workflow_template="templates/comfyui/readability-reference.json",
                output_path=f"generated/comfyui/{title_slug}/concept_readability_reference.png",
                gameplay_constraint="Must clarify objective, hazard, route, or player feedback.",
            ),
            ComfyUIPromptJob(
                job_id="material_palette_reference",
                purpose="material_reference",
                prompt=(
                    f"Compact material and color reference board for a playable greybox of {spec.title}. "
                    "Separate safe paths, hazards, interactables, objectives, and exit affordances."
                ),
                negative_prompt=(
                    "single-color palette, low contrast, decorative-only swatches, noisy texture sheet"
                ),
                workflow_template="templates/comfyui/material-palette.json",
                output_path=f"generated/comfyui/{title_slug}/material_palette_reference.png",
                gameplay_constraint="Every color group must map to a gameplay state or affordance.",
            ),
            ComfyUIPromptJob(
                job_id="objective_ui_reference",
                purpose="ui_reference",
                prompt=(
                    f"Minimal objective tracker reference for {spec.title}, game jam prototype UI, "
                    "clear current objective, pressure indicator, restart readable in a 10-foot UI test."
                ),
                negative_prompt="ornate UI, tiny text, decorative panels, unreadable labels, dense HUD",
                workflow_template="templates/comfyui/ui-reference.json",
                output_path=f"generated/comfyui/{title_slug}/objective_ui_reference.png",
                gameplay_constraint="UI reference must support objective clarity before visual style.",
            ),
        ],
        workflow_templates=[
            "templates/comfyui/readability-reference.json",
            "templates/comfyui/material-palette.json",
            "templates/comfyui/ui-reference.json",
        ],
        handoff_artifacts=[
            "generated/comfyui/*/*.png",
            "generated/comfyui/comfyui-visual-plan.yaml",
            "generated/comfyui/run-manifest.yaml",
        ],
        usage_rules=[
            "ComfyUI outputs are references, not proof of playable progress.",
            "Do not block UE greybox implementation on image generation.",
            "Every generated visual must map to objective clarity, hazard readability, or UI feedback.",
            "Generated images require review before becoming Unreal textures or UI assets.",
        ],
    )


def prepare_qa_plan(spec: GameplaySpec) -> QAPlan:
    return QAPlan(
        target_session_minutes=spec.target_session_minutes,
        smoke_tests=[
            "Project opens without missing plugin or asset errors",
            "Prototype map loads directly from editor and packaged build",
            "Player can restart a run without reloading the map manually",
        ],
        playability_checks=[
            "Primary objective is visible within 10 seconds",
            "Each core verb is required at least once before the final beat",
            "A first-time player can identify why they failed",
            "The full loop completes in the target session window",
        ],
        failure_checks=spec.failure_states,
        packaging_checks=[
            "Windows development package builds",
            "Default map is the prototype map",
            "Input mappings are included in packaged build",
            "Generated assets have valid collision",
        ],
        metrics=[
            "time_to_first_objective",
            "attempts_to_first_completion",
            "failure_reason_distribution",
            "average_session_minutes",
        ],
    )


def run_director_workflow(request: PromptRequest) -> DirectorBuildPlan:
    gameplay_spec = design_from_prompt(request)
    return DirectorBuildPlan(
        gameplay_spec=gameplay_spec,
        gdd=render_gdd(gameplay_spec),
        unreal_plan=prepare_unreal_project(gameplay_spec, request.engine_version),
        blender_plan=prepare_blender_assets(gameplay_spec),
        comfyui_plan=prepare_comfyui_visuals(gameplay_spec),
        qa_plan=prepare_qa_plan(gameplay_spec),
        next_actions=[
            "Review generated gameplay spec for loop coherence",
            "Export gameplay spec and GDD into generated/",
            "Run Blender greybox asset job",
            "Run ComfyUI reference jobs only after gameplay readability needs are approved",
            "Create UE project structure and import generated assets",
            "Run QA smoke test before adding visual polish",
        ],
    )
