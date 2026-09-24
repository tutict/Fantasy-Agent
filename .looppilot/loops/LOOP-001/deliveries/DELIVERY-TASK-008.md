# Public Blender Review Rework Delivery — TASK-008

Status: submitted for independent Task review and later Closure Reviewer reverification

Worker: `/root/exp008_worker_a`

Dispatch/product commit: `068f25b13a4f5c3fb1fb377d81b68a02e528b586`

Boundary: clean committed product files at `068f25b` plus preserved uncommitted governance and
evidence state, to the four tracked TASK-008 changes and this Delivery. Final raw hashes below
identify the exact verification surface. Pre-existing governance/evidence is not claimed.

Finding addressed: `EXP008-CLOSURE-SPEC-001`.

## Output

- Manifest production now selects the concrete reviewed artifact path before containment and
  hashing.
- Only a Blender review item whose planned suffix is `.fbx` maps to the corresponding `.glb`.
  The manifest records that `.glb` path and the SHA-256 identity of its exact bytes.
- Other source/suffix paths, including ComfyUI paths and already-concrete Blender `.glb`, are
  preserved unchanged.
- Existing trusted-root resolution runs after the concrete path is selected, so missing,
  absolute-outside, traversal, and symlink-resolved `.glb` candidates remain fail closed.
- Studio and ProductionSpec fixtures now materialize concrete files while returning the
  original public review unchanged. Studio implementation required no TASK-008 change.
- No extension-only or path-only authorization was added; byte identity remains mandatory for
  new decisions and authoritative at ingest.

## Verifiable Claims

| Claim | Evidence | Verification | Git Boundary |
|---|---|---|---|
| An unchanged public Blender `.fbx` review item binds to actual Godot `.glb` bytes. | Producer test leaves the item untouched, materializes only `.glb` bytes `b'abc'`, and observes the known SHA-256 plus a recorded `.glb` path. | Producer final selection: `10 passed in 0.37s`. | `068f25b13a4f5c3fb1fb377d81b68a02e528b586` to TASK-008 hashes |
| Non-Blender-FBX concrete paths stay unchanged. | Producer test passes a ComfyUI path and an already-concrete Blender `.glb`; manifest decision paths equal the supplied paths. | Producer final selection passed. | Same boundary |
| Mapped GLB candidates remain contained and fail closed. | Producer and Studio tests cover missing, readable absolute outside, `..` traversal, and a real symlink resolving outside. | Producer 10 passed; adjacent 8 passed. | Same boundary |
| Studio writes a manifest from an unchanged public review after concrete files exist. | Existing Studio YAML flow now materializes concrete files without rewriting review items; it approves a planned Blender `.fbx` and observes an identified `.glb` decision. | Adjacent final selection: `8 passed, 26 deselected in 0.59s`. | Same boundary |
| Studio writes no manifest for invalid mapped GLB cases. | Four parameterized Studio cases observe `FileNotFoundError` or `WorkspacePathError` and assert the manifest path does not exist. | Adjacent final selection passed. | Same boundary |
| All verification paths retain stable LF and focused static checks pass. | Five paths report `i/lf w/lf`; Ruff passes; diff check exits 0. | EOL, Ruff, and diff commands below. | Same boundary |

## RED and GREEN Evidence

### Real Producer RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests\test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task008-red -k uses_godot_glb_for_public_blender_item`

Observed: `1 failed, 7 deselected`. The untouched item named
`generated/assets/greybox_arena_kit.fbx`; only its `.glb` existed, and current producer code
raised `FileNotFoundError` while opening the planned `.fbx`.

### Minimal GREEN

After adding the Blender-FBX-only concrete path selection, the same test observed
`1 passed, 7 deselected`.

### Final Producer GREEN

`.\.venv\Scripts\python.exe -m pytest tests\test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task008-producer`

Observed: `10 passed in 0.37s`.

### Final Adjacent GREEN

`.\.venv\Scripts\python.exe -m pytest tests\test_production_spec_runtime.py tests\test_studio_app.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task008-adjacent -k "approval_manifest or full_approval_round_trip"`

Observed: `8 passed, 26 deselected in 0.59s`.

The selection includes unchanged public-review Studio success, four fail-no-manifest mapped
GLB cases, synchronized-bundle behavior, and the ProductionSpec full approval roundtrip.

