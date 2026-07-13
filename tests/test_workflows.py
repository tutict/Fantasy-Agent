from fantasy_agent.contracts import PromptRequest
from fantasy_agent.idea_discovery import extract_idea_seed, prompt_request_from_seed
from fantasy_agent.contracts import IdeaDiscoveryRequest
from fantasy_agent.workflows import run_director_workflow


def test_director_workflow_creates_playable_slice_plan():
    request = PromptRequest(
        prompt="a stealth courier escapes a haunted train station",
        target_minutes=10,
    )

    plan = run_director_workflow(request)

    assert plan.gameplay_spec.target_session_minutes == 10
    assert plan.gameplay_spec.i18n is not None
    assert plan.gameplay_spec.i18n.output_locales == ["en", "zh-CN"]
    assert len(plan.gameplay_spec.core_loop) >= 3
    assert len(plan.gameplay_spec.systems) >= 3
    assert plan.gdd.markdown.startswith("# ")
    assert "zh-CN" in plan.gdd.markdown_by_locale
    assert "核心循环" in plan.gdd.markdown_by_locale["zh-CN"]
    assert "M_Prototype_Greybox" in plan.unreal_plan.maps
    assert plan.godot_plan.scenes == ["scenes/main.tscn"]
    assert "assets/generated" in plan.godot_plan.folders
    assert plan.blender_plan.jobs
    assert plan.comfyui_plan.jobs
    assert plan.comfyui_plan.jobs[0].workflow_template.startswith("templates/comfyui/")
    assert plan.creative_review.items
    assert plan.creative_review.approval_gate == "blocks_unreal_ingest"
    assert {"comfyui", "blender"} <= {item.source for item in plan.creative_review.items}
    assert "average_session_minutes" in plan.qa_plan.metrics
    assert plan.task_breakdown is not None
    assert plan.task_breakdown.recommended_next_task == "gameplay_spec_review"
    assert any(task.requires_confirmation for task in plan.task_breakdown.tasks)
    assert any(task.id == "creative_asset_review" and task.status == "blocked" for task in plan.task_breakdown.tasks)
    assert any(task.id == "unreal_asset_ingest" and task.status == "blocked" for task in plan.task_breakdown.tasks)
    ingest_task = next(task for task in plan.task_breakdown.tasks if task.id == "unreal_asset_ingest")
    assert "creative_asset_review" in ingest_task.depends_on
    assert any(task.id == "unreal_level_assembly" and task.status == "blocked" for task in plan.task_breakdown.tasks)
    assert plan.production_pipeline is not None
    assert [stage.id for stage in plan.production_pipeline.stages] == [
        "gameplay_orchestration",
        "comfyui_visual_production",
        "blender_modeling",
        "creative_review",
        "asset_integration",
        "unreal_production",
        "optimization_testing",
    ]
    assert plan.production_pipeline.next_stage == "comfyui_visual_production"
    assert not any(stage.id == "godot_quick_play" for stage in plan.production_pipeline.stages)
    assert any(
        "character" in output.lower()
        for stage in plan.production_pipeline.stages
        for output in stage.outputs
    )
    assert any(
        stage.id == "asset_integration" and stage.status == "blocked"
        for stage in plan.production_pipeline.stages
    )
    asset_stage = next(stage for stage in plan.production_pipeline.stages if stage.id == "asset_integration")
    assert asset_stage.depends_on == ["creative_review"]


def test_director_workflow_switches_pipeline_for_godot_engine():
    request = PromptRequest(
        prompt="a stealth courier escapes a haunted train station",
        target_minutes=10,
        engine_version="Godot 4.3",
    )

    plan = run_director_workflow(request)

    assert plan.godot_plan.engine_version == "Godot 4.3"
    assert plan.unreal_plan.engine_version == "UE5"
    assert [stage.id for stage in plan.production_pipeline.stages] == [
        "gameplay_orchestration",
        "comfyui_visual_production",
        "blender_modeling",
        "creative_review",
        "asset_integration",
        "godot_quick_play",
        "optimization_testing",
    ]
    assert not any(stage.id == "unreal_production" for stage in plan.production_pipeline.stages)
    assert any(task.id == "godot_quick_play_project" for task in plan.task_breakdown.tasks)
    assert not any(task.id.startswith("unreal_") for task in plan.task_breakdown.tasks)


