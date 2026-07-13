from __future__ import annotations

from pathlib import Path

from fantasy_agent.contracts import (
    ProductionSpecBundle,
    SpecValidationIssue,
    SpecValidationReport,
)


def validate_production_spec_bundle(bundle: ProductionSpecBundle) -> SpecValidationReport:
    """Run structural, referential, numeric, path, and approval checks."""

    issues: list[SpecValidationIssue] = []
    segments = [
        bundle.level.teaching_segment,
        *bundle.level.mid_segments,
        bundle.level.final_test,
    ]
    level_names = {segment.name for segment in segments}

    if bundle.combat is not None:
        if bundle.combat.damage_model.contact_damage > 100:
            _issue(
                issues,
                "error",
                "CombatSpec",
                "damage_model.contact_damage",
                "contact_damage exceeds the conservative M7 boundary.",
            )
        if not bundle.combat.player_counterplay:
            _issue(
                issues,
                "error",
                "CombatSpec",
                "player_counterplay",
                "Combat must declare player counterplay.",
            )
        declared_roles = set(bundle.combat.enemy_roles)
        for encounter in bundle.combat.encounters:
            if not encounter.player_counterplay:
                _issue(
                    issues,
                    "error",
                    "CombatSpec",
                    f"encounters.{encounter.encounter_id}.player_counterplay",
                    "Each encounter must declare counterplay.",
                )
            if encounter.beat not in level_names:
                _issue(
                    issues,
                    "error",
                    "CombatSpec",
                    f"encounters.{encounter.encounter_id}.beat",
                    f"Encounter references unknown level beat: {encounter.beat}.",
                )
            missing_roles = sorted(set(encounter.enemy_roles) - declared_roles)
            if missing_roles:
                _issue(
                    issues,
                    "error",
                    "CombatSpec",
                    f"encounters.{encounter.encounter_id}.enemy_roles",
                    f"Encounter references undeclared enemy roles: {', '.join(missing_roles)}.",
                )

    if not bundle.level.objective_gates:
        _issue(
            issues,
            "error",
            "LevelSpec",
            "objective_gates",
            "Level spec must expose objective gates for execution.",
        )
    total_minutes = sum(segment.duration_minutes for segment in segments)
    if total_minutes != bundle.numeric.target_session_minutes:
        _issue(
            issues,
            "error",
            "LevelSpec",
            "segments.duration_minutes",
            (
                f"Level segments total {total_minutes} minutes but NumericTuningSpec targets "
                f"{bundle.numeric.target_session_minutes}."
            ),
        )

    for beat in bundle.narrative.beats:
        if beat.level_beat not in level_names:
            _issue(
                issues,
                "error",
                "NarrativeSpec",
                f"beats.{beat.beat_id}.level_beat",
                f"Narrative beat references unknown level beat: {beat.level_beat}.",
            )

    if bundle.numeric.pressure_clock_seconds < bundle.numeric.target_session_minutes * 45:
        _issue(
            issues,
            "warning",
            "NumericTuningSpec",
            "pressure_clock_seconds",
            "Pressure clock may be too short for the target session.",
        )
    numeric_values = {
        "player_move_speed": bundle.numeric.player_move_speed,
        "player_hp": bundle.numeric.player_hp,
        "pressure_clock_seconds": bundle.numeric.pressure_clock_seconds,
        "enemy_count_multiplier": bundle.numeric.enemy_pressure.enemy_count_multiplier,
        "move_speed_multiplier": bundle.numeric.enemy_pressure.move_speed_multiplier,
        "detection_radius_multiplier": bundle.numeric.enemy_pressure.detection_radius_multiplier,
        "patrol_radius_multiplier": bundle.numeric.enemy_pressure.patrol_radius_multiplier,
        "ranged_interval_multiplier": bundle.numeric.enemy_pressure.ranged_interval_multiplier,
    }
    for key, bounds in bundle.numeric.tuning_bounds.items():
        lower, upper = bounds
        if lower > upper:
            _issue(
                issues,
                "error",
                "NumericTuningSpec",
                f"tuning_bounds.{key}",
                "Tuning lower bound exceeds upper bound.",
            )
        if key in numeric_values and not lower <= float(numeric_values[key]) <= upper:
            _issue(
                issues,
                "error",
                "NumericTuningSpec",
                key,
                f"{key} is outside its declared tuning bounds.",
            )

    table_ids: set[str] = set()
    for table in bundle.config_tables.tables:
        if table.table_id in table_ids:
            _issue(
                issues,
                "error",
                "ConfigTableSpec",
                "tables.table_id",
                f"Duplicate config table id: {table.table_id}.",
            )
        table_ids.add(table.table_id)
        export_path = Path(table.export_path.replace("\\", "/"))
        if (
            export_path.is_absolute()
            or ".." in export_path.parts
            or export_path.parts[:2] != ("generated", "config")
        ):
            _issue(
                issues,
                "error",
                "ConfigTableSpec",
                f"tables.{table.table_id}.export_path",
                "Config table export_path must stay under generated/config.",
            )
        seen_keys: set[str] = set()
        for row_index, row in enumerate(table.rows):
            primary_value = str(row.get(table.primary_key, ""))
            if not primary_value:
                _issue(
                    issues,
                    "error",
                    "ConfigTableSpec",
                    f"tables.{table.table_id}.rows.{row_index}.{table.primary_key}",
                    "Config row is missing its primary key.",
                )
            elif primary_value in seen_keys:
                _issue(
                    issues,
                    "error",
                    "ConfigTableSpec",
                    f"tables.{table.table_id}.primary_key",
                    f"Duplicate primary key value: {primary_value}.",
                )
            seen_keys.add(primary_value)

    blocked_assets = set(bundle.resource_pipeline.blocked_assets)
    for asset in bundle.resource_pipeline.assets:
        if not asset.engine_destination:
            _issue(
                issues,
                "error",
                "ResourcePipelineSpec",
                f"assets.{asset.asset_id}.engine_destination",
                "engine_destination is required before ingest.",
            )
        if asset.approval_status == "approved":
            if asset.asset_id in blocked_assets or asset.blocked_reason:
                _issue(
                    issues,
                    "error",
                    "ResourcePipelineSpec",
                    f"assets.{asset.asset_id}.approval_status",
                    "Approved assets must not remain blocked.",
                )
        else:
            if not asset.blocked_reason:
                _issue(
                    issues,
                    "warning",
                    "ResourcePipelineSpec",
                    f"assets.{asset.asset_id}.blocked_reason",
                    "Non-approved assets should explain why they are blocked.",
                )
            if asset.asset_id not in blocked_assets:
                _issue(
                    issues,
                    "error",
                    "ResourcePipelineSpec",
                    f"assets.{asset.asset_id}.blocked_assets",
                    "Non-approved asset is missing from blocked_assets.",
                )

    coverage = {
        "combat": bundle.combat is not None,
        "level": bool(level_names and bundle.level.objective_gates),
        "numeric": bool(bundle.numeric.tuning_bounds),
        "narrative": bool(bundle.narrative.beats),
        "config_tables": bool(bundle.config_tables.tables),
        "resource_pipeline": bool(bundle.resource_pipeline.assets),
        "cross_spec_references": not any(
            issue.severity == "error"
            and issue.field.endswith((".beat", ".level_beat", ".enemy_roles"))
            for issue in issues
        ),
    }
    has_errors = any(issue.severity == "error" for issue in issues)
    status = "failed" if has_errors else "warning" if issues else "passed"
    return SpecValidationReport(status=status, issues=issues, coverage=coverage)


def _issue(
    issues: list[SpecValidationIssue],
    severity: str,
    spec: str,
    field: str,
    message: str,
) -> None:
    issues.append(
        SpecValidationIssue(
            severity=severity,
            spec=spec,
            field=field,
            message=message,
        )
    )