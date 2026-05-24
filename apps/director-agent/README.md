# Director Agent

The Director Agent owns orchestration. It accepts a raw gameplay prompt, asks the gameplay workflow for a scoped design, renders a GDD, prepares Unreal and Blender handoffs, and returns the next build actions.

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/director-agent
```

Primary endpoint:

- `POST /plan` with a `PromptRequest`
- Returns a `DirectorBuildPlan`

This app is intentionally thin. Long-running execution should move into LangGraph or another workflow runner while keeping the Pydantic contracts stable.
