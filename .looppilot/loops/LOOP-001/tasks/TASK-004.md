---
task_id: TASK-004
parent_goal: LOOP-001 / LOOP001-STD-001
status: integrated
previous_status: approved
assigned_role: worker
assigned_to: /root/exp008_worker_a
objective: Normalize producer-owned tracked files to stable LF without semantic changes.
scope:
  allowed:
    - fantasy_agent/contracts.py
    - fantasy_agent/workflows.py
    - tests/test_creative_review_agent.py
    - tests/test_production_spec_runtime.py
    - tests/test_studio_app.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-004.md
  forbidden:
    - all consumer files, authoritative governance, original evidence, LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: /root/exp008_loop_standards_reviewer
integration_owner: root
revision_count: 2
revision_budget: 2
created: 2026-07-26
updated: 2026-07-26
---

# Rework Task — TASK-004

Normalize exactly five producer-owned tracked files from mixed EOL to UTF-8 LF. This is a
mechanical rewrite exception to apply-patch-only editing; prove content is identical after
normalizing line endings. Do not format, reorder, edit semantics, touch untracked producer
files, consumer files, or governance except `DELIVERY-TASK-004.md`.

Acceptance: each path is `w/lf`; normalized logical-content hashes before/after match; producer,
adjacent tests, Ruff, and diff check pass. Record commands/hashes, Verifiable Claims,
Unverified Claims, exact paths, boundary, and no completion claim. No commit/push/delete.
