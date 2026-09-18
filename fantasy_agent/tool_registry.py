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

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

    # Argument that unlocks the tool's real side effect, e.g. `write_files`
    # or `confirmed_side_effects`. MCP tools default it to false, so a
    # granted run would otherwise still do nothing; see ToolRegistry.call.
    confirm_field: str | None = None

    # Which sub-plan of a DirectorBuildPlan this tool's `plan` argument comes
    # from. A model cannot invent a GodotProjectPlan, and it does not have to:
    # the planning tools already produced an authoritative one for this run.
    plan_key: str | None = None

    # Arguments hidden from the model because the pipeline supplies them.
    hidden_args: tuple[str, ...] = ()

    # Arguments naming a local binary to launch. Hidden *and* overwritten on
    # every call: hiding only removes them from the advertised schema, but a
    # model can still send arguments that were never declared. Letting it
    # choose the program turns a granted run into "run anything on this
    # machine", so ToolRegistry.call replaces these with a probed path and
    # discards whatever the model sent.
    executable_args: tuple[str, ...] = ()

    def model_schema(self) -> dict[str, Any]:
        """The shape handed to the model (Responses API function tool)."""

        hidden = set(self.hidden_args) | set(self.executable_args)
        if self.plan_key:
            hidden.add("plan")

        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": _without_args(self.input_schema, hidden),
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
        # Sub-plans harvested from this run's planning calls, keyed by name
        # ("godot_plan", "blender_plan", ...). Engine tools read them here
        # instead of asking the model to reconstruct them.
        self.artifacts: dict[str, Any] = {}

    def remember_plan(self, payload: Any) -> None:
        """Store any sub-plans found in a planning tool's result."""

        if not isinstance(payload, dict):
            return
        source = payload.get("summary")
        if not isinstance(source, dict):
            source = payload
        for key in set(PLAN_KEYS.values()):
            value = source.get(key)
            if isinstance(value, dict) and value:
                self.artifacts[key] = value
        # The gameplay spec travels with the same planning result and is not a
        # sub-plan, but the Godot tool is built from it -- see
        # _HIDDEN_ARG_SOURCES for why it has to be kept.
        for key in ("gameplay_spec", "production_spec_bundle"):
            value = source.get(key)
            if isinstance(value, dict) and value:
                self.artifacts[key] = value

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

        # Read from the store, not from ``arguments``: the model's own plan is
        # discarded in ``_call_arguments``, so accepting it here would let the
        # call through and then hand the handler an argument set with no plan in
        # it at all.
        if spec.plan_key and self.artifacts.get(spec.plan_key) is None:
            return ToolOutcome(
                name,
                "error",
                f"{name} needs a {spec.plan_key}, but this run has not produced "
                "one yet; call generate_game_production_plan first.",
            )

        try:
            payload = spec.handler(self._call_arguments(spec, arguments, allow_write, allow_execute))
        except Exception as exc:  # noqa: BLE001 - a bad tool call must not kill the loop
            return ToolOutcome(name, "error", f"{type(exc).__name__}: {exc}")

        if isinstance(payload, ToolOutcome):
            return payload
        text, data = _split_result(payload)
        return ToolOutcome(name, "ok", text, data)

    def _call_arguments(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any] | None,
        allow_write: bool,
        allow_execute: bool,
    ) -> dict[str, Any]:
        """Fill in what the model must not be trusted with, or need not supply.

        Four things are settled here, all outside the model's reach:

        - the plan, from this run's planning result, so the model asks for the
          work rather than reconstructing a nested object it cannot get right;
        - the rest of the pipeline's own inputs for that tool (the gameplay spec
          and production spec bundle for the Godot tool), from the same result;
        - the confirmation flag, reflecting the grant the *caller* made. An
          explicit ``false`` from the model is left alone: that is a
          deliberate dry run;
        - the executable path, from a local probe. When nothing is installed the
          key is dropped and the bridge falls back to its own default.

        The hidden ones are *discarded-then-filled*, never filled-if-missing.
        Hiding an argument only takes it out of the advertised schema, which
        does not stop a model from sending it anyway -- the executable probe has
        always had to cope with exactly that, and that is why it overwrites. An
        ``if args.get(...)`` guard does not do the same job; it keeps the
        model's value, which is the one thing the hiding existed to prevent. A
        Godot call carrying its own ``gameplay_spec`` would then silently build
        a project the rest of the run was not planned around, and one carrying
        ``gameplay_scripts`` would put hand-written GDScript on disk ahead of
        the codegen module that is supposed to produce it.
        """

        args = dict(arguments or {})

        hidden = set(_ENGINE_HIDDEN_ARGS.get(spec.name, ()))
        if spec.plan_key:
            hidden.add("plan")
        for argument in hidden:
            args.pop(argument, None)

        if spec.plan_key:
            plan = self.artifacts.get(spec.plan_key)
            if plan is not None:
                args["plan"] = plan

        for argument, artifact_key in _HIDDEN_ARG_SOURCES.get(spec.name, {}).items():
            value = self.artifacts.get(artifact_key)
            if value is not None:
                args[argument] = value

        if spec.confirm_field and spec.confirm_field not in args:
            granted = allow_execute if spec.permission == EXECUTE else (allow_write or allow_execute)
            if granted:
                args[spec.confirm_field] = True

        for argument in spec.executable_args:
            probed = _probe_executable(argument)
            if probed:
                args[argument] = probed
            else:
                args.pop(argument, None)

        return args


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


