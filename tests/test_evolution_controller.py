"""Experiments only act under a bounded human grant and measured improvement."""

import importlib
import threading

import pytest

from fantasy_agent.contracts import PlaytestReport, PlaytestSample, PromptRequest
from fantasy_agent.evolution.contracts import EvolutionRequest
from fantasy_agent.evolution.library import list_experiences, load_report
from fantasy_agent.process_runner import cancel_scope
from fantasy_agent.workflows import run_director_workflow


def _controller():
    return importlib.import_module("fantasy_agent.evolution.controller")


def _plan():
    return run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase across neon towers", engine_version="Godot 4"),
        use_llm=False,
    )


def _report(wins=0):
    return PlaytestReport(
        runs_requested=3,
        samples=[PlaytestSample(
            run_index=i, outcome="win" if i < wins else "fail",
            reason="" if i < wins else "Route timer expires before extraction",
            session_seconds=12, player_moved_distance=80, playable=True,
            axis="parkour", held=["sprint"], taps={"vault": 5, "slide": 2},
        ) for i in range(3)],
    )


def test_preview_cannot_write_or_execute_even_with_an_injected_runner(tmp_path):
    def forbidden(*_):
        pytest.fail("unconfirmed experiment executed")

    result = _controller().run_evolution(
        EvolutionRequest(plan=_plan()), experiment_id="preview", workspace_root=tmp_path,
        run_iteration=forbidden,
    )
    assert result.status == "confirmation_required"
    assert result.planned_side_effects
    assert not (tmp_path / "generated").exists()


def test_candidates_have_distinct_sessions_and_do_not_activate_themselves(tmp_path):
    calls = []

    def measured(plan, session_id, remaining):
        calls.append((plan.production_spec_bundle.numeric.pressure_clock_seconds, session_id, remaining))
        return _report(0 if len(calls) == 1 else 3)

    result = _controller().run_evolution(
        EvolutionRequest(plan=_plan(), confirmed=True), experiment_id="bounded",
        workspace_root=tmp_path, run_iteration=measured,
    )
    assert len(calls) == 2
    assert calls[1][0] > calls[0][0]
    assert calls[0][1] != calls[1][1]
    assert 0 < calls[1][2] <= calls[0][2] <= 600
    assert result.report.status == "improved"
    assert result.report.best_iteration == 1
    assert result.report.iterations[1].report.aggregate.wins == 3
    assert result.report.adopted_iteration is None
    assert list_experiences(workspace_root=tmp_path) == []
    assert load_report("bounded", workspace_root=tmp_path).status == "improved"


def test_no_more_candidates_start_after_the_total_wall_budget(tmp_path):
    now = [100.0]
    calls = []

    def measured(*args):
        calls.append(args)
        now[0] += 31
        return _report()

    result = _controller().run_evolution(
        EvolutionRequest(plan=_plan(), confirmed=True, max_wall_seconds=30),
        experiment_id="deadline", workspace_root=tmp_path,
        run_iteration=measured, clock=lambda: now[0],
    )
    assert len(calls) == 1
    assert result.report.status == "budget_exhausted"
    assert load_report("deadline", workspace_root=tmp_path).status == "budget_exhausted"


def test_cancel_stops_new_work_and_keeps_the_last_measurement(tmp_path):
    cancel = threading.Event()
    calls = []

    def measured(*args):
        calls.append(args)
        cancel.set()
        return _report()

    with cancel_scope(cancel):
        result = _controller().run_evolution(
            EvolutionRequest(plan=_plan(), confirmed=True), experiment_id="cancelled",
            workspace_root=tmp_path, run_iteration=measured,
        )
    assert len(calls) == 1
    assert result.report.status == "cancelled"
    assert len(load_report("cancelled", workspace_root=tmp_path).iterations) == 1


def test_a_broken_script_requests_manual_rework_instead_of_numeric_retries(tmp_path):
    calls = []

    def measured(*args):
        calls.append(args)
        report = _report()
        report.samples[0].script_errors = ["Parse Error"]
        return report

    result = _controller().run_evolution(
        EvolutionRequest(plan=_plan(), confirmed=True), experiment_id="script",
        workspace_root=tmp_path, run_iteration=measured,
    )
    assert len(calls) == 1
    assert result.report.status == "manual_rework"
    assert result.report.notes


