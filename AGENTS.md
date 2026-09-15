# Fantasy Agent 编排规则

Fantasy Agent 的生产角色是 `fantasy_agent/` 下的模块化库内工人，不是独立服务进程。每个角色只负责清晰边界内的任务，接收结构化输入，返回结构化输出，由 Studio 单进程直接调用，彼此之间没有 RPC。

## 全局规则

- 玩法优先于图形。
- 每个生成资产、机制和自动化步骤都必须服务可玩循环。
- 目标是 5 到 15 分钟的垂直切片。
- 优先做一个内聚循环，而不是多个断开的功能。
- 不创建空洞的程序化空间。
- 不隐藏不确定性。必须标出假设和未解决的生产风险。
- 本地工具（Blender / ComfyUI / Unreal / Godot / GitHub CLI）的实际操作必须在执行前声明清楚。
- Studio 是唯一的对外入口，只监听 `127.0.0.1`；不得新增任何供外部客户端接入的 MCP 端点。
- QA 检查必须先于打包和视觉扩展。
- 面向人的文档、界面和设计说明优先使用简体中文。
- 实现标识保持英文：类名、Blueprint 名、目录路径、MCP tool 名和 metric key 不翻译。
- ComfyUI 是视觉参考工人，不是玩法权威。
- ComfyUI 与 Blender 输出必须先通过 Creative Review，再进入 Unreal 或 Godot 导入。
- Godot 是快速可玩验证目标，不替代 Unreal 主线生产导入。
- 策划工作台是交互式计划入口，由 Studio 以本地 REST 端点提供；没有明确确认时不得执行生产实际操作。
- 前端不得替用户做执行确认：`confirmed_side_effects` / `confirmed` 这类标记必须由界面上的用户动作产生，不得在调用点写死 `true`。后端闸门（`local_tools.py`）只在没有该标记时拦得住，写死等于把闸门拆了。

## 测试与校验

- 后端测试用 `python scripts/run_tests.py` 跑（pytest 参数照常追加，如 `-k unreal -x`），**不要直接 `python -m pytest`**。原因：pytest 默认的临时目录方案会回收旧的编号 base 目录，回收方式是一次批量删除；本机护栏会拦下批量删除，于是 pytest 在退出阶段崩掉、汇总行被替换成护栏提示、退出码失真——测试可能是通过的，却报不出来。该脚本每次给一个全新的 `--basetemp`（没有旧目录可回收，因此根本不产生批量删除），并把结果写进 junit XML 再读回来，退出码由报告推导；收集到 0 个测试按失败处理（退出码 2）。
- **`--basetemp` 必须落在 OS 临时根目录下**（`tempfile.gettempdir()`，脚本里的 `TEMP_ROOT`），别挪回仓库内。护栏的放行条件是「路径在 OS 临时根之下」，`generated/test-tmp/` 不满足——实测把 base 目录放仓库里跑一次就会触发 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`，`SystemExit` 从 fixture 收尾里逃出来，`_pytest/fixtures.py` 的 `assert not self._finalizers` 接着让后面 156 条测试集体 `failed on setup`，真正坏掉的那条被淹没在里面。挪到 OS 临时根之后 3 连跑全绿、零护栏命中。`tests/test_run_tests_runner.py` 钉着这两条（目录在豁免根下、且不在仓库里）。
- `tests/test_dependency_guards.py` 守住几件「人工复核会过、之后会悄悄回归」的事：lock 的 `resolved` 必须全指向官方源（挡镜像污染）、每个包必须有 `integrity`、父包声明的依赖必须都记进 lock（挡平台二进制缺失——本地装得好好的，换 CI 的 runner 就 `npm ci` 找不到可执行文件）、依赖范围不得写 `latest`、`[tool.ruff.lint]` 不得出现 `select` 白名单。
- lint 跟随 ruff 默认规则集，不设 `select` 白名单：新版本启用新规则时 CI 变红，规则会被读到并采纳，而不是被 pin 掉。单条规则确实不适用就就地写 `# noqa: CODE - 理由`——`fantasy_agent/` 里 20 处 `except Exception` 都是这么标的。

## 前端（apps/frontend + apps/studio/static）

- 策划工作台在 `apps/frontend/src/workbench/`（`PlanningWorkbench` 主组件 + `workbenchModel` 纯函数 + `PlanPanels` 八个面板）。旧静态页 `planning-workbench.html` 已删除，`/workbench` 与其它路由一样走 dist 优先。
- 工作台通过 `POST /api/tools/{name}` 调后端策划工具。工具名是跨端契约：改动任一侧后跑 `tests/test_workbench_tool_coverage.py`，前端引用不存在的工具、或后端新增未接 UI 的工具都会红。
- 工作台只做策划，不写文件、不起进程 —— 执行一律在流程控制台。所以这里没有 `confirmed_side_effects` 之类的审批标记，唯一闸门是「点子确认后才能跑计划工具」。
- 新增/改名后端端点后，跑 `tests/test_frontend_endpoint_coverage.py`：前端引用了不存在的端点会红；后端新增了前端没接的端点必须登记进 `KNOWN_WITHOUT_UI` 并写明原因。
- i18n 的中英字典必须同步加 key：`npm run frontend:test` 里的字典一致性测试会抓单边缺失和空文案。
- 仍在用的静态页（`apps/studio/static/index.html`、`apps/studio/static/web-console/app.js`）往 DOM 里插后端字符串一律走 `escapeHtml()`；`list()` 已内置转义，不要绕过它自己拼 `<li>`。React 侧插值默认转义，别用 `dangerouslySetInnerHTML`。
- 提交前跑：`npm run frontend:typecheck`、`npm run frontend:test`、`npm run frontend:build`（CI 会跑同样的三条加后端 pytest + ruff）。
- 依赖不要写 `latest`；锁版本靠 `package-lock.json`，新增依赖后确认 lock 已同步（`tests/test_dependency_guards.py` 会检查，见上方「测试与校验」）。

## 语言规则

