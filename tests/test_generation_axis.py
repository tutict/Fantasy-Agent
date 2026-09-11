"""Guards for the per-axis design templates.

These tests exist because the axis templates were, for a long time, only
implemented for two of the eight axes. Every other axis silently fell through
to one generic loop / system set / beat list, so a horror-stealth prompt and a
cozy-farming prompt produced identical level beats.

The guards below are deliberately structural: they fail when a *new* template is
copy-pasted without editing it, or when an axis becomes unreachable from
``_detect_axis`` — both of which are invisible in a happy-path test.
"""

from __future__ import annotations

import pytest

from fantasy_agent.axis_templates import AXIS_TEMPLATES
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.generation import _detect_axis, design_from_prompt_deterministic

ALL_AXES = sorted(AXIS_TEMPLATES)


# ── reachability ─────────────────────────────────────────────────────────────

# One prompt per axis. These are the acceptance evidence: if an axis cannot be
# reached by a plain prompt, its template is dead weight.
PROMPT_FOR_AXIS = {
    "parkour": "rooftop parkour chase across neon towers",
    "career": "a game design applicant portfolio about a career pivot",
    "stealth": "horror stealth in an abandoned hospital",
    "combat": "tactical squad combat with a cover system and a boss",
    "survival": "survival storm on a frozen island with hunger",
    "puzzle": "a portal puzzle dungeon full of logic switches",
    # Deliberately free of "speed" / "chase" so this pins "racing" itself: the
    # substring "race" does not appear in "racing", which is exactly how the
    # mobility axis used to be unreachable by its own most common word.
    "mobility": "a racing game through underwater caves",
    "systems": "a cozy farming sim about growing magical pumpkins",
}


def test_every_template_axis_is_reachable_from_a_prompt():
    """A template no prompt can trigger is dead code that still has to be
    reviewed and kept alive."""

    for axis, prompt in PROMPT_FOR_AXIS.items():
        assert _detect_axis(prompt) == axis, f"{axis} is unreachable"


def test_every_detectable_axis_has_a_template():
    """The reverse direction: no axis should fall through to a KeyError."""

    reachable = {_detect_axis(prompt) for prompt in PROMPT_FOR_AXIS.values()}
    assert reachable == set(AXIS_TEMPLATES)


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_axis_produces_a_complete_spec(axis):
    for minutes in (5, 10, 15):
        spec = design_from_prompt_deterministic(
            PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=minutes)
        )
        assert spec.level_beats, f"{axis} produced no beats"
        assert spec.systems, f"{axis} produced no systems"
        assert len(spec.core_loop) == 4, f"{axis} loop drifted from four steps"
        assert spec.win_state
        assert len(spec.failure_states) == 3
        total = sum(beat.duration_minutes for beat in spec.level_beats)
        assert total == minutes, f"{axis} beats sum to {total}, not {minutes}"


# ── no two axes share content ────────────────────────────────────────────────


def test_no_two_axes_share_a_beat_name():
    """The original bug: stealth and farming both emitted "Onboarding Pocket".
    Beat names are the most visible output, so they are the tripwire."""

    owners: dict[str, str] = {}
    for axis, template in AXIS_TEMPLATES.items():
        for beat in template.beats:
            assert beat.name not in owners, (
                f"{axis} reuses beat {beat.name!r} from {owners[beat.name]}"
            )
            owners[beat.name] = axis


def test_no_two_axes_share_a_system_name():
    owners: dict[str, str] = {}
    for axis, template in AXIS_TEMPLATES.items():
        for system in template.systems:
            assert system.name not in owners, (
                f"{axis} reuses system {system.name!r} from {owners[system.name]}"
            )
            owners[system.name] = axis


def test_no_two_axes_share_a_verb_set():
    seen: dict[tuple[str, ...], str] = {}
    for axis, template in AXIS_TEMPLATES.items():
        key = tuple(template.verbs)
        assert key not in seen, f"{axis} shares verbs with {seen[key]}"
        seen[key] = axis


def test_different_axes_produce_different_beats():
    """End-to-end version of the tripwire, through the real generator."""

    by_axis = {
        axis: [
            beat.name
            for beat in design_from_prompt_deterministic(
                PromptRequest(prompt=prompt, target_minutes=10)
            ).level_beats
        ]
        for axis, prompt in PROMPT_FOR_AXIS.items()
    }
    distinct = {tuple(names) for names in by_axis.values()}
    assert len(distinct) == len(by_axis), "two axes produced identical beats"


# ── template self-consistency ────────────────────────────────────────────────


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_template_has_three_beats(axis):
    """``_level_beats_for_axis`` maps beats onto three durations positionally,
    so a template with a different count would silently drop or crash."""

    assert len(AXIS_TEMPLATES[axis].beats) == 3


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_template_has_four_loop_steps_and_three_systems(axis):
    template = AXIS_TEMPLATES[axis]
    assert len(template.loop) == 4
    assert len(template.systems) == 3
    assert len(template.verbs) == 4
    assert len(template.progression.unlocks) == 3
    assert len(template.narrative.design_pillars) == 4
    assert len(template.narrative.failure_states) == 3


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_template_translates_every_asset_and_note(axis):
    """A missing translation silently leaks English into a Chinese GDD."""

    template = AXIS_TEMPLATES[axis]
    assert len(template.zh_assets) == len(template.assets)
    narrative = template.narrative
    assert len(narrative.zh_notes_for_comfyui) == len(narrative.notes_for_comfyui)
    assert len(narrative.zh_pillars) == len(narrative.design_pillars)
    assert len(narrative.zh_failure_states) == len(narrative.failure_states)
    assert len(template.progression.zh_unlocks) == len(template.progression.unlocks)


