"""Approval manifest resolver for gated asset ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from fantasy_agent.contracts import AssetApprovalManifest
from fantasy_agent.godot_mcp import DEFAULT_WORKSPACE_ROOT, GodotMCPSafetyError
from fantasy_agent.path_safety import WorkspacePathError, resolve_workspace_path

DEFAULT_APPROVAL_MANIFEST_PATH = "generated/asset-approval-manifest.yaml"


@dataclass
class ApprovalFilterResult:
    approved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    manifest_path: str = DEFAULT_APPROVAL_MANIFEST_PATH
    approved_asset_ids: list[str] = field(default_factory=list)
    revision_asset_ids: list[str] = field(default_factory=list)
    rejected_asset_ids: list[str] = field(default_factory=list)
    pending_asset_ids: list[str] = field(default_factory=list)


def _resolve_manifest_path(
    manifest_path: str,
    *,
    workspace_root: Path | str,
) -> Path:
    try:
        return resolve_workspace_path(manifest_path, workspace_root=workspace_root)
    except WorkspacePathError as exc:
        raise GodotMCPSafetyError(str(exc)) from exc


def load_asset_approval_manifest(
    manifest_path: str = DEFAULT_APPROVAL_MANIFEST_PATH,
    *,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetApprovalManifest:
    path = _resolve_manifest_path(manifest_path, workspace_root=workspace_root)
    if not path.exists():
        raise FileNotFoundError(manifest_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AssetApprovalManifest.model_validate(data)


def _match_keys(path_or_id: str) -> set[str]:
    normalized = path_or_id.replace("\\", "/").casefold()
    path = Path(normalized)
    stem = path.stem.casefold()
    keys = {normalized, stem}
    if normalized.endswith(".fbx"):
        keys.add(f"{normalized[:-4]}.glb")
    if normalized.endswith(".glb"):
        keys.add(f"{normalized[:-4]}.fbx")
    return {key for key in keys if key}


def filter_approved_blender_assets(
    exported_assets: list[str],
    manifest: AssetApprovalManifest,
    *,
    manifest_path: str = DEFAULT_APPROVAL_MANIFEST_PATH,
) -> ApprovalFilterResult:
    allowed: set[str] = set()
    for decision in manifest.decisions:
        if decision.source != "blender" or decision.decision != "approved":
            continue
        allowed.update(_match_keys(decision.asset_id))
        allowed.update(_match_keys(decision.asset_path))

    result = ApprovalFilterResult(
        manifest_path=manifest_path,
        approved_asset_ids=list(manifest.approved_asset_ids),
        revision_asset_ids=list(manifest.revision_asset_ids),
        rejected_asset_ids=list(manifest.rejected_asset_ids),
        pending_asset_ids=list(manifest.pending_asset_ids),
    )
    for rel in exported_assets:
        keys = _match_keys(rel)
        if keys & allowed:
            result.approved.append(rel)
        else:
            result.skipped.append(rel)
    return result
