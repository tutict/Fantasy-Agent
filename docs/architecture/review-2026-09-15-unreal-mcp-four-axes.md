# Unreal MCP 修复的四轴 review

日期：2026-09-15
范围：`e3d4e34`（引擎发现 + DDC 路径上限）、`df74b36`（Studio 状态面板复用 `local_tools` resolver）
方法：四路只读子 agent 并发复核（正确性 / 安全性 / 可维护性 / 测试覆盖），每条 P0–P2 结论由我逐条独立复现后才采信

## 结论摘要

| 轴 | 真缺陷 | 误报 | 无问题 |
|---|---|---|---|
| 正确性 | 1（C2） | 1（C6） | 3 |
| 安全性 | 1（S1，威胁模型下有限） | 0 | 5 |
| 可维护性 | 0 | 0 | 5（含 1 项待你定） |
| 测试覆盖 | 0 | 1（T1 定级过重） | 5 |

没有 P0。修了 3 条，另有 1 条是**修复本身引入的覆盖盲区**（见 R1）。

## 逐条

| 编号 | 轴 | 结论 | 级别 | 处置 |
|---|---|---|---|---|
| C2 | 正确性 | `_unreal_candidate_key` 取路径里**所有**数字当版本，`C:\Users\user99\UE_5.8` 键成 `(99,5,8,64)`，压过干净的 `(5,9,64)` → 双引擎机器上选到**旧版** | P1→P2 | **采纳，已修** |
| C6 | 正确性 | 面板在只有 GUI 版的机器上会显示 ready，而 commandlet 会拿裸名 `UnrealEditor-Cmd` 启动失败 | P2 | **驳回**：`tool_registry.py:454` 用同一个 `_unreal_cmd_executable(_find_unreal())` 注入 `unreal_editor_cmd`，面板与实际启动同源，不存在矛盾 |
| C1 | 正确性 | docstring 称 "preferring the newest installed engine"，而 `UNREAL_EDITOR` / PATH 命中会在版本比较前直接 return | P1→P3 | 采纳（降级）：行为本身正确（显式指定优先），仅措辞不精确，**已改 docstring** |
| C4 | 正确性 | 外移后的 DDC 路径本身没有长度校验 | P3 | 采纳：本机实测 71 字符、余量 48，且有测试兜底，**已加注释**说明边界 |
| C5 | 正确性 | DDC hash key 未做大小写归一，5 种写法得 3 个 digest | P2→P3 | 驳回：`Path` 已归一正反斜杠与冗余分隔符（实测 `C:\proj\Game`、`C:/proj/Game`、`C:\proj\Game\\` 同 digest），只剩盘符/目录名大小写，代价是重建缓存而非正确性 |
| C3 | 正确性 | 单元素列表推导写法（`for candidate in [x]`） | P3 | 驳回：可读性偏好，功能正确 |
| C7 | 正确性 | 空 `project_file` 会怎样 | — | 已核对，无问题：`_assert_unreal_project_file` 抛 `UnrealMCPSafetyError`，响亮失败 |
| S1 | 安全性 | `_program_data_dir()` 不校验 `PROGRAMDATA` 是否绝对路径；相对值按 cwd 解析，可让 cwd 里的伪造 manifest 指定任意 exe 当引擎 | P2→P3 | 采纳（降级）：威胁模型下本机用户本就能直接设 `UNREAL_EDITOR`，并非新增攻击面；但校验零成本，**已加 `is_absolute()` + 测试 + mutation** |
| S2 | 安全性 | manifest 内容被视为可信输入 | P2→P3 | 与 S1 同源，随 S1 一并收敛 |
| S5 | 安全性 | 探针用 `confirmed_side_effects=True` + `allow_execute=True` 是否绕过闸门 | — | 已核对，无问题：走同一 `combined_registry().call`，`EXECUTE` 权限与 handler 内确认检查都在。（附带发现经**复核为误判**，见文末"后续"：注册表只在模型未提供该字段时注入，模型显式发 `false` 时 handler 内那层检查**照样命中**） |
| S3 / S4 / S6 / S7 | 安全性 | 路径穿越 / 共享 TEMP / 日志含本地路径 / 硬编码密钥 | — | 已核对，无问题：hash 只含 `[0-9a-f]` 跳不出 temp 根；TEMP 按用户隔离；输出含本机绝对路径但无凭据；`grep` 无任何密钥模式 |
| M2 | 可维护性 | 实测记录文档的「改动」表列了 `generated/mutation_check_all_guards.py`，而它被 gitignore | P2→P3 | 部分成立（该文件确实被改，只是不入库），已加脚注；**后续已迁到 `scripts/` 并进版本控制** |
| M5 | 可维护性 | S1/S2 等 mutation 守卫位于 gitignored 文件，CI 永不执行 | P2 | **已处理**（见文末"后续"） |
| M1 / M3 / M6 | 可维护性 | 文档与代码一致性 / 是否存在第三份引擎搜索 / 行尾 | — | 已核对，无问题：无残留的"预期 degraded"表述；所有调用方都复用 `local_tools._find_*`；`i/lf` 无 churn |
| M4 / M7 | 可维护性 | 测试硬编码 `DerivedDataCache`；`_find_blender` / `_find_godot` / `_find_unreal` 三种风格 | P3 | 驳回：风格偏好，非代价 |
| T1 | 测试覆盖 | `test_unreal_discovery_reports_nothing_rather_than_raising` 是"静默通过" | P1→P3 | 驳回：它对**自己的声称**（坏 manifest 不抛异常）承重——补 U3 变异守卫后确认会红；它不覆盖"manifest 特性整体缺失"，而那是另一条测试的职责 |
| T6 | 测试覆盖 | 后端 `McpService.metadata` 未出现在前端类型里 | P2→P3 | 采纳：既有缺口（`metadata` 一直是后端字段），本次首次有实际内容，**已补前端类型** |
| T2 / T3 / T4 / T7 | 测试覆盖 | 隔离是否关干净 / 长路径断言是否靠运气 / DDC 三测试是否互相污染 / 相关测试是否全绿 | — | 已核对，无问题：`_find_unreal` 只有 4 个来源且 helper 全关；回退路径 71 ≤ 119 是真实校验（深 TEMP 会红而非静默）；`_local_ddc_dir` 是纯函数不写盘 |