def default_registry(target: ToolRegistry | None = None) -> ToolRegistry:
    """The planning tools, wired to the deterministic workflows.

    Pass ``target`` to add them to an existing registry so both sets share one
    artifact store -- which is what lets an engine tool read the plan a
    planning tool just produced.
    """

    from fantasy_agent.contracts import IdeaDiscoveryRequest, PromptRequest
    from fantasy_agent.idea_discovery import extract_idea_seed
    from fantasy_agent.workflows import (
        decompose_production_tasks,
        run_director_workflow,
    )

    registry = target or ToolRegistry()

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


# Which sub-plan of a DirectorBuildPlan each engine tool consumes. The model
# never supplies these: it asks for the work, the registry supplies the plan
# that the planning tools already produced for this same run.
PLAN_KEYS: dict[str, str] = {
    "create_godot_project_structure": "godot_plan",
    "create_project_structure": "unreal_plan",
    "generate_blender_script": "blender_plan",
    "generate_asset_batch": "blender_plan",
    "prepare_visual_reference_workflows": "comfyui_plan",
    "run_visual_reference_workflow": "comfyui_plan",
}

# Arguments the model must not fill in even though Pydantic accepts them.
# They are pipeline outputs; letting the model supply them would both bloat
# the schema and let it diverge from the plan everything else is built on.
_ENGINE_HIDDEN_ARGS: dict[str, tuple[str, ...]] = {
    "create_godot_project_structure": (
        "gameplay_spec",
        "gameplay_scripts",
        "production_spec_bundle",
    ),
}

# Which artifact fills each hidden argument. Hiding an argument only removes it
# from the advertised schema -- something still has to supply it, and for the
# Godot tool that is this run's planning result. Without this the tool was
# built with no gameplay spec at all: the project got the plain player template,
# no game_manager.gd, and no code that spawns a player or decides the run, so
# the slice the model produced could not be played.
_HIDDEN_ARG_SOURCES: dict[str, dict[str, str]] = {
    "create_godot_project_structure": {
        "gameplay_spec": "gameplay_spec",
        "production_spec_bundle": "production_spec_bundle",
    },
}

#: Hidden arguments that no source fills in, and why that is deliberate. Every
#: entry is an argument that is taken out of the schema and then simply never
#: set, so the bridge decides the value on its own -- which is a decision worth
#: writing down here rather than leaving as an absence. A hidden argument in
#: neither table is the silent case: hidden, unsourced, and therefore whatever
#: the model felt like sending, which is what
#: ``test_every_hidden_argument_is_either_sourced_or_exempt`` forbids.
_HIDDEN_ARG_WITHOUT_SOURCE: dict[str, dict[str, str]] = {
    "create_godot_project_structure": {
        "gameplay_scripts": (
            "godot_mcp derives them from the spec it is handed, which keeps "
            '"how a script is made" in the codegen module'
        ),
    },
}

