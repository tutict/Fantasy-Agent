from __future__ import annotations

from fantasy_agent.contracts import (
    BlenderAssetPlan,
    CombatEncounterSpec,
    CombatSpec,
    ConfigTable,
    ConfigTableSpec,
    CreativeReviewReport,
    DamageModel,
    EnemyPressureTuning,
    GameplaySpec,
    LevelBeat,
    LevelSegmentSpec,
    LevelSpec,
    NarrativeBeatSpec,
    NarrativeSpec,
    NumericTuningSpec,
    ProductionSpecBundle,
    ResourcePipelineAsset,
    ResourcePipelineSpec,
)
from fantasy_agent.spec_validation import validate_production_spec_bundle


def build_production_spec_bundle(
    spec: GameplaySpec,
    *,
    blender_plan: BlenderAssetPlan | None = None,
    creative_review: CreativeReviewReport | None = None,
) -> ProductionSpecBundle:
    """Derive M7 executable production specs from the existing gameplay contract."""

    bundle = ProductionSpecBundle(
        gameplay_spec_title=spec.title,
        combat=_build_combat_spec(spec),
        level=_build_level_spec(spec),
        numeric=_build_numeric_spec(spec),
        narrative=_build_narrative_spec(spec),
        config_tables=_build_config_tables(spec),
        resource_pipeline=_build_resource_pipeline(
            spec,
            blender_plan=blender_plan,
            creative_review=creative_review,
        ),
        handoff_artifacts=[
            "generated/specs/production-spec-bundle.yaml",
            "generated/config/enemies.yaml",
            "generated/config/encounters.yaml",
            "generated/config/tuning.yaml",
            "generated/config/level-beats.yaml",
        ],
    )
    return bundle.model_copy(update={"validation": validate_production_spec_bundle(bundle)})


def _build_combat_spec(spec: GameplaySpec) -> CombatSpec | None:
    combat_verbs = {"attack", "evade", "recover", "position"}
    has_combat_language = bool(combat_verbs.intersection({verb.casefold() for verb in spec.core_verbs}))
    if not spec.enemies and not has_combat_language:
        return None

    encounters: list[CombatEncounterSpec] = []
    beats = spec.level_beats or [
        LevelBeat(
            name="Prototype Encounter",
            duration_minutes=spec.target_session_minutes,
            gameplay_focus="Validate enemy pressure in a compact greybox.",
            required_assets=["enemy marker"],
            success_condition=spec.win_state,
        )
    ]
    for index, enemy in enumerate(spec.enemies):
        beat = beats[min(index, len(beats) - 1)]
        encounters.append(
            CombatEncounterSpec(
                encounter_id=f"encounter_{index + 1}_{_slug(enemy.name)}",
                beat=beat.name,
                enemy_roles=[enemy.name],
                pressure_goal=_pressure_goal(enemy.behavior),
                telegraphs=[_telegraph_for_behavior(enemy.behavior)],
                player_counterplay=[_counterplay_for_behavior(enemy.behavior)],
            )
        )

    if not encounters and has_combat_language:
        beat = beats[0]
        encounters.append(
            CombatEncounterSpec(
                encounter_id="encounter_1_pressure_check",
                beat=beat.name,
                enemy_roles=["Pressure Dummy"],
                pressure_goal="Force positioning, attack timing, and recovery decisions.",
                telegraphs=["Use readable wind-up color before damage is applied."],
                player_counterplay=["Dodge out of the lane, then re-engage during cooldown."],
            )
        )

    enemy_roles = [enemy.name for enemy in spec.enemies] or ["Pressure Dummy"]
    avg_enemy_hp = round(sum(enemy.hp for enemy in spec.enemies) / len(spec.enemies)) if spec.enemies else 3
    return CombatSpec(
        encounters=encounters,
        enemy_roles=enemy_roles,
        damage_model=DamageModel(
            player_hp=5,
            enemy_hp_default=max(1, avg_enemy_hp),
            contact_damage=1,
            ranged_damage=1,
            recovery_seconds=1.0,
        ),
        failure_pressure=spec.failure_states[0] if spec.failure_states else "Enemy pressure can end the run.",
        telegraphs=list(dict.fromkeys(item for encounter in encounters for item in encounter.telegraphs)),
        player_counterplay=list(
            dict.fromkeys(item for encounter in encounters for item in encounter.player_counterplay)
        ),
    )


