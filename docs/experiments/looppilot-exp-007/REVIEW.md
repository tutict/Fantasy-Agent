# Review

## 独立性与边界

Spec、Standards、Security reviewers 均独立于实现者，只读审查，没有修改实现或
运行 external tool。固定比较基线为
`4355dd6d70a58477673f2a6e29c923219d3e8801`；审查覆盖三个 experiment commits
及其工作树差异。

## 首轮 Spec Review

结论：**FAIL，1 Major**。

观测：credential-bearing probe candidate 已在 `_resolve_endpoint` 被跳过，但当无
candidate 可用时，`probe_comfyui_capabilities` 仍把原 `request.endpoint` 写入
`ComfyUICapabilityProbeResult.endpoint`。public MCP wrapper 将其序列化并在 summary
中显示，因此 secret 仍泄漏到 `structuredContent` 与 `content`。

要求：在 public wrapper 上测试完整序列化结果不包含 secret；拒绝时不得复制原 URL；
为 execution manifest path 补充 no-client/no-write evidence。

## 首轮 Standards Review

结论：**CHANGES REQUESTED，1 Minor**。

观测：`AGENTS.md` 要求人类可读文档优先简体中文；初版 9 个 EXP-007 治理/研究
文档几乎全为英文。实现本身没有 hard violation，helper 与 `tmp_path`/fake client
测试模式符合现有架构。

要求：将叙述正文改为简体中文，保留路径、命令、类名、字段和 metric key 英文。

## 首轮 Security Review

结论：**FAIL，1 Major**，与 Spec Major 为同一 Finding，不重复计数。

攻击路径：`probe_comfyui_capabilities` 接收
`http://worker:secret@localhost:8188`；candidate 过滤后，unavailable result 和 summary
仍回显原 URL，可能进入 MCP transcript/log。Security reviewer 同时确认 planning 与
execution manifest validation 在 client construction/write 前已 fail closed。

## Rework 与 Mode 重评

Major 出现后停止 closure，并按 Lightweight escalation gate 重评。Finding 仍限于同一
Python module 与 test file；未出现第二 implementation owner、formal integration、
second runtime、active recovery 或 multiple independent contracts。因此保持
`Lightweight + Security Review`，没有诚实证据支持升级 Full Loop。

实施的 rework：

- unavailable probe 对 credential URL 返回固定安全 sentinel；
- public MCP test 序列化完整 response 并断言 secret 缺席；
- execution test 用 fake factory 断言无 client construction、无 generated write、无
  exception echo；
- 所有既有 EXP-007 人类可读文档改为简体中文为主。

## Reverification

| 轴 | 结论 | 可复核证据 |
| --- | --- | --- |
| Spec | PASS | public probe serialized response 无 secret；execution 在 client/write 前阻断。 |
| Standards | PASS | 人类可读叙述改为简体中文；helper 只复用两个判断点，无额外抽象。 |
| Security | PASS | planning/execution/probe 均 reject URL credentials；probe result 使用安全 sentinel。 |
| Evidence/Factual Accuracy | PASS（pre-closure） | 复核当时的 H1-H8、状态投影、工件分账与 fake/真实边界；不覆盖后来发现的 `EXP007-PATH-001`。 |

## Finding disposition

- Product Finding `EXP007-SEC-001`：credential URL 可被接受并在 probe 结果回显。
  状态：fixed and independently reverified。
- Standards Finding `EXP007-STD-001`：新增人类可读文档非简体中文为主。
  状态：fixed and independently reverified。
- EII `EXP007-EII-001`：默认 pytest temp ACL 导致 68 setup errors。
  状态：environment-corrected；不是 Product Finding。
- Test Harness Finding `EXP007-PATH-001`（Minor）：closure full pytest 暴露
  bridge/workspace_root 双根写入，留下 ignored Godot spec artifacts。状态：open、
  separate follow-up、out of selected Change Contract；产物已清理。
- EII `EXP007-EII-003`：三个只读 closure Reviewer sessions 均未在有界等待与 follow-up
  后提交 decision。状态：blocked；不计作 Worker attempt 或 Product/Protocol Finding。

未产生 delegated Worker Delivery，因此没有 Worker claim 可审；该事实不得被写成
Worker reliability 已验证。

## Closure Evidence Re-review

结论：**CLOSEABLE-WITH-DISCLOSED-RESIDUAL-FINDINGS**（用户提供的 Independent
Closure Review）。

最终三轴 decision：Spec **PASS**；Standards **PASS**；Evidence/Factual Accuracy
**PASS-WITH-FINDINGS**。`EXP007-EVID-001` 已纠正：Governance accounting 为 6 个工件、
232 行。`EXP007-PATH-001` 按 Minor Test Harness Finding / separate follow-up 保留；
external tool limitations 保持披露。

此前三个只读 Reviewer session 无交付仍按 `EXP007-EII-003` 保留，不改写为 PASS 或
Worker attempt；本次结论不授权第二个产品变更。
