"""Studio 本机连接设置；凭据仅在显式复制操作中公开。"""

from __future__ import annotations

import base64
import hmac
import ipaddress
import json
import secrets
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.studio_projects import _credential_payload


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def local_request_allowed(scope: dict[str, Any], *, require_origin: bool = False) -> bool:
    """验证 socket peer、字面 Host 及同源 Origin，不信任转发头。"""
    peer = scope.get("client")
    if not peer or peer[0] == "localhost" or not _loopback(peer[0]):
        return False
    pairs = scope.get("headers", [])
    hosts = [v.decode("latin-1") for k, v in pairs if k.lower() == b"host"]
    origins = [v.decode("latin-1") for k, v in pairs if k.lower() == b"origin"]
    if len(hosts) != 1 or len(origins) > 1:
        return False
    try:
        host = urlsplit("//" + hosts[0])
        if (
            host.username
            or host.password
            or host.path
            or host.query
            or host.fragment
            or not _loopback(host.hostname or "")
        ):
            return False
        port = host.port or (443 if scope.get("scheme") == "https" else 80)
        server = scope.get("server")
        if server and port != server[1]:
            return False
        if not origins:
            return not require_origin
        origin = urlsplit(origins[0])
        return (
            origin.scheme == scope.get("scheme", "http")
            and origin.hostname == host.hostname
            and (origin.port or (443 if origin.scheme == "https" else 80)) == port
            and not origin.username
            and not origin.password
            and not origin.path
            and not origin.query
            and not origin.fragment
        )
    except ValueError:
        return False


class MCPConnection:
    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root)
        self.path = self.workspace_root / "generated/studio/mcp-connection.json"
        self._lock = threading.RLock()
        self._recent: deque[dict[str, Any]] = deque(maxlen=40)
        self._secrets: list[str] = []
        self._revision = 0
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            saved = {"enabled": False, "token": secrets.token_urlsafe(48)}
            self._write(saved)
        except (ValueError, OSError) as exc:
            raise ValueError("MCP 连接配置损坏，请在本机修复配置文件。") from exc
        if (
            not isinstance(saved, dict)
            or type(saved.get("enabled")) is not bool
            or not isinstance(saved.get("token"), str)
            or len(saved["token"]) < 40
        ):
            raise ValueError("MCP 连接配置无效。")
        self._enabled = saved["enabled"]
        self._token = saved["token"]
        self._secrets.append(self._token)

    def _write(self, data: dict[str, Any]) -> None:
        write_atomic(self.path, json.dumps(data, ensure_ascii=False))

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def matches(self, token: str) -> bool:
        with self._lock:
            return hmac.compare_digest(self._token.encode(), token.encode())

    def copy_token(self) -> str:
        with self._lock:
            return self._token

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._write({"enabled": enabled, "token": self._token})
            self._enabled = enabled
            self._revision += 1

    def rotate(self) -> None:
        with self._lock:
            token = secrets.token_urlsafe(48)
            self._write({"enabled": self._enabled, "token": token})
            self._token = token
            self._secrets.append(token)
            self._revision += 1

    def approval_revision(self) -> int | None:
        """停用或轮换使正在展示的确认请求失效。"""
        with self._lock:
            return self._revision if self._enabled else None

    def contains_secret(self, value: Any) -> bool:
        if isinstance(value, bytes):
            return any(token.encode() in value for token in self._secrets)
        if isinstance(value, str):
            return any(token in value for token in self._secrets)
        if isinstance(value, dict):
            return any(self.contains_secret(k) or self.contains_secret(v) for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return any(self.contains_secret(item) for item in value)
        return False

    def sanitize(self, value: Any) -> Any:
        if isinstance(value, str):
            for token in self._secrets:
                value = value.replace(token, "[连接凭据已隐藏]")
            return value
        if isinstance(value, dict):
            # Binary resources are inspected before they can hide a token in base64.
            if value.get("encoding") == "base64" and isinstance(value.get("data"), str):
                try:
                    if self.contains_secret(base64.b64decode(value["data"], validate=True)):
                        return {"status": "blocked", "summary": "产物含连接凭据，无法公开。"}
                except ValueError:
                    return {"status": "blocked", "summary": "产物编码无效。"}
            return {
                self.sanitize(k): self.sanitize(v) for k, v in _credential_payload(value).items()
            }
        if isinstance(value, (list, tuple)):
            return [self.sanitize(item) for item in value]
        return value

    def record(self, operation: str, status: str, tool: str = "") -> None:
        with self._lock:
            self._recent.append(
                {
                    "time": time.time(),
                    "operation": self.sanitize(operation),
                    "status": self.sanitize(status),
                    "tool": self.sanitize(tool),
                }
            )

    def state(self, base_url: str) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "configured": True,
                "endpoint": base_url.rstrip("/") + "/mcp",
                "recent_activity": list(self._recent),
            }

    def config(self, base_url: str) -> dict[str, Any]:
        endpoint = base_url.rstrip("/") + "/mcp"
        workbuddy = {
            "mcpServers": {
                "fantasy-studio": {
                    "type": "http",
                    "url": endpoint,
                    "headers": {"Authorization": "Bearer ${FANTASY_STUDIO_MCP_TOKEN}"},
                }
            }
        }
        return {
            "endpoint": endpoint,
            "token_env_var": "FANTASY_STUDIO_MCP_TOKEN",
            "toml": "[mcp_servers.fantasy_studio]\nurl = "
            + json.dumps(endpoint)
            + '\nbearer_token_env_var = "FANTASY_STUDIO_MCP_TOKEN"\n',
            "instructions": "在本机环境变量 FANTASY_STUDIO_MCP_TOKEN 中设置复制的 Token，再添加此配置。原生确认需要客户端允许 approval_policy.granular.mcp_elicitations。",
            "workbuddy_json": json.dumps(workbuddy, ensure_ascii=False, indent=2),
        }
