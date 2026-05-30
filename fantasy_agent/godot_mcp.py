from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fantasy_agent.contracts import (
    GodotMCPCreateProjectRequest,
    GodotMCPResult,
    GodotMCPRunImportRequest,
    GodotMCPValidateProjectRequest,
    GodotProjectArtifact,
    GodotProjectPlan,
    GodotProjectValidationReport,
)

SERVER_NAME = "fantasy-agent-godot-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": "create_godot_project_structure",
            "title": "Create Godot project structure",
            "description": (
                "Use this when Fantasy Agent needs a Godot 4 project.godot, main scene, "
                "prototype scripts, asset folders, and a handoff manifest from a GodotProjectPlan. "
                "Defaults to in-memory output; set write_files only after file side effects are approved."
            ),
            "inputSchema": GodotMCPCreateProjectRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "validate_godot_project",
            "title": "Validate Godot project",
            "description": (
                "Use this before Godot execution to verify generated project.godot, main scene, "
                "prototype scripts, and generated/godot path safety without launching Godot."
            ),
            "inputSchema": GodotMCPValidateProjectRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "run_godot_import",
            "title": "Run Godot headless import",
            "description": (
                "Use this after explicit confirmation to launch Godot in headless import mode "
                "against a generated Fantasy Agent Godot project and capture logs."
            ),
            "inputSchema": GodotMCPRunImportRequest.model_json_schema(),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
    ]


class GodotMCPSafetyError(ValueError):
    pass


