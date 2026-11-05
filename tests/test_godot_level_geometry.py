"""The generated level's geometry, checked without an engine.

Two numbers in two different code generators have to agree or the prototype has
no walkable width: the distance at which an enemy has the player, and the lane
enemies stand in. They agreed by coincidence once -- both were the literal
``1.15`` -- and the generated slice could not be finished by anyone: the
playtest ran 5/5 to ``progress: 0`` about half a second after spawn.

These tests are the cheap half of that guard. The expensive half is
``test_gdscript_godot_check.py``, which walks the real project in a real engine;
this one fails in milliseconds and names the arithmetic.
"""

from __future__ import annotations

import pytest

from fantasy_agent import godot_mcp
from fantasy_agent.contracts import GodotProjectPlan, PromptRequest
from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts
from fantasy_agent.generation import design_from_prompt_deterministic
from fantasy_agent.godot_geometry import (
    CORRIDOR_HALF,
    ENEMY_LANE,
    LETHAL_RADIUS,
    MIN_WALKABLE_BAND,
    LevelGeometryError,
    check_lane_layout,
    kill_zone,
    walkable_band,
)
from fantasy_agent.godot_mcp import _main_gd

PROMPT = "一款仿拳皇的 2D 横版格斗游戏。玩家手里有一副卡牌，按顺序打出两三张组成连招。"

#: The layout the generator used to emit: the lane sat exactly at the radius the
#: enemy controller measured, so a lane's danger zone reached the centreline.
HISTORICAL_LANES = [1.15, -1.15]


def _plan() -> GodotProjectPlan:
    return GodotProjectPlan(
        project_name="GeometryCheck",
        engine_version="Godot 4.5",
        renderer="Compatibility",
        folders=["scenes", "scripts", "assets/generated"],
        scenes=["scenes/main.tscn"],
        scripts=["scripts/main.gd", "scripts/player_controller.gd"],
        input_actions=["move_forward", "move_back", "move_left", "move_right", "jump"],
        automation_steps=["Create project.godot"],
        handoff_artifacts=["generated/godot-project-plan.yaml"],
    )


def _spec():
    return design_from_prompt_deterministic(PromptRequest(prompt=PROMPT, target_minutes=10))


def test_the_historical_layout_had_no_walkable_width():
    """The regression this whole module exists for, stated as arithmetic.

    Measured on the generated slice: 301 sampled points across the 3m tile, 0 of
    them safe. Both lanes were occupied (three chargers and a turret put one
    enemy in each), and the centreline itself was inside both danger zones
    because the comparison is ``<=``.
    """

    assert walkable_band(HISTORICAL_LANES) is None
    corridor = [-CORRIDOR_HALF + i * 0.01 for i in range(int(2 * CORRIDOR_HALF / 0.01) + 1)]
    zones = [kill_zone(lane) for lane in HISTORICAL_LANES]
    safe = [
        x for x in corridor if not any(low <= x <= high for low, high in zones)
    ]
    assert safe == [], f"{len(safe)} of {len(corridor)} samples were safe, so the level was walkable"
    with pytest.raises(LevelGeometryError, match="no player can reach the exit"):
        check_lane_layout(HISTORICAL_LANES)


def test_the_generated_layout_leaves_a_band_a_player_can_stand_in():
    lanes = [ENEMY_LANE, -ENEMY_LANE]
    band = walkable_band(lanes)
    assert band is not None, f"{lanes} cover the corridor"
    low, high = band
    width = high - low
    assert width >= MIN_WALKABLE_BAND, (
        f"{lanes} leave {width:.2f}m of walkable floor, under the "
        f"{MIN_WALKABLE_BAND:.2f}m a player occupies"
    )
    # The middle has to be inside it: holding forward is the one policy every
    # player and every playtest bot starts with.
    assert low < 0.0 < high
    check_lane_layout(lanes)


def test_a_lane_sits_outside_its_own_lethal_radius():
    """The relation, not the number: whatever the radius becomes, the lane moves."""

    assert abs(ENEMY_LANE) > LETHAL_RADIUS
    assert kill_zone(ENEMY_LANE)[0] > 0.0, "the safe lane's zone still reaches the centreline"


def test_one_lane_leaves_the_other_half_of_the_corridor():
    band = walkable_band([ENEMY_LANE])
    assert band is not None
    assert band[1] - band[0] >= MIN_WALKABLE_BAND


def test_a_lane_off_the_tile_is_refused():
    with pytest.raises(LevelGeometryError, match="off the route"):
        check_lane_layout([CORRIDOR_HALF + 1.0])


def test_no_lanes_is_not_a_geometry_problem():
    # An axis that declares no enemies walks a corridor with nothing in it.
    check_lane_layout([])
    assert walkable_band([]) == (-CORRIDOR_HALF, CORRIDOR_HALF)


def test_the_emitted_level_and_the_emitted_enemy_measure_the_same_number():
    """One source of truth, checked in the output rather than in the source.

    Both files are generated text. Reading the literals back out of them is what
    says the two generators still agree -- a refactor that stops consuming the
    shared module would leave the Python constants intact and the game broken.
    """

    main_gd = _main_gd(_plan(), _spec(), with_gameplay=True)
    enemy_gd = deterministic_gameplay_scripts(_spec())["scripts/enemy_controller.gd"]

    assert f"const ENEMY_LANE := {ENEMY_LANE:g}" in main_gd
    assert "var lanes := [ENEMY_LANE, -ENEMY_LANE]" in main_gd
    assert f"const LETHAL_RADIUS := {LETHAL_RADIUS:g}" in enemy_gd
    assert "<= LETHAL_RADIUS" in enemy_gd
    assert "<= 1.15" not in enemy_gd, "the enemy measures a literal again, not the shared constant"

    # And the plain template, which has no gameplay scripts, must not carry a
    # constant it would then leave unused.
    assert "ENEMY_LANE" not in _main_gd(_plan(), None, with_gameplay=False)


def test_level_generation_refuses_a_lane_that_cannot_be_walked(monkeypatch):
    """The gate is wired into generation, not merely available.

    Removing the ``check_lane_layout`` call from ``_main_gd`` leaves every other
    test in this file green -- the module still computes the right answer, it is
    simply never asked. Pushing the lane onto the centreline is the cheapest way
    to force that question, and the answer has to be an exception rather than a
    project.
    """

    monkeypatch.setattr(godot_mcp, "ENEMY_LANE", 0.0)
    with pytest.raises(LevelGeometryError):
        _main_gd(_plan(), _spec(), with_gameplay=True)
