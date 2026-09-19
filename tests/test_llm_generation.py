"""Tests for the optional LLM backend in gameplay generation.

Covers the three behaviors that matter:
  1. A valid LLM payload is used and validated into a GameplaySpec.
  2. Any LLM failure degrades gracefully to the deterministic generator.
  3. Importing fantasy_agent.llm never constructs an API client (regression
     guard against the previous bolt-on that crashed at import time).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest import mock
from urllib import error

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
    """Importing the module must not build a client or need credentials.

    Executed against a throwaway copy of the module rather than by reloading the
    live one. ``importlib.reload`` re-executes the module and rebinds
    ``llm.LLMError`` to a *new* class object, while ``fantasy_agent.agent_loop``
    keeps the one it bound at import time -- so after a reload, the loop's
    ``except LLMError`` silently stops catching ``llm.LLMError``, and any test
    that depends on it passes or fails according to file ordering. Reloading also
    did not make this test any stronger than it looks: a reload resets
    ``_client`` either way, so the assertion was never about the live module's
    accumulated state. Executing the source somewhere disposable proves the same
    property -- importing builds nothing -- and leaves the live module, and its
    exception classes, untouched.
    """

    probe = _load_llm_probe()

    assert probe._client is None
    assert probe is not llm


def _load_llm_probe():
    """A second, private instance of ``fantasy_agent.llm`` from the same source.

    Registered in ``sys.modules`` *before* ``exec_module``, like the tray and
    launcher probes: ``llm.py`` declares dataclasses, and the stdlib resolves
    ``cls.__module__`` through ``sys.modules.get(...)`` while decorating them. An
    unregistered module makes that lookup return ``None`` and the exec dies with
    ``AttributeError: 'NoneType' object has no attribute '__dict__'``.
    """

    module_name = "fantasy_agent_llm_import_probe"
    assert llm.__file__ is not None
    spec = importlib.util.spec_from_file_location(module_name, Path(llm.__file__))
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


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


def _anthropic_response(text: str):
    """Build a context-manager stand-in for urlopen() returning Anthropic JSON."""

    body = json.dumps({"model": "claude-test", "content": [{"type": "text", "text": text}]})
    handle = mock.MagicMock()
    handle.read.return_value = body.encode("utf-8")
    handle.__enter__.return_value = handle
    handle.__exit__.return_value = False
    return handle


@pytest.fixture
def anthropic_credentials(tmp_path, monkeypatch):
    """Point settings at a throwaway dir and enable a keyed Anthropic provider."""

    monkeypatch.setenv("FANTASY_AGENT_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FANTASY_AGENT_MODEL", raising=False)
    monkeypatch.delenv("FANTASY_AGENT_BASE_URL", raising=False)
    from fantasy_agent.api_settings import LLMApiSettings, save_settings

    save_settings(LLMApiSettings(enabled=True, api_key="sk-test-1234567890"))
    return tmp_path


def test_complete_json_strips_code_fence(anthropic_credentials):
    fenced = '```json\n{"a": 1}\n```'

    with mock.patch(
        "urllib.request.urlopen", return_value=_anthropic_response(fenced)
    ):
        result = llm.complete_json(system="s", user="u")

    assert result == {"a": 1}


def test_complete_json_raises_on_non_object(anthropic_credentials):
    with mock.patch(
        "urllib.request.urlopen", return_value=_anthropic_response("[1, 2, 3]")
    ), pytest.raises(llm.LLMError):
        llm.complete_json(system="s", user="u")


def test_complete_json_posts_to_anthropic_messages_api(anthropic_credentials):
    """The default provider must work over HTTP without the anthropic SDK."""

    with mock.patch(
        "urllib.request.urlopen", return_value=_anthropic_response('{"a": 1}')
    ) as mocked:
        result = llm.complete_json(system="sys", user="usr")

    assert result == {"a": 1}
    sent = mocked.call_args[0][0]
    assert sent.full_url == "https://api.anthropic.com/v1/messages"
    assert sent.get_header("X-api-key") == "sk-test-1234567890"
    assert sent.get_header("Anthropic-version") == "2023-06-01"
    body = json.loads(sent.data.decode("utf-8"))
    assert body["system"] == "sys"
    assert body["messages"] == [{"role": "user", "content": "usr"}]


def test_complete_json_requires_key_for_anthropic(tmp_path, monkeypatch):
    monkeypatch.setenv("FANTASY_AGENT_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(llm.LLMError, match="No API key"):
        llm.complete_json(system="s", user="u")


def test_complete_json_normalizes_http_error(anthropic_credentials):
    http_error = error.HTTPError(
        "https://api.anthropic.com/v1/messages",
        429,
        "Too Many Requests",
        {},
        io.BytesIO(b'{"error":"rate limited"}'),
    )

    with (
        mock.patch("urllib.request.urlopen", side_effect=http_error),
        pytest.raises(llm.LLMError, match="HTTP 429"),
    ):
        llm.complete_json(system="s", user="u")
