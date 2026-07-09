"""Copy generated Blender assets into a Godot project.

M2 wires the Blender -> Godot leg: glb files produced under generated/assets are
copied into a generated Godot project's assets/generated/ folder so that a
subsequent `godot --headless --import` imports them and runtime
`load("res://assets/generated/<name>.glb")` calls resolve.

Only .glb is copied (Godot 4 imports it natively). .fbx is skipped and reported
because Godot needs an external fbx2gltf converter that M2 does not manage.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from fantasy_agent.godot_mcp import DEFAULT_WORKSPACE_ROOT, GodotMCPSafetyError
from fantasy_agent.path_safety import WorkspacePathError, resolve_workspace_path


@dataclass
class AssetCopyResult:
    """Outcome of copying assets into a Godot project."""

    copied: list[str] = field(default_factory=list)  # res:// relative names
    skipped: list[str] = field(default_factory=list)  # paths skipped (e.g. .fbx)
    missing: list[str] = field(default_factory=list)  # listed but not found


def _resolve_copy_path(path: str, *, workspace_root: Path | str) -> Path:
    try:
        return resolve_workspace_path(path, workspace_root=workspace_root)
    except WorkspacePathError as exc:
        raise GodotMCPSafetyError(str(exc)) from exc


def copy_assets_into_godot_project(
    exported_assets: list[str],
    project_dir: str,
    *,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetCopyResult:
    """Copy .glb assets into <project_dir>/assets/generated/.

    Args:
        exported_assets: Workspace-relative paths to exported assets
            (e.g. "generated/assets/foo.glb").
        project_dir: Workspace-relative Godot project dir under generated/godot.
        workspace_root: Sandbox root.

    Returns:
        AssetCopyResult with copied res:// names, skipped, and missing entries.
    """

    root = Path(workspace_root).resolve()
    dest_dir = _resolve_copy_path(
        (Path(project_dir.replace("\\", "/")) / "assets" / "generated").as_posix(),
        workspace_root=root,
    )
    result = AssetCopyResult()

    for rel in exported_assets:
        src = _resolve_copy_path(rel, workspace_root=root)
        if src.suffix.lower() != ".glb":
            result.skipped.append(rel)
            continue
        if not src.exists():
            result.missing.append(rel)
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir / src.name)
        result.copied.append(f"assets/generated/{src.name}")

    return result


_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def copy_references_into_godot_project(
    images: list[str],
    project_dir: str,
    *,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetCopyResult:
    """Copy ComfyUI reference images into <project_dir>/references/comfyui/.

    These are art-direction references, not engine textures: they are archived
    for review (per AGENTS.md, generated images must pass Creative Review before
    becoming engine textures), never auto-applied to meshes.

    Args:
        images: Workspace-relative paths to reference images
            (e.g. "generated/comfyui/foo/concept.png").
        project_dir: Workspace-relative Godot project dir under generated/godot.
        workspace_root: Sandbox root.

    Returns:
        AssetCopyResult with copied res:// names, skipped, and missing entries.
    """

    root = Path(workspace_root).resolve()
    dest_dir = _resolve_copy_path(
        (Path(project_dir.replace("\\", "/")) / "references" / "comfyui").as_posix(),
        workspace_root=root,
    )
    result = AssetCopyResult()

    for rel in images:
        src = _resolve_copy_path(rel, workspace_root=root)
        if src.suffix.lower() not in _IMAGE_SUFFIXES:
            result.skipped.append(rel)
            continue
        if not src.exists():
            result.missing.append(rel)
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir / src.name)
        result.copied.append(f"references/comfyui/{src.name}")

    return result
