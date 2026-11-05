from __future__ import annotations

import re

import pytest

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.generation import design_from_prompt_deterministic


@pytest.mark.parametrize(
    ("prompt", "expected_title"),
    [
        ("rooftop parkour chase across neon towers", "屋顶跑酷追逐"),
        ("horror stealth in an abandoned hospital", "医院潜行"),
        ("a portal puzzle dungeon full of logic switches", "地牢解谜"),
    ],
    ids=["parkour", "stealth", "puzzle"],
)
def test_english_ideas_get_chinese_display_titles_without_changing_identifiers(
    prompt: str, expected_title: str
):
    spec = design_from_prompt_deterministic(PromptRequest(prompt=prompt))

    assert spec.i18n is not None
    assert spec.i18n.field_translations["title"]["zh-CN"] == expected_title
    assert spec.i18n.field_translations["title"]["en"] == spec.title
    assert re.search(r"[A-Za-z]", spec.title)
    assert not re.search(r"[A-Za-z]", spec.i18n.field_translations["logline"]["zh-CN"])


def test_chinese_ideas_keep_their_original_display_title():
    spec = design_from_prompt_deterministic(PromptRequest(prompt="屋顶跑酷，逃离追兵"))
    assert spec.i18n is not None
    assert spec.i18n.field_translations["title"]["zh-CN"] == spec.title


def test_an_unrecognized_english_idea_still_gets_a_chinese_display_title():
    spec = design_from_prompt_deterministic(PromptRequest(prompt="an unusual abstract game"))
    assert spec.i18n is not None
    assert spec.i18n.field_translations["title"]["zh-CN"] == "互动原型"


def test_a_proper_name_is_not_discarded_when_the_idea_mentions_a_known_mechanic():
    spec = design_from_prompt_deterministic(PromptRequest(prompt="Aurelia combat"))
    assert spec.i18n is not None
    assert spec.i18n.field_translations["title"]["zh-CN"] == "Aurelia Combat"
