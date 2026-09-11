import subprocess
from pathlib import Path

import pytest

from fantasy_agent import local_tools
from fantasy_agent.contracts import (
    GodotMCPCreateProjectRequest,
    GodotMCPRunImportRequest,
    GodotMCPValidateProjectRequest,
    GodotProjectPlan,
)
from fantasy_agent.godot_mcp import GodotMCPBridge, call_godot_mcp_tool, tool_descriptors


def _plan() -> GodotProjectPlan:
    return GodotProjectPlan(
        project_name="MCPPrototype",
        engine_version="Godot 4.3",
        renderer="Compatibility",
        folders=["scenes", "scripts", "assets/generated", "references/comfyui", "data"],
        scenes=["scenes/main.tscn"],
        scripts=["scripts/main.gd", "scripts/player_controller.gd"],
        input_actions=["move_forward", "move_back", "move_left", "move_right", "jump"],
        automation_steps=[
            "Create project.godot",
            "Generate main scene",
            "Run headless import after confirmation",
        ],
        handoff_artifacts=["generated/godot-project-plan.yaml"],
    )


def test_godot_mcp_descriptors_expose_project_validation_and_import_tools():
    names = {tool["name"] for tool in tool_descriptors()}

    assert {
        "create_godot_project_structure",
        "validate_godot_project",
        "run_godot_import",
    }.issubset(names)


def test_create_godot_project_structure_can_write_handoff_files(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path)

    result = bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(plan=_plan(), write_files=True)
    )

    assert result.status == "written"
    assert result.written_files == [
        "generated/godot/mcpprototype/project.godot",
        "generated/godot/mcpprototype/scenes/main.tscn",
        "generated/godot/mcpprototype/scripts/main.gd",
        "generated/godot/mcpprototype/scripts/player_controller.gd",
        "generated/godot/mcpprototype/fantasy-agent-godot-manifest.json",
    ]
    assert (tmp_path / "generated/godot/mcpprototype/project.godot").exists()
    assert (tmp_path / "generated/godot/mcpprototype/assets/generated").exists()
    project_text = (tmp_path / "generated/godot/mcpprototype/project.godot").read_text(
        encoding="utf-8"
    )
    script_text = (tmp_path / "generated/godot/mcpprototype/scripts/main.gd").read_text(
        encoding="utf-8"
    )
    assert 'run/main_scene="res://scenes/main.tscn"' in project_text
    assert "renderer/rendering_method=\"gl_compatibility\"" in project_text
    assert "BoxMesh" in script_text
    assert "UCX_" in script_text


def test_validate_godot_project_accepts_generated_project(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path)
    bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(plan=_plan(), write_files=True)
    )

    result = bridge.validate_godot_project(
        GodotMCPValidateProjectRequest(
            project_file="generated/godot/mcpprototype/project.godot"
        )
    )

    assert result.status == "executed"
    assert result.validation_report is not None
    assert result.validation_report.script_count == 2
    assert result.validation_report.issues == []


def test_run_godot_import_blocks_without_confirmation(tmp_path: Path):
    bridge = GodotMCPBridge(tmp_path)
    bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(plan=_plan(), write_files=True)
    )

    result = bridge.run_godot_import(
        GodotMCPRunImportRequest(
            project_file="generated/godot/mcpprototype/project.godot",
            confirmed_side_effects=False,
        )
    )

    assert result.status == "blocked"
    assert "confirmed_side_effects=true" in result.risks[-1]
    assert "--headless" in result.command
    assert "--path" in result.command
    assert "--import" in result.command


def test_run_godot_import_uses_fake_runner_and_captures_logs(tmp_path: Path):
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="import ok", stderr="")

    bridge = GodotMCPBridge(tmp_path, runner=fake_runner)
    bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(plan=_plan(), write_files=True)
    )

    result = bridge.run_godot_import(
        GodotMCPRunImportRequest(
            project_file="generated/godot/mcpprototype/project.godot",
            confirmed_side_effects=True,
        )
    )

    assert result.status == "executed"
    assert result.stdout_tail == "import ok"
    assert (tmp_path / "generated/logs/godot/mcpprototype_import.stdout.log").exists()


