# Unreal Builder

Unreal Builder 根据 gameplay spec 准备 UE5 工程架构。它不编造内容，而是生成可以由 Unreal Python 或 Unreal MCP 执行的工程、目录、Blueprint、地图和自动化计划。

本地运行：

```bash
uvicorn app.main:app --reload --app-dir apps/unreal-builder
```

主要端点：

- `POST /prepare`
- 请求体：`GameplaySpec`
- 返回：`UnrealProjectPlan`

MCP 端点：

- `POST /mcp`
- 工具：`create_project_structure`、`prepare_asset_ingest`、`validate_asset_ingest`、`run_asset_ingest`、`prepare_level_assembly`、`validate_level_assembly`、`run_level_assembly`、`run_editor_commandlet`
- Unreal 执行必须在 `confirmed_side_effects=true` 后才允许。
