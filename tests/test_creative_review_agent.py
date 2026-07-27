from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from fantasy_agent.contracts import CreativeReviewRequest, PromptRequest
from fantasy_agent.path_safety import WorkspacePathError
from fantasy_agent.workflows import (
    build_asset_approval_manifest,
    prepare_blender_assets,
    prepare_comfyui_visuals,
    prepare_creative_review,
    run_director_workflow,
)


def _load_creative_review_app():
    module_path = Path("apps/creative-review-agent/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_creative_review_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_creative_review_blocks_unreal_ingest_until_user_decisions():
    director_plan = run_director_workflow(
        PromptRequest(
            prompt="a rooftop parkour demo with wall-runs and checkpoints",
            target_minutes=10,
        )
    )

    review = prepare_creative_review(
        director_plan.gameplay_spec,
        director_plan.blender_plan,
        director_plan.comfyui_plan,
    )

    assert review.approval_gate == "blocks_unreal_ingest"
    assert review.required_user_decisions
    assert len(review.items) == len(director_plan.blender_plan.jobs) + len(
        director_plan.comfyui_plan.jobs
    )
    assert all(item.approval_status == "pending_user_review" for item in review.items)
    assert any(item.revision_prompt for item in review.items if item.source == "comfyui")


def test_creative_review_agent_endpoint_returns_report_model():
    module = _load_creative_review_app()
    director_plan = run_director_workflow(
        PromptRequest(
            prompt="a stealth courier escapes a haunted train station",
            target_minutes=10,
        )
    )
    request = CreativeReviewRequest(
        gameplay_spec=director_plan.gameplay_spec,
        blender_plan=prepare_blender_assets(director_plan.gameplay_spec),
        comfyui_plan=prepare_comfyui_visuals(director_plan.gameplay_spec),
    )

    response = module.review(request)

    assert module.health()["agent"] == "creative-review-agent"
    assert response.source == "creative-review-agent"
    assert response.items
    assert response.handoff_artifacts == [
        "generated/creative-review-report.yaml",
        "generated/asset-approval-manifest.yaml",
    ]


def test_build_asset_approval_manifest_classifies_review_decisions(tmp_path: Path):
    director_plan = run_director_workflow(
        PromptRequest(
            prompt="a stealth courier escapes a haunted train station",
            target_minutes=10,
        )
    )
    review = prepare_creative_review(
        director_plan.gameplay_spec,
        director_plan.blender_plan,
        director_plan.comfyui_plan,
    )
    first = review.items[0].asset_id
    second = review.items[1].asset_id
    third = review.items[2].asset_id
    materialized_items = []
    for index, item in enumerate(review.items):
        artifact_path = tmp_path / f'artifact-{index}.bin'
        artifact_path.write_bytes(f'artifact-{index}'.encode())
        materialized_items.append(
            item.model_copy(update={'asset_path': artifact_path.as_posix()})
        )
    review = review.model_copy(update={'items': materialized_items})

    manifest = build_asset_approval_manifest(
        review,
        {first: "approved", second: "needs_revision", third: "rejected"},
        workspace_root=tmp_path,
    )

    assert manifest.approval_gate == "blocks_unreal_ingest"
    assert manifest.approved_asset_ids == [first]
    assert all(decision.artifact_identity is not None for decision in manifest.decisions)
    assert manifest.revision_asset_ids == [second]
    assert manifest.rejected_asset_ids == [third]
    assert review.items[3].asset_id in manifest.pending_asset_ids
    assert next(d for d in manifest.decisions if d.asset_id == second).revision_prompt


def test_build_asset_approval_manifest_binds_reviewed_file_bytes(tmp_path: Path):
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    review = prepare_creative_review(
        director_plan.gameplay_spec,
        director_plan.blender_plan,
        director_plan.comfyui_plan,
    )
    reviewed_path = tmp_path / 'reviewed.glb'
    reviewed_path.write_bytes(b'abc')
    reviewed_item = review.items[0].model_copy(
        update={'asset_path': reviewed_path.as_posix()}
    )
    focused_review = review.model_copy(update={'items': [reviewed_item]})

    manifest = build_asset_approval_manifest(
        focused_review,
        {reviewed_item.asset_id: 'approved'},
        workspace_root=tmp_path,
    )
    rebuilt_manifest = build_asset_approval_manifest(
        focused_review,
        {reviewed_item.asset_id: 'approved'},
        workspace_root=tmp_path,
    )

    assert manifest.decisions[0].artifact_identity.algorithm == 'sha256'
    assert manifest.decisions[0].artifact_identity.digest == (
        'ba7816bf8f01cfea414140de5dae2223'
        'b00361a396177a9cb410ff61f20015ad'
    )
    assert manifest.model_dump_json() == rebuilt_manifest.model_dump_json()


def test_build_asset_approval_manifest_rejects_missing_reviewed_file(tmp_path: Path):
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    review = prepare_creative_review(
        director_plan.gameplay_spec,
        director_plan.blender_plan,
        director_plan.comfyui_plan,
    )
    missing_item = review.items[0].model_copy(
        update={'asset_path': (tmp_path / 'missing.glb').as_posix()}
    )
    focused_review = review.model_copy(update={'items': [missing_item]})

    with pytest.raises(FileNotFoundError):
        build_asset_approval_manifest(
            focused_review,
            {missing_item.asset_id: 'approved'},
            workspace_root=tmp_path,
        )

    unreadable_path = tmp_path / 'directory.glb'
    unreadable_path.mkdir()
    unreadable_item = missing_item.model_copy(
        update={'asset_path': unreadable_path.as_posix()}
    )
    unreadable_review = review.model_copy(update={'items': [unreadable_item]})
    with pytest.raises(OSError):
        build_asset_approval_manifest(
            unreadable_review,
            {unreadable_item.asset_id: 'approved'},
            workspace_root=tmp_path,
        )


def test_build_asset_approval_manifest_rejects_absolute_path_outside_workspace(
    tmp_path: Path,
):
    workspace_root = tmp_path / 'workspace'
    workspace_root.mkdir()
    outside_path = tmp_path / 'outside.glb'
    outside_path.write_bytes(b'outside-secret')
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    outside_item = director_plan.creative_review.items[0].model_copy(
        update={'asset_path': outside_path.as_posix()}
    )
    focused_review = director_plan.creative_review.model_copy(
        update={'items': [outside_item]}
    )

    with pytest.raises(WorkspacePathError):
        build_asset_approval_manifest(
            focused_review,
            {outside_item.asset_id: 'approved'},
            workspace_root=workspace_root,
        )


def test_build_asset_approval_manifest_rejects_traversal_and_symlink_escape(
    tmp_path: Path,
):
    workspace_root = tmp_path / 'workspace'
    workspace_root.mkdir()
    outside_path = tmp_path / 'outside.glb'
    outside_path.write_bytes(b'outside-secret')
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    source_item = director_plan.creative_review.items[0]

    traversal_item = source_item.model_copy(update={'asset_path': '../outside.glb'})
    traversal_review = director_plan.creative_review.model_copy(
        update={'items': [traversal_item]}
    )
    with pytest.raises(WorkspacePathError):
        build_asset_approval_manifest(
            traversal_review,
            {traversal_item.asset_id: 'approved'},
            workspace_root=workspace_root,
        )

    linked_path = workspace_root / 'linked.glb'
    linked_path.symlink_to(outside_path)
    linked_item = source_item.model_copy(update={'asset_path': 'linked.glb'})
    linked_review = director_plan.creative_review.model_copy(
        update={'items': [linked_item]}
    )
    with pytest.raises(WorkspacePathError):
        build_asset_approval_manifest(
            linked_review,
            {linked_item.asset_id: 'approved'},
            workspace_root=workspace_root,
        )


def test_build_asset_approval_manifest_uses_godot_glb_for_public_blender_item(
    tmp_path: Path,
):
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
            engine_version='Godot 4',
        )
    )
    blender_item = next(
        item for item in director_plan.creative_review.items if item.source == 'blender'
    )
    planned_path = Path(blender_item.asset_path)
    assert planned_path.suffix == '.fbx'
    glb_relative_path = planned_path.with_suffix('.glb')
    glb_path = tmp_path / glb_relative_path
    glb_path.parent.mkdir(parents=True, exist_ok=True)
    glb_path.write_bytes(b'abc')
    focused_review = director_plan.creative_review.model_copy(
        update={'items': [blender_item]}
    )

    manifest = build_asset_approval_manifest(
        focused_review,
        {blender_item.asset_id: 'approved'},
        target='godot',
        workspace_root=tmp_path,
    )

    decision = manifest.decisions[0]
    assert blender_item.asset_path == planned_path.as_posix()
    assert decision.asset_path == glb_relative_path.as_posix()
    assert decision.artifact_identity is not None
    assert decision.artifact_identity.digest == (
        'ba7816bf8f01cfea414140de5dae2223'
        'b00361a396177a9cb410ff61f20015ad'
    )


