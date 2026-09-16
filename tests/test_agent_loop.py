"""Tests for the tool registry and the bounded agent loop.

The point of these tests is the guardrails, not the happy path: a loop that
can call tools is only acceptable if it cannot escalate its own permissions,
cannot run forever, and cannot take the deterministic fallback down with it.
"""

from __future__ import annotations

from typing import Any

import pytest

from fantasy_agent import llm
from fantasy_agent.agent_loop import AgentRunResult, run_agent
from fantasy_agent.tool_registry import (
    _ENGINE_HIDDEN_ARGS,
    _HIDDEN_ARG_SOURCES,
    _HIDDEN_ARG_WITHOUT_SOURCE,
    EXECUTE,
    READ_ONLY,
    WRITE,
    ToolRegistry,
    ToolSpec,
    combined_registry,
    default_registry,
    engine_registry,
    exposed_executable_args,
    permission_from_annotations,
    unimplemented_contracts,
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


# ── engine tools ─────────────────────────────────────────────────────────────


def test_engine_registry_covers_every_implemented_contract():
    """Every MCP contract with a bridge behind it must be callable."""

    names = engine_registry().names()
    assert len(names) == 16
    assert "run_godot_import" in names
    assert "publish_prototype_branch" not in names


def test_only_the_github_contract_is_left_unimplemented():
    """Pin the known gap, so implementing it (or deleting it) fails loudly."""

    assert unimplemented_contracts() == ["publish_prototype_branch"]


def test_permission_tier_follows_the_mcp_annotations():
    """Validate/probe stay free; prepare writes; only run_* launches."""

    registry = engine_registry()
    for name in ("validate_godot_project", "validate_asset_ingest", "probe_comfyui_capabilities"):
        assert registry.get(name).permission == READ_ONLY, name
    for name in ("create_godot_project_structure", "prepare_asset_ingest"):
        assert registry.get(name).permission == WRITE, name
    for name in ("run_godot_import", "run_asset_ingest", "generate_asset_batch"):
        assert registry.get(name).permission == EXECUTE, name


def test_annotations_map_onto_tiers_the_way_the_gate_expects():
    assert permission_from_annotations({"readOnlyHint": True}) == READ_ONLY
    assert permission_from_annotations({"readOnlyHint": False, "idempotentHint": True}) == WRITE
    assert permission_from_annotations({"readOnlyHint": False, "idempotentHint": False}) == EXECUTE


def test_plan_is_hidden_from_the_model_and_injected_from_the_run():
    """The model asks for the work; it must not invent a GodotProjectPlan."""

    registry = engine_registry()
    spec = registry.get("create_godot_project_structure")
    assert spec.plan_key == "godot_plan"
    assert "plan" not in spec.model_schema()["parameters"]["properties"]
    assert "plan" not in spec.model_schema()["parameters"].get("required", [])

    seen: dict = {}

    def spy(arguments):
        seen.update(arguments)
        return "ok"

    spec.handler = spy
    registry.artifacts["godot_plan"] = {"project_name": "rooftop"}

    registry.call("create_godot_project_structure", {}, allow_write=True)
    assert seen["plan"] == {"project_name": "rooftop"}


def test_hiding_the_plan_shrinks_the_schema_dramatically():
    """Otherwise the Godot tool alone would ship ~19KB of unreachable $defs."""

    import json

    spec = engine_registry().get("create_godot_project_structure")
    assert len(json.dumps(spec.model_schema())) < 4000


def test_a_hidden_argument_the_model_sent_is_discarded():
    """Hiding an argument takes it out of the schema. It does not stop a model.

    So the registry settles these by discarding whatever arrived and then
    filling from this run's own stores. Keeping the model's value instead --
    which is what an ``if args.get(...)`` guard does -- means a Godot call
    carrying its own ``gameplay_spec`` builds a project the rest of the run was
    never planned around, and one carrying ``gameplay_scripts`` puts
    hand-written GDScript on disk ahead of the codegen module that is supposed
    to produce it.
    """

    seen: dict = {}

    def spy(arguments):
        seen.update(arguments)
        return "ok"

    registry = engine_registry()
    spec = registry.get("create_godot_project_structure")
    spec.handler = spy
    registry.artifacts["godot_plan"] = {"project_name": "rooftop"}
    registry.artifacts["gameplay_spec"] = {"title": "the run's own spec"}
    registry.artifacts["production_spec_bundle"] = {"numeric": {"player_hp": 5}}

    registry.call(
        "create_godot_project_structure",
        {
            "gameplay_spec": {"title": "the model's own spec"},
            "production_spec_bundle": {"numeric": {"player_hp": 99}},
            "gameplay_scripts": {"player_controller.gd": "extends Node\n"},
        },
        allow_write=True,
    )

    assert seen["gameplay_spec"] == {"title": "the run's own spec"}
    assert seen["production_spec_bundle"] == {"numeric": {"player_hp": 5}}
    assert "gameplay_scripts" not in seen, (
        "the model's own GDScript reached the bridge; godot_mcp derives the "
        "scripts from the spec it is handed"
    )


def test_a_plan_the_model_sent_does_not_satisfy_the_run():
    """The gate has to look where the plan is kept, not at what arrived.

    A plan is hidden for the same reason the spec is, and is discarded the same
    way -- so reading ``arguments`` to decide whether the run has one lets a
    call through and then hands the handler an argument set with no plan in it.
    """

    registry = engine_registry()

    outcome = registry.call(
        "create_godot_project_structure",
        {"plan": {"project_name": "invented"}, "write_files": True},
        allow_write=True,
    )

    assert outcome.status == "error"
    assert "generate_game_production_plan" in outcome.content


def test_every_hidden_argument_is_either_sourced_or_exempt():
    """A hidden argument with nothing to fill it in is one the model supplies.

    ``_ENGINE_HIDDEN_ARGS`` promises the model does not get to set these, and
    the registry enforces it by discarding whatever arrives. An argument in that
    list which no table replaces is therefore simply never set -- deliberate for
    ``gameplay_scripts``, but only if the reason is written down. Without this
    check, adding a fourth hidden argument and forgetting its source is a silent
    hole rather than a red test.
    """

    unaccounted = []
    for tool, arguments in _ENGINE_HIDDEN_ARGS.items():
        sourced = set(_HIDDEN_ARG_SOURCES.get(tool, {}))
        exempt = set(_HIDDEN_ARG_WITHOUT_SOURCE.get(tool, {}))
        for argument in arguments:
            if argument not in sourced and argument not in exempt:
                unaccounted.append(f"{tool}.{argument}")
    assert unaccounted == [], (
        f"hidden with nothing to fill it in: {unaccounted}. Add it to "
        "_HIDDEN_ARG_SOURCES, or to _HIDDEN_ARG_WITHOUT_SOURCE with the reason."
    )

    phantom = sorted(
        f"{tool}.{argument}"
        for tool, sources in _HIDDEN_ARG_SOURCES.items()
        for argument in sources
        if argument not in _ENGINE_HIDDEN_ARGS.get(tool, ())
    )
    assert phantom == [], (
        f"filled in but not hidden: {phantom}. The injection overwrites whatever "
        "arrives, so the model could never set this argument even though the "
        "schema advertises it."
    )


def test_an_engine_tool_without_a_plan_names_the_missing_step():
    registry = engine_registry()

    outcome = registry.call("create_godot_project_structure", {}, allow_write=True)

    assert outcome.status == "error"
    assert "generate_game_production_plan" in outcome.content


def test_confirmation_is_injected_only_when_granted():
    """A grant must actually unlock the tool; without one it stays refused."""

    seen: list[dict] = []
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            "save",
            "d",
            {"type": "object", "properties": {"write_files": {"type": "boolean"}}},
            lambda a: seen.append(a) or "ok",
            WRITE,
            confirm_field="write_files",
        )
    )

    assert registry.call("save", {}).status == "refused"
    assert registry.call("save", {}, allow_write=True).status == "ok"
    assert seen == [{"write_files": True}]


