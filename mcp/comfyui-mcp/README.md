# ComfyUI MCP

ComfyUI MCP 用于执行受控本地 ComfyUI workflow，生成视觉参考。

端点：

```text
apps/comfyui-worker -> /mcp
```

初始范围：

- 从 `templates/comfyui/` 加载 allowlist workflow 模板。
- 将 `ComfyUIVisualPlan` 中的 prompt 和 negative prompt 注入 workflow。
- 在 `generated/comfyui/` 下准备 workflow JSON 和 run manifest。
- 在明确确认后向本地 ComfyUI 端点提交任务。
- 可选轮询 `/history/{prompt_id}`，并通过 `/view` 下载输出图片。
- 将输出图片和 run manifest 写入 `generated/comfyui/`。

ComfyUI 输出只是参考。它们不能阻塞 gameplay greybox，并且在成为 Unreal texture、UI asset 或 concept source material 前必须经过审阅。

执行护栏：

- `run_visual_reference_workflow` 需要 `confirmed_side_effects=true`。
- 默认端点必须是 `localhost`、`127.0.0.1` 或 `::1`。
- 远程端点需要 `allow_remote_endpoint=true`。
- Workflow 模板必须保持在 `templates/comfyui/`。
- Workflow JSON、run manifest 和输出图片必须保持在 `generated/comfyui/`。
- 日志捕获到 `generated/logs/comfyui/`。
