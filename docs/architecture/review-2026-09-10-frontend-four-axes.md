# 前端四轴 review（2026-09-10）

> **状态：P1 三条已修、P2 六条中五条已修。** 处理记录见文末「修复记录」。

评审对象：`apps/frontend/`（Vite + React/TSX 新版）与 `apps/studio/static/`（旧版静态页），后端 `apps/studio/app/main.py`（1182 行 FastAPI，38 个端点）。

方法：四条轴各派一路子 agent 并行评审，**所有指控由我逐条复核**（子 agent 误报率不低，本次 6 条被推翻，见文末）。

## 四轴定义与结论

| 轴 | 查什么 | 结论 |
|---|---|---|
| **契约一致性** | 前端调的端点/字段与后端 Pydantic 模型是否对齐 | 无断链。前端 11 个端点全部存在；但错误信息被前端吞掉 |
| **覆盖完整性** | 后端 38 个端点有多少有 UI 入口；两套前端是否重复 | 15 个命名端点只有测试没有 UI；两套前端并存，旧页仍在服务 |
| **安全边界** | AGENTS.md 硬约束（127.0.0.1 / 凭据掩码 / 执行闸门 / XSS） | 硬约束守住；但审批闸门被前端写死 `true` 绕过 |
| **可验证性** | 类型检查、构建、测试、CI | 类型检查和构建真能过；前端零测试、无 CI |

**总体：无 P0。** 3 条 P1、6 条 P2。

---

## P1

| # | 轴 | 位置 | 问题 | 证据 |
|---|---|---|---|---|
| 1 | 安全 | `apps/frontend/src/shared/api.ts:50`<br>`FlowConsole.tsx:239` | 人工纠偏「打开目标」把 `confirmed_side_effects` 写死 `true`，调用点**无二次确认**，直接绕过后端审批闸门 | `api.ts:50` `confirmed_side_effects: true`；后端 `local_tools.py:332` 有 `if not confirmed_side_effects: return {"status":"blocked"}`。实际动作是 `subprocess.Popen` 打开本机文件/编辑器，危害有限，但违反 AGENTS.md「没有明确确认时不得执行」 |
| 2 | 可验证性 | `package.json` | 新版前端**零测试**：无 `*.test/*.spec`、无 vitest/jest、无 `test` 脚本（只有 `frontend:dev/build/preview/typecheck`）；旧静态页 6733 行无任何 lint | `package.json` scripts 仅 4 项，全 `frontend:` 前缀；全仓无 eslint/htmlhint/stylelint 配置 |
| 3 | 可验证性 | 仓库根 | **无 CI**：没有 `.github/workflows`，类型检查/构建/后端 473 个测试全靠手动触发，PR 不保证可过 | `ls .github/workflows` → 不存在 |

## P2

| # | 轴 | 位置 | 问题 | 证据 |
|---|---|---|---|---|
| 4 | 契约 | `apps/frontend/src/shared/api.ts:33-36` | 错误只带状态码，后端 `HTTPException.detail` 全部丢失 —— 用户看不到「resume_from 需要同时提供 session_id」这类中文提示 | `throw new Error(\`HTTP ${response.status}\`)`；只有 `/api/settings/llm` PUT 走 `settingsRequest` 读 `payload.error` |
| 5 | 覆盖 | `main.py` 15 个端点 | `/api/plan`、`/api/design`、`/api/gdd`、`/api/qa`、`/api/tasks`、`/api/pipeline`、`/api/idea-seed`、`/api/tool-contracts`、`/api/{unreal,godot,blender,comfyui}/plan`、`/api/blender/script`、`/api/blender/plan-script`、`/api/creative-review` **无 UI 入口** | 前端只引用 11 个端点；旧页经 `/api/tools/{tool_name}` 间接覆盖。**注意：这些端点有 `tests/test_studio_app.py` 覆盖，不是死代码，是 UI 缺口** |
| 6 | 安全 | `apps/studio/static/web-console/app.js:1131-1138` | `innerHTML` 拼接 `stage.name` / `stage.detail` / `result.project_dir` 未转义 | 同页 `:/922` 处有其他 `escapeHtml`，此处漏了 |
| 7 | 可验证性 | `package.json` | 依赖全是 `"latest"`，TypeScript 钉在 `7.0.1-rc` | `{'vite':'latest','typescript':'7.0.1-rc','react':'latest'}`；靠 `package-lock.json` 兜底，锁一更新就漂 |
| 8 | 覆盖 | `main.py:81-82,474-479,888-890` | 两套前端并存：`/` 与 `/web-console` 优先返回前端 dist、**回退**旧静态页；`/workbench` 直接服务 `planning-workbench.html`（新版以 iframe 嵌入）。同一功能两份实现 | `_frontend_index_or()`：`dist/index.html` 存在则返回它，否则返回旧静态页 |
| 9 | 覆盖 | `FlowConsole.tsx:803` / `types.ts:302` | `ExecuteStage.logs` 在类型里声明了，后端返回了，前端不渲染 | 只渲染 `stages[].status`；`sessionState.done/failed` 也未被直接使用（用 `stages[].status` 替代，功能等价） |

