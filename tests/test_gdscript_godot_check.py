"""Parse + runtime check of the generated GDScript in a real Godot.

Structural tests catch typos; they do not catch a script that Godot refuses to
parse, or a block that presses an InputMap action the project never declares —
that one only surfaces at runtime as::

    Request for nonexistent InputMap action "hide"

So this test builds a throwaway project per axis, drops in the three generated
scripts, instantiates them in a SceneTree, pumps frames, and fails on any
SCRIPT ERROR / Parse Error / Invalid call in Godot's output.

Skipped when no Godot binary is available; point ``FANTASY_AGENT_GODOT_EXE`` at
one, or rely on the project's own probe (``local_tools._find_godot``), which
already knows the usual install locations.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from fantasy_agent import local_tools
from fantasy_agent.axis_templates import AXIS_TEMPLATES
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.gameplay_codegen import (
    ENEMY_SCRIPT,
    GAME_MANAGER_SCRIPT,
    PLAYER_SCRIPT,
    declared_input_actions,
    deterministic_gameplay_scripts,
)
from fantasy_agent.generation import design_from_prompt_deterministic
from fantasy_agent.tool_registry import combined_registry

ALL_AXES = sorted(AXIS_TEMPLATES)

PROMPT_FOR_AXIS = {
    "parkour": "rooftop parkour chase across neon towers",
    "career": "a game design applicant portfolio about a career pivot",
    "stealth": "horror stealth in an abandoned hospital",
    "combat": "tactical squad combat with a cover system and a boss",
    "survival": "survival storm on a frozen island with hunger",
    "puzzle": "a portal puzzle dungeon full of logic switches",
    "mobility": "a racing game through underwater caves",
    "systems": "a cozy farming sim about growing magical pumpkins",
}

#: Strings Godot prints when the generated code is wrong.
FAILURE_MARKERS = (
    "SCRIPT ERROR",
    "Parse Error",
    # Godot 4.5 wording: 'The InputMap action "hide" doesn't exist.'
    "InputMap action",
    "Invalid call",
    "Identifier not found",
    # Catch-all: Godot prints every runtime error as "ERROR: ..." on stderr.
    # A clean project produces no stderr at all, so anything here is a bug.
    "ERROR:",
)

_HARNESS = """extends SceneTree

func _initialize() -> void:
    var packed: PackedScene = load("res://scenes/main.tscn")
    var scene := packed.instantiate()
    get_root().add_child(scene)
    for _i in range(20):
        await process_frame
    quit()
"""

#: Drives the assembled prototype with real input over real physics frames.
#:
#: Pumping frames and watching for error strings is not a playtest: every
#: defect this catches imports and parses cleanly. Measured before the guards
#: landed -- the run reported WIN on its first frame (the exit trigger saw its
#: own parent), ``move_forward`` moved the player 0.0m (the spawn was inside a
#: solid beat marker), the exit stood 3.5m past the last tile, and the enemies
#: could not fail anyone because the run was already over.
_PLAYTEST = """extends SceneTree


func _say(key: String, value: Variant) -> void:
	print("PT|", key, "|", value)


func _spawn() -> Node:
	var packed: PackedScene = load("res://scenes/main.tscn")
	var scene: Node = packed.instantiate()
	get_root().add_child(scene)
	return scene


# Each tile is 3m across (x) and 5m along the route (z), so these are its half
# extents. ROUTE_SLACK is how far past a tile edge a body may be and still read
# as standing on the walkway: a patrol turns around when it reaches
# patrol_radius, and it crosses that line by up to one frame of travel (0.04m at
# the generated move_speed; measured 0.02m on the stealth axis), so a zero-slack
# test calls a legal patrol a stray.
const ROUTE_TILE_HALF_X := 1.5
const ROUTE_TILE_HALF_Z := 2.5
const ROUTE_SLACK := 0.5


func _route_excursion(scene: Node, point: Vector3) -> float:
	# How far outside the walkway this point is: 0.0 over any tile, measured
	# against the nearest one otherwise.
	var nearest := INF
	for child in scene.get_children():
		if not str(child.name).begins_with("FA_RouteFloor"):
			continue
		var tile := child as Node3D
		var dx := maxf(0.0, absf(tile.position.x - point.x) - ROUTE_TILE_HALF_X)
		var dz := maxf(0.0, absf(tile.position.z - point.z) - ROUTE_TILE_HALF_Z)
		nearest = minf(nearest, Vector2(dx, dz).length())
	return nearest


func _on_route(scene: Node, point: Vector3) -> bool:
	return _route_excursion(scene, point) <= ROUTE_SLACK


