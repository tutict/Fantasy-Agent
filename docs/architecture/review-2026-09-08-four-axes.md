# 四轴代码评审报告

**日期**：2026-09-08
**范围**：`fantasy_agent/` 全部 37 个模块（16179 行）+ `apps/studio` 请求层
**四轴**：正确性 · 安全性 · 可维护性 · 测试覆盖
**基线**：267 passed，ruff 全过
**方式**：四路并行评审，每条结论经人工复核（剔除 1 条误报）

---

## 结论先行

**没有 P0**（无需授权即可利用的漏洞）。核心安全设计扎实：全仓 0 处 `shell=True`、无 `eval/exec` 喂模型输出、凭据全程掩码、权限闸门双重生效。

但有两条必须尽快处理：

| 优先 | 问题 | 为什么急 |
|---|---|---|
| **1** | 模型可控可执行文件路径（`blender_executable` / `godot_executable` / `unreal_editor_cmd`） | 勾了 `allow_execute` 就等于允许执行任意本地二进制。而"勾执行授权"是这个功能的**正常用法**，不是异常条件 |
| **2** | Studio 请求模型继承普通 `BaseModel`（`extra="ignore"`） | 这是已经栽过两次的真实 bug 的**根因**，不修还会栽第三次 |

另外测试有 3 处"假绿"——绿不代表对。

---

## 轴一：正确性

| 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|
| P1 | `executor.py:989-995` | `except Exception: pass` 吞掉审批清单的加载与合并异常。若 YAML 损坏或 sync 逻辑抛错，用户**已批准的资产会静默不并入**，关卡继续以灰盒跑，调用方毫不知情。注释说"approval_gate 阶段会报告"，但该 except 已先于阶段合并阻断了 sync，资产根本没进来 | 区分"文件缺失（可忽略）"与"解析/合并失败（必须显式失败或计入 stage）"；至少 `logger.warning` |
| P1 | `apps/studio/app/main.py:16,86,94,100,107,112,119,126,1083` | 所有请求模型继承 `BaseModel`，默认 `extra="ignore"`。前端多传的未知字段被 FastAPI **静默丢弃、不报错**——这正是"传了 kwarg 但模型没加字段"两次事故的土壤 | 改继承 `contracts.StrictModel`（`extra="forbid"`），把字段漂移变成 422 而非静默丢失 |
| P2 | `comfyui_mcp.py:382-386` | `except Exception: continue` 无日志。端点因瞬断还是本就不可用，无法分辨 | 至少 `logger.debug` |

### 已剔除的误报

- ~~`validate_contract_refs()` 全库无调用方~~ —— **不实**。经核实 `tests/test_agent_loop.py:106` 与 `:127` 均有断言，契约引用是有测试守着的。

---

## 轴二：安全性

### P1（最该修的一条）

**模型可控可执行文件路径 → 以本进程权限执行任意二进制。**

已实测确认，字段确实暴露在给模型的 schema 里：

```
generate_asset_batch : ['plan', 'script_path', 'import_manifest_path',
                        'blender_executable', 'timeout_seconds', 'confirmed_side_effects']
run_godot_import     : ['project_file', 'godot_executable',
                        'timeout_seconds', 'confirmed_side_effects']
```

而 `blender_mcp.py:107` 直接把它作为 `command[0]`：

```python
command = [request.blender_executable, "--background", "--python", ...]
```

同类问题在 `godot_mcp.py:181`、`unreal_mcp.py:378/479/574`，契约字段见 `contracts.py:533/650/658/768`。

**攻击链**：勾 `allow_execute` → 注册表自动注入 `confirmed_side_effects=true`（这是我们自己的设计）→ 模型传 `blender_executable="C:/evil.exe"` → 直接执行。脚本内容是确定性模板没错，但**执行档本身已经变异成"运行任意程序"**。

**修法（与现有架构对齐，改动很小）**：复用 `plan_key` 已有的隐藏+注入机制，把 `*_executable` 从 schema 摘掉，改由注册表用 `local_tools._find_blender()` / `_find_godot()` 的探测结果注入。模型只该决定"跑不跑"，不该决定"跑哪个程序"。

### P2

