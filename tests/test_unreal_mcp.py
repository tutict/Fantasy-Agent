import json
import subprocess
from pathlib import Path

from fantasy_agent.contracts import (
    ComfyUIRunManifest,
    ComfyUIWorkflowArtifact,
    UnrealImportAsset,
    UnrealImportManifest,
    UnrealMCPEditorCommandletRequest,
    UnrealMCPCreateProjectRequest,
    UnrealMCPPrepareAssetIngestRequest,
    UnrealMCPRunAssetIngestRequest,
    UnrealMCPValidateAssetIngestRequest,
    UnrealProjectPlan,
)
from fantasy_agent.unreal_mcp import UnrealMCPBridge, call_unreal_mcp_tool, tool_descriptors


def _plan() -> UnrealProjectPlan:
    return UnrealProjectPlan(
        project_name="MCPPrototype",
        engine_version="UE5.3",
        template="third-person",
        plugins=["EnhancedInput", "GameplayTags"],
        folders=[
            "Content/Blueprints/CoreLoop",
            "Content/Maps",
            "Content/Art/Generated",
            "Content/Data",
        ],
        gameplay_classes=["BP_PlayerPrototypePawn", "BP_ObjectiveStateComponent"],
        blueprints=["BP_ObjectiveDirector", "WBP_ObjectiveTracker"],
        maps=["M_Prototype_Greybox"],
        automation_steps=["Create content folders", "Run asset ingest manifest validation"],
        handoff_artifacts=["generated/unreal-project-plan.yaml"],
    )


def test_unreal_mcp_descriptors_expose_project_and_commandlet_tools():
    names = {tool["name"] for tool in tool_descriptors()}

    assert {
        "create_project_structure",
        "prepare_asset_ingest",
        "run_asset_ingest",
        "validate_asset_ingest",
        "run_editor_commandlet",
    }.issubset(names)


def test_create_project_structure_can_write_handoff_files(tmp_path: Path):
    bridge = UnrealMCPBridge(tmp_path)

    result = bridge.create_project_structure(
        UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True)
    )

    assert result.status == "written"
    assert result.written_files == [
        "generated/unreal/mcpprototype/MCPPrototype.uproject",
        "generated/unreal/mcpprototype/fantasy-agent-content-manifest.json",
        "generated/unreal/mcpprototype/Scripts/fantasy_agent_setup.py",
        "generated/unreal/mcpprototype/Config/DefaultGame.ini",
        "generated/unreal/mcpprototype/Config/DefaultEngine.ini",
    ]
    assert (tmp_path / "generated/unreal/mcpprototype/MCPPrototype.uproject").exists()
    assert (tmp_path / "generated/unreal/mcpprototype/Content/Maps").exists()
    assert (
        "AnimationRecorderBoneCompressionSettings="
        in (tmp_path / "generated/unreal/mcpprototype/Config/DefaultEngine.ini").read_text(
            encoding="utf-8"
        )
    )
    descriptor = json.loads(
        (tmp_path / "generated/unreal/mcpprototype/MCPPrototype.uproject").read_text(
            encoding="utf-8"
        )
    )
    assert {plugin["Name"] for plugin in descriptor["Plugins"]} == {"EnhancedInput"}


def test_run_editor_commandlet_blocks_without_confirmation(tmp_path: Path):
    bridge = UnrealMCPBridge(tmp_path)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))

    result = bridge.run_editor_commandlet(
        UnrealMCPEditorCommandletRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            commandlet="DataValidation",
            confirmed_side_effects=False,
        )
    )

    assert result.status == "blocked"
    assert "confirmed_side_effects=true" in result.risks[-1]
    assert "-run=DataValidation" in result.command
    assert "-IncludeOnlyOnDiskAssets" in result.command
    assert "-DDC=InstalledNoZenLocalFallback" in result.command
    assert any(item.startswith("-ShaderWorkingDir=") for item in result.command)


def test_run_editor_commandlet_uses_fake_runner_and_captures_logs(tmp_path: Path):
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="data ok", stderr="")

    bridge = UnrealMCPBridge(tmp_path, runner=fake_runner)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))

    result = bridge.run_editor_commandlet(
        UnrealMCPEditorCommandletRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            commandlet="DataValidation",
            confirmed_side_effects=True,
        )
    )

    assert result.status == "executed"
    assert result.return_code == 0
    assert result.stdout_tail == "data ok"
    assert (
        tmp_path / "generated/logs/unreal/mcpprototype_DataValidation.stdout.log"
    ).exists()