def _build_level_spec(spec: GameplaySpec) -> LevelSpec:
    beats = spec.level_beats or [
        LevelBeat(
            name="Prototype Route",
            duration_minutes=spec.target_session_minutes,
            gameplay_focus="Validate the complete loop in one compact greybox route.",
            required_assets=["start marker", "objective prop", "exit gate"],
            success_condition=spec.win_state,
        )
    ]
    segments = [_segment_from_beat(index, beat) for index, beat in enumerate(beats)]
    return LevelSpec(
        teaching_segment=segments[0],
        mid_segments=segments[1:-1],
        final_test=segments[-1],
        spawn_zones=[segment.spawn_zone for segment in segments],
        safe_zones=[segment.safe_zone for segment in segments],
        objective_gates=[segment.objective_gate for segment in segments],
        hazard_rules=[
            "Do not place lethal pressure inside the initial spawn zone.",
            "Keep hazards visually distinct from safe route floor material.",
            "Every hazard must support a recoverable learning failure in the first half.",
        ],
        encounter_placement_rules=[
            "Distribute enemies along level beats, away from player spawn and final exit.",
            "Patrol enemies teach route reading; chase enemies add time pressure.",
            "Stationary and ranged enemies must create readable zones, not unavoidable damage.",
        ],
    )


def _build_numeric_spec(spec: GameplaySpec) -> NumericTuningSpec:
    return NumericTuningSpec(
        target_session_minutes=spec.target_session_minutes,
        pressure_clock_seconds=spec.target_session_minutes * 60,
        enemy_pressure=EnemyPressureTuning(),
        resource_costs={
            "restart_run": 0.0,
            "primary_interaction": 1.0,
            "mistake_penalty_seconds": 8.0,
        },
        tuning_bounds={
            "player_move_speed": (1.0, 40.0),
            "player_hp": (1.0, 999.0),
            "enemy_count_multiplier": (0.0, 3.0),
            "move_speed_multiplier": (0.25, 3.0),
            "pressure_clock_seconds": (60.0, 1800.0),
        },
        qa_risks=[
            "Validate first completion stays within the 5-15 minute target.",
            "Tune enemy pressure down if the first minute punishes before teaching.",
        ],
    )


def _build_narrative_spec(spec: GameplaySpec) -> NarrativeSpec:
    beats = [
        NarrativeBeatSpec(
            beat_id=f"narrative_{index + 1}_{_slug(beat.name)}",
            level_beat=beat.name,
            player_goal=beat.gameplay_focus,
            objective_copy=beat.success_condition,
            failure_feedback=spec.failure_states[min(index, len(spec.failure_states) - 1)]
            if spec.failure_states
            else "Try again with clearer route reading.",
        )
        for index, beat in enumerate(spec.level_beats)
    ]
    if not beats:
        beats = [
            NarrativeBeatSpec(
                beat_id="narrative_1_prototype",
                level_beat="Prototype Route",
                player_goal=spec.player_fantasy,
                objective_copy=spec.win_state,
                failure_feedback=spec.failure_states[0] if spec.failure_states else "Retry the loop.",
            )
        ]
    return NarrativeSpec(
        player_fantasy=spec.player_fantasy,
        premise=spec.logline,
        beats=beats,
        objective_copy=[beat.objective_copy for beat in beats],
        failure_feedback=spec.failure_states or [beats[0].failure_feedback],
        hud_text={
            "objective": spec.win_state,
            "restart": "Press restart_run to retry the loop.",
            "failure": spec.failure_states[0] if spec.failure_states else "Loop failed.",
        },
    )


def _build_config_tables(spec: GameplaySpec) -> ConfigTableSpec:
    tables = [
        ConfigTable(
            table_id="enemies",
            primary_key="enemy_id",
            rows=[
                {
                    "enemy_id": _slug(enemy.name),
                    "name": enemy.name,
                    "behavior": enemy.behavior,
                    "hp": enemy.hp,
                    "count": enemy.count,
                }
                for enemy in spec.enemies
            ],
            export_path="generated/config/enemies.yaml",
        ),
        ConfigTable(
            table_id="encounters",
            primary_key="encounter_id",
            rows=[
                {
                    "encounter_id": f"beat_{index + 1}_{_slug(beat.name)}",
                    "beat": beat.name,
                    "duration_minutes": beat.duration_minutes,
                    "success_condition": beat.success_condition,
                }
                for index, beat in enumerate(spec.level_beats)
            ],
            export_path="generated/config/encounters.yaml",
        ),
        ConfigTable(
            table_id="tuning",
            primary_key="tuning_id",
            rows=[
                {
                    "tuning_id": "session",
                    "target_session_minutes": spec.target_session_minutes,
                    "pressure_clock_seconds": spec.target_session_minutes * 60,
                }
            ],
            export_path="generated/config/tuning.yaml",
        ),
        ConfigTable(
            table_id="level_beats",
            primary_key="beat_id",
            rows=[
                {
                    "beat_id": f"beat_{index + 1}",
                    "name": beat.name,
                    "duration_minutes": beat.duration_minutes,
                    "gameplay_focus": beat.gameplay_focus,
                    "success_condition": beat.success_condition,
                }
                for index, beat in enumerate(spec.level_beats)
            ],
            export_path="generated/config/level-beats.yaml",
        ),
        ConfigTable(
            table_id="narrative_beats",
            primary_key="beat_id",
            rows=[
                {
                    "beat_id": f"narrative_{index + 1}",
                    "level_beat": beat.name,
                    "objective_copy": beat.success_condition,
                }
                for index, beat in enumerate(spec.level_beats)
            ],
            export_path="generated/config/narrative-beats.yaml",
        ),
    ]
    return ConfigTableSpec(
        tables=tables,
        handoff_artifacts=[table.export_path for table in tables],
    )


