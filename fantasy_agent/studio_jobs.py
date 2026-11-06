"""Small in-memory job registry for local Studio background work."""

from __future__ import annotations

import copy
import math
import threading
import time
from collections.abc import Callable
from concurrent.futures import Executor
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
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
        self._completion: dict[str, Callable[[str, dict[str, Any]], None]] = {}
        self._lock = threading.Lock()

    def preview(self, result: Any, *, engine: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "confirmation_required",
            "planned_side_effects": list(getattr(result, "planned_side_effects", [])),
        }
        if engine is not None:
            payload["engine"] = engine
        return payload

    def submit(
        self,
        worker: Callable[[], Any],
        *,
        job_id: str | None = None,
        deadline: float | None = None,
        clock: Callable[[], float] = time.time,
        on_complete: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> str:
        """Submit a reserved workflow id, optionally bound to its grant deadline.

        Legacy callers retain their immediate ``running`` state. Completion
        callbacks publish durable results before memory reports completion.
        """
        if deadline is not None and not math.isfinite(deadline):
            raise ValueError("任务截止时间无效。")
        reserved = job_id is not None
        job_id = job_id or self._new_job_id()
        with self._lock:
            if job_id in self._jobs:
                raise ValueError("任务编号已经登记，不能重复启动。")
            self._jobs[job_id] = {"status": "queued" if reserved else "running"}
            self._cancel_events[job_id] = threading.Event()
            if on_complete is not None:
                self._completion[job_id] = on_complete
        try:
            self._pool.submit(self._run, job_id, worker, deadline, clock)
        except Exception as exc:  # noqa: BLE001 - submission failure must settle the reserved job
            self._finish(job_id, {"status": "failed", "error": str(exc)})
        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return {"status": "unknown", "job_id": job_id}
        return copy.deepcopy({"job_id": job_id, **job})

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
        if job.get("status") not in {"queued", "running"}:
            return copy.deepcopy({"job_id": job_id, **job})
        if event is not None:
            event.set()
        return {"job_id": job_id, "status": "cancelling"}

    def _run(
        self,
        job_id: str,
        worker: Callable[[], Any],
        deadline: float | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        with self._lock:
            event = self._cancel_events.get(job_id) or threading.Event()
        timer: threading.Timer | None = None
        try:
            with cancel_scope(event):
                if deadline is not None:
                    remaining = deadline - clock()
                    if remaining <= 0:
                        raise TimeoutError("任务的授权时间预算已耗尽。")
                    timer = threading.Timer(remaining, event.set)
                    timer.daemon = True
                    timer.start()
                if event.is_set():
                    raise ProcessCancelled("Studio workflow")
                with self._lock:
                    self._jobs[job_id] = {"status": "running"}
                result = worker()
                payload = {"status": result.status, "result": asdict(result)}
                if event.is_set():
                    payload["status"] = "cancelled"
                    payload["error"] = "任务已取消，已生成的结果保留。"
        except ProcessCancelled as exc:
            payload = {"status": "cancelled", "error": str(exc), "log_paths": exc.log_paths}
        except Exception as exc:  # noqa: BLE001 - surface worker failures to the UI
            payload = {"status": "failed", "error": str(exc)}
        finally:
            if timer is not None:
                timer.cancel()
        if deadline is not None and clock() >= deadline:
            payload.update(status="failed", error="任务的授权时间预算已耗尽。")
        self._finish(job_id, payload)

    def _finish(self, job_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            callback = self._completion.pop(job_id, None)
        if callback is not None:
            try:
                callback(job_id, copy.deepcopy(payload))
            except Exception as exc:  # noqa: BLE001 - durability failure cannot look completed
                payload = {**payload, "status": "failed", "error": f"任务结果未能保存：{exc}"}
        with self._lock:
            self._jobs[job_id] = payload
            self._cancel_events.pop(job_id, None)

    @staticmethod
    def _new_job_id() -> str:
        return f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}-{uuid4().hex[:8]}"
