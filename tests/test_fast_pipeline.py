"""
Fast Pipeline 单元测试

测试各个 Agent 的输入/输出合约、错误处理和集成流程。
"""

import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from fantasy_agent.fast_agents import (
    parse_file_blocks,
    run_planning_agent,
    run_review_agent,
    write_project_files,
)


class TestPlanningAgent:
    """测试策划 Agent 的 GDD 生成"""

    def test_gdd_has_required_fields(self):
        """GDD 必须包含所有必需字段"""
        required_fields = [
            "game_title",
            "genre",
            "dimension",
            "engine_choice",
            "asset_list",
            "palette",
            "core_loop",
            "levels",
            "style",
        ]

        # Mock AI 响应
        mock_gdd = {
            "game_title": "Test Game",
            "genre": "platformer",
            "dimension": "2d",
            "engine_choice": "godot",
            "engine_reason": "2D 游戏",
            "asset_list": [
                {"name": "player", "type": "character", "poly_budget": 1000}
            ],
            "palette": ["#FF0000", "#00FF00"],
            "core_loop": "跳跃收集",
            "levels": 1,
            "style": "lowpoly",
            "controls": {"move": "WASD", "action": "Space", "camera": "none"},
            "audio": {"bgm_style": "ambient", "sfx_list": ["jump"]},
            "player": {"name": "player", "abilities": ["jump"], "start_position": {"x": 0, "y": 0}},
            "enemies": [],
            "level_descriptions": ["First level"],
            "win_condition": "Reach the end",
            "lose_condition": "Fall off map",
            "estimated_playtime_minutes": 5,
            "target_platform": "windows",
        }

        with mock.patch(
            "fantasy_agent.fast_agents.client.messages.create"
        ) as mock_create:
            mock_create.return_value.content = [
                mock.Mock(text=json.dumps(mock_gdd))
            ]

            gdd = run_planning_agent("Test idea")

            for field in required_fields:
                assert field in gdd, f"GDD 缺少字段 {field}"

    def test_gdd_engine_choice_valid(self):
        """engine_choice 必须是 godot 或 ue5"""
        mock_gdd = {
            "game_title": "Test",
            "genre": "platformer",
            "dimension": "2d",
            "engine_choice": "godot",
            "engine_reason": "2D game",
            "asset_list": [{"name": "test", "type": "prop", "poly_budget": 1000}],
            "palette": ["#FF0000"],
            "core_loop": "test",
            "levels": 1,
            "style": "lowpoly",
            "controls": {"move": "WASD", "action": "Space", "camera": "none"},
            "audio": {"bgm_style": "ambient", "sfx_list": []},
            "player": {"name": "p", "abilities": [], "start_position": {"x": 0, "y": 0}},
            "enemies": [],
            "level_descriptions": ["Test"],
            "win_condition": "Win",
            "lose_condition": "Lose",
            "estimated_playtime_minutes": 5,
            "target_platform": "windows",
        }

        with mock.patch(
            "fantasy_agent.fast_agents.client.messages.create"
        ) as mock_create:
            mock_create.return_value.content = [
                mock.Mock(text=json.dumps(mock_gdd))
            ]

            gdd = run_planning_agent("Test idea")
            assert gdd["engine_choice"] in ("godot", "ue5")

    def test_gdd_asset_list_not_empty(self):
        """asset_list 不能为空"""
        mock_gdd = {
            "game_title": "Test",
            "genre": "platformer",
            "dimension": "2d",
            "engine_choice": "godot",
            "engine_reason": "2D",
            "asset_list": [
                {"name": "player", "type": "character", "poly_budget": 1000}
            ],
            "palette": ["#FF0000"],
            "core_loop": "test",
            "levels": 1,
            "style": "lowpoly",
            "controls": {"move": "WASD", "action": "Space", "camera": "none"},
            "audio": {"bgm_style": "ambient", "sfx_list": []},
            "player": {"name": "p", "abilities": [], "start_position": {"x": 0, "y": 0}},
            "enemies": [],
            "level_descriptions": ["Test"],
            "win_condition": "Win",
            "lose_condition": "Lose",
            "estimated_playtime_minutes": 5,
            "target_platform": "windows",
        }

        with mock.patch(
            "fantasy_agent.fast_agents.client.messages.create"
        ) as mock_create:
            mock_create.return_value.content = [
                mock.Mock(text=json.dumps(mock_gdd))
            ]

            gdd = run_planning_agent("Test idea")
            assert len(gdd["asset_list"]) > 0


