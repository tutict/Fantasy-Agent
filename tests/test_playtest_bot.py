"""The bot presses the axis's verbs — all of them, and nothing else.

Gate 4's static half. The playtest used to ship one input plan for every axis
(hold ``move_forward``, tap ``jump``), so a combat slice reported "playable" on a
run where ``attack`` had never been pressed once. This module pins the other
side: the key set is enumerated per axis, and it is compared with the actions
that axis's *emitted controller* actually reads.

The comparison is the point. A table checked against itself agrees with itself;
this one is checked against generated source, so:

* a verb added to an axis's physics stops the suite until the bot learns it
  (otherwise the bot is blind to it again, silently);
* a key added to a policy that no controller reads fails too, because a bot
  pressing a dead key reports a verb it never exercised;
* a new axis with no bot fails, so "no policy" cannot be mistaken for "nothing
  to press".

The runtime half — that the presses arrive and that the priced verbs move a
number — is in ``test_gdscript_godot_check.py``, because that needs the engine.
"""

from __future__ import annotations

import pytest

from fantasy_agent.axis_templates import AXIS_TEMPLATES
from fantasy_agent.contracts import PlaytestSample, PromptRequest
from fantasy_agent.gameplay_codegen import (
    BASE_INPUT_ACTIONS,
    PLAYER_SCRIPT,
    axis_for_spec,
    deterministic_gameplay_scripts,
    referenced_input_actions,
)
from fantasy_agent.generation import design_from_prompt_deterministic
from fantasy_agent.playtest_bot import (
    BOT_POLICIES,
    COMMIT_VERBS,
    GENERIC_POLICY,
    JUMP_ACTION,
    MOVE_ACTION,
    VERB_WINDOW_FRAMES,
    policy_for,
    render_drive_gd,
)

ALL_AXES = sorted(AXIS_TEMPLATES)


def test_every_priced_effect_names_a_reported_sample_field():
    for axis, policy in BOT_POLICIES.items():
        assert set(policy.priced) <= set(PlaytestSample.model_fields), axis


def test_a_held_key_is_recorded_even_when_it_survives_the_previous_run():
    rendered = render_drive_gd(policy_for("parkour"), input_plan="forward_and_jump")
    hold_function = rendered.split("func _policy_hold(", 1)[1].split("\n\nfunc ", 1)[0]
    # The product is generated GDScript. Recording after this early return
    # loses the key on every run after the first scene reload.
    assert hold_function.index("_held.append(action)") < hold_function.index(
        "if Input.is_action_pressed(action):"
    )

#: Same prompts ``test_gdscript_godot_check`` builds its projects from; kept
#: here rather than imported so this module does not pull a second copy of the
#: engine suite into the process just to get a dict.
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


def _player_source(axis: str) -> str:
    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=10)
    )
    assert axis_for_spec(spec) == axis, f"the prompt no longer selects {axis}"
    return deterministic_gameplay_scripts(spec)[PLAYER_SCRIPT]


def _axis_actions(axis: str) -> set[str]:
    """What the emitted controller reads, minus the movement plan's own keys."""

    return set(referenced_input_actions(_player_source(axis))) - set(BASE_INPUT_ACTIONS)


def test_every_declared_axis_has_a_bot():
    missing = sorted(set(AXIS_TEMPLATES) - set(BOT_POLICIES))
    assert not missing, (
        f"{missing} declared by AXIS_TEMPLATES but no bot knows how to play them: "
        "the playtest would walk them and call it measured"
    )


@pytest.mark.parametrize("axis", ALL_AXES)
def test_the_bot_presses_exactly_the_verbs_the_controller_reads(axis):
    """Equality, not containment, in both directions.

    ``⊆`` alone lets a verb be unpressable (the original bug). ``⊇`` alone lets
    the bot press dead keys. Equality is the only version where the two halves
    of "the mechanic exists" -- the code reads it and the bot presses it -- are
    forced to be the same set.
    """

    read = _axis_actions(axis)
    assert read, f"{axis}'s controller reads no axis action at all; the prompt or the axis rotted"
    # The commit verb is subtracted on purpose and only through the table, so
    # "the bot does not press it" is a decision with a reason next door rather
    # than a gap in the comparison. Any *other* unpressable verb still fails.
    gate = COMMIT_VERBS.get(axis)
    pressed_on_purpose = {gate.action} if gate else set()
    policy = policy_for(axis)
    unpressed = sorted(read - pressed_on_purpose - policy.actions)
    assert not unpressed, (
        f"the {axis} controller reads {unpressed} and the bot never presses "
        f"them: the playtest would report on a mechanic it did not touch"
    )
    unread = sorted(policy.actions - read)
    assert not unread, (
        f"the {axis} bot presses {unread}, which its controller never reads: "
        "a press nobody reads looks identical to a working verb in the report"
    )


