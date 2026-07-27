# EXP-008 Post-Block Root-Cause Archive

Status: `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY`

Date: 2026-07-27

This record archives the post-block Root-Cause Review outcome. It does not accept or
close EXP-008, reopen TASK-010, authorize another revision, or change the frozen R2
boundary.

## Historical Boundary

- Product HEAD: `52173e08ae267700ef62e7e563ab6a50523981ad`.
- Frozen R2 tree: `4a874844744f92d60378d48aaa6787334942eb24`.
- Closure R2: Spec PASS; Standards FAIL; Evidence/Factual Accuracy FAIL;
  `NOT-CLOSEABLE`.
- TASK-010: `blocked`; revision `2 / 2` exhausted; no revision 3.
- `EXP008-CLOSURE-STD-001`: open.
- `EXP008-CLOSURE-EVID-001`: open.
- `EXP008-CLOSURE-STD-002`: R2 `VERIFIED-CORRECTED`.
- `EXP008-CLOSURE-EVID-002`: R2 `VERIFIED-CORRECTED`.

## Root-Cause Classification

### STD-001

- Reality: `CONFIRMED`.
- Severity: `Major`.
- Primary root cause: `TASK_CONTRACT`.
- Secondary contributors: `GOVERNANCE_OVERHEAD`, `EVIDENCE_GAP`.

TASK-010 did not define every state projection, metadata field, and snapshot assertion
as a fixed, enumerable acceptance inventory. R1 and R2 therefore omitted members of a
mutable governance set.

### EVID-001

- Reality: `CONFIRMED`.
- Classification: `GOVERNANCE CLAIM INCORRECT`.
- Primary root cause: `EVIDENCE_GAP`.
- Secondary contributor: `TASK_CONTRACT`.

The byte-derived totals were correct, but the prose describing artifact membership was
incorrect. Correct arithmetic did not prove a correct membership claim.

STD-001 and EVID-001 are related but distinct. Their shared upstream conditions were a
mutable governance set, no fixed evidence inventory, and a non-executable consistency
requirement.

## Product and Blocking Boundary

- Product classification: `PRODUCT_ACCEPTABLE_WITH_RESIDUAL_RISK`.
- Primary blocker: `CONTRACT`.
- Secondary blocker: `EVIDENCE`.
- Tertiary blocker: `COORDINATION`.
- Product and Integration are not the remaining EXP-008 blockers.

The reviewed bounded invariant was concrete reviewed bytes = manifest identity =
ingest-time concrete bytes. TOCTOU behavior, real GLB parsing, real Unreal and Godot,
browser E2E, external callers, packaging, release, and deployment remain unverified or
residual and are not repaired by this archive.

## Phase 9 Outcomes

| Mechanism | Outcome |
|---|---|
| Coordination Necessity | supported |
| Worker Failure Budget | not exercised |
| Ownership Collapse | not exercised |
| Worker Verifiable Claims | supported |
| Integrator role discipline | supported |
| Reviewer independence | tension |
| Revision budget | supported |
| Checkpoint recovery | supported |
| Honest blocked closure | supported |
| Artifact accounting | tension |

TASK-010 revision budget `2 / 2` is not the Worker Failure Budget. Neither Worker
Failure Budget nor Ownership Collapse was exercised.

## EII Boundary

- EII groups 1-49: independently verified through the R2 freeze.
- EII group 50: reported after R2; not independently reviewed.

The archive must not describe group 50 as verified.

## Recovery Disposition

The selected next strategy is a separate `Strategy B / EVIDENCE-ONLY RECOVERY` under
EXP-009 Lightweight governance. It may reference, analyze, and reconcile this history,
but it is not TASK-010 R3 and cannot rewrite EXP-008. EXP-008 remains blocked regardless
of the later EXP-009 result.
