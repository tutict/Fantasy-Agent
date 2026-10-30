# CSS 约定

> 这份是写样式时的硬约束。`shared/cssHygiene.test.ts` 把其中四条钉成测试，改样式前先跑一遍看它报什么。
> token 本身见 `tokens.md`，界面结构见 `architecture.md`。

## 1. 不写裸值

`styles/*.css`（除 `tokens.css`）里**不得出现**裸的 `#hex`、`rgb(`、`hsl(`。颜色、字号、间距、圆角一律走 token。

- `.tsx` 侧同规则由 `visualSystem.test.ts` 守住；CSS 侧由 `cssHygiene.test.ts` 守卫 1 守住。
- 2026-10-04 之前 CSS 侧完全裸奔：`studio.css` 一家就有 5 处 `var(--accent, #hex)` 形式的**误导性 fallback**（那个 `--accent` 明暗两块都定义了，所以 `#hex` 那个值从不渲染，但它让人以为焦点环是亮蓝色的）。这类代码比硬编码更坏：它看起来已经归了 token。那个 `--accent` 连同整套旧名别名已于 2026-10-19 退役并删除。

## 2. 阶梯

| 类别 | 允许的值 | 来源 |
|---|---|---|
| 字号 | 4 档：`--text-xs` 11px / `--text-s` 14px / `--text-l` 16px / `--text-xl` 24px | `tokens.css` |
| 间距 | `--space-1` 4 / `-1_5` 6 / `-2` 8 / `-2_5` 10 / `-3` 12 / `-3_5` 14 / `-4` 16 / `-5` 24 / `-6` 32 / `-7` 48 | `tokens.css` |
| 圆角 | 6 档：`--radius-xs` 2 / `--radius-s` 6 / `--radius-m` 10 / `--radius-m-lg` 12 / `--radius-l` 16 / `--radius-pill` 999px | `tokens.css` |

**间距一律就近取整到阶梯**，不新增 5/7/9/11/13/18px 这类孤值。间距是**关系**，错 1px 会累积成布局抖动。

**例外只有两类，且都在 `cssHygiene.test.ts` 的 `NOT_SPACING` 里逐条带理由列出**（豁免必须是一条决定，不是一个更松的正则）：

| 值 | 用在哪 | 为什么不在阶梯上 |
|---|---|---|
| `2px` / `3px` | 标签与其下方文字之间（`.eyebrow`、`.rail-title`、`.studio-topbar p`） | 全产品最紧的间距，是刻意的。放到 4px 标签就与它标注的东西脱开了 |
| `7px` / `9px` / `11px` | 控件自身的横向内边距（`.handoff-chip`、`.wb-tab`、`.wb-composer textarea`） | 夹在 6 和 10 之间。在控件内部，相邻元素和字号一样决定了这个内边距该是多少；给三处各补一档会把三个无关控件耦合到彼此的尺寸上 |
| `18px` | 控件组之间的间距（`.top-bar`、`.or-plan-meta`、`.studio-topbar`） | 比 16 宽半档、比 24 窄半档，它读起来是「一个间距，比紧凑的那个宽一点」 |
| `1px` | 滚动容器的焦点环留白 / 日志行之间的分隔线 | 前者是让焦点环画在框内，后者是分隔线不是留白 |

**不要为了消灭豁免而给阶梯补这些档。** 阶梯一旦变成 4/6/7/8/9/10/11/12…的密集数表，token 就比数字本身没多提供任何东西——那时该问的是这些控件是否真需要各自不同的内边距。

**例外：单侧边框宽度 1px / 2px / 3px 保留**——状态条的语义宽度不是间距。

**字号不就近**：只允许落在那 4 档上。`12px` 与 `13px` 曾经并存（40 + 36 次，占字号声明的 55%），两值视觉几乎不可区分却制造同屏两种渲染质量。**这两个值都是退役的**：`visualSystem.test.ts` 的「keeps the type scale in steps big enough to tell apart」直接点名 12 与 13 不许再作为一档回来——只写「相邻档差 ≥ 2px」是拦不住的，删掉一档之后 11/14/16/24 的间距是 3/2/8，把 14 改回 13 变成 2/3/8，两种都全过。

