# Director Agent

Director Agent 负责整体编排。它接收原始玩法 prompt，调用 gameplay workflow 生成收敛后的设计，渲染 GDD，准备 Unreal、Godot、Blender、ComfyUI 和 QA 交接，并返回下一步构建动作。

本地运行：

```bash
uvicorn app.main:app --reload --app-dir apps/director-agent
```

主要端点：

- `POST /plan`，请求体为 `PromptRequest`。
- 返回 `DirectorBuildPlan`。

这个 app 故意保持很薄。长耗时执行应移动到 LangGraph 或其他 workflow runner，同时保持 Pydantic 合约稳定。
