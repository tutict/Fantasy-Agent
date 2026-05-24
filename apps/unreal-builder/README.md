# Unreal Builder

The Unreal Builder prepares UE5 project architecture from the gameplay spec. It does not invent content; it creates a concrete project, folder, Blueprint, map, and automation plan that can be executed by Unreal Python or Unreal MCP.

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/unreal-builder
```

Primary endpoint:

- `POST /prepare`
- Request body: `GameplaySpec`
- Returns: `UnrealProjectPlan`
