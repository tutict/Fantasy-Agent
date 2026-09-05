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

这些模型是各生产角色之间的边界。某个角色背后的实现可以从确定性 Python 切换到 LLM 调用、LangGraph 节点或本地工具调用，而下游消费者不需要重写。

## Studio 单进程

整个工作台只运行一个 FastAPI 服务：`apps/studio`。所有生产角色都是 `fantasy_agent/` 下的库内模块，由 Studio 直接调用，没有进程间 RPC，也没有对外暴露的 MCP 端点。

Studio 内的页面：

- **策划工作台**（`/workbench`）：负责创意挖掘和计划生成，通过 `POST /api/tools/{tool_name}` 调用只读规划工具。
- **流程控制台**（`/web-console`）：负责接收计划、记录纠偏和检查执行准备度。
- **工具环境检测**：负责检查 ComfyUI、Blender、Unreal、Godot 和 GitHub CLI 在本机是否可用。

## 库内生产角色

- Director：编排边界，负责完整 prompt-to-playable 流程。
- Gameplay Designer：从 prompt 生成 Gameplay DSL。
- Unreal Builder：准备 UE5 架构计划。
- Godot Builder：准备快速可玩验证用的 Godot 工程交接。
- Blender Worker：准备程序化资产任务、Blender Python 脚本和 Unreal import manifest。
- ComfyUI Worker：准备玩法可读的视觉参考计划、workflow 和受控本地执行。
- Creative Reviewer：审阅生成图片和模型，阻塞未批准资产进入引擎。
- QA：准备可玩性、失败反馈、打包和性能检查。

## 本地工具桥接

`fantasy_agent/` 下的 `*_mcp.py` 模块不是对外 MCP Server，而是本机工具的受控桥接层：

- `blender_mcp.py` / `blender_runtime.py`：生成 allowlist 脚本并运行 `bpy` 任务。
- `comfyui_mcp.py`：准备 allowlist workflow JSON 并提交 prompt job。
- `unreal_mcp.py`：创建、导入和验证 UE 工程内容。
- `godot_mcp.py`：创建和验证 Godot 工程文件，只在明确确认后运行 headless import。
- `local_tools.py`：探测本机可执行文件，并封装 GitHub CLI 等本地操作。

所有页面与 API 都只监听 `127.0.0.1`，默认地址为 `http://127.0.0.1:7860`。