- Canonical implementation identifiers 保持英文：class name、Blueprint name、folder path、MCP tool name 和 metric key。
- 面向人的设计文本当前以 `zh-CN` 为主。
- 核心 DSL 仍保存稳定英文主字段；需要多语言时，字段路径翻译放在可选 `i18n` 下。
- GDD 与审阅文本可以按 `PromptRequest.output_locales` 输出多语言版本。

## 角色交接合约

各角色通过 `fantasy_agent/contracts.py` 中的 Pydantic 模型，以及 `generated/` 下的 YAML 或 Markdown 产物交换信息。

必要交接属性：

- `source`：产出角色或工具。
- `schema_version`：gameplay DSL 或 tool contract 版本。
- `inputs`：来源 prompt、spec 或 manifest。
- `outputs`：生成产物。
- `risks`：阻塞问题或假设。
- `next_actions`：具体下一步。

## 返工（Rework）

流水线必须支持节点级返工，不能等整条跑完再回头——ComfyUI、Blender 和 headless import 每个都要几分钟，跑完才发现问题是纯浪费。

两条机制：

**1. 前置闸门（`fantasy_agent/preflight.py`）**

在任何昂贵节点之前跑廉价静态校验，每个问题带 `rework_target`，直接指出该回到哪个节点：

- `prompt`：原始创意太薄，重写 prompt。
- `spec`：gameplay spec 有洞（缺 `level_beats`、`win_state`、`failure_states` 等）。
- `godot_plan`：引擎交接计划不合法（如工程名为空）。
- `flags`：计划没问题，是运行开关错了（声明了资产需求但没开 Blender 等）。

`rework_target` 说的是「改什么」，**执行阶段名说的是「从哪跑」**，这是两套词汇表。`pipeline_state.py` 的 `REWORK_TARGET_STAGES` 是两者之间唯一的翻译层，`normalize_resume_from()` 同时接受这两种写法，所以 `--from-stage spec` 和 `--from-stage blender` 都能用。有测试守着两个方向不漂移（新增 `REWORK_*` 常量必须同步加映射）。

每个 issue 还带一个 `resume_stage` 字段（会进 JSON），就是 UI 那个「从此节点续跑」按钮要用的值。未知的续跑节点一律报错，不再静默退化成整条重跑——那正是这个模块要消灭的浪费。

严重程度分两级，区分是关键：

- `blocking`：下游节点不可能产出有意义的东西。立刻停在闸门，不烧时间。
- `warning`：仍能产出可用的东西（降级灰盒、无参考图的 demo）。照常跑，只报告。

warning 这一级保住了既有承诺：缺工具仍然降级而不是失败，只有真正的设计缺陷才不再被拖到链路末尾。

**2. 阶段状态落盘 + 从节点续跑（`fantasy_agent/pipeline_state.py`）**

每次执行把每个已结束的阶段写进 `generated/<engine>/sessions/<session_id>/_pipeline_state.json`。

- 续跑：`--session-id <id> --from-stage <node>`（Studio 用 `ExecuteDemoRequest.session_id` / `resume_from`）。
- 只有**真的成功过**的阶段才会被跳过；失败阶段永远重跑，未知阶段名一律不跳过——续跑不能掩盖失败。
- `create` 和 `validate` 不可跳过：它们便宜，且后续每个阶段都依赖其产出的 `project_file`。
- `GODOT_STAGE_ORDER` 必须与 `execute_godot_demo` 的实际阶段保持同步，否则该节点永远不可续跑（有测试守着）。
- `UNREAL_STAGE_ORDER` 同样被测试钉在 `execute_unreal_demo` 的实际阶段上（成员与顺序都查，因为 `stages_before` 按位置读）。**但 Unreal 续跑尚未接线**：`execute_unreal_demo` 不调 `record_stage`，不写 `_pipeline_state.json`，`--from-stage` 对它无效。加能力时从这份清单出发。

**3. 界面纠偏闭环（Studio 流程控制台）**

`POST /api/execute` 返回 `session_id`，流程控制台据此在每次跑完后拉取 `GET /api/sessions/{id}/state`，列出各节点状态，每个节点一个「从此节点续跑」按钮。普通「生成 demo」永远开新 session，只有显式续跑才复用——避免节点级返工意外继承旧产物。

## Agent Loop（可选层，不是替代品）

确定性流水线答不了开放式规划问题（"比较这两个方向""还缺什么才能可玩"）。这类问题交给 `fantasy_agent/agent_loop.py` 的有界循环：让模型自己决定调哪个规划工具、调几次。

**三条不可逾越的边界**（任何改动都不得破坏）：

1. **模型不能决定"能不能做"。** 每个工具有 permission 分级（`read_only` / `write` / `execute`），闸门在 `tool_registry.py`，在循环之外。模型只能"尝试"，永远不能"提权"。被拒的工具以 refused 结果回传给模型，循环继续而不是崩掉。
2. **跑多久不由模型决定。** `max_turns` 是硬上限（默认 8）。没有它，一个跑偏的模型会在 1M 上下文里空转。
3. **失败不传染。** 任何 `LLMError` 返回 `status="error"`，调用方回退确定性流水线——和 `complete_json` 现有契约一致。循环是**增量**，不是替代；"demo 一定建得出来"这条保证仍由底下的确定性路径兜底。

**GPT-6 硬约束**：Astra 的 tool calling 只在 Responses API（`/v1/responses`）上提供，Chat Completions 会拒；且它**不接受 `temperature` / `top_p` / `logprobs`**，传了是硬报错而非忽略。所以：

- 用 GPT-6 跑循环必须选 provider `openai_responses`，默认模型 `gpt-6-astra`。这是**模型**的限制，不是代码闸门——换别的模型时 `anthropic` / `openai_compatible` 一样能跑循环。
- `api_settings.supports_sampling_params(model)` 在构造 payload 前判断，gpt-6 / o 系列一律不带采样参数。

**接入方式**：

