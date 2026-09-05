"""Tests for the API access settings layer.

Covers the behaviors the Studio panel depends on:
  1. Settings round-trip through disk and survive a corrupt file.
  2. The secret never leaks into the payload sent to the browser.
  3. Credential resolution precedence (UI settings, then env, then defaults).
  4. Connectivity probing reports each failure mode without raising.
"""

from __future__ import annotations

import io
import json
import unittest.mock as mock
from pathlib import Path
from urllib import error

import pytest

from fantasy_agent import api_settings
from fantasy_agent.api_settings import (
    ANTHROPIC,
    OPENAI_COMPATIBLE,
    LLMApiSettings,
    clear_settings,
    load_settings,
    llm_enabled,
    mask_secret,
    normalize_provider,
    public_settings,
    resolve_credentials,
    save_settings,
    test_connection as probe_connection,
)


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Point the settings file at a throwaway directory."""

    monkeypatch.setenv("FANTASY_AGENT_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FANTASY_AGENT_MODEL", raising=False)
    monkeypatch.delenv("FANTASY_AGENT_BASE_URL", raising=False)
    monkeypatch.delenv("FANTASY_AGENT_USE_LLM", raising=False)
    return tmp_path


def _response(payload: dict, status: int = 200):
    """Build a context-manager stand-in for urlopen()."""

    body = json.dumps(payload).encode("utf-8")
    handle = mock.MagicMock()
    handle.status = status
    handle.read.return_value = body
    handle.__enter__.return_value = handle
    handle.__exit__.return_value = False
    return handle


def test_settings_round_trip(config_dir):
    saved = save_settings(
        LLMApiSettings(
            enabled=True,
            provider=ANTHROPIC,
            base_url="https://api.example.com",
            model="claude-test",
            api_key="sk-test-1234567890",
            timeout_seconds=90,
        )
    )

    assert saved.enabled is True
    loaded = load_settings()
    assert loaded.model == "claude-test"
    assert loaded.api_key == "sk-test-1234567890"
    assert loaded.timeout_seconds == 90
    assert (config_dir / "llm-api.json").exists()


def test_corrupt_file_degrades_to_defaults(config_dir):
    (config_dir / "llm-api.json").write_text("{not json", encoding="utf-8")

    assert load_settings() == LLMApiSettings()


def test_missing_file_degrades_to_defaults(config_dir):
    loaded = load_settings()

    assert loaded.enabled is False
    assert loaded.api_key == ""


def test_public_settings_masks_secret(config_dir):
    save_settings(LLMApiSettings(enabled=True, api_key="sk-test-1234567890"))

    payload = public_settings()

    assert payload["api_key_configured"] is True
    assert payload["api_key_masked"] == "sk-t******7890"
    assert "sk-test-1234567890" not in json.dumps(payload)
    assert payload["ready"] is True
    assert payload["api_key_source"] == "settings"


def test_public_settings_reports_not_ready_without_key(config_dir):
    payload = public_settings()

    assert payload["ready"] is False
    assert payload["api_key_configured"] is False
    assert payload["api_key_masked"] == ""


def test_clear_settings_removes_file(config_dir):
    save_settings(LLMApiSettings(api_key="sk-test-1234567890"))
    assert clear_settings().api_key == ""
    assert not (config_dir / "llm-api.json").exists()


def test_clear_settings_wipes_secret_when_unlink_fails(config_dir, monkeypatch):
    """A locked or guarded file must still lose the key, not raise."""

    save_settings(LLMApiSettings(enabled=True, api_key="sk-test-1234567890"))

    def _boom():
        raise PermissionError("file in use")

    monkeypatch.setattr(Path, "unlink", _boom)

    assert clear_settings().api_key == ""
    on_disk = (config_dir / "llm-api.json").read_text(encoding="utf-8")
    assert "sk-test-1234567890" not in on_disk


def test_mask_secret_handles_short_values():
    assert mask_secret("") == ""
    assert mask_secret("abc") == "***"
    assert mask_secret("sk-1234567890abcd").endswith("abcd")


def test_normalize_provider():
    assert normalize_provider("anthropic") == ANTHROPIC
    assert normalize_provider("OpenAI") == OPENAI_COMPATIBLE
    assert normalize_provider("openai_compatible") == OPENAI_COMPATIBLE
    assert normalize_provider(None) == ANTHROPIC
    assert normalize_provider("something-else") == ANTHROPIC


def test_resolve_credentials_prefers_saved_settings(config_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    save_settings(LLMApiSettings(api_key="sk-saved-key", model="claude-saved"))

    resolved = resolve_credentials()

    assert resolved["api_key"] == "sk-saved-key"
    assert resolved["api_key_source"] == "settings"
    assert resolved["model"] == "claude-saved"


def test_resolve_credentials_falls_back_to_env(config_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    monkeypatch.setenv("FANTASY_AGENT_MODEL", "claude-env")

    resolved = resolve_credentials()

    assert resolved["api_key"] == "sk-env-key"
    assert resolved["api_key_source"] == "env"
    assert resolved["model"] == "claude-env"


def test_resolve_credentials_defaults_per_provider(config_dir):
    assert resolve_credentials()["base_url"] == "https://api.anthropic.com"
    assert resolve_credentials()["model"] == "claude-opus-4-8"

    openai_defaults = resolve_credentials(LLMApiSettings(provider=OPENAI_COMPATIBLE))

    assert openai_defaults["base_url"] == "https://api.openai.com/v1"
    assert openai_defaults["model"] == "gpt-4o-mini"


def test_resolve_credentials_openai_provider_uses_openai_env(config_dir, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-env")

    resolved = resolve_credentials(LLMApiSettings(provider=OPENAI_COMPATIBLE))

    assert resolved["api_key"] == "sk-openai-env"


def test_llm_enabled_precedence(config_dir, monkeypatch):
    assert llm_enabled() is False

    save_settings(LLMApiSettings(enabled=True))
    assert llm_enabled() is True

    monkeypatch.setenv("FANTASY_AGENT_USE_LLM", "0")
    assert llm_enabled() is False

    assert llm_enabled(True) is True
    assert llm_enabled(False) is False


def test_endpoint_url_shapes():
    assert api_settings.endpoint_url(ANTHROPIC, "https://api.anthropic.com") == (
        "https://api.anthropic.com/v1/messages"
    )
    assert api_settings.endpoint_url(ANTHROPIC, "https://gw.example.com/v1") == (
        "https://gw.example.com/v1/messages"
    )
    assert api_settings.endpoint_url(OPENAI_COMPATIBLE, "https://api.openai.com/v1") == (
        "https://api.openai.com/v1/chat/completions"
    )
    assert api_settings.endpoint_url(
        OPENAI_COMPATIBLE, "https://gw.example.com/v1/chat/completions"
    ) == ("https://gw.example.com/v1/chat/completions")


def test_request_headers_per_provider():
    anthropic_headers = api_settings.request_headers(ANTHROPIC, "sk-a")

    assert anthropic_headers["x-api-key"] == "sk-a"
    assert anthropic_headers["anthropic-version"] == "2023-06-01"

    openai_headers = api_settings.request_headers(OPENAI_COMPATIBLE, "sk-o")

    assert openai_headers["Authorization"] == "Bearer sk-o"


def test_extract_reply_per_provider():
    assert api_settings.extract_reply(
        ANTHROPIC, {"content": [{"type": "text", "text": "hi"}]}
    ) == "hi"
    assert api_settings.extract_reply(
        OPENAI_COMPATIBLE, {"choices": [{"message": {"content": "yo"}}]}
    ) == "yo"
    assert api_settings.extract_reply(OPENAI_COMPATIBLE, {"choices": []}) == ""


def test_connection_reports_missing_key(config_dir):
    result = probe_connection()

    assert result.ok is False
    assert result.status == "missing_key"
    assert result.detail_key == "apiTestMissingKey"


def test_connection_success_anthropic(config_dir):
    save_settings(LLMApiSettings(enabled=True, api_key="sk-test-1234567890", model="claude-test"))
    payload = {"model": "claude-test", "content": [{"type": "text", "text": "ok"}]}

    with mock.patch("urllib.request.urlopen", return_value=_response(payload)) as mocked:
        result = probe_connection()

    assert result.ok is True
    assert result.status == "connected"
    assert result.reply == "ok"
    assert result.model == "claude-test"
    assert result.http_status == 200
    sent = mocked.call_args[0][0]
    assert sent.full_url == "https://api.anthropic.com/v1/messages"
    assert sent.get_header("X-api-key") == "sk-test-1234567890"
    assert sent.get_header("Anthropic-version") == "2023-06-01"


def test_connection_success_openai_compatible(config_dir):
    settings = LLMApiSettings(
        enabled=True,
        provider=OPENAI_COMPATIBLE,
        base_url="https://gw.example.com/v1",
        model="local-model",
        api_key="sk-local",
    )
    payload = {"choices": [{"message": {"content": "ok"}}]}

    with mock.patch("urllib.request.urlopen", return_value=_response(payload)) as mocked:
        result = probe_connection(settings)

    assert result.ok is True
    assert result.reply == "ok"
    sent = mocked.call_args[0][0]
    assert sent.full_url == "https://gw.example.com/v1/chat/completions"
    assert sent.get_header("Authorization") == "Bearer sk-local"


def test_connection_reports_http_error(config_dir):
    save_settings(LLMApiSettings(api_key="sk-test-1234567890"))
    http_error = error.HTTPError(
        "https://api.anthropic.com/v1/messages",
        401,
        "Unauthorized",
        {},
        io.BytesIO(b'{"error":"invalid api key"}'),
    )

    with mock.patch("urllib.request.urlopen", side_effect=http_error):
        result = probe_connection()

    assert result.ok is False
    assert result.status == "http_error"
    assert result.http_status == 401
    assert "401" in result.detail


def test_connection_reports_unreachable(config_dir):
    save_settings(LLMApiSettings(api_key="sk-test-1234567890"))

    with mock.patch("urllib.request.urlopen", side_effect=OSError("DNS failure")):
        result = probe_connection()

    assert result.ok is False
    assert result.status == "unreachable"
    assert "DNS failure" in result.detail


def test_connection_reports_bad_response(config_dir):
    save_settings(LLMApiSettings(api_key="sk-test-1234567890"))
    handle = mock.MagicMock()
    handle.status = 200
    handle.read.return_value = b"<html>not json</html>"
    handle.__enter__.return_value = handle
    handle.__exit__.return_value = False

    with mock.patch("urllib.request.urlopen", return_value=handle):
        result = probe_connection()

    assert result.ok is False
    assert result.status == "bad_response"


def test_connection_never_raises_on_unexpected_error(config_dir):
    save_settings(LLMApiSettings(api_key="sk-test-1234567890"))

    with mock.patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
        result = probe_connection()

    assert result.ok is False
    assert result.status == "unreachable"
