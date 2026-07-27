---
task_id: TASK-006
parent_goal: LOOP-001 / LOOP001-SEC-001
status: integrated
previous_status: approved
assigned_role: worker
assigned_to: /root/exp008_worker_a
objective: Contain approval-manifest producer reads to an explicit workspace root.
scope:
  allowed:
    - fantasy_agent/workflows.py
    - apps/studio/app/main.py
    - tests/test_creative_review_agent.py
    - tests/test_production_spec_runtime.py
    - tests/test_studio_app.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-006.md
  forbidden:
    - artifact identity contract/helper, all consumer files/tests, authoritative governance, original evidence, LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: independent TASK-006 Reviewer, then original specialist
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-26
updated: 2026-07-26
---

# Security Rework Task — TASK-006

## Objective and Before State

Correct `LOOP001-SEC-001`. Before: manifest production directly opens request-provided paths,
and Studio supplies no trusted root.

## Owned Domain and Boundary

Only the six allowed paths. This is a bounded producer trust-boundary correction, not Loop
scope expansion. TASK-006 may update direct callers/tests but must not touch identity schema,
consumer enforcement, existing evidence, or authoritative state.

## Required Outcome

- Manifest production accepts/uses an explicit trusted workspace root and resolves every
  reviewed path through existing containment logic before hashing.
- Reject absolute outside paths, `..` traversal, and symlink-resolved escape before reading.
- Studio passes its `REPO_ROOT`; producer-owned callers/tests use honest roots. The
  consumer-owned cross-owner caller is delegated to dependent TASK-007.
- Preserve fail-closed missing-file behavior, identity semantics, serialization, and previous
  producer/adjacent/consumer integration behavior.

## TDD and Acceptance

Use the specialist's outside-file probe as attributed RED; add deterministic public producer
and Studio/API negative tests for outside/traversal/symlink escape, observe RED before GREEN,
then run producer, adjacent, focused Ruff, EOL, hash, and diff checks. Consumer/cross-owner
GREEN is TASK-007 plus re-integration acceptance, not TASK-006 write authority.
No real external tool. Delivery must disclose TASK-007 as unverified dependency and include
Verifiable Claims, Unverified Claims, RED/GREEN,
files, exact boundary, EII, risks, and no Finding/integration/completion claim.

## Authority

No commit, push, merge, material delete, external communication, release, deploy, or changes
outside the contract. Independent Task review precedes re-integration; original specialist
reverifies Security and Compatibility afterward.
