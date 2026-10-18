# 后端四轴 review（2026-10-17）

> **状态：1 条 P1、2 条 P2、3 条 P3。P1/P2 均已独立复现。** 本轮只读，不改产品代码。

范围：`fantasy_agent/`、`apps/studio/`（Python 后端与桌面外壳）、`scripts/`、`mcp/`、`tests/`。**不含前端**（`apps/frontend/`）。
方法：全量 pytest + `ruff check` 取基线 → 逐模块只读走查（重点：执行闸门、路径、状态机、LLM 分派、编排/快照恢复）→ 每条结论独立复现（py-spy 栈采样、A/B 对照脚本、单测最小复现）。

## 四轴结论

| 轴 | 真缺陷 | 已复核无问题 |
|---|---|---|
| 正确性 | 2（C1、C2） | 执行/续跑状态机、编排门控、spec 校验、GDScript 转义 |
| 安全性 | 1（S1） | 执行闸门、任意二进制、路径穿越、凭据掩码、仅监听 127.0.0.1 |
| 可维护性 | 2（M1、M2） | 单一真相源、注释与代码一致、无 TODO/死代码 |
| 测试覆盖 | 3 处缺口（T1–T3，各对应上面一条） | 变异守卫、双向守卫、隔离守卫 |

没有 P0。

## 逐条

| 编号 | 轴 | 结论 | 级别 | 处置 |
|---|---|---|---|---|
| T1 | 测试覆盖 / 隔离 | 一个桌面外壳测试真的启动 pystray 图标线程且不停，装了 `desktop` extra 的机器上**整个 pytest 进程在退出时永久挂死**；CI 装的是 `.[dev]`，结构上看不到 | P1 | 建议修 |
| C1 | 正确性 / 测试覆盖 | `complete_json` 的 `openai_compatible` 分支无条件发送 `temperature`，违反 AGENTS.md 写死的全局规则；连接探测不带该字段，于是 o 系列模型能“测试连接成功”却在每次生成时静默回退 | P2 | 建议修 |
| S1 | 安全性 / 正确性 | `pipeline_state.state_path` 与执行器的 session 目录拼接**未过 `assert_safe_path_segment`**（编排快照与人工决策两条路径都过了）。Windows 上 `victim.` 折叠到 `victim`，续跑可能按**别的 session** 的成功记录跳步 | P2 | 建议修 |
| M1 | 可维护性 | `orchestrator.READY` / `RUNNING` 被导出但任何代码路径都不产出（一趟同步推进，不存在“运行中”态） | P3 | 记录 |
| C2 | 正确性 | `approval_manifest._match_keys` 用裸 stem 匹配，`generated/assets/hero.glb` 的批准会顺带命中 `generated/assets/backup/hero.glb` | P3 | 记录 |
| M2 | 可维护性 | `_ORCHESTRATION_SESSIONS` 与 `InMemoryJobRegistry._jobs` 只增不删，长跑 Studio 会持续增长 | P3 | 记录 |

---

## T1（P1）——桌面外壳测试泄漏 pystray 非守护线程，套件在退出时挂死

**现象**：`python scripts/run_tests.py`（以及 CI 用的 `python -m pytest`）在**所有测试通过之后**不再返回。junit 报告已经写完、pytest 自己的汇总行也打印了，进程却停在解释器退出阶段。

**根因**（py-spy 栈采样，非推断）：

```
Thread 22384 (idle): "Thread-2 (<lambda>)"
    _mainloop (pystray\_win32.py:147)
    _run (pystray\_win32.py:128)
    ...
Thread 27192 (idle): "MainThread"
    _shutdown (threading.py:1624)
```

主线程卡在 `threading._shutdown`，等的是一个 **非守护** 的 pystray 消息循环线程。该线程由 `tests/test_desktop_launcher.py:552`
`test_the_tray_is_handed_to_webview_start_as_the_startup_hook` 启动：

1. 测试把 `webview.start` 换成会**立即调用 startup 钩子**的桩；
2. 钩子 `desktop.open_window` 的 `_start_tray()` 调 `TrayController.setup(window)`；
3. 该 venv 装了 `desktop` extra，于是 `import pystray` 成功，`Icon(...).run_detached()` 真的起了一条 Win32 消息循环线程；
4. `webview.start` 桩立刻返回，`open_window` 的 `finally: controller.request_quit()` 紧接着就调 `Icon.stop()`——**但此时线程还没进消息循环**，`stop()` 是空操作（实测：`run_detached()` 后立刻 `stop()`，线程仍在，进程挂死；`sleep(0.5)` 后再 `stop()`，线程正常退出）。

