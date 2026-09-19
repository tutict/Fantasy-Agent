# 内部 pi 的任务编排方案（实施计划）

> **给编码 Agent：** 本文件是分阶段提示文档。按 Task 顺序做，每个 Task 的 checkbox 逐条勾。**每个 Task 都要先写失败测试再实现**，且做完一个 Task 就跑一次全量测试与 `ruff`。
>
> 状态：**Task 1 ✅ / Task 2 ✅（2026-09-19，`fantasy_agent/orchestrator.py` + `ToolRegistry.scoped`，20 条测试 + 11 个变异全红）/ Task 3–6 ✅（2026-09-19）**。四个相关测试文件现共 132 条（`test_orchestrator` / `test_agent_skills` / `test_pipeline_state` / `test_studio_app`），全量后端 **734 passed / 0 failed**，`scripts/mutation_check_all_guards.py` **93/93 caught**（四轴 review 补了 `S2`：摘掉 `skill_brief` 的截断必须红）。下游 F3 编排板也已落地，见 `docs/superpowers/plans/2026-09-16-frontend-ui-replan.md`。

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

### Task 2: 编排器骨架（P0）✅ 已完成

**Files:**
- Modify: `fantasy_agent/tool_registry.py`（加 `ToolRegistry.scoped`）
- Create: `fantasy_agent/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [x] `ToolRegistry.scoped(names, *, up_to=None) -> ToolRegistry`：派生一个只含 `names` 的 registry，并**共享同一个 `artifacts` dict**（复用 `default_registry(target=...)` 的模式，这是 plan 注入能继续生效的前提）。名字解析不到就 `ValueError`——白名单写错必须响亮失败，不能静默给出一个空工具集。
- [x] `Orchestrator.run(plan, *, allow_write=False, allow_execute=False, max_turns=...)` 推进规则：
  - `depends_on` 未全部 `done` → 该阶段 `blocked`，**不派 agent、不消耗轮次**；
  - `kind="human"` → 置 `awaiting_human`，**不派 agent**；
  - 白名单 ∩ 授权可见集为空（例如整个阶段都是 execute 级工具但没给 `allow_execute`）→ 置 `awaiting_confirmation`，**不派 agent 去空转**；
  - 否则 → `run_agent(registry=scoped(stage.mcp_tools), permission_ceiling=...)`，其中 `permission_ceiling` 照现有规则跟随授权（无授权只见只读工具）。
  - 每阶段结束调 `pipeline_state.record_stage`。
- [x] 测试：monkeypatch `agent_loop.complete_with_tools`（**不是** `llm.complete_with_tools`，见 09-07 记录），断言模型收到的 schema **只有该阶段的工具**，且总数小于全量 20。
- [x] 测试：`depends_on` 未满足时，那个阶段的 handler 一次都没被调用。
- [x] 测试：模型请求白名单外的工具 → 得到 `error`（registry 不认识这个名字），循环继续而不是崩。
- [x] 测试：失败不传染——某阶段抛 `LLMError` 时该阶段标 `failed`，其余阶段状态不变，调用方拿到 `status="error"`。
- [x] 测试：`kind="human"` 的阶段全程不产生任何工具调用。

**验收（2026-09-19）：** `tests/test_orchestrator.py` **20 passed**；全量后端 655 passed；变异验证 **11/11 caught**，逐个逐字节还原。

**计划外发现四处，都写进代码了：**

1. **`run()` 是「推进」不是「重跑」，这需要一个 outcome map。** 计划只说"每阶段结束调 `record_stage`"，没规定同一实例被二次调用时的语义。但人工闸门的整个用法就是"用户动作后再 `run()` 一次"——若不记住已完成阶段，确认第 8 阶段的 `creative_review` 会把前面 7 个昂贵阶段重放一遍。所以 `Orchestrator` 持有 `self._outcomes`，已 `done` 的阶段直接返回上一次的结论、不派发、不花轮次。重跑一个**已完成**阶段属返工路径（Task 4）的职责，`run()` 只向前。测试 `test_a_finished_stage_is_not_dispatched_a_second_time` 钉住这条，变异 M8 报红。

2. **`kind="agent"` 但 `mcp_tools` 为空 → `failed`，不是 `awaiting_confirmation`。** 两者都表现为"可见集为空"，但含义相反：前者是阶段声明写错了（Task 1 的契约守卫已让它不可达标，但手写计划仍能出现），后者是权限不够、等人授权。把它们混为一谈会让一个写坏的阶段永远显示"等待确认"。

3. **编排阶段的记录与执行层阶段共用 `_pipeline_state.json`，这是有意的，但必须钉住。** `StageState.name` 用的是编排层 id（`creative_review`），而执行层用的是 `preflight` / `create` / `validate` 等。两套词汇表同文件共存是安全的——`executor._skippable_stages` 是 `stages_before(t) & done_stages() & RESUMABLE_STAGES`，三项都在执行层词汇表里过滤，而 `stages_before` 只看 `order` 元组、从不读记录名。但"安全"是推出来的，所以加了 `test_an_orchestration_record_never_tells_the_executor_to_skip_a_node` 对 `GODOT_STAGE_ORDER` 全量遍历断言。Task 4 正是要做两套词汇表的翻译，这条边界不能靠巧合。

4. **`agent_loop` 已把 `LLMError` 转成 `status="error"`，所以"某阶段抛 LLMError"不会真的抛穿。** 编排器只负责把这一个阶段的 status 映射成 `failed`，其余阶段的 outcome 原样保留。测试里 monkeypatch 的是 `complete_with_tools`（真的抛 `LLMError`），验的是这条既有路径而不是编排器自己的异常处理。

**两条本机工具事实（都踩过，一并记下）：**

- **`BLE001` 会豁免「handler 里调 `logger.exception`」的 `except Exception`。** 所以在那处写 noqa 会被 `RUF100` 判为 unused。做了对照实验（同形状 handler，带/不带日志各一个文件）才确认，不是猜的。
- **二进制读改写变异针点时，盘上文件是 CRLF 而针点里写 `\n` 会静默 0 命中。** 本仓 `core.autocrlf=true`，工作区是 CRLF。项目自带的 `mutation_check_all_guards.py` 因为走文本模式（读时归一化、写时再翻译）而绕过了这个坑；二进制模式下必须显式适配，否则两条变异静默 SKIP 却仍报「已证明」。

### Task 3: 阶段出口校验（P1a）✅ 已完成（2026-09-19）

**Files:**
- Modify: `fantasy_agent/contracts.py`（`exit_checks: list[str]`，默认空）
- Modify: `fantasy_agent/orchestrator.py`
- Modify: `tests/test_pipeline_contract.py`、`tests/test_orchestrator.py`

- [x] 加 `ProductionPipelineStage.exit_checks: list[str] = Field(default_factory=list)`。空 = 不做机器校验，维持现状。
- [x] 编排器在阶段结束后逐个调用 `exit_checks`，全部 `status == "ok"` 才把阶段标 `done`；任一非 ok → 阶段 `failed` 并把失败的工具名写进 `detail`。
- [x] 测试：`exit_checks` 里的名字必须以 `read_only` 权限注册——**非只读工具不许进 exit_checks**，否则出口校验会变成偷偷执行引擎。
- [x] 测试：某 check 返回 `error` 时阶段是 `failed` 而不是 `done`。

**落地时加的两条边界（计划里没有）**：

1. 校验结果记在 `outcome.checks`，与 `outcome.tools` **分开**。`tools` 是「模型被给了哪些工具」（菜单），`checks` 是「阶段结束后真跑了什么」。合成一个字段，界面上「由 X 校验通过」就会变成在读模型的菜单——`test_a_stage_runs_its_exit_checks_before_it_counts_as_done` 钉着这条。
2. 出口校验**不受阶段工具白名单约束**（`test_an_exit_check_runs_even_when_it_is_not_in_the_stages_whitelist`），因为白名单管的是"模型能用什么"，而出口校验是编排器自己跑的只读工具；同时 `kind="human"` 的阶段**不跑**任何出口校验（`test_a_human_stage_runs_no_exit_check`）——它没有工具可跑，跑了就是把审批阶段判成 failed。

### Task 4: 返工闭环 + 阶段词汇翻译（P1b）✅ 已完成（2026-09-19）

**Files:**
- Modify: `fantasy_agent/pipeline_state.py`（加 `ORCHESTRATION_TO_EXECUTOR_STAGES`）
- Modify: `fantasy_agent/orchestrator.py`
- Modify: `tests/test_pipeline_state.py`、`tests/test_orchestrator.py`

- [x] 加 `ORCHESTRATION_TO_EXECUTOR_STAGES: dict[ProductionPipelineStageId, tuple[str, ...]]`，**允许空元组**（`gameplay_orchestration` 与 `creative_review` 就没有对应的执行步骤）。
- [x] 测试：每个 `ProductionPipelineStageId` 都有条目（新增 stage id 忘了加映射必须红）。
- [x] 测试：映射值里的名字都在 `GODOT_STAGE_ORDER ∪ UNREAL_STAGE_ORDER` 里。
- [x] 阶段失败 → 用 `resume_stage_for(rework_target, code)` 解析出执行阶段 → 反查回编排阶段 → 从那里重跑，而不是整条重来。`rewind_from(plan, stage_id)` 返回被抹掉的阶段列表，`test_a_rework_target_lands_on_the_orchestration_stage_that_owns_the_node`（`godot_plan` → `godot_quick_play` 两跳）与 `test_a_rework_target_resolves_through_the_per_issue_override` 钉住。
- [x] **待实测复核**：按这一步做了——一次性探针 `scripts/_probe_stage_vocab_tmp.py` 用 stub bridge 跑真实入口、打印 `record_stage` 实际发出的名字，表是对着观察结果写的；**探针已删除**，复核结论落在 `test_pipeline_state.py` 的映射断言上。

**落地时加的两条**：

1. **未知阶段名一律报错，不再静默退化成整条重跑**（`test_rewinding_an_unknown_stage_is_a_loud_error`）。Studio 侧也照此处理：`rewind_stage` 传了不存在的 id 时返回带 `rewound: []` 的 payload，而不是 500。
2. **返工能重新回答已经答过的人工闸门**（`test_a_rewind_lets_a_human_gate_be_re_answered`）——否则返回到闸门之前，闸门的旧结论会把它直接判成 done，返工等于没发生。

### Task 5: 阶段级确认（P2）✅ 已完成（2026-09-19）

**Files:**
- Modify: `fantasy_agent/orchestrator.py`
- Modify: `apps/studio/app/main.py`（暴露待确认阶段）
- Modify: `tests/test_orchestrator.py`、`tests/test_studio_app.py`

- [x] `requires_confirmation=True` 的阶段（实测 2–7 全是）进入前产出 `awaiting_confirmation` 记录，由 Studio 的用户动作推进（`test_a_stage_that_asks_for_confirmation_waits_for_a_person`）。
- [x] 全局 `allow_write` / `allow_execute` **不足以**让某个 stage 直接跑完——授权要能按阶段给。`run(..., confirm_stages=(...))` 是那个按阶段的授权，`test_confirming_the_stage_lets_it_run` 与 `test_confirming_a_stage_does_not_widen_its_permissions` 分别钉住「确认后能跑」和「确认了也没多拿权限」。
- [x] 测试：未确认阶段里的 write/execute 工具仍然 `refused`（同上那条测试断言 `records.get(WRITE_TOOL, 0) == 0`）。
- [x] 前端：待确认阶段可见、状态可点（`tests/test_frontend_endpoint_coverage.py` 覆盖新端点）。界面落在 F3 编排板的 `or-gate` 区与阶段卡 approve 按钮；`kind="human"` 的阶段**不给** approve 按钮，只给「打开审批界面」入口——批准它不会让它跑。

**一条只有跑起来才发现的**：确认状态必须活到下一次 `run()`（`test_a_confirmation_survives_the_next_pass`）。编排器「推进不重跑」的语义让"确认第 8 阶段"这类操作发生在第二次调用上，若确认记录不跨次留存，第二次调用会重新把它判成待确认——闸门就永远打不开。

### Task 6: 角色指令接线（P3）✅ 已完成（2026-09-19）

**Files:**
- Create: `fantasy_agent/agent_skills.py`（`AGENT_SKILLS` 映射表）
- Modify: `fantasy_agent/orchestrator.py`（按 `owner_agent` 取 system prompt 片段）
- Create: `tests/test_agent_skills.py`

- [x] `AGENT_SKILLS: dict[ProductionTaskAgent, str | None]`，`None` 表示该角色暂无可复用 skill 并**写明理由**（`director-agent` / `godot-builder` / `qa-agent`），照 `_HIDDEN_ARG_WITHOUT_SOURCE` 的先例——`test_a_role_with_no_skill_says_why` 要求理由非空。
- [x] 测试双向查：每个 `owner_agent` 与 `participating_agents` 里的角色都有条目；`skills/` 下每个目录都被至少一个角色引用（`test_every_role_the_pipeline_uses_has_an_entry` / `test_the_table_covers_the_whole_contract_not_just_todays_plans` / `test_every_named_skill_directory_exists` / `test_every_skill_directory_is_claimed_by_a_role`）。
- [x] 阶段 goal 里复用 `purpose` / `inputs` / `outputs`，角色指令只补「怎么写」不补「写什么」（`test_the_goal_still_carries_purpose_and_outputs_not_the_skills_copy`）。

**落地时加的三条**：

1. **skill 摘要把 `Inputs` / `Outputs` 两节删掉**（`test_the_brief_drops_the_inputs_and_outputs_sections`）再贴进 system prompt——那两节是给流程看的，进 prompt 只会制造与 goal 的第二份事实。
2. **摘要有体积上限**，因为每轮都要发（`test_every_brief_is_small_enough_to_send_on_every_turn`）。
3. **没有 skill 的角色拿到的是原样的共享指令**，不是空串（`test_a_role_without_a_skill_gets_the_shared_instructions_unchanged`）——静默变成空 prompt 会让角色行为无声降级。

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