- CLI：`--agent "目标" [--agent-max-turns N] [--agent-engine-tools] [--agent-allow-write] [--agent-allow-execute]`
- Studio：`POST /api/agent/run`（永不抛异常，失败以 status 返回）
- Studio 界面：策划工作台的**「Agent」面板**，可填目标、设 max_turns、勾选引擎工具与 write/execute 授权，跑完展示回答、工具调用明细和被拒清单。

**工具调用在三个 provider 上都可用**：`llm.complete_with_tools` 按当前 provider 分派——`openai_responses` 走 `/v1/responses`，`anthropic` 走 Messages API 的原生 `tool_use`，`openai_compatible` 走 `/chat/completions` 的 `tools`/`tool_calls`。（范围仅限**工具调用**：生成路径 `complete_json` 只有 anthropic / openai_compatible 两个分支，配 `openai_responses` 跑生成会明确报错，见上方「可选 LLM 后端」。）

- **循环只有一种对话格式**：`agent_loop` 的转录是 Responses 形状（`function_call` / `function_call_output` 块，call id 靠它对齐）。另外两个 provider 拿到的是**这份转录的投影**，回复也会被重新表达成同一形状再交回循环。所以循环不知道自己在跟哪种 wire format 说话，换 provider 不需要改循环。
- 投影在 `llm.py` 里是四个纯函数：`_anthropic_transcript` / `_anthropic_tools`、`_openai_chat_transcript` / `_openai_chat_tools`（外加 `_parse_anthropic_tool_reply` / `_parse_openai_chat_tool_reply` 两个反方向解析）。加第四个 provider 就是加一对投影函数。
- **没有 key 仍然是响亮失败**：任何 provider 缺 key 都抛 `LLMError`，循环返回 `status="error"`，调用方回退确定性流水线——不会静默降级成"模型没工具可用"。

**工具注册表**：`fantasy_agent/tool_registry.py` 是唯一真相——工具在此声明 schema + permission + handler，同一份记录同时喂给模型、权限闸门和 UI。`validate_contract_refs()` 守卫 `MCPToolContract` 的 34 个 `schema_ref` 全部能在 `mcp/*.yaml` 解析（有测试守着，此前这些引用从无代码解析）。

### 引擎工具（Godot / Unreal / Blender / ComfyUI）

`engine_registry()` 把 16 个已实现的 MCP 工具接进循环。schema、描述、注解全部来自执行它的那个 bridge，所以 bridge 改形状，模型的工具列表必然跟着改——不存在第二份手写清单。

三条规则是这次接线定下的，改之前先读：

1. **权限从 MCP 注解推导，不手写。** `readOnlyHint` → `read_only`；非只读且 `idempotentHint` → `write`；非幂等 → `execute`（只有 `run_*` / `generate_asset_batch` 会启进程）。`permission_from_annotations()` 是唯一出处。
2. **模型不造 plan。** `create_godot_project_structure` 这类工具要一个嵌套 `GodotProjectPlan`，模型造不出来也不该造。它们声明 `plan_key`，`plan` 参数从 schema 里**隐藏**，由注册表把本轮 `generate_game_production_plan` 的产物注入（`run_agent` 每次调用后调 `remember_plan`）。附带收益：Godot 那个工具的 schema 从 19.5KB 降到 1.5KB。
3. **确认由闸门注入，不由模型声明。** `write_files` / `confirmed_side_effects` 默认都是 false，不注入的话"授权"等于什么都没发生。授权时注册表写入 true——但**模型显式传 false 时保留**，那是它主动要 dry run。

**未接线的一个**：`publish_prototype_branch`（github-mcp）只有契约没有实现。`unimplemented_contracts()` + 测试把这个缺口钉住——实现了却没接线、或删了契约忘了测试，都会红。

**暴露范围跟着授权走**：不给授权时循环只看到只读检查工具（`validate_*` / `probe_*`）；`allow_write` 放到 write 级；`allow_execute` 才放出 `run_*`。

**变异校验 `scripts/mutation_check_all_guards.py`**（进 CI，跟在 pytest 之后）：一套绿测试只说明守卫通过，不说明**把守卫声称要拦的行为删掉之后它会红**——守卫可以又绿又空。每条 case 就做这件事：把源码改回修复前的样子（或后来人真会写出的那个错），跑那一个守卫，要求它变红，再逐字节还原并校验还原结果。判定读 runner 自己的计数行、不读退出码，因为退出码两个方向都会骗人：节点名失效时 pytest 收集到 0 条、runner 退出 2，"非零即抓住"会把一个死守卫读成活的；守卫自己 skip 时退出 0 且报告全绿，看起来像"没抓住"。所以 `NO RUN` 与 `SKIPPED` 都单独报成**未证明**，不计入通过。需要本机引擎的 case（两条真跑 Godot）在 `ENGINE_REQUIREMENTS` 里声明，引擎不在时报 `N/A` 而非失败，于是它在没装引擎的 CI runner 上照样跑得完其余的。`tests/test_mutation_harness.py` 在 CI 里静态校验 harness 的输入——针点是否仍恰好命中 1 次（含行尾归一）、每个节点名是否存在、引擎声明是否还有对应 case——因为 harness 自己坏掉是隐形的。

**真机探针 `scripts/verify_engine_links.py`**（手动跑，不进 CI）：测试和探针各管一半——测试钉"代码路径对不对"，探针钉"本机的引擎真的应答"。它走的是同一个 `combined_registry`，所以权限闸门、可执行文件探测和模型 tool call 完全一致；每一步把引擎自己的命令行、`return_code`、stderr 打出来，于是"这条链路是通的"是可读的结论而不是信念。`python scripts/verify_engine_links.py [--workspace 目录]`。引擎会真的被拉起来，所以它会写 `generated/` 并占用引擎时间。Unreal 那一步是真的起 headless editor（`DataValidation` commandlet）——只把 `.uproject` 写出来不算验证，因为"没装"和"坏了"在磁盘上看一模一样；asset ingest / level assembly 要脚本，探针不建，所以不用它们做启动测试。**没装引擎的步骤照样报告，只是降级**——区分"Unreal 没装"和"Unreal 链路坏了"正是它存在的理由。探针里的工具名是手写的，`tests/test_workbench_tool_coverage.py` 守着它们仍在注册表里。

