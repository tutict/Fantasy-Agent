import subprocess
from pathlib import Path

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
    from fantasy_agent.generation import design_from_prompt_deterministic
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    scripts = deterministic_gameplay_scripts(spec)
    bridge = GodotMCPBridge(tmp_path)

    result = bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(
            plan=_plan(),
            write_files=True,
            gameplay_spec=spec,
            gameplay_scripts=scripts,
        )
    )

    assert "generated/godot/mcpprototype/scripts/enemy_controller.gd" in result.written_files
    main = (tmp_path / "generated/godot/mcpprototype/scripts/main.gd").read_text(encoding="utf-8")
    assert '"enemies"' in main
    assert "_spawn_enemies(gm)" in main
    assert 'player.add_to_group("player")' in main
