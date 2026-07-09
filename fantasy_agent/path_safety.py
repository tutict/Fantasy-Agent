"""Shared workspace path safety helpers.

The execution and asset-ingest modules accept workspace-relative paths from
plans, manifests, and UI requests. Keep the path rules in one small module so
callers get the same traversal checks and error messages.
"""

from __future__ import annotations

from pathlib import Path


class WorkspacePathError(ValueError):
    """Raised when a requested path escapes the configured workspace."""


def workspace_root_path(workspace_root: Path | str) -> Path:
    return Path(workspace_root).resolve()


def assert_under(path: Path, root: Path | str) -> None:
    resolved_root = workspace_root_path(root)
    try:
        path.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspacePathError(f"Path escapes workspace: {path}") from exc


def resolve_workspace_path(
    path: str,
    *,
    workspace_root: Path | str,
    required_prefix: str | None = None,
    allow_absolute: bool = False,
) -> Path:
    """Resolve a workspace path after optional relative-prefix validation."""

    if not allow_absolute and Path(path).is_absolute():
        raise WorkspacePathError(f"Absolute paths are not allowed: {path}")
    normalized = Path(path.replace("\\", "/"))
    if ".." in normalized.parts:
        raise WorkspacePathError(f"Parent traversal is not allowed: {path}")
    if required_prefix is not None:
        prefix = Path(required_prefix)
        if normalized.parts[: len(prefix.parts)] != prefix.parts:
            raise WorkspacePathError(f"Path must stay under {required_prefix}: {path}")
    root = workspace_root_path(workspace_root)
    resolved = (root / normalized).resolve()
    assert_under(resolved, root)
    return resolved


def display_workspace_path(path: Path, *, workspace_root: Path | str) -> str:
    return path.resolve().relative_to(workspace_root_path(workspace_root)).as_posix()
