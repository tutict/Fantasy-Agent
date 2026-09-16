# 内部 pi 的任务编排方案（实施计划）

> **给编码 Agent：** 本文件是分阶段提示文档。按 Task 顺序做，每个 Task 的 checkbox 逐条勾。**每个 Task 都要先写失败测试再实现**，且做完一个 Task 就跑一次全量测试与 `ruff`。

**目标：** 让内置 agent loop（下称「内部 pi」）按 `ProductionPipeline` 这张编排表推进，而不是从 20 个工具的扁平列表里自选 8 轮。编排器**不替模型决策，只收窄它的可选空间**。

**架构：** 新增 `fantasy_agent.orchestrator` 作为编排层。它按 `order` 推进阶段、用 `depends_on` 门控、为每个阶段派生一个只含该阶段工具的白名单 registry，再交给现有的有界 `run_agent`。阶段产出复用 `pipeline_state.record_stage` 落盘，失败经已有的 `rework_target` 回退。确定性流水线仍是兜底，`agent_loop` 的三条边界一行不改。

**技术栈：** Python 3.11+、Pydantic、pytest、FastAPI、React/TypeScript（仅 `types.ts` 需要同步新字段）。

---

## 诊断（实测）

`run_director_workflow(PromptRequest(engine_version="Godot 4"))` 产出 7 阶段，依赖图无环：

**勘误（Task 1 实测）：本文件初版写的「`mcp_tools` 悬空 0 个」是错的。** 那个结论来自只探 Godot 路线的复现片段。Unreal 路线另有 2 个悬空名：`unreal_production` 和 `optimization_testing` 的 `mcp_tools` 里都写着 `DataValidation`——那是 `run_editor_commandlet` 要跑的 **commandlet 名**，读起来像工具、解析结果为 0。Task 1 已改成 `run_editor_commandlet`，守卫从此同时跑两条路线（`tests/test_pipeline_contract.py` 的 `ROUTES`）。这条勘误本身就是"只测一条路线"的代价。

| order | stage | depends_on | status | confirm | mcp_tools |
|---|---|---|---|---|---|
| 1 | gameplay_orchestration | — | ready | false | extract_idea_seed / generate_game_production_plan / decompose_production_tasks / render_gdd |
| 2 | comfyui_visual_production | 1 | pending | true | probe_comfyui_capabilities / prepare_visual_reference_workflows / run_visual_reference_workflow |
| 3 | blender_modeling | 1 | pending | true | generate_blender_script |
| 4 | creative_review | 2,3 | blocked | true | 空 —— 但不是漏填，是 `kind="human"` 的人工闸门 |
| 5 | asset_integration | 4 | blocked | true | create_godot_project_structure / validate_godot_project |
| 6 | godot_quick_play | 5 | blocked | true | 上两者 + run_godot_import |
| 7 | optimization_testing | 6 | blocked | true | validate_godot_project |

**缺口：Python 侧一个读者都没有。** `stage.mcp_tools` 只在 `workflows.py` 里被**赋值**（2 处 `stage.mcp_tools = [...]` + 若干构造 kwarg），没有任何代码读它；`apps/studio/app/main.py:617` 读的只是 `stage.title`，用来拼一行展示摘要。`status` / `depends_on` / `requires_confirmation` / `quality_gates` / `owner_agent` **零运行时消费**；`agent_loop.py` 里 `production_pipeline` 出现 0 次。唯一读这些字段的运行时是前端（`console/rendering.tsx:172-182`、`workbench/PlanPanels.tsx:129-142`），而且是纯展示。所以「编排」目前是一份给 UI 看的文档。

**复现上表**（`.venv/Scripts/python.exe`，不要用系统 python）：

```python
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.tool_registry import combined_registry
from fantasy_agent.workflows import run_director_workflow

plan = run_director_workflow(PromptRequest(prompt="...", engine_version="Godot 4"))
registered = set(combined_registry().names())
for stage in plan.production_pipeline.stages:
    print(stage.order, stage.id, stage.status, stage.mcp_tools,
          [t for t in stage.mcp_tools if t not in registered])
```

