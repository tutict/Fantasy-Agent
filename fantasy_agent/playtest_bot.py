"""Which keys a headless bot is allowed to press, per mechanic axis.

The playtest used to ship one input plan -- hold ``move_forward``, tap ``jump``
-- and apply it to every axis. That is enough to prove the route can be walked,
and it is why the report could call a combat slice "playable" while nobody had
ever pressed ``attack``: the verbs the design is *about* were never exercised, so
a build where they do nothing and a build where they work produced the same
green report.

This module is the missing half of the playtest: one policy per axis, written
against the actions that axis's generated controller actually reads
(``gameplay_codegen._AXIS_MECHANICS``), and enumerated rather than inferred so a
new axis without a policy is a test failure instead of a bot that quietly walks.

Three rules shape the table, each one a way the previous design went wrong:

1. **The policy presses exactly what the controller reads** -- no more, no less.
   Pressing a verb nothing reads is a green light from a dead key; *not*
   pressing a verb the controller reads is the original bug. The parity test
   computes the read set from the emitted GDScript and compares it with this
   table, so neither side can drift alone.

2. **The movement plan stays separate.** ``input_plan`` owns ``move_forward``
   and ``jump``; this table owns only the axis's own verbs. A playtest that
   wants to measure the mechanic without walking can say ``input_plan="idle"``
   and still press every verb.

3. **Verbs that end the run on purpose are not pressed here.** ``solve``,
   ``extract`` and ``complete`` are the axis's *commit* verb: pressing one before
   the loop has produced its resource is a failure by design, and a production
   run that fails on purpose cannot be told apart from a broken build. They are
   pinned here as data (``COMMIT_VERBS``) with what they do on the first frame,
   and the engine test presses them in a dedicated probe.
"""

from __future__ import annotations

from dataclasses import dataclass

from fantasy_agent.axis_templates import AXIS_TEMPLATES

#: The movement plan's own action. Duplicated from
#: ``gameplay_codegen.BASE_INPUT_ACTIONS`` because importing that module here
#: closes an import cycle (``gameplay_codegen`` -> ``godot_mcp`` ->
#: ``godot_playtest`` -> this module); ``tests/test_playtest_bot.py`` asserts the
#: two agree, so the copy cannot rot in silence.
MOVE_ACTION = "move_forward"
JUMP_ACTION = "jump"

#: How long the engine test drives one policy before asking what was pressed.
#: Every verb has to fire inside it: a tap scheduled later than this is a tap
#: that is *listed* and never *delivered*, and the two read identically in a
#: table. Must match the ``range`` in ``test_gdscript_godot_check._axis_verbs``,
#: which is also where a mismatch shows up as red rather than as a footnote.
VERB_WINDOW_FRAMES = 120


@dataclass(frozen=True)
class Tap:
    """One key the bot presses on a cadence, never released for free.

    ``period`` frames between presses, ``width`` frames held, starting
    ``start`` frames into the run. ``period == 0`` means "once, at ``start``".
    Frames, not seconds: the probe counts engine frames, and a headless run
    advances them far faster than wall clock.
    """

    action: str
    period: int
    width: int
    start: int = 0


@dataclass(frozen=True)
class BotPolicy:
    """What one axis's bot does, and why that is the axis's loop."""

    axis: str
    intent: str
    #: Held for the whole run. Empty means the policy adds no held key.
    hold: tuple[str, ...] = ()
    #: Pressed on a cadence.
    taps: tuple[Tap, ...] = ()
    #: Observables this axis's verbs are expected to move, and that the suite
    #: therefore asserts on. Empty means "pressed, not priced": the slice has no
    #: number for that verb yet, and inventing one here would be a verdict with
    #: no measurement behind it.
    priced: tuple[str, ...] = ()

    @property
    def actions(self) -> frozenset[str]:
        """Every axis action this policy presses."""

        return frozenset({*self.hold, *(tap.action for tap in self.taps)})


@dataclass(frozen=True)
class CommitGate:
    """The axis verb that ends the run, and what it does before any work."""

    action: str
    #: ``last_outcome`` the verb produces on the first frame of a fresh run.
    #: Not a wish: the engine test measures it and fails if this changes, which
    #: is how a gap gets closed on purpose instead of by accident.
    at_spawn: str
    why: str


