# Blender Worker

Blender Worker 准备程序化资产任务，并为灰盒和可读性优先的资产阶段生成 Blender Python 脚本。目标是支持 Blender Python 与后续 Blender MCP 执行。

本地运行：

```bash
uvicorn app.main:app --reload --app-dir apps/blender-worker
```

主要端点：

- `POST /assets`
- 请求体：`GameplaySpec`
- 返回：`BlenderAssetPlan`

脚本端点：

- `POST /script`
- 请求体：`BlenderAssetPlan`
- 返回：`BlenderScriptArtifact`，包含生成的 `.py` 脚本文本和 Unreal import manifest。

- `POST /assets/script`
- 请求体：`GameplaySpec`
- 先准备资产计划，再返回 `BlenderScriptArtifact`。

MCP 端点：

- `GET /mcp`
- `POST /mcp`
- 传输：JSON-RPC over HTTP
- 工具：
  - `generate_blender_script`
  - `generate_asset_batch`

生成资产角色：

- 模块化墙体
- 门
- 坡道
- 危险标记
- 目标道具
- 出口门
- UI proxy mesh

生成脚本会设置场景单位、collection、材质色块、object origin、`UCX_` 碰撞 mesh、FBX/GLB 导出，以及位于 `generated/import-manifest.yaml` 的 JSON 兼容 Unreal import manifest。

Worker 不会从规划端点启动 Blender。Blender MCP 执行要求 `confirmed_side_effects=true`，脚本写入 `generated/blender/`，资产导出到 `generated/assets/`，日志捕获到 `generated/logs/blender/`。

MCP 执行示例：

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
