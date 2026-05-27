# Fantasy Agent ChatGPT Workbench

Fantasy Agent ChatGPT Workbench exposes the production pipeline as a ChatGPT Apps-compatible MCP server and widget.

Fantasy Agent ChatGPT 工作台把游戏生产管线暴露为 ChatGPT Apps 可连接的 MCP 服务和交互式 widget。

## App Shape

- Archetype: `interactive-decoupled`
- Server: FastAPI JSON-RPC MCP endpoint at `/mcp`
- Widget resource: `ui://fantasy-agent/workbench.html`
- Tool policy: read-only, idempotent planning tools
- Side effects: none; Unreal, Blender, ComfyUI, and GitHub execution remain future explicit MCP steps

## Tools

| Tool | Purpose |
| --- | --- |
| `generate_game_production_plan` | Full Director workflow with gameplay DSL, GDD, Unreal, Blender, ComfyUI, QA, and next actions. |
| `render_gdd` | Structured bilingual markdown GDD. |
| `prepare_unreal_plan` | UE5 project folders, plugins, maps, Blueprint classes, and automation steps. |
| `prepare_blender_plan` | Procedural greybox asset jobs and export paths. |
| `prepare_comfyui_plan` | Gameplay-readable visual reference jobs. |
| `prepare_qa_plan` | Smoke, playability, failure, packaging, and metrics checks. |

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --app-dir apps/chatgpt-workbench --host 127.0.0.1 --port 8787
```

Open the local widget preview:

```text
http://127.0.0.1:8787
```

Check the MCP endpoint:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8787/health
```

## ChatGPT Developer Mode Setup

1. Run the local server on `http://127.0.0.1:8787/mcp`.
2. Expose it through an HTTPS tunnel, for example `ngrok http 8787`.
3. In ChatGPT, enable Developer Mode under Settings -> Apps & Connectors -> Advanced settings.
4. Create a new app/connector using the tunneled HTTPS URL plus `/mcp`.
5. Refresh the ChatGPT app after changing MCP tool descriptors, widget metadata, or resource HTML.

## Safety Boundary

This app is a production workbench, not a one-click game generator. The first version generates structured plans and handoffs only. Any future tool that writes files, launches Blender, starts Unreal, calls ComfyUI, packages builds, or pushes GitHub changes must declare side effects and require explicit user approval.

这个入口是生产工作台，不是一键生成游戏工具。第一版只生成结构化计划和交接物；未来任何写文件、启动 Blender、启动 Unreal、调用 ComfyUI、打包或推送 GitHub 的工具，都必须声明副作用并取得明确确认。

## Docs Basis

- https://developers.openai.com/apps-sdk/
- https://developers.openai.com/apps-sdk/quickstart
- https://developers.openai.com/apps-sdk/build/mcp-server
- https://developers.openai.com/apps-sdk/build/chatgpt-ui
- https://developers.openai.com/apps-sdk/plan/tools
- https://developers.openai.com/apps-sdk/reference

