# 游戏设计流程四轴评审（2026-09-09）

评审对象：prompt → 可玩切片的**设计流水线**，范围全链路（`idea_discovery` → `generation` → `workflows` → `spec_validation` / `production_specs` → `gameplay_codegen` / `godot_mcp` / `unreal_mcp` → `executor`）。

与上一轮「代码四轴」（正确性 / 安全性 / 可维护性 / 测试覆盖）不同，本轮四轴是**流程维度**：

| 轴 | 要回答的问题 |
|---|---|
| 一 设计保真度 | prompt 的意图有多少真的传到了产物？ |
| 二 流程完整性 | 节点衔接、失败、部分失败、续跑时状态是否自洽？ |
| 三 返工闭环 | 评审 / 审批 / 人工纠正能否真的回流改变产物？ |
| 四 可验证性 | 有什么证据能证明设计是「对」的，而不只是「没崩」？ |

**方法**：四路子 agent 并行只读评审 → 主 agent 逐条复核（本轮剔除 2 条误报、修正 1 条）→ 关键指控以实测数据坐实。

---

## 结论摘要

**无 P0 崩溃类问题，但有 1 条 P0 级设计缺陷：确定性生成路径只有 parkour 一种玩法真的被设计出来，其余全部塌缩成同一套模板。**

这条不是代码 bug，代码跑得很好、测试全绿（304 passed）。问题是：**这条流水线对一个「恐怖潜行」prompt 产出的关卡，节拍名叫「Onboarding Pocket / System Mix / Final Push」，与「种南瓜的农场经营」产出的一模一样。**

| 优先级 | 问题 | 轴 |
|---|---|---|
| **P0** | 确定性生成只有 parkour 轴真实分化，其余 3 轴塌缩为通用模板 | 设计保真度 |
| **P0** | `rework_target` 与阶段名是两套词汇表，全仓零映射零消费 | 返工闭环 |
| **P1** | Unreal 侧零消费 `level_beats` / `enemies`，关卡坐标硬编码 | 设计保真度 |
| **P1** | 续跑跳过 `gameplay` 阶段时玩法脚本丢失，静默回退模板 | 流程完整性 |
| **P1** | 审批标 `revision` 的资产等于静默丢弃，无重新生成机制 | 返工闭环 |
| **P1** | 无跨引擎一致性校验与测试 | 可验证性 |
| **P2** | `GameplaySpec` 层校验只有 5 条，且无回归基线 | 可验证性 |

---

## 轴一：设计保真度

### 【真问题 · P0】只有 parkour 轴被真正设计

**实测证据**（跑 5 个差异极大的 prompt，`design_from_prompt_deterministic`）：

| prompt | `_detect_axis` | beats | verbs | enemies |
|---|---|---|---|---|
| rooftop parkour chase across neon towers | parkour | 3 | 4 | 1 |
| a cozy farming sim about growing magical pumpkins | systems | 3 | 4 | 0 |
| deep tactical squad combat with cover system | combat | 3 | 4 | 2 |
| horror stealth in an abandoned hospital | stealth | 3 | 4 | 2 |
| racing through underwater caves | systems | 3 | 4 | 0 |

**beats 恒为 3、verbs 恒为 4。** 展开看内容，差异只在动词：

```
### horror stealth in an abandoned hospital  (axis=stealth)
  verbs : ['scout', 'hide', 'distract', 'extract']
  beat  : Onboarding Pocket | focus=Learn controls and identify the objective language.
  beat  : System Mix      | focus=Use the core verbs while pressure changes the route.
  beat  : Final Push      | focus=Resolve the complete loop with win/fail stakes.
  win   : Complete the primary objective and reach the exit before pressure caps out.

### a cozy farming sim about growing magical pumpkins  (axis=systems)
  verbs : ['explore', 'interact', 'adapt', 'complete']
  beat  : Onboarding Pocket | focus=Learn controls and identify the objective language.
  beat  : System Mix      | focus=Use the core verbs while pressure changes the route.
  beat  : Final Push      | focus=Resolve the complete loop with win/fail stakes.
  win   : Complete the primary objective and reach the exit before pressure caps out.
```

对照 parkour 轴，内容是真分化的：

```
### rooftop parkour chase across neon towers  (axis=parkour)
  beat : Warmup Rooftop     | Chain vaults, wall-runs...  | required_assets=['start marker','checkpoint gate','low vault blockers']
  beat : Momentum Mix       | ...one boost shortcut       | required_assets=['wall-run panels','slide barriers','boost pad']
  beat : Extraction Sprint  | ...choose speed vs recovery | required_assets=['final gap ramp','pressure timer UI','extraction gate']
```

