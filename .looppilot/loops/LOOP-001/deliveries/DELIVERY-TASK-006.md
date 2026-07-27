# Security Rework Delivery — TASK-006

Status: submitted for independent Task review and later specialist reverification

Worker: `/root/exp008_worker_a`

Dispatch HEAD: `cec04ed22350e334c40e32dd6117cd17e3049294`

Boundary: preserved uncommitted Loop worktree at TASK-006 dispatch to the TASK-006 changes
listed below, identified by final per-file raw SHA-256 hashes. Pre-existing TASK-001 through
TASK-005, TASK-007, Integrator, and governance changes are preserved and not claimed.

Finding addressed: `LOOP001-SEC-001` from `REVIEW-LOOP-001-SPECIALIST-R0`.

## Output

- `build_asset_approval_manifest` now requires a keyword-only trusted `workspace_root`.
- Every review item path is passed through existing `resolve_workspace_path` containment with
  `allow_absolute=True` before hashing. Absolute paths are accepted only when their resolved
  target stays within the trusted root.
- Existing containment rejects absolute outside paths, explicit `..` traversal, and paths
  whose symlink-resolved target escapes the trusted root before file bytes are opened.
- Studio passes its module-level trusted `REPO_ROOT` to manifest production.
- Allowed direct producer and ProductionSpec callers pass their honest pytest `tmp_path`.
- Artifact identity schema/helper, consumer paths/tests, and original evidence were not edited.

## Verifiable Claims

| Claim | Evidence | Verification | Git Boundary |
|---|---|---|---|
| Manifest production cannot hash an absolute path outside its trusted root. | Public producer test creates a readable sibling file outside the workspace and observes `WorkspacePathError`. | Producer final selection: `7 passed in 0.32s`. | `cec04ed22350e334c40e32dd6117cd17e3049294` + preserved Loop diff + TASK-006 hashes |
| Traversal and symlink-resolved escapes fail before hashing. | Public producer test rejects `../outside.glb` and a real in-workspace symlink targeting a readable outside file. | Focused path-escape selection passed; producer final selection passed. | Same boundary |
| Studio uses its trusted root and writes no manifest for an outside path. | Studio public flow test monkeypatches `REPO_ROOT`, supplies a readable sibling file, observes `WorkspacePathError`, and verifies the manifest path was not created. | Adjacent final selection: `5 passed, 26 deselected in 0.48s`. | Same boundary |
| Existing exact-byte, missing-file, unreadable-file, classification, serialization, and adjacent behavior remains GREEN. | Preserved producer and adjacent selections pass with honest roots and materialized bytes. | Producer 7 passed; adjacent 5 passed. | Same boundary |
| Edited tracked paths retain stable LF. | All five tracked TASK-006 paths report `i/lf w/lf`. | Exact EOL command below. | Same boundary |
| Static and patch checks pass. | Focused Ruff reports success and diff check exits 0. | `All checks passed!`; `git diff --check` exit 0. | Same boundary |

## RED and GREEN Evidence

### Attributed Specialist RED

`REVIEW-LOOP-001-SPECIALIST-R0` records an isolated probe in which the pre-Rework producer
hashed a readable absolute sibling file outside the logical workspace, exposing a local
digest/existence oracle. The review artifact does not preserve a literal command, so this
Delivery attributes the result without fabricating one.

### Producer Interface RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests\test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task006-red -k absolute_path_outside_workspace`

Observed: `1 failed, 5 deselected`; `TypeError` showed that manifest production had no
`workspace_root` interface.

After the minimal required-root and containment change, the same selection observed
`1 passed, 5 deselected`.

### Studio RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests\test_studio_app.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task006-studio-red -k rejects_outside_workspace`

Observed: `1 failed, 16 deselected`; Studio raised `TypeError` because it supplied no required
trusted root.

After passing `REPO_ROOT`, the same selection observed `1 passed, 16 deselected`.

### Final Producer GREEN

`.\.venv\Scripts\python.exe -m pytest tests\test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task006-final-producer`

Observed: `7 passed in 0.32s`.

### Final Adjacent GREEN

`.\.venv\Scripts\python.exe -m pytest tests\test_production_spec_runtime.py tests\test_studio_app.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task006-final-adjacent -k "approval_manifest or full_approval_round_trip"`

Observed: `5 passed, 26 deselected in 0.48s`.

