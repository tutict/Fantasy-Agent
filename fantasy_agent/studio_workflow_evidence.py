"""Translate genuine worker results into the external workflow's production cards.

The table is server-owned. It never consumes a model-authored stage status or
grants permission, and preserves asset review before integration. A Godot
greybox can be prepared before optional art, as the deterministic executor does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fantasy_agent.contracts import ProductionPipeline
from fantasy_agent.pipeline_state import executor_stages_for

ALIASES = {
    "godot_quick_play": {"execute_demo"},
    "unreal_production": {"execute_demo"},
    "blender_modeling": {"execute_assets", "generate_asset_batch"},
    "comfyui_visual_production": {"execute_assets"},
    "asset_integration": {"copy_approved_godot_assets"},
    "optimization_testing": {"execute_demo", "run_evolution"},
}
PREPARATIONS = {
    "generate_blender_script",
    "prepare_visual_reference_workflows",
    "prepare_asset_ingest",
    "prepare_level_assembly",
}


def external_pipeline(plan: ProductionPipeline, jobs) -> ProductionPipeline:
    pipeline = plan.model_copy(deep=True)
    requested = set()
    for job in jobs:
        if job.tool_name in {"generate_asset_batch", "generate_blender_script"} or (
            job.tool_name == "execute_assets" and job.arguments.get("with_assets")
        ):
            requested.add("blender_modeling")
        if job.tool_name in {
            "prepare_visual_reference_workflows",
            "run_visual_reference_workflow",
        } or (job.tool_name == "execute_assets" and job.arguments.get("with_visuals")):
            requested.add("comfyui_visual_production")
    for stage in pipeline.stages:
        stage.mcp_tools = list(
            dict.fromkeys([*stage.mcp_tools, *sorted(ALIASES.get(stage.id, set()))])
        )
        stage.human_resolution = None
        if stage.id == "godot_quick_play":
            stage.depends_on = ["gameplay_orchestration"]
            stage.mcp_tools = [name for name in stage.mcp_tools if name != "playtest_godot_project"]
        elif stage.id == "creative_review":
            stage.depends_on = [dep for dep in stage.depends_on if dep in requested]
        elif stage.id == "asset_integration" and any(
            item.id == "godot_quick_play" for item in pipeline.stages
        ):
            stage.depends_on = ["creative_review", "godot_quick_play"]
            stage.mcp_tools = [
                name for name in stage.mcp_tools if name != "create_godot_project_structure"
            ]
    return pipeline


def worker_data(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result", payload)
    if isinstance(result, dict) and "kind" in result and isinstance(result.get("data"), dict):
        return result["data"]
    return result if isinstance(result, dict) else {}


@dataclass(frozen=True)
class StageEvidence:
    stage_id: str
    ok: bool
    detail: str
    prepared: bool = False


def evidence_for(
    name: str, data: dict[str, Any], pipeline: ProductionPipeline
) -> list[StageEvidence]:
    emitted = {stage.get("name"): stage for stage in data.get("stages", [])}
    results = []
    for stage in pipeline.stages:
        if stage.kind == "human" or name not in stage.mcp_tools:
            continue
        if name == "execute_demo":
            if stage.id not in {"godot_quick_play", "unreal_production", "optimization_testing"}:
                continue
            names = (
                ["playtest"]
                if stage.id == "optimization_testing"
                else [item for item in executor_stages_for(stage.id) if item in emitted]
            )
            if stage.id != "optimization_testing" and not {"create", "validate"} <= set(names):
                continue
            records = [emitted.get(item, {}) for item in names]
            ok = bool(records) and all(item.get("status") == "done" for item in records)
            results.append(
                StageEvidence(stage.id, ok, "；".join(item.get("detail", "") for item in records))
            )
        elif name == "execute_assets":
            target = "blender" if stage.id == "blender_modeling" else "comfyui"
            if (
                stage.id not in {"blender_modeling", "comfyui_visual_production"}
                or target not in emitted
            ):
                continue
            result = emitted[target]
            results.append(
                StageEvidence(stage.id, result.get("status") == "done", result.get("detail", ""))
            )
        elif name == "run_evolution":
            if stage.id != "optimization_testing":
                continue
            report = data.get("report", {})
            ok = report.get("status") in {"improved", "unchanged"} and bool(
                report.get("iterations")
            )
            results.append(StageEvidence(stage.id, ok, "已记录基线与候选的真实试玩测量。"))
        else:
            ok = data.get("tool_status", "ok") == "ok"
            results.append(
                StageEvidence(
                    stage.id, ok, data.get("detail", "已记录实际工具结果。"), name in PREPARATIONS
                )
            )
    return results
