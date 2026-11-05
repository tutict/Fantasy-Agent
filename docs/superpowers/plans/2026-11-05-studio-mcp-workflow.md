# Codex 通过 MCP 驱动灵构工坊全流程

> 用户已批准实施。基线 `4af893bb61e513c9f2fdb74adcb9bd03e23cf4b5`。
> 实施分支 `codex/studio-mcp-workflow`。外部模式由 Codex 主导推理；不重新打开设计确认。

## 验收规格

Studio 预先在后台运行。使用 `mcp==2.3.0`，把 Streamable HTTP `/mcp` 挂入现有 Studio 的同进程、同端口本机入口，仅监听 `127.0.0.1`。默认关闭；连接面板提供开启、配置片段、Token 复制、服务状态和最近客户端调用。Bearer Token 不得进入工具结果、日志或资源。更新旧的禁止外部 MCP 约定；库内工人仍直接调用。

后台持久化项目、计划版本、执行会话和任务引用。修改计划使用 `project_id` 与预期 `plan_version`；冲突返回最新快照。旧浏览器交接首次兼容导入；草稿和偏好仍留浏览器。运行中的任务绑定原计划快照与版本。

工具 schema、权限、处理器由 `ToolRegistry` 统一声明。外部模式无需应用模型密钥，使用结构化策划和确定性执行器。编排器只依据真实工具结果、产物验证和退出检查推进，保留依赖与返工规则。长任务返回 `job_id`，支持状态、日志摘要、取消；资源读取限制在所属项目。

MCP elicitation 在 Codex 对话中确认项目、计划版本、工具范围、素材路径和预算。单次授权默认总预算 **1800 秒（30 分钟）**；清单中的生产动作各执行一次，节点返工最多 **3 次**。反馈进化最多 **3 个候选**，默认 **600 秒**，同时受总预算剩余时间约束。生产授权由服务端持久化和验证，不接受模型伪造 `confirmed=true`。计划或范围改变重新授权。资产批准和最终采纳分别由用户决定，绑定内容或候选版本。客户端不支持或禁止 elicitation 时返回明确待授权状态及 Codex 配置说明。重连、重启、轮询不重放生产，不从状态推断批准。

首轮只接通已有能力；Git 发布、游戏打包、Unreal 节点续跑明确未支持。不自动启动 Studio，不自动修改 Codex 全局安全策略。

## 全局约束

- 生产角色为 `fantasy_agent/` 库内工人；只有 Studio 对外，同进程、本机端口。
- 决策文件原子写入；路径段校验；缺失与损坏区分；损坏不得被后续保存静默覆盖。
- 复用现有 `studio_jobs.InMemoryJobRegistry` 与执行/资产/进化单 worker 池、独立试玩池；不另建竞争执行系统。
- 外部接口不暴露调用方控制的执行程序、任意根目录、确认标志、原始计划注入、任意文件读取或任意命令。
- 简体中文面向人；标识、路径、工具名和 metric key 保持英文。所有外部结果含中文摘要、状态、资源引用、阻塞原因及下一步。
- UI 沿用 `docs/ui/architecture.md`、`tokens.md`、`css-conventions.md`；保持单一 locale/theme owner 和已访问面板不卸载。
- 后端用 `python scripts/run_tests.py`；前端 typecheck、test、build。Windows 使用大写盘符 cwd；不改 Vitest pool。
- 新 REST 路由进入端点覆盖检查；规划工具覆盖保持；新守卫加入现有变异脚本。
- 实际本地工具操作提前声明；此次用户已授权隔离目录 Godot 生成、试玩、返工、采纳。真实客户端与模拟客户端验收分开记录。
- 按功能切分提交，最终四轴复核后推送功能分支；不合并主线。

## Task 1: 持久项目与限时授权核心

**文件**：新增 `fantasy_agent/studio_projects.py`、`fantasy_agent/workflow_authorization.py` 及对应测试。先写行为测试，确认缺失行为红，再实现。

实现 `StudioProjectStore(workspace_root)`：`generated/studio/projects/<project_id>/` 下的项目记录与不可变计划版本（使用 `DirectorBuildPlan` 校验）。提供创建、列表、快照、CAS 更新、一次性旧交接导入、工作流任务引用和资源目录登记。返回快照含 `project_id`、`plan_version`、`plan`、任务和会话信息。同一根目录的锁保护 CAS 和并发任务记录；读取返回独立副本。无计划项目版本从 0 起，第一次保存为 1。`ProjectVersionConflict` 携带最新快照。历史版本仍可读取，任务永远引用提交时版本。

实现服务端限时授权存储，绑定 `project_id`、确切 `plan_version`、生产动作（工具名及规范化参数）、允许素材路径、签发时间、截止时间、使用记录。默认 1800 秒，用户可收窄；不得扩张到无限预算。一次授权的正常动作各一次，明确节点返工最多三次。`issue` 仅为可信服务端使用，不提供接受布尔确认的外部写端点。授权 claim 与 durable job 引用必须在同一锁/原子记录中先落盘再允许启动；相同请求/相同动作返回原任务，复用请求 id 但改变内容则拒绝。明确记录执行过、取消或进程中断；不在加载时执行。版本变化、路径或工具范围扩大、过期、超预算一律拒绝。可注入时钟验证预算；不把授权 id 当作跳过校验的能力。

