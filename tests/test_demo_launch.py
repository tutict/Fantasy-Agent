"""CLI and Studio share one demo launch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fantasy_agent.contracts import EnemyPressureTuning, PromptRequest
from fantasy_agent.demo_launch import (
    DemoLaunch,
    DemoLaunchError,
    infer_demo_engine,
    launch_demo,
    resolve_demo_executables,
)
from fantasy_agent.executor import ExecutionResult
from fantasy_agent.workflows import run_director_workflow

PROMPT = "rooftop parkour chase with wall-runs, vaults, and checkpoints"


@pytest.fixture(scope="module")
def plan():
    return run_director_workflow(
        PromptRequest(prompt=PROMPT, target_minutes=10, engine_version="Godot 4")
    )


def test_infer_demo_engine_follows_the_studio_rules(plan):
    assert infer_demo_engine(plan, "") == "godot"
    assert infer_demo_engine(plan, "Godot 4") == "godot"
    assert infer_demo_engine(plan, "UE5") == "unreal"
    assert infer_demo_engine(plan, "unreal") == "unreal"
    assert infer_demo_engine(plan, "UE5.4") == "unreal"
    assert infer_demo_engine(plan, "Unreal Engine") == "unreal"
    assert infer_demo_engine(plan, "value") == "godot"
    assert infer_demo_engine(plan, "rescue the courier") == "godot"
    assert infer_demo_engine(plan, "queue the next build") == "godot"


def test_resolve_prefers_an_explicit_path_and_falls_back(monkeypatch):
    def explode():
        raise AssertionError("probe")

    monkeypatch.setattr("fantasy_agent.local_tools._find_godot", explode)
    monkeypatch.setattr("fantasy_agent.local_tools._find_blender", explode)
    monkeypatch.setattr("fantasy_agent.local_tools._find_unreal", explode)
    explicit = resolve_demo_executables(
        godot_exe="C:/given/godot.exe",
        blender_exe="C:/given/blender.exe",
        unreal_cmd="C:/given/UnrealEditor-Cmd.exe",
    )
    assert explicit.godot_found is True
    assert explicit.godot_exe == "C:/given/godot.exe"
    assert explicit.unreal_cmd == "C:/given/UnrealEditor-Cmd.exe"

    monkeypatch.setattr("fantasy_agent.local_tools._find_godot", lambda: None)
    monkeypatch.setattr("fantasy_agent.local_tools._find_blender", lambda: None)
    monkeypatch.setattr("fantasy_agent.local_tools._find_unreal", lambda: None)
    missing = resolve_demo_executables()
    assert missing.godot_found is False
    assert missing.godot_exe == "godot"
    assert missing.blender_exe == "blender"
    assert missing.blender_found is False
    assert missing.unreal_found is False
    assert missing.unreal_cmd == "UnrealEditor-Cmd"


def test_godot_launch_normalizes_resume_and_forwards_flags(monkeypatch, plan):
    captured: dict = {}

    def fake_godot(_plan, **kwargs):
        captured.update(kwargs)
        return ExecutionResult(status="done", session_id=kwargs["session_id"])

    def fake_unreal(*_args, **_kwargs):
        raise AssertionError("unreal executor should not run")

    monkeypatch.setattr("fantasy_agent.executor.execute_godot_demo", fake_godot)
    monkeypatch.setattr("fantasy_agent.executor.execute_unreal_demo", fake_unreal)
    tuning = EnemyPressureTuning()
    result = launch_demo(
        DemoLaunch(
            plan=plan,
            engine="Godot 4",
            confirmed=True,
            session_id="sess-9",
            resume_from="spec",
            with_assets=True,
            with_visuals=True,
            with_gameplay=True,
            enemy_tuning=tuning,
            approval_manifest_path="generated/asset-approval-manifest.yaml",
            comfyui_endpoint="http://127.0.0.1:8188",
            run_import=False,
            godot_exe="C:/fake/godot.exe",
            blender_exe="C:/fake/blender.exe",
        )
    )
    assert result.session_id == "sess-9"
    assert captured["resume_from"] == "comfyui"
    assert captured["run_import"] is False
    assert captured["with_assets"] is True
    assert captured["with_visuals"] is True
    assert captured["with_gameplay"] is True
    assert captured["enemy_tuning"] is tuning
    assert captured["approval_manifest_path"] == "generated/asset-approval-manifest.yaml"
    assert captured["comfyui_endpoint"] == "http://127.0.0.1:8188"
    assert captured["godot_exe"] == "C:/fake/godot.exe"
    assert captured["blender_exe"] == "C:/fake/blender.exe"


def test_unreal_launch_keeps_the_session_and_drops_asset_flags(monkeypatch, plan):
    captured: dict = {}

    def fake_unreal(_plan, **kwargs):
        captured.update(kwargs)
        return ExecutionResult(status="done", session_id=kwargs["session_id"])

    monkeypatch.setattr("fantasy_agent.executor.execute_unreal_demo", fake_unreal)
    result = launch_demo(
        DemoLaunch(
            plan=plan,
            engine="UE5",
            confirmed=True,
            session_id="sess-u",
            run_import=False,
            with_assets=True,
            with_visuals=True,
            unreal_cmd="C:/fake/UnrealEditor-Cmd.exe",
        )
    )
    assert result.session_id == "sess-u"
    assert captured["session_id"] == "sess-u"
    assert captured["run_validation"] is False
    assert captured["unreal_cmd"] == "C:/fake/UnrealEditor-Cmd.exe"
    assert "with_assets" not in captured
    assert "with_visuals" not in captured
    assert "resume_from" not in captured


def test_resume_errors_use_stable_codes(plan):
    with pytest.raises(DemoLaunchError) as missing:
        launch_demo(
            DemoLaunch(plan=plan, engine="Godot 4", resume_from="create", godot_exe="C:/godot.exe")
        )
    assert missing.value.code == "resume_needs_session"

    with pytest.raises(DemoLaunchError) as unreal:
        launch_demo(
            DemoLaunch(
                plan=plan,
                engine="UE5",
                session_id="sess",
                resume_from="create",
                unreal_cmd="C:/UnrealEditor-Cmd.exe",
            )
        )
    assert unreal.value.code == "resume_not_supported"

    with pytest.raises(DemoLaunchError) as bad:
        launch_demo(
            DemoLaunch(
                plan=plan,
                engine="Godot 4",
                session_id="sess",
                resume_from="not-a-stage",
                godot_exe="C:/godot.exe",
            )
        )
    assert bad.value.code == "bad_stage"
    assert "未知的续跑节点" in str(bad.value)


def _cli_args(**overrides):
    args = {
        "engine": "UE5",
        "execute": True,
        "yes": True,
        "no_import": True,
        "with_assets": False,
        "with_visuals": False,
        "with_gameplay": False,
        "godot_exe": None,
        "blender_exe": None,
        "unreal_exe": "C:/fake/UnrealEditor-Cmd.exe",
        "session_id": None,
        "from_stage": None,
        "approval_manifest_path": None,
        "comfyui_endpoint": None,
    }
    args.update(overrides)
    return SimpleNamespace(**args)


def test_cli_honors_an_unreal_session_id(monkeypatch, plan, capsys):
    seen: dict = {}

    def fake(request):
        seen["request"] = request
        return ExecutionResult(status="done", session_id=request.session_id)

    monkeypatch.setattr("fantasy_agent.demo_launch.launch_demo", fake)
    from fantasy_agent.__main__ import _run_executor

    code = _run_executor(
        plan,
        _cli_args(with_assets=True, session_id="sess-unreal", no_import=True),
    )
    assert code == 0
    assert seen["request"].session_id == "sess-unreal"
    assert seen["request"].engine == "UE5"
    assert "not applied on the Unreal path" in capsys.readouterr().err


def test_cli_rejects_unreal_resume_without_launching(monkeypatch, plan, capsys):
    def fake(*_args, **_kwargs):
        raise AssertionError("executor")

    monkeypatch.setattr("fantasy_agent.executor.execute_unreal_demo", fake)
    from fantasy_agent.__main__ import _run_executor

    code = _run_executor(
        plan,
        _cli_args(session_id="sess", from_stage="create", no_import=True),
    )
    assert code == 2
    assert "Unreal resume is not wired" in capsys.readouterr().err


def test_cli_missing_godot_still_exits_2(monkeypatch, plan, capsys):
    monkeypatch.setattr("fantasy_agent.local_tools._find_godot", lambda: None)

    def fake(_request):
        raise AssertionError("launch")

    monkeypatch.setattr("fantasy_agent.demo_launch.launch_demo", fake)
    from fantasy_agent.__main__ import _run_executor

    code = _run_executor(
        plan,
        _cli_args(engine="Godot 4", no_import=False, unreal_exe=None),
    )
    assert code == 2
    assert "No Godot executable found" in capsys.readouterr().err
