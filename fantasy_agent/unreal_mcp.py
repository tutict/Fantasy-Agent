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
    UnrealAssetIngestValidationReport,
    UnrealContentManifest,
    UnrealMCPEditorCommandletRequest,
    UnrealMCPCreateProjectRequest,
    UnrealMCPPrepareLevelAssemblyRequest,
    UnrealMCPPrepareAssetIngestRequest,
    UnrealMCPResult,
    UnrealMCPRunAssetIngestRequest,
    UnrealMCPRunLevelAssemblyRequest,
    UnrealMCPValidateLevelAssemblyRequest,
    UnrealMCPValidateAssetIngestRequest,
    UnrealImportManifest,
    UnrealLevelAssemblyManifest,
    UnrealLevelAssemblyValidationReport,
    UnrealLevelPlacement,
    UnrealPlayerStartPlacement,
    UnrealProjectArtifact,
    UnrealProjectPlan,
)

SERVER_NAME = "fantasy-agent-unreal-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_COMMANDLETS = {"DataValidation"}
BUILTIN_MODULE_NAMES = {"GameplayTags"}
COMMANDLET_DEFAULT_ARGS = {
    "DataValidation": ["-IncludeOnlyOnDiskAssets"],
}
UNREAL_DDC_ARGS = ["-DDC=InstalledNoZenLocalFallback"]


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
            "name": "validate_asset_ingest",
            "title": "Validate Unreal asset ingest manifest",
            "description": (
                "Use this before or after Unreal execution to verify generated asset ingest "
                "manifests, Unreal-safe names, source paths, destination paths, and expected "
                "UCX collision naming without launching Unreal."
            ),
            "inputSchema": UnrealMCPValidateAssetIngestRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "prepare_level_assembly",
            "title": "Prepare Unreal level assembly",
            "description": (
                "Use this after asset ingest planning to generate a playable greybox map "
                "assembly manifest and Unreal Python script. Defaults to in-memory output; "
                "set write_files only after generated file side effects are approved."
            ),
            "inputSchema": UnrealMCPPrepareLevelAssemblyRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "validate_level_assembly",
            "title": "Validate Unreal level assembly manifest",
            "description": (
                "Use this before or after Unreal execution to verify map path, route roles, "
                "spawn/objective/exit coverage, and imported asset availability."
            ),
            "inputSchema": UnrealMCPValidateLevelAssemblyRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "run_level_assembly",
            "title": "Run Unreal level assembly",
            "description": (
                "Use this after explicit confirmation to launch Unreal Editor and execute a "
                "generated Fantasy Agent level assembly Python script."
            ),
            "inputSchema": UnrealMCPRunLevelAssemblyRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
        {
            "name": "run_editor_commandlet",
            "title": "Run Unreal Editor data validation",
            "description": (
                "Use this after explicit confirmation to run Unreal Editor data validation "
                "against a generated .uproject and capture logs under generated/logs."
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

    def validate_asset_ingest(
        self, request: UnrealMCPValidateAssetIngestRequest
    ) -> UnrealMCPResult:
        self._assert_relative_under(request.ingest_manifest_path, "generated/unreal")
        manifest = UnrealAssetIngestManifest.model_validate(
            self._load_manifest_data(request.ingest_manifest_path)
        )
        issues, warnings = self._validate_ingest_manifest(manifest, request)
        report = UnrealAssetIngestValidationReport(
            ingest_manifest_path=request.ingest_manifest_path,
            project_file=manifest.project_file,
            job_count=len(manifest.jobs),
            issues=issues,
            warnings=warnings,
        )
        return UnrealMCPResult(
            status="executed" if not issues else "failed",
            manifest=manifest,
            validation_report=report,
            risks=warnings
            if not issues
            else [*warnings, "Unreal asset ingest manifest has validation issues."],
        )

    def prepare_level_assembly(
        self, request: UnrealMCPPrepareLevelAssemblyRequest
    ) -> UnrealMCPResult:
        self._assert_unreal_project_file(request.project_file)
        self._assert_relative_under(request.ingest_manifest_path, "generated/unreal")
        if not _is_unreal_identifier(request.map_name):
            raise UnrealMCPSafetyError(f"Invalid Unreal map_name: {request.map_name}")

        assembly_script_path = request.assembly_script_path or _default_level_script_path(
            request.project_file
        )
        level_manifest_path = request.level_manifest_path or _default_level_manifest_path(
            request.project_file
        )
        self._assert_relative_under(assembly_script_path, "generated/unreal")
        self._assert_relative_under(level_manifest_path, "generated/unreal")

        ingest_manifest = UnrealAssetIngestManifest.model_validate(
            self._load_manifest_data(request.ingest_manifest_path)
        )
        manifest = self._level_assembly_manifest(
            request=request,
            ingest_manifest=ingest_manifest,
            assembly_script_path=assembly_script_path,
        )
        issues, warnings = self._validate_level_manifest(
            manifest,
            UnrealMCPValidateLevelAssemblyRequest(
                level_manifest_path=level_manifest_path,
                require_imported_assets=False,
            ),
        )
        if issues:
            raise UnrealMCPSafetyError(
                "Level assembly manifest is invalid: " + "; ".join(issues)
            )

        written_files: list[str] = []
        if request.write_files:
            written_files = self._write_level_assembly(manifest, level_manifest_path)
        return UnrealMCPResult(
            status="written" if request.write_files else "planned",
            manifest=manifest,
            written_files=written_files,
            risks=[*manifest.risks, *warnings],
        )

    def validate_level_assembly(
        self, request: UnrealMCPValidateLevelAssemblyRequest
    ) -> UnrealMCPResult:
        self._assert_relative_under(request.level_manifest_path, "generated/unreal")
        manifest = UnrealLevelAssemblyManifest.model_validate(
            self._load_manifest_data(request.level_manifest_path)
        )
        issues, warnings = self._validate_level_manifest(manifest, request)
        report = UnrealLevelAssemblyValidationReport(
            level_manifest_path=request.level_manifest_path,
            project_file=manifest.project_file,
            map_path=manifest.map_path,
            placement_count=len(manifest.placements),
            issues=issues,
            warnings=warnings,
        )
        return UnrealMCPResult(
            status="executed" if not issues else "failed",
            manifest=manifest,
            validation_report=report,
            risks=warnings
            if not issues
            else [*warnings, "Unreal level assembly manifest has validation issues."],
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
            *UNREAL_DDC_ARGS,
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
        env = self._unreal_env(project_file)
        project_log_path = self._project_log_path(project_file)
        project_log_offset = project_log_path.stat().st_size if project_log_path.exists() else 0
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

    def run_level_assembly(
        self, request: UnrealMCPRunLevelAssemblyRequest
    ) -> UnrealMCPResult:
        project_file = self._assert_unreal_project_file(request.project_file)
        self._assert_relative_under(request.assembly_script_path, "generated/unreal")
        assembly_script_path = self._resolve_workspace_path(request.assembly_script_path)
        if assembly_script_path.suffix.lower() != ".py":
            raise UnrealMCPSafetyError("Unreal level assembly requires a generated Python script.")
        if not assembly_script_path.exists():
            raise UnrealMCPSafetyError(
                f"Unreal level assembly script does not exist: {request.assembly_script_path}"
            )

        command = [
            request.unreal_editor_cmd,
            project_file.as_posix(),
            f"-ExecutePythonScript={assembly_script_path.as_posix()}",
            "-unattended",
            "-nop4",
            *UNREAL_DDC_ARGS,
            f"-ShaderWorkingDir={self._shader_working_dir(project_file).as_posix()}",
            "-log",
        ]
        risks = [
            "Unreal level assembly writes or updates a generated .umap under Content/Maps.",
            "Greybox assembly validates route readability, not final Blueprint movement logic.",
        ]
        if not request.confirmed_side_effects:
            return UnrealMCPResult(
                status="blocked",
                command=command,
                risks=[*risks, "Unreal level assembly requires confirmed_side_effects=true."],
            )

        stdout_path, stderr_path = self._log_paths(project_file.stem, "level_assembly")
        self._shader_working_dir(project_file).mkdir(parents=True, exist_ok=True)
        env = self._unreal_env(project_file)
        project_log_path = self._project_log_path(project_file)
        project_log_offset = project_log_path.stat().st_size if project_log_path.exists() else 0
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
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr) or (
                f"Unreal level assembly timed out after {request.timeout_seconds}s."
            )
            self._write_text(stdout_path, stdout)
            self._write_text(stderr_path, stderr)
            return UnrealMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
                risks=[*risks, "Unreal level assembly timed out."],
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
                    "Unreal Python level assembly logged errors."
                    if python_failed
                    else "Unreal level assembly returned a non-zero code."
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
            *UNREAL_DDC_ARGS,
            f"-ShaderWorkingDir={self._shader_working_dir(project_file).as_posix()}",
            "-log",
        ]
        risks = [
            "Unreal editor data validation can load project plugins and asset metadata.",
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
        env = self._unreal_env(project_file)
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

    def _validate_ingest_manifest(
        self,
        manifest: UnrealAssetIngestManifest,
        request: UnrealMCPValidateAssetIngestRequest,
    ) -> tuple[list[str], list[str]]:
        issues: list[str] = []
        warnings: list[str] = []
        try:
            self._assert_unreal_project_file(manifest.project_file)
        except UnrealMCPSafetyError as exc:
            issues.append(str(exc))
        try:
            self._assert_relative_under(manifest.import_script_path, "generated/unreal")
        except UnrealMCPSafetyError as exc:
            issues.append(str(exc))

        seen_packages: set[str] = set()
        for job in manifest.jobs:
            if not _is_unreal_identifier(job.asset_name):
                issues.append(f"invalid Unreal asset_name: {job.asset_name}")
            if not _is_unreal_game_path(job.destination_path):
                issues.append(f"invalid Unreal destination_path: {job.destination_path}")

            package_key = f"{job.destination_path.rstrip('/')}/{job.asset_name}".lower()
            if package_key in seen_packages:
                issues.append(f"duplicate Unreal destination asset: {package_key}")
            seen_packages.add(package_key)

            expected_source_root = (
                "generated/assets" if job.source == "blender" else "generated/comfyui"
            )
            try:
                self._assert_relative_under(job.source_file, expected_source_root)
            except UnrealMCPSafetyError as exc:
                issues.append(str(exc))

            if request.require_existing_sources and not self._resolve_workspace_path(
                job.source_file
            ).exists():
                issues.append(f"missing source file: {job.source_file}")

            if job.asset_type == "static_mesh":
                if not job.source_file.lower().endswith((".fbx", ".glb")):
                    issues.append(f"static mesh source must be .fbx or .glb: {job.source_file}")
                collision_object = str(job.import_settings.get("collision_object") or "")
                if not collision_object:
                    warnings.append(f"missing UCX collision_object for {job.asset_name}")
                elif not _is_unreal_identifier(collision_object):
                    issues.append(f"invalid Unreal collision_object: {collision_object}")
                elif not collision_object.startswith(f"UCX_{job.asset_name}_"):
                    issues.append(
                        "collision_object must match Unreal UCX naming for "
                        f"{job.asset_name}: {collision_object}"
                    )

            if job.asset_type == "texture_reference":
                if not job.source_file.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    issues.append(
                        f"texture reference source must be an image: {job.source_file}"
                    )
                if job.source == "comfyui" and not job.review_required:
                    warnings.append(f"ComfyUI reference should require review: {job.asset_name}")

        return issues, warnings

    def _level_assembly_manifest(
        self,
        *,
        request: UnrealMCPPrepareLevelAssemblyRequest,
        ingest_manifest: UnrealAssetIngestManifest,
        assembly_script_path: str,
    ) -> UnrealLevelAssemblyManifest:
        static_jobs = [
            job for job in ingest_manifest.jobs if job.asset_type == "static_mesh"
        ]
        jobs_by_name = {job.asset_name: job for job in static_jobs}

        def pick(*preferred_names: str, contains: tuple[str, ...] = ()) -> str | None:
            for name in preferred_names:
                if name in jobs_by_name:
                    return name
            for name in jobs_by_name:
                if all(term in name for term in contains):
                    return name
            return None

        floor = pick("modular_rooftop_floor_kit", contains=("floor",))
        ramp = pick("traversal_ramp", contains=("ramp",))
        vault = pick("low_vault_blocker_set", contains=("vault",))
        wall = pick("wall_run_panel_set", contains=("wall",))
        slide = pick("slide_barrier_set", contains=("slide",))
        boost = pick("boost_pad_marker", contains=("boost",))
        checkpoint = pick("checkpoint_gate", contains=("checkpoint",))
        hazard = pick("fall_hazard_marker_set", contains=("hazard",))
        objective = pick("objective_prop", contains=("objective",))
        exit_gate = pick("extraction_gate", "exit_gate", contains=("exit",))
        ui_proxy = pick("route_timer_ui_proxy", "ui_proxy_mesh", contains=("ui",))
        fallback_floor = floor or (static_jobs[0].asset_name if static_jobs else None)

        placements: list[UnrealLevelPlacement] = []

        def asset_path(asset_name: str) -> str:
            job = jobs_by_name[asset_name]
            return f"{job.destination_path.rstrip('/')}/{job.asset_name}"

        def add(
            *,
            actor_name: str,
            asset_name: str | None,
            gameplay_role: str,
            location_cm: tuple[float, float, float],
            beat: str,
            rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
            scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
            notes: str = "",
        ) -> None:
            if asset_name is None:
                return
            placements.append(
                UnrealLevelPlacement(
                    actor_name=actor_name,
                    asset_name=asset_name,
                    asset_path=asset_path(asset_name),
                    gameplay_role=gameplay_role,  # type: ignore[arg-type]
                    location_cm=location_cm,
                    rotation_deg=rotation_deg,
                    scale=scale,
                    beat=beat,
                    notes=notes,
                )
            )

        for index, x in enumerate((0.0, 650.0, 1300.0, 1950.0, 2600.0, 3250.0), start=1):
            add(
                actor_name=f"FA_RouteFloor_{index:02d}",
                asset_name=fallback_floor,
                gameplay_role="route_floor",
                location_cm=(x, 0.0, 0.0),
                beat="primary route",
                scale=(1.0, 1.0, 0.35),
                notes="Continuous rooftop runway for greybox movement tuning.",
            )
        add(
            actor_name="FA_Ramp_Teach",
            asset_name=ramp,
            gameplay_role="traversal",
            location_cm=(520.0, -110.0, 70.0),
            beat="first minute",
            rotation_deg=(0.0, 0.0, 0.0),
            notes="Teaches vertical route reading before pressure is added.",
        )
        add(
            actor_name="FA_Vault_Blocker",
            asset_name=vault,
            gameplay_role="obstacle",
            location_cm=(1080.0, 0.0, 110.0),
            beat="first minute",
            notes="Forces an early vault decision on the main route.",
        )
        add(
            actor_name="FA_WallRun_Panel",
            asset_name=wall,
            gameplay_role="traversal",
            location_cm=(1620.0, -260.0, 230.0),
            rotation_deg=(0.0, 0.0, 90.0),
            beat="midpoint combination",
            notes="Makes the midpoint combine speed with side-wall commitment.",
        )
        add(
            actor_name="FA_Slide_Barrier",
            asset_name=slide,
            gameplay_role="obstacle",
            location_cm=(2060.0, 0.0, 90.0),
            beat="midpoint combination",
            notes="Creates a low-profile timing gate after the wall-run section.",
        )
        add(
            actor_name="FA_Boost_Pad",
            asset_name=boost,
            gameplay_role="traversal",
            location_cm=(2360.0, 0.0, 40.0),
            beat="midpoint combination",
            notes="Marks the acceleration moment into the final run.",
        )
        add(
            actor_name="FA_Checkpoint_Gate",
            asset_name=checkpoint,
            gameplay_role="checkpoint",
            location_cm=(2620.0, 0.0, 120.0),
            beat="checkpoint recovery",
            notes="Visible recovery point before the final hazard read.",
        )
        add(
            actor_name="FA_Fall_Hazard_Left",
            asset_name=hazard,
            gameplay_role="hazard",
            location_cm=(2960.0, -260.0, 35.0),
            beat="final run",
            notes="Failure read on the left edge of the final route.",
        )
        add(
            actor_name="FA_Fall_Hazard_Right",
            asset_name=hazard,
            gameplay_role="hazard",
            location_cm=(2960.0, 260.0, 35.0),
            beat="final run",
            notes="Failure read on the right edge of the final route.",
        )
        add(
            actor_name="FA_Objective_Prop",
            asset_name=objective,
            gameplay_role="objective",
            location_cm=(3180.0, 0.0, 120.0),
            beat="final run",
            notes="Readable pickup/target before extraction.",
        )
        add(
            actor_name="FA_Exit_Gate",
            asset_name=exit_gate,
            gameplay_role="exit",
            location_cm=(3680.0, 0.0, 130.0),
            beat="final run",
            notes="Final win-state affordance.",
        )
        add(
            actor_name="FA_Route_Timer_UI",
            asset_name=ui_proxy,
            gameplay_role="ui",
            location_cm=(-250.0, -260.0, 170.0),
            rotation_deg=(0.0, 0.0, 12.0),
            beat="first minute",
            notes="World-space objective and timer proxy near player start.",
        )

        risks = [
            "Generated map assembly is a greybox route for playability tuning, not final art.",
            "Movement abilities still require Blueprint or C++ implementation before full playtest.",
        ]
        if not floor:
            risks.append("No dedicated floor asset was found; the first static mesh is reused.")
        if not objective or not exit_gate:
            risks.append("Objective or exit asset was not found; route completion may be incomplete.")

        map_path = f"/Game/Maps/{request.map_name}"
        playtest_report_path = (
            Path(request.project_file.replace("\\", "/")).parent
            / "fantasy-agent-playtest-smoke.json"
        ).as_posix()
        return UnrealLevelAssemblyManifest(
            project_file=request.project_file,
            map_name=request.map_name,
            map_path=map_path,
            assembly_script_path=assembly_script_path,
            playtest_report_path=playtest_report_path,
            source_ingest_manifest=request.ingest_manifest_path,
            player_start=UnrealPlayerStartPlacement(),
            placements=placements,
            playtest_checks=[
                "Map loads directly from /Game/Maps/M_Prototype_Greybox.",
                "Player starts facing the route and can see the first traversal affordance.",
                "Route contains traversal, obstacle, checkpoint, hazard, objective, and exit beats.",
                "Objective and exit are placed after the midpoint system-combination beat.",
                "DataValidation returns zero errors before visual expansion.",
            ],
            risks=risks,
        )

    def _validate_level_manifest(
        self,
        manifest: UnrealLevelAssemblyManifest,
        request: UnrealMCPValidateLevelAssemblyRequest,
    ) -> tuple[list[str], list[str]]:
        issues: list[str] = []
        warnings: list[str] = []
        try:
            project_file = self._assert_unreal_project_file(manifest.project_file)
        except UnrealMCPSafetyError as exc:
            issues.append(str(exc))
            project_file = self.workspace_root / manifest.project_file
        try:
            self._assert_relative_under(manifest.assembly_script_path, "generated/unreal")
        except UnrealMCPSafetyError as exc:
            issues.append(str(exc))
        try:
            self._assert_relative_under(manifest.playtest_report_path, "generated/unreal")
        except UnrealMCPSafetyError as exc:
            issues.append(str(exc))
        try:
            self._assert_relative_under(manifest.source_ingest_manifest, "generated/unreal")
        except UnrealMCPSafetyError as exc:
            issues.append(str(exc))

        if not _is_unreal_identifier(manifest.map_name):
            issues.append(f"invalid Unreal map_name: {manifest.map_name}")
        if not manifest.map_path.startswith("/Game/Maps/"):
            issues.append(f"map_path must stay under /Game/Maps: {manifest.map_path}")
        elif not _is_unreal_game_path(manifest.map_path):
            issues.append(f"invalid Unreal map_path: {manifest.map_path}")
        if not _is_unreal_identifier(manifest.player_start.actor_name):
            issues.append(f"invalid player_start actor_name: {manifest.player_start.actor_name}")

        seen_actor_names: set[str] = set()
        role_counts: dict[str, int] = {}
        for placement in manifest.placements:
            if not _is_unreal_identifier(placement.actor_name):
                issues.append(f"invalid actor_name: {placement.actor_name}")
            if placement.actor_name in seen_actor_names:
                issues.append(f"duplicate actor_name: {placement.actor_name}")
            seen_actor_names.add(placement.actor_name)
            if not _is_unreal_identifier(placement.asset_name):
                issues.append(f"invalid asset_name: {placement.asset_name}")
            if not _is_unreal_game_path(placement.asset_path):
                issues.append(f"invalid asset_path: {placement.asset_path}")
            role_counts[placement.gameplay_role] = role_counts.get(placement.gameplay_role, 0) + 1
            if request.require_imported_assets:
                asset_file = _game_asset_file(project_file, placement.asset_path)
                if not asset_file.exists():
                    issues.append(f"missing imported asset: {placement.asset_path}")

        if request.require_playtest_route:
            required_roles = {
                "route_floor": "at least one route floor",
                "objective": "a readable objective",
                "exit": "a readable exit gate",
            }
            for role, label in required_roles.items():
                if role_counts.get(role, 0) == 0:
                    issues.append(f"level assembly requires {label}")
            if role_counts.get("traversal", 0) < 2:
                warnings.append("route should include at least two traversal beats")
            if role_counts.get("obstacle", 0) == 0:
                warnings.append("route should include at least one obstacle beat")
            if role_counts.get("hazard", 0) == 0:
                warnings.append("route should include at least one failure-read hazard")
            if role_counts.get("checkpoint", 0) == 0:
                warnings.append("route should include at least one checkpoint")

        return issues, warnings

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

    def _write_level_assembly(
        self,
        manifest: UnrealLevelAssemblyManifest,
        level_manifest_path: str,
    ) -> list[str]:
        manifest_path = self._resolve_workspace_path(level_manifest_path)
        script_path = self._resolve_workspace_path(manifest.assembly_script_path)
        self._write_text(manifest_path, json.dumps(manifest.model_dump(mode="json"), indent=2))
        self._write_text(script_path, _level_assembly_script(manifest))
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
            config_files=[
                (project_root / "Config" / "DefaultGame.ini").as_posix(),
                (project_root / "Config" / "DefaultEngine.ini").as_posix(),
            ],
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
        game_config_path = self._resolve_workspace_path(artifact.config_files[0])
        engine_config_path = self._resolve_workspace_path(artifact.config_files[1])

        self._write_text(project_file, json.dumps(_uproject_descriptor(plan), indent=2))
        self._write_text(manifest_path, json.dumps(manifest.model_dump(mode="json"), indent=2))
        self._write_text(setup_script_path, _setup_script(manifest))
        self._write_text(game_config_path, _default_game_ini(plan))
        self._write_text(engine_config_path, _default_engine_ini(plan))
        return [
            self._display_path(project_file),
            self._display_path(manifest_path),
            self._display_path(setup_script_path),
            self._display_path(game_config_path),
            self._display_path(engine_config_path),
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

    def _unreal_env(self, project_file: Path) -> dict[str, str]:
        env = dict(os.environ)
        local_ddc = project_file.parent / "DerivedDataCache"
        local_ddc.mkdir(parents=True, exist_ok=True)
        env["UE-LocalDataCachePath"] = local_ddc.as_posix()
        env["UE-SharedDataCachePath"] = "None"
        env["UE-CloudDataCacheHost"] = "None"
        return env

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
        elif name == "validate_asset_ingest":
            request = UnrealMCPValidateAssetIngestRequest.model_validate(arguments or {})
            result = bridge.validate_asset_ingest(request)
        elif name == "prepare_level_assembly":
            request = UnrealMCPPrepareLevelAssemblyRequest.model_validate(arguments or {})
            result = bridge.prepare_level_assembly(request)
        elif name == "validate_level_assembly":
            request = UnrealMCPValidateLevelAssemblyRequest.model_validate(arguments or {})
            result = bridge.validate_level_assembly(request)
        elif name == "run_asset_ingest":
            request = UnrealMCPRunAssetIngestRequest.model_validate(arguments or {})
            result = bridge.run_asset_ingest(request)
        elif name == "run_level_assembly":
            request = UnrealMCPRunLevelAssemblyRequest.model_validate(arguments or {})
            result = bridge.run_level_assembly(request)
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
        if result.validation_report is not None:
            if isinstance(result.validation_report, UnrealLevelAssemblyValidationReport):
                return "Unreal MCP found level assembly validation issues."
            return "Unreal MCP found asset ingest validation issues."
        return "Unreal MCP failed. Check returned logs and stderr_tail."
    if result.status == "executed":
        if result.validation_report is not None:
            if isinstance(result.validation_report, UnrealLevelAssemblyValidationReport):
                return "Unreal MCP validated the level assembly manifest."
            return "Unreal MCP validated the asset ingest manifest."
        script_args = [item for item in result.command if item.startswith("-ExecutePythonScript=")]
        if script_args and "level_assembly" in script_args[0].lower():
            return "Unreal MCP assembled the greybox level and captured logs."
        if script_args:
            return "Unreal MCP executed asset ingest and captured logs."
        if any(item == "-run=DataValidation" for item in result.command):
            return "Unreal MCP executed Unreal editor data validation and captured logs."
        return "Unreal MCP executed Unreal Editor automation and captured logs."
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


def _default_engine_ini(plan: UnrealProjectPlan) -> str:
    first_map = plan.maps[0] if plan.maps else "M_Prototype_Greybox"
    map_path = f"/Game/Maps/{Path(first_map).stem}"
    return "\n".join(
        [
            "[/Script/EngineSettings.GameMapsSettings]",
            f"EditorStartupMap={map_path}",
            f"GameDefaultMap={map_path}",
            "",
            "[Animation.DefaultObjectSettings]",
            'BoneCompressionSettings="/ACLPlugin/ACLAnimBoneCompressionSettings"',
            'BoneCompressionSettingsFallback="/ACLPlugin/ACLAnimBoneCompressionSettings"',
            'AnimationRecorderBoneCompressionSettings="/ACLPlugin/ACLAnimBoneCompressionSettings"',
            'AnimationRecorderBoneCompressionSettingsFallback="/ACLPlugin/ACLAnimBoneCompressionSettings"',
            'CurveCompressionSettings="/ACLPlugin/ACLAnimCurveCompressionSettings"',
            'CurveCompressionSettingsFallback="/ACLPlugin/ACLAnimCurveCompressionSettings"',
            'VariableFrameStrippingSettings="/ACLPlugin/ACLAnimBoneCompressionSettings"',
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
    filename = source_path(job)
    if not Path(filename).exists():
        raise RuntimeError("Missing source file for Unreal import: {{}}".format(filename))
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = job["destination_path"]
    task.destination_name = job["asset_name"]
    task.automated = True
    task.save = True
    task.replace_existing = True
    if job["asset_type"] == "static_mesh" and task.filename.lower().endswith(".fbx"):
        task.options = mesh_options(job)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported_paths = list(getattr(task, "imported_object_paths", []) or [])
    if imported_paths:
        unreal.log(
            "Fantasy Agent imported {{}} -> {{}}".format(
                task.filename, ", ".join(imported_paths)
            )
        )
    else:
        unreal.log_warning(
            "Fantasy Agent import produced no reported object paths: {{}}".format(task.filename)
        )


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


def _level_assembly_script(manifest: UnrealLevelAssemblyManifest) -> str:
    payload = json.dumps(manifest.model_dump(mode="json"), indent=2)
    script = '''"""Fantasy Agent Unreal level assembly script.

Run inside Unreal Editor Python through Unreal MCP after side effects are confirmed.
"""

from __future__ import annotations

import json
from pathlib import Path

import unreal


MANIFEST = json.loads(__PAYLOAD__)
ASSET_LIBRARY = unreal.EditorAssetLibrary


def repo_root():
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if (parent / "fantasy_agent").exists():
            return parent
    return script_path.parents[3]


def vector(values):
    return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))


def rotator(values):
    return unreal.Rotator(float(values[0]), float(values[1]), float(values[2]))


def level_subsystem():
    cls = getattr(unreal, "LevelEditorSubsystem", None)
    if cls is None:
        return None
    return unreal.get_editor_subsystem(cls)


def new_level(map_path):
    subsystem = level_subsystem()
    if subsystem and hasattr(subsystem, "new_level"):
        subsystem.new_level(map_path)
        return
    unreal.EditorLevelLibrary.new_level(map_path)


def load_level(map_path):
    subsystem = level_subsystem()
    if subsystem and hasattr(subsystem, "load_level"):
        subsystem.load_level(map_path)
        return
    unreal.EditorLevelLibrary.load_level(map_path)


def open_or_create_level():
    map_path = MANIFEST["map_path"]
    if ASSET_LIBRARY.does_asset_exist(map_path):
        load_level(map_path)
        unreal.log("Fantasy Agent loaded existing map: " + map_path)
    else:
        new_level(map_path)
        unreal.log("Fantasy Agent created map: " + map_path)


def actor_label(actor):
    if hasattr(actor, "get_actor_label"):
        return actor.get_actor_label()
    return actor.get_name()


def clear_previous_assembly():
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        if actor_label(actor).startswith("FA_"):
            unreal.EditorLevelLibrary.destroy_actor(actor)


def set_label(actor, label):
    if hasattr(actor, "set_actor_label"):
        actor.set_actor_label(label)


def set_tags(actor, *tags):
    try:
        actor.tags = [unreal.Name(tag.replace(" ", "_")) for tag in tags if tag]
    except Exception as exc:
        unreal.log_warning("Could not set tags on {}: {}".format(actor_label(actor), exc))


def load_mesh(asset_path, asset_name):
    candidates = [asset_path, "{}.{}".format(asset_path, asset_name)]
    for candidate in candidates:
        mesh = ASSET_LIBRARY.load_asset(candidate)
        if mesh:
            return mesh
    raise RuntimeError("Missing static mesh asset for level assembly: " + asset_path)


def static_mesh_component(actor):
    if hasattr(actor, "static_mesh_component"):
        return actor.static_mesh_component
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    if components:
        return components[0]
    return None


def spawn_mesh(placement):
    mesh = load_mesh(placement["asset_path"], placement["asset_name"])
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        vector(placement["location_cm"]),
        rotator(placement["rotation_deg"]),
    )
    set_label(actor, placement["actor_name"])
    component = static_mesh_component(actor)
    if component is None:
        raise RuntimeError("StaticMeshActor has no StaticMeshComponent: " + placement["actor_name"])
    component.set_static_mesh(mesh)
    actor.set_actor_scale3d(vector(placement["scale"]))
    set_tags(actor, "FantasyAgent", placement["gameplay_role"], placement["beat"])
    unreal.log(
        "Fantasy Agent placed {} from {}".format(
            placement["actor_name"], placement["asset_path"]
        )
    )


def spawn_player_start():
    start = MANIFEST["player_start"]
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart,
        vector(start["location_cm"]),
        rotator(start["rotation_deg"]),
    )
    set_label(actor, start["actor_name"])
    set_tags(actor, "FantasyAgent", "player_start")


def spawn_lighting():
    light_specs = [
        ("DirectionalLight", "FA_KeyLight", (-600.0, -900.0, 900.0), (-45.0, -35.0, 0.0)),
        ("SkyLight", "FA_SkyLight", (0.0, 0.0, 600.0), (0.0, 0.0, 0.0)),
    ]
    for class_name, label, location, rotation in light_specs:
        actor_class = getattr(unreal, class_name, None)
        if actor_class is None:
            continue
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class,
            vector(location),
            rotator(rotation),
        )
        set_label(actor, label)
        set_tags(actor, "FantasyAgent", "lighting")


def save_current_level():
    if hasattr(unreal.EditorLevelLibrary, "save_current_level"):
        unreal.EditorLevelLibrary.save_current_level()
        return
    utils = getattr(unreal, "EditorLoadingAndSavingUtils", None)
    if utils and hasattr(utils, "save_dirty_packages"):
        utils.save_dirty_packages(True, True)
        return
    ASSET_LIBRARY.save_directory("/Game/Maps", only_if_is_dirty=False, recursive=True)


def write_playtest_smoke_report():
    actors = list(unreal.EditorLevelLibrary.get_all_level_actors())
    labels = [actor_label(actor) for actor in actors]
    fa_labels = [label for label in labels if label.startswith("FA_")]
    required_labels = {
        "FA_PlayerStart",
        "FA_Checkpoint_Gate",
        "FA_Objective_Prop",
        "FA_Exit_Gate",
    }
    missing = sorted(required_labels.difference(fa_labels))
    route_floors = sorted(label for label in fa_labels if label.startswith("FA_RouteFloor_"))
    hazards = sorted(label for label in fa_labels if label.startswith("FA_Fall_Hazard_"))
    traversal_labels = sorted(
        label
        for label in fa_labels
        if label
        in {
            "FA_Ramp_Teach",
            "FA_WallRun_Panel",
            "FA_Boost_Pad",
        }
    )
    issues = []
    if missing:
        issues.append("missing required actors: " + ", ".join(missing))
    if len(route_floors) < 6:
        issues.append("expected at least 6 route floor segments")
    if len(hazards) < 2:
        issues.append("expected at least 2 hazard markers")
    if len(traversal_labels) < 3:
        issues.append("expected ramp, wall-run, and boost traversal markers")
    report = {
        "map_path": MANIFEST["map_path"],
        "fa_actor_count": len(fa_labels),
        "route_floor_count": len(route_floors),
        "hazard_count": len(hazards),
        "traversal_marker_count": len(traversal_labels),
        "required_labels": sorted(required_labels),
        "missing_required_labels": missing,
        "issues": issues,
    }
    output_path = repo_root() / MANIFEST["playtest_report_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if issues:
        raise RuntimeError("Fantasy Agent playtest smoke failed: " + "; ".join(issues))
    unreal.log("Fantasy Agent playtest smoke passed: {}".format(json.dumps(report)))


open_or_create_level()
clear_previous_assembly()
spawn_player_start()
spawn_lighting()
for level_placement in MANIFEST["placements"]:
    spawn_mesh(level_placement)
save_current_level()
write_playtest_smoke_report()
unreal.log(
    "Fantasy Agent level assembly complete: {} placements into {}".format(
        len(MANIFEST["placements"]), MANIFEST["map_path"]
    )
)
'''
    return script.replace("__PAYLOAD__", repr(payload))


def _default_ingest_script_path(project_file: str) -> str:
    project_root = Path(project_file.replace("\\", "/")).parent
    return (project_root / "Scripts" / "fantasy_agent_asset_ingest.py").as_posix()


def _default_ingest_manifest_path(project_file: str) -> str:
    project_root = Path(project_file.replace("\\", "/")).parent
    return (project_root / "fantasy-agent-asset-ingest.json").as_posix()


def _default_level_script_path(project_file: str) -> str:
    project_root = Path(project_file.replace("\\", "/")).parent
    return (project_root / "Scripts" / "fantasy_agent_level_assembly.py").as_posix()


def _default_level_manifest_path(project_file: str) -> str:
    project_root = Path(project_file.replace("\\", "/")).parent
    return (project_root / "fantasy-agent-level-assembly.json").as_posix()


def _assert_game_path(path: str) -> None:
    if not path.startswith("/Game/"):
        raise UnrealMCPSafetyError(f"Unreal destination path must start with /Game/: {path}")


def _is_unreal_identifier(value: str) -> bool:
    if not value or not (value[0].isalpha() or value[0] == "_"):
        return False
    return all(ch.isalnum() or ch == "_" for ch in value)


def _is_unreal_game_path(path: str) -> bool:
    if not path.startswith("/Game/"):
        return False
    package_path = path.split(".", maxsplit=1)[0]
    parts = [part for part in package_path.removeprefix("/Game/").split("/") if part]
    return bool(parts) and all(_is_unreal_identifier(part) for part in parts)


def _game_asset_file(project_file: Path, asset_path: str) -> Path:
    package_path = asset_path.split(".", maxsplit=1)[0]
    relative_asset = package_path.removeprefix("/Game/").strip("/")
    return project_file.parent / "Content" / f"{relative_asset}.uasset"


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
