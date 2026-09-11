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
from dataclasses import dataclass, field
from typing import Any

from fantasy_agent.api_settings import (
    ANTHROPIC,
    OPENAI_COMPATIBLE,
    OPENAI_RESPONSES,
    endpoint_url,
    request_headers,
    resolve_credentials,
    supports_sampling_params,
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


@dataclass
class ToolCallRequest:
    """One tool invocation the model asked for."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelReply:
    """A model turn: free text plus zero or more tool calls."""

    text: str
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def complete_with_tools(
    *,
    instructions: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int = 4000,
    model: str | None = None,
) -> ModelReply:
    """One agent turn, on whichever provider the user configured.

    The transcript handed in is the Responses shape (``agent_loop`` builds it
    and echoes ``function_call`` blocks back verbatim so call ids line up), and
    every provider returns its reply normalized back into that same shape. That
    keeps exactly one conversation format to maintain: ``anthropic`` and
    ``openai_compatible`` receive a *projection* of it and hand back a reply
    that was re-expressed in it, so the loop never learns which wire format it
    is talking to.

    Raises:
        LLMError: when the provider has no key, the endpoint fails, or the
            reply cannot be understood. Callers fall back to the deterministic
            pipeline rather than retry.
    """

    resolved = resolve_credentials()
    provider = resolved["provider"]

    if provider == ANTHROPIC:
        return _anthropic_tool_turn(
            instructions=instructions,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            model=model,
        )
    if provider == OPENAI_COMPATIBLE:
        return _openai_chat_tool_turn(
            instructions=instructions,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            model=model,
        )
    if provider == OPENAI_RESPONSES:
        return _responses_tool_turn(
            instructions=instructions,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            model=model,
        )
    raise LLMError(f"tool calling is not implemented for provider {provider!r}")


def _responses_tool_turn(
    *,
    instructions: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int,
    model: str | None,
) -> ModelReply:
    """``/v1/responses``: the transcript is already in this wire format."""

    resolved = resolve_credentials()
    effective_model = model or str(resolved["model"])
    payload: dict[str, Any] = {
        "model": effective_model,
        "instructions": instructions,
        "input": messages,
        "tools": tools,
        "max_output_tokens": max_tokens,
    }
    # GPT-6 rejects temperature outright; sending it is a hard error, not a
    # silently ignored field.
    if supports_sampling_params(effective_model):
        payload["temperature"] = 0.2

    decoded = _post_json(
        endpoint_url(OPENAI_RESPONSES, str(resolved["base_url"])),
        payload=payload,
        headers=request_headers(OPENAI_RESPONSES, str(resolved["api_key"])),
        timeout=float(resolved["timeout_seconds"]),
    )
    return _parse_responses_reply(decoded)


def _anthropic_tool_turn(
    *,
    instructions: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int,
    model: str | None,
) -> ModelReply:
    """Anthropic Messages API with native ``tool_use`` blocks.

    Three shape differences matter: the system prompt is a top-level field
    rather than a message, tool schemas are ``input_schema`` rather than
    ``parameters``, and a tool result is a ``tool_result`` block inside the
    *following user turn* rather than a message of its own.
    """

    resolved = resolve_credentials()
    api_key = str(resolved["api_key"])
    if not api_key:
        raise LLMError("No API key configured for the Anthropic provider.")

    effective_model = model or model_name()
    payload: dict[str, Any] = {
        "model": effective_model,
        "max_tokens": max_tokens,
        "system": instructions,
        "messages": _anthropic_transcript(messages),
    }
    if tools:
        payload["tools"] = _anthropic_tools(tools)
    if supports_sampling_params(effective_model):
        payload["temperature"] = 0.2

    decoded = _post_json(
        endpoint_url(ANTHROPIC, str(resolved["base_url"])),
        payload=payload,
        headers=request_headers(ANTHROPIC, api_key),
        timeout=float(resolved["timeout_seconds"]),
    )
    return _parse_anthropic_tool_reply(decoded)


def _openai_chat_tool_turn(
    *,
    instructions: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int,
    model: str | None,
) -> ModelReply:
    """``/chat/completions`` with ``tools``/``tool_calls``.

    Works for any OpenAI-compatible gateway. GPT-6 Astra is the known
    exception -- it rejects tool calls on this endpoint, which is why
    ``openai_responses`` exists and why the provider is the user's choice
    rather than something guessed from the model name.
    """

    resolved = resolve_credentials()
    api_key = str(resolved["api_key"])
    if not api_key:
        raise LLMError("No API key configured for the OpenAI-compatible provider.")

    effective_model = model or str(resolved["model"])
    payload: dict[str, Any] = {
        "model": effective_model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": instructions},
            *_openai_chat_transcript(messages),
        ],
    }
    if tools:
        payload["tools"] = _openai_chat_tools(tools)
    if supports_sampling_params(effective_model):
        payload["temperature"] = 0.2

    decoded = _post_json(
        endpoint_url(OPENAI_COMPATIBLE, str(resolved["base_url"])),
        payload=payload,
        headers=request_headers(OPENAI_COMPATIBLE, api_key),
        timeout=float(resolved["timeout_seconds"]),
    )
    return _parse_openai_chat_tool_reply(decoded)


def _parse_anthropic_tool_reply(payload: dict[str, Any]) -> ModelReply:
    """Split an Anthropic body into text plus ``tool_use`` calls."""

    texts: list[str] = []
    calls: list[ToolCallRequest] = []
    output: list[dict[str, Any]] = []

    for block in payload.get("content") or []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            texts.append(str(block.get("text") or ""))
        elif kind == "tool_use":
            call_id = str(block.get("id") or "")
            name = str(block.get("name") or "")
            arguments = block.get("input") if isinstance(block.get("input"), dict) else {}
            calls.append(ToolCallRequest(id=call_id, name=name, arguments=arguments))
            output.append(_function_call_block(call_id, name, arguments))

    text = "".join(texts).strip()
    return ModelReply(text=text, tool_calls=calls, raw={"output": _with_text_block(output, text)})


def _parse_openai_chat_tool_reply(payload: dict[str, Any]) -> ModelReply:
    """Split a Chat Completions body into text plus function calls."""

    choices = payload.get("choices") or []
    if not choices:
        raise LLMError("LLM response contained no choices.")
    message = choices[0].get("message") or {}
    text = str(message.get("content") or "").strip()

    calls: list[ToolCallRequest] = []
    output: list[dict[str, Any]] = []
    for raw_call in message.get("tool_calls") or []:
        if not isinstance(raw_call, dict):
            continue
        function = raw_call.get("function") or {}
        call_id = str(raw_call.get("id") or "")
        name = str(function.get("name") or "")
        arguments = _parse_arguments(function.get("arguments"))
        calls.append(ToolCallRequest(id=call_id, name=name, arguments=arguments))
        output.append(_function_call_block(call_id, name, arguments))

    return ModelReply(text=text, tool_calls=calls, raw={"output": _with_text_block(output, text)})


def _function_call_block(call_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Re-express a provider tool call as a Responses ``function_call`` block.

    The loop echoes these blocks back on the next turn, so the arguments have
    to survive the round trip in the shape the next projection expects.
    """

    return {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps(arguments, ensure_ascii=False),
    }


def _with_text_block(output: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    if not text:
        return output
    return [
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]},
        *output,
    ]


