# 灵构工坊可分享能力包与自进化实施计划

日期：2026-11-02。状态：待实施；当前已完成代码与第三方发布包研究、产品范围收敛及基础测试。

**目标：** 在现有 Studio 内实现可编辑、可分叉、可分享的策划能力包，自动提出和评测候选版本，由用户启用经过本机验证的改进。

**架构：** 原生版本库、运行证据与评测控制器承载产品行为，`gepa==0.1.4` 作为可选优化内核。生产仍走现有 `run_agent`、`Orchestrator` 和 `ToolRegistry`。

**技术栈：** Python/Pydantic/FastAPI、GEPA 核心、Vite/React/TypeScript、原子 JSON 存储。

**设计依据：** [可分享能力包与自进化设计](../specs/2026-11-02-shareable-evolution-design.md)。实施时先读该文件和项目 `AGENTS.md`；以下任务按顺序进行，每个任务都应有独立的行为验证。

## 1. 全局约束与交付顺序

- 支持真实接入点 `planning_loop`、`gameplay_orchestration`；不将参与角色标记当作独立调用的 Agent。
- 只优化策略指令；权限、工具实现、阶段依赖、人工闸门、固定评测和晋升门槛保持代码所有权。
- Studio 是唯一入口，只监听 `127.0.0.1`。实验不启动引擎、不提供代码执行或新增 MCP 服务。
- 先完成运行与评测闭环，再做分享和界面扩展；打包检查排在功能 QA 之后。
- 保存决策输入走 `write_atomic`；索引读改写加工作区锁；用户显示名称不用于路径。
- UI 使用简体中文和现有视觉系统；字典双语同步，确认来自用户动作。
- 不依赖系统 PATH 中的 `python`；本机测试用 `.venv/Scripts/python.exe scripts/run_tests.py`，基于 OS 临时目录。

交付分为三个可核验阶段：

1. **能运行的版本化策略：** 任务 1–3；策略真实生效、证据可回读、旧会话可恢复。
2. **有证据的进化：** 任务 4–5；固定对照评测、预算、取消、人工晋升。
3. **能分享和复用：** 任务 6–8；安全文件协议、编辑器、空工作区复核与桌面依赖检查。

## 2. 模块与接口

在 `fantasy_agent/evolution/` 内集中实现，按责任拆分，避免把整个子系统塞进 `main.py`：

| 模块 | 单一责任 |
|---|---|
| `contracts.py` | 设计中的严格模型与协议常量 |
| `profiles.py` | 指令编译、工具引用检查、实际版本选择 |
| `library.py` | 不可变版本、谱系、索引、活动版本与工作区锁 |
| `evidence.py` | 运行观察、结构化证据、用户反馈和经验检索 |
| `evaluation.py` | 固定案例检查、比较报告与晋升资格 |
| `optimizer.py` | GEPA adapter、反思模型、预算、取消与后台结果 |
| `sharing.py` | 分享字段白名单、摘要、导入预览与文件输出 |

供 Studio 调用的接口固定如下；类型在本子系统模型中定义，库函数不返回 HTTP 响应：

```python
compile_profile(recipe: EvolutionRecipe, registry: ToolRegistry) -> CompiledEvolutionProfile
save_version(version: EvolutionVersion, *, workspace_root: Path) -> EvolutionVersion
resolve_profile(version_id: str, *, workspace_root: Path) -> ResolvedEvolutionProfile
record_evidence(evidence: RunEvidence, *, workspace_root: Path) -> str
evaluate_candidate(version: EvolutionVersion, cases: list[EvolutionCase], context: EvaluationContext) -> EvolutionEvaluationReport
run_evolution(request: EvolutionExperimentRequest, *, workspace_root: Path) -> EvolutionExperimentResult
preview_package(package: EvolutionPackage, *, workspace_root: Path) -> EvolutionPackagePreview
import_package(package: EvolutionPackage, *, workspace_root: Path) -> EvolutionVersion
export_package(version_id: str, case_ids: list[str], *, workspace_root: Path) -> bytes
activate_version(version_id: str, *, workspace_root: Path) -> EvolutionActivationResult
```

