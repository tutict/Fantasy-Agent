---
task_id: TASK-009
parent_goal: LOOP-001 / EXP008-CLOSURE-SPEC-001
status: integrated
previous_status: approved
assigned_role: worker
assigned_to: /root/exp008_worker_b
objective: Prove the public unmodified-plan FBX-to-GLB identity invariant end to end.
scope:
  allowed:
    - tests/test_approval_identity_integration.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-009.md
  forbidden:
    - all implementation, other tests, frontend, governance, prior evidence, LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: independent TASK-009 Reviewer
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-26
updated: 2026-07-27
---

# Public Flow Integration Rework — TASK-009

After TASK-011 approval, remove the integration test's review-item path rewrite. Use an
unchanged public plan/review item, materialize its corresponding GLB, assert the manifest
records/hashes that GLB, accept unchanged exported bytes, and reject same-path replacement.
Expectations may be extended but not weakened. Run both cross-owner tests and focused Ruff,
EOL/hash/diff checks. No implementation/governance edit, commit, push, or closure claim.

## Review Result

`REVIEW-TASK-009-R0` independently observed the two cross-owner tests, focused
Ruff/diff/hash/EOL evidence, and the unchanged public review-item invariant.
Spec PASS, Standards PASS, no Finding; TASK-009 is retained in INTEGRATION-003.
