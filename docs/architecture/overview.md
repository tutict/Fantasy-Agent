# 架构概览

Fantasy Agent 围绕稳定合约和可替换 worker 组织。每个智能体只拥有一个清晰责任边界，输出通过 Pydantic 模型和生成产物交接。

## 主流程

```text
PromptRequest
  -> 策划工作台或本地 API
  -> Director Agent
  -> Gameplay Agent
  -> GameplaySpec
  -> GDD Writer
  -> Unreal Builder
  -> Godot Builder
  -> Blender Worker
  -> ComfyUI Worker
  -> QA Agent
  -> MCP tools
  -> 可玩原型产物
```

## 共享合约

`fantasy_agent/` 包定义第一层合约：

- `PromptRequest`
- `GameplaySpec`
- `GDDDocument`
- `UnrealProjectPlan`
- `GodotProjectPlan`
- `BlenderAssetPlan`
- `ComfyUIVisualPlan`
- `CreativeReviewReport`
- `QAPlan`
- `DirectorBuildPlan`
- `MCPToolContract`

这些模型是智能体之间的边界。某个智能体背后的实现可以从确定性 Python 切换到 LLM 调用、LangGraph 节点或 MCP 工具，而下游消费者不需要重写。

## App Worker

每个 app 都是一个小型 FastAPI 服务：

- `studio`：本地桌面式入口，聚合策划工作台、流程控制台和 MCP 检测页。
- `director-agent`：编排边界。
- `chatgpt-workbench`：ChatGPT Apps MCP 端点和交互式 widget。
- `gameplay-agent`：从 prompt 生成 Gameplay DSL。
- `unreal-builder`：准备 UE5 架构计划。
- `godot-builder`：准备快速可玩验证用的 Godot 工程交接。
- `blender-worker`：准备程序化资产任务、Blender Python 脚本和 Unreal import manifest。
- `comfyui-worker`：准备玩法可读的视觉参考计划、workflow 和受控 ComfyUI MCP 执行。
- `creative-review-agent`：审阅生成图片和模型，阻塞未批准资产进入引擎。
- `qa-agent`：准备可玩性、失败反馈、打包和性能检查。

## ChatGPT Apps 入口

策划工作台复用同一套合约，提供创意提取、计划生成、GDD 渲染、Unreal 计划、Godot 快速可玩计划、Blender 计划、ComfyUI 计划和 QA 计划等只读工具。第一阶段不执行生产副作用。

## 本地 Studio

Studio 是面向用户的整合面板：

- 策划工作台负责创意挖掘和计划生成。
- 流程控制台负责接收计划、记录纠偏和检查执行准备度。
- MCP 页面负责检查 Fantasy Agent MCP、ComfyUI、Blender、Unreal、Godot 和 GitHub CLI 的连接状态。

这些页面共用本地 `apps/studio` 服务，默认地址为 `http://127.0.0.1:7860`。
