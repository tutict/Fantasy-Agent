from pathlib import Path

from fantasy_agent.blender_mcp import BlenderMCPBridge, call_blender_mcp_tool, tool_descriptors
from fantasy_agent.contracts import (
    BlenderAssetJob,
    BlenderAssetPlan,
    BlenderMCPExecuteRequest,
    BlenderMCPGenerateScriptRequest,
)


def _plan() -> BlenderAssetPlan:
    return BlenderAssetPlan(
        job_name="mcp-smoke",
        python_entrypoint="fantasy_agent/blender_procedural_job.py",
        export_format="fbx",
        handoff_artifacts=[],
        jobs=[
            BlenderAssetJob(
                asset_name="objective_prop",
                purpose="Readable objective actor for interaction testing.",
                primitive_strategy="Cylinder pedestal plus beacon cube.",
                export_path="generated/assets/objective_prop.fbx",
                collision_hint="UCX convex collision.",
                asset_kind="objective_prop",
            )
        ],
    )


def test_blender_mcp_descriptors_expose_script_and_batch_tools():
    names = {tool["name"] for tool in tool_descriptors()}

    assert {"generate_blender_script", "generate_asset_batch"}.issubset(names)


def test_generate_blender_script_can_write_handoff_files(tmp_path: Path):
    bridge = BlenderMCPBridge(tmp_path)
    result = bridge.generate_blender_script(
        BlenderMCPGenerateScriptRequest(plan=_plan(), write_files=True)
    )

    assert result.status == "written"
    assert result.written_files == [
        "generated/blender/mcp_smoke.py",
        "generated/import-manifest.yaml",
    ]
    assert (tmp_path / "generated/blender/mcp_smoke.py").exists()
    assert (tmp_path / "generated/import-manifest.yaml").exists()


def test_generate_asset_batch_blocks_without_confirmation(tmp_path: Path):
    bridge = BlenderMCPBridge(tmp_path)
    result = bridge.generate_asset_batch(
        BlenderMCPExecuteRequest(plan=_plan(), confirmed_side_effects=False)
    )

    assert result.status == "blocked"
    assert "confirmed_side_effects=true" in result.risks[-1]
    assert result.command[0] == "blender"


def test_blender_mcp_rejects_export_paths_outside_generated_assets(tmp_path: Path):
    plan = _plan().model_copy(
        update={
            "jobs": [
                _plan().jobs[0].model_copy(update={"export_path": "outside/objective_prop.fbx"})
            ]
        }
    )
    result = call_blender_mcp_tool(
        "generate_blender_script",
        {"plan": plan.model_dump(mode="json")},
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "generated/assets" in result["content"][0]["text"]