def _build_resource_pipeline(
    spec: GameplaySpec,
    *,
    blender_plan: BlenderAssetPlan | None,
    creative_review: CreativeReviewReport | None,
) -> ResourcePipelineSpec:
    assets: list[ResourcePipelineAsset] = []
    if creative_review is not None:
        review_decisions = _review_decision_by_asset_id(creative_review)
        for item in creative_review.items:
            approval_status = review_decisions.get(item.asset_id, _approval_status(item.approval_status))
            assets.append(
                ResourcePipelineAsset(
                    asset_id=item.asset_id,
                    source=item.source,
                    role=item.gameplay_role,
                    approval_status=approval_status,
                    engine_destination=_engine_destination(item.source, item.asset_id),
                    blocked_reason=None
                    if approval_status == "approved"
                    else "Awaiting Creative Review approval.",
                )
            )
    elif blender_plan is not None:
        for job in blender_plan.jobs:
            assets.append(
                ResourcePipelineAsset(
                    asset_id=job.asset_name,
                    source="blender",
                    role=job.asset_kind,
                    approval_status="pending_user_review",
                    engine_destination=_engine_destination("blender", job.asset_name),
                    blocked_reason="Awaiting Creative Review approval.",
                )
            )
    else:
        for asset in spec.asset_needs:
            asset_id = _slug(asset)
            assets.append(
                ResourcePipelineAsset(
                    asset_id=asset_id,
                    source="blender",
                    role=asset,
                    approval_status="pending_user_review",
                    engine_destination=_engine_destination("blender", asset_id),
                    blocked_reason="Asset plan not generated yet.",
                )
            )

    return ResourcePipelineSpec(
        assets=assets,
        ingest_rules=[
            "Only approved Blender GLB assets may be copied into Godot res://assets/generated.",
            "ComfyUI outputs remain visual references until explicitly approved for production use.",
            "Rejected or revision assets must stay out of engine ingest manifests.",
        ],
        blocked_assets=[
            asset.asset_id for asset in assets if asset.approval_status != "approved"
        ],
    )


def _segment_from_beat(index: int, beat: LevelBeat) -> LevelSegmentSpec:
    beat_id = _slug(beat.name) or f"beat_{index + 1}"
    return LevelSegmentSpec(
        name=beat.name,
        duration_minutes=beat.duration_minutes,
        gameplay_focus=beat.gameplay_focus,
        spawn_zone=f"spawn_{beat_id}",
        safe_zone=f"safe_{beat_id}",
        objective_gate=f"gate_{beat_id}",
        placement_rules=[
            f"Place required assets near {beat.name}: {', '.join(beat.required_assets)}.",
            "Keep route width readable for the active verb and pressure source.",
        ],
    )


def _pressure_goal(behavior: str) -> str:
    return {
        "patrol": "Teach route judgment through moving sightline pressure.",
        "chase": "Create time pressure without blocking recovery routes.",
        "stationary": "Create a readable danger zone that forces route planning.",
        "ranged": "Create position pressure with a clear attack cadence.",
    }.get(behavior, "Create readable pressure tied to the core loop.")


def _telegraph_for_behavior(behavior: str) -> str:
    return {
        "patrol": "Patrol path and facing direction must be visible before contact.",
        "chase": "Detection radius should pulse before pursuit starts.",
        "stationary": "Danger zone marker should be visible from the safe lane.",
        "ranged": "Projectile wind-up and interval must be visible before firing.",
    }.get(behavior, "Pressure source must telegraph before punishment.")


def _counterplay_for_behavior(behavior: str) -> str:
    return {
        "patrol": "Wait, distract, or route around the patrol lane.",
        "chase": "Sprint through checkpoints and use recovery lanes to break pursuit.",
        "stationary": "Read the zone and approach through the safe side.",
        "ranged": "Move between cover windows during the ranged cooldown.",
    }.get(behavior, "Use the primary verb to avoid pressure and recover.")


def _approval_status(status: str) -> str:
    if status == "approved_for_unreal_ingest":
        return "approved"
    if status in {"approved", "needs_revision", "rejected", "pending_user_review"}:
        return status
    return "pending_user_review"


def _review_decision_by_asset_id(review: CreativeReviewReport) -> dict[str, str]:
    decisions: dict[str, str] = {}
    for asset_id in review.approved_asset_ids:
        decisions[asset_id] = "approved"
    for asset_id in review.revision_asset_ids:
        decisions[asset_id] = "needs_revision"
    for asset_id in review.rejected_asset_ids:
        decisions[asset_id] = "rejected"
    return decisions


def _engine_destination(source: str, asset_id: str) -> str:
    if source == "comfyui":
        return f"references/comfyui/{asset_id}.png"
    return f"assets/generated/{asset_id}.glb"


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "item"
