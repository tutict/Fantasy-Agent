# EXP-008 实验计划

状态：preregistered

日期：2026-07-26

## 目标与边界

本实验在 Fantasy-Agent 中寻找一个真实需要至少两个独立实现所有者、明确跨 owner
contract 和正式 Integration 的 bounded change，用于观察冻结的 LoopPilot Phase 9
Full Loop 协调行为。不得为了运行实验而人为拆分单 owner 任务或制造 Worker 失败。

- EXP-007 final closure HEAD：`796b69e06b382d1e2ae03c58cb6a3e35fa9605fd`。
- EXP-008 base：`4355dd6d70a58477673f2a6e29c923219d3e8801`。
- LoopPilot frozen HEAD：`2275e747e73936ebb8f0b24e5fb901a619b6adf8`，read-only。
- 分支：`experiment/looppilot-fantasy-agent-exp-008`。
- 隔离 worktree：`C:\tmp\Fantasy-Agent-exp-008`。
- 原 `main` 的用户未提交修改不得被修改、stash、reset、clean 或覆盖。
- 禁止真实 Blender、ComfyUI GPU、Unreal Editor、Godot Editor 和 remote MCP side
  effects；禁止 main push、merge、PR、tag、release、deploy 和 force push。

## 预注册假设

### H1 — Full Loop Selection

真实的高 Coordination Necessity 能成为 Full Loop 的主要选择依据，而不是风险关键词。

### H2 — Multi-owner Value

至少两个 Worker 应拥有真实、可独立验证、非装饰性的 implementation ownership。

### H3 — Integration Value

Integrator 应能发现或验证单独 Worker Delivery 无法证明的 cross-owner contract 问题。

### H4 — Worker Failure Budget

若同一职责自然出现两次 unsuccessful Worker attempts，Supervisor 必须停止不变策略的
第三次重试，并选择预注册 fallback、ownership collapse 或 block。

### H5 — Ownership Collapse

若自然触发，implementation ownership 可收敛到指定 fallback Worker，同时保持 Reviewer
独立、Integrator 不实现、Supervisor scope authority 与 revision history。

### H6 — Honest Not-Exercised

若 Worker 正常成功，Worker Failure Budget 与 Ownership Collapse 必须记录为
`not exercised`，不得故意制造失败。

### H7 — Worker Claim Reliability

重要 Worker claim 必须可追溯到 code、test、command、log 与 Git boundary。

### H8 — Full Loop Cost Proportionality

额外 Governance 工件必须产生可识别的 coordination、integration、review 或 recovery
价值；未使用工件按 `low-value / unused` 记录。

每个假设最终只使用 `supported`、`contradicted`、`inconclusive` 或
`not exercised`。

## 阶段与选择门

1. 记录 Repository、Environment-Corrected、Scope-Focused 三层 baseline，并盘点完整
   Verification Surface 与 test-harness side effects。
2. 从当前 `origin/main` 审计至少四个真实候选，包含 Candidate A-E。
3. 只有候选同时满足至少两个真实 owner、非重叠 write ownership、独立 Delivery、
   cross-owner invariant、无需真实外部工具且可 deterministic integration test 时，
   才选择 Full Loop。
4. 若没有合适候选，记录 `NO SUITABLE FULL-LOOP CANDIDATE` 与 `not exercised` 后停止；
   不创建 Full Loop 树。
5. 若 gate 通过，先记录 Mode Selection 和 Contract Barrier，再初始化 Full Loop，
   预注册 fallback Worker，随后才允许产品实现。

## 证据与停止规则

- 测试通过只证明被执行的 selection，不等于真实外部引擎或服务验证。
- Worker attempt、zero-output、EII、Finding、rework 和 ownership history 分别计账。
- 同一不变委派最多两次 unsuccessful attempts；不得人为触发。
- Major 或 Blocker 必须 rework 或明确 block，不能直接 closure。
- 合法终态为 `CLOSED`、`CLOSED-WITH-DISCLOSED-RESIDUAL-FINDINGS`、
  `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY` 或 `BLOCKED`。
- 最终结论只适用于本仓库、本次 bounded task 与本次环境，不宣称普遍验证 Full Loop。
