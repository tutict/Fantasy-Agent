# 工具调用与引擎链路四轴 review（2026-09-14）

> **状态：1 条 P1、2 条 P2 已修；3 条经复核判为不成立或降级；其余 P3 明确不动。** 修复记录见文末。

评审对象：**本地已提交但未推送的三个提交** —— `de7e41e`（工具调用扩到三个 provider）、`a2ef985`（真机验证引擎链路 + 测试基础设施）、`c3c9d34`（ComfyUI 真机验证）。合计 13 文件，+1588/−53。

四轴沿用代码四轴（正确性 / 安全性 / 可维护性 / 测试覆盖）。本轮范围是「工具调用通道 + 引擎链路 + 测试基础设施」，所以四轴的重点分别是：三 provider 的 wire format 是否与官方契约相符、探针与测试会不会误伤真实环境、文档承诺与代码是否一致、以及**新加的守卫有没有一条是改不红的**。

**方法**：四路子 agent 并行只读评审 → 我逐条复核（本轮剔除 2 条误报）→ 关键结论用命令坐实（含给被测环境造真实对手）→ 修复后做变异验证。

---

## 四轴结论

| 轴 | 查什么 | 结论 |
|---|---|---|
| **正确性** | 三 provider 的 HTTP 契约、投影是否无损、采样参数抑制、Godot 修复是否可解析 | **1 条 P1**：`complete_json` 对 `openai_responses` 打错端点。投影经独立探针验证无损（3 轮、含并行 tool call 与文本混排） |
| **安全性** | 凭据泄漏面、探针破坏面、可执行边界、basetemp 可预测性、供应链 | 无泄漏、无路径穿越可利用面。**1 条 P2**：basetemp 秒级 stamp + `rm_rf` + 临时根上多个非管理员 SID 有写权 |
| **可维护性** | 分派对称性、命名与重复、文档自相矛盾、行尾与空白 | **1 条 P2**：`AGENTS.md` 的 provider 列表漏了 `openai_responses`，与两屏之上的说法不一致——**这正是 P1 长期没被发现的原因** |
| **测试覆盖** | 守卫是否真会红、静默 skip、环境失真、恒真空断言 | **11/11 变异全红**，没有改不红的守卫。**1 条 P2**：缺 key 那条测试只参数化 2/3 provider，第三个的缺口因此无人发现 |

**总体：1 条 P1、2 条 P2 已修，另 3 条经复核不成立或降级。**

---

## 已修的 3 条

| # | 轴 | 位置 | 问题 | 证据 |
|---|---|---|---|---|
| 1 | 正确性 | `fantasy_agent/llm.py:618` | `complete_json` 只分派 `openai_compatible`，其余全落进 anthropic 分支。把 provider 配成 `openai_responses` 再开 LLM 生成，会发 `POST https://api.openai.com/v1/messages`，头带 `x-api-key` + `anthropic-version`，body 是 `{"model": "gpt-6-astra", "system": ..., "messages": [...]}`。OpenAI 上没有该端点 → 404 → 调用方按"LLM 失败"回退确定性路径，于是**该 provider 的 LLM 生成永远不可能工作，且完全静默** | 打桩 `_post_json` 后实跑三种 provider 打印 URL/头/字段（见下方复核记录）；`api_settings.DEFAULT_BASE_URLS[OPENAI_RESPONSES] = "https://api.openai.com/v1"` 佐证 host |
| 2 | 正确性 | `fantasy_agent/llm.py:172` | `_responses_tool_turn` 缺 key 时不前置检查（另两个分支在 `:224` / `:266` 都检查），把 `Authorization: Bearer `（空值）发上线，靠 401 才失败。而 `AGENTS.md` 早已声称"任何 provider 缺 key 都抛 LLMError" | 给 `test_a_missing_key_is_a_loud_failure_not_a_degraded_run` 补上 `OPENAI_RESPONSES` 参数即变红（`AssertionError: the code under test sent more requests than the test queued`） |
| 3 | 安全性 | `scripts/run_tests.py:137` | run 目录名用秒级 UTC stamp。pytest 的 `TempPathFactory.getbasetemp` 在传入路径已存在时执行 `rm_rf(basetemp)`（`_pytest/tmpdir.py:154-159`），同秒启动的两个 run 会互删。**注意这是上一轮修复的副作用**：目录原先在仓库内，护栏会拦住该删除（响亮失败）；搬到 OS 临时根后护栏豁免，删除会**静默成功**。实测 `%TEMP%` 的 ACL 上有三个非管理员 SID 与 `CodexSandboxUsers` 持有 `(OI)(CI)(M)` | `sed -n '145,159p' .venv/Lib/site-packages/_pytest/tmpdir.py`；`icacls $LOCALAPPDATA\Temp` |

