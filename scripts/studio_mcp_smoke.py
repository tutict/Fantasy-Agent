"""本机 Studio ``/mcp`` 协议冒烟；只读探测，不改变连接开关状态。

前置：Studio 已在运行且连接面板已开启，Token 由用户在面板显式复制后放进环境变量。

    set FANTASY_STUDIO_MCP_TOKEN=<复制的 Token>
    .venv\\Scripts\\python.exe scripts\\studio_mcp_smoke.py

脚本不打印 Token、不写盘、不启动 Studio、不开启或关闭连接。``mcp==2.3.0``
的结果字段是 snake_case，客户端必须禁用环境代理，否则 loopback 请求会被
机器级 HTTP_PROXY 劫持。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import urllib.error
import urllib.request

import httpx2
from mcp.client.streamable_http import streamable_http_client

from mcp import ClientSession

DEFAULT_BASE = "http://127.0.0.1:7860"
TOKEN_ENV = "FANTASY_STUDIO_MCP_TOKEN"
INIT_BODY = (
    b'{"jsonrpc":"2.0","id":1,"method":"initialize",'
    b'"params":{"protocolVersion":"2025-06-18","capabilities":{},'
    b'"clientInfo":{"name":"studio-mcp-smoke","version":"0.1.0"}}}'
)


def probe(endpoint: str, base: str, token: str | None) -> int:
    """绕过代理发一条裸 JSON-RPC，返回 HTTP 状态码。"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Origin": base,
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(endpoint, data=INIT_BODY, method="POST", headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


async def handshake(base: str, token: str) -> tuple[str, list[str]]:
    endpoint = base.rstrip("/") + "/mcp"
    async with (
        httpx2.AsyncClient(
            headers={"Authorization": "Bearer " + token}, timeout=10, trust_env=False
        ) as client,
        streamable_http_client(endpoint, http_client=client) as streams,
        ClientSession(*streams, read_timeout_seconds=10) as session,
    ):
        initialized = await session.initialize()
        tools = await session.list_tools()
        return initialized.protocol_version, [tool.name for tool in tools.tools]


def main() -> int:
    parser = argparse.ArgumentParser(description="Studio /mcp 本机协议冒烟")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="Studio 根地址")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    token = os.environ.get(TOKEN_ENV, "")
    if not token:
        print(f"缺少环境变量 {TOKEN_ENV}；请先在连接面板显式复制 Token。")
        return 2

    endpoint = base + "/mcp"
    no_auth = probe(endpoint, base, None)
    bad_auth = probe(endpoint, base, "invalid-token")
    print(f"无 Bearer: {no_auth} (期望 401)；错误 Bearer: {bad_auth} (期望 401)")
    if no_auth == 503:
        print("连接未开启：请先在 Studio 连接面板开启。")
        return 1
    if (no_auth, bad_auth) != (401, 401):
        print("鉴权闸门异常，停止冒烟。")
        return 1

    protocol, names = asyncio.run(handshake(base, token))
    print(f"initialize: protocol={protocol}；tools/list={len(names)} 个工具")
    print("工具名：" + ", ".join(names))
    if not names:
        print("tools/list 为空，冒烟失败。")
        return 1
    print("SMOKE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
