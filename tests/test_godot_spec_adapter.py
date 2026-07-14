from fantasy_agent.contracts import PromptRequest
from fantasy_agent.godot_spec_adapter import compile_godot_spec_bundle
from fantasy_agent.workflows import run_director_workflow


def _bundle():
    plan = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes sentries", engine_version="Godot 4")
    )
    assert plan.production_spec_bundle is not None
    return plan.production_spec_bundle


def test_godot_adapter_compiles_combat_level_numeric_and_narrative():
    bundle = _bundle()
    numeric = bundle.numeric.model_copy(
        update={"player_move_speed": 13.5, "pressure_clock_seconds": 480}
    )
    narrative = bundle.narrative.model_copy(
        update={"hud_text": {**bundle.narrative.hud_text, "objective": "Reach the spectral platform"}}
    )
    changed = bundle.model_copy(update={"numeric": numeric, "narrative": narrative})

    result = compile_godot_spec_bundle(changed)

    assert result.runtime_handoff["numeric"]["player_move_speed"] == 13.5
    assert result.runtime_handoff["narrative"]["hud_text"]["objective"] == "Reach the spectral platform"
    assert result.runtime_handoff["level"]["segments"]
    assert result.runtime_handoff["combat"]["encounters"]
    fields = {trace.spec_field for trace in result.traces}
    assert "numeric.player_move_speed" in fields
    assert "narrative.hud_text.objective" in fields


def test_godot_adapter_derives_enemies_when_table_missing():
    bundle = _bundle()
    assert bundle.combat is not None
    stripped = bundle.model_copy(
        update={
            "config_tables": bundle.config_tables.model_copy(
                update={
                    "tables": [
                        table
                        for table in bundle.config_tables.tables
                        if table.table_id != "enemies"
                    ]
                }
            )
        }
    )

    result = compile_godot_spec_bundle(stripped)

    enemies = result.runtime_handoff["enemies"]
    assert enemies
    assert {row["name"] for row in enemies} == set(stripped.combat.enemy_roles)
    assert all(row["behavior"] == "patrol" for row in enemies)



def test_godot_main_and_gameplay_scripts_prefer_bundle_values():
    from fantasy_agent.gameplay_codegen import deterministic_gameplay_scripts
    from fantasy_agent.godot_mcp import _main_gd
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes sentries", engine_version="Godot 4")
    )
    assert plan.production_spec_bundle is not None
    bundle = plan.production_spec_bundle
    teaching = bundle.level.teaching_segment.model_copy(update={"name": "Spec Teaching Route"})
    narrative_beats = [
        beat.model_copy(update={"level_beat": "Spec Teaching Route"})
        if beat.level_beat == bundle.level.teaching_segment.name
        else beat
        for beat in bundle.narrative.beats
    ]
    changed = bundle.model_copy(
        update={
            "level": bundle.level.model_copy(update={"teaching_segment": teaching}),
            "numeric": bundle.numeric.model_copy(
                update={"player_move_speed": 13.5, "pressure_clock_seconds": 480}
            ),
            "narrative": bundle.narrative.model_copy(
                update={
                    "beats": narrative_beats,
                    "hud_text": {**bundle.narrative.hud_text, "objective": "Reach the spectral platform"},
                }
            ),
        }
    )

    main = _main_gd(
        plan.godot_plan,
        plan.gameplay_spec,
        with_gameplay=True,
        production_spec_bundle=changed,
    )
    scripts = deterministic_gameplay_scripts(
        plan.gameplay_spec,
        production_spec_bundle=changed,
    )

    assert "spec_teaching_route" in main
    assert "Reach the spectral platform" in main
    assert "@export var move_speed := 13.5" in scripts["scripts/player_controller.gd"]
    assert "@export var pressure_limit := 480.0" in scripts["scripts/game_manager.gd"]
    assert "Reach the spectral platform" in scripts["scripts/game_manager.gd"]