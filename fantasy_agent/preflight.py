"""Pre-flight gate for the execution pipeline.

Expensive nodes (ComfyUI, Blender, Godot headless import, Unreal
DataValidation) cost minutes each. When a plan is already known to be broken,
running those nodes burns that time and only surfaces the failure at the very
end -- which is exactly the waste this module exists to prevent.

Two severity levels, and the distinction is the whole design:

- blocking: the downstream node cannot produce anything meaningful from this
  plan. Stop *before* the expensive node and name the node to return to.
- warning: the run can still produce something useful (a degraded greybox, a
  demo without visual references). Report it and continue.

The warning tier is what keeps the existing guarantee intact: a missing tool
still degrades instead of failing, while genuine design defects are no longer
deferred to the end of the chain.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from fantasy_agent.contracts import DirectorBuildPlan, StrictModel

BLOCKING = "blocking"
WARNING = "warning"

# Where a human should go to fix an issue. These are node names the console
# and CLI can surface directly, so a failure tells you where to return to.
REWORK_PROMPT = "prompt"  # the original idea is too thin; rewrite it
REWORK_SPEC = "spec"  # the gameplay spec has a hole
REWORK_PLAN = "godot_plan"  # the engine handoff plan is malformed
REWORK_FLAGS = "flags"  # the plan is fine, the run switches are wrong


class PreflightIssue(StrictModel):
    """One problem found before an expensive node runs."""

    code: str
    severity: Literal["blocking", "warning"]
    field: str
    message: str
    rework_target: str


class PreflightReport(StrictModel):
    """Result of the pre-flight gate."""

    source: str = "fantasy-agent.preflight"
    schema_version: str = "0.1"
    engine: str = ""
    status: Literal["passed", "warning", "blocked"] = "passed"
    issues: list[PreflightIssue] = Field(default_factory=list)

    @property
    def blocking_issues(self) -> list[PreflightIssue]:
        return [issue for issue in self.issues if issue.severity == BLOCKING]

    @property
    def warning_issues(self) -> list[PreflightIssue]:
        return [issue for issue in self.issues if issue.severity == WARNING]

    @property
    def blocked(self) -> bool:
        return bool(self.blocking_issues)

    def summary(self) -> str:
        """Human-readable one-liner for a StageResult detail."""

        if not self.issues:
            return "preflight 通过，无阻断性问题"
        return "; ".join(
            f"[{issue.severity}] {issue.field}: {issue.message}（回到 {issue.rework_target}）"
            for issue in self.issues
        )


def preflight_plan(
    plan: DirectorBuildPlan,
    *,
    engine: str = "",
    with_assets: bool = False,
    with_visuals: bool = False,
    with_gameplay: bool = False,
) -> PreflightReport:
    """Check a build plan before any expensive node runs.

    Args:
        plan: The director build plan about to be executed.
        engine: Engine label recorded on the report for traceability.
        with_assets: Whether the Blender stage will run.
        with_visuals: Whether the ComfyUI stage will run.
        with_gameplay: Whether gameplay codegen will run.

    Returns:
        A report whose ``blocked`` flag tells the caller to stop, and whose
        issues each name the node to return to.
    """

    issues: list[PreflightIssue] = []
    spec = plan.gameplay_spec

    # --- Blocking: the run cannot produce anything meaningful -------------

    # The Godot route is generated from level_beats; with none, the level is an
    # empty floor and every downstream node is wasted time.
    if not spec.level_beats:
        issues.append(
            PreflightIssue(
                code="missing_level_beats",
                severity=BLOCKING,
                field="gameplay_spec.level_beats",
                message="玩法没有 level_beats，关卡路线无处生成",
                rework_target=REWORK_SPEC,
            )
        )

    if not spec.win_state.strip():
        issues.append(
            PreflightIssue(
                code="missing_win_state",
                severity=BLOCKING,
                field="gameplay_spec.win_state",
                message="没有胜利条件，demo 无法判定通关",
                rework_target=REWORK_SPEC,
            )
        )

    # AGENTS.md: failure states must teach the player what to try next.
    if not spec.failure_states:
        issues.append(
            PreflightIssue(
                code="missing_failure_states",
                severity=BLOCKING,
                field="gameplay_spec.failure_states",
                message="没有失败状态，玩家无法理解下一次尝试",
                rework_target=REWORK_SPEC,
            )
        )

    godot_plan = getattr(plan, "godot_plan", None)
    if godot_plan is not None and not str(godot_plan.project_name).strip():
        issues.append(
            PreflightIssue(
                code="empty_project_name",
                severity=BLOCKING,
                field="godot_plan.project_name",
                message="工程名为空，产物无处落地",
                rework_target=REWORK_PLAN,
            )
        )

    # --- Warnings: degraded but still worth running -----------------------

    if spec.asset_needs and not with_assets:
        issues.append(
            PreflightIssue(
                code="assets_declared_not_enabled",
                severity=WARNING,
                field="gameplay_spec.asset_needs",
                message=(
                    f"声明了 {len(spec.asset_needs)} 项资产需求但未启用 Blender，"
                    "将退化为纯灰盒"
                ),
                rework_target=REWORK_FLAGS,
            )
        )

    if with_assets and not spec.notes_for_blender:
        issues.append(
            PreflightIssue(
                code="blender_without_notes",
                severity=WARNING,
                field="gameplay_spec.notes_for_blender",
                message="启用了 Blender 但没有 notes_for_blender，导出缺乏可玩性约束",
                rework_target=REWORK_SPEC,
            )
        )

    if with_visuals and not spec.notes_for_comfyui:
        issues.append(
            PreflightIssue(
                code="comfyui_without_notes",
                severity=WARNING,
                field="gameplay_spec.notes_for_comfyui",
                message="启用了 ComfyUI 但没有 notes_for_comfyui，参考图缺乏美术方向",
                rework_target=REWORK_SPEC,
            )
        )

    if spec.enemies and not with_gameplay:
        issues.append(
            PreflightIssue(
                code="enemies_declared_not_generated",
                severity=WARNING,
                field="gameplay_spec.enemies",
                message=(
                    f"声明了 {len(spec.enemies)} 个敌人但未启用玩法代码生成，"
                    "敌人不会出现在灰盒中"
                ),
                rework_target=REWORK_FLAGS,
            )
        )

    if not spec.core_verbs:
        issues.append(
            PreflightIssue(
                code="missing_core_verbs",
                severity=WARNING,
                field="gameplay_spec.core_verbs",
                message="没有核心动词，玩家操作无法定义",
                rework_target=REWORK_PROMPT,
            )
        )

    if issues and not any(issue.severity == BLOCKING for issue in issues):
        status = "warning"
    elif any(issue.severity == BLOCKING for issue in issues):
        status = "blocked"
    else:
        status = "passed"

    return PreflightReport(engine=engine, status=status, issues=issues)
