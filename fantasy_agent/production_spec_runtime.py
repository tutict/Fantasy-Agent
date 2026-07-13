from __future__ import annotations

import json
from pathlib import Path

import yaml

from fantasy_agent.contracts import (
    AssetApprovalManifest,
    ProductionSpecBundle,
    ResourcePipelineAsset,
    SpecCompileResult,
    SpecValidationReport,
)
from fantasy_agent.path_safety import assert_under
from fantasy_agent.spec_validation import validate_production_spec_bundle


class ProductionSpecExecutionBlocked(ValueError):
    def __init__(self, report: SpecValidationReport):
        self.report = report
        super().__init__("Production spec validation failed.")


def load_production_spec_bundle(
    path: Path | str,
    *,
    workspace_root: Path | str = ".",
) -> ProductionSpecBundle:
    root = Path(workspace_root).resolve()
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    assert_under(resolved, root)
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    if resolved.suffix.casefold() in {".yaml", ".yml"}:
        payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    elif resolved.suffix.casefold() == ".json":
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    else:
        raise ValueError("Production spec bundle must be YAML or JSON.")
    bundle = ProductionSpecBundle.model_validate(payload)
    if bundle.schema_version != "0.1":
        raise ValueError(f"Unsupported production spec schema_version: {bundle.schema_version}")
    return bundle


def ensure_production_spec_executable(bundle: ProductionSpecBundle) -> SpecValidationReport:
    report = validate_production_spec_bundle(bundle)
    if report.status == "failed":
        raise ProductionSpecExecutionBlocked(report)
    return report


def compile_production_spec_bundle(
    bundle: ProductionSpecBundle,
    *,
    target: str,
) -> SpecCompileResult:
    ensure_production_spec_executable(bundle)
    if target.casefold() == "godot":
        from fantasy_agent.godot_spec_adapter import compile_godot_spec_bundle

        return compile_godot_spec_bundle(bundle)
    if target.casefold() in {"unreal", "ue", "ue5"}:
        from fantasy_agent.unreal_spec_adapter import compile_unreal_spec_bundle

        return compile_unreal_spec_bundle(bundle)
    raise ValueError(f"Unsupported production spec target: {target}")


def sync_bundle_with_approval_manifest(
    bundle: ProductionSpecBundle,
    manifest: AssetApprovalManifest,
) -> ProductionSpecBundle:
    decisions = {decision.asset_id: decision.decision for decision in manifest.decisions}
    assets: list[ResourcePipelineAsset] = []
    for asset in bundle.resource_pipeline.assets:
        status = decisions.get(asset.asset_id, "pending_user_review")
        reason = {
            "approved": None,
            "needs_revision": "Creative Review requested revision.",
            "rejected": "Creative Review rejected asset.",
            "pending_user_review": "Awaiting Creative Review approval.",
        }[status]
        assets.append(asset.model_copy(update={"approval_status": status, "blocked_reason": reason}))
    resource_pipeline = bundle.resource_pipeline.model_copy(
        update={
            "assets": assets,
            "blocked_assets": [
                asset.asset_id for asset in assets if asset.approval_status != "approved"
            ],
        }
    )
    synced = bundle.model_copy(update={"resource_pipeline": resource_pipeline})
    return synced.model_copy(update={"validation": validate_production_spec_bundle(synced)})

