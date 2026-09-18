# 前端 UI 重新规划

> 状态：F0 已落地；F1 已全部落地（2026-09-18，`2dfe487` + `99d16e4` + `ad8adf3` + `fa7b702`，含删 console 重复 tab）；**F5 第一步已落地**（2026-09-18，`d73762a`：`apps/studio/static/` 退场 + `_frontend_index_or` 响亮失败 + 测试依赖修完）；F2–F4 待定，F5 剩余两项（文档）待定。
> 上游依赖：`docs/superpowers/plans/2026-09-16-internal-pi-task-orchestration.md`——编排 Task 2–6 会改变这个界面**必须显示什么**。
> 本文所有数字都是本轮实测，复现命令见 §5。

## 0. 一句话

**界面不缺功能，缺的是"同一件事只有一个说法"。** 三处入口各自实现同一批面板，契约里已有的字段有两处没人渲染，三份样式表各带一套颜色 token，而上上代的手写前端还挂在盘上、还作为静默回退被服务。

## 1. 实测现状

### 1.1 三个入口，三套面板词汇表

| 入口 | 位置 | 行数 | 面板 |
|---|---|---|---|
| Studio 外壳 | `apps/frontend/src/studio/StudioShell.tsx` | 642 | 5 个导航项（workbench / console / mcp / api / agent），**前两个是 iframe** |
| 策划工作台 | `workbench/PlanningWorkbench.tsx` + `PlanPanels.tsx` | 483 + 427 | 8 面板：overview / pipeline / tasks / build / visuals / gdd / qa / dsl |
| 流程控制台 | `console/FlowConsole.tsx` + `rendering.tsx` | 982 + 503 | 10 个 tab 分 4 组：plan(overview/pipeline/tasks)、assets(review/visuals)、delivery(build/specs/qa)、docs(gdd/dsl) |

外壳把两个应用**同时挂在 DOM 里**（`studio.css:312-329`，非 active 只是 `display: none`），于是两边各自从 localStorage 读 locale / theme、再靠查询参数（`?locale=&theme=&embed=1`）对齐，"策划 → 执行"的交接靠 `localStorage["fantasy-agent-planning-handoff"]`。

实测两处不对等：`embed=1` 只有 `PlanningWorkbench.tsx:76` 读，**控制台那一份从来没人读**。

### 1.2 六个面板实现了两遍（500 行）

| 组件 | `console/rendering.tsx` | `workbench/PlanPanels.tsx` |
|---|---|---|
| BuildPanel | 50 | 37 |
| OverviewPanel | 40 | 101 |
| PipelinePanel | 55 | 56 |
| QaPanel | 16 | 13 |
| TasksPanel | 42 | 28 |
| VisualsPanel | 30 | 32 |
| **合计** | **233** | **267** |

两侧各有一份只属于自己的（console：`ReviewPanel` / `SpecBundlePanel` / `selectedEngineVersion` …；workbench：`GddPanel` / `DslPanel` / `ToolActions`），但共有的 6 个是同一件事的两种写法：类名不同（`.wb-pill` vs `.stage-pill` / `.task-pill`）、字段覆盖面不同（§1.3）、本地化 helper 不同（`localizedTitle` vs `localizedStageTitle` + `localizedTaskTitle`）。

另有两处 helper 分裂：

- `usesGodotEngine()` **两份逻辑相同**的实现（`workbenchModel.ts:336`、`rendering.tsx:43`）。
- `selectedEngineVersion()` **两份逻辑不同**的实现：`StudioShell.tsx:597` 手解 localStorage JSON，`rendering.tsx:47` 读 plan——同一个问题两个真相。

### 1.3 契约里有的字段，UI 不渲染

| 字段 | 后端 | `types.ts` | 渲染处 | 本轮 |
|---|---|---|---|---|
| `PipelineStage.depends_on` | 有 | **原来没有** | **0**（task 行渲染了，且 console 只显示条数） | 补类型 + 两面板 |
| `PipelineStage.kind` | 有（编排 Task 1 加） | 有 | **0** | 两面板加「人工闸门」 |
| `PipelineStage.risks` | 有 | 有 | 只有 console | workbench 补上 |

先例：`ExecuteStage.logs` 也曾"类型承诺、UI 丢弃"，`FlowConsole.test.tsx:30` 的注释记着这件事。

**这不是疏忽的集合，是一个没有守卫的类别**：`types.ts` 里加一个字段，不会被任何东西要求它被渲染。

