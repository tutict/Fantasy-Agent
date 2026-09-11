"""Tests for the pre-flight gate.

The point of these tests is not that the checks exist, but that a blocked plan
never reaches the expensive nodes. Blender and ComfyUI cost minutes; a plan
that fails pre-flight must not spend them.
"""

from __future__ import annotations

import pytest

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.executor import execute_asset_pipeline, execute_godot_demo
from fantasy_agent.pipeline_state import GODOT_STAGE_ORDER
from fantasy_agent.preflight import BLOCKING, WARNING, preflight_plan
from fantasy_agent.workflows import run_director_workflow


def _plan():
    """A realistic plan straight from the deterministic workflow."""

    return run_director_workflow(
        PromptRequest(prompt="跑酷 demo，屋顶追逐并避开巡逻守卫，抵达撤离点")
    )


def _plan_with_spec(**spec_updates):
    plan = _plan()
    spec = plan.gameplay_spec.model_copy(update=spec_updates)
    return plan.model_copy(update={"gameplay_spec": spec})


def test_realistic_plan_only_warns():
    """A plan from the real workflow must never be blocked."""

    report = preflight_plan(_plan(), engine="Godot 4")

    assert not report.blocked
    assert report.status in ("passed", "warning")


def test_missing_level_beats_is_blocking():
    report = preflight_plan(_plan_with_spec(level_beats=[]), engine="Godot 4")

    assert report.blocked
    issue = next(i for i in report.blocking_issues if i.code == "missing_level_beats")
    assert issue.severity == BLOCKING
    # The report must name the node to return to, not just complain.
    assert issue.rework_target == "spec"


def test_missing_win_state_is_blocking():
    report = preflight_plan(_plan_with_spec(win_state="   "), engine="Godot 4")

    assert report.blocked
    assert any(i.code == "missing_win_state" for i in report.blocking_issues)


def test_missing_failure_states_is_blocking():
    report = preflight_plan(_plan_with_spec(failure_states=[]), engine="Godot 4")

    assert report.blocked
    assert any(i.code == "missing_failure_states" for i in report.blocking_issues)


def test_empty_project_name_is_blocking():
    plan = _plan()
    godot_plan = plan.godot_plan.model_copy(update={"project_name": "  "})
    plan = plan.model_copy(update={"godot_plan": godot_plan})

    report = preflight_plan(plan, engine="Godot 4")

    assert report.blocked
    assert any(i.code == "empty_project_name" for i in report.blocking_issues)


def test_declared_assets_without_blender_only_warns():
    """A missing tool degrades; it does not stop the run."""

    report = preflight_plan(_plan(), engine="Godot 4", with_assets=False)

    assert not report.blocked
    issue = next(
        i for i in report.warning_issues if i.code == "assets_declared_not_enabled"
    )
    assert issue.severity == WARNING
    assert issue.rework_target == "flags"


def test_summary_names_the_rework_target():
    report = preflight_plan(_plan_with_spec(level_beats=[]), engine="Godot 4")

    assert "spec" in report.summary()
    assert "level_beats" in report.summary()


def test_godot_demo_stops_before_expensive_nodes(tmp_path):
    """Blocking issues must stop the run before Blender ever starts."""

    plan = _plan_with_spec(level_beats=[])

    result = execute_godot_demo(
        plan,
        session_id="pf-godot",
        confirmed=True,
        with_assets=True,
        with_visuals=True,
        workspace_root=tmp_path,
    )

    assert result.status == "failed"
    names = [s.name for s in result.stages]
    assert names == ["preflight"]
    assert "level_beats" in result.stages[0].detail


def test_asset_pipeline_stops_before_workers(tmp_path):
    """The asset pipeline had no spec gate at all; now it has one."""

    plan = _plan_with_spec(failure_states=[])

    result = execute_asset_pipeline(
        plan,
        session_id="pf-assets",
        confirmed=True,
        with_assets=True,
        with_visuals=True,
        workspace_root=tmp_path,
    )

    assert result.status == "failed"
    names = [s.name for s in result.stages]
    assert names == ["preflight"]
    assert "failure_states" in result.stages[0].detail


def test_warnings_do_not_stop_the_run(tmp_path):
    """A degraded toolchain still produces a demo."""

    plan = _plan()

    result = execute_asset_pipeline(
        plan,
        session_id="pf-warn",
        confirmed=True,
        with_assets=False,
        with_visuals=False,
        workspace_root=tmp_path,
    )

    assert result.status != "failed" or "preflight" not in [
        s.name for s in result.stages if s.status == "failed"
    ]
    gate = next((s for s in result.stages if s.name == "preflight"), None)
    assert gate is not None and gate.status == "done"


def test_unreal_demo_stops_before_the_editor_launches(tmp_path):
    """DataValidation boots a full editor; a broken plan must not get there."""

    from fantasy_agent.executor import execute_unreal_demo

    plan = _plan_with_spec(level_beats=[])

    result = execute_unreal_demo(
        plan,
        session_id="pf-unreal",
        confirmed=True,
        workspace_root=tmp_path,
    )

    assert result.status == "failed"
    assert [s.name for s in result.stages] == ["preflight"]
    assert "level_beats" in result.stages[0].detail


@pytest.mark.parametrize(
    "field",
    ["level_beats", "failure_states"],
)
def test_every_blocking_issue_has_a_rework_target(field):
    report = preflight_plan(_plan_with_spec(**{field: []}), engine="Godot 4")

    assert report.blocked
    for issue in report.blocking_issues:
        assert issue.rework_target, "blocking issues must say where to return to"


@pytest.mark.parametrize(
    ("field", "empty_value"),
    [("level_beats", []), ("win_state", ""), ("failure_states", [])],
)
def test_every_blocking_issue_names_a_real_resume_stage(field, empty_value):
    """A hint is only actionable if it names a stage the runner accepts.

    `rework_target` says *what* to fix; without `resume_stage` the user has to
    guess which execution node that corresponds to.
    """

    report = preflight_plan(_plan_with_spec(**{field: empty_value}), engine="Godot 4")

    assert report.blocked
    for issue in report.blocking_issues:
        assert issue.resume_stage, f"{issue.code} gives no stage to resume from"
        assert issue.resume_stage in GODOT_STAGE_ORDER


def test_resume_stage_reaches_the_api_payload():
    """The console reads issue.resume_stage from JSON; a plain property would
    not survive `model_dump` and the button would silently lose its target."""

    report = preflight_plan(_plan_with_spec(level_beats=[]), engine="Godot 4")

    payload = report.model_dump(mode="json")
    assert payload["issues"][0]["resume_stage"]


def test_summary_names_the_stage_not_just_the_target():
    report = preflight_plan(_plan_with_spec(level_beats=[]), engine="Godot 4")

    summary = report.summary()
    assert "spec" in summary
    assert "comfyui" in summary, "summary must tell the user where to resume"


def test_flags_issues_map_to_the_stage_their_switch_gates():
    """`flags` covers two unrelated switches; one blanket answer would either
    waste a node or skip the one that needed to run."""

    report = preflight_plan(_plan(), engine="Godot 4", with_assets=False)

    assets_issue = next(
        i for i in report.issues if i.code == "assets_declared_not_enabled"
    )
    assert assets_issue.resume_stage == "blender"

    report2 = preflight_plan(_plan(), engine="Godot 4", with_gameplay=False)
    enemy_issue = next(
        i for i in report2.issues if i.code == "enemies_declared_not_generated"
    )
    assert enemy_issue.resume_stage == "gameplay"