**引擎装在哪由 `local_tools` 解析，别写死路径**：`_find_unreal` 先读 Epic 自己的 `%PROGRAMDATA%\Epic\UnrealEngineLauncher\LauncherInstalled.dat`，再退回 `Program Files` 路径模式。原因是 Launcher 允许把引擎装到任意根目录——本机 `UE_5.8` 在 `C:\ue\UE_5.8`，而 `C:\Program Files\Epic Games\UE_5.8` 只剩一个空的 Launcher stub，所以只靠路径模式会对着装好的引擎报"未安装"。manifest 里插件行（`FabPlugin_5.8` / `QuixelBridge_5.7`）和引擎行同在一个目录，只认 `ArtifactId` 以 `UE_` 开头的那几条。`tests/test_unreal_mcp.py` 钉着"自定义根目录能发现""插件的版本号不算引擎版本""manifest 缺失或损坏读作未安装而不是抛异常"。

**状态面板也走这套解析**：`apps/studio/app/main.py` 的 `_probe_executable` 接受一个 resolver，不再自己复制一份 glob/PATH 搜索——它复制过，于是执行器认得出自定义根目录的引擎、而 `/api/tool-status` 报 `unavailable`，面板和它要启动的进程各说各话。`tests/test_studio_app.py` 用打桩的 resolver 钉住"面板没有第二份实现"；Unreal 那一格显示的是真正会启动的 `-Cmd` 二进制，不是磁盘上那个 `UnrealEditor.exe`。

**ComfyUI 那格同理**：`_probe_comfyui` 曾自建候选端点，且跳过 `_is_local_http_endpoint` 这道本地限定——`COMFYUI_ENDPOINT` 指到远程时面板报 `ready`，而每个 run 都拒绝同一个端点（`comfyui_mcp` 的 `allow_remote_endpoint` 默认 false），顺带把设计上要显式授权的对外请求发出去了。现在它直接读 `local_tools._comfyui_target()`，与 Unreal 那格同一个套路。两条守卫钉住它：一条打桩 resolver、要求面板只复述 resolver 的答案（自建探测读不到桩，两条分支都会红），一条记录 resolver 实际拨的 URL、要求非本机端点从未被请求。`scripts/mutation_check_all_guards.py` 的 `C1`/`C2` 证明这两条守卫承重。

**ComfyUI 是服务，不是二进制**：Godot / Blender / Unreal 是拉起来就跑，ComfyUI 得先有一个在 `127.0.0.1:8188` 上监听的服务，探针不会替你起。下面这条是本机（Windows）验证过的路，**路径全是这台机器的，换机要按自己的安装位置改**（ComfyUI Desktop 装在 `D:\Comfy-Desktop`）：

```
"D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe" ^
  "D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\main.py" ^
  --listen 127.0.0.1 --port 8188 ^
  --models-directory "D:\Comfy-Desktop\ComfyUI-Shared\models" ^
  --output-directory "D:\Comfy-Desktop\ComfyUI-Shared\output" ^
  --input-directory "D:\Comfy-Desktop\ComfyUI-Shared\input"
```

三个坑：`--base-directory` 会要求 `custom_nodes` 目录存在，用 `--models-directory` 分别挂更省事；带 torch 的解释器在 `ComfyUI/ComfyUI/.venv`，外层 `standalone-env` **没有 torch**（manifest 声称有，实际没装）；上面这条命令行是给 cmd / PowerShell 写的（`D:\...`），**从 Git Bash 直接跑会被 python 收到字面量 `/d/Comfy-Desktop/...`**，报 `argument --models-directory: The path ... does not exist`——在 Bash 里要把路径写成 `D:/...`。**底模要自己备**：`models/checkpoints` 原本是空的，验证时下的是 `v1-5-pruned-emaonly.safetensors`（SD1.5 fp32，4.27GB）。ComfyUI 在启动时缓存模型清单，加了底模要**重启服务**才看得到。

**探针报告的路径按 workspace 解析，不按 cwd**：各 bridge 报的都是 workspace 相对路径，直接 `Path(p).exists()` 会用 cwd 去查，于是拿仓库里几个月前的旧文件给本轮打勾（Blender 那段曾经把 5 月的 fbx 报成刚导出的）。`_resolve()` 是唯一出处，有测试钉着。

## Director Agent

职责：

- 负责完整 prompt-to-playable workflow。
- 将工作路由到 Gameplay Agent、GDD Writer、Unreal Builder、Godot Builder、Blender Worker、ComfyUI Worker、QA Agent 和未来 MCP 工具。
- 拒绝无法合理产出可玩垂直切片的范围。

输入：

- `PromptRequest`

输出：

- `DirectorBuildPlan`

流程：

1. 归一化 prompt 和约束。
2. 生成玩法优先的 spec。
3. 渲染 GDD。
4. 准备 Unreal、Godot、Blender 和 ComfyUI 交接。
5. 准备 QA 计划。
6. 返回下一步和风险。

## Gameplay Agent

职责：

- 将原始 prompt 转换为连贯的玩法系统。
- 定义核心循环、动词、节奏、进程、胜利状态和失败状态。

输入：

- `PromptRequest`

输出：

- `GameplaySpec`

规则：

- 只有能改变玩家决策的机制才有效。
- 只有能在灰盒地图中测试的循环才有效。
- 失败状态必须帮助玩家理解下一次尝试。

可选 LLM 后端：

