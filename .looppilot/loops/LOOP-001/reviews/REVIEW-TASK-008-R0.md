# TASK-008 Independent Review R0

- Reviewer: `/root/exp008_task008_reviewer`
- Boundary: product HEAD `068f25b13a4f5c3fb1fb377d81b68a02e528b586` plus the
  five TASK-008 Delivery hashes
- Spec: FAIL.
- Standards: FAIL.
- Decision: `NOT-APPROVED`.
- Reviewer remained read-only.

## Finding

- `TASK008-SPEC-001`, Major: `build_asset_approval_manifest` has no target/engine
  input, but TASK-008 globally maps every Blender `.fbx` review item to `.glb`.
  `PromptRequest` defaults to UE5, Creative Review declares `blocks_unreal_ingest`,
  and the Studio manifest API also has no target. The nominal Godot producer test
  uses the UE5 default, so the passing test demonstrates scope bleed rather than a
  target-specific contract.

## Independently Observed Evidence

- All five Delivery SHA-256 hashes matched current bytes.
- Exactly four allowed tracked paths differ from `068f25b`; `apps/studio/app/main.py`
  is unchanged.
- All five checked paths report `i/lf w/lf`.
- Producer selection: `10 passed in 0.31s` after the scoped temp workaround.
- The producer tests confirm hashing, deterministic serialization, non-FBX path
  preservation, and missing/outside/traversal/symlink fail-closed behavior.

## Execution Infrastructure Incidents

- The first sandboxed producer run had 2 passes and 8 fixture errors because the
  Reviewer could not create `C:\tmp\fa-exp008-task008-review`; a scoped permission
  rerun completed 10/10.
- The adjacent selection produced no output for more than 30 seconds and was
  terminated after Supervisor direction. It is unverified, not a Product Finding
  and not an unsuccessful Worker attempt.

## Required Rework and Unverified Evidence

- Add explicit target semantics so only Godot resolves planned Blender `.fbx` to
  `.glb`, while Unreal/default shared behavior preserves the concrete reviewed
  `.fbx` path; test both target paths.
- Adjacent tests, fresh Ruff/diff check, TASK-009 cross-owner integration, original
  Closure Reviewer reverification, and external tools remain unverified here.
- This Review does not close a Finding, Task, Loop, or Project.
