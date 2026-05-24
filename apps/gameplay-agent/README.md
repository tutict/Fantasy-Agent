# Gameplay Agent

The Gameplay Agent turns prompts into a structured Gameplay DSL document. It focuses on core loop, systems, pacing, progression, win state, and failure state before visual style.

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/gameplay-agent
```

Primary endpoint:

- `POST /design` with a `PromptRequest`
- Returns a `GameplaySpec`
