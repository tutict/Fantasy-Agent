---
task_id: TASK-008
parent_goal: LOOP-001 / EXP008-CLOSURE-SPEC-001
status: integrated-after-rework
previous_status: approved-after-rework
assigned_role: worker
assigned_to: /root/exp008_worker_a
objective: Bind the unchanged public Blender review item to the actual Godot GLB bytes.
scope:
  allowed:
    - fantasy_agent/workflows.py
    - apps/studio/app/main.py
    - tests/test_creative_review_agent.py
    - tests/test_production_spec_runtime.py
    - tests/test_studio_app.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-008.md
  forbidden:
    - consumer implementation/tests, frontend, authoritative governance, prior evidence, LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: /root/exp008_task008_reviewer, then original Closure Reviewer
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-26
updated: 2026-07-27
---

# Public Blender Review Identity Rework — TASK-008

Review R0: Spec FAIL / Standards FAIL / NOT-APPROVED. `TASK008-SPEC-001`
requires target-aware correction through TASK-011; this normal Rework does not
consume Worker Failure Budget.

TASK-011 original Reviewer reverification: Spec PASS / Standards PASS. The
correction is approved and retained in INTEGRATION-003; the parent Closure Finding
remains open pending Closure reverification.

## Objective and Before State

Before: public plan/Studio review items name planned `.fbx`, Godot exports `.glb`, and manifest
production opens `.fbx`. Correct the concrete Godot contract without requiring the caller to
rewrite the review or treating extension equivalence as identity.

## Required Outcome

- For a Blender review item whose planned path ends in `.fbx`, manifest production resolves,
  hashes, and records the corresponding in-workspace `.glb` actually intended for Godot ingest.
- Other source/suffix paths remain the concrete supplied artifact path.
- Missing/outside/traversal/symlink GLB fails closed before a manifest is written.
- Studio accepts the unchanged public review after the GLB exists and writes no manifest if it
  does not. Identity comparison remains byte-based; no path-only authorization returns.
- Preserve deterministic serialization, existing security containment, and excluded Unreal scope.

## TDD and Acceptance

Observe RED with an unmodified plan/review item, only its real GLB materialized, and current
producer behavior. Add public producer/Studio tests, minimal GREEN, producer and adjacent
selections, Ruff, EOL/hash/diff evidence. Delivery must include Verifiable/Unverified Claims,
exact boundary, RED/GREEN, EII, residuals, and TASK-009 dependency. No status/closure claim.
