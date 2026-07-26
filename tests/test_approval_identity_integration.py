from __future__ import annotations

from pathlib import Path

import yaml

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.executor import execute_godot_demo
from fantasy_agent.godot_mcp import GodotMCPBridge
from fantasy_agent.workflows import (
    build_asset_approval_manifest,
    run_director_workflow,
)
from tests.test_executor import _FakeBlenderBridge, _ok_runner


_EXPORTED_REL = "generated/assets/reviewed_prop.glb"


def _execute_with_producer_manifest(tmp_path: Path, reviewed_bytes: bytes):
    plan = run_director_workflow(
        PromptRequest(
            prompt="rooftop parkour chase across neon towers",
            target_minutes=10,
            engine_version="Godot 4",
        )
    )
    reviewed_path = tmp_path / _EXPORTED_REL
    reviewed_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_path.write_bytes(reviewed_bytes)

    blender_item = next(item for item in plan.creative_review.items if item.source == "blender")
    reviewed_item = blender_item.model_copy(
        update={
            "asset_id": "reviewed_prop",
            "asset_path": reviewed_path.as_posix(),
        }
    )
    focused_review = plan.creative_review.model_copy(update={"items": [reviewed_item]})
    manifest = build_asset_approval_manifest(
        focused_review,
        {reviewed_item.asset_id: "approved"},
        workspace_root=tmp_path,
    )
    manifest_path = tmp_path / "generated" / "asset-approval-manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )

    result = execute_godot_demo(
        plan,
        session_id="identity-replacement",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        workspace_root=tmp_path,
        bridge=GodotMCPBridge(tmp_path, runner=_ok_runner),
        blender_bridge=_FakeBlenderBridge(
            status="executed",
            exported=[_EXPORTED_REL],
            root=tmp_path,
        ),
    )
    return result


def test_producer_manifest_allows_unchanged_approved_bytes(tmp_path: Path):
    result = _execute_with_producer_manifest(tmp_path, b"glTF-stub")

    gate = next(stage for stage in result.stages if stage.name == "approval_gate")
    assert gate.metadata["approved_assets"] == [_EXPORTED_REL]
    assert gate.metadata["skipped_assets"] == []
    assert "copy_assets" in [stage.name for stage in result.stages]
    copied = (
        tmp_path / result.project_dir / "assets" / "generated" / "reviewed_prop.glb"
    )
    assert copied.read_bytes() == b"glTF-stub"


def test_producer_manifest_rejects_same_path_byte_replacement_before_copy(
    tmp_path: Path,
):
    result = _execute_with_producer_manifest(tmp_path, b"reviewed-glb-bytes")

    gate = next(stage for stage in result.stages if stage.name == "approval_gate")
    assert gate.metadata["approved_assets"] == []
    assert gate.metadata["skipped_assets"] == [_EXPORTED_REL]
    assert "copy_assets" not in [stage.name for stage in result.stages]
    assert not (
        tmp_path / result.project_dir / "assets" / "generated" / "reviewed_prop.glb"
    ).exists()