- 默认使用确定性生成（`design_from_prompt_deterministic`），基于关键词与模板，无需任何外部依赖或 API key。
- 设置环境变量 `FANTASY_AGENT_USE_LLM=1`（或在 CLI 传 `--llm`）可启用 LLM 后端，由 `fantasy_agent/llm.py` 统一生成 `GameplaySpec`。
- Studio 的「API 接入」面板可在界面上配置 provider、base URL、model、key 和 timeout，写入 `generated/config/llm-api.json`；`fantasy_agent/api_settings.py` 是唯一的配置读写入口，凭据只存本机且对外只返回掩码。
- provider 有三个：`anthropic`、`openai_compatible`（含本地网关）、`openai_responses`。**生成路径（`llm.complete_json`）只实现了前两个**，两条都走标准库发 HTTP，**不强制安装 SDK**，`pip install fantasy-agent[llm]` 只是可选的 SDK 逃生通道；`openai_responses` 只实现了 tool calling（见「Agent Loop」），把它配成当前 provider 再开 LLM 生成会拿到明确报错并回退确定性路径——不会静默把 Anthropic 形状的请求体连 `x-api-key` 一起发到 `api.openai.com/v1/messages`。
- 模型默认按 provider 取：`anthropic` → `claude-opus-4-8`，`openai_compatible` → `gpt-4o-mini`，`openai_responses` → `gpt-6-astra`（见 `api_settings.DEFAULT_MODELS`）；可用 `FANTASY_AGENT_MODEL` 覆盖。凭据走标准的 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`。界面配置的优先级高于环境变量。
- 任何 LLM 失败（未配置、无 key、API 错误、输出非法或未通过 `GameplaySpec` 校验）都会自动回退到确定性生成，绝不中断流程。无论走哪条路径，返回的都是同一套 `GameplaySpec` 契约，下游 Unreal/Godot/Blender/ComfyUI/QA 编排无需改动。

**机制轴模板（`fantasy_agent/axis_templates.py`）**

确定性路径按 `_detect_axis()` 识别的机制轴取模板，目前 8 条：`parkour` / `career` / `stealth` / `combat` / `survival` / `puzzle` / `mobility` / `systems`。每条轴自带核心动词、四步循环、三个系统、三段曲线、三个关卡节拍、资产需求和叙事包装（win/fail、设计支柱、ComfyUI 备注）。

- **`systems` 是兜底轴**，文案刻意通用：它描述"一个可玩切片的形状"，不假装有具体题材。某个题材反复落到这里，正确做法是加一条轴，而不是把通用文案改得更好听。
- **中文文案与英文写在同一条记录里。** `i18n.py` 按位置把英文字段和 zh-CN 配对，所以两者分开存放必然漂移——曾经所有非 career 轴的中文 GDD 都写着"教学口袋区 / 系统混合区"，而英文已经是"Warmup Rooftop"。
- **新增一条轴**：在 `AXIS_TEMPLATES` 加条目 → 让 `_detect_axis` 能返回该键 → 跑 `tests/test_generation_axis.py`。该测试断言每条轴都能被真实 prompt 触发、任意两轴不共用节拍名/系统名/动词组、每轴中英文条目数一致，复制粘贴忘了改会立刻红。
- 关键词表要覆盖最常见词形：`"racing"` 里并不包含子串 `"race"`，只写 `"race"` 会让整条 mobility 轴在英语里不可达。

**GDScript 跟着轴走（`fantasy_agent/gameplay_codegen.py`）**

设计模板只决定"说什么"，`_AXIS_MECHANICS` 决定"生成什么代码"：每条轴一份 `AxisMechanics`（@export 参数、状态变量、`_physics_process` 里的动作块、辅助函数、敌人接触文案）。过去只有 `parkour` 有实现，其余 7 条轴共用同一个 WASD+jump —— 潜行设计生成的代码不能蹲下，解谜设计生成的代码不能交互。

- **轴判定查表，不写死分支。** `_axis_from_verbs()` 用 `AXIS_TEMPLATES` 的动词集给每条轴打分，新增轴不用改判定函数。
- **每个核心动词必须落成实现块。** 生成的代码里每个动词有一个 `# [VERB]` 锚点，测试逐轴断言"设计声明的动词都在代码里"，动词只写进文案会立刻红。
- **只能按项目里存在的 InputMap 动作。** 动作名来自 `spec.core_verbs`（`workflows.prepare_godot_project` 注册），所以 `action_name()` 与 `godot_mcp._godot_identifier` 必须同源；按了一个没注册的动作，Godot 运行时报 `Request for nonexistent InputMap action`。
- **敌人行为只有一个来源**：设计模板的 `enemies` 名册。轴里不再另存一份行为清单（曾经两份会漂移）。
- **新增一条轴**：`AXIS_TEMPLATES` 加条目 → `_AXIS_MECHANICS` 加对应实现 → 跑 `tests/test_gameplay_codegen_axis.py`（键集不一致立刻红）。
- **真机校验**：`tests/test_gdscript_godot_check.py` 给每条轴建临时工程，跑 `godot --check-only --script` 做语法检查，再用一个 SceneTree harness 实例化并推 20 帧，抓运行时错误。同一个文件还走一次 `combined_registry`（= tool call 同一条路径）生成工程并真跑 `run_godot_import`，断言 Godot 日志里没有任何 `Parse Error` / `SCRIPT ERROR` / `ERROR:`。
  - **二进制发现用项目自己的探针**（`local_tools._find_godot`：环境变量 → PATH → 安装位置 glob），不再只看 PATH。之前它只看 PATH，本机 Godot 装在 `Downloads/` 下，于是整个文件静默 skip —— 这正是"生成的代码坏了却一路绿灯"的成因。探针优先 `*_console` 版本，因为 Windows 上只有它能把输出写进被捕获的管道。
  - **`HANDOFF` 是 `const` 字典字面量，只能 `.get()` 读。** Godot 在解析期就拿字面量的已知键做静态检查，所以 `HANDOFF["gameplay"]` 在键不存在时是**静态解析错误**，`if HANDOFF.has("gameplay")` 挡不住——要挡的那行本身就编译不过。没有 gameplay 块的工程（也正是模型经注册表能产生的唯一形态）会整份 main.gd 加载失败，而 `validate_godot_project` 只查文件存在性，会报 `issues: []`。守卫分两层：`tests/test_godot_mcp.py` 断言源码里没有 `HANDOFF[`（CI 可跑），`test_gdscript_godot_check.py` 用真 Godot 复现（本地跑）。

命令行入口：

