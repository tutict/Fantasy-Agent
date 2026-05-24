# Blender Worker

The Blender Worker prepares procedural asset jobs for greybox and readability-first asset passes. It targets Blender Python and future Blender MCP execution.

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/blender-worker
```

Primary endpoint:

- `POST /assets`
- Request body: `GameplaySpec`
- Returns: `BlenderAssetPlan`
