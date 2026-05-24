"""Blender Python entrypoint for future MCP execution.

This file is safe to import outside Blender. The bpy import happens inside main so
regular Python tooling can lint and compile the repository.
"""

from __future__ import annotations


def main(job_manifest: dict) -> list[str]:
    import bpy  # type: ignore[import-not-found]

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    exported: list[str] = []
    for job in job_manifest.get("jobs", []):
        asset_name = job["asset_name"]
        bpy.ops.mesh.primitive_cube_add(size=100)
        obj = bpy.context.object
        obj.name = asset_name
        obj.scale = (1.0, 1.0, 0.25)
        export_path = job["export_path"]
        bpy.ops.export_scene.fbx(filepath=export_path, use_selection=False)
        exported.append(export_path)
    return exported
