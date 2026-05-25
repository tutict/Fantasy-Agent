"""Small ComfyUI HTTP client for future MCP-backed execution.

This module deliberately avoids external dependencies. It prepares the same
request shape that a ComfyUI `/prompt` call expects, but orchestration should
prefer `comfyui-mcp` so side effects are logged centrally.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import request


@dataclass(frozen=True)
class ComfyUIClient:
    endpoint: str = "http://127.0.0.1:8188"

    def queue_prompt(self, workflow: dict, client_id: str = "fantasy-agent") -> dict:
        payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
        req = request.Request(
            f"{self.endpoint.rstrip('/')}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
