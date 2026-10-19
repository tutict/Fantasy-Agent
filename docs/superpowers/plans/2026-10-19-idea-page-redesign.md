# 「点子」页重设计：WorkBuddy 式侧边栏 + 对话主区

> 2026-10-19。用户原话：「点子的页面要更改，直接参考 workbuddy 的侧边栏和对话页面，不要在复用旧前端设计，旧前端设计消息密度过重，样式繁杂，根本不利于用户使用」。
> 改的是**布局与样式**，不改行为：访谈状态机、工具闸门、载荷构造、handoff 全部原样（`workbenchModel.ts` 一行不动）。

## 1. 问题：密度从哪来

旧 `PlanningWorkbench` 的密度不是某一个决定，是四层叠加：

| 密度来源 | 旧形状 | 后果 |
|---|---|---|
| 顶栏堆控件 | `wb-topbar` 里 6 个控件（品牌 + 2 chip + 语言/主题 4 个 ghost 按钮） | 首屏最亮的一行是设置，不是内容 |
| 盒中盒 | 双列里**每个区块都是带 head 的 `wb-card`**（会话卡、种子卡、工具卡、计划卡），卡片带边框+阴影 | 四个盒子互相竞争，没有主次 |
| 消息成块 | 每条消息是带边框的 `wb-bubble`，还带一行大写角色标题 | 一问一答被拆成 12 个方框 |
| 双列同时展示 | 左对话右计划，7 个 tab + 2×4 工具网格同屏 | 一屏两套信息架构，都要读 |

参照物（WorkBuddy 自身 UI）的三个特征：**侧边栏承载导航与动作，主区一次只看一样东西；消息是纯文本流；composer 吸底**。

## 2. 新结构

```
.wb-shell（一屏高，grid: 288px | 1fr；≤1100px 断点改为整页滚动 + 顶部横带）
├─ aside.wb-side                    侧边栏（chrome 底，右侧发丝线，自带滚动）
│  ├─ .wb-side-brand                PL 标 +「游戏生产 / 策划工作台」
│  ├─ .wb-side-foot                 语言 / 主题分段控件（data-locale 保留）
│  ├─ .wb-side-status               本地服务 chip + 状态 chip（data-testid=status-chip）
│  ├─ nav.wb-side-nav               「点子对话」（带种子状态）+「计划」组：7 个面板钮
│  └─ .wb-side-tools                「计划工具」+ 提示 + 10 个工具钮（2 列）
└─ .wb-main（grid: head | body | composer）
   ├─ .wb-main-head                 对话态：标题+副标题；面板态：plan-title + 建议行
   ├─ .wb-main-body                 唯一滚动区：错误横幅 +（对话态：线程+种子字段区｜面板态：.wb-panel）
   └─ .wb-composer                  仅对话态：textarea + 发送 + 提示/字数
```

关键决定：

1. **主区二选一，不同时显示。** 对话态 = 消息流 + 种子字段区 + 吸底 composer；面板态 = 计划面板。侧边栏永远可见，所以「确认点子→跑工具」不用切画面。
2. **工具从右列网格搬进侧边栏。** 它们是动作不是内容；禁用态（未确认）在侧边栏里本身就是「先确认」的提示。
3. **消息去框。** AI 消息纯文本（主区头部已写明是谁），用户消息右侧淡底气泡。角色标题删除，`ThreadEntry.title` 随之删除。
4. **种子字段区从卡片改 `<details>` 折叠区。** 默认收起（首屏只剩对话）；种子到达时自动展开（`ingest` 里 `setSeedOpen(true)`），用户也可手动收起。字段在 DOM 里常在，编辑/确认行为不变。
5. **提取种子不切画面。** `resultPanel` 仍会把 `extract_idea_seed` 映射到 overview，但只有非提取工具才 `setMainView("plan")`——提取的答案属于对话。
6. **locale/theme 分段控件留在工作台自己的侧边栏**（外壳侧边栏可折叠到 82px，那时它的语言/主题开关是 `display:none`；且 `/workbench` 测试是脱离外壳挂载的，`data-locale` 必须还在工作台里）。**位置在品牌区正下方、不在侧边栏末尾**：截图发现 10 个工具钮在 1440×900 下把页脚挤到折叠线以下；这两个还是外壳折叠后仅剩的带文字开关。
7. **错误从面板内 `<p class="wb-empty">` 改为主区顶部横幅**（`role="alert"`），两种态都可见；状态 chip 仍在侧边栏。
8. **≤1100px 用整页滚动，不用一屏高应用外壳。** 侧边栏变成顶部横带后，「一屏高 + 主区内部滚动」把 composer 和种子区压瘪在约 200px 里；改为 `.wb-shell height:auto/min-height:100%`、`.wb-main min-height:60vh`、`.wb-main-body overflow-y:visible`，窄屏就是普通文档流。

