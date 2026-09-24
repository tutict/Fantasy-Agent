# Finding - TASK008-SPEC-001

- Source: `REVIEW-TASK-008-R0`
- Category / Severity / Status: target semantics and compatibility / Major / closed
- Reviewer: `/root/exp008_task008_reviewer`
- Affected Task: TASK-008
- Rework: TASK-011

## Evidence and Impact

The producer API has no target/engine input but globally rewrites every Blender
`.fbx` review item to `.glb`. The default plan and approval-gate contract remain
Unreal-oriented, so an Unreal approval can hash or require the wrong artifact.
Passing Godot-named tests do not prove isolation because the producer test uses the
default UE5 request.

## Supervisor Disposition

Preserve the shared/Unreal concrete `.fbx` contract and require an explicit Godot
target before selecting `.glb`. Add both Godot and Unreal/default assertions, retain
containment and exact-byte identity, then return to the original TASK-008 Reviewer.
This is normal Review Rework and consumes no Worker Failure Budget.

## Verification and Closure

The original TASK-008 Reviewer independently observed producer 12 and adjacent 8
passing, Ruff/diff/EOL/hash evidence, explicit Godot GLB mapping, and default/Unreal
FBX preservation. `REVIEW-TASK-011-R0` is Spec PASS / Standards PASS with no
Finding. Supervisor approved corrected disposition; Integrator recorded
`VERIFIED-CORRECTED` on 2026-07-27. This does not close the parent Closure Finding.
