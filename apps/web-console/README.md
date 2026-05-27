# Fantasy Agent Web Console

The Web Console is a local operator interface for Fantasy Agent. It runs a FastAPI server, serves the static UI, and exposes the Director workflow through `/api/plan`.

Run from the repository root:

```bash
uvicorn app.main:app --reload --app-dir apps/web-console --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860
```

The interface supports English and Simplified Chinese output, target session controls, constraints, and structured views for Gameplay DSL, GDD, Unreal, Blender, ComfyUI, and QA plans.
