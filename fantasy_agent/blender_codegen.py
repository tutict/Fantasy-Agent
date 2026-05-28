from __future__ import annotations

import json
from pathlib import PurePosixPath

from fantasy_agent.blender_runtime import DEFAULT_DIMENSIONS_CM, build_import_manifest
from fantasy_agent.contracts import (
    BlenderAssetJob,
    BlenderAssetKind,
    BlenderAssetPlan,
    BlenderMaterialKey,
    BlenderScriptArtifact,
    UnrealImportAsset,
    UnrealImportManifest,
)

KIND_DEFAULT_MATERIAL: dict[BlenderAssetKind, BlenderMaterialKey] = {
    "modular_wall": "neutral",
    "door": "door",
    "ramp": "ramp",
    "hazard_marker": "hazard",
    "objective_prop": "objective",
    "exit_gate": "exit",
    "ui_proxy_mesh": "ui",
    "generic_greybox": "neutral",
}

KIND_DEFAULT_COLLECTION: dict[BlenderAssetKind, str] = {
    "modular_wall": "FA_Modular_Walls",
    "door": "FA_Doors",
    "ramp": "FA_Ramps",
    "hazard_marker": "FA_Hazards",
    "objective_prop": "FA_Objectives",
    "exit_gate": "FA_Exits",
    "ui_proxy_mesh": "FA_UI_Proxies",
    "generic_greybox": "FA_Greybox",
}


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "asset"


def classify_asset_kind(asset_name: str, purpose: str) -> BlenderAssetKind:
    text = f"{asset_name} {purpose}".lower()
    if "ui" in text or "hud" in text or "tracker" in text:
        return "ui_proxy_mesh"
    if "exit" in text or "gate" in text:
        return "exit_gate"
    if "hazard" in text or "danger" in text or "pressure" in text:
        return "hazard_marker"
    if "objective" in text or "goal" in text or "pickup" in text:
        return "objective_prop"
    if "ramp" in text or "slope" in text:
        return "ramp"
    if "door" in text or "lock" in text:
        return "door"
    if "wall" in text or "arena" in text or "kit" in text or "blocker" in text:
        return "modular_wall"
    return "generic_greybox"


def enrich_blender_job(job: BlenderAssetJob, export_format: str = "fbx") -> BlenderAssetJob:
    asset_kind = job.asset_kind
    if asset_kind == "generic_greybox":
        asset_kind = classify_asset_kind(job.asset_name, job.purpose)
    extension = "glb" if export_format == "glb" else "fbx"
    export_path = job.export_path
    if not export_path.endswith((".fbx", ".glb")):
        export_path = f"{export_path}.{extension}"
    dimensions = job.dimensions_cm
    if dimensions == (100.0, 100.0, 100.0):
        dimensions = DEFAULT_DIMENSIONS_CM[asset_kind]
    material_key = job.material_key
    if material_key == "neutral":
        material_key = KIND_DEFAULT_MATERIAL[asset_kind]
    collection = job.collection
    if collection == "GameplayGreybox":
        collection = KIND_DEFAULT_COLLECTION[asset_kind]
    collision_name = job.collision_name or f"UCX_{job.asset_name}_00"
    return job.model_copy(
        update={
            "asset_kind": asset_kind,
            "dimensions_cm": dimensions,
            "material_key": material_key,
            "collection": collection,
            "export_path": export_path,
            "collision_name": collision_name,
        }
    )


def enrich_blender_plan(plan: BlenderAssetPlan) -> BlenderAssetPlan:
    jobs = [enrich_blender_job(job, plan.export_format) for job in plan.jobs]
    artifacts = list(dict.fromkeys([*plan.handoff_artifacts, "generated/blender/*.py"]))
    return plan.model_copy(update={"jobs": jobs, "handoff_artifacts": artifacts})


def build_unreal_import_manifest(plan: BlenderAssetPlan) -> UnrealImportManifest:
    enriched = enrich_blender_plan(plan)
    manifest = build_import_manifest(enriched.model_dump(mode="json"))
    return UnrealImportManifest(
        import_settings=manifest["import_settings"],
        scene_units=enriched.scene_units,
        assets=[UnrealImportAsset.model_validate(asset) for asset in manifest["assets"]],
    )


def default_script_path(plan: BlenderAssetPlan) -> str:
    return f"generated/blender/{slugify(plan.job_name)}.py"


def generate_blender_python_script(
    plan: BlenderAssetPlan,
    import_manifest_path: str = "generated/import-manifest.yaml",
) -> str:
    enriched = enrich_blender_plan(plan)
    payload = json.dumps(enriched.model_dump(mode="json"), indent=2)
    return f'''"""Generated Blender Python script for Fantasy Agent.

Run from the repository root with Blender, for example:
blender --background --python {default_script_path(enriched)}

This script writes assets to generated/assets and writes an Unreal import manifest
to {import_manifest_path}.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path.cwd()
SCRIPT_ROOT = Path(__file__).resolve()
for candidate in (REPO_ROOT, *SCRIPT_ROOT.parents):
    if (candidate / "fantasy_agent").exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
        break

from fantasy_agent.blender_runtime import run_blender_asset_plan


PLAN = {payload}


if __name__ == "__main__":
    run_blender_asset_plan(PLAN, import_manifest_path="{import_manifest_path}")
'''


def build_blender_script_artifact(
    plan: BlenderAssetPlan,
    script_path: str | None = None,
    import_manifest_path: str = "generated/import-manifest.yaml",
) -> BlenderScriptArtifact:
    enriched = enrich_blender_plan(plan)
    resolved_script_path = script_path or default_script_path(enriched)
    manifest = build_unreal_import_manifest(enriched)
    script = generate_blender_python_script(enriched, import_manifest_path)
    output_dir = str(PurePosixPath(resolved_script_path).parent)
    return BlenderScriptArtifact(
        plan_name=enriched.job_name,
        script_path=resolved_script_path,
        script=script,
        import_manifest_path=import_manifest_path,
        import_manifest=manifest,
        execution_notes=[
            "Generated script requires Blender with the repository package on PYTHONPATH.",
            "Run from the repository root so generated/ paths resolve inside the workspace.",
            f"Script directory target: {output_dir}",
            "Blender MCP should execute this script only after side effects are confirmed.",
        ],
        side_effects=[
            "Deletes the active Blender scene before generation.",
            "Writes FBX or GLB assets under generated/assets.",
            f"Writes Unreal import manifest to {import_manifest_path}.",
        ],
    )
