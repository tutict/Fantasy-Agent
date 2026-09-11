"""Tool calling on every provider, not just ``openai_responses``.

The loop's transcript is the Responses shape (``agent_loop`` echoes
``function_call`` blocks so call ids line up). ``anthropic`` and
``openai_compatible`` therefore talk to *projections* of it, and their replies
are re-expressed in it before the loop sees them.

What these tests pin down, in order of what actually breaks:

1. the request each provider receives (tool schema shape, system prompt
   placement, tool-result placement, sampling params);
2. the reply each provider's body parses into;
3. that the loop still accepts a tool call when the transport is any of the
   three -- driven end to end through the real registry and the real Godot
   bridge, with only the HTTP layer stubbed.

The wire shapes are the contract with three external services we cannot call
in CI, so they are asserted literally rather than described.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from fantasy_agent import llm
from fantasy_agent.api_settings import ANTHROPIC, OPENAI_COMPATIBLE, OPENAI_RESPONSES, PROVIDERS
from fantasy_agent.tool_registry import engine_registry

INSTRUCTIONS = "You are the planning agent."
GOAL = "is this project valid?"

_TOOL = {
    "type": "function",
    "name": "validate_godot_project",
    "description": "Check a generated Godot project.",
    "parameters": {
        "type": "object",
        "required": ["project_file"],
        "properties": {"project_file": {"type": "string"}},
    },
}


def _credentials(provider: str, **overrides: Any) -> dict[str, Any]:
    resolved: dict[str, Any] = {
        "provider": provider,
        "api_key": "test-key",
        "api_key_source": "settings",
        "base_url": "",
        "model": "",
        "timeout_seconds": 30.0,
    }
    resolved.update(overrides)
    return resolved


class _Transport:
    """Stands in for ``_post_json``: records requests, replays queued bodies."""

    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url, *, payload, headers, timeout):
        self.calls.append({"url": url, "payload": payload, "headers": headers, "timeout": timeout})
        if not self.replies:
            raise AssertionError("the code under test sent more requests than the test queued")
        return self.replies.pop(0)

    @property
    def last(self) -> dict[str, Any]:
        return self.calls[-1]

    def body(self, index: int) -> dict[str, Any]:
        return self.calls[index]["payload"]


@pytest.fixture
def transport(monkeypatch):
    def install(provider: str, replies: list[dict[str, Any]], **overrides: Any) -> _Transport:
        captured = _Transport(replies)
        monkeypatch.setattr(llm, "resolve_credentials", lambda *a, **k: _credentials(provider, **overrides))
        monkeypatch.setattr(llm, "_post_json", captured)
        return captured

    return install


def _turn(provider: str, transport: _Transport, **kwargs: Any) -> llm.ModelReply:
    call = {
        ANTHROPIC: llm._anthropic_tool_turn,
        OPENAI_COMPATIBLE: llm._openai_chat_tool_turn,
        OPENAI_RESPONSES: llm._responses_tool_turn,
    }[provider]
    return call(
        instructions=INSTRUCTIONS,
        tools=[_TOOL],
        max_tokens=1234,
        model=kwargs.pop("model", None),
        **kwargs,
    )


# ── request shaping ──────────────────────────────────────────────────────────


def test_anthropic_sends_input_schema_and_a_top_level_system_prompt(transport):
    t = transport(ANTHROPIC, [{"content": [{"type": "text", "text": "ok"}]}])

    _turn(ANTHROPIC, t, messages=[{"role": "user", "content": GOAL}])

    body = t.last["payload"]
    assert t.last["url"].endswith("/v1/messages")
    assert t.last["headers"]["x-api-key"] == "test-key"
    assert t.last["headers"]["anthropic-version"] == "2023-06-01"
    # Anthropic takes the system prompt as a field, not as a message.
    assert body["system"] == INSTRUCTIONS
    assert body["messages"] == [{"role": "user", "content": GOAL}]
    assert body["max_tokens"] == 1234
    assert body["tools"] == [
        {
            "name": "validate_godot_project",
            "description": "Check a generated Godot project.",
            "input_schema": _TOOL["parameters"],
        }
    ]


def test_anthropic_splits_text_from_tool_use(transport):
    t = transport(
        ANTHROPIC,
        [
            {
                "content": [
                    {"type": "text", "text": "checking"},
                    {"type": "tool_use", "id": "t1", "name": "validate_godot_project", "input": {"project_file": "p"}},
                ]
            }
        ],
    )

    reply = _turn(ANTHROPIC, t, messages=[{"role": "user", "content": GOAL}])

    assert reply.text == "checking"
    assert [(c.id, c.name, c.arguments) for c in reply.tool_calls] == [
        ("t1", "validate_godot_project", {"project_file": "p"})
    ]
    # The echo block is what the loop feeds back, so its arguments must be the
    # JSON string the next projection expects to parse.
    echoed = [b for b in reply.raw["output"] if b["type"] == "function_call"]
    assert json.loads(echoed[0]["arguments"]) == {"project_file": "p"}
    assert echoed[0]["call_id"] == "t1"


def test_anthropic_puts_the_tool_result_in_a_following_user_turn(transport):
    t = transport(ANTHROPIC, [{"content": [{"type": "text", "text": "done"}]}])

    _turn(
        ANTHROPIC,
        t,
        messages=[
            {"role": "user", "content": GOAL},
            {"type": "function_call", "call_id": "t1", "name": "validate_godot_project", "arguments": '{"project_file": "p"}'},
            {"type": "function_call_output", "call_id": "t1", "output": '{"status": "ok"}'},
        ],
    )

    assert t.last["payload"]["messages"] == [
        {"role": "user", "content": GOAL},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "validate_godot_project",
                    "input": {"project_file": "p"},
                }
            ],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": '{"status": "ok"}'}],
        },
    ]


def test_anthropic_merges_text_and_tool_use_into_one_assistant_turn(transport):
    """A turn that both speaks and calls must not become two assistant messages."""

    t = transport(ANTHROPIC, [{"content": [{"type": "text", "text": "done"}]}])

    _turn(
        ANTHROPIC,
        t,
        messages=[
            {"role": "user", "content": GOAL},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "thinking"}]},
            {"type": "function_call", "call_id": "t1", "name": "validate_godot_project", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "t1", "output": "{}"},
        ],
    )

    messages = t.last["payload"]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[1]["content"] == [
        {"type": "text", "text": "thinking"},
        {"type": "tool_use", "id": "t1", "name": "validate_godot_project", "input": {}},
    ]


def test_openai_chat_nests_tools_under_function_and_keys_results_by_call_id(transport):
    t = transport(
        OPENAI_COMPATIBLE,
        [{"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "validate_godot_project", "arguments": '{"project_file": "p"}'}}
        ]}}]}],
    )

    reply = _turn(
        OPENAI_COMPATIBLE,
        t,
        messages=[
            {"role": "user", "content": GOAL},
            {"type": "function_call", "call_id": "c1", "name": "validate_godot_project", "arguments": '{"project_file": "p"}'},
            {"type": "function_call_output", "call_id": "c1", "output": '{"status": "ok"}'},
        ],
    )

    body = t.last["payload"]
    assert t.last["url"].endswith("/chat/completions")
    assert t.last["headers"]["Authorization"] == "Bearer test-key"
    assert body["messages"][0] == {"role": "system", "content": INSTRUCTIONS}
    assert body["messages"][1] == {"role": "user", "content": GOAL}
    assert body["messages"][2] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "validate_godot_project", "arguments": '{"project_file": "p"}'},
            }
        ],
    }
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": '{"status": "ok"}'}
    assert body["tools"] == [{"type": "function", "function": {
        "name": "validate_godot_project",
        "description": "Check a generated Godot project.",
        "parameters": _TOOL["parameters"],
    }}]
    assert [(c.id, c.name, c.arguments) for c in reply.tool_calls] == [
        ("c1", "validate_godot_project", {"project_file": "p"})
    ]


def test_openai_chat_parses_a_text_only_reply(transport):
    transport(OPENAI_COMPATIBLE, [{"choices": [{"message": {"role": "assistant", "content": "  all good  "}}]}])

    reply = _turn(OPENAI_COMPATIBLE, transport, messages=[{"role": "user", "content": GOAL}])

    assert reply.text == "all good"
    assert reply.tool_calls == []


def test_openai_chat_without_choices_is_an_error(transport):
    transport(OPENAI_COMPATIBLE, [{"choices": []}])

    with pytest.raises(llm.LLMError, match="no choices"):
        _turn(OPENAI_COMPATIBLE, transport, messages=[{"role": "user", "content": GOAL}])


def test_responses_payload_is_unchanged_by_the_other_providers(transport):
    t = transport(OPENAI_RESPONSES, [{"output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}])
    messages = [{"role": "user", "content": GOAL}]

    reply = _turn(OPENAI_RESPONSES, t, messages=messages)

    body = t.last["payload"]
    assert t.last["url"].endswith("/responses")
    assert body["input"] == messages
    assert body["instructions"] == INSTRUCTIONS
    assert body["max_output_tokens"] == 1234
    # Responses already speaks this shape, so the tool is passed through whole.
    assert body["tools"] == [_TOOL]
    assert reply.text == "ok"


def test_sampling_params_follow_the_model_not_the_provider(transport):
    """GPT-6 rejects temperature outright, so it must not be sent at all."""

    unsampled = transport(OPENAI_COMPATIBLE, [{"choices": [{"message": {"content": "ok"}}]}], model="gpt-6-astra")
    _turn(OPENAI_COMPATIBLE, unsampled, messages=[{"role": "user", "content": GOAL}], model="gpt-6-astra")
    assert "temperature" not in unsampled.last["payload"]

    sampled = transport(OPENAI_COMPATIBLE, [{"choices": [{"message": {"content": "ok"}}]}], model="gpt-4o-mini")
    _turn(OPENAI_COMPATIBLE, sampled, messages=[{"role": "user", "content": GOAL}], model="gpt-4o-mini")
    assert sampled.last["payload"]["temperature"] == 0.2

    anthropic = transport(ANTHROPIC, [{"content": [{"type": "text", "text": "ok"}]}])
    _turn(ANTHROPIC, anthropic, messages=[{"role": "user", "content": GOAL}])
    assert anthropic.last["payload"]["temperature"] == 0.2


# ── failure modes ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("provider", [ANTHROPIC, OPENAI_COMPATIBLE])
def test_a_missing_key_is_a_loud_failure_not_a_degraded_run(transport, provider):
    t = transport(provider, [], api_key="")

    with pytest.raises(llm.LLMError, match="No API key configured"):
        _turn(provider, t, messages=[{"role": "user", "content": GOAL}])
    assert t.calls == []


def test_an_unmapped_provider_raises_instead_of_guessing_a_wire_format(monkeypatch):
    monkeypatch.setattr(llm, "resolve_credentials", lambda *a, **k: _credentials("mystery"))

    with pytest.raises(llm.LLMError, match="not implemented"):
        llm.complete_with_tools(
            instructions=INSTRUCTIONS,
            messages=[{"role": "user", "content": GOAL}],
            tools=[_TOOL],
        )


# ── the loop, per provider, over the real registry ───────────────────────────

# The Godot bridge only accepts paths inside its own sandbox prefix, so the
# fixture project has to live under generated/godot like a real session does --
# pointing it at a bare tmp_path is refused before the tool ever runs.
PROJECT = "generated/godot/tool-call-test/project.godot"

_CALL_BY_PROVIDER: dict[str, dict[str, Any]] = {
    ANTHROPIC: {
        "content": [
            {
                "type": "tool_use",
                "id": "c1",
                "name": "validate_godot_project",
                "input": {"project_file": PROJECT},
            }
        ]
    },
    OPENAI_COMPATIBLE: {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "validate_godot_project",
                                "arguments": json.dumps({"project_file": PROJECT}),
                            },
                        }
                    ],
                }
            }
        ]
    },
    OPENAI_RESPONSES: {
        "output": [
            {
                "type": "function_call",
                "call_id": "c1",
                "name": "validate_godot_project",
                "arguments": json.dumps({"project_file": PROJECT}),
            }
        ]
    },
}

_FINAL_BY_PROVIDER: dict[str, dict[str, Any]] = {
    ANTHROPIC: {"content": [{"type": "text", "text": "the project is valid"}]},
    OPENAI_COMPATIBLE: {"choices": [{"message": {"role": "assistant", "content": "the project is valid"}}]},
    OPENAI_RESPONSES: {
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "the project is valid"}]}]
    },
}

# An EXECUTE-tier tool the model asks for without a grant: the refusal has to
# come from the registry gate, on every transport, before the bridge is reached.
_REFUSED_CALL_BY_PROVIDER: dict[str, dict[str, Any]] = {
    ANTHROPIC: {
        "content": [
            {"type": "tool_use", "id": "c1", "name": "run_godot_import", "input": {"project_file": PROJECT}}
        ]
    },
    OPENAI_COMPATIBLE: {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "run_godot_import",
                                "arguments": json.dumps({"project_file": PROJECT}),
                            },
                        }
                    ]
                }
            }
        ]
    },
    OPENAI_RESPONSES: {
        "output": [
            {
                "type": "function_call",
                "call_id": "c1",
                "name": "run_godot_import",
                "arguments": json.dumps({"project_file": PROJECT}),
            }
        ]
    },
}


def _project(workspace) -> None:
    """Write a minimal *valid* generated project, so the bridge reports no issues.

    The validation request defaults to requiring a main scene and at least one
    script, exactly like a real ``generated/godot/sessions/<id>/<name>/`` does.
    """

    root = workspace / PROJECT.rsplit("/", 1)[0]
    root.mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text(
        'config_version=5\n\n[application]\n\nrun/main_scene="res://scenes/main.tscn"\n'
        'renderer/rendering_method="gl_compatibility"\n',
        encoding="utf-8",
    )
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    (root / "scenes" / "main.tscn").write_text("[gd_scene format=3]\n", encoding="utf-8")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "main.gd").write_text("extends Node3D\n", encoding="utf-8")


def _transcript(provider: str, body: dict[str, Any]) -> list[dict[str, Any]]:
    """The conversation a request carried, under that provider's own field name."""

    return body.get("input") if provider == OPENAI_RESPONSES else body.get("messages") or []


