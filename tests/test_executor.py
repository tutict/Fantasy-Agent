"""Tests for the Godot execution orchestrator and spec-driven project template.

The orchestrator is exercised with a fake subprocess runner so no real Godot is
required. A separate set of tests asserts the generated main.gd reflects the
GameplaySpec (route segments per level beat, win/fail intent) rather than the
old fixed greybox.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.executor import execute_godot_demo, format_execution_report
from fantasy_agent.generation import design_from_prompt_deterministic
from fantasy_agent.godot_mcp import GodotMCPBridge, _main_gd
from fantasy_agent.workflows import prepare_godot_project, run_director_workflow


def _plan(prompt: str = "rooftop parkour chase across neon towers"):
    return run_director_workflow(
        PromptRequest(prompt=prompt, target_minutes=10, engine_version="Godot 4")
    )


def _ok_runner(*args, **kwargs):
    return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="import ok", stderr="")


# ── confirmation gate ────────────────────────────────────────────────────────


def test_confirmation_gate_writes_nothing(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    result = execute_godot_demo(
        _plan(), session_id="s1", confirmed=False, bridge=bridge
    )

    assert result.status == "confirmation_required"
    assert result.planned_side_effects  # lists what WOULD happen
    assert result.stages == []
    # Nothing was written to the sandbox.
    assert not (tmp_path / "generated").exists()


def test_confirmation_gate_report_mentions_side_effects(tmp_path: Path):
    result = execute_godot_demo(_plan(), session_id="s1", confirmed=False)
    report = format_execution_report(result)
    assert "requires confirmation" in report
    assert "--yes" in report


# ── orchestration order + success ────────────────────────────────────────────


def test_executes_create_validate_import_in_order(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    result = execute_godot_demo(
        _plan(), session_id="s2", confirmed=True, godot_exe="godot", bridge=bridge
    )

    assert result.ok
    assert [s.name for s in result.stages] == ["create", "validate", "import"]
    assert all(s.status == "done" for s in result.stages)
    # Project actually written under the godot sandbox prefix.
    assert (tmp_path / result.project_dir / "project.godot").exists()
    assert result.project_dir.startswith("generated/godot/sessions/s2/")


def test_no_import_stops_after_validate(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    result = execute_godot_demo(
        _plan(), session_id="s3", confirmed=True, run_import=False, bridge=bridge
    )

    assert result.ok
    names = {s.name: s.status for s in result.stages}
    assert names["create"] == "done"
    assert names["validate"] == "done"
    assert names["import"] == "blocked"


def test_import_failure_is_reported(tmp_path: Path):
    def failing_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=1, stdout="", stderr="boom")

    bridge = GodotMCPBridge(tmp_path, runner=failing_runner)
    result = execute_godot_demo(
        _plan(), session_id="s4", confirmed=True, godot_exe="godot", bridge=bridge
    )

    assert result.status == "failed"
    assert result.stages[-1].name == "import"
    assert result.stages[-1].status == "failed"


# ── spec-driven template ─────────────────────────────────────────────────────


def test_main_gd_without_spec_keeps_default_route():
    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    plan = prepare_godot_project(spec)
    script = _main_gd(plan)  # no spec
    assert "FA_Ramp_Teach" in script  # original fixed greybox marker


def test_main_gd_with_spec_has_one_floor_per_beat():
    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    plan = prepare_godot_project(spec)
    script = _main_gd(plan, spec)

    floors = re.findall(r"FA_RouteFloor_\d+_", script)
    assert len(floors) == len(spec.level_beats)
    # Win/fail intent is embedded.
    assert "win_state" in script
    assert "failure_state" in script


def test_main_gd_route_differs_by_prompt():
    spec_a = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    spec_b = design_from_prompt_deterministic(
        PromptRequest(prompt="a calm puzzle game about sorting colors")
    )
    script_a = _main_gd(prepare_godot_project(spec_a), spec_a)
    script_b = _main_gd(prepare_godot_project(spec_b), spec_b)
    assert script_a != script_b


# ── M2: Blender asset stage ──────────────────────────────────────────────────


class _FakeBlenderResult:
    def __init__(self, status: str, exported_assets: list[str]):
        self.status = status
        self.exported_assets = exported_assets
        self.log_paths: list[str] = []


class _FakeBlenderBridge:
    """Stub that mimics generate_asset_batch without launching Blender."""

    def __init__(self, status: str = "executed", exported: list[str] | None = None, *, root=None):
        self._status = status
        self._exported = exported or []
        self._root = root

    def generate_asset_batch(self, request):
        # Optionally drop real files so the copy stage has something to move.
        if self._root is not None and self._status == "executed":
            assets_dir = Path(self._root) / "generated" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for rel in self._exported:
                (Path(self._root) / rel).write_bytes(b"glTF-stub")
        return _FakeBlenderResult(self._status, self._exported)


def test_with_assets_stage_order_and_copy(tmp_path: Path):
    exported = ["generated/assets/start_marker.glb", "generated/assets/objective_prop.glb"]
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    blender = _FakeBlenderBridge(status="executed", exported=exported, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m2",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        workspace_root=tmp_path,
        bridge=bridge,
        blender_bridge=blender,
    )

    assert result.ok
    names = [s.name for s in result.stages]
    assert names == ["blender", "create", "copy_assets", "validate", "import"]
    # glb actually copied into the project.
    copied = list((tmp_path / result.project_dir / "assets" / "generated").glob("*.glb"))
    assert len(copied) == 2


def test_blender_failure_degrades_to_greybox(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    blender = _FakeBlenderBridge(status="failed", exported=[])

    result = execute_godot_demo(
        _plan(),
        session_id="m2fail",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        workspace_root=tmp_path,
        bridge=bridge,
        blender_bridge=blender,
    )

    # Chain still completes (greybox), blender stage marked failed, no copy stage.
    assert result.ok
    names = [s.name for s in result.stages]
    assert "blender" in names
    assert next(s for s in result.stages if s.name == "blender").status == "failed"
    assert "copy_assets" not in names
    assert names[-1] == "import"


def test_confirmation_gate_lists_blender_side_effects(tmp_path: Path):
    result = execute_godot_demo(
        _plan(), session_id="m2", confirmed=False, with_assets=True, blender_exe="blender"
    )
    assert result.status == "confirmation_required"
    assert any("Blender" in e for e in result.planned_side_effects)
    assert any("Copy exported glb" in e for e in result.planned_side_effects)


# ── M2: spec-driven glb instancing in the template ───────────────────────────


def test_main_gd_with_spec_emits_glb_load_with_fallback():
    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    script = _main_gd(prepare_godot_project(spec), spec)
    assert "_spawn_marker" in script
    assert "res://assets/generated/" in script
    assert "ResourceLoader.exists" in script
    # Box fallback helper still present.
    assert "func _box(" in script

