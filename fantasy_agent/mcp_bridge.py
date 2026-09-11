"""Shared plumbing for the MCP engine bridges.

Blender, ComfyUI, Godot and Unreal each grew their own copy of workspace-path
resolution, text writing and path display. Keeping four copies in sync is
exactly how they drifted: three of them only check containment *after*
``Path.resolve()``, while :func:`fantasy_agent.path_safety.resolve_workspace_path`
also rejects absolute paths and ``..`` segments up front with messages that say
what actually went wrong.

Subclasses declare which error type their callers expect via ``safety_error``
so the public exception contract stays unchanged.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from fantasy_agent.path_safety import (
    WorkspacePathError,
    display_workspace_path,
    resolve_workspace_path,
)
from fantasy_agent.process_runner import run_streaming

DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


class BaseMCPBridge:
    """Workspace-rooted helpers shared by every engine bridge.

    Owns three things that were previously duplicated verbatim: the resolved
    workspace root plus runner, safe path resolution, and the small file and
    display helpers.
    """

    #: Raised when a path escapes the workspace. Subclasses narrow this to
    #: their own ``*MCPSafetyError`` so existing ``except`` blocks keep working.
    safety_error: ClassVar[type[ValueError]] = WorkspacePathError

    def __init__(
        self,
        workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.runner = runner or run_streaming

    def _resolve_workspace_path(
        self,
        path: str,
        *,
        required_prefix: str | None = None,
        allow_absolute: bool = False,
    ) -> Path:
        try:
            return resolve_workspace_path(
                path,
                workspace_root=self.workspace_root,
                required_prefix=required_prefix,
                allow_absolute=allow_absolute,
            )
        except WorkspacePathError as exc:
            raise self.safety_error(str(exc)) from exc

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        return display_workspace_path(path, workspace_root=self.workspace_root)
