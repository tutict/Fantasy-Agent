from __future__ import annotations

import importlib.util
from pathlib import Path

from fantasy_agent.contracts import PromptRequest


def _load_web_console_app():
    module_path = Path("apps/web-console/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_web_console_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_console_static_ui_exposes_flow_console_sections():
    module = _load_web_console_app()
    html = module.STATIC_DIR.joinpath("index.html").read_text(encoding="utf-8")
    js = module.STATIC_DIR.joinpath("app.js").read_text(encoding="utf-8")

    assert module.health()["agent"] == "web-console"
    assert 'id="stage-strip"' in html
    assert 'id="gate-summary"' in html
    assert 'id="review-panel"' in html
    assert 'id="activity-log"' in html
    assert 'id="load-handoff-button"' in html
    assert 'id="correction-notes"' in html
    assert 'id="plan-form"' not in html
    assert "Flow console" in html
    assert "流程控制台" in js
    assert "策划交接" in js
    assert "纠偏队列" in js
    assert "fantasy-agent-planning-handoff" in js
    assert "usesGodotEngine" in js
    assert "创意审阅" in js
    assert "执行门禁" in js


def test_web_console_plan_payload_feeds_review_and_pipeline_ui():
    module = _load_web_console_app()
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
    module = _load_web_console_app()
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
