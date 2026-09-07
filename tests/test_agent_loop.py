"""Tests for the tool registry and the bounded agent loop.

The point of these tests is the guardrails, not the happy path: a loop that
can call tools is only acceptable if it cannot escalate its own permissions,
cannot run forever, and cannot take the deterministic fallback down with it.
"""

from __future__ import annotations

import pytest

from fantasy_agent import llm
from fantasy_agent.agent_loop import AgentRunResult, run_agent
from fantasy_agent.tool_registry import (
    EXECUTE,
    READ_ONLY,
    WRITE,
    ToolRegistry,
    ToolSpec,
    default_registry,
    validate_contract_refs,
)


# ── registry ─────────────────────────────────────────────────────────────────


def test_planning_tools_are_all_read_only():
    """Nothing exposed to the model by default may write or launch."""

    registry = default_registry()
    assert registry.names()
    for name in registry.names():
        assert registry.get(name).permission == READ_ONLY, f"{name} is not read-only"


def test_schemas_cap_at_the_permission_ceiling():
    registry = ToolRegistry()
    registry.register(ToolSpec("read", "d", {"type": "object"}, lambda _: "ok", READ_ONLY))
    registry.register(ToolSpec("write", "d", {"type": "object"}, lambda _: "ok", WRITE))
    registry.register(ToolSpec("run", "d", {"type": "object"}, lambda _: "ok", EXECUTE))

    assert [s["name"] for s in registry.schemas(up_to=READ_ONLY)] == ["read"]
    assert [s["name"] for s in registry.schemas(up_to=WRITE)] == ["read", "write"]
    assert [s["name"] for s in registry.schemas(up_to=EXECUTE)] == ["read", "run", "write"]


def test_write_and_execute_are_refused_without_a_grant():
    registry = ToolRegistry()
    registry.register(ToolSpec("save", "d", {"type": "object"}, lambda _: "ok", WRITE))
    registry.register(ToolSpec("launch", "d", {"type": "object"}, lambda _: "ok", EXECUTE))

    assert registry.call("save", {}).status == "refused"
    assert registry.call("launch", {}).status == "refused"
    # A grant only unlocks its own tier.
    assert registry.call("save", {}, allow_write=True).status == "ok"
    assert registry.call("launch", {}, allow_execute=True).status == "ok"


def test_refusal_is_returned_not_raised():
    """The loop must survive a refusal and keep going."""

    registry = ToolRegistry()
    registry.register(ToolSpec("save", "d", {"type": "object"}, lambda _: "ok", WRITE))

    outcome = registry.call("save", {})

    assert outcome.status == "refused"
    assert "save" in outcome.content


def test_unknown_tool_is_an_error_outcome():
    assert default_registry().call("nope", {}).status == "error"


def test_handler_exception_does_not_escape():
    def boom(_arguments):
        raise RuntimeError("kaboom")

    registry = ToolRegistry()
    registry.register(ToolSpec("bad", "d", {"type": "object"}, boom))

    outcome = registry.call("bad", {})

    assert outcome.status == "error"
    assert "kaboom" in outcome.content


def test_unknown_permission_is_rejected_at_registration():
    registry = ToolRegistry()
    with pytest.raises(ValueError):
        registry.register(ToolSpec("x", "d", {"type": "object"}, lambda _: "ok", "sudo"))


def test_declared_mcp_contracts_still_resolve():
    """These refs were never parsed by any code; this keeps them honest."""

    from fantasy_agent.mcp import initial_mcp_contracts

    # Guard against the check passing simply because it looked at nothing.
    assert len(initial_mcp_contracts()) == 17
    assert validate_contract_refs() == []


def test_contract_validation_detects_a_broken_ref(monkeypatch):
    """The guard must actually fail when a YAML anchor disappears."""

    from fantasy_agent import mcp as mcp_module

    original = mcp_module.initial_mcp_contracts

    def broken():
        contracts = original()
        first = contracts[0].model_copy(
            update={"input_schema_ref": "mcp/unreal-mcp/tools.yaml#no_such_tool"}
        )
        return [first, *contracts[1:]]

    # validate_contract_refs imports the symbol inside the function body, so
    # patching the source module is what takes effect.
    monkeypatch.setattr(mcp_module, "initial_mcp_contracts", broken)

    problems = validate_contract_refs()
    assert problems and "no_such_tool" in problems[0]


# ── Responses API parsing ────────────────────────────────────────────────────


def test_parses_message_and_function_call_blocks():
    reply = llm._parse_responses_reply(
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Let me check."}],
                },
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "render_gdd",
                    "arguments": '{"prompt": "rooftop parkour chase"}',
                },
            ]
        }
    )

    assert reply.text == "Let me check."
    assert len(reply.tool_calls) == 1
    assert reply.tool_calls[0].id == "call_1"
    assert reply.tool_calls[0].name == "render_gdd"
    assert reply.tool_calls[0].arguments == {"prompt": "rooftop parkour chase"}