（这一版曾列 6 档含 `--text-2xl`，又列过 5 档含 `--text-m`。两个 token 都已经不在 `tokens.css` 里了，而表格比代码多活了两档——**表格里的 token 名必须能在 `tokens.css` 里 grep 到**，这条由 `docsTokenNames.test.ts` 钉着。）

## 3. 焦点环：唯一来源是 `ui.css`

```
ui.css   .ui-button/button/a/input/select/textarea/summary/iframe:focus-visible
         → outline: 2px solid var(--focus-ring-color); outline-offset: 1px
         + box-shadow: 0 0 0 4px var(--focus-soft)（外层光晕）
         + @media (forced-colors: active) 兜底
```

**其余 `styles/*.css` 一律不得再写 `:focus-visible` 或 `:focus`**——`cssHygiene.test.ts`的「keeps the focus ring in one place」钉着，变异用例 FE6-10。

**这条规则的理由不只是「整洁」**：四张视图样式表都被导入**同一个 document**（`console.css` 从 `FlowConsole.tsx` 导入，`studio.css` 从 `StudioShell.tsx`，以此类推），所以写在 `console.css` 里的 `:focus-visible` **从来不是 console 私有的**——它落在全应用每个字段上，只是待在一个名字说不然的文件里。2026-10-04 的值层治理恰好新增了两条这样的规则（字段的边框与背景反馈），它们从来不是局部的；已搬进 `ui.css` 紧邻共享环的那条规则，视觉零变化。

- **环是 outline，不是 box-shadow。** 它曾经是 `box-shadow: 0 0 0 3px rgba(20, 63, 56, .28)`——半透明阴影叠在亮色暖纸上合成后只有 **1.64:1**，键盘用户基本看不见。**调 alpha 救不回来**：扫 0.28 / 0.55 / 0.70 / 0.80 得 1.64 / 2.01 / 2.71 / 3.46，要提到 0.80 才过 3:1，那时环是一块实心板。根因是暖纸底亮度 L≈0.93，半透明叠加只能小步移动亮度。**实色 outline 不受底色影响**：亮色 `#0d2b26` 最差 11.61:1，暗色 `#cf9a4a` 最差 5.31:1（`focusRing.test.ts` 逐个表面算，不是声称的）。
- **暗色的环色不能用暖色系。** 聚焦时 `input` / `textarea` 的边框会提成 `--line-strong`（暗色 `#c4a48c`），环与它只差 1.08:1。实测六个候选：暖色系（`#cf9a4a` / `#e8863a`）都撞在这 1.08–1.14 上；能拉开的（青 `#8adcee` / 石灰 `#b6d94a`）改为撞**状态色**——距 `status-human` 1.00、距 `status-success` 1.03、距 `status-danger` 1.01。**「读作边框变粗」比「读作状态标签」轻**，所以留在暖色，并由守卫钉住这个取舍。
- `--focus-soft` 保留为外层光晕，所以环仍然读作环而不是边框。环自己的对比度是硬要求（≥3:1，`focusRing.test.ts` 逐表面算）；光晕只需 ≥1.1。
- **`forced-colors` 兜底是必须的**：Windows 高对比度模式下浏览器会丢弃 box-shadow，只留 outline。那块**原本就是兜底**（因为环是 shadow），现在 outline 本来就在，两者语义终于一致。
- 例外：`.api-field textarea` 上的 `outline: none` 可以留（它去掉的是 UA 默认环，与共享 outline 配对），**但必须紧邻 `:focus-visible` 规则**，否则单焦点时没有环。

## 4. 断点：4 档栅格

| 值 | 语义 |
|---|---|
| 1360px | 三栏 cockpit → 两栏 |
| 1100px | 侧栏折叠，双栏 → 单栏 |
| 900px | 全局单栏 |
| 560px | 手机 |

**所有 `@media (max-width: Npx)` 的 N 必须 ∈ 这四个。** `cssHygiene.test.ts` 守卫 4 钉着。

**断点不做成 token**：`@media` 不接受 `var()`，写成 `--bp-*` 就是零引用死 token，与「零引用 token 是债」自相矛盾。所以它们是文档约定 + 测试断言，不是 token。

`orchestration.css`（编排板）**有意不加媒体查询**：它的每一行容器都是 `flex-wrap: wrap` 的单列流式布局，没有任何多列 grid 或固定宽度，所以窄屏下自然折行。它没有"窄屏塌成两栏"的问题要解决。**不要为了对齐而给它加一个空断点。**