---

## 被推翻的指控（复核记录）

这些是子 agent 报了、我查完认为不成立的。留档以免下次重复排查。

| 原指控 | 复核结果 |
|---|---|
| `planning-workbench.html:1611` innerHTML 未转义 → XSS | **误报**：内容经 `messageBubble()`（1578-1580）处理，其中 `escapeHtml(title)` / `escapeHtml(body)` 已转义 |
| `apps/frontend/dist/` 是过期的构建产物，被提交进仓库 | **误报**：`.gitignore:62` 忽略该目录，`git check-ignore` 确认未入库；且重新构建后 dist/index.html 引用的 hash 与产物一致 |
| 前端读 `preview.planned_side_effects`，但 `/api/specs/preview` 不返回该字段 | **误报**：`previewExecute` 走的是 `POST /api/execute` 的 dry-run（`main.py:1091`，`confirmed=False`），返回 `ExecutionResult`，确含 `planned_side_effects`（`executor.py:85`） |
| 「调用点写了、请求模型没写」→ 多传字段被静默丢弃 | **方向反了**：`contracts.py:106` `StrictModel` 是 `extra="forbid"`，多传会 **422** 而不是丢弃。当前代码没有多传字段的实例 |
| 15 个命名端点是死端点 | **降级**：`tests/test_studio_app.py` 有覆盖，属 UI 缺口（P2）而非死代码 |
| 旧静态页全是死代码 | **部分修正**：`/workbench` 仍直接服务 `planning-workbench.html`；`/` 和 `/web-console` 在 dist 缺失时用它兜底 |

## 已确认合规（非问题）

- 绑定：`--host 127.0.0.1`，全仓无 `CORSMiddleware`，无 `allow_origins="*"`；未新增外部 MCP 端点。
- 凭据：`api_settings.py:187` 对外只返回 `api_key_masked`；`storage.ts` 不存 key；`StudioShell.tsx:396` 输入框 `type="password"`。
- 路径穿越：session_id 经 `pipeline_state.py:186` `resolve_workspace_path` 兜底。
- 类型检查与构建真能过：`npm run frontend:typecheck` → `error TS` 计数 **0**（`strict: true` 已开）；`npm run frontend:build` → ✓ built in 1.95s。

---

## 建议的下一步（按性价比）

1. **修 P1-1**：`openManualCorrectionTarget` 加 `window.confirm`，把写死的 `true` 改成用户确认后传入。改动约 10 行，直接补上被绕过的闸门。
2. **修 P2-4**：`jsonRequest` 失败时读 `payload.detail`（后端 HTTPException 的形状），fallback 到状态码。改动约 5 行，用户能立刻看到后端中文提示。
3. **补 P1-3 的最小 CI**：一个 workflow 跑 `pytest` + `frontend:typecheck` + `frontend:build`。仓库当前完全没有自动化门禁，这是最便宜的回归保险。

