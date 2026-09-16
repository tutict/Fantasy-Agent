import re
import subprocess
from itertools import pairwise
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

    The no-gameplay variant is the one that shipped broken. A tool call used to
    produce nothing else, because the registry hid ``gameplay_spec`` /
    ``gameplay_scripts`` from the model and nothing supplied them back; it hands
    the spec over now, so this variant is what a bare bridge call still
    produces. It gave Godot a main.gd that refused to load, and no test noticed,
    because the Godot-side check skipped whenever the binary was not on PATH.
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


# ── the route a player can actually walk ────────────────────────────────────
#
# Everything below was found by driving a generated prototype with real input
# over real physics frames. Every one of them imports and parses cleanly, which
# is why the parse-only guard above let all of it through.


def _route_floor_z(main: str) -> list[float]:
    names = re.findall(
        r'_box\("(FA_RouteFloor\w*)", Vector3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)', main
    )
    return [float(z) for _name, _x, _y, z in names]


@pytest.mark.parametrize("with_spec", [False, True])
def test_the_route_runs_along_the_axis_move_forward_moves(tmp_path: Path, with_spec: bool):
    """The route used to run along ``x`` while ``move_forward`` is ``-z``.

    The controller maps ``move_forward`` to ``Vector3(0, 0, -1)``, so a route
    laid out along ``x`` lay *across* the player and the first key anyone
    presses walks them off its side, into open air, with nothing below to land
    on. Measured before the fix: forward moved the player 0.0m.

    Both routes: the fixed one used without a spec, and the per-beat one.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = (
        design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
        if with_spec
        else None
    )
    main = _main_gd_text(tmp_path, spec)
    names = re.findall(
        r'_box\("(FA_RouteFloor\w*)", Vector3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)', main
    )
    assert names, "the route emitted no floor tiles"
    assert all(x == "0.0" for _n, x, _y, _z in names), names


def test_the_route_has_no_gap_between_tiles(tmp_path: Path):
    """Tiles were 5.0 long and 6.0 apart: a 1.0m hole between every pair.

    The player is 0.8m wide, so a walking player drops through the route rather
    than along it -- and nothing catches a fall, so the run then ended only when
    the pressure clock ran out.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    zs = _route_floor_z(_main_gd_text(tmp_path, spec))
    assert len(zs) >= 3, zs

    gaps = [round(a - b, 3) for a, b in pairwise(zs)]
    assert all(gap == 5.0 for gap in gaps), (
        f"consecutive tiles must be one tile-length apart so they touch; got {gaps} from {zs}"
    )


def test_the_exit_gate_stands_on_a_tile(tmp_path: Path):
    """The gate used to hang one full spacing past the last floor.

    That is 3.5m of air between the end of the route and the thing that ends
    it -- reachable only by a jump nobody is told about.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    main = _main_gd_text(tmp_path, spec)
    floor_z = _route_floor_z(main)
    gate = re.search(r'_box\("FA_Exit_Gate", Vector3\(0\.0, [\d.]+, ([-\d.]+)\)', main)
    assert gate is not None, "no exit gate in the route"
    assert round(float(gate.group(1)), 3) in [round(z, 3) for z in floor_z[-1:]], (
        f"the gate at z={gate.group(1)} is not on the last tile {floor_z[-1]}"
    )


def test_route_props_carry_no_collision(tmp_path: Path):
    """A solid prop in a 3m corridor is an invisible wall.

    The player spawns on the first tile and the first beat's marker sat on that
    same tile as a ``StaticBody3D`` -- so the player was spawned inside it, got
    depenetrated 0.8m sideways, and every step forward was blocked by the pillar
    (``get_slide_collision`` named the marker). The greybox stand-in was also
    stricter than the glb it stands in for, which carries only the collision the
    asset itself has.
    """

    main = _main_gd_text(tmp_path)
    assert "return _prop(node_name, origin, size, color)" in main, (
        "the marker's greybox fallback must be a mesh-only prop"
    )
    for prop in (
        "FA_Ramp_Teach",
        "FA_Checkpoint_Gate",
        "FA_Objective_Prop",
        "FA_Boost_Pad",
        "FA_Fall_Hazard_A",
    ):
        assert f'_prop("{prop}"' in main, f"{prop} is emitted as a solid body"
    # The route's collision is what it is made of, plus the gate at the end.
    assert '_box("FA_RouteFloor_Start"' in main
    assert '_box("FA_Exit_Gate"' in main


def test_the_player_spawns_where_the_route_actually_starts(tmp_path: Path):
    """The spawn was one hardcoded coordinate, correct for one beat count.

    ``Vector3(-6.0, 1.0, 0.0)`` is the first tile of a three-beat route and
    nothing else: a four-beat route starts at -9, so the player was dropped
    into the hole between two tiles instead of onto the route.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    main = _main_gd_text(tmp_path, spec, deterministic_gameplay_scripts(spec))
    assert "Vector3(-6.0, 1.0, 0.0)" not in main
    assert "player.position = _player_spawn_position()" in main
    assert "floors[0]" in main, "the spawn has to be read off the generated route"


