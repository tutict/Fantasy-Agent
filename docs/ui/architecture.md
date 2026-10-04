# 前端界面基线

> 这份是**现行依据**。动界面结构或样式前读它，以及配套的 `tokens.md` 与 `css-conventions.md`。
> 被它取代的是 `docs/superpowers/plans/2026-09-16-frontend-ui-replan.md`（F0–F5，2026-09-25 起被 `3af5854` 超越，仅作历史决策记录读）。

## 0. 现状一句话

`apps/frontend/` 是唯一一代界面（Vite + React/TSX），经 `apps/frontend/dist/` 由 Studio 服务。三条路由对应三个整页视图，设置类面板（工具环境 / API / Agent）内联在同一个外壳里。视觉方向是**暖纸色 + 氧化铜**（`3af5854` 定），本文只记录规则，不重开色系讨论。

## 1. 导航结构

单一根组件 `main.tsx` → `StudioShell` 读一次 pathname，**没有路由库**。

| 路由 | 面板 key | 组件 | 用途 |
|---|---|---|---|
| `/workbench` | `workbench` | `workbench/PlanningWorkbench.tsx` | 策划：只做规划，不写文件不起进程 |
| `/pipeline` | `pipeline` | `orchestration/OrchestrationBoard.tsx` | 编排：`production_pipeline` 的运行状态 |
| `/web-console` | `console` | `console/FlowConsole.tsx` | 执行：执行前体检、确认、试玩、手改回扫 |
| 其它任意路径 | `workbench`（兜底） | — | `panelFromPathname()` 的 default |

- 路由表在 `studio/StudioShell.tsx:44-48`（`PANEL_ROUTES`），路径解析在 `:69-77`（`panelFromPathname`）。
- **兜底是 `workbench`**：任何不认识的路径都渲染策划工作台，不报错也不 404。
- 设置类三个面板（`mcp` / `api` / `agent`）**没有自己的路由**，是 `StudioShell` 内的二级导航（`SETTING_NAV`），共用 `/workbench` 那条路径。
- `basePath()` 读 `import.meta.env.BASE_URL` 并剥掉尾斜杠。**它必须是显式参数而不是内联读取**：`import.meta.env` 编译期内联，测试里恒为真，生产分支否则没有任何测试够得着（它就是这么漏掉一次 404 的）。变异用例 FE4-6 钉住这条。

### 1.1 四面板内联，切走不卸载

四个面板全部**内联在同一个 document 里**。`StudioShell.tsx:127` 的 `visitedPanels` 记录访问过的面板，首次访问即挂载，之后只由 CSS 隐藏、永不卸载（`:308/318/333` 三处条件渲染）。

**为什么不能改成卸载**：console 有在飞的 job 轮询、策划有未保存的对话，都在组件 state 里，卸载就是丢进度。**这不是样式取舍。** 行为面由 `studio/StudioShell.test.tsx` 的 "keeps a visited view mounted once the user switches away" 与变异用例 FE4-5 钉住。

**这条决策的代价**：访问过的视图永久挂载，DOM 与组件 state 只增不减。本仓库目前没有守卫覆盖这个增长，长期使用的内存表现是未验证的。

## 2. 面板归属

| 面板 key | 组件 | 样式表 | 状态 |
|---|---|---|---|
| `workbench` | `PlanningWorkbench.tsx`（468 行） | `workbench.css` + 共享 `wb-*` | — |
| `pipeline` | `OrchestrationBoard.tsx`（470 行） | `orchestration.css`（`or-*`） | **无媒体查询**：它本来就是单列流式布局，加断点只会让它在某个宽度下突然变形 |
| `console` | `FlowConsole.tsx`（已降到千行以内；`Metric` / `AssetList` / `Panel` / `SegmentedControl` 在 `FlowConsole.parts.tsx`，执行阶段/试玩/纠偏三张卡片各在自己目录） | `console.css` + `studio.css` 同页共存 | tab 只有 2 个：`review` / `specs` |
| `mcp` / `api` / `agent` | `StudioShell.tsx` 内联 | `studio.css`（`mcp-*` / `api-*` / `agent-*`） | 设置类 |

样式表的归属判据：**一个 class 只属于一张表**。`shared/panelStyles.test.ts` 钉着共享面板发出的每个 class 必须在 `workbench.css` 有定义、console 私有类必须留在 `console.css`。

## 3. 视觉规则

- **保留暖纸色 + 氧化铜方向**（`--bg: #f3efe6` 暖纸、`--brand: #1f5c52` 氧化铜）。这套的对比度已由 `visualSystem.test.ts` 逐条断言通过，**不重开色系讨论**。
- 状态色不复用品牌色，7 个 status 色互不复用（`visualSystem.test.ts` 钉着）。
- **暗色只换颜色，不换间距/字号/圆角**——间距与字号不随主题变，这是对的，但也意味着任何硬编码的间距在暗色下同样生效，不会被主题掩盖。
- 焦点环唯一来源是 `styles/ui.css`（box-shadow + `forced-colors` 兜底），其余样式表不得再写 `:focus-visible`。**注意四张视图样式表都导入同一个 document**，所以「写在 `console.css` 里」不等于「只影响 console」——`cssHygiene.test.ts` 的 "keeps the focus ring in one place" 钉着，变异用例 FE6-10。
- 字号只有 6 档（`--text-xs/s/m/l/xl/2xl`），间距只有 `--space-*` 阶梯上的值，圆角只有 6 档。细则见 `css-conventions.md`。

