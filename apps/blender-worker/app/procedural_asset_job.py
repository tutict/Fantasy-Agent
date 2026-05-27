"""Blender Python entrypoint for MCP execution.

This file is safe to import outside Blender. The bpy import happens inside main so
regular Python tooling can lint and compile the repository.
"""

from __future__ import annotations

from fantasy_agent.blender_runtime import run_blender_asset_plan


def main(job_manifest: dict) -> dict:
    return run_blender_asset_plan(job_manifest)
