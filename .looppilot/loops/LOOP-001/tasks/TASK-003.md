---
task_id: TASK-003
parent_goal: PROJECT-EXP-008 / LOOP-001
status: integrated
previous_status: approved
status_changed_by: supervisor
assigned_role: worker
assigned_to: /root/exp008_worker_a
objective: Reconcile byte-bound manifest production with existing approval surfaces.
scope:
  allowed:
    - tests/test_production_spec_runtime.py
    - tests/test_studio_app.py
    - tests/test_creative_review_agent.py
    - fantasy_agent/workflows.py
    - fantasy_agent/artifact_identity.py
    - fantasy_agent/contracts.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-003.md
  forbidden:
    - fantasy_agent/approval_manifest.py
    - fantasy_agent/executor.py
    - tests/test_executor.py
    - tests/test_approval_identity_integration.py
    - authoritative governance and LoopPilot
deliverables:
  - correction for TASK001-SPEC-001
  - adjacent and producer GREEN evidence
  - Rework Delivery preserving original judgment
success_criteria:
  - affected tests materialize reviewed bytes and the adjacent selection passes without path-only fallback
required_evidence:
  - original 3-failure RED, corrected GREEN, focused Ruff, diff, Git boundary
dependencies:
  - TASK-001 delivery and REVIEW-TASK-001-R0
research_inputs: []
skill_assignment:
  required: []
  optional: []
  forbidden:
    - installing or inventing skills
  fallback:
    - strategy: repository code and scoped Rework Contract only
skill_selection:
  considered: []
  selected: []
  verified_available: []
  selected_by: supervisor
authority:
  read: true
  modify: true
  delete: false
  commit: false
  push: false
  release: false
  deploy: false
  external_communication: false
reviewer: /root/exp008_task001_reviewer
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-26
updated: 2026-07-26
---

# Rework Task Contract — TASK-003

## Identity and Objective

Rework of TASK-001 for Major Finding `TASK001-SPEC-001`. WORKER-A must restore the three
adjacent producer surfaces while preserving byte-bound approval and original review history.

## Before State

Producer-focused tests pass, but the fixed adjacent selection has 3 failures because planned
artifact paths do not exist when identity is computed.

## Owned Files / Domain

Only the listed producer code/tests and Rework Delivery. Prefer test-fixture materialization;
change producer code only if evidence shows the contract cannot otherwise remain honest.

## Allowed Reads and Forbidden Writes

Read the original Contract, Delivery, Review, and Finding. Do not edit consumer files,
authoritative governance, review/finding history, or unrelated paths. No commit/push/delete,
external tools, path-only fallback, or identity-less approval.

## Inputs and Outputs

Inputs: original submitted diff, Major Finding, exact adjacent RED. Outputs: minimal repair,
updated focused tests if needed, `DELIVERY-TASK-003.md`.

## Acceptance

- Materialize actual bytes before manifest creation in affected test/flow selections.
- Keep missing real reviewed artifacts fail closed and all newly approved decisions identified.
- Adjacent selection: 4 passed; producer selection: 5 passed; focused Ruff and diff check pass.
- Delivery has Verifiable Claims, explicit Unverified Claims, RED/GREEN, and exact boundary.

## Focused Tests

Run the exact adjacent selection from the Finding, then `tests/test_creative_review_agent.py`.

## Dependencies and Git Boundary

Depends on TASK-001 submission and R0 review. Boundary remains baseline commit
`cec04ed22350e334c40e32dd6117cd17e3049294` plus the preserved TASK-001 diff; record it.

## Reviewer and Revision

Original `/root/exp008_task001_reviewer` must reverify Spec and preserve Standards judgment.
Revision 1 of 2. This ordinary Rework is not an unsuccessful Worker attempt.

## Worker Submission

Record only Rework output/evidence/risks in `DELIVERY-TASK-003.md`; do not rewrite original
Delivery/Review/Finding or claim Task/Loop/Project completion.
