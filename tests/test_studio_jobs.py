"""Tests for the Studio job registry, especially cooperative cancellation."""

from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from fantasy_agent import process_runner
from fantasy_agent.studio_jobs import InMemoryJobRegistry


@dataclass
class _Result:
    status: str


_SLOW_SCRIPT = (
    "import time\n"
    "for i in range(200):\n"
    "    print(i, flush=True)\n"
    "    time.sleep(0.5)\n"
)


def _wait_for_status(registry: InMemoryJobRegistry, job_id: str, *states: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        payload = registry.status(job_id)
        if payload["status"] in states:
            return payload
        time.sleep(0.05)
    return registry.status(job_id)


def test_unknown_job_reports_unknown():
    registry = InMemoryJobRegistry(ThreadPoolExecutor(max_workers=1))
    assert registry.status("nope") == {"status": "unknown", "job_id": "nope"}
    assert registry.cancel("nope") == {"status": "unknown", "job_id": "nope"}


def test_submit_runs_the_worker_to_completion():
    with ThreadPoolExecutor(max_workers=2) as pool:
        registry = InMemoryJobRegistry(pool)
        job_id = registry.submit(lambda: _Result("executed"))
        payload = _wait_for_status(registry, job_id, "executed")

    assert payload["status"] == "executed"
    assert payload["result"] == {"status": "executed"}


def test_worker_failure_is_surfaced():
    def boom() -> _Result:
        raise RuntimeError("kaboom")

    with ThreadPoolExecutor(max_workers=2) as pool:
        registry = InMemoryJobRegistry(pool)
        job_id = registry.submit(boom)
        payload = _wait_for_status(registry, job_id, "failed")

    assert payload["status"] == "failed"
    assert "kaboom" in payload["error"]


def test_cancel_stops_a_cooperative_worker():
    started = threading.Event()

    def worker() -> _Result:
        started.set()
        while True:
            event = process_runner.current_cancel_event()
            if event is not None and event.is_set():
                raise process_runner.ProcessCancelled("demo-command")
            time.sleep(0.05)

    with ThreadPoolExecutor(max_workers=2) as pool:
        registry = InMemoryJobRegistry(pool)
        job_id = registry.submit(worker)
        assert started.wait(timeout=5)

        assert registry.cancel(job_id) == {"job_id": job_id, "status": "cancelling"}
        payload = _wait_for_status(registry, job_id, "cancelled")

    assert payload["status"] == "cancelled"


def test_cancel_reaches_a_real_subprocess(tmp_path: Path):
    """The signal must survive the trip from job registry down to the process."""

    started = threading.Event()

    def worker() -> _Result:
        started.set()
        process_runner.run_streaming(
            [sys.executable, "-c", _SLOW_SCRIPT],
            stdout_path=tmp_path / "out.log",
            timeout=120,
        )
        raise AssertionError("the run should have been cancelled")

    with ThreadPoolExecutor(max_workers=2) as pool:
        registry = InMemoryJobRegistry(pool)
        job_id = registry.submit(worker)
        assert started.wait(timeout=5)

        started_at = time.monotonic()
        registry.cancel(job_id)
        payload = _wait_for_status(registry, job_id, "cancelled")
        elapsed = time.monotonic() - started_at

    assert payload["status"] == "cancelled"
    assert elapsed < 20, f"cancel took {elapsed:.1f}s; the process was not stopped"


def test_cancel_after_completion_reports_the_final_status():
    with ThreadPoolExecutor(max_workers=2) as pool:
        registry = InMemoryJobRegistry(pool)
        job_id = registry.submit(lambda: _Result("executed"))
        _wait_for_status(registry, job_id, "executed")

        payload = registry.cancel(job_id)

    assert payload["status"] == "executed"


def test_preview_shape_is_unchanged():
    registry = InMemoryJobRegistry(ThreadPoolExecutor(max_workers=1))

    class _Planned:
        planned_side_effects = ["write project", "run import"]

    assert registry.preview(_Planned(), engine="Godot 4") == {
        "status": "confirmation_required",
        "planned_side_effects": ["write project", "run import"],
        "engine": "Godot 4",
    }
