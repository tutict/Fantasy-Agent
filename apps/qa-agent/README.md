# QA Agent

QA Agent 将 gameplay spec 转换为垂直切片所需的冒烟测试、可玩性检查、失败反馈检查、打包检查和 telemetry 指标。

本地运行：

```bash
uvicorn app.main:app --reload --app-dir apps/qa-agent
```

主要端点：

- `POST /qa`
- 请求体：`GameplaySpec`
- 返回：`QAPlan`
