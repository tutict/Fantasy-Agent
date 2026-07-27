# Finding — EXP008-CLOSURE-SPEC-001

- Source: `REVIEW-EXP-008-CLOSURE-R0`
- Category / Severity / Status: Public identity contract / Major / open
- Reviewer: `/root/exp008_closure_reviewer`
- Rework: TASK-008 producer/public flow and TASK-009 cross-owner integration

## Evidence and Impact

The public review plan names Blender `.fbx`; Godot execution exports `.glb`; the current
integration test rewrites the review item to `.glb`. Thus the production path can hash the
wrong representation or fail before manifest creation, and the claimed public identity
invariant is not proven.

## Supervisor Disposition

Define the concrete Godot-reviewed artifact contract: the manifest must bind and record the
actual exported `.glb` bytes corresponding to an unchanged public plan/review item. Preserve
byte identity as authoritative; extension equivalence cannot substitute for it. Use two
owner-preserving Rework Tasks, re-integrate, and return to the original Closure Reviewer.