**为什么 CI 抓不到**：`.github/workflows/ci.yml` 的后端 job 装 `.[dev]`（不含 `pywebview`/`pystray`）。没有 pystray 时 `setup()` 抛 `ImportError`，被 `_start_tray` 的 `except Exception` 吞掉，测试照样绿。`release.yml` 装 `.[desktop]` 但不跑测试。也就是说**只有装了桌面 extra 的开发机/打包环境**会中招，而 CI 永远绿。

**复现**（本机 venv 已装 pystray）：

```
.\.venv\Scripts\python.exe scripts\run_tests.py tests/test_desktop_launcher.py -k startup_hook
# 测试全部通过后不返回；py-spy dump 显示 pystray _mainloop 线程
```

**建议**：让该测试不去驱动真实的 `TrayController.setup`（同文件 `test_a_failing_tray_does_not_take_the_window_down_with_it` 已经用了“monkeypatch `TrayController.setup`”的写法），或在 `finally` 里等线程真正起来再 `stop()`。无论哪种，守卫都应能在一个**装了 extra** 的环境里跑完并退出——这正是 CI 覆盖不到的那一半。

**测试覆盖缺口（T1 的根）**：没有任何测试断言“测试套件在装了 `desktop` extra 时也能正常退出”。`tests/test_test_isolation.py` 只扫 `importlib.reload`，扫不到线程泄漏。

---

## C1（P2）——生成路径对不支持采样参数的模型仍发送 `temperature`

AGENTS.md 把这条写成全局规则：「`api_settings.supports_sampling_params(model)` 在构造 payload 前判断，gpt-6 / o 系列一律不带采样参数」。工具调用路径确实照做了（`llm.py:202/244/288`，`tests/test_llm_tool_calling.py` 钉着），**但 `complete_json` 的 `openai_compatible` 分支没有**：

```python
# fantasy_agent/llm.py:733  _complete_openai_compatible
payload = {
    "model": model,
    "max_tokens": max_tokens,
    "temperature": temperature,   # 无条件
    "messages": [...],
}
```

**实测**（把 `_post_json` 换成捕获桩，配置 `provider=openai_compatible, model=o3-mini`）：

```
provider: openai_compatible model: o3-mini
url: https://example.invalid/v1/chat/completions
payload keys: ['max_tokens', 'messages', 'model', 'temperature']
temperature present: True
```

**后果**：o 系列模型（`UNSAMPLED_MODEL_PREFIXES` 里明确列了 `o1/o3/o4`）走 `openai_compatible` 网关时，请求会被硬拒（不是忽略），`complete_json` 抛 `LLMError`，调用方**静默回退确定性生成**——用户只看到“LLM 好像没用上”。

**更糟的是探测与生成不一致**：`api_settings._probe_payload` 的 openai 兼容分支只发 `model/max_tokens/messages`，**不带 temperature**。于是一个拒绝 temperature 的模型能通过“测试连接”，却在每次真实生成时失败——正是 `llm.py` 模块 docstring 想避免的“UI 报成功、生成静默回退”。

**建议**：`_complete_openai_compatible` 用 `supports_sampling_params(model)` 决定是否带 `temperature`（与工具路径同一处判断），并给生成路径补一条与 `test_gpt6_never_receives_temperature` 对偶的测试。

**测试覆盖缺口（C1 的根）**：`tests/test_llm_tool_calling.py` 只覆盖工具调用路径的采样参数；生成路径没有任何“不支持采样的模型不带 temperature”的断言，也没有“探测体与生成体对采样参数一致”的断言。

---

## S1（P2）——执行器把 `session_id` 直接拼进路径，未过名字校验

AGENTS.md 的规则：「`session_id` / `engine_key` 进路径前必须过 `path_safety.assert_safe_path_segment`」，并点名 `orchestration_state.state_path` 对两者都调用。**但 `pipeline_state.state_path` 没调**，而它正是执行器续跑读写的那个文件：

```python
# fantasy_agent/pipeline_state.py:282
def state_path(session_id, *, engine_key="godot", workspace_root):
    relative = f"generated/{engine_key}/sessions/{session_id}/{STATE_FILENAME}"
    return resolve_workspace_path(relative, workspace_root=workspace_root,
                                  required_prefix=f"generated/{engine_key}")
```

同一处缺口还在 `executor._session_project_dir`（`executor.py:154`）与 `executor._unreal_session_project_dir`（`executor.py:1431`）。`session_id` 是调用方可控的：`ExecuteDemoRequest.session_id`（`apps/studio/app/main.py:152`，无校验）与 CLI `--session-id` 都直达这里。

**A/B 实测**：

