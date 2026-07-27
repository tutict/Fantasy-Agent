# EXP-009 Recovery Analysis

Status: `CANDIDATE-AWAITING-INDEPENDENT-REVIEW`

## Boundary Reconciliation

- Product HEAD is `52173e08ae267700ef62e7e563ab6a50523981ad`.
- Archive A is `ebf2a60266342cf90a76dd34c5dece732d54f2ed`; its tree is exactly
  `4a874844744f92d60378d48aaa6787334942eb24`.
- Archive B and the EXP-009 base are `8b6075aaee8e86a6c7905911487e537672a4125b`.
- The preregistration commit is `5a0347a7bf7161ac992e1dfa1ea86f68b634dc85`.
- Git reports no change from Product HEAD under `fantasy_agent`, `tests`, or `apps`.
- Git reports no EXP-009 change to the archived `.looppilot` or EXP-008 evaluation paths.
- TASK-010 has the same blob `e00de12b4bd6e7f7e87bcda8e6df4f2bb2e8c80a`
  at Archive B and the candidate boundary.

## Inventory Reconciliation

The frozen inventory has 93 members and membership SHA-256
`8057eadae81aa4e87c921e4d7e0cdc01259798852a465b47941a6fa479902ecd`.
The validator independently derives each row from source Git blobs and passes count,
membership, SHA-256, physical-line, byte, and product-boundary checks together.

| Category | Members |
|---|---:|
| PRODUCT | 14 |
| AUTHORITATIVE_GOVERNANCE | 7 |
| SUPPORTING_GOVERNANCE | 40 |
| REVIEW | 24 |
| EVALUATION | 7 |
| RECOVERY | 1 |

The 71 `.looppilot` members total 4,709 physical lines and 215,285 source bytes. The
eight EXP-008 evaluation/recovery members total 720 lines and 39,663 bytes. The 14
product evidence members total 7,661 lines and 281,539 Git-blob bytes.

### Hash Convention Reconciliation

Twelve of the fourteen INTEGRATION-003 hashes equal Product HEAD Git-blob bytes. The
two TypeScript paths use `i/lf w/crlf`; their recorded Integration hashes exactly equal
the CRLF checkout bytes, while the inventory intentionally hashes the LF source blobs
named by its source commit/tree. This is a declared byte-domain difference, not an
unexplained mismatch and not a reason to change frozen membership.

## Root-Cause Reconciliation

STD-001 remains a confirmed Major historical Finding with primary root cause
`TASK_CONTRACT` and secondary `GOVERNANCE_OVERHEAD`/`EVIDENCE_GAP`. EVID-001 remains a
confirmed incorrect governance claim with primary `EVIDENCE_GAP` and secondary
`TASK_CONTRACT`. Correct totals did not prove correct prose membership.

The archive still contains the exact stale projections identified by R2 in HANDOFF,
CHECKLIST, LOOP-CONTRACT metadata, and EXP-008 RESULTS. EXP-009 treats those bytes as
historical evidence of the blocked outcome. It neither edits them nor repeats them as
current EXP-009 state. STD-002 and EVID-002 remain R2 `VERIFIED-CORRECTED`.

## Process Comparison

| Dimension | EXP-008 TASK-010 | EXP-009 |
|---|---|---|
| Mode | Full Loop | Lightweight |
| Objective | closure correction | evidence recovery |
| Product writes | prohibited | prohibited |
| Inventory | mutable/implicit | fixed/explicit |
| Artifact accounting | totals plus prose | membership plus totals |
| Writer count | root Integrator | one Evidence Owner |
| Review | Full Closure | bounded independent three-axis Review |
| Revision budget | 2 | 1 experiment correction |
| Governance surface | 71 archived files | 5 bounded governance files |
| Historical state | mutable projections | immutable archived reference |

## Research Questions

1. Fixed inventory prevented silent omission: all 93 expected commit/path members are derived and compared.
2. Membership validation prevented the EVID-001 error type by checking the set and totals together.
3. Lightweight produced the candidate with one owner; final sufficiency awaits Review.
4. Full Loop would be disproportionate for this read-only, single-owner recovery.
5. The 71-file surface was an important amplifier, but the Task Contract gap remained primary.
6. No stale present-tense claim was found in the new EXP-009 artifacts before Review.
7. The one-correction budget has not been exercised; sufficiency is therefore not yet tested.
8. Independent Reviewer delivery is pending.
9. Eight EXP-009 EII groups occurred and all recovered without product/history mutation.
10. EXP-008 remains `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY`.

## Phase 9 Mechanisms

- Supported by EXP-008 history: Coordination Necessity, Worker Verifiable Claims,
  Integrator role discipline, revision budget, Checkpoint recovery, honest blocked closure.
- Tension: Reviewer independence and artifact accounting.
- Not exercised: Worker Failure Budget and Ownership Collapse.
- Supported by the recovery candidate: fixed membership, executable accounting, one
  canonical evidence source, and Lightweight proportionality.
- Contradicted: totals-alone accounting as sufficient evidence.
- Inconclusive before Review: Reviewer usefulness and correction sufficiency.

## Provisional Conclusion

The evidence supports recovery without changing historical failure. Final status remains
pending the required independent Review; the candidate does not claim acceptance.