def _tool_result_of(provider: str, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the tool result in a request, in that provider's own shape."""

    for message in messages:
        if provider == ANTHROPIC:
            content = message.get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    return block
            continue
        if provider == OPENAI_COMPATIBLE and message.get("role") == "tool":
            return message
        if provider == OPENAI_RESPONSES and message.get("type") == "function_call_output":
            return message
    return None


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_the_loop_accepts_a_tool_call_on_every_provider(transport, tmp_path, provider):
    """A model tool call reaches the real bridge, whatever the transport is.

    Only the HTTP layer is stubbed: the tool that runs is the actual Godot
    bridge, reached through the actual registry, so this covers the seam the
    user cares about -- "the built-in API can call the tools".
    """

    from fantasy_agent.agent_loop import run_agent

    _project(tmp_path)
    t = transport(provider, [_CALL_BY_PROVIDER[provider], _FINAL_BY_PROVIDER[provider]])

    result = run_agent(GOAL, registry=engine_registry(tmp_path))

    assert result.ok, result.error
    assert result.answer == "the project is valid"
    assert result.tool_calls == 1
    assert result.refusals == []

    step = result.steps[0].calls[0]
    assert step["name"] == "validate_godot_project"
    assert step["status"] == "ok"
    assert "validated" in step["content"].lower()

    # The tool list reached the model in this provider's own schema shape.
    tools = t.body(0)["tools"]
    assert tools, "no tools were advertised to the model"
    if provider == ANTHROPIC:
        assert set(tools[0]) == {"name", "description", "input_schema"}
    elif provider == OPENAI_COMPATIBLE:
        assert set(tools[0]) == {"type", "function"}
        assert set(tools[0]["function"]) == {"name", "description", "parameters"}
    else:
        assert set(tools[0]) == {"type", "name", "description", "parameters"}

    # And the result went back in this provider's own result shape.
    result_block = _tool_result_of(provider, _transcript(provider, t.body(1)))
    assert result_block is not None, f"no tool result in the {provider} follow-up request"
    if provider == ANTHROPIC:
        assert result_block["tool_use_id"] == "c1"
    elif provider == OPENAI_COMPATIBLE:
        assert result_block["tool_call_id"] == "c1"
    else:
        assert result_block["call_id"] == "c1"


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_the_permission_gate_is_not_provider_specific(transport, tmp_path, provider):
    """A refused tool stays refused on every transport."""

    from fantasy_agent.agent_loop import run_agent

    transport(provider, [_REFUSED_CALL_BY_PROVIDER[provider], _FINAL_BY_PROVIDER[provider]])

    result = run_agent(
        "import it",
        registry=engine_registry(tmp_path),
        permission_ceiling="execute",
    )

    assert result.ok
    assert result.refusals == ["run_godot_import"]
