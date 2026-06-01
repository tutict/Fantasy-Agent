# Godot MCP

Godot MCP 为 Fantasy Agent 暴露受控 Godot 4 工程交接工具。

当一个玩法想法需要在 Unreal 主线生产前做快速本地 playable-loop 验证时使用它。生成文件保持在 `generated/godot/`；日志保持在 `generated/logs/godot/`；Godot CLI 执行需要 `confirmed_side_effects=true`。

## 工具

- `create_godot_project_structure`：准备或写入 `project.godot`、场景、GDScript 文件和 manifest。
- `validate_godot_project`：不启动 Godot，只检查生成工程结构。
- `run_godot_import`：在明确确认后启动 Godot headless import。
