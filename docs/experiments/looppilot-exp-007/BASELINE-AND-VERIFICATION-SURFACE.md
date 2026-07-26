# Baseline 与 Verification Surface

以下结果均于 2026-07-26 在隔离 experiment worktree 中直接观测。

## Repository baseline

- LoopPilot：`main`，HEAD `2275e747e73936ebb8f0b24e5fb901a619b6adf8`，
  `git status --short` 为空；全程只读。
- Fantasy-Agent fetch 后 `origin/main`：
  `4355dd6d70a58477673f2a6e29c923219d3e8801`。
- Experiment branch：`experiment/looppilot-fantasy-agent-exp-007`。
- 原 Fantasy-Agent `main` worktree：10 个 tracked modified files，368 insertions / 185
  deletions；全部排除，未 clean、stash、stage 或 edit。
- 隔离路径：`C:\tmp\Fantasy-Agent-exp-007`。
- 复用既有 `.venv`，未 install/upgrade：
  `C:\Users\tutic\IdeaProjects\Fantasy-Agent\.venv`。
- Git 2.51.0.windows.1；Python 3.12.13；pytest 9.0.3；ruff 0.15.14；
  FastAPI 0.136.3；Pydantic 2.13.4；PyYAML 6.0.3。
- Node v24.12.0；npm 11.17.0。通过临时 junction 只读复用既有
  `node_modules`，未安装依赖；junction 与 `dist` 在验证后已删除。

## 三层 baseline

### Raw baseline

运行既有 venv 的 `python -m pytest -ra`，没有产品代码修改：

- collected 159；passed 91；failed 0；setup errors 68；
  skipped/xfailed/warnings reported 0/0/0；duration 17.18s。
- 68 个 error 的共同原因：pytest 创建 `tmp_path` 时无法扫描
  `C:\Users\tutic\AppData\Local\Temp\pytest-of-tutic`，均为
  `PermissionError`。
- 归类：observed Execution Infrastructure Incident，不是 Product Finding。
- `python -m ruff check fantasy_agent tests apps`：`All checks passed!`。
- 更早一次 sandbox-only ruff 无法初始化 `.ruff_cache`；宿主范围重跑成功，前者同样
  归类 EII。

### Environment-corrected baseline

唯一改动是 pytest 参数 `--basetemp=C:\tmp\fa-exp007-pytest`；没有改变 test
selection、dependency 或 product file。

- collected/passed 159/159；failed/errors/skipped/xfailed/warnings reported 均为 0；
  duration 12.91s。
- ruff 全配置 scope 通过。
- `npm.cmd run frontend:typecheck` exit 0。
- `npm.cmd run frontend:build` exit 0，23 modules transformed。

### Scope-focused baseline

- 既有 approval tests：5 passed，33 deselected，0.47s。
- planning-only CLI exit 0；未使用 `--execute` 或 `--yes`。
- Candidate C characterization：审批 `reviewed_revision.fbx` 且
  `asset_id=start_marker` 时，现实现会放行不同 path 的 `start_marker.glb`。
- Selected Candidate E characterization：planning 接受
  `http://user:secret@localhost:8188`，返回 `isError=False`、status `planned`，并声称
  已准备 run manifest。

## Verification Surface

- Python version：CPython 3.12.13，使用仓库既有 venv。
- pytest configuration：`pyproject.toml` 的 `[tool.pytest.ini_options]`。
- pytest testpaths：`tests`；`pythonpath=["."]`。
- test selection filters：full run 无；focused run 仅用明确 file/`-k`。
- skipped tests：完整 baseline 未观测到。
- optional dependencies：LLM 路径使用 controlled fallback；未使用 live Anthropic
  dependency 或 credential。
- external applications：Blender、ComfyUI、Godot、Unreal tests 使用 fake
  runner/client 与 `tmp_path`，不构成真实应用执行证据。
- ruff scope：`fantasy_agent tests apps`。
- CLI validation：planning-only 可达；本实验禁止真实 `--execute`/`--yes`。
- generated artifacts：大多数 fake tests 使用 temporary artifacts，但 closure full pytest
  观测到 `tests/test_executor.py` 的 s2-s4 cases 在 worktree 留下 ignored
  `generated/godot/sessions/`。根因是 bridge 使用 `tmp_path`、spec export 仍使用默认
  `workspace_root`；产物已清理，登记为 Minor Test Harness Finding `EXP007-PATH-001`。frontend build 的 ignored
  `dist` 也已清理；两者都不是 external-engine evidence。
- focused validation：完整 `tests/test_comfyui_mcp.py`、reviewer rework tests、selected
  ruff scopes。
- full validation：完整 Python suite、ruff、frontend typecheck/build 与 planning CLI。
- closure reverification：禁用 pytest cache、ruff cache 与 Python bytecode；完整 suite
  162 passed（13.05s），`tests/test_comfyui_mcp.py` 11 passed（0.20s），ruff、
  planning-only CLI、frontend typecheck/build 均通过。普通权限首次创建新的外部
  basetemp 仍被 ACL 拒绝，提升权限重跑通过，归入既有 EII。清理 worktree 后单独
  重跑 planning-only CLI 未创建 `generated/godot`，因此该残留来自 full pytest，
  不是 CLI side effect。
- CI validation：未观测到 `.github` workflow；不声称 remote CI passed。
- unreachable：真实 Blender、ComfyUI HTTP generation、Unreal import/PIE/DataValidation、
  Godot editor/import、GPU generation 与 remote MCP。

`pytest passed` 不等于全部 Fantasy-Agent execution paths 已验证；fake/mock external
tool tests passed 也不等于 Unreal、Blender、Godot 或 ComfyUI 已真实执行。