# The argument that unlocks a tool's real side effect. Both default to false,
# so without injection a granted run would still be a dry run.
CONFIRM_FIELDS: tuple[str, ...] = ("write_files", "confirmed_side_effects")

# Arguments naming a local binary to launch. These are stripped from the
# model's schema and replaced with a probed path on every call, because a
# model that can name the executable can run any program on this machine --
# the script it hands over is a fixed template, so the executable is the
# only part of the command line it could ever control.
EXECUTABLE_FIELDS: tuple[str, ...] = (
    "blender_executable",
    "godot_executable",
    "unreal_editor_cmd",
)


def _probe_executable(field: str) -> str | None:
    """Locate the engine binary a hidden executable argument refers to.

    Returns None when nothing is installed, which leaves the bridge's own
    default (a bare command name resolved through PATH) in place. That keeps
    the degraded behaviour identical to running the tool by hand.
    """

    from fantasy_agent import local_tools

    if field == "godot_executable":
        return local_tools._find_godot()
    if field == "blender_executable":
        return local_tools._find_blender()
    if field == "unreal_editor_cmd":
        return local_tools._unreal_cmd_executable(local_tools._find_unreal())
    return None


def _executable_args(schema: dict[str, Any]) -> tuple[str, ...]:
    properties = schema.get("properties") or {}
    return tuple(field for field in EXECUTABLE_FIELDS if field in properties)


def permission_from_annotations(annotations: dict[str, Any]) -> str:
    """Map MCP tool annotations onto a permission tier.

    MCP has no permission field, but its three hints line up with exactly what
    the gate needs: a read-only tool can be exposed freely, an idempotent
    non-read-only one writes files, and a non-idempotent one launches a
    process.
    """

    if annotations.get("readOnlyHint"):
        return READ_ONLY
    if annotations.get("idempotentHint"):
        return WRITE
    return EXECUTE


def engine_registry(workspace_root: Path | str | None = None) -> ToolRegistry:
    """Every implemented MCP engine tool, built from its own descriptors.

    Nothing here is hand-written: the schema, description and annotations
    come from the bridge that also executes the tool, so a bridge cannot
    change shape without the model's tool list changing with it.
    """

    from fantasy_agent import blender_mcp, comfyui_mcp, godot_mcp, unreal_mcp

    registry = ToolRegistry()
    for server, module, dispatch in (
        ("godot-mcp", godot_mcp, godot_mcp.call_godot_mcp_tool),
        ("unreal-mcp", unreal_mcp, unreal_mcp.call_unreal_mcp_tool),
        ("blender-mcp", blender_mcp, blender_mcp.call_blender_mcp_tool),
        ("comfyui-mcp", comfyui_mcp, comfyui_mcp.call_comfyui_mcp_tool),
    ):
        _register_engine_server(registry, server, module, dispatch, workspace_root)
    return registry


def _register_engine_server(
    registry: ToolRegistry,
    server: str,
    module: Any,
    dispatch: Callable[..., dict[str, Any]],
    workspace_root: Path | str | None,
) -> None:
    for descriptor in module.tool_descriptors():
        name = str(descriptor.get("name") or "")
        if not name:
            continue
        schema = descriptor.get("inputSchema") or {"type": "object", "properties": {}}
        description = str(descriptor.get("description") or name)
        if PLAN_KEYS.get(name):
            description = (
                f"{description} The plan is supplied from this run's production "
                "plan; do not construct one."
            )
        registry.register(
            ToolSpec(
                name=name,
                description=description,
                input_schema=schema,
                handler=_mcp_handler(dispatch, name, workspace_root),
                permission=permission_from_annotations(descriptor.get("annotations") or {}),
                server=server,
                confirm_field=_confirm_field(schema),
                plan_key=PLAN_KEYS.get(name),
                hidden_args=_ENGINE_HIDDEN_ARGS.get(name, ()),
                executable_args=_executable_args(schema),
            )
        )


