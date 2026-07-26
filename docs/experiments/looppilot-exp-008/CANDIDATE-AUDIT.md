# EXP-008 Full Loop Candidate Audit

Status: complete

Audit boundary: `origin/main` at `4355dd6d70a58477673f2a6e29c923219d3e8801`

## Candidate A — Approval Identity / Stale Artifact Gate

Observed chain: `artifact -> Creative Review -> approval manifest -> Godot ingest`.

- `CreativeReviewItem`, `AssetApprovalDecision`, and `AssetApprovalManifest` record IDs,
  paths, sources, and decisions, but no content digest.
- `build_asset_approval_manifest` copies those fields without binding reviewed bytes.
- `filter_approved_blender_assets` matches path/stem keys, treats `.fbx` and `.glb` as
  equivalent, and never checks bytes.
- `executor.py` uses that filter before Godot copying; a stale manifest for the same path
  remains trusted after byte replacement.
- Deterministic characterization produced:
  `{'digest_changed': True, 'before_approved': ['generated/assets/gate.glb'], 'after_approved': ['generated/assets/gate.glb']}`.
- Unreal validates `ProductionSpecBundle` and can warn on `approved_assets_only`, but it
  does not consume this Creative Review manifest. Real Unreal ingest is unverified.

Two real responsibility owners exist: the approval producer defines and records the identity
of reviewed bytes; the ingest consumer rejects current bytes that do not equal that identity.
Their write sets can be non-overlapping and each has a focused Delivery. Neither alone can
prove `reviewed identity = manifest identity = ingest-time identity`. A deterministic
integration test can create a manifest, accept unchanged bytes, replace the same path, and
observe rejection without an engine. Candidate A passes the gate. Compatibility is a review
axis, not an artificial third implementation owner.

## Candidate B — ProductionSpecBundle Version Migration + Approval

`load_production_spec_bundle` model-validates and rejects versions other than `0.1`;
`compile_production_spec_bundle` validates and dispatches. No migration, semantic diff, or
change-approval authority exists. README lists these as future work. The gap is real, but
introducing migration, diff, approval, and UI representation together is not a bounded
experiment task. Rejected rather than artificially split.

## Candidate C — Cross-engine Spec Adapter Consistency

Godot and Unreal adapters consume the same `ProductionSpecBundle`. Public compilation and
both executor paths validate before writes. Unreal adds QA evidence, but the audit found no
deterministic inconsistency requiring independent shared/Godot/Unreal owners. Rejected for
lack of a proven multi-owner gap; starting editors would also violate the tool boundary.

## Candidate D — Execution Approval Across Surfaces

CLI uses bare `--yes`; Studio preview/run requests use bare `confirmed` across separate
requests. No operation ID, confirmation ID, nonce, fingerprint, or digest binds approval to
the exact operation. Inspected ChatGPT/MCP-facing tools are planning-only, so three execution
surfaces do not share one authority. This is a real two-surface gap, but redesigning public
request semantics is broader and less isolated than A. Deferred, not declared safe.

## Candidate E — Packaged Playtest / Runtime Metrics

README identifies packaged Godot playtest/runtime metrics as future work. Credible end-to-end
verification requires a real editor/runtime or GUI-heavy environment. Rejected because
external-tool validation would dominate the coordination experiment.

## Selection Gate

| Mandatory condition | Candidate A evidence |
| --- | --- |
| Two real owners | Approval-authority producer and ingest-enforcement consumer |
| Non-overlapping writes | Contract/workflow producer paths versus manifest/executor consumer paths |
| Independent Delivery | Identity creation versus mismatch enforcement |
| Integration-only invariant | Both owners must compute the same identity for the same bytes |
| No production/release/deploy | Temporary files and deterministic hashes only |
| No real external tool | Python tests; no engine/editor launch |
| Deterministic integration | Unchanged bytes accepted; same-path replacement rejected |
| Bounded scope | Shared identity contract plus Godot approval gate |

Decision: `FULL LOOP SELECTED — Candidate A`.
