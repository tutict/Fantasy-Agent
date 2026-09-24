---
task_id: TASK-012
parent_goal: LOOP-001 / LOOP001-COMP-001
status: integrated
previous_status: approved
assigned_role: worker
assigned_to: /root/exp008_worker_a_task012
objective: Propagate the Studio plan target through the public approval-manifest request.
scope:
  allowed:
    - apps/frontend/src/shared/api.ts
    - apps/frontend/src/console/hooks.ts
    - tests/frontend_approval_manifest_api.test.mjs
    - .looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-012.md
  forbidden:
    - backend implementation/tests
    - other frontend files
    - authoritative governance/reviews/findings/prior evidence
    - original main and LoopPilot
authority: {read: true, modify: true, delete: false, commit: false, push: false, release: false, deploy: false}
reviewer: /root/exp008_loop_specialist_r2 plus independent Task Spec/Standards Reviewer
integration_owner: root
revision_count: 1
revision_budget: 2
created: 2026-07-27
updated: 2026-07-27
---

# Studio Target Propagation Rework - TASK-012

## Required Outcome

- `writeApprovalManifest` serializes an explicit `godot | unreal` target.
- The public hook derives target from the current plan with the existing
  `usesGodotEngine` helper and passes it to the API boundary.
- A dependency-free Node test intercepts `fetch` and proves both target values are
  present in the serialized request; it must demonstrate a real pre-fix RED.
- Existing API compatibility is preserved where practical; no backend default or
  producer/consumer identity rule is weakened.

## Verification and Delivery

Run the Node request-body test, `npm.cmd run frontend:typecheck`, and
`npm.cmd run frontend:build`, plus focused diff/EOL/hash checks. The build may create
only its normal ignored output; report it for exact Integrator cleanup. Delivery must
separate observed/unverified evidence, EII, residuals, and exact changed paths.

No backend/product-owner overlap, governance edit, commit, push, Closure claim,
real external tool, release, or deployment is authorized.

## Review Result

`REVIEW-TASK-012-R0`: Spec PASS, Standards PASS, no Finding. The Reviewer
independently observed Node/default-compatibility/hash/diff/EOL evidence. Task is
approved and integrated in INTEGRATION-003; LOOP001-COMP-001 remains open for
original Specialist reverification.
