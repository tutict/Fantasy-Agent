"""Execution orchestrator: turn a DirectorBuildPlan into a runnable Godot demo.

This is the glue layer between planning and execution. It does NOT reimplement
engine logic; it sequences the existing godot_mcp tools (create -> validate ->
import) and surfaces a per-stage status report.

Safety model (matches AGENTS.md):
  - A single total-confirmation gate: with confirmed=False, execute_godot_demo
    returns the list of side effects it WOULD perform and writes nothing.
  - With confirmed=True, each side-effecting MCP call still passes its own
    write_files / confirmed_side_effects flag, and outputs stay sandboxed under
    generated/sessions/<session_id>/godot/.
  - No automatic retry in M1; failures are reported with captured logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

from fantasy_agent.contracts import (
    BlenderMCPExecuteRequest,
    ComfyUIMCPExecuteRequest,
    DirectorBuildPlan,
    EnemyPressureReport,
    EnemyPressureTuning,
    GodotMCPCreateProjectRequest,
    GodotMCPRunImportRequest,
    GodotMCPValidateProjectRequest,
    UnrealMCPCreateProjectRequest,
    UnrealMCPEditorCommandletRequest,
    UnrealMCPPrepareAssetIngestRequest,
    UnrealMCPPrepareLevelAssemblyRequest,
)
from fantasy_agent.approval_manifest import (
    filter_approved_blender_assets,
    load_asset_approval_manifest,
)
from fantasy_agent.godot_mcp import DEFAULT_WORKSPACE_ROOT, GodotMCPBridge


@dataclass
class StageResult:
    """Outcome of one orchestration stage."""

    name: str
    status: str  # pending | running | done | failed | blocked
    detail: str = ""
    artifacts: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Aggregate result of an execution run."""

    status: str  # confirmation_required | done | failed
    session_id: str
    project_dir: str = ""
    stages: list[StageResult] = field(default_factory=list)
    planned_side_effects: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "done"


def _session_project_dir(session_id: str, project_name: str) -> str:
    from fantasy_agent.godot_mcp import _slug

    safe = _slug(project_name) or "demo"
    # Stay under the godot_mcp sandbox prefix (generated/godot) while still
    # isolating each run in its own session subfolder.
    return f"generated/godot/sessions/{session_id}/{safe}"


def _planned_side_effects(
    plan: DirectorBuildPlan,
    project_dir: str,
    godot_exe: str,
    *,
    with_assets: bool = False,
    blender_exe: str = "blender",
    with_visuals: bool = False,
    with_gameplay: bool = False,
    approval_manifest_path: str | None = None,
) -> list[str]:
    effects: list[str] = []
    if with_gameplay:
        effects.append(
            "Generate real playable GDScript (player mechanics + win/fail + HUD) "
            "from the gameplay spec"
        )
        effects.append(
            "Apply enemy pressure tuning and write a deterministic enemy pressure report"
        )
    if with_visuals:
        effects.append(
            "Run ComfyUI to generate visual reference images (writes generated/comfyui/*)"
        )
        effects.append(f"Copy reference images into {project_dir}/references/comfyui/")
    if with_assets:
        effects.append(
            f"Run Blender to export glb assets: {blender_exe} --background --python <script> "
            "(writes generated/assets/*.glb)"
        )
        if approval_manifest_path:
            effects.append(
                f"Filter Blender exports through approval manifest: {approval_manifest_path}"
            )
        effects.append(f"Copy exported glb assets approved by manifest into {project_dir}/assets/generated/")
    effects.extend(
        [
            f"Write Godot project files under {project_dir}/ "
            f"(project.godot, scenes, scripts, manifest)",
            f"Validate the generated project at {project_dir}/project.godot",
            f"Run headless import: {godot_exe} --headless --path {project_dir} --import",
        ]
    )
    return effects