def test_director_workflow_specializes_parkour_prompts():
    request = PromptRequest(
        prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
        target_minutes=10,
    )

    plan = run_director_workflow(request)

    assert plan.gameplay_spec.core_verbs == ["sprint", "vault", "wall-run", "slide"]
    assert "Momentum Chain" in {system.name for system in plan.gameplay_spec.systems}
    assert "Wall-run panel set" in plan.gameplay_spec.asset_needs
    assert any("checkpoint" in beat.gameplay_focus.lower() for beat in plan.gameplay_spec.level_beats)


def test_director_workflow_detects_chinese_parkour_prompt():
    # Chinese "跑酷" (parkour) must resolve to the parkour axis, not the
    # generic systems fallback, in the deterministic planner.
    request = PromptRequest(prompt="我想做一个跑酷的demo", target_minutes=10)

    plan = run_director_workflow(request)

    assert plan.gameplay_spec.core_verbs == ["sprint", "vault", "wall-run", "slide"]
    assert "Momentum Chain" in {system.name for system in plan.gameplay_spec.systems}


def test_director_workflow_specializes_chinese_portfolio_godot_story():
    seed_request = IdeaDiscoveryRequest(
        raw_idea=(
            "我想利用 Godot 做一个用来应聘的小游戏，结合休学、他人评价、"
            "走出自己的道路、害怕自废武功、从代码转职游戏策划、"
            "以及希望像团队里的战地庸医一样关键时刻发挥价值的经历。"
        ),
        target_minutes=10,
        engine_version="Godot 4.3",
        source_locale="zh-CN",
        output_locales=["zh-CN", "en"],
        constraints=["应聘作品", "个人经历改编", "game jam 规模"],
    )
    prompt_request = prompt_request_from_seed(extract_idea_seed(seed_request), seed_request)

    plan = run_director_workflow(prompt_request)
    spec = plan.gameplay_spec

    assert spec.title == "Road Beyond The Fog"
    assert spec.core_verbs == ["discern", "choose", "compose", "support"]
    assert "Evaluation Fog" in {system.name for system in spec.systems}
    assert "Design Board Translation" in {system.name for system in spec.systems}
    assert "Interview Gate Triage" in {beat.name for beat in spec.level_beats}
    assert "Design board UI proxy" in spec.asset_needs
    assert plan.godot_plan.engine_version == "Godot 4.3"
    assert any(stage.id == "godot_quick_play" for stage in plan.production_pipeline.stages)
    assert not any(stage.id == "unreal_production" for stage in plan.production_pipeline.stages)
    assert "雾外之路" in plan.gdd.markdown_by_locale["zh-CN"]
    assert "应聘门" in plan.gdd.markdown_by_locale["zh-CN"]



def test_level_beats_cover_every_valid_target_minutes():
    # PromptRequest allows 5-15 minutes. The deterministic beats must sum to
    # that target for every value, otherwise the production spec bundle fails
    # deep validation and blocks its own execution.
    axis_prompts = [
        "a rooftop parkour demo",
        "a portfolio story about choosing your own road",
        "a stealth courier escapes a haunted train station",
    ]
    for prompt in axis_prompts:
        for target in range(5, 16):
            plan = run_director_workflow(PromptRequest(prompt=prompt, target_minutes=target))
            beats = plan.gameplay_spec.level_beats
            assert sum(beat.duration_minutes for beat in beats) == target, (prompt, target)

            bundle = plan.production_spec_bundle
            assert bundle is not None
            errors = [
                issue.message
                for issue in bundle.validation.issues
                if issue.severity == "error"
            ]
            assert bundle.validation.status != "failed", (prompt, target, errors)


def test_enemy_rosters_follow_axis_and_explicit_prompt():
    stealth = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes a haunted train station")
    ).gameplay_spec
    assert {enemy.behavior for enemy in stealth.enemies} >= {"patrol", "stationary"}

    parkour = run_director_workflow(
        PromptRequest(prompt="a rooftop parkour demo with a chase drone")
    ).gameplay_spec
    assert any(enemy.behavior == "chase" for enemy in parkour.enemies)

    career = run_director_workflow(
        PromptRequest(prompt="a portfolio story about choosing your own road")
    ).gameplay_spec
    assert career.enemies == []

    explicit = run_director_workflow(
        PromptRequest(prompt="a calm puzzle game with one hostile drone enemy")
    ).gameplay_spec
    assert len(explicit.enemies) == 1
    assert explicit.enemies[0].behavior == "chase"