## 3. 逐文件改动

| 文件 | 改动 |
|---|---|
| `workbench/DiscoveryThread.tsx` | `ThreadEntry` 去掉 `title`；`wb-bubble` → `wb-msg`（AI 无框 / 用户右对齐气泡）；滚动自贴逻辑不动 |
| `workbench/SeedInspector.tsx` | `wb-card` 外壳 → `details.wb-seed`；`wb-field-row` → `wb-field-grid`（主字段 `minmax(240px,1fr)`、配置行 `minmax(150px,1fr)`）；标签改常规字体重量（不再是 xs 大写）；新增 `seedOpen` / `onSeedOpenChange` props；字段 id 全部保留 |
| `workbench/PlanPanels.tsx` | `ToolActions` 从卡片改 `.wb-side-tools` 块；`data-tool` 顺序与禁用逻辑原样；`GddPanel`/`DslPanel` 不动 |
| `workbench/PlanningWorkbench.tsx` | 新外壳；新增 `mainView`（"chat"｜"plan"）与 `seedOpen` 状态；`ingest` 增加「种子到达→展开字段区」「非提取工具→切计划态」；线程条目去掉 title、计划就绪条目带上计划名；错误横幅进主区；`useLocaleTheme()` 那行按原缩进保留（FE4-3 的针脚） |
| `styles/workbench.css` | 删 `wb-topbar/wb-brand/wb-eyebrow/wb-grid/wb-column/wb-card/wb-tabs/wb-tab/wb-bubble/wb-field-row` 与文档级 reset；新增侧边栏/主区/消息/折叠区/composer/分段控件；共享面板规则（`wb-block/wb-row/wb-pill/wb-empty/wb-pre/wb-script*`）与 `wb-button/wb-chip/wb-tool-grid/wb-thread/wb-field/wb-actions` 保留或改样式；`--surface-strong` 改由 composer 引用（否则删 `.wb-card` 会留孤儿 token） |
| `shared/i18n.ts` | 删 `aiName`/`userName`/`promptLabel`；加 `navIdea`/`navPlan`/`send`；`readyToExtract` 文案「检查右侧字段」→「检查下面的点子字段」（字段不在右边了） |
| `workbench/PlanningWorkbench.test.tsx` | `send()` 的按钮文案 `Initial idea` → `Send`；新增「提取种子后字段区自动展开且留在对话」用例 |

## 4. 守卫

