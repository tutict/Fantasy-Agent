# Finding — LOOP001-SEC-001

- Source: `REVIEW-LOOP-001-SPECIALIST-R0`
- Category / Severity / Status: Security path containment / Major / closed
- Affected: `build_asset_approval_manifest` and Studio caller
- Reviewer: `/root/exp008_loop_specialist_reviewer`

## Impact

Untrusted review paths can cause Studio to hash readable files outside the workspace,
violating the producer trust boundary and exposing a local digest/existence oracle.

## Supervisor Disposition

Scoped TASK-006 to WORKER-A: explicit workspace root, contained resolution before hashing,
Studio passes REPO_ROOT, negative absolute/traversal/symlink tests. No permissive fallback,
risk acceptance, severity change, or unsuccessful-attempt charge. Original specialist must
reverify Security and continuing Compatibility after Task review and re-integration.

## Verification and Closure

- TASK-006 and TASK-007 each passed independent Spec and Standards review and were
  re-integrated in the eleven-file boundary.
- Original specialist R1: Security PASS, Compatibility PASS, `VERIFIED-CORRECTED`, no new Finding.
- Supervisor decision: close after original Reviewer verification; severity/history preserved.
- Integrator record: 78 fixed-boundary tests, eleven hashes, Ruff/diff, and 14 specialist
  assertions verified. TOCTOU and external-tool surfaces remain excluded residuals.
