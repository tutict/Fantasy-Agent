"""Keep the Studio REST surface and the frontend's use of it in sync.

Two directions matter, and they fail differently:

- **Frontend calls an endpoint the backend doesn't have** -- a 404 at runtime,
  usually from a rename. This must never pass.
- **The backend grows an endpoint the frontend never calls** -- not a bug on
  its own (most of these are covered by ``tests/test_studio_app.py`` and are
  reached through the legacy static pages), but a silent UI gap. New ones have
  to be registered in ``KNOWN_WITHOUT_UI`` on purpose rather than by accident.

This test exists because the 2026-09-10 frontend review found 15 of the
backend's API endpoints with no UI entry point; without a guard the list just
keeps growing unnoticed. See
``docs/architecture/review-2026-09-10-frontend-four-axes.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = REPO_ROOT / "apps" / "studio" / "app" / "main.py"
FRONTEND_SRC = REPO_ROOT / "apps" / "frontend" / "src"

ROUTE_PATTERN = re.compile(r'@app\.(?:get|post|put|delete|patch)\("([^"]+)"')
# `%` appears in encoded ids; `?`/`#` start query and fragment, which are not
# part of the route.
API_PATH_PATTERN = re.compile(r"(/api/[A-Za-z0-9/_.\-%{}]*)")
# `/api/sessions/${id}/state` -- collapse the JS interpolation before matching
# so it lines up with FastAPI's `{session_id}`.
TEMPLATE_PATTERN = re.compile(r"\$\{[^}]*\}")
PATH_PARAM_PATTERN = re.compile(r"\{[^}]*\}")

PARAM = "{param}"

# Endpoints the backend serves that the new frontend (`apps/frontend/`) does
# not call. Every entry needs a reason -- if you are adding one, the question
# is whether it should be a UI feature instead.
KNOWN_WITHOUT_UI: dict[str, str] = {
    "/api/plan": "plan generation; the React workbench calls generate_game_production_plan via /api/tools",
    "/api/design": "gameplay spec preview; no panel in the new console yet",
    "/api/gdd": "GDD rendering; the workbench calls render_gdd via /api/tools",
    "/api/qa": "QA plan; the workbench calls prepare_qa_plan via /api/tools",
    "/api/tasks": "task breakdown; rendered from the plan payload instead",
    "/api/pipeline": "production pipeline; rendered from the plan payload instead",
    "/api/idea-seed": "idea seeds; the workbench calls extract_idea_seed via /api/tools",
    "/api/tool-contracts": "MCP contract dump; inspection-only, no UI",
    "/api/unreal/plan": "per-engine plan; the console builds plans client-side",
    "/api/godot/plan": "per-engine plan; the console builds plans client-side",
    "/api/blender/plan": "per-engine plan; the console builds plans client-side",
    "/api/blender/script": "Blender script preview; no panel yet",
    "/api/blender/plan-script": "Blender plan+script; no panel yet",
    "/api/comfyui/plan": "per-engine plan; the console builds plans client-side",
    "/api/creative-review": "creative review; reached through the approval manifest flow",
}


def _normalize(path: str) -> str:
    return PATH_PARAM_PATTERN.sub(PARAM, path).rstrip("/")


def _backend_api_routes() -> set[str]:
    if not MAIN_PY.exists():
        pytest.skip(f"Studio backend not present at {MAIN_PY}")
    found = {_normalize(m.group(1)) for m in ROUTE_PATTERN.finditer(MAIN_PY.read_text(encoding="utf-8"))}
    return {route for route in found if route.startswith("/api")}


def _frontend_api_paths() -> set[str]:
    if not FRONTEND_SRC.exists():
        pytest.skip(f"Frontend sources not present at {FRONTEND_SRC}")
    paths: set[str] = set()
    for source in FRONTEND_SRC.rglob("*"):
        if source.suffix not in {".ts", ".tsx"}:
            continue
        if source.stem.endswith(".test"):
            # Test fixtures quote endpoint URLs as expectations; those are not
            # real call sites and would otherwise show up as false positives.
            continue
        text = TEMPLATE_PATTERN.sub(PARAM, source.read_text(encoding="utf-8"))
        paths.update(_normalize(m.group(1)) for m in API_PATH_PATTERN.finditer(text))
    return paths


def test_backend_and_frontend_are_scannable() -> None:
    """Guard the scanner itself: an empty parse would make every test vacuous."""

    backend = _backend_api_routes()
    frontend = _frontend_api_paths()
    assert len(backend) >= 20, f"expected a populated backend route set, parsed {len(backend)}"
    assert len(frontend) >= 10, f"expected a populated frontend path set, parsed {len(frontend)}"


def test_frontend_never_calls_a_missing_endpoint() -> None:
    backend = _backend_api_routes()
    broken = sorted(_frontend_api_paths() - backend)
    assert not broken, (
        "frontend calls endpoints the Studio backend does not serve:\n"
        + "\n".join(f"  - {path}" for path in broken)
    )


def test_endpoints_without_ui_are_registered() -> None:
    backend = _backend_api_routes()
    frontend = _frontend_api_paths()
    unregistered = sorted(backend - frontend - set(KNOWN_WITHOUT_UI))
    assert not unregistered, (
        "backend endpoints have no UI entry point and are not registered in "
        "KNOWN_WITHOUT_UI. Either wire them into apps/frontend or add them to "
        "the list with a reason:\n" + "\n".join(f"  - {path}" for path in unregistered)
    )


def test_known_without_ui_has_no_stale_entries() -> None:
    backend = _backend_api_routes()
    frontend = _frontend_api_paths()
    stale = sorted(set(KNOWN_WITHOUT_UI) - backend)
    assert not stale, (
        "KNOWN_WITHOUT_UI lists endpoints the backend no longer serves: "
        + ", ".join(stale)
    )
    now_wired = sorted(set(KNOWN_WITHOUT_UI) & frontend)
    assert not now_wired, (
        "these endpoints now have a UI -- drop them from KNOWN_WITHOUT_UI: "
        + ", ".join(now_wired)
    )
