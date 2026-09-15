"""The engine resolvers, and the open path that launches what they return.

Every engine probe in the repo ends here: the status panel is handed
``_find_godot`` / ``_find_unreal`` / ``_find_blender`` as a resolver instead of
searching again, the executor launches what they return, and
``scripts/verify_engine_links.py`` reports it. A wrong answer here is a wrong
answer everywhere, so the two ways to produce one are pinned below -- ranking
candidates by numbers that are not the version, and accepting something that
exists but is not a binary.
"""

from pathlib import Path

from fantasy_agent import local_tools


def test_a_digit_in_the_install_path_does_not_outrank_the_engine_version():
    """``user99`` is not a Godot release.

    The sort key used to be *every* digit in the path, so a sibling segment
    could outvote the version: ``C:/Users/user99/...Godot_v4.5...`` keyed as
    ``(99, 4, 5, 64, ...)`` against a clean ``(4, 6, 3, 64, ...)`` and won. The
    ``C:/Users/*/`` segment is one the install search itself expands, so a digit
    in a home directory name was enough to select the older engine.
    """

    older = "C:/Users/user99/Downloads/Godot_v4.5-stable_win64/Godot_v4.5-stable_win64_console.exe"
    newer = "C:/Users/tutic/Downloads/Godot_v4.6.3-stable_win64/Godot_v4.6.3-stable_win64_console.exe"

    assert max([older, newer], key=local_tools._godot_candidate_key) == newer


def test_a_renamed_executable_still_ranks_by_its_install_folder():
    """The version survives an exe that was renamed.

    Reading it out of the file name alone would drop every install whose exe
    does not carry it, and ``godot.exe`` inside a ``Godot_v4.6.3-...`` folder is
    what a manual extract looks like. The folder name is the fallback, so it has
    to keep deciding.
    """

    renamed = "C:/Users/tutic/Downloads/Godot_v4.6.3-stable_win64/godot.exe"
    older = "C:/Users/tutic/Downloads/Godot_v4.6.1-stable_win64/Godot_v4.6.1-stable_win64.exe"

    assert max([renamed, older], key=local_tools._godot_candidate_key) == renamed


def test_a_directory_named_as_the_executable_does_not_answer_a_probe(monkeypatch, tmp_path):
    """Naming a folder is not naming a binary.

    The variable check was ``exists()``, so pointing ``GODOT_EXECUTABLE`` at the
    folder that holds Godot -- which is what the panel's own "set it to the
    Godot executable" reads like -- satisfied the probe. The panel then reported
    ``ready`` on a directory and the launch raised ``PermissionError``. All three
    engine variables share that check, so all three are exercised.
    """

    folder = tmp_path / "Godot_v4.6.3-stable_win64"
    folder.mkdir()

    for variable, resolver in (
        ("GODOT_EXECUTABLE", local_tools._find_godot),
        ("BLENDER_EXECUTABLE", local_tools._find_blender),
        ("UNREAL_EDITOR", local_tools._find_unreal),
    ):
        monkeypatch.setenv(variable, str(folder))
        answer = resolver()

        # A directory is never the answer. Whether the search then finds a real
        # engine or nothing at all is a property of the machine, not of this
        # guard, so both are accepted -- returning the folder is not.
        assert answer != str(folder), variable
        assert answer is None or Path(answer).is_file(), variable


def test_the_open_path_reports_a_target_it_cannot_launch(monkeypatch, tmp_path):
    """An unlaunchable target is a status, not a 500.

    ``open_manual_correction_target`` caught ``FileNotFoundError`` only, but that
    is one ``OSError`` among several and they all mean the same thing here: a
    directory where a binary was expected raises ``PermissionError`` from
    ``Popen``. It escaped the function, so ``POST /api/manual-correction/open``
    answered 500 instead of naming the problem. The resolver is stubbed to force
    that state, because the resolver's own half is pinned above.
    """

    folder = tmp_path / "Godot_v4.6.3-stable_win64"
    folder.mkdir()
    monkeypatch.setattr(local_tools, "_find_godot", lambda: str(folder))

    result = local_tools.open_manual_correction_target(
        target_id="godot",
        engine="Godot",
        confirmed_side_effects=True,
    )

    assert result["status"] == "unavailable"
    assert result["detail_key"] == "manualOpenUnavailable"
    assert result["detail"]


def test_every_detail_key_the_open_path_returns_exists_in_the_frontend(monkeypatch, tmp_path):
    """A ``detail_key`` the dictionary lacks renders as the raw key.

    ``FlowConsole`` calls ``t(result.detail_key)`` whenever it is present, and
    ``makeTranslator`` falls back to the key itself -- so a missing entry shows
    the user the string ``manualOpenUnavailable``. Three of the five keys this
    path can return were in that state. ``_launch`` is stubbed so the branch that
    reports success does not start an editor.
    """

    monkeypatch.setattr(local_tools, "_launch", lambda args: None)

    keys = {
        "planning": local_tools.open_manual_correction_target(
            target_id="planning", confirmed_side_effects=True
        )["detail_key"],
        "unknown target": local_tools.open_manual_correction_target(
            target_id="nonsense", confirmed_side_effects=True
        )["detail_key"],
        "no confirmation": local_tools.open_manual_correction_target(target_id="godot")["detail_key"],
        "launched": local_tools.open_manual_correction_target(
            target_id="godot", engine="Godot", confirmed_side_effects=True
        )["detail_key"],
    }

    monkeypatch.setattr(local_tools, "_find_godot", lambda: None)
    keys["missing binary"] = local_tools.open_manual_correction_target(
        target_id="godot", engine="Godot", confirmed_side_effects=True
    )["detail_key"]

    i18n = local_tools.REPO_ROOT.joinpath("apps/frontend/src/shared/i18n.ts").read_text(
        encoding="utf-8"
    )
    absent = sorted(key for key in keys.values() if f"{key}:" not in i18n)

    assert not absent, f"manual-correction keys missing from i18n.ts: {absent}"
