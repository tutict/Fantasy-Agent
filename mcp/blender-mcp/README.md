# Blender MCP

Blender MCP will execute controlled Blender Python jobs for procedural asset generation.

Initial scope:

- Generate Blender Python scripts from `BlenderAssetPlan`.
- Run allowlisted asset generation scripts.
- Export FBX or GLB files into `generated/assets/`.
- Return export manifests and errors.
- Validate scale, naming, and collision hints.

Side effects must stay inside the workspace.

Generated scripts support modular walls, doors, ramps, hazard markers, objective props, exit gates, and UI proxy meshes. Scripts also set material color keys, collections, floor-friendly origins, `UCX_` collision meshes, and Unreal import manifests.

Script generation is safe as a planning step. Running Blender is a side-effecting step and requires explicit confirmation.
