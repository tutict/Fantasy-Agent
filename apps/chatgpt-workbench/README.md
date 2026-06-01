# Fantasy Agent 策划工作台

Fantasy Agent 策划工作台把游戏生产管线暴露为兼容 ChatGPT Apps 的 MCP 服务和交互式 widget。

## App 形态

- 原型：`interactive-decoupled`
- 服务：FastAPI JSON-RPC MCP 端点 `/mcp`
- Widget resource：`ui://fantasy-agent/workbench.html`
- 工具策略：只读、幂等的规划工具
- 副作用：无；Unreal、Godot、Blender、ComfyUI 和 GitHub 执行仍是未来显式 MCP 步骤

## 工具

| 工具 | 用途 |
| --- | --- |
| `extract_idea_seed` | 访谈式创意挖掘，把松散回答整理为 `IdeaSeed` 和生产 prompt。 |
| `decompose_production_tasks` | 执行前可检查的任务板。 |
| `generate_game_production_plan` | 完整 Director workflow，包含 Gameplay DSL、GDD、Unreal、Godot、Blender、ComfyUI、QA 和下一步。 |
| `prepare_production_pipeline` | 分阶段的玩法、ComfyUI、Blender、整合、Unreal/Godot 和 QA 管线。 |
| `render_gdd` | 结构化 Markdown GDD。 |
| `prepare_unreal_plan` | UE5 工程目录、插件、地图、Blueprint 类和自动化步骤。 |
| `prepare_godot_plan` | Godot quick-play 场景、脚本、输入动作和导入交接步骤。 |
| `prepare_blender_plan` | 程序化灰盒资产任务和导出路径。 |
| `prepare_comfyui_plan` | 玩法可读的视觉参考任务。 |
| `prepare_qa_plan` | 冒烟、可玩性、失败、打包和指标检查。 |

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --app-dir apps/chatgpt-workbench --host 127.0.0.1 --port 8787
```

打开本地 widget 预览：

```text
http://127.0.0.1:8787
```

检查 MCP 端点：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8787/health
```

## ChatGPT Developer Mode 设置

1. 在本地运行 `http://127.0.0.1:8787/mcp`。
2. 通过 HTTPS 隧道暴露，例如 `ngrok http 8787`。
3. 在 ChatGPT 中进入 Settings -> Apps & Connectors -> Advanced settings，启用 Developer Mode。
4. 使用隧道 HTTPS URL 加 `/mcp` 创建新的 app/connector。
5. 修改 MCP tool descriptor、widget metadata 或 resource HTML 后刷新 ChatGPT app。

## 安全边界

这个入口是策划工作台，不是一键生成游戏工具。第一版只生成结构化计划和交接物；未来任何写文件、启动 Blender、启动 Unreal/Godot、调用 ComfyUI、打包或推送 GitHub 的工具，都必须声明副作用并取得明确确认。

## 参考文档

- https://developers.openai.com/apps-sdk/
- https://developers.openai.com/apps-sdk/quickstart
- https://developers.openai.com/apps-sdk/build/mcp-server
- https://developers.openai.com/apps-sdk/build/chatgpt-ui
- https://developers.openai.com/apps-sdk/plan/tools
- https://developers.openai.com/apps-sdk/reference
