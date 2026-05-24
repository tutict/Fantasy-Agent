# Blender MCP

Blender MCP will execute controlled Blender Python jobs for procedural asset generation.

Initial scope:

- Run allowlisted asset generation scripts.
- Export FBX or GLB files into `generated/assets/`.
- Return export manifests and errors.
- Validate scale, naming, and collision hints.

Side effects must stay inside the workspace.