def test_prepare_asset_ingest_writes_blender_and_comfyui_import_script(tmp_path: Path):
    _write_source_manifests(tmp_path)
    bridge = UnrealMCPBridge(tmp_path)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))

    result = bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            blender_import_manifest_path="generated/import-manifest.yaml",
            comfyui_run_manifest_path="generated/comfyui/run-manifest.json",
            write_files=True,
        )
    )

    assert result.status == "written"
    assert result.manifest is not None
    assert len(result.manifest.jobs) == 2
    assert result.written_files == [
        "generated/unreal/mcpprototype/fantasy-agent-asset-ingest.json",
        "generated/unreal/mcpprototype/Scripts/fantasy_agent_asset_ingest.py",
    ]
    script = tmp_path / "generated/unreal/mcpprototype/Scripts/fantasy_agent_asset_ingest.py"
    script_text = script.read_text(encoding="utf-8")
    assert "AssetImportTask" in script_text
    assert "MANIFEST = json.loads" in script_text
    assert "imported_object_paths" in script_text


def test_validate_asset_ingest_accepts_unreal_safe_manifest(tmp_path: Path):
    _write_source_manifests(tmp_path)
    bridge = UnrealMCPBridge(tmp_path)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))
    bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            blender_import_manifest_path="generated/import-manifest.yaml",
            write_files=True,
        )
    )

    result = bridge.validate_asset_ingest(
        UnrealMCPValidateAssetIngestRequest(
            ingest_manifest_path="generated/unreal/mcpprototype/fantasy-agent-asset-ingest.json"
        )
    )

    assert result.status == "executed"
    assert result.validation_report is not None
    assert result.validation_report.job_count == 1
    assert result.validation_report.issues == []


def test_validate_asset_ingest_rejects_invalid_unreal_names(tmp_path: Path):
    _write_source_manifests(tmp_path)
    bridge = UnrealMCPBridge(tmp_path)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))
    bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            blender_import_manifest_path="generated/import-manifest.yaml",
            write_files=True,
        )
    )
    manifest_path = tmp_path / "generated/unreal/mcpprototype/fantasy-agent-asset-ingest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["jobs"][0]["asset_name"] = "wall-run_panel_set"
    data["jobs"][0]["import_settings"]["collision_object"] = "UCX_wall-run_panel_set_00"
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    result = bridge.validate_asset_ingest(
        UnrealMCPValidateAssetIngestRequest(
            ingest_manifest_path="generated/unreal/mcpprototype/fantasy-agent-asset-ingest.json"
        )
    )

    assert result.status == "failed"
    assert result.validation_report is not None
    assert "invalid Unreal asset_name: wall-run_panel_set" in result.validation_report.issues
    assert (
        "invalid Unreal collision_object: UCX_wall-run_panel_set_00"
        in result.validation_report.issues
    )


def test_run_asset_ingest_blocks_without_confirmation(tmp_path: Path):
    _write_source_manifests(tmp_path)
    bridge = UnrealMCPBridge(tmp_path)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))
    bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            blender_import_manifest_path="generated/import-manifest.yaml",
            write_files=True,
        )
    )

    result = bridge.run_asset_ingest(
        UnrealMCPRunAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            import_script_path="generated/unreal/mcpprototype/Scripts/fantasy_agent_asset_ingest.py",
            confirmed_side_effects=False,
        )
    )

    assert result.status == "blocked"
    assert "confirmed_side_effects=true" in result.risks[-1]
    assert "-DDC=InstalledNoZenLocalFallback" in result.command
    assert any(item.startswith("-ShaderWorkingDir=") for item in result.command)


def test_run_asset_ingest_uses_fake_runner_and_captures_logs(tmp_path: Path):
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ingest ok", stderr="")

    _write_source_manifests(tmp_path)
    bridge = UnrealMCPBridge(tmp_path, runner=fake_runner)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))
    bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            blender_import_manifest_path="generated/import-manifest.yaml",
            write_files=True,
        )
    )

    result = bridge.run_asset_ingest(
        UnrealMCPRunAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            import_script_path="generated/unreal/mcpprototype/Scripts/fantasy_agent_asset_ingest.py",
            confirmed_side_effects=True,
        )
    )

    assert result.status == "executed"
    assert result.stdout_tail == "ingest ok"
    assert (tmp_path / "generated/logs/unreal/mcpprototype_asset_ingest.stdout.log").exists()


