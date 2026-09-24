# LOOP-001 Fixed-Boundary Specialist Review R2

- Reviewer: `/root/exp008_loop_specialist_r2`
- Boundary: INTEGRATION-002 eleven-file hashes plus the public Studio caller
- Security: PASS.
- Compatibility: FAIL.
- Decision: `NEEDS-REWORK`; no Closure/Project approval.
- Reviewer remained read-only.

## Finding

`LOOP001-COMP-001`, Major: the Studio frontend `writeApprovalManifest` request
omits `target`, and its hook does not derive the plan engine. The backend defaults
to `unreal`, so a real UI Godot flow tries to hash the public `.fbx` instead of the
concrete `.glb`. Direct backend tests hide this because they inject `target=godot`.

## Independently Observed Evidence

- All eleven INTEGRATION-002 hashes matched; focused Ruff passed.
- Fixed-boundary pytest: `86 passed in 10.74s` after the scoped ACL retry.
- Security containment remains before hashing; missing/outside/traversal/symlink
  selected Godot GLB paths fail closed.

## EII and Required Rework

- First sandbox run: 30 passed and 56 fixture setup errors because its fresh
  `C:\tmp` basetemp was ACL-denied; identical authorized rerun passed 86.
- Propagate `godot | unreal` from the plan through the frontend API request and add
  request-body coverage. Return to this Specialist for Compatibility reverification.
