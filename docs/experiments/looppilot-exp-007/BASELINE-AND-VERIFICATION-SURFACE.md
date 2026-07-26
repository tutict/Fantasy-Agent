# Baseline and Verification Surface

All observations below were made on 2026-07-26 in the isolated experiment worktree.

## Repository baseline

- Frozen LoopPilot HEAD: `2275e747e73936ebb8f0b24e5fb901a619b6adf8`; branch
  `main`; `git status --short` empty.
- Fantasy-Agent fetch target: `origin/main` at
  `4355dd6d70a58477673f2a6e29c923219d3e8801`.
- Experiment branch: `experiment/looppilot-fantasy-agent-exp-007`.
- Original Fantasy-Agent `main` worktree: 10 modified tracked files, 368 insertions
  and 185 deletions. It is excluded and was not cleaned, stashed, staged, or edited.
- Isolation: Git worktree at `C:\tmp\Fantasy-Agent-exp-007`.
- Existing virtual environment reused without install or upgrade:
  `C:\Users\tutic\IdeaProjects\Fantasy-Agent\.venv`.
- Git 2.51.0.windows.1; Python 3.12.13; pytest 9.0.3; ruff 0.15.14;
  FastAPI 0.136.3; Pydantic 2.13.4; PyYAML 6.0.3.
- Node v24.12.0; npm 11.17.0. Existing `node_modules` was reused through an ignored
  worktree junction; no package install occurred.

## Three-layer baseline

### Raw baseline

Command: existing venv Python, `-m pytest -ra`, with no product-code change.

- Collected: 159.
- Passed: 91.
- Failed: 0.
- Setup errors: 68.
- Skipped/xfailed/warnings reported: 0/0/0.
- Duration: 17.18s.
- Common cause for all 68 errors: `PermissionError` scanning
  `C:\Users\tutic\AppData\Local\Temp\pytest-of-tutic` while creating `tmp_path`.
- Attribution: observed Execution Infrastructure Incident (test-temp ACL), not a
  Product Finding.
- Ruff: `python -m ruff check fantasy_agent tests apps` reported `All checks passed!`.
- An earlier sandbox-only ruff attempt could not initialize `.ruff_cache`; the
  host-scoped rerun above is the authoritative result and the cache error is EII.

### Environment-corrected baseline

Only pytest's temp directory changed:
`--basetemp=C:\tmp\fa-exp007-pytest`. No test selection, dependency, or product file
changed.

- Collected/passed: 159/159.
- Failed/errors/skipped/xfailed/warnings reported: 0/0/0/0/0.
- Duration: 12.91s.
- Ruff: all configured Python scopes passed.
- Frontend typecheck: `npm.cmd run frontend:typecheck`, exit 0.
- Frontend build: `npm.cmd run frontend:build`, exit 0; 23 modules transformed.

### Scope-focused baseline

- Existing approval tests:
  `pytest -q tests/test_executor.py tests/test_creative_review_agent.py -k
  'approval_manifest or approval_gate'`: 5 passed, 33 deselected, 0.47s.
- Planning-only CLI:
  `python -m fantasy_agent --prompt 'EXP-007 planning-only courier loop' --minutes
  10 --engine 'Godot 4' --format summary`: exit 0; returned a plan and did not use
  `--execute` or `--yes`.
- Candidate C characterization: an approved decision for
  `generated/assets/reviewed_revision.fbx` with `asset_id=start_marker` approved the
  different export `generated/assets/start_marker.glb`.
- Selected Candidate E characterization: planning accepted
  `http://user:secret@localhost:8188`; result had `isError=False`, status `planned`,
  and claimed a run manifest had been prepared.

## Verification Surface

- Python version: CPython 3.12.13 through the repository's existing venv.
- pytest configuration: `[tool.pytest.ini_options]` in `pyproject.toml`.
- pytest testpaths: `tests` with `pythonpath=["."]`.
- test selection filters: none for full runs; explicit file/`-k` selection for
  focused runs only.
- skipped tests: none observed in the full baseline.
- tests requiring optional dependencies: LLM paths are tested with controlled
  fallbacks; no live Anthropic dependency or credential was used.
- tests requiring external applications: existing Blender, ComfyUI, Godot, and
  Unreal execution tests use fake runners/clients and `tmp_path`. They do not prove
  a real application run.
- ruff scope: `fantasy_agent tests apps`.
- CLI validation: planning-only CLI is reachable; `--execute`/`--yes` is prohibited
  except through fake/test adapters in this experiment.
- generated artifact validation: tests inspect temporary artifacts; the frontend
  build emits ignored `apps/frontend/dist` and is not external-engine evidence.
- focused validation: selected ComfyUI MCP tests plus the no-secret assertions.
- full validation: 159-test Python suite, ruff, frontend typecheck, and frontend
  build are reachable.
- CI validation: no `.github` workflow was observed; no remote CI run is claimed.
- unreachable verification under current environment: real Blender execution,
  ComfyUI HTTP generation, Unreal import/PIE/DataValidation, Godot editor/import,
  GPU generation, and remote MCP.

`pytest passed` does not mean all Fantasy-Agent execution paths were validated.
Passing fake/mock external-tool tests does not mean Unreal, Blender, Godot, or
ComfyUI executed successfully in reality.
