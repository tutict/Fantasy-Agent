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
- 增加本地策划工作台页面，提供只读规划 REST 工具与交互式界面。
- 增加本地 Studio、流程控制台和工具环境检测页。

## 第二阶段：玩法与 GDD 生成

- 用 LLM 支持的玩法生成替换确定性 prompt 解析。
- 为生成 YAML 增加 schema 校验。
- 将 GDD 渲染到 `generated/gdd.md`。
- 增加潜入、生存、谜题、战斗和移动原型示例。
- 增加循环连贯性、必填字段和目标会话时长测试。
- 在保持只读安全边界的前提下，将策划工作台工具从确定性规划扩展到 LLM 支持的玩法与 GDD 生成。

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
- M6b 敌人系统：`GameplaySpec.enemies`、Godot `enemy_controller.gd`、路线敌人生成和失败联动已完成第一轮垂直切片。
- M6c 敌人压力：执行链生成 deterministic enemy pressure report，Studio 可调敌人数、速度、侦测、巡逻和远程间隔倍率。
- Approval manifest：Creative Review 决策可持久化到 `generated/asset-approval-manifest.yaml`，继续阻塞未经批准的资产导入。
- M6d 资产执行：Studio / Flow Console 已能独立触发 ComfyUI 与 Blender 资产工人，复用两段式确认和后台 job 轮询。
- M6e 审批门控导入：Godot `--with-assets` 路径会按 approval manifest 过滤 Blender GLB，未批准资产不会复制进工程。
- M6f 审批门控 QA 与预览：executor 写出 `approval-gate-report.yaml`，前端阶段卡片显示 manifest、报告路径、批准/跳过资产和待修订状态。

## 第七阶段：可玩原型自动化

- 串联 Director Agent、玩法、GDD、Blender、ComfyUI、Unreal/Godot、QA 和 GitHub workflow。
- 灰盒需求经过审阅后再引入 ComfyUI 视觉参考。
- 打包 Windows development build。
- 对打包原型运行冒烟测试。
- 打开包含生成 spec、manifest 和自动化日志的 GitHub PR。
- 跟踪不同原型迭代的指标。

## M7：Agent 可执行生产 Spec

状态：M7.1-M7.5 已完成第一轮垂直切片。

- [x] M7.1：Bundle loader、深度校验、`--spec-file` 与执行阻断。
- [x] M7.2：Godot 以 Combat/Level/Numeric/Narrative Spec 为主驱动，保留旧 payload 回退。
- [x] M7.3：ConfigTableCompiler 支持 YAML/JSON/CSV-ready，并同步 approval manifest 状态。
- [x] M7.4：Studio / Flow Console 展示 Spec Bundle、校验、产物、字段追踪与 QA。
- [x] M7.5：Unreal DataTable/DataAsset adapter 与机器可执行 QA 接入执行链。

后续验证重点：真实 Unreal Editor 导入 adapter 源、PIE 指标采集、Godot packaged playtest 和跨版本 schema migration。
## 第八阶段：独立工作台生产化

- 增加本地托管生产计划的项目会话。
- 持久化已批准的 spec、GDD 和交接 manifest。
- 为会修改 Unreal、Godot、Blender、ComfyUI、GitHub 和打包工具的操作增加执行前确认。
- 将生产事件流回 Studio 工作台页面。
- 保持单进程本地自闭环；不引入任何对外暴露的协议端点。

## 非目标

- 不做虚假的 AAA 生产范围。
- 不生成没有机制支撑的装饰性程序化世界。
- 不隐藏工具实际操作。
- 不生成无法在可玩循环中测试的内容。