### 1.4 三份样式表，各带一套 token

| 样式表 | 行数 | 定义的 token | 说明 |
|---|---|---|---|
| `console.css` | 1690 | 28 | `:root` + `:root[data-theme="dark"]` 各 28 行 |
| `workbench.css` | 553 | 28 | **与 console.css 逐字节相同** |
| `studio.css` | 652 | 18 | 只含上面 17 个 + 独有的 `--sidebar-width` |

`console.css` ∩ `workbench.css` = 28 个 token，值**全部相同**，差异数 0 → **112 行纯重复**。三份都被 `main.tsx` 静态 import，全站生效（没有 CSS Modules、没有 scoped），所以"哪个文件是 token 的准"没有唯一答案。

**现在一致不是因为有人守着它，是因为还没人只改其中一份。** 一次主题调色漏掉一份就会分叉，而没有任何检查会发现。

（本轮做过一次"引用了但没定义的自定义属性"扫描，`console.css` 只命中 `--mono`，它带着 fallback（`var(--mono, ui-monospace, …)`）——**误报**，记在这里以免下次重跑再被骗一次。）

### 1.5 上上代前端还在盘上，而且仍然会被服务

| 文件 | 字节 |
|---|---|
| `apps/studio/static/index.html` | 61,088 |
| `apps/studio/static/web-console/index.html` | 12,440 |
| `apps/studio/static/web-console/app.js` | 49,322 |
| `apps/studio/static/web-console/styles.css` | 23,128 |
| **合计** | **≈ 146 KB 手写前端** |

`main.py:151` 的 `_frontend_index_or()`：`apps/frontend/dist/index.html` 不存在时**静默**返回这些手写页，而 `/`、`/web-console`、`/workbench` 三个路由都走它；`/studio-static` 与 `/assets` 两个 mount 也还指着它们。

后果：忘跑一次 `npm run frontend:build`，用户看到的是**另一套五天前的 UI**——它能正常渲染、正常调 API，只是**不是我们正在改的那个**。

`main.py:813` 的注释自己写着那个手写 workbench 页 "That page is gone"（2359 行的 `planning-workbench.html` 确实删了，`test_studio_app.py:57` 钉着它不存在），但同族的另外两个页面留了下来。

### 1.6 一个因此失去牙齿的守卫

`tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls` 有 16 条断言，形式全是 `X in <遗留 static/index.html> or X in <React 源码>`。

实测 **15 条的左半边就为真**（`data-locale="en"`、`sidebar-resizer`、`id="mcp-refresh"`、`mcpStatusTitle`、`流程控制台`、`策划工作台` … 在手写页里全都有）。左半边恒真 ⇒ **这 16 条断言今天检验的是那个已被取代的手写页，不是 React 外壳**；把 React 外壳里的控件全删掉，测试照样绿。

这和第 1.3 节是同一病灶的两个面：**被检对象还在，但它不是我们要检的那个。**

### 1.7 文档漂移

- `docs/ui/web-console.md:12` 写 `--app-dir apps/web-console`——该目录不存在（真实的是 `apps/studio`）。
- 同文件 21-25 行"通常更推荐通过 Studio 统一入口访问：`http://127.0.0.1:7860`"，与上一段是同一个 URL。
- 该文档只描述"流程控制台"，完全没提 `/workbench`、Studio 外壳，也没提 console 那 10 个 tab 的分组。
- `README.md:193` 的目录注释仍写 `frontend/  # 可选的 React/TSX 面板源码`。

## 2. 编排落地后，UI 得补的账

| 编排 Task | 落地后 UI 必须能做到 | 今天的状态 |
|---|---|---|
| 2 编排器骨架 | 显示**运行时**阶段状态（ready / blocked / running / awaiting_confirmation / done / failed） | 两个 pipeline 面板显示的是**计划产物里的** `status`（生成时写死的 pending / blocked）；console 的"当前阶段"读 `current_stage` 字符串；真实执行状态在 `ExecutionStageCard`（又一套 stage 名） |
| 3 `exit_checks` | 每阶段显示出口校验结果与失败项 | 无 |
| 4 返工闭环 + `ORCHESTRATION_TO_EXECUTOR_STAGES` | 返工挂在**编排阶段**上，并可下钻到执行层 stage | console 的 rework 面板列的是 `sessionState.stages`（`preflight` / `create` / `validate` / `import` / `approval_gate` …）。两套词汇表**今天已经同屏并列**，只是没人把它们接起来 |
| 5 阶段级确认 | 每阶段一个确认动作 | 只有 `AgentPanel` 的全局 `allow_write` / `allow_execute` 两个复选框；计划里的 `requires_confirmation`（2–7 全 true）只是药丸 |
| 6 `owner_agent` → 指令 | 阶段卡显示角色与指令来源 | 只是一个药丸文本 |

