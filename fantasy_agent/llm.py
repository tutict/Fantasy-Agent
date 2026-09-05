"""Central LLM client for Fantasy Agent.

The wider codebase is deterministic; this module is the single place that talks
to an LLM. It is intentionally lazy: importing this module must never construct
an API client or require credentials, so the package keeps importing cleanly in
environments without ``anthropic`` installed or without an API key.

Configuration, in precedence order:
    FANTASY_AGENT_MODEL    Override the model id.
    ANTHROPIC_API_KEY      Standard Anthropic credential (read by the SDK).
    OPENAI_API_KEY         Credential for OpenAI-compatible endpoints.
    FANTASY_AGENT_BASE_URL Override the endpoint base URL.
    Studio UI settings     Saved in ``generated/config/llm-api.json`` via
                           ``fantasy_agent.api_settings``.

The Studio "API access" panel writes that settings file, so credentials entered
in the UI flow through this module without touching any other call site.
"""

from __future__ import annotations

import json
import os
from typing import Any

from fantasy_agent.api_settings import (
    ANTHROPIC,
    OPENAI_COMPATIBLE,
    endpoint_url,
    request_headers,
    resolve_credentials,
)

DEFAULT_MODEL = "claude-opus-4-8"

# Module-level singleton, created lazily on first use. Never built at import.
_client: Any | None = None


class LLMError(RuntimeError):
    """Raised when an LLM call cannot be completed or its output is unusable.

    Callers are expected to catch this and fall back to deterministic logic.
    """


def model_name() -> str:
    """Return the effective model id (env override, then UI settings)."""

    env_model = os.environ.get("FANTASY_AGENT_MODEL", "").strip()
    if env_model:
        return env_model
    return str(resolve_credentials()["model"] or DEFAULT_MODEL)


def current_provider() -> str:
    """Return the effective provider id."""

    return str(resolve_credentials()["provider"] or ANTHROPIC)


def get_client() -> Any:
    """Return a cached Anthropic SDK client, constructing it on first call.

    This is an opt-in escape hatch for callers that want the official SDK's
    features. The generation path itself does **not** use it: ``complete_json``
    speaks both provider wire formats over the standard library so that a
    configured API works without installing the optional ``llm`` extra.

    Raises:
        LLMError: if the ``anthropic`` package is not installed.
    """

    global _client
    if _client is not None:
        return _client

    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover - exercised via fallback path
        raise LLMError(
            "anthropic package is not installed. Install it with "
            "`pip install fantasy-agent[llm]` to use the SDK client."
        ) from exc

    credentials = resolve_credentials()
    kwargs: dict[str, Any] = {}
    if credentials["api_key"]:
        kwargs["api_key"] = credentials["api_key"]
    if credentials["base_url"]:
        kwargs["base_url"] = credentials["base_url"]

    _client = Anthropic(**kwargs)
    return _client


def complete_json(
    *,
    system: str,
    user: str,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    model: str | None = None,
) -> dict[str, Any]:
    """Call the model and parse its reply as a JSON object.

    Strips a leading/trailing markdown code fence if present, then parses.

    Raises:
        LLMError: on missing package, API failure, or unparseable / non-object
            output. Callers should treat this as a signal to fall back.
    """

    resolved = resolve_credentials()

    if resolved["provider"] == OPENAI_COMPATIBLE:
        raw = _complete_openai_compatible(
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model or str(resolved["model"]),
            base_url=str(resolved["base_url"]),
            api_key=str(resolved["api_key"]),
            timeout=float(resolved["timeout_seconds"]),
        )
    else:
        raw = _complete_anthropic(
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        )

    parsed = _parse_json_object(raw)
    if not isinstance(parsed, dict):
        raise LLMError(f"LLM returned non-object JSON of type {type(parsed).__name__}")
    return parsed


def _complete_anthropic(
    *,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
    model: str | None,
) -> str:
    """Send the request to the Anthropic Messages API over plain HTTP.

    Deliberately uses the standard library: the panel's "test connection" probe
    already proves the endpoint works over HTTP, and requiring an SDK install
    would let the UI report success while generation silently fell back.
    """

    resolved = resolve_credentials()
    api_key = str(resolved["api_key"])
    if not api_key:
        raise LLMError("No API key configured for the Anthropic provider.")

    url = endpoint_url(ANTHROPIC, str(resolved["base_url"]))
    payload = {
        "model": model or model_name(),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    decoded = _post_json(
        url,
        payload=payload,
        headers=request_headers(ANTHROPIC, api_key),
        timeout=float(resolved["timeout_seconds"]),
    )

    blocks = decoded.get("content") or []
    texts = [block.get("text", "") for block in blocks if isinstance(block, dict)]
    return "".join(texts).strip()


def _complete_openai_compatible(
    *,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
    model: str,
    base_url: str,
    api_key: str,
    timeout: float,
) -> str:
    """Send the request to an OpenAI-compatible ``/chat/completions`` endpoint.

    Uses the standard library so the optional ``llm`` extra stays optional.
    """

    if not api_key:
        raise LLMError("No API key configured for the OpenAI-compatible provider.")

    url = endpoint_url(OPENAI_COMPATIBLE, base_url)
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    decoded = _post_json(
        url,
        payload=payload,
        headers=request_headers(OPENAI_COMPATIBLE, api_key),
        timeout=timeout,
    )

    choices = decoded.get("choices") or []
    if not choices:
        raise LLMError("LLM response contained no choices.")
    content = (choices[0].get("message") or {}).get("content", "")
    return str(content).strip()


def _post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """POST JSON and return the decoded body, normalizing every error to LLMError."""

    from urllib import error, request

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        snippet = ""
        try:
            snippet = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # noqa: BLE001 - body may already be consumed
            snippet = ""
        raise LLMError(f"LLM request failed: HTTP {exc.code} {snippet or exc.reason}") from exc
    except Exception as exc:  # noqa: BLE001 - normalize transport errors
        raise LLMError(f"LLM request failed: {exc}") from exc

    try:
        decoded = json.loads(raw)
    except ValueError as exc:
        raise LLMError(f"LLM returned invalid JSON: {exc}") from exc
    if not isinstance(decoded, dict):
        raise LLMError(f"LLM returned a non-object JSON body: {raw[:200]}")
    return decoded


def _parse_json_object(raw: str) -> Any:
    """Parse model output as JSON, tolerating a surrounding markdown fence."""

    text = _strip_code_fence(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM returned invalid JSON: {exc}") from exc


def _strip_code_fence(text: str) -> str:
    """Remove a surrounding ```...``` markdown fence if the model added one."""

    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    # Drop the opening fence (possibly ```json) and a trailing fence if present.
    lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
