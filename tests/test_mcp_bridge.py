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


def test_bridges_keep_their_log_writes_off_the_atomic_helper(tmp_path: Path):
    """The engine log writes must stay on a plain write, forever.

    This is a guard against a well-meant "let's make them all atomic" sweep.
    It is not a style preference: `_pump` holds engine log files open with
    ``path.open("a")`` for the life of the subprocess, and the bridges then
    write *the same two paths* through ``_write_text`` (see ``godot_mcp``'s
    import branch). ``run_streaming`` returns after
    ``pump.join(timeout=PUMP_JOIN_TIMEOUT)`` -- a join allowed to time out -- so
    the handle can still be open when ``_write_text`` runs, and on Windows an
    atomic replace then raises ``PermissionError (13)``. The sweep would turn a
    slow engine log write into a failed tool call.

    Asserted behaviourally rather than by grepping imports, so the guard keeps
    working even if the helper is reached indirectly.
    """

    from fantasy_agent.atomic_write import write_atomic

    target = tmp_path / "import.stderr.log"
    # What _pump holds open for the life of the subprocess.
    held_open = target.open("a", encoding="utf-8")
    try:
        bridge = GodotMCPBridge(tmp_path)
        bridge._write_text(target, "engine output\n")  # must not raise
    finally:
        held_open.close()

    # And the reason, asserted rather than assumed: the collision is real on
    # this platform. If a future Python or filesystem made replace tolerate an
    # open target, the sweep would merely become wasteful rather than broken,
    # and this test would tell us the reason has gone away.
    with target.open("a", encoding="utf-8"):
        try:
            write_atomic(target, "replacement")
        except PermissionError as exc:
            assert "拒绝访问" in str(exc) or "Permission denied" in str(exc)
        else:
            pytest.skip("this platform now allows replacing an open file")

    assert target.read_text(encoding="utf-8") == "engine output\n"


def test_no_bridge_module_reaches_for_the_atomic_helper():
    """Belt to the behavioural test's braces: no bridge imports it at all.

    Read from the source rather than trusted to the import graph, because the
    failure being prevented is someone adding the import in the first place.

    The glob is every module with ``mcp`` in its name, not ``*_mcp.py``: the
    base class all four bridges inherit ``_write_text`` from is
    ``mcp_bridge.py``, which the narrower glob silently skipped -- so a sweep
    landing in the one file every bridge shares was invisible to this scan.
    The behavioural test above covers what a scan cannot (a replace that
    avoids the helper by name), which is why both exist.
    """

    import fantasy_agent

    package = Path(fantasy_agent.__file__).parent
    offenders = [
        module.name
        for module in package.glob("*mcp*.py")
        if "atomic_write" in module.read_text(encoding="utf-8")
    ]

    assert offenders == [], (
        f"engine bridges must keep plain writes: {offenders}"
    )


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