#: One policy per axis, each pressed against the read set the emitted controller
#: has (see the module docstring). Ordered by the axis's own loop, not by the
#: alphabet: the first verb is the one the loop is built on.
BOT_POLICIES: dict[str, BotPolicy] = {
    "parkour": BotPolicy(
        axis="parkour",
        intent="keep momentum: sprint held, vault and slide on the run cadence",
        hold=("sprint",),
        taps=(Tap("vault", 45, 4), Tap("slide", 90, 6)),
    ),
    "stealth": BotPolicy(
        axis="stealth",
        intent="alternate quiet and loud frames, scan, and spend a decoy",
        taps=(Tap("scout", 40, 4), Tap("hide", 240, 120), Tap("distract", 150, 3)),
    ),
    "combat": BotPolicy(
        axis="combat",
        intent="attack on reach cooldown, evade for position, brace and recover",
        taps=(
            Tap("attack", 24, 4),
            Tap("evade", 60, 3, start=10),
            Tap("position", 300, 60),
            Tap("recover", 240, 90, start=60),
        ),
        # The two verbs whose effect the slice can actually measure: a strike
        # inside reach must cost an enemy a point of health, and an evade must
        # cost the player stamina. Both are asserted in the engine test, which
        # is why "the bot presses attack" is not the end of the story.
        priced=("enemy_hp_lost", "stamina_spent"),
    ),
    "survival": BotPolicy(
        axis="survival",
        intent="travel fast, shelter under pressure, gather when stopped, craft warmth",
        taps=(
            Tap("gather", 120, 60),
            Tap("endure", 300, 90, start=30),
            Tap("craft", 200, 4),
            Tap("route", 400, 120),
        ),
    ),
    "puzzle": BotPolicy(
        axis="puzzle",
        intent="scan for fragments, combine them into keys, fire the device",
        taps=(Tap("observe", 30, 12), Tap("combine", 120, 4, start=60), Tap("trigger", 90, 4)),
    ),
    "mobility": BotPolicy(
        axis="mobility",
        intent="spend boost, burst on the dash cooldown, run hot between them",
        taps=(Tap("boost", 120, 90), Tap("dash", 90, 4), Tap("risk", 300, 120)),
    ),
    "career": BotPolicy(
        axis="career",
        intent="study options, commit, compose a portfolio piece, support the run",
        taps=(
            Tap("discern", 60, 40),
            Tap("choose", 150, 4, start=30),
            Tap("compose", 300, 4, start=60),
            Tap("support", 400, 4, start=90),
        ),
    ),
    "systems": BotPolicy(
        axis="systems",
        intent="engage nodes, cycle the response mode",
        taps=(Tap("interact", 120, 4), Tap("adapt", 300, 4)),
    ),
}

#: What the bot does when the project does not declare an axis (a greybox, or a
#: project generated before the axis was written down). Walks and nothing else,
#: which is exactly what every playtest used to do -- so the report can say so
#: out loud instead of implying the verbs were exercised.
GENERIC_POLICY = BotPolicy(
    axis="generic",
    intent="no axis declared: walk the route and press nothing else",
)

#: The commit verb of each axis that has one, with what it does on frame zero.
COMMIT_VERBS: dict[str, CommitGate] = {
    "stealth": CommitGate(
        action="extract",
        at_spawn="win",
        why=(
            "noise starts at 0.0 and the gate is 'noise <= extract_noise_limit', "
            "so the exit is open on the first frame. The run still travels "
            "because the exit trigger is the other way to win, not because the "
            "gate holds."
        ),
    ),
    "puzzle": CommitGate(
        action="solve",
        at_spawn="fail",
        why="no keys held yet, so the commit is refused and the run ends on the spec's refusal text",
    ),
    "systems": CommitGate(
        action="complete",
        at_spawn="fail",
        why="no nodes engaged yet, so closing the loop is refused and the run ends",
    ),
}


def policy_for(axis: str) -> BotPolicy:
    """The bot for ``axis``, falling back to walking only."""

    return BOT_POLICIES.get(axis, GENERIC_POLICY)


