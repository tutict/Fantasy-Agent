from pathlib import Path

import pytest
import yaml

from fantasy_agent.contracts import AssetApprovalDecision, AssetApprovalManifest, PromptRequest
from fantasy_agent.production_spec_runtime import (
    ProductionSpecExecutionBlocked,
    compile_production_spec_bundle,
    ensure_production_spec_executable,
    load_production_spec_bundle,
    sync_bundle_with_approval_manifest,
)
from fantasy_agent.spec_validation import validate_production_spec_bundle
from fantasy_agent.workflows import run_director_workflow


def _bundle():
    plan = run_director_workflow(
        PromptRequest(
            prompt="a stealth courier escapes a guarded haunted station",
            target_minutes=10,
            engine_version="Godot 4",
        )
    )
    assert plan.production_spec_bundle is not None
    return plan.production_spec_bundle


def test_load_production_spec_bundle_accepts_yaml_and_json(tmp_path: Path):
    bundle = _bundle()
    yaml_path = tmp_path / "bundle.yaml"
    json_path = tmp_path / "bundle.json"
    yaml_path.write_text(
        yaml.safe_dump(bundle.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    json_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    loaded_yaml = load_production_spec_bundle(yaml_path, workspace_root=tmp_path)
    loaded_json = load_production_spec_bundle(json_path, workspace_root=tmp_path)

    assert loaded_yaml == bundle
    assert loaded_json == bundle


def test_deep_validation_rejects_cross_spec_and_config_errors():
    bundle = _bundle()
    assert bundle.combat is not None
    broken_encounter = bundle.combat.encounters[0].model_copy(update={"beat": "missing_beat"})
    enemy_table = next(table for table in bundle.config_tables.tables if table.table_id == "enemies")
    duplicate_rows = [*enemy_table.rows, dict(enemy_table.rows[0])]
    broken_table = enemy_table.model_copy(
        update={"rows": duplicate_rows, "export_path": "../outside/enemies.yaml"}
    )
    broken = bundle.model_copy(
        update={
            "combat": bundle.combat.model_copy(update={"encounters": [broken_encounter]}),
            "config_tables": bundle.config_tables.model_copy(
                update={
                    "tables": [
                        broken_table if table.table_id == "enemies" else table
                        for table in bundle.config_tables.tables
                    ]
                }
            ),
        }
    )

    report = validate_production_spec_bundle(broken)

    assert report.status == "failed"
    fields = {issue.field for issue in report.issues}
    assert "encounters.encounter_1_patrol_guard.beat" in fields
    assert "tables.enemies.primary_key" in fields
    assert "tables.enemies.export_path" in fields


def test_failed_bundle_blocks_execution_before_compile():
    bundle = _bundle()
    broken = bundle.model_copy(
        update={"level": bundle.level.model_copy(update={"objective_gates": []})}
    )

    with pytest.raises(ProductionSpecExecutionBlocked):
        ensure_production_spec_executable(broken)


def test_compile_dispatches_to_target_adapter():
    bundle = _bundle()

    godot = compile_production_spec_bundle(bundle, target="godot")
    unreal = compile_production_spec_bundle(bundle, target="unreal")

    assert godot.target == "godot"
    assert unreal.target == "unreal"
    assert godot.traces
    assert unreal.traces


def test_sync_bundle_with_approval_manifest_updates_resource_pipeline():
    bundle = _bundle()
    asset = bundle.resource_pipeline.assets[0]
    manifest = AssetApprovalManifest(
        decisions=[
            AssetApprovalDecision(
                asset_id=asset.asset_id,
                source=asset.source,
                asset_path=f"generated/assets/{asset.asset_id}.glb",
                gameplay_role=asset.role,
                decision="approved",
            )
        ],
        approved_asset_ids=[asset.asset_id],
    )

    synced = sync_bundle_with_approval_manifest(bundle, manifest)
    synced_asset = next(item for item in synced.resource_pipeline.assets if item.asset_id == asset.asset_id)

    assert synced_asset.approval_status == "approved"
    assert synced_asset.blocked_reason is None
    assert asset.asset_id not in synced.resource_pipeline.blocked_assets



def test_cli_spec_file_prints_loaded_bundle(tmp_path: Path, monkeypatch, capsys):
    from fantasy_agent.__main__ import main

    bundle = _bundle()
    path = tmp_path / "bundle.yaml"
    path.write_text(
        yaml.safe_dump(bundle.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--spec-file", "bundle.yaml", "--format", "specs"])

    assert exit_code == 0
    assert bundle.gameplay_spec_title in capsys.readouterr().out