三条都补了守卫并做完变异验证（见「变异验证」）。

---

## 复核记录：判为不成立 / 降级接受

子 agent 报了、我查完认为不该按原级别处理的。留档以免下次重复排查。

| 原指控 | 复核结果 |
|---|---|
| `_anthropic_tool_turn` 用 `model_name()`，另两处用 `str(resolved["model"])`，取值方式不一致 | **不成立**。`resolve_credentials()` 在 `api_settings.py:230-234` 有 `DEFAULT_MODELS[provider]` 兜底，`resolved["model"]` 永非空串，两者实际等价 |
| `_message_block_text` 只认 `output_text`/`text`，不认 `input_text` | **降级 P3，不改**。该分支要求 content 是 list，而 `agent_loop.py:115` 的首条消息是纯字符串 `{"role": "user", "content": goal}`，当前不可达；将来 loop 改动才需要补 |
| `test_known_without_ui_has_no_stale_entries` 遍历空字典，循环体永不执行，是恒真空守卫 | **确认现象，但不算问题**。`KNOWN_WITHOUT_UI = {}`（`tests/test_workbench_tool_coverage.py:26`）确实让循环体今天跑不到，但它守的是"将来有人加了条目又忘了标注"——条目一存在就能红，且同文件的 `test_backend_tools_are_reachable_from_the_ui` 才是今天活着的守卫。保留 |
| `verify_engine_links._resolve` 与 `--workspace` 可把输出带出仓库 | **降级 P3，不改**。实测 `--workspace ../../../escape` → `C:\Users\escape`。这是用户给自己传参，且探针本来就允许写到任意 workspace（写 `generated/` 只是默认）。真实写入路径由 `BaseMCPBridge` 的 `path_safety.resolve_workspace_path` 钉在 workspace 内，与探针的只读 `.exists()` 判定无关 |
| `AGENTS.md` 里写死 `D:\Comfy-Desktop\...` 属个人机器状态进共享文档 | **部分采纳**。绝对路径是这条指令可复现的全部价值，删掉就没用了；但确实会让人误以为是通用指令。处理方式 = 保留路径 + 明说"是本机路径，换机要改"（`b809d12`） |
| `temperature` 门控代码在三处字面重复 | **P3 不改**。三行同形常量，抽出来反而要多一层间接 |

---

## P3：明确不动的

- `scripts/run_tests.py` 里三连空行 → 已顺手改成两行（ruff 默认规则集不含 E303，lint 不会报，但空白问题该顺手清）。
- `tests/test_godot_mcp.py` 末尾多一个空行 → 已清。
- `tests/test_workbench_tool_coverage.py:119` 的 `{step.status} <= {"ok","refused","error"}` 是弱断言（超集判定，几乎恒真）。保留：真正的判定在紧随其后的 `probe_comfyui_capabilities["status"] == "unavailable"`。
- `tests/test_godot_mcp.py` 里 `from test_gdscript_godot_check import _godot_exe` 依赖 rootdir 的 sys.path 注入。可接受（同目录测试互相引用在本仓库是既有做法），且它在无 Godot 的机器上会 skip 而不是报错。
- 探针 `call(label, name, ...)` 的 `label` 与 `name` 是同一个字符串。冗余但无害，动它会牵连 `step.label == TOOLS` 那条断言。

---

## 变异验证（确认守卫真会红，不是假绿）

`generated/mutation_check_all_guards.py` 扩到 11 条，**11/11 全红，每个源文件逐字节还原**：

| 编号 | 变异 | 结果 |
|---|---|---|
| G1/G2 | `main.gd` 改回 `HANDOFF["gameplay"]`（文本断言 / 真 Godot 各一条） | RED |
| G3 | Godot 守卫模块只看 PATH | RED |
| R1/R2 | run 目录挪回仓库 / 父目录不再创建 | RED |
| R3 | **新** run id 去掉唯一性 | RED |
| P1/P3/P2 | 探针工具名失效 / `_resolve` 不拼 workspace / 探针不再授权 write | RED |
| L1 | **新** `complete_json` 的 `openai_responses` 守卫失效（落进 anthropic 分支） | RED |
| L2 | **新** `_responses_tool_turn` 去掉缺 key 检查 | RED（3 个参数化里红 1） |

