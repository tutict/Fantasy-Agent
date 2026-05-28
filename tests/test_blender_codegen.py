from fantasy_agent.blender_codegen import build_blender_script_artifact, enrich_blender_plan
from fantasy_agent.blender_runtime import build_import_manifest
from fantasy_agent.contracts import BlenderAssetJob, BlenderAssetPlan, PromptRequest
from fantasy_agent.workflows import prepare_blender_assets, run_director_workflow


EXPECTED_KINDS = {
    "modular_wall",
    "door",
    "ramp",
    "hazard_marker",
    "objective_prop",
    "exit_gate",
    "ui_proxy_mesh",
}


def test_director_blender_plan_includes_playable_greybox_kit():
    plan = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes a haunted train station")
    ).blender_plan

    kinds = {job.asset_kind for job in plan.jobs}

    assert EXPECTED_KINDS.issubset(kinds)
    assert all(job.collection.startswith("FA_") for job in plan.jobs)
    assert all(job.collision_name and job.collision_name.startswith("UCX_") for job in plan.jobs)
    assert "generated/blender/*.py" in plan.handoff_artifacts


def test_blender_script_artifact_generates_python_and_unreal_manifest():
    asset_plan = prepare_blender_assets(
        run_director_workflow(
            PromptRequest(prompt="a puzzle climber redirects light through broken towers")
        ).gameplay_spec
    )

    artifact = build_blender_script_artifact(asset_plan)

    assert artifact.script_path.startswith("generated/blender/")
    assert "from fantasy_agent.blender_runtime import run_blender_asset_plan" in artifact.script
    assert "PLAN =" in artifact.script
    assert artifact.import_manifest.assets
    assert {asset.asset_kind for asset in artifact.import_manifest.assets} >= EXPECTED_KINDS
    assert all(
        asset.collision_object.startswith("UCX_") for asset in artifact.import_manifest.assets
    )
    assert "Writes FBX or GLB assets under generated/assets." in artifact.side_effects


def test_enrich_blender_plan_supports_glb_exports_and_role_defaults():
    plan = BlenderAssetPlan(
        job_name="glb-test",
        export_format="glb",
        python_entrypoint="apps/blender-worker/app/procedural_asset_job.py",
        handoff_artifacts=[],
        jobs=[
            BlenderAssetJob(
                asset_name="test_exit_gate",
                purpose="Readable exit gate for extraction.",
                primitive_strategy="primitive composition",
                export_path="generated/assets/test_exit_gate",
                collision_hint="convex",
            )
        ],
    )

    enriched = enrich_blender_plan(plan)
    manifest = build_import_manifest(enriched.model_dump(mode="json"))
    job = enriched.jobs[0]

    assert job.asset_kind == "exit_gate"
    assert job.material_key == "exit"
    assert job.export_path.endswith(".glb")
    assert manifest["assets"][0]["destination_path"] == "/Game/Art/Generated"
    assert manifest["assets"][0]["collision_object"] == "UCX_test_exit_gate_00"


def test_enrich_blender_plan_normalizes_unreal_asset_and_collision_names():
    plan = BlenderAssetPlan(
        job_name="unsafe-name-test",
        python_entrypoint="apps/blender-worker/app/procedural_asset_job.py",
        handoff_artifacts=[],
        jobs=[
            BlenderAssetJob(
                asset_name="wall-run panel set",
                purpose="Wall run readability panel.",
                primitive_strategy="primitive wall",
                export_path="generated/assets/wall-run_panel_set.fbx",
                collision_hint="convex",
            )
        ],
    )

    enriched = enrich_blender_plan(plan)
    manifest = build_import_manifest(enriched.model_dump(mode="json"))
    job = enriched.jobs[0]

    assert job.asset_name == "wall_run_panel_set"
    assert job.collision_name == "UCX_wall_run_panel_set_00"
    assert manifest["assets"][0]["asset_name"] == "wall_run_panel_set"
    assert manifest["assets"][0]["collision_object"] == "UCX_wall_run_panel_set_00"
