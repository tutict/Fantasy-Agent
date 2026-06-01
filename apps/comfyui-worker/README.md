# ComfyUI Worker

ComfyUI Worker 根据 gameplay spec 准备并执行受控视觉参考任务。它不是玩法事实来源；它的输出用于在可玩循环收敛后支持可读性、材质语言、UI 方向和 texture seed。

本地运行：

```bash
uvicorn app.main:app --reload --app-dir apps/comfyui-worker
```

主要端点：

- `POST /visuals`
- 请求体：`GameplaySpec`
- 返回：`ComfyUIVisualPlan`

MCP 端点：

- `GET /mcp`
- `POST /mcp`
- 传输：JSON-RPC over HTTP
- 工具：
  - `prepare_visual_reference_workflows`
  - `run_visual_reference_workflow`

执行行为：

- Workflow 模板必须保持在 `templates/comfyui/`。
- 准备好的 workflow JSON 与 run manifest 保持在 `generated/comfyui/`。
- 日志保持在 `generated/logs/comfyui/`。
- 默认端点必须是本地：`http://127.0.0.1:8188`。
- 提交 prompt 需要 `confirmed_side_effects=true`。
- 生成图片成为 Unreal texture 或 UI asset 前必须经过审阅。

MCP payload 示例：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_visual_reference_workflow",
    "arguments": {
      "plan": {},
      "confirmed_side_effects": true,
      "wait_for_completion": false
    }
  }
}
```
