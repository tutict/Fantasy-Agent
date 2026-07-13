from __future__ import annotations

import json

from fantasy_agent.contracts import (
    CompiledSpecArtifact,
    ProductionSpecBundle,
    SpecCompileResult,
    SpecTraceRecord,
)


def compile_godot_spec_bundle(bundle: ProductionSpecBundle) -> SpecCompileResult:
    segments = [
        bundle.level.teaching_segment,
        *bundle.level.mid_segments,
        bundle.level.final_test,
    ]
    enemy_table = next(
        (table for table in bundle.config_tables.tables if table.table_id == "enemies"),
        None,
    )
    handoff = {
        "schema_version": bundle.schema_version,
        "combat": bundle.combat.model_dump(mode="json") if bundle.combat else {"encounters": []},
        "level": {
            "segments": [segment.model_dump(mode="json") for segment in segments],
            "spawn_zones": bundle.level.spawn_zones,
            "safe_zones": bundle.level.safe_zones,
            "objective_gates": bundle.level.objective_gates,
            "hazard_rules": bundle.level.hazard_rules,
            "encounter_placement_rules": bundle.level.encounter_placement_rules,
        },
        "numeric": bundle.numeric.model_dump(mode="json"),
        "narrative": bundle.narrative.model_dump(mode="json"),
        "enemies": enemy_table.rows if enemy_table else [],
        "resource_pipeline": bundle.resource_pipeline.model_dump(mode="json"),
    }
    path = "data/production-spec-runtime.json"
    artifact = CompiledSpecArtifact(
        path=path,
        media_type="application/json",
        content=json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
    )
    fields = [
        "combat.encounters",
        "level.teaching_segment",
        "level.mid_segments",
        "level.final_test",
        "numeric.player_move_speed",
        "numeric.player_hp",
        "numeric.pressure_clock_seconds",
        "numeric.enemy_pressure",
        "narrative.hud_text.objective",
        "narrative.failure_feedback",
        "resource_pipeline.assets",
    ]
    traces = [
        SpecTraceRecord(spec_field=field, artifact_path=path, consumer="godot-spec-adapter")
        for field in fields
    ]
    return SpecCompileResult(
        target="godot",
        artifacts=[artifact],
        traces=traces,
        runtime_handoff=handoff,
    )