"""One registry for every tool an agent may call.

Before this module the project had four inventories that did not know about
each other: ``mcp/*.yaml`` (never parsed by any code), ``fantasy_agent/mcp.py``
(hand-written contracts served only to the UI), the ``if name == ...`` chain in
the Studio app (the real dispatcher), and ``skills/*.md`` (prose). Adding a
tool meant touching three of them by hand, and nothing failed if they drifted.

This module makes the registry the single source of truth:

- a tool declares its JSON schema, its permission tier and its handler once;
- the same record feeds the model's tool list, the permission gate and the UI;
- ``validate_contract_refs`` is the guard that keeps the declared MCP
  contracts and the YAML schemas from drifting apart again.

Permission tiers exist because AGENTS.md forbids running a local tool with
real side effects before its effects are declared and confirmed. The loop
therefore never decides *whether* it may act -- only *what* to attempt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

READ_ONLY = "read_only"  # computes and returns a plan; never writes or launches
WRITE = "write"  # writes under generated/
EXECUTE = "execute"  # launches Blender / Godot / Unreal / ComfyUI

PERMISSIONS = (READ_ONLY, WRITE, EXECUTE)


class ToolPermissionError(RuntimeError):
    """Raised when a call is attempted without the matching permission grant."""


@dataclass
class ToolSpec:
    """One callable tool, with everything the loop and the UI needs."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    permission: str = READ_ONLY
    server: str = "fantasy-agent"

    def model_schema(self) -> dict[str, Any]:
        """The shape handed to the model (Responses API function tool)."""

        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }


@dataclass
class ToolOutcome:
    """Result of one tool call, safe to feed straight back to the model."""

    name: str
    status: str  # ok | refused | error
    content: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "content": self.content,
            "data": self.data,
        }


