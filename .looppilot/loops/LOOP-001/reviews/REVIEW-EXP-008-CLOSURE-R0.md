# EXP-008 Independent Closure Review R0

- Reviewer: `/root/exp008_closure_reviewer`
- Boundary: product HEAD `068f25b13a4f5c3fb1fb377d81b68a02e528b586` plus staged
  index tree `d9c6bae2ec77e06944381cfb8f50bcba248725d4`
- Spec: FAIL.
- Standards: FAIL.
- Evidence/Factual Accuracy: FAIL.
- Conjunctive verdict: `NOT-CLOSEABLE`.
- Reviewer remained read-only; this was not a final-HEAD review.

## Findings

- `EXP008-CLOSURE-SPEC-001`, Major: public plan/Studio review retains Blender `.fbx`,
  Godot executor exports `.glb`, and the integration test hid the mismatch by replacing the
  review path with `.glb`. The real public invariant was not proven.
- `EXP008-CLOSURE-STD-001`, Major: Ledger/Integration/Closure projections retained stale,
  contradictory lifecycle statements.
- `EXP008-CLOSURE-EVID-001`, Minor: staged governance was 42 files / 3,146 physical lines,
  not 42 / 2,212.
- `EXP008-CLOSURE-EVID-002`, Minor: R0 added three Closure Review EII groups, taking the
  stated grouping from 15 to 18 before subsequent Rework.

## Independently Verified

Eleven product/test artifacts and 525/18 product diff; all eleven hashes matched; seven
evaluation artifacts; seven Deliveries with 7 successful/0 unsuccessful/0 zero-output;
three pre-R0 Major Findings recorded closed; staged diff check passed.

Fresh pytest/Ruff, ignored cleanup, original-main/LoopPilot Git state, supplied staged-tree
SHA, and final commit/push/sync remained unverified in R0. Product and governance Findings
must be corrected, re-integrated, and independently reverified before closure.