func _initialize() -> void:
	await process_frame
	await _static_report()
	await _walk_to_the_exit()
	await _enemy_contact()
	await _fall_off_the_route()
	await _patrol_stays_on_the_route()
	await _dash_burst()
	quit()


func _dash_burst() -> void:
	var scene := _spawn()
	await physics_frame
	var player := scene.get_node_or_null("FA_Player") as CharacterBody3D
	if player == null or player.get("_dash_time") == null:
		_say("dash_supported", false)
		scene.free()
		return
	_say("dash_supported", true)
	for _i in range(30):
		await physics_frame
	Input.action_press("move_forward")
	for _i in range(12):
		await physics_frame
	var plain_start: Vector3 = player.global_position
	for _i in range(6):
		await physics_frame
	_say("plain_6_frames", plain_start.distance_to(player.global_position))
	var dash_start: Vector3 = player.global_position
	Input.action_press("dash")
	await physics_frame
	Input.action_release("dash")
	for _i in range(5):
		await physics_frame
	_say("dash_6_frames", dash_start.distance_to(player.global_position))
	Input.action_release("move_forward")
	scene.free()


func _patrol_stays_on_the_route() -> void:
	var scene := _spawn()
	await physics_frame
	var patrolling: Array = []
	for enemy in get_nodes_in_group("enemy"):
		if enemy.behavior == "patrol":
			patrolling.append(enemy)
	_say("patrol_count", patrolling.size())
	var worst: Array = []
	for _enemy in patrolling:
		worst.append(0.0)
	# Watched every frame, not read once at the end. A patrol that strides across
	# the walkway instead of along it is only off it for part of each leg, so a
	# single reading can land mid-leg and call it fine -- which is exactly how
	# this went unnoticed: one sample of three patrols showed one stray.
	for _i in range(240):
		await physics_frame
		for index in patrolling.size():
			var enemy := patrolling[index] as Node3D
			worst[index] = maxf(worst[index], _route_excursion(scene, enemy.global_position))
	var off := 0
	for excursion in worst:
		if excursion > ROUTE_SLACK:
			off += 1
	_say("patrol_off_route", off)
	_say("patrol_worst_excursion", worst.max() if not worst.is_empty() else 0.0)
	scene.free()


func _static_report() -> void:
	var scene := _spawn()
	await physics_frame
	await physics_frame
	var player := scene.get_node_or_null("FA_Player")
	var gm := get_first_node_in_group("game_manager")
	_say("player_present", player != null)
	_say("game_manager_present", gm != null)
	_say("ended_at_spawn", gm._ended if gm != null else true)
	_say("hud_at_spawn", gm._hud.text if gm != null and gm._hud else "")
	var enemies := get_nodes_in_group("enemy")
	_say("enemy_count", enemies.size())
	var on_route := 0
	for enemy in enemies:
		if _on_route(scene, (enemy as Node3D).global_position):
			on_route += 1
	_say("enemies_on_route", on_route)
	_say("exit_trigger_present", scene.get_node_or_null("FA_ExitTrigger") != null)
	scene.free()


func _walk_to_the_exit() -> void:
	var scene := _spawn()
	await physics_frame
	var player := scene.get_node_or_null("FA_Player") as Node3D
	var gm := get_first_node_in_group("game_manager")
	if player == null or gm == null:
		_say("walk_ended", false)
		scene.free()
		return
	# Clear the threats: this asks whether the *route* carries a walking player
	# to the exit, which an intercepting enemy would mask.
	for enemy in get_nodes_in_group("enemy"):
		enemy.free()
	for _i in range(30):
		await physics_frame
	var start: Vector3 = player.global_position
	Input.action_press("move_forward")
	for _i in range(600):
		await physics_frame
		if gm._ended:
			break
	Input.action_release("move_forward")
	_say("walk_moved", start.distance_to(player.global_position))
	_say("walk_ended", gm._ended)
	_say("walk_hud", gm._hud.text)
	_say("walk_fell_out", player.global_position.y < -5.0)
	scene.free()


func _enemy_contact() -> void:
	var scene := _spawn()
	await physics_frame
	var player := scene.get_node_or_null("FA_Player") as Node3D
	var gm := get_first_node_in_group("game_manager")
	var enemies := get_nodes_in_group("enemy")
	if player == null or gm == null or enemies.is_empty():
		_say("contact_hud", "MISSING")
		scene.free()
		return
	player.global_position = (enemies[0] as Node3D).global_position
	for _i in range(30):
		await physics_frame
	_say("contact_ended", gm._ended)
	_say("contact_hud", gm._hud.text)
	scene.free()


