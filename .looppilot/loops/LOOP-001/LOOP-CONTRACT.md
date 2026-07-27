# Loop Contract

## Identity

- Project ID: `PROJECT-EXP-008`
- Loop ID: `LOOP-001`
- Title: Approval identity and ingest enforcement
- Contract Status: approved
- Created/updated: 2026-07-26
- Supervisor: root
- Integrator: root
- Status authority: `.looppilot/LOOP-MAP.md`

## Objective

Bind each approved asset decision to the bytes reviewed and fail closed when current bytes
do not match at Godot ingest.

## Before and After State

- Before: approval is path/stem based; same-path replacement remains approved.
- After: manifest carries canonical SHA-256 identity; unchanged content is accepted and
  missing, malformed, or mismatched identity is rejected before copy.

## User and System Outcomes

Reviewers authorize specific bytes, executors enforce the same identity, and legacy/stale
authority cannot silently cross the ingest boundary.

## Included Changes

Canonical identity helper/contract, manifest production, Godot manifest filtering/execution,
focused and cross-owner tests, integration, reviews, and evaluation.

## Excluded Changes

Real tools, Unreal Creative Review ingest, generic migration, frontend changes unless a
producer schema break is proven, test-harness cleanup, releases, deploys, and main changes.

## Grouping Rationale

One outcome crosses approval-authority and ingest-enforcement owners. A single Loop preserves
one acceptance boundary while two Tasks preserve independent implementation accountability.

## Mode Decision Context

- Mode: Full Loop.
- Product Risk: high.
- Coordination Necessity: high.
- Evidence: `docs/experiments/looppilot-exp-008/MODE-SELECTION.md`.
- Supervisor decision / Integrator record: Full Loop selected and recorded 2026-07-26.
- Lightweight rejected because authoritative multi-owner Deliveries, integration, and
  failed-delegation fallback history are required.

## Coordination Necessity

- Two real owners: identity producer and enforcement consumer.
- Primary writes do not overlap; Deliveries and focused tests are independently checkable.
- TASK-002 follows the canonical API from TASK-001.
- A dedicated Integration Record proves agreement over real temporary-file bytes.
- Expected cost: two Worker attempts, two Task reviews, four Loop review axes, checkpoints.

## Engineering Context References

- Project context: `.looppilot/PROJECT.md`.
- Baseline: `docs/experiments/looppilot-exp-008/BASELINE-AND-VERIFICATION-SURFACE.md`.
- Candidate evidence: `docs/experiments/looppilot-exp-008/CANDIDATE-AUDIT.md`.

## Business Rules and Invariants

- Approved, allowed-path, present-file, well-formed-identity, and digest match are conjunctive.
- Cross-owner invariant: reviewed identity = manifest identity = ingest-time identity.
- Digest algorithm is SHA-256 over exact file bytes with lowercase hexadecimal encoding.
- Identity failure is fail closed and must not be converted to path-only approval.
- Existing `.fbx`/`.glb` path equivalence cannot substitute for byte identity.

## Engineering Concern Matrix

| Concern | Impact | Work | Reviewer |
|---|---|---|---|
| Security | same-path substitution | negative mismatch enforcement | Security |
| Compatibility | path-only legacy manifest | explicit fail-closed tests | Compatibility |
| Data | canonical representation | one shared helper/API | Standards |
| Business rule | reviewed equals ingested | combined test | Spec |

## Architecture Profile

- Minimal pure identity module; no framework or dependency addition.
- Producer records shared value; consumer imports rather than duplicates it.
- Streaming hash for bounded memory use.
- Rejected: permissive fallback, duplicate algorithms, unrelated refactor.

## Task DAG

`TASK-001 (producer contract) -> TASK-002 (consumer enforcement) -> formal integration -> reviews -> closure`.

## Worker Plan

- TASK-001 / WORKER-A primary: identity contract, manifest production, producer tests.
  Fallback: WORKER-B only after two unsuccessful unchanged attempts and formal reassignment.