class GodotMCPBridge:
    def __init__(
        self,
        workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.runner = runner or subprocess.run

    def create_godot_project_structure(
        self,
        request: GodotMCPCreateProjectRequest,
    ) -> GodotMCPResult:
        project_dir = request.project_dir or f"generated/godot/{_slug(request.plan.project_name)}"
        artifact = self._artifact(request.plan, project_dir)
        risks = self._validate_artifact(artifact, request.plan)
        created_paths = [artifact.project_dir, *artifact.asset_dirs]
        written_files: list[str] = []
        if request.write_files:
            written_files = self._write_project_artifact(artifact, request.plan)
        return GodotMCPResult(
            status="written" if request.write_files else "planned",
            artifact=artifact,
            created_paths=created_paths,
            written_files=written_files,
            risks=risks,
        )

    def validate_godot_project(
        self,
        request: GodotMCPValidateProjectRequest,
    ) -> GodotMCPResult:
        project_file = self._assert_godot_project_file(request.project_file, require_exists=False)
        issues: list[str] = []
        warnings: list[str] = []
        main_scene_path = ""
        script_count = 0

        if not project_file.exists():
            issues.append(f"Godot project file does not exist: {request.project_file}")
        else:
            project_text = project_file.read_text(encoding="utf-8")
            main_scene = _main_scene_from_project(project_text)
            if not main_scene:
                issues.append("project.godot is missing application/run/main_scene.")
            else:
                main_scene_path = (project_file.parent / main_scene.removeprefix("res://")).as_posix()
                main_scene_file = project_file.parent / main_scene.removeprefix("res://")
                if request.require_main_scene and not main_scene_file.exists():
                    issues.append(f"Main scene does not exist: {main_scene}")
            script_dir = project_file.parent / "scripts"
            scripts = sorted(script_dir.glob("*.gd")) if script_dir.exists() else []
            script_count = len(scripts)
            if request.require_scripts and script_count == 0:
                issues.append("No generated Godot scripts found under scripts/.")
            if "renderer/rendering_method=" not in project_text:
                warnings.append("No renderer/rendering_method configured; Godot will use editor defaults.")

        report = GodotProjectValidationReport(
            project_file=request.project_file,
            main_scene_path=_display_rel(self.workspace_root, Path(main_scene_path))
            if main_scene_path
            else "",
            script_count=script_count,
            issues=issues,
            warnings=warnings,
        )
        return GodotMCPResult(
            status="executed" if not issues else "failed",
            validation_report=report,
            risks=warnings
            if not issues
            else [*warnings, "Generated Godot project has validation issues."],
        )

    def run_godot_import(self, request: GodotMCPRunImportRequest) -> GodotMCPResult:
        project_file = self._assert_godot_project_file(request.project_file)
        command = [
            request.godot_executable,
            "--headless",
            "--path",
            project_file.parent.as_posix(),
            "--import",
        ]
        risks = [
            "Godot import writes .godot metadata and imported asset cache inside the generated project.",
            "Godot is a rapid prototype target here; Unreal remains the primary production integration path.",
        ]
        if not request.confirmed_side_effects:
            return GodotMCPResult(
                status="blocked",
                command=command,
                risks=[*risks, "Godot import requires confirmed_side_effects=true."],
            )

        stdout_path, stderr_path = self._log_paths(project_file.parent.name, "import")
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
            stderr = f"Godot executable not found: {request.godot_executable}"
            self._write_text(stderr_path, stderr)
            return GodotMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stderr_path)],
                stderr_tail=stderr,
                risks=[*risks, str(exc)],
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr) or f"Godot import timed out after {request.timeout_seconds}s."
            self._write_text(stdout_path, stdout)
            self._write_text(stderr_path, stderr)
            return GodotMCPResult(
                status="failed",
                command=command,
                log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
                risks=[*risks, "Godot import timed out."],
            )

        self._write_text(stdout_path, _to_text(process.stdout))
        self._write_text(stderr_path, _to_text(process.stderr))
        return GodotMCPResult(
            status="executed" if process.returncode == 0 else "failed",
            command=command,
            log_paths=[self._display_path(stdout_path), self._display_path(stderr_path)],
            return_code=process.returncode,
            stdout_tail=_tail(process.stdout),
            stderr_tail=_tail(process.stderr),
            risks=risks if process.returncode == 0 else [*risks, "Godot import returned a non-zero code."],
        )

    def _artifact(self, plan: GodotProjectPlan, project_dir: str) -> GodotProjectArtifact:
        base = Path(project_dir.replace("\\", "/"))
        scenes = [_join_project_path(base, scene) for scene in plan.scenes]
        scripts = [_join_project_path(base, script) for script in plan.scripts]
        asset_dirs = [
            _join_project_path(base, folder)
            for folder in plan.folders
            if folder.startswith("assets") or folder.startswith("references")
        ]
        main_scene = scenes[0] if scenes else (base / "scenes" / "main.tscn").as_posix()
        return GodotProjectArtifact(
            project_name=plan.project_name,
            project_dir=base.as_posix(),
            project_file=(base / "project.godot").as_posix(),
            main_scene_path=main_scene,
            manifest_path=(base / "fantasy-agent-godot-manifest.json").as_posix(),
            scene_paths=scenes,
            script_paths=scripts,
            asset_dirs=asset_dirs,
            side_effects=[
                "writes generated Godot project.godot and scene files",
                "writes generated GDScript prototype scripts",
                "creates generated Godot asset/reference folders",
            ],
        )

    def _validate_artifact(
        self,
        artifact: GodotProjectArtifact,
        plan: GodotProjectPlan,
    ) -> list[str]:
        if not plan.scenes:
            raise GodotMCPSafetyError("GodotProjectPlan.scenes must contain at least one scene.")
        if not plan.scripts:
            raise GodotMCPSafetyError("GodotProjectPlan.scripts must contain at least one script.")
        self._assert_relative_under(artifact.project_dir, "generated/godot")
        self._assert_relative_under(artifact.project_file, "generated/godot")
        self._assert_relative_under(artifact.main_scene_path, "generated/godot")
        self._assert_relative_under(artifact.manifest_path, "generated/godot")
        for scene_path in artifact.scene_paths:
            self._assert_relative_under(scene_path, "generated/godot")
            if not scene_path.endswith(".tscn"):
                raise GodotMCPSafetyError(f"Godot scene paths must end with .tscn: {scene_path}")
        for script_path in artifact.script_paths:
            self._assert_relative_under(script_path, "generated/godot")
            if not script_path.endswith(".gd"):
                raise GodotMCPSafetyError(f"Godot script paths must end with .gd: {script_path}")
        for asset_dir in artifact.asset_dirs:
            self._assert_relative_under(asset_dir, "generated/godot")
        return [
            "Godot output is for rapid gameplay validation; do not treat it as final UE content.",
            "Reviewed Blender and ComfyUI assets should be copied into res://assets/generated only after approval.",
        ]

    def _write_project_artifact(
        self,
        artifact: GodotProjectArtifact,
        plan: GodotProjectPlan,
    ) -> list[str]:
        project_dir = self._resolve_workspace_path(artifact.project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)
        for folder in plan.folders:
            self._resolve_workspace_path(_join_project_path(Path(artifact.project_dir), folder)).mkdir(
                parents=True,
                exist_ok=True,
            )
        for asset_dir in artifact.asset_dirs:
            self._resolve_workspace_path(asset_dir).mkdir(parents=True, exist_ok=True)

        project_file = self._resolve_workspace_path(artifact.project_file)
        main_scene_path = self._resolve_workspace_path(artifact.main_scene_path)
        manifest_path = self._resolve_workspace_path(artifact.manifest_path)
        main_script = _script_path_by_name(artifact.script_paths, "main.gd")
        player_script = _script_path_by_name(artifact.script_paths, "player_controller.gd")
        if main_script is None:
            main_script = (Path(artifact.project_dir) / "scripts" / "main.gd").as_posix()
            artifact.script_paths.append(main_script)
        if player_script is None:
            player_script = (Path(artifact.project_dir) / "scripts" / "player_controller.gd").as_posix()
            artifact.script_paths.append(player_script)

        self._write_text(project_file, _project_godot(plan))
        self._write_text(main_scene_path, _main_scene())
        self._write_text(self._resolve_workspace_path(main_script), _main_gd(plan))
        self._write_text(self._resolve_workspace_path(player_script), _player_controller_gd(plan))
        self._write_text(manifest_path, json.dumps(_manifest(plan, artifact), indent=2))
        return [
            self._display_path(project_file),
            self._display_path(main_scene_path),
            self._display_path(self._resolve_workspace_path(main_script)),
            self._display_path(self._resolve_workspace_path(player_script)),
            self._display_path(manifest_path),
        ]

    def _assert_godot_project_file(
        self,
        project_file: str,
        *,
        require_exists: bool = True,
    ) -> Path:
        self._assert_relative_under(project_file, "generated/godot")
        resolved = self._resolve_workspace_path(project_file)
        if resolved.name != "project.godot":
            raise GodotMCPSafetyError("Godot project file must be named project.godot.")
        if require_exists and not resolved.exists():
            raise GodotMCPSafetyError(f"Godot project file does not exist: {project_file}")
        return resolved

    def _assert_relative_under(self, path: str, required_prefix: str) -> None:
        if Path(path).is_absolute():
            raise GodotMCPSafetyError(f"Absolute paths are not allowed: {path}")
        normalized = Path(path.replace("\\", "/"))
        if ".." in normalized.parts:
            raise GodotMCPSafetyError(f"Parent traversal is not allowed: {path}")
        prefix = Path(required_prefix)
        if normalized.parts[: len(prefix.parts)] != prefix.parts:
            raise GodotMCPSafetyError(f"Path must stay under {required_prefix}: {path}")
        self._resolve_workspace_path(path)

    def _resolve_workspace_path(self, path: str) -> Path:
        resolved = (self.workspace_root / path).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise GodotMCPSafetyError(f"Path escapes workspace: {path}") from exc
        return resolved

    def _log_paths(self, project_name: str, operation: str) -> tuple[Path, Path]:
        safe_name = _slug(project_name)
        log_dir = self.workspace_root / "generated" / "logs" / "godot"
        return log_dir / f"{safe_name}_{operation}.stdout.log", log_dir / f"{safe_name}_{operation}.stderr.log"

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        return path.relative_to(self.workspace_root).as_posix()


