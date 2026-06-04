from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib import parse

from pydantic import ValidationError

from fantasy_agent.comfyui_client import ComfyUIClient
from fantasy_agent.contracts import (
    ComfyUICapabilityProbeRequest,
    ComfyUICapabilityProbeResult,
    ComfyUIMCPExecuteRequest,
    ComfyUIMCPGenerateRequest,
    ComfyUIMCPResult,
    ComfyUIPromptJob,
    ComfyUIRunManifest,
    ComfyUIVisualPlan,
    ComfyUIWorkflowArtifact,
)

SERVER_NAME = "fantasy-agent-comfyui-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": "probe_comfyui_capabilities",
            "title": "Probe ComfyUI capabilities",
            "description": (
                "Use this before execution to discover the active local ComfyUI endpoint, "
                "required txt2img nodes, available checkpoints, and blocking setup issues."
            ),
            "inputSchema": ComfyUICapabilityProbeRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "prepare_visual_reference_workflows",
            "title": "Prepare ComfyUI workflows",
            "description": (
                "Use this when Fantasy Agent needs allowlisted ComfyUI workflow JSON and a "
                "run manifest from a ComfyUIVisualPlan. Defaults to in-memory output; set "
                "write_files only after generated file operations are approved."
            ),
            "inputSchema": ComfyUIMCPGenerateRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "run_visual_reference_workflow",
            "title": "Run ComfyUI visual references",
            "description": (
                "Use this after explicit confirmation to write prepared workflows, submit "
                "ComfyUI prompt jobs to a local endpoint, optionally poll history, and capture "
                "run manifests under generated/comfyui."
            ),
            "inputSchema": ComfyUIMCPExecuteRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
    ]


class ComfyUIMCPSafetyError(ValueError):
    pass