def test_run_asset_ingest_detects_unreal_python_log_errors(tmp_path: Path):
    def fake_runner(*args, **kwargs):
        log_dir = Path(kwargs["cwd"]) / "Saved" / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "MCPPrototype.log").write_text(
            "LogPython: Error: import failed\nPython script executed with errors\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    _write_source_manifests(tmp_path)
    bridge = UnrealMCPBridge(tmp_path, runner=fake_runner)
    bridge.create_project_structure(UnrealMCPCreateProjectRequest(plan=_plan(), write_files=True))
    bridge.prepare_asset_ingest(
        UnrealMCPPrepareAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            blender_import_manifest_path="generated/import-manifest.yaml",
            write_files=True,
        )
    )

    result = bridge.run_asset_ingest(
        UnrealMCPRunAssetIngestRequest(
            project_file="generated/unreal/mcpprototype/MCPPrototype.uproject",
            import_script_path="generated/unreal/mcpprototype/Scripts/fantasy_agent_asset_ingest.py",
            confirmed_side_effects=True,
        )
    )

    assert result.status == "failed"
    assert "Unreal Python asset ingest logged errors." in result.risks


def test_unreal_mcp_rejects_project_dir_outside_generated_unreal(tmp_path: Path):
    result = call_unreal_mcp_tool(
        "create_project_structure",
        {"plan": _plan().model_dump(mode="json"), "project_dir": "outside/unreal"},
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "generated/unreal" in result["content"][0]["text"]


def test_unreal_mcp_rejects_blender_ingest_paths_outside_generated_assets(tmp_path: Path):
    _write_source_manifests(tmp_path, blender_source="outside/objective.fbx")

    result = call_unreal_mcp_tool(
        "prepare_asset_ingest",
        {
            "project_file": "generated/unreal/mcpprototype/MCPPrototype.uproject",
            "blender_import_manifest_path": "generated/import-manifest.yaml",
        },
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "generated/assets" in result["content"][0]["text"]


def test_unreal_mcp_rejects_non_uproject_commandlet_target(tmp_path: Path):
    result = call_unreal_mcp_tool(
        "run_editor_commandlet",
        {
            "project_file": "generated/unreal/mcpprototype/not-a-project.txt",
            "commandlet": "DataValidation",
        },
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert ".uproject" in result["content"][0]["text"]


def _write_source_manifests(
    root: Path,
    blender_source: str = "generated/assets/objective_prop.fbx",
) -> None:
    (root / "generated/assets").mkdir(parents=True, exist_ok=True)
    (root / "generated/comfyui/smoke").mkdir(parents=True, exist_ok=True)
    (root / "generated/assets/objective_prop.fbx").write_text("fbx", encoding="utf-8")
    (root / "generated/comfyui/smoke/concept.png").write_text("png", encoding="utf-8")
    blender_manifest = UnrealImportManifest(
        import_settings={
            "combine_meshes": False,
            "generate_missing_collision": False,
            "import_materials": True,
            "import_textures": False,
            "unit_scale": 1.0,
        },
        assets=[
            UnrealImportAsset(
                asset_name="objective_prop",
                asset_kind="objective_prop",
                source_file=blender_source,
                destination_path="/Game/Art/Generated",
                collision_object="UCX_objective_prop_00",
                material_key="objective",
                dimensions_cm=(120.0, 120.0, 170.0),
                gameplay_role="Readable objective prop.",
            )
        ],
    )
    comfyui_manifest = ComfyUIRunManifest(
        plan_name="Smoke Visuals",
        endpoint="http://127.0.0.1:8188",
        prompt_ids=["prompt-1"],
        generated_images=["generated/comfyui/smoke/concept.png"],
        jobs=[
            ComfyUIWorkflowArtifact(
                job_id="concept_readability_reference",
                workflow_template="templates/comfyui/readability-reference.json",
                workflow_path="generated/comfyui/workflows/smoke/concept.json",
                workflow={},
                output_path="generated/comfyui/smoke/concept.png",
                prompt="Readable objective reference.",
                negative_prompt="decorative-only",
                gameplay_constraint="Clarify objective readability.",
                seed=42,
            )
        ],
    )
    (root / "generated/import-manifest.yaml").write_text(
        json.dumps(blender_manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (root / "generated/comfyui/run-manifest.json").write_text(
        json.dumps(comfyui_manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
