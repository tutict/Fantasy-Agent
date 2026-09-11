"""Tests for the shared MCP bridge plumbing.

Four engine bridges used to carry their own copy of workspace path resolution,
and the copies drifted: three of them accepted absolute paths as long as the
result landed inside the workspace, while ``path_safety.resolve_workspace_path``
rejects them outright. These tests pin the unified behaviour so the drift
cannot come back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fantasy_agent.blender_mcp import BlenderMCPBridge, BlenderMCPSafetyError
from fantasy_agent.comfyui_mcp import ComfyUIMCPBridge, ComfyUIMCPSafetyError
from fantasy_agent.godot_mcp import GodotMCPBridge, GodotMCPSafetyError
from fantasy_agent.mcp_bridge import BaseMCPBridge
from fantasy_agent.unreal_mcp import UnrealMCPBridge, UnrealMCPSafetyError

BRIDGES = [
    (BlenderMCPBridge, BlenderMCPSafetyError, "generated/blender/script.py"),
    (ComfyUIMCPBridge, ComfyUIMCPSafetyError, "generated/comfyui/workflow.json"),
    (GodotMCPBridge, GodotMCPSafetyError, "generated/godot/project.godot"),
    (UnrealMCPBridge, UnrealMCPSafetyError, "generated/unreal/Game.uproject"),
]


def _ids() -> list[str]:
    return [bridge.__name__ for bridge, _, _ in BRIDGES]


@pytest.mark.parametrize(("bridge_cls", "error_cls", "good_path"), BRIDGES, ids=_ids())
def test_bridges_share_one_resolver(bridge_cls, error_cls, good_path, tmp_path: Path):
    bridge = bridge_cls(tmp_path)

    assert isinstance(bridge, BaseMCPBridge)
    assert bridge.safety_error is error_cls
    assert bridge._resolve_workspace_path(good_path) == tmp_path / good_path


@pytest.mark.parametrize(("bridge_cls", "error_cls", "_"), BRIDGES, ids=_ids())
def test_bridges_reject_absolute_paths(bridge_cls, error_cls, _, tmp_path: Path):
    """Absolute paths are refused even when they point inside the workspace.

    Passing a pre-resolved path back into the resolver is what the old ComfyUI
    code did; it only worked because the duplicated resolver was lenient.
    """
    bridge = bridge_cls(tmp_path)
    inside = (tmp_path / "generated" / "inside.txt").as_posix()

    with pytest.raises(error_cls, match="Absolute paths are not allowed"):
        bridge._resolve_workspace_path(inside)
    # Drive-less form: on Windows this is not "absolute" per pathlib, but it
    # still discards the workspace prefix when joined, so it must be refused.
    with pytest.raises(error_cls, match="Absolute paths are not allowed"):
        bridge._resolve_workspace_path("/etc/passwd")


@pytest.mark.parametrize(("bridge_cls", "error_cls", "_"), BRIDGES, ids=_ids())
def test_bridges_reject_parent_traversal(bridge_cls, error_cls, _, tmp_path: Path):
    bridge = bridge_cls(tmp_path)

    with pytest.raises(error_cls, match="Parent traversal is not allowed"):
        bridge._resolve_workspace_path("generated/../../secrets.txt")


@pytest.mark.parametrize(("bridge_cls", "error_cls", "_"), BRIDGES, ids=_ids())
def test_bridges_reject_paths_outside_required_prefix(bridge_cls, error_cls, _, tmp_path: Path):
    bridge = bridge_cls(tmp_path)

    with pytest.raises(error_cls, match="Path must stay under generated/prefix"):
        bridge._resolve_workspace_path(
            "generated/elsewhere/file.txt", required_prefix="generated/prefix"
        )


@pytest.mark.parametrize(("bridge_cls", "error_cls", "_"), BRIDGES, ids=_ids())
def test_bridges_display_paths_relative_to_workspace(
    bridge_cls, error_cls, _, tmp_path: Path
):
    bridge = bridge_cls(tmp_path)
    resolved = bridge._resolve_workspace_path("generated/thing.txt")

    assert bridge._display_path(resolved) == "generated/thing.txt"