class ComfyUIMCPBridge:
    def __init__(
        self,
        workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.client_factory = client_factory or (lambda endpoint: ComfyUIClient(endpoint))

    def prepare_visual_reference_workflows(
        self,
        request: ComfyUIMCPGenerateRequest,
    ) -> ComfyUIMCPResult:
        self._assert_relative_under(request.output_dir, "generated/comfyui")
        checkpoint_name = _configured_checkpoint_name(request.plan, request.checkpoint_name)
        manifest = self._manifest(request.plan, request.output_dir, checkpoint_name)
        risks = self._validate_manifest(manifest, allow_remote_endpoint=False)
        if not _has_configured_checkpoint(request.plan, request.checkpoint_name):
            risks.append(
                "No ComfyUI checkpoint configured. Execution will probe local checkpoints and block if none exist."
            )
        written_files: list[str] = []
        if request.write_files:
            written_files = self._write_manifest_artifacts(manifest, request.output_dir)
        return ComfyUIMCPResult(
            status="written" if request.write_files else "planned",
            manifest=manifest,
            workflow_files=[job.workflow_path for job in manifest.jobs],
            manifest_path=self._manifest_path(request.output_dir),
            written_files=written_files,
            generated_images=[job.output_path for job in manifest.jobs],
            risks=risks,
        )

    def run_visual_reference_workflow(
        self,
        request: ComfyUIMCPExecuteRequest,
    ) -> ComfyUIMCPResult:
        self._assert_relative_under(request.output_dir, "generated/comfyui")
        configured_checkpoint = _configured_checkpoint_name(request.plan, request.checkpoint_name)
        manifest = self._manifest(request.plan, request.output_dir, configured_checkpoint)
        risks = self._validate_manifest(manifest, request.allow_remote_endpoint)
        manifest_path = self._manifest_path(request.output_dir)
        if not request.confirmed_side_effects:
            return ComfyUIMCPResult(
                status="blocked",
                manifest=manifest,
                workflow_files=[job.workflow_path for job in manifest.jobs],
                manifest_path=manifest_path,
                generated_images=[job.output_path for job in manifest.jobs],
                risks=[*risks, "ComfyUI execution requires confirmed_side_effects=true."],
            )

        if request.validate_server_capabilities:
            probe = self.probe_comfyui_capabilities(
                ComfyUICapabilityProbeRequest(
                    endpoint=request.plan.endpoint,
                    endpoint_candidates=request.endpoint_candidates,
                    auto_discover_endpoint=request.auto_discover_endpoint,
                    allow_remote_endpoint=request.allow_remote_endpoint,
                    preferred_checkpoint_name=request.checkpoint_name or request.plan.checkpoint_name,
                    require_checkpoint=True,
                )
            )
            selected_checkpoint = configured_checkpoint
            if probe.selected_checkpoint:
                selected_checkpoint = probe.selected_checkpoint
            runtime_plan = request.plan.model_copy(
                update={"endpoint": probe.endpoint, "checkpoint_name": selected_checkpoint}
            )
            manifest = self._manifest(runtime_plan, request.output_dir, selected_checkpoint)
            risks = [
                *self._validate_manifest(manifest, request.allow_remote_endpoint),
                *probe.warnings,
            ]
            if probe.blockers or probe.status != "ready":
                return ComfyUIMCPResult(
                    status="blocked",
                    manifest=manifest,
                    workflow_files=[job.workflow_path for job in manifest.jobs],
                    manifest_path=manifest_path,
                    generated_images=[job.output_path for job in manifest.jobs],
                    stderr_tail="; ".join(probe.blockers),
                    risks=[*risks, *probe.blockers],
                )

        workflow_files = self._write_manifest_artifacts(manifest, request.output_dir)
        client = self.client_factory(manifest.endpoint)
        prompt_ids: list[str] = []
        stdout_events: list[str] = []
        try:
            for job in manifest.jobs:
                response = client.queue_prompt(job.workflow, client_id=f"fantasy-agent-{job.job_id}")
                prompt_id = str(response.get("prompt_id") or response.get("id") or "")
                if not prompt_id:
                    raise ComfyUIMCPSafetyError(f"ComfyUI did not return a prompt_id for {job.job_id}.")
                prompt_ids.append(prompt_id)
                stdout_events.append(json.dumps({"job_id": job.job_id, "response": response}))
            generated_images = list(manifest.generated_images)
            if request.wait_for_completion:
                generated_images = self._wait_for_outputs(client, manifest, prompt_ids, request)
        except Exception as exc:  # noqa: BLE001 - MCP must return structured failures
            stdout_path, stderr_path = self._log_paths(manifest.plan_name)
            self._write_text(stdout_path, "\n".join(stdout_events))
            self._write_text(stderr_path, str(exc))
            failed_manifest = manifest.model_copy(update={"prompt_ids": prompt_ids})
            self._write_run_manifest(failed_manifest, manifest_path)
            return ComfyUIMCPResult(
                status="failed",
                manifest=failed_manifest,
                workflow_files=workflow_files,
                manifest_path=manifest_path,
                written_files=workflow_files,
                prompt_ids=prompt_ids,
                generated_images=generated_images if "generated_images" in locals() else [],
                log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
                stderr_tail=str(exc),
                risks=[*risks, "ComfyUI execution failed."],
            )

        stdout_path, stderr_path = self._log_paths(manifest.plan_name)
        executed_manifest = manifest.model_copy(
            update={"prompt_ids": prompt_ids, "generated_images": generated_images}
        )
        self._write_run_manifest(executed_manifest, manifest_path)
        self._write_text(stdout_path, "\n".join(stdout_events))
        self._write_text(stderr_path, "")
        return ComfyUIMCPResult(
            status="executed" if request.wait_for_completion else "queued",
            manifest=executed_manifest,
            workflow_files=workflow_files,
            manifest_path=manifest_path,
            written_files=workflow_files,
            prompt_ids=prompt_ids,
            generated_images=generated_images,
            log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
            risks=risks,
        )

    def probe_comfyui_capabilities(
        self,
        request: ComfyUICapabilityProbeRequest,
    ) -> ComfyUICapabilityProbeResult:
        endpoint, endpoint_warnings = self._resolve_endpoint(request)
        if endpoint is None:
            return ComfyUICapabilityProbeResult(
                status="unavailable",
                endpoint=request.endpoint,
                blockers=["No reachable ComfyUI endpoint found."],
                warnings=endpoint_warnings,
            )

        client = self.client_factory(endpoint)
        try:
            system_stats = client.system_stats()
            object_info = client.object_info()
            checkpoints = client.models("checkpoints")
        except Exception as exc:  # noqa: BLE001 - capability probes must report structured failures
            return ComfyUICapabilityProbeResult(
                status="unavailable",
                endpoint=endpoint,
                blockers=[f"Failed to read ComfyUI capabilities: {exc}"],
                warnings=endpoint_warnings,
            )

        checkpoints = _dedupe([*checkpoints, *_checkpoint_loader_options(object_info)])
        required_nodes = {node: node in object_info for node in request.required_nodes}
        selected_checkpoint = _select_checkpoint(request.preferred_checkpoint_name, checkpoints)
        blockers: list[str] = []
        missing_nodes = [node for node, present in required_nodes.items() if not present]
        if missing_nodes:
            blockers.append(f"Missing required ComfyUI nodes: {', '.join(missing_nodes)}.")
        if request.require_checkpoint and not selected_checkpoint:
            blockers.append(
                "No local checkpoint models are available. Add a .safetensors or .ckpt file under "
                "ComfyUI/models/checkpoints, then restart or refresh ComfyUI."
            )
        system = system_stats.get("system", {}) if isinstance(system_stats, dict) else {}
        devices = system_stats.get("devices", []) if isinstance(system_stats, dict) else []
        device_names = [str(device.get("name", "unknown")) for device in devices if isinstance(device, dict)]
        status = "ready" if not blockers else "degraded"
        return ComfyUICapabilityProbeResult(
            status=status,
            endpoint=endpoint,
            comfyui_version=system.get("comfyui_version"),
            python_version=system.get("python_version"),
            pytorch_version=system.get("pytorch_version"),
            devices=device_names,
            required_nodes=required_nodes,
            checkpoints=checkpoints,
            selected_checkpoint=selected_checkpoint,
            blockers=blockers,
            warnings=endpoint_warnings,
        )

    def _manifest(
        self,
        plan: ComfyUIVisualPlan,
        output_dir: str,
        checkpoint_name: str,
    ) -> ComfyUIRunManifest:
        jobs = [
            self._workflow_artifact(plan, job, output_dir, index, checkpoint_name)
            for index, job in enumerate(plan.jobs)
        ]
        return ComfyUIRunManifest(
            plan_name=plan.plan_name,
            endpoint=plan.endpoint,
            jobs=jobs,
            generated_images=[job.output_path for job in jobs],
            risks=[
                "ComfyUI outputs are references, not proof of playable progress.",
                "Generated images require review before use as Unreal textures or UI assets.",
            ],
        )

    def _workflow_artifact(
        self,
        plan: ComfyUIVisualPlan,
        job: ComfyUIPromptJob,
        output_dir: str,
        index: int,
        checkpoint_name: str,
    ) -> ComfyUIWorkflowArtifact:
        template_path = self._resolve_template_path(job.workflow_template)
        template = json.loads(template_path.read_text(encoding="utf-8"))
        seed = _stable_seed(f"{plan.plan_name}:{job.job_id}:{index}")
        output_path = self._normalized_output_path(output_dir, plan.plan_name, job)
        workflow = _inject_placeholders(
            template,
            {
                "prompt": job.prompt,
                "negative_prompt": job.negative_prompt,
                "seed": seed,
                "output_path": output_path,
                "job_id": job.job_id,
                "gameplay_constraint": job.gameplay_constraint,
                "checkpoint_name": checkpoint_name,
                "filename_prefix": f"FantasyAgent/{_slug(plan.plan_name)}/{_slug(job.job_id)}",
            },
        )
        workflow_path = (
            Path(output_dir.replace("\\", "/"))
            / "workflows"
            / _slug(plan.plan_name)
            / f"{_slug(job.job_id)}.json"
        ).as_posix()
        return ComfyUIWorkflowArtifact(
            job_id=job.job_id,
            workflow_template=job.workflow_template,
            workflow_path=workflow_path,
            workflow=workflow,
            output_path=output_path,
            prompt=job.prompt,
            negative_prompt=job.negative_prompt,
            gameplay_constraint=job.gameplay_constraint,
            seed=seed,
        )

    def _validate_manifest(
        self,
        manifest: ComfyUIRunManifest,
        allow_remote_endpoint: bool,
    ) -> list[str]:
        if not allow_remote_endpoint and not _is_local_endpoint(manifest.endpoint):
            raise ComfyUIMCPSafetyError(
                f"ComfyUI endpoint must be local unless allow_remote_endpoint=true: {manifest.endpoint}"
            )
        if not manifest.jobs:
            raise ComfyUIMCPSafetyError("ComfyUI visual plan must contain at least one job.")
        for job in manifest.jobs:
            if not job.gameplay_constraint.strip():
                raise ComfyUIMCPSafetyError(f"Job {job.job_id} is missing gameplay_constraint.")
            self._assert_relative_under(job.workflow_path, "generated/comfyui")
            self._assert_relative_under(job.output_path, "generated/comfyui")
            self._resolve_template_path(job.workflow_template)
            errors = _workflow_validation_errors(job.workflow)
            if errors:
                raise ComfyUIMCPSafetyError(
                    f"ComfyUI workflow template is not executable for job {job.job_id}: "
                    + " ".join(errors)
                )
        return list(manifest.risks)

    def _resolve_endpoint(
        self,
        request: ComfyUICapabilityProbeRequest,
    ) -> tuple[str | None, list[str]]:
        candidates = [request.endpoint]
        if request.auto_discover_endpoint:
            candidates = _dedupe([request.endpoint, *request.endpoint_candidates])
        warnings: list[str] = []
        for endpoint in candidates:
            if not request.allow_remote_endpoint and not _is_local_endpoint(endpoint):
                warnings.append(f"Skipped non-local ComfyUI endpoint: {endpoint}")
                continue
            try:
                client = self.client_factory(endpoint)
                client.system_stats()
            except Exception:
                continue
            if endpoint != request.endpoint:
                warnings.append(f"Auto-discovered active ComfyUI endpoint: {endpoint}")
            return endpoint, warnings
        return None, warnings

    def _write_manifest_artifacts(self, manifest: ComfyUIRunManifest, output_dir: str) -> list[str]:
        written: list[str] = []
        for job in manifest.jobs:
            path = self._resolve_workspace_path(job.workflow_path)
            self._write_text(path, json.dumps(job.workflow, indent=2))
            written.append(self._display_path(path))
        manifest_path = self._resolve_workspace_path(self._manifest_path(output_dir))
        self._write_run_manifest(manifest, manifest_path.as_posix())
        written.append(self._display_path(manifest_path))
        return written

    def _write_run_manifest(self, manifest: ComfyUIRunManifest, manifest_path: str) -> None:
        path = self._resolve_workspace_path(manifest_path)
        self._write_text(path, json.dumps(manifest.model_dump(mode="json"), indent=2))

    def _wait_for_outputs(
        self,
        client: Any,
        manifest: ComfyUIRunManifest,
        prompt_ids: list[str],
        request: ComfyUIMCPExecuteRequest,
    ) -> list[str]:
        deadline = time.monotonic() + request.timeout_seconds
        generated = list(manifest.generated_images)
        remaining = dict(zip(prompt_ids, manifest.jobs, strict=True))
        while remaining and time.monotonic() < deadline:
            for prompt_id, job in list(remaining.items()):
                history = client.history(prompt_id)
                image_refs = _extract_image_refs(history, prompt_id)
                if image_refs:
                    first = image_refs[0]
                    client.download_image(
                        first["filename"],
                        first.get("subfolder", ""),
                        first.get("type", "output"),
                        self._resolve_workspace_path(job.output_path).as_posix(),
                    )
                    remaining.pop(prompt_id)
            if remaining:
                time.sleep(request.poll_interval_seconds)
        if remaining:
            raise TimeoutError(f"Timed out waiting for ComfyUI outputs: {', '.join(remaining)}")
        return generated

    def _normalized_output_path(
        self,
        output_dir: str,
        plan_name: str,
        job: ComfyUIPromptJob,
    ) -> str:
        path = Path(job.output_path.replace("\\", "/"))
        if path.parts[:2] == ("generated", "comfyui"):
            return path.as_posix()
        suffix = path.suffix or ".png"
        return (Path(output_dir) / _slug(plan_name) / f"{_slug(job.job_id)}{suffix}").as_posix()

    def _manifest_path(self, output_dir: str) -> str:
        return (Path(output_dir.replace("\\", "/")) / "run-manifest.json").as_posix()

    def _resolve_template_path(self, path: str) -> Path:
        self._assert_relative_under(path, "templates/comfyui")
        resolved = self._resolve_workspace_path(path)
        if not resolved.exists():
            raise ComfyUIMCPSafetyError(f"ComfyUI workflow template does not exist: {path}")
        return resolved

    def _assert_relative_under(self, path: str, required_prefix: str) -> None:
        if Path(path).is_absolute():
            raise ComfyUIMCPSafetyError(f"Absolute paths are not allowed: {path}")
        normalized = Path(path.replace("\\", "/"))
        if ".." in normalized.parts:
            raise ComfyUIMCPSafetyError(f"Parent traversal is not allowed: {path}")
        prefix = Path(required_prefix)
        if normalized.parts[: len(prefix.parts)] != prefix.parts:
            raise ComfyUIMCPSafetyError(f"Path must stay under {required_prefix}: {path}")
        self._resolve_workspace_path(path)

    def _resolve_workspace_path(self, path: str) -> Path:
        resolved = (self.workspace_root / path).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ComfyUIMCPSafetyError(f"Path escapes workspace: {path}") from exc
        return resolved

    def _log_paths(self, plan_name: str) -> tuple[Path, Path]:
        safe_name = _slug(plan_name)
        log_dir = self.workspace_root / "generated" / "logs" / "comfyui"
        return log_dir / f"{safe_name}.stdout.log", log_dir / f"{safe_name}.stderr.log"

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        return path.relative_to(self.workspace_root).as_posix()


def call_comfyui_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> dict[str, Any]:
    bridge = ComfyUIMCPBridge(workspace_root)
    try:
        if name == "probe_comfyui_capabilities":
            request = ComfyUICapabilityProbeRequest.model_validate(arguments or {})
            result = bridge.probe_comfyui_capabilities(request)
            return {
                "structuredContent": result.model_dump(mode="json"),
                "content": [{"type": "text", "text": _probe_content_summary(result)}],
            }
        if name == "prepare_visual_reference_workflows":
            request = ComfyUIMCPGenerateRequest.model_validate(arguments or {})
            result = bridge.prepare_visual_reference_workflows(request)
        elif name == "run_visual_reference_workflow":
            request = ComfyUIMCPExecuteRequest.model_validate(arguments or {})
            result = bridge.run_visual_reference_workflow(request)
        else:
            available = ", ".join(tool["name"] for tool in tool_descriptors())
            return _error(f"Unknown ComfyUI MCP tool '{name}'. Available tools: {available}.")
        return {
            "structuredContent": result.model_dump(mode="json"),
            "content": [{"type": "text", "text": _content_summary(result)}],
        }
    except (ValidationError, ComfyUIMCPSafetyError) as exc:
        return _error(str(exc))


def _probe_content_summary(result: ComfyUICapabilityProbeResult) -> str:
    if result.status == "ready":
        return f"ComfyUI is ready at {result.endpoint} with checkpoint {result.selected_checkpoint}."
    if result.status == "degraded":
        return f"ComfyUI is reachable at {result.endpoint}, but setup is incomplete: {' '.join(result.blockers)}"
    return f"ComfyUI is unavailable at {result.endpoint}: {' '.join(result.blockers)}"


def _content_summary(result: ComfyUIMCPResult) -> str:
    if result.status == "blocked":
        reason = result.stderr_tail or (result.risks[-1] if result.risks else "preflight did not pass.")
        return f"ComfyUI MCP blocked execution: {reason}"
    if result.status == "failed":
        return "ComfyUI MCP failed. Check returned logs and stderr_tail."
    if result.status == "executed":
        return f"ComfyUI MCP completed {len(result.generated_images)} visual reference jobs."
    if result.status == "queued":
        return f"ComfyUI MCP queued {len(result.prompt_ids)} visual reference jobs."
    if result.status == "written":
        return f"ComfyUI MCP wrote {len(result.workflow_files)} prepared workflow files."
    return "ComfyUI MCP prepared workflow JSON and a run manifest."


def _error(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def _inject_placeholders(value: Any, replacements: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _inject_placeholders(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_inject_placeholders(item, replacements) for item in value]
    if isinstance(value, str):
        result = value
        for key, replacement in replacements.items():
            token = "{{ " + key + " }}"
            if result == token:
                return replacement
            result = result.replace(token, str(replacement))
        return result
    return value


def _stable_seed(value: str) -> int:
    seed = 0
    for char in value:
        seed = (seed * 131 + ord(char)) % 2_147_483_647
    return seed or 1


def _configured_checkpoint_name(plan: ComfyUIVisualPlan, request_checkpoint: str | None) -> str:
    return request_checkpoint or plan.checkpoint_name or "__FANTASY_AGENT_CHECKPOINT_REQUIRED__"


def _has_configured_checkpoint(plan: ComfyUIVisualPlan, request_checkpoint: str | None) -> bool:
    return bool((request_checkpoint or plan.checkpoint_name or "").strip())


def _checkpoint_loader_options(object_info: dict[str, Any]) -> list[str]:
    try:
        options = object_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except (KeyError, IndexError, TypeError):
        return []
    if isinstance(options, list):
        return [str(item) for item in options if str(item).strip()]
    return []


def _select_checkpoint(preferred: str | None, checkpoints: list[str]) -> str | None:
    if preferred:
        for checkpoint in checkpoints:
            if checkpoint == preferred:
                return checkpoint
        return None
    return checkpoints[0] if checkpoints else None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _workflow_validation_errors(workflow: dict[str, Any]) -> list[str]:
    if "nodes" in workflow and "links" in workflow:
        return ["Template looks like a ComfyUI UI export; save or convert it to API prompt JSON."]
    errors: list[str] = []
    output_node_found = False
    if not workflow:
        return ["Workflow graph is empty."]
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            errors.append(f"Node {node_id} must be an object.")
            continue
        class_type = node.get("class_type")
        inputs = node.get("inputs")
        if not isinstance(class_type, str) or not class_type:
            errors.append(f"Node {node_id} is missing class_type.")
        if not isinstance(inputs, dict):
            errors.append(f"Node {node_id} is missing inputs.")
        if class_type in {"SaveImage", "PreviewImage"}:
            output_node_found = True
    if not output_node_found:
        errors.append("Workflow graph needs a SaveImage or PreviewImage output node.")
    return errors


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "comfyui"


def _is_local_endpoint(endpoint: str) -> bool:
    parsed = parse.urlparse(endpoint)
    host = parsed.hostname or ""
    return host in {"127.0.0.1", "localhost", "::1"}


def _extract_image_refs(history: dict[str, Any], prompt_id: str) -> list[dict[str, str]]:
    record = history.get(prompt_id) if prompt_id in history else history
    outputs = record.get("outputs", {}) if isinstance(record, dict) else {}
    refs: list[dict[str, str]] = []
    for output in outputs.values():
        if not isinstance(output, dict):
            continue
        for image in output.get("images", []):
            if isinstance(image, dict) and image.get("filename"):
                refs.append(
                    {
                        "filename": str(image["filename"]),
                        "subfolder": str(image.get("subfolder", "")),
                        "type": str(image.get("type", "output")),
                    }
                )
    return refs
