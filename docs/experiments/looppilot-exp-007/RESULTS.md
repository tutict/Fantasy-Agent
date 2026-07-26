# EXP-007 结果

## 范围与结论边界

- **已观测**：基线为 `4355dd6d70a58477673f2a6e29c923219d3e8801`；实验分支为
  `experiment/looppilot-fantasy-agent-exp-007`。LoopPilot 保持只读、干净，位于
  `2275e747e73936ebb8f0b24e5fb901a619b6adf8`。
- **已观测**：本实验的产品实现仅修改 `fantasy_agent/comfyui_mcp.py` 与
  `tests/test_comfyui_mcp.py`，处理 ComfyUI endpoint URL 中 userinfo 凭据的拒绝与
  回显防护。
- **未验证**：未启动真实 Blender、ComfyUI、Unreal、Godot、GPU、远端 MCP 或网络服务。
  下述结论不声称验证这些系统的真实执行。

## Mode 与专业审查

| 项目 | 记录 |
| --- | --- |
| Product Risk | 高：8 个维度合计 `8/16`，包含外部端点、凭据泄露、文件写入与兼容性风险。 |
| Coordination Necessity | 低：`0/16`；单一 Python 模块、单一测试文件、单一实现者，未出现跨 runtime 或正式集成。 |
| 选择的 Mode | `Lightweight + Security Review`。高 Product Risk 不自动等于 Full Loop。 |
| 专项审查价值 | Spec/Security 独立发现了首版遗漏的 public probe 回显，形成真实 Major 和有界返工。 |
| Mode 触发器 | Major 触发暂停和重新评估；未观察到第二 owner、formal integration、跨 runtime、active recovery 或多重独立契约，故无证据升级 Full Loop。 |
| Worker Failure Budget | 未触发：本轮没有 delegated LoopPilot Worker Delivery；不得据此推断 Worker 可靠性。 |

## 验证证据

| 类别 | 命令或范围 | 已观测结果 |
| --- | --- | --- |
| 原始基线 | `pytest -ra` | 159 collected；91 passed、68 setup errors。错误同属默认 pytest temp ACL，归为 EII。 |
| 环境纠正基线 | `pytest -ra --basetemp=C:\tmp\fa-exp007-pytest` | 159 passed，12.91s。 |
| 初始聚焦 | Candidate C approval tests；planning-only CLI | 5 passed、33 deselected，0.47s；CLI 成功。 |
| 变更后完整 | `pytest -ra --basetemp=C:\tmp\fa-exp007-final2-pytest`；closure 重跑禁用 cache/bytecode 并使用 `C:\tmp\fa-exp007-final-resume-pytest` | 分别为 162 passed（13.16s）与 162 passed（13.05s）。closure 普通权限重跑先出现 91 passed / 71 setup errors，原因仍是 basetemp ACL；提升权限后同一 test selection 全绿。full run 留下 s2-s4 ignored Godot spec artifacts，已清理并登记 `EXP007-PATH-001`。 |
| 变更后聚焦 | `pytest -q tests/test_comfyui_mcp.py`，显式外部 basetemp 且禁用 cache/bytecode | 11 passed；初次记录 0.21s，closure 重跑 0.20s。 |
| 静态检查 | `ruff check fantasy_agent tests apps` | `All checks passed!` |
| CLI | `python -m fantasy_agent --prompt 'EXP-007 final rework planning-only' --minutes 10 --engine 'Godot 4' --format summary` | exit 0；仅 planning-only。 |
| 前端 | `npm.cmd run frontend:typecheck`；`npm.cmd run frontend:build` | 均 exit 0；build 为 23 modules、105ms。 |
| 外部工具 | Blender/ComfyUI/Unreal/Godot/GPU/远端 MCP | 未授权、未运行，保持 unverified。 |

