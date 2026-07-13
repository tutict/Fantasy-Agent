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
from fantasy_agent.contracts import GodotMCPResult
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


def test_with_assets_defaults_to_approval_manifest_and_blocks_copy(tmp_path: Path):
    exported = ["generated/assets/start_marker.glb", "generated/assets/objective_prop.glb"]
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    blender = _FakeBlenderBridge(status="executed", exported=exported, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m2defaultgate",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        workspace_root=tmp_path,
        bridge=bridge,
        blender_bridge=blender,
    )

    assert result.ok
    names = [s.name for s in result.stages]
    assert names == ["blender", "approval_gate", "create", "validate", "import"]
    gate = next(s for s in result.stages if s.name == "approval_gate")
    assert gate.status == "blocked"
    assert gate.metadata["manifest_path"] == "generated/asset-approval-manifest.yaml"
    assert "copy_assets" not in names
    assert not list((tmp_path / result.project_dir / "assets" / "generated").glob("*.glb"))


def test_with_assets_approval_manifest_copies_only_approved(tmp_path: Path):
    import yaml

    exported = [
        "generated/assets/start_marker.glb",
        "generated/assets/objective_prop.glb",
        "generated/assets/rejected_gate.glb",
    ]
    manifest_path = tmp_path / "generated" / "asset-approval-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "source": "studio.approval-manifest",
                "schema_version": "0.1",
                "approval_gate": "blocks_unreal_ingest",
                "decisions": [
                    {
                        "asset_id": "start_marker",
                        "source": "blender",
                        "asset_path": "generated/assets/start_marker.fbx",
                        "gameplay_role": "objective_prop",
                        "decision": "approved",
                        "risks": [],
                    },
                    {
                        "asset_id": "objective_prop",
                        "source": "blender",
                        "asset_path": "generated/assets/objective_prop.fbx",
                        "gameplay_role": "objective_prop",
                        "decision": "needs_revision",
                        "risks": [],
                    },
                    {
                        "asset_id": "rejected_gate",
                        "source": "blender",
                        "asset_path": "generated/assets/rejected_gate.fbx",
                        "gameplay_role": "exit_gate",
                        "decision": "rejected",
                        "risks": [],
                    },
                ],
                "approved_asset_ids": ["start_marker"],
                "revision_asset_ids": ["objective_prop"],
                "rejected_asset_ids": ["rejected_gate"],
                "pending_asset_ids": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    blender = _FakeBlenderBridge(status="executed", exported=exported, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m2approved",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        workspace_root=tmp_path,
        bridge=bridge,
        blender_bridge=blender,
    )

    assert result.ok
    names = [s.name for s in result.stages]
    assert names == ["blender", "approval_gate", "create", "copy_assets", "validate", "import"]
    gate = next(s for s in result.stages if s.name == "approval_gate")
    assert gate.detail == "1 approved, 2 skipped"
    assert gate.metadata["approved_assets"] == ["generated/assets/start_marker.glb"]
    assert gate.metadata["skipped_assets"] == [
        "generated/assets/objective_prop.glb",
        "generated/assets/rejected_gate.glb",
    ]
    assert gate.metadata["revision_asset_ids"] == ["objective_prop"]
    assert gate.metadata["rejected_asset_ids"] == ["rejected_gate"]
    assert gate.metadata["report_path"].endswith("approval-gate-report.yaml")
    report_path = tmp_path / str(gate.metadata["report_path"])
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "approved_count": 1,
        "skipped_count": 2,
        "revision_count": 1,
        "rejected_count": 1,
        "pending_count": 0,
    }
    assert report["approved_assets"] == ["generated/assets/start_marker.glb"]
    assert "Skipped assets remain available" in " ".join(report["qa_notes"])
    copied = sorted(p.name for p in (tmp_path / result.project_dir / "assets" / "generated").glob("*.glb"))
    assert copied == ["start_marker.glb"]


