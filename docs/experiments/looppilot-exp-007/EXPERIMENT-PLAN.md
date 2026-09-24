# LoopPilot EXP-007 实验计划

## 目标与边界

EXP-007 验证 Phase 9 的 Product Risk / Coordination Necessity 分离能否迁移到
Fantasy-Agent 的 Python/FastAPI/Pydantic/PyYAML 技术栈。本轮最多实施一个可独立
验收的 bounded product change。

LoopPilot 冻结且只读，HEAD 为 `2275e747e73936ebb8f0b24e5fb901a619b6adf8`。
Fantasy-Agent 原 `main` 工作树已有 10 个 modified files，全部排除。本轮在
`C:\tmp\Fantasy-Agent-exp-007` 隔离 worktree 执行，分支为
`experiment/looppilot-fantasy-agent-exp-007`，基于观测到的 `origin/main`
`4355dd6d70a58477673f2a6e29c923219d3e8801`。

禁止真实 Blender、ComfyUI、Unreal、Godot、GPU generation、remote MCP、deploy、
release、merge 与 PR。外部执行只能用 deterministic fake/mock 与 temporary
filesystem 表示。

## 预注册假设

- **H1 - Cross-stack Mode Transfer**：Phase 9 mode selection 适用于此 Python /
  FastAPI / Pydantic / MCP 仓库。
- **H2 - Product Risk != Full Loop**：高 Product Risk 只增加 review、validation、
  evidence depth，不能单独证明 Full Loop 必要。
- **H3 - Coordination Necessity**：Full Loop 主要由 multiple implementation
  owners、formal integration、active recovery、structured rework 或非平凡
  ownership boundaries 驱动。
- **H4 - Specialist-reviewed Lightweight**：高 Product Risk + single owner +
  bounded change + deterministic verification 可以合法使用 Lightweight + 匹配
  Specialist Review。
- **H5 - Verification Surface Transfer**：Verification Surface 能诚实区分
  pytest、ruff、CLI characterization、integration-like tests、optional
  dependencies 与 external-tool validation。
- **H6 - Product-Agent / Governance-Agent Separation**：Fantasy-Agent 多产品
  Agent 不会污染 LoopPilot governance roles。
- **H7 - Worker Claim Reliability**：LoopPilot Worker claim 只有经 code、test 或
  command evidence 验证后才能进入 authoritative state。
- **H8 - Artifact Accounting**：Product、Governance、Evaluation 工件分账在第三
  项目仍有意义。

每个假设最终只能分类为 `supported`、`contradicted`、`inconclusive` 或
`not exercised`；反证与支持证据同等优先。

## 方法

1. 记录 repository、raw、environment-corrected 与 scope-focused baselines。
2. 审计 Candidate A-E，并主动寻找反例。
3. 分别评分 Product Risk 与 Coordination Necessity，只在 Lightweight、Full Loop、
   No implementation justified 中选择。
4. 对真实 gap 使用 characterization -> real RED -> minimal GREEN -> focused
   regression。
5. 执行 Spec、Standards、匹配 Specialist，以及 Evidence/Factual Accuracy review。
6. 运行可达完整 Verification Surface，并披露不可达的真实外部工具路径。

## Stop / escalation 条件

出现 Major/Blocker、必须加入第二 implementation owner、formal integration、跨多个
runtime implementation、active recovery、重复同类 correction 或 contract drift 时，
Lightweight 必须停止并重评 Full Loop。不得人为制造 Worker failure。

## 实施前选择

选中 Candidate E：带 credentials 的本地 ComfyUI endpoint 会被 planning interface
接受并可进入可写 run manifest。本轮将拒绝 URL credentials，且不回显 secret。
Candidate C 也存在真实 path-identity weakness，但完整 artifact binding 需要更广的
review-to-execution contract，故排除在本轮唯一变更之外。
