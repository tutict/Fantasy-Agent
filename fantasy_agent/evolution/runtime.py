"""The engine boundary for an explicitly granted, deterministic experiment."""

import time
from collections.abc import Callable
from pathlib import Path

from fantasy_agent import local_tools, process_runner
from fantasy_agent.contracts import DirectorBuildPlan, PlaytestFinding, PlaytestReport
from fantasy_agent.executor import execute_godot_demo
from fantasy_agent.godot_mcp import GodotMCPBridge


class EvolutionBudgetExceeded(RuntimeError):
    """No additional engine work may start after the experiment deadline."""


def make_iteration_runner(
    *, workspace_root: Path | str, confirmed: bool,
    clock: Callable[[], float] = time.monotonic,
):
    """Reuse the executor, clipping every engine process to the remaining budget.

    A bundle is mandatory at the controller boundary; that executor path uses
    deterministic codegen even when the workspace has a configured model.
    """
    if not confirmed:
        raise ValueError("Godot 实验需要用户明确确认。")
    executable = local_tools._find_godot()

    def measured(plan: DirectorBuildPlan, session_id: str, remaining_seconds: float) -> PlaytestReport:
        if not executable:
            return PlaytestReport(findings=[PlaytestFinding(
                code="engine_missing", severity="blocking", message="未找到 Godot，请先配置工具环境。",
                rework_target="flags",
            )])
        deadline = clock() + remaining_seconds

        def launch(command, **kwargs):
            event = process_runner.current_cancel_event()
            if event is not None and event.is_set():
                raise process_runner.ProcessCancelled(command)
            remaining = deadline - clock()
            if remaining <= 0:
                raise EvolutionBudgetExceeded("实验总时间预算已耗尽。")
            timeout = kwargs.get("timeout")
            kwargs["timeout"] = min(remaining, timeout) if timeout is not None else remaining
            return process_runner.run_streaming(command, **kwargs)

        # The bridge uses this marker to pass log paths and the cancel context.
        launch.fa_streaming = True
        bridge = GodotMCPBridge(workspace_root=workspace_root, runner=launch)
        result = execute_godot_demo(
            plan, session_id=session_id, confirmed=confirmed,
            workspace_root=workspace_root, godot_exe=executable,
            with_gameplay=True, with_assets=False, with_visuals=False, bridge=bridge,
        )
        stage = next((stage for stage in result.stages if stage.name == "playtest"), None)
        if stage is not None and stage.metadata:
            return PlaytestReport.model_validate(stage.metadata)
        if clock() >= deadline:
            raise EvolutionBudgetExceeded("实验总时间预算已耗尽。")
        failed = [stage.detail for stage in result.stages if stage.status == "failed"]
        raise ValueError("工程未完成试玩：" + "; ".join(failed or [result.status]))

    return measured
