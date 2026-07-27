# Target-Aware Public Review Identity Rework Delivery - TASK-011

Status: submitted for independent Task review

Worker: `/root/exp008_worker_a`

Dispatch/product commit: `068f25b13a4f5c3fb1fb377d81b68a02e528b586`

Boundary: product commit `068f25b`, the preserved TASK-008 diff and unrelated
pre-existing governance/evidence state, plus the five allowed tracked TASK-011
paths and this Delivery. The raw hashes below identify the exact final product
and test bytes. Pre-existing governance/evidence is not claimed.

Rework source: `TASK008-SPEC-001`.

## Output

- Manifest production now takes an explicit `target` keyword with a
  backward-compatible `unreal` default.
- Only a Godot target maps a public Blender `.fbx` review item to its
  corresponding in-workspace `.glb`. Default and explicit Unreal calls preserve,
  hash and record the concrete `.fbx`.
- ComfyUI paths and already-concrete Blender paths remain unchanged for Godot.
- Studio `ApprovalManifestRequest` exposes the same `unreal` default and forwards
  the selected target to the producer before any manifest write.
- Target selection still precedes trusted-root resolution and exact-byte hashing.
  Missing, outside, traversal and symlink-selected Godot paths fail closed.

## Verifiable Claims

| Claim | Observed Evidence | Verification | Git Boundary |
|---|---|---|---|
| Default and explicit Unreal preserve and hash the actual `.fbx` bytes. | The parameterized producer test materializes `.fbx` bytes `abc` and different adjacent `.glb` bytes; both decisions retain `.fbx` and the known SHA-256 of `abc`. | Focused GREEN: `2 passed, 10 deselected in 0.16s`; producer: `12 passed in 0.73s`. | `068f25b` plus preserved TASK-008 diff to hashes below |
| Explicit Godot maps only the planned Blender `.fbx` to concrete `.glb` identity. | The Godot producer test uses `engine_version='Godot 4'`, passes `target='godot'`, keeps the public item unchanged and records the known SHA-256 of real `.glb` bytes. | Producer selection passed. | Same boundary |
| Supplied ComfyUI and concrete Blender paths are preserved. | The focused producer test passes Godot with a ComfyUI item and an already-concrete Blender `.glb`; both decision paths equal the supplied paths. | Producer selection passed. | Same boundary |
| Studio exposes and forwards the explicit target. | The Studio request asserts `target == 'godot'`; with producer default now Unreal, the observed `.glb` decision proves the caller forwarded Godot. | Adjacent approval selection: `8 passed, 26 deselected in 0.62s`. | Same boundary |
| Invalid selected Godot paths fail before manifest writing. | Producer and Studio cover missing, readable absolute outside, `..` traversal and a real symlink resolving outside; Studio asserts the manifest does not exist. | Producer and adjacent selections passed. | Same boundary |
| Serialization, byte identity and adjacent behavior remain stable. | Existing deterministic manifest JSON and exact-byte identity tests pass; the complete three-module selection passes. | Final run: `46 passed in 7.70s`. | Same boundary |
| Focused static, whitespace and EOL checks pass. | Ruff reports `All checks passed!`; `git diff --check` exits 0; all five tracked paths report `i/lf w/lf attr/`. | Commands below. | Same boundary |

## RED and GREEN Evidence

### Real Target-Agnostic RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests\test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task011-red -k preserves_unreal_fbx_bytes`

Environment: `PYTHONDONTWRITEBYTECODE=1`.

Observed after the scoped ACL retry: `2 failed, 10 deselected in 0.26s`.

- Default call recorded `generated/assets/greybox_arena_kit.glb` instead of the
  expected public `.fbx`.
- Explicit `target='unreal'` raised `TypeError` because the TASK-008 producer
  had no target parameter.

### Minimal GREEN

The unchanged focused selection after the smallest producer and Studio target
surface change observed `2 passed, 10 deselected in 0.16s`.

### Final Producer and Adjacent GREEN

- Producer: `12 passed in 0.73s`.
- Approval-focused adjacent selection:
  `8 passed, 26 deselected in 0.62s`.
- Final complete producer plus adjacent modules: `46 passed in 7.70s`.

Every pytest run used `PYTHONDONTWRITEBYTECODE=1`,
`-p no:cacheprovider` and a dedicated `C:\tmp` basetemp.

### Focused Ruff and Diff

`.\.venv\Scripts\python.exe -m ruff check --no-cache fantasy_agent\workflows.py apps\studio\app\main.py tests\test_creative_review_agent.py tests\test_production_spec_runtime.py tests\test_studio_app.py`

