# EXP-008 Baseline and Verification Surface

Status: observed baseline

Date: 2026-07-26

## Repository Baseline

- Base and `origin/main`: `4355dd6d70a58477673f2a6e29c923219d3e8801`.
- Branch/worktree: `experiment/looppilot-fantasy-agent-exp-008` at
  `C:\tmp\Fantasy-Agent-exp-008`; it started clean.
- EXP-007 closure HEAD: `796b69e06b382d1e2ae03c58cb6a3e35fa9605fd`.
- Frozen LoopPilot HEAD: `2275e747e73936ebb8f0b24e5fb901a619b6adf8`.
- The original `main` worktree remained at the base SHA. Its ten pre-existing modified
  paths were observed before and after isolation and were not touched:
  `apps/frontend/src/console/hooks.ts`, `apps/studio/app/main.py`,
  `fantasy_agent/executor.py`, `fantasy_agent/godot_mcp.py`,
  `fantasy_agent/production_spec_runtime.py`, `fantasy_agent/unreal_spec_adapter.py`,
  `tests/test_executor.py`, `tests/test_production_spec_runtime.py`,
  `tests/test_studio_app.py`, and `tests/test_unreal_spec_adapter.py`.

## Repository Baseline Run

The first repository-wide run collected 159 tests, displayed three
`tests/test_executor.py` failures, reached 100 percent progress, then exceeded 300 seconds
during temp finalization without a summary. The first Ruff run could not access
`.ruff_cache`. These incomplete results are EII, not product-regression claims. An earlier
GraalPy venv bootstrap also timed out and was stopped before delegation; it is EII and not
a Worker attempt.

## Environment-Corrected Baseline

- Git `2.51.0.windows.1`; bundled CPython `3.12.13`.
- Dependency versions were aligned to the repository's existing environment without
  changing constraints or lock files; Ruff was aligned from newly resolved `0.16.0` to
  existing `0.15.14`.
- `python -m pytest -ra -p no:cacheprovider --basetemp=C:\tmp\fa-exp008-baseline-aligned`:
  159 collected, 159 passed, 0 failed/errors/skipped, no warning summary, 13.32 seconds.
- `python -m ruff check --no-cache fantasy_agent tests apps`: all checks passed.

The environment-corrected result is the authoritative product baseline. It does not erase
the disclosed cache/temp EII.

## Scope-Focused Baseline

- Approval-focused pytest: 52 collected, 7 selected and passed, 45 deselected, 0.59 s.
- Planning-only CLI summary: exit 0 and no generated product write.
- `npm run frontend:typecheck`: exit 0.
- `npm run frontend:build`: exit 0; Vite 8.1.3 built 23 modules in 109 ms.

## Verification Surface

| Surface | Observed coverage | Boundary |
| --- | --- | --- |
| pytest | `testpaths=[tests]`, `pythonpath=[.]`; 159 collected; no skip/xfail/importorskip marker found | Approval focus intentionally deselected 45 tests. |
| Ruff | `line-length=100`, `target-version=py311`; `fantasy_agent tests apps` | `--no-cache` avoids observed ACL failure. |
| CLI | Planning-only summary | Does not authorize execution or prove engine ingest. |
| frontend | Typecheck and Vite build | Ignored build output is removed before commit. |
| external tools | Deterministic Python/mocked paths only | No real Blender, ComfyUI GPU, Unreal, Godot, or remote MCP side effect. |
| generated tree | Before: `generated/.gitkeep` only | Full suite reproducibly created ignored `generated/godot/sessions/s2`, `s3`, `s4`. |
| temp behavior | Default pytest/cache paths unreliable | `C:\tmp` basetemp plus disabled cache produced the authoritative run. |

## Test Harness Finding

`EXP008-PATH-001` is independently observed on current main: the full suite leaves ignored
Godot session trees under `generated/`. It is a Minor Test Harness Finding because tracked
state and product assertions are unaffected, but isolation is weakened. It is outside the
approval-identity scope, is cleaned before commits, and remains a separate follow-up.

## Honesty Boundary

Passing pytest, Ruff, CLI, typecheck, and build results prove only those selections. They do
not validate real engines, Blender, ComfyUI, packaged playtests, GPUs, or remote services.
