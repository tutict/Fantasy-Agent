from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from fantasy_agent.contracts import GameplaySpec, GodotProjectPlan
from fantasy_agent.godot_mcp import (
    SERVER_NAME,
    SERVER_VERSION,
    call_godot_mcp_tool,
    tool_descriptors,
)
from fantasy_agent.workflows import prepare_godot_project

app = FastAPI(
    title="Fantasy Agent Godot Builder",
    version=SERVER_VERSION,
    description="Prepares controlled Godot 4 quick-play prototype handoffs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "godot-builder"}


@app.post("/prepare", response_model=GodotProjectPlan)
def prepare(spec: GameplaySpec) -> GodotProjectPlan:
    return prepare_godot_project(spec)


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _initialize(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    protocol_version = params.get("protocolVersion") or "2024-11-05"
    return _jsonrpc_result(
        request_id,
        {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        },
    )


def _handle_rpc(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None
    if method == "initialize":
        return _initialize(request_id, params)
    if method == "ping":
        return _jsonrpc_result(request_id, {})
    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": tool_descriptors()})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return _jsonrpc_error(request_id, -32602, "tools/call requires params.name")
        return _jsonrpc_result(request_id, call_godot_mcp_tool(name, arguments))
    return _jsonrpc_error(request_id, -32601, f"Unsupported method: {method}")


@app.get("/mcp")
def mcp_info() -> dict[str, Any]:
    return {
        "status": "ok",
        "transport": "json-rpc-over-http",
        "endpoint": "/mcp",
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


@app.post("/mcp")
async def mcp(request: Request) -> Response:
    payload = await request.json()
    if isinstance(payload, list):
        responses = [_handle_rpc(message) for message in payload if isinstance(message, dict)]
        responses = [response for response in responses if response is not None]
        if not responses:
            return Response(status_code=202)
        return JSONResponse(responses)
    if not isinstance(payload, dict):
        return JSONResponse(_jsonrpc_error(None, -32600, "Invalid JSON-RPC payload"), status_code=400)
    response = _handle_rpc(payload)
    if response is None:
        return Response(status_code=202)
    return JSONResponse(response)
