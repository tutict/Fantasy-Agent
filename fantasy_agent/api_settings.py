"""Local API credential settings for the optional LLM backend.

Fantasy Agent is deterministic by default. When a user wants richer gameplay
and GDD generation, they can connect a model API from the Studio UI. This
module is the single place that stores, resolves and probes those credentials.

Storage layout::

    generated/config/llm-api.json

The path can be overridden with ``FANTASY_AGENT_CONFIG_DIR`` so tests can use a
temporary directory. Importing this module never reads the network and never
requires credentials.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from pydantic import BaseModel, Field

ANTHROPIC = "anthropic"
OPENAI_COMPATIBLE = "openai_compatible"
PROVIDERS = (ANTHROPIC, OPENAI_COMPATIBLE)

DEFAULT_BASE_URLS: dict[str, str] = {
    ANTHROPIC: "https://api.anthropic.com",
    OPENAI_COMPATIBLE: "https://api.openai.com/v1",
}

DEFAULT_MODELS: dict[str, str] = {
    ANTHROPIC: "claude-opus-4-8",
    OPENAI_COMPATIBLE: "gpt-4o-mini",
}

# Probe prompt kept tiny on purpose: a connection test should cost almost nothing.
PROBE_PROMPT = 'Reply with the single word "ok" and nothing else.'
PROBE_MAX_TOKENS = 16


class LLMApiSettings(BaseModel):
    """Credentials and endpoint choices saved from the Studio UI."""

    enabled: bool = False
    provider: str = Field(default=ANTHROPIC)
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    timeout_seconds: float = Field(default=60.0, ge=5.0, le=600.0)


class ApiTestResult(BaseModel):
    """Outcome of a connectivity probe."""

    ok: bool = False
    provider: str = ANTHROPIC
    model: str = ""
    status: str = "not_checked"
    detail: str = ""
    detail_key: str = ""
    latency_ms: int = 0
    http_status: int | None = None
    reply: str = ""


def settings_path() -> Path:
    """Return the JSON file holding the saved API settings."""

    override = os.environ.get("FANTASY_AGENT_CONFIG_DIR", "").strip()
    if override:
        return Path(override) / "llm-api.json"
    return Path(__file__).resolve().parents[1] / "generated" / "config" / "llm-api.json"


def load_settings() -> LLMApiSettings:
    """Load saved settings, falling back to defaults when missing or corrupt.

    A corrupt file must never break the Studio: it degrades to defaults so the
    user can simply re-enter credentials in the UI.
    """

    path = settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return LLMApiSettings()
    if not isinstance(raw, dict):
        return LLMApiSettings()
    try:
        return LLMApiSettings.model_validate(raw)
    except Exception:  # noqa: BLE001 - corrupt config degrades to defaults
        return LLMApiSettings()


def save_settings(settings: LLMApiSettings) -> LLMApiSettings:
    """Persist settings to disk and return the saved model."""

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings.model_dump(), indent=2, ensure_ascii=False)
    path.write_text(payload, encoding="utf-8")
    # Best-effort owner-only permissions; a no-op on Windows.
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return settings


def clear_settings() -> LLMApiSettings:
    """Remove the stored credentials and return defaults.

    The secret is overwritten first, then the file is deleted if the filesystem
    allows it. Order matters: a locked, read-only or sandbox-guarded file must
    still lose the key rather than leave it on disk just because the unlink
    failed.
    """

    defaults = LLMApiSettings()
    save_settings(defaults)
    try:
        settings_path().unlink()
    except Exception:  # noqa: BLE001 - deletion is best-effort after the wipe
        pass
    return defaults


def normalize_provider(value: str | None) -> str:
    """Return a supported provider id, defaulting to Anthropic."""

    text = (value or "").strip().casefold()
    if text in PROVIDERS:
        return text
    if "openai" in text or text in {"openai", "compatible", "openai-compatible"}:
        return OPENAI_COMPATIBLE
    return ANTHROPIC


def mask_secret(value: str | None) -> str:
    """Return a display-only prefix/suffix mask for a secret."""

    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}{'*' * 6}{text[-4:]}"


def public_settings(settings: LLMApiSettings | None = None) -> dict[str, Any]:
    """Return a UI-safe view: the raw key is never sent back to the browser."""

    current = settings or load_settings()
    resolved = resolve_credentials(current)
    return {
        "enabled": current.enabled,
        "provider": resolved["provider"],
        "base_url": resolved["base_url"],
        "model": resolved["model"],
        "timeout_seconds": current.timeout_seconds,
        "api_key_masked": mask_secret(resolved["api_key"]),
        "api_key_configured": bool(resolved["api_key"]),
        "api_key_source": resolved["api_key_source"],
        "ready": bool(current.enabled and resolved["api_key"]),
        "config_path": str(settings_path()),
    }


def resolve_credentials(settings: LLMApiSettings | None = None) -> dict[str, Any]:
    """Resolve effective credentials.

    Precedence: saved UI settings first, then environment variables, then
    built-in defaults. This keeps the existing ``ANTHROPIC_API_KEY`` /
    ``FANTASY_AGENT_MODEL`` workflow working unchanged.
    """

    current = settings or load_settings()
    provider = normalize_provider(current.provider)

    api_key = (current.api_key or "").strip()
    api_key_source = "settings"
    if not api_key:
        env_key = "ANTHROPIC_API_KEY" if provider == ANTHROPIC else "OPENAI_API_KEY"
        api_key = os.environ.get(env_key, "").strip()
        if api_key:
            api_key_source = "env"
    if not api_key:
        # A key pasted for one provider is still the user's intent; allow both.
        api_key = (
            os.environ.get("OPENAI_API_KEY", "").strip()
            or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        )
        if api_key:
            api_key_source = "env"
    if not api_key:
        api_key_source = "none"

    base_url = (current.base_url or "").strip().rstrip("/")
    if not base_url:
        base_url = os.environ.get("FANTASY_AGENT_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = DEFAULT_BASE_URLS[provider]

    model = (current.model or "").strip()
    if not model:
        model = os.environ.get("FANTASY_AGENT_MODEL", "").strip()
    if not model:
        model = DEFAULT_MODELS[provider]

    timeout = current.timeout_seconds or 60.0

    return {
        "provider": provider,
        "api_key": api_key,
        "api_key_source": api_key_source,
        "base_url": base_url,
        "model": model,
        "timeout_seconds": timeout,
    }


def llm_enabled(use_llm: bool | None = None) -> bool:
    """Whether the LLM backend should be attempted.

    Explicit ``use_llm`` wins; otherwise read the ``FANTASY_AGENT_USE_LLM`` env
    flag; otherwise trust the saved UI toggle.
    """

    if use_llm is not None:
        return bool(use_llm)
    env_flag = os.environ.get("FANTASY_AGENT_USE_LLM", "").strip().casefold()
    if env_flag:
        return env_flag in {"1", "true", "yes", "on"}
    return bool(load_settings().enabled)


def endpoint_url(provider: str, base_url: str) -> str:
    """Build the chat endpoint URL for a provider.

    Tolerates base URLs entered with or without the version prefix or the full
    operation path, because gateways in the wild are inconsistent about it.
    """

    root = base_url.rstrip("/")
    if provider == ANTHROPIC:
        if root.endswith("/v1"):
            return f"{root}/messages"
        return f"{root}/v1/messages"
    if root.endswith("/chat/completions"):
        return root
    return f"{root}/chat/completions"


def request_headers(provider: str, api_key: str) -> dict[str, str]:
    """Build the auth headers for a provider."""

    headers = {"Content-Type": "application/json"}
    if provider == ANTHROPIC:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def extract_reply(provider: str, payload: dict[str, Any]) -> str:
    """Pull the assistant text out of a provider response."""

    if provider == ANTHROPIC:
        blocks = payload.get("content") or []
        texts = [block.get("text", "") for block in blocks if isinstance(block, dict)]
        return "".join(texts).strip()
    choices = payload.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        return str(message.get("content", "")).strip()
    return ""


def _probe_payload(model: str) -> dict[str, Any]:
    """The two provider wire formats happen to share this minimal shape."""

    return {
        "model": model,
        "max_tokens": PROBE_MAX_TOKENS,
        "messages": [{"role": "user", "content": PROBE_PROMPT}],
    }


def test_connection(settings: LLMApiSettings | None = None) -> ApiTestResult:
    """Send a minimal real request to verify the configured API works.

    Never raises: every failure path returns an ``ok=False`` result with a
    localized message key so the UI can explain what to fix.
    """

    current = settings or load_settings()
    resolved = resolve_credentials(current)
    provider = resolved["provider"]
    api_key = resolved["api_key"]
    model = resolved["model"]

    if not api_key:
        return ApiTestResult(
            ok=False,
            provider=provider,
            model=model,
            status="missing_key",
            detail_key="apiTestMissingKey",
            detail="No API key configured.",
        )

    url = endpoint_url(provider, resolved["base_url"])
    body = json.dumps(_probe_payload(model)).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        headers=request_headers(provider, api_key),
        method="POST",
    )

    started = time.perf_counter()
    try:
        with request.urlopen(http_request, timeout=resolved["timeout_seconds"]) as response:
            raw = response.read().decode("utf-8", errors="replace")
            http_status = int(getattr(response, "status", 200) or 200)
    except error.HTTPError as exc:
        latency = int((time.perf_counter() - started) * 1000)
        snippet = ""
        try:
            snippet = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:  # noqa: BLE001 - body may already be consumed
            snippet = ""
        return ApiTestResult(
            ok=False,
            provider=provider,
            model=model,
            status="http_error",
            detail_key="apiTestHttpError",
            detail=f"HTTP {exc.code}: {snippet or exc.reason}",
            latency_ms=latency,
            http_status=int(exc.code),
        )
    except Exception as exc:  # noqa: BLE001 - DNS, TLS, timeout, proxy issues
        latency = int((time.perf_counter() - started) * 1000)
        return ApiTestResult(
            ok=False,
            provider=provider,
            model=model,
            status="unreachable",
            detail_key="apiTestUnreachable",
            detail=f"{type(exc).__name__}: {exc}",
            latency_ms=latency,
        )

    latency = int((time.perf_counter() - started) * 1000)
    try:
        payload = json.loads(raw)
    except ValueError:
        return ApiTestResult(
            ok=False,
            provider=provider,
            model=model,
            status="bad_response",
            detail_key="apiTestBadResponse",
            detail=f"Response is not JSON: {raw[:200]}",
            latency_ms=latency,
            http_status=http_status,
        )

    reply = extract_reply(provider, payload)
    return ApiTestResult(
        ok=True,
        provider=provider,
        model=str(payload.get("model") or model),
        status="connected",
        detail_key="apiTestConnected",
        detail="Connection succeeded.",
        latency_ms=latency,
        http_status=http_status,
        reply=reply[:200],
    )