def call_godot_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> dict[str, Any]:
    bridge = GodotMCPBridge(workspace_root)
    try:
        if name == "create_godot_project_structure":
            request = GodotMCPCreateProjectRequest.model_validate(arguments or {})
            result = bridge.create_godot_project_structure(request)
        elif name == "validate_godot_project":
            request = GodotMCPValidateProjectRequest.model_validate(arguments or {})
            result = bridge.validate_godot_project(request)
        elif name == "run_godot_import":
            request = GodotMCPRunImportRequest.model_validate(arguments or {})
            result = bridge.run_godot_import(request)
        else:
            available = ", ".join(tool["name"] for tool in tool_descriptors())
            return _error(f"Unknown Godot MCP tool '{name}'. Available tools: {available}.")
        return {
            "structuredContent": result.model_dump(mode="json"),
            "content": [{"type": "text", "text": _content_summary(result)}],
        }
    except (ValidationError, GodotMCPSafetyError) as exc:
        return _error(str(exc))


def _content_summary(result: GodotMCPResult) -> str:
    if result.status == "blocked":
        return "Godot MCP blocked execution because side effects were not confirmed."
    if result.status == "failed":
        if result.validation_report is not None:
            return "Godot MCP found project validation issues."
        return "Godot MCP failed. Check returned logs and stderr_tail."
    if result.status == "executed":
        if result.validation_report is not None:
            return "Godot MCP validated the generated project."
        return "Godot MCP ran headless import and captured logs."
    if result.status == "written":
        return f"Godot MCP wrote {len(result.written_files)} generated handoff files."
    return "Godot MCP prepared a project structure and import handoff."