**过程中发现并修掉一个假信号**：`.gitattributes` 是 `* text=auto`（index 一律 LF），工作区里多数文件是 CRLF，但 `tests/test_run_tests_runner.py` 是 LF。R2/P1/P2 三条针点写的是 `\n`，对 CRLF 文件**静默失配**，于是被报成"没抓住"——三条活得好好的守卫被误判为死的。加了 `_as_eol()` 让针点跟随文件真实行尾。**教训：变异脚本报 SKIP 就是针点错了，不是守卫坏了。**

---

## 数字

- 后端：**529 passed / 0 failed / 0 skipped**（原 524，新增 5 条：缺 key 补第 3 个 provider、`complete_json` 拒绝、两个 provider 的生成路径回归、run id 唯一性）
- 全量连跑 3 次（修复前）均 524 全绿、护栏零命中；修复后 529 全绿
- ruff：`All checks passed!`（`fantasy_agent tests apps scripts`）
- 前端：typecheck 通过、67 tests 通过、build 通过（本轮未改前端，跑一遍确认没被牵连）
- 依赖：`git diff origin/main..HEAD -- pyproject.toml package.json package-lock.json` 为空，无新增依赖；`pip install --dry-run -e ".[dev]"` 可解
- 独立探针（我自己写的，非子 agent 的）：3 轮含并行 tool call 与文本混排的转录，两张投影的角色交替、`tool_result` 配对、`tool_call_id` 配对、`arguments` 保持 JSON 字符串——全部通过
- 降级守卫的承重性：在 8188 起假 ComfyUI 应答 `/system_stats` `/object_info` `/models/checkpoints`，测试仍绿（stub 有效）；摘掉 stub 后 `assert 'ready' == 'unavailable'` 变红（stub 承重）

---

## 修复记录

- `dc5b9e0` **Refuse the Responses provider in the JSON path instead of posting an Anthropic body** — 6 文件 +117/−6
  `fantasy_agent/llm.py`、`scripts/run_tests.py`、`tests/test_llm_tool_calling.py`、`tests/test_run_tests_runner.py`、`tests/test_workbench_tool_coverage.py`、`tests/test_godot_mcp.py`
- `b809d12` **Say what the generation path actually supports** — 2 文件 +7/−7
  `AGENTS.md`、`scripts/verify_engine_links.py`（docstring）

`main` 领先 `origin/main` 5 个提交，**未推送**（沙箱内 GCM 读不到凭据，推送需在终端自己跑）。

---

## 未做（明确交代）

- **P1 的修法是"显式拒绝"，不是"把 Responses API 接进生成路径"**。理由是后者要新增一条无法用真实 key 验证的 wire format 分支。代价：把 provider 配成 `openai_responses` 就无法使用 LLM 生成（会拿到明确报错并回退确定性路径）。**要做的话是一份独立工作**：仿 `complete_with_tools` 的 `/v1/responses` 分支加 `_complete_openai_responses`，约 40 行 + 打桩测试。
- **缺 key 前置检查会改变"无 key 的本地网关"行为**。如果某人的 `openai_responses` 指向一个不需要鉴权的本地 `/responses` 实现，现在会被拦下。这种用法可以改用 `openai_compatible`，但我没有实际见到，属纸面权衡。
- **basetemp 的抢占风险只做了加固，没有做隔离**。加了 pid + 随机后缀使同机并发不再互删；`%TEMP%` 上其它 SID 有写权这一点是 Windows 用户临时目录的既有属性，未做权限收紧。
- **探针的 `--workspace` 仍允许指向仓库外**（P3，理由见复核记录）。
- **Unreal 链路仍未真机验证**，本机没装；`execute_unreal_demo` 的续跑也仍未接线。
- `scripts/verify_engine_links.py` 的 label/name 冗余未动（P3）。

---

## 推送前判定

**可以推送。** 无 P0；唯一 P1 已修并有守卫钉住；三 provider 的 tool calling 通道与两条真机引擎链路上轮已验证；529 全绿、lint 干净、11/11 变异全红。