`CompiledEvolutionProfile` 提供 `instructions_for(target, baseline)`，`ResolvedEvolutionProfile` 同时返回有效版本与提示原因。`EvaluationContext` 包含冻结的运行环境、统一预算和证据观察器；HTTP 层不得自行创建第二套评分或启用规则。

## 3. 实施任务

### 任务 1：能力包契约与真实指令接入

**文件：** 新建子系统 `contracts.py`、`profiles.py` 和 `tests/test_evolution_profiles.py`；修改 `agent_loop.py`、`orchestrator.py`。

**消费：** 现有工具注册表、`SYSTEM_PROMPT`、`STAGE_INSTRUCTIONS` 与阶段 owner。

**交付：** 严格配方模型、`compile_profile`，两个真实接入点可消费版本化指令。

- [ ] 定义两个 component key、4,000 字符上限及只读规划工具偏好；元数据和内部交接字段按设计赋予默认值。
- [ ] 基础指令与技能摘要由现有代码提供，profile 只附加策略片段；工具偏好作为提示，不改权限或阶段白名单。
- [ ] 对每个接入点增加行为测试：记录传给模型的实际指令，再让假模型依据片段选择不同的工具调用，证明接线改变了实际行为。
- [ ] 测试不存在的 component、工具名、超长指令及未知字段被拒；诱导执行的指令无法令受限 handler 被调用。
- [ ] 未指定 profile 的 `run_agent` 和阶段指令保持原样。

**守卫示例：** 在 `tests/test_evolution_profiles.py` 构造一个带执行诱导的配方，用有调用计数器的 EXECUTE handler 和两轮假模型运行；断言 handler 计数为 0，并且返回记录包含拒绝结果。不要只检查提示中含“禁止执行”。

**验证：** `scripts/run_tests.py tests/test_evolution_profiles.py tests/test_agent_loop.py tests/test_agent_skills.py tests/test_orchestrator.py`。

### 任务 2：版本库与会话固定

**文件：** 新建 `library.py`、`tests/test_evolution_library.py`；修改 `orchestration_state.py` 和 Studio 的恢复路径。

**消费：** 任务 1 的 profile 与严格版本模型。

**交付：** 不可变版本、来源谱系、活动选择、版本快照与旧格式兼容。

- [ ] 在 `generated/evolution/` 用后端 id／摘要命名文件，创建版本与索引的原子写入接口。
- [ ] 索引所有读改写共用工作区锁。保存失败须报告，不能提前写入指向缺失版本的索引。
- [ ] 相同内容复用；同一身份和版本号的不同内容报冲突；fork 创建新身份与来源引用。
- [ ] 给 `OrchestrationState` 增加带默认值的版本 id、摘要和 profile 快照；不往 `StageOutcome` 加摘要字段来绕开镜像契约。
- [ ] 新会话固定有效策略，旧会话请求另一策略报 409；恢复兑现已有批准，且只消费该会话策略快照。
- [ ] 索引缺失与损坏分开；切换默认策略不改变已运行会话。版本文件移除后，已有合法快照仍可显示与恢复。

**必须验证：** 重启前的 profile A，在默认版本改成 B 后仍被旧会话实际使用；不只比较状态文字。缺少 profile 字段的旧快照用内置策略恢复。

**验证：** `scripts/run_tests.py tests/test_evolution_library.py tests/test_orchestration_state.py tests/test_orchestrator.py tests/test_atomic_write.py tests/test_path_safety.py`。

### 任务 3：运行证据、完整规划结果与经验

**文件：** 新建 `evidence.py`、`tests/test_evolution_evidence.py`；扩展 `agent_loop.py`、`llm.py`、规划结果投影和前后端共享类型。

**消费：** 任务 1–2 的有效版本标识与当前调用数据。

**交付：** 可回读的真实运行证据、跨会话反馈，以及可回到工作台的完整计划。

