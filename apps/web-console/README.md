# Fantasy Agent 流程控制台

流程控制台是 Fantasy Agent 的执行准备度界面。它运行 FastAPI 服务，提供静态 UI，并消费策划工作台生成的 planning handoff。

从仓库根目录运行：

```bash
uvicorn app.main:app --reload --app-dir apps/web-console --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

界面支持简体中文输出、策划交接审阅、纠偏记录、副作用门禁，以及 Gameplay DSL、GDD、Unreal、Godot、Blender、ComfyUI 和 QA 计划的结构化视图。
