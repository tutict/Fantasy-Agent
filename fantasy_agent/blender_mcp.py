from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fantasy_agent.blender_codegen import build_blender_script_artifact
from fantasy_agent.contracts import (
    BlenderAssetPlan,
    BlenderMCPExecuteRequest,
    BlenderMCPGenerateScriptRequest,
    BlenderMCPResult,
    BlenderScriptArtifact,
)

SERVER_NAME = "fantasy-agent-blender-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": "generate_blender_script",
            "title": "Generate Blender Python script",
            "description": (
                "Use this when Fantasy Agent needs a Blender Python script and Unreal import "
                "manifest from a BlenderAssetPlan. Defaults to in-memory output; set write_files "
                "only when generated file side effects are approved."
            ),
            "inputSchema": BlenderMCPGenerateScriptRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "generate_asset_batch",
            "title": "Run Blender asset batch",
            "description": (
                "Use this when the user has explicitly confirmed Blender execution. Writes a "
                "generated script, launches Blender in background mode, exports FBX/GLB assets "
                "under generated/assets, and writes an Unreal import manifest."
            ),
            "inputSchema": BlenderMCPExecuteRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
    ]


class BlenderMCPSafetyError(ValueError):
    pass


class BlenderMCPBridge:
    def __init__(self, workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def generate_blender_script(self, request: BlenderMCPGenerateScriptRequest) -> BlenderMCPResult:
        artifact = self._artifact(
            request.plan,
            request.script_path,
            request.import_manifest_path,
        )
        risks = self._validate_artifact(artifact)
        written_files: list[str] = []
        if request.write_files:
            written_files = self._write_artifact(artifact)
        return BlenderMCPResult(
            status="written" if request.write_files else "planned",
            artifact=artifact,
            written_files=written_files,
            import_manifest_path=artifact.import_manifest_path,
            risks=risks,
        )

    def generate_asset_batch(self, request: BlenderMCPExecuteRequest) -> BlenderMCPResult:
        artifact = self._artifact(
            request.plan,
            request.script_path,
            request.import_manifest_path,
        )
        risks = self._validate_artifact(artifact)
        command = [
            request.blender_executable,
            "--background",
            "--python",
            str(self._resolve_workspace_path(artifact.script_path)),
        ]
        if not request.confirmed_side_effects:
            return BlenderMCPResult(
                status="blocked",
                artifact=artifact,
                command=command,
                import_manifest_path=artifact.import_manifest_path,
                risks=[
                    *risks,
                    "Blender execution requires confirmed_side_effects=true.",
                ],
            )

        written_files = self._write_artifact(artifact)
        stdout_path, stderr_path = self._log_paths(artifact.plan_name)
        env = dict(os.environ)
        env["PYTHONPATH"] = (
            str(self.workspace_root)
            if not env.get("PYTHONPATH")
            else f"{self.workspace_root}{os.pathsep}{env['PYTHONPATH']}"
        )

        try:
            process = subprocess.run(
                command,
                cwd=self.workspace_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=request.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            stderr = f"Blender executable not found: {request.blender_executable}"
            self._write_text(stderr_path, stderr)
            return BlenderMCPResult(
                status="failed",
                artifact=artifact,
                command=command,
                written_files=written_files,
                import_manifest_path=artifact.import_manifest_path,
                log_paths=[self._display_path(stderr_path)],
                stderr_tail=stderr,
                risks=[*risks, str(exc)],
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or f"Blender execution timed out after {request.timeout_seconds}s."
            self._write_text(stdout_path, stdout)
            self._write_text(stderr_path, stderr)
            return BlenderMCPResult(
                status="failed",
                artifact=artifact,
                command=command,
                written_files=written_files,
                import_manifest_path=artifact.import_manifest_path,
                log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
                risks=[*risks, "Blender execution timed out."],
            )

        self._write_text(stdout_path, process.stdout)
        self._write_text(stderr_path, process.stderr)
        return BlenderMCPResult(
            status="executed" if process.returncode == 0 else "failed",
            artifact=artifact,
            command=command,
            written_files=written_files,
            exported_assets=[asset.source_file for asset in artifact.import_manifest.assets],
            import_manifest_path=artifact.import_manifest_path,
            log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
            return_code=process.returncode,
            stdout_tail=_tail(process.stdout),
            stderr_tail=_tail(process.stderr),
            risks=risks if process.returncode == 0 else [*risks, "Blender returned a non-zero code."],
        )

    def _artifact(
        self,
        plan: BlenderAssetPlan,
        script_path: str | None,
        import_manifest_path: str,
    ) -> BlenderScriptArtifact:
        return build_blender_script_artifact(
            plan,
            script_path=script_path,
            import_manifest_path=import_manifest_path,
        )

    def _validate_artifact(self, artifact: BlenderScriptArtifact) -> list[str]:
        risks = [
            "Blender will clear the active scene inside its background process before generation.",
            "Exports are intended for greybox playability validation, not final art.",
        ]
        self._assert_relative_under(artifact.script_path, "generated/blender")
        self._assert_relative_under(artifact.import_manifest_path, "generated")
        for asset in artifact.import_manifest.assets:
            self._assert_relative_under(asset.source_file, "generated/assets")
            if not asset.source_file.lower().endswith((".fbx", ".glb")):
                raise BlenderMCPSafetyError(
                    f"Unsupported export extension for {asset.source_file}; expected .fbx or .glb."
                )
        return risks

    def _write_artifact(self, artifact: BlenderScriptArtifact) -> list[str]:
        script_path = self._resolve_workspace_path(artifact.script_path)
        manifest_path = self._resolve_workspace_path(artifact.import_manifest_path)
        self._write_text(script_path, artifact.script)
        self._write_text(
            manifest_path,
            json.dumps(artifact.import_manifest.model_dump(mode="json"), indent=2),
        )
        return [self._display_path(script_path), self._display_path(manifest_path)]

    def _assert_relative_under(self, path: str, required_prefix: str) -> None:
        if Path(path).is_absolute():
            raise BlenderMCPSafetyError(f"Absolute paths are not allowed: {path}")
        normalized = Path(path.replace("\\", "/"))
        if ".." in normalized.parts:
            raise BlenderMCPSafetyError(f"Parent traversal is not allowed: {path}")
        prefix = Path(required_prefix)
        if normalized.parts[: len(prefix.parts)] != prefix.parts:
            raise BlenderMCPSafetyError(f"Path must stay under {required_prefix}: {path}")
        self._resolve_workspace_path(path)

    def _resolve_workspace_path(self, path: str) -> Path:
        resolved = (self.workspace_root / path).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise BlenderMCPSafetyError(f"Path escapes workspace: {path}") from exc
        return resolved

    def _log_paths(self, plan_name: str) -> tuple[Path, Path]:
        safe_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in plan_name).strip("_")
        log_dir = self.workspace_root / "generated" / "logs" / "blender"
        return log_dir / f"{safe_name}.stdout.log", log_dir / f"{safe_name}.stderr.log"

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        return path.relative_to(self.workspace_root).as_posix()


def call_blender_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> dict[str, Any]:
    bridge = BlenderMCPBridge(workspace_root)
    try:
        if name == "generate_blender_script":
            request = BlenderMCPGenerateScriptRequest.model_validate(arguments or {})
            result = bridge.generate_blender_script(request)
        elif name == "generate_asset_batch":
            request = BlenderMCPExecuteRequest.model_validate(arguments or {})
            result = bridge.generate_asset_batch(request)
        else:
            available = ", ".join(tool["name"] for tool in tool_descriptors())
            return _error(f"Unknown Blender MCP tool '{name}'. Available tools: {available}.")
        return {
            "structuredContent": result.model_dump(mode="json"),
            "content": [{"type": "text", "text": _content_summary(result)}],
        }
    except (ValidationError, BlenderMCPSafetyError) as exc:
        return _error(str(exc))


def _content_summary(result: BlenderMCPResult) -> str:
    if result.status == "blocked":
        return "Blender MCP blocked execution because side effects were not confirmed."
    if result.status == "failed":
        return "Blender MCP failed. Check returned logs and stderr_tail."
    if result.status == "executed":
        return f"Blender MCP exported {len(result.exported_assets)} assets."
    if result.status == "written":
        return f"Blender MCP wrote {len(result.written_files)} generated handoff files."
    return "Blender MCP prepared a script and Unreal import manifest."


def _error(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def _tail(value: str | bytes | None, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-limit:]