**根因**（AST 统计 `generation.py` 各函数的 `axis ==` 分支）：

| 函数 | 覆盖的 axis |
|---|---|
| `_detect_axis` | parkour, systems, combat, stealth（4 类） |
| `_loop_for_axis` | **parkour, career** |
| `_systems_for_axis` | **parkour, career** |
| `_progression_for_axis` | **parkour, career** |
| `_level_beats_for_axis` | **parkour, career** |
| `_asset_needs_for_axis` | **parkour, career** |
| `_enemies_for_axis` | combat, parkour, stealth, systems（4 类） |

`_detect_axis` 能识别 4 类，但 5 个核心玩法生成函数**只实现了 parkour 与 career 两条分支**。`stealth` / `combat` / `systems` 全部落进 `career` 兜底分支，而 career 分支是通用模板。

**成本账**：兜底分支不是崩溃，是「一定出得来东西」——这符合项目承诺（demo 一定建得出来）。代价是**除了跑酷，其他玩法类型的设计意图在确定性路径上等于零传导**。开了 LLM 能缓解，但默认路径是无 key 的确定性路径，也就是大多数用户拿到的是模板。

### 【真问题 · P1】Unreal 侧零消费设计字段

`unreal_mcp.py` 中 `level_beats` 出现 **0 次**、`enemies` 出现 **0 次**。关卡坐标是硬编码的六个点：

```python
# unreal_mcp.py:864
for index, x in enumerate((0.0, 650.0, 1300.0, 1950.0, 2600.0, 3250.0), start=1):
```

`_level_assembly_manifest`（unreal_mcp.py:797）的签名只接 `request` 与 `ingest_manifest`，**没有 gameplay_spec 入口**。

对照 Godot 侧：`godot_mcp.py` 有 5 处消费 `level_beats`（583/587/621/805/827），是真传导。

**含义**：同一份 `GameplaySpec` 走两条引擎路，Godot 表达了设计，Unreal 表达的是一组固定间距的箱子。AGENTS.md 写了「Godot 是快速可玩验证目标，Unreal 是主线生产导入」——主线反而是不传导设计的那条。

### 【已确认没问题】parkour 轴本身质量不错

动词、节拍名、所需资产、成功条件四层都是 parkour 特化的，`_fit_level_beats_to_target` 也真的按 `target_minutes` 分配（2/5/3 分钟）。这是模板化生成能做到的合理上限，不需要推翻。

---

## 轴二：流程完整性

### 【真问题 · P1】续跑跳过 gameplay 阶段会丢玩法

```python
# executor.py:1102-1112
gameplay_scripts: dict[str, str] = {}
if "gameplay" in skip:
    _skipped("gameplay")
elif with_gameplay:
    gameplay_scripts, gameplay_was_llm = _run_gameplay_codegen(plan, stages)

create = bridge.create_godot_project_structure(
    GodotMCPCreateProjectRequest(
        ...
        gameplay_scripts=gameplay_scripts,   # 空 dict 照样传下去
```

`gameplay` 在 `RESUMABLE_STAGES` 里（pipeline_state.py:52-54），所以从 `create` 或更后阶段续跑时会被跳过，`gameplay_scripts` 为空 dict 仍传给 `create`。下游 `godot_mcp.py:583` 的 `if gameplay_spec is None or not gameplay_spec.level_beats` 不拦这个（spec 还在，只是脚本没了），玩家控制器回退到默认模板。

**表现**：点了「从 create 续跑」，工程建出来了、测试绿，但玩法是模板，不是上一轮生成的那套。

### 【已确认没问题】续跑不会掩盖失败

这块做得扎实，值得点名：

- `stages_before`（pipeline_state.py:176-186）对未知阶段名返回**空集**——typo 不可能静默跳过工作。
- 跳过需同时满足三个条件（executor.py:104-112）：在续跑点之前 ∩ 上次真的 done ∩ 在 `RESUMABLE_STAGES` 里。**失败阶段永远不会被跳过。**
- `create` / `validate` 故意排除在 `RESUMABLE_STAGES` 外：便宜，且后续每个阶段都依赖其产出的 `project_file`。
- 有测试守着 `GODOT_STAGE_ORDER` 与实际阶段同步（AGENTS.md 明写）。

### 【待复核】取消发生在写文件中间会留下半截产物

