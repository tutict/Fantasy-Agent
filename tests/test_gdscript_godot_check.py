"""Parse + runtime check of the generated GDScript in a real Godot.

Structural tests catch typos; they do not catch a script that Godot refuses to
parse, or a block that presses an InputMap action the project never declares —
that one only surfaces at runtime as::

    Request for nonexistent InputMap action "hide"

So this test builds a throwaway project per axis, drops in the three generated
scripts, instantiates them in a SceneTree, pumps frames, and fails on any
SCRIPT ERROR / Parse Error / Invalid call in Godot's output.

Skipped when no Godot binary is available; point ``FANTASY_AGENT_GODOT_EXE`` at
one (or have ``godot`` on PATH) to run it.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

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


def _godot_exe() -> str | None:
    candidates = [os.environ.get("FANTASY_AGENT_GODOT_EXE", ""), shutil.which("godot") or ""]
    return next((c for c in candidates if c and os.path.exists(c)), None)


pytestmark = pytest.mark.skipif(
    _godot_exe() is None, reason="no Godot binary (set FANTASY_AGENT_GODOT_EXE)"
)


def _write(project_dir, relative: str, content: str) -> None:
    path = project_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_project(tmp_path, axis: str, spec) -> "object":
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
        capture_output=True,
        text=True,
        timeout=180,
    )
    output = result.stdout + result.stderr
    bad = [marker for marker in FAILURE_MARKERS if marker in output]
    assert not bad, f"{axis} runtime -> {bad}\n{output}"
