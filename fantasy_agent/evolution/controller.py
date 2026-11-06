"""Bounded numeric rework; only a human adopts a measured candidate."""

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

from fantasy_agent.contracts import DirectorBuildPlan, PlaytestReport
from fantasy_agent.demo_launch import infer_demo_engine
from fantasy_agent.evolution.candidates import (
    apply_changes,
    changes_from_experience,
    plan_fingerprint,
    propose_changes,
)
from fantasy_agent.evolution.contracts import (
    EvolutionExperience,
    EvolutionIteration,
    EvolutionReport,
    EvolutionRequest,
    NumericChange,
    NumericField,
)
from fantasy_agent.evolution.evaluation import candidate_notes, compare_reports, measurement_notes
from fantasy_agent.evolution.library import (
    EvolutionLibraryError,
    list_experiences,
    load_report,
    save_experience,
    save_report,
)
from fantasy_agent.evolution.runtime import EvolutionBudgetExceeded, make_iteration_runner
from fantasy_agent.gameplay_codegen import axis_for_spec
from fantasy_agent.godot_playtest import _status_for, aggregate_samples, build_findings
from fantasy_agent.path_safety import assert_safe_path_segment
from fantasy_agent.process_runner import ProcessCancelled, current_cancel_event


@dataclass
class EvolutionJobResult:
    status: str
    report: EvolutionReport | None = None
    planned_side_effects: list[str] = field(default_factory=list)


@dataclass
class EvolutionSuggestion:
    plan: DirectorBuildPlan
    changes: list[NumericChange] = field(default_factory=list)
    experience_id: str = ""
    notes: list[str] = field(default_factory=list)


_adoption_lock = threading.RLock()


def _validate_plan(plan: DirectorBuildPlan) -> None:
    pipeline = plan.production_pipeline
    if not any(stage.id == "godot_quick_play" for stage in pipeline.stages) or (
        infer_demo_engine(plan, plan.godot_plan.engine_version) != "godot"
    ):
        raise ValueError("首版反馈进化只支持 Godot 灰盒。")
    apply_changes(plan, [])  # Strict bundle and declared tuning bounds, before any write.


def planned_evolution_effects(request: EvolutionRequest) -> list[str]:
    return [
        f"生成一个基线和最多 {request.max_iterations} 个独立 Godot 灰盒候选。",
        "仅调整列出的数值参数；保持玩法规则、核心动作和试玩判据。",
        "启动 Godot headless 导入和试玩，记录每轮真实采样与比较结果。",
        f"总时间预算 {request.max_wall_seconds:g} 秒，可取消。",
        "在 generated/evolution/ 保存实验记录；点击采用后才保存可复用经验。",
        "可调参数：移动速度、压力时钟、敌人数量／移动速度／侦测半径倍率。",
    ]


def _cancel_check() -> None:
    event = current_cancel_event()
    if event is not None and event.is_set():
        raise ProcessCancelled("Godot numeric evolution")


def _measurement(payload: PlaytestReport) -> PlaytestReport:
    report = PlaytestReport.model_validate(payload).model_copy(deep=True)
    report.aggregate = aggregate_samples(report.samples)
    findings = {item.code: item for item in report.findings}
    findings.update({item.code: item for item in build_findings(report.samples, report.aggregate)})
    report.findings = list(findings.values())
    report.status = _status_for(report.findings, report.aggregate)
    return report