`ProcessCancelled` 在阶段边界的处理没深挖。若取消落在 `_write_level_assembly` 中途，磁盘上是部分文件，而状态文件可能未更新（此时 `load_state` 返回 None → 不跳过任何阶段 → 安全）。推断是安全的，但没实测，标待复核。

---

## 轴三：返工闭环

### 【真问题 · P0】`rework_target` 是两套词汇表，全仓零消费

取值（`preflight.py:33-36`）：

```python
REWORK_PROMPT = "prompt"      # 原始创意太薄
REWORK_SPEC   = "spec"        # gameplay spec 有洞
REWORK_PLAN   = "godot_plan"  # 引擎交接计划不合法
REWORK_FLAGS  = "flags"       # 运行开关错了
```

阶段名（`pipeline_state.py:33-47`）：

```
spec_validation, preflight, comfyui, blender, approval_gate,
gameplay, create, enemy_metrics, copy_assets, copy_refs, validate, import
```

**交集为空。** 而全仓搜 `rework_target`：

| 位置 | 性质 |
|---|---|
| `preflight.py:117,128,140,152,168,179,190,204,215` | 生产方（8 处） |
| `executor.py:1024` | 生产方（1 处） |
| 其他任何 Python / TS / TSX | **零** |
| `apps/frontend/src/console/FlowConsole.tsx` | 只消费 `resumeFrom`，不认 `rework_target` |

测试层面也只断言「非空」（`test_preflight.py:180-185`），**没有断言它能映射到一个真实可续跑的阶段**。

**后果**：前置闸门说「回到 spec 节点重做」，但没有任何代码把这个 `spec` 翻译成 `resume_from` 的值。用户看到提示，却不知道该填哪个节点名；手填 `spec` 会被 `stages_before` 判定为未知阶段 → 返回空集 → **什么都不跳过，等于整条重跑**。

也就是说：**`rework_target` 目前是纯展示文案，不是可执行的返工路由。** AGENTS.md 里「每个问题带 `rework_target`，直接指出该回到哪个节点」这条承诺没有落地。

### 【真问题 · P1】标 `revision` 的资产等于静默丢弃

`approval_manifest.py` 有 `revision_asset_ids`（:23），executor 里只用于**报数**：

```
executor.py:620  "revision_count": len(approval.revision_asset_ids),
executor.py:627  "revision_asset_ids": approval.revision_asset_ids,
executor.py:632  "Skipped assets remain available in generated/assets for review or revision."
executor.py:654  "revision_asset_ids": approval.revision_asset_ids,
```

没有任何机制让 `revision` 状态的资产触发重新生成。「要求返工」和「拒绝」在效果上都是跳过。文案说「remain available for review or revision」，但流水线里没有 revision 这一步。

### 【已确认没问题】创意评审不是 dead field（推翻子 agent 结论）

子 agent 报 `art_direction` / `required_user_decisions` 无人消费。复核后**不成立**：

- `creative_review` 整体被 `production_specs.py:293-298` 消费，驱动资产审批状态（`_review_decision_by_asset_id`）——这是真闭环。
- `art_direction` / `required_user_decisions` 在前端 `rendering.tsx:270-275 / 415` 展示。

它们不参与机器决策是**设计意图**（给人做判断），不是缺陷。

### 【待复核】人工纠正后的回流路径

`local_tools.manual_correction_targets` 打开目标供人工修改，但没查到「重新读取」的环节。推断改完需整条重跑，未实测。

---

## 轴四：可验证性

### 【已确认没问题】`spec_validation` 比预期扎实

22 条规则，覆盖五类（`spec_validation.py:74-330`）：

| 类别 | 规则 |
|---|---|
| 引用完整性 | encounter.beat / narrative.beat 必须指向存在的 level beat；enemy_roles 必须已声明 |
| 数值 | contact_damage ≤ 100；pressure_clock ≥ target × 45；tuning_bounds 越界；bounds 下界 > 上界 |
| 时长 | **segments 总时长必须等于 `target_session_minutes`**（:137） |
| 路径安全 | config table 的 export_path 必须在 `generated/config` 下、无绝对路径、无 `..` |
| 唯一性 | 重复 table_id、重复主键、**编译文件名冲突**（:216-240，防止后导出覆盖前导出） |
| 审批一致性 | approved 资产不得仍 blocked；非 approved 必须给出 blocked_reason 且列入 blocked_assets |

子 agent 报的「没有时长校验 / 没有重复校验」是**误报**，`:137` 与 `:200-240` 都有。