def _run_comfyui_stage(
    plan: DirectorBuildPlan,
    stages: list[StageResult],
    *,
    workspace_root: Path | str,
    endpoint: str | None,
    comfyui_bridge: Any | None,
) -> list[str]:
    """Run ComfyUI to generate visual reference images. Returns image paths.

    On any failure (offline, missing checkpoint, error) the stage is recorded as
    failed and an empty list is returned, so the caller continues without
    references rather than breaking the chain.
    """

    try:
        if comfyui_bridge is None:
            from fantasy_agent.comfyui_mcp import ComfyUIMCPBridge

            comfyui_bridge = ComfyUIMCPBridge(workspace_root=workspace_root)
        visual_plan = plan.comfyui_plan
        checkpoint = visual_plan.checkpoint_name or ""
        request_kwargs: dict[str, Any] = {
            "plan": visual_plan,
            "checkpoint_name": checkpoint,
            "confirmed_side_effects": True,
            "wait_for_completion": True,
        }
        if endpoint:
            request_kwargs["endpoint_candidates"] = [endpoint]
            request_kwargs["auto_discover_endpoint"] = False
        result = comfyui_bridge.run_visual_reference_workflow(
            ComfyUIMCPExecuteRequest(**request_kwargs)
        )
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on any failure
        stages.append(
            StageResult("comfyui", "failed", detail=f"{exc}; continuing without references")
        )
        return []

    if result.status not in ("executed", "queued"):
        stages.append(
            StageResult(
                "comfyui",
                "failed",
                detail=f"status={result.status}; continuing without references",
                logs=result.log_paths,
            )
        )
        return []

    images = list(result.generated_images)
    stages.append(
        StageResult(
            "comfyui",
            "done",
            detail=f"generated {len(images)} reference images",
            artifacts=images,
            logs=result.log_paths,
        )
    )
    return images


