# Godot Builder

Godot Builder 为 Fantasy Agent 准备 Godot 4 快速可玩工程交接。

它用于在较重 Unreal 工作前快速验证玩法循环、空间节奏和交互可读性。它可以准备 `GodotProjectPlan`，暴露 JSON-RPC MCP 端点，在 `generated/godot/` 下写入生成的 Godot 工程文件，验证工程结构，并只在明确副作用确认后运行 Godot headless import。

Godot Builder 不取代 Unreal 主线生产导入。

## 本地端点

- `GET /health`
- `POST /prepare`
- `GET /mcp`
- `POST /mcp`
