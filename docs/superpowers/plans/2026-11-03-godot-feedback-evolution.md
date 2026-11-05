# Godot 试玩反馈进化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将试玩失败转为受控数值候选，经复测与人工采用沉淀经验，并让下一次任务消费经验。

**Architecture:** 独立 evolution 库模块承载规则、决策记录和实验控制。Studio 使用既有执行池与取消上下文，流程控制台提供明确确认、报告和采用入口。

**Tech Stack:** Python/Pydantic/FastAPI、Vite/React/TypeScript、原子 JSON 文件，无新增第三方依赖。

**Spec:** `docs/superpowers/specs/2026-11-03-godot-feedback-evolution-design.md`

## Global Constraints

- 保留当前工作区已有未提交玩法改动；本次新增文件和接线独立审阅。
- 仅 Godot 确定性灰盒；三个候选上限，默认总预算 600 秒，用户明确授权整个实验。
- 数值白名单、模型、预算、评测器、执行闸门和 Creative Review 不由模型修改。
- 所有决策文件原子保存；损坏报错；路径段校验；重启不自动重放。
- 后端测试用 `.venv/Scripts/python.exe scripts/run_tests.py`，临时目录保持 OS 临时根；前端 cwd 为 `C:/Users/tutic/IdeaProjects/Fantasy-Agent`。
- 人类文案简体中文优先，中英字典同步；读取三份现行 UI 规则后改组件。

### Task 1: 固定候选、评测和经验库

**Files:** 新建 `fantasy_agent/evolution/{__init__,contracts,candidates,evaluation,library}.py` 和 `tests/test_evolution_core.py`。

**Interfaces:** 使用设计文档的严格模型与纯函数签名，供控制器及 API 消费。

- [x] 先写拒绝缺失样本、伪造 aggregate、退化动作、越界修改、损坏记录和跨任务经验应用的行为测试。
- [x] 执行测试确认预期失败，再实现模型、候选规则、固定评测与原子记录。
- [x] 验证每条候选实际改变当前 bundle 且保持原计划不变；保存失败可见。

```python
accepted, notes = compare_reports(baseline, candidate)
assert not accepted  # 缺失真实采样时不能晋升
updated = apply_changes(plan, changes)
assert updated.production_spec_bundle.numeric.player_move_speed == 9.0
assert plan.production_spec_bundle.numeric.player_move_speed == 8.0
```

### Task 2: 有界实验、真实 runtime 和 Studio 接线

**Files:** 新建 `evolution/controller.py`、`evolution/runtime.py`、`tests/test_evolution_controller.py`、`tests/test_evolution_api.py`；修改 `apps/studio/app/main.py`。

**Interfaces:** 消费 Task 1 的模型、`compare_reports`、候选和库；生产 `run_evolution` 与设计文档列出的六个端点。

- [x] 先写预览零副作用、预算终止、取消、独立 session、人工采用、陈旧计划拒绝和重启恢复测试，执行并看到失败。
- [x] 实现控制器；真实 runner 复用 executor，并将剩余总预算传到 import 与 playtest 进程边界。
- [x] 接入现有执行池与取消 scope；采用只消费服务端已验证候选，经验不继承执行确认。

```python
result = run_evolution(EvolutionRequest(plan=plan), experiment_id='probe', workspace_root=tmp_path,
                       run_iteration=lambda *_: (_ for _ in ()).throw(AssertionError('executed')))
assert result.status == 'confirmation_required'
assert not (tmp_path / 'generated').exists()
```

### Task 3: 质量步骤的操作闭环

**Files:** 新建 `apps/frontend/src/console/evolution/` 组件与行为测试；修改 `FlowConsole.tsx`、`shared/api.ts`、`shared/types.ts`、`shared/i18n.ts`。

**Interfaces:** 消费六个 API；以 `plan` 与 `onAdoptBundle(bundle)` 接入现有 handoff。

- [x] 先写点击预览不能执行、确认才执行、取消、读取失败、报告差异和采用后更新 handoff 的测试。
- [x] 实现复用现有 primitives 的面板；记录实验 id，刷新读取进度，不自动恢复执行。
- [x] 添加中英文文案，不添加根 token、第二个 provider 或独立页面导航。

```typescript
fireEvent.click(screen.getByRole('button', { name: '预览实验' }));
expect(startedRequests).toEqual([]);
fireEvent.click(screen.getByRole('button', { name: '确认开始' }));
expect(startedRequests[0].confirmed).toBe(true);
```

### Task 4: 集成验收与守卫

**Files:** 修改两套 mutation 脚本的 CASES，补用户使用说明。

- [x] 跑新后端测试、相关既有测试、完整后端与 ruff。
- [x] 跑前端 typecheck/test/build、端点覆盖和相关前端变异，确认点名守卫抓住写死批准。
- [x] 检查当前 diff，保留既有未提交文件内容；最终报告能力与真实引擎效果的验证范围。

## 执行记录

- 接入基础已经通过 117 项模拟测试。当前实现直接在用户授权的共享工作区进行，不移动已有玩法改动。
- 文档中的 GEPA 可分享策略方案保持待实施；本轮完成独立的 Godot 反馈闭环。


### 最终验收（2026-11-04）

- 后端回归：1039 passed，2 skipped；真实 Godot 探针文件本轮未运行。
- 前端：381 passed；typecheck、build、ruff、UI Metrics 通过。
- 新增后端/诊断读取变异 6/6，前端变异 7/7，源码逐字节恢复。
- 浏览器：本机 Studio + Playwright/Edge，1360×900 与 560×900；预览和取消通过、无控制台错误或横向溢出、未发出执行确认。
- 显示精修：预算控件分组、结构化确认清单、语义状态、完整工作区高度、窄屏自然滚动和长内容适配。
- 修复验证中暴露的旧测试工作区泄漏与 Windows GBK/UTF-8 诊断读取问题。
- 独立审阅服务因高负载未能运行，源码已本地复查；真实引擎改善幅度等待用户确认实验后观察。

### 四轴复核补充（2026-11-05）

- 正确性与安全性已完成独立只读审阅，可维护性剩余核对及测试覆盖由主线程完成。
- 修复战斗计费指标名和跨局持续输入漏记；中文标题兼容旧计划并保留未知专名。
- 后端 1049 passed、2 skipped，前端 398 passed；类型、构建、ruff 与界面预算通过。
- 本次后端 6/6、前端 8/8 变异被捕获，源码逐字节恢复。详细结论见[四轴复核记录](../../architecture/review-2026-11-05-feedback-evolution.md)。
- 真实引擎改善幅度仍需在用户确认实验后观察。