未做：旧静态页（6733 行）是否下线，涉及 `/workbench` 和新版嵌入方式，需要先决定新版是否重写策划工作台 —— 这是产品决策，不是修补。

---

## 修复记录（2026-09-10 下午）

| # | 级别 | 处理 | 落点 |
|---|---|---|---|
| 1 | P1 | **已修** | `api.ts` 的 `openManualCorrectionTarget` 增加 `confirmedSideEffects` 形参，不再写死 `true`；`FlowConsole.openManualTarget` 调用前 `window.confirm`（文案走 i18n `manualOpenConfirm` / `manualOpenCancelled`）。测试钉住：传 `false` 时线上不会出现 `true` |
| 2 | P1 | **已修** | 引入 vitest 5 + jsdom + @testing-library/react；`npm run frontend:test` / `frontend:test:watch`；首批 22 例（api 9 / i18n 9 / 组件 4）。`vitest.config.ts` 复用 `vite.config.ts` 的 root 与 react 插件 |
| 3 | P1 | **已修** | `.github/workflows/ci.yml`：backend（pytest + ruff，含 `apps/`）与 frontend（typecheck + test + build）两个 job，`concurrency` 取消过期 run |
| 4 | P2 | **已修** | `jsonRequest` 失败时解析 `{"detail": ...}`，支持字符串与 422 的 `loc/msg` 列表两种形状，无可用信息才 fallback `HTTP {status}`。抽成 `errorMessageFromPayload` 并单测 |
| 5 | P2 | **改为守卫** | 15 个端点不硬写 UI（产品决策）。新增 `tests/test_frontend_endpoint_coverage.py`：前端引用必须是后端真实端点；后端无 UI 端点必须登记在 `KNOWN_WITHOUT_UI` 白名单并写明原因；白名单项若已接通 UI 或已被后端删除，测试也会红 |
| 6 | P2 | **已修** | `web-console/app.js` 的 `renderGenerateStages` 与预览确认框两处 `innerHTML` 插值改走既有 `escapeHtml`。全量扫过三个旧页：其余插值要么是数字格式化、要么已在 `list()` / `escapeHtml()` 内处理，无新的真实向量 |
| 7 | P2 | **已修** | `package.json` 依赖从 `latest` 钉到 `^实际版本`（vite 8.1.3 / react 19.2.7 / @types 19.2.x）。`typescript` 从 `7.0.1-rc` 降到 `^5.9.3` 并移到 devDependencies —— 实测 typecheck / test / build 全绿，理由见文末「TypeScript 降版」。（**注：2026-09-11 已升回 `^7.0.2`**，降版前提仅对 RC 成立，见文末「后续变更」；「钉到 `^实际版本` + 移出 devDependencies」这两条仍然有效） |
| 8 | P2 | **已修** | 策划工作台已用 React 重写（详见下方「P2-8 已闭环」），旧 `planning-workbench.html` 已删除。剩余两份旧静态页仅作 dist 缺失兜底 |
| 9 | P2 | **已修** | `ExecutionStageCard` 渲染 `stage.logs`（i18n `stageLogs`），组件已 export 并补 4 例测试 |

### 数字

- 后端：473 → **477 passed**（新增 4 例端点覆盖守卫），`ruff check fantasy_agent tests apps --no-cache` 全绿。
- 前端：**22 passed**（api 9 / i18n 9 / 组件 4），`frontend:typecheck` 0 错，`frontend:build` 1.55s。

### 变异测试（确认真红，非假绿）

| 变异 | 结果 |
|---|---|
| `confirmed_side_effects` 改回硬编码 `true` | 前端红 2 例 |
| 删掉 `stage.logs` 渲染块 | 前端红 1 例 |
| 前端端点改名 `/api/tool-status-typo` | 后端红：端点守卫 |
| 后端新增未登记端点 `/api/new-unwired-endpoint` | 后端红：端点守卫 |

### 顺带发现（非 review 条目）

