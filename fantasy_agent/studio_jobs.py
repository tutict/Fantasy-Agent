"""Small in-memory job registry for local Studio background work."""

from __future__ import annotations

from concurrent.futures import Executor
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4


class InMemoryJobRegistry:
    """Track single-process background jobs behind the Studio HTTP interface."""

    def __init__(self, pool: Executor) -> None:
        self._pool = pool
        self._jobs: dict[str, dict[str, Any]] = {}

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
        self._jobs[job_id] = {"status": "running"}
        self._pool.submit(self._run, job_id, worker)
        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            return {"status": "unknown", "job_id": job_id}
        return {"job_id": job_id, **job}

    def _run(self, job_id: str, worker: Callable[[], Any]) -> None:
        try:
            result = worker()
            self._jobs[job_id] = {"status": result.status, "result": asdict(result)}
        except Exception as exc:  # noqa: BLE001 - surface worker failures to the UI
            self._jobs[job_id] = {"status": "failed", "error": str(exc)}

    @staticmethod
    def _new_job_id() -> str:
        return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}-{uuid4().hex[:8]}"
