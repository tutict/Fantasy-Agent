"""Server-issued, finite workflow grants, committed with durable jobs.

``issue`` and ``rework=True`` are trusted server-only operations. Transport
handlers must derive actions from a saved plan and real user approval; this
module deliberately accepts no boolean confirmation flag. It neither starts
processes nor treats a grant id as permission to skip scope validation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fantasy_agent.path_safety import (
    assert_safe_path_segment,
    is_absolute_path,
    resolve_workspace_path,
)
from fantasy_agent.studio_projects import (
    ProjectStoreError,
    StudioProjectStore,
    WorkflowJob,
    _ProjectRecord,
    assert_no_connection_credentials,
    public_job,
)

MAX_AUTHORIZATION_SECONDS = 1800
MAX_NODE_REWORKS = 3


class AuthorizationError(ValueError):
    """A missing, invalid or exhausted grant refuses production before dispatch."""


class _AuthorizationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class WorkflowAction(_AuthorizationModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    node_id: str = ""

    @field_validator("tool_name", "node_id")
    @classmethod
    def safe_names(cls, value: str, info) -> str:
        if value or info.field_name == "tool_name":
            assert_safe_path_segment(value, label=info.field_name)
        return value

    @field_validator("arguments")
    @classmethod
    def json_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        assert_no_connection_credentials(value)
        return json.loads(_canonical_json(value))


class AuthorizationUse(_AuthorizationModel):
    job_id: str
    action_key: str
    node_id: str = ""
    rework: bool = False
    claimed_at: float = Field(allow_inf_nan=False)


class WorkflowGrant(_AuthorizationModel):
    grant_id: str
    project_id: str
    plan_version: int = Field(ge=1, strict=True)
    actions: list[WorkflowAction]
    allowed_asset_paths: list[str] = Field(default_factory=list)
    issued_at: float = Field(allow_inf_nan=False)
    expires_at: float = Field(allow_inf_nan=False)
    max_reworks: int = Field(default=MAX_NODE_REWORKS, ge=0, le=MAX_NODE_REWORKS, strict=True)
    uses: list[AuthorizationUse] = Field(default_factory=list)

    @model_validator(mode="after")
    def finite_scope(self) -> WorkflowGrant:
        for label in ("grant_id", "project_id"):
            assert_safe_path_segment(getattr(self, label), label=label)
        if not 0 < self.expires_at - self.issued_at <= MAX_AUTHORIZATION_SECONDS:
            raise ValueError("授权时间预算无效。")
        keys = [action_key(action) for action in self.actions]
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("授权必须包含不重复的生产动作。")
        return self


class AuthorizationClaim(_AuthorizationModel):
    job: WorkflowJob
    reused: bool = False

    @field_validator("job")
    @classmethod
    def public_job_projection(cls, value: WorkflowJob) -> WorkflowJob:
        return public_job(value)


class WorkflowAuthorizationStore:
    def __init__(
        self,
        projects: StudioProjectStore,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.projects = projects
        self._clock = clock

    def issue(
        self,
        project_id: str,
        *,
        plan_version: int,
        actions: list[WorkflowAction | dict[str, Any]],
        allowed_asset_paths: list[str] | None = None,
        ttl_seconds: float = MAX_AUTHORIZATION_SECONDS,
        max_reworks: int = MAX_NODE_REWORKS,
    ) -> WorkflowGrant:
        """Trusted server issuance after user approval; never expose as an MCP tool."""
        if isinstance(ttl_seconds, bool) or not math.isfinite(ttl_seconds):
            raise ValueError("授权时间预算无效。")
        if not 0 < ttl_seconds <= MAX_AUTHORIZATION_SECONDS:
            raise ValueError("授权时间预算超出范围。")
        validated = [_action_copy(action) for action in actions]
        paths = self._paths(allowed_asset_paths or [])

        def save(record: _ProjectRecord) -> WorkflowGrant:
            now = self._now()
            if plan_version != record.plan_version or plan_version not in record.plans:
                raise AuthorizationError("只能授权当前已保存的计划版本。")
            grant = WorkflowGrant(
                grant_id=f"grant-{uuid4().hex}",
                project_id=project_id,
                plan_version=plan_version,
                actions=validated,
                allowed_asset_paths=paths,
                issued_at=now,
                expires_at=now + ttl_seconds,
                max_reworks=max_reworks,
            )
            record.grants[grant.grant_id] = grant.model_dump(mode="json")
            return grant

        return self._transaction(project_id, save)

    def claim(
        self,
        project_id: str,
        *,
        grant_id: str,
        plan_version: int,
        request_id: str,
        action: WorkflowAction | dict[str, Any],
        asset_paths: list[str] | None = None,
        rework: bool = False,
    ) -> AuthorizationClaim:
        """Commit usage and job together before dispatch. Rework is server-validated."""
        assert_safe_path_segment(grant_id, label="grant_id")
        assert_safe_path_segment(request_id, label="request_id")
        if type(rework) is not bool:
            raise AuthorizationError("返工请求标记无效。")
        validated = _action_copy(action)
        paths = self._paths(asset_paths or [])
        key = action_key(validated)

        def reserve(record: _ProjectRecord) -> AuthorizationClaim:
            now = self._now()
            grant = self._valid_grant(record, grant_id, plan_version, now)
            self._check_scope(grant, validated, paths)
            if existing_id := record.request_jobs.get(request_id):
                existing = record.jobs[existing_id]
                self._check_same_request(existing, grant_id, key, paths, rework)
                return AuthorizationClaim(job=existing, reused=True)
            normal = next(
                (
                    record.jobs[use.job_id]
                    for use in grant.uses
                    if use.action_key == key and not use.rework
                ),
                None,
            )
            if not rework and normal is not None:
                self._check_same_request(normal, grant_id, key, paths, False)
                record.request_jobs[request_id] = normal.job_id
                return AuthorizationClaim(job=normal, reused=True)
            if rework:
                if not validated.node_id or normal is None:
                    raise AuthorizationError("节点返工需要该动作的已有正常任务。")
                spent = sum(use.rework and use.node_id == validated.node_id for use in grant.uses)
                if spent >= grant.max_reworks:
                    raise AuthorizationError("节点返工预算已用尽。")
            job = WorkflowJob(
                job_id=f"job-{uuid4().hex}",
                plan_version=plan_version,
                tool_name=validated.tool_name,
                arguments=validated.arguments,
                node_id=validated.node_id,
                grant_id=grant_id,
                request_id=request_id,
                asset_paths=paths,
                rework=rework,
                created_at=now,
            )
            grant.uses.append(
                AuthorizationUse(
                    job_id=job.job_id,
                    action_key=key,
                    node_id=validated.node_id,
                    rework=rework,
                    claimed_at=now,
                )
            )
            record.jobs[job.job_id] = job
            record.request_jobs[request_id] = job.job_id
            record.grants[grant_id] = grant.model_dump(mode="json")
            return AuthorizationClaim(job=job, reused=False)

        return self._transaction(project_id, reserve)

    def start_job(self, project_id: str, job_id: str) -> bool:
        """Recheck authorization at queued→running; False means never dispatch again."""
        assert_safe_path_segment(job_id, label="job_id")

        def start(record: _ProjectRecord) -> bool:
            now = self._now()
            if job_id not in record.jobs:
                raise AuthorizationError("生产任务不存在。")
            job = record.jobs[job_id]
            grant = self._valid_grant(record, job.grant_id, job.plan_version, now)
            action = WorkflowAction(
                tool_name=job.tool_name, arguments=job.arguments, node_id=job.node_id
            )
            self._check_scope(grant, action, self._paths(job.asset_paths))
            if not any(use.job_id == job_id for use in grant.uses):
                raise AuthorizationError("生产任务没有授权使用记录。")
            return self.projects._start_job(job, now)

        return self._transaction(project_id, start)

    def _transaction(self, project_id: str, operation):
        try:
            return self.projects._mutate(project_id, operation)
        except (ProjectStoreError, KeyError) as exc:
            raise AuthorizationError("授权记录不存在、损坏或不一致。") from exc

    def _valid_grant(
        self,
        record: _ProjectRecord,
        grant_id: str,
        plan_version: int,
        now: float,
    ) -> WorkflowGrant:
        if grant_id not in record.grants:
            raise AuthorizationError("生产动作需要服务端签发的授权。")
        grant = WorkflowGrant.model_validate(record.grants[grant_id])
        if grant.project_id != record.project_id or grant.plan_version != plan_version:
            raise AuthorizationError("授权不属于该项目或计划版本。")
        if record.plan_version != grant.plan_version:
            raise AuthorizationError("计划版本已经变化，请重新批准。")
        if not grant.issued_at <= now < grant.expires_at:
            raise AuthorizationError("授权尚未生效或已经过期。")
        return grant

    @staticmethod
    def _check_scope(grant: WorkflowGrant, action: WorkflowAction, paths: list[str]) -> None:
        if action_key(action) not in {action_key(allowed) for allowed in grant.actions}:
            raise AuthorizationError("生产工具或参数超出已批准范围。")
        if not set(map(os.path.normcase, paths)) <= set(
            map(os.path.normcase, grant.allowed_asset_paths)
        ):
            raise AuthorizationError("素材路径超出已批准范围。")

    @staticmethod
    def _check_same_request(
        job: WorkflowJob,
        grant_id: str,
        key: str,
        paths: list[str],
        rework: bool,
    ) -> None:
        original = WorkflowAction(
            tool_name=job.tool_name, arguments=job.arguments, node_id=job.node_id
        )
        if (
            job.grant_id != grant_id
            or action_key(original) != key
            or job.rework != rework
            or set(map(os.path.normcase, job.asset_paths)) != set(map(os.path.normcase, paths))
        ):
            raise AuthorizationError("请求标识已经用于不同内容。")

    def _paths(self, paths: list[str]) -> list[str]:
        """Exact local input allowlist; output containment is a separate policy."""
        canonical: dict[str, str] = {}
        try:
            for path in paths:
                if path.startswith(("\\\\", "//")) or (
                    re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path)
                    and not re.match(r"^[A-Za-z]:[/\\]", path)
                ):
                    raise ValueError("素材输入必须是本机文件路径。")
                if is_absolute_path(path):
                    candidate = Path(path.replace("\\", "/"))
                    if not candidate.is_absolute():
                        raise ValueError("素材输入必须是本机绝对路径。")
                    resolved = candidate.resolve()
                else:
                    resolved = resolve_workspace_path(
                        path, workspace_root=self.projects.workspace_root
                    )
                try:
                    relative = resolved.relative_to(self.projects.workspace_root)
                except ValueError:
                    absolute = str(resolved)
                else:
                    # Rejoin in-root inputs for a stable Windows drive case.
                    absolute = str(self.projects.workspace_root / relative)
                canonical[os.path.normcase(absolute)] = absolute
        except (ValueError, TypeError) as exc:
            raise AuthorizationError("素材输入路径无效，必须是本机文件。") from exc
        return [canonical[key] for key in sorted(canonical)]

    def _now(self) -> float:
        now = self._clock()
        if not math.isfinite(now):
            raise AuthorizationError("授权时钟无效。")
        return now


def action_key(action: WorkflowAction) -> str:
    return hashlib.sha256(_canonical_json(action.model_dump(mode="json")).encode()).hexdigest()


def _canonical_json(value: Any) -> str:
    def check(item: Any) -> None:
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("生产参数必须使用字符串键。")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif item is not None and type(item) not in {str, int, float, bool}:
            raise ValueError("生产参数必须是 JSON 数据。")

    check(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("生产参数必须是有限 JSON 数据。") from exc


def _action_copy(action: WorkflowAction | dict[str, Any]) -> WorkflowAction:
    payload = action.model_dump(mode="python") if isinstance(action, WorkflowAction) else action
    try:
        return WorkflowAction.model_validate(payload)
    except (ValueError, TypeError) as exc:
        raise AuthorizationError("生产动作参数无效。") from exc


def validate_grant_records(record: _ProjectRecord) -> None:
    """Validate durable usage against jobs; corruption cannot reset a budget."""
    claimed_jobs: set[str] = set()
    for grant_id, payload in record.grants.items():
        grant = WorkflowGrant.model_validate(payload)
        if grant.grant_id != grant_id or grant.project_id != record.project_id:
            raise ValueError("授权项目引用不一致。")
        if grant.plan_version not in record.plans:
            raise ValueError("授权计划版本不存在。")
        actions = {action_key(action): action for action in grant.actions}
        normal: set[str] = set()
        reworks: dict[str, int] = {}
        for use in grant.uses:
            if use.job_id in claimed_jobs or use.job_id not in record.jobs:
                raise ValueError("授权任务使用记录不一致。")
            job = record.jobs[use.job_id]
            action = WorkflowAction(
                tool_name=job.tool_name, arguments=job.arguments, node_id=job.node_id
            )
            if (
                use.action_key not in actions
                or action_key(action) != use.action_key
                or job.grant_id != grant_id
                or job.plan_version != grant.plan_version
                or use.rework != job.rework
                or use.node_id != job.node_id
                or not grant.issued_at <= use.claimed_at < grant.expires_at
            ):
                raise ValueError("授权任务超出范围。")
            if not set(map(os.path.normcase, job.asset_paths)) <= set(
                map(os.path.normcase, grant.allowed_asset_paths)
            ):
                raise ValueError("授权任务素材超出范围。")
            if use.rework:
                if use.action_key not in normal or not use.node_id:
                    raise ValueError("返工缺失正常动作记录。")
                reworks[use.node_id] = reworks.get(use.node_id, 0) + 1
                if reworks[use.node_id] > grant.max_reworks:
                    raise ValueError("节点返工预算超出范围。")
            else:
                if use.action_key in normal:
                    raise ValueError("正常动作重复消耗授权。")
                normal.add(use.action_key)
            claimed_jobs.add(use.job_id)
    if claimed_jobs != {job.job_id for job in record.jobs.values() if job.grant_id}:
        raise ValueError("生产任务缺失授权使用记录。")
