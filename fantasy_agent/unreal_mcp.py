from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from fantasy_agent.contracts import (
    ComfyUIRunManifest,
    UnrealAssetIngestJob,
    UnrealAssetIngestManifest,
    UnrealContentManifest,
    UnrealMCPEditorCommandletRequest,
    UnrealMCPCreateProjectRequest,
    UnrealMCPPrepareAssetIngestRequest,
    UnrealMCPResult,
    UnrealMCPRunAssetIngestRequest,
    UnrealImportManifest,
    UnrealProjectArtifact,
    UnrealProjectPlan,
)

SERVER_NAME = "fantasy-agent-unreal-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_COMMANDLETS = {"MapCheck", "ResavePackages", "AssetAudit"}
BUILTIN_MODULE_NAMES = {"GameplayTags"}
COMMANDLET_DEFAULT_ARGS = {
    "MapCheck": [],
    "ResavePackages": ["-ProjectOnly"],
    "AssetAudit": [],
}


def tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": "create_project_structure",
            "title": "Create Unreal project structure",
            "description": (
                "Use this when Fantasy Agent needs a UE5 project descriptor, content folders, "
                "setup script, and content manifest from an UnrealProjectPlan. Defaults to "
                "in-memory output; set write_files only after file side effects are approved."
            ),
            "inputSchema": UnrealMCPCreateProjectRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "prepare_asset_ingest",
            "title": "Prepare Unreal asset ingest",
            "description": (
                "Use this when Fantasy Agent needs Unreal Python import automation for Blender "
                "mesh exports and reviewed ComfyUI reference images. Defaults to in-memory output; "
                "set write_files only after generated file side effects are approved."
            ),
            "inputSchema": UnrealMCPPrepareAssetIngestRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "run_asset_ingest",
            "title": "Run Unreal asset ingest",
            "description": (
                "Use this after explicit confirmation to launch Unreal Editor and execute a "
                "generated Fantasy Agent asset ingest Python script."
            ),
            "inputSchema": UnrealMCPRunAssetIngestRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
        {
            "name": "run_editor_commandlet",
            "title": "Run Unreal Editor commandlet",
            "description": (
                "Use this after explicit confirmation to run an allowlisted Unreal Editor "
                "commandlet against a generated .uproject and capture logs under generated/logs."
            ),
            "inputSchema": UnrealMCPEditorCommandletRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
    ]


class UnrealMCPSafetyError(ValueError):
    pass


