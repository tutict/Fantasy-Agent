# EXP-008 Independent Closure Review R2

- Reviewer: `/root/exp008_closure_reviewer`
- Product boundary: `52173e08ae267700ef62e7e563ab6a50523981ad`
- Frozen R2 tree: `4a874844744f92d60378d48aaa6787334942eb24`
- Spec: **PASS**
- Standards: **FAIL**
- Evidence/Factual Accuracy: **FAIL**
- Conjunctive verdict: **`NOT-CLOSEABLE`**

## Independently Observed Boundary

- `git rev-parse HEAD` returned the exact product boundary.
- `git cat-file -t 4a8748...` returned `tree`.
- `git diff --cached --name-status 4a8748...` was empty: index equals the frozen tree.
- `git diff --name-status` was empty: tracked worktree equals index.
- Tree and cached `git diff --check` both exited 0.
- The tree differs from product HEAD in exactly 73 paths: 70 under `.looppilot/**`,
  three under `docs/experiments/looppilot-exp-008/**`, and zero outside those scopes.
- No product, test, or frontend path changed after `52173e0`.
- TASK-010 independently reports `revision_count: 2` and `revision_budget: 2`;
  the Task Ledger records revision 2 under review.

## Byte and Line Accounting

The Reviewer enumerated paths with `git ls-tree -r --name-only <tree> -- <prefix>`.
After proving tree/index/worktree equality, each corresponding worktree file was read
as raw bytes. Bytes are the byte-array lengths. Physical lines are LF-byte count,
plus one only for a nonempty file lacking a final LF. All measured files were nonempty
and ended with LF.

| Boundary | Files | Physical lines | Bytes |
|---|---:|---:|---:|
| `.looppilot/**` | 70 | 4,559 | 208,197 |
| EXP-008 evaluation directory | 7 | 627 | 36,331 |

## EII and Worker Accounting

The pre-R1 subtotal is 43. R1 added groups 44-45; R2 preparation added groups 46-49:

- 46: repeated identical apply-patch sandbox-helper refresh failures, coalesced.
- 47: batch-wrapper ACL denial.
- 48: distinct batch-wrapper argument/terminator transport failure.
- 49: same-phase tree-freeze/restaging index-lock denials, coalesced.

Arithmetic is `43 + 2 + 4 = 49`. The grouping distinguishes phase/cause and
coalesces identical repeats consistently. R2 inspection added no new EII; the recurring
global-ignore warning remains coalesced.

Eleven Delivery artifacts remain present. All eleven assignment turns produced valid
Deliveries; TASK-008's reviewed rejection and later Rework are not an unsuccessful
unchanged or zero-output attempt. Worker unsuccessful/zero-output remains `0 / 0`.

## Finding Reverification

### `EXP008-CLOSURE-STD-001`: NOT VERIFIED-CORRECTED

All five specific R1 content defects were corrected. Current governance nevertheless
retains blocking stale claims:

- `LOOP-CONTRACT.md` changed three commits to four in revision 2, but its current
  `Created/updated` metadata still says only `2026-07-26`.
- `HANDOFF.md` says remaining work is to finish revision 2 and freeze/stage R2 although
  TASK-010 is already under review and the frozen R2 tree exists. Its Resume Point and
  Recommended Next Action repeat that stale pre-freeze state.
- `CHECKLIST.md` likewise points to finishing revision 2 and freezing R2 instead of the
  authoritative Checkpoint action to conduct R2.

The current shared projections therefore do not consistently represent the frozen
review boundary.

### `EXP008-CLOSURE-STD-002`: VERIFIED-CORRECTED

The R1 uncontracted delegation is preserved in the Finding, Delegation, Coordination,
Handoff, Checkpoint, Closure, Results, and Scorecard. They state that both support Agents
were interrupted, their outputs were unread and excluded, and the original Reviewer
remained sole judgment authority. R2 was performed personally, with no Agent spawned
and no interrupted R1 support output read or used.

### `EXP008-CLOSURE-EVID-001`: NOT VERIFIED-CORRECTED

The actual pre-R2 totals are exactly correct. However, current `RESULTS.md` item 58 says
final accounting is pending `R1/Finding/R2 artifacts`. The measured 70-file pre-R2
boundary already includes the R1 Review and STD-002 Finding; only the R2 artifact is
absent. That current inclusion claim is factually inaccurate.

### `EXP008-CLOSURE-EVID-002`: VERIFIED-CORRECTED

The frozen subtotal is exactly 49, groups 46-49 are consistently classified/coalesced,
later incidents remain explicitly open, and Worker attempt accounting remains separate
at `0 / 0`.

## Evidence Limits

- Product behavioral suites were not rerun because the product boundary is unchanged
  and R2 is governance-only.
- Recorded pytest 177, Ruff, CLI, frontend typecheck/build, and cleanup results remain
  attributed to their existing evidence artifacts.
- Real Blender, ComfyUI, Godot/Unreal Editors, remote MCP, browser E2E, GLB parsing/import,
  packaging, release, deployment, post-hash/pre-copy mutation, fresh remote-main state,
  and original-main byte equality remain unverified.

## Stop Decision

Standards and Evidence/Factual Accuracy fail conjunctively. The frozen R2 candidate is
therefore `NOT-CLOSEABLE`.

TASK-010 has exhausted its `2 / 2` revision budget. This review does not propose or
authorize an unchanged revision 3.

## Read-Only Statement

The Reviewer modified no file, index, Ledger, implementation, governance artifact,
Git metadata, commit, branch, tag, or remote state; invoked no metadata-writing Git
command or real external tool; and delegated no part of R2.
