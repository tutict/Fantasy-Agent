"""Small in-memory job registry for local Studio background work."""

from __future__ import annotations

import threading
from concurrent.futures import Executor
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

from fantasy_agent.process_runner import ProcessCancelled, cancel_scope


class InMemoryJobRegistry:
    """Track single-process background jobs behind the Studio HTTP interface.

    Each submitted job gets a cancel event bound into the execution context.
    Long-running tools read it back out of the context and stop cooperatively,
    so no worker signature has to grow a cancel parameter.
    """

    def __init__(self, pool: Executor) -> None:
        self._pool = pool
        self._jobs: dict[str, dict[str, Any]] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def preview(self, result: Any, *, engine: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "confirmation_required",
            "planned_side_effects": list(getattr(result, "planned_side_effects", [])),
        }
        if engine is not None:
            payload["engine"] = engine
        return payload

    def submit(self, worker: Callable[[], Any]) -> str:
        job_id = self._new_job_id()
        with self._lock:
            self._jobs[job_id] = {"status": "running"}
            self._cancel_events[job_id] = threading.Event()
        self._pool.submit(self._run, job_id, worker)
        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return {"status": "unknown", "job_id": job_id}
        return {"job_id": job_id, **job}

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Ask a running job to stop.

        Returns ``cancelling`` once the signal is raised; the job settles on
        ``cancelled`` when the worker actually unwinds. A job that is not
        running simply reports its current status.
        """

        with self._lock:
            job = self._jobs.get(job_id)
            event = self._cancel_events.get(job_id)
        if job is None:
            return {"status": "unknown", "job_id": job_id}
        if job.get("status") != "running":
            return {"job_id": job_id, **job}
        if event is not None:
            event.set()
        return {"job_id": job_id, "status": "cancelling"}

    def _run(self, job_id: str, worker: Callable[[], Any]) -> None:
        with self._lock:
            event = self._cancel_events.get(job_id) or threading.Event()
        try:
            with cancel_scope(event):
                result = worker()
        except ProcessCancelled as exc:
            self._finish(job_id, {"status": "cancelled", "error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 - surface worker failures to the UI
            self._finish(job_id, {"status": "failed", "error": str(exc)})
            return
        self._finish(job_id, {"status": result.status, "result": asdict(result)})

    def _finish(self, job_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id] = payload
            self._cancel_events.pop(job_id, None)

    @staticmethod
    def _new_job_id() -> str:
        return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}-{uuid4().hex[:8]}"