def test_with_assets_missing_approval_manifest_blocks_asset_copy(tmp_path: Path):
    exported = ["generated/assets/start_marker.glb"]
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    blender = _FakeBlenderBridge(status="executed", exported=exported, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m2blocked",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        approval_manifest_path="generated/asset-approval-manifest.yaml",
        workspace_root=tmp_path,
        bridge=bridge,
        blender_bridge=blender,
    )

    assert result.ok
    gate = next(s for s in result.stages if s.name == "approval_gate")
    assert gate.status == "blocked"
    assert gate.metadata["manifest_path"] == "generated/asset-approval-manifest.yaml"
    assert "blocked_reason" in gate.metadata
    assert "copy_assets" not in [s.name for s in result.stages]
    assert not (tmp_path / result.project_dir / "assets" / "generated" / "start_marker.glb").exists()


class _CreateFailedBridge(GodotMCPBridge):
    def create_godot_project_structure(self, request):
        return GodotMCPResult(status="failed", risks=["create boom"])


def test_approval_gate_report_waits_until_project_create_succeeds(tmp_path: Path):
    import yaml

    exported = ["generated/assets/start_marker.glb"]
    manifest_path = tmp_path / "generated" / "asset-approval-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "source": "studio.approval-manifest",
                "schema_version": "0.1",
                "approval_gate": "blocks_unreal_ingest",
                "decisions": [
                    {
                        "asset_id": "start_marker",
                        "source": "blender",
                        "asset_path": "generated/assets/start_marker.fbx",
                        "gameplay_role": "objective_prop",
                        "decision": "approved",
                        "risks": [],
                    }
                ],
                "approved_asset_ids": ["start_marker"],
                "revision_asset_ids": [],
                "rejected_asset_ids": [],
                "pending_asset_ids": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    blender = _FakeBlenderBridge(status="executed", exported=exported, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m2createfail",
        confirmed=True,
        godot_exe="godot",
        with_assets=True,
        workspace_root=tmp_path,
        bridge=_CreateFailedBridge(tmp_path, runner=_ok_runner),
        blender_bridge=blender,
    )

    assert result.status == "failed"
    gate = next(s for s in result.stages if s.name == "approval_gate")
    assert gate.status == "done"
    assert "report_path" not in gate.metadata
    assert not (tmp_path / result.project_dir / "generated" / "approval-gate-report.yaml").exists()


def test_asset_pipeline_runs_comfyui_and_blender_without_godot_project(tmp_path: Path):
    from fantasy_agent.executor import execute_asset_pipeline

    images = ["generated/comfyui/rooftop/concept.png"]
    glb = ["generated/assets/start_marker.glb"]
    comfy = _FakeComfyBridge(status="executed", images=images, root=tmp_path)
    blender = _FakeBlenderBridge(status="executed", exported=glb, root=tmp_path)

    result = execute_asset_pipeline(
        _plan(),
        session_id="assets1",
        confirmed=True,
        with_visuals=True,
        with_assets=True,
        workspace_root=tmp_path,
        comfyui_bridge=comfy,
        blender_bridge=blender,
    )

    assert result.ok
    assert [s.name for s in result.stages] == ["comfyui", "blender"]
    assert not (tmp_path / "generated" / "godot").exists()


def test_asset_pipeline_confirmation_gate_lists_workers(tmp_path: Path):
    from fantasy_agent.executor import execute_asset_pipeline

    result = execute_asset_pipeline(
        _plan(), session_id="assets2", confirmed=False, with_visuals=True, with_assets=True
    )

    assert result.status == "confirmation_required"
    assert any("ComfyUI" in effect for effect in result.planned_side_effects)
    assert any("Blender" in effect for effect in result.planned_side_effects)


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
    assert any("Filter Blender exports through approval manifest" in e for e in result.planned_side_effects)
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


# ── M3: ComfyUI visual reference stage ───────────────────────────────────────


class _FakeComfyResult:
    def __init__(self, status: str, generated_images: list[str]):
        self.status = status
        self.generated_images = generated_images
        self.log_paths: list[str] = []