### 【真问题 · P1】它校验的是 `ProductionSpecBundle`，不是 `GameplaySpec`

`GameplaySpec` 层的校验只有 `preflight.py` 的 5 条：

| code | 严重度 |
|---|---|
| `missing_level_beats` | blocking |
| `missing_win_state` | blocking |
| `missing_failure_states` | blocking |
| `empty_project_name` | blocking |
| `missing_core_verbs` | warning |

而 `spec_validation` 整段是条件执行的：

```python
# executor.py:955
if plan.production_spec_bundle is not None:
    from fantasy_agent.spec_validation import validate_production_spec_bundle
```

实测默认 `run_director_workflow` 确实总带 `production_spec_bundle=True`，所以默认路径下是跑的。但**手工构造 plan、或未来 bundle 生成失败时，22 条校验会整段静默消失**，只剩 5 条。

**该校验而没校验的**：`level_beats` 数量是否 ≥ 3、beat 时长总和与 `target_minutes` 的偏差（GameplaySpec 层，ProductionSpecBundle 层有）、同一 asset 被两个 beat 重复引用、engine 字段与产物是否匹配。

### 【真问题 · P1】无跨引擎一致性校验与测试

全仓 grep 无任何 `godot` vs `unreal` 的对比测试（唯一命中是 `test_studio_app.py:66` 的服务清单断言，不是设计一致性）。结合轴一的 Unreal 硬编码，这意味着**「两条引擎路表达同一个设计」这件事目前没有任何东西守着**。

### 【真问题 · P2】无回归基线

改了 `generation.py` 的模板后，无法自动发现产物变了。只有「测试不红」，没有「产物变了什么」的 diff 机制。

---

## 剔除的误报（复核后不成立）

| 子 agent 原结论 | 复核结果 |
|---|---|
| `creative_review` 的 `art_direction` / `required_user_decisions` 是 dead field | **不成立**。前端 `rendering.tsx:270-275/415` 展示；`creative_review` 整体被 `production_specs.py:293-298` 消费驱动审批。不参与机器决策是设计意图 |
| `spec_validation` 缺时长校验 / 重复校验 | **不成立**。`:137` 校验时长总和，`:200-240` 校验重复 ID 与文件名冲突 |
| `_detect_axis` 只识别 2 类 axis | **部分不成立**。它识别 4 类；问题是**消费方**只实现 2 条分支。结论方向对，根因定位错了 |

---

## 建议修复顺序

| 优先级 | 事项 | 落地方向 |
|---|---|---|
| **P0** | 补 `stealth` / `combat` / `systems` 轴的生成分支 | 至少让 `_level_beats_for_axis` / `_loop_for_axis` 三轴各有特化模板；或明确承认「确定性路径只保 parkour + 通用兜底」，把承诺写进文档不让用户误判 |
| **P0** | `rework_target` → 阶段名映射表 | 在 `pipeline_state.py` 加 `REWORK_TARGET_STAGES: dict[str, str]`，并加测试断言每个取值都指向真实可续跑阶段；前端「回到 X 重做」按钮直接读它 |
| **P1** | Unreal 侧消费 `level_beats` | `_level_assembly_manifest` 增加 `gameplay_spec` 参数，替换硬编码的 6 个 x 坐标 |
| **P1** | 续跑不丢玩法 | `gameplay` 从 `RESUMABLE_STAGES` 移出，或把 `gameplay_scripts` 落盘到 session 目录供续跑读取 |
| **P1** | `revision` 资产触发返工 | 至少给出明确的 next_action 文案 + 可用的重新生成入口，别让「返工」等于「丢弃」 |
| **P1** | 跨引擎一致性测试 | 同一 spec 走两条路，断言 level beat 数 / 敌人数 / 胜负条件一致 |
| **P2** | GameplaySpec 层补校验 + 回归基线 | 补 beat 数量、时长偏差、asset 重复引用；产物快照 diff |

---

_评审人：灯 💡 | 方法：四路子 agent 并行只读评审 + 主 agent 逐条复核 + 关键指控实测坐实_
_复核状态：剔除 2 条误报、修正 1 条根因定位；3 条标【待复核】未实测，见各轴_

---

## 修复记录（2026-09-09）

两条最重的都已落地。测试 304 → 320，ruff 全仓干净。两条都做了变异测试确认真的钉住。

### P0 `rework_target` 零消费 → 加翻译层

根因是两套词汇表没有连接点：`rework_target` 是**创作节点**（改什么），阶段名是**执行节点**（从哪跑）。

