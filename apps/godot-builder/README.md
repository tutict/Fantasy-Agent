# Godot Builder

Godot Builder prepares a Godot 4 quick-play handoff for Fantasy Agent.

It is intended for fast playable-loop validation before heavier Unreal work. It can prepare a `GodotProjectPlan`, expose a JSON-RPC MCP endpoint, write generated Godot project files under `generated/godot/`, validate the generated project, and run Godot headless import only after explicit side-effect confirmation.

Godot Builder 不取代 Unreal 主线。它用于更快验证玩法循环、空间节奏和交互可读性。

## Local Endpoints

- `GET /health`
- `POST /prepare`
- `GET /mcp`
- `POST /mcp`
