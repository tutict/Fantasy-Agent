"""Guards for per-axis GDScript generation.

Why this file exists
--------------------

``gameplay_codegen`` used to specialise only ``parkour``. Every other axis got
the same WASD+jump body, so a stealth design shipped a prototype that could not
crouch and a puzzle design shipped one with no way to interact. The design was
axis-aware; the code was not.

The guards below are structural rather than behavioural: they fail when a new
axis is added without mechanics, when a mechanics block drifts from the verbs
the design template declares, or — the one that bites at runtime — when a block
presses an InputMap action the generated ``project.godot`` never declares.
"""

from __future__ import annotations

import pytest

from fantasy_agent.axis_templates import AXIS_TEMPLATES
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.gameplay_codegen import (
    _AXIS_MECHANICS,
    ENEMY_SCRIPT,
    GAME_MANAGER_SCRIPT,
    PLAYER_SCRIPT,
    _axis_from_verbs,
    declared_input_actions,
    deterministic_gameplay_scripts,
    referenced_input_actions,
)
from fantasy_agent.generation import design_from_prompt_deterministic

ALL_AXES = sorted(AXIS_TEMPLATES)

# Same prompts as tests/test_generation_axis.py: they are the acceptance
# evidence that each axis is reachable, so reusing them keeps one source.
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


def _spec_for(axis: str):
    return design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=10)
    )


# ── table coverage ───────────────────────────────────────────────────────────

def test_axis_mechanics_cover_every_template_axis():
    """Adding a design axis without mechanics must fail here, not in Godot."""

    assert set(_AXIS_MECHANICS) == set(AXIS_TEMPLATES)


@pytest.mark.parametrize("axis", ALL_AXES)
def test_axis_is_detected_from_the_designs_own_verbs(axis):
    assert _axis_from_verbs(_spec_for(axis)) == axis


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_core_verb_has_an_implementation_block(axis):
    """Each verb the design declares must appear as a ``[VERB]`` anchor in the
    generated controller — otherwise the verb is copy, not mechanics."""

    spec = _spec_for(axis)
    player = deterministic_gameplay_scripts(spec)[PLAYER_SCRIPT]
    for verb in spec.core_verbs:
        anchor = f"[{verb.upper().replace('-', '_').replace(' ', '_')}]"
        assert anchor in player, f"{axis} declares {verb!r} but never implements it"


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_axis_produces_a_distinct_player_controller(axis):
    """The old bug was that every axis produced the same body. If two axes ever
    collapse back onto one script, this fails."""

    bodies = {
        axis: deterministic_gameplay_scripts(_spec_for(axis))[PLAYER_SCRIPT]
        for axis in ALL_AXES
    }
    assert len(set(bodies.values())) == len(ALL_AXES)


@pytest.mark.parametrize("axis", ALL_AXES)
def test_generated_scripts_only_press_declared_input_actions(axis):
    """A block that presses an action the project never declares raises
    'Request for nonexistent InputMap action' the moment the prototype runs.

    Actions come from ``spec.core_verbs`` (see
    ``workflows.prepare_godot_project``), so a verb-shaped action is safe and
    anything else is a latent crash.
    """

    spec = _spec_for(axis)
    declared = declared_input_actions(spec)
    for name, source in deterministic_gameplay_scripts(spec).items():
        stray = referenced_input_actions(source) - declared
        assert not stray, f"{axis}/{name} presses undeclared actions: {sorted(stray)}"


# ── enemy script ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("axis", ALL_AXES)
def test_enemy_script_only_ships_behaviors_the_axis_declares(axis):
    spec = _spec_for(axis)
    template = AXIS_TEMPLATES[axis]
    # Behaviors come from the design's enemy roster, with patrol as the default
    # branch an axis with no enemies still needs.
    expected = {behavior for _name, behavior, _hp, _count in template.enemies} | {"patrol"}
    enemy = deterministic_gameplay_scripts(spec)[ENEMY_SCRIPT]
    for behavior in expected:
        assert f'"{behavior}":' in enemy, f"{axis} enemies need {behavior}"
        assert f"func _{behavior}(" in enemy
    for behavior in {"patrol", "chase", "stationary", "ranged"} - expected:
        assert f'"{behavior}":' not in enemy, f"{axis} ships an unused {behavior} branch"


def test_combat_axis_can_damage_enemies():
    """The combat axis declares attacks, so both ends of the hook must exist:
    the player strikes and the enemy can take it."""

    scripts = deterministic_gameplay_scripts(_spec_for("combat"))
    assert "func _strike_closest_enemy" in scripts[PLAYER_SCRIPT]
    assert 'get_nodes_in_group("enemy")' in scripts[PLAYER_SCRIPT]
    assert "func take_damage" in scripts[ENEMY_SCRIPT]
    assert 'add_to_group("enemy")' in scripts[ENEMY_SCRIPT]


def test_enemy_contact_text_is_axis_specific():
    """Generic contact text makes every failure read the same in a playtest."""

    messages = {
        axis: deterministic_gameplay_scripts(_spec_for(axis))[ENEMY_SCRIPT]
        for axis in ALL_AXES
    }
    reasons = {
        axis: source.split('_notify_failure("')[1].split('")')[0]
        for axis, source in messages.items()
    }
    assert len(set(reasons.values())) == len(ALL_AXES), reasons


# ── game manager contract ────────────────────────────────────────────────────

