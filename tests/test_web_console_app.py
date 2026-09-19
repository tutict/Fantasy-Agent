from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from fantasy_agent.contracts import PromptRequest


def _load_studio_app():
    module_path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_console_ui_exposes_flow_console_sections():
    """The flow console's sections must exist in the React source.

    This used to read `apps/studio/static/web-console/` and accept a hit in
    either the static page or the React source. The static page is gone, so the
    "or" is gone too: each assertion could be satisfied by the dead copy, which
    is exactly how a removed UI keeps passing its own tests.
    """

    module = _load_studio_app()
    frontend_source = module.REPO_ROOT.joinpath("apps/frontend/src/console/FlowConsole.tsx").read_text(encoding="utf-8")
    frontend_i18n = module.REPO_ROOT.joinpath("apps/frontend/src/shared/i18n.ts").read_text(encoding="utf-8")
    frontend_storage = module.REPO_ROOT.joinpath("apps/frontend/src/shared/storage.ts").read_text(encoding="utf-8")

    assert module.health()["agent"] == "fantasy-agent-studio"
    # The stage strip used to be asserted here. It moved to the orchestration
    # board, which is now the only reader of `production_pipeline` -- so this
    # side of the boundary is pinned as an *absence*, and
    # `test_orchestration_board_owns_the_stage_rows` pins the other side. A
    # "presence in either file" assertion would let the dead copy keep passing.
    assert 'id="stage-strip"' not in frontend_source
    assert 'id="gate-summary"' in frontend_source
    assert 'id={`${tab}-panel`}' in frontend_source
    assert 'id="activity-log"' in frontend_source
    assert 'id="load-handoff-button"' in frontend_source
    assert 'id="correction-notes"' in frontend_source
    assert 'id="manual-tool-grid"' in frontend_source
    assert 'id="open-recommended-tool-button"' in frontend_source
    assert "Flow console" in frontend_i18n
    assert "\u6d41\u7a0b\u63a7\u5236\u53f0" in frontend_i18n
    assert "\u7b56\u5212\u4ea4\u63a5" in frontend_i18n
    assert "\u7ea0\u504f\u961f\u5217" in frontend_i18n
    assert "\u624b\u52a8\u7ea0\u504f\u5165\u53e3" in frontend_i18n
    assert "openManualCorrectionTarget" in frontend_source
    # The handoff key belongs to `shared/storage.ts`, not to this component: the
    # console *reads* the handoff, the workbench writes it, and both go through
    # the same exported constant. Asserting it against FlowConsole.tsx pinned a
    # string the component is correct not to contain.
    assert 'HANDOFF_KEY = "fantasy-agent-planning-handoff"' in frontend_storage
    assert "usePlanningHandoff" in frontend_source
    assert "usesGodotEngine" in frontend_source
    # The console must not author a plan -- the workbench does that, through its
    # own composer (`chatInput`) and `IdeaSeed`, and the handoff exists so the
    # two never disagree about one. This replaced `assert 'id="plan-form"' not in
    # html`, which was vacuously true: no file in the repo has ever contained
    # `plan-form`, so it guarded nothing while looking like a boundary. Pin the
    # ownership where it is observable instead -- the console knows nothing about
    # seeds or the plan composer.
    assert 'id="correction-notes"' in frontend_source
    assert "IdeaSeed" not in frontend_source
    assert "chatInput" not in frontend_source
    assert "\u521b\u610f\u5ba1\u9605" in frontend_i18n
    assert "\u6267\u884c\u524d\u786e\u8ba4" in frontend_i18n
    targets = module.correction_targets()
    assert targets["engine_kind"] == "unreal"
    assert {"planning", "comfyui", "blender", "unreal", "generated"} <= {
        target["id"] for target in targets["targets"]
    }
    blocked = module.correction_open(
        module.ManualCorrectionOpenRequest(target_id="blender", confirmed_side_effects=False)
    )
    assert blocked["status"] == "blocked"


def test_orchestration_board_owns_the_stage_rows():
    """The board is the only reader of `production_pipeline`.

    F3 moved the stage rows out of the console and out of the workbench, because
    a plan has to be *run* from the same view that draws it -- and the two had
    drifted into showing a plan-time snapshot of what the console was actually
    executing. The console test above pins this boundary as an absence; this
    pins the other side, so "the rows are gone from both" cannot pass as a fix.

    Only the load-bearing anchors are asserted here. What each card *does* with
    them (human gates get an approval entry point rather than an approve button,
    a rework click sends `rewind_stage`, a refusal list is shown) is covered by
    `apps/frontend/src/orchestration/OrchestrationBoard.test.tsx`, where it can
    be clicked; duplicating it as text matching would produce two guards that
    can only disagree.
    """

    module = _load_studio_app()
    board_source = module.REPO_ROOT.joinpath(
        "apps/frontend/src/orchestration/OrchestrationBoard.tsx"
    ).read_text(encoding="utf-8")

    assert 'data-testid="orchestration-board"' in board_source
    assert 'id="orchestration-cards"' in board_source
    # Plan status and run status are two vocabularies over one card, and the card
    # root carries both: rendering only one of them hides either "the plan says
    # this is ready" or "the run is blocked on approval", which is the whole
    # reason the split exists. `data-stage` is what makes the rows rows.
    assert (
        "data-stage={card.id} data-status={card.status} "
        "data-plan-status={card.plan_status}"
    ) in board_source


def test_ui_routes_refuse_to_serve_a_stale_page_when_the_bundle_is_missing(monkeypatch, tmp_path):
    """A missing bundle is a 503, not a fallback to some other HTML.

    The old behaviour returned the hand-written page with a 200, which is why
    the two UIs could drift apart without anything failing. Now the only
    possible answers are the bundle or an error that names the fix.
    """

    module = _load_studio_app()
    missing = tmp_path / "not-built" / "index.html"
    monkeypatch.setattr(module, "FRONTEND_INDEX_PATH", missing)

    for route in (module.index, module.web_console, module.workbench):
        with pytest.raises(module.HTTPException) as caught:
            route()
        assert caught.value.status_code == 503
        assert "frontend:build" in caught.value.detail


def test_ui_routes_serve_the_bundle_when_it_exists(monkeypatch, tmp_path):
    module = _load_studio_app()
    built = tmp_path / "index.html"
    built.write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    monkeypatch.setattr(module, "FRONTEND_INDEX_PATH", built)

    for route in (module.index, module.web_console, module.workbench):
        assert Path(route().path) == built


def test_web_console_plan_payload_feeds_review_and_pipeline_ui():
    module = _load_studio_app()
    plan = module.plan(
        PromptRequest(
            prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
            target_minutes=10,
        )
    )

    assert plan.production_pipeline is not None
    assert not any(stage.id == "godot_quick_play" for stage in plan.production_pipeline.stages)
    assert any(stage.id == "creative_review" for stage in plan.production_pipeline.stages)
    assert plan.creative_review.items
    assert any(task.id == "creative_asset_review" for task in plan.task_breakdown.tasks)


def test_web_console_plan_payload_switches_to_godot_pipeline_when_selected():
    module = _load_studio_app()
    plan = module.plan(
        PromptRequest(
            prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
            target_minutes=10,
            engine_version="Godot 4.3",
        )
    )

    assert plan.production_pipeline is not None
    assert any(stage.id == "godot_quick_play" for stage in plan.production_pipeline.stages)
    assert not any(stage.id == "unreal_production" for stage in plan.production_pipeline.stages)
    assert any(task.id == "godot_quick_play_project" for task in plan.task_breakdown.tasks)