- 既有守卫全部原样依赖：`PlanningWorkbench.test.tsx` 的 `discovery-thread` / `Question 3 of 6` / `data-tool` 全集与顺序 / `data-panel-button` / `[data-panel]` / `plan-title` / `status-chip.error` / `data-locale` / 字段 id / handoff。
- `StudioShell.test.tsx` 依赖工作台根节点含「策划工作台」——新侧边栏品牌位保留 `navPlanning`。
- `localeOwnership` / FE4-3：不写 `documentElement`、不读 embed、`useLocaleTheme()` 行原样。
- `panelStyles.test.ts`：共享面板 class 不动，`wb-empty`/`wb-pre` 保留。
- **新增**：`cssHygiene.test.ts` 的 pairs 补 `workbench/PlanningWorkbench.tsx`、`workbench/DiscoveryThread.tsx`、`workbench/SeedInspector.tsx`、`workbench/PlanPanels.tsx`（§5 要求「每一个发静态 className 字面量的组件」都在清单里，workbench 四个文件一直不在，本次补齐）。
- **新增变异用例**（`scripts/mutation_check_frontend_guards.py`）：
  - FE12-1 `SeedInspector` 类半改名（`wb-seed-body`→`wb-seed-panel`）→ cssHygiene pairs 红
  - FE12-2 删 `ingest` 里的 `setSeedOpen(true)` → 新用例红
  - FE12-3 发送按钮硬编码 `Send` → `send` 键孤键 → panelI18n 红

## 5. 验收

```bash
npm run frontend:typecheck
npm run frontend:test        # Windows：大写盘符 cwd 跑法
npm run frontend:build
python scripts/mutation_check_frontend_guards.py   # FE12-1..3 全 caught，红因逐条核
python scripts/run_tests.py                          # 全量 pytest + ruff
python scripts/run_tests.py tests/test_product_name.py
```

人工验收（截图）：首屏只剩对话 + 侧边栏；发三条消息后线程是纯文本流；提取后字段区自动展开；确认后侧边栏工具解禁；点「任务」主区换成任务面板；切中文/深色仍只在侧边栏；窗口 <1100px 时侧边栏变成顶部横带。

## 6. 执行结果

2026-10-19 当天完成，全链绿（布局修正后又整体重跑过一遍）：

| 检查 | 结果 |
|---|---|
| `npm run frontend:typecheck` | 通过 |
| `npm run frontend:test` | **347/347**（33 个文件；较基线 +1，即新增的「种子到达自动展开且留在对话」用例） |
| `npm run frontend:build` | 通过（CSS 65.95 kB / JS 407.28 kB，`index-DfVcV-3F.css`） |
| `python scripts/mutation_check_frontend_guards.py` | **42/42 caught**（39 条既有 + FE12-1..3 新三条），每条红因均为点名测试断言失败，全部源文件 sha256 逐字节还原 |
| `python scripts/run_tests.py` | **954 passed / 2 skipped / 0 failed**（与基线一致）+ ruff 全绿 |
| `python scripts/run_tests.py tests/test_product_name.py` | 6 passed（文案改过，按 AGENTS.md 补跑） |

人工验收（Edge headless 截图，studio 服务 `127.0.0.1:7865` 提供新 dist）：

- **1440×900 深色中文**：首屏只剩侧边栏 + 对话——欢迎语、「第 1/6 题」+ 问题纯文本、收起的种子折叠行（「点子预览与修改 / 由 AI 模型提取的点子 / 草稿」）、吸底 composer（输入框 + 发送 + Enter 提示 + 0/2000）。消息区无框无盒，密度显著下降。
- **1024 窄屏**：侧边栏变顶部横带，整页滚动，横带 → 对话 → 种子区 → composer 依次可达。

截图过程发现并修掉两处布局问题（两处修完都重跑了 typecheck/test/build + 复截图）：

1. **语言/主题分段控件原本在侧边栏末尾**，1440×900 下被 10 个工具钮挤到折叠线以下。移到品牌区正下方（`.wb-side-foot` 去掉 `margin-top:auto`）——它还是外壳侧边栏折叠到 82px 后仅剩的带文字开关，位置必须保证永远可见。
2. **≤1100px 原本沿用「一屏高应用外壳」**，侧边栏横带约 440px 把主区挤到约 200px，composer 与种子区被压瘪。改为整页滚动（`.wb-shell height:auto/min-height:100%`、`.wb-main min-height:60vh`、`.wb-main-body overflow-y:visible`）。

截图是过程性证据，存在 `%TEMP%\fa-run\`（`idea-v2-dark.png` 1440×900、`idea-v3-narrow-tall.png` 1024×1700），不随提交保留。