### Focused Ruff and Diff

`.\.venv\Scripts\python.exe -m ruff check --no-cache fantasy_agent\workflows.py apps\studio\app\main.py tests\test_creative_review_agent.py tests\test_production_spec_runtime.py tests\test_studio_app.py`

Observed: `All checks passed!`.

`git diff --check` exited 0. Git emitted only repository `core.autocrlf` conversion notices.

## EOL and Hash Evidence

EOL command:

`git ls-files --eol -- fantasy_agent/workflows.py apps/studio/app/main.py tests/test_creative_review_agent.py tests/test_production_spec_runtime.py tests/test_studio_app.py`

Observed: all five paths report `i/lf w/lf attr/`.

Final raw SHA-256 boundary:

| Path | SHA-256 | TASK-008 state |
|---|---|---|
| `fantasy_agent/workflows.py` | `79f5107dee498829ea4ef0d02d9c0c929c62ba4485bca6bd8d89fa8ecbac75b0` | modified |
| `apps/studio/app/main.py` | `775e54ba72b2ab2e031fe4f62d7dd688e21dca091851e58f6805263cfef6b4dc` | unchanged, verified caller |
| `tests/test_creative_review_agent.py` | `e0484dfc52c5113a3051f721e0df1c47151a460826e24e75aa91632ee3222047` | modified |
| `tests/test_production_spec_runtime.py` | `48b2ae523940d73ed2771c114e34b3ba09cf1a8457f1fe59a1052613783d32cd` | modified |
| `tests/test_studio_app.py` | `7734ae1fe7b664f911eec4bc91ca7181c6919353eab0e4b45dfffb0b7641dfab` | modified |

`git diff --name-status 068f25b --` over the five allowed tracked paths reports only
`fantasy_agent/workflows.py`, `tests/test_creative_review_agent.py`,
`tests/test_production_spec_runtime.py`, and `tests/test_studio_app.py` as modified.

## Files Changed by TASK-008

- `fantasy_agent/workflows.py`
- `tests/test_creative_review_agent.py`
- `tests/test_production_spec_runtime.py`
- `tests/test_studio_app.py`
- `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-008.md`

## Execution Infrastructure Incidents

- No new EII occurred. Pytest used the established scoped `C:\tmp` basetemp workaround, and
  the installed apply-patch helper applied authorized edits.
- Real symlink creation succeeded in producer and Studio coverage; no skipped or mocked
  containment result was recorded.

## Risks and Residuals

- The `.fbx` to `.glb` rule is intentionally limited to `source == blender` and suffix
  `.fbx`; it does not infer identity for other sources or suffixes.
- Tests use deterministic placeholder bytes because approval identity hashes bytes and does
  not parse the asset format. Actual Godot import/format validation remains downstream.
- The previously disclosed post-hash/pre-copy filesystem mutation interval remains outside
  this producer correction.
- Unreal Creative Review ingest remains excluded; TASK-008 does not claim an Unreal artifact
  mapping or execution behavior.

## Unverified Claims

- TASK-009 must update and rerun the integration-owned cross-owner test without rewriting the
  public review item. Cross-owner GREEN and re-integration are unverified by TASK-008.
- Repository-wide pytest and repository-wide Ruff were not run by this Worker; only the
  producer, adjacent, and focused static selections above are observed.
- Independent TASK-008 review, TASK-009 completion, fixed-boundary integration, Closure
  Reviewer reverification, Finding closure, Loop closure, and Project completion remain
  unverified and outside Worker authority.
- Real Blender, ComfyUI, Godot, Unreal, remote MCP, packaging, release, and deployment were
  not executed and remain unverified.

## Scope and Authority Confirmation

- No integration test, consumer implementation/test, frontend path, authoritative governance,
  prior evidence, LoopPilot path, or unrelated file was edited by this Worker.
- Product commit `068f25b` was preserved; TASK-008 remains an uncommitted scoped diff. The only
  governance write is this required Delivery.
- No material data was deleted. No commit, push, merge, release, deployment, or external tool
  execution occurred.
- This is a TASK-008 submission only. It does not claim Task approval, Finding closure,
  integration, Loop closure, or Project completion.
