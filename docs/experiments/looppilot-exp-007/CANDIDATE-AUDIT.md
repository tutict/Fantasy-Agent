# Candidate Audit

Evidence labels are `observed`, `inferred`, or `unverified`. Risk and coordination
ratings are qualitative here; the selected task's numeric gate is in
`MODE-SELECTION.md`.

## Candidate A - ProductionSpecBundle pre-write validation

- Observed behavior: YAML/JSON loading uses strict Pydantic validation, rejects an
  unsupported schema version, and `compile_production_spec_bundle` calls
  `ensure_production_spec_executable`. Existing tests include invalid-spec blocking
  before Godot create and focused adapter tests.
- Potential gap: a complete proof across every CLI, Studio, Godot, and Unreal entry
  was not established; changing shared validation authority could span adapters.
- Evidence: `fantasy_agent/production_spec_runtime.py`,
  `tests/test_production_spec_runtime.py`, `tests/test_executor.py`.
- Product Risk: high if a bypass exists; no bypass was observed in sampled paths.
- Coordination Necessity: potentially high for a cross-engine authority change.
- Likely review axes: Compatibility and Data.
- Testability: deterministic with invalid bundles and fake project writers.
- External side effects: none required.
- Scope: potentially multi-module/cross-engine.
- Decision: rejected because existing protection supplied the requested
  counterexample "looks risky but is protected" and no bounded real gap was proven.

## Candidate B - explicit execution confirmation

- Observed behavior: CLI maps `--yes` to `confirmed`; Studio previews when
  `confirmed=false`; top-level Godot/Unreal/asset executors return planned effects
  before writes; lower MCP calls retain their own side-effect flags.
- Potential gap: direct use of lower prepare interfaces intentionally exposes
  `write_files`; proving or changing a single authority across CLI, Studio, and MCP
  would cross several owners.
- Evidence: `fantasy_agent/__main__.py`, `fantasy_agent/executor.py`,
  `apps/studio/app/main.py`, and confirmation tests in `tests/test_executor.py`.
- Product Risk: high if bypassed; no bypass was observed in tested top-level paths.
- Coordination Necessity: medium/high for a shared authority redesign.
- Likely review axes: Security and Compatibility.
- Testability: fake adapters can verify zero/one action without engines.
- External side effects: none required for tests.
- Scope: cross-interface.
- Decision: rejected as the "looks local but crosses owners" counterexample.

## Candidate C - Creative Review to approval-gated ingest

- Observed behavior: approved Blender decisions are copied; rejected,
  needs-revision, pending, and missing-manifest paths are skipped or blocked in
  current tests. A pure-memory characterization also observed that a decision for
  `reviewed_revision.fbx` can approve `start_marker.glb` solely through
  `asset_id=start_marker`.
- Potential gap: the manifest has no content digest, so it cannot prove that bytes at
  a reviewed path were not replaced. A filename-only patch would not satisfy full
  artifact identity.
- Evidence: `fantasy_agent/approval_manifest.py::_match_keys`, manifest models in
  `fantasy_agent/contracts.py`, approval tests, and the recorded characterization.
- Product Risk: high (approval and artifact integrity).
- Coordination Necessity: low for path-only matching, but medium/high for an honest
  content-binding contract spanning review creation, schema, Studio persistence,
  Blender format conversion, and execution.
- Likely review axes: Data, Compatibility, then Security if execution is changed.
- Testability: path mismatch is deterministic; content binding requires a declared
  digest lifecycle.
- External side effects: none required; `tmp_path` and fake bridges suffice.
- Scope: complete fix is cross-contract.
- Decision: rejected for this one-change experiment. This is a real residual Product
  Finding, not evidence that the selected mode heuristic failed.

## Candidate D - generated artifact path boundary

- Observed behavior: shared helpers reject absolute paths, parent traversal, prefix
  violations, and resolved escapes. MCP tests cover outside-root cases; resolution
  also contains symlink targets through `resolve().relative_to(root)`.
- Potential gap: overwrite policy and every Windows junction/device-name case were
  not exhaustively characterized.
- Evidence: `fantasy_agent/path_safety.py`, MCP bridge path helpers, and outside-root
  tests in Blender/Godot/Unreal/ComfyUI suites.
- Product Risk: high for a proven escape; none was observed.
- Coordination Necessity: low for the shared helper, higher if per-adapter overwrite
  policy changes.
- Likely review axes: Security.
- Testability: deterministic temporary filesystem; no real escape file required.
- External side effects: none.
- Scope: bounded only if a helper-level gap is proven.
- Decision: rejected as the explicit "no real gap found" candidate.

## Candidate E - MCP/local-tool endpoint boundary (selected)

- Observed behavior: remote ComfyUI endpoints are rejected by default and execution
  still requires confirmation. However, a planning call accepted
  `http://user:secret@localhost:8188` because locality checks only the hostname.
  The endpoint is a field of `ComfyUIRunManifest`, so `write_files=true` can persist
  URL credentials.
- Potential gap: embedded username/password can cross planning, probing, and manifest
  boundaries; existing remote-endpoint errors can also echo the supplied endpoint.
- Evidence: public `call_comfyui_mcp_tool` characterization returned planned rather
  than error; `ComfyUIRunManifest.endpoint`; `_is_local_endpoint`; manifest writer.
- Product Risk: high security and credential-disclosure risk.
- Coordination Necessity: low; one Python implementation owner, one module, one test
  file, no runtime integration.
- Likely review axes: Security in addition to permanent Spec and Standards.
- Testability: deterministic public-interface calls with a fake client factory.
- External side effects: none; the test must prove the fake client is not called.
- Scope: bounded endpoint validation and no-secret error behavior.
- Decision: selected because the gap is real, independently acceptable, fully
  testable, and high-risk/low-coordination without forcing Lightweight.

## Counterexample summary

1. High Product Risk + low coordination: selected Candidate E.
2. High Product Risk + high coordination: complete Candidate C content binding or a
   Candidate A cross-engine authority redesign.
3. Dangerous-looking but protected: Candidate A sampled pre-write validation.
4. Local-looking but cross-owner: Candidate B shared confirmation authority.
5. No real gap: Candidate D in sampled path escape behavior.

No candidate was selected merely to support Phase 9. Candidate E replaced the
initial provisional Candidate C because it permits a complete, honest bounded fix.