### Focused Ruff and Diff

`.\.venv\Scripts\python.exe -m ruff check --no-cache fantasy_agent\workflows.py apps\studio\app\main.py tests\test_creative_review_agent.py tests\test_production_spec_runtime.py tests\test_studio_app.py`

Observed: `All checks passed!`.

`git diff --check` exited 0. Git emitted only line-ending conversion notices associated with
the repository `core.autocrlf` environment.

## EOL and Hash Evidence

EOL command:

`git ls-files --eol -- fantasy_agent/workflows.py apps/studio/app/main.py tests/test_creative_review_agent.py tests/test_production_spec_runtime.py tests/test_studio_app.py`

Observed: each exact path reports `i/lf w/lf attr/`.

Studio initially became `w/mixed` after its scoped edit. A mechanical strict-UTF-8 LF rewrite
changed no normalized logical content:

- before normalized SHA-256: `775e54ba72b2ab2e031fe4f62d7dd688e21dca091851e58f6805263cfef6b4dc`
- after raw LF SHA-256: `775e54ba72b2ab2e031fe4f62d7dd688e21dca091851e58f6805263cfef6b4dc`
- raw bytes: `28781 → 27989`

Final raw SHA-256 boundary:

| Path | SHA-256 |
|---|---|
| `fantasy_agent/workflows.py` | `90727edf36bd04cf39a2c5f36514a55b7b9cb00cb42e4aa2c9b1830e68f3ad76` |
| `apps/studio/app/main.py` | `775e54ba72b2ab2e031fe4f62d7dd688e21dca091851e58f6805263cfef6b4dc` |
| `tests/test_creative_review_agent.py` | `659cd380e46ec71de1b29878d7cfcd3cdd34178035cfbc0d9bec579072cfbcc8` |
| `tests/test_production_spec_runtime.py` | `380166bb1f0952e85a7f525d7731b748693cf52d501dd8378c88a6883563f14b` |
| `tests/test_studio_app.py` | `7f38645da5fb32516223ff0b6602fd0f1347ea2e6d938cae0ba92b0feb3b8e15` |

## Files Changed by TASK-006

- `fantasy_agent/workflows.py`
- `apps/studio/app/main.py`
- `tests/test_creative_review_agent.py`
- `tests/test_production_spec_runtime.py`
- `tests/test_studio_app.py`
- `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-006.md`

## Execution Infrastructure Incidents

- No new EII occurred. Pytest used the previously documented scoped `C:\tmp` basetemp
  workaround, and the installed apply-patch helper was used for authorized edits.
- Real file symlink creation succeeded in the focused producer test; no skip or mocked
  containment result was used.

## Risks

- The previously disclosed post-hash/pre-copy filesystem mutation interval remains outside
  this bounded producer correction. TASK-006 prevents out-of-root reads but does not claim to
  eliminate that residual TOCTOU interval.
- `allow_absolute=True` preserves existing absolute in-workspace test/caller compatibility;
  containment still evaluates the resolved target against the explicit trusted root.
- The required-root interface intentionally breaks the integration-owned caller until
  TASK-007 passes its honest `tmp_path`; no insecure default or path-derived root was added.

## Unverified Claims

- Per the Supervisor amendment, consumer/cross-owner GREEN depends on pre-created TASK-007 and
  is unverified by TASK-006. This is an ownership dependency, not a TASK-006 fallback.
- Repository-wide pytest and repository-wide Ruff were not run by this Worker; only the
  producer, adjacent, and focused static selections above are observed.
- Independent TASK-006 review, TASK-007 completion, re-integration, original specialist
  reverification, Finding closure, Loop acceptance, and Project closure remain unverified.
- Real Blender, ComfyUI, Godot, Unreal, remote MCP, packaging, release, and deployment were
  not executed and remain unverified.

## Scope and Authority Confirmation

- No artifact identity contract/helper, consumer file/test, authoritative governance file,
  original evidence, LoopPilot path, or unrelated path was edited by this Worker.
- Pre-existing Worker and Integrator changes were preserved and are not claimed as TASK-006
  edits. The only governance write is this required Delivery.
- No material data was deleted. No commit, push, merge, release, deployment, or external tool
  execution occurred.
- This is a Security Rework submission only. It does not claim Task approval, Finding closure,
  integration, Loop completion, or Project completion.
