from __future__ import annotations

from fantasy_agent.contracts import MCPToolContract


def initial_mcp_contracts() -> list[MCPToolContract]:
    return [
        MCPToolContract(
            name="create_project_structure",
            server="unreal-mcp",
            input_schema_ref="mcp/unreal-mcp/tools.yaml#create_project_structure",
            output_schema_ref="mcp/unreal-mcp/tools.yaml#create_project_structure.output",
            side_effects=[
                "optionally writes generated .uproject, Config, setup script, and content manifest",
                "optionally creates generated Unreal content folders",
            ],
            safety_checks=[
                "project path must be generated/unreal",
                "content folders must start with Content/",
                "engine version must be explicit",
            ],
        ),
        MCPToolContract(
            name="run_editor_commandlet",
            server="unreal-mcp",
            input_schema_ref="mcp/unreal-mcp/tools.yaml#run_editor_commandlet",
            output_schema_ref="mcp/unreal-mcp/tools.yaml#run_editor_commandlet.output",
            side_effects=["launches Unreal Editor commandlet"],
            safety_checks=[
                "requires confirmed side effects",
                "project file must be generated/unreal/*.uproject",
                "commandlet allowlist",
                "timeout required",
                "logs captured under generated/logs/unreal",
            ],
        ),
        MCPToolContract(
            name="prepare_asset_ingest",
            server="unreal-mcp",
            input_schema_ref="mcp/unreal-mcp/tools.yaml#prepare_asset_ingest",
            output_schema_ref="mcp/unreal-mcp/tools.yaml#prepare_asset_ingest.output",
            side_effects=[
                "optionally writes Unreal Python import script",
                "optionally writes asset ingest manifest",
            ],
            safety_checks=[
                "project file must be generated/unreal/*.uproject",
                "Blender assets must be generated/assets",
                "ComfyUI images must be generated/comfyui",
                "ComfyUI imports remain review references",
            ],
        ),
        MCPToolContract(
            name="run_asset_ingest",
            server="unreal-mcp",
            input_schema_ref="mcp/unreal-mcp/tools.yaml#run_asset_ingest",
            output_schema_ref="mcp/unreal-mcp/tools.yaml#run_asset_ingest.output",
            side_effects=["launches Unreal Editor", "imports assets into project content"],
            safety_checks=[
                "requires confirmed side effects",
                "project file must be generated/unreal/*.uproject",
                "script must be generated/unreal/*.py",
                "logs captured under generated/logs/unreal",
            ],
        ),
        MCPToolContract(
            name="generate_blender_script",
            server="blender-mcp",
            input_schema_ref="mcp/blender-mcp/tools.yaml#generate_blender_script",
            output_schema_ref="mcp/blender-mcp/tools.yaml#generate_blender_script.output",
            side_effects=["optionally writes generated Blender scripts and import manifests"],
            safety_checks=[
                "script path must be generated/blender",
                "manifest path must be generated",
                "export paths must be generated/assets",
            ],
        ),
        MCPToolContract(
            name="generate_asset_batch",
            server="blender-mcp",
            input_schema_ref="mcp/blender-mcp/tools.yaml#generate_asset_batch",
            output_schema_ref="mcp/blender-mcp/tools.yaml#generate_asset_batch.output",
            side_effects=["runs Blender Python", "writes mesh exports"],
            safety_checks=[
                "requires confirmed side effects",
                "export path must be generated/assets",
                "script must avoid external downloads",
                "logs captured under generated/logs/blender",
            ],
        ),
        MCPToolContract(
            name="prepare_visual_reference_workflows",
            server="comfyui-mcp",
            input_schema_ref="mcp/comfyui-mcp/tools.yaml#prepare_visual_reference_workflows",
            output_schema_ref="mcp/comfyui-mcp/tools.yaml#prepare_visual_reference_workflows.output",
            side_effects=["optionally writes prepared ComfyUI workflow JSON and run manifests"],
            safety_checks=[
                "workflow templates must be templates/comfyui",
                "output path must be generated/comfyui",
                "jobs must reference gameplay constraints",
            ],
        ),
        MCPToolContract(
            name="run_visual_reference_workflow",
            server="comfyui-mcp",
            input_schema_ref="mcp/comfyui-mcp/tools.yaml#run_visual_reference_workflow",
            output_schema_ref="mcp/comfyui-mcp/tools.yaml#run_visual_reference_workflow.output",
            side_effects=["submits ComfyUI prompt jobs", "writes generated reference images"],
            safety_checks=[
                "requires confirmed side effects",
                "ComfyUI endpoint must be local or explicitly approved",
                "output path must be generated/comfyui",
                "jobs must reference gameplay constraints",
                "workflow templates must be templates/comfyui",
            ],
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