def run_evolution(
    request: EvolutionRequest,
    *,
    experiment_id: str,
    workspace_root: Path | str,
    run_iteration: Callable[[DirectorBuildPlan, str, float], PlaytestReport] | None = None,
    clock: Callable[[], float] | None = None,
    experience_workspace_root: Path | str | None = None,
) -> EvolutionJobResult:
    """Run one baseline followed by at most the explicitly granted candidates."""
    request = EvolutionRequest.model_validate(request.model_dump())
    assert_safe_path_segment(experiment_id, label="experiment_id")
    _validate_plan(request.plan)
    effects = planned_evolution_effects(request)
    if not request.confirmed:
        return EvolutionJobResult("confirmation_required", planned_side_effects=effects)
    if load_report(experiment_id, workspace_root=workspace_root) is not None:
        raise ValueError("实验 id 已存在，请开始新实验。")

    tick = clock or time.monotonic
    started = tick()
    deadline = started + request.max_wall_seconds
    report = EvolutionReport(
        experiment_id=experiment_id,
        status="running",
        original_plan=request.plan.model_copy(deep=True),
        inputs={"plan_sha256": plan_fingerprint(request.plan)},
        outputs=[f"generated/evolution/experiments/{experiment_id}.json"],
    )
    save_report(report, workspace_root=workspace_root)

    def persist():
        report.elapsed_seconds = max(0.0, tick() - started)
        report.outputs = [
            f"generated/evolution/experiments/{experiment_id}.json",
            *sorted(
                {
                    item.report.project_dir
                    for item in report.iterations
                    if item.report and item.report.project_dir
                }
            ),
        ]
        if report.status != "running":
            report.next_actions = [
                "查看候选工程并人工试玩，确认有效后在质量面板采用。"
                if report.status == "improved"
                else "检查保留的测量与返工原因，纠偏后明确开始新实验。"
            ]
        save_report(report, workspace_root=workspace_root)

    def remaining():
        _cancel_check()
        value = deadline - tick()
        if value <= 0:
            raise EvolutionBudgetExceeded("实验总时间预算已耗尽。")
        return value

    try:
        remaining()
        measured = run_iteration or make_iteration_runner(
            workspace_root=workspace_root,
            confirmed=request.confirmed,
            clock=tick,
        )
        current_plan = request.plan.model_copy(deep=True)
        current_report = _measurement(
            measured(
                current_plan,
                f"{experiment_id}-0",
                remaining(),
            )
        )
        report.iterations.append(
            EvolutionIteration(
                index=0,
                session_id=f"{experiment_id}-0",
                plan=current_plan,
                report=current_report,
                eligible=not candidate_notes(current_report),
                notes=measurement_notes(current_report),
            )
        )
        persist()
        remaining()
        axis_mismatch = {sample.axis for sample in current_report.samples} != {
            axis_for_spec(request.plan.gameplay_spec)
        }
        if (
            axis_mismatch
            or measurement_notes(current_report)
            or any(
                sample.script_errors or sample.missing_actions for sample in current_report.samples
            )
        ):
            report.status = "manual_rework"
            report.notes = [
                *measurement_notes(current_report),
                "测量、脚本或输入问题需要人工返工。",
            ]
            if axis_mismatch:
                report.notes.append("试玩机制轴与当前计划不一致，停止返工。")
        else:
            best_report = current_report
            seen = {plan_fingerprint(current_plan)}
            for index in range(1, request.max_iterations + 1):
                remaining()
                suggestion = (
                    suggest_evolution(
                        current_plan,
                        workspace_root=(
                            experience_workspace_root
                            if experience_workspace_root is not None
                            else workspace_root
                        ),
                    )
                    if (request.use_experience and index == 1)
                    else None
                )
                changes = (suggestion.changes if suggestion else []) or propose_changes(
                    current_plan, current_report
                )
                if not changes:
                    report.notes.append(
                        "没有可验证的数值修改；未解决的路线、机制和体验问题需人工返工。"
                    )
                    report.status = (
                        "improved"
                        if report.best_iteration is not None
                        else (
                            "unchanged" if not candidate_notes(current_report) else "manual_rework"
                        )
                    )
                    break
                candidate = apply_changes(current_plan, changes)
                fingerprint = plan_fingerprint(candidate)
                if fingerprint in seen:
                    report.notes.append("候选与已经测试的版本相同，停止重复实验。")
                    break
                seen.add(fingerprint)
                session_id = f"{experiment_id}-{index}"
                candidate_report = _measurement(measured(candidate, session_id, remaining()))
                improved, notes = compare_reports(best_report, candidate_report)
                report.iterations.append(
                    EvolutionIteration(
                        index=index,
                        session_id=session_id,
                        plan=candidate,
                        report=candidate_report,
                        changes=changes,
                        eligible=not candidate_notes(candidate_report),
                        improved=improved,
                        notes=notes,
                    )
                )
                if improved:
                    best_report = candidate_report
                    report.best_iteration = index
                current_plan, current_report = candidate, candidate_report
                persist()
                remaining()
            if report.status == "running":
                report.status = "improved" if report.best_iteration is not None else "unchanged"
    except ProcessCancelled:
        report.status = "cancelled"
        report.notes.append("用户取消了实验；已有测量保留，不启动后续候选。")
    except EvolutionBudgetExceeded as exc:
        report.status = "budget_exhausted"
        report.notes.append(str(exc))
    except EvolutionLibraryError:
        raise  # A failed decision write cannot masquerade as a completed experiment.
    except Exception as exc:  # noqa: BLE001 - persist worker failure for the quality panel
        report.status = "failed"
        report.notes.append(f"实验未完成：{exc}")
    persist()
    return EvolutionJobResult(
        "cancelled"
        if report.status == "cancelled"
        else "failed"
        if report.status == "failed"
        else "done",
        report=report,
        planned_side_effects=effects,
    )