class UnrealMCPBridge:
    def __init__(
        self,
        workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.runner = runner or subprocess.run

    def create_project_structure(self, request: UnrealMCPCreateProjectRequest) -> UnrealMCPResult:
        plan = self._load_plan(request)
        project_dir = request.project_dir or f"generated/unreal/{_slug(plan.project_name)}"
        artifact = self._artifact(plan, project_dir, request.content_manifest_path)
        manifest = self._manifest(plan, artifact, request.import_manifest_paths)
        risks = self._validate_artifact(artifact, manifest)
        created_paths = [artifact.project_dir, *artifact.content_folders]
        written_files: list[str] = []
        if request.write_files:
            written_files = self._write_project_artifact(artifact, manifest, plan)
        return UnrealMCPResult(
            status="written" if request.write_files else "planned",
            artifact=artifact,
            manifest=manifest,
            created_paths=created_paths,
            written_files=written_files,
            risks=risks,
        )

    def prepare_asset_ingest(self, request: UnrealMCPPrepareAssetIngestRequest) -> UnrealMCPResult:
        self._assert_unreal_project_file(request.project_file)
        if not request.blender_import_manifest_path and not request.comfyui_run_manifest_path:
            raise UnrealMCPSafetyError(
                "prepare_asset_ingest requires blender_import_manifest_path or comfyui_run_manifest_path."
            )

        import_script_path = request.import_script_path or _default_ingest_script_path(
            request.project_file
        )
        ingest_manifest_path = request.ingest_manifest_path or _default_ingest_manifest_path(
            request.project_file
        )
        self._assert_relative_under(import_script_path, "generated/unreal")
        self._assert_relative_under(ingest_manifest_path, "generated/unreal")

        jobs: list[UnrealAssetIngestJob] = []
        risks = [
            "ComfyUI images are imported as review references unless promoted by a later approved step.",
            "Blender mesh imports depend on generated UCX collision and Unreal importer behavior.",
        ]
        source_manifests: list[str] = []
        if request.blender_import_manifest_path:
            source_manifests.append(request.blender_import_manifest_path)
            jobs.extend(self._blender_ingest_jobs(request.blender_import_manifest_path))
        if request.comfyui_run_manifest_path:
            source_manifests.append(request.comfyui_run_manifest_path)
            jobs.extend(self._comfyui_ingest_jobs(request.comfyui_run_manifest_path))
        if not jobs:
            raise UnrealMCPSafetyError("Asset ingest requires at least one import job.")

        missing_sources = self._missing_sources(jobs)
        if missing_sources and request.require_existing_sources:
            raise UnrealMCPSafetyError(
                "Missing ingest source files: " + ", ".join(missing_sources[:6])
            )
        if missing_sources:
            risks.append(
                "Some source files do not exist yet and must be produced before Unreal ingest: "
                + ", ".join(missing_sources[:6])
            )

        manifest = UnrealAssetIngestManifest(
            project_file=request.project_file,
            import_script_path=import_script_path,
            jobs=jobs,
            source_manifests=source_manifests,
            risks=risks,
        )
        written_files: list[str] = []
        if request.write_files:
            written_files = self._write_asset_ingest(manifest, ingest_manifest_path)
        return UnrealMCPResult(
            status="written" if request.write_files else "planned",
            manifest=manifest,
            written_files=written_files,
            risks=risks,
        )

    def run_asset_ingest(self, request: UnrealMCPRunAssetIngestRequest) -> UnrealMCPResult:
        project_file = self._assert_unreal_project_file(request.project_file)
        self._assert_relative_under(request.import_script_path, "generated/unreal")
        import_script_path = self._resolve_workspace_path(request.import_script_path)
        if import_script_path.suffix.lower() != ".py":
            raise UnrealMCPSafetyError("Unreal asset ingest requires a generated Python script.")
        if not import_script_path.exists():
            raise UnrealMCPSafetyError(f"Unreal asset ingest script does not exist: {request.import_script_path}")

        command = [
            request.unreal_editor_cmd,
            project_file.as_posix(),
            f"-ExecutePythonScript={import_script_path.as_posix()}",
            "-unattended",
            "-nop4",
            "-DDC-ForceMemoryCache",
            f"-ShaderWorkingDir={self._shader_working_dir(project_file).as_posix()}",
            "-log",
        ]
        risks = [
            "Unreal asset ingest writes .uasset files and may update project metadata.",
            "Imported ComfyUI references must be reviewed before becoming production textures or UI.",
        ]
        if not request.confirmed_side_effects:
            return UnrealMCPResult(
                status="blocked",
                command=command,
                risks=[*risks, "Unreal asset ingest requires confirmed_side_effects=true."],
            )

        stdout_path, stderr_path = self._log_paths(project_file.stem, "asset_ingest")
        self._shader_working_dir(project_file).mkdir(parents=True, exist_ok=True)
        project_log_path = self._project_log_path(project_file)
        project_log_offset = project_log_path.stat().st_size if project_log_path.exists() else 0
        try:
            process = self.runner(
                command,
                cwd=project_file.parent,
                env=dict(os.environ),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=request.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            stderr = f"Unreal Editor command executable not found: {request.unreal_editor_cmd}"
            self._write_text(stderr_path, stderr)
            return UnrealMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stderr_path)],
                stderr_tail=stderr,
                risks=[*risks, str(exc)],
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr) or f"Unreal asset ingest timed out after {request.timeout_seconds}s."
            self._write_text(stdout_path, stdout)
            self._write_text(stderr_path, stderr)
            return UnrealMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
                risks=[*risks, "Unreal asset ingest timed out."],
            )

        self._write_text(stdout_path, _to_text(process.stdout))
        self._write_text(stderr_path, _to_text(process.stderr))
        project_log_tail = self._project_log_tail(project_file, project_log_offset)
        python_failed = (
            "LogPython: Error" in project_log_tail
            or "Python script executed with errors" in project_log_tail
        )
        stderr_tail = _tail(process.stderr)
        if python_failed:
            stderr_tail = project_log_tail
        return UnrealMCPResult(
            status="executed" if process.returncode == 0 and not python_failed else "failed",
            command=command,
            log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
            return_code=process.returncode,
            stdout_tail=_tail(process.stdout),
            stderr_tail=stderr_tail,
            risks=risks
            if process.returncode == 0 and not python_failed
            else [
                *risks,
                (
                    "Unreal Python asset ingest logged errors."
                    if python_failed
                    else "Unreal asset ingest returned a non-zero code."
                ),
            ],
        )

    def run_editor_commandlet(self, request: UnrealMCPEditorCommandletRequest) -> UnrealMCPResult:
        project_file = self._assert_unreal_project_file(request.project_file)
        if request.commandlet not in ALLOWED_COMMANDLETS:
            raise UnrealMCPSafetyError(f"Commandlet is not allowlisted: {request.commandlet}")

        command = [
            request.unreal_editor_cmd,
            project_file.as_posix(),
            f"-run={request.commandlet}",
            *COMMANDLET_DEFAULT_ARGS[request.commandlet],
            "-unattended",
            "-nop4",
            "-DDC-ForceMemoryCache",
            f"-ShaderWorkingDir={self._shader_working_dir(project_file).as_posix()}",
            "-log",
        ]
        risks = [
            "Unreal commandlets can load project plugins and may write project metadata.",
            "Validation output must be reviewed before packaging or visual expansion.",
        ]
        if not request.confirmed_side_effects:
            return UnrealMCPResult(
                status="blocked",
                command=command,
                risks=[*risks, "Unreal execution requires confirmed_side_effects=true."],
            )

        stdout_path, stderr_path = self._log_paths(project_file.stem, request.commandlet)
        self._shader_working_dir(project_file).mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        try:
            process = self.runner(
                command,
                cwd=project_file.parent,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=request.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            stderr = f"Unreal Editor command executable not found: {request.unreal_editor_cmd}"
            self._write_text(stderr_path, stderr)
            return UnrealMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stderr_path)],
                stderr_tail=stderr,
                risks=[*risks, str(exc)],
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or f"Unreal commandlet timed out after {request.timeout_seconds}s."
            self._write_text(stdout_path, _to_text(stdout))
            self._write_text(stderr_path, _to_text(stderr))
            return UnrealMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
                risks=[*risks, "Unreal commandlet timed out."],
            )

        self._write_text(stdout_path, _to_text(process.stdout))
        self._write_text(stderr_path, _to_text(process.stderr))
        return UnrealMCPResult(
            status="executed" if process.returncode == 0 else "failed",
            command=command,
            log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
            return_code=process.returncode,
            stdout_tail=_tail(process.stdout),
            stderr_tail=_tail(process.stderr),
            risks=risks
            if process.returncode == 0
            else [*risks, "Unreal commandlet returned a non-zero code."],
        )

    def _load_plan(self, request: UnrealMCPCreateProjectRequest) -> UnrealProjectPlan:
        if request.plan is not None:
            return request.plan
        if not request.plan_path:
            raise UnrealMCPSafetyError("create_project_structure requires plan or plan_path.")
        self._assert_relative_under(request.plan_path, "generated")
        path = self._resolve_workspace_path(request.plan_path)
        if not path.exists():
            raise UnrealMCPSafetyError(f"Unreal project plan does not exist: {request.plan_path}")
        data: Any
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return UnrealProjectPlan.model_validate(data)

    def _blender_ingest_jobs(self, manifest_path: str) -> list[UnrealAssetIngestJob]:
        self._assert_relative_under(manifest_path, "generated")
        manifest = UnrealImportManifest.model_validate(self._load_manifest_data(manifest_path))
        jobs: list[UnrealAssetIngestJob] = []
        for asset in manifest.assets:
            self._assert_relative_under(asset.source_file, "generated/assets")
            if not asset.source_file.lower().endswith((".fbx", ".glb")):
                raise UnrealMCPSafetyError(
                    f"Blender source asset must be .fbx or .glb: {asset.source_file}"
                )
            _assert_game_path(asset.destination_path)
            jobs.append(
                UnrealAssetIngestJob(
                    job_id=f"blender_{_slug(asset.asset_name)}",
                    source="blender",
                    asset_type="static_mesh",
                    source_file=asset.source_file,
                    destination_path=asset.destination_path,
                    asset_name=asset.asset_name,
                    gameplay_role=asset.gameplay_role,
                    source_manifest=manifest_path,
                    import_settings={
                        **manifest.import_settings,
                        "collision_object": asset.collision_object,
                        "material_key": asset.material_key,
                        "unit_scale": manifest.import_settings.get("unit_scale", 1.0),
                    },
                )
            )
        return jobs

    def _comfyui_ingest_jobs(self, manifest_path: str) -> list[UnrealAssetIngestJob]:
        self._assert_relative_under(manifest_path, "generated/comfyui")
        manifest = ComfyUIRunManifest.model_validate(self._load_manifest_data(manifest_path))
        outputs = manifest.generated_images or [job.output_path for job in manifest.jobs]
        job_by_path = {job.output_path: job for job in manifest.jobs}
        jobs: list[UnrealAssetIngestJob] = []
        for index, output_path in enumerate(outputs):
            self._assert_relative_under(output_path, "generated/comfyui")
            if not output_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                raise UnrealMCPSafetyError(f"ComfyUI source image is not importable: {output_path}")
            prompt_job = job_by_path.get(output_path)
            job_id = prompt_job.job_id if prompt_job else f"comfyui_reference_{index + 1}"
            asset_name = _unreal_identifier(Path(output_path).stem)
            jobs.append(
                UnrealAssetIngestJob(
                    job_id=f"comfyui_{_slug(job_id)}",
                    source="comfyui",
                    asset_type="texture_reference",
                    source_file=output_path,
                    destination_path="/Game/Art/References/ComfyUI",
                    asset_name=asset_name,
                    gameplay_role=(
                        prompt_job.gameplay_constraint
                        if prompt_job
                        else "Reviewed visual reference for gameplay readability."
                    ),
                    source_manifest=manifest_path,
                    import_settings={
                        "reference_only": True,
                        "prompt_id": ",".join(manifest.prompt_ids),
                    },
                    review_required=True,
                )
            )
        return jobs

    def _load_manifest_data(self, path: str) -> Any:
        resolved = self._resolve_workspace_path(path)
        if not resolved.exists():
            raise UnrealMCPSafetyError(f"Source manifest does not exist: {path}")
        if resolved.suffix.lower() == ".json":
            return json.loads(resolved.read_text(encoding="utf-8"))
        return yaml.safe_load(resolved.read_text(encoding="utf-8"))

    def _missing_sources(self, jobs: list[UnrealAssetIngestJob]) -> list[str]:
        return [job.source_file for job in jobs if not self._resolve_workspace_path(job.source_file).exists()]

    def _write_asset_ingest(
        self,
        manifest: UnrealAssetIngestManifest,
        ingest_manifest_path: str,
    ) -> list[str]:
        manifest_path = self._resolve_workspace_path(ingest_manifest_path)
        script_path = self._resolve_workspace_path(manifest.import_script_path)
        self._write_text(manifest_path, json.dumps(manifest.model_dump(mode="json"), indent=2))
        self._write_text(script_path, _asset_ingest_script(manifest))
        return [self._display_path(manifest_path), self._display_path(script_path)]

    def _artifact(
        self,
        plan: UnrealProjectPlan,
        project_dir: str,
        content_manifest_path: str | None,
    ) -> UnrealProjectArtifact:
        project_root = Path(project_dir.replace("\\", "/"))
        project_name = _unreal_identifier(plan.project_name)
        manifest_path = content_manifest_path or (
            project_root / "fantasy-agent-content-manifest.json"
        ).as_posix()
        content_folders = [
            (project_root / folder.replace("\\", "/")).as_posix() for folder in plan.folders
        ]
        return UnrealProjectArtifact(
            project_name=project_name,
            project_dir=project_root.as_posix(),
            project_file=(project_root / f"{project_name}.uproject").as_posix(),
            content_manifest_path=manifest_path,
            setup_script_path=(project_root / "Scripts" / "fantasy_agent_setup.py").as_posix(),
            config_files=[(project_root / "Config" / "DefaultGame.ini").as_posix()],
            content_folders=content_folders,
            side_effects=[
                "creates generated Unreal project descriptor and Config files",
                "creates Content folder hierarchy for gameplay prototype assets",
                "writes Unreal Python setup script and Fantasy Agent content manifest",
            ],
        )

    def _manifest(
        self,
        plan: UnrealProjectPlan,
        artifact: UnrealProjectArtifact,
        import_manifest_paths: list[str],
    ) -> UnrealContentManifest:
        return UnrealContentManifest(
            project_name=artifact.project_name,
            engine_version=plan.engine_version,
            template=plan.template,
            plugins=plan.plugins,
            content_folders=plan.folders,
            gameplay_classes=plan.gameplay_classes,
            blueprints=plan.blueprints,
            maps=plan.maps,
            automation_steps=plan.automation_steps,
            import_manifests=import_manifest_paths,
        )

    def _validate_artifact(
        self,
        artifact: UnrealProjectArtifact,
        manifest: UnrealContentManifest,
    ) -> list[str]:
        self._assert_relative_under(artifact.project_dir, "generated/unreal")
        self._assert_relative_under(artifact.project_file, "generated/unreal")
        self._assert_relative_under(artifact.content_manifest_path, "generated/unreal")
        self._assert_relative_under(artifact.setup_script_path, "generated/unreal")
        for config_file in artifact.config_files:
            self._assert_relative_under(config_file, "generated/unreal")
        if not artifact.project_file.endswith(".uproject"):
            raise UnrealMCPSafetyError("Generated Unreal project file must end with .uproject.")
        for folder in manifest.content_folders:
            normalized = folder.replace("\\", "/")
            if not normalized.startswith("Content/"):
                raise UnrealMCPSafetyError(f"Unreal content folder must start with Content/: {folder}")
        for folder in artifact.content_folders:
            self._assert_relative_under(folder, "generated/unreal")
        for import_manifest in manifest.import_manifests:
            self._assert_relative_under(import_manifest, "generated")
        return [
            "Generated UE files are setup handoffs; Unreal Editor still owns .uasset creation.",
            "Blueprint and map names are planned identifiers until Unreal automation runs.",
        ]

    def _write_project_artifact(
        self,
        artifact: UnrealProjectArtifact,
        manifest: UnrealContentManifest,
        plan: UnrealProjectPlan,
    ) -> list[str]:
        project_dir = self._resolve_workspace_path(artifact.project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)
        for folder in artifact.content_folders:
            self._resolve_workspace_path(folder).mkdir(parents=True, exist_ok=True)

        project_file = self._resolve_workspace_path(artifact.project_file)
        manifest_path = self._resolve_workspace_path(artifact.content_manifest_path)
        setup_script_path = self._resolve_workspace_path(artifact.setup_script_path)
        config_path = self._resolve_workspace_path(artifact.config_files[0])

        self._write_text(project_file, json.dumps(_uproject_descriptor(plan), indent=2))
        self._write_text(manifest_path, json.dumps(manifest.model_dump(mode="json"), indent=2))
        self._write_text(setup_script_path, _setup_script(manifest))
        self._write_text(config_path, _default_game_ini(plan))
        return [
            self._display_path(project_file),
            self._display_path(manifest_path),
            self._display_path(setup_script_path),
            self._display_path(config_path),
        ]

    def _assert_unreal_project_file(self, path: str) -> Path:
        self._assert_relative_under(path, "generated/unreal")
        project_file = self._resolve_workspace_path(path)
        if project_file.suffix.lower() != ".uproject":
            raise UnrealMCPSafetyError("Unreal operations require a .uproject file.")
        return project_file

    def _assert_relative_under(self, path: str, required_prefix: str) -> None:
        if Path(path).is_absolute():
            raise UnrealMCPSafetyError(f"Absolute paths are not allowed: {path}")
        normalized = Path(path.replace("\\", "/"))
        if ".." in normalized.parts:
            raise UnrealMCPSafetyError(f"Parent traversal is not allowed: {path}")
        prefix = Path(required_prefix)
        if normalized.parts[: len(prefix.parts)] != prefix.parts:
            raise UnrealMCPSafetyError(f"Path must stay under {required_prefix}: {path}")
        self._resolve_workspace_path(path)

    def _resolve_workspace_path(self, path: str) -> Path:
        resolved = (self.workspace_root / path).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise UnrealMCPSafetyError(f"Path escapes workspace: {path}") from exc
        return resolved

    def _log_paths(self, project_name: str, commandlet: str) -> tuple[Path, Path]:
        safe_name = f"{_slug(project_name)}_{_slug(commandlet)}"
        log_dir = self.workspace_root / "generated" / "logs" / "unreal"
        return log_dir / f"{safe_name}.stdout.log", log_dir / f"{safe_name}.stderr.log"

    def _project_log_path(self, project_file: Path) -> Path:
        return project_file.parent / "Saved" / "Logs" / f"{project_file.stem}.log"

    def _shader_working_dir(self, project_file: Path) -> Path:
        return project_file.parent / "Intermediate" / "Shaders" / "WorkingDirectory"

    def _project_log_tail(self, project_file: Path, start: int = 0, limit: int = 12000) -> str:
        log_path = self._project_log_path(project_file)
        if not log_path.exists():
            return ""
        with log_path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(start)
            return handle.read()[-limit:]

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        return path.relative_to(self.workspace_root).as_posix()


