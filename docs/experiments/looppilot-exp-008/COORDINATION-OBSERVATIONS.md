# EXP-008 Coordination Observations

Status: Closure R1 NOT-CLOSEABLE; TASK-010 revision 2 under review

Date: 2026-07-27

## Coordination Outcome

- Real implementation owners: 2; active implementation owners: 0.
- Worker assignments / valid Deliveries / approved outcomes: `11 / 11 / 10`.
- Unsuccessful unchanged attempts / zero-output attempts: `0 / 0`.
- Failure Budget: not exercised; fallback and ownership collapse: not triggered/not exercised.
- Human implementation rescue after dispatch: 0; Integrator changed no product/test file.
- Token usage: unavailable and not estimated.

TASK-008 produced a bounded, reviewable Delivery but failed Spec/Standards because its
mapping was target-agnostic. That is ordinary Finding/Rework history, not zero-output or
an unchanged unsuccessful attempt. TASK-011 corrected it under the same producer owner.

## Ownership History

| Worker | Responsibility | Tasks | Result |
|---|---|---|---|
| `/root/exp008_worker_a` | producer identity, callers, EOL, containment, target semantics | 001,003,004,006,008,011,012 | seven valid Deliveries; six approved outcomes |
| `/root/exp008_worker_b` | ingest, consumer EOL, integration caller/public proof | 002,005,007,009 | four approved Deliveries |

Cross-Worker primary product-file overlap remained zero. Worker B owned the shared
integration test; Worker A reported dependencies without editing it. Reviewers were read-only.

## Rework Accounting

| Wave | Trigger | Owner-preserving response | Result |
|---|---|---|---|
| 1 | `TASK001-SPEC-001` | TASK-003 producer caller materialization | verified corrected |
| 2 | `LOOP001-STD-001` | TASK-004/005 EOL normalization | verified corrected |
| 3 | `LOOP001-SEC-001` | TASK-006 containment + TASK-007 caller | verified corrected |
| Closure R0 | public FBX/GLB mismatch | TASK-008, TASK-011, TASK-009 | integrated; Closure reverify pending |
| Closure R0/R1 | governance/accounting and Reviewer discipline | TASK-010 Integrator-only | revision 2 under review |

No rework was manufactured to exercise the failure policy.

## Integration Value

`INTEGRATION-003` freezes fourteen hashes and an executable public invariant:

`reviewed concrete bytes = manifest identity = ingest-time concrete bytes`

It proved explicit Godot maps the unchanged public `.fbx` review item to actual `.glb`
bytes, while default/Unreal preserve `.fbx`; unchanged GLB bytes copy and same-path
replacement rejects. The fixed boundary passed 86 tests plus Ruff/diff/EOL/hash checks.

## Claim Reliability

All eleven Deliveries map claims to code, tests, commands, hashes, or explicit boundaries.
Independent Task review rejected TASK-008's semantic overreach and later approved the
target-aware correction and public-flow proof. Shared-worktree process authorship is not
cryptographically proven; hashes and reconstructable diffs bound accepted claims.

External tools/callers, atomic post-hash copy, release, and deployment remain unverified.

## Execution Infrastructure Incidents

The stable grouping is one event per phase/cause, with repeated identical warnings
coalesced. Through R2 freeze the observed subtotal is 49 groups:

- pre-Closure-R0 baseline/worker/review/integration/cleanup groups: 15;
- Closure R0 executable probe, Git ownership, and index-metadata ACL groups: 3;
- TASK-008 Reviewer basetemp ACL and no-output adjacent selection: 2;
- TASK-011 Worker patch-helper and basetemp ACL, plus Reviewer basetemp ACL: 3;
- TASK-009 Worker basetemp ACL and patch-helper, plus Reviewer basetemp ACL: 3;
- Integrator patch-helper, INTEGRATION-002 basetemp ACL, and origin fetch ACL: 3.
- fixed-boundary Spec/Standards Reviewer basetemp ACL: 1.
- fixed-boundary Specialist Reviewer basetemp ACL: 1.
- TASK-012 Worker/Integrator patch transport, normalization/index ACL, dependency
  resolution, Vite timestamp ACL, and junction cleanup: 5.
- TASK-012 Reviewer PowerShell quote transport: 1.
- product-commit staging index-lock ACL: 1.
- pre-R1 candidate write-tree index-lock ACL: 1.
- pre-R1 scoped-authorization reviewer service 503: 1.
- pre-R1 apply_patch sandbox-helper refresh failure: 1.
- pre-R1 direct workspace-write ACL: 1.
- pre-R1 lifecycle-rewrite assertion transport: 1.
- Closure R1 Reviewer write-tree index-lock ACL: 1.
- Closure R1 focused pytest basetemp ACL: 1.
- R2-preparation apply-patch sandbox-helper refresh failures, coalesced: 1.
- R2-preparation batch-wrapper ACL denial: 1.
- R2-preparation batch-wrapper argument/terminator transport failure: 1.
- R2 tree-freeze `git write-tree` and restaging index-lock ACL denials, coalesced: 1.

All recovered locally except the optional fresh origin refresh, which remains unverified.
No EII invalidated a Delivery or consumed Worker Failure Budget. Recurring global-ignore
and EOL notices are coalesced with their existing cause and not counted per occurrence.
The final count remains open until all reviews and validation finish.

## Recovery and Governance Cost

State advanced through `CHECKPOINT-028`. Conversation compaction resumed from current
authorities and rechecked files, hashes, tests, Git state, and permission scope.
Ledgers, Deliveries, Reviews, Integration, and Checkpoint directly supported decisions.
Checklist was the lowest-value projection; Handoff/Compaction were useful but duplicative.
Final artifact and byte-derived physical-line counts remain pending all evidence files.
During R1, two support Agents were spawned without Supervisor Contracts, interrupted, and
excluded without their output being read. The original Reviewer remained sole authority.

## EXP-006 Behavioral Comparison

| Observation | EXP-006 | EXP-008 current observation |
|---|---|---|
| Worker attempts | about 8 | 11 assignment turns |
| Zero-output | about 4 | 0 |
| EII | 9 reported | 49 grouped through R2 freeze; final pending |
| Failure budget | coordination stalled | not exercised |
| Fallback/collapse | no completed recovery | preregistered, not triggered |
| Integration | incomplete | fourteen files, 86 fixed-boundary tests |
| Product delivery | none | two product commits; fresh 177-test validation |
| Governance | 16 files reported | pre-R2 70 files / 4,559 lines / 208,197 bytes |

Reporting conventions and product tasks differ; no rate or score comparison is claimed.
The observed improvement is bounded to ownership, rework, integration, and EII separation.