@pytest.mark.parametrize('target', [None, 'unreal'])
def test_build_asset_approval_manifest_preserves_unreal_fbx_bytes(
    target: str | None,
    tmp_path: Path,
):
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    blender_item = next(
        item for item in director_plan.creative_review.items if item.source == 'blender'
    )
    planned_path = Path(blender_item.asset_path)
    assert planned_path.suffix == '.fbx'
    fbx_path = tmp_path / planned_path
    fbx_path.parent.mkdir(parents=True, exist_ok=True)
    fbx_path.write_bytes(b'abc')
    fbx_path.with_suffix('.glb').write_bytes(b'not-the-reviewed-fbx')
    focused_review = director_plan.creative_review.model_copy(
        update={'items': [blender_item]}
    )
    target_arg = {} if target is None else {'target': target}

    manifest = build_asset_approval_manifest(
        focused_review,
        {blender_item.asset_id: 'approved'},
        workspace_root=tmp_path,
        **target_arg,
    )

    decision = manifest.decisions[0]
    assert decision.asset_path == blender_item.asset_path
    assert decision.artifact_identity is not None
    assert decision.artifact_identity.digest == (
        'ba7816bf8f01cfea414140de5dae2223'
        'b00361a396177a9cb410ff61f20015ad'
    )


def test_build_asset_approval_manifest_preserves_other_concrete_paths(tmp_path: Path):
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    comfyui_item = next(
        item for item in director_plan.creative_review.items if item.source == 'comfyui'
    )
    blender_item = next(
        item for item in director_plan.creative_review.items if item.source == 'blender'
    ).model_copy(update={'asset_path': 'generated/assets/already-concrete.glb'})
    for item in (comfyui_item, blender_item):
        artifact_path = tmp_path / item.asset_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(f'bytes-{item.asset_id}'.encode())
    focused_review = director_plan.creative_review.model_copy(
        update={'items': [comfyui_item, blender_item]}
    )

    manifest = build_asset_approval_manifest(
        focused_review,
        target='godot',
        workspace_root=tmp_path,
    )

    assert [decision.asset_path for decision in manifest.decisions] == [
        comfyui_item.asset_path,
        blender_item.asset_path,
    ]


