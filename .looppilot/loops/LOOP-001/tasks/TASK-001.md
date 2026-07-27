---
task_id: TASK-001
parent_goal: PROJECT-EXP-008 / LOOP-001
status: integrated
previous_status: approved
status_changed_by: supervisor
assigned_role: worker
assigned_to: /root/exp008_worker_a
objective: Produce canonical reviewed-artifact identity in approval manifests.
scope:
  allowed:
    - fantasy_agent/artifact_identity.py
    - fantasy_agent/contracts.py
    - fantasy_agent/workflows.py
    - tests/test_creative_review_agent.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-001.md
  forbidden:
    - fantasy_agent/approval_manifest.py
    - fantasy_agent/executor.py
    - tests/test_executor.py
    - tests/test_approval_identity_integration.py
    - authoritative Ledgers, Loop Map, Project, Checkpoint, and Loop Contract
deliverables:
  - canonical SHA-256 artifact identity contract and implementation
  - manifest producer binding reviewed bytes
  - characterization RED, minimal GREEN, focused tests, and Worker Delivery
success_criteria:
  - produced approval decision contains the digest of the reviewed file bytes
required_evidence:
  - focused pytest command, observed RED/GREEN, diff, and dispatch Git boundary
dependencies:
  - none
research_inputs: []
skill_assignment:
  required: []
  optional: []
  forbidden:
    - installing or inventing skills
  fallback:
    - strategy: Use repository code and Task Contract only.
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
reviewer: REVIEWER-TASK-001
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-26
updated: 2026-07-26
---

# Task Contract — TASK-001

## Identity and Objective

WORKER-A owns the approval-identity producer. Create one canonical SHA-256 identity API and
record exact reviewed-file identity in every built approval decision.

## Before State

Contracts and `build_asset_approval_manifest` store path/decision metadata only.

## Owned Files / Domain

Only `scope.allowed`: contracts, identity, manifest production, producer tests, and Delivery.

## Allowed Reads and Forbidden Writes

Read dependencies. Do not write consumer-owned files, authoritative governance, unrelated
paths, or LoopPilot. No delete, commit, push, merge, external tools, or scope expansion.

## Inputs and Outputs

Input: Creative Review item and artifact path. Output: canonical identity API, serialized
approval identity, tests, and Delivery.

## Acceptance

- SHA-256 of exact bytes, lowercase hex, explicit algorithm; missing/unreadable input fails.
- Serialization is deterministic; record real characterization RED then minimal GREEN.
- Delivery includes Verifiable Claims table and explicit Unverified Claims.

## Focused Tests

`python -m pytest tests/test_creative_review_agent.py -q` plus narrow new selections.

## Dependencies and Git Boundary

No Task dependency. Dispatch boundary is the baseline/contract commit at branch HEAD; record
its exact SHA and diff in Delivery. Never commit.

## Reviewer and Revision

`REVIEWER-TASK-001` independently decides Spec and Standards. Revision 0 of 2.

## Worker Submission

Record outputs/evidence/risks/unfinished/conflicts in `DELIVERY-TASK-001.md`; do not announce
parent or Loop completion.