- TASK-002 / WORKER-B primary: ingest enforcement and consumer/cross-owner test.
  Fallback: WORKER-A only after two unsuccessful unchanged attempts and formal reassignment.
- Maximum implementation Workers: 2; no decorative third Worker.
- First-round primary write ownership must not overlap.

## Reviewer Matrix

### Mandatory Axes

- Spec and Standards for every Delivery and the fixed integration boundary.

### Conditional Reviewers

- Security and Compatibility are active for the Loop boundary.
- Data review is not loaded: no database, migration, or sensitive-data lifecycle is added.

## Integration Strategy

- Accept only independently reviewed Deliveries.
- Freeze and record the combined Git/diff boundary.
- Run a temporary-file sequence: create -> manifest -> unchanged accept -> replace -> reject.
- Check for duplicate digest logic, ownership overlap, compatibility fallback, and incomplete
  executor propagation.
- Integration returns `integration-ready`, `needs-rework`, or `blocked`; Integrator writes no
  product code. RED returns to the owning Worker, then integration is rerun.

## Acceptance Criteria

### Functional Acceptance

Manifest binds bytes; unchanged bytes pass; missing/malformed/mismatched identity fails closed.

### Engineering Acceptance

Focused RED/GREEN evidence, non-overlap, shared API, cross-owner GREEN, full pytest and Ruff.

### Delivery Acceptance

Deliveries, Integration Record, reviews, closure review, RESULTS, four coherent commits,
experiment-branch push, sync, clean status, and disclosed external-tool limits.

## Barriers

### Contract Barrier

Passed: objective, scope, invariant, DAG, ownership, fallback, budgets, review, acceptance,
rollback, stop conditions, and authority are explicit before implementation.

### Implementation Barrier

Opens after baseline/contract commit and dispatch with the exact HEAD; each Task must submit a
verifiable Delivery and Task-level Spec+Standards approval.

### Integration Barrier

Both Tasks approved, ownership clean, combined invariant executable, and Integration Record
`integration-ready`.

### Review Barrier

Fixed boundary receives Spec, Standards, Security, and Compatibility decisions; Major or
Blocker requires rework or explicit block and original Reviewer reverification.

### Closure Barrier

All mandatory Tasks integrated, Findings permitted, validation/commit results honest,
Checkpoint current, independent Closure Review delivered, residuals disclosed.

## Budget

- Same unchanged responsibility: maximum two unsuccessful Worker attempts.
- Unsuccessful attempt follows the user definition; ordinary RED/Rework or valid blocked
  Delivery does not automatically consume it.
- Revision budget: two normal revisions per Task; additional work requires Supervisor replan.
- Fallback is pre-registered above. Ownership collapse preserves Reviewer, Integrator,
  Supervisor, revision, attempt, and Finding histories.
- If no failure occurs, failure budget and ownership collapse are `not exercised`.

## Rollback and Stop Conditions

- Rollback: revert bounded experiment commits; no data migration.
- Stop for unresolved Major/Blocker, scope/authority drift, inability to prove the invariant,
  two unsuccessful unchanged attempts without safe fallback, or critical context pressure.
- Block honestly rather than fabricate Delivery or external-tool evidence.

## Authority

- Workers: read scoped dependencies; modify owned paths only; no delete/commit/push/merge.
- Reviewers: read-only; no implementation/status/commit/push.
- Integrator: governance recording, integration commands, stage/commit/push experiment branch;
  no product implementation.
- User authorizes experiment-branch commits and push only. No main push, merge, PR, tag,
  release, deployment, force push, or real external side effect.

## Risks and Open Decisions

- Legacy path-only manifests intentionally fail closed; Compatibility Reviewer must confirm.
- Check-after-hash filesystem replacement remains unverified outside this bounded local model.
- Exact Worker agent IDs and dispatch HEAD are recorded at dispatch; roles are fixed here.