def test_build_asset_approval_manifest_rejects_invalid_concrete_godot_glb(
    tmp_path: Path,
):
    workspace_root = tmp_path / 'workspace'
    workspace_root.mkdir()
    outside_glb = tmp_path / 'outside.glb'
    outside_glb.write_bytes(b'outside-secret')
    director_plan = run_director_workflow(
        PromptRequest(
            prompt='a stealth courier escapes a haunted train station',
            target_minutes=10,
        )
    )
    blender_item = next(
        item for item in director_plan.creative_review.items if item.source == 'blender'
    )

    missing_review = director_plan.creative_review.model_copy(
        update={'items': [blender_item]}
    )
    with pytest.raises(FileNotFoundError):
        build_asset_approval_manifest(
            missing_review,
            target='godot',
            workspace_root=workspace_root,
        )

    outside_item = blender_item.model_copy(
        update={'asset_path': (tmp_path / 'outside.fbx').as_posix()}
    )
    outside_review = director_plan.creative_review.model_copy(
        update={'items': [outside_item]}
    )
    with pytest.raises(WorkspacePathError):
        build_asset_approval_manifest(
            outside_review,
            target='godot',
            workspace_root=workspace_root,
        )

    traversal_item = blender_item.model_copy(update={'asset_path': '../outside.fbx'})
    traversal_review = director_plan.creative_review.model_copy(
        update={'items': [traversal_item]}
    )
    with pytest.raises(WorkspacePathError):
        build_asset_approval_manifest(
            traversal_review,
            target='godot',
            workspace_root=workspace_root,
        )

    linked_glb = workspace_root / 'linked.glb'
    linked_glb.symlink_to(outside_glb)
    linked_item = blender_item.model_copy(update={'asset_path': 'linked.fbx'})
    linked_review = director_plan.creative_review.model_copy(
        update={'items': [linked_item]}
    )
    with pytest.raises(WorkspacePathError):
        build_asset_approval_manifest(
            linked_review,
            target='godot',
            workspace_root=workspace_root,
        )
