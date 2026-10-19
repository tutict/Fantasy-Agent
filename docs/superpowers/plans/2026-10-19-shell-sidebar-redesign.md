# 外壳侧边栏重设计：从「盒子墙」到一条导航

> 2026-10-19。用户原话：「请推翻原设计文档中的现有侧边栏方案，针对其不雅观、不够简洁的问题，提出更优雅、简洁的替代设计」，附外壳侧边栏截图（深色中文、默认宽度）。
> 本文件是**修订版方案**，内容按「可直接替换现行侧边栏方案」写：替换对象是 `studio/StudioShell.tsx` 的侧边栏部分 + `styles/studio.css` 的 `.studio-sidebar*` 规则 + `docs/ui/architecture.md` §1 对外壳导航的描述。
> **为什么没有「原设计文档」可改**：`2026-09-16-frontend-ui-replan.md` §3.3 白纸黑字写着「不做视觉重设计：配色、`[data-theme]`、既有版式保留」，此后 `3af5854`（2026-09-25）的视觉 + 旅程重构**没有落文档**。现行侧边栏从来没有过成文方案——本文件补上这份依据，并按替换写。

## 0. 一句话

现行侧边栏是一面墙：导航主体是带边框的卡片，语言/主题是两枚全宽控件占着顶部黄金位，「设置」「资产」是两枚收起态比展开态更丑的大空盒，底部还挂着一块给开发者看的路由调试信息。修订后它只做一件事——**告诉你你在哪、能去哪**；设置退位到页脚，盒子全部拆除，分隔只靠发丝线与留白。

## 1. 原方案缺陷（逐条带证据）

| # | 缺陷 | 证据 | 后果 |
|---|---|---|---|
| 1 | **盒子套盒子，没有一处留白** | `.studio-nav button` 是 46px 带边框+底色卡片（`studio.css:165-177`）；`.locale-switch/.theme-switch` 各一枚外框（`:133-142`）；`.ui-disclosure` 给「设置」「资产」各一个带边框+padding 的盒（`ui.css:202-207`）；`.studio-status` 是盒，里面还套一个 `<code>` 小盒（`:205-227`） | 一个侧边栏四层盒子互相竞争，没有主次——「不雅观」的直接来源 |
| 2 | **设置控件占着导航位** | 语言（EN/中文）、主题（深色/浅色）是两枚**全宽分段控件**，排在品牌正下方、旅程六步之上（`StudioShell.tsx:231-247`） | 首屏最该回答「我在哪、能去哪」，实际先看到两枚设置；六步被整体下推 |
| 3 | **Disclosure 用错了地方** | 「设置」3 项、「资产」1 项都用 `<details>`；`.ui-disclosure` 的边框+padding 让**收起态是一个大盒子装一行字**（截图里两枚巨型空盒）；资产只有 1 个条目，根本不需要折叠分组 | 折叠交互本身没错，错在折叠态比展开态更丑；分组制造了它要解决的空间问题 |
| 4 | **状态三重表达** | 每个旅程项同时有：编号圆圈的颜色/形状（`studio.css:739-743`，current 圆、complete/blocked/attention 方角）、`data-state` 属性、「当前/之后」文字行（`.nav-state`） | 同一信息三种说法，视觉噪音；编号圆圈在行里再套一个圆圈/方块 |
| 5 | **底部挂调试信息** | `.studio-status` 把当前面板名 + 路由路径（`<code>/workbench</code>`）放在侧边栏底部，由 `panelEndpoint()` 供给（`StudioShell.tsx:285-288, 446-454`） | 这是路由表，不是产品状态。用户的位置已由导航高亮 + 主区标题说明；`<code>` 把终端样式带进了界面 |
| 6 | **hover 与「你在这里」同规则** | `.studio-nav button:hover, .studio-nav button.active` 是**同一条规则**（`studio.css:179-184`） | 鼠标划过和当前面板长得一样，当前态没有从视觉上跳出来 |
| 7 | **类名跨表竞争，胜负由打包顺序决定** | `.locale-switch/.locale-option/.theme-switch/.theme-option` 有**两个活消费者**：外壳侧边栏（`StudioShell.tsx:231-247`）和 console 顶栏（`FlowConsole.tsx:483-507` 的 `SegmentedControl`，默认类名就是这两个——`FlowConsole.parts.tsx:42-43`）。两套定义分别住在 `console.css:239-299`（40px 带边框）和 `studio.css:133-158`（36px 无框）。已实测构建产物：console 的规则在前、studio 的在后 ⇒ **今天赢的是 studio——于是 console 顶栏那两个控件一直被 studio.css 悄悄改扮成 36px 无框，而这不是谁的决定，是导入图顺序送的**。另：`.brand-mark` 同样是两个活消费者——外壳品牌标（`StudioShell.tsx:213`「灵」）与 console 顶栏品牌标（`FlowConsole.tsx:467-468`「FA」）——两处定义（`console.css:86` 与 studio.css 主体 + 724 追加块），studio.css 排后 ⇒ console 的「FA」标一直被悄悄改扮成 44px 实心品牌方块，而 `console.css:86` 要的是 40px `--accent-soft` 淡底 | 外壳控件长什么样取决于用户访问过哪些面板、取决于 import 顺序调整；console 顶栏控件今天就已经被改错了样式而无人察觉。`parts.test.tsx` 的注释自己记着「`active` 是个三张表都定义的类」——同一个病，第三次 |
| 8 | **矮窗口下内容被裁且够不着** | `.studio-sidebar` 是 `overflow: hidden`（`studio.css:62-73`），没有滚动 | 视口矮时底部内容直接消失，没有滚动条可以够到它 |
| 9 | **品牌三件套 + 一圈死代码** | 品牌行 = 44px 标 + 两行文字（`本地工坊`/`灵构工坊`）+ 40px 折叠钮；`panels` map 的 `icon` 字段（`StudioShell.tsx:28-36`）无人读取，`.nav-icon` 规则（`studio.css:186-195`）无任何元素渲染 | 一个产品名拆两行；死代码让下一位读者以为图标系统已经存在 |
| 10 | **与页内 chrome 两种语言** | 外壳是盒子风；`2c323c9`（2026-10-19）刚把「点子」页重设计为行式侧边栏（无盒、竖条高亮、页脚设置） | 同一产品两层 chrome 各说各话——用户刚在新页面里习惯的语言，一出面板就被外壳推翻 |

