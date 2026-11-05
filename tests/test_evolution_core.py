"""A feedback loop must earn improvement with measured, non-regressing play."""

from __future__ import annotations

import importlib

import pytest

from fantasy_agent.contracts import PlaytestReport, PlaytestSample, PromptRequest
from fantasy_agent.workflows import run_director_workflow


def _module(name):
    return importlib.import_module(f"fantasy_agent.evolution.{name}")


def _plan():
    return run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase across neon towers", engine_version="Godot 4")
    )


def _report(*, wins=0, taps=None, distance=80.0, axis="parkour", samples=3):
    return PlaytestReport(
        runs_requested=3,
        samples=[
            PlaytestSample(
                run_index=index,
                outcome="win" if index < wins else "fail",
                reason="" if index < wins else "Route timer expires before extraction",
                session_seconds=12.0,
                player_moved_distance=distance,
                playable=True,
                axis=axis,
                held=["sprint"],
                taps=taps if taps is not None else {"vault": 5, "slide": 2},
            )
            for index in range(samples)
        ],
    )


def test_a_candidate_earns_improvement_from_samples_instead_of_its_summary():
    evaluation = _module("evaluation")
    improved, _ = evaluation.compare_reports(_report(), _report(wins=2))
    assert improved
    invented = _report()
    invented.aggregate.wins = 3
    invented.aggregate.win_rate = 1.0
    improved, _ = evaluation.compare_reports(_report(), invented)
    assert not improved


def test_a_combat_candidate_with_measured_damage_and_stamina_can_be_promoted():
    taps = {"attack": 5, "evade": 2, "position": 1, "recover": 1}
    baseline = _report(axis="combat", taps=taps)
    candidate = _report(axis="combat", taps=taps, wins=3)
    for report in (baseline, candidate):
        for sample in report.samples:
            sample.enemy_hp_lost = 2
            sample.stamina_spent = 0.68
    improved, notes = _module("evaluation").compare_reports(baseline, candidate)
    assert improved, notes


@pytest.mark.parametrize(
    "candidate",
    [_report(samples=0), _report(samples=2, wins=2), _report(wins=3, axis=""),
     _report(wins=3, taps={}), _report(wins=3, distance=0.01)],
)
def test_missing_measurement_or_core_play_cannot_be_promoted(candidate):
    improved, notes = _module("evaluation").compare_reports(_report(), candidate)
    assert not improved
    assert notes


def test_script_errors_and_missing_input_actions_block_promotion():
    candidate = _report(wins=3)
    candidate.samples[0].script_errors = ["Parse Error"]
    assert not _module("evaluation").compare_reports(_report(), candidate)[0]
    candidate.samples[0].script_errors = []
    candidate.samples[1].missing_actions = ["slide"]
    assert not _module("evaluation").compare_reports(_report(), candidate)[0]


def test_same_results_do_not_claim_learning():
    assert not _module("evaluation").compare_reports(_report(wins=3), _report(wins=3))[0]


def test_changes_update_the_bundle_without_mutating_the_original_plan():
    contracts = _module("contracts")
    plan = _plan()
    plan.production_spec_bundle.numeric.player_move_speed = 8.0
    change = contracts.NumericChange(
        field="numeric.player_move_speed", before=8.0, after=9.0, reason="实测路线速度"
    )
    updated = _module("candidates").apply_changes(plan, [change])
    assert updated.production_spec_bundle.numeric.player_move_speed == 9.0
    assert plan.production_spec_bundle.numeric.player_move_speed == 8.0


def test_a_stale_change_and_an_out_of_bounds_change_are_rejected():
    contracts = _module("contracts")
    plan = _plan()
    change = contracts.NumericChange(
        field="numeric.player_move_speed", before=999.0, after=9.0, reason="陈旧建议"
    )
    with pytest.raises(ValueError):
        _module("candidates").apply_changes(plan, [change])
    change = contracts.NumericChange(
        field="numeric.player_move_speed",
        before=plan.production_spec_bundle.numeric.player_move_speed,
        after=100.0,
        reason="越界建议",
    )
    with pytest.raises(ValueError):
        _module("candidates").apply_changes(plan, [change])