一条**已经成立、但还没接线**的对应关系：编排 Task 1 把 `creative_review` 定成唯一的 `kind="human"`，而控制台**已经有**完整的审批 UI（`ReviewPanel` + `POST /api/creative-review/approval-manifest` + manifest 落盘）。那个人工闸门的界面早就在了，只是挂在一个叫 "review" 的 tab 下，与 pipeline 面板之间没有任何连线。

## 3. 重新规划

### 3.1 五条定调

**① 单一入口、三层导航。** Studio 外壳保留，workbench / console 从 iframe 变成同一个 SPA 内的路由。
依据：§1.1——两个应用常驻 DOM、各自读 storage、靠查询参数与 localStorage 字符串同步，其中 `selectedEngineVersion()` 还是第二真相。

**② 一个面板只实现一次。** 6 个共用面板抽到 `shared/panels/`，两侧 import；console 只留执行语义的面板。
依据：§1.2 的 500 行双实现，以及 §1.3——**字段覆盖面已经分叉，这是双实现的必然结果而不是偶然**：两份实现不共享字段清单，就不会共享覆盖面。

**③ `production_pipeline` 只有一个读者：编排板。** 其余面板都不再自己渲染阶段。
依据：现在两处各写一遍阶段行，一处有 `risks` 一处没有，两处都没有 `depends_on` / `kind`。

**④ 设计 token 收敛到 `styles/tokens.css`。** 28 个 token × 2 主题只写一次，其余样式表只剩布局。
依据：§1.4 的 112 行逐字节重复；一致是巧合，不是机制。

**⑤ 上上代手写前端退场。** 删 `apps/studio/static/{index.html, web-console/}`，`_frontend_index_or` 在缺 dist 时**明确失败**（日志 + 一句可读提示），而不是静默端出另一套 UI。
依据：§1.5 + §1.6。**这条不是纯删除**——`test_studio_app.py`（57 / 59 / 60 / 371 / 400 / 419 行）与 `test_web_console_app.py`（21 / 60 行）共 8 处依赖这些文件；而且 §1.6 那 15 条恒真断言，**恰恰要靠删掉它才第一次落到 React 源码上**（其中 `data-target="console"`、`data-target="workbench"`、`fantasy-agent-studio-locale` 三条需要先把 React 分支改成测试能认的形式）。所以⑤ = 删 + 修 8 处依赖 + 修 3 条断言的右半边。

### 3.2 目标结构

```
Studio 外壳（单页，一层路由）
├─ 策划 Planning      /workbench   对话 · 点子种子 · 计划工具 · 计划内容 tab
├─ 编排 Orchestration /pipeline    唯一读 production_pipeline 的地方
│                                  阶段卡：status · kind · depends_on · 工具 · 出口校验 · 确认 · 返工
│                                  human 阶段 → 直接打开审批面板
├─ 执行 Execution     /console     job · session · 执行阶段卡 · 审批 manifest · spec 预览
└─ 设置 Settings                   mcp · api · agent（保持内联，不进路由）
```

### 3.3 明确不做

- 不动后端契约（`contracts.py` 一行不改；编排层改动归那份 plan）。
- 不引入组件库或新依赖（`package.json` 目前只有 react / react-dom / vite / @vitejs/plugin-react）。
- 不做视觉重设计：配色、`[data-theme]`、既有版式保留；本轮只做结构与字段。
- 不做响应式 / 移动端布局（Studio 是本地桌面工具）。
- 不做并行 stage / 多 agent 并发 UI；不动 `agent_loop` 三条边界。

## 4. 任务分解

### F0 让 UI 不再吞字段（**本轮已落地**）

**Files：** `shared/types.ts`、`workbench/PlanPanels.tsx`、`console/rendering.tsx`、`shared/i18n.ts`、`styles/{workbench,console}.css`、`workbench/PlanningWorkbench.test.tsx`、新增 `console/rendering.test.tsx`。

