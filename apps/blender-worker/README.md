# Blender Worker

The Blender Worker prepares procedural asset jobs and generates Blender Python scripts for greybox and readability-first asset passes. It targets Blender Python and future Blender MCP execution.

Blender Worker 会生成面向玩法可读性的程序化资产计划和 Blender Python 脚本，后续可交给 Blender MCP 执行。

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/blender-worker
```

Primary endpoint:

- `POST /assets`
- Request body: `GameplaySpec`
- Returns: `BlenderAssetPlan`

Script endpoints:

- `POST /script`
- Request body: `BlenderAssetPlan`
- Returns: `BlenderScriptArtifact` with generated `.py` script text and Unreal import manifest.

- `POST /assets/script`
- Request body: `GameplaySpec`
- Returns: `BlenderScriptArtifact` after first preparing the asset plan.

MCP endpoint:

- `GET /mcp`
- `POST /mcp`
- Transport: JSON-RPC over HTTP
- Tools:
  - `generate_blender_script`
  - `generate_asset_batch`

Generated asset roles:

- Modular walls
- Doors
- Ramps
- Hazard markers
- Objective props
- Exit gates
- UI proxy meshes

The generated script sets scene units, collections, material color keys, object origins, `UCX_` collision meshes, FBX/GLB exports, and a JSON-compatible Unreal import manifest at `generated/import-manifest.yaml`.

The worker does not launch Blender from planning endpoints. Blender MCP execution requires `confirmed_side_effects=true`, writes generated scripts under `generated/blender/`, exports assets under `generated/assets/`, and captures logs under `generated/logs/blender/`.

Example MCP execution payload:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "generate_asset_batch",
    "arguments": {
      "plan": {},
      "confirmed_side_effects": true,
      "blender_executable": "blender"
    }
  }
}
```
