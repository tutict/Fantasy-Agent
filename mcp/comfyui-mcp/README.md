# ComfyUI MCP

ComfyUI MCP will execute controlled local ComfyUI workflows for visual reference generation.

Endpoint:

```text
apps/comfyui-worker -> /mcp
```

Initial scope:

- Load allowlisted workflow templates from `templates/comfyui/`.
- Inject prompt and negative prompt text from `ComfyUIVisualPlan`.
- Prepare workflow JSON and run manifests under `generated/comfyui/`.
- Submit jobs to a local ComfyUI endpoint after explicit confirmation.
- Optionally poll `/history/{prompt_id}` and download output images through `/view`.
- Write output images and run manifests under `generated/comfyui/`.

ComfyUI outputs are references. They must not block the gameplay greybox, and they require review before becoming Unreal textures, UI assets, or concept source material.

Execution guardrails:

- `run_visual_reference_workflow` requires `confirmed_side_effects=true`.
- Default endpoint must be `localhost`, `127.0.0.1`, or `::1`.
- Remote endpoints require `allow_remote_endpoint=true`.
- Workflow templates must stay under `templates/comfyui/`.
- Workflow JSON, run manifests, and output images must stay under `generated/comfyui/`.
- Logs are captured under `generated/logs/comfyui/`.