def _run_blender_stage(
    plan: DirectorBuildPlan,
    stages: list[StageResult],
    *,
    blender_exe: str,
    workspace_root: Path | str,
    blender_bridge: Any | None,
) -> list[str]:
    """Run Blender to export glb assets. Returns exported .glb paths.

    On any failure the stage is recorded as failed/blocked and an empty list is
    returned, so the caller degrades to a pure greybox without breaking.
    """

    try:
        if blender_bridge is None:
            from fantasy_agent.blender_mcp import BlenderMCPBridge

            blender_bridge = BlenderMCPBridge(workspace_root=workspace_root)
        # Request glb explicitly for the Godot path.
        glb_plan = plan.blender_plan.model_copy(update={"export_format": "glb"})
        result = blender_bridge.generate_asset_batch(
            BlenderMCPExecuteRequest(
                plan=glb_plan,
                blender_executable=blender_exe,
                confirmed_side_effects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on any failure
        stages.append(
            StageResult("blender", "failed", detail=f"{exc}; degrading to greybox")
        )
        return []

    if result.status != "executed":
        stages.append(
            StageResult(
                "blender",
                "failed",
                detail=f"status={result.status}; degrading to greybox",
                logs=result.log_paths,
            )
        )
        return []

    exported = [a for a in result.exported_assets if a.lower().endswith(".glb")]
    stages.append(
        StageResult(
            "blender",
            "done",
            detail=f"exported {len(exported)} glb",
            artifacts=exported,
            logs=result.log_paths,
        )
    )
    return exported


def _build_enemy_pressure_report(
    plan: DirectorBuildPlan,
    tuning: EnemyPressureTuning,
) -> EnemyPressureReport:
    weights = {"patrol": 1.0, "chase": 1.4, "stationary": 0.8, "ranged": 1.2}
    behavior_counts = {"patrol": 0, "chase": 0, "stationary": 0, "ranged": 0}
    weighted = 0.0
    tuned_enemy_count = 0
    for enemy in plan.gameplay_spec.enemies:
        base_count = enemy.count
        if tuning.enemy_count_multiplier == 0:
            tuned_count = 0
        else:
            tuned_count = max(1, round(base_count * tuning.enemy_count_multiplier))
        behavior_counts[enemy.behavior] += int(tuned_count)
        tuned_enemy_count += int(tuned_count)
        weighted += weights[enemy.behavior] * int(tuned_count)
    if tuned_enemy_count:
        speed_factor = (tuning.move_speed_multiplier + tuning.detection_radius_multiplier) / 2.0
        ranged_factor = 1.0 / tuning.ranged_interval_multiplier
        pressure_score = round(weighted * speed_factor * ranged_factor, 2)
    else:
        pressure_score = 0.0
    warnings: list[str] = []
    if pressure_score >= 10.0:
        warnings.append("High enemy pressure; verify the slice still teaches before punishing.")
    if tuning.enemy_count_multiplier == 0 and plan.gameplay_spec.enemies:
        warnings.append("Enemy roster exists but tuning disables all enemy instances.")
    metrics: dict[str, float | int | str] = {
        "declared_enemy_groups": len(plan.gameplay_spec.enemies),
        "tuned_enemy_count": tuned_enemy_count,
        "pressure_band": "none" if pressure_score == 0 else "high" if pressure_score >= 10 else "medium" if pressure_score >= 5 else "low",
    }
    return EnemyPressureReport(
        enemy_count=tuned_enemy_count,
        behavior_counts=behavior_counts,
        pressure_score=pressure_score,
        tuning=tuning,
        metrics=metrics,
        warnings=warnings,
    )


def _write_enemy_pressure_report(
    report: EnemyPressureReport,
    project_dir: str,
    workspace_root: Path | str,
) -> str:
    report_rel = (Path(project_dir) / "data" / "enemy-pressure-report.json").as_posix()
    report_path = Path(workspace_root) / report_rel
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_rel


def _run_gameplay_codegen(
    plan: DirectorBuildPlan, stages: list[StageResult]
) -> tuple[dict[str, str], bool]:
    """Generate gameplay GDScript. Returns (scripts, was_llm_generated).

    Tries the LLM first; on failure returns deterministic scripts. The
    was_llm flag tells the caller whether to attempt a deterministic fallback
    if the LLM scripts later fail the Godot import.
    """
    from fantasy_agent import gameplay_codegen

    try:
        scripts = gameplay_codegen._generate_with_llm(plan.gameplay_spec)
        stages.append(
            StageResult("gameplay", "done", detail=f"LLM generated {len(scripts)} scripts")
        )
        return scripts, True
    except Exception as exc:  # noqa: BLE001 - degrade to deterministic
        scripts = gameplay_codegen.deterministic_gameplay_scripts(plan.gameplay_spec)
        stages.append(
            StageResult(
                "gameplay",
                "degraded",
                detail=f"LLM unavailable ({exc}); using deterministic scripts",
            )
        )
        return scripts, False


def _asset_planned_side_effects(
    *,
    with_assets: bool,
    blender_exe: str,
    with_visuals: bool,
) -> list[str]:
    effects: list[str] = []
    if with_visuals:
        effects.append("Run ComfyUI to generate visual reference images")
    if with_assets:
        effects.append(
            f"Run Blender to export glb assets: {blender_exe} --background --python <script>"
        )
    if not effects:
        effects.append("No asset workers selected")
    return effects


def _write_approval_gate_report(
    approval: Any,
    project_dir: str,
    workspace_root: Path | str,
) -> str:
    import yaml

    root = Path(workspace_root)
    path = root / project_dir / "generated" / "approval-gate-report.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "executor.approval-gate",
        "schema_version": "0.1",
        "manifest_path": approval.manifest_path,
        "summary": {
            "approved_count": len(approval.approved),
            "skipped_count": len(approval.skipped),
            "revision_count": len(approval.revision_asset_ids),
            "rejected_count": len(approval.rejected_asset_ids),
            "pending_count": len(approval.pending_asset_ids),
        },
        "approved_assets": approval.approved,
        "skipped_assets": approval.skipped,
        "approved_asset_ids": approval.approved_asset_ids,
        "revision_asset_ids": approval.revision_asset_ids,
        "rejected_asset_ids": approval.rejected_asset_ids,
        "pending_asset_ids": approval.pending_asset_ids,
        "qa_notes": [
            "Only approved Blender GLB assets are eligible for Godot copy.",
            "Skipped assets remain available in generated/assets for review or revision.",
        ],
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path.relative_to(root).as_posix()


def execute_asset_pipeline(
    plan: DirectorBuildPlan,
    *,
    session_id: str,
    confirmed: bool = False,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
    with_assets: bool = False,
    blender_exe: str = "blender",
    with_visuals: bool = False,
    comfyui_endpoint: str | None = None,
    blender_bridge: Any | None = None,
    comfyui_bridge: Any | None = None,
) -> ExecutionResult:
    planned = _asset_planned_side_effects(
        with_assets=with_assets,
        blender_exe=blender_exe,
        with_visuals=with_visuals,
    )
    if not confirmed:
        return ExecutionResult(
            status="confirmation_required",
            session_id=session_id,
            planned_side_effects=planned,
        )

    stages: list[StageResult] = []
    if with_visuals:
        _run_comfyui_stage(
            plan,
            stages,
            workspace_root=workspace_root,
            endpoint=comfyui_endpoint,
            comfyui_bridge=comfyui_bridge,
        )
    if with_assets:
        _run_blender_stage(
            plan,
            stages,
            blender_exe=blender_exe,
            workspace_root=workspace_root,
            blender_bridge=blender_bridge,
        )
    if not stages:
        stages.append(StageResult("assets", "blocked", detail="No asset workers selected"))

    status = "failed" if any(stage.status == "failed" for stage in stages) else "done"
    return ExecutionResult(status, session_id, stages=stages, planned_side_effects=planned)


def execute_godot_demo(
    plan: DirectorBuildPlan,
    *,
    session_id: str,
    confirmed: bool = False,
    godot_exe: str = "godot",
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
    run_import: bool = True,
    with_assets: bool = False,
    blender_exe: str = "blender",
    with_visuals: bool = False,
    comfyui_endpoint: str | None = None,
    with_gameplay: bool = False,
    enemy_tuning: EnemyPressureTuning | None = None,
    approval_manifest_path: str | None = None,
    bridge: GodotMCPBridge | None = None,
    blender_bridge: Any | None = None,
    comfyui_bridge: Any | None = None,
) -> ExecutionResult:
    """Orchestrate (optional ComfyUI/Blender) -> create -> validate -> import.

    Args:
        plan: The director build plan (provides godot_plan + gameplay_spec).
        session_id: Unique id for this run; outputs land under
            generated/godot/sessions/<session_id>/.
        confirmed: Total-confirmation gate. If False, returns the planned side
            effects without writing or executing anything.
        godot_exe: Path to the Godot executable for headless import.
        workspace_root: Sandbox root (defaults to the repo root).
        run_import: If False, stop after validate (no engine launch).
        with_assets: If True, run a Blender stage to export glb assets and copy
            them into the project. On any Blender failure the run degrades to a
            pure greybox (the chain is not broken).
        blender_exe: Path to the Blender executable.
        with_visuals: If True, run a ComfyUI stage to generate visual reference
            images and copy them into references/comfyui/. On any failure the
            run continues without references (the chain is not broken).
        comfyui_endpoint: Optional ComfyUI endpoint override.
        enemy_tuning: Enemy pressure multipliers for generated Godot enemies.
        approval_manifest_path: Optional generated approval manifest for asset copy gating.
        bridge: Optional pre-built GodotMCPBridge (for testing).
        blender_bridge: Optional pre-built BlenderMCPBridge (for testing).
        comfyui_bridge: Optional pre-built ComfyUIMCPBridge (for testing).

    Returns:
        ExecutionResult with per-stage status, artifacts, and logs.
    """

    enemy_tuning = enemy_tuning or EnemyPressureTuning()
    project_dir = _session_project_dir(session_id, plan.godot_plan.project_name)
    planned = _planned_side_effects(
        plan,
        project_dir,
        godot_exe,
        with_assets=with_assets,
        blender_exe=blender_exe,
        with_visuals=with_visuals,
        with_gameplay=with_gameplay,
        approval_manifest_path=approval_manifest_path,
    )

    if not confirmed:
        return ExecutionResult(
            status="confirmation_required",
            session_id=session_id,
            project_dir=project_dir,
            planned_side_effects=planned,
        )

    bridge = bridge or GodotMCPBridge(workspace_root=workspace_root)
    stages: list[StageResult] = []

    # Stage A (optional): ComfyUI visual references. Degrades on failure.
    reference_images: list[str] = []
    if with_visuals:
        reference_images = _run_comfyui_stage(
            plan,
            stages,
            workspace_root=workspace_root,
            endpoint=comfyui_endpoint,
            comfyui_bridge=comfyui_bridge,
        )

    # Stage B (optional): Blender asset export. Degrades to greybox on failure.
    exported_glb: list[str] = []
    if with_assets:
        exported_glb = _run_blender_stage(
            plan,
            stages,
            blender_exe=blender_exe,
            workspace_root=workspace_root,
            blender_bridge=blender_bridge,
        )

    if with_assets and exported_glb and approval_manifest_path:
        try:
            manifest = load_asset_approval_manifest(
                approval_manifest_path, workspace_root=workspace_root
            )
            approval = filter_approved_blender_assets(
                exported_glb, manifest, manifest_path=approval_manifest_path
            )
            exported_glb = approval.approved
            detail = f"{len(approval.approved)} approved, {len(approval.skipped)} skipped"
            approval_report = _write_approval_gate_report(
                approval, project_dir, workspace_root
            )
            stages.append(
                StageResult(
                    "approval_gate",
                    "done",
                    detail=detail,
                    artifacts=[approval_manifest_path, approval_report],
                    logs=approval.skipped,
                    metadata={
                        "manifest_path": approval_manifest_path,
                        "report_path": approval_report,
                        "approved_assets": approval.approved,
                        "skipped_assets": approval.skipped,
                        "approved_asset_ids": approval.approved_asset_ids,
                        "revision_asset_ids": approval.revision_asset_ids,
                        "rejected_asset_ids": approval.rejected_asset_ids,
                        "pending_asset_ids": approval.pending_asset_ids,
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001 - gate assets, keep greybox running
            exported_glb = []
            stages.append(
                StageResult(
                    "approval_gate",
                    "blocked",
                    detail=f"{exc}; no Blender assets copied",
                    artifacts=[approval_manifest_path],
                    metadata={
                        "manifest_path": approval_manifest_path,
                        "approved_assets": [],
                        "skipped_assets": [],
                        "blocked_reason": str(exc),
                    },
                )
            )

    # Stage C (optional): generate real playable GDScript from the spec.
    gameplay_scripts: dict[str, str] = {}
    gameplay_was_llm = False
    if with_gameplay:
        gameplay_scripts, gameplay_was_llm = _run_gameplay_codegen(plan, stages)

    # Stage 1: create project files (with generated gameplay scripts if any).
    create = bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(
            plan=plan.godot_plan,
            project_dir=project_dir,
            write_files=True,
            gameplay_spec=plan.gameplay_spec,
            gameplay_scripts=gameplay_scripts,
            enemy_tuning=enemy_tuning,
        )
    )
    if create.status != "written" or create.artifact is None:
        stages.append(
            StageResult("create", "failed", detail="; ".join(create.risks) or "create failed")
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    stages.append(
        StageResult(
            "create",
            "done",
            detail=f"wrote {len(create.written_files)} files",
            artifacts=create.written_files,
        )
    )

    project_file = create.artifact.project_file

    if with_gameplay:
        enemy_report = _build_enemy_pressure_report(plan, enemy_tuning)
        report_path = _write_enemy_pressure_report(enemy_report, project_dir, workspace_root)
        detail = (
            f"{enemy_report.enemy_count} enemies, pressure_score="
            f"{enemy_report.pressure_score}, band={enemy_report.metrics.get('pressure_band')}"
        )
        stages.append(
            StageResult(
                "enemy_metrics",
                "done",
                detail=detail,
                artifacts=[report_path],
                logs=enemy_report.warnings,
            )
        )

    # Stage 1b (optional): copy exported glb assets into the project so the
    # import step picks them up and runtime load() calls resolve.
    if with_assets and exported_glb:
        from fantasy_agent.godot_assets import copy_assets_into_godot_project

        copy_result = copy_assets_into_godot_project(
            exported_glb, project_dir, workspace_root=workspace_root
        )
        detail = f"copied {len(copy_result.copied)} glb"
        if copy_result.skipped:
            detail += f", skipped {len(copy_result.skipped)}"
        stages.append(
            StageResult("copy_assets", "done", detail=detail, artifacts=copy_result.copied)
        )

    # Stage 1c (optional): copy ComfyUI reference images into the project for
    # review (art-direction archive; not applied as textures).
    if with_visuals and reference_images:
        from fantasy_agent.godot_assets import copy_references_into_godot_project

        ref_result = copy_references_into_godot_project(
            reference_images, project_dir, workspace_root=workspace_root
        )
        detail = f"copied {len(ref_result.copied)} references"
        if ref_result.skipped:
            detail += f", skipped {len(ref_result.skipped)}"
        stages.append(
            StageResult("copy_refs", "done", detail=detail, artifacts=ref_result.copied)
        )

    # Stage 2: validate.
    validate = bridge.validate_godot_project(
        GodotMCPValidateProjectRequest(project_file=project_file)
    )
    report = validate.validation_report
    if report is not None and report.issues:
        stages.append(
            StageResult("validate", "failed", detail="; ".join(report.issues))
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    stages.append(
        StageResult(
            "validate",
            "done",
            detail=f"{report.script_count if report else 0} scripts validated",
        )
    )

    # Stage 3: headless import (optional).
    if not run_import:
        stages.append(StageResult("import", "blocked", detail="run_import=False"))
        return ExecutionResult("done", session_id, project_dir, stages, planned)

    imported = bridge.run_godot_import(
        GodotMCPRunImportRequest(
            project_file=project_file,
            godot_executable=godot_exe,
            confirmed_side_effects=True,
        )
    )
    if imported.status != "executed" or (imported.return_code not in (0, None)):
        # If LLM-generated gameplay scripts broke the import, fall back to the
        # deterministic templates and re-import once so the demo still runs.
        if gameplay_was_llm:
            from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts

            fallback = deterministic_gameplay_scripts(plan.gameplay_spec)
            bridge.create_godot_project_structure(
                GodotMCPCreateProjectRequest(
                    plan=plan.godot_plan,
                    project_dir=project_dir,
                    write_files=True,
                    gameplay_spec=plan.gameplay_spec,
                    gameplay_scripts=fallback,
                    enemy_tuning=enemy_tuning,
                )
            )
            reimport = bridge.run_godot_import(
                GodotMCPRunImportRequest(
                    project_file=project_file,
                    godot_executable=godot_exe,
                    confirmed_side_effects=True,
                )
            )
            if reimport.status == "executed" and reimport.return_code in (0, None):
                stages.append(
                    StageResult(
                        "gameplay",
                        "degraded",
                        detail="LLM scripts failed import; fell back to deterministic templates",
                    )
                )
                stages.append(
                    StageResult(
                        "import", "done", detail="headless import ok (fallback)",
                        logs=reimport.log_paths,
                    )
                )
                return ExecutionResult("done", session_id, project_dir, stages, planned)
        stages.append(
            StageResult(
                "import",
                "failed",
                detail=imported.stderr_tail or f"import status={imported.status}",
                logs=imported.log_paths,
            )
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    stages.append(
        StageResult("import", "done", detail="headless import ok", logs=imported.log_paths)
    )

    return ExecutionResult("done", session_id, project_dir, stages, planned)


def format_execution_report(result: ExecutionResult) -> str:
    """Human-readable summary for CLI output."""

    if result.status == "confirmation_required":
        lines = [
            "Execution requires confirmation. The following side effects would run:",
            *[f"  - {effect}" for effect in result.planned_side_effects],
            "",
            "Re-run with --yes to proceed.",
        ]
        return "\n".join(lines)

    icon = {"done": "OK", "failed": "FAILED"}.get(result.status, result.status)
    lines = [f"[{icon}] session {result.session_id}", f"  project: {result.project_dir}"]
    for stage in result.stages:
        lines.append(f"  - {stage.name}: {stage.status} ({stage.detail})")
        for log in stage.logs:
            lines.append(f"      log: {log}")
    return "\n".join(lines)


def _unreal_session_project_dir(session_id: str, project_name: str) -> str:
    from fantasy_agent.godot_mcp import _slug

    safe = _slug(project_name) or "demo"
    return f"generated/unreal/sessions/{session_id}/{safe}"


def _unreal_planned_side_effects(project_dir: str, unreal_cmd: str, run_validation: bool) -> list[str]:
    effects = [
        f"Write Unreal project files under {project_dir}/ (.uproject, Config, Content, scripts)",
        "Prepare asset ingest manifest + Python script",
        "Prepare level assembly manifest + Python script",
    ]
    if run_validation:
        effects.append(
            f"Run DataValidation: {unreal_cmd} <project> -run=DataValidation -IncludeOnlyOnDiskAssets"
        )
    return effects


def execute_unreal_demo(
    plan: DirectorBuildPlan,
    *,
    session_id: str,
    confirmed: bool = False,
    unreal_cmd: str = "UnrealEditor-Cmd",
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
    run_validation: bool = True,
    bridge: Any | None = None,
) -> ExecutionResult:
    """Orchestrate create -> prepare ingest -> prepare level -> DataValidation.

    Generates a complete UE5 project and validates it with the DataValidation
    commandlet. The heavyweight run_asset_ingest / run_level_assembly steps are
    intentionally out of scope here (they require real fbx assets and a full
    editor launch).

    Args:
        plan: Director build plan (provides unreal_plan + blender_plan manifest).
        session_id: Unique id; outputs land under generated/unreal/sessions/<id>/.
        confirmed: Total-confirmation gate. If False, returns planned side effects.
        unreal_cmd: Path to UnrealEditor-Cmd for headless DataValidation.
        workspace_root: Sandbox root.
        run_validation: If False, stop after prepare_level (no editor launch).
        bridge: Optional pre-built UnrealMCPBridge (for testing).

    Returns:
        ExecutionResult with per-stage status, artifacts, and logs.
    """

    project_dir = _unreal_session_project_dir(session_id, plan.unreal_plan.project_name)
    planned = _unreal_planned_side_effects(project_dir, unreal_cmd, run_validation)

    if not confirmed:
        return ExecutionResult(
            status="confirmation_required",
            session_id=session_id,
            project_dir=project_dir,
            planned_side_effects=planned,
        )

    if bridge is None:
        from fantasy_agent.unreal_mcp import UnrealMCPBridge

        bridge = UnrealMCPBridge(workspace_root=workspace_root)
    stages: list[StageResult] = []

    # Write the Blender->Unreal import manifest so prepare_asset_ingest can read
    # it. Source fbx files need not exist yet (require_existing_sources=False).
    manifest_path = _write_unreal_import_manifest(plan, workspace_root)

    # Stage 1: create project.
    create = bridge.create_project_structure(
        UnrealMCPCreateProjectRequest(
            plan=plan.unreal_plan,
            project_dir=project_dir,
            write_files=True,
        )
    )
    if create.status != "written" or create.artifact is None:
        stages.append(
            StageResult("create", "failed", detail="; ".join(create.risks) or "create failed")
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    project_file = create.artifact.project_file
    stages.append(
        StageResult(
            "create", "done", detail=f"wrote {len(create.written_files)} files",
            artifacts=create.written_files,
        )
    )

    # Stage 2: prepare asset ingest.
    ingest = bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file=project_file,
            blender_import_manifest_path=manifest_path,
            write_files=True,
            require_existing_sources=False,
        )
    )
    if ingest.status != "written" or ingest.manifest is None:
        stages.append(
            StageResult("prepare_ingest", "failed", detail="; ".join(ingest.risks) or "failed")
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    ingest_manifest_path = next(
        (f for f in ingest.written_files if f.endswith((".yaml", ".yml", ".json"))),
        "",
    )
    stages.append(
        StageResult("prepare_ingest", "done", detail=f"{len(ingest.manifest.jobs)} ingest jobs")
    )

    # Stage 3: prepare level assembly.
    level = bridge.prepare_level_assembly(
        UnrealMCPPrepareLevelAssemblyRequest(
            project_file=project_file,
            ingest_manifest_path=ingest_manifest_path,
            write_files=True,
        )
    )
    if level.status != "written":
        stages.append(
            StageResult("prepare_level", "failed", detail="; ".join(level.risks) or "failed")
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    stages.append(StageResult("prepare_level", "done", detail="level manifest + script written"))

    # Stage 4 (optional): DataValidation commandlet.
    if not run_validation:
        stages.append(StageResult("validate", "blocked", detail="run_validation=False"))
        return ExecutionResult("done", session_id, project_dir, stages, planned)

    validation = bridge.run_editor_commandlet(
        UnrealMCPEditorCommandletRequest(
            project_file=project_file,
            commandlet="DataValidation",
            unreal_editor_cmd=unreal_cmd,
            confirmed_side_effects=True,
        )
    )
    if validation.status != "executed" or (validation.return_code not in (0, None)):
        stages.append(
            StageResult(
                "validate",
                "failed",
                detail=validation.stderr_tail or f"status={validation.status}",
                logs=validation.log_paths,
            )
        )
        return ExecutionResult("failed", session_id, project_dir, stages, planned)
    stages.append(
        StageResult("validate", "done", detail="DataValidation ok", logs=validation.log_paths)
    )
    return ExecutionResult("done", session_id, project_dir, stages, planned)


def _write_unreal_import_manifest(plan: DirectorBuildPlan, workspace_root: Path | str) -> str:
    """Serialize the Blender->Unreal import manifest to YAML and return its path."""
    import yaml

    from fantasy_agent.blender_codegen import build_unreal_import_manifest

    manifest = build_unreal_import_manifest(plan.blender_plan)
    rel = "generated/import-manifest.yaml"
    dest = Path(workspace_root) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return rel