- `python -m fantasy_agent --prompt "游戏创意" [--llm] [--minutes 10] [--engine "Godot 4"] [--format summary|json|gdd]`
- 安装后亦可用 `fantasy-agent` 控制台命令。

## GDD Writer

职责：

- 将 gameplay spec 转换成结构化 Markdown 设计文档。
- 保留玩法意图，不添加未经批准的功能。

输入：

- `GameplaySpec`

输出：

- `GDDDocument`

规则：

- 面向实现编写。
- 区分已确认设计和假设。
- 美术方向必须服从互动可读性。

## Level Director

职责：

- 将玩法循环转换为关卡节奏和灰盒需求。
- 保持空间计划足够紧凑，方便快速迭代。

输入：

- `GameplaySpec`

输出：

- 关卡节奏计划。
- encounter 或目标计划。
- 灰盒资产需求。

规则：

- 第一分钟必须教会循环。
- 中段必须组合系统。
- 最后一段必须强制玩家使用完整循环。

## Unreal Builder

职责：

- 准备 UE5 工程结构、插件、地图、Blueprint 类、Data Asset 和自动化步骤。

输入：

- `GameplaySpec`

输出：

- `UnrealProjectPlan`

未来 MCP 兼容性：

- Unreal MCP 只应执行 allowlist 内的工程创建、资产导入、地图验证和打包命令。

执行编排（Executor，M4）：

- `executor.py` 的 `execute_unreal_demo()` 编排：`create_project_structure` → `prepare_asset_ingest` → `prepare_level_assembly` → `run_editor_commandlet("DataValidation")`，生成完整 .uproject 工程并用 DataValidation 真跑验证。
- **M4 范围**：工程生成 + DataValidation。重型的 `run_asset_ingest` / `run_level_assembly`（需真 fbx 资产 + 开 UE 编辑器）暂不跑，留作未来扩展。
- prepare 阶段只写盘（沙箱内，无需确认）；DataValidation 过 `confirmed_side_effects` 门。`run_validation=False`（CLI `--no-import`）时止于 prepare_level，无 UE 环境也能出工程。
- ingest 用 `require_existing_sources=False`：executor 先把 Blender→Unreal import manifest 写到 `generated/import-manifest.yaml`，源 fbx 不存在仅警告（M4 不强制先跑 Blender）。
- 降级：DataValidation 失败标记 failed，但前面工程已生成（与 Godot import 失败一致）。
- session 产物布局：`generated/unreal/sessions/<session_id>/<project>/`，保持在 `generated/unreal` 沙箱前缀内。
- headless 用 `UnrealEditor-Cmd.exe`：`local_tools._unreal_cmd_executable()` 把探测到的 `UnrealEditor.exe` 映射到同目录 Cmd 版。
- **本地 DDC 路径有 119 字符上限，别让它跟着工程目录长**：`_unreal_env()` 会把 `UE-LocalDataCachePath` 指到 `<工程目录>/DerivedDataCache`（让生成的 demo 自带缓存），但 Unreal 的 `FileSystemCacheStore` 在路径超过 `unreal_mcp.MAX_LOCAL_DDC_PATH`（119）时**在 commandlet 跑起来之前就直接 Fatal 退出**，退出码 3，报"缓存路径 ... 长于119个字符"。实测本机默认 workspace 的路径是 105（贴线），而探针多嵌一层 `--workspace` 就变成 133、当场炸——症状和"引擎坏了"完全一样。所以 `_local_ddc_dir()` 只在路径放得下时才留在工程内，放不下就按工程路径哈希挪到 OS 临时根下的 `fantasy-agent-ue-ddc/<hash>`；缓存丢了只损失编译时间，不损失产物。`tests/test_unreal_mcp.py` 钉着"长路径必须挪出去""短路径必须留在工程内""两个长路径工程不能共用缓存目录"。
- 引擎路由：CLI 按 `--engine` 分派——含 godot 走 Godot 路径，含 ue/unreal 走 Unreal 路径。`--engine UE5 --execute [--yes] [--unreal-exe PATH] [--no-import]`。`--with-assets`/`--with-visuals` 在 Unreal 路径下 M4 暂不适用（传了会提示忽略）。

## Godot Builder

职责：

- 为快速可玩循环验证准备 Godot 4 工程交接。
- 在 generated 路径下生成 `project.godot`、主场景、GDScript prototype 脚本和 import manifest。

输入：

- `GameplaySpec`

输出：

- `GodotProjectPlan`

规则：

- Godot 用于在较重 Unreal 工作前验证循环时长、路线可读性和交互节奏。
- Godot MCP 执行必须将工程保持在 `generated/godot/`，日志保持在 `generated/logs/godot/`。
- 没有明确执行确认时，不得启动 Godot 或运行 headless import。

执行编排（Executor）：

- `fantasy_agent/executor.py` 的 `execute_godot_demo()` 是从 `DirectorBuildPlan` 到可运行 Godot 工程的编排层，串联现有 godot MCP 三步：`create_godot_project_structure(write_files=True)` → `validate_godot_project` → `run_godot_import(confirmed_side_effects=True)`，逐阶段回报状态/日志/产物，不重复实现引擎逻辑。
- 工程文件由 `GameplaySpec` 驱动：`level_beats` 映射为路线分段（每个 beat 一段 floor + 由其 `required_assets` 关键词决定材质语义的标记体），`win_state`/`failure_states` 注入 `main.gd`。不同创意产出不同灰盒，而非固定模板。
- 单次总确认门：`confirmed=False` 时只返回"将执行的副作用清单"且不写盘；`confirmed=True` 后每个副作用阶段仍各自带 `write_files` / `confirmed_side_effects` 标志。
- session 产物布局：`generated/godot/sessions/<session_id>/<project>/`，保持在 `generated/godot/` 沙箱前缀内。
- M1 不做失败自动重试；失败阶段附带捕获的日志路径。
- CLI：`python -m fantasy_agent --prompt "..." --engine "Godot 4" --execute [--yes] [--godot-exe PATH] [--no-import]`。不带 `--yes` 打印副作用清单；不带 `--execute` 仍是纯规划。Godot 可执行文件由 `local_tools._find_godot()` 自动探测（含 `~/Downloads` 下的版本）。
- 资产链（M2）：加 `--with-assets` 在 create 前插入 Blender 阶段（导出 glb）并在 import 前复制进工程；`--blender-exe PATH` 覆盖探测。阶段顺序 blender→create→copy_assets→validate→import。Blender 失败自动降级为纯灰盒。`main.gd` 的 beat 标记体会先尝试 `load("res://assets/generated/<asset>.glb")`，缺失则回退到程序化 box——因此无资产时行为与纯灰盒一致。