class _FakeComfyBridge:
    """Stub mimicking run_visual_reference_workflow without hitting ComfyUI."""

    def __init__(self, status: str = "executed", images: list[str] | None = None, *, root=None):
        self._status = status
        self._images = images or []
        self._root = root

    def run_visual_reference_workflow(self, request):
        if self._root is not None and self._status == "executed":
            for rel in self._images:
                p = Path(self._root) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x89PNG-stub")
        return _FakeComfyResult(self._status, self._images)


def test_with_visuals_stage_order_and_copy(tmp_path: Path):
    images = ["generated/comfyui/rooftop/concept.png", "generated/comfyui/rooftop/ui.png"]
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    comfy = _FakeComfyBridge(status="executed", images=images, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m3",
        confirmed=True,
        godot_exe="godot",
        with_visuals=True,
        workspace_root=tmp_path,
        bridge=bridge,
        comfyui_bridge=comfy,
    )

    assert result.ok
    names = [s.name for s in result.stages]
    assert names == ["comfyui", "create", "copy_refs", "validate", "import"]
    copied = list((tmp_path / result.project_dir / "references" / "comfyui").glob("*.png"))
    assert len(copied) == 2


def test_comfyui_failure_does_not_break_chain(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    comfy = _FakeComfyBridge(status="failed", images=[])

    result = execute_godot_demo(
        _plan(),
        session_id="m3fail",
        confirmed=True,
        godot_exe="godot",
        with_visuals=True,
        workspace_root=tmp_path,
        bridge=bridge,
        comfyui_bridge=comfy,
    )

    assert result.ok  # chain still completes without references
    names = [s.name for s in result.stages]
    assert next(s for s in result.stages if s.name == "comfyui").status == "failed"
    assert "copy_refs" not in names
    assert names[-1] == "import"


def test_confirmation_gate_lists_comfyui_side_effects(tmp_path: Path):
    result = execute_godot_demo(_plan(), session_id="m3", confirmed=False, with_visuals=True)
    assert result.status == "confirmation_required"
    assert any("ComfyUI" in e for e in result.planned_side_effects)
    assert any("reference images" in e for e in result.planned_side_effects)


def test_visuals_and_assets_compose(tmp_path: Path):
    import yaml

    images = ["generated/comfyui/rooftop/concept.png"]
    glb = ["generated/assets/start_marker.glb"]
    manifest_path = tmp_path / "generated" / "asset-approval-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "source": "studio.approval-manifest",
                "schema_version": "0.1",
                "approval_gate": "blocks_unreal_ingest",
                "decisions": [
                    {
                        "asset_id": "start_marker",
                        "source": "blender",
                        "asset_path": "generated/assets/start_marker.fbx",
                        "gameplay_role": "objective_prop",
                        "decision": "approved",
                        "risks": [],
                    }
                ],
                "approved_asset_ids": ["start_marker"],
                "revision_asset_ids": [],
                "rejected_asset_ids": [],
                "pending_asset_ids": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    comfy = _FakeComfyBridge(status="executed", images=images, root=tmp_path)
    blender = _FakeBlenderBridge(status="executed", exported=glb, root=tmp_path)

    result = execute_godot_demo(
        _plan(),
        session_id="m3both",
        confirmed=True,
        godot_exe="godot",
        with_visuals=True,
        with_assets=True,
        workspace_root=tmp_path,
        bridge=bridge,
        comfyui_bridge=comfy,
        blender_bridge=blender,
    )

    assert result.ok
    names = [s.name for s in result.stages]
    # ComfyUI runs first, then Blender, then approval gate, create and both copies.
    assert names == [
        "comfyui",
        "blender",
        "approval_gate",
        "create",
        "copy_assets",
        "copy_refs",
        "validate",
        "import",
    ]


# ── M4: Unreal executor (project generation + DataValidation) ────────────────


def _unreal_plan(prompt: str = "rooftop parkour chase"):
    return run_director_workflow(
        PromptRequest(prompt=prompt, target_minutes=10, engine_version="UE5")
    )


def _unreal_bridge(tmp_path: Path, returncode: int = 0):
    from fantasy_agent.unreal_mcp import UnrealMCPBridge

    def runner(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=returncode,
            stdout="data ok" if returncode == 0 else "",
            stderr="" if returncode == 0 else "validation error",
        )

    return UnrealMCPBridge(tmp_path, runner=runner)


def test_unreal_confirmation_gate_writes_nothing(tmp_path: Path):
    from fantasy_agent.executor import execute_unreal_demo

    result = execute_unreal_demo(
        _unreal_plan(), session_id="u1", confirmed=False, workspace_root=tmp_path
    )
    assert result.status == "confirmation_required"
    assert result.stages == []
    assert any("DataValidation" in e for e in result.planned_side_effects)
    assert not (tmp_path / "generated" / "unreal").exists()


def test_unreal_executes_stage_order(tmp_path: Path):
    from fantasy_agent.executor import execute_unreal_demo

    result = execute_unreal_demo(
        _unreal_plan(),
        session_id="u2",
        confirmed=True,
        unreal_cmd="UnrealEditor-Cmd",
        workspace_root=tmp_path,
        bridge=_unreal_bridge(tmp_path),
    )

    assert result.ok
    assert [s.name for s in result.stages] == [
        "create",
        "spec_compile",
        "spec_qa",
        "prepare_ingest",
        "prepare_level",
        "validate",
    ]
    assert list((tmp_path / result.project_dir).glob("*.uproject"))
    assert result.project_dir.startswith("generated/unreal/sessions/u2/")


def test_unreal_execution_writes_compiled_specs_and_executable_qa(tmp_path: Path):
    from fantasy_agent.executor import execute_unreal_demo

    result = execute_unreal_demo(
        _unreal_plan(),
        session_id="u-specs",
        confirmed=True,
        workspace_root=tmp_path,
        run_validation=False,
        bridge=_unreal_bridge(tmp_path),
    )

    assert result.ok
    project = tmp_path / result.project_dir
    assert (project / "Content/FantasyAgent/Data/DT_Enemies.json").exists()
    assert (project / "Content/FantasyAgent/Data/DT_Encounters.json").exists()
    assert (project / "Content/FantasyAgent/Data/DA_ProductionSpec.json").exists()
    assert (project / "Content/FantasyAgent/Data/SpecTrace.json").exists()
    assert (project / "Content/FantasyAgent/Data/QA_Executable.json").exists()
    stages = {stage.name: stage for stage in result.stages}
    assert stages["spec_compile"].status == "done"
    assert stages["spec_qa"].status in {"done", "degraded"}
    assert stages["spec_compile"].artifacts
    assert stages["spec_qa"].metadata["status"] in {"passed", "warning"}


def test_unreal_no_validation_stops_after_prepare_level(tmp_path: Path):
    from fantasy_agent.executor import execute_unreal_demo

    result = execute_unreal_demo(
        _unreal_plan(),
        session_id="u3",
        confirmed=True,
        workspace_root=tmp_path,
        run_validation=False,
        bridge=_unreal_bridge(tmp_path),
    )

    assert result.ok
    names = {s.name: s.status for s in result.stages}
    assert names["create"] == "done"
    assert names["prepare_ingest"] == "done"
    assert names["prepare_level"] == "done"
    assert names["validate"] == "blocked"


def test_unreal_validation_failure_keeps_generated_project(tmp_path: Path):
    from fantasy_agent.executor import execute_unreal_demo

    result = execute_unreal_demo(
        _unreal_plan(),
        session_id="u4",
        confirmed=True,
        unreal_cmd="UnrealEditor-Cmd",
        workspace_root=tmp_path,
        bridge=_unreal_bridge(tmp_path, returncode=1),
    )

    assert result.status == "failed"
    # Project was still generated before validation failed.
    assert list((tmp_path / result.project_dir).glob("*.uproject"))
    assert result.stages[-1].name == "validate"
    assert result.stages[-1].status == "failed"



# ── M6a: gameplay codegen stage ──────────────────────────────────────────────


def test_with_gameplay_generates_scripts_and_imports(tmp_path: Path):
    from unittest import mock

    fake = {
        "scripts/player_controller.gd": "extends CharacterBody3D\nfunc _ready():\n\tpass\n",
        "scripts/game_manager.gd": "extends Node\nfunc reach_exit():\n\tpass\n",
    }
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    with mock.patch("fantasy_agent.llm.complete_json", return_value=fake):
        result = execute_godot_demo(
            _plan(), session_id="g1", confirmed=True, godot_exe="godot",
            with_gameplay=True, workspace_root=tmp_path, bridge=bridge,
        )

    assert result.ok
    names = [s.name for s in result.stages]
    assert names[0] == "gameplay"
    assert names == ["gameplay", "create", "enemy_metrics", "validate", "import"]
    enemy_metrics = next(s for s in result.stages if s.name == "enemy_metrics")
    assert "pressure_score=" in enemy_metrics.detail
    assert enemy_metrics.artifacts
    assert enemy_metrics.artifacts[0].endswith("/data/enemy-pressure-report.json")
    # Gameplay scripts, including M6b enemies, were written into the project.
    assert (tmp_path / result.project_dir / "scripts" / "game_manager.gd").exists()
    assert (tmp_path / result.project_dir / "scripts" / "enemy_controller.gd").exists()
    report = (tmp_path / result.project_dir / "data" / "enemy-pressure-report.json").read_text(
        encoding="utf-8"
    )
    assert '"enemy_count"' in report
    assert '"pressure_score"' in report
    main = (tmp_path / result.project_dir / "scripts" / "main.gd").read_text(encoding="utf-8")
    assert "_spawn_enemies(gm)" in main
    assert "FA_Enemy_" in main
    assert '"enemy_tuning"' in main


def test_with_gameplay_degrades_to_deterministic_when_llm_unavailable(tmp_path: Path):
    from unittest import mock

    import fantasy_agent.llm as llm

    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    legacy_plan = _plan().model_copy(update={"production_spec_bundle": None})
    with mock.patch("fantasy_agent.llm.complete_json", side_effect=llm.LLMError("no key")):
        result = execute_godot_demo(
            legacy_plan, session_id="g2", confirmed=True, godot_exe="godot",
            with_gameplay=True, workspace_root=tmp_path, bridge=bridge,
        )

    assert result.ok
    gameplay = next(s for s in result.stages if s.name == "gameplay")
    assert gameplay.status == "degraded"
    # Deterministic player controller (sprint/wall-run/slide) was written.
    player = (tmp_path / result.project_dir / "scripts" / "player_controller.gd").read_text(
        encoding="utf-8"
    )
    assert "[SPRINT]" in player
    enemy = (tmp_path / result.project_dir / "scripts" / "enemy_controller.gd").read_text(encoding="utf-8")
    assert "extends Area3D" in enemy
    assert "fail_from_enemy" in enemy


def test_with_gameplay_listed_in_confirmation_gate(tmp_path: Path):
    result = execute_godot_demo(
        _plan(), session_id="g3", confirmed=False, with_gameplay=True
    )
    assert result.status == "confirmation_required"
    assert any("GDScript" in e for e in result.planned_side_effects)
    assert any("enemy pressure tuning" in e for e in result.planned_side_effects)


def test_with_gameplay_accepts_enemy_pressure_tuning(tmp_path: Path):
    from fantasy_agent.contracts import EnemyPressureTuning

    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)
    result = execute_godot_demo(
        _plan(),
        session_id="g4",
        confirmed=True,
        godot_exe="godot",
        with_gameplay=True,
        enemy_tuning=EnemyPressureTuning(
            enemy_count_multiplier=2.0,
            move_speed_multiplier=1.5,
            detection_radius_multiplier=1.25,
            patrol_radius_multiplier=1.1,
            ranged_interval_multiplier=0.75,
        ),
        workspace_root=tmp_path,
        bridge=bridge,
    )

    assert result.ok
    enemy_metrics = next(s for s in result.stages if s.name == "enemy_metrics")
    assert "pressure_score=" in enemy_metrics.detail
    report = (tmp_path / result.project_dir / "data" / "enemy-pressure-report.json").read_text(
        encoding="utf-8"
    )
    assert '"enemy_count_multiplier": 2.0' in report
    main = (tmp_path / result.project_dir / "scripts" / "main.gd").read_text(encoding="utf-8")
    assert '"move_speed_multiplier": 1.5' in main
    assert "count_multiplier" in main