def call_unreal_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> dict[str, Any]:
    bridge = UnrealMCPBridge(workspace_root)
    try:
        if name == "create_project_structure":
            request = UnrealMCPCreateProjectRequest.model_validate(arguments or {})
            result = bridge.create_project_structure(request)
        elif name == "prepare_asset_ingest":
            request = UnrealMCPPrepareAssetIngestRequest.model_validate(arguments or {})
            result = bridge.prepare_asset_ingest(request)
        elif name == "run_asset_ingest":
            request = UnrealMCPRunAssetIngestRequest.model_validate(arguments or {})
            result = bridge.run_asset_ingest(request)
        elif name == "run_editor_commandlet":
            request = UnrealMCPEditorCommandletRequest.model_validate(arguments or {})
            result = bridge.run_editor_commandlet(request)
        else:
            available = ", ".join(tool["name"] for tool in tool_descriptors())
            return _error(f"Unknown Unreal MCP tool '{name}'. Available tools: {available}.")
        return {
            "structuredContent": result.model_dump(mode="json"),
            "content": [{"type": "text", "text": _content_summary(result)}],
        }
    except (ValidationError, UnrealMCPSafetyError) as exc:
        return _error(str(exc))


def _content_summary(result: UnrealMCPResult) -> str:
    if result.status == "blocked":
        return "Unreal MCP blocked execution because side effects were not confirmed."
    if result.status == "failed":
        return "Unreal MCP failed. Check returned logs and stderr_tail."
    if result.status == "executed":
        return "Unreal MCP executed the commandlet and captured logs."
    if result.status == "written":
        return f"Unreal MCP wrote {len(result.written_files)} generated handoff files."
    return "Unreal MCP prepared a project structure and automation handoff."