def _anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project Responses-shaped function tools onto Anthropic's ``tools``."""

    projected: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name") or "")
        if not name:
            continue
        entry: dict[str, Any] = {
            "name": name,
            "input_schema": tool.get("parameters") or {"type": "object", "properties": {}},
        }
        description = tool.get("description")
        if description:
            entry["description"] = str(description)
        projected.append(entry)
    return projected


def _openai_chat_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project Responses-shaped function tools onto Chat Completions ``tools``.

    The two differ only by the extra ``function`` nesting. A tool that already
    carries it is passed through untouched so this cannot double-wrap.
    """

    projected: list[dict[str, Any]] = []
    for tool in tools:
        function = tool.get("function")
        if isinstance(function, dict):
            projected.append(tool)
            continue
        name = str(tool.get("name") or "")
        if not name:
            continue
        body: dict[str, Any] = {
            "name": name,
            "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
        }
        description = tool.get("description")
        if description:
            body["description"] = str(description)
        projected.append({"type": "function", "function": body})
    return projected


def _anthropic_transcript(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project the loop's transcript onto Anthropic ``messages``.

    Consecutive same-role list-content turns are merged so a turn's text and
    its ``tool_use`` blocks land in one assistant message, and the tool results
    that follow land in one user message -- which is the alternation the API
    expects.
    """

    out: list[dict[str, Any]] = []
    for item in messages:
        kind = item.get("type")
        if kind == "function_call":
            _push_content_block(
                out,
                "assistant",
                {
                    "type": "tool_use",
                    "id": _call_id(item),
                    "name": str(item.get("name") or ""),
                    "input": _tool_arguments(item.get("arguments")),
                },
            )
            continue
        if kind == "function_call_output":
            _push_content_block(
                out,
                "user",
                {
                    "type": "tool_result",
                    "tool_use_id": _call_id(item),
                    "content": str(item.get("output") or ""),
                },
            )
            continue
        if kind == "message":
            text = _message_block_text(item)
            if text:
                _push_content_block(out, "assistant", {"type": "text", "text": text})
            continue
        role = str(item.get("role") or "")
        content = item.get("content")
        if role in {"user", "assistant"} and not isinstance(content, list):
            out.append({"role": role, "content": str(content or "")})
    return out