def missing_policies() -> list[str]:
    """Axes the design declares that no bot knows how to play."""

    return sorted(set(AXIS_TEMPLATES) - set(BOT_POLICIES))


def _gd_taps(taps: tuple[Tap, ...]) -> str:
    return "[" + ", ".join(
        f'["{tap.action}", {tap.period}, {tap.width}, {tap.start}]' for tap in taps
    ) + "]"


def render_drive_gd(policy: BotPolicy, *, input_plan: str) -> str:
    """The GDScript that turns ``policy`` into key presses.

    Rendered once and spliced into both hosts -- the playtest probe and the
    engine test harness. Two copies of this loop would be two chances for the
    thing under test and the thing doing the testing to disagree, and the
    failure mode of that disagreement is silence: the bot presses nothing and
    every assertion about what it pressed passes on zero.

    ``input_plan`` owns movement and nothing else. ``idle`` drops the held
    direction, which is how a caller asks "does the mechanic work while standing
    still"; the axis taps and the axis's own held key fire either way -- a
    parkour bot that is told not to walk still sprints, because sprint is the
    verb under test, not the way it travels.
    """

    holds = [] if input_plan == "idle" else [MOVE_ACTION]
    move_taps = (Tap(JUMP_ACTION, 90, 6),) if input_plan == "forward_and_jump" else ()
    return f'''# ── axis bot ─────────────────────────────────────────────────────────────
# Rendered from fantasy_agent.playtest_bot.BOT_POLICIES; edit the table there.
# AXIS names the mechanic family this project was generated for, and every key
# below is one that family's own controller reads (parity is a test, not a hope).
const AXIS := "{policy.axis}"
const POLICY_HOLD := [{", ".join(f'"{action}"' for action in holds)}]
const POLICY_AXIS_HOLD := [{", ".join(f'"{action}"' for action in policy.hold)}]
const POLICY_MOVE_TAP := {_gd_taps(move_taps)}
const POLICY_TAP := {_gd_taps(policy.taps)}

var _taps: Dictionary = {{}}
var _held: Array = []
var _policy_missing: Array = []


func _policy_action_ok(action: String) -> bool:
\t# Reported, not swallowed. An action the project never declared cannot be
\t# pressed -- Godot prints an error per frame -- but a bot that silently skips
\t# it turns "this build cannot play its own axis" into a clean green report.
\tif InputMap.has_action(action):
\t\treturn true
\tif not _policy_missing.has(action):
\t\t_policy_missing.append(action)
\treturn false


func _policy_press(action: String) -> void:
\tInput.action_press(action)
\t_taps[action] = int(_taps.get(action, 0)) + 1


func _policy_hold(action: String) -> void:
\tif not _policy_action_ok(action):
\t\treturn
\t# A held input can survive a scene reload; record it for this run too.
\tif not _held.has(action):
\t\t_held.append(action)
\tif Input.is_action_pressed(action):
\t\treturn
\tInput.action_press(action)


func _policy_tap_entry(entry: Array, run_frames: int) -> void:
\tvar action := str(entry[0])
\tvar period := int(entry[1])
\tvar width := int(entry[2])
\tvar start := int(entry[3])
\tif run_frames < start:
\t\treturn
\tvar phase := run_frames - start
\tif period <= 0:
\t\tif phase == 0:
\t\t\tif _policy_action_ok(action):
\t\t\t\t_policy_press(action)
\t\telif phase == width:
\t\t\tInput.action_release(action)
\telif phase % period == 0:
\t\tif _policy_action_ok(action):
\t\t\t_policy_press(action)
\telif phase % period == width:
\t\tInput.action_release(action)


func _policy_drive(run_frames: int, movement: bool = true) -> void:
\t# The axis's own held key is not the movement plan's: pressing it while the
\t# bot stands still is how "does this verb work on its own" gets asked.
\tfor action in POLICY_AXIS_HOLD:
\t\t_policy_hold(action)
\tif movement:
\t\tfor action in POLICY_HOLD:
\t\t\t_policy_hold(action)
\t\tfor entry in POLICY_MOVE_TAP:
\t\t\t_policy_tap_entry(entry, run_frames)
\tfor entry in POLICY_TAP:
\t\t_policy_tap_entry(entry, run_frames)
'''
