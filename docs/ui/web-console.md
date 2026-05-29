# Flow Console

The Fantasy Agent Flow Console is a local execution-readiness interface for the Director workflow.

It is an operator surface, not a landing page. Gameplay intake belongs in the Planning Workbench. The Flow Console loads that planning handoff, then helps the user review execution readiness, capture correction notes, and inspect side-effect gates before ComfyUI, Blender, or Unreal work runs.

## Run

From the repository root:

```bash
uvicorn app.main:app --reload --app-dir apps/web-console --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860
```

## Capabilities

- Loads the latest Planning Workbench handoff from local browser storage.
- Keeps `/api/plan` available for API clients that need the Director workflow directly.
- Displays Overview, Gameplay DSL, GDD, Build, Visuals, and QA tabs.
- Supports English and Simplified Chinese UI labels.
- Displays bilingual GDD output from `GDDDocument.markdown_by_locale`.
- Shows Unreal, Blender, ComfyUI, and QA handoff plans.
- Records correction notes for gameplay, visual direction, scope, and technical import review.

## Boundaries

- The UI does not call external model services.
- It does not execute Unreal, Blender, or ComfyUI side effects.
- MCP execution should remain explicit and logged through the MCP layer.

## 中文说明

Fantasy Agent 流程控制台是 Director workflow 的本地浏览器界面。

它不是营销首页，而是操作台。玩法输入属于策划工作台；流程控制台负责载入策划交接，检查执行准备度，记录纠偏，并在 ComfyUI、Blender 或 Unreal 执行前确认副作用门禁。

界面展示：

- 策划交接
- 纠偏队列
- 概览
- Gameplay DSL
- GDD
- Unreal/Blender 构建计划
- ComfyUI 视觉参考计划
- QA 检查计划
