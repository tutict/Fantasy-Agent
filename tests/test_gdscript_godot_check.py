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


def test_the_registry_built_project_survives_a_real_godot(tmp_path):
    """The project a *tool call* produces has to load in a real Godot.

    This is the path a model takes. The registry hides ``gameplay_spec`` and
    ``gameplay_scripts`` from the model, so the project is built with the plain
    ``main.gd`` template and a manifest that carries no ``gameplay`` block.
    That template used to read its const manifest as ``HANDOFF["gameplay"]``,
    which Godot rejects as a *static* parse error -- the key is checked against
    the literal while parsing, so even ``if HANDOFF.has(...)`` around it fails
    to compile. Godot then refused to load the prototype at all, while
    ``validate_godot_project`` reported ``issues: []``, because it only checks
    that files exist.

    Nothing caught it: ``test_godot_mcp`` never ran Godot, and this module
    skipped whenever the binary was not on PATH.
    """

    registry = combined_registry(tmp_path)
    planned = registry.call(
        "generate_game_production_plan",
        {"prompt": PROMPT_FOR_AXIS["parkour"], "target_minutes": 10},
    )
    registry.remember_plan(planned.data)

    created = registry.call(
        "create_godot_project_structure", {"write_files": True}, allow_write=True
    )
    assert created.status == "ok", created.content
    project_file = (created.data.get("structuredContent") or created.data)["artifact"][
        "project_file"
    ]

    imported = registry.call(
        "run_godot_import",
        {"project_file": project_file, "confirmed_side_effects": True, "timeout_seconds": 180},
        allow_execute=True,
    )
    assert imported.status == "ok", imported.content
    structured = imported.data.get("structuredContent") or imported.data
    assert structured["return_code"] == 0, structured

    # The tail is capped at 4000 chars, so read the log itself: a parse error
    # printed early would otherwise be pushed out by later progress output.
    log_dir = tmp_path / "generated" / "logs" / "godot"
    logs = sorted(log_dir.glob("*"))
    assert logs, f"no Godot logs under {log_dir} -- the engine never ran"
    output = "".join(path.read_text(encoding="utf-8") for path in logs)
    assert output.strip(), "Godot logged nothing, so the marker check would be vacuous"
    bad = [marker for marker in FAILURE_MARKERS if marker in output]
    assert not bad, f"registry-built project -> {bad}\n{output}"
