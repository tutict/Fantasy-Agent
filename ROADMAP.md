# Fantasy Agent 路线图

## 第一阶段：仓库基础

状态：已启动。

- 将旧 Spring/Flutter 项目保留在 `legacy/`。
- 建立模块化的 app、skill、MCP、template、generated、examples 和 docs 结构。
- 定义 prompt、玩法规格、GDD、Unreal 计划、Godot 计划、Blender 计划、ComfyUI 计划、QA 计划和 Director 计划的 Pydantic 合约。
- 定义 ComfyUI 视觉参考合约与 MCP 交接边界。
- 定义 `gameplay-schema.yaml`。
- 提供确定性的第一版 workflow。
- 文档化编排规则与游戏设计哲学。
- 增加兼容 ChatGPT Apps 的策划工作台，提供只读 MCP 规划工具和交互式 widget。
- 增加本地 Studio、流程控制台和 MCP 连接检测页。

## 第二阶段：玩法与 GDD 生成

- 用 LLM 支持的玩法生成替换确定性 prompt 解析。
- 为生成 YAML 增加 schema 校验。
- 将 GDD 渲染到 `generated/gdd.md`。
- 增加潜入、生存、谜题、战斗和移动原型示例。
- 增加循环连贯性、必填字段和目标会话时长测试。
- 在保持只读副作用边界的前提下，将 ChatGPT Workbench 工具从确定性规划扩展到 LLM 支持的玩法与 GDD 生成。

## 第三阶段：Blender MCP 集成

- 从 `BlenderAssetPlan` 生成 Blender Python 脚本。
- 支持模块化墙体、门、坡道、危险标记、目标道具、出口门和 UI proxy mesh。
- 生成包含材质、collection、尺寸和碰撞元数据的 Unreal import manifest。
- 实现 Blender MCP 服务合约。
- 通过 Blender Worker 暴露 Blender MCP JSON-RPC 端点。
- 从 `BlenderAssetPlan` 执行 `bpy` 程序化资产任务。
- 将 FBX 或 GLB 资产导出到 `generated/assets/`。
- 为 Unreal 生成 import manifest。
- 增加资产比例和碰撞检查。

## 第四阶段：ComfyUI MCP 集成

- 实现 ComfyUI MCP 服务合约。
- 通过 ComfyUI Worker 暴露 ComfyUI MCP JSON-RPC 端点。
- 从 `ComfyUIVisualPlan` 准备 allowlist workflow JSON 和 run manifest。
- 执行 allowlist ComfyUI workflow 模板。
- 将生成参考图写入 `generated/comfyui/`。
- 产出 prompt ID、run manifest 和审阅说明。
- 保持 ComfyUI 输出服务于玩法可读性需求。

## 第五阶段：Unreal MCP 集成

- 实现 Unreal MCP 服务合约。
- 创建 UE 工程目录、地图、Data Asset 和 Blueprint stub。
- 导入 Blender 生成资产。
- 运行 editor validation commandlet。
- 产出构建日志和失败摘要。

## 第六阶段：Godot 快速可玩验证

- 实现 Godot MCP 服务合约。
- 生成 `project.godot`、主场景、GDScript prototype 脚本和 import manifest。
- 运行结构校验与可选 headless import。
- 将 Godot 作为轻量 playability 验证目标，而不是替代 Unreal 主线。

## 第七阶段：可玩原型自动化

- 串联 Director Agent、玩法、GDD、Blender、ComfyUI、Unreal/Godot、QA 和 GitHub workflow。
- 灰盒需求经过审阅后再引入 ComfyUI 视觉参考。
- 打包 Windows development build。
- 对打包原型运行冒烟测试。
- 打开包含生成 spec、manifest 和自动化日志的 GitHub PR。
- 跟踪不同原型迭代的指标。

## 第八阶段：ChatGPT 生产工作台

- 增加 ChatGPT 托管生产计划的认证项目会话。
- 持久化已批准的 spec、GDD 和交接 manifest。
- 为会修改 Unreal、Godot、Blender、ComfyUI、GitHub 和打包工具的操作增加显式确认门禁。
- 将生产事件流回 ChatGPT widget。
- 等私有 Developer Mode 工作流稳定后，再准备提交就绪审阅。

## 非目标

- 不做虚假的 AAA 生产范围。
- 不生成没有机制支撑的装饰性程序化世界。
- 不隐藏工具副作用。
- 不生成无法在可玩循环中测试的内容。