| 位置 | 问题 | 建议 |
|---|---|---|
| `blender_mcp.py:236`、`unreal_mcp.py:1226`、`comfyui_mcp.py:469` | 三份自造的 `_resolve_workspace_path` 比 `path_safety` 弱。blender 版**只做 `relative_to`**，不拒绝对路径、不拒 `..`、无 `required_prefix` | 统一改用 `path_safety.resolve_workspace_path`（见轴三，一并修） |
| `agent_loop.py:86/113`、`__main__.py:173` | `workspace_root` 未校验，可设为 `/` 或 `C:\` | 禁止文件系统根，限制在仓库/用户目录内 |

### 确认干净的攻击面

- **命令注入**：全仓 0 处 `shell=True` / `os.system` / `os.popen`，全部是参数列表 `Popen([...])`
- **LLM 输出当代码执行**：`blender_codegen.py` 生成的是固定模板（内嵌 JSON 化 plan，非自由代码），GDScript 只在 Godot 引擎内解释
- **凭据泄露**：`mask_secret` 掩码完备，异常只回显响应体片段，配置写盘 `chmod 0o600`
- **闸门绕过**：即使绕过 `ToolRegistry.call` 直接调 `call_*_mcp_tool`，各 bridge 仍各自校验确认位并返回 `blocked`——纵深防御有效

---

## 轴三：可维护性

### P1：四个 `*_mcp.py` 大量逐字重复

`_resolve_workspace_path` 定义了四遍（`blender:236` / `comfyui:469` / `godot:400` / `unreal:1226`），`_run_tool`（blender:244 / godot:406 / unreal:1234）、`_write_text`、`call_*_mcp_tool` 的 if/elif 派发骨架、`_error` 返回、`_content_summary` 全部雷同。

**成本**：改路径规则要在 3–4 处同步，漏一处就行为漂移——而漂移已经发生了（blender 版校验最弱，见轴二）。

**建议**：抽 `BaseMCPBridge`，路径统一走 `path_safety`，`_run_tool` / `_write_text` / `display_path` 提为基类方法，`call_*_mcp_tool` 改注册表式派发。**一个改动同时收掉可维护 P1 和安全 P2。**

### P2

| 问题 | 位置 |
|---|---|
| 超长函数：`_execute_godot_demo_inner`(368行)、`prepare_production_pipeline`(355)、`_build_task_breakdown`(301)、`_level_assembly_script`(236)、`execute_unreal_demo`(219) | `executor.py:875` `workflows.py:555` `workflows.py:963` `unreal_mcp.py:1562` `executor.py:1288` |
| 阶段名字符串在 executor 散写约 30 处，与 `pipeline_state.GODOT_STAGE_ORDER` 是两套知识源 | executor 各处 |
| `GODOT_STAGE_ORDER` 守卫**只单向**：`test_pipeline_state.py:184` 只断言"产出 ⊆ 元组"，删掉 executor 某阶段后元组冗余项无人捕获 | `tests/test_pipeline_state.py` |
| 日志目录 `generated/logs/<engine>` 在四个 `_log_paths` 硬编码 | comfyui:479 / blender:282 / godot:444 / unreal:1272 |

### 确认干净

- **无循环 import**，依赖图是 DAG，`contracts.py` / `path_safety.py` / `process_runner.py` 为叶子
- **工具注册表确为唯一真相**：`engine_registry()` 完全由各 `tool_descriptors()` 派生，权限由 `permission_from_annotations()` 单一出处推导，无第二份手写清单——AGENTS.md 的描述属实

---

## 轴四：测试覆盖

267 全绿，但有几处绿得没道理。

### P1

| 位置 | 问题 | 建议 |
|---|---|---|
| `tests/test_studio_app.py:79-85` → `local_tools.py:34` | `correction_targets()` 会发**真实** `urlopen("http://127.0.0.1:8188/system_stats")`，`manual_correction_targets` 会做真实 `shutil.which` + `glob("C:\Program Files\...")`。测试只断言 `"godot" in target ids`，status 无关 → **永远绿** | monkeypatch `_http_json` 与 `_find_*`，分别断言 ready / degraded 两种 status |
| `path_safety.py:38` | 绝对路径拒绝分支**零覆盖**（全库 grep `is_absolute` 在 tests/ 无命中）。而它是 6 个调用方的唯一防线 | 新增 `tests/test_path_safety.py`，直测绝对路径 / `..` / `required_prefix` / Windows `\` 归一化 |
| `tests/test_studio_app.py:210,248,368,401,501` | 5 处 `monkeypatch` 打在**私有函数** `_build_execution_result` 上，跳过 preflight→executor→registry 的真实装配。其内部编排变了测试还绿 | 至少留一条走真实 `_build_execution_result`，只把最外层 runner/bridge 换成 fake |

### P2

- `blender_runtime.py:155` `run_blender_asset_plan` 零覆盖——但 `bpy` 是作为参数注入的（`:181,:188`），完全可用 fake `bpy` 测
- `contracts.py` 有 124 处 `ge/le/Literal` 约束，只有 1 个边界测试（`test_production_specs.py:100`）。契约是 LLM 输出的唯一守门人
- 无 `conftest.py`；`llm.py:77` 的全局 `_client` 靠 `test_llm_generation.py:40` 的 `importlib.reload` 隔离，制造顺序耦合
- 弱断言：`test_studio_app.py:388`、`test_studio_jobs.py:129`、`test_preflight.py:180`

### 覆盖缺口（按风险×缺口排序）

| 模块 | 行数 | 测试状况 |
|---|---|---|
| `blender_runtime.py` | 792 | 仅 `build_import_manifest`，15+ 个 bpy 函数零覆盖 |
| `local_tools.py` | 383 | 无直接测试，`_find_*` 零断言 |
| `i18n.py` | 459 | 零直接测试 |
| `contracts.py` | 1054 | 无专属文件，124 处约束仅 1 例边界 |
| `path_safety.py` | 54 | 无直接测试，绝对路径分支零覆盖 |

### 做得好的地方（不凑数）

- **权限闸门 32 个测试极为扎实**：拒绝而非抛异常、schema 天花板、三档拒绝、注册期非法 tier、confirm 仅授权时注入、显式 `False` 保持 dry-run、annotations→tier 映射——全项目最稳的部分
- **LLM 降级路径用 `side_effect=AssertionError("must not call")` 反向证明**默认路径不碰 LLM，是好模式
- **`pipeline_state.py` 14 例完整**：failed 永不算 done、未跑过不跳、未知 target 不跳、损坏文件降级、create/validate 不可续跑
- **preflight 分层清晰**，blocking 与 warning 分开断言，且参数化保证每条 blocking 都带 rework target
- 一致使用 `tmp_path`，无 `os.chdir`；网络统一 mock 在 `urllib.request.urlopen` 边界

---

## 建议的处理顺序（按 ROI）

| # | 事项 | 收益 | 改动量 |
|---|---|---|---|
| 1 | 把 `*_executable` 从模型 schema 摘掉，改由注册表注入 | 消除 RCE | 小（复用 plan_key 机制） |
| 2 | Studio 请求模型改 `StrictModel` | 一次消除一整类静默 bug | 小（改基类，可能需修 422） |
| 3 | 抽 `BaseMCPBridge`，统一走 `path_safety` | 收掉可维护 P1 + 安全 P2 | 中 |
| 4 | 补 `test_path_safety.py`，去掉测试的真实网络/文件探测依赖 | 消除假绿与 flaky | 小 |
| 5 | `executor.py:989` 的 `except pass` 改显式失败或告警 | 消除静默资产丢失 | 小 |

---

## 修复记录（2026-09-08）

上表 5 项全部落地，测试从 270 增至 302，ruff 干净。

| # | 事项 | 落地方式 | 验证 |
|---|---|---|---|
| 1 | 摘掉 `*_executable` | `tool_registry.py` 新增 `EXECUTABLE_FIELDS` / `ToolSpec.executable_args` / `_probe_executable()`，`call()` 强制覆盖模型传入值；新增 `exposed_executable_args()` 守卫。5 个工具从 schema 摘除 | `test_agent_loop.py` +2 |
| 2 | `StrictModel` | Studio 7 个请求模型改 `StrictModel`（响应模型保持宽松），先核对前端载荷字段对齐 | `test_request_models_reject_unknown_fields` |
| 3 | `BaseMCPBridge` | 新增 `fantasy_agent/mcp_bridge.py`，四个 bridge 继承；`_resolve_workspace_path` / `_write_text` / `_display_path` / `__init__` 全部上提，`safety_error` 类属性保留各自的异常类型 | `test_mcp_bridge.py` +20 |
| 4 | 测试假绿 | 新增 `test_path_safety.py`（+8）；`correction_targets` 改为 mock 探测并断言 ready / degraded 两态；新增一条走真实 `_build_execution_result` 的测试 | 变异测试确认有效 |
| 5 | `except pass` | 审批清单加载拆 `FileNotFoundError`（正常降级）与其他异常（阻断性 preflight 问题 `approval_manifest_unreadable`） | `test_unreadable_approval_manifest_blocks_the_run` |

### 顺带修掉的真实缺陷

收拢 bridge 时暴露出两个此前被重复实现掩盖的问题：

1. **`comfyui_mcp._write_run_manifest` 双重解析**：上层已把路径解析成绝对路径，再传回 resolver 二次解析。旧的宽松 resolver 接受绝对路径所以没炸，换成严格版后直接失败。改为接收已解析的 `Path`。
2. **Windows 下无盘符路径不算绝对路径**：`Path("/etc/passwd").is_absolute()` 在 Windows 返回 `False`，该分支实际由包含性检查兜底。已在测试中注明，断言改用带盘符的真实绝对路径。
