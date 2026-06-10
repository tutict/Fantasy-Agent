# Fantasy Agent 编排规则

Fantasy Agent 的智能体是模块化生产工人。每个智能体只负责清晰边界内的任务，接收结构化输入，返回结构化输出，未来可以由 LLM、LangGraph 节点、本地脚本或 MCP 工具驱动。

## 全局规则

- 玩法优先于图形。
- 每个生成资产、机制和自动化步骤都必须服务可玩循环。
- 目标是 5 到 15 分钟的垂直切片。
- 优先做一个内聚循环，而不是多个断开的功能。
- 不创建空洞的程序化空间。
- 不隐藏不确定性。必须标出假设和未解决的生产风险。
- MCP 工具的实际操作必须在执行前声明清楚。
- QA 检查必须先于打包和视觉扩展。
- 面向人的文档、界面和设计说明优先使用简体中文。
- 实现标识保持英文：类名、Blueprint 名、目录路径、MCP tool 名和 metric key 不翻译。
- ComfyUI 是视觉参考工人，不是玩法权威。
- ComfyUI 与 Blender 输出必须先通过 Creative Review，再进入 Unreal 或 Godot 导入。
- Godot 是快速可玩验证目标，不替代 Unreal 主线生产导入。
- ChatGPT Apps 工具是交互式计划入口；没有明确确认时不得执行生产实际操作。

## 语言规则

- Canonical implementation identifiers 保持英文：class name、Blueprint name、folder path、MCP tool name 和 metric key。
- 面向人的设计文本当前以 `zh-CN` 为主。
- 核心 DSL 仍保存稳定英文主字段；需要多语言时，字段路径翻译放在可选 `i18n` 下。
- GDD 与审阅文本可以按 `PromptRequest.output_locales` 输出多语言版本。

## 智能体交接合约

智能体通过 `fantasy_agent/contracts.py` 中的 Pydantic 模型，以及 `generated/` 下的 YAML 或 Markdown 产物交换信息。

必要交接属性：

- `source`：产出智能体或工具。
- `schema_version`：gameplay DSL 或 tool contract 版本。
- `inputs`：来源 prompt、spec 或 manifest。
- `outputs`：生成产物。
- `risks`：阻塞问题或假设。
- `next_actions`：具体下一步。

## Director Agent

职责：

- 负责完整 prompt-to-playable workflow。
- 将工作路由到 Gameplay Agent、GDD Writer、Unreal Builder、Godot Builder、Blender Worker、ComfyUI Worker、QA Agent 和未来 MCP 工具。
- 拒绝无法合理产出可玩垂直切片的范围。

输入：

- `PromptRequest`

输出：

- `DirectorBuildPlan`

流程：

1. 归一化 prompt 和约束。
2. 生成玩法优先的 spec。
3. 渲染 GDD。
4. 准备 Unreal、Godot、Blender 和 ComfyUI 交接。
5. 准备 QA 计划。
6. 返回下一步和风险。

## Gameplay Agent

职责：

- 将原始 prompt 转换为连贯的玩法系统。
- 定义核心循环、动词、节奏、进程、胜利状态和失败状态。

输入：

- `PromptRequest`

输出：

- `GameplaySpec`

规则：

- 只有能改变玩家决策的机制才有效。
- 只有能在灰盒地图中测试的循环才有效。
- 失败状态必须帮助玩家理解下一次尝试。

可选 LLM 后端：

- 默认使用确定性生成（`design_from_prompt_deterministic`），基于关键词与模板，无需任何外部依赖或 API key。
- 设置环境变量 `FANTASY_AGENT_USE_LLM=1`（或在 CLI 传 `--llm`）可启用 LLM 后端，由 `fantasy_agent/llm.py` 统一调用 Claude 生成 `GameplaySpec`。
- 模型默认 `claude-opus-4-8`，可通过 `FANTASY_AGENT_MODEL` 覆盖；凭据走标准的 `ANTHROPIC_API_KEY`。
- LLM 依赖是可选安装项：`pip install fantasy-agent[llm]`。
- 任何 LLM 失败（未安装、无 key、API 错误、输出非法或未通过 `GameplaySpec` 校验）都会自动回退到确定性生成，绝不中断流程。无论走哪条路径，返回的都是同一套 `GameplaySpec` 契约，下游 Unreal/Godot/Blender/ComfyUI/QA 编排无需改动。

