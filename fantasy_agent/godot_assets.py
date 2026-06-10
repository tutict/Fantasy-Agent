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


@dataclass
class AssetCopyResult:
    """Outcome of copying assets into a Godot project."""

    copied: list[str] = field(default_factory=list)  # res:// relative names
    skipped: list[str] = field(default_factory=list)  # paths skipped (e.g. .fbx)
    missing: list[str] = field(default_factory=list)  # listed but not found


def _assert_under(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise GodotMCPSafetyError(f"Path escapes workspace: {path}") from exc


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
    dest_dir = root / project_dir / "assets" / "generated"
    _assert_under(dest_dir, root)
    result = AssetCopyResult()

    for rel in exported_assets:
        src = (root / rel).resolve()
        _assert_under(src, root)
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
