from __future__ import annotations

from fantasy_agent.contracts import (
    BlenderAssetJob,
    BlenderAssetPlan,
    BlenderAssetKind,
    ArtDirectionBrief,
    CreativeReviewItem,
    CreativeReviewReport,
    ComfyUIPromptJob,
    ComfyUIVisualPlan,
    DirectorBuildPlan,
    DirectorTaskBreakdown,
    GameplaySpec,
    GodotProjectPlan,
    PromptRequest,
    ProductionPipeline,
    ProductionPipelineStage,
    ProductionTask,
    QAPlan,
    UnrealProjectPlan,
)
from fantasy_agent.blender_codegen import enrich_blender_plan, slugify
from fantasy_agent.gdd import render_gdd
from fantasy_agent.generation import design_from_prompt


BLENDER_KIT_JOBS: tuple[tuple[str, str, BlenderAssetKind], ...] = (
    (
        "modular_wall_400",
        "Reusable modular wall for blocking sightlines and routes.",
        "modular_wall",
    ),
    ("interaction_door", "Readable door or gate for lock, key, or route-change tests.", "door"),
    ("traversal_ramp", "Simple ramp for vertical movement and route readability tests.", "ramp"),
    (
        "hazard_marker",
        "Readable hazard marker for pressure, danger, or failure feedback.",
        "hazard_marker",
    ),
    (
        "objective_prop",
        "Readable objective prop for interaction and pickup testing.",
        "objective_prop",
    ),
    ("exit_gate", "Readable exit gate for win-state and extraction tests.", "exit_gate"),
    (
        "ui_proxy_mesh",
        "World-space UI proxy mesh for objective and pressure readability.",
        "ui_proxy_mesh",
    ),
)

DIRECTOR_NEXT_ACTIONS = [
    "Review generated gameplay spec for loop coherence",
    "Export gameplay spec and GDD into generated/",
    "Run Blender greybox asset job",
    "Run ComfyUI reference jobs only after gameplay readability needs are approved",
    "Review ComfyUI and Blender outputs with the user before Unreal ingest",
    "Prepare a Godot quick-play project handoff when fast loop validation is useful",
    "Create UE project structure and import generated assets",
    "Run QA smoke test before adding visual polish",
]


def _is_godot_engine(engine_version: str) -> bool:
    return "godot" in engine_version.casefold()


def _unreal_engine_version(requested_engine: str) -> str:
    return "UE5" if _is_godot_engine(requested_engine) else requested_engine


def _godot_engine_version(requested_engine: str) -> str:
    return requested_engine if _is_godot_engine(requested_engine) else "Godot 4"


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
            "Assemble playable greybox map",
            "Create data assets from gameplay DSL",
            "Run asset ingest manifest validation",
            "Run level assembly manifest validation",
        ],
        handoff_artifacts=[
            "generated/gameplay-spec.yaml",
            "generated/gdd.md",
            "generated/unreal-project-plan.yaml",
        ],
    )


def prepare_godot_project(spec: GameplaySpec, engine_version: str = "Godot 4") -> GodotProjectPlan:
    project_slug = "".join(part for part in spec.title.title().split()) or "FantasyPrototype"
    input_actions = [
        "move_forward",
        "move_back",
        "move_left",
        "move_right",
        "jump",
        "restart_run",
        *[slugify(verb).replace("-", "_") for verb in spec.core_verbs[:4]],
    ]
    return GodotProjectPlan(
        project_name=f"{project_slug}Godot",
        engine_version=engine_version,
        renderer="Compatibility",
        folders=[
            "scenes",
            "scripts",
            "assets/generated",
            "references/comfyui",
            "data",
        ],
        scenes=["scenes/main.tscn"],
        scripts=["scripts/main.gd", "scripts/player_controller.gd", "scripts/enemy_controller.gd"],
        input_actions=list(dict.fromkeys(input_actions)),
        automation_steps=[
            "Create Godot 4 project.godot for quick playable-loop validation",
            "Generate main scene with greybox route, hazards, objective, exit, and UI proxy",
            "Generate prototype GDScript movement, enemies, and scene assembly scripts",
            "Copy reviewed Blender and ComfyUI outputs under res://assets/generated",
            "Run Godot headless import only after explicit execution confirmation",
            "Use Godot smoke playtests to validate loop timing before heavier UE work",
        ],
        handoff_artifacts=[
            "generated/godot-project-plan.yaml",
            "generated/godot/<project>/project.godot",
            "generated/godot/<project>/fantasy-agent-godot-manifest.json",
        ],
    )