- i18n 一致性测试**当场抓到一个真 bug**：加 zh 文案时整段替换，把 `manualOpen` / `manualOpenRecommended` 两个 zh 键删掉了 —— 界面会掉回英文。已补回。
- 端点扫描最初把我自己测试里的期望字符串当成真实调用（`"/api/sessions/session%2F..%2Fevil/state"`），误报一次。修法：正则允许 `%`、扫描排除 `*.test.ts(x)`。

### P2-8 已闭环：策划工作台重写完成（2026-09-10 晚）

`planning-workbench.html`（2359 行）已删除，功能由 `apps/frontend/src/workbench/` 下的 React 组件接管。`/workbench` 现在与其它路由一致走 `_frontend_index_or`（dist 优先）。

**旧页的两个真实缺陷，重写时一并修了**：

| 缺陷 | 证据 | 修法 |
|---|---|---|
| 后端 11 个策划工具，旧页只接了 3 个 | `_workbench_tool` 有 11 个 `if name ==` 分支；旧页只调 `extract_idea_seed` / `generate_game_production_plan` / `decompose_production_tasks` | `PlanPanels.PLAN_TOOLS` 暴露全部 10 个计划工具 + 提取工具，共 11 个 |
| 「pacing」「risks」两个区块恒空 | 后端 `GameplaySpec` **没有** `pacing` 字段，`DirectorBuildPlan` **没有** `risks`（旧页读 `spec.pacing.beats` / `plan.risks`） | 改用真实字段 `level_beats` / `failure_states` / `qa_focus` |
| `must_keep` / `can_cut` / `reference_feel` / `playable_loop` 用户改不了 | 旧页把它们放在 `hidden-field` textarea 里，只能由后端回填 | SeedInspector 给四者都加了可见编辑框 |

**补的守卫**：`tests/test_workbench_tool_coverage.py` —— 前端引用的工具名必须是后端真实工具；后端新增工具若没接 UI 会直接红。当前双向 11 = 11，无差异。

**真机验证**（uvicorn 起服务，字节级比对）：

```
dist/index.html   sha 5e7da4f1…   1194 bytes   <script src="/frontend/assets/index-Bi_2-NR5.js">
static/index.html sha a1f222f8…  61088 bytes
/              == dist: True   == legacy: False
/web-console   == dist: True   == legacy: False
/workbench     == dist: True   == legacy: False
```

### 仍未做

- 删 `static/index.html` 与 `web-console/`（约 2875 行，只在 dist 缺失时兜底）。前提是先保证 `frontend:build` 一定跑过 —— 仍是产品决策，没动。

### TypeScript 降版（7.0.1-rc → ^5.9.3）

`7.0.1-rc` 是精确版本号，本身不会漂，但它是**预发布版**：一旦有人删 lock 重建，或者 CI 上 `npm ci` 拿到的 RC 被 npm 撤下，构建就会挂。降到 5.9.3 后实测全绿：

| 项 | 结果 |
|---|---|
| `npx tsc --version` | 5.9.3 |
| `frontend:typecheck` | 0 错 |
| `frontend:test` | 26 passed |
| `frontend:build` | ✓ built in 1.41s |

顺带把它从 `dependencies` 移到 `devDependencies`（构建工具不该是运行时依赖）。~~**要回退**：`npm install -D typescript@7.0.1-rc`~~ —— **此回退指令已于 2026-09-11 作废**（TS 7 已转正，见下方「后续变更」小节；勿再据此装回 RC 或降版）。

### 后续变更（2026-09-11）：TS 7 已转正，重新升回 `^7.0.2`

上一节的降版理由只有一条：`7.0.1-rc` 是**预发布版**，可能被 npm 撤下导致 CI 构建挂。**该理由只对 RC 成立**——2026-09-11 时 `typescript@latest` 已是稳定的 `7.0.2`（Go 原生编译器），风险消失，因此升回 7。上面"要回退到 5.9.3"的结论作废，勿再据此降版。

升级后实测（`npm run` 三关全绿）：