真实玩法代码生成（M6a）：

- 加 `--with-gameplay` 在 create 前插入「玩法代码生成」阶段：由 `fantasy_agent/gameplay_codegen.py` 产出真实 GDScript——玩家控制器实现 `core_verbs`（如 parkour 的 sprint/wall-run/slide），game_manager 实现 `win_state`/`failure_states` 的真判定 + CanvasLayer Label HUD + 到时重开。生成的脚本写入工程，`main.gd` 实例化玩家 + game_manager 并把出口门接到 `reach_exit()`。
- **LLM 优先 + 确定性回退**：`use_llm` 时用 `llm.complete_json` 让模型生成 GDScript；不可用/输出非法时回退到 axis-aware 确定性模板（仍比旧的 WASD+跳丰富）。
- **导入校验 + 失败回退**：LLM 脚本若导致 Godot headless 导入报脚本错误，executor 自动用确定性模板重生成并重新导入，gameplay 阶段标记 `degraded`——保证 demo 一定能跑。
- 阶段顺序：gameplay→create→validate→import，可与 `--with-assets`/`--with-visuals` 组合。
- **真实敌人闭环（M6b）**：`GameplaySpec.enemies` 由确定性/LLM 规划生成，`--with-gameplay` 写出 `enemy_controller.gd`，`main.gd` 沿路线生成 patrol/chase/stationary/ranged 敌人；敌人只通过 `game_manager.fail_from_enemy()` 触发失败，不直接重启场景。
- **敌人压力调参（M6c）**：`EnemyPressureTuning` 可调整敌人数、移动速度、侦测半径、巡逻半径和远程攻击间隔；executor 写出 deterministic enemy pressure report，Studio 生成面板可在确认执行前调参。
- **范围**：M6a 先完成玩家机制 + 胜负 + HUD；M6b 已接入 `EnemySpec`、`enemy_controller.gd` 和 `main.gd` 敌人实例化，让声明的敌人能在 Godot 灰盒中产生失败压力。

## Blender Worker

职责：

- 准备支持灰盒可玩性和互动可读性的程序化资产任务。
- 从已批准的 `BlenderAssetPlan` 交接生成 Blender Python 脚本。

输入：

- `GameplaySpec`

输出：

- `BlenderAssetPlan`

规则：

- 先生成模块化资产。
- 使用比例正确的导出。
- 按玩法角色命名资产。
- 每次导出都生成 `UCX_` 碰撞对象和 Unreal import manifest。
- 没有明确执行确认时，不得从规划界面运行 Blender。
- Blender MCP 执行必须将脚本放在 `generated/blender/`，导出放在 `generated/assets/`，日志放在 `generated/logs/blender/`。

Blender → Godot 资产链（M2）：

- Executor 的 `--with-assets` 路径会先跑 Blender 导出 **glb**（Godot 4 原生格式），再把 `.glb` 复制进 Godot 工程的 `assets/generated/`，由 `godot --headless --import` 导入。
- 导出格式由 `BlenderAssetPlan.export_format` 决定；executor 在 Godot 路径下强制 `glb`。`enrich_blender_job` 按格式规范化扩展名（不再出现 `name.fbx.glb` 双扩展名）。
- `fantasy_agent/godot_assets.py` 的 `copy_assets_into_godot_project` 只复制 `.glb`，`.fbx` 跳过并记录（Godot 需 fbx2gltf 转换器，M2 不处理；Unreal 线仍独立用 fbx）。
- **approval-gated ingest（M6e）**：传入 `approval_manifest_path` 时，executor 会先读取 `generated/asset-approval-manifest.yaml` 或指定 manifest，只把 Creative Review 标记为 approved 的 Blender GLB 复制到 Godot 工程；revision/rejected/pending 资产只记录在 `approval_gate` 阶段，不进入 `assets/generated/`。
- **approval gate QA / preview（M6f）**：`approval_gate` 阶段必须返回结构化 metadata，并写出 `generated/approval-gate-report.yaml`；Studio / Flow Console 需要显示 manifest、报告路径、approved/skipped/revision/rejected/pending 摘要和跳过资产清单。
- **降级语义**：Blender 不可用或执行失败时，blender 阶段标记 failed，整条链继续以纯灰盒完成，不中断。
- 重要约束：Blender 阶段要求 `workspace_root` 为仓库根（生成的脚本需 import `fantasy_agent.blender_runtime`）。纯 Godot 路径无此约束。

## ComfyUI Worker

职责：

- 为 ComfyUI 准备服务玩法可读性的视觉参考任务。
- 在玩法需求明确后生成 concept、material、UI、texture seed 或 storyboard 参考。

输入：

- `GameplaySpec`

输出：

- `ComfyUIVisualPlan`

规则：

- 不因图像生成阻塞灰盒工作。
- 每个 prompt 都必须包含玩法约束。
- 生成图片成为 Unreal texture 或 UI asset 前必须经过审阅。
- 避免不说明目标、危险、路线、材质或反馈的装饰图片。
- ComfyUI MCP 执行必须将模板放在 `templates/comfyui/`，输出放在 `generated/comfyui/`，日志放在 `generated/logs/comfyui/`。
- 没有明确执行确认时，不得向 ComfyUI 提交 prompt。

ComfyUI → Godot 参考链（M3）：

