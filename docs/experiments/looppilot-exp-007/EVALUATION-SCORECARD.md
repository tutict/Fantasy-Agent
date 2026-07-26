# Evaluation Scorecard

评分为 0-3：0 表示未观测，1 表示弱或部分证据，2 表示有界证据，3 表示本实验范围内
直接、可复核的充分证据。总分不是 Mode 的自动决策器。

| # | 维度 | 分数 | 证据 |
| ---: | --- | ---: | --- |
| 1 | Cross-project orientation | 3 | 读取冻结 MMGH/Final-Assignment evidence，并在第三个 Python 项目执行。 |
| 2 | Baseline attribution | 3 | raw、environment-corrected、scope-focused 三层均有命令与归因。 |
| 3 | Verification Surface | 3 | pytest、ruff、CLI、frontend、fake external tool、unreachable surface 分开记录。 |
| 4 | Candidate audit | 2 | A-E 均被审计，但 Candidate D 的 split-root artifact leak 直到 closure full run 才被识别并纠正。 |
| 5 | Counterexample search | 3 | 高/低协调、跨 owner、已保护、无 gap 均有实例。 |
| 6 | Product Risk assessment | 3 | 8 个 0-2 维度与证据明确记录。 |
| 7 | Coordination assessment | 3 | 8 个 0-2 维度与 single-owner 事实明确记录。 |
| 8 | Mode proportionality | 3 | high risk 仍 Lightweight；Major 后停止并重评但无 Full Loop 事实。 |
| 9 | Specialist Review proportionality | 3 | 只加载匹配的 Security specialist，并直接发现泄漏。 |
| 10 | Product-agent / LoopPilot-agent separation | 3 | 产品多 Agent 未被计为 LoopPilot Workers。 |
| 11 | Scope discipline | 3 | 仅 ComfyUI endpoint userinfo 与报告表面；无 schema/runtime/refactor 扩张。 |
| 12 | Characterization quality | 3 | public planning 接受不安全 URL 的 before-change observation 可复现。 |
| 13 | RED honesty | 3 | Cycle 1、Cycle 2 与 reviewer rework 都有真实 RED；execution 为初始 GREEN。 |
| 14 | Test quality | 3 | public MCP serialization、fake client、no-write/no-client assertions。 |
| 15 | External-side-effect safety | 3 | 未调用真实 endpoint/engine；只用 `tmp_path` 与 fake。 |
| 16 | Worker claim traceability | 2 | 模板与状态明确要求 evidence，但没有 delegated Worker Delivery。 |
| 17 | Worker reliability | 0 | 未委派 Worker，故 not exercised。 |
| 18 | Review usefulness | 3 | 独立 Spec/Security 发现同一真实 secret echo。 |
| 19 | Finding specificity | 3 | Finding 指向 probe result、wrapper serialization 与 summary surface。 |
| 20 | Rework effectiveness | 3 | 新 RED 后修复，三轴独立 reverification PASS。 |
| 21 | Artifact accounting | 3 | Product/Governance/Evaluation 分账，预算只计 Governance。 |
| 22 | Governance cost | 2 | 6 个 Governance artifacts 仍在 4-7 heuristic 内，但三个 Reviewer sessions 无交付，产生了实质协调成本。 |
| 23 | Evaluation cost | 2 | 研究/报告工件较多但不侵占 Governance budget；仍需披露成本。 |
| 24 | EII classification | 3 | pytest temp ACL 与 ruff cache 明确归为 EII。 |
| 25 | Closure honesty | 3 | 不把 fake/CLI/pytest 写成真实 external execution。 |
| 26 | Residual-risk disclosure | 3 | Candidate C、URL canonicalization、真实工具均明确保留。 |
| 27 | Technical-stack neutrality | 3 | 在 Python/FastAPI/Pydantic/MCP 栈验证，不依赖 MMGH/Flutter 机制。 |
| 28 | Phase 9 heuristic transfer | 2 | 一个第三项目任务支持迁移；非控制实验，不支持普遍性。 |

总分：**76/84**。低分或零分不是失败掩盖：第 17 项明确说明 Worker reliability
未被本轮触发；第 23、28 项限制了评估成本与外推强度。
