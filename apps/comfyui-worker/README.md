# ComfyUI Worker

The ComfyUI Worker prepares and executes controlled visual reference jobs from a gameplay spec. It is not the gameplay source of truth. Its outputs support readability, material language, UI direction, and texture seeds after the playable loop is scoped.

ComfyUI Worker 只负责玩法可读性的视觉参考，不负责决定玩法。

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/comfyui-worker
```

Primary endpoint:

- `POST /visuals`
- Request body: `GameplaySpec`
- Returns: `ComfyUIVisualPlan`

MCP endpoint:

- `GET /mcp`
- `POST /mcp`
- Transport: JSON-RPC over HTTP
- Tools:
  - `prepare_visual_reference_workflows`
  - `run_visual_reference_workflow`

Execution behavior:

- Workflow templates must stay under `templates/comfyui/`.
- Prepared workflow JSON and run manifests stay under `generated/comfyui/`.
- Logs stay under `generated/logs/comfyui/`.
- Default endpoint must be local: `http://127.0.0.1:8188`.
- Prompt submission requires `confirmed_side_effects=true`.
- Generated images require review before becoming Unreal textures or UI assets.

Example MCP payload:

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
