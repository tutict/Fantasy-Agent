# 推送前四轴 review（2026-09-11）

> **状态：无 P0 / P1。5 条 P2 已修，6 条经复核判为不成立或降级接受。** 修复记录见文末。

评审对象：**本地已提交但尚未推送的全部 13 个提交** —— `git diff origin/main..main`，66 文件，+13738/−3649。

四轴沿用 09-08 那轮的**代码四轴**（正确性 / 安全性 / 可维护性 / 测试覆盖），因为本轮范围是混合的后端流水线 + 前端重写，不是上一轮的纯前端。

**方法**：四路子 agent 并行只读评审 → 我逐条复核（**本轮剔除/降级 4 条误报**）→ 关键修复做变异验证确认"该红时红"。

## 四轴结论

| 轴 | 查什么 | 结论 |
|---|---|---|
| **正确性** | 逻辑、边界、错误处理、续跑状态自洽、契约与实现相符 | 未发现 P0/P1。1 条语义不一致（降级子阶段标 `failed`），判为低危并说明为何推前不动 |
| **安全性** | AGENTS.md 硬约束、执行闸门、任意二进制、路径穿越、命令注入、XSS、凭据 | **无阻断项。** 五类攻击面实测干净；1 条非可利用的防御性一致化已修 |
| **可维护性** | 重复、超长函数、多套知识源、死代码、注释与代码不符 | 单一真相源做得扎实（5 组双向守卫）；1 条**孤儿且错误**的常量已修 |
| **测试覆盖** | 假绿、新代码裸奔、弱断言、守卫有效性、CI 覆盖缝隙 | 6 组守卫逐项验真；2 条真缺口已修（1 条名实不符的假守卫、1 个跨边界函数零测试） |

**总体：无 P0、无 P1。** 5 条 P2 已修，另 6 条经复核不成立或降级接受（见「复核记录」）。

---

## 已修的 5 条

| # | 轴 | 位置 | 问题 | 证据 |
|---|---|---|---|---|
| 1 | 可维护性 | `fantasy_agent/pipeline_state.py:56` | `UNREAL_STAGE_ORDER` **全仓零引用**（`GODOT_STAGE_ORDER` 有 19 处），且**内容与实际不符**：`execute_unreal_demo` 会发出 `spec_qa` 与 `spec_validation`，而该元组两个都没有。`stages_before(target, order=...)` 正是等它当 `order` 用——将来有人按这份错清单接 Unreal 续跑，会写出一份永远对不上的映射 | `grep -rn UNREAL_STAGE_ORDER` 只命中定义处；`tests/test_executor.py:672` 已断言实际发出 `[create, spec_compile, spec_qa, prepare_ingest, prepare_level, validate]` |
| 2 | 测试覆盖 | `tests/test_unreal_mcp.py:723` | `test_declared_enemies_without_an_asset_are_reported` **名实不符**：函数名与 docstring 说要验证"声明了敌人却没有资产时会被上报"，正文却断言 `not any("enemy spawn" in risk ...)`——**恰好是相反结论**，因为它用的夹具本来就带 spawn marker | 原正文注释自认「this path is exercised by removing it」，即该分支从未被执行 |
| 3 | 测试覆盖 | `apps/frontend/src/shared/api.test.ts` | `callWorkbenchTool`（`api.ts:116`）**零单测**：URL 拼接、`encodeURIComponent`、POST + JSON body 都没被断言。它已是工作台全部 11 个工具的唯一出口 | `api.test.ts` 的 import 列表覆盖了 5 个函数，不含它 |
| 4 | 可维护性 | `fantasy_agent/executor.py:70` | `StageResult.status` 的注释写着 `pending \| running \| done \| failed \| blocked`，**漏了 `degraded`** —— 而 `degraded` 已在 `executor.py:580/1246/1455` 三处使用，且 `test_executor.py:705` 明确断言它 | 注释与代码不一致，读注释的人会以为 `degraded` 不是合法值 |
| 5 | 安全性 | `fantasy_agent/executor.py:1548` | `_write_unreal_import_manifest` 用 `Path(workspace_root) / rel` 直接拼，**绕过**全模块统一的 `resolve_workspace_path(required_prefix=...)`。该文件另有 **10 处**都走了解析器，只有这一处漏网 | `rel` 是硬编码字面量 `"generated/import-manifest.yaml"`，**当前不可利用**；按一致性加固处理 |

---

## 复核记录：判为不成立 / 降级 / 接受的指控

子 agent 报了、我查完认为不该按原级别处理的。留档以免下次重复排查。

