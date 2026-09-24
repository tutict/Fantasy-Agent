# EXP-007 项目

目标：在 Fantasy-Agent 中执行一次 LoopPilot Phase 9 第三项目行为复现实验，最多
实施一个有证据支撑、可独立验收的 bounded product change。

模式：`Lightweight + Security Review`。

ComfyUI Worker、Creative Review Agent 等是 Fantasy-Agent 的产品领域角色；它们
不拥有 LoopPilot Supervisor、Worker、Reviewer 或 Integrator 权限。本轮没有委派
LoopPilot Worker。

closure 阶段因新发现的 test-isolation evidence 曾委派只读 Evidence Reviewer；三个
session 均未交付 decision。它们不是产品实现 Worker，也不改变 selected Mode 或唯一
bounded product change；用户提供的最终独立 Closure Review 已补足三轴 decision。

权限边界：用户只授权实验分支、commit 与该分支的 push。`main`、merge、PR、
release、deploy、真实外部工具执行以及修改 LoopPilot 均不在范围内。
