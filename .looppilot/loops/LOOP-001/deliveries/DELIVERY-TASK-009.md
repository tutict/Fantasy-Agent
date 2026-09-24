# Public Flow Integration Rework Delivery - TASK-009

Status: submitted for independent Task review

Worker: `/root/exp008_worker_b`

Boundary: product HEAD `068f25b13a4f5c3fb1fb377d81b68a02e528b586`, the
approved but not Worker-integrated TASK-011 working-tree state, unrelated
pre-existing governance/evidence changes, and exactly the two TASK-009-owned paths
listed below. This Delivery claims only the integration-test change and evidence
directly observed by this Worker.

## Output

- The integration fixture now selects the unchanged public Blender review item
  returned by `run_director_workflow(... engine_version="Godot 4")`; it no
  longer rewrites `asset_id` or `asset_path`.
- The fixture materializes the corresponding in-workspace GLB and explicitly calls
  the approved producer with `target="godot"`.
- The manifest decision is asserted to preserve the public asset id while recording
  the concrete GLB path and SHA-256 of the reviewed GLB bytes.
- The fake Blender bridge exposes that same GLB path. Unchanged exported bytes pass
  the gate and copy; a same-path replacement before the gate/copy is rejected and
  no copy stage runs.

## Verifiable Claims

| Claim | Observed Evidence | Boundary |
|---|---|---|
| The public review item is not rewritten by the integration test. | The helper passes the `blender_item` selected directly from `plan.creative_review.items` into the focused review; no `model_copy(update=...)` is applied to the item. | `tests/test_approval_identity_integration.py` only |
| Explicit Godot production binds the concrete GLB identity. | The test materializes `Path(blender_item.asset_path).with_suffix(".glb")`, calls `build_asset_approval_manifest(..., target="godot")`, and asserts the decision path plus SHA-256 against the reviewed bytes. | Approved TASK-011 producer API consumed without implementation edits |
| Unchanged bytes are eligible for copy. | The first cross-owner test observes the same GLB in `approved_assets`, an empty skipped list, a `copy_assets` stage, and identical copied bytes. | Fake local bridges; no real external tool |
| Same-path replacement is rejected before copy. | The fake Blender export replaces the pre-reviewed bytes at the same GLB path; the second test observes no approved asset, the GLB in `skipped_assets`, no `copy_assets` stage, and no copied file. | Existing consumer behavior; no consumer edit |
| Both cross-owner tests pass with the corrected public fixture. | Corrected first run: `2 passed in 0.35s`. | `PYTHONDONTWRITEBYTECODE=1`, cache provider disabled, fresh `C:\tmp\fa-exp008-task009-green-b2` basetemp |
| Focused static and Git checks pass. | Ruff: `All checks passed!`; `git diff --check`: exit 0; EOL: `i/lf w/lf attr/`; test SHA-256: `c3a7bcae47e4f3e892fcb72178b45ec767358c7a2622312e197b9a31d0ee69e5`. | TASK-009 test path only |

## Characterization, RED, and GREEN Evidence

Before editing, the stale path-rewriting integration module passed
`2 passed in 0.34s` after the scoped basetemp ACL retry. This characterized the
existing consumer behavior but did not prove the public unmodified-plan invariant.

After removing the rewrite and adding the explicit approved producer target and
identity assertions, the correct test selection passed on its first run:
`2 passed in 0.35s`. Therefore, **no new RED was present**: approved TASK-011
already supplied the required producer behavior. No target was omitted and no
failure was manufactured. The same-path replacement case is a passing negative
behavior test, not a fabricated TDD RED.

Both pytest commands used `PYTHONDONTWRITEBYTECODE=1`,
`-p no:cacheprovider`, and a distinct fresh `C:\tmp` basetemp.

## Focused Verification

- `.\.venv\Scripts\python.exe -m pytest tests\test_approval_identity_integration.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task009-green-b2`
  observed `2 passed in 0.35s`.
- `.\.venv\Scripts\python.exe -m ruff check --no-cache tests\test_approval_identity_integration.py`
  observed `All checks passed!`.
- `git diff --check -- tests/test_approval_identity_integration.py` exited 0.
- `git ls-files --eol -- tests/test_approval_identity_integration.py` observed
  `i/lf w/lf attr/`.
- `git diff --name-status 068f25b -- tests/test_approval_identity_integration.py`
  reports exactly that tracked path as modified; numstat is `26/23`.

## Exact Task Boundary

Files changed by this Worker:

- `tests/test_approval_identity_integration.py`
- `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-009.md`

No implementation, other test, frontend, authoritative governance, Review,
Finding, Ledger, Checkpoint, Results, prior evidence, or LoopPilot repository path
was modified. No commit, push, merge, deletion, release, deployment, or real
external production tool operation occurred.

## Execution Infrastructure Incidents

- The first characterization run could not create its fresh `C:\tmp` basetemp
  and ended with two fixture `PermissionError` setup errors before product
  assertions. The unchanged command received scoped authorization and then passed.
- The built-in patch helper could not initialize its Windows sandbox for the
  assigned `C:\tmp` worktree. Several official helper argument-transport retries
  failed before the same scoped patch was applied through the official Codex
  apply-patch executable. Failed transports made no file changes.
- Git reported inability to read the user-global ignore file and emitted the
  repository `core.autocrlf` conversion notice. Diff, EOL, hash, and test evidence
  remained available.

These are Execution Infrastructure Incidents, not Product or Protocol Findings and
not unsuccessful unchanged Worker attempts.

## Risks and Residuals

- The fake Blender bridge uses deterministic placeholder bytes. Manifest identity
  and consumer copy behavior are observed; real GLB parsing or Blender/Godot import
  validity is not tested.
- The integration test covers replacement during the fake export before approval
  filtering and copy. It does not claim to eliminate every possible filesystem
  mutation interval after the gate has recomputed identity.
- Verification is focused on the two cross-owner tests and this file's Ruff/Git
  boundary; repository-wide regressions remain for parent integration validation.
- TASK-011 is independently approved, but integration remains the parent
  Integrator's authority.

## TASK-010 Dependency

TASK-010 governance reconciliation remains dependent on independently reviewing
this Delivery and on the parent Integrator's accepted integration evidence. This
Worker does not update governance, reconcile counts, close the parent Finding, or
claim TASK-009/TASK-010/Loop/Project completion.

## Unverified Claims

- Independent TASK-009 Spec and Standards review, approval, integration, TASK-010,
  original Closure Reviewer reverification, and parent Finding disposition remain
  unverified.
- Repository-wide pytest, repository-wide Ruff, CLI/frontend validation, packaging,
  and experiment scoring were not run by this Worker.
- Real Blender, Godot, Unreal, ComfyUI, remote MCP, release, and deployment were not
  executed and remain unverified.
- Finding closure, Task completion, Loop closure, Project acceptance, and Project
  completion are outside Worker authority and are not claimed.