| 原指控 | 复核结果 |
|---|---|
| 可维护性：`AGENTS.md:277` 也把 `UNREAL_STAGE_ORDER` 当既有能力描述 | **假引用**。`AGENTS.md` 只提到 `GODOT_STAGE_ORDER`（第 88 行），全仓 grep 该常量在 `.md` 里零命中 |
| 正确性：`execute_asset_pipeline:828` 与 `execute_godot_demo` 对同类降级给出相反结论，是缺陷 | **降级为设计使然**。两个入口的交付物不同：资产管线的**唯一职责**就是产出资产，没产出即整体 `failed` 是对的；Godot demo 的资产只是加分项，降级后 demo 仍在，整体 `done` 也是对的。同名子阶段、不同整体语义，是这个差异的正确表达，不是不一致 |
| 正确性：降级子阶段标 `failed` 而整体 `done`，`result.ok` 与 `stages` 打架 | **事实成立，但推前不改**。把它改成 `degraded` 会连带改变 `execute_asset_pipeline:828` 的聚合结论（`any(status == "failed")` 不再命中 → 资产全瞎也报 `done`），这是一次**行为变更**，不该混在推送前的收尾里。已改为在 `executor.py:70` 把 `degraded` 写进词表，并把语义差异记在这里 |
| 安全性：`api_settings.py:130` 的 `chmod(0o600)` 在 Windows 是 no-op，密钥明文落盘 | **已知取舍，代码已注明**：该行上方就写着 `# Best-effort owner-only permissions; a no-op on Windows.`。传输与读取链路全程掩码（`public_settings()` / `test_connection` 响应均不含明文），属本机开发工具的取舍，非新缺陷 |
| 测试覆盖：`SeedInspector.tsx` / `DiscoveryThread.tsx` 无专属单测 | **降级**。`SeedInspector` 只从 `workbenchModel` 导入两个常量与一个类型，解析与映射逻辑都在纯函数层（`workbenchModel.test.ts` 26 例）；组件本身是哑组件，`PlanningWorkbench.test.tsx` 的间接覆盖已足够 |
| 安全性：`_write_unreal_import_manifest` 绕过 `required_prefix`（同上表 #5） | 事实成立但 **非可利用**，已按防御性一致化修掉 |

---

## 已确认合规（非问题，列此以免下轮重复排查）

**安全边界**

- 全仓 **0 处** `shell=True` / `os.system` / `os.popen` / `eval` / `exec`（`fantasy_agent/` + `apps/` 实测 grep 无命中）；所有进程调用都是参数列表。
- 全仓无 `CORSMiddleware` / `allow_origins` / `0.0.0.0`。
- `apps/frontend/src/` **0 处** `dangerouslySetInnerHTML`。
- **执行闸门**：实测 4 处 `confirmed: true` / `confirmed=True` 字面量，逐处查证均为**过闸之后**的值，不是旁路：
  - `apps/studio/app/main.py:1073` / `:1102` —— 上方都有 `if not req.confirmed: return preview`，字面量是 worker lambda 闭包里的"已确认"值；
  - `apps/frontend/src/shared/api.ts:182` / `:300` —— 分别是 `startExecute` / `startAssetExecution`，即"用户已确认的那次运行"；唯一调用点是 `FlowConsole.tsx:296` / `:358`，由"先显示副作用清单、再点确认"两步触发（`onGenerateClick` → `previewExecute(confirmed=false)` → 确认按钮 → `startGenerate`）。
  - 与 09-10 那条 P1 的区别：`openManualCorrectionTarget` 当时是在**用户没要求执行**的动作里写死 `true`，无二次确认；这 4 处是同一个端点的"已批准"分支，用户动作就是那个确认按钮。
  - 附注（已知范围限制，非缺陷）：Studio 只监听 `127.0.0.1`，本机任意进程都能直接 POST `confirmed: true`。这个闸门是**防误操作**的 UX 闸门，不是对本机进程的安全边界——与既有设计一致。
- 任意二进制：`tool_registry.EXECUTABLE_FIELDS` + `_probe_executable()` 强制覆盖模型传入值，`exposed_executable_args()` 有测试钉住为空。
- 路径穿越：请求驱动的文件写都走 `resolve_workspace_path(required_prefix=...)`，`is_absolute_path` 覆盖了 Windows 上 `/etc/passwd` 不算绝对路径这个坑。

**正确性与契约**

- 续跑状态机：`_resume_skip` 用 `stages_before ∩ done_stages ∩ RESUMABLE_STAGES` 三重交集，失败/未跑过的阶段绝不跳过；`DONE_STATUSES = {"done"}`，所以 `degraded` 不会被误当已完成；未知续跑节点 `raise ValueError`，不退化成全量重放。
- 取消信号：`ProcessCancelled` 在各 stage 函数中被显式 `raise` 透传，未被 `except Exception` 吞掉。
- GPT-6 Responses API：`supports_sampling_params` 对 `gpt-6*` / `o*` 正确省略采样参数；`function_call_output` 的 `call_id` 与响应 `output` 对齐。

**可维护性**