| 落地点 | 内容 |
|---|---|
| `pipeline_state.py` | 新增 `REWORK_TARGET_STAGES`（目标→最早需重跑的阶段）、`REWORK_CODE_STAGES`（`flags` 两个开关的细粒度覆盖）、`normalize_resume_from()`（接受两种写法，未知值抛错而非静默全量重跑）、`resume_stage_for()` |
| `preflight.py` | `PreflightIssue.resume_stage` 用 `@computed_field`，保证进 JSON；`summary()` 同时给出「改什么」和「从哪跑」 |
| `executor.py` | `_resume_skip` 先归一化再查状态（校验前置，无论有无历史状态都一致报错） |
| `__main__.py` | `--from-stage` 接受返工目标；help 列出两套取值 |
| `apps/studio/app/main.py` | `_validate_resume_request`：未知值 400 + 缺 `session_id` 时 400（后者此前会静默新建 session，等于整条重跑） |

映射语义（保守优先，宁可多跑不可复用陈旧产物）：

| 目标 | 阶段 | 理由 |
|---|---|---|
| `prompt` | `spec_validation` | 换创意则全盘重生成，无可复用 |
| `spec` | `comfyui` | spec 同时喂 ComfyUI 备注 / Blender 备注 / Godot 路线 / 玩法代码，全部重建 |
| `godot_plan` | `create` | 只影响工程结构，视觉资产与玩法脚本不依赖它 → **真省节点** |
| `flags` | `blender` / `gameplay` | 按 issue code 细分：`assets_declared_not_enabled`→`blender`，`enemies_declared_not_generated`→`gameplay` |

**一处契约变更**：未知续跑节点从「跳过空集 = 整条重跑」改为**显式报错**。旧行为安全但把一次 typo 变成全量重放，正是这个模块要消灭的浪费。`test_unknown_resume_target_skips_nothing` 已改写为 `test_unknown_resume_target_is_rejected_loudly`。

### P1 Unreal 零设计传导 → 照 Godot 的模式改

Godot 侧早就是「一个 level_beat 一段路线，beat 名进 actor 名，无 spec 时回退」。Unreal 照此重写 `_level_assembly_manifest`：

- 新增 `_beats_from_spec()`：从 `spec.level_beats` 取 (名字, 分钟)，无 spec 时回退 teaching/mix/finale 三段（与 AGENTS.md 的第一分钟/中段/最后一段一致）
- 路线长度与分段由节拍推导：`floor_count = max(4, round(total_minutes × 0.6))`——0.6 这个系数正好复现原手工布局的 6 块地板，所以无 spec 时产物不变
- 道具位置从**绝对厘米**改为**路线比例**，随设计伸缩
- 每个 placement 的 `beat` 字段改为真实节拍名，可反查 GDD
- 新增 `enemy` 角色（`contracts.py` 的 `UnrealLevelPlacementRole`），`spec.enemies` 现在会生成出生点标记，沿路线 0.35→0.9 分布
- 敌人声明了但没有可用资产时写进 `risks`，不静默丢弃
- `UnrealMCPPrepareLevelAssemblyRequest` 新增 `gameplay_spec` 字段，executor 接线传入

**实测对比**（同一条流水线，两种设计）：

```
5分钟潜行（2节拍 + 2敌人）  地板 4  长度 1950cm  敌人标记 2  节拍 ['Exit','Ward']
15分钟跑酷（4节拍 + 无敌人） 地板 9  长度 5200cm  敌人标记 0  节拍 ['A','B','C','D']
```

无 spec 时仍是 6 块地板 / 3250cm，与改动前一致。

### 变异测试结果

| 改动 | 变异 | 结果 |
|---|---|---|
| P0 | `godot_plan` → `spec_validation` | `test_resuming_from_a_rework_target_skips_real_work` 变红 |
| P0 | 删除 `spec` 映射 | 8 条变红（含漂移守卫与 JSON 载荷断言） |
| P1 | `_beats_from_spec` 强制走回退分支 | 3 条变红 |
| P1 | `floor_count` 改回固定 6 | `test_route_length_follows_the_design_duration` 变红 |

---

## 修复记录（2026-09-09 晚）：补齐全机制轴特化模板

测试 320 → 404（新增 `tests/test_generation_axis.py` 84 例），ruff 全仓干净，三次变异测试全部如期变红。

### P0 机制轴只有 parkour / career 两条实现

