# Gameplay Agent

Gameplay Agent 将 prompt 转换为结构化 Gameplay DSL 文档。它在视觉风格之前优先处理核心循环、系统、节奏、进程、胜利状态和失败状态。

本地运行：

```bash
uvicorn app.main:app --reload --app-dir apps/gameplay-agent
```

主要端点：

- `POST /design`，请求体为 `PromptRequest`。
- 返回 `GameplaySpec`。
