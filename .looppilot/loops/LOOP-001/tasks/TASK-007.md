---
task_id: TASK-007
parent_goal: LOOP-001 / LOOP001-SEC-001
status: integrated
previous_status: submitted
assigned_role: worker
assigned_to: /root/exp008_worker_b
objective: Adapt the consumer-owned cross-owner test to TASK-006's explicit workspace root.
scope:
  allowed:
    - tests/test_approval_identity_integration.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-007.md
  forbidden:
    - all producer and consumer implementation files, other tests, governance, LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: independent TASK-007 Reviewer
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-26
updated: 2026-07-26
---

# Cross-owner Caller Rework — TASK-007

Depends on approved TASK-006 producer API. Update only the integration test caller to pass
its trusted `tmp_path` workspace root. Do not weaken or infer the root, edit producer/consumer
implementation, or change test expectations. Run the two cross-owner tests and focused Ruff;
preserve LF/hash stability. Delivery requires Verifiable/Unverified Claims, exact diff and
boundary, dependency evidence, and no status/integration/completion claim. No commit/push.