def test_godot_execution_exports_production_specs(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)

    result = execute_godot_demo(
        _plan(),
        session_id="m7",
        confirmed=True,
        godot_exe="godot",
        workspace_root=tmp_path,
        bridge=bridge,
        run_import=False,
    )

    assert result.ok
    create = next(stage for stage in result.stages if stage.name == "create")
    assert any(path.endswith("data/production-spec-bundle.yaml") for path in create.artifacts)
    assert any(path.endswith("data/config/enemies.yaml") for path in create.artifacts)
    bundle = tmp_path / result.project_dir / "data" / "production-spec-bundle.yaml"
    assert bundle.exists()
    assert "ProductionSpecBundle" not in bundle.read_text(encoding="utf-8")
    assert "combat:" in bundle.read_text(encoding="utf-8")
    main = (tmp_path / result.project_dir / "scripts" / "main.gd").read_text(encoding="utf-8")
    assert '"production_specs"' in main
    assert '"level_objective_gates"' in main
    assert '"config_tables"' in main


def test_invalid_production_spec_blocks_before_godot_create(tmp_path: Path):
    plan = _plan()
    assert plan.production_spec_bundle is not None
    plan = plan.model_copy(
        update={
            "production_spec_bundle": plan.production_spec_bundle.model_copy(
                update={
                    "level": plan.production_spec_bundle.level.model_copy(
                        update={"objective_gates": []}
                    )
                }
            )
        }
    )
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)

    result = execute_godot_demo(
        plan,
        session_id="invalid-spec",
        confirmed=True,
        workspace_root=tmp_path,
        bridge=bridge,
    )

    assert result.status == "failed"
    assert result.stages[0].name == "spec_validation"
    assert result.stages[0].status == "failed"
    assert not (tmp_path / "generated").exists()

def test_godot_execution_uses_config_compiler_and_writes_trace(tmp_path: Path):
    plan = _plan("combat arena with guards and ranged turrets")
    assert plan.production_spec_bundle is not None
    tables = [
        table.model_copy(
            update={
                "format": "csv-ready",
                "export_path": "generated/config/enemies.csv",
            }
        )
        if table.table_id == "enemies"
        else table
        for table in plan.production_spec_bundle.config_tables.tables
    ]
    plan = plan.model_copy(
        update={
            "production_spec_bundle": plan.production_spec_bundle.model_copy(
                update={
                    "config_tables": plan.production_spec_bundle.config_tables.model_copy(
                        update={"tables": tables}
                    )
                }
            )
        }
    )
    bridge = GodotMCPBridge(tmp_path, runner=_ok_runner)

    result = execute_godot_demo(
        plan,
        session_id="config-compiler",
        confirmed=True,
        workspace_root=tmp_path,
        bridge=bridge,
        run_import=False,
    )

    assert result.ok
    project = tmp_path / result.project_dir
    assert (project / "data" / "config" / "enemies.csv").exists()
    trace = project / "data" / "spec-trace.json"
    assert trace.exists()
    assert "config_tables.tables.enemies" in trace.read_text(encoding="utf-8")