# 流程控制台（/web-console）

> 「流程控制台」是**操作台，不是营销首页**。玩法输入归策划工作台；这里负责载入交接、检查执行准备度、记录纠偏、跑无头试玩、把手改接回来看。
> 界面结构与约定见 `architecture.md`。

## 它是什么

`/web-console` 是 `StudioShell` 里的 `console` 面板，**不是一个独立应用**。

- 组件：`apps/frontend/src/console/FlowConsole.tsx`
- 样式：`console.css`，与 `studio.css`（外壳）**在同一页共存** —— 所以两边都有 `button`、`.primary-action` 之类的同名选择器，靠各自的作用域分开，不是两套应用。
- 路由：`StudioShell.tsx:44-48` 的 `PANEL_ROUTES` 把它映射到 `/web-console`；`panelFromPathname()` 解析。
- 启动：随 Studio 一起，`scripts/start-fantasy-agent.ps1` 或 `apps/studio/desktop.py` 双击入口都包含它。**没有独立的启动命令**（本文旧版写的 `--app-dir apps/web-console` 目录不存在）。

## 两个 tab

| tab | 内容 |
|---|---|
| `review` | 执行前体检：`ReviewPanel`（`console/rendering.tsx`） |
| `specs` | Spec Bundle + 重新生成并对比（`SpecBundlePanel` + `SpecRegenPanel`） |

tab 只有 2 个。2026-09-18 之前这里有 10 个（overview / tasks / build / visuals / gdd / dsl …），它们与策划层重复，已在 F5 删掉 —— **重复实现本身就是第二真相**。

## 右侧栏（与 tab 无关）

三张 rail-card 常驻：资产执行、demo 生成 + 返工 + 试玩、活动日志。**「生成工程」与「试玩」都在这里**，不在 tab 里。

## 它做什么

| 能力 | 说明 |
|---|---|
| 载入策划交接 | 从 localStorage 的 handoff key 读；`decodeStoredHandoff()` 区分 empty / invalid / handoff / plan 四态 |
| 执行前体检 | 展示 spec、构建计划、审批清单，并指出未就绪项 |
| 执行确认 | 资产执行、demo 生成、无头试玩都走**两段式确认**：先列 `planned_side_effects`，人点了才起进程。**前端不得写死 `confirmed`**（`AGENTS.md` 全局规则） |
| 无头试玩 | Godot headless 真跑若干局，采集时长分布与失败原因，未达标项翻译成返工目标。**只验结构可玩性下限，不判「好不好玩」** |
| 手改回扫 | 报告哪些产物被手改过、哪些数值被改过。**只报告不动文件** —— 下次生成本来就会覆盖，报告的职责是让覆盖发生前可见 |

## 它不做什么

- **不写 spec、不改策划**：那是 `/workbench` 的事。
- **不判「好不好玩」**：试玩是 bot 跑脚本化路径，只能验目标可达、失败可解释、能重开、时长落在区间。测不出乐趣，报告里 `goal_notes` 每次都把这句写明。
- **不替用户确认**：任何会起进程/写文件的调用，确认标记必须来自界面上的用户动作。

## 边界（不变）

- UI 不调用外部模型服务。
- UI 不自动执行 Unreal、Godot、Blender 或 ComfyUI 生产任务。
- 打开本地软件或生成目录属于显式点击触发的手动纠偏实际操作，只允许固定 allowlist 目标。
- MCP 执行必须保持显式确认，并通过 MCP 层记录日志。

## 状态外置

四个面板内联在同一 document，切走**不卸载**（`visitedPanels`）。因为 console 有在飞的 job 轮询，卸载就是丢进度。代价是访问过的视图永久挂载、DOM 只增不减 —— 详见 `architecture.md` §1.1。

## 相关测试

| 文件 | 断言什么 |
|---|---|
| `console/FlowConsole.test.tsx` | 执行阶段卡渲染（stage 名/状态/日志/产物） |
| `console/FlowConsole.approval.test.tsx` | 两段式确认门：取消不调后端、确认后才带 `true` |
| `console/playtestPanel.test.tsx` | 试玩门控 + 报告卡 + 纠偏报告卡 |
| `console/recovery.test.tsx` | 失败后能改输入或续跑 |
| `console/specRegen.test.tsx` | spec 重生成面板的 diff 规则 |
| `console/hooks.test.ts` | `promptRequestFromPlan` 的两条推断（prompt 重建、平台猜测） |
