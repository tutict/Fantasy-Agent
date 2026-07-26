# Change Contract

## Problem

The ComfyUI MCP planning interface treats a URL with embedded username/password as
local when its hostname is `localhost` or loopback. The endpoint can later be probed
and can be serialized in a run manifest. Credentials in endpoint URLs are not a
supported configuration interface and must not cross this trust boundary.

## Included scope

- Validate ComfyUI endpoint URL credentials in `fantasy_agent/comfyui_mcp.py`.
- Apply the rule to preparation/execution manifest validation and capability-probe
  candidate resolution.
- Return a sanitized error/warning that does not contain username, password, or the
  raw credential-bearing URL.
- Add public-interface tests in `tests/test_comfyui_mcp.py` using a fake client and
  `tmp_path`; no network or external tool.

## Excluded scope

- Authentication headers, tokens, secret storage, or a new credential mechanism.
- General URL canonicalization, DNS rebinding defenses, TLS policy, or remote MCP.
- ComfyUI retries/timeouts, Blender/Godot/Unreal behavior, approval manifests,
  ProductionSpecBundle, frontend, schema versioning, and LoopPilot changes.
- Real ComfyUI contact or generation.

## Public behavior and acceptance

1. `prepare_visual_reference_workflows` rejects an endpoint containing URL username
   or password before writing files; returned content does not include the secret.
2. `probe_comfyui_capabilities` skips/rejects a credential-bearing candidate without
   constructing/calling the client; diagnostics do not include the secret.
3. Normal loopback endpoints remain accepted by existing tests.
4. Remote endpoints remain rejected by default and existing confirmation behavior is
   unchanged.
5. Focused tests, full pytest, ruff, planning CLI, frontend typecheck, and frontend
   build remain green. Real external tools remain unverified.

## TDD sequence

- Cycle 1 RED: add the planning rejection/no-secret test through
  `call_comfyui_mcp_tool`.
- Cycle 1 GREEN: minimally reject credentials during manifest validation.
- Cycle 2 RED: add capability-probe test proving no client call and no secret echo.
- Cycle 2 GREEN: reuse the credential check during candidate resolution.
- Refactor only while green and only to remove duplication revealed by both paths.

## Rollback

Revert the product commit. No schema/data migration or generated external asset is
created.