def test_adoption_verifies_the_server_record_and_then_records_reusable_experience(tmp_path):
    calls = []

    def measured(*args):
        calls.append(args)
        return _report(0 if len(calls) == 1 else 3)

    plan = _plan()
    _controller().run_evolution(
        EvolutionRequest(plan=plan, confirmed=True), experiment_id="adopt",
        workspace_root=tmp_path, run_iteration=measured,
    )
    updated, experience = _controller().adopt_evolution(
        "adopt", plan, feedback="人工试玩目标更清楚", workspace_root=tmp_path,
    )
    assert updated.production_spec_bundle.numeric.pressure_clock_seconds > plan.production_spec_bundle.numeric.pressure_clock_seconds
    assert experience.feedback == "人工试玩目标更清楚"
    assert len(list_experiences(workspace_root=tmp_path)) == 1
    suggestion = _controller().suggest_evolution(plan, workspace_root=tmp_path)
    assert suggestion.experience_id == experience.id
    assert suggestion.plan.production_spec_bundle.numeric.pressure_clock_seconds == updated.production_spec_bundle.numeric.pressure_clock_seconds
    assert not hasattr(experience, "confirmed")


def test_changed_plan_cannot_adopt_an_old_experiment(tmp_path):
    calls = []

    def measured(*args):
        calls.append(args)
        return _report(0 if len(calls) == 1 else 3)

    plan = _plan()
    _controller().run_evolution(
        EvolutionRequest(plan=plan, confirmed=True), experiment_id="stale",
        workspace_root=tmp_path, run_iteration=measured,
    )
    plan.gameplay_spec.title = "new idea"
    with pytest.raises(ValueError, match="计划"):
        _controller().adopt_evolution("stale", plan, workspace_root=tmp_path)
    assert list_experiences(workspace_root=tmp_path) == []


def test_unsupported_engine_is_rejected_before_any_record_or_execution(tmp_path):
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase across neon towers", engine_version="UE5"),
        use_llm=False,
    )
    with pytest.raises(ValueError, match="Godot"):
        _controller().run_evolution(
            EvolutionRequest(plan=plan, confirmed=True), experiment_id="wrong-engine",
            workspace_root=tmp_path, run_iteration=lambda *_: _report(3),
        )
    assert not (tmp_path / "generated").exists()


def test_a_report_for_another_mechanic_axis_cannot_drive_retries(tmp_path):
    calls = []

    def measured(*args):
        calls.append(args)
        report = _report()
        for sample in report.samples:
            sample.axis = "combat"
        return report

    result = _controller().run_evolution(
        EvolutionRequest(plan=_plan(), confirmed=True), experiment_id="wrong-axis",
        workspace_root=tmp_path, run_iteration=measured,
    )
    assert len(calls) == 1
    assert result.report.status == "manual_rework"


def test_a_stored_score_without_measured_improvement_cannot_be_adopted(tmp_path):
    from fantasy_agent.evolution.candidates import apply_changes, propose_changes
    from fantasy_agent.evolution.contracts import EvolutionIteration, EvolutionReport
    from fantasy_agent.evolution.library import save_report

    plan = _plan()
    changes = propose_changes(plan, _report())
    candidate = apply_changes(plan, changes)
    save_report(EvolutionReport(
        experiment_id="invented-score", status="improved", original_plan=plan, best_iteration=1,
        iterations=[
            EvolutionIteration(index=0, session_id="base", plan=plan, report=_report()),
            EvolutionIteration(index=1, session_id="candidate", plan=candidate,
                               report=_report(), changes=changes, eligible=True, improved=True),
        ],
    ), workspace_root=tmp_path)
    with pytest.raises(ValueError, match="检查"):
        _controller().adopt_evolution("invented-score", plan, workspace_root=tmp_path)
    assert list_experiences(workspace_root=tmp_path) == []