func _fall_off_the_route() -> void:
	var scene := _spawn()
	await physics_frame
	var player := scene.get_node_or_null("FA_Player") as Node3D
	var gm := get_first_node_in_group("game_manager")
	if player == null or gm == null:
		_say("boundary_hud", "MISSING")
		scene.free()
		return
	player.global_position = Vector3(6.0, 4.0, 0.0)
	for _i in range(300):
		await physics_frame
		if gm._ended:
			break
	_say("boundary_hud", gm._hud.text)
	scene.free()
"""


def _godot_exe() -> str | None:
    """The Godot to check with: explicit override, then PATH, then the probe.

    ``local_tools._find_godot`` is the same resolver the engine tools use, and
    it prefers the ``*_console`` build on Windows -- the only one whose output a
    captured pipe actually receives. Without it this module skipped silently on
    a machine with Godot installed outside PATH, which is exactly how a broken
    generated script keeps passing.
    """

    candidates = [
        os.environ.get("FANTASY_AGENT_GODOT_EXE", ""),
        shutil.which("godot") or "",
        local_tools._find_godot() or "",
    ]
    return next((c for c in candidates if c and Path(c).exists()), None)


pytestmark = pytest.mark.skipif(
    _godot_exe() is None,
    reason="no Godot binary found (checked FANTASY_AGENT_GODOT_EXE, PATH and the install probe)",
)


def _write(project_dir, relative: str, content: str) -> None:
    path = project_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_project(tmp_path, axis: str, spec) -> object:
    project = tmp_path / f"axis_{axis}"
    scripts = deterministic_gameplay_scripts(spec)
    actions = "\n".join(
        f'{action}={{"deadzone":0.5,"events":[]}}' for action in sorted(declared_input_actions(spec))
    )
    _write(
        project,
        "project.godot",
        f'config_version=5\n\n[application]\nconfig/name="AxisCheck"\n'
        f'run/main_scene="res://scenes/main.tscn"\n\n[input]\n{actions}\n',
    )
    _write(project, PLAYER_SCRIPT, scripts[PLAYER_SCRIPT])
    _write(project, GAME_MANAGER_SCRIPT, scripts[GAME_MANAGER_SCRIPT])
    _write(project, ENEMY_SCRIPT, scripts[ENEMY_SCRIPT])
    _write(project, "scripts/verify_harness.gd", _HARNESS)
    _write(
        project,
        "scenes/main.tscn",
        '[gd_scene load_steps=4 format=3]\n\n'
        '[ext_resource type="Script" path="res://scripts/game_manager.gd" id="1_gm"]\n'
        '[ext_resource type="Script" path="res://scripts/player_controller.gd" id="2_pc"]\n'
        '[ext_resource type="Script" path="res://scripts/enemy_controller.gd" id="3_ec"]\n\n'
        '[node name="Main" type="Node3D"]\n\n'
        '[node name="GameManager" type="Node" parent="."]\nscript = ExtResource("1_gm")\n\n'
        '[node name="FA_Player" type="CharacterBody3D" parent="."]\nscript = ExtResource("2_pc")\n\n'
        '[node name="Enemy" type="Area3D" parent="."]\nscript = ExtResource("3_ec")\n',
    )
    return project


@pytest.mark.parametrize("axis", ALL_AXES)
def test_generated_scripts_load_and_run_in_godot(tmp_path, axis):
    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=10)
    )
    project = _build_project(tmp_path, axis, spec)
    for name in (PLAYER_SCRIPT, GAME_MANAGER_SCRIPT, ENEMY_SCRIPT):
        result = subprocess.run(
            [
                _godot_exe(),
                "--headless",
                "--path",
                str(project),
                "--check-only",
                "--script",
                f"res://{name}",
            ],
            check=False,  # failures are asserted through FAILURE_MARKERS below
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        bad = [marker for marker in FAILURE_MARKERS if marker in output]
        assert not bad, f"{axis}/{name} -> {bad}\n{output}"

    # Now actually instantiate and pump frames: this is what catches an
    # InputMap action the generated project.godot never declared.
    result = subprocess.run(
        [
            _godot_exe(),
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://scripts/verify_harness.gd",
        ],
        check=False,  # the harness reports through markers, not the exit code
        capture_output=True,
        text=True,
        timeout=180,
    )
    output = result.stdout + result.stderr
    bad = [marker for marker in FAILURE_MARKERS if marker in output]
    assert not bad, f"{axis} runtime -> {bad}\n{output}"


def _result_data(outcome) -> dict:
    """The structured half of a tool result, whichever shape it arrived in."""

    data = outcome.data
    return data.get("structuredContent") or data


def _import_and_read_the_log(registry, workspace: Path, project_file: str, label: str) -> None:
    """Import a project through a tool call and fail on anything Godot printed."""

    imported = registry.call(
        "run_godot_import",
        {"project_file": project_file, "confirmed_side_effects": True, "timeout_seconds": 180},
        allow_execute=True,
    )
    assert imported.status == "ok", imported.content
    structured = _result_data(imported)
    assert structured["return_code"] == 0, structured

    # The tail is capped at 4000 chars, so read the log itself: a parse error
    # printed early would otherwise be pushed out by later progress output.
    log_dir = workspace / "generated" / "logs" / "godot"
    logs = sorted(log_dir.glob("*"))
    assert logs, f"{label}: no Godot logs under {log_dir} -- the engine never ran"
    output = "".join(path.read_text(encoding="utf-8") for path in logs)
    assert output.strip(), f"{label}: Godot logged nothing, so the check would be vacuous"
    bad = [marker for marker in FAILURE_MARKERS if marker in output]
    assert not bad, f"{label} -> {bad}\n{output}"


def test_the_registry_built_project_survives_a_real_godot(tmp_path):
    """Both shapes a tool call can produce have to load in a real Godot.

    A tool call gets a project built one of two ways, and they differ in exactly
    the place that broke:

    * a plan whose result carries a gameplay spec -- what a model's session
      produces, and the manifest then has a ``gameplay`` block;
    * a plan and no spec -- the plain player template, no ``game_manager.gd``,
      no ``gameplay`` block in the manifest. Still the documented fallback for
      any caller that hands over only a plan.

    That second template used to read its const manifest as ``HANDOFF["gameplay"]``,
    which Godot rejects as a *static* parse error -- the key is checked against
    the literal while parsing, so even ``if HANDOFF.has(...)`` around it fails to
    compile. Godot then refused to load the prototype at all, while
    ``validate_godot_project`` reported ``issues: []``, because it only checks
    that files exist.

    Nothing caught it: ``test_godot_mcp`` never ran Godot, and this module
    skipped whenever the binary was not on PATH.

    Both legs are here because fixing the registry to supply the spec took the
    plain manifest *out* of the tool-call path. The defect then became invisible
    to this test rather than fixed -- a driver whose mutation goes unnoticed is
    not a guard -- so the plan-only leg stays, asserted to really be the plain
    one.
    """

    registry = combined_registry(tmp_path / "planned")
    planned = registry.call(
        "generate_game_production_plan",
        {"prompt": PROMPT_FOR_AXIS["parkour"], "target_minutes": 10},
    )
    registry.remember_plan(planned.data)
    created = registry.call(
        "create_godot_project_structure", {"write_files": True}, allow_write=True
    )
    assert created.status == "ok", created.content
    planned_project = _result_data(created)["artifact"]["project_file"]
    _import_and_read_the_log(
        registry, tmp_path / "planned", planned_project, "the spec-carrying project"
    )

    # A store holding the plan but not the spec is how a caller gets the
    # plan-only project. Written into the store rather than passed as an
    # argument, because a hidden argument is discarded whatever arrives -- the
    # plan has to come from where the registry looks for it.
    spec_source = planned.data.get("summary")
    if not isinstance(spec_source, dict):
        spec_source = planned.data
    plain_registry = combined_registry(tmp_path / "plain")
    plain_registry.artifacts["godot_plan"] = spec_source["godot_plan"]
    plan_only = plain_registry.call(
        "create_godot_project_structure", {"write_files": True}, allow_write=True
    )
    assert plan_only.status == "ok", plan_only.content
    plain_project = _result_data(plan_only)["artifact"]["project_file"]

    main_gd = (tmp_path / "plain" / plain_project).parent / "scripts" / "main.gd"
    plain_text = main_gd.read_text(encoding="utf-8")
    assert '"gameplay":' not in plain_text, (
        "the plan-only leg picked up a gameplay block, so it is re-testing the "
        "first leg -- and the manifest it exists to load is no longer covered"
    )
    assert not (main_gd.parent / "game_manager.gd").exists(), (
        "the plan-only project grew a game manager, so it is no longer the "
        "plain template this leg exists to load"
    )
    _import_and_read_the_log(
        plain_registry, tmp_path / "plain", plain_project, "the plan-only project"
    )


# ── the prototype gets played, not just loaded ───────────────────────────────


def _registry_project(tmp_path, prompt: str) -> Path:
    """Build a project the way a tool call does, and return its directory."""

    registry = combined_registry(tmp_path)
    planned = registry.call(
        "generate_game_production_plan", {"prompt": prompt, "target_minutes": 10}
    )
    registry.remember_plan(planned.data)
    created = registry.call(
        "create_godot_project_structure", {"write_files": True}, allow_write=True
    )
    assert created.status == "ok", created.content
    structured = created.data.get("structuredContent") or created.data
    project_file = structured["artifact"]["project_file"]
    return tmp_path / Path(project_file).parent


def _play(project: Path) -> dict[str, str]:
    _write(project, "scripts/playtest.gd", _PLAYTEST)
    result = subprocess.run(
        [
            _godot_exe(),
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://scripts/playtest.gd",
        ],
        check=False,  # the playtest reports through PT| lines, not the exit code
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout + result.stderr
    bad = [marker for marker in FAILURE_MARKERS if marker in output]
    assert not bad, f"{project.name} -> {bad}\n{output}"

    report: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("PT|"):
            _, key, value = line.split("|", 2)
            report[key] = value
    assert report, f"the playtest printed nothing:\n{output}"
    return report


@pytest.mark.parametrize("axis", ["parkour", "stealth", "mobility"])
def test_the_generated_prototype_can_actually_be_played(tmp_path, axis):
    """Load-and-look-for-errors is not a playtest.

    Every defect here survives a clean import, a clean parse and 20 pumped
    frames -- which is all this module used to do, and why all of it shipped.
    The prototype is driven with real input now, over real physics frames, and
    asked the questions a player would ask: is there a player, did the run start
    un-ended, does forward move me, does the route carry me to the exit, does an
    enemy fail me, and does stepping off the side fail me.

    Three axes on purpose: parkour's enemy chases and stealth's patrol, so both
    branches of the enemy roster move and get checked against the route, plus
    mobility, whose burst verb needs a measurement rather than a source
    assertion.
    """

    report = _play(_registry_project(tmp_path, PROMPT_FOR_AXIS[axis]))

    assert report["player_present"] == "true", "nothing to move"
    assert report["game_manager_present"] == "true", "nothing to win or lose"
    assert report["ended_at_spawn"] == "false", (
        f"the run was already over on the first frame: {report['hud_at_spawn']}"
    )
    assert float(report["walk_moved"]) >= 3.0, (
        f"holding forward moved the player {report['walk_moved']}m"
    )
    assert report["walk_fell_out"] == "false", "walking forward left the route"
    assert report["walk_ended"] == "true", "walking the route to its end never ended the run"
    assert report["walk_hud"].startswith("WIN"), report["walk_hud"]
    assert report["exit_trigger_present"] == "true"

    # Whether there is anything to be caught by is the design's call, so ask the
    # roster rather than assuming: mobility declares no enemies at all.
    if AXIS_TEMPLATES[axis].enemies:
        assert int(report["enemy_count"]) >= 1, "the design declares enemies"
        assert report["enemies_on_route"] == report["enemy_count"], (
            f"{report['enemy_count']} enemies, {report['enemies_on_route']} on the route"
        )
        assert report["contact_ended"] == "true", "walking into an enemy did not end the run"
        assert report["contact_hud"].startswith("FAIL"), report["contact_hud"]
    else:
        assert report["enemy_count"] == "0", "the design declares no enemies"
        assert report["contact_hud"] == "MISSING", report["contact_hud"]
    assert report["boundary_hud"].startswith("FAIL"), (
        f"falling off the route was not a failure: {report['boundary_hud']}"
    )
    # A patrol that walks across the route rather than along it leaves the
    # walkway on its first leg, where it guards nothing -- and it only shows up
    # after the thing has been moving for a while.
    declared_patrols = sum(
        count
        for _name, behavior, _hp, count in AXIS_TEMPLATES[axis].enemies
        if behavior == "patrol"
    )
    assert int(report["patrol_count"]) == declared_patrols, (
        f"the design declares {declared_patrols} patrols; the scene has "
        f"{report['patrol_count']}, so 'none drifted' would mean nothing"
    )
    assert report["patrol_off_route"] == "0", (
        f"{report['patrol_off_route']} of {report['patrol_count']} patrols drifted off "
        f"the route (worst excursion {report['patrol_worst_excursion']}m)"
    )
    if report.get("dash_supported") == "true":
        plain = float(report["plain_6_frames"])
        dashed = float(report["dash_6_frames"])
        assert plain > 0.0, report
        assert dashed > plain * 1.3, (
            f"dashing covered {dashed}m in 6 frames, walking covered {plain}m -- "
            "the burst is not reaching the movement"
        )
