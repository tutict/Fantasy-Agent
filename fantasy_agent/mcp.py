from __future__ import annotations

from fantasy_agent.contracts import MCPToolContract


def initial_mcp_contracts() -> list[MCPToolContract]:
    return [
        MCPToolContract(
            name="create_project_structure",
            server="unreal-mcp",
            input_schema_ref="mcp/unreal-mcp/tools.yaml#create_project_structure",
            output_schema_ref="mcp/unreal-mcp/tools.yaml#create_project_structure.output",
            side_effects=["creates UE project folders", "writes content manifests"],
            safety_checks=["project path must be inside workspace", "engine version must be explicit"],
        ),
        MCPToolContract(
            name="run_editor_commandlet",
            server="unreal-mcp",
            input_schema_ref="mcp/unreal-mcp/tools.yaml#run_editor_commandlet",
            output_schema_ref="mcp/unreal-mcp/tools.yaml#run_editor_commandlet.output",
            side_effects=["launches Unreal Editor commandlet"],
            safety_checks=["commandlet allowlist", "timeout required", "logs captured"],
        ),
        MCPToolContract(
            name="generate_asset_batch",
            server="blender-mcp",
            input_schema_ref="mcp/blender-mcp/tools.yaml#generate_asset_batch",
            output_schema_ref="mcp/blender-mcp/tools.yaml#generate_asset_batch.output",
            side_effects=["runs Blender Python", "writes mesh exports"],
            safety_checks=["export path must be generated/assets", "script must avoid external downloads"],
        ),
        MCPToolContract(
            name="publish_prototype_branch",
            server="github-mcp",
            input_schema_ref="mcp/github-mcp/tools.yaml#publish_prototype_branch",
            output_schema_ref="mcp/github-mcp/tools.yaml#publish_prototype_branch.output",
            side_effects=["creates branch", "opens pull request"],
            safety_checks=["requires clean generated manifest", "never commits secrets"],
        ),
    ]