命令行入口：

- `python -m fantasy_agent --prompt "游戏创意" [--llm] [--minutes 10] [--engine "Godot 4"] [--format summary|json|gdd]`
- 安装后亦可用 `fantasy-agent` 控制台命令。

## GDD Writer

职责：

- 将 gameplay spec 转换成结构化 Markdown 设计文档。
- 保留玩法意图，不添加未经批准的功能。

输入：

- `GameplaySpec`

输出：

- `GDDDocument`

规则：

- 面向实现编写。
- 区分已确认设计和假设。
- 美术方向必须服从互动可读性。

## Level Director

职责：

- 将玩法循环转换为关卡节奏和灰盒需求。
- 保持空间计划足够紧凑，方便快速迭代。

输入：

- `GameplaySpec`

输出：

- 关卡节奏计划。
- encounter 或目标计划。
- 灰盒资产需求。

规则：

- 第一分钟必须教会循环。
- 中段必须组合系统。
- 最后一段必须强制玩家使用完整循环。

## Unreal Builder

职责：

- 准备 UE5 工程结构、插件、地图、Blueprint 类、Data Asset 和自动化步骤。

输入：

- `GameplaySpec`

输出：

- `UnrealProjectPlan`

未来 MCP 兼容性：

- Unreal MCP 只应执行 allowlist 内的工程创建、资产导入、地图验证和打包命令。

## Godot Builder

职责：

- 为快速可玩循环验证准备 Godot 4 工程交接。
- 在 generated 路径下生成 `project.godot`、主场景、GDScript prototype 脚本和 import manifest。

输入：

- `GameplaySpec`

输出：

- `GodotProjectPlan`

规则：

- Godot 用于在较重 Unreal 工作前验证循环时长、路线可读性和交互节奏。
- Godot MCP 执行必须将工程保持在 `generated/godot/`，日志保持在 `generated/logs/godot/`。
- 没有明确执行确认时，不得启动 Godot 或运行 headless import。

执行编排（Executor）：

- `fantasy_agent/executor.py` 的 `execute_godot_demo()` 是从 `DirectorBuildPlan` 到可运行 Godot 工程的编排层，串联现有 godot MCP 三步：`create_godot_project_structure(write_files=True)` → `validate_godot_project` → `run_godot_import(confirmed_side_effects=True)`，逐阶段回报状态/日志/产物，不重复实现引擎逻辑。
- 工程文件由 `GameplaySpec` 驱动：`level_beats` 映射为路线分段（每个 beat 一段 floor + 由其 `required_assets` 关键词决定材质语义的标记体），`win_state`/`failure_states` 注入 `main.gd`。不同创意产出不同灰盒，而非固定模板。
- 单次总确认门：`confirmed=False` 时只返回"将执行的副作用清单"且不写盘；`confirmed=True` 后每个副作用阶段仍各自带 `write_files` / `confirmed_side_effects` 标志。
- session 产物布局：`generated/godot/sessions/<session_id>/<project>/`，保持在 `generated/godot/` 沙箱前缀内。
- M1 不做失败自动重试；失败阶段附带捕获的日志路径。
- CLI：`python -m fantasy_agent --prompt "..." --engine "Godot 4" --execute [--yes] [--godot-exe PATH] [--no-import]`。不带 `--yes` 打印副作用清单；不带 `--execute` 仍是纯规划。Godot 可执行文件由 `local_tools._find_godot()` 自动探测（含 `~/Downloads` 下的版本）。
- 资产链（M2）：加 `--with-assets` 在 create 前插入 Blender 阶段（导出 glb）并在 import 前复制进工程；`--blender-exe PATH` 覆盖探测。阶段顺序 blender→create→copy_assets→validate→import。Blender 失败自动降级为纯灰盒。`main.gd` 的 beat 标记体会先尝试 `load("res://assets/generated/<asset>.glb")`，缺失则回退到程序化 box——因此无资产时行为与纯灰盒一致。

## Blender Worker

职责：

- 准备支持灰盒可玩性和互动可读性的程序化资产任务。
- 从已批准的 `BlenderAssetPlan` 交接生成 Blender Python 脚本。

输入：

- `GameplaySpec`

输出：

- `BlenderAssetPlan`

规则：