def combined_registry(workspace_root: Path | str | None = None) -> ToolRegistry:
    """Planning tools and engine tools sharing one artifact store."""

    return default_registry(engine_registry(workspace_root))


def _confirm_field(schema: dict[str, Any]) -> str | None:
    properties = schema.get("properties") or {}
    for candidate in CONFIRM_FIELDS:
        if candidate in properties:
            return candidate
    return None


def _mcp_handler(
    dispatch: Callable[..., dict[str, Any]],
    name: str,
    workspace_root: Path | str | None,
) -> Callable[[dict[str, Any]], ToolOutcome]:
    def handler(arguments: dict[str, Any]) -> ToolOutcome:
        if workspace_root is None:
            payload = dispatch(name, arguments)
        else:
            payload = dispatch(name, arguments, workspace_root)
        return _mcp_outcome(name, payload)

    return handler


def _mcp_outcome(name: str, payload: dict[str, Any]) -> ToolOutcome:
    """Translate an MCP envelope into a ToolOutcome.

    ``blocked`` becomes a refusal, not an error: the tool declined to act for
    want of confirmation, which is the same situation as the registry gate
    refusing, and the loop should treat it the same way -- report it and carry
    on rather than abandon the run.
    """

    structured = payload.get("structuredContent") or {}
    if payload.get("isError"):
        return ToolOutcome(name, "error", _first_text(payload), structured)

    status = str(structured.get("status") or "")
    if status == "blocked":
        return ToolOutcome(
            name, "refused", _first_text(payload) or f"{name} was not run.", structured
        )
    if status == "failed":
        return ToolOutcome(name, "error", _first_text(payload), structured)
    return ToolOutcome(name, "ok", _first_text(payload), structured)


def _first_text(payload: dict[str, Any]) -> str:
    for block in payload.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text") or "")
    return ""


def _without_args(schema: dict[str, Any], hidden: set[str]) -> dict[str, Any]:
    """Remove hidden arguments, then prune definitions nothing references."""

    if not hidden:
        return schema

    result = {k: v for k, v in schema.items() if k not in ("properties", "required")}
    properties = {k: v for k, v in (schema.get("properties") or {}).items() if k not in hidden}
    required = [r for r in (schema.get("required") or []) if r not in hidden]
    if properties:
        result["properties"] = properties
    if required:
        result["required"] = required
    return _prune_defs(result)


