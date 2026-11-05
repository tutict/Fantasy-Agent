"""The real executor path clips import and playtest without launching an engine."""

import json
import subprocess

import pytest

from fantasy_agent.evolution import runtime
from fantasy_agent.evolution.contracts import EvolutionReport
from fantasy_agent.evolution.library import EvolutionLibraryError, load_report, save_report
from tests.test_evolution_controller import _plan


def test_every_engine_process_receives_only_the_remaining_experiment_budget(tmp_path, monkeypatch):
    now = [0.0]
    launches = []
    monkeypatch.setattr(runtime.local_tools, "_find_godot", lambda: "fake-godot")

    def process(command, **kwargs):
        launches.append((command, kwargs["timeout"]))
        if "--import" in command:
            now[0] += 2
            return subprocess.CompletedProcess(command, 0, "import ok", "")
        now[0] += 3
        payload = {"runs": [{
            "run_index": i, "outcome": "win", "session_seconds": 12,
            "player_moved_distance": 80, "playable": True, "axis": "parkour",
            "held": ["sprint"], "taps": {"vault": 5, "slide": 2},
        } for i in range(5)]}
        return subprocess.CompletedProcess(command, 0, "PLAYTEST-RESULT " + json.dumps(payload), "")

    monkeypatch.setattr(runtime.process_runner, "run_streaming", process)
    measured = runtime.make_iteration_runner(workspace_root=tmp_path, confirmed=True, clock=lambda: now[0])
    report = measured(_plan(), "runtime-budget", 20)
    assert len(launches) == 2
    assert launches[0][1] == 20
    assert launches[1][1] == 18
    assert report.runs_requested == 5
    assert len(report.samples) == 5
    assert (tmp_path / "generated/godot/sessions/runtime-budget").is_dir()


def test_the_runtime_itself_also_refuses_an_unconfirmed_experiment(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime.local_tools, "_find_godot", lambda: pytest.fail("unconfirmed discovery"))
    with pytest.raises(ValueError, match="确认"):
        runtime.make_iteration_runner(workspace_root=tmp_path, confirmed=False)
    assert not (tmp_path / "generated").exists()


def test_a_report_cannot_be_restored_under_a_different_record_id(tmp_path):
    report = EvolutionReport(experiment_id="real-id", status="unchanged", original_plan=_plan())
    save_report(report, workspace_root=tmp_path)
    original = tmp_path / "generated/evolution/experiments/real-id.json"
    other = original.with_name("other-id.json")
    other.write_bytes(original.read_bytes())
    with pytest.raises(EvolutionLibraryError, match="id"):
        load_report("other-id", workspace_root=tmp_path)
