# Delivery — TASK-001

Status: submitted for independent Spec and Standards review

Worker: `/root/exp008_worker_a`

Dispatch Git boundary: `cec04ed22350e334c40e32dd6117cd17e3049294`

## Output

- Added the canonical `ArtifactIdentity` contract with explicit `sha256` algorithm and a
  lowercase 64-hex digest constraint.
- Added `compute_artifact_identity(path)`, which streams exact file bytes into SHA-256 and
  propagates missing or unreadable input errors.
- Added `AssetApprovalDecision.artifact_identity`. The field remains optional only so legacy
  path-only manifests can be represented and explicitly rejected at the TASK-002 ingest seam;
  `build_asset_approval_manifest` always populates it for every newly built decision.
- Bound manifest production to the current bytes at each `CreativeReviewItem.asset_path`.

## Verifiable Claims

| Claim | Evidence | Verification | Git Boundary |
|---|---|---|---|
| A produced decision records explicit SHA-256 for exact reviewed bytes. | The known `b'abc'` vector produced lowercase digest `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`. | Focused pytest below; `test_build_asset_approval_manifest_binds_reviewed_file_bytes`. | `cec04ed22350e334c40e32dd6117cd17e3049294` to uncommitted TASK-001 diff |
| Every decision built by the producer carries non-null identity. | The classification test materializes all reviewed artifacts and asserts identity for every manifest decision, including revision, rejected, and pending decisions. | Final focused pytest: 5 passed. | Same boundary |
| Missing input and an unreadable directory path fail before a manifest is returned. | The failure test observed `FileNotFoundError` for a missing path and `OSError` for a directory opened as artifact bytes. | Final focused pytest: 5 passed. | Same boundary |
| Serialization is deterministic for unchanged reviewed bytes. | Two independently rebuilt manifests have identical `model_dump_json()` output. | Final focused pytest: 5 passed. | Same boundary |
| The implementation stays within producer ownership. | Product/test changes are limited to `fantasy_agent/artifact_identity.py`, `fantasy_agent/contracts.py`, `fantasy_agent/workflows.py`, and `tests/test_creative_review_agent.py`; this Delivery is the fifth allowed path. | `git status --short`, `git diff --check`, and allowed-path diff inspection. | Same boundary |

## TDD Evidence

### RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests/test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task001-red -k binds_reviewed_file_bytes`

Observed result: `1 failed, 3 deselected`. The public producer characterization failed with
`AttributeError: AssetApprovalDecision has no attribute artifact_identity`.

Before that real RED, a sandboxed invocation could not create the `C:\tmp` basetemp and
errored during test setup. The same selection was rerun with scoped permission; only the
second result above is product RED evidence.

### GREEN

Tracer-bullet command after the minimal implementation:

`.\.venv\Scripts\python.exe -m pytest tests/test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task001-green -k binds_reviewed_file_bytes`

Observed result: `1 passed, 3 deselected`.

Final focused command:

`.\.venv\Scripts\python.exe -m pytest tests/test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task001-final2`

Observed result: `5 passed in 0.32s`.

Static validation:

`.\.venv\Scripts\python.exe -m ruff check --no-cache fantasy_agent\artifact_identity.py fantasy_agent\contracts.py fantasy_agent\workflows.py tests\test_creative_review_agent.py`

Observed result: `All checks passed!`.

`git diff --check` exited 0. Git emitted only existing line-ending notices for modified
working-tree files.

## Files Changed

- `fantasy_agent/artifact_identity.py`
- `fantasy_agent/contracts.py`
- `fantasy_agent/workflows.py`
- `tests/test_creative_review_agent.py`
- `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-001.md`

## Risks

- Legacy path-only identity is representable as `None` for compatibility with non-ingest
  consumers. TASK-002 must reject it explicitly and must not restore path-only approval.
- Manifest production now fails for planned or stale paths whose bytes are unavailable. This
  is intentional fail-closed behavior, but repository-wide caller compatibility remains to be
  validated at integration.
- A file replacement after producer hashing is outside this bounded producer task. Ingest-time
  re-hashing and mismatch rejection belong to TASK-002.
- The first direct apply-patch and sandboxed pytest attempts hit Windows sandbox-helper or ACL
  errors. Scoped use of the installed apply-patch helper and `C:\tmp` basetemp resolved these
  execution-infrastructure incidents without changing product scope.

## Unverified Claims

- TASK-002 consumer enforcement, legacy-manifest rejection at ingest, digest mismatch
  rejection, and the full cross-owner invariant are unverified by this Delivery.
- Repository-wide pytest and repository-wide Ruff were not run by this Worker; only the
  focused commands above are observed.
- Real Blender, ComfyUI, Godot, Unreal, remote MCP, packaging, and deployment behavior are
  unverified and were not executed.
- Check-after-hash filesystem replacement behavior is unverified outside the bounded local
  producer model.

## Scope and Authority Confirmation

- No forbidden consumer file, authoritative Ledger, Loop Map, Project, Checkpoint, Loop
  Contract, LoopPilot file, or unrelated path was edited by this Worker.
- Pre-existing Supervisor/Integrator governance modifications were preserved and not claimed.
- No material data was deleted. No commit, push, merge, release, deployment, or external tool
  execution occurred.
- This is a TASK-001 submission only. It does not claim parent Project or Loop completion,
  approval, integration, or closure.