class ToolRegistry:
    """Name -> ToolSpec, with the permission gate applied on every call."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.permission not in PERMISSIONS:
            raise ValueError(f"unknown permission {spec.permission!r}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self, *, up_to: str = READ_ONLY) -> list[dict[str, Any]]:
        """Tool schemas the model may see, capped at a permission tier."""

        ceiling = PERMISSIONS.index(up_to)
        return [
            spec.model_schema()
            for spec in sorted(self._tools.values(), key=lambda s: s.name)
            if PERMISSIONS.index(spec.permission) <= ceiling
        ]

    def call(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        allow_write: bool = False,
        allow_execute: bool = False,
    ) -> ToolOutcome:
        """Run one tool, refusing anything the caller did not grant.

        A refusal is returned rather than raised so the loop can hand the
        refusal back to the model and let it continue with what it has.
        """

        spec = self._tools.get(name)
        if spec is None:
            return ToolOutcome(
                name,
                "error",
                f"unknown tool {name!r}; available: {', '.join(self.names())}",
            )

        if spec.permission == EXECUTE and not allow_execute:
            return ToolOutcome(
                name,
                "refused",
                f"{name} launches a local tool and requires explicit execution "
                "confirmation; it was not run.",
            )
        if spec.permission == WRITE and not (allow_write or allow_execute):
            return ToolOutcome(
                name,
                "refused",
                f"{name} writes files and requires write confirmation; it was not run.",
            )

        try:
            payload = spec.handler(arguments or {})
        except Exception as exc:  # noqa: BLE001 - a bad tool call must not kill the loop
            return ToolOutcome(name, "error", f"{type(exc).__name__}: {exc}")

        if isinstance(payload, ToolOutcome):
            return payload
        text, data = _split_result(payload)
        return ToolOutcome(name, "ok", text, data)


def _split_result(payload: Any) -> tuple[str, dict[str, Any]]:
    """Reduce a workflow result to (model-visible text, structured data)."""

    if isinstance(payload, dict):
        data = payload.get("data")
        text = payload.get("message") or payload.get("summary") or ""
        if not isinstance(data, dict):
            data = payload
        return str(text)[:4000], data
    if hasattr(payload, "model_dump"):
        return str(payload)[:500], payload.model_dump(mode="json")
    return str(payload)[:4000], {}


# Every registered planning tool is read-only: it computes a plan and returns
# it. Nothing here writes or launches, which is what makes it safe to expose to
# a model in the first place.
_PROMPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["prompt"],
    "properties": {
        "prompt": {
            "type": "string",
            "minLength": 8,
            "description": "Raw gameplay idea.",
        },
        "target_minutes": {
            "type": "integer",
            "minimum": 5,
            "maximum": 15,
            "description": "Target session length. Defaults to 10.",
        },
        "engine_version": {
            "type": "string",
            "description": "Target engine label, e.g. 'Godot 4' or 'UE5'.",
        },
    },
}

_SEED_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["raw_idea"],
    "properties": {
        "raw_idea": {
            "type": "string",
            "minLength": 4,
            "description": "Unstructured initial game idea.",
        },
        "target_minutes": {"type": "integer", "minimum": 5, "maximum": 15},
    },
}


def default_registry() -> ToolRegistry:
    """The planning tools, wired to the deterministic workflows."""

    from fantasy_agent.idea_discovery import extract_idea_seed
    from fantasy_agent.workflows import (
        decompose_production_tasks,
        run_director_workflow,
    )
    from fantasy_agent.contracts import IdeaDiscoveryRequest, PromptRequest

    registry = ToolRegistry()

    def _seed(arguments: dict[str, Any]) -> dict[str, Any]:
        request = IdeaDiscoveryRequest.model_validate(arguments)
        seed = extract_idea_seed(request)
        return {
            "message": f"IdeaSeed: core action '{seed.core_action}'.",
            "data": {"idea_seed": seed.model_dump(mode="json")},
        }

    def _plan(arguments: dict[str, Any]) -> dict[str, Any]:
        request = PromptRequest.model_validate(arguments)
        plan = run_director_workflow(request)
        spec = plan.gameplay_spec
        return {
            "message": (
                f"Production plan for '{spec.title}': {len(spec.core_loop)} loop steps, "
                f"{len(spec.level_beats)} level beats, {len(spec.systems)} systems. "
                f"Win: {spec.win_state}"
            ),
            "data": {"summary": plan.model_dump(mode="json")},
        }

    def _tasks(arguments: dict[str, Any]) -> dict[str, Any]:
        request = PromptRequest.model_validate(arguments)
        breakdown = decompose_production_tasks(request)
        return {
            "message": (
                f"{len(breakdown.tasks)} production tasks; "
                f"recommended next: {breakdown.recommended_next_task}."
            ),
            "data": {"task_breakdown": breakdown.model_dump(mode="json")},
        }

    def _gdd(arguments: dict[str, Any]) -> dict[str, Any]:
        request = PromptRequest.model_validate(arguments)
        plan = run_director_workflow(request)
        return {
            "message": f"GDD rendered for '{plan.gameplay_spec.title}'.",
            "data": {"gdd": plan.gdd.model_dump(mode="json")},
        }

    registry.register(
        ToolSpec(
            name="extract_idea_seed",
            description=(
                "Turn a vague idea into a structured IdeaSeed (core action, "
                "verbs, tone). Use this first when the idea is thin."
            ),
            input_schema=_SEED_SCHEMA,
            handler=_seed,
        )
    )
    registry.register(
        ToolSpec(
            name="generate_game_production_plan",
            description=(
                "Produce the full DirectorBuildPlan: gameplay spec, GDD, task "
                "breakdown and engine handoffs. The main planning call."
            ),
            input_schema=_PROMPT_SCHEMA,
            handler=_plan,
        )
    )
    registry.register(
        ToolSpec(
            name="decompose_production_tasks",
            description="Break an idea into ordered production tasks with a recommended next step.",
            input_schema=_PROMPT_SCHEMA,
            handler=_tasks,
        )
    )
    registry.register(
        ToolSpec(
            name="render_gdd",
            description="Render the structured game design document for an idea.",
            input_schema=_PROMPT_SCHEMA,
            handler=_gdd,
        )
    )
    return registry


def validate_contract_refs() -> list[str]:
    """Return contract refs that do not resolve in ``mcp/*.yaml``.

    ``MCPToolContract.input_schema_ref`` is currently just a documentation
    string: nothing parses it, so a broken or renamed anchor went unnoticed.
    This turns that silent drift into a failing test.
    """

    import yaml

    from fantasy_agent.mcp import initial_mcp_contracts

    root = _mcp_root()
    problems: list[str] = []
    for contract in initial_mcp_contracts():
        for ref in (contract.input_schema_ref, contract.output_schema_ref):
            path, _, anchor = ref.partition("#")
            target = root / path
            if not target.exists():
                problems.append(f"{contract.name}: missing file {path}")
                continue
            document = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
            tools = document.get("tools") or {}
            head = anchor.split(".")[0]
            if head and head not in tools:
                problems.append(f"{contract.name}: {path} has no tool '{head}'")
    return problems


def _mcp_root() -> "Path":  # noqa: F821 - local import keeps this module light
    from pathlib import Path

    return Path(__file__).resolve().parents[1]