def _error(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def _project_godot(plan: GodotProjectPlan) -> str:
    return "\n".join(
        [
            "; Engine configuration file.",
            "; Fantasy Agent generated Godot prototype handoff.",
            "config_version=5",
            "",
            "[application]",
            f'config/name="{plan.project_name}"',
            'run/main_scene="res://scenes/main.tscn"',
            f'config/features=PackedStringArray("{_engine_feature(plan.engine_version)}")',
            "",
            "[rendering]",
            f'renderer/rendering_method="{_renderer_method(plan.renderer)}"',
            "",
            "[input]",
            *[_input_action_line(action) for action in plan.input_actions],
            "",
        ]
    )


def _main_scene() -> str:
    return "\n".join(
        [
            "[gd_scene load_steps=2 format=3]",
            "",
            '[ext_resource type="Script" path="res://scripts/main.gd" id="1_main"]',
            "",
            '[node name="FantasyAgentPrototype" type="Node3D"]',
            'script = ExtResource("1_main")',
            "",
        ]
    )


def _main_gd(plan: GodotProjectPlan) -> str:
    payload = json.dumps(
        {
            "project_name": plan.project_name,
            "automation_steps": plan.automation_steps,
            "input_actions": plan.input_actions,
        },
        indent=2,
    )
    return f'''extends Node3D

const HANDOFF := {payload}
const MAT_SAFE := Color(0.0, 1.0, 0.8, 1.0)
const MAT_HAZARD := Color(1.0, 0.18, 0.12, 1.0)
const MAT_OBJECTIVE := Color(1.0, 0.84, 0.2, 1.0)
const MAT_EXIT := Color(0.2, 0.55, 1.0, 1.0)
const MAT_NEUTRAL := Color(0.38, 0.42, 0.4, 1.0)


func _ready() -> void:
    _build_lighting()
    _build_greybox_route()
    _build_ui_proxy()


func _build_lighting() -> void:
    var sun := DirectionalLight3D.new()
    sun.name = "FA_KeyLight"
    sun.rotation_degrees = Vector3(-52.0, 32.0, 0.0)
    add_child(sun)
    var camera := Camera3D.new()
    camera.name = "FA_PrototypeCamera"
    camera.position = Vector3(0.0, 8.0, 13.0)
    camera.rotation_degrees = Vector3(-38.0, 0.0, 0.0)
    add_child(camera)
    camera.current = true


func _build_greybox_route() -> void:
    _box("FA_RouteFloor_Start", Vector3(-6.0, 0.0, 0.0), Vector3(5.0, 0.25, 3.0), MAT_SAFE)
    _box("FA_RouteFloor_Mid", Vector3(0.0, 0.0, 0.0), Vector3(5.0, 0.25, 3.0), MAT_SAFE)
    _box("FA_RouteFloor_Final", Vector3(6.0, 0.0, 0.0), Vector3(5.0, 0.25, 3.0), MAT_SAFE)
    _box("FA_Ramp_Teach", Vector3(-2.6, 0.55, -1.25), Vector3(2.4, 0.3, 1.0), MAT_NEUTRAL)
    _box("FA_WallRun_Panel", Vector3(1.2, 1.5, -1.7), Vector3(3.5, 2.4, 0.24), MAT_NEUTRAL)
    _box("FA_Boost_Pad", Vector3(3.9, 0.18, 1.0), Vector3(1.5, 0.18, 0.9), MAT_EXIT)
    _box("FA_Fall_Hazard_A", Vector3(-0.1, -0.08, 2.0), Vector3(2.3, 0.12, 0.45), MAT_HAZARD)
    _box("FA_Fall_Hazard_B", Vector3(5.1, -0.08, -2.0), Vector3(2.8, 0.12, 0.45), MAT_HAZARD)
    _box("FA_Checkpoint_Gate", Vector3(0.0, 1.1, 0.0), Vector3(0.35, 2.2, 3.1), MAT_EXIT)
    _box("FA_Objective_Prop", Vector3(6.6, 0.75, 0.0), Vector3(0.8, 1.4, 0.8), MAT_OBJECTIVE)
    _box("FA_Exit_Gate", Vector3(8.8, 1.2, 0.0), Vector3(0.45, 2.4, 3.2), MAT_EXIT)


func _build_ui_proxy() -> void:
    var label := Label3D.new()
    label.name = "FA_UIProxy_Objective"
    label.text = "Objective -> Reach exit"
    label.position = Vector3(-5.8, 2.2, 0.0)
    label.pixel_size = 0.035
    add_child(label)


func _box(node_name: String, origin: Vector3, size: Vector3, color: Color) -> StaticBody3D:
    var body := StaticBody3D.new()
    body.name = node_name
    body.position = origin
    add_child(body)

    var mesh_instance := MeshInstance3D.new()
    mesh_instance.name = node_name + "_Mesh"
    var mesh := BoxMesh.new()
    mesh.size = size
    mesh_instance.mesh = mesh
    mesh_instance.material_override = _material(color)
    body.add_child(mesh_instance)

    var collision := CollisionShape3D.new()
    collision.name = "UCX_" + node_name + "_00"
    var shape := BoxShape3D.new()
    shape.size = size
    collision.shape = shape
    body.add_child(collision)
    return body


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.85
    return material
'''


def _player_controller_gd(plan: GodotProjectPlan) -> str:
    return f'''extends CharacterBody3D

@export var move_speed := 8.0
@export var jump_velocity := 6.0
@export var gravity := 18.0


func _physics_process(delta: float) -> void:
    var input_dir := Vector2.ZERO
    input_dir.x = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
    input_dir.y = Input.get_action_strength("move_back") - Input.get_action_strength("move_forward")
    var direction := Vector3(input_dir.x, 0.0, input_dir.y).normalized()
    velocity.x = direction.x * move_speed
    velocity.z = direction.z * move_speed
    if not is_on_floor():
        velocity.y -= gravity * delta
    elif Input.is_action_just_pressed("jump"):
        velocity.y = jump_velocity
    move_and_slide()


func fantasy_agent_handoff() -> Dictionary:
    return {{
        "project_name": "{plan.project_name}",
        "role": "prototype_player_controller",
        "notes": "Replace with gameplay-specific movement after the greybox loop is validated."
    }}
'''


def _manifest(plan: GodotProjectPlan, artifact: GodotProjectArtifact) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "generated_by": "fantasy-agent.godot-builder",
        "project_name": plan.project_name,
        "engine_version": plan.engine_version,
        "renderer": plan.renderer,
        "project_file": artifact.project_file,
        "main_scene_path": artifact.main_scene_path,
        "scene_paths": artifact.scene_paths,
        "script_paths": artifact.script_paths,
        "asset_dirs": artifact.asset_dirs,
        "automation_steps": plan.automation_steps,
        "risks": [
            "Godot is used as a fast playable-loop validation target.",
            "Keep assets under res://assets/generated after Creative Review approval.",
        ],
    }