```
pipeline_state.state_path              'victim.'                            -> ACCEPTED
pipeline_state.state_path              'victim '                            -> ACCEPTED
pipeline_state.state_path              'a\n2026-01-01 INFO root: forged'    -> ACCEPTED
orchestration_state.state_path         'victim.'                            -> WorkspacePathError
orchestration_state.state_path         'victim '                            -> WorkspacePathError
human_decision.decision_record_path    'victim.'                            -> WorkspacePathError
```

`resolve_workspace_path` 挡不住这个：它只拒绝 `..` 与绝对根，**看不见 Windows 的尾点/尾空格折叠**——`victim.` 与 `victim` 是同一个目录。`tests/test_orchestration_state.py::test_the_two_ids_windows_would_collapse_really_do_collapse` 已经证明了这个前提本身成立。

**后果**：`session_id="victim."` 的续跑会读到 `session_id="victim"` 的 `_pipeline_state.json`，`_resume_skip` 据此跳过 `victim.` 从未成功过的阶段——「续跑不能掩盖失败」这条保证被绕过；项目文件也会写进同一个目录、覆盖另一个 session。

**建议**：`pipeline_state.state_path` 与两个 `*_session_project_dir` 都按既有约定调 `assert_safe_path_segment`（`engine_key` 同理），并补一条与 `test_orchestration_state` 对偶的守卫。

**测试覆盖缺口（S1 的根）**：`tests/test_studio_app.py:2194` 只对**编排**端点验证了敌意 id；执行器路径（`/api/execute`、`--session-id`）没有任何“不能当目录名的 id 被拒”的断言。

---

## M1（P3）——`READY` / `RUNNING` 是导出但永不产出的状态

`orchestrator.py:91-92` 定义、`STAGE_STATUSES` 收录、`__all__` 导出，但 `_advance`/`_dispatch` 只会产出 `BLOCKED / AWAITING_HUMAN / AWAITING_CONFIRMATION / DONE / FAILED`（一趟同步推进，没有“运行中”这个可观测态）。全仓 grep 只有定义与导出命中。前端若照 `STAGE_STATUSES` 渲染，会画出永远不会出现的状态。建议删掉，或在 docstring 里说明它们是为将来的异步推进预留。没有任何测试把“状态词汇表”钉到“实际会产出的集合”上。

## C2（P3）——批准清单按裸 stem 匹配，可能跨目录误批

`approval_manifest._match_keys` 把 `Path(x).stem` 也放进匹配键：

```
decision keys  for generated/assets/hero.glb:        ['generated/assets/hero.fbx', 'generated/assets/hero.glb', 'hero']
exported keys  for generated/assets/backup/hero.glb: ['generated/assets/backup/hero.fbx', 'generated/assets/backup/hero.glb', 'hero']
intersection: {'hero'}
```

即对 `generated/assets/hero.glb` 的批准也会命中同名不同目录的 `generated/assets/backup/hero.glb`。当前 Blender 导出路径扁平、且 `artifact_identity` 通常兜底，实际风险低；但“同名不同目录”一旦出现，批准会越界。建议把 stem 匹配限制在同目录内，或仅在双方都无路径分隔符时生效。

## M2（P3）——会话/任务注册表只增不删

`apps/studio/app/main.py` 的 `_ORCHESTRATION_SESSIONS` 与 `fantasy_agent/studio_jobs.py` 的 `InMemoryJobRegistry._jobs` 都只增不删。Studio 是本地长跑进程，反复跑编排/任务会让这两个 dict 持续增长（内存，不是正确性）。可接受，但值得记一笔；若要收口，加一个按 `updated_at` 的 TTL 即可。

---

## 复核记录：查过、判为无问题或不成立

