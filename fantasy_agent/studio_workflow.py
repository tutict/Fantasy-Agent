"""Project-scoped workflow used by Studio and its local MCP transport.

The external agent selects operations. This service supplies saved plans,
checks server-issued grants and calls existing library workers. It never runs
the application's model loop or creates a second execution pool.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import logging
import mimetypes
import shutil
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from jsonschema import Draft202012Validator
from pydantic import Field, ValidationError

from fantasy_agent import local_tools
from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.contracts import (
    ComfyUIRunManifest,
    DirectorBuildPlan,
    IdeaDiscoveryRequest,
    ProductionPipeline,
    PromptRequest,
    StrictModel,
    UnrealAssetIngestManifest,
    UnrealImportManifest,
    UnrealLevelAssemblyManifest,
)
from fantasy_agent.demo_launch import DemoLaunch, launch_demo
from fantasy_agent.evolution.contracts import EvolutionExperience, EvolutionReport, EvolutionRequest
from fantasy_agent.evolution.controller import (
    prepare_evolution_adoption,
    run_evolution,
    suggest_evolution,
)
from fantasy_agent.evolution.library import (
    EvolutionLibraryError,
    load_report,
    save_experience,
    save_report,
)
from fantasy_agent.orchestration_state import load_state
from fantasy_agent.orchestrator import Orchestrator, StageOutcome
from fantasy_agent.path_safety import assert_safe_path_segment, resolve_workspace_path
from fantasy_agent.pipeline_state import ORCHESTRATION_TO_EXECUTOR_STAGES, executor_stages_for
from fantasy_agent.pipeline_state import load_state as load_pipeline_state
from fantasy_agent.planning_actions import PLANNING_TOOL_NAMES, run_planning_action
from fantasy_agent.process_runner import ProcessCancelled, current_cancel_event
from fantasy_agent.studio_asset_review import ProjectAssetReview
from fantasy_agent.studio_jobs import InMemoryJobRegistry
from fantasy_agent.studio_projects import (
    ProjectResource,
    ProjectSnapshot,
    ProjectVersionConflict,
    StudioProjectStore,
    WorkflowJob,
    assert_no_connection_credentials,
)
from fantasy_agent.studio_workflow_evidence import (
    PREPARATIONS,
    StageEvidence,
    evidence_for,
    external_pipeline,
    worker_data,
)
from fantasy_agent.tool_registry import (
    EXECUTE,
    READ_ONLY,
    WRITE,
    ToolOutcome,
    ToolRegistry,
    ToolSpec,
    combined_registry,
    engine_registry,
)
from fantasy_agent.workflow_authorization import WorkflowAction, WorkflowAuthorizationStore


class DemoAction(StrictModel):
    engine: Literal["godot", "unreal"] = "godot"
    # Production and review are separate operations in the external workflow.
    with_assets: Literal[False] = False
    with_visuals: Literal[False] = False
    with_gameplay: bool = True
    run_import: bool = True
    resume_from: str = ""


class AssetAction(StrictModel):
    with_assets: bool = True
    with_visuals: bool = False


class EvolutionAction(StrictModel):
    max_iterations: int = Field(default=3, ge=1, le=3)
    max_wall_seconds: float = Field(default=600, ge=30, le=1800, allow_inf_nan=False)
    use_experience: bool = True


class IngestAction(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    source_path: str = Field(min_length=1)
    license: str = ""
    author: str = ""
    source_url: str = ""
    notes: str = ""
    tags: list[str] = Field(default_factory=list)


class AssetCopyAction(StrictModel):
    resource_ids: list[str] = Field(min_length=1, max_length=128)


@dataclass
class WorkflowResult:
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    kind: str = "tool"


_MODELS = {
    "execute_demo": DemoAction,
    "execute_assets": AssetAction,
    "run_evolution": EvolutionAction,
    "ingest_asset": IngestAction,
    "copy_approved_godot_assets": AssetCopyAction,
}
_LABELS = {
    "extract_idea_seed": "提炼点子",
    "generate_game_production_plan": "生成并保存生产计划",
    "decompose_production_tasks": "拆分生产任务",
    "render_gdd": "整理设计文档",
    "prepare_production_pipeline": "整理编排计划",
    "prepare_unreal_plan": "规划 Unreal 工程",
    "prepare_godot_plan": "规划 Godot 工程",
    "prepare_blender_plan": "规划模型资产",
    "prepare_comfyui_plan": "规划视觉参考",
    "prepare_creative_review_plan": "准备创意审阅",
    "prepare_qa_plan": "准备质量检查",
    "execute_demo": "生成可玩工程与质量检查",
    "execute_assets": "制作本轮模型与视觉参考",
    "run_evolution": "运行反馈进化实验",
    "ingest_asset": "录入本机素材",
    "copy_approved_godot_assets": "将已审阅资产写入 Godot 工程",
    "create_godot_project_structure": "创建 Godot 工程",
    "run_godot_import": "导入并校验 Godot 工程",
    "playtest_godot_project": "运行 Godot 试玩",
    "generate_blender_script": "生成模型制作脚本",
    "generate_asset_batch": "运行 Blender 制作资产",
    "prepare_visual_reference_workflows": "准备视觉参考工作流",
    "run_visual_reference_workflow": "生成视觉参考",
    "run_editor_commandlet": "校验 Unreal 工程",
}
_HIDDEN = {
    "plan",
    "gameplay_spec",
    "gameplay_scripts",
    "production_spec_bundle",
    "enemy_tuning",
    "confirmed",
    "confirmed_side_effects",
    "write_files",
    "workspace_root",
    "project_dir",
    "project_file",
    "plan_path",
    "content_manifest_path",
    "import_manifest_paths",
    "import_manifest_path",
    "script_path",
    "import_script_path",
    "assembly_script_path",
    "ingest_manifest_path",
    "level_manifest_path",
    "blender_import_manifest_path",
    "comfyui_run_manifest_path",
    "output_dir",
    "endpoint",
    "endpoint_candidates",
    "allow_remote_endpoint",
    "commandlet",
    "godot_executable",
    "blender_executable",
    "unreal_editor_cmd",
    "stdout_path",
    "stderr_path",
}
_UNSUPPORTED = {"publish_prototype_branch", "package_desktop", "package_game", "resume_unreal"}
_LOG = logging.getLogger(__name__)
_PRIVATE_FILES = {"llm-api.json", "mcp-settings.json", "mcp-connection.json", "project.json"}
_ASSET_SUFFIXES = {".glb", ".fbx", ".blend", ".png", ".jpg", ".jpeg", ".webp"}
_MAX_RESOURCE_BYTES = 3 * 1024 * 1024


def _private_path(path: str | Path, *, workspace_root: Path | None = None) -> bool:
    candidate = Path(path)
    if workspace_root is not None:
        try:
            candidate = candidate.relative_to(workspace_root)
        except ValueError:
            pass
    parts = [part.rstrip(" .").casefold() for part in candidate.parts]
    return bool(parts and parts[-1] in _PRIVATE_FILES) or any(
        part in {".git", ".codex", "config"} for part in parts
    )


def _json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return _json(asdict(value))
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    properties = copy.deepcopy(properties)
    definitions = {}
    for prop in properties.values():
        definitions.update(prop.pop("$defs", {}))
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
        **({"$defs": definitions} if definitions else {}),
    }


class StudioWorkflowService:
    def __init__(
        self,
        projects: StudioProjectStore,
        authorization: WorkflowAuthorizationStore,
        *,
        execute_jobs: InMemoryJobRegistry,
        asset_jobs: InMemoryJobRegistry,
        playtest_jobs: InMemoryJobRegistry,
        evolution_jobs: InMemoryJobRegistry,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.projects, self.authorization, self.clock = projects, authorization, clock
        self.asset_review = ProjectAssetReview(projects)
        self.execute_jobs, self.asset_jobs = execute_jobs, asset_jobs
        self.playtest_jobs, self.evolution_jobs = playtest_jobs, evolution_jobs
        self._registries = {
            "execute": execute_jobs,
            "assets": asset_jobs,
            "playtest": playtest_jobs,
            "evolution": evolution_jobs,
        }
        self._intents: dict[str, dict[str, Any]] = {}
        self._orchestrators: dict[tuple[str, int], Orchestrator] = {}
        engines = engine_registry(projects.workspace_root)
        self._engine_specs = {name: engines.get(name) for name in engines.names()}
        self.registry = self._registry()

    def _registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        context = {
            "project_id": {"type": "string", "minLength": 1},
            "plan_version": {"type": "integer", "minimum": 0},
        }
        for name in PLANNING_TOOL_NAMES:
            source = IdeaDiscoveryRequest if name == "extract_idea_seed" else PromptRequest
            schema = source.model_json_schema()
            schema["properties"].update(context)
            registry.register(
                ToolSpec(
                    name,
                    _LABELS[name],
                    schema,
                    lambda args, name=name: self._planning(name, args),
                    permission=WRITE if name == "generate_game_production_plan" else READ_ONLY,
                    effect_scope="session_metadata",
                    title=_LABELS[name],
                )
            )
        for name, spec in self._engine_specs.items():
            if spec is None:
                continue
            schema = self._arguments_schema(name)
            schema["properties"].update(context)
            schema["properties"].update(
                {"grant_id": {"type": "string"}, "request_id": {"type": "string"}}
            )
            schema["required"] = [*schema.get("required", []), "project_id", "plan_version"]
            registry.register(
                ToolSpec(
                    name,
                    _LABELS.get(name, f"本机工具：{name}"),
                    schema,
                    lambda args, name=name: self._production_call(name, args),
                    permission=spec.permission,
                    title=_LABELS.get(name, name),
                )
            )
        for name, model in _MODELS.items():
            schema = model.model_json_schema()
            schema["properties"].update(context)
            schema["properties"].update(
                {"grant_id": {"type": "string"}, "request_id": {"type": "string"}}
            )
            schema["required"] = [*schema.get("required", []), "project_id", "plan_version"]
            registry.register(
                ToolSpec(
                    name,
                    _LABELS[name],
                    schema,
                    lambda args, name=name: self._production_call(name, args),
                    permission=WRITE
                    if name in {"ingest_asset", "copy_approved_godot_assets"}
                    else EXECUTE,
                    title=_LABELS[name],
                )
            )
        string = {"type": "string", "minLength": 1}
        metadata = [
            (
                "create_project",
                "创建项目（仅保存会话元数据）",
                _schema({"name": string}, ("name",)),
                lambda a: self.projects.create(a["name"]).model_dump(mode="json"),
                WRITE,
            ),
            (
                "list_projects",
                "列出后台项目",
                _schema({}),
                lambda a: {
                    "projects": [
                        p.model_dump(mode="json", exclude={"plan"})
                        for p in self.projects.list_projects()
                    ]
                },
                READ_ONLY,
            ),
            (
                "get_project_snapshot",
                "读取项目与计划版本",
                _schema(context, ("project_id",)),
                lambda a: self.snapshot(a["project_id"], a.get("plan_version")),
                READ_ONLY,
            ),
            (
                "save_project_plan",
                "保存计划（版本冲突会保留最新快照）",
                _schema(
                    {**context, "plan": DirectorBuildPlan.model_json_schema()},
                    ("project_id", "plan_version", "plan"),
                ),
                lambda a: self._save_plan_call(a),
                WRITE,
            ),
            (
                "get_workflow_job",
                "查询任务、日志摘要与产物",
                _schema({"project_id": string, "job_id": string}, ("project_id", "job_id")),
                lambda a: self.get_job(a["project_id"], a["job_id"]),
                READ_ONLY,
            ),
            (
                "cancel_workflow_job",
                "取消任务并保留已生成结果",
                _schema({"project_id": string, "job_id": string}, ("project_id", "job_id")),
                lambda a: self.cancel_job(a["project_id"], a["job_id"]),
                WRITE,
            ),
            (
                "get_workflow_state",
                "读取编排与权限状态",
                _schema(context, ("project_id",)),
                lambda a: self.workflow_state(a["project_id"], a.get("plan_version")),
                READ_ONLY,
            ),
            (
                "read_project_resource",
                "读取本项目已登记的产物",
                _schema(
                    {"project_id": string, "resource_id": string}, ("project_id", "resource_id")
                ),
                lambda a: {"resource": self.read_resource(a["project_id"], a["resource_id"])},
                READ_ONLY,
            ),
            (
                "suggest_evolution",
                "根据已采用经验提出数值建议",
                _schema(context, ("project_id",)),
                lambda a: _json(
                    suggest_evolution(
                        self._snapshot(a["project_id"], a.get("plan_version")).plan,
                        workspace_root=self.projects.production_workspace(a["project_id"]),
                    )
                ),
                READ_ONLY,
            ),
        ]
        action_schema = WorkflowAction.model_json_schema()
        auth_schema = _schema(
            {
                **context,
                "actions": {"type": "array", "minItems": 1, "maxItems": 30, "items": action_schema},
                "allowed_asset_paths": {"type": "array", "items": {"type": "string"}},
                "ttl_seconds": {"type": "number", "minimum": 1, "maximum": 1800, "default": 1800},
            },
            ("project_id", "plan_version", "actions"),
        )
        metadata.append(
            (
                "request_workflow_authorization",
                "在对话中请求本轮生产授权",
                auth_schema,
                lambda a: self.request_authorization(**a),
                READ_ONLY,
            )
        )
        metadata.extend(
            [
                (
                    "request_asset_review",
                    "请用户审阅实际生成的资产",
                    _schema(
                        {
                            **context,
                            "resource_ids": {"type": "array", "minItems": 1, "items": string},
                        },
                        ("project_id", "plan_version", "resource_ids"),
                    ),
                    lambda a: self.request_asset_review(**a),
                    READ_ONLY,
                ),
                (
                    "request_candidate_adoption",
                    "请用户决定是否采纳实测优胜候选",
                    _schema(
                        {**context, "job_id": string}, ("project_id", "plan_version", "job_id")
                    ),
                    lambda a: self.request_candidate_adoption(**a),
                    READ_ONLY,
                ),
                (
                    "rework_node",
                    "从已执行任务的指定节点续跑（最多三次）",
                    _schema(
                        {
                            **context,
                            "job_id": string,
                            "resume_from": string,
                            "request_id": string,
                            "grant_id": string,
                        },
                        ("project_id", "plan_version", "job_id", "resume_from"),
                    ),
                    lambda a: self.rework_node(**a),
                    WRITE,
                ),
            ]
        )
        for name, label, schema, handler, permission in metadata:
            registry.register(
                ToolSpec(
                    name,
                    label,
                    schema,
                    handler,
                    permission=permission,
                    effect_scope="session_metadata",
                    title=label,
                )
            )
        return registry

    def _arguments_schema(self, name: str) -> dict[str, Any]:
        if name in _MODELS:
            return _MODELS[name].model_json_schema()
        spec = self._engine_specs.get(name)
        if spec is None:
            raise ValueError("生产工具尚未实现。")
        schema = copy.deepcopy(spec.model_schema()["parameters"])
        hidden = _HIDDEN | set(spec.executable_args) | set(spec.hidden_args)
        schema["properties"] = {
            key: value for key, value in schema.get("properties", {}).items() if key not in hidden
        }
        schema["required"] = [key for key in schema.get("required", []) if key not in hidden]
        schema["additionalProperties"] = False
        return schema

    def _arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        assert_no_connection_credentials(arguments)
        schema = self._arguments_schema(name)
        if list(Draft202012Validator(schema).iter_errors(arguments)):
            raise ValueError("工具参数无效；执行路径、计划与确认标记只能由服务端提供。")
        result = copy.deepcopy(arguments)
        for key, prop in schema.get("properties", {}).items():
            if key not in result and "default" in prop:
                result[key] = copy.deepcopy(prop["default"])
        if name in _MODELS:
            result = _MODELS[name].model_validate(result).model_dump(mode="json")
        if name == "execute_demo" and result.get("resume_from"):
            if result.get("engine") == "unreal":
                raise ValueError("Unreal 节点续跑尚未实现。")
            raise ValueError("续跑必须使用 rework_node 并引用已有任务。")
        if name == "ingest_asset":
            result["source_path"] = self.authorization._paths([result["source_path"]])[0]
            if _private_path(result["source_path"], workspace_root=self.projects.workspace_root):
                raise ValueError("连接或模型凭据不能录入素材库。")
        return result

    def _node(self, name: str, arguments: dict[str, Any]) -> str:
        if name in {"playtest_godot_project", "run_editor_commandlet", "run_evolution"}:
            return "optimization_testing"
        if name in {"generate_blender_script", "generate_asset_batch", "execute_assets"}:
            return "blender_modeling"
        if "visual" in name or "comfyui" in name:
            return "comfyui_visual_production"
        if name in {"ingest_asset", "copy_approved_godot_assets"} or "ingest" in name:
            return "asset_integration"
        if "godot" in name or (name == "execute_demo" and arguments.get("engine") == "godot"):
            return "godot_quick_play"
        return "unreal_production"

    def _snapshot(self, project_id: str, version: int | None = None) -> ProjectSnapshot:
        snapshot = self.projects.snapshot(project_id, plan_version=version)
        if snapshot is None:
            raise ValueError("项目或计划版本不存在。")
        return snapshot

    def _root(self, project_id: str, version: int) -> Path:
        return self.projects.production_workspace(project_id) / "versions" / f"v{version}"

    def call(self, name: str, arguments: dict[str, Any]) -> ToolOutcome:
        if name in _UNSUPPORTED:
            return ToolOutcome(
                name,
                "refused",
                "该操作尚未实现。",
                self._envelope("unsupported", "该操作尚未实现。"),
            )
        spec = self.registry.get(name)
        if spec is None:
            return ToolOutcome(name, "error", "工具不存在。")
        try:
            if list(Draft202012Validator(spec.input_schema).iter_errors(arguments)):
                raise ValueError("工具参数不符合声明的范围。")
            granted = False
            if spec.effect_scope == "production" and spec.permission != READ_ONLY:
                self.authorization.get_grant(
                    arguments["project_id"],
                    arguments.get("grant_id", ""),
                    plan_version=arguments["plan_version"],
                )
                granted = True
            result = self.registry.call(
                name,
                arguments,
                allow_write=spec.effect_scope == "session_metadata" or granted,
                allow_execute=granted,
            )
            if result.status == "ok":
                data = result.data
                result.content = str(
                    data.get("summary") or _LABELS.get(name, spec.title or "操作已完成。")
                )
                result.data = {
                    **self._envelope(str(data.get("status", "ok")), result.content),
                    **data,
                }
            elif not result.data:
                summary = result.content.split(": ", 1)[-1]
                result.content = summary
                result.data = self._envelope(
                    "blocked",
                    summary,
                    next_actions=[
                        "检查阻塞原因并重新读取当前项目；授权过期时，请在对话中确认新的生产范围。"
                    ],
                )
            return result
        except ProjectVersionConflict as exc:
            return ToolOutcome(
                name,
                "refused",
                str(exc),
                self._envelope(
                    "version_conflict", str(exc), latest=exc.latest.model_dump(mode="json")
                ),
            )
        except ValueError as exc:
            return ToolOutcome(name, "refused", str(exc), self._envelope("blocked", str(exc)))

    @staticmethod
    def _envelope(status: str, summary: str, **data: Any) -> dict[str, Any]:
        return {
            "source": "fantasy_agent.studio_workflow",
            "schema_version": "0.1",
            "status": status,
            "summary": summary,
            "resources": [],
            "blockers": []
            if status not in {"blocked", "failed", "version_conflict"}
            else [summary],
            "next_actions": [],
            **data,
        }

    def _planning(self, name: str, arguments: dict[str, Any]) -> dict[str, Any] | ToolOutcome:
        args = copy.deepcopy(arguments)
        project_id, version = args.pop("project_id", None), args.pop("plan_version", None)
        action = run_planning_action(name, args, use_llm=False)
        if action.seed is not None:
            return {"idea_seed": _json(action.seed), "summary": "点子已提炼，下一步生成生产计划。"}
        plan = action.require_plan()
        if name == "generate_game_production_plan" and project_id:
            if version is None:
                raise ValueError("保存计划需要预期版本。")
            try:
                saved = self.projects.update_plan(project_id, plan, expected_version=version)
            except ProjectVersionConflict as exc:
                return ToolOutcome(
                    name,
                    "refused",
                    str(exc),
                    self._envelope(
                        "version_conflict", str(exc), latest=exc.latest.model_dump(mode="json")
                    ),
                )
            self._record_plan(project_id, saved.plan_version, plan, name)
            return self._envelope(
                "saved",
                f"生产计划已保存为第 {saved.plan_version} 版。",
                project_id=project_id,
                plan_version=saved.plan_version,
                resources=[self._virtual_ref(project_id, f"plan-v{saved.plan_version}")],
            )
        projection = {
            "decompose_production_tasks": "task_breakdown",
            "render_gdd": "gdd",
            "prepare_production_pipeline": "production_pipeline",
            "prepare_unreal_plan": "unreal_plan",
            "prepare_godot_plan": "godot_plan",
            "prepare_blender_plan": "blender_plan",
            "prepare_comfyui_plan": "comfyui_plan",
            "prepare_creative_review_plan": "creative_review",
            "prepare_qa_plan": "qa_plan",
        }
        key = projection.get(name)
        return {
            key or "plan": _json(getattr(plan, key)) if key else _json(plan),
            "summary": "策划结果已生成，保存计划后再授权生产动作。",
            "status": "planned",
            "next_actions": ["保存计划后再授权生产动作。"],
        }

    def save_plan(
        self, project_id: str, plan: dict[str, Any] | DirectorBuildPlan, version: int
    ) -> dict[str, Any]:
        saved = self.projects.update_plan(project_id, plan, expected_version=version)
        self._record_plan(project_id, saved.plan_version, saved.plan, "save_project_plan")
        return saved.model_dump(mode="json")

    def _save_plan_call(self, arguments: dict[str, Any]) -> dict[str, Any] | ToolOutcome:
        try:
            return self.save_plan(
                arguments["project_id"], arguments["plan"], arguments["plan_version"]
            )
        except ProjectVersionConflict as exc:
            return ToolOutcome(
                "save_project_plan",
                "refused",
                str(exc),
                self._envelope(
                    "version_conflict", str(exc), latest=exc.latest.model_dump(mode="json")
                ),
            )

    def _record_plan(
        self, project_id: str, version: int, plan: DirectorBuildPlan, tool_name: str
    ) -> None:
        orchestrator = self._orchestrator(project_id, version, register=True)
        if orchestrator is None:
            return
        observed = ToolOutcome(
            tool_name,
            "ok",
            "生产计划已保存并通过静态检查。",
            {"summary": plan.model_dump(mode="json")},
        )
        orchestrator.accept_external_result(
            plan.production_pipeline,
            "gameplay_orchestration",
            observed,
            artifacts=[],
            plan_evidence=plan,
        )

    def request_authorization(
        self,
        project_id: str,
        *,
        plan_version: int,
        actions: list[dict[str, Any]],
        allowed_asset_paths: list[str] | None = None,
        ttl_seconds: float = 1800,
    ) -> dict[str, Any]:
        snapshot = self._snapshot(project_id, plan_version)
        if snapshot.plan is None or self._snapshot(project_id).plan_version != plan_version:
            raise ValueError("只能授权当前已保存的计划。")
        if not 0 < ttl_seconds <= 1800:
            raise ValueError("授权时间预算必须在 1 到 1800 秒之间。")
        if not 1 <= len(actions) <= 30:
            raise ValueError("一次授权需要 1 到 30 个明确生产动作。")
        normalized = []
        paths = list(allowed_asset_paths or [])
        for source in actions:
            if set(source) - {"tool_name", "arguments", "node_id"}:
                raise ValueError("授权动作包含未声明的确认或范围参数。")
            name = source["tool_name"]
            args = self._arguments(name, source.get("arguments", {}))
            node = self._node(name, args)
            if source.get("node_id") and source["node_id"] != node:
                raise ValueError("节点不属于该工具。")
            if name == "ingest_asset":
                paths.append(args["source_path"])
            normalized.append(WorkflowAction(tool_name=name, arguments=args, node_id=node))
        return self._intent(
            "authorization",
            project_id,
            plan_version,
            actions=[a.model_dump(mode="json") for a in normalized],
            allowed_asset_paths=self.authorization._paths(paths),
            ttl_seconds=ttl_seconds,
        )

    def _intent(self, kind: str, project_id: str, version: int, **data: Any) -> dict[str, Any]:
        intent = {
            "intent_id": "intent-" + uuid4().hex,
            "kind": kind,
            "project_id": project_id,
            "plan_version": version,
            "created_at": self.clock(),
            **data,
        }
        self._intents[intent["intent_id"]] = copy.deepcopy(intent)
        return self._envelope(
            "awaiting_authorization" if kind == "authorization" else "awaiting_review",
            "请在 Agent 对话中确认本轮范围。",
            **intent,
        )

    def _take_intent(self, project_id: str, intent_id: str, kind: str) -> dict[str, Any]:
        with self.projects._lock:
            intent = self._intents.pop(intent_id, None)
            if intent is None or intent["project_id"] != project_id or intent["kind"] != kind:
                raise ValueError("审阅请求不存在、已消费或不属于该项目。")
            if self.clock() - intent["created_at"] > 1800:
                raise ValueError("审阅请求已过期。")
            if self._snapshot(project_id).plan_version != intent["plan_version"]:
                raise ProjectVersionConflict(self._snapshot(project_id))
            return intent

    def apply_authorization(
        self,
        project_id: str,
        intent_id: str,
        *,
        approved: bool,
        ttl_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Trusted native-elicitation callback, deliberately absent from the registry."""
        intent = self._take_intent(project_id, intent_id, "authorization")
        if approved is not True:
            return self._envelope("declined", "本轮生产未获批准。")
        duration = intent["ttl_seconds"] if ttl_seconds is None else ttl_seconds
        if not 0 < duration <= intent["ttl_seconds"]:
            raise ValueError("回复不能扩大授权预算。")
        grant = self.authorization.issue(
            project_id,
            plan_version=intent["plan_version"],
            actions=intent["actions"],
            allowed_asset_paths=intent["allowed_asset_paths"],
            ttl_seconds=duration,
        )
        self._record_plan(
            project_id,
            grant.plan_version,
            self._snapshot(project_id, grant.plan_version).plan,
            "save_project_plan",
        )
        orchestrator = self._orchestrator(project_id, grant.plan_version, register=True)
        if orchestrator is not None:
            in_plan = {
                stage.id
                for stage in self._snapshot(
                    project_id, grant.plan_version
                ).plan.production_pipeline.stages
            }
            covered = {a.node_id for a in grant.actions if a.node_id in in_plan}
            for action in grant.actions:
                if action.tool_name in {"execute_demo", "run_evolution"}:
                    covered.add("optimization_testing")
                if action.tool_name == "run_evolution":
                    covered.add("godot_quick_play")
                if action.tool_name == "execute_assets":
                    if action.arguments.get("with_assets"):
                        covered.add("blender_modeling")
                    if action.arguments.get("with_visuals"):
                        covered.add("comfyui_visual_production")
            orchestrator.confirm(covered & in_plan)
            from fantasy_agent.orchestration_state import save_state

            save_state(
                orchestrator.snapshot(
                    self._snapshot(project_id, grant.plan_version).plan.production_pipeline
                ),
                workspace_root=self._root(project_id, grant.plan_version),
            )
        return self._envelope(
            "authorized",
            "已批准本轮生产，任务会按范围执行一次。",
            grant_id=grant.grant_id,
            expires_at=grant.expires_at,
            project_id=project_id,
            plan_version=grant.plan_version,
        )

    def _production_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        args = copy.deepcopy(arguments)
        project_id, version = args.pop("project_id"), args.pop("plan_version")
        grant_id, request_id = (
            args.pop("grant_id", ""),
            args.pop("request_id", "request-" + uuid4().hex),
        )
        if self.registry.get(name).permission == READ_ONLY:
            run = combined_registry(self._root(project_id, version), use_llm=False)
            snapshot = self._snapshot(project_id, version)
            run.remember_plan(snapshot.plan.model_dump(mode="json"))
            outcome = run.call(name, self._bridge_arguments(project_id, version, name, args))
            return {
                **outcome.data,
                "summary": "本机静态检查已完成。",
                "tool_status": outcome.status,
            }
        return self.execute_tool(
            project_id,
            plan_version=version,
            tool_name=name,
            arguments=args,
            grant_id=grant_id,
            request_id=request_id,
        )

    def execute_tool(
        self,
        project_id: str,
        *,
        plan_version: int,
        tool_name: str,
        arguments: dict[str, Any],
        grant_id: str,
        request_id: str,
        node_id: str = "",
        _rework: bool = False,
        _resume_from: str = "",
        _execution_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        args = self._arguments(tool_name, arguments)
        snapshot = self._snapshot(project_id, plan_version)
        if snapshot.plan is None:
            raise ValueError("项目尚未保存计划。")
        node = self._node(tool_name, args)
        if node_id and node_id != node:
            raise ValueError("节点不属于该生产动作。")
        grant = self.authorization.get_grant(project_id, grant_id, plan_version=plan_version)
        if tool_name == "run_evolution" and grant.expires_at - self.clock() < 30:
            raise ValueError("总预算剩余不足 30 秒，请重新授权实验。")
        if tool_name == "copy_approved_godot_assets":
            self.asset_review.require_approved(project_id, plan_version, args["resource_ids"])
        action = WorkflowAction(tool_name=tool_name, arguments=args, node_id=node)
        paths = [args["source_path"]] if tool_name == "ingest_asset" else []
        claim = self.authorization.claim(
            project_id,
            grant_id=grant_id,
            plan_version=plan_version,
            request_id=request_id,
            action=action,
            asset_paths=paths,
            rework=_rework,
            execution_context=_execution_context,
        )
        if claim.reused:
            return self.get_job(project_id, claim.job.job_id)
        job = self.projects.bind_job_session(
            project_id,
            claim.job.job_id,
            claim.job.execution_context.get("session_id") or f"run-{claim.job.job_id}",
        )
        registry = self._job_registry(job.tool_name)
        captured_plan = snapshot.plan.model_copy(deep=True)

        def work() -> WorkflowResult:
            if not self.authorization.start_job(project_id, job.job_id):
                return WorkflowResult("interrupted", kind=tool_name)
            if self.clock() >= grant.expires_at:
                raise ValueError("生产授权已过期。")
            event = current_cancel_event()
            if event is not None and event.is_set():
                raise ProcessCancelled(tool_name)
            self._begin_job(project_id, job)
            return self._run(project_id, job, captured_plan, args, grant.expires_at, _resume_from)

        registry.submit(
            work,
            job_id=job.job_id,
            deadline=grant.expires_at,
            clock=self.clock,
            on_complete=lambda identifier, payload: self._complete(project_id, job, payload),
        )
        return self._envelope(
            "queued",
            "任务已登记，正在后台执行。",
            project_id=project_id,
            plan_version=plan_version,
            job_id=job.job_id,
            next_actions=[
                {
                    "tool": "get_workflow_job",
                    "arguments": {"project_id": project_id, "job_id": job.job_id},
                }
            ],
        )

    def _job_registry(self, name: str) -> InMemoryJobRegistry:
        if name == "run_evolution":
            return self.evolution_jobs
        if name == "playtest_godot_project":
            return self.playtest_jobs
        if name in {
            "execute_assets",
            "generate_asset_batch",
            "run_visual_reference_workflow",
            "ingest_asset",
        }:
            return self.asset_jobs
        return self.execute_jobs

    def _begin_job(self, project_id: str, job: WorkflowJob) -> None:
        with self.projects._lock:
            orchestrator = self._orchestrator(project_id, job.plan_version, register=True)
            if orchestrator is None:
                return
            pipeline = self.workflow_pipeline(project_id, job.plan_version)
            targets = [
                stage.id
                for stage in pipeline.stages
                if stage.kind != "human" and job.tool_name in stage.mcp_tools
            ]
            if job.tool_name == "execute_assets":
                targets = [
                    name
                    for name in targets
                    if job.arguments.get(
                        "with_assets" if name == "blender_modeling" else "with_visuals"
                    )
                ]
            orchestrator.begin_external_attempt(pipeline, targets)

    def _run(
        self,
        project_id: str,
        job: WorkflowJob,
        plan: DirectorBuildPlan,
        args: dict[str, Any],
        deadline: float,
        resume_from: str,
    ) -> WorkflowResult:
        root = self._root(project_id, job.plan_version)
        remaining = deadline - self.clock()
        name = job.tool_name
        plan = self._asset_plan_for_job(plan, job)
        if name == "execute_demo":
            self._asset_gate(project_id, job.plan_version, name)
            plan = self.asset_review.effective_plan(project_id, job.plan_version)
            data = launch_demo(
                DemoLaunch(
                    plan=plan,
                    confirmed=True,
                    session_id=job.session_id,
                    workspace_root=root,
                    use_llm=False,
                    resume_from=resume_from or None,
                    **{k: v for k, v in args.items() if k != "resume_from"},
                )
            )
            return WorkflowResult(data.status, _json(data), name)
        if name == "execute_assets":
            from fantasy_agent.executor import execute_asset_pipeline

            data = execute_asset_pipeline(
                plan,
                session_id=job.session_id,
                confirmed=True,
                workspace_root=root,
                blender_exe=local_tools._find_blender() or "blender",
                **args,
            )
            result = _json(data)
            wanted = {
                tool
                for tool, enabled in (
                    ("blender", args["with_assets"]),
                    ("comfyui", args["with_visuals"]),
                )
                if enabled
            }
            expected = {
                "blender": [root / item.export_path for item in plan.blender_plan.jobs],
                "comfyui": [root / item.output_path for item in plan.comfyui_plan.jobs],
            }
            for stage in result["stages"]:
                tool = stage["name"]
                if tool in wanted and any(not path.is_file() for path in expected[tool]):
                    stage.update(status="failed", detail="本轮所需资产产物缺失。")
            completed = {stage["name"] for stage in result["stages"] if stage["status"] == "done"}
            successful = wanted <= completed
            if not successful:
                result["status"] = "failed"
                result["detail"] = "本轮所需资产尚未全部生成，请检查制作结果。"
            return WorkflowResult(data.status if successful else "failed", result, name)
        if name == "run_evolution":
            limited = {**args, "max_wall_seconds": min(args["max_wall_seconds"], remaining)}
            data = run_evolution(
                EvolutionRequest(plan=plan, confirmed=True, **limited),
                experiment_id=job.job_id,
                workspace_root=root,
                experience_workspace_root=self.projects.production_workspace(project_id),
            )
            return WorkflowResult(data.status, _json(data), name)
        if name == "ingest_asset":
            from fantasy_agent.asset_library import ingest_asset

            data = ingest_asset(workspace_root=root, **args)
            return WorkflowResult("done", {"entry": _json(data)}, name)
        if name == "copy_approved_godot_assets":
            from fantasy_agent.godot_assets import (
                copy_assets_into_godot_project,
                copy_references_into_godot_project,
            )

            selected = self.asset_review.require_approved(
                project_id, job.plan_version, args["resource_ids"]
            )
            project_file = self._project_file(project_id, job.plan_version, ".godot")
            project_dir = project_file.parent.relative_to(root).as_posix()
            source_paths = [
                self.asset_review.path(project_id, job.plan_version, resource)
                .relative_to(root)
                .as_posix()
                for resource in selected
            ]
            models = copy_assets_into_godot_project(source_paths, project_dir, workspace_root=root)
            images = copy_references_into_godot_project(
                source_paths, project_dir, workspace_root=root
            )
            copied = [*models.copied, *images.copied]
            if not copied:
                raise ValueError("所选素材尚无 Godot 可用格式；请使用 GLB 或图像参考。")
            return WorkflowResult(
                "done",
                {
                    "project_dir": project_dir,
                    "written_files": [(Path(project_dir) / path).as_posix() for path in copied],
                    "copied": copied,
                    "summary": "已复制用户审阅的素材，下一步运行引擎导入与试玩。",
                },
                name,
            )
        self._asset_gate(project_id, job.plan_version, name)
        registry = combined_registry(root, use_llm=False)
        effective = self._asset_plan_for_job(
            self.asset_review.effective_plan(project_id, job.plan_version), job
        )
        registry.remember_plan(effective.model_dump(mode="json"))
        inputs = self._bridge_arguments(project_id, job.plan_version, name, args, job=job)
        outcome = registry.call(
            name,
            inputs,
            allow_write=True,
            allow_execute=True,
        )
        if name == "generate_asset_batch" and outcome.status == "ok":
            exported = outcome.data.get("exported_assets", [])
            if not exported or any(
                not resolve_workspace_path(path, workspace_root=root).is_file() for path in exported
            ):
                outcome.status = "error"
                outcome.content = "本轮资产产物缺失；准备脚本或旧文件不能算作制作成功。"

        return WorkflowResult(
            "done" if outcome.status == "ok" else "failed",
            {
                **outcome.data,
                "tool_name": name,
                "tool_status": outcome.status,
                "detail": outcome.content,
                "execution_inputs": {
                    key: value
                    for key, value in inputs.items()
                    if key in _HIDDEN
                    and key not in {"plan", "gameplay_spec", "production_spec_bundle"}
                },
            },
            name,
        )

    def _asset_plan_for_job(self, plan: DirectorBuildPlan, job: WorkflowJob) -> DirectorBuildPlan:
        """Isolate actual asset outputs; the immutable saved plan remains intact."""
        result = plan.model_copy(deep=True)
        if job.tool_name in {"execute_assets", "generate_blender_script", "generate_asset_batch"}:
            for item in result.blender_plan.jobs:
                original = Path(item.export_path.replace("\\", "/"))
                relative = original.relative_to("generated/assets")
                item.export_path = (
                    Path("generated/assets/workflow") / job.job_id / relative
                ).as_posix()
        if job.tool_name in {
            "execute_assets",
            "prepare_visual_reference_workflows",
            "run_visual_reference_workflow",
        }:
            for item in result.comfyui_plan.jobs:
                original = Path(item.output_path.replace("\\", "/"))
                relative = original.relative_to("generated/comfyui")
                item.output_path = (
                    Path("generated/comfyui/workflow") / job.job_id / relative
                ).as_posix()
        return result

    def _resource_path(self, project_id: str, resource: Any) -> Path:
        path = resolve_workspace_path(
            resource.path, workspace_root=self.projects.production_workspace(project_id)
        )
        if not path.is_file() or (resource.sha256 and _hash(path) != resource.sha256):
            raise ValueError("产物内容已变化，请重新生成并读取当前版本。")
        return path

    def _project_file(self, project_id: str, version: int, suffix: str) -> Path:
        snapshot = self._snapshot(project_id, version)
        producers = {
            job.job_id
            for job in snapshot.jobs
            if job.plan_version == version
            and job.tool_name
            in {"create_godot_project_structure", "create_project_structure", "execute_demo"}
            and (
                job.status == "done"
                or {"create", "validate"}
                <= {
                    stage.get("name")
                    for stage in worker_data(job.result).get("stages", [])
                    if stage.get("status") == "done"
                }
            )
        }
        resource = next(
            (
                item
                for item in reversed(snapshot.resources)
                if item.plan_version == version
                and item.job_id in producers
                and (
                    Path(item.path).name == "project.godot"
                    if suffix == ".godot"
                    else Path(item.path).suffix == suffix
                )
            ),
            None,
        )
        if resource is None:
            raise ValueError("先生成本项目当前版本的引擎工程。")
        return self._resource_path(project_id, resource)

    def _manifest_output(
        self,
        project_id: str,
        version: int,
        producers: set[str],
        model: Any,
        *,
        project_file: str = "",
    ):
        """Read a typed manifest only from a completed producer's registered outputs."""
        snapshot = self._snapshot(project_id, version)
        root = self._root(project_id, version)
        for job in reversed(snapshot.jobs):
            if (
                job.plan_version != version
                or job.tool_name not in producers
                or job.status != "done"
            ):
                continue
            for resource in reversed(snapshot.resources):
                if resource.job_id != job.job_id or Path(resource.path).suffix not in {
                    ".json",
                    ".yaml",
                    ".yml",
                }:
                    continue
                path = self._resource_path(project_id, resource)
                if path.stat().st_size > _MAX_RESOURCE_BYTES:
                    raise ValueError("交接清单过大，请重新生成。")
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8"))
                    manifest = model.model_validate(data)
                except ValidationError:
                    # A producer may return several different typed artifacts.
                    continue
                if project_file and manifest.project_file != project_file:
                    continue
                return path.relative_to(root).as_posix(), manifest
        return None

    def _bridge_arguments(
        self,
        project_id: str,
        version: int,
        name: str,
        args: dict[str, Any],
        *,
        job: WorkflowJob | None = None,
    ) -> dict[str, Any]:
        result = copy.deepcopy(args)
        snapshot = self._snapshot(project_id, version)
        root = self._root(project_id, version)
        spec = self._engine_specs[name]
        properties = spec.input_schema.get("properties", {})
        if job and name in {"generate_blender_script", "generate_asset_batch"}:
            result["script_path"] = f"generated/blender/workflow/{job.job_id}/produce.py"
            result["import_manifest_path"] = (
                f"generated/blender/workflow/{job.job_id}/import-manifest.yaml"
            )
        if job and name in {"prepare_visual_reference_workflows", "run_visual_reference_workflow"}:
            result["output_dir"] = f"generated/comfyui/workflow/{job.job_id}"
        if name in {"create_godot_project_structure", "create_project_structure"}:
            session_id = job.session_id if job else f"workflow-v{version}"
            engine = "godot" if name == "create_godot_project_structure" else "unreal"
            plan = snapshot.plan.godot_plan if engine == "godot" else snapshot.plan.unreal_plan
            assert_safe_path_segment(plan.project_name, label="project_name")
            result["project_dir"] = f"generated/{engine}/sessions/{session_id}/{plan.project_name}"
        if name in {"validate_godot_project", "run_godot_import", "playtest_godot_project"}:
            resolved = self._project_file(project_id, version, ".godot")
            target = resolved.parent if name == "playtest_godot_project" else resolved
            result["project_dir" if name == "playtest_godot_project" else "project_file"] = (
                target.relative_to(root).as_posix()
            )
        if name in {
            "prepare_asset_ingest",
            "prepare_level_assembly",
            "run_asset_ingest",
            "run_editor_commandlet",
            "run_level_assembly",
            "validate_asset_ingest",
            "validate_level_assembly",
        }:
            project_file = (
                self._project_file(project_id, version, ".uproject").relative_to(root).as_posix()
            )
            if "project_file" in properties:
                result["project_file"] = project_file
            if name == "prepare_asset_ingest":
                for key, producers, model in (
                    (
                        "blender_import_manifest_path",
                        {"generate_asset_batch", "execute_assets"},
                        UnrealImportManifest,
                    ),
                    (
                        "comfyui_run_manifest_path",
                        {"run_visual_reference_workflow", "execute_assets"},
                        ComfyUIRunManifest,
                    ),
                ):
                    source = self._manifest_output(project_id, version, producers, model)
                    if source:
                        result[key] = source[0]
                if not any(
                    result.get(key)
                    for key in ("blender_import_manifest_path", "comfyui_run_manifest_path")
                ):
                    raise ValueError("先完成资产制作并审阅实际产物，再准备引擎导入。")
            if name in {"validate_asset_ingest", "prepare_level_assembly", "run_asset_ingest"}:
                source = self._manifest_output(
                    project_id,
                    version,
                    {"prepare_asset_ingest", "execute_demo"},
                    UnrealAssetIngestManifest,
                    project_file=project_file,
                )
                if source is None:
                    raise ValueError("先为当前工程准备资产导入交接。")
                if "ingest_manifest_path" in properties:
                    result["ingest_manifest_path"] = source[0]
                if "import_script_path" in properties:
                    result["import_script_path"] = source[1].import_script_path
            if name in {"validate_level_assembly", "run_level_assembly"}:
                source = self._manifest_output(
                    project_id,
                    version,
                    {"prepare_level_assembly", "execute_demo"},
                    UnrealLevelAssemblyManifest,
                    project_file=project_file,
                )
                if source is None:
                    raise ValueError("先为当前工程准备关卡组装交接。")
                if "level_manifest_path" in properties:
                    result["level_manifest_path"] = source[0]
                if "assembly_script_path" in properties:
                    result["assembly_script_path"] = source[1].assembly_script_path
        if name == "run_editor_commandlet":
            result["commandlet"] = "DataValidation"
        if "allow_remote_endpoint" in properties:
            result["allow_remote_endpoint"] = False
        if name == "run_visual_reference_workflow":
            result["wait_for_completion"] = True
        return result

    def _complete(self, project_id: str, job: WorkflowJob, payload: dict[str, Any]) -> None:
        prior = next(item for item in self._snapshot(project_id).jobs if item.job_id == job.job_id)
        if prior.status == "interrupted":
            return
        root = self._root(project_id, job.plan_version)
        payload = self._preserve_job_logs(root, job, payload)
        for reported in self._reported_paths(payload, prepared=job.tool_name in PREPARATIONS):
            path = resolve_workspace_path(reported, workspace_root=root, allow_absolute=True)
            if path.is_dir():
                # Only a directory explicitly returned by this worker may be expanded.
                paths = path.rglob("*")
            else:
                paths = [path]
            for path in paths:
                if not path.is_file() or any(
                    part in {".godot", "__pycache__"} for part in path.parts
                ):
                    continue
                if path.name.startswith("_") or _private_path(path.relative_to(root)):
                    continue
                checked = resolve_workspace_path(
                    str(path),
                    workspace_root=self.projects.production_workspace(project_id),
                    allow_absolute=True,
                )
                relative = checked.relative_to(
                    self.projects.production_workspace(project_id)
                ).as_posix()
                digest = _hash(checked)
                rid = (
                    "artifact-"
                    + hashlib.sha256((job.job_id + relative + digest).encode()).hexdigest()[:24]
                )
                self.projects.register_resource(
                    project_id,
                    resource_id=rid,
                    path=relative,
                    kind=(
                        "asset"
                        if path.suffix.lower() in _ASSET_SUFFIXES
                        and job.tool_name != "copy_approved_godot_assets"
                        else "imported_asset"
                        if path.suffix.lower() in _ASSET_SUFFIXES
                        else "artifact"
                    ),
                    asset_key=self._asset_key(job, checked.relative_to(root).as_posix()),
                    plan_version=job.plan_version,
                    job_id=job.job_id,
                    sha256=digest,
                    mime_type="text/plain"
                    if path.suffix.lower()
                    in {".godot", ".gd", ".tscn", ".tres", ".yaml", ".yml", ".cfg", ".ini"}
                    else mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                )
        status = payload.get("status", "failed")
        if status not in {"done", "failed", "cancelled", "interrupted"}:
            status = "failed"
        self._observe(project_id, job.plan_version, job.tool_name, payload, job.job_id)
        self.projects.update_job(
            project_id, job.job_id, status=status, result=_json(payload), session_id=job.session_id
        )

    @staticmethod
    def _asset_key(job: WorkflowJob, path: str) -> str:
        for source, folder in (("blender", "assets"), ("comfyui", "comfyui")):
            prefix = f"generated/{folder}/workflow/{job.job_id}/"
            if path.startswith(prefix):
                return f"{source}:{path.removeprefix(prefix)}"
        return ""

    def _preserve_job_logs(
        self, root: Path, job: WorkflowJob, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Snapshot reported logs and experiment reports before their later updates."""
        replacements = {}
        for reported in self._reported_paths(payload):
            source = resolve_workspace_path(reported, workspace_root=root, allow_absolute=True)
            relative = source.relative_to(root)
            experiment_report = (
                job.tool_name == "run_evolution"
                and relative.parts[:3] == ("generated", "evolution", "experiments")
                and source.suffix == ".json"
            )
            if not source.is_file() or (source.suffix != ".log" and not experiment_report):
                continue
            folder = "workflow-job-artifacts" if experiment_report else "workflow-job-logs"
            target = resolve_workspace_path(
                (Path("generated") / folder / job.job_id / relative).as_posix(),
                workspace_root=root,
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            replacements[reported] = target.relative_to(root).as_posix()

        def replace(value: Any) -> Any:
            if isinstance(value, str):
                return replacements.get(value, value)
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace(item) for item in value]
            return value

        return replace(payload)

    @staticmethod
    def _reported_paths(payload: dict[str, Any], *, prepared: bool = False) -> list[str]:
        """Catalog actual output fields, never all files in a version workspace."""
        lists = {
            "written_files",
            "artifacts",
            "artifact_paths",
            "exported_assets",
            "generated_images",
            "outputs",
            "log_paths",
            "logs",
            "workflow_files",
        }
        singles = {
            "stdout_path",
            "stderr_path",
            "report_path",
            "manifest_path",
            "import_manifest_path",
            "ingest_manifest_path",
            "level_manifest_path",
            "script_path",
            "playtest_report_path",
        }
        inputs = {
            "plan",
            "original_plan",
            "inputs",
            "gameplay_spec",
            "production_spec_bundle",
            "next_actions",
            "planned_side_effects",
            "request",
        }
        found: set[str] = set()

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in inputs or (prepared and key == "generated_images"):
                        continue
                    if key in singles and isinstance(child, str) and child:
                        found.add(child)
                    elif key in lists and isinstance(child, list):
                        found.update(item for item in child if isinstance(item, str) and item)
                    elif (
                        key == "entry"
                        and isinstance(child, dict)
                        and isinstance(child.get("path"), str)
                    ):
                        found.add(child["path"])
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(payload)
        return sorted(found)

    def get_job(self, project_id: str, job_id: str) -> dict[str, Any]:
        snapshot = self._snapshot(project_id)
        job = next((item for item in snapshot.jobs if item.job_id == job_id), None)
        if job is None:
            raise ValueError("任务不属于该项目或不存在。")
        memory = self._job_registry(job.tool_name).status(job_id)
        status = (
            job.status
            if job.status in {"done", "failed", "cancelled", "interrupted"}
            else (memory["status"] if memory["status"] != "unknown" else job.status)
        )
        result = job.result or (memory if memory["status"] != "unknown" else {})
        refs = [
            self._ref(project_id, resource)
            for resource in snapshot.resources
            if resource.job_id == job_id
        ]
        logs = []
        root = self._root(project_id, job.plan_version)
        for resource in snapshot.resources:
            if resource.job_id != job_id or Path(resource.path).suffix != ".log":
                continue
            checked = resolve_workspace_path(
                resource.path, workspace_root=self.projects.production_workspace(project_id)
            )
            if not checked.is_file() or (resource.sha256 and _hash(checked) != resource.sha256):
                continue
            with checked.open("rb") as stream:
                stream.seek(max(0, checked.stat().st_size - 4096))
                logs.append(stream.read(4096).decode("utf-8", errors="replace"))
            if len(logs) == 3:
                break
        engine = "unreal" if job.arguments.get("engine") == "unreal" else "godot"
        state = (
            load_pipeline_state(job.session_id, workspace_root=root, engine_key=engine)
            if job.session_id
            else None
        )
        data = worker_data(result)
        blockers = [result["error"]] if result.get("error") else []
        if status == "failed":
            blockers.extend(
                stage.get("detail", "")
                for stage in data.get("stages", [])
                if stage.get("status") in {"failed", "blocked"}
            )
            blockers.extend(
                item.get("message", "")
                for item in data.get("preflight_issues", [])
                if item.get("severity") == "blocking"
            )
            if not blockers:
                blockers.extend(
                    [
                        data.get("stderr_tail", ""),
                        data.get("detail", "任务未通过真实执行与产物检查。"),
                    ]
                )
        blockers = list(dict.fromkeys(item for item in blockers if item))
        next_actions: list[Any] = []
        if status in {"queued", "running"}:
            next_actions = [
                {
                    "tool": "get_workflow_job",
                    "arguments": {"project_id": project_id, "job_id": job_id},
                    "summary": "继续查询本任务的进度。",
                }
            ]
        elif status in {"failed", "cancelled", "interrupted"}:
            next_actions = [
                "读取阻塞原因并修正；节点续跑使用 rework_node，授权过期时重新确认本轮范围。"
            ]
        elif (
            job.tool_name == "run_evolution"
            and data.get("report", {}).get("status") == "improved"
            and data["report"].get("adopted_iteration") is None
        ):
            next_actions = [
                {
                    "tool": "request_candidate_adoption",
                    "arguments": {
                        "project_id": project_id,
                        "plan_version": job.plan_version,
                        "job_id": job_id,
                    },
                    "summary": "待采纳：比较实验结果后，由用户决定是否采纳本候选。",
                }
            ]
        elif job.tool_name in PREPARATIONS:
            next_actions = ["准备文件已写入；确认下一项生产动作后再启动制作或引擎执行。"]
        elif any(resource["kind"] == "asset" for resource in refs):
            next_actions = [
                {
                    "tool": "request_asset_review",
                    "arguments": {
                        "project_id": project_id,
                        "plan_version": job.plan_version,
                        "resource_ids": [
                            ref["resource_id"] for ref in refs if ref["kind"] == "asset"
                        ],
                    },
                    "summary": "请用户审阅本轮实际产物，再进入引擎导入。",
                }
            ]
        else:
            next_actions = ["读取工作流状态，根据实测结果安排下一步。"]
        return self._envelope(
            status,
            {
                "queued": "任务已排队。",
                "running": "任务正在执行。",
                "done": "任务已完成。",
                "failed": "任务未完成，请检查阻塞原因。",
                "cancelled": "任务已取消。",
                "interrupted": "Studio 已重启，旧任务未重放。",
            }.get(status, status),
            project_id=project_id,
            plan_version=job.plan_version,
            job_id=job_id,
            tool_name=job.tool_name,
            session_id=job.session_id,
            result=result.get("result", result),
            resources=refs,
            logs=logs,
            progress=_json(state) if state else None,
            blockers=blockers,
            next_actions=next_actions,
        )

    def cancel_job(self, project_id: str, job_id: str) -> dict[str, Any]:
        job = next((j for j in self._snapshot(project_id).jobs if j.job_id == job_id), None)
        if job is None:
            raise ValueError("任务不存在。")
        if job.status in {"done", "failed", "cancelled", "interrupted"}:
            return self.get_job(project_id, job_id)
        response = self._job_registry(job.tool_name).cancel(job_id)
        return self._envelope(
            response["status"], "已请求取消任务。", project_id=project_id, job_id=job_id
        )

    def recover_interrupted(self) -> None:
        """Only invoked at Studio startup after the previous process has stopped."""
        for project in self.projects.list_projects():
            self.projects.mark_interrupted_jobs(project.project_id)
            versions = {project.plan_version, *(job.plan_version for job in project.jobs)}
            for version in sorted(versions):
                orchestrator = self._orchestrator(project.project_id, version, register=True)
                if orchestrator is not None:
                    orchestrator.interrupt_external_attempts(
                        self.workflow_pipeline(project.project_id, version)
                    )
            for decision in project.decisions.values():
                if (
                    decision.get("kind") == "candidate_adoption"
                    and decision.get("status") == "approved"
                ):
                    self._repair_adoption_projections(project.project_id, decision)

    def submit_ui_job(
        self,
        project_id: str,
        *,
        plan_version: int,
        tool_name: str,
        arguments: dict[str, Any],
        worker: Callable[[], Any],
        confirmed_by_user: bool,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Trusted UI callback. Its boolean comes from the existing confirmation button.

        This method is deliberately absent from the external tool registry. UI
        approvals use the same durable, finite server ledger as MCP approvals.
        """
        if confirmed_by_user is not True:
            raise ValueError("需要界面上的用户确认。")
        snapshot = self._snapshot(project_id)
        if snapshot.plan_version != plan_version:
            raise ProjectVersionConflict(snapshot)
        action = WorkflowAction(
            tool_name=tool_name,
            arguments=_json(arguments),
            node_id=self._node(tool_name, arguments),
        )
        grant = self.authorization.issue(project_id, plan_version=plan_version, actions=[action])
        claim = self.authorization.claim(
            project_id,
            grant_id=grant.grant_id,
            plan_version=plan_version,
            request_id=f"ui-{uuid4().hex}",
            action=action,
            execution_context={"source": "studio_ui"},
        )
        job = self.projects.bind_job_session(
            project_id, claim.job.job_id, session_id or f"run-{claim.job.job_id}"
        )

        def run():
            if not self.authorization.start_job(project_id, job.job_id):
                return WorkflowResult("interrupted", kind=tool_name)
            self._begin_job(project_id, job)
            return worker()

        self._job_registry(tool_name).submit(
            run,
            job_id=job.job_id,
            deadline=grant.expires_at,
            clock=self.clock,
            on_complete=lambda identifier, payload: self._complete(project_id, job, payload),
        )
        return {
            "status": "running",
            "job_id": job.job_id,
            "project_id": project_id,
            "plan_version": plan_version,
            "session_id": job.session_id,
        }

    def locate_job(self, job_id: str) -> tuple[str, WorkflowJob] | None:
        """Resolve legacy UI task URLs without restoring or scheduling workers."""
        assert_safe_path_segment(job_id, label="job_id")
        for project in self.projects.list_projects():
            for job in project.jobs:
                if job.job_id == job_id or (
                    job.tool_name == "run_evolution"
                    and job.arguments.get("experiment_id") == job_id
                ):
                    return project.project_id, job
        return None

    def rework_node(
        self,
        project_id: str,
        *,
        plan_version: int,
        job_id: str,
        resume_from: str,
        request_id: str | None = None,
        grant_id: str | None = None,
    ) -> dict[str, Any]:
        job = next((j for j in self._snapshot(project_id).jobs if j.job_id == job_id), None)
        if (
            job is None
            or job.plan_version != plan_version
            or job.status not in {"done", "failed", "cancelled", "interrupted"}
        ):
            raise ValueError("返工需要本版本的已结束任务。")
        if job.tool_name != "execute_demo" or job.arguments.get("engine") != "godot":
            raise ValueError("首轮节点续跑只支持 Godot 执行任务。")
        from fantasy_agent.pipeline_state import normalize_resume_from

        target = normalize_resume_from(resume_from)
        return self.execute_tool(
            project_id,
            plan_version=plan_version,
            tool_name=job.tool_name,
            arguments=job.arguments,
            grant_id=grant_id or job.grant_id,
            request_id=request_id or "rework-" + uuid4().hex,
            _rework=True,
            _resume_from=target,
            _execution_context={
                "resume_from": target,
                "source_job_id": job_id,
                "session_id": job.session_id,
            },
        )

    @staticmethod
    def _virtual_ref(project_id: str, resource_id: str) -> dict[str, Any]:
        return {
            "resource_id": resource_id,
            "uri": f"studio://projects/{project_id}/{resource_id}",
            "mime_type": "application/json",
        }

    def _ref(self, project_id: str, resource: Any) -> dict[str, Any]:
        return {
            **resource.model_dump(mode="json"),
            "uri": f"studio://projects/{project_id}/{resource.resource_id}",
        }

    def resources(self, project_id: str) -> list[dict[str, Any]]:
        snapshot = self._snapshot(project_id)
        return [
            self._virtual_ref(project_id, "snapshot"),
            *(
                [self._virtual_ref(project_id, f"plan-v{snapshot.plan_version}")]
                if snapshot.plan
                else []
            ),
            *[self._virtual_ref(project_id, job.job_id) for job in snapshot.jobs],
            *[
                self._ref(project_id, resource)
                for resource in snapshot.resources
                if not _private_path(resource.path)
            ],
        ]

    def read_resource(self, project_id: str, resource_id: str) -> dict[str, Any]:
        assert_safe_path_segment(resource_id, label="resource_id")
        snapshot = self._snapshot(project_id)
        if resource_id == "snapshot":
            return {"data": self.snapshot(project_id), "mime_type": "application/json"}
        if resource_id.startswith("plan-v"):
            version = int(resource_id[6:])
            return {
                "data": self._snapshot(project_id, version).plan.model_dump(mode="json"),
                "mime_type": "application/json",
            }
        if any(job.job_id == resource_id for job in snapshot.jobs):
            return {"data": self.get_job(project_id, resource_id), "mime_type": "application/json"}
        resource = next((r for r in snapshot.resources if r.resource_id == resource_id), None)
        if resource is None:
            raise ValueError("产物不属于该项目或不存在。")
        if _private_path(resource.path):
            raise ValueError("凭据和决策配置不能作为产物资源读取。")
        path = resolve_workspace_path(
            resource.path, workspace_root=self.projects.production_workspace(project_id)
        )
        if not path.is_file() or path.stat().st_size > _MAX_RESOURCE_BYTES:
            raise ValueError("产物不存在或过大，请使用本机编辑器查看。")
        if resource.sha256 and _hash(path) != resource.sha256:
            raise ValueError("产物内容已变化，请读取新的产物版本并重新审阅。")
        raw = path.read_bytes()
        try:
            data = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "data": base64.b64encode(raw).decode(),
                "encoding": "base64",
                "mime_type": resource.mime_type,
            }
        return {"data": data, "mime_type": resource.mime_type}

    def snapshot(self, project_id: str, version: int | None = None) -> dict[str, Any]:
        snapshot = self._snapshot(project_id, version)
        data = snapshot.model_dump(mode="json")
        data["creative_review"] = _json(self.asset_review.review_report(snapshot))
        data["authorizations"] = [
            {
                "grant_id": grant.grant_id,
                "plan_version": grant.plan_version,
                "expires_at": grant.expires_at,
                "remaining_seconds": max(0, grant.expires_at - self.clock()),
                "active": grant.plan_version == data["plan_version"]
                and grant.issued_at <= self.clock() < grant.expires_at,
                "actions": [a.model_dump(mode="json") for a in grant.actions],
                "uses": len(grant.uses),
            }
            for grant in self.authorization.grants(project_id)
        ]
        return data

    def _orchestrator(
        self, project_id: str, version: int, *, register: bool = False
    ) -> Orchestrator | None:
        key = (project_id, version)
        if key in self._orchestrators:
            return self._orchestrators[key]
        snapshot = self._snapshot(project_id, version)
        if snapshot.plan is None or snapshot.plan.production_pipeline is None:
            return None
        root = self._root(project_id, version)
        registry = combined_registry(root, use_llm=False)
        registry.remember_plan(snapshot.plan.model_dump(mode="json"))
        engine = (
            "godot"
            if any(s.id == "godot_quick_play" for s in snapshot.plan.production_pipeline.stages)
            else "unreal"
        )
        orchestrator = Orchestrator(
            session_id=f"workflow-v{version}",
            workspace_root=root,
            engine_key=engine,
            registry=registry,
        )
        restored = load_state(orchestrator.session_id, engine_key=engine, workspace_root=root)
        if restored is not None:
            orchestrator = Orchestrator.restore(
                restored,
                plan=ProductionPipeline.model_validate(restored.plan),
                workspace_root=root,
                registry=registry,
            )
        if register:
            self._orchestrators[key] = orchestrator
        return orchestrator

    def workflow_pipeline(self, project_id: str, version: int) -> ProductionPipeline:
        snapshot = self._snapshot(project_id, version)
        return external_pipeline(
            snapshot.plan.production_pipeline,
            [job for job in snapshot.jobs if job.plan_version == version],
        )

    def _observe(
        self, project_id: str, version: int, name: str, payload: dict[str, Any], job_id: str
    ) -> None:
        orchestrator = self._orchestrator(project_id, version, register=True)
        if orchestrator is None:
            return
        snapshot = self._snapshot(project_id, version)
        stages = self.workflow_pipeline(project_id, version)
        refs = [r for r in snapshot.resources if r.plan_version == version and r.job_id == job_id]
        files = [str(self.projects.production_workspace(project_id) / r.path) for r in refs]
        data = worker_data(payload)
        project_file = next((path for path in files if Path(path).name == "project.godot"), None)
        if project_file is None:
            actual = data.get("project_dir") or data.get("execution_inputs", {}).get("project_dir")
            if actual:
                candidate = (
                    resolve_workspace_path(
                        actual, workspace_root=self._root(project_id, version), allow_absolute=True
                    )
                    / "project.godot"
                )
                project_file = str(candidate) if candidate.is_file() else None
            elif data.get("execution_inputs", {}).get("project_file"):
                candidate = resolve_workspace_path(
                    data["execution_inputs"]["project_file"],
                    workspace_root=self._root(project_id, version),
                    allow_absolute=True,
                )
                project_file = (
                    str(candidate)
                    if candidate.name == "project.godot" and candidate.is_file()
                    else None
                )
        checks = (
            {
                "validate_godot_project": {
                    "project_file": Path(project_file)
                    .relative_to(self._root(project_id, version))
                    .as_posix()
                }
            }
            if project_file
            else {}
        )
        evidence_items = evidence_for(name, data, stages)
        if payload.get("status") in {"failed", "cancelled", "interrupted"} and not evidence_items:
            evidence_items = [
                StageEvidence(
                    stage.id,
                    False,
                    payload.get("error") or data.get("detail") or "本轮任务未完成。",
                )
                for stage in stages.stages
                if stage.kind != "human" and name in stage.mcp_tools
            ]
        for evidence in evidence_items:
            try:
                result = ToolOutcome(
                    name,
                    "ok" if evidence.ok else "error",
                    evidence.detail,
                    data,
                )
                observed_files = files or ([project_file] if project_file else [])
                orchestrator.accept_external_result(
                    stages,
                    evidence.stage_id,
                    result,
                    artifacts=observed_files,
                    prepared=evidence.prepared,
                    check_arguments=checks,
                )
            except ValueError as exc:
                # A prepared project can exist before all production dependencies;
                # its finished job stays truthful, and its card stops running.
                orchestrator.block_external_attempt(
                    stages,
                    evidence.stage_id,
                    ToolOutcome(name, "error", str(exc), data),
                )

    def workflow_state(self, project_id: str, version: int | None = None) -> dict[str, Any]:
        snapshot = self._snapshot(project_id, version)
        orchestrator = self._orchestrator(project_id, snapshot.plan_version)
        if orchestrator is None:
            return {
                "project_id": project_id,
                "plan_version": snapshot.plan_version,
                "status": "empty",
                "stages": [],
            }
        pipeline = self.workflow_pipeline(project_id, snapshot.plan_version)
        state = orchestrator.snapshot(pipeline)
        stages = []
        for stage in pipeline.stages:
            outcome = next((item for item in state.stages if item.stage_id == stage.id), None)
            status = "ready"
            if any(
                orchestrator.outcomes.get(dep) is None
                or orchestrator.outcomes[dep].status != "done"
                for dep in stage.depends_on
            ):
                status = "blocked"
            elif stage.kind == "human":
                status = "awaiting_human"
            elif stage.requires_confirmation and stage.id not in orchestrator.confirmed:
                status = "awaiting_confirmation"
            stages.append(
                {
                    **stage.model_dump(mode="json"),
                    "stage_id": stage.id,
                    **(_json(outcome) if outcome else asdict(StageOutcome(stage.id, status))),
                    "confirmed": stage.id in orchestrator.confirmed,
                    "human_resolution": orchestrator.human_decisions.get(stage.id),
                    "executor_stages": list(executor_stages_for(stage.id)),
                }
            )
        statuses = {stage["status"] for stage in stages}
        status = next(
            (
                value
                for value in (
                    "failed",
                    "running",
                    "awaiting_human",
                    "awaiting_confirmation",
                    "blocked",
                    "ready",
                )
                if value in statuses
            ),
            "done",
        )
        return {
            "project_id": project_id,
            "plan_version": snapshot.plan_version,
            "session_id": orchestrator.session_id,
            "engine": orchestrator.engine_key,
            "status": "error" if status == "failed" else status,
            "goal": pipeline.goal,
            "project_name": pipeline.project_name,
            "stage_translation": {
                key: list(value) for key, value in ORCHESTRATION_TO_EXECUTOR_STAGES.items()
            },
            "pending_confirmations": orchestrator.pending_confirmations(pipeline),
            "human_decisions": orchestrator.human_decisions,
            "stages": stages,
            "confirmed": sorted(orchestrator.confirmed),
            "pending_human_gates": orchestrator.pending_human_gates(pipeline),
            "authorizations": self.snapshot(project_id)["authorizations"],
        }

    def request_asset_review(
        self, project_id: str, *, plan_version: int, resource_ids: list[str]
    ) -> dict[str, Any]:
        snapshot = self._snapshot(project_id, plan_version)
        active = self.asset_review.active_assets(snapshot, plan_version)
        if not resource_ids:
            raise ValueError("请选择本版本实际生成的资产。")
        subjects = []
        for rid in resource_ids:
            resource = next(
                (r for r in active if r.resource_id == rid and r.plan_version == plan_version),
                None,
            )
            if resource is None or Path(resource.path).suffix.lower() not in _ASSET_SUFFIXES:
                raise ValueError("请选择本版本实际生成的资产。")
            self.asset_review.path(project_id, plan_version, resource)
            subjects.append(self._ref(project_id, resource))
        return self._intent("asset_review", project_id, plan_version, subjects=subjects)

    def apply_asset_review(
        self,
        project_id: str,
        intent_id: str,
        *,
        approved: bool,
        feedback: str = "",
        decision: str | None = None,
    ) -> dict[str, Any]:
        intent = self._take_intent(project_id, intent_id, "asset_review")
        for subject in intent["subjects"]:
            path = resolve_workspace_path(
                subject["path"], workspace_root=self.projects.production_workspace(project_id)
            )
            if _hash(path) != subject["sha256"]:
                raise ValueError("用户审阅的资产版本已变化。")
        status = (
            decision if decision is not None else ("approved" if approved is True else "rejected")
        )
        if status not in {"approved", "rejected", "needs_revision"} or (status == "approved") != (
            approved is True
        ):
            raise ValueError("审阅决定无效。")
        decision = {
            "kind": "asset_review",
            "plan_version": intent["plan_version"],
            "status": status,
            "subjects": intent["subjects"],
            "feedback": feedback,
            "created_at": self.clock(),
        }
        self.projects.save_decision(project_id, intent_id, decision)
        self.asset_review.write_manifest(project_id, intent["plan_version"])
        self._sync_asset_gate(project_id, intent["plan_version"])
        return self._envelope(decision["status"], "资产审阅决定已保存。", project_id=project_id)

    def _sync_asset_gate(self, project_id: str, version: int) -> None:
        snapshot = self._snapshot(project_id, version)
        resources = self.asset_review.active_assets(snapshot, version)
        if not resources:
            return
        statuses = [self.asset_review.decision(snapshot, resource) for resource in resources]
        if "pending_user_review" in statuses:
            return
        for resource in resources:
            self.asset_review.path(project_id, version, resource)
        orchestrator = self._orchestrator(project_id, version, register=True)
        if orchestrator is None:
            return
        try:
            orchestrator.accept_external_human_decision(
                self.workflow_pipeline(project_id, version),
                "creative_review",
                "approved" if all(status == "approved" for status in statuses) else "rejected",
            )
        except ValueError:
            # A real review can precede a separate producer's completion. It
            # remains in the decision ledger and is redeemed after that result.
            return

    def _asset_gate(self, project_id: str, version: int, name: str) -> None:
        if name not in {
            "execute_demo",
            "run_godot_import",
            "prepare_asset_ingest",
            "run_asset_ingest",
            "run_level_assembly",
        }:
            return
        self.asset_review.require_approved(project_id, version)

    def request_candidate_adoption(
        self, project_id: str, *, plan_version: int, job_id: str
    ) -> dict[str, Any]:
        snapshot = self._snapshot(project_id)
        if snapshot.plan_version != plan_version:
            raise ProjectVersionConflict(snapshot)
        if any(
            decision.get("kind") == "candidate_adoption"
            and decision.get("status") == "approved"
            and decision.get("job_id") == job_id
            for decision in snapshot.decisions.values()
        ):
            raise ValueError("该候选已有用户采纳决定。")
        job = next((j for j in snapshot.jobs if j.job_id == job_id), None)
        if (
            job is None
            or job.tool_name != "run_evolution"
            or job.plan_version != plan_version
            or job.status != "done"
        ):
            raise ValueError("请选择本版本已完成的反馈进化实验。")
        report = load_report(job_id, workspace_root=self._root(project_id, plan_version))
        if report is None or report.status != "improved" or report.best_iteration is None:
            raise ValueError("实验尚无可采纳的实测改进。")
        digest = hashlib.sha256(report.model_dump_json().encode()).hexdigest()
        winner = next(i for i in report.iterations if i.index == report.best_iteration)
        return self._intent(
            "candidate_adoption",
            project_id,
            plan_version,
            job_id=job_id,
            subject_sha256=digest,
            candidate_index=winner.index,
            changes=_json(winner.changes),
            measurement=_json(winner.report),
            risks=report.risks,
        )

    def apply_candidate_adoption(
        self, project_id: str, intent_id: str, *, approved: bool, feedback: str = ""
    ) -> dict[str, Any]:
        with self.projects._lock:
            intent = self._take_intent(project_id, intent_id, "candidate_adoption")
            if approved is not True:
                return self._envelope("declined", "当前候选未被采纳。")
            root = self._root(project_id, intent["plan_version"])
            report = load_report(intent["job_id"], workspace_root=root)
            if (
                report is None
                or hashlib.sha256(report.model_dump_json().encode()).hexdigest()
                != intent["subject_sha256"]
            ):
                raise ValueError("用户审阅的候选已变化。")
            updated, experience, adopted_report = prepare_evolution_adoption(
                intent["job_id"],
                self._snapshot(project_id).plan,
                workspace_root=root,
                feedback=feedback,
                experience_workspace_root=self.projects.production_workspace(project_id),
            )
            job = next(
                item for item in self._snapshot(project_id).jobs if item.job_id == intent["job_id"]
            )
            report_text = adopted_report.model_dump_json(indent=2)
            digest = hashlib.sha256(report_text.encode("utf-8")).hexdigest()
            report_path = f"generated/workflow-job-artifacts/{job.job_id}/adopted-{digest}.json"
            write_atomic(root / report_path, report_text)
            relative = (
                (root / report_path)
                .relative_to(self.projects.production_workspace(project_id))
                .as_posix()
            )
            resource = ProjectResource(
                resource_id="artifact-"
                + hashlib.sha256((job.job_id + relative + digest).encode()).hexdigest()[:24],
                path=relative,
                plan_version=job.plan_version,
                job_id=job.job_id,
                sha256=digest,
                mime_type="application/json",
            )
            result = copy.deepcopy(job.result)
            data = worker_data(result)
            data["report"] = _json(adopted_report)
            data["report_path"] = report_path
            data["written_files"] = [*data.get("written_files", []), report_path]
            decision = {
                "kind": "candidate_adoption",
                "plan_version": intent["plan_version"],
                "status": "approved",
                "job_id": intent["job_id"],
                "candidate_index": intent["candidate_index"],
                "subject_sha256": intent["subject_sha256"],
                "experience": _json(experience),
            }
            saved = self.projects.adopt_candidate(
                project_id,
                plan=updated,
                expected_version=intent["plan_version"],
                decision_id=intent_id,
                decision=decision,
                job_id=job.job_id,
                result=result,
                report_resource=resource,
            )
            risks = self._repair_adoption_projections(project_id, decision)
            return self._envelope(
                "adopted",
                "候选已采纳，继续生产需要按新计划授权。",
                project_id=project_id,
                plan_version=saved.plan_version,
                experience=_json(experience),
                risks=risks,
            )

    def _repair_adoption_projections(self, project_id: str, decision: dict[str, Any]) -> list[str]:
        """Restore only projections of an already persisted human adoption decision."""
        if "experience" not in decision:
            return []  # Older decisions have no recovery payload; never infer one.
        try:
            snapshot = self._snapshot(project_id)
            job = next(item for item in snapshot.jobs if item.job_id == decision["job_id"])
            report = EvolutionReport.model_validate(worker_data(job.result)["report"])
            experience = EvolutionExperience.model_validate(decision["experience"])
            if (
                job.status != "done"
                or job.tool_name != "run_evolution"
                or report.adopted_iteration != decision["candidate_index"]
                or experience.experiment_id != report.experiment_id
                or decision["plan_version"] != job.plan_version
            ):
                raise ValueError("采纳投影与已保存决定不一致。")
            save_report(report, workspace_root=self._root(project_id, job.plan_version))
            save_experience(
                experience, workspace_root=self.projects.production_workspace(project_id)
            )
        except (EvolutionLibraryError, OSError, ValueError, KeyError, StopIteration):
            _LOG.warning(
                "采纳投影尚未完成，等待启动恢复：project_id=%r job_id=%r",
                project_id,
                decision.get("job_id"),
            )
            return ["采纳决定和新计划已保存；报告或经验索引暂未完成写入，Studio 下次启动会恢复。"]
        return []