def _input_action_line(action: str) -> str:
    safe_action = _godot_identifier(action)
    return f'{safe_action}={{"deadzone":0.5,"events":[]}}'


def _renderer_method(renderer: str) -> str:
    return {
        "Forward+": "forward_plus",
        "Mobile": "mobile",
        "Compatibility": "gl_compatibility",
    }.get(renderer, "gl_compatibility")


def _engine_feature(engine_version: str) -> str:
    parts = [part for part in engine_version.replace("Godot", "").strip().split(".") if part]
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}.{parts[1]}"
    return "4.0"


def _main_scene_from_project(project_text: str) -> str:
    for line in project_text.splitlines():
        if line.startswith("run/main_scene="):
            return line.split("=", maxsplit=1)[1].strip().strip('"')
    return ""


def _script_path_by_name(paths: list[str], name: str) -> str | None:
    for path in paths:
        if Path(path).name == name:
            return path
    return None


def _join_project_path(base: Path, path: str) -> str:
    normalized = Path(path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise GodotMCPSafetyError(f"Godot project-relative path is unsafe: {path}")
    return (base / normalized).as_posix()


def _godot_identifier(value: str) -> str:
    identifier = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value).strip("_")
    if not identifier:
        return "action"
    if identifier[0].isdigit():
        return f"action_{identifier}"
    return identifier


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "godot_project"


def _display_rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _tail(value: str | bytes | None, limit: int = 4000) -> str:
    return _to_text(value)[-limit:]


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
