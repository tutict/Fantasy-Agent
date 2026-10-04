# 设计 token

> 唯一权威来源是 `apps/frontend/src/styles/tokens.css`，由 `main.tsx` 导入**一次**。这份文档解释每个分组是什么、以及改 token 时必须同步动哪些守卫。
> 规矩全文见 `AGENTS.md` 的「前端（apps/frontend）」一节；裸值与断点的硬约束见 `css-conventions.md`。

## 0. 为什么 token 数不许写死在任何文档里

本文件早期版本与 `AGENTS.md` 都写「28 个自定义属性 × 明暗两套」。2026-10-04 实测：**明色 86 个、暗色 64 个**，漂移 3 倍。写死的数字必然再漂，所以本文只写结构与分组，不写数量。

当前实测（2026-10-04）：明色 86 / 暗色 64；**明有暗无的 22 个全是间距、字号、圆角、时长、层级**——这是对的，间距与字号不随主题变。

## 1. 分组

| 组 | token | 用途 |
|---|---|---|
| 字体 | `--font-ui` `--font-mono` `--mono` | `--mono` 是 `--font-mono` 的别名 |
| 间距 | `--space-1` … `--space-7` | 阶梯，见 `css-conventions.md` |
| 控件 | `--size-control` `--size-sidebar` | `--size-sidebar` 是**零引用的历史值**，见 §4 |
| 圆角 | `--radius-s/m/l` | 阶梯 |
| 字号 | `--text-xs` … `--text-2xl` | 阶梯 |
| 时长 | `--duration-fast` `--duration-slow` | 动效 |
| 层级 | `--layer-sticky/overlay/dialog` | `z-index` 阶梯 |
| 阴影 | `--shadow-s` `--shadow-l` `--shadow` | `--shadow` 是 `--shadow-l` 的别名 |
| 品牌 | `--brand` `--brand-strong` `--brand-soft` `--on-brand` | 氧化铜 |
| 文字 | `--text` `--text-soft` `--muted` `--muted-strong` | |
| 表面 | `--bg` `--surface` `--surface-strong` `--surface-muted` `--chrome` `--chrome-strong` | |
| 输入 | `--field` `--code-bg` `--tab-bg` `--pill-bg` | |
| 线 | `--line` `--line-strong` `--grid-line-a` `--grid-line-b` | |
| 状态 | `--status-running/success/waiting/warning/danger/human/info` + 各自 `-soft` | 7 个互不复用，钉在 `visualSystem.test.ts` |
| 焦点 | `--focus` `--focus-soft` `--focus-ring` | `--focus-ring` 是 box-shadow 表达式 |
| 数据 | `--data-1` … `--data-6` | 图表/序列，非文本 ≥3:1 |

**正名与别名**：状态色是正名（`--status-success`），`--ok` / `--warn` / `--accent` / `--blue` / `--amber` / `--danger` 是兼容别名，都用 `var(--status-*)` 转指。**新代码写正名**。

## 2. 对比度由测试钉着

`shared/visualSystem.test.ts` 逐条断言（2026-10-04 全绿）：

- `--text` / `--muted` / `--text-soft` / `--on-brand` / `--on-danger` 对 `--bg` 与 `--surface` **≥ 4.5:1**（正文级）
- `--line-strong` **≥ 3:1**（非文本构件）
- 7 个 status 色 **≥ 4.5:1**、6 个 data 色 **≥ 3:1**
- 24 个配对 token 明暗都必须是 6 位 hex

**改任何颜色 token 之前先跑这条测试**，它会在你改完立刻告诉你对比度破了没有。

## 3. 改 token 的同步清单

| 动作 | 必须同步 |
|---|---|
| 改任何颜色的值 | `visualSystem.test.ts` 的对比度断言会自动验；改完必须跑 |
| **新增或删除** token | `visualSystem.test.ts` 的 `PAIRED` 列表（配对 token 逐条断言 6 位 hex） |
| 新增间距/字号/圆角档位 | `css-conventions.md` 的阶梯表 + `cssHygiene.test.ts`（它从 `tokens.css` 实际值算阶梯，不是写死） |
| 删除 token | 先确认全仓 `var(--x)` **零引用**——`cssHygiene.test.ts` 守卫 3 会抓「定义了没人用」 |
| 改 token 数量 | **不要在任何文档里写数量**（见 §0） |

## 4. 已知的债

2026-10-04 实测的待清理项，本轮或后续处理：

| 项 | 状态 |
|---|---|
| `--space-7: 48px` / `--text-2xl: 34px` / `--field-bg` | 零引用，且被更小的档位覆盖 → 删 |
| `--size-sidebar: 292px` | 零引用；组件实际硬编码 282px（`StudioShell.tsx:107` 内联）/ 82px（折叠）。**292 与 282 不等是漂移不是可用值** → 移到 `.studio-shell` 组件作用域 |
| `--layer-overlay` | 零引用，待找 z-index 消费点或删 |
| `--shadow-s` / `--layer-sticky` / `--space-1` / `--space-6` / `--text-m` / `--radius-s` | 零引用，但正好是本轮值层要启用的档位 → 启用 |
| `--accent-deep` / `--accent-soft` / `--blue*` / `--amber*` / `--danger*` | **保留**：分别在用 2/17/10/10/10/23 处，是活跃的兼容层 |

## 5. 写 token 时的两条纪律

- **明暗成对。** 颜色类 token 必须在 `:root` 与 `:root[data-theme="dark"]` 都定义。`tokenOwnership.test.ts` 断言「暗有明无」是空集——它防的是暗色下残留亮色值。
- **间距与字号只放 `:root`。** 暗色块不重复定义它们，因为间距不随主题变；重复定义等于给「暗色用不同间距」开了一个没人用的口子。