## 2. 修订后的设计

三条原则，后面所有决定都从它们推出来：

1. **侧边栏只做导航。** 设置（语言/主题）退出导航位，去页脚；调试信息删除。
2. **分隔用线与留白，不用盒子。** 侧边栏内不再有任何「带边框 + 底色」的容器；唯一的实色元素是品牌标（身份）与当前项的一条竖条（位置）。
3. **一层 chrome 一种语言。** 行高、控件尺寸、标签样式与刚落地的「点子」页侧边栏逐项相同（`--size-control` 行高、36px 分段选项、xs 大写小标题）。

### 2.1 布局结构

```
.studio-shell（grid: 侧边栏 | 主区，100vh——外壳骨架不动）
┌─ aside.studio-sidebar（默认 240px，可拖 220–430，折叠 82px；overflow-y:auto）─┐
│  品牌行：灵  灵构工坊                              〈（折叠钮）              │
│  ───── 发丝线 ──────────────────────────────────────────────────────────  │
│   1   点子                          ●    ← 当前项：竖条 + 淡底 + 粗体      │
│   2   计划                              （● = 状态点，见 2.4）             │
│   3   编排                                                               │
│   4   执行                                                               │
│   5   审阅                                                               │
│   6   质量                                                               │
│  ───── 发丝线 ──────────────────────────────────────────────────────────  │
│   资产                          ●    一行，与旅程行同形（无编号）           │
│   设置（xs 大写小标题，无盒）                                              │
│      MCP 服务 ／ API ／ Agent    三行，与旅程行同形（缩进一档）             │
│  ───── 发丝线 ──────────────────────────────────────────────────────────  │
│  页脚（margin-top:auto 吸底，可随滚动到达）                                │
│    ┌ EN │ 中文 ┐  ┌ 深色 │ 浅色 ┐     两枚紧凑分段，36px 选项              │
│    本地工坊                   text-xs 弱化小字（productLabel 退位至此）    │
└──────────────────────────────────────────────────────────────────────────┘
```

