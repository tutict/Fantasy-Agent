# Finding — TASK001-SPEC-001

## Identity

- Source: `REVIEW-TASK-001-R0`
- Category / Severity / Status: Spec compatibility regression / Major / closed
- Affected Task/symbol: `TASK-001` / `build_asset_approval_manifest`
- Reviewer: `/root/exp008_task001_reviewer`
- Decision authority / recording authority: Supervisor / Integrator

## Evidence

Adjacent approval pytest returned 3 failed, 1 passed, 26 deselected. ProductionSpec
roundtrip and two Studio tests raise `FileNotFoundError` while hashing planned generated
paths that are not materialized.

## Impact

Focused producer tests are GREEN, but three active surfaces regress from the 159-pass
baseline, blocking TASK-001 and Loop acceptance.

## Supervisor Disposition

- Correct through scoped `TASK-003`; no risk acceptance or severity change.
- Materialize actual reviewed bytes for affected producer selections while retaining
  fail-closed identity authority.
- Original Reviewer reverification is mandatory.

## Verification and Closure

- Original Reviewer decision: `VERIFIED-CORRECTED`, Spec PASS; Standards PASS retained.
- Evidence: adjacent 4 passed, producer 5 passed, Ruff/diff check passed.
- Supervisor closure decision: close after verified scoped correction; no risk acceptance.
- Recorded by Integrator on 2026-07-26; history and severity preserved.

## Authority Boundary

Worker repairs only through TASK-003. Reviewer remains read-only. Integrator records but
cannot close or lower this Finding.