- [ ] 给 Agent 增加可选观察器，覆盖回合、实际工具结果、类型化规划产物和结束状态；现有短摘要作为显示层保留。
- [ ] `AgentRunResult` 增加可选 `planning_result`、`evidence_id` 和有效版本元数据；完整计划只从本轮成功生成的 `DirectorBuildPlan` 提取。
- [ ] 模型请求观察仅记录 provider/model、计数、时间和可获得的 usage，不记录 headers、key 或 endpoint。内层生成回退作为明确事件保存。
- [ ] 用户开启经验记录后保存证据，用户反馈单独记录；按 component／轴／失败代码检索最多 5 条。
- [ ] 记录故障明确返回状态，并保留原任务的结果；不把“记录失败”静默当成已保存经验。
- [ ] 给证据增加固定输入指纹与运行 id，保证一个旧计划或失败前残留不能成为另一次任务的输出。

**必须验证：** 本轮未产出计划时 `planning_result` 为空；另一轮 registry 中已有完整计划仍不能满足本轮。超过显示摘要长度的关键失败和产物字段仍能进入机器证据。

**验证：** `scripts/run_tests.py tests/test_evolution_evidence.py tests/test_agent_loop.py tests/test_llm_tool_calling.py tests/test_planning_actions.py`。

### 任务 4：固定评测与晋升资格

**文件：** 新建 `evaluation.py`、`tests/test_evolution_evaluation.py`、`examples/evolution/cases.yaml`。

**消费：** 真实 profile、独立 registry、完整运行证据、既有 `plan_checks` 与 spec 校验。

**交付：** `evaluate_candidate`、逐例对照报告、机器晋升资格。

- [ ] 在开发、验证和独立验收三个集合各放入八轴案例；验收另加设计指定的四类边界。用不同提示，避免同一个案例跨集合复用。
- [ ] 定义 `planning`、`orchestration_stage`、`expected_refusal` 三种任务检查；期望产物和固定检查来自案例，不来自候选指令。
- [ ] 每个 rollout 新建 registry；阶段内通过现有 scoped store 共享产物。单纯 `status=done` 或模型自述完成不算成功。
- [ ] 按设计公式返回搜索分数，同时保留成功率、请求数、工具数和违规结果，不将一个分数作为全部证据。
- [ ] 最终基线／候选按案例交替运行各 3 次；验收完整、逐例无退步且满足成功率或 10% 请求改善规则，才能返回 `eligible`。
- [ ] 环境指纹不一致、缺失产物、模型故障、部分结果和无改进分别给出原因；验收输入与逐例轨迹不进入反思资料。

**必须验证：** 模型说“检查通过”但 registry 没有产物时为失败；总分提高但某个轴退步不能晋升；同成功率且少 9% 请求不能满足 10% 门槛；缺一例或跳过测试不得晋升。

**验证：** `scripts/run_tests.py tests/test_evolution_evaluation.py tests/test_exit_checks_wired.py tests/test_generation_axis.py tests/test_preflight.py tests/test_production_spec_runtime.py`。

### 任务 5：GEPA、实验预算与后台任务

**文件：** 新建 `optimizer.py`、`tests/test_evolution_optimizer.py`；扩展 `llm.py`，接入现有 `studio_jobs`；在 `pyproject.toml` 加可选依赖。

**消费：** 任务 3–4 的证据、案例、评分与冻结环境。

**交付：** 自动候选生成和评测、有预算且可取消的后台实验。

- [ ] 添加 `[project.optional-dependencies].evolution = ["gepa==0.1.4"]`，使用自定义 `GEPAAdapter.evaluate` 与 `make_reflective_dataset`。
- [ ] 反思 callable 经现有 `complete_with_tools(tools=[])` 发起；适配三种既有 provider，不经 GEPA 内建 LiteLLM 或 MCP adapter。
- [ ] 固定 `run_dir=None`、`skip_perfect_score=False`、关闭 merge 和外部追踪；候选及父子关系映射成原生版本，不加载 pickle。
- [ ] 默认上限为 3 个新候选、64 次搜索案例评测、500 次累计模型请求、30 分钟；单次 Agent 8 轮及 8 个工具调用。最终验收的请求也计入总预算。
- [ ] `_post_json` 接入上下文预算：外层循环、内层生成、反思请求共用计数，调用前检查取消与剩余时间；退出时解除上下文。
- [ ] 与 `InMemoryJobRegistry` 共享取消事件；在每个 rollout 和模型调用边界检查。API timeout 按剩余预算收窄。
- [ ] 超预算、取消、provider 错误与重启中断都保存已有原生证据；不完整候选不能晋升。候选只能经人工启用变成默认。