## 4. 命名约定

| 前缀 | 归属 | 例子 |
|---|---|---|
| `wb-*` | 共享面板（workbench 与 console 共用） | `wb-card`、`wb-button`、`wb-empty` |
| `or-*` | 编排板私有 | `or-card`、`or-answer` |
| `mcp-*` `api-*` `agent-*` | 设置面板私有 | `mcp-status-card`、`api-field` |
| `playtest-*` `rework-*` `correction-*` `manual-*` | console 私有，四种都表示「带状态列表的侧面板」 | `playtest-panel`、`rework-panel` |
| **无前缀** | console 私有 | `rail-card`、`gate-item`、`pane-section-header` |

历史上有过三套并行前缀（`wb-` / 无前缀 / `or-`），**`/workbench` 前缀是 0 个**——CSS class 不带视图名。判断一个新 class 该用哪套时看它属于哪个面板，不看它在哪个文件里。

`shared/panels/` 里的共享面板统一用 `wb-*`；console 侧通过 `console/rendering.tsx` 紧挨 re-export 处 `import "../styles/workbench.css"` 拿到样式（`panelStyles.test.ts` 钉着这个 import 必须在）。

## 5. 组件拆分判据

**旧判据是「能不能测」，这是循环论证**——测试是拆分的结果，不是前提。按它办的结果是：`ExecutionStageCard` 等 4 个有测试的都拆出去了，`Metric` 却因为「测不到」长期内联在 `FlowConsole.tsx`。

**判据，按序命中即拆**：

1. 被 **≥2 个文件**引用（含测试文件）→ 独立文件 + 必须导出
2. **≥50 行** → 独立文件
3. 携带自己的 CSS 前缀（`or-*` / `mcp-*` / `api-*` / `agent-*` / `wb-*`）→ 独立文件 + 独立样式表归属
4. 有 **≥3 个专属 i18n 键** → 独立文件
5. 被 **≥6 处**使用 → 独立文件

**明确不作为判据**：有没有测试、文件是否过长（长度只触发第 2 条，阈值是 50 行不是 500 行）。

**「独立文件」指的是不在 `FlowConsole.tsx` 里，不一定是自己一个文件。** 这一条以前没写清楚，于是判据和现状看起来打架：判据 1 与 5 说 `Metric` 该拆（它被 3 个文件引用、7 处使用，两条都命中），而结论却说它「留在 `FlowConsole.parts.tsx` 是正确结果」。两句并不矛盾——`FlowConsole.parts.tsx` 就是那个独立文件，`Metric` 已经导出给 `PlaytestReportCard` 用了——但读者只看到矛盾。

判据的**动作**是「移出 `FlowConsole.tsx`」，**不是**「每个组件一个文件」。同一个文件里可以放多个组件，只要它们共用同一个理由被拆出来。当前 `FlowConsole.parts.tsx` 装的是四个无 state、无异步、无路由知识的小组件（`AssetList` / `Metric` / `Panel` / `SegmentedControl`），外加两个纯格式化函数。

`cssHygiene.test.ts` 的 `pairs` 现在列了 7 个组件而不是 2 个——新拆出来的组件漏进去过一次，代价是FE6-1 长期由别的守卫代红。**新增组件要同步加进那个清单**，它不是可选的完备性检查。

## 6. 状态的两个 owner

| context | 位置 | 持有 | 规矩 |
|---|---|---|---|
| `LocaleThemeContext` | `shared/localeTheme.tsx` | locale + theme | **唯一 owner**。provider 外 `useLocaleTheme()` **抛错不回落**——回落会静默重建「两个真相」 |
| `JourneyContext` | `shared/journeyContext.tsx` | 六步生产旅程状态（`idea/plan/orchestrate/execute/review/qa`） | console 私有的作业状态**不属于它**，别塞进来 |

**不加第三个 provider。** 视图私有状态留在视图自己的 hook 里；跨视图才进 context。

## 7. 改界面前要跑什么

```bash
npm run frontend:typecheck
npm run frontend:test        # Windows 上见 AGENTS.md 的大写盘符要求
npm run frontend:build
python scripts/mutation_check_frontend_guards.py   # 改守卫或样式约定时
python scripts/run_tests.py tests/test_frontend_endpoint_coverage.py  # 改后端端点时
python scripts/run_tests.py tests/test_product_name.py               # 改界面文案时
```

新增/改名后端端点后必须跑端点覆盖测试：前端引用不存在的端点会红；后端新增了前端没接的端点必须登记进 `KNOWN_WITHOUT_UI` 并写明原因。
