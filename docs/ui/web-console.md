# 流程控制台

Fantasy Agent 流程控制台是 Director workflow 的本地执行准备度界面。

它不是营销首页，而是操作台。玩法输入属于策划工作台；流程控制台负责载入策划交接，检查执行准备度，记录纠偏，并在 ComfyUI、Blender、Unreal 或 Godot 执行前确认副作用门禁。

## 运行

从仓库根目录启动：

```bash
uvicorn app.main:app --reload --app-dir apps/web-console --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

通常更推荐通过 Studio 统一入口访问：

```text
http://127.0.0.1:7860
```

## 能力

- 从本地浏览器存储载入最新策划工作台交接。
- 为需要直接访问 Director workflow 的 API 客户端保留 `/api/plan`。
- 展示 Overview、Gameplay DSL、GDD、Build、Visuals 和 QA tabs。
- 支持简体中文界面文案。
- 展示 `GDDDocument.markdown_by_locale` 中的 GDD 输出。
- 展示 Unreal、Godot、Blender、ComfyUI 和 QA 交接计划。
- 记录玩法、视觉方向、范围和技术导入审阅的纠偏说明。

## 边界

- UI 不调用外部模型服务。
- UI 不执行 Unreal、Godot、Blender 或 ComfyUI 副作用。
- MCP 执行必须保持显式确认，并通过 MCP 层记录日志。