行规格（全部走 token，无裸值）：

| 元素 | 规格 |
|---|---|
| 旅程行/资产行/设置行 | `min-height: var(--size-control)`（44px，与页内导航行一致）；无边框、无底色；`padding: 0 var(--space-2_5)`；`border-radius: var(--radius-s)` |
| 编号 | 纯文字（不再是圆圈），20px 列宽，`--muted`，当前项转 `--text` 并加粗；折叠态它就是图标 |
| 状态点 | 6px 圆点，`margin-left: auto` 右对齐；实心/空心按状态（2.4） |
| 当前态（`.active`） | 左侧 2px `--brand` 竖条（`border-left`）+ `--accent-soft` 淡底 + 标签 `--text` 加粗 |
| hover | `--surface-muted` 淡底，与 active 的 `--accent-soft` 是两种底色（补缺陷 6；与页内 `.wb-nav-item:hover` 同款） |
| 小标题（设置） | `--text-xs` + `--muted` + 大写 + 字距，与页内 `.wb-side-label` 同规格 |
| 页脚分段 | 轻容器（1px `--line` 边 + `--surface` 底 + `--radius-m` + `--space-1` 内距），选项 36px + `--radius-s`，active = `--accent-soft` 底 + `--accent` 字——与页内 `.wb-seg` 同款 |
| 品牌标 | 40px / `--radius-m` / 字重 900 / `--line-strong` 细边；外壳用 `--brand` 实心（身份），页内用 `--accent-soft`（退让）——**同一条规则两个参数，不是两套规则** |
| 折叠钮 | 32px 无框图标钮，`--muted`，hover 淡底；不再用 `<`/`>` 之外任何装饰 |

品牌行只留产品名（`brandName`）；`本地工坊`（`productLabel`）退到页脚做弱化小字——描述信息不丢，但不再占两行品牌位。

### 2.2 视觉风格

- **零盒子**：侧边栏内唯一的边框是发丝线（分组分隔）与品牌标的细边；唯一的实心形状是品牌标、当前项竖条、状态点。
- **一个高亮态**：当前项 = 竖条 + 淡底 + 粗体，三件事一起做，和「merely hover」明确区分（hover 用 `--surface-muted`，当前项用 `--accent-soft`，两种底色）。
- **命名空间收编**：外壳控件全部收进 `studio-*`（`.studio-side-foot` / `.studio-seg` / `.studio-seg-option` / `.studio-nav-dot` / `.studio-nav-index` / `.studio-brand-mark`）。改名之后 `console.css` 的 `.locale-*` / `.theme-*` / `.brand-mark` 只剩 console 顶栏一个消费者，`studio.css` 的新规则只剩外壳一个消费者——**两个活消费者不再共用类名，跨表竞争到此为止**（缺陷 7 的修法）。收编后三个 chrome 三套命名各归各的表：外壳 `studio-seg`、页内 `wb-seg`（`2c323c9` 已建）、console 顶栏 `locale-switch`。`.brand-mark` 的收编方向是**外壳让名**：它留给 console 顶栏的「FA」标，外壳的「灵」标改名 `.studio-brand-mark`——`cssHygiene.test.ts` 新增守卫钉住「两表不得定义同名类」，白名单只有 `mcp-state` / `primary-action`（既有病灶，登记不修）与 `.active`（只以 `.x.active` 形态出现，从来不是键类）。
- **暗色只换色不换形**：所有尺寸/间距/圆角走 token 阶梯；`studio.css` 里 724–751 那段后来追加的单行规则块**并入主体并去重**（`.brand-mark` 从 4 处定义回到 1 处）。
- **状态色只走 status token**：`--status-running/success/danger/waiting`，与 `visualSystem.test.ts` 的「7 个 status 色互不复用」共存，不引入新色。

### 2.3 交互逻辑