在变更前，public planning 调用会接受 credential-bearing localhost URL 并返回
`planned`。TDD 记录了两个真实 RED：先是 public planning 未返回安全错误，随后是
probe 在 client factory 前仍收到原 URL。审查返工再产生一个真实 RED：完整 public MCP
响应的 `structuredContent` 与 summary 含有 secret。execution 的新增测试初始即为 GREEN，
因为它复用了已经覆盖的 manifest validation；本报告不将其表述为 RED。

## 假设分类

| 假设 | 状态 | 依据 |
| --- | --- | --- |
| H1：Cross-stack Mode Transfer | supported | 在 Python/FastAPI/Pydantic/MCP 项目中按风险与协调评分完成一次有界 Mode 选择。 |
| H2：Product Risk != Full Loop | supported | 高风险 `8/16` 未被单独当成 Full Loop 依据；Major 后也按触发事实重评。 |
| H3：Coordination Necessity | supported | 未观察到多 owner、formal integration、active recovery、structured rework 或非平凡 ownership boundary。 |
| H4：Specialist-reviewed Lightweight | supported | 单 owner、有界变更与 deterministic fake 验证下，Security review 发现 Major 并完成返工。 |
| H5：Verification Surface Transfer | supported | pytest、ruff、CLI、frontend、fake external boundary 与真实外部工具 unverified 被分开记录；closure 还暴露 full pytest 的 split-root artifact leak。 |
| H6：Product-Agent / Governance-Agent Separation | supported | Fantasy-Agent 的产品 Agent 未获得或计作 LoopPilot 治理角色。 |
| H7：Worker Claim Reliability | not exercised | 未委派 LoopPilot Worker；没有可验证的 Worker claim 可进入 authoritative state。 |
| H8：Artifact Accounting | supported | 产品 2 个文件、Governance 4 个、Evaluation 9 个分别计账。 |

额外观察（不重定义预注册编号）：三层基线避免了 pytest temp ACL 的错误归因；独立
Spec/Security 审查发现 public-result 泄露面；`tmp_path`、fake factory 和完整 wrapper
序列化覆盖了拒绝边界，但不替代真实外部工具验证。

**推断**：本单一、非对照实验支持 Phase 9 启发式在第三个技术栈中的可迁移性，
但不支持其普遍有效性或优越性。没有观察到直接反驳 H1-H6/H8 的证据；Candidate C 的
内容绑定缺口与 `EXP007-PATH-001` split-root 写入仍是未修复的独立产品风险。

## 跨项目比较

下表中 MMGH 和 Final Assignment 是对 LoopPilot 冻结仓库既有证据的只读摘要，
不是本次重新执行的结果。其来源为 LoopPilot 的
`docs/mmgh-behavioral-evidence.md`、`docs/final-assignment-behavioral-evidence.md`、
`docs/evaluation-synthesis-and-protocol-calibration.md` 与相关实验记录。

| 维度 | MMGH（既有记录） | Final Assignment（既有记录） | Fantasy-Agent EXP-007（本次） |
| --- | --- | --- | --- |
| 1. 项目/栈 | 多个 TypeScript/Rust 边界 | Spring/Flutter | Python/FastAPI/Pydantic/PyYAML |
| 2. 变更边界 | 多个受控实验 | 作业集成/恢复语境 | ComfyUI URL userinfo 拒绝与回显 |
| 3. Mode | EXP-001/003/004 Full，EXP-002 Lightweight | Lightweight 与 Full/blocked 样本 | Lightweight + Security Review |
| 4. 风险/协调 | 记录为独立判断 | 记录为独立判断 | 高 `8/16` / 低 `0/16` |
| 5. 基线形状 | 既有实验基线 | 有 Surefire/环境问题 | raw、纠正、聚焦三层 |
| 6. 验证面 | 语言/仓库测试面 | 后端与客户端面 | pytest、ruff、CLI、frontend、fake |
| 7. 外部执行 | 受各实验授权限制 | 受环境限制 | 未执行真实引擎或服务 |
| 8. 审查与返工 | 记录独立审查 | 有作业审查记录 | Spec/Security 发现 Major，最小返工 |
| 9. Worker/委派 | 含既有委派证据 | 有不完整/阻塞证据 | 无 Worker Delivery |
| 10. 治理工件 | 各实验按 Mode 记录 | 既有作业工件 | 6 个 Governance 工件 |
| 11. EII | 既有环境归因 | Surefire/环境归因 | pytest temp ACL、ruff cache、Reviewer session 无交付 |
| 12. 结果与限制 | 不等同普遍规律 | 证据不完整 | 一次有界支持，非对照 |
| 13. 证据来源 | 冻结仓库只读文档 | 冻结仓库只读文档 | Git diff、命令、测试、独立审查 |