## R1 —— 修复本身引入的覆盖盲区（本轮最有价值的发现）

修完 C2 后重跑变异校验，**U2（"a plugin row answers for an engine"）从 RED 变成 GREEN (MISSED)**。

原因：U2 的 fixture 里插件行指向 `custom/QuixelBridge_5.9`。旧版本键取路径里所有数字，插件行会以 `(5,9,64)` 压过引擎的 `(5,8,64)`，所以删掉 `ArtifactId` 过滤就会红。新的版本键只认 `UE_<ver>` 段，而 `QuixelBridge_5.9` 里没有这个形状 → 插件行版本为空元组，排到最后，**即使过滤被删也仍选对**。

**这不是覆盖退化，而是修复从另一条路径堵住了同一个洞**——但只要守卫是绿的，它就不再是守卫。处置：把插件行的安装根改成 `custom/UE_5.9`（模拟插件装在一个恰好以 `UE_5.9` 命名的根目录、且该目录里有编辑器），使其路径携带**更高**版本。这样删掉过滤后插件行会赢，U2 重新变红，同时这条测试现在同时守着"过滤"和"版本键"两件事。

这条记录也是流程教训：**改完被测代码必须重跑变异校验**，否则修复会静默废掉守卫。

## 修复清单（本次提交）

| 文件 | 改动 |
|---|---|
| `fantasy_agent/local_tools.py` | `_unreal_candidate_key` 改为只在 `UE_<ver>` 段取版本（C2）；`_program_data_dir` 拒绝相对 `PROGRAMDATA`（S1）；`_find_unreal` docstring 说明显式来源优先（C1） |
| `fantasy_agent/unreal_mcp.py` | `_local_ddc_dir` 注释写明回退路径的实测余量与"不做二次校验"的边界（C4） |
| `tests/test_unreal_mcp.py` | 新增：版本排序不受路径无关数字影响、无版本段排在其后、相对 `PROGRAMDATA` 不跟随；改 `test_unreal_is_found_through_the_launcher_manifest` 的 plugin fixture（R1） |
| `apps/frontend/src/shared/types.ts` | `McpService` 补 `metadata`（T6） |
| `docs/architecture/mcp-connectivity-2026-09-15.md` | 改动表加脚注：mutation 脚本不入版本控制（M2） |
| `generated/mutation_check_all_guards.py` | 新增 U3（manifest 容错被删）、U4（版本键退回全数字）、U5（相对 PROGRAMDATA 被跟随）。该文件随后迁至 `scripts/mutation_check_all_guards.py` |

## 后续（本轮之后的一次提交）

上面两条都已处理。

**1. mutation 守卫进版本控制并接进 CI（M5/T5）**

`generated/mutation_check_all_guards.py` → `scripts/mutation_check_all_guards.py`。原处它被 `generated/*` gitignore，所以永远不会进仓库、也永远不会在 CI 里跑。搬家后立刻暴露三件事：

- **原文件从未被 lint 过**（`ruff check` 只覆盖 `fantasy_agent tests apps scripts`，不含 `generated/`），当场 3 处报错，都修了。
- **没有引擎的机器跑不完它**。G2/G3 两条守卫在无 Godot 时被 `pytest.mark.skipif` 跳过 → runner 退出 0 → 旧判定 `caught = exit_code != 0` 会报 `GREEN (MISSED!)`，也就是**在 CI 上必然假红**。现在这两条在 `ENGINE_REQUIREMENTS` 里声明所需引擎，缺失时报 `N/A`（单独计数、显式打印）而不是失败。
- **退出码两个方向都会骗人**。节点名失效时 pytest 收集到 0 条、runner 退出 2，`exit_code != 0` 会把它读成"抓住了"——死守卫看起来是活的。判定改为读 runner 自己的计数行，`NO RUN`（收集到 0 条）与 `SKIPPED`（守卫自己跳过）都单独报为**未证明**。

**2. S5 的"第二道锁不可达"经复核不成立**

`confirmed_side_effects` 不在 `_ENGINE_HIDDEN_ARGS` 里（那里只有 `create_godot_project_structure` 的几个 spec 字段），模型看得到它、也能显式发 `false`；注册表的注入条件是 `spec.confirm_field not in args`，显式 `false` 会被原样保留，handler 里那层检查照样命中。实测：

```
A) 显式 false + allow_execute=True  -> refused  Unreal MCP blocked execution because the operation was not confirmed.
B) 省略字段 + allow_execute=True    -> error    （注入 true，真的走到 bridge 了）
C) 省略字段 + 无授权                -> refused  （权限闸门拦下）
```

`tests/test_agent_loop.py::test_an_explicit_false_stays_a_dry_run` 本来就钉着这条语义（用 `write_files`，机制相同）。所以这是**两道都活着的锁**，不是"看起来两道、实际一道"。结论：不改代码，只把记录改对。

**3. 新增 `tests/test_mutation_harness.py`**

harness 自己的失效是隐形的（针点漂了打印 SKIP、守卫改名让退出码看起来像抓住了）。8 条静态守卫在 CI 里校验它的输入，不跑任何变异。同时 harness 长出 5 条**自变异**用例（H1–H5），把这些守卫本身也钉住——用同一个机制证明它们真会红。