@pytest.mark.parametrize("axis", sorted(COMMIT_VERBS))
def test_the_commit_verb_is_never_part_of_the_running_policy(axis):
    """The verb that ends the run is recorded, not pressed.

    Pressing it inside a win-rate measurement is a deliberate failure, and a
    deliberate failure is indistinguishable from a broken build in the report.
    ``test_gdscript_godot_check`` presses it once, in an experiment whose
    expected outcome is written down next door.
    """

    gate = COMMIT_VERBS[axis]
    assert axis in AXIS_TEMPLATES, f"{axis} is not an axis"
    assert gate.action in _axis_actions(axis), (
        f"{gate.action} is not read by the {axis} controller, so the gate this "
        "table pins does not exist"
    )
    assert gate.action not in policy_for(axis).actions, (
        f"the {axis} policy presses its commit verb {gate.action}"
    )
    assert gate.at_spawn in {"win", "fail"}, gate.at_spawn
    assert len(gate.why) >= 40, (
        f"the {axis} commit entry does not explain itself: {gate.why!r}"
    )


def test_the_generic_policy_presses_nothing_of_its_own():
    """No declared axis means walking and nothing else -- and saying so.

    This is the shape every playtest had before the table existed, kept as the
    honest fallback for greyboxes and for projects generated before the axis was
    recorded. The report flags it (``axis_undeclared``); nothing infers a policy
    from the project's shape, because an inferred policy is one nobody wrote.
    """

    assert GENERIC_POLICY.hold == ()
    assert GENERIC_POLICY.taps == ()
    assert policy_for("") is GENERIC_POLICY
    assert policy_for("no-such-axis") is GENERIC_POLICY


def test_the_movement_keys_are_the_generators_own():
    """The one duplicated literal, tied back to its owner."""

    assert MOVE_ACTION in BASE_INPUT_ACTIONS
    assert JUMP_ACTION in BASE_INPUT_ACTIONS


def test_the_rendered_block_carries_the_axis_and_its_keys():
    rendered = render_drive_gd(policy_for("combat"), input_plan="forward_and_jump")

    assert 'const AXIS := "combat"' in rendered
    # Movement and the axis's own held key are separate lists: the verb must
    # survive a run that is told not to walk, or "does the mechanic work on its
    # own" is a question this bot cannot ask.
    assert 'const POLICY_HOLD := ["move_forward"]' in rendered
    assert 'const POLICY_AXIS_HOLD := []' in rendered
    assert '["attack", 24, 4, 0]' in rendered
    assert 'const POLICY_MOVE_TAP := [["jump", 90, 6, 0]]' in rendered
    assert "__DRIVE__" not in rendered
    # The commit verb is deliberately absent: the policy never presses it.
    assert "COMMIT_ACTION" not in rendered


def test_a_held_verb_is_not_the_way_the_bot_travels():
    rendered = render_drive_gd(policy_for("parkour"), input_plan="idle")

    assert "const POLICY_HOLD := []" in rendered
    assert 'const POLICY_AXIS_HOLD := ["sprint"]' in rendered


def test_a_still_run_keeps_the_verbs_and_drops_the_walking():
    """``idle`` is "measure the mechanic without walking", not "press nothing"."""

    rendered = render_drive_gd(policy_for("puzzle"), input_plan="idle")

    assert "const POLICY_HOLD := []" in rendered
    assert "const POLICY_MOVE_TAP := []" in rendered
    assert '["observe", 30, 12, 0]' in rendered


def test_every_tap_starts_inside_the_frame_budget_it_is_measured_in():
    """A tap that first fires past the budget is a tap that never fires.

    Measured on the generated slices: a run ends when the player reaches the
    exit or dies, in roughly 150 engine frames. A verb scheduled at frame 600
    would be pressed in no run at all -- and the policy would still read as
    complete, because "scheduled" and "delivered" are different words. The
    engine test caught exactly that on the career axis (``compose`` at 120,
    ``support`` at 240, a 120-frame window) before this bound was right.
    """

    for axis, policy in BOT_POLICIES.items():
        for tap in policy.taps:
            assert tap.start < VERB_WINDOW_FRAMES, (
                f"{axis}/{tap.action} starts at frame {tap.start}, past the "
                f"{VERB_WINDOW_FRAMES}-frame window it is measured in"
            )
            assert tap.period >= 0, f"{axis}/{tap.action}: {tap.period}"
            if tap.period:
                assert tap.width < tap.period, (
                    f"{axis}/{tap.action} is held for {tap.width} of every "
                    f"{tap.period} frames, so it is a hold, not a tap"
                )
