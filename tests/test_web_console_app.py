from __future__ import annotations

import importlib.util
from pathlib import Path

from fantasy_agent.contracts import PromptRequest


def _load_studio_app():
    module_path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_console_static_ui_exposes_flow_console_sections():
    module = _load_studio_app()
    console_dir = module.STATIC_DIR.joinpath("web-console")
    html = console_dir.joinpath("index.html").read_text(encoding="utf-8")
    js = console_dir.joinpath("app.js").read_text(encoding="utf-8")
    frontend_source = module.REPO_ROOT.joinpath("apps/frontend/src/console/FlowConsole.tsx").read_text(encoding="utf-8")
    frontend_i18n = module.REPO_ROOT.joinpath("apps/frontend/src/shared/i18n.ts").read_text(encoding="utf-8")

    assert module.health()["agent"] == "fantasy-agent-studio"
    assert 'id="stage-strip"' in html or 'id="stage-strip"' in frontend_source
    assert 'id="gate-summary"' in html or 'id="gate-summary"' in frontend_source
    assert 'id="review-panel"' in html or 'id={`${tab}-panel`}' in frontend_source
    assert 'id="activity-log"' in html or 'id="activity-log"' in frontend_source
    assert 'id="load-handoff-button"' in html or 'id="load-handoff-button"' in frontend_source
    assert 'id="correction-notes"' in html or 'id="correction-notes"' in frontend_source
    assert 'id="manual-tool-grid"' in html or 'id="manual-tool-grid"' in frontend_source
    assert 'id="open-recommended-tool-button"' in html or 'id="open-recommended-tool-button"' in frontend_source
    assert 'id="plan-form"' not in html
    assert "Flow console" in html or "Flow console" in frontend_i18n
    assert "\u6d41\u7a0b\u63a7\u5236\u53f0" in frontend_i18n
    assert "\u7b56\u5212\u4ea4\u63a5" in frontend_i18n
    assert "\u7ea0\u504f\u961f\u5217" in frontend_i18n
    assert "\u624b\u52a8\u7ea0\u504f\u5165\u53e3" in frontend_i18n
    assert "/api/manual-correction/open" in js or "openManualCorrectionTarget" in frontend_source
    assert "fantasy-agent-planning-handoff" in js or "fantasy-agent-planning-handoff" in frontend_source
    assert "usesGodotEngine" in js or "usesGodotEngine" in frontend_source
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


def test_web_console_prefers_vite_frontend_dist_when_available(monkeypatch):
    module = _load_studio_app()
    frontend_index = module.STATIC_DIR / "index.html"
    monkeypatch.setattr(module, "FRONTEND_INDEX_PATH", frontend_index)

    assert Path(module.web_console().path) == frontend_index


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
