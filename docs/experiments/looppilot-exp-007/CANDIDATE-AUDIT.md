# Candidate Audit

证据标签使用 `observed`、`inferred`、`unverified`。本文件做定性审计；选中任务的
0-2 数值 gate 见 `MODE-SELECTION.md`。

## Candidate A - ProductionSpecBundle pre-write validation

- Observed behavior：YAML/JSON loader 使用 strict Pydantic validation，拒绝不支持的
  schema version；compile 前调用 `ensure_production_spec_executable`；既有 tests 包含
  invalid spec 在 Godot create 前阻断。
- Potential gap：尚未证明每个 CLI/Studio/Godot/Unreal entry 均无 bypass；若修改共享
  authority，可能跨 adapters。
- Evidence：`production_spec_runtime.py`、相关 runtime/executor tests。
- Product Risk：若有 bypass 为 high；抽样路径未观测到 bypass。
- Coordination Necessity：cross-engine authority change 可能 high。
- Review axes：Compatibility、Data。
- Testability：invalid bundle + fake writer 可 deterministic test。
- External side effects：不需要。
- Scope：可能 multi-module/cross-engine。
- 决策：reject。它提供“看似危险但已有充分保护”的反例，未证明 bounded real gap。

## Candidate B - explicit execution confirmation

- Observed behavior：CLI 把 `--yes` 映射到 `confirmed`；Studio 在
  `confirmed=false` 时 preview；top-level Godot/Unreal/asset executor 在写盘前返回
  planned effects；底层 MCP 仍有各自 side-effect flags。
- Potential gap：底层 prepare interface 有意暴露 `write_files`；统一 CLI/Studio/MCP
  authority 会跨多个 ownership surfaces。
- Evidence：`__main__.py`、`executor.py`、Studio routes 与 confirmation tests。
- Product Risk：被 bypass 时 high；已测 top-level paths 未观测 bypass。
- Coordination Necessity：共享 authority redesign 为 medium/high。
- Review axes：Security、Compatibility。
- Testability：fake adapter 可验证 zero/one action。
- External side effects：不需要。
- Scope：cross-interface。
- 决策：reject，作为“看似局部但实际跨 owner”的反例。

## Candidate C - Creative Review -> approval-gated ingest

- Observed behavior：approved Blender assets 被 copy；rejected、needs_revision、pending
  与 missing manifest 在现有 tests 中被 skip/block。纯内存 characterization 观测到：
  `reviewed_revision.fbx` 可仅凭相同 `asset_id` 放行 `start_marker.glb`。
- Potential gap：manifest 没有 content digest，无法证明 reviewed path 的 bytes 未被
  替换；只修 filename 不能诚实满足完整 artifact identity。
- Evidence：`approval_manifest.py::_match_keys`、manifest models 与 approval tests。
- Product Risk：approval/artifact integrity high。
- Coordination Necessity：path-only fix low；完整 content binding 需要 review creation、
  schema、Studio persistence、Blender format conversion 与 execution，故 medium/high。
- Review axes：Data、Compatibility；若改 execution 再加 Security。
- Testability：path mismatch deterministic；content binding 需先定义 digest lifecycle。
- External side effects：不需要，`tmp_path` + fake bridge 足够。
- Scope：完整修复 cross-contract。
- 决策：本轮 reject。它是 residual Product Finding，不是 Mode heuristic failure。

## Candidate D - generated artifact path boundary

- Observed behavior：shared helper 拒绝 absolute path、parent traversal、prefix
  violation 与 resolved escape；MCP tests 覆盖 outside-root；`resolve().relative_to`
  也约束 symlink target。closure 完整 pytest 还直接观测到：三条注入
  `GodotMCPBridge(tmp_path)` 的 fake-execution tests 仍在 worktree 写入
  `generated/godot/sessions/s2-s4`，因为 `execute_godot_demo.workspace_root` 保持默认仓库根。
- Potential gap：`bridge.workspace_root` 与函数 `workspace_root` 是两个写入 authority；
  调用者只注入 bridge 时，project 与 production-spec exports 可落在不同根。path
  traversal 未复现；overwrite policy 及全部 Windows junction/device-name cases仍未穷尽。
- Evidence：`path_safety.py`、`executor.py::_write_production_spec_exports`、
  `tests/test_executor.py` 的 s2-s4 tests，以及清理后 full pytest/单独 planning CLI 复现。
- Product Risk：split-root unintended write 为 medium；若证明 escape 则 high，但本轮未观测 escape。
- Coordination Necessity：当前 seam/test-isolation fix 可 low；统一所有 adapter root authority
  或 overwrite policy 更高。
- Review axes：Security。
- Testability：temporary filesystem + post-test workspace assertion；无需真实 escape file。
- External side effects：不需要。
- Scope：本地 executor/test seam 可 bounded；跨 adapter root authority 更广。
- 决策：reject。该 finding 在唯一 Candidate E product change 锁定并完成后由 closure
  verification 发现，记录为 Minor Test Harness Finding `EXP007-PATH-001`，不得追加第二个产品变更。

## Candidate E - MCP/local-tool endpoint boundary（selected）

- Observed behavior：remote ComfyUI endpoint 默认拒绝，execution 仍需 confirmation；但
  planning 接受 `http://user:secret@localhost:8188`，因为 locality 只看 hostname。
  `ComfyUIRunManifest.endpoint` 可在 `write_files=true` 时持久化 credentials。
- Potential gap：username/password 可穿过 planning、probe 与 manifest；错误路径也可能
  回显原 endpoint。
- Evidence：public `call_comfyui_mcp_tool` characterization、run manifest model、
  `_is_local_endpoint` 与 manifest writer。
- Product Risk：Security/credential disclosure high。
- Coordination Necessity：low；single owner、one Python module、one test file、无 runtime
  integration。
- Review axes：永久 Spec/Standards + Security。
- Testability：public interface + fake client，deterministic。
- External side effects：不需要；test 证明 client 未被构造。
- Scope：endpoint validation + no-secret reporting。
- 决策：selected。它是真实、完整可修、可独立验收的 high-risk/low-coordination gap。

## Counterexample summary

1. high Product Risk + low Coordination：Candidate E。
2. high Product Risk + high Coordination：Candidate C 完整 content binding，或 Candidate
   A cross-engine authority redesign。
3. 看似危险但保护充分：Candidate A sampled validation。
4. 看似局部但跨 owner：Candidate B confirmation authority。
5. 无真实 gap：Candidate A sampled validation paths；Candidate D 未复现 traversal，
   但发现了独立的 split-root/test-isolation gap。

Candidate E 替代最初 provisional Candidate C，是因为它能形成完整诚实的 bounded fix，
不是为了预设支持 Phase 9。
