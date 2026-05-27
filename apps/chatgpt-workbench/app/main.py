from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fantasy_agent.chatgpt_app import (
    SERVER_NAME,
    SERVER_VERSION,
    WIDGET_MIME_TYPE,
    WIDGET_URI,
    call_workbench_tool,
    tool_descriptors,
    widget_resource,
    widget_resource_meta,
)

APP_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = APP_DIR / "static"
WIDGET_PATH = STATIC_DIR / "workbench.html"

app = FastAPI(
    title="Fantasy Agent ChatGPT Workbench",
    version=SERVER_VERSION,
    description="MCP endpoint and widget resource for ChatGPT Apps.",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        },
    )


def _read_widget() -> str:
    return WIDGET_PATH.read_text(encoding="utf-8")


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
        return _jsonrpc_result(request_id, call_workbench_tool(name, arguments))
    if method == "resources/list":
        return _jsonrpc_result(request_id, {"resources": [widget_resource()]})
    if method == "resources/read":
        uri = params.get("uri")
        if uri != WIDGET_URI:
            return _jsonrpc_error(request_id, -32002, f"Unknown resource URI: {uri}")
        return _jsonrpc_result(
            request_id,
            {
                "contents": [
                    {
                        "uri": WIDGET_URI,
                        "mimeType": WIDGET_MIME_TYPE,
                        "text": _read_widget(),
                        "_meta": widget_resource_meta(),
                    }
                ]
            },
        )
    return _jsonrpc_error(request_id, -32601, f"Unsupported method: {method}")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WIDGET_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": SERVER_NAME, "version": SERVER_VERSION}


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


@app.post("/debug/tool/{tool_name}")
async def debug_tool(tool_name: str, request: Request) -> dict[str, Any]:
    arguments = await request.json()
    return call_workbench_tool(tool_name, arguments)