## 5. 命名与归属

- 一个 class 只属于一张样式表。共享面板（`shared/panels/`）统一 `wb-*`，其 class 必须在 `workbench.css` 有定义。
- console 私有类不加前缀；`playtest-*` / `rework-*` / `correction-*` / `manual-*` 四种都表示「带状态列表的侧面板」，写法保持一致。
- **CSS class 不带视图名**：没有 `.workbench-*`、`.console-*`、`.orchestration-*`。判断新 class 归哪张表看它属于哪个面板，不看它在哪个文件里。
- 状态类用 `X-state` 形态由模板字符串发出（如 `playtest-${status}`、`rework-${status}`），这类**不算死样式**——静态 grep 会误判。
- **状态不要再写成第二个 class**：`wb-chip ${status}` 这种写法是词汇表读不到的拼写，它必然导致那张表里再长出一小套映射（2026-10-19 收敛前有 11 条这样的）。状态一律走 `data-status`，颜色去 `ui.css` 取。

## 5.1 状态 → 颜色：只有一个地方知道答案

```
[data-status="running"]  ─┐
[data-state="current"]   ─┤  ui.css 的一张表  ──►  --tone / --tone-soft
[data-decision="…"]      ─┤                        组件只负责「涂在哪」
[data-permission="…"]    ─┘
```

- 四个属性名是**一张表的四种输入**，不是四套映射。`data-status` 跑生命周期、`data-state` 跑旅程步和可用性、`data-decision` 跑人的裁决、`data-permission` 跑工具权限。
- 组件规则读 `var(--tone, <自己的中性色>)`。**fallback 是组件自己的**，它决定「没有状态时我长什么样」；**取值是词汇表的**，它决定「这个状态是什么颜色」。
- 组件必须先在 `ui.css` 的 `:where(...)` 读者名单里关掉继承，否则一个没带状态的 pill 会捡起父元素的 tone。
- **affordance 和 report 不是一回事**：一个 pill 报告「已批准」是 success；一个你按下去去批准的按钮不是「已批准的东西」，它是品牌色的可点提示。所以 `.or-button[data-decision="approved"]` 不读词汇表——这是唯一两条留在表外的映射，各自在原地写了理由。
- 改之前先跑 `python scripts/ui_metrics.py --json` 看 `state_mappings_outside_vocabulary`（当前 2，就是上面那两条）。**这个数涨了就是有人又自己造了一套。**

## 5.2 组件族：合并还是保留

判据只有一条，写在文件里而不是留在口头上：

> 两个成员**视觉可区分**吗？可区分 → 保留（`.journey-header` 就该和 `.pane-section-header` 不同）。不可区分 → 合并。

**「不可区分」要拿规则体证明，不能凭名字像。** 2026-10-19 核过 `-note` 族 5 个成员：都是「弱化的小字段落」，差异在 `margin` 与 `font-size`（`--text-xs` vs `--text-s`、上下外边距各差一档）。**这是漂移，不是设计** —— 但要合并就要同时改 5 个组件的外观，那是设计决定，不是清理，所以本轮没动。判据留在这里，等有人愿意承担视觉改动时照它执行。

## 6. 加新样式前的检查

1. 这个值在阶梯上吗？不在 → 加 token 或就近取整，别写裸值。
2. 这个颜色有 token 吗？没有就在 `tokens.css` 明暗**成对**加，而不是在组件里硬编码 + 留 fallback。
3. 这个 class 属于哪张表？跨表就是设计错误。**「谁渲染它」说了算**：只有 console 渲染的留在 `console.css`，两个视图都渲染的必须进 `ui.css` —— 视图表只在首次访问该视图时才注入文档，所以 `/workbench` 上 `console.css` 的类是裸的。
4. 这个状态的颜色是自己写的吗？是 → 挪进 `ui.css` 的词汇表，见 §5.1。
5. 焦点环、`@media` 断点、reduced-motion 里有重复实现吗？分别是 `ui.css`、4 档栅格、`ui.css` 全局那一条。
6. 改完跑 `npm run frontend:test`、`python scripts/ui_metrics.py --check` 与 `python scripts/mutation_check_frontend_guards.py`。前端 CI 也会执行 UI Metrics 预算检查，预算变化必须随代码一起审阅。
