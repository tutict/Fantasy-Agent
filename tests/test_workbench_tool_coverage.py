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


def test_every_tool_the_engine_probe_addresses_is_registered():
    """``scripts/verify_engine_links.py`` names its tools by hand.

    The registry is the single source of truth for tool names, so a rename would
    leave the probe addressing a tool that no longer exists -- and nothing would
    notice until somebody next ran it against a real engine, which is exactly
    the situation the probe exists to make rare.
    """

    from fantasy_agent.tool_registry import combined_registry
    from scripts import verify_engine_links

    registered = set(combined_registry().names())
    unknown = sorted(set(verify_engine_links.TOOLS) - registered)
    assert not unknown, (
        f"scripts/verify_engine_links.py addresses unregistered tools: {unknown}. "
        "Update its TOOLS so the probe still covers every link."
    )


def test_the_engine_probe_reports_every_link_without_any_engine_installed(
    monkeypatch, tmp_path
):
    """The degraded path is the one that actually runs on most machines.

    Unreal is not installed here and ComfyUI is usually not running, so "the
    probe still produces a result for every link" is the behaviour that gets
    exercised -- and the one worth pinning, because a probe that raises on the
    first missing engine cannot tell you which links are fine. All three engine
    lookups are stubbed to ``None`` and the ComfyUI client is stubbed to refuse;
    the bridges then fall back to their own defaults and report a failed launch
    instead of raising.
    """

    from urllib import error

    from fantasy_agent import local_tools
    from fantasy_agent.comfyui_client import ComfyUIClient
    from scripts import verify_engine_links

    for engine in ("_find_godot", "_find_blender", "_find_unreal"):
        monkeypatch.setattr(local_tools, engine, lambda: None)

    # ComfyUI is a *service*, not a binary, so there is nothing for the lookup
    # stub to disable. Without this the probe would drive a real GPU generation
    # on any machine that happens to have a server up, and the test would pass
    # for the wrong reason while quietly doing minutes of work.
    def no_server(*_args: object, **_kwargs: object) -> None:
        raise error.URLError("no ComfyUI server in this test")

    # `history` and `download_image` do not route through `get_json`, and today
    # they are unreachable here -- `queue_prompt` raises before the run step
    # gets to them. They are stubbed anyway because "unreachable" is a property
    # of the current call order, not of this test: a later edit that reads
    # history first would put a live ComfyUI back in the loop. Necessity here is
    # not provable, which is stated rather than dressed up.
    for method in ("get_json", "queue_prompt", "history", "download_image"):
        monkeypatch.setattr(ComfyUIClient, method, no_server)

    steps = verify_engine_links.probe(tmp_path)

    assert [step.label for step in steps] == list(verify_engine_links.TOOLS)
    # Nothing crashed on the way, and the links that need no engine still work.
    assert {step.status for step in steps} <= {"ok", "refused", "error"}
    assert next(s for s in steps if s.label == "create_project_structure").status == "ok"
    # A missing service is a report, not an exception: the probe's whole job is
    # telling "not running" apart from "broken".
    probe = next(s for s in steps if s.label == "probe_comfyui_capabilities")
    assert verify_engine_links._structured(probe.outcome)["status"] == "unavailable"


def test_the_probe_resolves_reported_paths_against_its_own_workspace(tmp_path):
    """Bridges report workspace-relative paths, and the cwd is not the workspace.

    Checking them against the cwd judges *this* run by whatever an older run
    left in the repo: the Blender step once printed ``exists=True`` for .fbx
    files that were four months old, while the run's real output sat untouched
    under the workspace. A probe that confirms success from stale files is worse
    than one that reports nothing.
    """

    from scripts import verify_engine_links

    relative = verify_engine_links._resolve(tmp_path, "generated/assets/a.fbx")
    assert relative == tmp_path / "generated" / "assets" / "a.fbx"

    absolute = verify_engine_links._resolve(tmp_path, "D:/elsewhere/a.fbx")
    assert absolute == Path("D:/elsewhere/a.fbx")


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