def test_godot_mcp_rejects_paths_outside_generated_godot(tmp_path: Path):
    result = call_godot_mcp_tool(
        "create_godot_project_structure",
        {"plan": _plan().model_dump(mode="json"), "project_dir": "outside/godot"},
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "generated/godot" in result["content"][0]["text"]



def test_create_with_gameplay_scripts_writes_enemy_controller(tmp_path: Path):
    from fantasy_agent.contracts import EnemyPressureTuning, PromptRequest
    from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    scripts = deterministic_gameplay_scripts(spec)
    bridge = GodotMCPBridge(tmp_path)

    result = bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(
            plan=_plan(),
            write_files=True,
            gameplay_spec=spec,
            gameplay_scripts=scripts,
            enemy_tuning=EnemyPressureTuning(
                enemy_count_multiplier=1.5,
                move_speed_multiplier=1.25,
                detection_radius_multiplier=1.1,
            ),
        )
    )

    assert "generated/godot/mcpprototype/scripts/enemy_controller.gd" in result.written_files
    main = (tmp_path / "generated/godot/mcpprototype/scripts/main.gd").read_text(encoding="utf-8")
    assert '"enemies"' in main
    assert '"enemy_count_multiplier": 1.5' in main
    assert "count_multiplier" in main
    assert "move_speed_value" in main
    assert "_spawn_enemies(gm)" in main
    assert 'player.add_to_group("player")' in main


def _main_gd_text(workspace: Path, spec=None, scripts=None) -> str:
    GodotMCPBridge(workspace).create_godot_project_structure(
        GodotMCPCreateProjectRequest(
            plan=_plan(),
            write_files=True,
            gameplay_spec=spec,
            gameplay_scripts=scripts or {},
        )
    )
    return (workspace / "generated/godot/mcpprototype/scripts/main.gd").read_text(encoding="utf-8")


def test_generated_main_script_never_indexes_the_handoff_literal(tmp_path: Path):
    """``HANDOFF["k"]`` is a *static* parse error in Godot, guard or no guard.

    ``HANDOFF`` is a ``const`` dictionary literal, so Godot resolves its keys
    while parsing. Indexing a key the literal does not carry fails to compile
    *even behind* ``if HANDOFF.has("k")`` -- the guard is itself the thing that
    cannot be parsed, which is why ``.get()`` is the only safe read.

    The no-gameplay variant is the one that shipped broken: it is also the only
    variant a model-driven tool call can produce, because the registry hides
    ``gameplay_spec``/``gameplay_scripts`` from the model. It handed Godot a
    main.gd that refused to load, and no test noticed, because the Godot-side
    check skipped whenever the binary was not on PATH.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    texts = {
        "without gameplay": _main_gd_text(tmp_path / "plain"),
        "with gameplay": _main_gd_text(
            tmp_path / "gameplay", spec, deterministic_gameplay_scripts(spec)
        ),
    }

    for label, main in texts.items():
        assert "HANDOFF[" not in main, f"{label}: indexing the const literal cannot be parsed"
        assert 'HANDOFF.get("gameplay", {})' in main, label

    # Only the gameplay variant's manifest carries a gameplay block. Match the
    # JSON key (with the colon) so the `.get("gameplay", ...)` read above does
    # not make the two variants look alike.
    assert '"gameplay":' in texts["with gameplay"]
    assert '"gameplay":' not in texts["without gameplay"]


def test_the_godot_guard_module_does_not_silently_skip_here():
    """A guard that skips is indistinguishable from a guard that passed.

    ``test_gdscript_godot_check.py`` skips when it cannot find a Godot binary:
    correct on a machine without one, and a silent no-op on a machine with one.
    That is precisely how the ``HANDOFF["gameplay"]`` static parse error shipped
    -- the Godot-side guard had been skipping on this machine (it only looked on
    ``PATH``), so nothing noticed that Godot refused to load the ``main.gd`` the
    bridge had just generated.

    This module never skips for that reason, so a discovery regression that is
    *not* "no engine installed" fails here instead of hiding. The project's own
    resolver is the reference: if it can see Godot, the guard has to see it too.
    """

    from test_gdscript_godot_check import _godot_exe

    installed = local_tools._find_godot()
    if installed is None:
        pytest.skip("no Godot on this machine; there is nothing to disagree about")
    if not Path(installed).exists():  # a stale glob hit, not an installed engine
        pytest.skip(f"Godot candidate {installed} no longer exists")

    assert _godot_exe() is not None, (
        f"Godot is installed at {installed} and the project's own resolver finds it, "
        "but the Godot guard module cannot -- so it skips, and generated GDScript that "
        "Godot refuses to parse would pass unnoticed."
    )