def _openai_chat_transcript(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project the loop's transcript onto Chat Completions ``messages``.

    Tool calls are grouped into the assistant message that requested them
    (``tool_calls``), and each result becomes a ``role: tool`` message keyed by
    ``tool_call_id`` -- the shape this endpoint validates before it will accept
    the results at all.
    """

    out: list[dict[str, Any]] = []
    for item in messages:
        kind = item.get("type")
        if kind == "function_call":
            call = {
                "id": _call_id(item),
                "type": "function",
                "function": {
                    "name": str(item.get("name") or ""),
                    "arguments": _arguments_text(item.get("arguments")),
                },
            }
            if out and out[-1].get("role") == "assistant":
                out[-1].setdefault("tool_calls", []).append(call)
            else:
                out.append({"role": "assistant", "content": "", "tool_calls": [call]})
            continue
        if kind == "function_call_output":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": _call_id(item),
                    "content": str(item.get("output") or ""),
                }
            )
            continue
        if kind == "message":
            text = _message_block_text(item)
            if not text:
                continue
            if out and out[-1].get("role") == "assistant":
                out[-1]["content"] = str(out[-1].get("content") or "") + text
            else:
                out.append({"role": "assistant", "content": text})
            continue
        role = str(item.get("role") or "")
        if role in {"user", "assistant"} and not isinstance(item.get("content"), list):
            out.append({"role": role, "content": str(item.get("content") or "")})
    return out


def _push_content_block(
    out: list[dict[str, Any]],
    role: str,
    block: dict[str, Any],
) -> None:
    """Append ``block`` to the trailing message of the same role, else start one."""

    if out and out[-1].get("role") == role and isinstance(out[-1].get("content"), list):
        out[-1]["content"].append(block)
        return
    out.append({"role": role, "content": [block]})


def _call_id(item: dict[str, Any]) -> str:
    return str(item.get("call_id") or item.get("id") or "")


def _message_block_text(block: dict[str, Any]) -> str:
    parts = [
        str(part.get("text") or "")
        for part in block.get("content") or []
        if isinstance(part, dict) and part.get("type") in ("output_text", "text")
    ]
    return "".join(parts)


def _tool_arguments(raw: Any) -> dict[str, Any]:
    """Return a tool call's arguments as an object, whatever shape they arrived in."""

    parsed = _parse_arguments(raw)
    return parsed if isinstance(parsed, dict) else {}


def _arguments_text(raw: Any) -> str:
    """Return a tool call's arguments as the JSON *string* Chat Completions wants."""

    if isinstance(raw, str):
        return raw
    try:
        return json.dumps(raw if isinstance(raw, dict) else {}, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


def _parse_responses_reply(payload: dict[str, Any]) -> ModelReply:
    """Split a Responses body into text plus function calls.

    ``output`` is an ordered array: ``message`` blocks carry assistant text,
    ``function_call`` blocks carry one call each with a ``call_id`` that the
    matching ``function_call_output`` must reference.
    """

    blocks = payload.get("output") or []
    texts: list[str] = []
    calls: list[ToolCallRequest] = []

    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "message":
            texts.extend(
                str(part.get("text", ""))
                for part in block.get("content") or []
                if isinstance(part, dict)
            )
        elif kind == "function_call":
            calls.append(
                ToolCallRequest(
                    id=str(block.get("call_id") or block.get("id") or ""),
                    name=str(block.get("name") or ""),
                    arguments=_parse_arguments(block.get("arguments")),
                )
            )

    text = "".join(texts).strip() or str(payload.get("output_text") or "").strip()
    return ModelReply(text=text, tool_calls=calls, raw=payload)


def _parse_arguments(raw: Any) -> dict[str, Any]:
    """Function call arguments arrive as a JSON *string*, not an object."""

    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
    except Exception as exc:
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
