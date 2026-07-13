from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fantasy_agent.path_safety import (
    WorkspacePathError,
    display_workspace_path,
    resolve_workspace_path,
)
from fantasy_agent.contracts import (
    EnemyPressureTuning,
    GameplaySpec,
    GodotMCPCreateProjectRequest,
    GodotMCPResult,
    GodotMCPRunImportRequest,
    GodotMCPValidateProjectRequest,
    GodotProjectArtifact,
    GodotProjectPlan,
    ProductionSpecBundle,
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
                "Defaults to in-memory output; set write_files only after file operations are approved."
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
            written_files = self._write_project_artifact(
                artifact,
                request.plan,
                request.gameplay_spec,
                request.gameplay_scripts,
                request.enemy_tuning,
                request.production_spec_bundle,
            )
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
        gameplay_spec: GameplaySpec | None = None,
        gameplay_scripts: dict[str, str] | None = None,
        enemy_tuning: EnemyPressureTuning | None = None,
        production_spec_bundle: ProductionSpecBundle | None = None,
    ) -> list[str]:
        gameplay_scripts = gameplay_scripts or {}
        enemy_tuning = enemy_tuning or EnemyPressureTuning()
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
        enemy_script = _script_path_by_name(artifact.script_paths, "enemy_controller.gd")
        if main_script is None:
            main_script = (Path(artifact.project_dir) / "scripts" / "main.gd").as_posix()
            artifact.script_paths.append(main_script)
        if player_script is None:
            player_script = (Path(artifact.project_dir) / "scripts" / "player_controller.gd").as_posix()
            artifact.script_paths.append(player_script)

        self._write_text(project_file, _project_godot(plan))
        self._write_text(main_scene_path, _main_scene())
        has_gameplay = bool(gameplay_scripts)
        self._write_text(
            self._resolve_workspace_path(main_script),
            _main_gd(
                plan,
                gameplay_spec,
                with_gameplay=has_gameplay,
                enemy_tuning=enemy_tuning,
                production_spec_bundle=production_spec_bundle,
            ),
        )
        # Player controller: use the generated script if provided, else template.
        player_src = gameplay_scripts.get("scripts/player_controller.gd")
        self._write_text(
            self._resolve_workspace_path(player_script),
            player_src if player_src else _player_controller_gd(plan),
        )
        written = [
            self._display_path(project_file),
            self._display_path(main_scene_path),
            self._display_path(self._resolve_workspace_path(main_script)),
            self._display_path(self._resolve_workspace_path(player_script)),
        ]
        if enemy_script and "scripts/enemy_controller.gd" not in gameplay_scripts:
            resolved_enemy = self._resolve_workspace_path(enemy_script)
            self._write_text(resolved_enemy, _enemy_controller_gd())
            written.append(self._display_path(resolved_enemy))
        # Any extra generated scripts (e.g. game_manager.gd) beyond the player.
        for rel, source in gameplay_scripts.items():
            if rel == "scripts/player_controller.gd":
                continue
            extra_path = (Path(artifact.project_dir) / rel).as_posix()
            resolved = self._resolve_workspace_path(extra_path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            self._write_text(resolved, source)
            if extra_path not in artifact.script_paths:
                artifact.script_paths.append(extra_path)
            written.append(self._display_path(resolved))
        self._write_text(manifest_path, json.dumps(_manifest(plan, artifact), indent=2))
        written.append(self._display_path(manifest_path))
        return written

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
        try:
            resolve_workspace_path(
                path,
                workspace_root=self.workspace_root,
                required_prefix=required_prefix,
            )
        except WorkspacePathError as exc:
            raise GodotMCPSafetyError(str(exc)) from exc

    def _resolve_workspace_path(self, path: str) -> Path:
        try:
            return resolve_workspace_path(path, workspace_root=self.workspace_root)
        except WorkspacePathError as exc:
            raise GodotMCPSafetyError(str(exc)) from exc

    def _log_paths(self, project_name: str, operation: str) -> tuple[Path, Path]:
        safe_name = _slug(project_name)
        log_dir = self.workspace_root / "generated" / "logs" / "godot"
        return log_dir / f"{safe_name}_{operation}.stdout.log", log_dir / f"{safe_name}_{operation}.stderr.log"

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        return display_workspace_path(path, workspace_root=self.workspace_root)


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
        return "Godot MCP blocked execution because the operation was not confirmed."
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


def _default_route_body() -> str:
    """The original fixed greybox route, used when no GameplaySpec is supplied."""
    lines = [
        '    _box("FA_RouteFloor_Start", Vector3(-6.0, 0.0, 0.0), Vector3(5.0, 0.25, 3.0), MAT_SAFE)',
        '    _box("FA_RouteFloor_Mid", Vector3(0.0, 0.0, 0.0), Vector3(5.0, 0.25, 3.0), MAT_SAFE)',
        '    _box("FA_RouteFloor_Final", Vector3(6.0, 0.0, 0.0), Vector3(5.0, 0.25, 3.0), MAT_SAFE)',
        '    _box("FA_Ramp_Teach", Vector3(-2.6, 0.55, -1.25), Vector3(2.4, 0.3, 1.0), MAT_NEUTRAL)',
        '    _box("FA_WallRun_Panel", Vector3(1.2, 1.5, -1.7), Vector3(3.5, 2.4, 0.24), MAT_NEUTRAL)',
        '    _box("FA_Boost_Pad", Vector3(3.9, 0.18, 1.0), Vector3(1.5, 0.18, 0.9), MAT_EXIT)',
        '    _box("FA_Fall_Hazard_A", Vector3(-0.1, -0.08, 2.0), Vector3(2.3, 0.12, 0.45), MAT_HAZARD)',
        '    _box("FA_Fall_Hazard_B", Vector3(5.1, -0.08, -2.0), Vector3(2.8, 0.12, 0.45), MAT_HAZARD)',
        '    _box("FA_Checkpoint_Gate", Vector3(0.0, 1.1, 0.0), Vector3(0.35, 2.2, 3.1), MAT_EXIT)',
        '    _box("FA_Objective_Prop", Vector3(6.6, 0.75, 0.0), Vector3(0.8, 1.4, 0.8), MAT_OBJECTIVE)',
        '    _box("FA_Exit_Gate", Vector3(8.8, 1.2, 0.0), Vector3(0.45, 2.4, 3.2), MAT_EXIT)',
    ]
    return "\n".join(lines)


def _beat_material(required_assets: list[str]) -> str:
    """Pick a material constant by scanning a beat's required-asset keywords."""
    joined = " ".join(required_assets).casefold()
    if any(word in joined for word in ("hazard", "trap", "danger", "fall")):
        return "MAT_HAZARD"
    if any(word in joined for word in ("exit", "gate", "goal", "finish")):
        return "MAT_EXIT"
    if any(word in joined for word in ("objective", "prop", "target", "pickup", "collect")):
        return "MAT_OBJECTIVE"
    return "MAT_SAFE"


def _beat_asset_glb(required_assets: list[str]) -> str:
    """Expected glb filename for a beat's first required asset, or "" if none.

    Mirrors prepare_blender_assets, which names exports by slugify(asset_need).
    The returned value is a bare filename (no directory); the GDScript helper
    resolves it under res://assets/generated/.
    """
    if not required_assets:
        return ""
    return f"{_slug(required_assets[0])}.glb"


def _route_body_from_spec(gameplay_spec: GameplaySpec | None) -> str:
    """Generate the _build_greybox_route body, one segment per level beat.

    Falls back to the fixed greybox route when no spec is available so existing
    behavior and tests are preserved.
    """
    if gameplay_spec is None or not gameplay_spec.level_beats:
        return _default_route_body()

    lines: list[str] = []
    spacing = 6.0
    start_x = -spacing * (len(gameplay_spec.level_beats) - 1) / 2.0
    for index, beat in enumerate(gameplay_spec.level_beats):
        x = start_x + index * spacing
        safe_name = _slug(beat.name) or f"beat_{index}"
        floor_name = f"FA_RouteFloor_{index}_{safe_name}"
        lines.append(
            f'    _box("{floor_name}", Vector3({x:.1f}, 0.0, 0.0), '
            "Vector3(5.0, 0.25, 3.0), MAT_SAFE)"
        )
        material = _beat_material(beat.required_assets)
        marker_name = f"FA_Beat_{index}_{safe_name}_Marker"
        # Prefer an imported glb for this beat's first required asset; the GDScript
        # helper falls back to a greybox box when the asset is absent, so the
        # no-asset path stays identical to M1.
        asset_glb = _beat_asset_glb(beat.required_assets)
        asset_literal = json.dumps(asset_glb, ensure_ascii=False)
        lines.append(
            f'    _spawn_marker("{marker_name}", Vector3({x:.1f}, 0.9, 0.0), '
            f"Vector3(0.8, 1.4, 0.8), {material}, {asset_literal})"
        )
    # Final exit gate beyond the last beat.
    exit_x = start_x + len(gameplay_spec.level_beats) * spacing
    lines.append(
        f'    _box("FA_Exit_Gate", Vector3({exit_x:.1f}, 1.2, 0.0), '
        "Vector3(0.45, 2.4, 3.2), MAT_EXIT)"
    )
    return "\n".join(lines)


def _route_body_from_production_specs(bundle: ProductionSpecBundle) -> str:
    """Generate the greybox route directly from LevelSpec segments."""

    segments = [
        bundle.level.teaching_segment,
        *bundle.level.mid_segments,
        bundle.level.final_test,
    ]
    lines: list[str] = []
    spacing = 6.0
    start_x = -spacing * (len(segments) - 1) / 2.0
    for index, segment in enumerate(segments):
        x = start_x + index * spacing
        safe_name = _slug(segment.name) or f"segment_{index}"
        lines.append(
            f'    _box("FA_RouteFloor_{index}_{safe_name}", Vector3({x:.1f}, 0.0, 0.0), '
            "Vector3(5.0, 0.25, 3.0), MAT_SAFE)"
        )
        marker_name = f"FA_SpecGate_{index}_{_slug(segment.objective_gate)}"
        material = "MAT_OBJECTIVE" if index < len(segments) - 1 else "MAT_EXIT"
        lines.append(
            f'    _spawn_marker("{marker_name}", Vector3({x:.1f}, 0.9, 0.0), '
            f'Vector3(0.8, 1.4, 0.8), {material}, "")'
        )
    exit_x = start_x + len(segments) * spacing
    lines.append(
        f'    _box("FA_Exit_Gate", Vector3({exit_x:.1f}, 1.2, 0.0), '
        "Vector3(0.45, 2.4, 3.2), MAT_EXIT)"
    )
    return "\n".join(lines)


_GAMEPLAY_SPAWN_GD = '''
func _spawn_gameplay() -> void:
    var player_script := load("res://scripts/player_controller.gd")
    if player_script != null:
        var player: CharacterBody3D = player_script.new()
        player.name = "FA_Player"
        player.add_to_group("player")
        player.position = Vector3(-6.0, 1.0, 0.0)
        var col := CollisionShape3D.new()
        var caps := CapsuleShape3D.new()
        caps.radius = 0.4
        caps.height = 1.6
        col.shape = caps
        player.add_child(col)
        var mesh := MeshInstance3D.new()
        var capsule := CapsuleMesh.new()
        capsule.radius = 0.4
        capsule.height = 1.6
        mesh.mesh = capsule
        player.add_child(mesh)
        add_child(player)
    var gm_script := load("res://scripts/game_manager.gd")
    if gm_script != null:
        var gm: Node = gm_script.new()
        gm.name = "FA_GameManager"
        add_child(gm)
        var exit := get_node_or_null("FA_Exit_Gate")
        if exit != null and gm.has_method("reach_exit"):
            var area := Area3D.new()
            area.name = "FA_ExitTrigger"
            var acol := CollisionShape3D.new()
            var box := BoxShape3D.new()
            box.size = Vector3(1.2, 3.0, 3.6)
            acol.shape = box
            area.add_child(acol)
            exit.add_child(area)
            area.body_entered.connect(func(_b: Node) -> void: gm.reach_exit())
        _spawn_enemies(gm)


func _spawn_enemies(gm: Node) -> void:
    if not HANDOFF.has("gameplay"):
        return
    var enemies: Array = HANDOFF["gameplay"].get("enemies", [])
    if enemies.is_empty():
        return
    var tuning: Dictionary = HANDOFF["gameplay"].get("enemy_tuning", {})
    var count_multiplier := float(tuning.get("enemy_count_multiplier", 1.0))
    var speed_multiplier := float(tuning.get("move_speed_multiplier", 1.0))
    var detection_multiplier := float(tuning.get("detection_radius_multiplier", 1.0))
    var patrol_multiplier := float(tuning.get("patrol_radius_multiplier", 1.0))
    var ranged_interval_multiplier := float(tuning.get("ranged_interval_multiplier", 1.0))
    var enemy_script := load("res://scripts/enemy_controller.gd")
    if enemy_script == null:
        return
    var spawned := 0
    for enemy in enemies:
        var base_count := int(enemy.get("count", 1))
        var count := 0
        if count_multiplier > 0.0:
            count = max(1, int(round(float(base_count) * count_multiplier)))
        for _i in range(count):
            var instance: Area3D = enemy_script.new()
            var behavior := str(enemy.get("behavior", "patrol"))
            var enemy_name := str(enemy.get("name", "Enemy"))
            instance.name = "FA_Enemy_%s_%02d" % [behavior, spawned]
            instance.position = _enemy_spawn_position(spawned)
            if instance.has_method("setup"):
                instance.setup(enemy_name, behavior, int(enemy.get("hp", 3)), gm)
            var move_speed_value = instance.get("move_speed")
            if move_speed_value != null:
                instance.set("move_speed", float(move_speed_value) * speed_multiplier)
            var detection_radius_value = instance.get("detection_radius")
            if detection_radius_value != null:
                instance.set("detection_radius", float(detection_radius_value) * detection_multiplier)
            var patrol_radius_value = instance.get("patrol_radius")
            if patrol_radius_value != null:
                instance.set("patrol_radius", float(patrol_radius_value) * patrol_multiplier)
            var ranged_interval_value = instance.get("ranged_interval")
            if ranged_interval_value != null:
                instance.set("ranged_interval", float(ranged_interval_value) * ranged_interval_multiplier)
            _decorate_enemy(instance, behavior)
            add_child(instance)
            spawned += 1


func _enemy_spawn_position(index: int) -> Vector3:
    # Distribute threats along the route, away from the player spawn and final exit.
    var x := -2.0 + float(index) * 2.2
    var z := -1.35 if index % 2 == 0 else 1.35
    return Vector3(x, 0.85, z)


func _decorate_enemy(enemy: Area3D, behavior: String) -> void:
    var collision := CollisionShape3D.new()
    var shape := SphereShape3D.new()
    shape.radius = 0.75
    collision.shape = shape
    enemy.add_child(collision)

    var mesh := MeshInstance3D.new()
    var box := BoxMesh.new()
    box.size = Vector3(0.8, 0.8, 0.8)
    mesh.mesh = box
    var color := MAT_HAZARD
    if behavior == "stationary":
        color = MAT_OBJECTIVE
    elif behavior == "ranged":
        color = MAT_EXIT
    mesh.material_override = _material(color)
    enemy.add_child(mesh)

    var label := Label3D.new()
    label.name = enemy.name + "_Label"
    label.text = behavior
    label.position = Vector3(0.0, 0.9, 0.0)
    label.pixel_size = 0.03
    enemy.add_child(label)
'''


def _main_gd(
    plan: GodotProjectPlan,
    gameplay_spec: GameplaySpec | None = None,
    *,
    with_gameplay: bool = False,
    enemy_tuning: EnemyPressureTuning | None = None,
    production_spec_bundle: ProductionSpecBundle | None = None,
) -> str:
    handoff: dict[str, Any] = {
        "project_name": plan.project_name,
        "automation_steps": plan.automation_steps,
        "input_actions": plan.input_actions,
    }
    if gameplay_spec is not None:
        enemy_tuning = enemy_tuning or EnemyPressureTuning()
        handoff["gameplay"] = {
            "title": gameplay_spec.title,
            "core_loop_steps": len(gameplay_spec.core_loop),
            "win_state": gameplay_spec.win_state,
            "failure_states": gameplay_spec.failure_states,
            "level_beats": [beat.name for beat in gameplay_spec.level_beats],
            "enemies": [enemy.model_dump(mode="json") for enemy in gameplay_spec.enemies],
            "enemy_tuning": enemy_tuning.model_dump(mode="json"),
        }
    if production_spec_bundle is not None:
        from fantasy_agent.godot_spec_adapter import compile_godot_spec_bundle

        compiled = compile_godot_spec_bundle(production_spec_bundle)
        effective_tuning = enemy_tuning or production_spec_bundle.numeric.enemy_pressure
        handoff["production_specs"] = compiled.runtime_handoff
        handoff["level_objective_gates"] = production_spec_bundle.level.objective_gates
        handoff["config_tables"] = {
            table.table_id: table.export_path
            for table in production_spec_bundle.config_tables.tables
        }
        handoff["gameplay"] = {
            "title": production_spec_bundle.gameplay_spec_title,
            "core_loop_steps": len(production_spec_bundle.narrative.beats),
            "win_state": production_spec_bundle.narrative.objective_copy[-1],
            "failure_states": production_spec_bundle.narrative.failure_feedback,
            "level_beats": [
                segment["name"] for segment in compiled.runtime_handoff["level"]["segments"]
            ],
            "enemies": compiled.runtime_handoff["enemies"],
            "enemy_tuning": effective_tuning.model_dump(mode="json"),
            "damage_model": (
                production_spec_bundle.combat.damage_model.model_dump(mode="json")
                if production_spec_bundle.combat
                else None
            ),
        }
    payload = json.dumps(handoff, ensure_ascii=False, indent=2)
    route_body = (
        _route_body_from_production_specs(production_spec_bundle)
        if production_spec_bundle is not None
        else _route_body_from_spec(gameplay_spec)
    )
    objective_text = (
        production_spec_bundle.narrative.hud_text.get("objective")
        or production_spec_bundle.narrative.objective_copy[-1]
        if production_spec_bundle is not None
        else gameplay_spec.win_state if gameplay_spec is not None else "Reach exit"
    )
    objective_literal = json.dumps(objective_text, ensure_ascii=False)
    # When real gameplay scripts are present, spawn a controllable player and a
    # game manager, and wire the exit gate's body to reach_exit().
    gameplay_ready = (
        "    _spawn_gameplay()\n" if with_gameplay else ""
    )
    gameplay_funcs = _GAMEPLAY_SPAWN_GD if with_gameplay else ""
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
    _report_objective()
{gameplay_ready}{gameplay_funcs}

func _report_objective() -> void:
    # Win/fail intent is derived from the GameplaySpec so the slice reflects the idea.
    print("[FantasyAgent] objective: ", {objective_literal})
    if HANDOFF.has("gameplay"):
        print("[FantasyAgent] win_state: ", HANDOFF["gameplay"]["win_state"])
        for failure in HANDOFF["gameplay"]["failure_states"]:
            print("[FantasyAgent] failure_state: ", failure)


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
{route_body}


func _build_ui_proxy() -> void:
    var label := Label3D.new()
    label.name = "FA_UIProxy_Objective"
    label.text = "Objective -> Reach exit"
    label.position = Vector3(-5.8, 2.2, 0.0)
    label.pixel_size = 0.035
    add_child(label)


func _spawn_marker(node_name: String, origin: Vector3, size: Vector3, color: Color, asset_file: String) -> Node3D:
    # Prefer an imported glb under res://assets/generated/; fall back to a
    # greybox box when the asset is missing so the slice always builds.
    if asset_file != "":
        var res_path := "res://assets/generated/" + asset_file
        if ResourceLoader.exists(res_path):
            var packed := load(res_path)
            if packed is PackedScene:
                var instance: Node3D = packed.instantiate()
                instance.name = node_name
                instance.position = origin
                add_child(instance)
                return instance
    return _box(node_name, origin, size, color)


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



def _enemy_controller_gd() -> str:
    return """extends Area3D

var _label := "Enemy"


func setup(enemy_name: String, enemy_behavior: String, enemy_hp: int, game_manager: Node) -> void:
    _label = enemy_name


func fantasy_agent_handoff() -> Dictionary:
    return {
        "role": "prototype_enemy_controller",
        "notes": "Generated when a plan declares enemy_controller.gd without a gameplay script pass."
    }
"""


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
