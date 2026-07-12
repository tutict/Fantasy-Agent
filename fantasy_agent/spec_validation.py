from __future__ import annotations

from fantasy_agent.contracts import (
    ProductionSpecBundle,
    SpecValidationIssue,
    SpecValidationReport,
)


def validate_production_spec_bundle(bundle: ProductionSpecBundle) -> SpecValidationReport:
    """Validate the M7 agent-executable production spec bundle."""

    issues: list[SpecValidationIssue] = []
    coverage = {
        "combat": bundle.combat is not None,
        "level": True,
        "numeric": True,
        "narrative": True,
        "config_tables": bool(bundle.config_tables.tables),
        "resource_pipeline": bool(bundle.resource_pipeline.assets),
    }

    if bundle.combat is not None:
        if bundle.combat.damage_model.contact_damage > 100:
            issues.append(
                SpecValidationIssue(
                    severity="error",
                    spec="CombatSpec",
                    field="damage_model.contact_damage",
                    message="contact_damage exceeds the conservative M7 boundary.",
                )
            )
        if not bundle.combat.player_counterplay:
            issues.append(
                SpecValidationIssue(
                    severity="error",
                    spec="CombatSpec",
                    field="player_counterplay",
                    message="Combat must declare player counterplay.",
                )
            )
        for encounter in bundle.combat.encounters:
            if not encounter.player_counterplay:
                issues.append(
                    SpecValidationIssue(
                        severity="error",
                        spec="CombatSpec",
                        field=f"encounters.{encounter.encounter_id}.player_counterplay",
                        message="Each encounter must declare counterplay.",
                    )
                )

    if not bundle.level.objective_gates:
        issues.append(
            SpecValidationIssue(
                severity="error",
                spec="LevelSpec",
                field="objective_gates",
                message="Level spec must expose objective gates for execution.",
            )
        )

    if bundle.numeric.pressure_clock_seconds < bundle.numeric.target_session_minutes * 45:
        issues.append(
            SpecValidationIssue(
                severity="warning",
                spec="NumericTuningSpec",
                field="pressure_clock_seconds",
                message="Pressure clock may be too short for the target session.",
            )
        )

    for asset in bundle.resource_pipeline.assets:
        if not asset.engine_destination:
            issues.append(
                SpecValidationIssue(
                    severity="error",
                    spec="ResourcePipelineSpec",
                    field=f"assets.{asset.asset_id}.engine_destination",
                    message="engine_destination is required before ingest.",
                )
            )
        if asset.approval_status != "approved" and not asset.blocked_reason:
            issues.append(
                SpecValidationIssue(
                    severity="warning",
                    spec="ResourcePipelineSpec",
                    field=f"assets.{asset.asset_id}.blocked_reason",
                    message="Non-approved assets should explain why they are blocked.",
                )
            )

    has_errors = any(issue.severity == "error" for issue in issues)
    status = "failed" if has_errors else "warning" if issues else "passed"
    return SpecValidationReport(status=status, issues=issues, coverage=coverage)
