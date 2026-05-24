# QA Agent

The QA Agent converts a gameplay spec into smoke tests, playability checks, failure checks, packaging checks, and telemetry metrics for the vertical slice.

Run locally:

```bash
uvicorn app.main:app --reload --app-dir apps/qa-agent
```

Primary endpoint:

- `POST /qa`
- Request body: `GameplaySpec`
- Returns: `QAPlan`