实测（5 个差异极大的 prompt）此前产出 `beats=3 / verbs=4` 完全相同。根因经 AST 统计 `axis ==` 分支确认：`_detect_axis` 能识别 8 类，但 5 个核心生成函数只实现了 parkour / career，其余 6 类全落通用兜底。

**做法：表驱动重构，而非继续堆 if 分支。** 8 条轴 × 5 类内容若写成 if 分支会膨胀到 1200+ 行，且每加一条轴要改 5 个函数——那正是漂移的温床。

- 新增 `fantasy_agent/axis_templates.py`：每条轴一份 `AxisTemplate`（动词 / 四步循环 / 三系统 / 三段曲线 / 三节拍 / 资产 / 叙事）。
- `generation.py` 五个 `_for_axis` 函数改为查表，parkour 的英文逐字保留（`test_workflows.py` 断言了 `Momentum Chain`）。
- 新增 `stealth` / `combat` / `survival` / `puzzle` / `mobility` 五条轴；`systems` 保留为兜底轴，文案刻意通用并在注释里说明。

**实测对比（改动后）：**

| prompt | axis | 关卡节拍 |
|---|---|---|
| rooftop parkour | parkour | Warmup Rooftop / Momentum Mix / Extraction Sprint |
| horror stealth hospital | stealth | Outer Ward / Patrol Crossing / Vault Extraction |
| tactical squad combat | combat | Sparring Yard / Pressure Wave / Boss Reckoning |
| frozen island survival | survival | Shelter Basin / Forecast Spike / Cache Run |
| portal puzzle dungeon | puzzle | Teaching Chamber / Twin Rule Hall / Chain Room |
| cozy farming pumpkins | systems | Onboarding Pocket / System Mix / Final Push |

### 顺带修掉：mobility 轴在英语里不可达

`"racing"` 不包含子串 `"race"`（r-a-c-i-n-g），关键词表只写了 `"race"` —— 这条轴对自己的最常见词形无反应。补 `racing` / `racer` / `time trial` / `lap time` 及中文词，并加最小关键词路由测试钉住。

### 中文文案必须一起改，否则是"看着有内容其实在骗人"

`i18n.py` 按位置把英文字段和 zh-CN 配对，且**只有 career 有真中文**，其余 7 条轴（含 parkour）共用一套通用文案。只特化英文会让中文 GDD 写着"教学口袋区"而英文 spec 写着 "Warmup Rooftop"——比不特化更糟，因为文档看起来有内容。

所以中文一并进入模板：

- `i18n.py` 从 `AXIS_TEMPLATES` 取 zh-CN，删掉全部按 axis 硬编码的中文分支（459 → 335 行）。
- `AXIS_ZH` 改为从模板派生，消掉第二份清单。
- 补齐 72 个 beat 资产术语 + 87 个 systems 输入/输出术语到共享词汇表（此前会漏英文到中文句子中间）。
- 每条轴的 `zh_assets` / `zh_notes_for_comfyui` 进模板——此前 `asset_needs` 的中文只有 career 一份，潜行设计会被标注成"灰盒场地套件"。

**中英对照实测：**

```
parkour  EN=['Warmup Rooftop', 'Momentum Mix', 'Extraction Sprint']  ZH=['热身屋顶','动量混合段','撤离冲刺']
stealth  EN=['Outer Ward', 'Patrol Crossing', 'Vault Extraction']    ZH=['外围病区','巡逻交汇口','密库撤离']
combat   EN=['Sparring Yard', 'Pressure Wave', 'Boss Reckoning']     ZH=['练武场','压迫波次','首领清算']
```

### 变异测试

| 变异 | 结果 |
|---|---|
| stealth 节拍名改成 systems 的 `Onboarding Pocket` | `test_no_two_axes_share_a_beat_name` 变红 |
| 删掉 `racing` 关键词 | 5 条变红（含可达性、中英差异、最小关键词路由） |
| 中文 beat 名回退通用文案 | `test_chinese_beat_names_differ_between_axes` 变红 |

第一次跑变异 2 时**没变红**——测试用的 prompt 里还含 "speed"，把 mobility 兜住了。已把 prompt 改成不含 speed/chase 的形式，并单独加最小关键词断言。

### 未做（明确交代）

- `gameplay_codegen.py` 仍只有 `axis == "parkour"` 两个分支，生成的 GDScript 玩法代码没有跟着新轴特化。设计意图现在传到了 spec / GDD / 关卡，还没传到代码。
- 8 条轴的中文文案是逐条手写的，`systems` 兜底轴的资产与 ComfyUI 备注仍偏通用。