- [x] `types.ts` 补 `PipelineStage.depends_on`（后端一直在发，类型一直丢）。
- [x] 两个 pipeline 面板渲染 `kind === "human"` → 「人工闸门」药丸（虚线边框，读作"这里不执行任何东西"）。
- [x] 两个 pipeline 面板渲染 `depends_on`；workbench 补 `risks`（与 console 对齐）。
- [x] 修掉 workbench 面板里硬编码的 `" stages"`（改走 `stagesCount` 键）、重复的 `recommended` 标签、无标签的 `current_stage`。
- [x] i18n 补 `humanGate` / `stagesCount` / `currentStage` / `projectGoal`（en + zh-CN，`i18n.test.ts` 钉键对齐）。
- [x] 测试：workbench 面板断言人工闸门 / 依赖 / 风险 / 阶段数；新增 `console/rendering.test.tsx` 断言 console 侧同样两件事，并断言没有 human 阶段时**不出现**闸门标记。

### F1 一个面板只实现一次

**Files：** 新增 `apps/frontend/src/shared/panels/`、`console/rendering.test.tsx`、`shared/panelI18n.test.ts`；改 `workbench/PlanPanels.tsx`、`console/rendering.tsx`、`shared/i18n.ts`、`styles/{console,workbench}.css`。

- [x] **先补安全网**（2026-09-18 落地）。console 侧从 10 条 → 32 条（`rendering.test.tsx` 2 → 21 条、新增 `shared/panelI18n.test.ts` 7 条）；前端总计 69 → 95（90 passed / 5 todo）。补了什么见下方「安全网补了什么」。
- [x] **定下合并方向：并集**。两侧同名面板渲染的字段集几乎不重叠（Overview 只共享 4/10 个字段），F1 不是"去重"而是"合并成哪个"。已定：合并后渲染两边全部字段，断言只写一次。
- [x] **逐面板迁到 `apps/frontend/src/shared/panels/`**（2026-09-18，`2dfe487`）。六个面板单实现落地；`console/rendering.tsx` 与 `workbench/PlanPanels.tsx` 改为 re-export，两个入口的导入路径不变。
- [x] **样式类统一成一套**（2026-09-18，`99d16e4` + `ad8adf3`）。共享面板只发 `wb-*`；`console.css` 删掉已无匹配的 `.summary-block` / `.stage-row` / `.task-row` / `.task-board` / `.pipeline-board` / `.overview-grid`（1690 → 1632 行）。**这一步暴露了一个真 bug，见下方「样式归属」**。
- [x] 守卫：同一个导出组件名不得出现在两个文件里。`panelI18n.test.ts` 的 `single implementation` describe 已生效（todo 已解开）；新增 `shared/panelStyles.test.ts` 守样式归属。
- [ ] 删除 console 中与策划层重复的 tab（overview / tasks / build / visuals / gdd / dsl），console 保留 review / specs / 执行面板。**未动，见下方「F1 剩下的这一项为什么没直接做」**。
- [x] 依赖方向修正：`shared/` 不得从入口目录导入，故 `localizedValue` / `localizedArray` / `localizedTitle` / `planDisplayTitle` / `usesGodotEngine` / `selectedEngineVersion` 提到 `shared/planModel.ts`，`workbenchModel.ts` re-export（26 条 model 测试未破）。

#### 迁移抓出的真实缺陷：BuildPanel 漏字段

并集实现时按 workbench 原版的字段顺序排，漏掉了 console 独有的 Unreal `folders` 与两个引擎的 `engine_version`——**数据静默丢失**。安全网抓出（`console/rendering.test.tsx` 的 build 面板断言）。若上一轮没补网，这条会绿着上线。

#### 样式归属：两个入口共用一个组件，样式表却各挂各的

删掉 console 的"死选择器"之后，`/web-console` 的面板**整个失去样式**。根因不是删错了，而是更早的一个假设不成立：

- `workbench.css` 由 `PlanningWorkbench` 导入，而它只在 `/workbench` 挂载；`/web-console` 走 `FlowConsole`，只导入 `console.css`。
- Vite 会把所有样式表合成一个文件，但**只在该模块进入路由的图时注入它的 CSS**。所以 console 路由拿不到 `wb-*` 规则。
- 而当时 `console.css` 里那些"待清理的别名"（`.task-board` / `.pipeline-board` / `wb-row stage-row`）正是唯一给 console 路由上样式的东西。两套类名**各活一半**，任何一张表都不承认。