**必须验证：** 用假的反思模型与真实 GEPA 核心完成一次小数据搜索；内层生成的请求触发总预算后不再发新请求；中途取消后不再开始下一案例；即便有最高搜索分数，未完成独立验收也不可启用。

**验证：** `scripts/run_tests.py tests/test_evolution_optimizer.py tests/test_llm_tool_calling.py tests/test_studio_jobs.py tests/test_process_runner.py tests/test_api_settings.py tests/test_dependency_guards.py`。

### 任务 6：可移植分享协议与空工作区复核

**文件：** 新建 `sharing.py`、`tests/test_evolution_sharing.py`；给 `examples/evolution/` 增加可公开分享的示例包。

**消费：** 原生版本、公开案例、固定指标摘要和库索引。

**交付：** `.fantasy-evo.json` 文件导入、导出、分叉与接收端验证。

- [ ] 最大 2 MiB；规范化 JSON 摘要；严格版本与字段检查。文件内容由用户选择上传，服务端不接受 URL 下载或任意落盘路径。
- [ ] 以输出模型白名单导出，排除凭据、endpoint、本机路径、批准、原始会话、私有经验和独立验收集；展示最终内容预览。
- [ ] 导入后状态恒为草稿；原作者报告与本机验证分开保存；导出摘要或原作者 `passed` 不能满足 `activate_version`。
- [ ] 原封不动的重复导入复用；身份冲突报 409；fork 保留来源且没有本机批准。
- [ ] 工具／环境不兼容时保留为待处理草稿；协议、内容摘要、额外字段或 component 非法直接拒绝。
- [ ] 在第二个空工作区走完整导入、评测、人工启用流程；用源工作区的审批和路径诱导接收端，必须无法继承。

**必须验证：** 包中伪造的启用标记与执行确认被拒；外部评分不能晋升；导出不含种在本机配置、日志或私有经验中的哨兵秘密；导入与预览不启动任何工具或网络请求。

**验证：** `scripts/run_tests.py tests/test_evolution_sharing.py tests/test_evolution_library.py tests/test_evolution_evaluation.py tests/test_path_safety.py`。

### 任务 7：Studio 接口、能力编辑器与生产入口

**文件：** Studio 路由仍在 `apps/studio/app/main.py`；新增 `apps/frontend/src/evolution/` 视图、模型和测试；修改 `shared/api.ts`、`shared/types.ts`、`StudioShell`、Agent 面板、编排板及工作台。

**消费：** 前六个任务的库接口。后端路由清单以设计文档的 REST 表为准。

**交付：** 能力工坊、版本选择、明确确认、实际应用与分享交互。

- [ ] `/evolution` 作为资产库同级整页入口，加入 `PANEL_ROUTES`、`visitedPanels` 与 ErrorBoundary，不改六步旅程的含义。
- [ ] 建立配方编辑器、工具偏好与流程预览、来源版本树、逐例对比报告；详细指标和原始内容按需展开。
- [ ] 实验 `confirmed=false` 只预览；按钮动作再提交确认。页面挂载、导入、恢复和选择版本都不发起实验或启用。
- [ ] Agent 与编排请求传可选版本；显示后端有效版本及待复核原因，前端不自行推断有效策略。
- [ ] 工作台新增“用能力包完善计划”，调用只读 Agent；用户选择采用完整返回计划后更新 handoff，保留旧计划供比较。
- [ ] 保存、分叉、经验反馈、实验取消、人工启用／回内置策略、包预览／下载／导入均有 UI 调用点，保持端点覆盖检查双向通过。
- [ ] 所有新文案进入中英字典；CSS 用独立 `ev-*` 前缀和现有 token，登记样式所有权及守卫覆盖。
- [ ] 切走能力工坊保留运行状态，重启读回实验为中断状态；读取失败显示错误而不是空库。

