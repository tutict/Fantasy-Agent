"""The workbench tool names are a cross-boundary contract.

``apps/studio/app/main.py::_workbench_tool`` implements a fixed set of planning
tools; the React workbench calls them by name through ``/api/tools/{name}``.
Nothing connects the two lists, so a renamed backend tool (or a typo in a
button) would only show up as a runtime failure deep in a planning session.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = REPO_ROOT / "apps" / "studio" / "app" / "main.py"
PLAN_PANELS = REPO_ROOT / "apps" / "frontend" / "src" / "workbench" / "PlanPanels.tsx"
WORKBENCH = REPO_ROOT / "apps" / "frontend" / "src" / "workbench" / "PlanningWorkbench.tsx"

BACKEND_TOOL_PATTERN = re.compile(r'if name == "([a-z_]+)":')
FRONTEND_TOOL_PATTERN = re.compile(r'\{\s*tool:\s*"([a-z_]+)"')
EXTRACT_TOOL_PATTERN = re.compile(r'EXTRACT_TOOL\s*=\s*"([a-z_]+)"')

# Tools the frontend is allowed not to expose, with a reason.
KNOWN_WITHOUT_UI: dict[str, str] = {}


def _backend_tools() -> set[str]:
    if not MAIN_PY.exists():
        pytest.skip(f"Studio backend not present at {MAIN_PY}")
    return set(BACKEND_TOOL_PATTERN.findall(MAIN_PY.read_text(encoding="utf-8")))


def _frontend_tools() -> set[str]:
    if not PLAN_PANELS.exists():
        pytest.skip(f"Workbench frontend not present at {PLAN_PANELS}")
    tools = set(FRONTEND_TOOL_PATTERN.findall(PLAN_PANELS.read_text(encoding="utf-8")))
    extract = EXTRACT_TOOL_PATTERN.search(WORKBENCH.read_text(encoding="utf-8"))
    if extract:
        tools.add(extract.group(1))
    return tools


def test_backend_tool_names_are_discoverable():
    backend = _backend_tools()
    assert "extract_idea_seed" in backend
    assert "generate_game_production_plan" in backend
    # The retired static page only wired three of these; the rewrite wires all.
    assert len(backend) >= 11


def test_every_frontend_tool_exists_in_the_backend():
    """A typo'd tool name would otherwise 404 inside a planning session."""

    backend = _backend_tools()
    frontend = _frontend_tools()
    assert frontend, "no workbench tools found in the frontend sources"
    assert frontend - backend == set()


def test_backend_tools_are_reachable_from_the_ui():
    """New backend planning tools need a button, or a reason not to have one."""

    backend = _backend_tools()
    frontend = _frontend_tools()
    missing = backend - frontend - set(KNOWN_WITHOUT_UI)
    assert missing == set(), f"backend tools with no UI entry: {sorted(missing)}"


def test_known_without_ui_has_no_stale_entries():
    """An entry here must not describe a tool that is now wired up or gone."""

    backend = _backend_tools()
    frontend = _frontend_tools()
    stale = [name for name in KNOWN_WITHOUT_UI if name in frontend or name not in backend]
    assert stale == [], f"stale KNOWN_WITHOUT_UI entries: {sorted(stale)}"