修法两处：共享面板只发 `wb-*`（去掉三个残留的 console 类名）；`console/rendering.tsx` 紧挨着它 re-export 的面板 `import "../styles/workbench.css"`——样式表和需要它的标记放在一起，而不是取决于用户从哪个路由进来。

守卫 `shared/panelStyles.test.ts`（6 条）双向对比：面板发的每个类名都必须在 console 路由会加载的表里定义；console 自己的表面（stage-strip / insight-row / split-output / review-item / review-inspector）必须留在 `console.css`；以及反转"类名不得回到退役的 console 命名空间"。三条独立断言各做过变异验证（删 CSS 导入 / 把 `task-board` 改回来 / 让 CSS 读成空串），全部报红。

**踩到的坑：`?raw` 读 `.css` 返回空串**（本机 Vitest 5 + Vite 8）。不抛异常，直接让所有对比式断言**真空通过**。所以样式表改走 `node:fs` 读盘，并单加一条"仍能读到选择器"（>20 / >50）的空读护栏。<br>另：`fileURLToPath(import.meta.url)` 给的是正常路径，但 `new URL("..", import.meta.url)` 在 jsdom 下抛 `ERR_INVALID_URL_SCHEME`（旧笔记记过这条），要用 `path.resolve(dirname(...), ...)`。

#### F1 剩下的这一项为什么没直接做

> 删除 console 中与策划层重复的 tab（overview / tasks / build / visuals / gdd / dsl）

这一项暂时没动，因为它是**界面收缩，不是重构**：删掉后 console 只剩 review / specs / 执行面板，操作员唯一的"执行前体检"入口就没了。而 `apps/studio/static/` 底下还有一个**仍在被服务的上一代静态页**带着同一批 tab，删了 console 侧并不删那个。在 F5（静态页退场）之前删，等于把两份界面推向更不一致。当时给工程师的三个选项：

- (a) 现在删，接受 console 变薄；
- (b) 先做 F5 让静态页退场，再一起删；
- (c) 不删，把 console 定位从"全量检视"改成"执行台"，tab 保留只读。

**结论：走了 (b)，2026-09-18 完成，落地情况见 §4 F5。** `_frontend_index_or` 不再回退旧页（`d73762a`），随后删掉 console 的 6 个重复 tab 入口。


#### 安全网补了什么

| 文件 | 条数 | 覆盖 |
|---|---|---|
| `console/rendering.test.tsx` | 21（3 todo） | 6 个共用面板各一条「字段被渲染」+ 空态不炸；pipeline 另有人工闸门 / 依赖 / 质量门 / 风险 / 工具 |
| `shared/panelI18n.test.ts` | 7（2 todo） | 跨字典 key 可用性 + 共享 key 不裂 + 单实现锚点 |

两条通用不变量：面板的 `list()` 空数组渲染「No items」而不是空白区（否则操作员分不清"没有"和"没到"）；缺数据时渲染各面板自己的空壳 id（`#pipeline-output` / `#tasks-output` / …），不渲染半个面板。

#### 迁移时真正的坑：19 个 key 只在 workbench 字典里

`PlanPanels.tsx` 调的 38 个 key 里有 **19 个 `consoleI18n` 完全没有**：`assetNeeds` `comfyui` `confirmRequired` `coreAction` `coreVerbs` `designPillars` `failureStates` `gameplayLoop` `logline` `noPlan` `pacing` `playerFantasy` `projectGoal` `qaFocus` `stagesCount` `toolActions` `toolActionsHint` `unreal` `winState`。

`makeTranslator` 对缺 key 的回退是 `|| key`，所以 console 侧挂上公共面板后会**渲染出字面量 `logline` / `stagesCount`**——不抛异常、不报错、现有测试全绿。这正是 F1 最可能的静默坏法。

已由 `panelI18n.test.ts` 钉住：新增任何一个只落单侧的 key 会立刻报红并指名 key。迁移时把这 19 个 key 补进 `consoleI18n`（en + zh-CN），守卫里的 `KNOWN_CONSOLE_GAP` 缩到空数组，该 describe 就可删。

守卫的 key 提取读**源码文本**（`?raw` 导入），不读运行时模块：esbuild 转换后 `Function.prototype.toString()` 不保证保留 `t("...")` 调用，运行时提取器会静默少报——而少报的守卫比没有更坏。这条已用变异验证：从 `consoleI18n` 删掉 `humanGate`，两条独立断言都报红。

