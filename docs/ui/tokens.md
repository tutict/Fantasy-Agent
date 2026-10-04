# 设计 token

> 唯一权威来源是 `apps/frontend/src/styles/tokens.css`，由 `main.tsx` 导入**一次**。这份文档解释每个分组是什么、以及改 token 时必须同步动哪些守卫。
> 规矩全文见 `AGENTS.md` 的「前端（apps/frontend）」一节；裸值与断点的硬约束见 `css-conventions.md`。

## 0. 为什么 token 数不许写死在任何文档里

本文件早期版本与 `AGENTS.md` 都写「28 个自定义属性 × 明暗两套」，实际早已漂移了数倍。写死的数字必然再漂，所以本文只写结构与分组，不写数量——包括下面这份清单。

要当前的数量，跑这条命令（它就是 `cssHygiene.test.ts` 的 `declaredTokens` 逻辑）：

```bash
python - <<'PY'
import re, pathlib
src = pathlib.Path("apps/frontend/src/styles/tokens.css").read_text(encoding="utf-8")
light, dark = src.split(':root[data-theme="dark"]')
decl = lambda b: {m.group(1) for m in re.finditer(r"^\s*(--[a-z0-9-]+)\s*:", b, re.M)}
L, D = decl(light), decl(dark)
print("明色", len(L), "暗色", len(D), "明有暗无", len(L - D))
print(sorted(L - D))
PY
```

**明有暗无的那一组应该只有间距、字号、圆角、时长、层级** —— 这是对的，这些不随主题变。出现别的（尤其是颜色）就是错，`tokenOwnership.test.ts` 钉着「暗有明无」为空集，那一边同理。

## 1. 分组

| 组 | token | 用途 |
|---|---|---|
| 字体 | `--font-ui` `--font-mono` `--mono` | `--mono` 是 `--font-mono` 的别名 |
| 间距 | `--space-1` `--space-1_5` `--space-2` `--space-2_5` `--space-3` `--space-3_5` `--space-4` … `--space-7` | 阶梯，见 `css-conventions.md` |
| 控件 | `--size-control` | |
| 圆角 | `--radius-xs/s/m/m-lg/l` `--radius-pill` | 阶梯；`pill` 是 999px 那一档 |
| 字号 | `--text-xs/s/m/l/xl` | 阶梯，明暗同值 |
| 时长 | `--duration-fast` `--duration-slow` | 动效 |
| 层级 | `--layer-sticky/overlay/dialog` | `z-index` 阶梯 |
| 阴影 | `--shadow-s` `--shadow-l` `--shadow` | `--shadow` 是 `--shadow-l` 的别名 |
| 品牌 | `--brand` `--brand-strong` `--brand-soft` `--on-brand` | 氧化铜 |
| 文字 | `--text` `--text-soft` `--text-placeholder` `--muted` `--muted-strong` | |
| 表面 | `--bg` `--surface` `--surface-strong` `--surface-muted` `--chrome` `--chrome-strong` | |
| 输入 | `--field` `--code-bg` `--tab-bg` `--pill-bg` | |
| 线 | `--line` `--line-strong` `--grid-line-a` `--grid-line-b` | |
| 状态 | `--status-running/success/waiting/warning/danger/human/info` + 各自 `-soft` | 7 个互不复用，钉在 `visualSystem.test.ts` |
| 焦点 | `--focus` `--focus-soft` `--focus-ring` | `--focus-ring` 是 box-shadow 表达式 |
| 数据 | `--data-1` … `--data-6` | 图表/序列，非文本 ≥3:1 |

阶梯的档位会随 token 治理增删，所以这里列的是**当前成员**而不是「共几档」。要确认某一档在不在，看 `tokens.css`；要确认它有没有人在用，看 `cssHygiene.test.ts` 的 "does not accumulate tokens nothing reads"。

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

**这一节只写还存在的债。** 已经删掉的不要留在这里——2026-10-04 那一版把 `--text-2xl`、`--field-bg`、`--size-sidebar` 列成「待删」，而它们在这一轮之前就已经从 `tokens.css` 里删掉了，表格却没跟着改，于是它变成了「三个不存在的 token 各欠一次清理」的假债。

判定口径：一条债要成立，得能在 `tokens.css` 里 grep 到那个名字。grep 不到 = 已经还了，从这里划掉。

剩余项：

| 项 | 怎么确认的 | 状态 |
|---|---|---|
| `--layer-overlay` | `grep -- '--layer-overlay:' tokens.css` 有定义；全仓 `var(--layer-overlay)` 零引用 | 零引用，待找 z-index 消费点或删 |
| `--accent-deep` / `--accent-soft` / `--blue*` / `--amber*` / `--danger*` | 全仓有引用 | **保留**：是活跃的兼容层，不是债 |
| `UNREFERENCED_EXEMPT` 里那批（`--data-*` / `--status-*-soft` / `--duration-slow` / `--layer-sticky` / `--layer-overlay` / `--shadow-s` / `--space-6` / `--space-7`） | `cssHygiene.test.ts` 的豁免清单，逐条带理由 | 豁免而非债：调色板先于视图存在，或阶梯的上下界。改豁免清单必须是决定，不是绕过去 |

## 5. 写 token 时的两条纪律

- **明暗成对。** 颜色类 token 必须在 `:root` 与 `:root[data-theme="dark"]` 都定义。`tokenOwnership.test.ts` 断言「暗有明无」是空集——它防的是暗色下残留亮色值。
- **间距与字号只放 `:root`。** 暗色块不重复定义它们，因为间距不随主题变；重复定义等于给「暗色用不同间距」开了一个没人用的口子。
