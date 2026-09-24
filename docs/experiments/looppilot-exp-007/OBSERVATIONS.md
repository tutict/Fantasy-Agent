# Observations

## 直接观测

1. 原 Fantasy-Agent `main` 有 10 个 pre-existing modified files，实验通过独立
   worktree 隔离；未清理用户修改。
2. LoopPilot 保持 `main` / `2275e747e73936ebb8f0b24e5fb901a619b6adf8` 且干净。
3. raw pytest 收集 159 项，91 passed、68 setup errors；共同原因是 pytest 默认 temp
   目录 ACL。只设置 `--basetemp` 后为 159/159 passed。
4. ruff、planning-only CLI、frontend typecheck/build 均通过；这些命令不验证真实
   Blender、ComfyUI、Godot 或 Unreal。
5. before-change public planning call 接受 credential-bearing localhost URL，并返回
   `planned`。这是选中 Candidate E 的 Product Finding 证据。
6. Cycle 1 与 Cycle 2 新测试均先真实失败，再以最小实现变绿。首次 execution
   characterization 已因共享 validation 初始 green，未伪造 RED。
7. 首轮 Spec/Security review 发现：probe candidate 虽被跳过，但 unavailable result
   和 summary 仍回显 secret。此 Major 促成 scoped rework；最终 public response test
   覆盖整个 serialized MCP result。
8. 首轮 Standards review 发现新增面向人的文档非简体中文为主；所有既有 EXP-007
   叙述已重写，复核 PASS。
9. review Major 触发 Mode 重评，但没有新 owner、formal integration、跨 runtime
   implementation、active recovery 或 structured rework，因此 Full Loop 未获得事实
   支持。
10. 最终完整验证收集 162 项并全部通过；额外 3 项是初始 endpoint tests 加上
    reviewer rework execution test。具体命令和时长见 baseline/result。
11. closure 重跑在普通权限下再次因新 basetemp ACL 得到 91 passed / 71 setup errors；
    提升权限且保持相同 test selection 后为 162 passed。聚焦 11 passed、ruff、
    planning-only CLI、frontend typecheck/build 也再次通过，未启动外部工具。
12. closure 完整 pytest 在 worktree 留下 `generated/godot/sessions/s2-s4`。清理后单独
    重跑 planning-only CLI 不写盘；代码追踪显示 fake tests 注入的 bridge 使用
    `tmp_path`，而 production-spec export 仍使用 `execute_godot_demo` 的默认仓库根。
    该事实登记为 Minor Test Harness Finding `EXP007-PATH-001`，并纠正了先前“pytest 只写 temporary
    artifacts”的过强表述。

## Worker Claims

本轮没有 delegated LoopPilot Worker，因此没有 Worker Delivery、Worker attempt 或
Worker claim 可进入 authoritative state。实现者的自然语言摘要不当作证据；权威事实
仅来自 Git、diff、test、lint、CLI 与独立 review。

## EII

- `EXP007-EII-001`：默认 pytest temp ACL 导致 68 setup errors；环境纠正为显式
  `--basetemp`，不改产品代码。
- `EXP007-EII-002`：早期 sandbox ruff cache 初始化失败；宿主范围 ruff 成功。
- `EXP007-EII-003`：三个独立只读 closure Reviewer sessions 在有界等待与 follow-up
  后均未提交 decision；停止继续重试。pre-closure Evidence PASS 不覆盖后发现的
  `EXP007-PATH-001`；用户提供的最终 closure review 后续给出三轴 decision。

这些 EII 不是 Product Finding、Protocol Finding 或 Mode escalation 依据。

## 未验证 / residual risks

- real Blender、real ComfyUI HTTP generation、real Unreal import/PIE/DataValidation、
  real Godot editor/import、GPU generation、remote MCP 均未授权，保持 unverified。
- Candidate C 的 same-path asset replacement/content digest contract 没有修复。
- `EXP007-PATH-001`（Minor Test Harness Finding）：`execute_godot_demo` 同时接受 bridge 与独立 `workspace_root`；两者
  不一致时可把 project 与 spec exports 写到不同根。当前完整 tests 会在 worktree 留下
  ignored artifacts；本轮已清理但未追加第二个产品修复。
- URL query-string tokens、headers、malformed/nonstandard URL canonicalization、
  DNS rebinding、TLS policy 与 secret storage 不在 Change Contract 内。
- 未观测到 delegated Worker failure，因此 Worker Failure Budget 不适用且未测试。
