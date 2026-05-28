# Blender MCP

Blender MCP will execute controlled Blender Python jobs for procedural asset generation.

Endpoint:

```text
apps/blender-worker -> /mcp
```

Initial scope:

- Generate Blender Python scripts from `BlenderAssetPlan`.
- Run allowlisted asset generation scripts.
- Export FBX or GLB files into `generated/assets/`.
- Return export manifests and errors.
- Validate scale, naming, and collision hints.

Side effects must stay inside the workspace.

Generated scripts support modular walls, doors, ramps, hazard markers, objective props, exit gates, and UI proxy meshes. Scripts also set material color keys, collections, floor-friendly origins, `UCX_` collision meshes, and Unreal import manifests.

Script generation is safe as a planning step when `write_files=false`. Writing scripts or running Blender is a side-effecting step and requires explicit confirmation.

Execution guardrails:

- `generate_asset_batch` requires `confirmed_side_effects=true`.
- Generated scripts must stay under `generated/blender/`.
- Mesh exports must stay under `generated/assets/`.
- Logs are captured under `generated/logs/blender/`.
- Blender runs in background mode through `blender --background --python <script>`.
