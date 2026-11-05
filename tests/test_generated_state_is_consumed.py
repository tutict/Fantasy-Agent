"""No generated script may carry state it never consumes.

The defect this file exists for has one shape in two places. ``max_hp`` was
declared, exported, and — through the ``# [PLAYER_HP]`` anchor — rewritable by
the tuning table, and then read by nothing: the spec's first failure state said
"health reaches zero" while the generated project had no health. ``_stamina``
was worse, because it looked alive: it was declared, accumulated every frame,
and consumed by nothing, so a spec promising a stamina economy shipped a build
with no stamina in it.

Declaring the variable is the cheap half. These tests ask whether anything reads
it, and where the answer is no, whether somebody wrote down why.
"""

from __future__ import annotations

import json
import re

import pytest

from fantasy_agent.axis_templates import AXIS_TEMPLATES
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.gameplay_codegen import (
    _AXIS_MECHANICS,
    UNIMPLEMENTED_MECHANICS,
    _boundary_failure,
    deterministic_gameplay_scripts,
)
from fantasy_agent.generation import design_from_prompt_deterministic

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
ALL_AXES = list(PROMPT_FOR_AXIS)

ENEMY = "scripts/enemy_controller.gd"
PLAYER = "scripts/player_controller.gd"
MANAGER = "scripts/game_manager.gd"

_DECL = re.compile(r"^\s*(?:@export\s+)?var\s+([A-Za-z_]\w*)\s*(?::\s*[^=]+?)?\s*:?=")
_EXPORT = re.compile(r"^\s*@export\s+var\s+([A-Za-z_]\w*)")


def _scripts(axis: str) -> dict[str, str]:
    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=10)
    )
    return deterministic_gameplay_scripts(spec)


