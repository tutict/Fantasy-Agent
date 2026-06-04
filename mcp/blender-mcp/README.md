# Blender MCP

Blender MCP 用于执行受控 Blender Python 任务，生成程序化资产。

端点：

```text
apps/blender-worker -> /mcp
```

初始范围：

- 从 `BlenderAssetPlan` 生成 Blender Python 脚本。
- 运行 allowlist 内的资产生成脚本。
- 将 FBX 或 GLB 文件导出到 `generated/assets/`。
- 返回导出 manifest 和错误。
- 校验比例、命名和碰撞提示。

所有实际操作必须保持在 workspace 内。

生成脚本支持模块化墙体、门、坡道、危险标记、目标道具、出口门和 UI proxy mesh。脚本还会设置材质色块、collection、适合落地的 origin、`UCX_` 碰撞 mesh 和 Unreal import manifest。

当 `write_files=false` 时，脚本生成属于安全规划步骤。写入脚本或运行 Blender 是实际操作步骤，需要明确确认。

执行护栏：

- `generate_asset_batch` 需要 `confirmed_side_effects=true`。
- 生成脚本必须保存在 `generated/blender/`。
- Mesh 导出必须保存在 `generated/assets/`。
- 日志捕获到 `generated/logs/blender/`。
- Blender 通过 `blender --background --python <script>` 以后台模式运行。
