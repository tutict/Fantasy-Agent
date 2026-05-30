# Godot MCP

Godot MCP exposes controlled Godot 4 project handoff tools for Fantasy Agent.

Use it when a gameplay idea needs a fast, local quick-play project before Unreal production work. Generated files stay under `generated/godot/`; logs stay under `generated/logs/godot/`; Godot CLI execution requires `confirmed_side_effects=true`.

## Tools

- `create_godot_project_structure`: prepares or writes `project.godot`, scenes, GDScript files, and a manifest.
- `validate_godot_project`: checks generated project structure without launching Godot.
- `run_godot_import`: launches Godot headless import after explicit confirmation.
