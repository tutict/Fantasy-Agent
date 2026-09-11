"""Direct tests for the workspace path rules.

``path_safety.resolve_workspace_path`` is the single guard in front of every
engine bridge, yet its rejection branches had no direct coverage — the
absolute-path check in particular was never exercised by any test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fantasy_agent.path_safety import (
    WorkspacePathError,
    display_workspace_path,
    resolve_workspace_path,
)


def test_resolves_relative_paths_under_the_workspace(tmp_path: Path):
    resolved = resolve_workspace_path("generated/godot/project.godot", workspace_root=tmp_path)

    assert resolved == (tmp_path / "generated/godot/project.godot").resolve()


def test_rejects_absolute_paths(tmp_path: Path):
    """The absolute-path branch is the only thing standing between plan data
    and an arbitrary filesystem location, so it gets its own test."""

    with pytest.raises(WorkspacePathError, match="Absolute paths are not allowed"):
        resolve_workspace_path("/etc/passwd", workspace_root=tmp_path)


def test_rejects_drive_less_absolute_paths(tmp_path: Path):
    """Windows quirk: ``Path("/etc/passwd").is_absolute()`` is False there.

    Without the root check this fell through to the containment guard, so the
    same input produced a different error on each platform. Both now report it
    as an absolute path.
    """
    from fantasy_agent.path_safety import is_absolute_path

    assert is_absolute_path("/etc/passwd") is True
    assert is_absolute_path(r"\etc\passwd") is True
    assert is_absolute_path("generated/godot/project.godot") is False

    with pytest.raises(WorkspacePathError, match="Absolute paths are not allowed"):
        resolve_workspace_path("/etc/passwd", workspace_root=tmp_path)


def test_rejects_absolute_paths_that_point_inside_the_workspace(tmp_path: Path):
    inside = (tmp_path / "generated" / "inside.txt").as_posix()

    with pytest.raises(WorkspacePathError, match="Absolute paths are not allowed"):
        resolve_workspace_path(inside, workspace_root=tmp_path)


def test_rejects_parent_traversal(tmp_path: Path):
    with pytest.raises(WorkspacePathError, match="Parent traversal is not allowed"):
        resolve_workspace_path("generated/../../secrets.txt", workspace_root=tmp_path)


def test_rejects_paths_outside_the_required_prefix(tmp_path: Path):
    with pytest.raises(WorkspacePathError, match="Path must stay under generated/godot"):
        resolve_workspace_path(
            "generated/unreal/Game.uproject",
            workspace_root=tmp_path,
            required_prefix="generated/godot",
        )


def test_normalizes_windows_separators(tmp_path: Path):
    resolved = resolve_workspace_path(
        r"generated\godot\project.godot", workspace_root=tmp_path
    )

    assert resolved == (tmp_path / "generated/godot/project.godot").resolve()


def test_allow_absolute_opt_in_still_enforces_containment(tmp_path: Path):
    inside = tmp_path / "generated" / "inside.txt"

    allowed = resolve_workspace_path(
        inside.as_posix(), workspace_root=tmp_path, allow_absolute=True
    )
    assert allowed == inside.resolve()

    with pytest.raises(WorkspacePathError, match="Path escapes workspace"):
        resolve_workspace_path(
            (tmp_path.parent / "outside.txt").as_posix(),
            workspace_root=tmp_path,
            allow_absolute=True,
        )


def test_display_path_is_relative_to_the_workspace(tmp_path: Path):
    resolved = resolve_workspace_path("generated/a/b.txt", workspace_root=tmp_path)

    assert display_workspace_path(resolved, workspace_root=tmp_path) == "generated/a/b.txt"
