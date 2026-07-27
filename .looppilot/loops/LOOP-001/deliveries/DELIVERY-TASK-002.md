# Delivery — TASK-002

Status: submitted for independent Spec and Standards review

Worker: `/root/exp008_worker_b`

Dispatch Git boundary: `cec04ed22350e334c40e32dd6117cd17e3049294`, plus the preserved
approved uncommitted TASK-001 producer submission and TASK-003 fixture-only Rework boundary.

## Output

- The Godot approval filter now resolves each exported asset inside the supplied
  `workspace_root`, computes its current identity through TASK-001's shared
  `compute_artifact_identity` API, and approves only a matching approved Blender decision.
- The executor propagates its actual `workspace_root` into the approval filter before the
  copy stage.
- Existing FBX/GLB path and stem equivalence remains eligible only when current bytes match
  the manifest identity.
- Missing exported files, identity-less decisions, malformed manifest identities, and
  mismatched bytes all fail closed before `copy_assets`.

## Verifiable Claims

| Claim | Evidence | Verification | Git Boundary |
|---|---|---|---|
| A producer-built manifest accepts unchanged approved bytes. | The cross-owner test builds a manifest from actual `b"glTF-stub"` bytes, the fake Blender stage writes the same bytes, and the copied Godot artifact retains those bytes. | Final focused suite: `40 passed in 2.36s`; `test_producer_manifest_allows_unchanged_approved_bytes`. | Dispatch HEAD plus preserved producer/Rework boundary and uncommitted TASK-002 diff |
| Same-path byte replacement is rejected before copy. | The producer binds `b"reviewed-glb-bytes"`; the fake Blender stage replaces the exact path with `b"glTF-stub"`; approval becomes empty, the export is skipped, and no `copy_assets` stage or destination file exists. | Required RED was `1 failed in 0.37s`; tracer GREEN was `1 passed in 0.35s`; final cross-owner selection is GREEN. | Same boundary |
| Missing, malformed, and identity-less inputs fail closed. | Dedicated executor tests observe skipped identity-less and missing exports, a blocked malformed manifest, and no copy stage in every case. | Focused negative selection: `3 passed, 35 deselected in 0.46s`. | Same boundary |
| Path equivalence cannot replace identity. | Existing `.fbx` manifest-path to `.glb` export fixtures copy only after receiving the identity of the current GLB bytes; the mismatch integration test rejects despite path/stem equivalence. | Corrected valid-fixture selection: `3 passed, 32 deselected in 0.40s`; final focused suite GREEN. | Same boundary |
| The consumer duplicates no digest algorithm. | `approval_manifest.py` imports TASK-001's helper; no `hashlib` or `sha256` implementation appears in the two consumer modules. | `rg -n "hashlib|sha256" fantasy_agent\approval_manifest.py fantasy_agent\executor.py` exited 1 with no matches, as expected. | Same boundary |
| TASK-002 remains within assigned write scope. | Changes owned here are the two consumer modules, two consumer/cross-owner tests, and this Delivery. | Scoped diff inspection, `git status --short`, and `git diff --check` exit 0. | Same boundary |

## TDD Evidence

### RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests\test_approval_identity_integration.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task002-red -k same_path_byte_replacement`

Observed product result: `1 failed in 0.37s`. The approval gate returned
`["generated/assets/reviewed_prop.glb"]` as approved after that exact reviewed path had
been overwritten, failing the expected empty approved list. This demonstrated the original
path/stem-only consumer defect through the public producer and executor surfaces.

### GREEN

Tracer-bullet command after the minimal consumer implementation:

`.\.venv\Scripts\python.exe -m pytest tests\test_approval_identity_integration.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task002-green -k same_path_byte_replacement`

Observed result: `1 passed in 0.35s`.

Final focused consumer/cross-owner command:

`.\.venv\Scripts\python.exe -m pytest tests\test_executor.py tests\test_approval_identity_integration.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task002-focused-green`

Observed result: `40 passed in 2.36s`.

Focused static command:

`.\.venv\Scripts\python.exe -m ruff check --no-cache fantasy_agent\approval_manifest.py fantasy_agent\executor.py tests\test_executor.py tests\test_approval_identity_integration.py`

Observed result: `All checks passed!`.

`git diff --check` exited 0. Git emitted only existing CRLF conversion warnings.

## Execution-Infrastructure Incidents

- The first RED invocation failed during pytest setup with `PermissionError: [WinError 5]`
  while creating `C:\tmp\fa-exp008-task002-red`; no product code ran. The identical
  selection was rerun with the recorded scoped `C:\tmp` workaround and produced the real
  product RED above.
- The native `apply_patch` filesystem helper twice failed before edits with
  `windows sandbox failed: helper_unknown_error: setup refresh had errors`. The established
  scoped installed Codex apply-patch helper was then used. Intermediate stdin/argument
  formatting attempts also failed before modification; successful patches reported their
  exact updated files.
- `git status --short` emitted permission warnings while reading the user-level global
  ignore file, but still returned the repository status used for scope inspection.

## Files Changed by TASK-002

- `fantasy_agent/approval_manifest.py`
- `fantasy_agent/executor.py`
- `tests/test_executor.py`
- `tests/test_approval_identity_integration.py`
- `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-002.md`

## Risks

- Hashing and copying remain separate filesystem operations. A replacement in the narrow
  check-after-hash/before-copy interval is not prevented by this bounded change.
- Identity-less and missing artifacts are reported through the existing skipped-assets
  surface rather than a new identity-specific reason field. They remain fail closed.
- Legacy path-only manifests now intentionally ingest no assets; Compatibility review remains
  required by the Loop Contract.

## Unverified Claims

- Repository-wide pytest and repository-wide Ruff were not run by this Worker; only the
  focused commands above are observed.
- Real Blender, Godot, ComfyUI, Unreal, remote MCP, packaging, release, deployment, and
  external side effects were not executed and remain unverified.
- Concurrent filesystem replacement after successful hashing and before copy remains
  unverified outside this bounded local model.
- Independent TASK-002 review, formal integration, Loop closure, Project completion, commit,
  push, and synchronization remain outside this Delivery and are unverified.

## Scope and Authority Confirmation

- No producer-owned `artifact_identity.py`, `contracts.py`, `workflows.py`, or producer
  tests were edited by this Worker.
- No authoritative Ledger, Loop Map, Project, Checkpoint, Loop Contract, LoopPilot file, or
  unrelated path was edited by this Worker. Pre-existing Supervisor, Integrator, TASK-001,
  and TASK-003 changes were preserved and are not claimed.
- No material data was deleted. No commit, push, merge, release, deployment, external message,
  or material external-tool execution occurred.
- This is a TASK-002 Worker submission only. It does not claim Task approval, integration,
  parent Project completion, Loop completion, or closure.
