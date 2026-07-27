# Mechanical Rework Delivery — TASK-004

Status: submitted for original Standards Reviewer reverification

Worker: `/root/exp008_worker_a`

Dispatch HEAD: `cec04ed22350e334c40e32dd6117cd17e3049294`

Boundary: the preserved uncommitted Loop worktree at TASK-004 dispatch, identified for this
Rework by the five per-file logical hashes below, to the same logical hashes with UTF-8 LF
worktree bytes. Other pre-existing Worker, Integrator, and governance changes are not claimed.

Finding addressed: `LOOP001-STD-001` from `REVIEW-LOOP-001-STANDARDS-R0`.

## Mechanical Output

Exactly five tracked producer-owned files were decoded with strict UTF-8, had only CRLF/CR
line separators converted to LF, and were written with `UTF8Encoding(false)`. No formatting,
reordering, identifier, literal, or behavior edit was made. `fantasy_agent/artifact_identity.py`
was deliberately excluded because TASK-004 forbids touching that untracked file.

## Logical-Content Proof

SHA-256 was computed over each file after in-memory CRLF/CR-to-LF normalization both before
and after the rewrite.

| Path | Before normalized SHA-256 | After normalized SHA-256 | Raw bytes before → after | After EOL |
|---|---|---|---|---|
| `fantasy_agent/contracts.py` | `064180959b4cc491d4637985e4b05174ac6e834c14e17e28a5d86e4fe58b8b16` | `064180959b4cc491d4637985e4b05174ac6e834c14e17e28a5d86e4fe58b8b16` | `35387 → 34335` | `i/lf w/lf` |
| `fantasy_agent/workflows.py` | `1bcd76bc971e84ddc529cbdaef22bd59e4b778ce1013f775b8a714e20c6da647` | `1bcd76bc971e84ddc529cbdaef22bd59e4b778ce1013f775b8a714e20c6da647` | `57959 → 56651` | `i/lf w/lf` |
| `tests/test_creative_review_agent.py` | `27df5f3fd1a2f4183e100d430ea06c76ce45af95c149fcde109bd325ef13d58a` | `27df5f3fd1a2f4183e100d430ea06c76ce45af95c149fcde109bd325ef13d58a` | `6516 → 6423` | `i/lf w/lf` |
| `tests/test_production_spec_runtime.py` | `43c381e276a37eab96b739adb6728e77d4c3acf698f86979545fc28efba55345` | `43c381e276a37eab96b739adb6728e77d4c3acf698f86979545fc28efba55345` | `12632 → 12312` | `i/lf w/lf` |
| `tests/test_studio_app.py` | `496c47cbe45106c06c1d1e90d083e7d4e221a1b29ee78e17b7eb304138aa0499` | `496c47cbe45106c06c1d1e90d083e7d4e221a1b29ee78e17b7eb304138aa0499` | `17545 → 17151` | `i/lf w/lf` |

Hash command method:

`ReadAllBytes → strict UTF8Encoding(false, true).GetString → Replace CRLF/CR with LF → UTF8Encoding(false).GetBytes → SHA256.ComputeHash`

Rewrite command method:

`ReadAllBytes → strict UTF-8 decode → Replace CRLF/CR with LF → File.WriteAllText using UTF8Encoding(false)`

EOL verification command:

`git ls-files --eol -- fantasy_agent/contracts.py fantasy_agent/workflows.py tests/test_creative_review_agent.py tests/test_production_spec_runtime.py tests/test_studio_app.py`

Observed result: all five paths report `i/lf w/lf attr/`.

## Verifiable Claims

| Claim | Evidence | Verification | Git Boundary |
|---|---|---|---|
| Logical content is identical across normalization. | All five before and after normalized SHA-256 pairs match exactly. | Per-file strict UTF-8 normalized hash command and table above. | Dispatch worktree logical hashes to identical exit hashes |
| Only EOL encoding changed in the five tracked files. | Raw byte counts decreased to the normalized logical byte counts while logical hashes stayed equal. | Before/after byte counts and scoped file list above. | Same boundary |
| All five producer-owned tracked files now use LF. | Git reports `i/lf w/lf` for each exact path. | Exact `git ls-files --eol` command above. | Same boundary |
| Producer behavior remains GREEN. | Producer-focused pytest passed. | `5 passed in 0.30s`. | `cec04ed22350e334c40e32dd6117cd17e3049294` plus preserved Loop diff and mechanical rewrite |
| Adjacent behavior remains GREEN. | Exact approval selection passed. | `4 passed, 26 deselected in 0.40s`. | Same boundary |
| Static and patch checks remain GREEN. | Focused Ruff passed and diff check exited 0. | `All checks passed!`; `git diff --check` exit 0. | Same boundary |

## Validation Commands and Results

Producer:

`.\.venv\Scripts\python.exe -m pytest tests\test_creative_review_agent.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task004-producer`

Observed: `5 passed in 0.30s`.

Adjacent:

`.\.venv\Scripts\python.exe -m pytest tests\test_production_spec_runtime.py tests\test_studio_app.py -q -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-task004-adjacent -k "approval_manifest or full_approval_round_trip"`

Observed: `4 passed, 26 deselected in 0.40s`.

Ruff:

`.\.venv\Scripts\python.exe -m ruff check --no-cache fantasy_agent\artifact_identity.py fantasy_agent\contracts.py fantasy_agent\workflows.py tests\test_creative_review_agent.py tests\test_production_spec_runtime.py tests\test_studio_app.py`

Observed: `All checks passed!`.

`git diff --check` exited 0. Git emitted line-ending notices for other current worktree paths;
those notices are not logical-content failures and are outside this five-file Rework proof.

## Files Mechanically Rewritten

- `fantasy_agent/contracts.py`
- `fantasy_agent/workflows.py`
- `tests/test_creative_review_agent.py`
- `tests/test_production_spec_runtime.py`
- `tests/test_studio_app.py`

Created evidence path: `.looppilot/loops/LOOP-001/deliveries/DELIVERY-TASK-004.md`.

## Risks

- Repository `core.autocrlf` behavior can emit future conversion notices if another tool
  rewrites these files. The directly observed exit state is `w/lf` for all five paths.
- Consumer-owned tracked files are outside TASK-004 and require their separate TASK-005
  normalization before the complete eight-file integration boundary is stable.

## Unverified Claims

- TASK-005 consumer EOL normalization and the eventual all-file raw integration hashes are
  unverified by this Delivery.
- Repository-wide pytest and repository-wide Ruff were not rerun by this Worker; only the
  focused commands above are observed.
- Standards Reviewer reverification, Finding closure, fixed-boundary reintegration, Loop
  acceptance, and Project closure remain unverified and outside Worker authority.
- Real Blender, ComfyUI, Godot, Unreal, remote MCP, packaging, release, and deployment were
  not executed and remain unverified.

## Scope and Authority Confirmation

- No logical or semantic change was made. No untracked producer file, consumer path,
  authoritative governance file, original evidence, LoopPilot path, or unrelated path was
  modified by this Worker during TASK-004.
- The only governance write is this required Delivery.
- No material data was deleted. No commit, push, merge, release, deployment, or external tool
  execution occurred.
- This is a mechanical Rework submission only. It does not claim Finding closure, review
  approval, integration, Loop completion, or Project completion.
