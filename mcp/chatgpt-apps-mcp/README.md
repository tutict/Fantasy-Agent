# Fantasy Agent ChatGPT Apps MCP

这个 MCP 入口把 Fantasy Agent 暴露为 ChatGPT Apps 工作台。

## 端点

```text
apps/chatgpt-workbench -> /mcp
```

本地默认地址：

```text
http://127.0.0.1:8787/mcp
```

## Resource

```text
ui://fantasy-agent/workbench.html
```

该 resource 返回一个自包含 HTML widget。在 ChatGPT 环境中使用 ChatGPT Apps bridge，在本地浏览器预览时使用 debug route。

## 工具边界

第一版只读。它可以生成生产计划、GDD Markdown、Unreal 计划、Godot 计划、Blender 计划、ComfyUI 计划和 QA 计划。它不得启动工具、创建引擎工程、生成图片、打包构建或推送仓库变更。
