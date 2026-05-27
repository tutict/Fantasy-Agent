from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from fantasy_agent.contracts import DirectorBuildPlan, PromptRequest
from fantasy_agent.workflows import (
    prepare_blender_assets,
    prepare_comfyui_visuals,
    prepare_qa_plan as prepare_qa_plan_from_spec,
    prepare_unreal_project,
    run_director_workflow,
)

WIDGET_URI = "ui://fantasy-agent/workbench.html"
WIDGET_MIME_TYPE = "text/html;profile=mcp-app"
SERVER_NAME = "fantasy-agent-chatgpt-workbench"
SERVER_VERSION = "0.1.0"

DOCS_USED = [
    "https://developers.openai.com/apps-sdk/",
    "https://developers.openai.com/apps-sdk/quickstart",
    "https://developers.openai.com/apps-sdk/build/mcp-server",
    "https://developers.openai.com/apps-sdk/build/chatgpt-ui",
    "https://developers.openai.com/apps-sdk/plan/tools",
    "https://developers.openai.com/apps-sdk/reference",
]


def prompt_request_schema() -> dict[str, Any]:
    schema = PromptRequest.model_json_schema()
    schema["title"] = "Fantasy Agent Production Request"
    schema["description"] = (
        "Gameplay idea and prototype constraints for Fantasy Agent. "
        "The tools are read-only planning tools and do not execute Unreal, Blender, or ComfyUI."
    )
    return schema


def _base_tool_meta(invoking: str, invoked: str) -> dict[str, Any]:
    return {
        "openai/outputTemplate": WIDGET_URI,
        "openai/widgetAccessible": True,
        "openai/toolInvocation/invoking": invoking,
        "openai/toolInvocation/invoked": invoked,
    }


def _tool(
    name: str,
    title: str,
    description: str,
    invoking: str,
    invoked: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "title": title,
        "description": description,
        "inputSchema": prompt_request_schema(),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "_meta": _base_tool_meta(invoking, invoked),
    }


def tool_descriptors() -> list[dict[str, Any]]:
    return [
        _tool(
            "generate_game_production_plan",
            "Generate game production plan",
            (
                "Use this when the user wants a full prompt-to-playable production plan with "
                "gameplay DSL, GDD, Unreal, Blender, ComfyUI, QA, and next actions."
            ),
            "Orchestrating Fantasy Agent plan",
            "Fantasy Agent plan ready",
        ),
        _tool(
            "render_gdd",
            "Render structured GDD",
            (
                "Use this when the user wants an implementation-focused markdown GDD from a "
                "gameplay idea, including requested English and Simplified Chinese outputs."
            ),
            "Rendering Fantasy Agent GDD",
            "Fantasy Agent GDD ready",
        ),
        _tool(
            "prepare_unreal_plan",
            "Prepare Unreal project plan",
            (
                "Use this when the user wants UE5 folders, plugins, maps, Blueprint classes, "
                "and automation steps without executing Unreal."
            ),
            "Preparing Unreal handoff",
            "Unreal handoff ready",
        ),
        _tool(
            "prepare_blender_plan",
            "Prepare Blender asset plan",
            (
                "Use this when the user wants procedural greybox asset jobs and export handoff "
                "paths without launching Blender."
            ),
            "Preparing Blender jobs",
            "Blender jobs ready",
        ),
        _tool(
            "prepare_comfyui_plan",
            "Prepare ComfyUI visual plan",
            (
                "Use this when the user wants gameplay-readable ComfyUI reference jobs after "
                "the gameplay loop is known, without calling ComfyUI."
            ),
            "Preparing ComfyUI references",
            "ComfyUI references ready",
        ),
        _tool(
            "prepare_qa_plan",
            "Prepare QA plan",
            (
                "Use this when the user wants smoke, playability, failure, packaging, and "
                "metrics checks for a short playable vertical slice."
            ),
            "Preparing QA checks",
            "QA checks ready",
        ),
    ]


def widget_resource() -> dict[str, Any]:
    return {
        "uri": WIDGET_URI,
        "name": "fantasy_agent_workbench",
        "title": "Fantasy Agent Workbench",
        "description": "Interactive ChatGPT workbench for gameplay-first game production plans.",
        "mimeType": WIDGET_MIME_TYPE,
        "_meta": widget_resource_meta(),
    }


def widget_resource_meta() -> dict[str, Any]:
    csp = {"connectDomains": [], "resourceDomains": []}
    return {
        "openai/widgetDescription": (
            "Fantasy Agent workbench for generating and inspecting gameplay-first production plans."
        ),
        "openai/widgetPrefersBorder": True,
        "openai/widgetCSP": {
            "connect_domains": [],
            "resource_domains": [],
        },
        "ui": {
            "csp": csp,
            "prefersBorder": True,
        },
    }


def _request(arguments: dict[str, Any] | None) -> PromptRequest:
    return PromptRequest.model_validate(arguments or {})


def _plan(request: PromptRequest) -> DirectorBuildPlan:
    return run_director_workflow(request)


def _summary_for_plan(plan: DirectorBuildPlan) -> dict[str, Any]:
    spec = plan.gameplay_spec
    return {
        "title": spec.title,
        "logline": spec.logline,
        "target_session_minutes": spec.target_session_minutes,
        "core_verbs": spec.core_verbs,
        "design_pillars": spec.design_pillars,
        "win_state": spec.win_state,
        "failure_states": spec.failure_states,
        "next_actions": plan.next_actions,
    }