- Executor 的 `--with-visuals` 路径会跑 ComfyUI 出概念/角色/UI/材质参考图，再把图片复制进 Godot 工程的 `references/comfyui/`。`fantasy_agent/godot_assets.py` 的 `copy_references_into_godot_project` 只收图片扩展名（png/jpg/webp）、保持沙箱前缀校验。
- **边界**：参考图是艺术方向**归档**，供 Creative Review 审阅，**不自动贴到 3D 模型上**——这正是「生成图成为引擎纹理前必须经审阅」约束的体现。把图变成实际纹理是 Creative Review 通过后的后续工作。
- **降级语义**（与 Blender 一致）：ComfyUI 离线/未加载 checkpoint/执行失败时，comfyui 阶段标记 failed，整条链继续完成（无参考图），不中断。
- 执行是 HTTP（非 subprocess），端点默认限本地（`allow_remote_endpoint` 默认 false）。`local_tools._comfyui_target()` 自动探测 `http://127.0.0.1:8001` 等候选。
- CLI：加 `--with-visuals` 触发，`--comfyui-endpoint` 覆盖。可与 `--with-assets` 组合，阶段顺序 comfyui→blender→create→copy_assets→copy_refs→validate→import。

## Creative Review Agent

职责：

- 在 Unreal 或 Godot 导入前，与用户一起审阅 ComfyUI 参考图和 Blender mesh。
- 将用户审美、艺术方向、玩法可读性和技术导入检查转换为结构化审批决策。
- 将被拒绝或不明确的资产转回具体 ComfyUI 或 Blender 修改请求。

输入：

- `CreativeReviewRequest`

输出：

- `CreativeReviewReport`

规则：

- 生成参考或 mesh 成为引擎导入候选前必须获得用户批准。
- 审阅关卡会阻塞引擎导入，直到资产被批准、修改或拒绝。
- 反馈必须说明资产名称、玩法角色和具体修改请求。

## 策划工作台

职责：

- 在 Studio 内提供本地交互式策划工作台页面（`/workbench`）。
- 通过 `POST /api/tools/{tool_name}` 本地 REST 端点路由到各角色使用的同一套结构化规划合约。
- 在页面上渲染玩法、GDD、Unreal、Godot、Blender、ComfyUI 和 QA 交接。

输入：

- `PromptRequest`

输出：

- `DirectorBuildPlan`
- 聚焦子计划，例如 `GDDDocument`、`UnrealProjectPlan`、`GodotProjectPlan`、`BlenderAssetPlan`、`ComfyUIVisualPlan` 或 `QAPlan`

规则：

- 在明确执行前确认机制实现前，工具必须保持只读且幂等。
- 页面状态可以总结计划，但实现标识保持英文。
- 工作台交互必须保持玩法优先层级和 i18n 输出。
- 默认不得从该界面启动 Unreal、Godot、Blender、ComfyUI、打包、写文件或推送 GitHub。
- 所有端点只监听 `127.0.0.1`，不对外暴露协议端点。

studio 一键生成（M5a / M6c / M6d）：

- studio 后端提供 `POST /api/execute`（body `{plan, engine, with_assets, with_visuals, with_gameplay, enemy_tuning, approval_manifest_path, confirmed}`）+ `GET /api/execute/{job_id}`，给引擎执行链一个图形入口。
- studio 后端提供 `POST /api/assets/execute`（body `{plan, with_assets, with_visuals, confirmed}`）+ `GET /api/assets/execute/{job_id}`，用于只运行 ComfyUI / Blender 资产工人，不创建 Godot 或 Unreal 工程。
- 两段式授权：`confirmed=false` 同步返回 `planned_side_effects`（确认门，不写盘）；前端展示清单、用户点「继续」后再以 `confirmed=true` 发起。
- `confirmed=true` 时后端用单 worker `ThreadPoolExecutor` 起后台 job（避免并发跑多引擎），立即返回 `job_id`；前端轮询 `/api/execute/{job_id}` 拿阶段状态与产物，完成后展示 `project_dir`。
- 引擎路由：`engine` 含 godot/ue/unreal 或从 `plan.gameplay_spec.engine_choice` 推断，分派到 `execute_godot_demo` / `execute_unreal_demo`。引擎可执行文件用 local_tools 探测。
- 前端在 web-console（flow console）的执行确认区下方提供「一键生成」与「资产工人执行」面板，复用工具状态卡片样式渲染阶段，i18n 中英双语；approval gate 阶段额外展示批准/跳过清单和报告 artifact。job 仅存内存，studio 为本地开发工具。

## QA Agent

职责：

- 将 gameplay spec 转换为测试，验证可玩性、失败反馈和打包准备度。

输入：

- `GameplaySpec`

输出：

- `QAPlan`

规则：

- 先测试循环，再做打磨。
- 检查完成时间、重开流程、目标可读性和打包构建行为。

## M7 Agent 可执行生产 Spec

M7 以 `DirectorBuildPlan.production_spec_bundle` 作为执行权威，包含 `CombatSpec`、`LevelSpec`、`NumericTuningSpec`、`NarrativeSpec`、`ConfigTableSpec` 与 `ResourcePipelineSpec`。

规则：

- Agent 可从 YAML/JSON 读取现有 bundle；`schema_version` 不支持或深度校验失败时必须在任何工程写盘前阻断。
- `--spec-file` 不重新生成设计，只构造兼容下游计划；`GameplaySpec` 仅服务旧接口和未迁移路径。
- Godot 运行时 handoff 必须优先使用 Combat/Level/Numeric/Narrative Spec，输出 `data/production-spec-runtime.json`、配置表和 `data/spec-trace.json`。
- `ConfigTableCompiler` 必须确定性排序、校验主键和导出路径，并支持 YAML、JSON、CSV-ready。
- Creative Review 写入 approval manifest 后必须同步 `ResourcePipelineSpec.assets[].approval_status` 与 `blocked_assets`；未批准资产不得进入引擎 ingest。
- Studio Spec Bundle 面板必须展示校验状态、编译产物、字段到产物追踪和机器可执行 QA。
- Unreal adapter 输出 DataTable/DataAsset JSON 源与 `QA_Executable.json`；错误级 QA 阻断后续执行，警告级 QA 以 degraded 状态继续。