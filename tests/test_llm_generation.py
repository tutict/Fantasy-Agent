"""Tests for the optional LLM backend in gameplay generation.

Covers the three behaviors that matter:
  1. A valid LLM payload is used and validated into a GameplaySpec.
  2. Any LLM failure degrades gracefully to the deterministic generator.
  3. Importing fantasy_agent.llm never constructs an API client (regression
     guard against the previous bolt-on that crashed at import time).
"""

from __future__ import annotations

import importlib
from unittest import mock

import pytest

from fantasy_agent import llm
from fantasy_agent.contracts import GameplaySpec, PromptRequest
from fantasy_agent.generation import (
    design_from_prompt,
    design_from_prompt_deterministic,
)


def _valid_spec_payload() -> dict:
    """A schema-valid GameplaySpec dict, derived from the deterministic output."""
    request = PromptRequest(prompt="a 2D platformer where a cat collects fish")
    spec = design_from_prompt_deterministic(request)
    payload = spec.model_dump()
    payload.pop("i18n", None)  # generator re-attaches i18n itself
    payload["title"] = "LLM Cat Quest"  # marker proving the LLM path was taken
    return payload


def test_import_llm_does_not_construct_client():
    """Importing the module must not build a client or need credentials."""
    module = importlib.reload(llm)
    assert module._client is None


def test_llm_path_used_when_payload_valid():
    request = PromptRequest(prompt="a 2D platformer where a cat collects fish")

    with mock.patch.object(llm, "complete_json", return_value=_valid_spec_payload()) as mocked:
        spec = design_from_prompt(request, use_llm=True)

    mocked.assert_called_once()
    assert isinstance(spec, GameplaySpec)
    assert spec.title == "LLM Cat Quest"
    # i18n is still attached on the LLM path.
    assert spec.i18n is not None
    assert spec.i18n.output_locales == ["en", "zh-CN"]


def test_falls_back_when_llm_raises():
    request = PromptRequest(prompt="a 2D platformer where a cat collects fish")

    with mock.patch.object(llm, "complete_json", side_effect=llm.LLMError("boom")):
        spec = design_from_prompt(request, use_llm=True)

    # Should match deterministic output, and definitely not the LLM marker title.
    assert isinstance(spec, GameplaySpec)
    assert spec.title != "LLM Cat Quest"
    assert spec.title == design_from_prompt_deterministic(request).title


def test_falls_back_when_payload_invalid():
    request = PromptRequest(prompt="a 2D platformer where a cat collects fish")
    # Missing required fields -> Pydantic validation fails -> fallback.
    bad_payload = {"title": "Broken", "logline": "incomplete"}

    with mock.patch.object(llm, "complete_json", return_value=bad_payload):
        spec = design_from_prompt(request, use_llm=True)

    assert isinstance(spec, GameplaySpec)
    assert spec.title != "Broken"


def test_default_path_is_deterministic_without_env(monkeypatch):
    monkeypatch.delenv("FANTASY_AGENT_USE_LLM", raising=False)
    request = PromptRequest(prompt="a 2D platformer where a cat collects fish")

    # complete_json must not even be called on the default path.
    with mock.patch.object(llm, "complete_json", side_effect=AssertionError("must not call")):
        spec = design_from_prompt(request)

    assert spec.title == design_from_prompt_deterministic(request).title


def test_env_flag_enables_llm(monkeypatch):
    monkeypatch.setenv("FANTASY_AGENT_USE_LLM", "1")
    request = PromptRequest(prompt="a 2D platformer where a cat collects fish")

    with mock.patch.object(llm, "complete_json", return_value=_valid_spec_payload()) as mocked:
        spec = design_from_prompt(request)

    mocked.assert_called_once()
    assert spec.title == "LLM Cat Quest"


def test_complete_json_strips_code_fence():
    """The fenced-JSON cleanup should yield a parsed dict."""
    fenced = '```json\n{"a": 1}\n```'

    fake_message = mock.Mock()
    fake_message.content = [mock.Mock(text=fenced)]
    fake_client = mock.Mock()
    fake_client.messages.create.return_value = fake_message

    with mock.patch.object(llm, "get_client", return_value=fake_client):
        result = llm.complete_json(system="s", user="u")

    assert result == {"a": 1}


def test_complete_json_raises_on_non_object():
    fake_message = mock.Mock()
    fake_message.content = [mock.Mock(text="[1, 2, 3]")]
    fake_client = mock.Mock()
    fake_client.messages.create.return_value = fake_message

    with mock.patch.object(llm, "get_client", return_value=fake_client):
        with pytest.raises(llm.LLMError):
            llm.complete_json(system="s", user="u")