- 先生成模块化资产。
- 使用比例正确的导出。
- 按玩法角色命名资产。
- 每次导出都生成 `UCX_` 碰撞对象和 Unreal import manifest。
- 没有明确执行确认时，不得从规划界面运行 Blender。
- Blender MCP 执行必须将脚本放在 `generated/blender/`，导出放在 `generated/assets/`，日志放在 `generated/logs/blender/`。

Blender → Godot 资产链（M2）：

- Executor 的 `--with-assets` 路径会先跑 Blender 导出 **glb**（Godot 4 原生格式），再把 `.glb` 复制进 Godot 工程的 `assets/generated/`，由 `godot --headless --import` 导入。
- 导出格式由 `BlenderAssetPlan.export_format` 决定；executor 在 Godot 路径下强制 `glb`。`enrich_blender_job` 按格式规范化扩展名（不再出现 `name.fbx.glb` 双扩展名）。
- `fantasy_agent/godot_assets.py` 的 `copy_assets_into_godot_project` 只复制 `.glb`，`.fbx` 跳过并记录（Godot 需 fbx2gltf 转换器，M2 不处理；Unreal 线仍独立用 fbx）。
- **降级语义**：Blender 不可用或执行失败时，blender 阶段标记 failed，整条链继续以纯灰盒完成，不中断。
- 重要约束：Blender 阶段要求 `workspace_root` 为仓库根（生成的脚本需 import `fantasy_agent.blender_runtime`）。纯 Godot 路径无此约束。

## ComfyUI Worker

职责：

- 为 ComfyUI 准备服务玩法可读性的视觉参考任务。
- 在玩法需求明确后生成 concept、material、UI、texture seed 或 storyboard 参考。

输入：

- `GameplaySpec`

输出：

- `ComfyUIVisualPlan`

规则：

- 不因图像生成阻塞灰盒工作。
- 每个 prompt 都必须包含玩法约束。
- 生成图片成为 Unreal texture 或 UI asset 前必须经过审阅。
- 避免不说明目标、危险、路线、材质或反馈的装饰图片。
- ComfyUI MCP 执行必须将模板放在 `templates/comfyui/`，输出放在 `generated/comfyui/`，日志放在 `generated/logs/comfyui/`。
- 没有明确执行确认时，不得向 ComfyUI 提交 prompt。

## Creative Review Agent

职责：

- 在 Unreal 或 Godot 导入前，与用户一起审阅 ComfyUI 参考图和 Blender mesh。
- 将用户审美、艺术方向、玩法可读性和技术导入检查转换为结构化审批决策。
- 将被拒绝或不明确的资产转回具体 ComfyUI 或 Blender 修改请求。

输入：

- `CreativeReviewRequest`

输出：

- `CreativeReviewReport`

规则：

- 生成参考或 mesh 成为引擎导入候选前必须获得用户批准。
- 审阅关卡会阻塞引擎导入，直到资产被批准、修改或拒绝。
- 反馈必须说明资产名称、玩法角色和具体修改请求。

## ChatGPT Workbench

职责：

- 将 Fantasy Agent 暴露为兼容 ChatGPT Apps 的交互式工作台。
- 将 ChatGPT tool call 路由到本地智能体使用的同一套结构化规划合约。
- 在 widget 中渲染玩法、GDD、Unreal、Godot、Blender、ComfyUI 和 QA 交接。

输入：

- `PromptRequest`

输出：

- `DirectorBuildPlan`
- 聚焦子计划，例如 `GDDDocument`、`UnrealProjectPlan`、`GodotProjectPlan`、`BlenderAssetPlan`、`ComfyUIVisualPlan` 或 `QAPlan`

规则：

- 在明确执行前确认机制实现前，工具必须保持只读且幂等。
- Widget 状态可以总结计划，但实现标识保持英文。
- ChatGPT 交互必须保持玩法优先层级和 i18n 输出。
- 默认不得从该界面启动 Unreal、Godot、Blender、ComfyUI、打包、写文件或推送 GitHub。

## QA Agent

职责：

- 将 gameplay spec 转换为测试，验证可玩性、失败反馈和打包准备度。

输入：

- `GameplaySpec`

输出：

- `QAPlan`

规则：

- 先测试循环，再做打磨。
- 检查完成时间、重开流程、目标可读性和打包构建行为。