def test_feedback_only_proposes_supported_numeric_fixes():
    candidates = _module("candidates")
    plan = _plan()
    changes = candidates.propose_changes(plan, _report())
    assert changes and changes[0].field == "numeric.pressure_clock_seconds"
    assert changes[0].after > changes[0].before
    broken = _report()
    broken.samples[0].script_errors = ["Parse Error"]
    assert candidates.propose_changes(plan, broken) == []


def test_an_experience_changes_the_current_value_proportionally():
    contracts = _module("contracts")
    plan = _plan()
    plan.production_spec_bundle.numeric.player_move_speed = 10.0
    experience = contracts.EvolutionExperience(
        id="lesson-1", experiment_id="experiment-1", axis="parkour",
        changes=[contracts.NumericChange(
            field="numeric.player_move_speed", before=8.0, after=9.0, reason="已复测"
        )],
    )
    changes = _module("candidates").changes_from_experience(plan, experience)
    updated = _module("candidates").apply_changes(plan, changes)
    assert updated.production_spec_bundle.numeric.player_move_speed == 11.25


def test_experience_from_a_different_axis_is_not_applied():
    contracts = _module("contracts")
    experience = contracts.EvolutionExperience(
        id="lesson-1", experiment_id="experiment-1", axis="combat", changes=[]
    )
    assert _module("candidates").changes_from_experience(_plan(), experience) == []


def test_reports_and_experiences_survive_a_reload(tmp_path):
    contracts = _module("contracts")
    library = _module("library")
    report = contracts.EvolutionReport(
        experiment_id="experiment-1", status="unchanged", original_plan=_plan()
    )
    library.save_report(report, workspace_root=tmp_path)
    assert library.load_report("experiment-1", workspace_root=tmp_path) == report
    experience = contracts.EvolutionExperience(
        id="lesson-1", experiment_id="experiment-1", axis="parkour", changes=[]
    )
    library.save_experience(experience, workspace_root=tmp_path)
    library.save_experience(experience, workspace_root=tmp_path)
    assert library.list_experiences(workspace_root=tmp_path) == [experience]


def test_corrupt_library_is_an_error_instead_of_an_empty_history(tmp_path):
    library = _module("library")
    contracts = _module("contracts")
    assert library.list_experiences(workspace_root=tmp_path) == []
    library.save_experience(contracts.EvolutionExperience(
        id="lesson-1", experiment_id="experiment-1", axis="parkour", changes=[]
    ), workspace_root=tmp_path)
    index = tmp_path / "generated/evolution/experiences.json"
    index.write_text("{broken", encoding="utf-8")
    with pytest.raises(library.EvolutionLibraryError):
        library.list_experiences(workspace_root=tmp_path)


def test_state_files_are_atomic_and_keep_the_old_record_when_replace_fails(tmp_path, monkeypatch):
    contracts = _module("contracts")
    library = _module("library")
    report = contracts.EvolutionReport(
        experiment_id="experiment-1", status="unchanged", original_plan=_plan()
    )
    library.save_report(report, workspace_root=tmp_path)
    from fantasy_agent import atomic_write

    def fail_replace(*_):
        raise OSError("disk unavailable")

    monkeypatch.setattr(atomic_write.os, "replace", fail_replace)
    report.status = "failed"
    with pytest.raises(library.EvolutionLibraryError):
        library.save_report(report, workspace_root=tmp_path)
    assert library.load_report("experiment-1", workspace_root=tmp_path).status == "unchanged"


def test_report_ids_cannot_escape_or_alias_a_windows_directory(tmp_path):
    library = _module("library")
    for experiment_id in ("../outside", "victim.", "victim "):
        with pytest.raises(ValueError):
            library.load_report(experiment_id, workspace_root=tmp_path)


def test_experiments_cannot_smuggle_an_approval_or_exceed_the_candidate_budget():
    from pydantic import ValidationError

    contracts = _module("contracts")
    with pytest.raises(ValidationError):
        contracts.EvolutionRequest(plan=_plan(), max_iterations=4)
    with pytest.raises(ValidationError):
        contracts.EvolutionExperience(
            id="lesson-1", experiment_id="experiment-1", axis="parkour",
            changes=[], confirmed=True,
        )