def prepare_blender_assets(spec: GameplaySpec) -> BlenderAssetPlan:
    jobs: list[BlenderAssetJob] = []
    seen_kinds: set[BlenderAssetKind] = set()
    for asset in spec.asset_needs:
        asset_name = slugify(asset)
        jobs.append(
            BlenderAssetJob(
                asset_name=asset_name,
                purpose=asset,
                primitive_strategy=(
                    "modular low-poly mesh with bevels only where readability improves play"
                ),
                export_path=f"generated/assets/{asset_name}.fbx",
                collision_hint="simple convex collision, authored at UE centimeter scale",
            )
        )
    enriched_jobs = enrich_blender_plan(
        BlenderAssetPlan(
            job_name=f"{spec.title} Greybox Asset Pass",
            jobs=jobs,
            python_entrypoint="apps/blender-worker/app/procedural_asset_job.py",
            handoff_artifacts=[],
        )
    ).jobs
    seen_kinds.update(job.asset_kind for job in enriched_jobs)

    for asset_name, purpose, asset_kind in BLENDER_KIT_JOBS:
        if asset_kind in seen_kinds:
            continue
        jobs.append(
            BlenderAssetJob(
                asset_name=asset_name,
                purpose=purpose,
                primitive_strategy="gameplay-readable primitive composition generated by bpy",
                export_path=f"generated/assets/{asset_name}.fbx",
                collision_hint="UCX convex collision generated with matching bounds",
                asset_kind=asset_kind,
            )
        )
        seen_kinds.add(asset_kind)

    return enrich_blender_plan(
        BlenderAssetPlan(
            job_name=f"{spec.title} Greybox Asset Pass",
            jobs=jobs,
            python_entrypoint="apps/blender-worker/app/procedural_asset_job.py",
            handoff_artifacts=[
                "generated/assets/*.fbx",
                "generated/blender/*.py",
                "generated/blender-asset-plan.yaml",
                "generated/import-manifest.yaml",
            ],
        )
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
                job_id="character_readability_portrait",
                purpose="concept_reference",
                prompt=(
                    f"Playable character portrait and silhouette sheet for {spec.title}. "
                    "Show a readable full-body pose, clear traversal affordances, and simple "
                    "shape language that remains legible in third-person gameplay."
                ),
                negative_prompt=(
                    "fashion-only portrait, tiny props, unreadable silhouette, photorealistic noise, "
                    "cinematic crop, decorative costume without gameplay readability"
                ),
                workflow_template="templates/comfyui/readability-reference.json",
                output_path=f"generated/comfyui/{title_slug}/character_readability_portrait.png",
                gameplay_constraint=(
                    "Character reference must improve player silhouette and verb readability."
                ),
            ),
            ComfyUIPromptJob(
                job_id="game_logo_reference",
                purpose="ui_reference",
                prompt=(
                    f"Prototype game logo reference for {spec.title}. "
                    "Use bold readable lettering, a simple mark tied to the core loop, "
                    "and a layout that can fit a start screen or build splash."
                ),
                negative_prompt=(
                    "overly ornate logo, illegible typography, busy background, fake AAA key art, "
                    "tiny subtitle text, unrelated decorative symbols"
                ),
                workflow_template="templates/comfyui/ui-reference.json",
                output_path=f"generated/comfyui/{title_slug}/game_logo_reference.png",
                gameplay_constraint="Logo reference must communicate the playable fantasy and genre quickly.",
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


def prepare_creative_review(
    spec: GameplaySpec,
    blender_plan: BlenderAssetPlan,
    comfyui_plan: ComfyUIVisualPlan,
) -> CreativeReviewReport:
    art_direction = ArtDirectionBrief(
        title=f"{spec.title} Creative Review Brief",
        visual_intent=(
            f"Keep visual decisions subordinate to the playable fantasy: {spec.player_fantasy}. "
            f"Every accepted asset must improve route, hazard, objective, feedback, or verb clarity."
        ),
        style_keywords=[
            *spec.design_pillars[:3],
            "readable silhouette",
            "gameplay-state color coding",
            "greybox-first composition",
        ],
        avoid_keywords=[
            "decorative-only detail",
            "busy visual noise",
            "unreadable silhouettes",
            "single-hue mood board",
            "fake AAA key art",
        ],
        gameplay_readability_rules=[
            "Safe route, hazard, objective, interactable, and exit states must be visually distinct.",
            "Character and prop silhouettes must remain readable from gameplay camera distance.",
            "Mesh scale, origin, collision naming, and export paths must survive Unreal import.",
            "Reference images can guide art direction but cannot replace greybox playability checks.",
        ],
        user_review_questions=[
            "Does this asset match the intended player fantasy and tone?",
            "Can the player immediately read what this asset means during play?",
            "Should this become an Unreal import candidate, a revision request, or a rejected reference?",
            "What concrete style or proportion change would make it closer to your art direction?",
        ],
        i18n=spec.i18n,
    )

    items: list[CreativeReviewItem] = []
    for job in comfyui_plan.jobs:
        items.append(
            CreativeReviewItem(
                asset_id=job.job_id,
                source="comfyui",
                asset_path=job.output_path,
                gameplay_role=job.purpose,
                intended_use=job.gameplay_constraint,
                review_dimensions=[
                    "gameplay_readability",
                    "style_alignment",
                    "silhouette_clarity",
                    "cohesion_with_gameplay",
                ],
                user_prompt=(
                    f"Review {job.job_id}: approve, revise, or reject this reference for "
                    f"{job.gameplay_constraint}"
                ),
                revision_prompt=(
                    f"Revise {job.job_id} to improve gameplay readability for {spec.title}. "
                    f"Preserve the role: {job.gameplay_constraint}. Avoid: {job.negative_prompt}."
                ),
                risks=[
                    "ComfyUI output is a visual reference only and may need style revision.",
                    "Do not import as a UE texture until the user approves the reference.",
                ],
            )
        )

    for job in blender_plan.jobs:
        items.append(
            CreativeReviewItem(
                asset_id=job.asset_name,
                source="blender",
                asset_path=job.export_path,
                gameplay_role=job.asset_kind,
                intended_use=job.purpose,
                review_dimensions=[
                    "gameplay_readability",
                    "cohesion_with_gameplay",
                    "technical_usability",
                ],
                user_prompt=(
                    f"Review {job.asset_name}: confirm this mesh is readable and useful for "
                    f"{job.purpose}"
                ),
                revision_prompt=(
                    f"Revise {job.asset_name} as a modular {job.asset_kind} for {spec.title}. "
                    "Keep UE centimeter scale, clear origin, collision naming, and gameplay role."
                ),
                risks=[
                    "Mesh should stay modular and scale-correct before Unreal import.",
                    "Reject if the shape does not support a playable route, hazard, objective, or UI role.",
                ],
            )
        )

    return CreativeReviewReport(
        art_direction=art_direction,
        items=items,
        required_user_decisions=[
            "Approve, revise, or reject each ComfyUI reference before it can become a UE texture or UI asset.",
            "Approve Blender meshes for readability, scale, origin, and collision before UE import.",
            "Record concrete revision prompts for anything that does not match the intended art direction.",
        ],
        handoff_artifacts=[
            "generated/creative-review-report.yaml",
            "generated/asset-approval-manifest.yaml",
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


def _pipeline_stage(
    *,
    stage_id: str,
    order: int,
    title: str,
    title_zh: str,
    purpose: str,
    owner_agent: str,
    participating_agents: list[str],
    inputs: list[str],
    outputs: list[str],
    artifacts: list[str] | None = None,
    mcp_tools: list[str] | None = None,
    quality_gates: list[str] | None = None,
    side_effects: list[str] | None = None,
    depends_on: list[str] | None = None,
    status: str = "pending",
    requires_confirmation: bool = False,
    risks: list[str] | None = None,
) -> ProductionPipelineStage:
    return ProductionPipelineStage(
        id=stage_id,  # type: ignore[arg-type]
        order=order,
        title=title,
        title_i18n={"en": title, "zh-CN": title_zh},
        purpose=purpose,
        owner_agent=owner_agent,  # type: ignore[arg-type]
        participating_agents=participating_agents,  # type: ignore[arg-type]
        inputs=inputs,
        outputs=outputs,
        artifacts=artifacts or [],
        mcp_tools=mcp_tools or [],
        quality_gates=quality_gates or [],
        side_effects=side_effects or [],
        depends_on=depends_on or [],  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        requires_confirmation=requires_confirmation,
        risks=risks or [],
    )


def prepare_production_pipeline(
    *,
    request: PromptRequest,
    spec: GameplaySpec,
    unreal_plan: UnrealProjectPlan,
    godot_plan: GodotProjectPlan,
    blender_plan: BlenderAssetPlan,
    comfyui_plan: ComfyUIVisualPlan,
    creative_review: CreativeReviewReport,
    qa_plan: QAPlan,
) -> ProductionPipeline:
    primary_is_godot = _is_godot_engine(request.engine_version)
    engine_label = "Godot" if primary_is_godot else "Unreal"
    goal = (
        f"Orchestrate gameplay, visual references, modular assets, {engine_label} assembly, "
        f"and QA into a {spec.target_session_minutes}-minute playable slice for {spec.title}."
    )
    stages = [
        _pipeline_stage(
            stage_id="gameplay_orchestration",
            order=1,
            title="Gameplay orchestration",
            title_zh="玩法编排",
            owner_agent="director-agent",
            participating_agents=["gameplay-agent", "gdd-writer", "level-director"],
            purpose=(
                "Turn the prompt into a coherent loop, level beats, implementation GDD, "
                "and task board before any visual or engine work expands scope."
            ),
            inputs=["PromptRequest", "target session length", "platform constraints"],
            outputs=["GameplaySpec", "GDDDocument", "DirectorTaskBreakdown"],
            artifacts=[
                "generated/gameplay-spec.yaml",
                "generated/gdd.md",
                "generated/level-beats.yaml",
            ],
            quality_gates=[
                "Core loop has at least three testable decisions.",
                "First minute teaches the loop in greybox form.",
                "Win and failure states can be validated without final art.",
            ],
            status="ready",
            risks=["Reject disconnected mechanics even if they look visually interesting."],
        ),
        _pipeline_stage(
            stage_id="comfyui_visual_production",
            order=2,
            title="ComfyUI visual production",
            title_zh="ComfyUI 视觉生产",
            owner_agent="comfyui-worker",
            participating_agents=["director-agent"],
            purpose=(
                "Generate gameplay-readable references for character portrait, game logo, "
                "UI, material palette, and feedback language after the loop is known."
            ),
            inputs=["GameplaySpec.notes_for_comfyui", "ComfyUIVisualPlan", "local checkpoint"],
            outputs=[
                "character readability portrait reference",
                "game logo reference",
                "UI objective reference",
                "material palette reference",
                "ComfyUIRunManifest",
            ],
            artifacts=[
                "generated/comfyui/comfyui-visual-plan.yaml",
                "generated/comfyui/*/*.png",
                "generated/comfyui/run-manifest.yaml",
            ],
            mcp_tools=[
                "probe_comfyui_capabilities",
                "prepare_visual_reference_workflows",
                "run_visual_reference_workflow",
            ],
            quality_gates=[
                "Every prompt includes a gameplay constraint.",
                "References clarify objective, hazard, route, feedback, or brand readability.",
                "Generated images are reviewed before becoming Unreal textures or UI assets.",
            ],
            side_effects=[
                "submits local ComfyUI prompt jobs",
                "writes generated/comfyui images and run manifests",
            ],
            depends_on=["gameplay_orchestration"],
            status="pending",
            requires_confirmation=True,
            risks=[
                "ComfyUI is a reference worker and must not block greybox UE playability.",
                f"{len(comfyui_plan.jobs)} planned jobs require a usable local checkpoint.",
            ],
        ),
        _pipeline_stage(
            stage_id="blender_modeling",
            order=3,
            title="Blender procedural modeling",
            title_zh="Blender 程序化建模",
            owner_agent="blender-worker",
            participating_agents=["level-director", "unreal-builder"],
            purpose=(
                "Generate modular wall, door, ramp, hazard, objective, exit, and UI proxy meshes "
                "that make the route playable before polish."
            ),
            inputs=["BlenderAssetPlan", "GameplaySpec.level_beats", "GameplaySpec.asset_needs"],
            outputs=["Blender Python script", "FBX or GLB exports", "UnrealImportManifest"],
            artifacts=[
                "generated/blender/*.py",
                "generated/assets/*.fbx",
                "generated/import-manifest.yaml",
            ],
            mcp_tools=["generate_blender_script"],
            quality_gates=[
                "Assets use UE centimeter scale.",
                "Each gameplay mesh has a UCX collision object.",
                "Asset names describe gameplay role rather than visual polish.",
            ],
            side_effects=[
                "writes generated/blender scripts",
                "launches Blender when execution is confirmed",
                "writes generated/assets exports",
            ],
            depends_on=["gameplay_orchestration"],
            status="pending",
            requires_confirmation=True,
            risks=[f"{len(blender_plan.jobs)} planned mesh jobs must stay modular and reusable."],
        ),
        _pipeline_stage(
            stage_id="godot_quick_play",
            order=7,
            title="Godot production",
            title_zh="Godot 制作",
            owner_agent="godot-builder",
            participating_agents=["gameplay-agent", "qa-agent"],
            purpose=(
                "Create the Godot quick-play project, assemble the playable scene, and validate "
                "the loop in a lightweight runtime."
            ),
            inputs=["GameplaySpec", "GodotProjectPlan", "AssetApprovalManifest", "level beat plan"],
            outputs=["Godot project.godot", "main scene", "prototype scripts", "Godot handoff manifest"],
            artifacts=[
                "generated/godot-project-plan.yaml",
                "generated/godot/<project>/project.godot",
                "generated/godot/<project>/fantasy-agent-godot-manifest.json",
            ],
            mcp_tools=["create_godot_project_structure", "validate_godot_project", "run_godot_import"],
            quality_gates=[
                f"Main scene targets {godot_plan.scenes[0] if godot_plan.scenes else 'scenes/main.tscn'}.",
                "Godot is the selected engine for this plan.",
                "Headless import runs only after explicit execution confirmation.",
            ],
            side_effects=[
                "writes generated Godot project files",
                "launches Godot headless import when execution is confirmed",
                "writes generated/logs/godot import logs",
            ],
            depends_on=["asset_integration"],
            status="blocked",
            requires_confirmation=True,
            risks=["Keep the Godot project compact enough for quick playable-loop validation."],
        ),
        _pipeline_stage(
            stage_id="creative_review",
            order=5,
            title="Creative review",
            title_zh="创意审阅",
            owner_agent="creative-review-agent",
            participating_agents=["director-agent", "comfyui-worker", "blender-worker"],
            purpose=(
                "Compare generated ComfyUI references and Blender meshes against user art direction, "
                "gameplay readability, and Unreal ingest readiness before production assets move forward."
            ),
            inputs=[
                "CreativeReviewReport",
                "ComfyUIRunManifest",
                "UnrealImportManifest",
                "user art direction decisions",
            ],
            outputs=["review decisions", "revision prompts", "AssetApprovalManifest"],
            artifacts=[
                "generated/creative-review-report.yaml",
                "generated/asset-approval-manifest.yaml",
            ],
            quality_gates=[
                "Every candidate has approve, revise, or reject status.",
                "User taste and art direction override generated visual references.",
                "Approved assets still serve route, hazard, objective, feedback, or verb readability.",
            ],
            side_effects=["asks the user for asset approval decisions"],
            depends_on=["comfyui_visual_production", "blender_modeling"],
            status="blocked",
            requires_confirmation=True,
            risks=[
                f"{len(creative_review.items)} review items block Unreal ingest until decisions exist.",
                "Revision requests may return work to ComfyUI or Blender before UE import.",
            ],
        ),
        _pipeline_stage(
            stage_id="asset_integration",
            order=6,
            title="Asset integration",
            title_zh="资产整合",
            owner_agent="godot-builder" if primary_is_godot else "unreal-builder",
            participating_agents=[
                "creative-review-agent",
                "blender-worker",
                "comfyui-worker",
                "qa-agent",
            ],
            purpose=(
                f"Move reviewed Blender exports and approved ComfyUI references into the {engine_label} project "
                "through explicit manifests."
            ),
            inputs=(
                ["GodotProjectPlan", "generated mesh exports", "ComfyUIRunManifest", "review decisions"]
                if primary_is_godot
                else ["UnrealProjectPlan", "UnrealImportManifest", "ComfyUIRunManifest", "review decisions"]
            ),
            outputs=[
                "GodotAssetIngestManifest" if primary_is_godot else "UnrealAssetIngestManifest",
                "imported static meshes",
                "reviewed texture references",
            ],
            artifacts=(
                [
                    "generated/godot/<project>/fantasy-agent-godot-manifest.json",
                    "generated/logs/godot/*import*.log",
                ]
                if primary_is_godot
                else [
                    "generated/unreal/*/fantasy-agent-asset-ingest.json",
                    "generated/logs/unreal/*asset_ingest*.log",
                ]
            ),
            mcp_tools=(
                ["create_godot_project_structure", "validate_godot_project"]
                if primary_is_godot
                else ["prepare_asset_ingest", "run_asset_ingest"]
            ),
            quality_gates=[
                "No ComfyUI image imports without review_required handling.",
                "Source paths stay inside generated/assets or generated/comfyui.",
                "Imported meshes retain valid collision and gameplay role metadata.",
            ],
            side_effects=(
                ["writes generated Godot project files", "validates generated Godot project"]
                if primary_is_godot
                else ["launches Unreal Editor", "imports generated assets into Content"]
            ),
            depends_on=["creative_review"],
            status="blocked",
            requires_confirmation=True,
            risks=[f"Blocked until Blender exports and user-approved visual decisions exist for {engine_label}."],
        ),
        _pipeline_stage(
            stage_id="unreal_production",
            order=7,
            title="Unreal production",
            title_zh="UE 制作",
            owner_agent="unreal-builder",
            participating_agents=["level-director", "qa-agent"],
            purpose=(
                "Create the UE project, assemble the greybox map, wire objective flow, and keep "
                "the default map playable in editor and packaged builds."
            ),
            inputs=["UnrealProjectPlan", "UnrealAssetIngestManifest", "GameplaySpec.level_beats"],
            outputs=["UE project structure", "M_Prototype_Greybox", "level assembly manifest"],
            artifacts=[
                "generated/unreal/**/*.uproject",
                "generated/unreal/*/Content/Maps/M_Prototype_Greybox.umap",
                "generated/unreal/*/fantasy-agent-level-assembly.json",
            ],
            mcp_tools=[
                "prepare_level_assembly",
                "run_level_assembly",
                "DataValidation",
            ],
            quality_gates=[
                f"Default map opens to {', '.join(unreal_plan.maps[:1])}.",
                "Spawn, route, hazards, checkpoints, objective, and exit are present.",
                "DataValidation returns zero blocking errors before packaging.",
            ],
            side_effects=[
                "writes generated Unreal project files",
                "launches Unreal Editor",
                "writes or updates generated .umap files",
            ],
            depends_on=["asset_integration"],
            status="blocked",
            requires_confirmation=True,
            risks=["Requires a compatible local Unreal Engine installation."],
        ),
        _pipeline_stage(
            stage_id="optimization_testing",
            order=8,
            title="Optimization and testing",
            title_zh="优化与测试",
            owner_agent="qa-agent",
            participating_agents=["unreal-builder", "director-agent"],
            purpose=(
                "Run playability, failure-feedback, performance, and packaged-build checks before "
                "visual polish expands the prototype."
            ),
            inputs=["QAPlan", "assembled UE map", "packaged build candidate"],
            outputs=["QA report", "performance notes", "blocking issue list", "package readiness decision"],
            artifacts=[
                "generated/qa-report.json",
                "generated/logs/qa/*.log",
                "generated/logs/unreal/*.log",
            ],
            mcp_tools=["DataValidation"],
            quality_gates=[
                f"Average session remains within {qa_plan.target_session_minutes} minutes.",
                "A first-time player can understand failure reason and restart.",
                "Packaged build opens directly into the prototype map.",
            ],
            side_effects=["runs Unreal commandlets or packaged build checks"],
            depends_on=["unreal_production"],
            status="blocked",
            requires_confirmation=True,
            risks=["Run this before broad visual expansion or packaging distribution."],
        ),
    ]
    if primary_is_godot:
        stages = [stage for stage in stages if stage.id != "unreal_production"]
        for stage in stages:
            if stage.id == "optimization_testing":
                stage.participating_agents = ["godot-builder", "director-agent"]
                stage.inputs = ["QAPlan", "assembled Godot scene", "Godot quick-play candidate"]
                stage.artifacts = ["generated/qa-report.json", "generated/logs/qa/*.log", "generated/logs/godot/*.log"]
                stage.mcp_tools = ["validate_godot_project"]
                stage.side_effects = ["runs Godot validation or quick-play checks"]
                stage.depends_on = ["godot_quick_play"]
    else:
        stages = [stage for stage in stages if stage.id != "godot_quick_play"]
    stages = sorted(stages, key=lambda stage: stage.order)
    for index, stage in enumerate(stages, start=1):
        stage.order = index
    return ProductionPipeline(
        project_name=unreal_plan.project_name,
        goal=goal,
        goal_i18n={
            "en": goal,
            "zh-CN": (
                f"把玩法、视觉参考、模块化资产、UE 组装和 QA 编排成 "
                f"{spec.title} 的 {spec.target_session_minutes} 分钟可玩切片。"
            ),
        },
        stages=stages,
        current_stage="gameplay_orchestration",
        next_stage="comfyui_visual_production",
        risks=[
            "Execution stages require explicit confirmation before MCP tool operations.",
            "Greybox playability remains the production priority over visual polish.",
            f"Requested locales: {', '.join(request.output_locales)}.",
        ],
        i18n=spec.i18n,
    )


def decompose_production_tasks(request: PromptRequest) -> DirectorTaskBreakdown:
    gameplay_spec = design_from_prompt(request)
    godot_plan = prepare_godot_project(gameplay_spec, _godot_engine_version(request.engine_version))
    blender_plan = prepare_blender_assets(gameplay_spec)
    comfyui_plan = prepare_comfyui_visuals(gameplay_spec)
    creative_review = prepare_creative_review(gameplay_spec, blender_plan, comfyui_plan)
    return _build_task_breakdown(
        request=request,
        spec=gameplay_spec,
        unreal_plan=prepare_unreal_project(gameplay_spec, _unreal_engine_version(request.engine_version)),
        godot_plan=godot_plan,
        blender_plan=blender_plan,
        comfyui_plan=comfyui_plan,
        creative_review=creative_review,
        qa_plan=prepare_qa_plan(gameplay_spec),
    )


def _task(
    *,
    task_id: str,
    title: str,
    title_zh: str,
    agent: str,
    purpose: str,
    inputs: list[str],
    outputs: list[str],
    side_effects: list[str] | None = None,
    depends_on: list[str] | None = None,
    artifacts: list[str] | None = None,
    status: str = "pending",
    requires_confirmation: bool = False,
    risks: list[str] | None = None,
) -> ProductionTask:
    return ProductionTask(
        id=task_id,
        title=title,
        title_i18n={"en": title, "zh-CN": title_zh},
        agent=agent,  # type: ignore[arg-type]
        purpose=purpose,
        inputs=inputs,
        outputs=outputs,
        side_effects=side_effects or [],
        depends_on=depends_on or [],
        artifacts=artifacts or [],
        status=status,  # type: ignore[arg-type]
        requires_confirmation=requires_confirmation,
        risks=risks or [],
    )


def _build_task_breakdown(
    *,
    request: PromptRequest,
    spec: GameplaySpec,
    unreal_plan: UnrealProjectPlan,
    godot_plan: GodotProjectPlan,
    blender_plan: BlenderAssetPlan,
    comfyui_plan: ComfyUIVisualPlan,
    creative_review: CreativeReviewReport,
    qa_plan: QAPlan,
) -> DirectorTaskBreakdown:
    primary_is_godot = _is_godot_engine(request.engine_version)
    tasks = [
        _task(
            task_id="gameplay_spec_review",
            title="Gameplay spec review",
            title_zh="玩法规格审查",
            agent="gameplay-agent",
            purpose="Validate the core loop, verbs, pacing, progression, win state, and failure states.",
            inputs=["PromptRequest", "user constraints"],
            outputs=["GameplaySpec"],
            artifacts=["generated/gameplay-spec.yaml"],
            status="ready",
            risks=["Reject mechanics that do not change player decisions."],
        ),
        _task(
            task_id="gdd_generation",
            title="Structured GDD generation",
            title_zh="结构化 GDD 生成",
            agent="gdd-writer",
            purpose="Render implementation-facing markdown without adding unapproved features.",
            inputs=["GameplaySpec"],
            outputs=["GDDDocument"],
            depends_on=["gameplay_spec_review"],
            artifacts=["generated/gdd.md"],
            status="ready",
        ),
        _task(
            task_id="level_beat_plan",
            title="Level beat plan",
            title_zh="关卡节奏计划",
            agent="level-director",
            purpose="Turn the loop into first-minute teaching, midpoint combination, and final challenge beats.",
            inputs=["GameplaySpec.level_beats", "GameplaySpec.asset_needs"],
            outputs=["level beat plan", "greybox requirements"],
            depends_on=["gameplay_spec_review"],
            artifacts=["generated/level-beats.yaml"],
            status="ready",
        ),
        _task(
            task_id="godot_quick_play_project",
            title="Godot quick-play project",
            title_zh="Godot 快速玩法项目",
            agent="godot-builder",
            purpose="Prepare a lightweight Godot 4 project for fast playable-loop validation before heavier UE work.",
            inputs=["GameplaySpec", "level beat plan"],
            outputs=["project.godot", "main scene", "prototype scripts", "Godot handoff manifest"],
            side_effects=[
                "writes generated Godot project files",
                "launches Godot headless import when confirmed",
            ],
            depends_on=["level_beat_plan"],
            artifacts=[
                "generated/godot-project-plan.yaml",
                "generated/godot/<project>/project.godot",
                *godot_plan.handoff_artifacts,
            ],
            status="pending",
            requires_confirmation=True,
            risks=["Use Godot to validate the loop quickly; keep Unreal as the production target."],
        ),
        _task(
            task_id="blender_asset_plan",
            title="Blender asset plan",
            title_zh="Blender 资产计划",
            agent="blender-worker",
            purpose=f"Prepare {len(blender_plan.jobs)} modular greybox asset jobs for readable play.",
            inputs=["GameplaySpec.asset_needs"],
            outputs=["BlenderAssetPlan", "Unreal import manifest plan"],
            depends_on=["level_beat_plan"],
            artifacts=["generated/blender-asset-plan.yaml"],
            status="ready",
        ),
        _task(
            task_id="blender_asset_generation",
            title="Generate Blender assets",
            title_zh="生成 Blender 资产",
            agent="blender-worker",
            purpose="Run approved Blender Python to create scale-correct FBX or GLB greybox assets.",
            inputs=["BlenderAssetPlan"],
            outputs=["FBX or GLB exports", "UnrealImportManifest"],
            side_effects=[
                "launches Blender",
                "writes generated/blender scripts",
                "writes generated/assets mesh exports",
            ],
            depends_on=["blender_asset_plan"],
            artifacts=["generated/assets/*.fbx", "generated/import-manifest.yaml"],
            status="pending",
            requires_confirmation=True,
        ),
        _task(
            task_id="comfyui_visual_plan",
            title="ComfyUI visual plan",
            title_zh="ComfyUI 视觉计划",
            agent="comfyui-worker",
            purpose=f"Prepare {len(comfyui_plan.jobs)} gameplay-readable reference jobs.",
            inputs=["GameplaySpec.notes_for_comfyui", "GameplaySpec.design_pillars"],
            outputs=["ComfyUIVisualPlan"],
            depends_on=["gameplay_spec_review"],
            artifacts=["generated/comfyui/comfyui-visual-plan.yaml"],
            status="ready",
        ),
        _task(
            task_id="comfyui_reference_generation",
            title="Generate ComfyUI references",
            title_zh="生成 ComfyUI 参考图",
            agent="comfyui-worker",
            purpose="Submit approved local ComfyUI workflow jobs for readability, material, and UI references.",
            inputs=["ComfyUIVisualPlan", "local ComfyUI checkpoint"],
            outputs=["review reference images", "ComfyUIRunManifest"],
            side_effects=[
                "submits ComfyUI prompt jobs",
                "writes generated/comfyui images",
                "writes generated/logs/comfyui logs",
            ],
            depends_on=["comfyui_visual_plan"],
            artifacts=["generated/comfyui/*/*.png", "generated/comfyui/run-manifest.json"],
            status="pending",
            requires_confirmation=True,
            risks=["References must be reviewed before becoming UE textures or UI assets."],
        ),
        _task(
            task_id="creative_review_plan",
            title="Creative review plan",
            title_zh="创意审阅计划",
            agent="creative-review-agent",
            purpose=(
                f"Prepare {len(creative_review.items)} review items that compare generated outputs "
                "against gameplay readability and user art direction."
            ),
            inputs=["GameplaySpec", "BlenderAssetPlan", "ComfyUIVisualPlan"],
            outputs=["CreativeReviewReport", "review questions", "revision prompt templates"],
            depends_on=["blender_asset_plan", "comfyui_visual_plan"],
            artifacts=["generated/creative-review-report.yaml"],
            status="ready",
        ),
        _task(
            task_id="creative_asset_review",
            title="Review generated assets",
            title_zh="审阅生成资产",
            agent="creative-review-agent",
            purpose=(
                "Ask the user to approve, revise, or reject generated ComfyUI references and Blender "
                "meshes before Unreal import."
            ),
            inputs=[
                "CreativeReviewReport",
                "generated ComfyUI images",
                "generated Blender exports",
                "user art direction",
            ],
            outputs=["AssetApprovalManifest", "revision prompts", "rejected asset list"],
            side_effects=["asks the user for approval decisions"],
            depends_on=[
                "creative_review_plan",
                "blender_asset_generation",
                "comfyui_reference_generation",
            ],
            artifacts=["generated/asset-approval-manifest.yaml"],
            status="blocked",
            requires_confirmation=True,
            risks=["Unapproved visuals or meshes must loop back to ComfyUI or Blender before UE import."],
        ),
        _task(
            task_id="unreal_project_setup",
            title="Unreal project setup",
            title_zh="Unreal 项目搭建",
            agent="unreal-builder",
            purpose=f"Prepare {unreal_plan.project_name} folders, plugins, maps, classes, and setup scripts.",
            inputs=["UnrealProjectPlan", "GameplaySpec"],
            outputs=["UE project structure", "content manifest", "setup script"],
            side_effects=[
                "writes generated/unreal project files",
                "creates generated Unreal content folders",
            ],
            depends_on=["gameplay_spec_review", "level_beat_plan"],
            artifacts=["generated/unreal/**/*.uproject", "generated/unreal/content-manifest.json"],
            status="pending",
            requires_confirmation=True,
            risks=["Requires a compatible local Unreal Engine installation before editor validation."],
        ),
        _task(
            task_id="unreal_asset_ingest",
            title="Unreal asset ingest",
            title_zh="Unreal 资产导入",
            agent="unreal-builder",
            purpose="Move reviewed Blender and ComfyUI outputs into the generated Unreal project.",
            inputs=[
                "UnrealAssetIngestManifest",
                "AssetApprovalManifest",
                "Blender exports",
                "reviewed ComfyUI references",
            ],
            outputs=["imported UE assets", "ingest logs"],
            side_effects=["launches Unreal Editor", "imports generated assets into Content"],
            depends_on=[
                "unreal_project_setup",
                "blender_asset_generation",
                "comfyui_reference_generation",
                "creative_asset_review",
            ],
            artifacts=["generated/unreal/*/Content/**", "generated/logs/unreal/*.log"],
            status="blocked",
            requires_confirmation=True,
            risks=[
                "Blocked until source assets exist, the UE project exists, and user approvals are recorded."
            ],
        ),
        _task(
            task_id="unreal_level_assembly",
            title="Unreal level assembly",
            title_zh="Unreal 关卡组装",
            agent="level-director",
            purpose=(
                "Place imported greybox assets into a playable route with spawn, traversal, "
                "checkpoint, objective, and exit beats."
            ),
            inputs=[
                "UnrealLevelAssemblyManifest",
                "imported generated assets",
                "GameplaySpec.level_beats",
            ],
            outputs=["generated UE map", "level assembly logs", "playtest route manifest"],
            side_effects=["launches Unreal Editor", "writes or updates generated .umap files"],
            depends_on=["unreal_asset_ingest", "qa_plan"],
            artifacts=[
                "generated/unreal/*/Content/Maps/*.umap",
                "generated/unreal/*/fantasy-agent-level-assembly.json",
                "generated/logs/unreal/*level_assembly*.log",
            ],
            status="blocked",
            requires_confirmation=True,
            risks=["Run DataValidation after assembly before broader playtesting."],
        ),
        _task(
            task_id="qa_plan",
            title="QA plan",
            title_zh="QA 计划",
            agent="qa-agent",
            purpose=f"Prepare smoke, playability, failure, and packaging checks for {qa_plan.target_session_minutes} minutes.",
            inputs=["GameplaySpec", "UnrealProjectPlan"],
            outputs=["QAPlan"],
            depends_on=["gameplay_spec_review"],
            artifacts=["generated/qa-plan.yaml"],
            status="ready",
        ),
        _task(
            task_id="playability_smoke_test",
            title="Playability smoke test",
            title_zh="可玩性冒烟测试",
            agent="qa-agent",
            purpose="Verify objective readability, restart flow, collision, map load, and package readiness.",
            inputs=["generated Unreal project", "imported assets", "QAPlan"],
            outputs=["QA report", "blocking issues"],
            side_effects=["runs Unreal commandlets or packaged build checks"],
            depends_on=["unreal_level_assembly", "qa_plan"],
            artifacts=["generated/qa-report.json", "generated/logs/qa/*.log"],
            status="blocked",
            requires_confirmation=True,
            risks=["Run this before visual polish or packaging expansion."],
        ),
    ]
    if primary_is_godot:
        tasks = [task for task in tasks if not task.id.startswith("unreal_")]
        for task in tasks:
            if task.id == "playability_smoke_test":
                task.inputs = ["generated Godot project", "imported assets", "QAPlan"]
                task.side_effects = ["runs Godot validation or quick-play checks"]
                task.depends_on = ["godot_quick_play_project", "qa_plan"]
    else:
        tasks = [task for task in tasks if task.id != "godot_quick_play_project"]
    goal = f"Produce a {spec.target_session_minutes}-minute playable vertical slice for {spec.title}."
    return DirectorTaskBreakdown(
        source_prompt=request.prompt,
        goal=goal,
        goal_i18n={
            "en": goal,
            "zh-CN": f"为 {spec.title} 制作一个 {spec.target_session_minutes} 分钟的可玩垂直切片。",
        },
        tasks=tasks,
        recommended_next_task="gameplay_spec_review",
        risks=[
            "Execution tasks require explicit confirmation before local tool operations.",
            "Prefer greybox playability before visual expansion.",
            "Unreal, Blender, and ComfyUI availability should be probed before execution.",
        ],
        next_actions=DIRECTOR_NEXT_ACTIONS,
        confirmation_required=any(task.requires_confirmation for task in tasks),
        i18n=spec.i18n,
    )


def run_director_workflow(request: PromptRequest) -> DirectorBuildPlan:
    gameplay_spec = design_from_prompt(request)
    unreal_plan = prepare_unreal_project(gameplay_spec, _unreal_engine_version(request.engine_version))
    godot_plan = prepare_godot_project(gameplay_spec, _godot_engine_version(request.engine_version))
    blender_plan = prepare_blender_assets(gameplay_spec)
    comfyui_plan = prepare_comfyui_visuals(gameplay_spec)
    creative_review = prepare_creative_review(gameplay_spec, blender_plan, comfyui_plan)
    qa_plan = prepare_qa_plan(gameplay_spec)
    production_pipeline = prepare_production_pipeline(
        request=request,
        spec=gameplay_spec,
        unreal_plan=unreal_plan,
        godot_plan=godot_plan,
        blender_plan=blender_plan,
        comfyui_plan=comfyui_plan,
        creative_review=creative_review,
        qa_plan=qa_plan,
    )
    return DirectorBuildPlan(
        gameplay_spec=gameplay_spec,
        gdd=render_gdd(gameplay_spec),
        unreal_plan=unreal_plan,
        godot_plan=godot_plan,
        blender_plan=blender_plan,
        comfyui_plan=comfyui_plan,
        creative_review=creative_review,
        qa_plan=qa_plan,
        task_breakdown=_build_task_breakdown(
            request=request,
            spec=gameplay_spec,
            unreal_plan=unreal_plan,
            godot_plan=godot_plan,
            blender_plan=blender_plan,
            comfyui_plan=comfyui_plan,
            creative_review=creative_review,
            qa_plan=qa_plan,
        ),
        production_pipeline=production_pipeline,
        next_actions=DIRECTOR_NEXT_ACTIONS,
    )