def test_function_call_arguments_arrive_as_a_json_string():
    reply = llm._parse_responses_reply(
        {
            "output": [
                {
                    "type": "function_call",
                    "call_id": "c",
                    "name": "x",
                    "arguments": '{"a": {"b": 1}}',
                }
            ]
        }
    )
    assert reply.tool_calls[0].arguments == {"a": {"b": 1}}


def test_malformed_arguments_become_empty_dict():
    reply = llm._parse_responses_reply(
        {"output": [{"type": "function_call", "call_id": "c", "name": "x", "arguments": "{oops"}]}
    )
    assert reply.tool_calls[0].arguments == {}


def test_gpt6_never_receives_temperature():
    from fantasy_agent.api_settings import supports_sampling_params

    assert not supports_sampling_params("gpt-6-astra")
    assert not supports_sampling_params("o3-mini")
    assert supports_sampling_params("gpt-4o-mini")


# ── the loop ─────────────────────────────────────────────────────────────────


class _FakeResponses:
    """Minimal Responses API stand-in: yields queued replies, records calls."""

    def __init__(self, replies: list[llm.ModelReply]):
        self.replies = list(replies)
        self.payloads: list[dict] = []

    def __call__(self, *, instructions, messages, tools, max_tokens=0, model=None):
        self.payloads.append(
            {"instructions": instructions, "messages": list(messages), "tools": tools}
        )
        if not self.replies:
            raise AssertionError("loop called the model more times than queued")
        return self.replies.pop(0)


@pytest.fixture
def fake_complete(monkeypatch):
    def install(replies: list[llm.ModelReply]):
        fake = _FakeResponses(replies)
        monkeypatch.setattr("fantasy_agent.agent_loop.complete_with_tools", fake)
        return fake

    return install


def _call(name: str, call_id: str = "c1", **arguments) -> llm.ModelReply:
    return llm.ModelReply(
        text="",
        tool_calls=[llm.ToolCallRequest(id=call_id, name=name, arguments=arguments)],
        raw={"output": [{"type": "function_call", "call_id": call_id, "name": name}]},
    )


def test_loop_stops_when_the_model_stops_calling(fake_complete):
    fake = fake_complete(
        [_call("decompose_production_tasks", prompt="rooftop parkour chase"), llm.ModelReply(text="done")]
    )

    result = run_agent("break this idea into tasks")

    assert result.ok
    assert result.answer == "done"
    assert result.tool_calls == 1
    assert len(fake.payloads) == 2


def test_loop_hits_the_turn_ceiling_instead_of_running_forever(fake_complete):
    # A model that always calls another tool: the ceiling must stop it.
    fake_complete([_call(f"tool_{i}", call_id=f"c{i}") for i in range(50)])

    result = run_agent("loop forever", max_turns=3)

    assert result.status == "max_turns"
    assert len(result.steps) == 3


def test_tool_results_are_fed_back_with_matching_call_ids(fake_complete):
    fake = fake_complete(
        [
            _call("decompose_production_tasks", call_id="abc", prompt="rooftop parkour chase"),
            llm.ModelReply(text="here you go"),
        ]
    )

    run_agent("tasks please")

    second_input = fake.payloads[1]["messages"]
    outputs = [m for m in second_input if m.get("type") == "function_call_output"]
    assert outputs and outputs[0]["call_id"] == "abc"


def test_a_refused_tool_does_not_kill_the_loop(fake_complete):
    from fantasy_agent.tool_registry import ToolSpec

    registry = ToolRegistry()
    registry.register(ToolSpec("launch", "d", {"type": "object"}, lambda _: "ok", EXECUTE))
    fake_complete([_call("launch"), llm.ModelReply(text="cannot run it, but here is the plan")])

    result = run_agent("run it", registry=registry, permission_ceiling=EXECUTE)

    assert result.ok
    assert result.refusals == ["launch"]
    assert result.answer


def test_llm_failure_returns_error_status_for_the_caller_to_fall_back(monkeypatch):
    def boom(**_kwargs):
        raise llm.LLMError("provider unreachable")

    monkeypatch.setattr("fantasy_agent.agent_loop.complete_with_tools", boom)

    result = run_agent("anything")

    assert result.status == "error"
    assert "unreachable" in result.error
    assert not result.ok


def test_only_read_only_tools_are_shown_by_default(fake_complete):
    fake = fake_complete([llm.ModelReply(text="ok")])

    run_agent("hello")

    names = [t["name"] for t in fake.payloads[0]["tools"]]
    assert "generate_game_production_plan" in names
    assert all(not n.startswith("run_") for n in names)


def test_result_exposes_what_happened_for_the_ui():
    result = AgentRunResult(status="done", answer="x")
    assert result.ok
    assert AgentRunResult(status="error").ok is False