| 交互 | 行为 | 与现行的差异 |
|---|---|---|
| 点旅程/资产/设置行 | 切面板 + `pushState`（`selectPanel` 原样） | 无 |
| 折叠钮 | 82px 图标态：隐藏文字/点/页脚/品牌名，保留品牌标 + 编号列；宽度与折叠态持久化 | 无（针脚 `id="sidebar-toggle"` 保留） |
| 拖拽 resizer | 220–430px，持久化 | 无（针脚 `sidebar-resizer` 保留） |
| 语言/主题 | 即时切换，`data-locale` / `data-theme-choice` 针脚保留 | 位置从顶部两枚全宽控件 → 页脚两枚紧凑分段 |
| 侧边栏滚动 | **新增**：`overflow-y: auto`，矮窗口下页脚随滚动可达 | 修缺陷 8（原 `overflow: hidden` 会裁剪） |
| 行钮提示 | 每个行钮加 `aria-label`（折叠态文字被 `display:none`，屏读得靠它）+ `title` tooltip | 新增 |
| ≤900px | 侧边栏变顶部横带（既有断点，不新增）：旅程/设置行改 `repeat(auto-fit, minmax(150px, 1fr))` 横排网格，页脚分段横排；`journey-nav` 的 `<details>` 折叠能力保留（summary 仅窄屏可见） | 版式跟随新行规格，交互不变 |

折叠态说明：不引入图标系统——**编号就是折叠态的图标**（旅程的身份是「第几步」，顶栏 `JourneyHeader` 同样编号，语言一致）。配 `aria-label`/`title` 补全可读性。

### 2.4 信息层级

| 层 | 内容 | 视觉重量 |
|---|---|---|
| L1 身份与位置 | 品牌行（这是什么）；旅程**当前项**高亮（你在哪） | 最重：唯一实心品牌标 + 唯一竖条 |
| L2 可去之处 | 旅程六步（顺序即生产流程）→ 资产 → 设置三项 | 中：等重量的行，靠顺序与分组表达结构，不靠盒子 |
| L3 状态 | 每行右侧 6px 点：current=`--status-running` 实心／complete=`--status-success` 实心／blocked=`--status-danger` 实心／attention=`--status-waiting` 实心／upcoming=空心圈 | 最轻的一点信息，替代原来的「编号配色 + 文字行」三重表达 |
| L4 环境 | 语言/主题分段 + 「本地工坊」弱化小字 | 最轻：xs 字号、muted、吸底 |

两个「当前」必须分开，别合并：`.active`（竖条）= **你正在看的面板**；`aria-current="step"` + 状态点 = **旅程进度走到哪**。现行实现已经是这个语义（测试钉着：点「执行」后 `.active` 在 execute，`aria-current` 仍留在 plan），修订只换视觉，不并语义。

## 3. 行为面边界（一根都不能碰）

这些是测试钉住的针脚，重设计只换它们的**视觉外壳**：

- `StudioShell.test.tsx`：`[data-target="…"]` 行钮可点可切；`.studio-nav` 容器类名 + 行钮 `active` 类名（"restores the handed-off project" 直接查询 `.studio-nav button.active` 并映射 `data-journey`）；`data-journey` + `data-state` + `aria-current="step"`；`data-locale="en"/"zh-CN"`；`data-theme-choice`；`screen.getByText("设置")`（设置标签必须是可见文字——小标题即可）；六步标签文字（点子/计划/编排/执行/审阅/质量）；`planning-workbench` testid；frames 的 `data-panel`/`data-frame`。
- `tests/test_studio_app.py`（读发布源码）：`data-locale="en"`/`"zh-CN"` 字面量、`"sidebar-resizer"`、`id="sidebar-toggle"`、`data-target={key}` 绑定、`useState<PanelKey>(panelFromPathname)`、`activePanel, setActivePanel] = useState<PanelKey>(`、`panels` map 的 `workbench: { titleKey:` / `console: { titleKey:` 条目、`id="mcp-refresh"`、`id="mcp-status-grid"`、`getMcpStatus`、`mcpStatusTitle`、无 `<iframe`、字典无 `FrameTitle`、`workbench: "策划工作台"` / `console: "流程控制台"` 标签。
- 存储键 `fantasy-agent-studio-sidebar-width` / `-collapsed`（test_studio_app.py:488-489 钉）。
- `visitedPanels` 切走不卸载、`panelHref` 双分支、ErrorBoundary 包网格不包 section——全部不动。

