from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib import error, parse, request


@dataclass(frozen=True)
class ComfyUIClient:
    endpoint: str = "http://127.0.0.1:8188"

    def get_json(self, path: str, timeout: int = 30) -> dict[str, Any] | list[Any]:
        req = request.Request(f"{self.endpoint.rstrip('/')}{path}", method="GET")
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def system_stats(self) -> dict[str, Any]:
        payload = self.get_json("/system_stats", timeout=10)
        return payload if isinstance(payload, dict) else {}

    def object_info(self) -> dict[str, Any]:
        payload = self.get_json("/object_info", timeout=30)
        return payload if isinstance(payload, dict) else {}

    def models(self, folder: str) -> list[str]:
        payload = self.get_json(f"/models/{parse.quote(folder)}", timeout=10)
        if isinstance(payload, list):
            return [str(item) for item in payload]
        return []

    def queue_prompt(self, workflow: dict, client_id: str = "fantasy-agent") -> dict:
        payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
        req = request.Request(
            f"{self.endpoint.rstrip('/')}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ComfyUI HTTP {exc.code}: {body}") from exc

    def history(self, prompt_id: str) -> dict:
        req = request.Request(
            f"{self.endpoint.rstrip('/')}/history/{parse.quote(prompt_id)}",
            method="GET",
        )
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def download_image(self, filename: str, subfolder: str, image_type: str, output_path: str) -> str:
        query = parse.urlencode({"filename": filename, "subfolder": subfolder, "type": image_type})
        req = request.Request(f"{self.endpoint.rstrip('/')}/view?{query}", method="GET")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with request.urlopen(req, timeout=60) as response:
            output.write_bytes(response.read())
        return output.as_posix()