| 项 | 结果 |
|---|---|
| `tsc --version` | 7.0.2（原生 `@typescript/typescript-win32-x64/lib/tsc.exe`，24.5 MB） |
| `frontend:typecheck` | 0 错（纳入 133 个文件） |
| `frontend:test` | 67 passed / 6 files |
| `frontend:build` | ✓ built in 302ms |
| 编译开关探活 | `strict`→TS18047、`isolatedModules`→TS1205、实参→TS2345、`readonly`→TS2540 均按预期报错 |

**跨平台注意**：`typescript@7` 把各平台二进制作为 optionalDependency 分发。lock 中 20 个平台包**必须齐全**（已验证含 `typescript-linux-x64`），否则 CI 的 `npm ci` 在 ubuntu runner 上会找不到可执行文件。

**性能注意**：本项目仅 133 个文件，两份编译器的编译工作量都远小于进程启动开销，因此 TS7 的吞吐优势体现不出来。实测（6 次取区间）：

| 调用方式 | 耗时 |
|---|---|
| `node` 空启动基线 | ~630 ms |
| TS 5.9.3 `node bin/tsc` | ~640 ms |
| TS 7.0.2 原生 `tsc.exe` 直调 | ~730 ms |
| TS 7.0.2 `node bin/tsc`（win32 走 shim） | ~1255 ms |
| `npm run frontend:typecheck` | ~4700 ms（其中 npm 自身开销 ~4150 ms） |

即 TS7 相比 TS5 **净增约 0.6 s**，全部来自 `lib/tsc.js` 在 win32 上无法 `process.execve`（仅非 win32 且 node > 22.15 才走 execve 原地替换），只能 `execFileSync` 再起一个进程。Linux/macOS 的 CI 不受影响。**结论：按此规模不值得为省这 0.6 s 去改脚本直调 exe，保持可移植的 `tsc` 调用即可。**

### P2-8 决策材料：旧静态页的精确边界

复核时发现「两套前端并存」的说法不够准，实际情况是**三份前端代码 + 一个按 pathname 分发的 SPA**：

`apps/frontend/src/main.tsx` 按 pathname 路由 —— 访问 `/web-console` 渲染 `FlowConsole`，访问其它路径渲染 `StudioShell`。所以 StudioShell 里那个 `src="/web-console?embed=1"` 的 iframe 加载的是**新版 FlowConsole**，不是旧页，**不存在自嵌套**。

| 旧页 | 行数 | 何时被用到 | 下线代价 |
|---|---|---|---|
| ~~`planning-workbench.html`~~ | ~~2359~~ | **已删除** —— 由 `apps/frontend/src/workbench/PlanningWorkbench.tsx` 接管，`/workbench` 走 dist 优先 | 已完成 |
| `static/index.html` | 1636 | 仅 `apps/frontend/dist/index.html` **不存在**时兜底（`/` 走 `_frontend_index_or`） | 低：build 过的机器上永远走不到 |
| `web-console/index.html` + `app.js` | 1239 | 同上，仅 dist 缺失时兜底（`/web-console` 走 `_frontend_index_or`） | 低：同上 |

端点层面：旧页只引用 8 个端点，其中 7 个新版也用，**旧页独占的只有 `/api/tools/{tool_name}`**（策划工作台的数据端点）。

所以决策其实拆成了两件独立的事：

1. **删 `static/index.html` 和 `web-console/`**（合计约 2875 行）—— 技术上很便宜，前提是接受「没 build 过时 Studio 只有兜底页或空白」。建议先把 `frontend:build` 放进启动脚本再删。
2. **要不要重写策划工作台** —— 真正的成本项，也是唯一还活着的旧页。这是产品决策，没动。

### 顺带修的（非 review 条目）

- `npm audit` 原本报 2 个 high（`postcss <=8.5.22`、`nanoid <=3.3.17`，均为 vite 构建期传递依赖）。已执行 `npm audit fix` → **0 vulnerabilities**，lock 更新后 build / test / typecheck 全绿。