## 四个开放问题的定调

| # | 问题 | 定调 | 依据 |
|---|---|---|---|
| 1 | 空 `mcp_tools` 是什么意思 | **两种含义拆开，空列表不再合法。** stage 1 是**漏填**（它的 outputs 正是 4 个规划工具的产物），填上；stage 4 是**人工闸门**（side_effect 写着 `asks the user for asset approval decisions`，注册表里没有对应工具），用新字段 `kind="human"` 显式表达 | 读源码：stage 1 的 `_pipeline_stage(...)` 调用里**根本没传** `mcp_tools`；`prepare_creative_review` 不在 `default_registry()` 的 4 个工具里，也不在 `engine_registry()` 的 16 个里 |
| 2 | `quality_gates` 是否机器可校验 | **保持人读，不参与编排。** 新增可选 `exit_checks`，值只能是**注册表里已有的只读工具名** | 实测导出全部 **21 条**（7 阶段 × 3），逐条看过，没有一条是可机器校验的形式——最常见的是「Average session remains within 10 minutes.」「Assets use UE centimeter scale.」这类判断句；发明一门检查 DSL 是另一个量级，复用注册表零新语言 |
| 3 | `owner_agent` 与 `skills/` 对不上怎么办 | **加显式映射表 + 守卫测试，不改目录名、不改契约枚举** | `owner_agent` 是 `contracts.py` 的 Literal，进 JSON、被前端渲染，改名是破坏性变更；7 个 `SKILL.md` **没有 frontmatter**（只有 H1），改名无代码影响；两边是不同抽象层——角色 vs 能力包。项目已有同类先例：`KNOWN_WITHOUT_UI`、`unimplemented_contracts()`、`_HIDDEN_ARG_WITHOUT_SOURCE` |
| 4 | 两套阶段词汇表怎么处理 | **加第二个翻译层，不合并。** 一个编排阶段映射到零到多个执行阶段 | 执行层 `GODOT_STAGE_ORDER` 有 12 个**进程步骤**（含 `preflight` / `approval_gate` / `copy_refs`），编排层 7 个是**生产语义**；`gameplay_orchestration` 与 `creative_review` 在生产语义上成立但在进程步骤里没有对应物。合并会把实现细节泄漏进生产语义。先例是 `REWORK_TARGET_STAGES`（AGENTS.md 明写「唯一翻译层」） |

`owner_agent` → `skills/` 的完整映射（本方案的结论，Task 6 用）：

| ProductionTaskAgent | skills/ | 备注 |
|---|---|---|
| director-agent | — | 编排角色，能力分散在下面三个 skill 里 |
| gameplay-agent | gameplay-designer | 名不同 |
| gdd-writer | gdd-writer | 一致 |
| level-director | level-director | 一致 |
| blender-worker | blender-generator | 名不同 |
| comfyui-worker | comfyui-generator | 名不同 |
| creative-review-agent | creative-reviewer | 名不同 |
| unreal-builder | ue-architect | 名不同 |
| godot-builder | — | 无 |
| qa-agent | — | 无 |

7↔7 正好对上，3 个角色无 skill。这正是映射表比改名好的证据：改名解决不了 `director-agent` / `godot-builder` / `qa-agent` 没有对应物这件事。

---

### Task 1: 让编排表自己诚实 ✅ 已完成

**Files:**
- Modify: `fantasy_agent/contracts.py`（加 `ProductionStageKind` + `kind` 字段）
- Modify: `fantasy_agent/workflows.py`（填 stage 1 的 `mcp_tools`、设 stage 4 的 `kind`、修 2 个悬空工具名）
- Create: `tests/test_pipeline_contract.py`（8 条守卫）
- Modify: `apps/frontend/src/shared/types.ts`（`PipelineStage` 加 `kind?: string`）
- Modify: `AGENTS.md`（四条不变量写进 Director Agent 一节）
- Modify: `scripts/mutation_check_all_guards.py`（T1–T8，55 → 63 例）

