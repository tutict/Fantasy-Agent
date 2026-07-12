import json

import pytest
from pydantic import ValidationError

from fantasy_agent.contracts import (
    CombatEncounterSpec,
    CombatSpec,
    CreativeReviewReport,
    DamageModel,
    PromptRequest,
    ResourcePipelineAsset,
)
from fantasy_agent.production_specs import build_production_spec_bundle
from fantasy_agent.spec_validation import validate_production_spec_bundle
from fantasy_agent.workflows import (
    prepare_blender_assets,
    prepare_comfyui_visuals,
    prepare_creative_review,
    run_director_workflow,
)


def test_production_spec_bundle_derives_agent_executable_specs():
    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena where a ranger evades turrets and guards")
    )

    bundle = plan.production_spec_bundle

    assert bundle is not None
    assert bundle.source == "fantasy-agent.production-specs"
    assert bundle.combat is not None
    assert bundle.combat.encounters
    assert bundle.combat.damage_model.player_hp >= 1
    assert bundle.level.teaching_segment.name
    assert bundle.level.final_test.name
    assert bundle.numeric.enemy_pressure.enemy_count_multiplier == 1.0
    assert bundle.narrative.objective_copy
    assert {table.table_id for table in bundle.config_tables.tables} >= {
        "enemies",
        "encounters",
        "tuning",
        "level_beats",
    }
    assert bundle.resource_pipeline.assets
    assert "generated/specs/production-spec-bundle.yaml" in bundle.handoff_artifacts


def test_non_combat_prompt_keeps_combat_spec_optional():
    plan = run_director_workflow(
        PromptRequest(prompt="a career portfolio story about choosing your own road")
    )

    assert plan.production_spec_bundle is not None
    assert plan.production_spec_bundle.combat is None
    assert "narrative_beats" in {
        table.table_id for table in plan.production_spec_bundle.config_tables.tables
    }


def test_production_spec_validation_reports_design_risks():
    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena where a ranger evades turrets and guards")
    )
    bundle = plan.production_spec_bundle
    assert bundle is not None and bundle.combat is not None
    broken = bundle.model_copy(
        update={
            "combat": bundle.combat.model_copy(
                update={
                    "encounters": [
                        encounter.model_copy(update={"player_counterplay": []})
                        for encounter in bundle.combat.encounters
                    ],
                    "damage_model": bundle.combat.damage_model.model_copy(
                        update={"contact_damage": 999}
                    ),
                }
            ),
            "resource_pipeline": bundle.resource_pipeline.model_copy(
                update={
                    "assets": [
                        asset.model_copy(update={"engine_destination": ""})
                        for asset in bundle.resource_pipeline.assets[:1]
                    ]
                }
            ),
        }
    )

    report = validate_production_spec_bundle(broken)

    assert report.status == "failed"
    assert any("counterplay" in issue.message for issue in report.issues)
    assert any("contact_damage" in issue.message for issue in report.issues)
    assert any("engine_destination" in issue.message for issue in report.issues)


def test_contract_boundaries_reject_invalid_numeric_specs():
    with pytest.raises(ValidationError):
        DamageModel(player_hp=0)

    with pytest.raises(ValidationError):
        CombatSpec(
            encounters=[],
            enemy_roles=[],
            damage_model=DamageModel(contact_damage=999),
            failure_pressure="unfair burst damage",
            telegraphs=[],
            player_counterplay=[],
        )

    with pytest.raises(ValidationError):
        CombatEncounterSpec(
            encounter_id="encounter_empty_role",
            beat="Prototype",
            enemy_roles=[],
            pressure_goal="Force route decisions.",
            telegraphs=["Readable wind-up."],
            player_counterplay=["Dodge during cooldown."],
        )

    with pytest.raises(ValidationError):
        ResourcePipelineAsset(
            asset_id="bad_asset",
            source="blender",
            role="objective",
            approval_status="approved",
            engine_destination="",
        )


def test_build_production_spec_bundle_accepts_old_gameplay_spec_only():
    spec = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes a haunted train station")
    ).gameplay_spec

    bundle = build_production_spec_bundle(spec)

    assert bundle.gameplay_spec_title == spec.title
    assert bundle.level.objective_gates
    assert bundle.numeric.tuning_bounds
    assert json.loads(bundle.model_dump_json())["schema_version"] == "0.1"

def test_resource_pipeline_uses_report_level_creative_review_decisions():
    plan = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes a haunted train station")
    )
    blender_plan = prepare_blender_assets(plan.gameplay_spec)
    comfyui_plan = prepare_comfyui_visuals(plan.gameplay_spec)
    review = prepare_creative_review(plan.gameplay_spec, blender_plan, comfyui_plan)
    assert len(review.items) >= 3
    approved_item = review.items[0]
    revised_item = review.items[1]
    rejected_item = review.items[2]
    report = CreativeReviewReport(
        art_direction=review.art_direction,
        items=review.items,
        required_user_decisions=review.required_user_decisions,
        approved_asset_ids=[approved_item.asset_id],
        revision_asset_ids=[revised_item.asset_id],
        rejected_asset_ids=[rejected_item.asset_id],
    )

    bundle = build_production_spec_bundle(plan.gameplay_spec, creative_review=report)
    assets_by_id = {asset.asset_id: asset for asset in bundle.resource_pipeline.assets}

    assert assets_by_id[approved_item.asset_id].approval_status == "approved"
    assert assets_by_id[approved_item.asset_id].blocked_reason is None
    assert assets_by_id[revised_item.asset_id].approval_status == "needs_revision"
    assert assets_by_id[rejected_item.asset_id].approval_status == "rejected"
    assert approved_item.asset_id not in bundle.resource_pipeline.blocked_assets
    assert revised_item.asset_id in bundle.resource_pipeline.blocked_assets
    assert rejected_item.asset_id in bundle.resource_pipeline.blocked_assets