def _net_changes(report: EvolutionReport, winner: EvolutionIteration) -> list[NumericChange]:
    original = report.original_plan.production_spec_bundle.model_dump()
    candidate = winner.plan.production_spec_bundle.model_dump()
    changes = []
    for name in get_args(NumericField):
        before, after = original, candidate
        for segment in name.split("."):
            before, after = before[segment], after[segment]
        if not math.isclose(before, after, rel_tol=1e-9):
            changes.append(
                NumericChange(
                    field=name,
                    before=before,
                    after=after,
                    reason="经基线与候选试玩比较，并由用户采用。",
                )
            )
    return changes


def prepare_evolution_adoption(
    experiment_id: str,
    plan: DirectorBuildPlan,
    *,
    workspace_root: Path | str,
    feedback: str = "",
    experience_workspace_root: Path | str | None = None,
) -> tuple[DirectorBuildPlan, EvolutionExperience, EvolutionReport]:
    """Validate the stored winner and prepare its adoption without publishing it."""
    with _adoption_lock:
        report = load_report(experiment_id, workspace_root=workspace_root)
        if report is None:
            raise ValueError("实验不存在。")
        if report.status != "improved" or report.best_iteration is None:
            raise ValueError("该实验没有完成可采用的改进。")
        if plan_fingerprint(plan) != plan_fingerprint(report.original_plan):
            raise ValueError("当前计划已变化，请对当前计划重新实验。")
        baseline = next((item for item in report.iterations if item.index == 0), None)
        winner = next(
            (item for item in report.iterations if item.index == report.best_iteration), None
        )
        if baseline is None or winner is None or baseline.report is None or winner.report is None:
            raise ValueError("实验缺失真实测量。")
        if not compare_reports(baseline.report, winner.report)[0]:
            raise ValueError("固定检查未证明该候选改善。")
        changes = _net_changes(report, winner)
        if not changes:
            raise ValueError("候选没有可回写的数值变化。")
        updated = apply_changes(plan, changes)
        if plan_fingerprint(updated) != plan_fingerprint(winner.plan):
            raise ValueError("候选包含数值白名单之外的计划变化。")
        experience_id = f"experience-{experiment_id}"
        experience_root = (
            experience_workspace_root if experience_workspace_root is not None else workspace_root
        )
        existing = next(
            (
                item
                for item in list_experiences(workspace_root=experience_root)
                if item.id == experience_id
            ),
            None,
        )
        experience = existing or EvolutionExperience(
            id=experience_id,
            experiment_id=experiment_id,
            axis=axis_for_spec(plan.gameplay_spec),
            changes=changes,
            feedback=feedback,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        report.adopted_iteration = winner.index
        return updated, experience, report


def adopt_evolution(
    experiment_id: str,
    plan: DirectorBuildPlan,
    *,
    workspace_root: Path | str,
    feedback: str = "",
    experience_workspace_root: Path | str | None = None,
) -> tuple[DirectorBuildPlan, EvolutionExperience]:
    """Adopt the stored winner, never a score or approval supplied by a client."""
    with _adoption_lock:
        updated, experience, report = prepare_evolution_adoption(
            experiment_id,
            plan,
            workspace_root=workspace_root,
            feedback=feedback,
            experience_workspace_root=experience_workspace_root,
        )
        save_experience(
            experience,
            workspace_root=experience_workspace_root
            if experience_workspace_root is not None
            else workspace_root,
        )
        save_report(report, workspace_root=workspace_root)
        return updated, experience


def suggest_evolution(
    plan: DirectorBuildPlan, *, workspace_root: Path | str
) -> EvolutionSuggestion:
    _validate_plan(plan)
    for experience in reversed(list_experiences(workspace_root=workspace_root)):
        changes = changes_from_experience(plan, experience)
        if changes:
            return EvolutionSuggestion(
                apply_changes(plan, changes),
                changes,
                experience.id,
                ["该建议来自人工采用的实测经验；用于新任务时仍需重新验证。"],
            )
    return EvolutionSuggestion(
        plan.model_copy(deep=True), notes=["当前机制轴没有可应用的已采用经验。"]
    )
