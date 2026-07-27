---
task_id: TASK-011
parent_goal: LOOP-001 / TASK008-SPEC-001
status: integrated
previous_status: approved
assigned_role: worker
assigned_to: /root/exp008_worker_a
objective: Make Blender artifact resolution explicitly target-aware without Unreal scope bleed.
scope:
  allowed:
    - fantasy_agent/workflows.py
    - apps/studio/app/main.py
    - tests/test_creative_review_agent.py
    - tests/test_production_spec_runtime.py
    - tests/test_studio_app.py
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-011.md
  forbidden:
    - consumer implementation/tests, integration tests, frontend, authoritative governance, prior evidence, LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: /root/exp008_task008_reviewer
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-27
updated: 2026-07-27
---

# Target-Aware Public Review Identity Rework - TASK-011

Independent R0: Spec PASS / Standards PASS / APPROVED. INTEGRATION-003 retains this Task.

## Objective and Before State

TASK-008 correctly hashes mapped GLB bytes but applies the mapping to every Blender
`.fbx` item. The shared producer and Studio API have no target input even though the
default public plan and approval-gate contract are Unreal-oriented.

## Required Outcome

- Add explicit, deterministic target semantics at the producer and Studio request
  boundary. Godot maps an unchanged public Blender `.fbx` item to its in-workspace
  `.glb`; default/Unreal behavior preserves and hashes the concrete `.fbx`.
- Preserve supplied ComfyUI paths and already-concrete Blender paths.
- Missing/outside/traversal/symlink paths fail closed after target selection and
  before hashing or manifest writing.
- Preserve backward-compatible default/Unreal calls, deterministic serialization,
  byte identity, and the excluded Unreal implementation scope.
- Do not edit consumer or integration-owned files; TASK-009 consumes the approved API.

## Inputs, Outputs, Dependencies, and Git Boundary

- Inputs: TASK-008 Contract/Delivery, REVIEW-TASK-008-R0, TASK008-SPEC-001, current
  product HEAD `068f25b` plus the preserved TASK-008 diff.
- Output: corrected producer/Studio surface, focused tests, and
  `DELIVERY-TASK-011.md` with Verifiable and Unverified Claims.
- Dependency: none; TASK-009 remains dependency-waiting until this Delivery is approved.
- Git boundary: no commit, push, merge, release, deploy, or real external tool.

## TDD and Acceptance

Record a real RED showing an Unreal/default `.fbx` review fails or maps to `.glb`
under TASK-008. Implement the smallest target-aware GREEN. Independently prove:

- explicit Godot + unchanged public review + real `.glb` bytes records `.glb` identity;
- default/Unreal + unchanged public review + real `.fbx` bytes records `.fbx` identity;
- Studio forwards the explicit target and writes no manifest for invalid selected paths;
- producer and adjacent selections, focused Ruff, EOL/hash/diff evidence pass.

The Worker must preserve scope, report all EII/residuals, and make no status or
closure claim. Two unsuccessful unchanged attempts trigger the pre-registered
WORKER-B fallback; ordinary RED/Rework does not consume that budget.
