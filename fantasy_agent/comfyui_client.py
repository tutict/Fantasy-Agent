from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib import parse, request


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