def _prune_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Drop ``$defs`` entries nothing can reach any more.

    Pydantic inlines every reachable model, so hiding ``plan`` would otherwise
    leave tens of kilobytes of unreachable definitions in the tool list --
    most of the Godot tool's 19KB is definitions reachable only from ``plan``.
    """

    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return schema

    reachable = _refs_in({k: v for k, v in schema.items() if k != "$defs"})
    frontier = list(reachable)
    while frontier:
        name = frontier.pop()
        for ref in _refs_in(defs.get(name) or {}):
            if ref not in reachable:
                reachable.add(ref)
                frontier.append(ref)

    pruned = {n: body for n, body in defs.items() if n in reachable}
    if not pruned:
        return {k: v for k, v in schema.items() if k != "$defs"}
    return {**schema, "$defs": pruned}


def _refs_in(node: Any) -> set[str]:
    found: set[str] = set()
    frontier: list[Any] = [node]
    while frontier:
        item = frontier.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if key == "$ref" and isinstance(value, str):
                    found.add(value.rsplit("/", 1)[-1])
                elif isinstance(value, (dict, list)):
                    frontier.append(value)
        elif isinstance(item, list):
            frontier.extend(x for x in item if isinstance(x, (dict, list)))
    return found


def unimplemented_contracts() -> list[str]:
    """MCP contracts that declare a tool no bridge implements.

    ``publish_prototype_branch`` is the known gap: it is declared and served
    to the UI but nothing implements it. Pinning the gap here means either
    implementing it without wiring it up, or deleting the contract and
    forgetting this test, fails loudly.
    """

    from fantasy_agent.mcp import initial_mcp_contracts

    registered = set(engine_registry().names())
    return sorted(c.name for c in initial_mcp_contracts() if c.name not in registered)


def tool_catalog() -> dict[str, Any]:
    """Every tool an agent may call, with the tier the gate will enforce.

    ``/api/tool-contracts`` predates the registry: it serves ``MCPToolContract``,
    a hand-written record that names a tool and its schema anchors but says
    nothing about what the gate actually does with it. An operator reading that
    list cannot tell a read-only probe from one that launches Blender, which is
    the one thing AGENTS.md says must be declared before it runs.

    This is the registry's own view instead -- the same records that feed the
    model's tool list and the permission gate -- so the tiers shown here are the
    tiers enforced, not a second inventory that can drift:

    - ``source`` is ``"planning"`` for the four deterministic planning tools and
      ``"engine"`` for the MCP bridges.
    - ``permission`` is the gate's tier. Engine tools derive it from the bridge's
      MCP annotations via ``permission_from_annotations``; nothing here is
      hand-typed per tool.
    - ``confirm_field`` names the argument that unlocks the real side effect
      (MCP tools default it to false, so a granted run still writes nothing
      until the caller sets it).
    - ``hidden_args`` / ``executable_args`` are the arguments withheld from the
      model. ``executable_args`` are *also* overwritten on every call -- a hidden
      argument is only removed from the advertised schema, and a model can still
      send one it was never offered.
    - ``contract`` names the declared ``MCPToolContract`` when one exists, so a
      tool implemented without a contract, or a contract with no implementation,
      is visible rather than implied.

    ``permission_counts`` is returned alongside so a caller can assert on the
    shape without walking the list -- the UI prints it as a summary line.
    """

    from fantasy_agent.mcp import initial_mcp_contracts

    declared = {contract.name: contract for contract in initial_mcp_contracts()}
    implemented_engine = set(engine_registry().names())

    entries: list[dict[str, Any]] = []
    for source, registry in (
        ("planning", default_registry()),
        ("engine", engine_registry()),
    ):
        for name in registry.names():
            spec = registry.get(name)
            if spec is None:
                continue
            contract = declared.get(name)
            entries.append(
                {
                    "name": name,
                    "source": source,
                    "server": spec.server,
                    "permission": spec.permission,
                    "description": spec.description,
                    "confirm_field": spec.confirm_field,
                    "plan_key": spec.plan_key,
                    "hidden_args": list(spec.hidden_args),
                    "executable_args": list(spec.executable_args),
                    "contract": (
                        {
                            "declared": True,
                            "side_effects": list(contract.side_effects),
                            "safety_checks": list(contract.safety_checks),
                        }
                        if contract
                        else None
                    ),
                }
            )

    counts = {tier: 0 for tier in PERMISSIONS}
    for entry in entries:
        counts[entry["permission"]] += 1

    # Contracts that declare a tool nothing implements. Kept in the payload
    # because the UI is the only place a human sees this list; the test that
    # pins it (`unimplemented_contracts`) is invisible outside CI.
    declared_only = sorted(
        contract.name for contract in declared.values() if contract.name not in implemented_engine
    )

    return {
        "tools": entries,
        "permission_counts": counts,
        # The planning tools are not MCP contracts, so only the engine half can
        # be missing an implementation.
        "declared_without_implementation": declared_only,
    }


def exposed_executable_args(registry: ToolRegistry | None = None) -> list[str]:
    """Tools whose model-visible schema still lets the model name a binary.

    A model that picks the executable picks the program, which is the one
    part of an otherwise fixed command line it could control. New engine
    tools arrive by being added to a bridge's descriptors, so this guard
    catches one that smuggles an executable path back in.
    """

    tools = registry or engine_registry()
    problems: list[str] = []
    for name in tools.names():
        spec = tools.get(name)
        if spec is None:
            continue
        properties = spec.model_schema()["parameters"].get("properties") or {}
        for argument in EXECUTABLE_FIELDS:
            if argument in properties:
                problems.append(f"{name} exposes {argument}")
    return sorted(problems)


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


def _mcp_root() -> Path:
    return Path(__file__).resolve().parents[1]
