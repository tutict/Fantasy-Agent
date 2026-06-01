# ComfyUI 集成

ComfyUI 在 Fantasy Agent 中是视觉参考工人，不是玩法事实来源。

## 角色

ComfyUI 适合生成：

- 玩法可读性概念参考。
- 材质和色彩板。
- UI 参考帧。
- 经审阅后可用的 texture seed。
- 关卡节奏 storyboard。

ComfyUI 不决定机制、节奏、胜利状态、失败状态或关卡布局。这些来自 Gameplay DSL。

## 流程

```text
GameplaySpec
  -> ComfyUI Worker
  -> ComfyUIVisualPlan
  -> comfyui-mcp
  -> generated/comfyui/*
  -> 经审阅的视觉参考
```

## MCP 工具

- `prepare_visual_reference_workflows`：准备 allowlist workflow JSON 和 run manifest。除非 `write_files=true`，否则属于规划安全操作。
- `run_visual_reference_workflow`：在 `confirmed_side_effects=true` 后向 ComfyUI 提交已准备的任务。

MCP 桥接使用本地 ComfyUI HTTP 路由 `/prompt`、`/history/{prompt_id}` 和 `/view` 完成排队、轮询和可选图片下载。

## 安全边界

- 默认端点是 `http://127.0.0.1:8188`。
- 输出保持在 `generated/comfyui/`。
- Workflow 模板来自 `templates/comfyui/`。
- 每个任务都必须包含玩法约束。
- 生成图片成为引擎资产前必须经过审阅。
- 远程 ComfyUI 端点需要显式 `allow_remote_endpoint=true`。
- 提交 prompt 需要 `confirmed_side_effects=true`。
- 日志保持在 `generated/logs/comfyui/`。

ComfyUI 输出不应阻塞灰盒原型；只有当它能说明目标、危险、路线、材质、UI 反馈或 storyboard 时才值得生成。