**必须验证：** 自动生成最高分版本后，默认版本仍未变化；只有点击启用才变化。导入包后始终未批准。切换面板保持实验轮询。工作台采用计划前后，执行确认仍由原有实际动作产生。

**验证：** 前端 typecheck、test、build；后端 `tests/test_frontend_endpoint_coverage.py`、`tests/test_workbench_tool_coverage.py`、`tests/test_product_name.py` 与新增 API 测试。

### 任务 8：守卫、完整 QA 与交付说明

**文件：** 将新增后端与前端守卫登记到两套既有变异检查脚本；更新架构说明、安装说明与能力包用户文档。

**消费：** 完整产品闭环。

**交付：** 可以实施验收和发布评估的功能，不以基础测试代替进化效果。

- [ ] 后端变异至少覆盖：遗漏真实指令接线、旧产物给新任务补分、内层请求不计预算、验收泄漏给反思、外部评分直接批准、自动启用、恢复时换策略、索引非原子写入。
- [ ] 前端变异覆盖：导入／挂载时自动启用、写死确认、缺失失败态、切走卸载；先跑未变异基线，并要求点名测试变红。
- [ ] 运行完整后端测试、ruff、前端三项、UI metrics 和相关变异。Windows 使用规范的大写盘符 cwd，不更改 vitest pool 掩盖跑法问题。
- [ ] 完整 QA 后检查桌面打包的 GEPA 可选依赖与模块收集；未安装扩展时展示不可用原因，已有编辑／分享和规划功能可用。
- [ ] 用户手动确认后开展一次真实模型小预算试验：记录基线、候选、逐例结果、总请求和未改善情况，不预设一定能提升。
- [ ] 在空工作区完成导入、独立验收、人工启用和回退。在线社区、代码自修改与 Godot 参数调优另立设计，不混入这轮验收。

## 4. 核验命令与当前证据

实现后的常规检查：

```powershell
.\.venv\Scripts\python.exe scripts/run_tests.py
.\.venv\Scripts\python.exe -m ruff check fantasy_agent apps/studio scripts tests
npm run frontend:typecheck
npm run frontend:test
npm run frontend:build
.\.venv\Scripts\python.exe scripts/ui_metrics.py --check
```

新增守卫登记后分别运行后端与前端变异脚本的精确 `--only` 选择，再执行 CI 所需范围；不要用一个退出码代替被点名测试的报告。

研究阶段已经通过的基础检查：

```powershell
.\.venv\Scripts\python.exe scripts/run_tests.py tests/test_agent_loop.py tests/test_agent_skills.py tests/test_exit_checks_wired.py tests/test_playtest.py tests/test_playtest_bot.py tests/test_corrections.py
```

结果：**134 passed / 0 failed / 0 errors / 0 skipped**。此前的系统 Python 指向无 pytest 的 GraalPy；虚拟环境首次受沙箱临时目录权限限制。允许测试访问规定的 OS 临时根后同一测试命令全部通过，没有修改 runner、测试或临时目录位置。

新能力的测试、GEPA 在项目中的真实调用、真实模型收益和引擎效果均未在本轮验证。

## 5. 验收定义与默认选择

最终验收要求用户能够：编辑策略 → 运行有限实验 → 查到候选的真实差异与逐例证据 → 人工启用 → 在新任务观察到相同版本实际生效 → 导出文件 → 在空工作区导入 → 本机复核后由另一位用户启用。

以下约定固定为首版默认：

- 框架采用 GEPA 核心作为库内优化器，安装为可选扩展；平台能力不依赖它才能打开。
- 只进化两个已经实际调用的策划接入点，使用表单与流程预览的能力编辑器。
- 分享走本机文件，导入永远是草稿；启用、默认选择和执行批准留在接收端。
- 不完整、环境变更或未改善结果不能宣称进化成功；真实玩法是否有趣仍由人工试玩判断。
- 当前工作区已有玩法、bot 与几何相关未提交改动，实施时以最终确认的基线建立指纹，保留这些改动，不把本计划当作覆盖它们的授权。