### F2 token 收敛

- [ ] 新增 `apps/frontend/src/styles/tokens.css`（28 token × light/dark），三份样式表 import 它并删掉自己的 `:root` 块。
- [ ] 守卫：除 `tokens.css` 外，任何 `styles/*.css` 不得定义 `--*` 自定义属性。
- [ ] 验证：`frontend:build` 后 dist CSS 里 token 定义处数 = 56。

### F3 编排板（依赖编排 Task 2 落地）

- [ ] 新增 `apps/frontend/src/orchestration/`，把 `production_pipeline` 的渲染从两个 panel 里搬进来（定调③）。
- [ ] 阶段卡从"计划快照"改成"运行状态"：区分计划态与运行态 `status`；`kind="human"` 的阶段给确认入口而不是工具清单。
- [ ] 接入 `ORCHESTRATION_TO_EXECUTOR_STAGES`（编排 Task 4 的产物），阶段卡可下钻到执行层 stage。
- [ ] 出口校验、阶段级确认、返工按钮随编排 Task 3 / 4 / 5 依次接线。

### F4 入口收敛（iframe → 路由）

- [ ] 三个视图改成同一 SPA 的路由。**先定**：保留"切走不卸载"（等价于现在的 `display: none`）还是明确接受状态丢失。
- [ ] locale / theme 单一来源，去掉查询参数传递与没人读的 `embed=1`。
- [ ] `selectedEngineVersion()` 两套实现合一（读 plan）。

### F5 清理与文档

- [x] `apps/studio/static/` 退场 + `_frontend_index_or` 明确失败 + 修测试依赖（2026-09-18）。实测：4 个文件删除、`/studio-static` 与 `/assets` 两个 mount 移除、`_frontend_index_or()` 由「静默回退旧页」改为「dist 缺失 → 503 + 指名 `npm run frontend:build`」。
  - 实际触及 **7 处**测试依赖（不是预估的 8 处）：`test_web_console_app.py` 2 处 + `test_studio_app.py` 3 处 `STATIC_DIR` 引用，外加 2 条被删/改写的测试。
  - 「修 3 条断言的右半边」落地方式与预想不同：3 条断言不是"右半边要改"，而是**左半边（旧静态页）删掉后暴露出右半边本身就写错了**——`data-target="console"` 在 React 里根本不存在（是 `data-target={key}` 由 map 生成）、`fantasy-agent-planning-handoff` 属于 `shared/storage.ts` 而非 console 组件、`fantasy-agent-studio-locale` 是导入常量。原来那个 `or` 让这些错误断言一直由死页兜着。
  - 顺手补了一条 `test_store_keys_are_defined_once_and_imported_everywhere`：`StudioShell.tsx:599` 原先把 handoff key 写成字符串字面量（而非导入 `HANDOFF_KEY`），意味着 key 有两个定义、重命名时 shell 会静默读不到 handoff 而没有任何测试会红。已改为导入，并由新测试钉住。
- [ ] 重写 `docs/ui/web-console.md`（它描述的入口已不存在）或并入 `docs/ui/studio.md`：三层导航、面板归属、`KNOWN_WITHOUT_UI` 的边界。
- [ ] `README.md:193` 目录注释同步。
- [x] 删除 console 中与策划层重复的 tab（2026-09-18，`d73762a` 之后）。原计划删 6 个，实际按计划删 6 个 —— 但**核实后确认 `pipeline` 与 `qa` 同样有 workbench 等价物**（workbench 的 `panelBody()` 对二者都有 case），只是计划当初漏列。工程师定调「按计划删 6 个」，故 `pipeline`/`qa` 保留。
  - 删的是**入口不是实现**：6 个面板的实现都在 `shared/panels/PlanPanels.tsx`，workbench 继续用，一个字没动。console 的 tab 从 10 个降到 2 个（`review` / `specs`）—— 这两个是 console 独有（workbench 完全不引用 `ReviewPanel` / `SpecBundlePanel`）。执行面板（rail）不在 tab 体系内，未受影响。
  - 连带清理：`consoleI18n` 删 13 个死 key（227 → 214）、删死组件 `EmptyState`、删 `setGddLocale` 调用点、删 `console.css` 里 `.empty-state` / `.signal-map` / `.signal-route` / `.signal-dot` / `.dot-a/b/c` / `@keyframes pulse` 整段（CSS 37.10 → 36.09 kB）。
  - 新增守卫 `panelI18n.test.ts` → "console dictionary has no keys nothing calls"：3 条。已变异验证（把 `tabGdd` 塞回字典 → 2 条精确报红并指名该 key）。
    **提取器踩坑**：范围必须同时满足三条 —— ① 含 `shared/panels/`（console 仍渲染其中部分面板，排除会把 `systems`/`tools` 误报为孤儿）；② 排测试文件（测试会把 key 名当字符串列出，制造假阳性）；③ 排 `i18n.ts` 自身。判据要同时认 `t("key")` 直接调用和裸 `"key"` 字面量（`tabGroups` 走 `{t(label)}` 间接解析）。试错三轮才收敛，都写进注释了。
  - **既有死 key 未动**：另有 17 个孤儿（`toggleLog` / `manual*` 系列 / `winState` / `failureStates` 等）是更早的合并遗留，与本轮无关，已登记在守卫的 `KNOWN_DEAD` 里，另开一轮清理。

