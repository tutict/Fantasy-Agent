# Change Contract

## 问题

ComfyUI MCP 会把带 username/password 的 URL 当成本地 endpoint，只要 hostname 是
`localhost` 或 loopback。该值后续可能被 probe，也可能序列化到 run manifest。URL
credentials 不是受支持的配置接口，不得穿过此 trust boundary。

## Included scope

- 在 `fantasy_agent/comfyui_mcp.py` 校验 ComfyUI endpoint URL credentials。
- 同一规则覆盖 prepare/execution manifest validation 与 capability-probe candidate
  resolution。
- 拒绝时使用脱敏 error/warning/result，不包含 username、password 或完整原 URL。
- 在 `tests/test_comfyui_mcp.py` 通过 public interface、fake client 与 `tmp_path` 测试；
  不得联网或启动外部工具。

## Excluded scope

- Authentication headers、tokens、secret storage 或新的 credential mechanism。
- 一般 URL canonicalization、DNS rebinding、TLS policy 或 remote MCP。
- retries/timeouts、Blender/Godot/Unreal、approval manifest、ProductionSpecBundle、
  frontend、schema versioning 与 LoopPilot 修改。
- 真实 ComfyUI contact/generation。

## Public behavior / acceptance

1. `prepare_visual_reference_workflows` 在写盘前拒绝 URL username/password，返回
   content 不包含 secret。
2. `probe_comfyui_capabilities` 在 client construction 前跳过/拒绝该 candidate；
   blockers、warnings、structured result 与 summary 均不包含 secret。
3. `run_visual_reference_workflow` 在 client construction 与写盘前拒绝同类 endpoint。
4. 正常 loopback endpoint 保持可用；remote endpoint 默认拒绝；confirmation 行为不变。
5. focused tests、full pytest、ruff、planning CLI、frontend typecheck/build 保持 green；
   真实外部工具保持 unverified。

## TDD 与 review rework

- Cycle 1：planning rejection/no-secret test 真实 RED，再最小 GREEN。
- Cycle 2：probe no-client/no-secret test 真实 RED，再最小 GREEN。
- GREEN 后只抽取两调用点共享的 `_has_url_credentials`。
- Reviewer rework：公开 MCP serialized result test 真实 RED，安全 result sentinel 后 GREEN。
- execution characterization 首次即 GREEN；没有制造 RED。

## Rollback

Revert 两个 product commits。无 schema/data migration，也没有外部生成资产。