## 4. 逐文件改动

| 文件 | 改动 |
|---|---|
| `studio/StudioShell.tsx` | 品牌行收成一行（标 + 产品名 + 折叠钮）；品牌标类名 `brand-mark` → `studio-brand-mark`（让名给 console 顶栏的「FA」标，见 §2.2）；locale/theme 两枚全宽控件移入页脚并改名 `studio-seg`（aria-label 收进字典，见 i18n 行）；两个 `Disclosure` 删除——「设置」改小标题 + 常驻三行，「资产」改单行；删 `.studio-status` 整块与 `panelEndpoint()` 函数；旅程钮内部从「圆圈编号 + 两行文字」改为「文字编号 + 状态点」，删 `.nav-state` 文字行；行钮加 `aria-label`；资产行补一枚空心状态点与旅程行同形；`panels` map 删无人读取的 `icon` 字段 |
| `styles/studio.css` | 侧边栏区块按 §2 重写；724–751 追加单行块并入主体并去重（`.brand-mark` 回到 1 处定义，随后随让名改为 `.studio-brand-mark`）；删 `.studio-status`/`.locale-*`/`.theme-*`/`.nav-icon`/`.nav-index`/`.nav-state` 旧规则，新增 `.studio-side-foot`/`.studio-seg`/`.studio-seg-option`/`.studio-nav-dot`/`.studio-nav-index`；`--sidebar-width` 默认 282→240（无盒后 240 足够，resizer 范围与已存宽度不变）；`.studio-sidebar` 加 `overflow-y: auto`；≤900px 规则随新行规格更新 |
| `styles/console.css` | **零改动**。`.brand-mark`（`:86`）**不是死规则**——`FlowConsole.tsx:467-468` 渲染着 console 顶栏的「FA」标，外壳让名后它只剩这一个消费者，定义原样保留；`.locale-*` / `.theme-*` 规则同样保留，服务 console 顶栏的 `SegmentedControl`。预期后果：console 顶栏的语言/主题控件与「FA」标回到 console.css 的原意样式（40px 带边框、40px 淡底标），这是对被 studio.css 意外改扮的**修正**，截图验收时属可见变化 |
| `shared/ui/primitives.tsx` + `styles/ui.css` | `Disclosure` 导出随唯一使用方归零而删除；`.ui-disclosure` 两条规则同删（实现时先 grep 确认无其他引用方与测试引用） |
| `shared/i18n.ts` | 新增 `interfaceLanguage` / `themeSwitch` 两个 aria-label 键（en: "Interface language" / "Theme"；zh-CN: 「界面语言」/「主题」）——现行 aria-label 是硬编码英文，中文界面下屏读播英语；删 `assetsNavLabel`（资产分组标签随单行化消失，留着就是孤键，panelI18n 会红）；`productLabel` 移页脚后仍在用，`journeySettings` 改作小标题仍在用 |
| `workbench/PlanningWorkbench.tsx`（同轮，两行） | 两处硬编码 `aria-label="Interface language"`/`"Theme"` 改用同一对键——补上轮留下的小不一致，保两层 chrome 一种语言 |
| `studio/StudioShell.test.tsx` | **预计零改动**（§3 针脚全保留）。若 `getByText("设置")` 因小标题改动受影响，改 role 查询而非改针脚本意 |
| `docs/ui/architecture.md` §1 | 补一段侧边栏信息层级（L1–L4）+ 指向本方案；§2 面板表 workbench 行不变 |

## 5. 守卫与验收

**新增守卫**（归属 `shared/cssHygiene.test.ts`，实现时定）：