## 反例与限制检查

| 反例类型 | EXP-007 观察 | 决策 |
| --- | --- | --- |
| 高风险、高协调 | Candidate A/C 若扩展到内容绑定或多系统生命周期 | 未选；超出有界单 owner 修复。 |
| 低风险、低协调 | 无外部写入的纯局部行为 | 不是本轮目标。 |
| 高风险、低协调 | Candidate E credential URL | 选中。 |
| 低风险、高协调 | 需跨 owner 的接口或文档契约调整 | 未选。 |
| 已受保护 | Candidate B 顶层 confirmation gate | 未选；观察到保护存在。 |
| 无可复现 gap | Candidate A sampled validation paths | 未选；采样未见 validation bypass。 |
| 测试隔离反例 | Candidate D split-root writes | full pytest 留下 ignored Godot spec artifacts；已清理并作为 residual finding 披露。 |
| 验证表面不足 | 真实外部引擎/网络 | 标记 unverified，不以 fake 代替。 |
| 协调升级事件 | Major 后的 scoped rework | 重评后无 Full Loop 触发事实。 |

## 成本、账目与建议

- **Governance**：6 个工件：`.looppilot/PROJECT.md`、`STATE.md`、`CHECKLIST.md`、
  `HANDOFF.md`、`DELEGATION.md` 与 closure Evidence Review Task Contract；仍在
  Lightweight 的 4-7 启发式范围内。
- **Evaluation**：9 个实验文档：计划、基线、候选审计、Mode、契约、审查、评分、观察、
  结果。它们单独计入评估成本，不占 Governance 预算。
- **Product**：1 个实现文件和 1 个测试文件；没有 schema、runtime 架构或外部配置扩张。
- **Scorecard**：`76/84`，详见 `EVALUATION-SCORECARD.md`。该分数不是 Mode 自动决策器。

建议保持 LoopPilot Phase 9 文案和规则不变：本实验仅增加一条跨栈、单任务证据，
不足以重校准阈值或声明普适性。EXP-008 尚未满足启动条件：没有已观测的多 owner
Full Loop recovery 或委派失败预算耗尽样本。未来实验应先取得这些触发事实，而不是
预设升级结论。

## Closure 状态

状态为 **blocked with verified product change**。缓存、pytest basetemp、frontend
`dist` 与临时 `node_modules` junction 已清理；完整 pytest、聚焦测试、ruff、
planning-only CLI、frontend typecheck/build 均通过。pre-closure 的独立 Evidence Review
曾 PASS，但它早于 `EXP007-PATH-001` 的发现，不能覆盖新证据。三个只读 closure
Reviewer sessions 在有界等待和 follow-up 后均未提交 decision，归为
`EXP007-EII-003`；因此 corrected closure claims 未获得独立复核，不能标为最终 PASS。

H1-H8 分类是 Supervisor 基于已观测 evidence 的当前结论，其中 H7 仍为 not exercised；
独立 closure confirmation 保持 unverified。按附件授权，最终 Git 检查、commit 与实验
分支 push 用于保存这一诚实的 blocked experiment outcome，不代表 merge、release、
deploy 或 EXP-008 readiness。