持久文件使用 `write_atomic`，id 使用 `assert_safe_path_segment`；缺失空集/不存在，损坏响亮失败。无需备份或 schema 迁移。报错及公开快照不含连接 Token。

**验证**：真实文件回读/CAS 并发、旧交接重复导入、历史版本任务、损坏拒绝、无授权/伪造参数、stale grant、范围、截止、动作/返工次数、重复请求、防止重启重放。用项目测试脚本和 ruff。报告公开接口供下一任务使用。

## Task 2: 外部工作流、任务证据与编排接线

**文件**：新增 `fantasy_agent/studio_workflow.py`；修改 `tool_registry.py`、`studio_jobs.py`、`orchestrator.py`，对应测试。读 Task 1 报告接口后实施；本任务不修改 Studio HTTP 主文件或前端。

建立可由 Studio 注入现有 job registries 的工作流服务。所有工具 schema、permission、handler 通过 `ToolRegistry` 声明；会话元数据写入与生产写入/执行区分。公开项目创建/list/snapshot/save、授权请求意图、工具执行、任务 get/cancel、资源列举、审阅意图、返工与进化等已实现能力。元数据操作不需要生产批准。外部规划显式 `use_llm=False`，不调内部 `run_agent`；提供 `default_registry` 的确定性覆盖且不改变旧调用默认。引擎桥接 schema 从桥接器导出，隐藏并注入计划/spec、可执行路径，生产工具的调用方不能传确认字段或任意工作区。

工作流长任务复用已有 registries；先登记授权使用与任务，再提交，立即返回 id。任务包含项目版本和输入快照，worker 起跑再验证预算，deadline 以现有取消链停止进程（排队时间也计入）。持久化完成结果；重启后在飞任务诚实显示 interrupted，不重新提交。相同生产请求返回原 job。取消使用已有 cancel_scope；状态返回简明进度、有限日志摘要、资源引用。资源以不可伪造的服务端登记引用读取，逐次校验项目归属与路径 containment，拒绝 symlink 越界、连接设置及密钥文件。

接通点子、所有已实现规划、编排、资产制作/录入、引擎生成/验证、Creative Review、QA/试玩、纠偏/返工、进化建议/实验/采纳。不要用模型声明的 done 推进编排：新增内部的 external result 入口，校验 stage 依赖、tool whitelist、真实结果、产物和出口检查；人类 gate 只由另行确认的决定解锁。反复查询不产生确认。资产审阅和候选采纳绑定记录的内容/版本，并提供可信服务端决定应用接口，等待 Task 3 的 elicitation 调用。Unreal 只暴露当前已实现能力，续跑清晰拒绝；发布/打包不冒充可用。

进化上限 3 候选、默认 600 秒，实际预算 `min(请求预算, 剩余总预算)`；不足控制器最小预算时阻断，实验结果不自动采纳。用户审阅决定改变计划通过 CAS，新生产需新授权。

**验证**：空模型 key 的全套确定性规划、真实服务分派（只对昂贵进程边界用替身）、无授权/参数伪造、重复启动、排队过期、取消、重启引用、资源跨项目/越界、真实证据与依赖、人类 gate、候选/预算上限。记录工具和返回 schema。

## Task 3: MCP 传输、elicitation 与 Studio 接口

**文件**：新增 `apps/studio/app/mcp_server.py`（必要时拆连接配置模块）、测试；修改 `main.py`、`pyproject.toml`、`AGENTS.md`、端点覆盖检查登记。只采用 `mcp==2.3.0` 官方 SDK，先安装/检查真实 v2 API，不假定 v1 FastMCP。

在 Studio lifespan 管理 Streamable HTTP session manager，`/mcp` 无第二服务端口。HTTP transport 验证 loopback peer/Host/Origin，防 DNS rebinding；任何端口入口不允许远程 peer 使用。Bearer Token 默认生成并原子保存，常量时间校验；默认 disabled。提供同源本机 REST 连接管理端点：状态、开启/关闭、显式 Token 读取/轮换、Codex TOML 配置（使用 env Token 引用而非把密钥塞配置文本）。最近访问只记有限中文操作摘要、工具、时间、结果；不存参数和认证 header。关闭立即拒绝后续请求。

工具列表完全从工作流 Registry 投影；server instructions 首 512 字自包含。所有 call/result/resource 都经过统一的安全/中文结果层，包含 summary/status/resources/blockers/next_actions。MCP resources 提供项目快照、计划、任务、审阅产物；按服务端引用及项目校验，不开放 raw path。后台项目 REST 创建/list/get/update/import 与只读工作流快照/任务用于 UI，route 在 main.py 显式声明以符合端点扫描器。