- [x] 先写失败测试：`kind="agent"` 的 stage 必须有非空 `mcp_tools`；`kind="human"` 的必须为空。两条都覆盖 Godot 与 Unreal 两条路线。
- [x] 加 `ProductionStageKind = Literal["agent", "human"]`，`ProductionPipelineStage.kind` 默认 `"agent"`（旧构造点与旧 JSON 都不受影响；`test_a_stage_written_before_the_kind_field_still_loads_as_an_agent_stage` 把"去掉这个键仍按 agent 加载"钉住）。
- [x] `gameplay_orchestration.mcp_tools = ["extract_idea_seed", "generate_game_production_plan", "decompose_production_tasks", "render_gdd"]`——它现在的 outputs 就是这 4 个工具的产物。
- [x] `creative_review.kind = "human"`——它的 side_effect 是「问用户要审批决定」，不是执行工具。守卫顺带断言这一点，`kind` 是对表的读数而不是新主张。
- [x] 测试：每个 `mcp_tools` 里的名字都能在 `combined_registry()` 里解析。
- [x] 测试：`depends_on` 引用的 stage id 都存在，且 order 严格小于自身（无环、无前向引用）。
- [x] 测试：`order` 恰好是 `1..N` 且唯一。
- [x] 测试：`current_stage` / `next_stage` 指向本路线真实存在的 stage；契约声明过的 stage id 至少被一条路线构建出来。
- [x] `types.ts` 补 `kind?: string`。

**计划外发现三处，都改了：**

1. **`DataValidation` 不是工具名，是 commandlet 名。** `unreal_production` 与 `optimization_testing` 的 `mcp_tools` 里都写着它——工具是 `run_editor_commandlet`。这个错只在 Unreal 路线上出现，所以"只探 Godot 路线"的旧诊断看不见它。两处改成 `run_editor_commandlet`。
2. **`kind` 的契约默认值不被管线触达。** `_pipeline_stage()` 显式传 `kind=kind`，所以把默认值从 `"agent"` 改成 `"human"` 不会让任何**管线**断言变红——变异 T4 实测 GREEN（漏检）。守这个默认值的只能是那条"旧 JSON 去掉 `kind` → 仍按 agent 加载"的测试，T4 因此改钉在它上面（改钉后 RED）。教训：**测"默认值"必须走缺字段的输入，不能走会显式传值的构造点。**
3. **变异 harness 被打断会留下残留。** 第一次用 `--only T` 跑新 case（子串太短，实际命中全部 63 条）在超时点被 SIGTERM 杀掉，`finally` 没执行，`fantasy_agent/godot_mcp.py` 的 `spacing = 5.0` 以 `6.0` 留在盘上；下一次全量运行报的是 `D7 ... needle appears 0x`——一个与故障无关的文件，很容易被误读成"针点过期"而去改针点。harness 的 `SKIP` 分支、`test_every_needle_still_matches_exactly_once` 与 AGENTS.md 现在都会先说"这可能是残留，先 `git diff`"。（被改坏的那个文件已按字节还原，`git diff` 为空。）

**没做的一件事：** `kind` 没接进 UI，`i18n.ts` 未改。`rendering.tsx` / `PlanPanels.tsx` 目前仍只按 `requires_confirmation` 显示 pill；把"人工闸门"显式化属于 Task 5（阶段级确认）的界面工作。副作用一条：stage 1 现在有了工具清单，前端会开始给第 1 阶段多显示一行「工具」，这是本 Task 唯一的可见变化。

### Task 2: 编排器骨架（P0）