def test_an_explicit_false_stays_a_dry_run():
    """A model asking for a plan must get a plan, even inside a granted run."""

    seen: list[dict] = []
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            "save",
            "d",
            {"type": "object", "properties": {"write_files": {"type": "boolean"}}},
            lambda a: seen.append(a) or "ok",
            WRITE,
            confirm_field="write_files",
        )
    )

    registry.call("save", {"write_files": False}, allow_execute=True)
    assert seen == [{"write_files": False}]


def test_a_blocked_mcp_call_is_reported_as_a_refusal_not_a_failure():
    """'Not confirmed' and 'crashed' are different; the loop treats them so."""

    from fantasy_agent.tool_registry import _mcp_handler

    def dispatch(name, arguments):
        if name == "launch":
            return {
                "structuredContent": {"status": "blocked"},
                "content": [{"type": "text", "text": "not confirmed"}],
            }
        return {"isError": True, "content": [{"type": "text", "text": "crashed"}]}

    registry = ToolRegistry()
    registry.register(
        ToolSpec("launch", "d", {"type": "object"}, _mcp_handler(dispatch, "launch", None), EXECUTE)
    )
    registry.register(
        ToolSpec("boom", "d", {"type": "object"}, _mcp_handler(dispatch, "boom", None), EXECUTE)
    )

    assert registry.call("launch", {}, allow_execute=True).status == "refused"
    assert registry.call("boom", {}, allow_execute=True).status == "error"


