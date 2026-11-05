"""Persistent, single-process Studio projects and immutable plan history.

The project record is the transaction boundary: plan versions, durable jobs
and authorization usage are published together. Locks are shared by every
store pointing at the same root, including the authorization store. Studio
runs one process; this is deliberately not an inter-process database lock.

All mutation methods are trusted server APIs, not transport tool handlers.
Loading never schedules a job or changes its status. New state fields have
defaults so existing records remain readable; unknown schemas fail loudly.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.contracts import DirectorBuildPlan
from fantasy_agent.path_safety import (
    assert_safe_path_segment,
    assert_under,
    display_workspace_path,
    resolve_workspace_path,
    workspace_root_path,
)

JobStatus = Literal["queued", "running", "done", "failed", "cancelled", "interrupted"]
TERMINAL_JOB_STATUSES = frozenset({"done", "failed", "cancelled", "interrupted"})
_ROOT_LOCKS: dict[str, Any] = {}
_ROOT_LOCKS_GUARD = threading.Lock()
_T = TypeVar("_T")
_CREDENTIAL_KEYS = frozenset(
    {
        "connectiontoken",
        "bearertoken",
        "accesstoken",
        "refreshtoken",
        "authorization",
        "apikey",
        "apisecret",
        "clientsecret",
        "password",
        "credentials",
        "connectioncredentials",
        "secretkey",
    }
)
_CREDENTIAL_CONTEXTS = frozenset({"connection", "auth", "authentication"})


def _credential_payload(
    value: Any, *, reject: bool = False, credential_context: bool = False
) -> Any:
    """Exclude credential fields, without interpreting normal gameplay text.

    The transport must additionally redact actual known bearer-token strings
    in arbitrary text using its authentication context. Core never stores that
    connection context or guesses secrets from ordinary gameplay strings.
    """
    if isinstance(value, dict):
        clean = {}
        for key, child in value.items():
            normalized = "".join(char for char in str(key).casefold() if char.isalnum())
            credential = normalized in _CREDENTIAL_KEYS or (
                credential_context and normalized in {"token", "key", "secret"}
            )
            if credential:
                if reject:
                    raise ValueError("连接凭证不能作为生产动作参数。")
                continue
            clean[key] = _credential_payload(
                child,
                reject=reject,
                credential_context=credential_context or normalized in _CREDENTIAL_CONTEXTS,
            )
        return clean
    if isinstance(value, (list, tuple)):
        return [
            _credential_payload(child, reject=reject, credential_context=credential_context)
            for child in value
        ]
    return deepcopy(value)


def assert_no_connection_credentials(value: dict[str, Any]) -> None:
    _credential_payload(value, reject=True)


class ProjectStoreError(ValueError):
    """A project record is corrupt or inconsistent, rather than absent."""


class _StateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class WorkflowJob(_StateModel):
    job_id: str
    plan_version: int = Field(ge=1)
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    node_id: str = ""
    grant_id: str = ""
    request_id: str = ""
    asset_paths: list[str] = Field(default_factory=list)
    rework: bool = False
    status: JobStatus = "queued"
    session_id: str = ""
    created_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def arguments_without_credentials(cls, value: dict[str, Any]) -> dict[str, Any]:
        assert_no_connection_credentials(value)
        return value

    @field_validator("result")
    @classmethod
    def public_result(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _credential_payload(value)


def public_job(job: WorkflowJob) -> WorkflowJob:
    """An independent public DTO; credential fields never leave the core."""
    return job.model_copy(
        deep=True,
        update={
            "arguments": _credential_payload(job.arguments),
            "result": _credential_payload(job.result),
        },
    )


class ProjectResource(_StateModel):
    resource_id: str
    path: str
    kind: str = "artifact"
    plan_version: int = Field(default=0, ge=0)
    job_id: str = ""


class ProjectSnapshot(_StateModel):
    project_id: str
    name: str
    plan_version: int = 0
    plan: DirectorBuildPlan | None = None
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    jobs: list[WorkflowJob] = Field(default_factory=list)
    sessions: list[str] = Field(default_factory=list)
    resources: list[ProjectResource] = Field(default_factory=list)
    created_at: float = 0
    updated_at: float = 0


class ProjectVersionConflict(ValueError):
    def __init__(self, latest: ProjectSnapshot) -> None:
        super().__init__("项目计划版本已变化，请重新读取最新计划。")
        self.latest = latest.model_copy(deep=True)


class _ProjectRecord(_StateModel):
    schema_version: Literal["0.1"] = "0.1"
    project_id: str
    name: str = Field(min_length=1)
    plan_version: int = Field(default=0, ge=0)
    plans: dict[int, DirectorBuildPlan] = Field(default_factory=dict)
    jobs: dict[str, WorkflowJob] = Field(default_factory=dict)
    request_jobs: dict[str, str] = Field(default_factory=dict)
    resources: dict[str, ProjectResource] = Field(default_factory=dict)
    grants: dict[str, dict[str, Any]] = Field(default_factory=dict)
    import_key: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class StudioProjectStore:
    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = workspace_root_path(workspace_root)
        lock_key = os.path.normcase(str(self.workspace_root))
        with _ROOT_LOCKS_GUARD:
            self._lock = _ROOT_LOCKS.setdefault(lock_key, threading.RLock())

    def record_path(self, project_id: str) -> Path:
        assert_safe_path_segment(project_id, label="project_id")
        path = self.workspace_root / "generated/studio/projects" / project_id / "project.json"
        assert_under(path, self.workspace_root)
        return path

    def production_workspace(self, project_id: str) -> Path:
        """The only root production workers may write or catalog for this project."""
        directory = self.record_path(project_id).parent
        root = directory / "workspace"
        assert_under(root, directory)
        return root.resolve()

    def create(
        self,
        name: str,
        *,
        project_id: str | None = None,
        plan: DirectorBuildPlan | dict[str, Any] | None = None,
    ) -> ProjectSnapshot:
        project_id = project_id if project_id is not None else f"project-{uuid4().hex}"
        self.record_path(project_id)
        if not name.strip():
            raise ValueError("项目名称不能为空。")
        validated = _plan_copy(plan) if plan is not None else None
        with self._lock:
            if self._load(project_id) is not None:
                raise ValueError("项目已经存在。")
            record = _ProjectRecord(project_id=project_id, name=name)
            if validated is not None:
                record.plan_version = 1
                record.plans[1] = validated
            self._publish(record)
            return self._snapshot(record)

    def list_projects(self) -> list[ProjectSnapshot]:
        with self._lock:
            root = self.workspace_root / "generated/studio/projects"
            assert_under(root, self.workspace_root)
            if not root.exists():
                return []
            snapshots = []
            for directory in sorted(root.iterdir()):
                if directory.is_dir():
                    record = self._load(directory.name)
                    if record is not None:
                        snapshots.append(self._snapshot(record))
            return snapshots

    def snapshot(
        self, project_id: str, *, plan_version: int | None = None
    ) -> ProjectSnapshot | None:
        with self._lock:
            record = self._load(project_id)
            if record is None:
                return None
            version = record.plan_version if plan_version is None else plan_version
            if version != 0 and version not in record.plans:
                return None
            return self._snapshot(record, version)

    def update_plan(
        self,
        project_id: str,
        plan: DirectorBuildPlan | dict[str, Any],
        *,
        expected_version: int,
    ) -> ProjectSnapshot:
        validated = _plan_copy(plan)

        def update(record: _ProjectRecord) -> ProjectSnapshot:
            if record.plan_version != expected_version:
                raise ProjectVersionConflict(self._snapshot(record))
            record.plan_version += 1
            record.plans[record.plan_version] = validated
            return self._snapshot(record)

        return self._mutate(project_id, update)

    def import_legacy(
        self,
        plan: DirectorBuildPlan | dict[str, Any],
        *,
        import_key: str = "legacy-handoff",
    ) -> ProjectSnapshot:
        """Import a trusted legacy handoff once per workspace and import key."""
        assert_safe_path_segment(import_key, label="import_key")
        project_id = "legacy-" + hashlib.sha256(import_key.encode()).hexdigest()[:24]
        with self._lock:
            existing = self._load(project_id)
            if existing is not None:
                if existing.import_key != import_key:
                    raise ProjectStoreError("旧交接导入记录不一致。")
                return self._snapshot(existing)
            record = _ProjectRecord(
                project_id=project_id,
                name="旧交接项目",
                import_key=import_key,
                plan_version=1,
                plans={1: _plan_copy(plan)},
            )
            self._publish(record)
            return self._snapshot(record)

    def register_job(
        self,
        project_id: str,
        *,
        job_id: str,
        plan_version: int,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        session_id: str = "",
    ) -> WorkflowJob:
        """Trusted registration for background work; production uses authorization.claim."""
        job = WorkflowJob(
            job_id=job_id,
            plan_version=plan_version,
            tool_name=tool_name,
            arguments=arguments or {},
            session_id=session_id,
        )

        def register(record: _ProjectRecord) -> WorkflowJob:
            if job_id in record.jobs:
                raise ValueError("任务已经存在。")
            record.jobs[job_id] = job
            return public_job(job)

        return self._mutate(project_id, register)

    def register_resource(
        self,
        project_id: str,
        *,
        resource_id: str,
        path: str,
        kind: str = "artifact",
        plan_version: int | None = None,
        job_id: str = "",
    ) -> ProjectResource:
        root = self.production_workspace(project_id)
        resolved = resolve_workspace_path(path, workspace_root=root)
        relative = display_workspace_path(resolved, workspace_root=root)

        def register(record: _ProjectRecord) -> ProjectResource:
            resource = ProjectResource(
                resource_id=resource_id,
                path=relative,
                kind=kind,
                plan_version=record.plan_version if plan_version is None else plan_version,
                job_id=job_id,
            )
            record.resources[resource_id] = resource
            return resource

        return self._mutate(project_id, register)

    def update_job(
        self,
        project_id: str,
        job_id: str,
        *,
        status: JobStatus,
        result: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> WorkflowJob:
        """Settle a job, preserving its authorization and original plan reference."""
        if status not in TERMINAL_JOB_STATUSES:
            raise ValueError("任务只能经 start_job 进入执行态。")

        def update(record: _ProjectRecord) -> WorkflowJob:
            job = record.jobs[job_id]
            if job.status in TERMINAL_JOB_STATUSES and job.status != status:
                raise ValueError("已结束的任务不能重新执行或改写状态。")
            job.status = status
            if job.finished_at is None:
                job.finished_at = time.time()
            job.result = _credential_payload(result if result is not None else job.result)
            if session_id is not None:
                job.session_id = session_id
            return public_job(job)

        return self._mutate(project_id, update)

    def start_job(self, project_id: str, job_id: str) -> bool:
        """Trusted non-production start. Production must use authorization.start_job."""

        def start(record: _ProjectRecord) -> bool:
            job = record.jobs[job_id]
            if job.grant_id:
                raise ValueError("生产任务必须经过授权校验再启动。")
            return self._start_job(job, time.time())

        return self._mutate(project_id, start)

    def mark_interrupted_jobs(self, project_id: str) -> list[WorkflowJob]:
        """Explicit startup reconciliation, after ensuring no old worker is alive."""

        def reconcile(record: _ProjectRecord) -> list[WorkflowJob]:
            changed = []
            for job in record.jobs.values():
                if job.status in {"queued", "running"}:
                    job.status = "interrupted"
                    job.finished_at = time.time()
                    changed.append(public_job(job))
            return changed

        return self._mutate(project_id, reconcile)

    @staticmethod
    def _start_job(job: WorkflowJob, now: float) -> bool:
        if job.status != "queued":
            return False
        job.status = "running"
        job.started_at = now
        return True

    def _mutate(self, project_id: str, change: Callable[[_ProjectRecord], _T]) -> _T:
        """Internal shared transaction seam; never expose a caller-provided callback."""
        with self._lock:
            record = self._load(project_id)
            if record is None:
                raise KeyError("项目不存在。")
            before = record.model_dump_json()
            result = change(record)
            if before != record.model_dump_json():
                record.updated_at = time.time()
                self._publish(record)
            if isinstance(result, ProjectSnapshot):
                result.updated_at = record.updated_at
            # No retained mutable model is handed to callers, even from a callback.
            return deepcopy(result)

    def _load(self, project_id: str) -> _ProjectRecord | None:
        path = self.record_path(project_id)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as exc:
            raise ProjectStoreError("项目记录无法读取。") from exc
        try:
            record = _ProjectRecord.model_validate_json(text)
            self._validate_record(record, project_id)
            return record
        except (ValueError, TypeError) as exc:
            raise ProjectStoreError("项目记录损坏或不一致。") from exc

    def _publish(self, record: _ProjectRecord) -> None:
        # Revalidate nested caller inputs before atomic publication, without
        # echoing plan or parameter values in public validation errors.
        try:
            checked = _ProjectRecord.model_validate_json(record.model_dump_json())
            self._validate_record(checked, record.project_id)
        except (ValueError, TypeError) as exc:
            raise ProjectStoreError("项目记录无效。") from exc
        write_atomic(self.record_path(record.project_id), checked.model_dump_json(indent=2))

    def _validate_record(self, record: _ProjectRecord, project_id: str) -> None:
        if record.project_id != project_id or set(record.plans) != set(
            range(1, record.plan_version + 1)
        ):
            raise ValueError("项目版本记录不一致。")
        for key, job in record.jobs.items():
            assert_safe_path_segment(key, label="job_id")
            if key != job.job_id or job.plan_version not in record.plans:
                raise ValueError("任务版本引用不一致。")
            for label in ("request_id", "grant_id", "node_id", "session_id"):
                if value := getattr(job, label):
                    assert_safe_path_segment(value, label=label)
            if job.grant_id and (
                not job.request_id or record.request_jobs.get(job.request_id) != key
            ):
                raise ValueError("授权任务的原请求引用缺失或不一致。")
        for key, resource in record.resources.items():
            assert_safe_path_segment(key, label="resource_id")
            if key != resource.resource_id:
                raise ValueError("资源引用不一致。")
            if resource.plan_version and resource.plan_version not in record.plans:
                raise ValueError("资源版本引用不一致。")
            if resource.job_id and resource.job_id not in record.jobs:
                raise ValueError("资源任务引用不存在。")
            resolve_workspace_path(
                resource.path, workspace_root=self.production_workspace(project_id)
            )
        for request_id, job_id in record.request_jobs.items():
            assert_safe_path_segment(request_id, label="request_id")
            job = record.jobs.get(job_id)
            if job is None or not job.grant_id or not job.request_id:
                raise ValueError("请求必须引用有授权的生产任务。")
        if record.grants or any(job.grant_id for job in record.jobs.values()):
            # Lazy import keeps the project models independent of authorization
            # during module import; loaded grants still undergo strict validation.
            from fantasy_agent.workflow_authorization import validate_grant_records

            validate_grant_records(record)

    @staticmethod
    def _snapshot(record: _ProjectRecord, version: int | None = None) -> ProjectSnapshot:
        version = record.plan_version if version is None else version
        plan = record.plans.get(version)
        return ProjectSnapshot(
            project_id=record.project_id,
            name=record.name,
            plan_version=version,
            plan=plan,
            tasks=[task.model_dump(mode="json") for task in plan.task_breakdown.tasks]
            if plan is not None and plan.task_breakdown is not None
            else [],
            jobs=[public_job(job) for job in record.jobs.values()],
            resources=list(record.resources.values()),
            sessions=list(
                dict.fromkeys(job.session_id for job in record.jobs.values() if job.session_id)
            ),
            created_at=record.created_at,
            updated_at=record.updated_at,
        ).model_copy(deep=True)


def _plan_copy(plan: DirectorBuildPlan | dict[str, Any]) -> DirectorBuildPlan:
    payload = plan.model_dump(mode="json") if isinstance(plan, DirectorBuildPlan) else plan
    try:
        return DirectorBuildPlan.model_validate_json(json.dumps(payload, allow_nan=False))
    except (ValidationError, ValueError, TypeError) as exc:
        raise ValueError("计划必须符合 DirectorBuildPlan 合约。") from exc
