# ComfyUI Worker

The ComfyUI Worker prepares visual reference jobs from a gameplay spec. It is not the gameplay source of truth. Its outputs support readability, material language, UI direction, and texture seeds after the playable loop is scoped.

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/comfyui-worker
```

Primary endpoint:

- `POST /visuals`
- Request body: `GameplaySpec`
- Returns: `ComfyUIVisualPlan`

Future execution should go through `comfyui-mcp` so prompt jobs, output paths, and side effects are logged.