def _error(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def _uproject_descriptor(plan: UnrealProjectPlan) -> dict[str, Any]:
    return {
        "FileVersion": 3,
        "EngineAssociation": plan.engine_version,
        "Category": "Fantasy Agent",
        "Description": "Fantasy Agent gameplay-first prototype handoff.",
        "Plugins": [
            {"Name": plugin, "Enabled": True}
            for plugin in plan.plugins
            if plugin not in BUILTIN_MODULE_NAMES
        ],
    }


def _setup_script(manifest: UnrealContentManifest) -> str:
    folders = [
        f"/Game/{folder.removeprefix('Content/').strip('/')}" for folder in manifest.content_folders
    ]
    maps = [f"/Game/Maps/{Path(map_name).stem}" for map_name in manifest.maps]
    return "\n".join(
        [
            '"""Fantasy Agent Unreal setup script.',
            "",
            "Run inside Unreal Python after opening the generated .uproject.",
            '"""',
            "",
            "import unreal",
            "",
            f"FOLDERS = {folders!r}",
            f"MAPS = {maps!r}",
            f"BLUEPRINTS = {manifest.blueprints!r}",
            f"GAMEPLAY_CLASSES = {manifest.gameplay_classes!r}",
            "",
            "asset_library = unreal.EditorAssetLibrary",
            "for folder in FOLDERS:",
            "    if not asset_library.does_directory_exist(folder):",
            "        asset_library.make_directory(folder)",
            "",
            "unreal.log('Fantasy Agent folders prepared: {}'.format(len(FOLDERS)))",
            "unreal.log('Planned maps: {}'.format(', '.join(MAPS)))",
            "unreal.log('Planned Blueprints: {}'.format(', '.join(BLUEPRINTS)))",
            "unreal.log('Planned gameplay classes: {}'.format(', '.join(GAMEPLAY_CLASSES)))",
            "",
        ]
    )


def _default_game_ini(plan: UnrealProjectPlan) -> str:
    first_map = plan.maps[0] if plan.maps else "M_Prototype_Greybox"
    map_path = f"/Game/Maps/{Path(first_map).stem}"
    return "\n".join(
        [
            "[/Script/EngineSettings.GameMapsSettings]",
            f"EditorStartupMap={map_path}",
            f"GameDefaultMap={map_path}",
            "",
        ]
    )


def _asset_ingest_script(manifest: UnrealAssetIngestManifest) -> str:
    payload = json.dumps(manifest.model_dump(mode="json"), indent=2)
    return f'''"""Fantasy Agent Unreal asset ingest script.

Run inside Unreal Editor Python through Unreal MCP after side effects are confirmed.
"""

from __future__ import annotations

import json
from pathlib import Path

import unreal


MANIFEST = json.loads({payload!r})


def find_repo_root() -> Path:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if (parent / "fantasy_agent").exists():
            return parent
    return script_path.parents[3]


REPO_ROOT = find_repo_root()


def source_path(job: dict) -> str:
    return str((REPO_ROOT / job["source_file"]).resolve())


def ensure_directory(path: str) -> None:
    library = unreal.EditorAssetLibrary
    if not library.does_directory_exist(path):
        library.make_directory(path)


def set_if_available(obj, name: str, value) -> None:
    if hasattr(obj, name):
        setattr(obj, name, value)


def mesh_options(job: dict):
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = bool(job["import_settings"].get("import_materials", True))
    options.import_textures = False
    data = options.static_mesh_import_data
    set_if_available(data, "combine_meshes", bool(job["import_settings"].get("combine_meshes", False)))
    set_if_available(
        data,
        "auto_generate_collision",
        bool(job["import_settings"].get("generate_missing_collision", False)),
    )
    return options


def import_job(job: dict) -> None:
    ensure_directory(job["destination_path"])
    task = unreal.AssetImportTask()
    task.filename = source_path(job)
    task.destination_path = job["destination_path"]
    task.destination_name = job["asset_name"]
    task.automated = True
    task.save = True
    task.replace_existing = True
    if job["asset_type"] == "static_mesh" and task.filename.lower().endswith(".fbx"):
        task.options = mesh_options(job)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    unreal.log("Fantasy Agent imported {{}} -> {{}}".format(task.filename, task.destination_path))


for ingest_job in MANIFEST["jobs"]:
    if ingest_job["source"] == "comfyui" and ingest_job.get("review_required", False):
        unreal.log_warning(
            "Importing ComfyUI reference only; review before production use: {{}}".format(
                ingest_job["source_file"]
            )
        )
    import_job(ingest_job)

unreal.log("Fantasy Agent asset ingest complete: {{}} jobs".format(len(MANIFEST["jobs"])))
'''


def _default_ingest_script_path(project_file: str) -> str:
    project_root = Path(project_file.replace("\\", "/")).parent
    return (project_root / "Scripts" / "fantasy_agent_asset_ingest.py").as_posix()


def _default_ingest_manifest_path(project_file: str) -> str:
    project_root = Path(project_file.replace("\\", "/")).parent
    return (project_root / "fantasy-agent-asset-ingest.json").as_posix()


def _assert_game_path(path: str) -> None:
    if not path.startswith("/Game/"):
        raise UnrealMCPSafetyError(f"Unreal destination path must start with /Game/: {path}")


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "unreal_project"


def _unreal_identifier(value: str) -> str:
    identifier = "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")
    if not identifier:
        identifier = "FantasyPrototype"
    if not identifier[0].isalpha():
        identifier = f"FA_{identifier}"
    return identifier


def _tail(value: str | bytes | None, limit: int = 4000) -> str:
    return _to_text(value)[-limit:]


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
