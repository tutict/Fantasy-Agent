# Fantasy Agent ChatGPT Apps MCP

This MCP entrypoint exposes Fantasy Agent as a ChatGPT Apps workbench.

这个 MCP 入口把 Fantasy Agent 暴露为 ChatGPT Apps 工作台。

## Endpoint

```text
apps/chatgpt-workbench -> /mcp
```

Local default:

```text
http://127.0.0.1:8787/mcp
```

## Resource

```text
ui://fantasy-agent/workbench.html
```

The resource returns a self-contained HTML widget using the ChatGPT Apps bridge when available and a local debug route when previewed in a browser.

## Tool Boundary

The first version is read-only. It may generate production plans, GDD markdown, Unreal plans, Blender plans, ComfyUI plans, and QA plans. It must not launch tools, create engine projects, generate images, package builds, or push repository changes.

第一版只读。它可以生成生产计划、GDD、Unreal 计划、Blender 计划、ComfyUI 计划和 QA 计划，但不能启动工具、创建引擎项目、生成图像、打包构建或推送仓库变更。

