"""Headless playtest: measurement, verdict and rework translation.

None of these tests launch Godot. The engine is the slowest thing in the repo,
so what gets pinned here is everything around it: how runs are aggregated, how
a verdict becomes a rework target, and above all that a report nobody ran is
never dressed up as one somebody did.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from fantasy_agent.contracts import (
    PlaytestReport,
    PlaytestRequest,
    PlaytestSample,
    PromptRequest,
)
from fantasy_agent.godot_playtest import (
    MIN_PLAYER_MOVE_METERS,
    aggregate_samples,
    build_findings,
    planned_playtest_side_effects,
    render_probe_script,
    summarize_playtest,
)
from fantasy_agent.path_safety import WorkspacePathError
from fantasy_agent.pipeline_state import REWORK_TARGET_STAGES
from fantasy_agent.unreal_spec_adapter import evaluate_executable_qa
from fantasy_agent.workflows import run_director_workflow


def _load_studio_app():
    module_path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample(**overrides: object) -> PlaytestSample:
    payload: dict[str, object] = {
        "run_index": 0,
        "outcome": "fail",
        "reason": "Route timer expires before the extraction gate",
        "session_seconds": 8.0,
        "player_moved_distance": 24.0,
        "playable": True,
    }
    payload.update(overrides)
    return PlaytestSample.model_validate(payload)


def _report(samples: list[PlaytestSample]) -> PlaytestReport:
    aggregate = aggregate_samples(samples)
    report = PlaytestReport(samples=samples, aggregate=aggregate)
    report.findings = build_findings(samples, aggregate)
    return report


def test_aggregate_reports_a_distribution_not_a_point():
    samples = [
        _sample(run_index=0, session_seconds=1.0),
        _sample(run_index=1, session_seconds=2.0),
        _sample(run_index=2, session_seconds=10.0),
    ]
    aggregate = aggregate_samples(samples)

    assert aggregate.runs == 3
    assert aggregate.session_seconds_p50 == 2.0
    # Interpolated between the last two samples, not rounded to one of them.
    assert 9.0 < aggregate.session_seconds_p95 < 10.0


def test_degraded_runs_block_and_name_a_rework_target():
    degraded = _sample(degraded=True, degraded_reason="no node in the player group", playable=False)
    report = _report([degraded, degraded])

    blocking = [f for f in report.findings if f.severity == "blocking"]
    assert blocking, "a run the probe could not observe has to block"
    assert blocking[0].rework_target == "godot_plan"
    # The console reuses one resume control, so the stage has to be real.
    assert blocking[0].resume_stage in set(REWORK_TARGET_STAGES.values())


def test_every_timeout_warns_that_the_loop_never_resolved():
    report = _report([_sample(outcome="timeout", playable=False, session_seconds=0.0)])

    assert any(f.code == "never_ended" for f in report.findings)
    assert not any(f.code == "no_win_path" for f in report.findings), (
        "a run that never ended did not lose; saying so would misreport why"
    )


def test_failures_without_a_win_warn_about_the_win_path():
    report = _report([_sample(outcome="fail"), _sample(run_index=1, outcome="fail")])

    assert any(f.code == "no_win_path" for f in report.findings)


def test_script_errors_block_the_verdict():
    sample = _sample(script_errors=["SCRIPT ERROR: Parse Error: bad indent"])
    report = _report([sample])

    error_findings = [f for f in report.findings if f.code == "script_error"]
    assert error_findings
    assert error_findings[0].severity == "blocking"


def test_a_stuck_player_blocks_even_when_the_loop_ends():
    stuck = _sample(player_moved_distance=MIN_PLAYER_MOVE_METERS / 2, playable=False)
    report = _report([stuck])

    assert any(f.code == "player_stuck" for f in report.findings)


def test_probe_script_bakes_its_budget_in():
    script = render_probe_script(
        runs=3, max_frames=1200, input_plan="forward_and_jump", out_file="C:/tmp/out.json"
    )

    assert "const MAX_RUNS := 3" in script
    assert "const MAX_FRAMES := 1200" in script
    assert 'const INPUT_PLAN := "forward_and_jump"' in script
    assert "__RUNS__" not in script


def test_missing_engine_blocks_before_anything_launches(tmp_path):
    from unittest import mock

    from fantasy_agent import godot_playtest

    with mock.patch.object(godot_playtest, "_find_godot", return_value=None):
        report = godot_playtest.run_playtest(
            PlaytestRequest(project_dir=str(tmp_path)),
            workspace_root=tmp_path,
        )

    assert report.status == "failed"
    assert [f.code for f in report.findings] == ["engine_missing"]
    assert not (tmp_path / "generated" / "playtest").exists(), (
        "no engine means no probe, no report, nothing written"
    )


def test_a_project_without_project_godot_is_refused(tmp_path):
    from fantasy_agent import godot_playtest

    report = godot_playtest.run_playtest(
        PlaytestRequest(project_dir=str(tmp_path), godot_executable="godot"),
        workspace_root=tmp_path,
    )

    assert report.status == "failed"
    assert report.findings[0].code == "project_missing"


def test_static_qa_stays_silent_when_nobody_ran_the_prototype():
    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena with guards", engine_version="UE5")
    )
    bundle = plan.production_spec_bundle
    assert bundle is not None

    report = evaluate_executable_qa(bundle)

    assert not [r for r in report.results if r.metric_key.startswith("playtest_")], (
        "an untested prototype must not collect playtest assertions"
    )


def test_measured_run_feeds_the_qa_assertions():
    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena with guards", engine_version="UE5")
    )
    bundle = plan.production_spec_bundle
    assert bundle is not None
    measured = _report([_sample(outcome="win"), _sample(run_index=1)])

    report = evaluate_executable_qa(bundle, measured)

    by_key = {result.metric_key: result for result in report.results}
    assert by_key["playtest_runs"].actual == 2
    assert by_key["playtest_playable_rate"].actual == 1.0
    assert by_key["playtest_decided_runs"].actual == 2
    assert by_key["playtest_script_errors"].actual == []


def test_a_run_with_script_errors_fails_the_qa_verdict():
    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena with guards", engine_version="UE5")
    )
    bundle = plan.production_spec_bundle
    assert bundle is not None
    measured = _report([_sample(script_errors=["SCRIPT ERROR: boom"])])

    report = evaluate_executable_qa(bundle, measured)

    assert report.status == "failed"


def test_side_effects_are_declared_before_the_run():
    effects = planned_playtest_side_effects(PlaytestRequest(project_dir="generated/godot/x"))

    assert effects
    assert any("Godot" in effect for effect in effects)


def test_summary_states_the_lower_bound_out_loud():
    report = _report([_sample()])
    report.goal_notes = ["lower bound"]

    text = summarize_playtest(report)

    assert "lower bound" in text
    assert str(report.aggregate.runs) in text


def test_a_median_below_the_floor_is_reported_as_short():
    report = _report(
        [_sample(session_seconds=1.0), _sample(run_index=1, session_seconds=1.5)]
    )

    assert any(f.code == "session_too_short" for f in report.findings)


def test_a_session_id_cannot_walk_out_of_the_workspace(tmp_path):
    from fantasy_agent import godot_playtest

    for escaped in ("..", "../evil", ".", "a/b", "a\\b", "C:/Windows", "C:\\Windows"):
        with pytest.raises(WorkspacePathError):
            godot_playtest.playtest_artifact_paths(tmp_path, escaped)

    paths = godot_playtest.playtest_artifact_paths(tmp_path, "20261002_160815")
    assert paths["dir"] == tmp_path / "generated" / "playtest" / "20261002_160815"


def test_the_endpoint_model_cannot_restate_the_contract():
    """The wire model inherits the library contract, so bounds have one home.

    A copy would drift, and a drifted bound is the kind of bug that only shows
    up as a 500 from inside a job: the edge validated a number the library
    then refused.
    """

    module = _load_studio_app()

    assert issubclass(module.PlaytestRunRequest, PlaytestRequest)
    for name in ("runs", "max_frames", "max_wall_seconds", "project_dir"):
        assert (
            module.PlaytestRunRequest.model_fields[name].metadata
            == PlaytestRequest.model_fields[name].metadata
        )
    with pytest.raises(ValidationError):
        module.PlaytestRunRequest(project_dir="generated/godot/x", runs=0)
    with pytest.raises(ValidationError):
        module.PlaytestRunRequest(project_dir="generated/godot/x", input_plan="banana")


def test_the_endpoint_previews_without_launching_an_engine(monkeypatch):
    from fantasy_agent import godot_playtest

    module = _load_studio_app()

    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("a preview must not launch an engine")

    monkeypatch.setattr(godot_playtest, "run_playtest", explode)

    payload = module.run_playtest_job(
        module.PlaytestRunRequest(project_dir="generated/godot/whatever")
    )

    assert payload["status"] == "confirmation_required"
    assert payload["planned_side_effects"], (
        "the two-step gate has to say what confirming would do"
    )
    assert "report" not in payload


def test_unknown_playtest_jobs_answer_unknown():
    module = _load_studio_app()
    routes = {route.path for route in module.app.routes}

    assert "/api/playtest/run" in routes
    assert "/api/playtest/{job_id}" in routes
    assert "/api/playtest/{job_id}/cancel" in routes
    assert module.playtest_status("nope") == {"status": "unknown", "job_id": "nope"}
    assert module.playtest_cancel("nope") == {"status": "unknown", "job_id": "nope"}


def test_done_is_a_job_status_not_a_verdict():
    """A run that measured a failure still finished.

    ``ok`` has to agree with ``executor.ExecutionResult``: the poller reads
    job vocabulary, and the verdict lives in ``report.status``.
    """

    from fantasy_agent.godot_playtest import PlaytestResult

    assert PlaytestResult(status="done").ok is True
    assert PlaytestResult(status="confirmation_required").ok is False
    assert PlaytestResult(status="failed").ok is False
