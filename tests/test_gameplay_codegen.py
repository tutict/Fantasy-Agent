"""Tests for gameplay GDScript generation (M6a/M6b)."""

from __future__ import annotations

from unittest import mock

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.gameplay_codegen import (
    ENEMY_SCRIPT,
    GAME_MANAGER_SCRIPT,
    PLAYER_SCRIPT,
    deterministic_gameplay_scripts,
    generate_gameplay_scripts,
)
from fantasy_agent.generation import design_from_prompt_deterministic


def _parkour_spec():
    return design_from_prompt_deterministic(
        PromptRequest(prompt="a rooftop parkour demo", target_minutes=10)
    )


def test_deterministic_parkour_has_real_mechanics():
    scripts = deterministic_gameplay_scripts(_parkour_spec())
    player = scripts[PLAYER_SCRIPT]
    # Richer than the old WASD+jump: sprint/wall-run/slide present.
    assert "[SPRINT]" in player
    assert "[WALL_RUN]" in player
    assert "[SLIDE]" in player
    assert "is_on_wall()" in player
    assert player.startswith("extends CharacterBody3D")


def test_deterministic_game_manager_has_win_fail_hud():
    scripts = deterministic_gameplay_scripts(_parkour_spec())
    gm = scripts[GAME_MANAGER_SCRIPT]
    assert "func reach_exit" in gm
    assert "_win" in gm and "_fail" in gm
    assert "Label" in gm  # HUD
    assert "reload_current_scene" in gm
    assert "func fail_from_enemy" in gm


def test_deterministic_enemy_controller_has_m6b_behaviors():
    scripts = deterministic_gameplay_scripts(_parkour_spec())
    enemy = scripts[ENEMY_SCRIPT]
    assert enemy.startswith("extends Area3D")
    for behavior in ["patrol", "chase", "stationary", "ranged"]:
        assert behavior in enemy
    assert "fail_from_enemy" in enemy
    assert 'get_first_node_in_group("player")' in enemy


def test_generate_uses_llm_when_available():
    spec = _parkour_spec()
    fake = {
        PLAYER_SCRIPT: "extends CharacterBody3D\nfunc _ready(): pass\n",
        GAME_MANAGER_SCRIPT: "extends Node\nfunc reach_exit(): pass\n",
    }
    with mock.patch("fantasy_agent.llm.complete_json", return_value=fake) as mocked:
        scripts = generate_gameplay_scripts(spec, use_llm=True)
    mocked.assert_called_once()
    assert scripts[PLAYER_SCRIPT].startswith("extends CharacterBody3D")


def test_generate_falls_back_when_llm_returns_invalid():
    spec = _parkour_spec()
    # Missing game_manager / not valid GDScript -> fall back to deterministic.
    with mock.patch("fantasy_agent.llm.complete_json", return_value={"foo": "bar"}):
        scripts = generate_gameplay_scripts(spec, use_llm=True)
    # Deterministic fallback markers present.
    assert "[SPRINT]" in scripts[PLAYER_SCRIPT]
    assert ENEMY_SCRIPT in scripts


def test_generate_falls_back_when_llm_raises():
    spec = _parkour_spec()
    import fantasy_agent.llm as llm

    with mock.patch("fantasy_agent.llm.complete_json", side_effect=llm.LLMError("boom")):
        scripts = generate_gameplay_scripts(spec, use_llm=True)
    assert "func reach_exit" in scripts[GAME_MANAGER_SCRIPT]
    assert "fail_from_enemy" in scripts[GAME_MANAGER_SCRIPT]


def test_default_path_is_deterministic_without_flag(monkeypatch):
    monkeypatch.delenv("FANTASY_AGENT_USE_LLM", raising=False)
    spec = _parkour_spec()
    with mock.patch(
        "fantasy_agent.llm.complete_json", side_effect=AssertionError("must not call")
    ):
        scripts = generate_gameplay_scripts(spec)
    assert "[SPRINT]" in scripts[PLAYER_SCRIPT]