**Files:**
- Modify: `fantasy_agent/tool_registry.py`（加 `ToolRegistry.scoped`）
- Create: `fantasy_agent/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] `ToolRegistry.scoped(names, *, up_to=None) -> ToolRegistry`：派生一个只含 `names` 的 registry，并**共享同一个 `artifacts` dict**（复用 `default_registry(target=...)` 的模式，这是 plan 注入能继续生效的前提）。名字解析不到就 `ValueError`——白名单写错必须响亮失败，不能静默给出一个空工具集。
- [ ] `Orchestrator.run(plan, *, allow_write=False, allow_execute=False, max_turns=...)` 推进规则：
  - `depends_on` 未全部 `done` → 该阶段 `blocked`，**不派 agent、不消耗轮次**；
  - `kind="human"` → 置 `awaiting_human`，**不派 agent**；
  - 白名单 ∩ 授权可见集为空（例如整个阶段都是 execute 级工具但没给 `allow_execute`）→ 置 `awaiting_confirmation`，**不派 agent 去空转**；
  - 否则 → `run_agent(registry=scoped(stage.mcp_tools), permission_ceiling=...)`，其中 `permission_ceiling` 照现有规则跟随授权（无授权只见只读工具）。
  - 每阶段结束调 `pipeline_state.record_stage`。
- [ ] 测试：monkeypatch `agent_loop.complete_with_tools`（**不是** `llm.complete_with_tools`，见 09-07 记录），断言模型收到的 schema **只有该阶段的工具**，且总数小于全量 20。
- [ ] 测试：`depends_on` 未满足时，那个阶段的 handler 一次都没被调用。
- [ ] 测试：模型请求白名单外的工具 → 得到 `error`（registry 不认识这个名字），循环继续而不是崩。
- [ ] 测试：失败不传染——某阶段抛 `LLMError` 时该阶段标 `failed`，其余阶段状态不变，调用方拿到 `status="error"`。
- [ ] 测试：`kind="human"` 的阶段全程不产生任何工具调用。

### Task 3: 阶段出口校验（P1a）

**Files:**
- Modify: `fantasy_agent/contracts.py`（`exit_checks: list[str]`，默认空）
- Modify: `fantasy_agent/orchestrator.py`
- Modify: `tests/test_pipeline_contract.py`、`tests/test_orchestrator.py`

- [ ] 加 `ProductionPipelineStage.exit_checks: list[str] = Field(default_factory=list)`。空 = 不做机器校验，维持现状。
- [ ] 编排器在阶段结束后逐个调用 `exit_checks`，全部 `status == "ok"` 才把阶段标 `done`；任一非 ok → 阶段 `failed` 并把失败的工具名写进 `detail`。
- [ ] 测试：`exit_checks` 里的名字必须以 `read_only` 权限注册——**非只读工具不许进 exit_checks**，否则出口校验会变成偷偷执行引擎。
- [ ] 测试：某 check 返回 `error` 时阶段是 `failed` 而不是 `done`。

### Task 4: 返工闭环 + 阶段词汇翻译（P1b）

**Files:**
- Modify: `fantasy_agent/pipeline_state.py`（加 `ORCHESTRATION_TO_EXECUTOR_STAGES`）
- Modify: `fantasy_agent/orchestrator.py`
- Modify: `tests/test_pipeline_state.py`、`tests/test_orchestrator.py`

- [ ] 加 `ORCHESTRATION_TO_EXECUTOR_STAGES: dict[ProductionPipelineStageId, tuple[str, ...]]`，**允许空元组**（`gameplay_orchestration` 与 `creative_review` 就没有对应的执行步骤）。
- [ ] 测试：每个 `ProductionPipelineStageId` 都有条目（新增 stage id 忘了加映射必须红）。
- [ ] 测试：映射值里的名字都在 `GODOT_STAGE_ORDER ∪ UNREAL_STAGE_ORDER` 里。
- [ ] 阶段失败 → 用 `resume_stage_for(rework_target, code)` 解析出执行阶段 → 反查回编排阶段 → 从那里重跑，而不是整条重来。
- [ ] **待实测复核**：映射值先按语义填，然后用 `execute_godot_demo` 里 `record_stage` 的实际调用点核对一遍。这一步不能只靠读代码——`GODOT_STAGE_ORDER` 与 `execute_godot_demo` 漂移过一次（AGENTS.md 有记录）。

### Task 5: 阶段级确认（P2）

**Files:**
- Modify: `fantasy_agent/orchestrator.py`
- Modify: `apps/studio/app/main.py`（暴露待确认阶段）
- Modify: `tests/test_orchestrator.py`、`tests/test_studio_app.py`

- [ ] `requires_confirmation=True` 的阶段（实测 2–7 全是）进入前产出 `awaiting_confirmation` 记录，由 Studio 的用户动作推进。
- [ ] 全局 `allow_write` / `allow_execute` **不足以**让某个 stage 直接跑完——授权要能按阶段给。
- [ ] 测试：未确认阶段里的 write/execute 工具仍然 `refused`。
- [ ] 前端：待确认阶段可见、状态可点（`tests/test_frontend_endpoint_coverage.py` 覆盖新端点）。

### Task 6: 角色指令接线（P3）

**Files:**
- Create: `fantasy_agent/agent_skills.py`（`AGENT_SKILLS` 映射表）
- Modify: `fantasy_agent/orchestrator.py`（按 `owner_agent` 取 system prompt 片段）
- Create: `tests/test_agent_skills.py`

- [ ] `AGENT_SKILLS: dict[ProductionTaskAgent, str | None]`，`None` 表示该角色暂无可复用 skill 并**写明理由**（`director-agent` / `godot-builder` / `qa-agent`），照 `_HIDDEN_ARG_WITHOUT_SOURCE` 的先例。
- [ ] 测试双向查：每个 `owner_agent` 与 `participating_agents` 里的角色都有条目；`skills/` 下每个目录都被至少一个角色引用（新增 skill 目录没人用、或角色漏登记，都会红）。
- [ ] 阶段 goal 里复用 `purpose` / `inputs` / `outputs`，角色指令只补「怎么写」不补「写什么」。

---

## 非目标

- 不做并行阶段执行或多 agent 并发（AGENTS.md 要求单进程本地自闭环）。
- 不让模型决定阶段顺序、跳过阶段或改写 `order`（`order` 是确定性的）。
- 不引入外部编排库（pi / LangGraph / Temporal）。
- 不改 `agent_loop` 的三条边界（模型不能提权、`max_turns` 硬上限、失败不传染）。
- 不为 `quality_gates` 发明检查 DSL。

## 风险

| 风险 | 处置 |
|---|---|
| 收窄工具后模型卡住（该阶段缺它需要的工具） | 白名单来自 `mcp_tools`，Task 1 的「非空 + 可解析」测试保证它不是空的；真缺工具就改编排表，不改编排器 |
| 阶段语汇翻译表靠猜 | Task 4 明确要求用 `execute_godot_demo` 的实际 `record_stage` 调用点实测复核，并标注这一步不能只读代码 |
| 契约加字段影响前端 | `kind` 有默认值，是加法；`types.ts` 必须同步，否则新字段对 UI 不可见 |
| 编排器变成第二个流水线，两套逻辑打架 | 编排器只做「收窄 + 门控 + 记状态」，**不重写任何引擎调用**；执行仍走既有的 `*_mcp.call_*_tool` 与 `executor` |

## 验证

```bash
python scripts/run_tests.py -q                       # 不要直接 python -m pytest
ruff check fantasy_agent tests apps scripts
python scripts/mutation_check_all_guards.py --only <新守卫>
npm run frontend:typecheck && npm run frontend:test && npm run frontend:build
```

新守卫（Task 1/3/4/6 引入的静态检查）都要进 `scripts/mutation_check_all_guards.py`，每个配一条自变异 case（把守卫改坏必须变红），否则它们只是「写下来」，不是「被守住」。