## 5. 验证

| 项 | 命令 | F0 实测（2026-09-16） | 安全网后（2026-09-18） | 静态页退场后（2026-09-18） | 删重复 tab 后（2026-09-18） |
|---|---|---|---|---|---|
| 前端类型 | `npm run frontend:typecheck` | clean | clean | clean | clean |
| 前端测试 | `npm run frontend:test` | 69 passed | **90 passed / 5 todo（95）** | **103 passed（9 files）** | **106 passed（9 files）** |
| 前端构建 | `npm run frontend:build` | — | ✓ built（29 modules，340.63 kB） | ✓ built（32 modules，335.95 kB） | ✓ built（32 modules，333.25 kB / CSS 36.09 kB） |
| Ruff | `.venv/Scripts/python.exe -m ruff check .` | — | — | All checks passed | All checks passed |
| 读前端源码的后端测试 | `.venv/Scripts/python.exe scripts/run_tests.py tests/test_studio_app.py tests/test_web_console_app.py -q` | **43 passed** | 未动后端，未跑 | **40 passed** | 未重跑（并入全量） |
| 全量后端 | `.venv/Scripts/python.exe scripts/run_tests.py` | 未跑（本轮只动前端资产） | 未跑（同上） | **590 passed / 0 failed（108.16s）** | **590 passed / 0 failed（112.28s）** |

**跑法注意（踩过一次）**：不要给 vitest 传 `--root apps/frontend`。根 `vitest.config.ts` 已经设了 `root: "apps/frontend"`，命令行再传一次会覆盖掉配置里的 `environment: "jsdom"`，回落到 node 环境后 workbench 那 10 条全部报 `localStorage is not defined`——看起来像真回归、其实是跑法错了（20 failed / 49 passed）。正确命令是裸的 `npm run frontend:test`。

## 6. 风险

- **console 的测试面比 workbench 薄得多**：补安全网前是 console 10 条（FlowConsole 4 + approval 4 + rendering 2）、workbench 36 条（PlanningWorkbench 10 + workbenchModel 26）。F1 是纯重构但跨两个入口——**先把 console 的断言补到能承重再动刀**，否则重构会静默改掉 console 的行为而全绿。**2026-09-18 已补**：console 32 条、前端总计 95（90 passed / 5 todo）。
- **iframe → 路由会改变状态生命周期**：现在两个应用常驻 DOM、切走不卸载；改路由后默认卸载，未保存的对话 / 编辑会丢。这是 F4 的第一个待决问题，不是实现细节。
- **删遗留静态页会让 3 条断言立刻变红**（不是"可能"）——它们现在只由 legacy 满足。要连带改测试，别把它当成纯删除提交。
- **F1 与 F3 有顺序依赖**：编排板的字段清单要先定下来再抽公共面板，否则抽完还得再改一遍。

## 7. 与 `docs/architecture/review-2026-09-10-frontend-four-axes.md` 的关系

那份 review 的产物之一是 `tests/test_frontend_endpoint_coverage.py`（后端路由 ↔ 前端调用点的双向守卫，含 15 条 `KNOWN_WITHOUT_UI` 登记）。本轮 §1.3 / §1.6 是同一族但换了个轴：**契约字段 ↔ 渲染点**、**断言左边 ↔ 断言右边**。F0 修了实例，F1 / F2 的守卫是把它变成机制。