class TestFileBlockParsing:
    """测试多文件格式解析"""

    def test_parse_single_file(self):
        """解析单个文件块"""
        raw = """===FILE: res://project.godot===
[gd_resource type="ProjectSettings"]
===END==="""
        files = parse_file_blocks(raw)
        assert "res://project.godot" in files
        assert "[gd_resource" in files["res://project.godot"]

    def test_parse_multiple_files(self):
        """解析多个文件块"""
        raw = """===FILE: res://project.godot===
content1
===END===
===FILE: res://src/player.gd===
extends Node2D
===END==="""
        files = parse_file_blocks(raw)
        assert len(files) == 2
        assert "res://project.godot" in files
        assert "res://src/player.gd" in files

    def test_parse_empty_output(self):
        """空输出返回空字典"""
        files = parse_file_blocks("no files here")
        assert files == {}

    def test_parse_strips_whitespace(self):
        """解析时清理路径和内容的空白"""
        raw = """===FILE:   res://test.gd   ===
   content
===END==="""
        files = parse_file_blocks(raw)
        # 路径应被 strip
        assert "res://test.gd" in files


class TestProjectFileWriting:
    """测试项目文件写入"""

    def test_write_godot_files(self):
        """写入 Godot 项目文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {
                "res://project.godot": "[gd_resource]\n",
                "res://scenes/main.tscn": "[gd_scene]\n",
                "res://src/player.gd": "extends Node2D\n",
            }

            count = write_project_files(files, tmpdir, "godot")

            assert count == 3
            assert (Path(tmpdir) / "project.godot").exists()
            assert (Path(tmpdir) / "scenes" / "main.tscn").exists()
            assert (Path(tmpdir) / "src" / "player.gd").exists()

    def test_write_creates_subdirectories(self):
        """写入时自动创建子目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {"res://scenes/levels/level1.tscn": "content"}

            write_project_files(files, tmpdir, "godot")

            assert (Path(tmpdir) / "scenes" / "levels" / "level1.tscn").exists()

    def test_write_preserves_encoding(self):
        """写入时保留中文编码"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {"res://test.md": "# 游戏标题\n## 玩法说明"}

            write_project_files(files, tmpdir, "godot")

            content = (Path(tmpdir) / "test.md").read_text(encoding="utf-8")
            assert "游戏标题" in content


class TestReviewAgent:
    """测试审查 Agent"""

    def test_review_returns_empty_array_if_no_issues(self):
        """无问题时返回空数组"""
        project_files = {"res://src/player.gd": "extends CharacterBody2D\nvar speed = 100"}
        gdd = {"game_title": "Test", "genre": "platformer"}

        with mock.patch(
            "fantasy_agent.fast_agents.client.messages.create"
        ) as mock_create:
            mock_create.return_value.content = [mock.Mock(text="[]")]

            issues = run_review_agent(project_files, gdd)
            assert issues == []

    def test_review_returns_issues_with_required_fields(self):
        """返回的问题必须有所有必需字段"""
        project_files = {"res://src/player.gd": "var x = $NonexistentNode"}
        gdd = {"game_title": "Test"}

        mock_issues = [
            {
                "file": "res://src/player.gd",
                "line": 1,
                "severity": "critical",
                "category": "crash",
                "description": "节点不存在",
                "fix_suggestion": "使用 @onready 声明",
            }
        ]

        with mock.patch(
            "fantasy_agent.fast_agents.client.messages.create"
        ) as mock_create:
            mock_create.return_value.content = [
                mock.Mock(text=json.dumps(mock_issues))
            ]

            issues = run_review_agent(project_files, gdd)

            assert len(issues) == 1
            issue = issues[0]
            assert issue["file"] == "res://src/player.gd"
            assert issue["severity"] in ("critical", "warning")
            assert issue["category"] in (
                "crash",
                "logic",
                "performance",
                "missing_file",
            )
            assert issue["line"] >= 0