def _text_summary(title: str, plan: DirectorBuildPlan) -> str:
    spec = plan.gameplay_spec
    return (
        f"{title}: {spec.title}. "
        f"Target session: {spec.target_session_minutes} minutes. "
        f"Core verbs: {', '.join(spec.core_verbs)}. "
        f"Next action: {plan.next_actions[0]}"
    )


def _tool_result(
    tool_name: str,
    request: PromptRequest,
    structured_content: dict[str, Any],
    content_text: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": content_text}],
        "_meta": {
            "toolName": tool_name,
            "request": request.model_dump(mode="json"),
            "widgetUri": WIDGET_URI,
            **(meta or {}),
        },
    }


def generate_game_production_plan(arguments: dict[str, Any] | None) -> dict[str, Any]:
    request = _request(arguments)
    plan = _plan(request)
    plan_payload = plan.model_dump(mode="json")
    return _tool_result(
        "generate_game_production_plan",
        request,
        {
            "kind": "director_build_plan",
            "summary": _summary_for_plan(plan),
            "plan": plan_payload,
        },
        _text_summary("Generated full production plan", plan),
        {"plan": plan_payload, "activePanel": "overview"},
    )


def render_gdd(arguments: dict[str, Any] | None) -> dict[str, Any]:
    request = _request(arguments)
    plan = _plan(request)
    gdd = plan.gdd.model_dump(mode="json")
    return _tool_result(
        "render_gdd",
        request,
        {
            "kind": "gdd_document",
            "summary": _summary_for_plan(plan),
            "gdd": gdd,
        },
        _text_summary("Rendered GDD", plan),
        {"plan": plan.model_dump(mode="json"), "gdd": gdd, "activePanel": "gdd"},
    )


def prepare_unreal_plan(arguments: dict[str, Any] | None) -> dict[str, Any]:
    request = _request(arguments)
    spec = _plan(request).gameplay_spec
    unreal_plan = prepare_unreal_project(spec, request.engine_version)
    return _tool_result(
        "prepare_unreal_plan",
        request,
        {
            "kind": "unreal_project_plan",
            "gameplay_title": spec.title,
            "unreal_plan": unreal_plan.model_dump(mode="json"),
        },
        f"Prepared Unreal handoff for {spec.title}: {', '.join(unreal_plan.maps)}.",
        {"unrealPlan": unreal_plan.model_dump(mode="json"), "activePanel": "build"},
    )


def prepare_blender_plan(arguments: dict[str, Any] | None) -> dict[str, Any]:
    request = _request(arguments)
    spec = _plan(request).gameplay_spec
    blender_plan = prepare_blender_assets(spec)
    return _tool_result(
        "prepare_blender_plan",
        request,
        {
            "kind": "blender_asset_plan",
            "gameplay_title": spec.title,
            "blender_plan": blender_plan.model_dump(mode="json"),
        },
        f"Prepared {len(blender_plan.jobs)} Blender greybox asset jobs for {spec.title}.",
        {"blenderPlan": blender_plan.model_dump(mode="json"), "activePanel": "build"},
    )


def prepare_comfyui_plan(arguments: dict[str, Any] | None) -> dict[str, Any]:
    request = _request(arguments)
    spec = _plan(request).gameplay_spec
    comfyui_plan = prepare_comfyui_visuals(spec)
    return _tool_result(
        "prepare_comfyui_plan",
        request,
        {
            "kind": "comfyui_visual_plan",
            "gameplay_title": spec.title,
            "comfyui_plan": comfyui_plan.model_dump(mode="json"),
        },
        f"Prepared {len(comfyui_plan.jobs)} ComfyUI visual reference jobs for {spec.title}.",
        {"comfyuiPlan": comfyui_plan.model_dump(mode="json"), "activePanel": "visuals"},
    )


def prepare_qa_plan(arguments: dict[str, Any] | None) -> dict[str, Any]:
    request = _request(arguments)
    spec = _plan(request).gameplay_spec
    qa_plan = prepare_qa_plan_from_spec(spec)
    return _tool_result(
        "prepare_qa_plan",
        request,
        {
            "kind": "qa_plan",
            "gameplay_title": spec.title,
            "qa_plan": qa_plan.model_dump(mode="json"),
        },
        f"Prepared QA checks for a {qa_plan.target_session_minutes}-minute slice of {spec.title}.",
        {"qaPlan": qa_plan.model_dump(mode="json"), "activePanel": "qa"},
    )


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any] | None], dict[str, Any]]] = {
    "generate_game_production_plan": generate_game_production_plan,
    "render_gdd": render_gdd,
    "prepare_unreal_plan": prepare_unreal_plan,
    "prepare_blender_plan": prepare_blender_plan,
    "prepare_comfyui_plan": prepare_comfyui_plan,
    "prepare_qa_plan": prepare_qa_plan,
}


def call_workbench_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        available = ", ".join(sorted(TOOL_HANDLERS))
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown Fantasy Agent tool '{name}'. Available tools: {available}.",
                }
            ],
        }
    try:
        return handler(arguments)
    except ValidationError as exc:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Invalid Fantasy Agent request: {exc}"}],
        }