1. **跨表同名即红**：`console.css` 与 `studio.css` 不得定义同一个「独立键类」（该类是规则键复合选择器里唯一的简单选择器；`.studio-topbar .journey-header` 这类上下文override 与 `.x.active` 这类修饰态不算——前者特异性定胜负、后者从来不是键类）。白名单 `KNOWN_SHARED` 只有 `mcp-state` 与 `primary-action`（既有病灶：console 的阶段列表/运行钮与外壳的 mcp 面板跨表共享，登记不修，各带理由）。另钉外壳侧边栏控件确有自己的命名：`.studio-seg`/`.studio-seg-option`/`.studio-nav-dot`/`.studio-nav-index` 必须在 studio.css 有定义，`.locale-*`/`.theme-*`/`.brand-mark` 必须不在（缺陷 7 的针脚）。
2. **高亮态有牙**：`.studio-nav button.active` 的规则必须含 `border-left` 或 `::before` 形态，且不得与 `.studio-nav button:hover` 并回同一条选择器列表——竖条被删、或两者合并，即红（缺陷 6 的针脚）。
3. **状态不丢**：`.studio-nav-dot` 基础规则在（空心圈），`[data-state="current|complete|blocked|attention"]` 四条着色规则各从一个 `--status-*` token 取色，`upcoming` 不得有着色规则（空心即它的表述）——「改纯文字行」回潮即红（缺陷 4 的针脚）。渲染侧由 `StudioShell.test.tsx` 新用例「marks every journey row with one state dot, and no text of its own」补：每个旅程行钮恰好一个 `.studio-nav-dot` 且无文字，资产行一枚空心点。

**新增变异用例**（`scripts/mutation_check_frontend_guards.py`，FE13 组，共 4 条）：FE13-1 删当前行竖条 → 守卫 2 红；FE13-2 studio.css 把 `.locale-switch` 加回外壳分段控件规则 → 守卫 1 红；FE13-3 TSX 把页脚分段控件类名改成 `locale-switch`（只改渲染方）→ pairs 检查红；FE13-4 删旅程行状态点渲染 → 新用例红。每条红因逐条核（点名测试断言失败），跑完 sha256 逐字节还原。

**验收命令**：

```bash
npm run frontend:typecheck
npm run frontend:test        # Windows：大写盘符 cwd 跑法
npm run frontend:build
python scripts/mutation_check_frontend_guards.py   # FE13-1..4 全 caught
python scripts/run_tests.py                          # 954 passed / 2 skipped 基线 + ruff
python scripts/run_tests.py tests/test_product_name.py
```

**人工验收**（Edge headless 截图，studio 服务提供新 dist）：

- 1440×900 深色中文展开态：侧边栏只剩品牌行 + 六步 + 资产 + 设置三行 + 页脚；**没有一个带边框的盒子**；当前项有竖条；hover 与当前项可区分。
- 82px 折叠态：只剩品牌标 + 编号列 + 折叠钮；tooltip/aria-label 可读。
- 1024 窄屏：顶部横带，旅程行横排网格，页脚分段横排。
- 中/英 × 明/暗 四态：aria-label 跟随语言；明暗只换色不换形。
- 访问过 `/web-console` 再回外壳：外壳侧边栏视觉与首访一致，且 console 顶栏控件只被 console.css 打扮（缺陷 7 的回归检查：两个 chrome 的控件各归各的表）——console 顶栏的语言/主题控件回到 40px 带边框、「FA」标回到 40px `--accent-soft` 淡底（今天它们分别是 36px 无框与 44px 实心品牌方块，这是被 studio.css 改错后的修正，属预期可见变化）。

## 6. 明确不做

- **不动主区**：顶栏 `JourneyHeader` 仍显示六步进度——它与侧边栏的有意冗余（一个是导航入口、一个是进度上下文），不合并。
- **不引入图标系统**：折叠态用编号当图标（见 2.3）。
- **不新增断点**：窄屏继续用既有 900px；断点白名单 {1360,1100,900,560} 不动。
- **不动任何行为**：路由、`visitedPanels`、ErrorBoundary、`panelHref`、locale/theme 单一 owner、存储键——本方案是纯视觉修订。
- **不收敛 console 顶栏的语言/主题开关**：它与外壳侧边栏是同一设置的两个入口（`FlowConsole.tsx:483-507`），理想形态是只留外壳一处。那是行为变更，超出「侧边栏重设计」范围，登记为后续；本方案只保证两处控件不再跨表抢样式。console 顶栏的「FA」品牌标（`FlowConsole.tsx:467-468`）同理：样式定义原样保留，只是不再被外壳的类名打扮。
- **不重开配色**：暖纸色 + 氧化铜方向不变（`visualSystem.test.ts` 钉着），只拆盒子。

