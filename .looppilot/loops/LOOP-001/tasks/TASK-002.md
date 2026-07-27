---
task_id: TASK-002
parent_goal: PROJECT-EXP-008 / LOOP-001
status: integrated
previous_status: approved
status_changed_by: supervisor
assigned_role: worker
assigned_to: /root/exp008_worker_b
objective: Enforce approved artifact identity at the Godot ingest boundary.
scope:
  allowed:
    - fantasy_agent/approval_manifest.py
    - fantasy_agent/executor.py
    - tests/test_executor.py
    - tests/test_approval_identity_integration.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-002.md
  forbidden:
    - fantasy_agent/artifact_identity.py
    - fantasy_agent/contracts.py
    - fantasy_agent/workflows.py
    - tests/test_creative_review_agent.py
    - authoritative Ledgers, Loop Map, Project, Checkpoint, and Loop Contract
deliverables:
  - ingest-time identity enforcement and fail-closed behavior
  - deterministic same-path replacement integration test
  - characterization RED, minimal GREEN, focused tests, and Worker Delivery
success_criteria:
  - unchanged approved bytes pass and replaced bytes reject before copy
required_evidence:
  - focused pytest command, observed RED/GREEN, diff, and dispatch Git boundary
dependencies:
  - TASK-001 approved producer API
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
reviewer: REVIEWER-TASK-002
integration_owner: root
revision_count: 0
revision_budget: 2
created: 2026-07-26
updated: 2026-07-26
---

# Task Contract — TASK-002

## Identity and Objective

WORKER-B owns the consumer. Enforce TASK-001 identity before Godot asset copy and provide
the same-path-substitution integration test.

## Before State

The filter uses path/stem equivalence only; executor accepts stale same-path contents.

## Owned Files / Domain

Only `scope.allowed`: manifest filter, executor, consumer/integration tests, and Delivery.

## Allowed Reads and Forbidden Writes

Read TASK-001's API and dependencies. Do not edit producer files, authoritative governance,
unrelated paths, or LoopPilot. No delete, commit, push, merge, external tools, permissive
legacy fallback, or scope expansion.

## Inputs and Outputs

Input: TASK-001 API/manifest and current asset path. Output: fail-closed enforcement, tests,
and Delivery.

## Acceptance

- Import shared API; no duplicate algorithm.
- Matching bytes pass; missing/malformed identity, missing file, or mismatch rejects.
- Preserve path equivalence only with matching identity; record real RED then minimal GREEN.
- Delivery includes Verifiable Claims and explicit Unverified Claims.

## Focused Tests

`python -m pytest tests/test_executor.py tests/test_approval_identity_integration.py -q`.

## Dependencies and Git Boundary

TASK-001 must be approved. Record then-current HEAD, reviewed dependency, and diff in Delivery.
Never commit.

## Reviewer and Revision

`REVIEWER-TASK-002` independently decides Spec and Standards. Revision 0 of 2; integration
RED returns to the owner and is not automatically an unsuccessful attempt.

## Worker Submission

Record outputs/evidence/risks/unfinished/conflicts in `DELIVERY-TASK-002.md`; do not announce
parent or Loop completion.
