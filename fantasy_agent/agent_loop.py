"""A bounded, permission-gated agent loop.

This exists because the deterministic pipeline cannot answer open-ended
planning questions ("compare two directions for this idea", "what is missing
before this is playable"). For those, letting the model decide *which* planning
tool to call and how many times is genuinely better than a fixed chain.

What is deliberately NOT handed to the model:

- **Whether it may act.** Every tool carries a permission tier, and the gate
  lives in ``ToolRegistry``, outside the loop. The model can only attempt; it
  can never escalate. A refusal comes back as a tool result so the loop can
  continue instead of dying.
- **How long it may run.** ``max_turns`` is a hard ceiling. Without it a
  misbehaving model burns a 1M-token context on a planning question.
- **Whether the run succeeded.** Any ``LLMError`` returns ``status="error"``
  and the caller falls back to the deterministic pipeline, exactly like the
  existing ``complete_json`` contract. The loop is an addition, never a
  replacement -- the guarantee "a demo always gets built" still holds on the
  deterministic path underneath.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from fantasy_agent.llm import LLMError, complete_with_tools
from fantasy_agent.tool_registry import READ_ONLY, ToolOutcome, ToolRegistry, default_registry

DEFAULT_MAX_TURNS = 8

SYSTEM_PROMPT = (
    "You are the planning agent for Fantasy Agent, a gameplay-first game "
    "production pipeline. Use the provided tools to inspect and develop a game "
    "idea. Prefer the fewest tool calls that answer the question. "
    "Tool results marked 'refused' were not executed and cannot be retried by "
    "asking again -- work with what you have and say what is missing."
)


@dataclass
class AgentStep:
    """One turn: what the model said, what it called, what came back."""

    text: str = ""
    calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentRunResult:
    """Outcome of a whole loop run."""

    status: str  # done | max_turns | error | no_provider
    answer: str = ""
    steps: list[AgentStep] = field(default_factory=list)
    tool_calls: int = 0
    refusals: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "done"


def run_agent(
    goal: str,
    *,
    registry: ToolRegistry | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    allow_write: bool = False,
    allow_execute: bool = False,
    instructions: str = SYSTEM_PROMPT,
    permission_ceiling: str = READ_ONLY,
) -> AgentRunResult:
    """Run the loop until the model stops calling tools or the ceiling hits.

    Args:
        goal: The user's request, in their words.
        registry: Tools the model may call. Defaults to the planning tools.
        max_turns: Hard ceiling on model round-trips.
        allow_write: Grant WRITE-tier tools. Still off unless a human confirmed.
        allow_execute: Grant EXECUTE-tier tools (launching Blender/Godot/UE).
        instructions: System prompt for the run.
        permission_ceiling: Highest tier to even *show* the model.
    """

    tools = registry or default_registry()
    schemas = tools.schemas(up_to=permission_ceiling)
    messages: list[dict[str, Any]] = [{"role": "user", "content": goal}]

    result = AgentRunResult(status="max_turns")
    for _ in range(max(1, max_turns)):
        try:
            reply = complete_with_tools(
                instructions=instructions,
                messages=messages,
                tools=schemas,
            )
        except LLMError as exc:
            result.status = "error"
            result.error = str(exc)
            return result

        step = AgentStep(text=reply.text)
        result.steps.append(step)

        if not reply.tool_calls:
            result.status = "done"
            result.answer = reply.text
            return result

        # Echo the assistant blocks back verbatim so the Responses API can
        # match each function_call_output to its call_id.
        messages.extend(block for block in reply.raw.get("output") or [] if isinstance(block, dict))

        for call in reply.tool_calls:
            outcome = tools.call(
                call.name,
                call.arguments,
                allow_write=allow_write,
                allow_execute=allow_execute,
            )
            result.tool_calls += 1
            step.calls.append(
                {
                    "name": call.name,
                    "arguments": call.arguments,
                    "status": outcome.status,
                    "content": outcome.content[:500],
                }
            )
            if outcome.status == "refused":
                result.refusals.append(call.name)
            messages.append(
                {
                    "type": "function_call_output",
                    "call_id": call.id,
                    "output": json.dumps(outcome.as_json(), ensure_ascii=False),
                }
            )

    result.answer = _last_text(result.steps)
    return result


def _last_text(steps: list[AgentStep]) -> str:
    for step in reversed(steps):
        if step.text:
            return step.text
    return ""


__all__ = [
    "AgentRunResult",
    "AgentStep",
    "DEFAULT_MAX_TURNS",
    "SYSTEM_PROMPT",
    "ToolOutcome",
    "run_agent",
]