def _declaration_lines(source: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for index, line in enumerate(source.splitlines()):
        match = _DECL.match(line)
        if match:
            found.setdefault(match.group(1), index)
    return found


def _is_read(source: str, name: str) -> bool:
    """True when some line uses ``name`` for something other than assigning it.

    A self-feeding write — ``_stamina = minf(1.0, _stamina + rate * delta)`` —
    therefore does **not** count: the value never leaves its own assignment,
    which is exactly the shape that made a dead stamina bar look alive.
    """

    escaped = re.escape(name)
    word = re.compile(rf"\b{escaped}\b")
    write = re.compile(rf"^\s*{escaped}\s*(?:[+\-*/]=|:=|=)")
    declaration = _declaration_lines(source).get(name)
    for index, line in enumerate(source.splitlines()):
        if index == declaration or not word.search(line):
            continue
        if not write.match(line):
            return True
    return False


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_export_is_read(axis):
    """An exported knob is one the correction path can rewrite.

    ``corrections.py`` finds these by their ``# [ANCHOR]`` marker and reports
    changed values back to the operator. If nothing reads the value, applying
    the correction is a no-op that looks exactly like a success.
    """

    for name, source in sorted(_scripts(axis).items()):
        for index, line in enumerate(source.splitlines()):
            match = _EXPORT.match(line)
            if match and not _is_read(source, match.group(1)):
                pytest.fail(
                    f"{axis}/{name}: `{match.group(1)}` is exported (line {index + 1}) "
                    "and read by nothing, so tuning it changes no behaviour"
                )


@pytest.mark.parametrize("axis", ALL_AXES)
def test_axis_mechanic_state_is_read_or_written_down(axis):
    """Every declared mechanic variable is consumed, or has a reason it is not.

    The comparison is against :data:`UNIMPLEMENTED_MECHANICS` rather than a
    threshold, so the failure message names the variable and the two ways out
    are both explicit: read it, or explain it.
    """

    source = _scripts(axis)[PLAYER]
    declared = re.findall(r"^\s*var\s+([A-Za-z_]\w*)", _AXIS_MECHANICS[axis].state, re.MULTILINE)
    dead = {name for name in declared if not _is_read(source, name)}
    documented = set(UNIMPLEMENTED_MECHANICS.get(axis, {}))
    assert dead == documented, (
        f"{axis}: unread mechanic state {sorted(dead)} but the decision table "
        f"says {sorted(documented)}. Either read the variable, or add/remove "
        "its entry in UNIMPLEMENTED_MECHANICS with a reason."
    )


def test_the_decision_table_answers_for_every_axis_and_explains_itself():
    assert set(UNIMPLEMENTED_MECHANICS) == set(AXIS_TEMPLATES), (
        "every axis must be answered for, including the ones with nothing "
        "deferred -- an absent key reads as 'not considered'"
    )
    for axis, entries in UNIMPLEMENTED_MECHANICS.items():
        declared = set(
            re.findall(r"^\s*var\s+([A-Za-z_]\w*)", _AXIS_MECHANICS[axis].state, re.MULTILINE)
        )
        for name, reason in entries.items():
            assert name in declared, f"{axis}: {name} is not declared by its mechanics block"
            assert len(reason.strip()) > 30, (
                f"{axis}/{name}: the reason has to say what is missing, not that "
                f"something is: {reason!r}"
            )


def test_combat_spends_stamina_and_reads_the_brace_flag():
    """The concrete case, pinned by name.

    The generic test above is satisfied by adding a line to the decision table;
    this one is satisfied only by the stamina economy doing something.
    """

    source = _scripts("combat")[PLAYER]
    assert "_stamina >= evade_cost" in source, "the dodge is not paid for out of stamina"
    assert "_stamina -= evade_cost" in source, "nothing spends stamina"
    assert "brace_recover_multiplier if _bracing else" in source, (
        "bracing still only writes its flag; the brace verb buys nothing"
    )
    assert UNIMPLEMENTED_MECHANICS["combat"] == {}, (
        "combat's mechanics are implemented now, so its deferral list must be empty"
    )


@pytest.mark.parametrize("axis", ALL_AXES)
def test_failure_states_the_build_cannot_reach_are_declared(axis):
    """A spec's failure list is a promise; the build can only keep some of it.

    ``game_manager.gd`` has exactly two failure paths: the clock (and, since
    health became real, a spent health bar) reports the spec's *first* failure
    state, and falling off reports the spec's own boundary wording when it wrote
    one. Everything else goes into ``UNREPORTABLE_FAILURES`` and is printed on
    start, so the gap lands in the log instead of in an assumption.
    """

    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=10)
    )
    manager = _scripts(axis)[MANAGER]
    match = re.search(r"const UNREPORTABLE_FAILURES := (\[[^\]]*\])", manager)
    assert match, "the manager does not declare which failure states it cannot report"
    declared = json.loads(match.group(1))

    assert set(declared) <= set(spec.failure_states), (
        f"{axis}: UNREPORTABLE_FAILURES names text the spec never declared: {declared}"
    )
    boundary = _boundary_failure(list(spec.failure_states), "Left the active route")
    expected = [text for text in spec.failure_states if text in {spec.failure_states[0], boundary}]
    reportable = [text for text in spec.failure_states if text not in declared]
    assert reportable == expected, (
        f"{axis}: the build reports {reportable} but has code paths for "
        f"{expected} (first failure state, plus the boundary wording)"
    )
    assert "UNREPORTABLE_FAILURES.is_empty()" in manager, (
        "nothing reads the declaration, so it is a comment with a type"
    )


def test_the_combat_slice_cannot_report_two_of_its_three_failures():
    """Pinned on the axis that motivated the ledger.

    This is the honest version of the old build's claim: it listed a stagger
    break, a stamina exhaustion and a range trap, and could produce one of them.
    Deleting this pin is fine -- implementing the paths and updating the ledger
    is how it should die.
    """

    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS["combat"], target_minutes=10)
    )
    manager = _scripts("combat")[MANAGER]
    declared = json.loads(
        re.search(r"const UNREPORTABLE_FAILURES := (\[[^\]]*\])", manager).group(1)
    )
    assert declared == [
        "Stamina exhaustion leaves no answer to the boss tell",
        "Both attackers reach punish range and the arena becomes unrecoverable",
    ], declared
    assert spec.failure_states[0] not in declared
