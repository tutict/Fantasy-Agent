# Web Console

The Fantasy Agent Web Console is a local browser interface for the Director workflow.

It is an operator surface, not a landing page. The first screen lets the user enter a gameplay idea, set the target session length, choose source/output languages, add constraints, and generate a structured production plan.

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

- Calls `/api/plan`, which reuses `fantasy_agent.workflows.run_director_workflow`.
- Displays Overview, Gameplay DSL, GDD, Build, Visuals, and QA tabs.
- Supports English and Simplified Chinese UI labels.
- Displays bilingual GDD output from `GDDDocument.markdown_by_locale`.
- Shows Unreal, Blender, ComfyUI, and QA handoff plans.

## Boundaries

- The UI does not call external model services.
- It does not execute Unreal, Blender, or ComfyUI side effects.
- MCP execution should remain explicit and logged through the MCP layer.

## 中文说明

Fantasy Agent Web Console 是 Director workflow 的本地浏览器界面。

它不是营销首页，而是操作台。第一屏可以输入玩法想法、设置目标时长、选择输入/输出语言、添加约束，并生成结构化生产计划。

界面展示：

- 概览
- Gameplay DSL
- GDD
- Unreal/Blender 构建计划
- ComfyUI 视觉参考计划
- QA 检查计划
