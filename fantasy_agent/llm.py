"""Central LLM client for Fantasy Agent.

The wider codebase is deterministic; this module is the single place that talks
to an LLM. It is intentionally lazy: importing this module must never construct
an API client or require credentials, so the package keeps importing cleanly in
environments without ``anthropic`` installed or without an API key.

Configuration (environment variables):
    FANTASY_AGENT_MODEL    Override the default model id.
    ANTHROPIC_API_KEY      Standard Anthropic credential (read by the SDK).
"""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_MODEL = "claude-opus-4-8"

# Module-level singleton, created lazily on first use. Never built at import.
_client: Any | None = None


class LLMError(RuntimeError):
    """Raised when an LLM call cannot be completed or its output is unusable.

    Callers are expected to catch this and fall back to deterministic logic.
    """


def model_name() -> str:
    """Return the configured model id (env override or default)."""

    return os.environ.get("FANTASY_AGENT_MODEL", DEFAULT_MODEL)


def get_client() -> Any:
    """Return a cached Anthropic client, constructing it on first call.

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
            "`pip install fantasy-agent[llm]` to enable the LLM backend."
        ) from exc

    _client = Anthropic()
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

    client = get_client()

    try:
        response = client.messages.create(
            model=model or model_name(),
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = response.content[0].text.strip()
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize any SDK/transport error
        raise LLMError(f"LLM request failed: {exc}") from exc

    raw = _strip_code_fence(raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMError(f"LLM returned non-object JSON of type {type(parsed).__name__}")

    return parsed


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