def director_plan_from_production_spec_bundle(
    bundle: ProductionSpecBundle,
    *,
    engine_version: str = "Godot 4",
):
    """Build compatibility plans without regenerating the authoritative bundle."""

    from fantasy_agent.contracts import (
        DirectorBuildPlan,
        EnemySpec,
        GameplaySpec,
        LevelBeat,
        LoopStep,
        ProgressionSpec,
        SystemSpec,
    )
    from fantasy_agent.gdd import render_gdd
    from fantasy_agent.workflows import (
        prepare_blender_assets,
        prepare_comfyui_visuals,
        prepare_creative_review,
        prepare_godot_project,
        prepare_qa_plan,
        prepare_unreal_project,
    )

    segments = [
        bundle.level.teaching_segment,
        *bundle.level.mid_segments,
        bundle.level.final_test,
    ]
    enemy_table = next(
        (table for table in bundle.config_tables.tables if table.table_id == "enemies"),
        None,
    )
    enemies = [
        EnemySpec(
            name=str(row.get("name", row.get("enemy_id", "Enemy"))),
            behavior=str(row.get("behavior", "patrol")),
            hp=int(row.get("hp", bundle.numeric.player_hp)),
            count=int(row.get("count", 1)),
        )
        for row in (enemy_table.rows if enemy_table else [])
    ]
    win_state = bundle.narrative.objective_copy[-1]
    failure_states = bundle.narrative.failure_feedback
    gameplay_spec = GameplaySpec(
        title=bundle.gameplay_spec_title,
        logline=bundle.narrative.premise,
        target_session_minutes=bundle.numeric.target_session_minutes,
        player_fantasy=bundle.narrative.player_fantasy,
        design_pillars=[
            "Spec-driven execution",
            "Readable player decisions",
            "Recoverable failure feedback",
        ],
        core_verbs=["move", "interact", "recover"],
        core_loop=[
            LoopStep(
                order=1,
                action="Read the current objective",
                player_decision="Choose a route through the active level segment.",
                feedback=bundle.narrative.hud_text.get("objective", win_state),
            ),
            LoopStep(
                order=2,
                action="Execute the route under pressure",
                player_decision="Use safe zones, counterplay, and timing.",
                feedback=failure_states[0],
            ),
            LoopStep(
                order=3,
                action="Pass the objective gate",
                player_decision="Commit when the success condition is readable.",
                feedback=win_state,
            ),
        ],
        systems=[
            SystemSpec(
                name="SpecRuntime",
                purpose="Apply compiled production-spec values.",
                inputs=["ProductionSpecBundle"],
                outputs=["runtime handoff"],
                failure_pressure=failure_states[0],
            ),
            SystemSpec(
                name="ObjectiveGates",
                purpose="Advance through declared level objective gates.",
                inputs=bundle.level.objective_gates,
                outputs=["level progression"],
                failure_pressure=failure_states[0],
            ),
            SystemSpec(
                name="ReadableFeedback",
                purpose="Expose objective and failure text from NarrativeSpec.",
                inputs=bundle.narrative.objective_copy,
                outputs=bundle.narrative.failure_feedback,
                failure_pressure=failure_states[0],
            ),
        ],
        progression=ProgressionSpec(
            first_minute=bundle.level.teaching_segment.gameplay_focus,
            midpoint_shift=(
                bundle.level.mid_segments[0].gameplay_focus
                if bundle.level.mid_segments
                else bundle.level.teaching_segment.gameplay_focus
            ),
            final_minutes=bundle.level.final_test.gameplay_focus,
        ),
        win_state=win_state,
        failure_states=failure_states,
        level_beats=[
            LevelBeat(
                name=segment.name,
                duration_minutes=segment.duration_minutes,
                gameplay_focus=segment.gameplay_focus,
                required_assets=["spec marker", segment.objective_gate],
                success_condition=next(
                    (
                        beat.objective_copy
                        for beat in bundle.narrative.beats
                        if beat.level_beat == segment.name
                    ),
                    win_state,
                ),
            )
            for segment in segments
        ],
        asset_needs=[asset.role for asset in bundle.resource_pipeline.assets] or ["spec marker"],
        qa_focus=bundle.numeric.qa_risks or ["Validate compiled spec execution."],
        notes_for_unreal=["Use ProductionSpecBundle compiled DataTables and DataAssets."],
        notes_for_blender=["Only produce assets declared by ResourcePipelineSpec."],
        notes_for_comfyui=["Keep visual references subordinate to NarrativeSpec objectives."],
        enemies=enemies,
    )
    unreal_plan = prepare_unreal_project(gameplay_spec, engine_version if "unreal" in engine_version.casefold() or "ue" in engine_version.casefold() else "UE5")
    godot_plan = prepare_godot_project(gameplay_spec, engine_version if "godot" in engine_version.casefold() else "Godot 4")
    blender_plan = prepare_blender_assets(gameplay_spec)
    comfyui_plan = prepare_comfyui_visuals(gameplay_spec)
    creative_review = prepare_creative_review(gameplay_spec, blender_plan, comfyui_plan)
    return DirectorBuildPlan(
        gameplay_spec=gameplay_spec,
        production_spec_bundle=bundle,
        gdd=render_gdd(gameplay_spec),
        unreal_plan=unreal_plan,
        godot_plan=godot_plan,
        blender_plan=blender_plan,
        comfyui_plan=comfyui_plan,
        creative_review=creative_review,
        qa_plan=prepare_qa_plan(gameplay_spec),
        next_actions=["Validate, compile, preview side effects, then execute the loaded bundle."],
    )