授权/资产审阅/候选采纳使用 `ServerSession.elicit_form` 等 v2 原生支持：展示服务端生成项目、版本、动作、路径、预算或产物内容标识，`accept` 且有效用户选项才 issue/decide。客户端不支持、decline/cancel、超时、`approval_policy.granular.mcp_elicitations` 禁止时返回等待状态和设置说明；不回退到自动批准。工具参数中的 confirmed/plan/path 注入不得提供另一入口。elicitation 与执行之间重新检查当前版本/内容。

更新禁止外部接入约定，允许 Studio 本机入口；其它库内角色保持直接调用。新传输挂载不能破坏既有 REST 与桌面启动，读取服务实际端口生成配置。

**验证**：SDK 客户端初始化、tools/list/call、resources/list/read、elicitation accept/decline/unsupported；disabled/no bearer/bad bearer/nonloopback/host/origin 拒绝；Token 不出现在结果/资源/日志；MCP 和 UI 用同一个项目与池。现有 Studio endpoint 覆盖和测试通过。

## Task 4: 后台计划成为面板共同权威

**文件**：`apps/frontend/src/shared/` 项目 client/store/types、shell/workbench/console/orchestration 相应 hooks 及测试，i18n；必要的 backend UI 适配。先读当前 UI 三份基线。

建立一个跨面板共享项目 store（可用 `useSyncExternalStore`，无需新 locale/theme provider）。保存 active project 引用于浏览器，后台 owns plan；首次启动把有效 legacy handoff 一次性导入，失败明确可重试且不得吞草稿。项目列表/选择/create/save 使用 backend，CAS 失败显示最新版本并保留未提交草稿；旧局部草稿不得无声覆盖 MCP 修改。面板切换/轮询读取后台更新，仍保持已挂载视图。在飞 UI 操作和后台 job 绑定提交时项目及版本，不将旧版本结果贴到当前计划。

工作台保存、console planning handoff、shell title/engine、编排 board 统一读当前后台快照。浏览器保留点子对话/未提交计划草稿、locale/theme/sidebar 偏好。工作台仍只策划，不启动生产。当前内部执行 UI 的显式确认继续来自用户动作。绑定项目元数据的既有 REST 更新/查询与外部工作流在 UI 中可见；不要只改顶部标题而留另一套计划来源。

**验证**：legacy 一次导入、无后端不伪装空项目、MCP 更新跨面板同步、版本冲突保留草稿、运行中计划变化、切换不卸载、重启项目恢复。frontend typecheck/test/build，endpoint/workbench/product guards，新增 mutation cases。

## Task 5: 中文连接页与工作流结果显示

**文件**：`studio/settings/` 连接 UI、console/board 任务展示、对应 i18n/CSS/测试；不重做现有主题。

连接页清楚区分「服务是否开启」「最近 Agent 访问」「当前生产授权」；默认关闭，用户动作开启。提供服务 URL、Codex TOML/env 设置说明、Token 显式复制/轮换、简短连接步骤，技术片段按需展开。Token 不进入 localStorage、持久日志或普通状态 DOM，复制操作明确。说明 elicitation 被客户端禁用时的配置，不自动改 Codex 全局策略。

展示后台项目/版本、在飞工作流进度、日志摘要、取消、待授权/待审阅/待采纳与可执行下一步；资源给安全读入口。Codex 操作后既有策划、编排、执行、审阅和 QA 面板显示相同结果。中文模式减少冗余英文，标识与路径保留；空态/报错/expired/interrupted 都有中文文案与有效下一步，i18n 字典同步。保留低密度、token 阶梯、统一状态语义和可访问性。

**验证**：前端 UI 行为、字典和 CSS 守卫、mutation、宽/窄屏明/暗浏览器显示，无前端硬编码确认。录入既有样式 class pairs，UI Metrics 通过。

## Task 6: 全链验收、四轴复核与交付

**文件**：持久使用文档、协议 smoke/隔离 Godot 验收脚本、现有 mutation scripts cases、四轴 review 记录。

补齐未完成的 contract/guard 变异验证，独立验收版本冲突、预算耗尽、伪造确认、重复生产、取消、重连/重启/面板切换。执行 SDK MCP smoke，尽可能使用实际 Codex 客户端连接并观察授权/审阅显示；不得把模拟表述成真实 Codex 对话。真实客户端若无法在当前运行任务热接入，记录证据和可复现启动步骤，不自动改全局安全策略。

提前声明本地操作后，在隔离项目完成经授权 Godot 生成、headless 试玩、节点返工和候选采纳，记录实际文件/报告。Unreal 限已实现能力，不为未支持事项伪造成功。

后端 `python scripts/run_tests.py`、ruff，前端 typecheck/test/build，UI Metrics，新增前后端 mutations 全通过。四轴（功能正确性、授权与安全、可靠性、维护性/界面契约）独立复核，修复证据充分的问题。按功能提交并 push `codex/studio-mcp-workflow`，不自动合并。最终中文报告能力、验证结果、实际客户端验收状态和剩余真实限制。
