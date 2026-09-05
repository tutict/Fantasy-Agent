# 从 Prompt 到可玩原型的流程

Fantasy Agent 使用分阶段 workflow，保证每个产物在触发外部工具实际操作前都可以被检查、纠偏和确认。

## 阶段 1：想法输入

输入：

- 原始玩法想法。
- 目标游玩时长。
- 平台与引擎约束。
- 生产约束。

输出：

- `PromptRequest`

入口：

- 策划工作台 MCP tool call。
- Director Agent API。

本地流程控制台位于该阶段下游。它载入策划工作台的交接结果，记录纠偏说明，并检查执行前确认项，而不是重复收集玩法想法。

## 阶段 2：Gameplay DSL

Gameplay Agent 生成 `GameplaySpec`，包含：

- 玩家幻想。
- 设计支柱。
- 核心动词。
- 核心循环。
- 系统。
- 进程。
- 胜利状态。
- 失败状态。
- 关卡节奏。
- 资产需求。
- QA 重点。

## 阶段 3：GDD

GDD Writer 将 gameplay spec 渲染为 Markdown。它不添加新范围，只澄清实现意图。

## 阶段 4：资产、视觉和引擎交接

- Blender Worker 准备程序化资产任务，生成 Blender Python 脚本，并准备 Unreal import manifest。
- ComfyUI Worker 准备服务可读性、材质语言、UI 参考和经审阅 texture seed 的视觉参考任务。
- Unreal Builder 准备工程结构、地图、Blueprint 类和自动化步骤。
- Godot Builder 准备轻量 quick-play 工程，用于检查循环时长和路线可读性。

## 阶段 5：本地工具执行

本地工具桥接层在明确确认后执行受控操作：

- Studio 的 `/api/tools/{tool_name}` 端点暴露只读规划工具。
- Blender MCP 生成 allowlist 脚本，要求明确执行确认，运行 `bpy` 任务，捕获日志并导出资产。
- ComfyUI MCP 准备 allowlist workflow JSON，要求明确执行确认，提交 prompt job，捕获 prompt ID，并可下载已审阅的参考输出。
- Unreal MCP 创建、导入和验证工程内容。
- Godot MCP 创建和验证生成的 Godot 工程文件，并只在明确确认后运行 headless import。
- GitHub MCP 发布审阅分支和 PR。

## 阶段 6：QA 与打包

QA Agent 检查：

- 目标可读性。
- 循环完成情况。
- 失败反馈。
- 重开流程。
- 打包构建行为。

只有循环已经可玩后，才进入打包。
