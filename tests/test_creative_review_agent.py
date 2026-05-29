from __future__ import annotations

import importlib.util
from pathlib import Path

from fantasy_agent.contracts import CreativeReviewRequest, PromptRequest
from fantasy_agent.workflows import (
    prepare_blender_assets,
    prepare_comfyui_visuals,
    prepare_creative_review,
    run_director_workflow,
)


def _load_creative_review_app():
    module_path = Path("apps/creative-review-agent/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_creative_review_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_creative_review_blocks_unreal_ingest_until_user_decisions():
    director_plan = run_director_workflow(
        PromptRequest(
            prompt="a rooftop parkour demo with wall-runs and checkpoints",
            target_minutes=10,
        )
    )

    review = prepare_creative_review(
        director_plan.gameplay_spec,
        director_plan.blender_plan,
        director_plan.comfyui_plan,
    )

    assert review.approval_gate == "blocks_unreal_ingest"
    assert review.required_user_decisions
    assert len(review.items) == len(director_plan.blender_plan.jobs) + len(
        director_plan.comfyui_plan.jobs
    )
    assert all(item.approval_status == "pending_user_review" for item in review.items)
    assert any(item.revision_prompt for item in review.items if item.source == "comfyui")


def test_creative_review_agent_endpoint_returns_report_model():
    module = _load_creative_review_app()
    director_plan = run_director_workflow(
        PromptRequest(
            prompt="a stealth courier escapes a haunted train station",
            target_minutes=10,
        )
    )
    request = CreativeReviewRequest(
        gameplay_spec=director_plan.gameplay_spec,
        blender_plan=prepare_blender_assets(director_plan.gameplay_spec),
        comfyui_plan=prepare_comfyui_visuals(director_plan.gameplay_spec),
    )

    response = module.review(request)

    assert module.health()["agent"] == "creative-review-agent"
    assert response.source == "creative-review-agent"
    assert response.items
    assert response.handoff_artifacts == [
        "generated/creative-review-report.yaml",
        "generated/asset-approval-manifest.yaml",
    ]
