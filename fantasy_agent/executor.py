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

from fantasy_agent.contracts import (
    DirectorBuildPlan,
    GodotMCPCreateProjectRequest,
    GodotMCPRunImportRequest,
    GodotMCPValidateProjectRequest,
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


def _planned_side_effects(plan: DirectorBuildPlan, project_dir: str, godot_exe: str) -> list[str]:
    return [
        f"Write Godot project files under {project_dir}/ "
        f"(project.godot, scenes, scripts, manifest)",
        f"Validate the generated project at {project_dir}/project.godot",
        f"Run headless import: {godot_exe} --headless --path {project_dir} --import",
    ]


def execute_godot_demo(
    plan: DirectorBuildPlan,
    *,
    session_id: str,
    confirmed: bool = False,
    godot_exe: str = "godot",
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
    run_import: bool = True,
    bridge: GodotMCPBridge | None = None,
) -> ExecutionResult:
    """Orchestrate create -> validate -> import for a Godot demo.

    Args:
        plan: The director build plan (provides godot_plan + gameplay_spec).
        session_id: Unique id for this run; outputs land under
            generated/sessions/<session_id>/godot/.
        confirmed: Total-confirmation gate. If False, returns the planned side
            effects without writing or executing anything.
        godot_exe: Path to the Godot executable for headless import.
        workspace_root: Sandbox root (defaults to the repo root).
        run_import: If False, stop after validate (no engine launch). Useful
            when Godot is unavailable.
        bridge: Optional pre-built GodotMCPBridge (for testing).

    Returns:
        ExecutionResult with per-stage status, artifacts, and logs.
    """

    project_dir = _session_project_dir(session_id, plan.godot_plan.project_name)
    planned = _planned_side_effects(plan, project_dir, godot_exe)

    if not confirmed:
        return ExecutionResult(
            status="confirmation_required",
            session_id=session_id,
            project_dir=project_dir,
            planned_side_effects=planned,
        )

    bridge = bridge or GodotMCPBridge(workspace_root=workspace_root)
    stages: list[StageResult] = []

    # Stage 1: create project files.
    create = bridge.create_godot_project_structure(
        GodotMCPCreateProjectRequest(
            plan=plan.godot_plan,
            project_dir=project_dir,
            write_files=True,
            gameplay_spec=plan.gameplay_spec,
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