def test_the_exit_trigger_is_not_a_child_of_its_own_gate(tmp_path: Path):
    """This is what made every generated run report ``WIN`` on its first frame.

    An ``Area3D`` placed inside the ``StaticBody3D`` that is its own parent
    reports that parent as an overlap, so ``body_entered`` fired while the scene
    was loading and ``reach_exit()`` won the run before the player could move.
    Measured: ``get_overlapping_bodies()`` == ``[FA_Exit_Gate]``, HUD ``WIN``
    two physics frames in.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts
    from fantasy_agent.generation import design_from_prompt_deterministic

    spec = design_from_prompt_deterministic(PromptRequest(prompt="rooftop parkour chase"))
    main = _main_gd_text(tmp_path, spec, deterministic_gameplay_scripts(spec))

    assert "exit.add_child(area)" not in main, "the trigger cannot be the gate's child"
    assert "add_child(area)" in main
    assert "area.body_entered.connect(_on_exit_entered.bind(gm))" in main
    assert 'body.is_in_group("player")' in main, (
        "only the player's arrival may end the run; a patrolling enemy walking "
        "through the gate is not an arrival"
    )


def test_a_tool_call_builds_a_project_that_can_be_played(tmp_path: Path):
    """The model never sends the gameplay spec, so the pipeline has to.

    ``create_godot_project_structure`` hides ``gameplay_spec`` /
    ``gameplay_scripts`` / ``production_spec_bundle`` from the model -- and,
    until now, hid them from itself as well: nothing filled them back in. Every
    tool-driven run therefore wrote the plain player template, no
    ``game_manager.gd``, and a ``main.gd`` without ``_spawn_gameplay()``: a
    project with no player at all, nothing to win and nothing to lose. It
    imported cleanly, which is exactly why it read as fine.
    """

    from fantasy_agent.tool_registry import combined_registry

    registry = combined_registry(tmp_path)
    planned = registry.call(
        "generate_game_production_plan",
        {"prompt": "rooftop parkour chase across neon towers", "target_minutes": 10},
    )
    registry.remember_plan(planned.data)

    created = registry.call("create_godot_project_structure", {"write_files": True}, allow_write=True)
    assert created.status == "ok", created.content
    structured = created.data.get("structuredContent") or created.data
    written = structured["written_files"]
    assert any(name.endswith("game_manager.gd") for name in written), written

    main = next(tmp_path.glob("generated/godot/*/scripts/main.gd")).read_text(encoding="utf-8")
    assert "_spawn_gameplay()" in main
    assert 'add_to_group("player")' in main
    assert '"enemies"' in main, "the manifest has to carry the roster the spawn loop reads"