Observed: `All checks passed!`.

`git diff --check -- fantasy_agent/workflows.py apps/studio/app/main.py tests/test_creative_review_agent.py tests/test_production_spec_runtime.py tests/test_studio_app.py`

Observed: exit 0. Git emitted only the repository `core.autocrlf` conversion
notices.

## EOL, Hash and Git Boundary Evidence

`git ls-files --eol` observed `i/lf w/lf attr/` for all five tracked paths.

| Path | Final SHA-256 | Cumulative state from `068f25b` |
|---|---|---|
| `fantasy_agent/workflows.py` | `7ec026007ddca43f5aa5a322d3e4f5a2dbba38eab6dea44d45d0cd04d0580b8b` | modified |
| `apps/studio/app/main.py` | `9d997de46b16d65912fd56898c1080a219461b7cdc4631a65c104970d9bc7c01` | modified |
| `tests/test_creative_review_agent.py` | `5b63d6003c7243f28f6a1459004fda519deb83d12e51ac926384b3bf28b7c0a6` | modified |
| `tests/test_production_spec_runtime.py` | `c5cb0d89f04d60109bbea863f47c8a21c92702365f106c78e6886c0e008c5fb8` | modified |
| `tests/test_studio_app.py` | `71eba0a1b5b67cde6287430b663456356b164d3b706063429e44e9b52fef0e9e` | modified |

`git diff --name-status 068f25b --` over the five allowed tracked paths reports
exactly those five paths as modified. The cumulative numstat is respectively
`15/2`, `2/0`, `179/0`, `7/7` and `70/24`; it includes preserved
TASK-008 changes and must not be read as TASK-011-only line ownership.

This new Delivery is the sixth allowed TASK-011 path. An embedded self-hash is
intentionally omitted because adding it would change the file being hashed.

## Files Changed by TASK-011

- `fantasy_agent/workflows.py`
- `apps/studio/app/main.py`
- `tests/test_creative_review_agent.py`
- `tests/test_production_spec_runtime.py`
- `tests/test_studio_app.py`
- `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-011.md`

No consumer implementation/test, integration test, frontend, authoritative
governance, prior evidence or LoopPilot path was edited by this Worker.

## Execution Infrastructure Incidents

- The built-in patch helper could not initialize its Windows sandbox for the
  assigned `C:\tmp` worktree, and the sandboxed wrapper was access denied.
  Several argument-transport retries failed before the same scoped patch was
  applied through the official patch executable with minimal authorization.
  Failed transport attempts made no file changes and did not alter strategy.
- The first RED run could not create its dedicated `C:\tmp` basetemp and ended
  with two fixture `PermissionError` errors before product assertions ran. The
  unchanged command received scoped authorization and then produced the recorded
  real RED.
- Git reported inability to read the user-global ignore file and emitted
  `core.autocrlf` notices. Repository diff, EOL and test evidence remained
  available.

These are Execution Infrastructure Incidents, not Product or Protocol Findings
and not unsuccessful Worker attempts.

## Risks and Residuals

- Target recognition follows the existing engine convention: values containing
  `godot` case-insensitively select Godot mapping; default, Unreal and all other
  values preserve the supplied concrete path.
- Identity tests use deterministic placeholder bytes because approval identity
  hashes bytes and does not parse Blender formats. Real format/import validation
  remains downstream.
- The previously disclosed post-hash/pre-copy filesystem mutation interval is
  unchanged and outside this producer correction.
- Unreal consumer implementation and ingest behavior remain excluded; this Task
  changes only the shared producer and Studio request boundary.

## TASK-009 Dependency

TASK-009 remains dependency-waiting on independent approval of this Delivery. Its
integration-owned cross-owner test must consume the explicit Godot producer API
without rewriting the public review item. No TASK-009 implementation, test or
integration claim is made here.

## Unverified Claims

- Independent TASK-011 Spec and Standards review, original Finding reverification,
  approval, integration and TASK-009 remain unverified.
- Repository-wide pytest and repository-wide Ruff were not run; verification is
  limited to the three allowed test modules and focused Ruff paths above.
- Real Blender, ComfyUI, Godot, Unreal, remote MCP, packaging, release and
  deployment were not executed and remain unverified.
- Finding closure, Task completion, Loop closure and Project completion remain
  outside Worker authority and are not claimed.

## Scope and Authority Confirmation

Product commit `068f25b` was preserved. No material data was deleted, and no
commit, push, merge, release or deployment occurred. No real external production
tool was executed. This is a bounded TASK-011 Delivery for independent review only.