## 7. 执行结果（2026-10-19）

| 项 | 结果 |
|---|---|
| `npm run frontend:typecheck` | ✓ |
| `npm run frontend:test` | 351 passed（347 + 3 守卫 + 1 外壳用例） |
| `npm run frontend:build` | CSS 65.51 kB（改前 65.95 kB） |
| `mutation_check_frontend_guards.py` | 46/46 caught；FE13-1..4 全红 |
| `scripts/run_tests.py` | 954 passed / 2 skipped（基线不变） |
| `tests/test_product_name.py` | 6 passed |
| Edge headless 截图 | 1440×900 深色中文展开 / 82px 折叠 / 880px 顶部横带 / 1440×900 浅色英文 / console 顶栏回合 / hover vs active |

**与方案的偏差，逐条**：

1. **`console.css` 从「删死规则」改为「零改动」**。方案 §1/§4 称 `console.css:86` 的 `.brand-mark` 是无元素渲染的死规则。实现时 grep 渲染方发现 `FlowConsole.tsx:467-468` 渲染着 console 顶栏的「FA」标——它是活规则：`.brand-mark` 一直是**两个活消费者**跨表竞争（外壳「灵」+ console「FA」），console 的标被 studio.css 悄悄改扮成 44px 实心品牌方块，而 `console.css` 要的是 40px `--accent-soft`。修法随之从「删」改为「**让名**」：外壳的标改名 `.studio-brand-mark`，`console.css` 原样保留。教训与上一轮相同：**判「死」之前先 grep 渲染方**。构建产物已核实：`index-*.css` 里 `.brand-mark` 只剩 console.css 一条（40px 淡底），`.studio-brand-mark` 是外壳自己的一条。
2. **FE13 变异用例 3 → 4 条**：补 FE13-4（删旅程行状态点渲染 → 外壳新用例红），让守卫 3 的渲染侧也有自己的变异体——原三条只覆盖了 CSS 侧。
3. **守卫 1 的白名单是 `mcp-state` 与 `primary-action` 两条**（既有病灶，各带理由，登记不修）。`.active` 不在名单里：它只以 `.x.active` 形态出现，从来不是键类，守卫的提取逻辑天然不报它。
4. **窄屏验收口径**：§5 原文写「1024 窄屏：顶部横带」，但横带断点是既有的 900px（§6 明确不新增断点）——1024px 下侧边栏仍是左侧列，横带截图取 880px。口径随实现修正为「≤900px」。
5. **FE6-4 的 needle 随宽度默认值搬家**：它原钉 `--sidebar-width: 282px`（本次 282→240），更新为 240px 后重跑 caught——守卫的形状没变，只是锚点换了行。

截图（Edge headless，studio 服务提供新构建的 dist）：1440×900 深色中文展开态（品牌行 + 六步 + 资产 + 设置三行 + 页脚，无一个带边框的盒子，当前项有竖条）；82px 折叠态（品牌标 + 编号列 + 当前行条）；880px 顶部横带（旅程行 auto-fit 横排、页脚分段横排、`journey-nav` summary 可见）；1440×900 浅色英文（aria-label 跟随语言，明暗只换色不换形）；访问过 `/web-console` 后回外壳（console 顶栏的「FA」标与语言/主题控件只被 console.css 打扮）；hover vs active 对比（hover 的 `--surface-muted` 暖灰底 vs 当前的 `--accent-soft` 淡底 + 品牌竖条——hover 无法由 headless 截图真实触发，该图用同一 token 复现 hover 规则的底色，规则本身由守卫 2 钉住）。