@pytest.mark.parametrize("axis", ALL_AXES)
def test_no_verb_placeholder_survives_into_the_output(axis):
    """The generic axis writes "{verb_0}" and expects it to be substituted."""

    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS[axis], target_minutes=10)
    )
    for step in spec.core_loop:
        assert "{" not in step.action, f"{axis} leaked a placeholder: {step.action}"


# ── the zh-CN copy actually reaches the bundle ───────────────────────────────


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_axis_translates_its_beat_names(axis):
    """Before the templates carried Chinese, every non-career axis shipped the
    same generic beat names ("教学口袋区") regardless of the design."""

    spec = design_from_prompt_deterministic(
        PromptRequest(
            prompt=PROMPT_FOR_AXIS[axis], target_minutes=10, output_locales=["zh-CN"]
        )
    )
    bundle = spec.i18n
    assert bundle is not None
    for index, beat in enumerate(spec.level_beats):
        entry = bundle.field_translations.get(f"level_beats.{index}.name")
        assert entry is not None, f"{axis} beat {index} has no translation"
        zh = entry.get("zh-CN")
        assert zh, f"{axis} beat {index} has an empty translation"
        assert zh != beat.name, f"{axis} beat {index} was not translated"


def test_chinese_beat_names_differ_between_axes():
    """The Chinese GDD must tell the two designs apart too — otherwise the
    English specialisation is invisible to the audience the docs target."""

    names = set()
    for prompt in PROMPT_FOR_AXIS.values():
        spec = design_from_prompt_deterministic(
            PromptRequest(prompt=prompt, target_minutes=10, output_locales=["zh-CN"])
        )
        assert spec.i18n is not None
        translated = tuple(
            spec.i18n.field_translations[f"level_beats.{i}.name"]["zh-CN"]
            for i in range(len(spec.level_beats))
        )
        names.add(translated)
    assert len(names) == len(PROMPT_FOR_AXIS), "two axes share Chinese beat names"


def test_asset_needs_are_translated_per_axis():
    """Previously the only translated asset list was the career one, so a
    stealth design was documented with generic arena props."""

    for axis, prompt in PROMPT_FOR_AXIS.items():
        spec = design_from_prompt_deterministic(
            PromptRequest(prompt=prompt, target_minutes=10, output_locales=["zh-CN"])
        )
        assert spec.i18n is not None
        for index, asset in enumerate(spec.asset_needs):
            entry = spec.i18n.field_translations.get(f"asset_needs.{index}")
            assert entry is not None, f"{axis} asset {index} untranslated"
            assert entry["zh-CN"] != asset, f"{axis} asset {asset!r} not translated"


# ── parkour and career must not have moved ───────────────────────────────────


def test_parkour_keeps_its_established_system_names():
    """Two workflow tests assert on these; moving them is a breaking change."""

    spec = design_from_prompt_deterministic(
        PromptRequest(prompt=PROMPT_FOR_AXIS["parkour"], target_minutes=10)
    )
    assert "Momentum Chain" in {system.name for system in spec.systems}
    assert [beat.name for beat in spec.level_beats] == [
        "Warmup Rooftop",
        "Momentum Mix",
        "Extraction Sprint",
    ]


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_beat_asset_is_translated(axis):
    """Beat asset names go straight into the Chinese GDD; an untranslated term
    shows up as raw English in the middle of a Chinese sentence."""

    spec = design_from_prompt_deterministic(
        PromptRequest(
            prompt=PROMPT_FOR_AXIS[axis], target_minutes=10, output_locales=["zh-CN"]
        )
    )
    assert spec.i18n is not None
    for beat_index, beat in enumerate(spec.level_beats):
        for asset_index, asset in enumerate(beat.required_assets):
            path = f"level_beats.{beat_index}.required_assets.{asset_index}"
            entry = spec.i18n.field_translations.get(path)
            assert entry is not None, f"{axis}: {path} missing"
            assert entry["zh-CN"] != asset, f"{axis}: {asset!r} not translated"


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("racing", "mobility"),
        ("racer", "mobility"),
        ("speed", "mobility"),
        ("race", "mobility"),
        ("竞速", "mobility"),
        ("stealth", "stealth"),
        ("潜行", "stealth"),
        ("puzzle", "puzzle"),
        ("combat", "combat"),
        ("survival", "survival"),
        ("parkour", "parkour"),
    ],
)
def test_single_keywords_route_to_their_axis(prompt, expected):
    """A single obvious keyword must be enough.

    "racing" does not contain the substring "race", so a keyword list holding
    only "race" silently makes the whole axis unreachable by normal English.
    """

    assert _detect_axis(prompt) == expected


@pytest.mark.parametrize("axis", ALL_AXES)
def test_every_system_term_is_translated(axis):
    """System inputs / outputs are a shared glossary, not per-axis copy; an
    untranslated term shows up as raw English inside a Chinese sentence."""

    spec = design_from_prompt_deterministic(
        PromptRequest(
            prompt=PROMPT_FOR_AXIS[axis], target_minutes=10, output_locales=["zh-CN"]
        )
    )
    assert spec.i18n is not None
    for index, system in enumerate(spec.systems):
        for kind, values in (("inputs", system.inputs), ("outputs", system.outputs)):
            for term_index, term in enumerate(values):
                path = f"systems.{index}.{kind}.{term_index}"
                entry = spec.i18n.field_translations.get(path)
                assert entry is not None, f"{axis}: {path} missing"
                assert entry["zh-CN"] != term, f"{axis}: {term!r} not translated"