@pytest.mark.parametrize("axis", ALL_AXES)
def test_game_manager_exposes_the_hooks_axis_mechanics_call(axis):
    """puzzle/career/systems call reach_exit, register_progress and
    register_trigger through the group; the manager must answer all of them."""

    manager = deterministic_gameplay_scripts(_spec_for(axis))[GAME_MANAGER_SCRIPT]
    for hook in ("func reach_exit", "func fail_from_enemy", "func register_progress",
                 "func register_trigger"):
        assert hook in manager
    assert 'add_to_group("game_manager")' in manager


@pytest.mark.parametrize("axis", ALL_AXES)
def test_player_controller_and_manager_stay_valid_gdscript(axis):
    """Cheap structural check: no Python leakage and every func is closed by a
    move_and_slide() / return-style body with 4-space indentation."""

    for name, source in deterministic_gameplay_scripts(_spec_for(axis)).items():
        assert "def " not in source and "None" not in source
        assert source.startswith("extends ")
        for line in source.splitlines():
            if line.strip() and not line.startswith(("func ", "@export", "@onready")):
                indent = len(line) - len(line.lstrip(" "))
                assert indent in {0, 4, 8, 12}, f"{axis}/{name}: bad indent {line!r}"
    assert "move_and_slide()" in deterministic_gameplay_scripts(_spec_for(axis))[PLAYER_SCRIPT]


# ── burst verbs ──────────────────────────────────────────────────────────────

#: axis -> (verb, duration export, timer). Every "burst" verb in the table:
#: they add to velocity, which the same function assigns from the input
#: direction, so both the order and the duration of the addition matter.
BURST_VERBS = {
    "parkour": ("slide", "slide_duration", "_slide_time"),
    "combat": ("evade", "evade_duration", "_evade_time"),
    "mobility": ("dash", "dash_duration", "_dash_time"),
}


@pytest.mark.parametrize("axis", sorted(BURST_VERBS))
def test_burst_verbs_last_longer_than_one_frame(axis):
    """An impulse worth ``x/60`` m is an impulse nobody can feel.

    These three added their boost to velocity for the single frame the key was
    read on: ``6.0`` becomes 0.1m of travel, so slide/evade/dash read as "does
    nothing". Measured on the mobility axis before the fix: dashing covered the
    same 0.80m in 6 frames as not dashing. Each now runs a short burst.
    """

    verb, export, timer = BURST_VERBS[axis]
    player = deterministic_gameplay_scripts(_spec_for(axis))[PLAYER_SCRIPT]

    assert f"@export var {export} :=" in player
    assert f"var {timer} := 0.0" in player
    assert f"{timer} = {verb}_duration" in player, "the burst is never started"
    assert f"if {timer} > 0.0:" in player, "the burst is applied for one frame only"
    assert f"{timer} = maxf(0.0, {timer} - delta)" in player


def test_the_dash_is_applied_after_the_speed_assignment():
    """The mobility dash was erased on the frame it fired.

    ``_MOBILITY_PHYSICS`` added to velocity *before* the pair of assignments
    that set it from the input direction, so the assignment overwrote the whole
    impulse. Asserting the order because that is the defect: with the burst
    moved below them, the impulse survives.
    """

    player = deterministic_gameplay_scripts(_spec_for("mobility"))[PLAYER_SCRIPT]
    assert player.index("_dash_time = dash_duration") > player.index(
        "velocity.z = direction.z * speed"
    )


# ── leaving the route ────────────────────────────────────────────────────────

def test_losing_the_route_ends_the_run():
    """There was no failure for falling, so a fall was a soft-lock.

    The walkway is 3m wide, so stepping off the side is one keypress away --
    and the only thing that could end the run afterwards was the pressure
    clock, which is ten minutes of falling.
    """

    manager = deterministic_gameplay_scripts(_spec_for("parkour"))[GAME_MANAGER_SCRIPT]
    assert "fall_limit" in manager
    assert "player.global_position.y < fall_limit" in manager
    # The parkour spec names this failure itself, so its own words are used.
    assert "Player leaves the rooftop boundary and loses the active route" in manager


def test_an_unnamed_boundary_failure_is_not_quoted_as_the_pressure_clock():
    """A spec with no boundary wording must not be misquoted.

    Falling back to the pressure-clock text would report the run as having
    ended for a reason the spec never gave, which is worse than saying what
    actually happened.
    """

    manager = deterministic_gameplay_scripts(_spec_for("stealth"))[GAME_MANAGER_SCRIPT]
    assert "Left the active route" in manager
    assert "Alert level reaches the lockdown threshold before extraction" in manager, (
        "the pressure-clock text still has to be the timer's reason"
    )
    assert manager.index("Left the active route") != manager.index(
        "Alert level reaches the lockdown threshold before extraction"
    ), "the boundary failure is quoting the timer"


# ── fallback ─────────────────────────────────────────────────────────────────

def test_unknown_verbs_fall_back_to_the_generic_controller():
    """A spec whose verbs match no axis still gets a playable body."""

    spec = _spec_for("parkour")
    spec.core_verbs = ["teleport", "sing", "trade"]
    scripts = deterministic_gameplay_scripts(spec)
    player = scripts[PLAYER_SCRIPT]
    assert _axis_from_verbs(spec) == "generic"
    assert player.startswith("extends CharacterBody3D")
    assert "move_and_slide()" in player
    for verb in ("teleport", "sing", "trade"):
        assert f"[{verb.upper()}]" not in player