- 五组"单一真相源"都有**双向**守卫：阶段顺序（`GODOT_STAGE_ORDER` ↔ executor）、返工映射（`REWORK_TARGET_STAGES` ↔ `preflight.REWORK_*`）、工具名（前后端）、端点（前后端 + 白名单过期校验）、i18n 字典（键集合 + 非空）。
- `AGENTS.md` 里的数字与代码一致：引擎工具 16 个、`schema_ref` 34 个，实测相符。
- 死代码已清：`WORKBENCH_PATH` 有测试断言其不存在，`planning-workbench.html` 已删且被断言。
- `ruff check .`（含 `apps/`）全绿。

---

## 变异验证（确认新守卫真会红，不是假绿）

| 变异 | 结果 |
|---|---|
| 从 `UNREAL_STAGE_ORDER` 删掉 `spec_qa` | 红：`assert 'spec_qa' in ('spec_validation', 'preflight', 'create', 'spec_compile', ...)` |
| 关掉 `enemy_spawn_marker` 缺失时的风险上报分支 | 红：`AssertionError: [...]` / `assert []` |
| 去掉 `callWorkbenchTool` 的 `encodeURIComponent` | 红：前端 `percent-encodes the tool name ...` 1 例失败 |

---

## 数字

| 项 | 评审前 | 评审后 |
|---|---|---|
| 后端 pytest | 475 passed, 8 skipped | **476 passed, 8 skipped** |
| 前端 vitest | 65 passed (6 文件) | **67 passed (6 文件)** |
| `ruff check .` | All checks passed | All checks passed |
| `frontend:typecheck` | 0 错 | 0 错 |
| `frontend:build` | ✓ | ✓（bundle `index-Bi_2-NR5.js`，310.14 kB） |

后端 +1 是新增的 Unreal 阶段顺序守卫（那条敌人的测试是改写，计数不变）；前端 +2 是 `callWorkbenchTool` 的两例。

---

## 修复记录

| # | 级别 | 处理 | 落点 |
|---|---|---|---|
| 1 | P2 | **已修** | `UNREAL_STAGE_ORDER` 补上 `spec_validation` / `spec_qa` 并调整顺序，加注释说明「Resume 尚未接线，此元组是为了接入时从一份与现实相符的清单出发」；新增 `tests/test_executor.py::test_unreal_stage_order_covers_every_stage_the_executor_emits`，**同时校验成员与顺序**（`stages_before` 是按位置读的，只查成员不够） |
| 2 | P2 | **已修** | 给 `_write_level_source_manifests` / `_assemble` 加 `assets` 参数，新增 `ASSETS_WITHOUT_ENEMY_MARKER` 夹具；测试改为断言「无 enemy placement + 风险文本出现 + 类型数写进文案」，并保留原名字（现在名副其实了） |
| 3 | P2 | **已修** | `api.test.ts` 新增 `workbench tool calls` 两组：一例断言 URL / method / body 往返与 envelope 返回，一例断言工具名被百分号编码而不是新增路径段 |
| 4 | P2 | **已修** | `StageResult.status` 注释补 `degraded` 并说明语义（"产出了空但运行继续；故意不算 `done`，所以续跑会重试；也不算 `failed`，以免读的人以为整条跑挂"） |
| 5 | P2 | **已修** | `_write_unreal_import_manifest` 改用 `resolve_workspace_path(rel, required_prefix="generated")`，与同模块另外 10 处一致 |

---

## 未做（明确交代）

| 事项 | 为什么没做 |
|---|---|
| 降级子阶段 `failed` → `degraded` | 会连带改变 `execute_asset_pipeline` 的聚合结论，属行为变更。**要真做，得先把"资产管线降级 = 整体失败还是降级完成"这个语义定下来**，再统一两个入口，不宜塞进推送前收尾 |
| Unreal 接续跑（`record_stage`） | 这是新功能不是修补。已把常量修对并加守卫，接的时候从对的地图出发 |
| 拆 `_execute_godot_demo_inner`（385 行）/ `execute_unreal_demo`（222 行） | 存量问题，09-08 那轮已点过名，非本轮引入。重构风险高于收益，且与本次推送内容无关 |
| 工作台工具派发改走统一 registry | 现状有双向守卫钉着（`test_workbench_tool_coverage.py`），属重复知识源但不漂。要合并工具体系时一并做 |
| CI 跑 Godot 集成测试 | CI 是 ubuntu 无 Godot，`test_gdscript_godot_check.py` 在 CI 与本地都整组 skip。**接受为本地准入门禁**；要进 CI 得先装 Godot 并暴露 `FANTASY_AGENT_GODOT_EXE` |
| 端点守卫区分 HTTP method | `test_frontend_endpoint_coverage.py` 只看路径。smoke guard 的固有限度，可接受 |

---

## 推送前判定

**可以推送。** 无 P0/P1，5 条 P2 已修且三条关键修复有变异验证背书。全部改动仍未推送，需要作者在终端执行 `git push origin main`（沙箱内无凭据）。