def test_loop_harvests_the_plan_for_later_engine_calls(fake_complete):
    """An engine tool can only run if a planning result reached the store."""

    registry = combined_registry()
    fake_complete(
        [
            _call("generate_game_production_plan", prompt="rooftop parkour chase with guards"),
            llm.ModelReply(text="done"),
        ]
    )

    assert run_agent("build it", registry=registry).ok
    assert set(registry.artifacts) >= {"godot_plan", "blender_plan", "comfyui_plan", "unreal_plan"}


def test_engine_tools_appear_only_at_the_granted_tier(fake_complete):
    """Read-only checks are always offered; launching one needs a grant."""

    fake = fake_complete([llm.ModelReply(text="ok")])
    run_agent("check the project", include_engine_tools=True)
    names = [t["name"] for t in fake.payloads[0]["tools"]]
    assert "validate_godot_project" in names
    assert "run_godot_import" not in names

    fake = fake_complete([llm.ModelReply(text="ok")])
    run_agent("run the import", include_engine_tools=True, allow_execute=True)
    names = [t["name"] for t in fake.payloads[0]["tools"]]
    assert "run_godot_import" in names


# ── executable arguments ─────────────────────────────────────────────────────


def test_no_engine_tool_lets_the_model_name_an_executable():
    """Naming the binary is naming the program. That is not the model's call."""

    assert exposed_executable_args() == []


def _executable_probe_registry(probe, seen):
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            "run_godot_import",
            "d",
            {
                "type": "object",
                "properties": {
                    "project_file": {"type": "string"},
                    "godot_executable": {"type": "string"},
                },
            },
            lambda args: seen.update(args) or {"status": "ok"},
            EXECUTE,
            executable_args=("godot_executable",),
        )
    )
    return registry


def test_a_model_supplied_executable_is_overwritten(monkeypatch):
    """Hiding the arg only removes it from the schema, not from the wire.

    A model can send arguments it was never shown, so the gate has to
    overwrite rather than merely fill in.
    """

    import fantasy_agent.tool_registry as registry_module

    monkeypatch.setattr(registry_module, "_probe_executable", lambda _f: "C:/probed/godot.exe")
    seen: dict[str, Any] = {}

    _executable_probe_registry(None, seen).call(
        "run_godot_import", {"godot_executable": "C:/evil/pwn.exe"}, allow_execute=True
    )

    assert seen["godot_executable"] == "C:/probed/godot.exe"


def test_executable_is_dropped_when_nothing_is_installed(monkeypatch):
    """No probe result means the bridge default applies -- not the model's."""

    import fantasy_agent.tool_registry as registry_module

    monkeypatch.setattr(registry_module, "_probe_executable", lambda _f: None)
    seen: dict[str, Any] = {}

    _executable_probe_registry(None, seen).call(
        "run_godot_import", {"godot_executable": "C:/evil/pwn.exe"}, allow_execute=True
    )

    assert "godot_executable" not in seen