- **执行/续跑状态机**：`_resume_skip = stages_before ∩ done_stages ∩ RESUMABLE_STAGES`，失败/未跑过绝不跳过；`DONE_STATUSES={"done"}`，`degraded` 不会被误当完成；未知阶段名 `raise` 而非静默全量重放。`GODOT_STAGE_ORDER`/`UNREAL_STAGE_ORDER` 都有“成员+顺序”守卫。
- **编排门控**：`_advance` 先判 `depends_on` 再判 human/confirmation（“让用户批准看不见的东西”这一坑被显式挡住）；`confirmed` 恢复必须走 `confirm()`，`human_resolution` 由 `_stamp_plan` 无条件对齐到 map（不 overlay），快照存 plan。`tests/test_orchestrator.py` + 变异 B2/B4 钉着。
- **执行闸门**：`ToolRegistry.call` 按 tier 拒绝；`_call_arguments` 对隐藏参数“先丢再填”、对可执行文件强制覆盖；`exposed_executable_args()` 有测试断言为空。
- **路径**：`resolve_workspace_path` 覆盖 `..`/绝对根/`/etc/passwd`（Windows 无盘符绝对路径）；`mcp_bridge` 四处桥统一走它。`corrections.py` 刻意用 `display_workspace_path` 避免在 HTTP 响应里泄露绝对路径。
- **凭据**：`public_settings` 只回掩码；`resolve_credentials` 优先级明确；`test_connection` 永不抛。
- **LLM 分派**：`openai_responses` 跑生成会**明确报错**，不会把 Anthropic 形状的请求体发到 OpenAI 主机；缺 key 在三个 provider 上都响亮失败。
- **仅监听本地**：`desktop.py` / `start-fantasy-agent.ps1` 全部 `--host 127.0.0.1`；无 `0.0.0.0`。
- **`api_settings.public_settings` 回传绝对 `config_path`**：与 `corrections.py` 的口径不一致，但前端 `ApiSettingsPanel` 正是要用它显示“密钥存在哪”，属有意为之，**不按缺陷计**。
- **无 TODO/FIXME、无可变默认参数、生产代码无 `assert`**（grep 全仓）。
- **`ruff check .`**：All checks passed。

## 数字

| 项 | 值 |
|---|---|
| 后端 pytest（`scripts/run_tests.py`） | **928 passed, 0 failed, 0 errors, 0 skipped**（90.08s） |
| `ruff check .` | All checks passed |
| 本轮新增文件 | 仅本 review |

## 修复（2026-10-18，复审通过后提交）

上表是**只读 review 轮**的基线。三条「建议修」的修复落在另一轮，逐条：

| 编号 | 处置 | 落在哪 |
|---|---|---|
| T1 | startup-hook 测试改为桩 `TrayController.setup`（改为记录传入的窗口，原断言「钩子用它拿到的窗口建托盘」保留）；另加模块级 autouse 守卫——任何测试留下非守护线程即红，消息点名线程名 | `tests/test_desktop_launcher.py` |
| C1 | `_complete_anthropic` 与 `_complete_openai_compatible` 都用 `supports_sampling_params(model)` 门控 temperature，与工具路径同一处判断；补 3 条对偶测试（o 系省略 / 采样模型保留 / anthropic 保留） | `fantasy_agent/llm.py`、`tests/test_llm_generation.py` |
| S1 | `state_path`（session_id + engine_key）、`_session_project_dir`、`_unreal_session_project_dir`、`godot_playtest._session_dir_name` 全部过 `assert_safe_path_segment`（具体报错消息保持在前，`..`/`a/b` 的文案不变）；新增 `demo_launch.validate_session_id`，在 `/api/execute` 边界与 `launch_demo` 内部两层拒绝；补 3 条守卫 | 5 个源文件 + 3 个测试文件 |

**复审记录（2026-10-18）**：每条修复的声称均已复跑；三条新守卫各做一次「改坏→红→还原」探针——摘 llm 门控→omit 测试红；摘 `state_path` 校验→pipeline 守卫红（端点测试仍绿，它的 400 来自边界层，两层独立）；摘 startup-hook 的桩→线程守卫红**并复现退出挂死**（实测泄漏两条线程：`setup_handler` 与 pystray 的 `<lambda>`，比本文档记录的还多一条）。全量 **933 passed**（928 + 新 5）、`ruff check .` clean、runner 干净退出（修 T1 前它在装了 desktop extra 的机器上挂在退出阶段）。

## 未做（明确交代）

- **未跑 `scripts/mutation_check_all_guards.py`**。它逐个变异源码再跑守卫，中途被杀会**把变异留在工作区**（harness docstring 自己警告过），在本轮时间盒里风险高于收益。上面每条 P1/P2 都用独立复现（栈采样 / A/B 脚本 / 最小单测）替代了“变异证明”。
- **未在前端侧做任何事**（按范围排除）。
- **环境注记**：本机 Codex 沙箱会让 `mkdir(mode=0o700)` 建出的目录不可 `scandir`，而 pytest 的 `TempPathFactory` 正是这么建 basetemp 的——沙箱内跑会得到 384 条 `PermissionError` 的假 `failed on setup`。这是**沙箱**问题不是仓库问题，全量测试是在沙箱外（escalated）跑的；`scripts/run_tests.py` 本身的设计（basetemp 落在 OS 临时根）是对的。
- 复核期间为取栈临时 `pip install` 了 `py-spy`（venv 内，仓库已 gitignore）；卸载时被沙箱拦下，未成功移除，**不影响仓库**。
