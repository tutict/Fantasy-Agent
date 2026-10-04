"""Reading hand edits back out of a generated project.

The console sends operators out to Blender, ComfyUI and the Godot editor, and
whatever they change over there lives only in those tools. These tests pin the
way back, and they are written around one rule: **a hand edit is the operator's
work, so this module reports and never acts.** A test that only checked "the
scan returns something" would pass against an implementation that quietly
rewrote the project, which is the one behaviour that must not exist.

The load-bearing cases are the negative ones -- an untouched project reporting
nothing, and an edit to one number not dragging fifty untouched neighbours
along with it. Both are the failure modes that make a report worthless: noise
teaches the operator to ignore it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fantasy_agent.corrections import (
    ANCHOR_RE,
    MANIFEST_FILENAME,
    SPEC_BACKED_ANCHORS,
    extract_tweaks,
    file_sha256,
    inspect_corrections,
    summarize_corrections,
)

PLAYER_SCRIPT = """extends CharacterBody3D

@export var move_speed := 8.0        # [MOVE_SPEED]
@export var max_hp := 5# [PLAYER_HP]
@export var jump_velocity := 6.0     # [JUMP_VELOCITY]
@export var gravity := 18.0          # [GRAVITY]

# [SPRINT] hold to accelerate
func _physics_process(delta: float) -> void:
    velocity.x = move_speed
"""


def _project(root: Path, *, script_text: str = PLAYER_SCRIPT, record_hashes: bool = True) -> Path:
    """A minimal generated project with the manifest this module reads."""

    project = root / "generated" / "godot" / "demo"
    scripts = project / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    player = scripts / "player_controller.gd"
    player.write_text(script_text, encoding="utf-8")
    (project / "scenes").mkdir(parents=True, exist_ok=True)
    (project / "scenes" / "main.tscn").write_text("[node name=\"Main\"]\n", encoding="utf-8")

    player_rel = player.relative_to(root).as_posix()
    scene_rel = (project / "scenes" / "main.tscn").relative_to(root).as_posix()
    manifest = {
        "schema_version": "0.1",
        "project_name": "Demo",
        "script_paths": [player_rel],
        "scene_paths": [scene_rel],
        "artifact_anchors": {player_rel: {"MOVE_SPEED": 8.0, "PLAYER_HP": 5, "JUMP_VELOCITY": 6.0, "GRAVITY": 18.0}},
    }
    if record_hashes:
        manifest["artifact_sha256"] = {
            player_rel: file_sha256(player),
            scene_rel: file_sha256(project / "scenes" / "main.tscn"),
        }
    (project / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return project


def _rel(project: Path, root: Path) -> str:
    return project.relative_to(root).as_posix()


def test_an_untouched_project_reports_nothing(tmp_path):
    project = _project(tmp_path)

    report = inspect_corrections(_rel(project, tmp_path), workspace_root=tmp_path)

    assert report.manifest_found
    assert report.drifted == []
    assert report.recoverable == []
    assert report.engine_only == []
    assert any("No hand edits" in note for note in report.notes)


def test_a_changed_file_is_reported_as_drifted(tmp_path):
    project = _project(tmp_path)
    player = project / "scripts" / "player_controller.gd"
    player.write_text(PLAYER_SCRIPT.replace("# [SPRINT]", "# edited note\n\n# [SPRINT]"), encoding="utf-8")

    report = inspect_corrections(_rel(project, tmp_path), workspace_root=tmp_path)

    assert [item.path for item in report.drifted] == [
        _rel(project / "scripts" / "player_controller.gd", tmp_path)
    ]
    assert report.drifted[0].kind == "script"


def test_editing_one_value_does_not_report_its_neighbours(tmp_path):
    """The load-bearing case.

    A hand edit leaves every other line in the file intact. Filtering on the
    file hash alone would call all fifty anchors edited and bury the one
    number the operator actually touched.
    """

    project = _project(tmp_path)
    player = project / "scripts" / "player_controller.gd"
    player.write_text(PLAYER_SCRIPT.replace("move_speed := 8.0", "move_speed := 11.5"), encoding="utf-8")

    report = inspect_corrections(_rel(project, tmp_path), workspace_root=tmp_path)

    assert [item.anchor for item in report.recoverable] == ["MOVE_SPEED"]
    assert report.recoverable[0].value == 11.5
    assert report.recoverable[0].generated_value == 8.0
    assert report.engine_only == []


def test_a_value_with_no_dsl_home_is_reported_as_unrecoverable(tmp_path):
    project = _project(tmp_path)
    player = project / "scripts" / "player_controller.gd"
    player.write_text(
        PLAYER_SCRIPT.replace("jump_velocity := 6.0", "jump_velocity := 9.25"), encoding="utf-8"
    )

    report = inspect_corrections(_rel(project, tmp_path), workspace_root=tmp_path)

    assert [item.anchor for item in report.engine_only] == ["JUMP_VELOCITY"]
    assert report.engine_only[0].spec_field == ""
    assert report.recoverable == []
    assert any("nowhere to write them back" in note for note in report.notes), (
        "an edit that cannot be saved has to say so, or the operator assumes it is safe"
    )


def test_an_anchor_with_no_recorded_baseline_is_reported_as_unverified(tmp_path):
    """No baseline is not evidence of "unchanged".

    The manifest records the values a build wrote. An anchor it does not know
    about has no baseline at all. Skipping it silently would call it unchanged
    on the strength of nothing -- the same mistake as reporting a missing hash
    as "no drift".

    The line is appended *after* the manifest was written, so the file counts as
    hand-edited and the scan actually looks inside it.
    """

    project = _project(tmp_path)
    player = project / "scripts" / "player_controller.gd"
    player.write_text(
        player.read_text(encoding="utf-8") + "\n@export var stamina_max := 4.0  # [STAMINA_MAX]\n",
        encoding="utf-8",
    )

    _recoverable, engine_only = extract_tweaks(_rel(project, tmp_path), workspace_root=tmp_path)

    unverified = [item for item in engine_only if item.anchor == "STAMINA_MAX"]
    assert len(unverified) == 1, "an anchor with no baseline must not be silently skipped"
    assert unverified[0].generated_value is None


def test_a_behaviour_comment_is_not_mistaken_for_an_editable_value(tmp_path):
    """`# [SPRINT] hold to accelerate` is prose; only declarations are values."""

    project = _project(tmp_path)
    player = project / "scripts" / "player_controller.gd"
    player.write_text(PLAYER_SCRIPT.replace("# [SPRINT]", "# [SPRINT] tweaked by hand"), encoding="utf-8")

    _recoverable, engine_only = extract_tweaks(_rel(project, tmp_path), workspace_root=tmp_path)

    assert engine_only == [], "a comment edit is a drift, not a tunable"


def test_a_project_without_a_recorded_hash_is_not_called_unchanged(tmp_path):
    project = _project(tmp_path, record_hashes=False)

    report = inspect_corrections(_rel(project, tmp_path), workspace_root=tmp_path)

    # Both artifacts (script and scene) lack a hash, and both must be reported:
    # a project generated before hashing existed cannot be vouched for either.
    assert {item.kind for item in report.drifted} == {"script", "scene"}
    assert all(item.hash_unknown for item in report.drifted)
    assert any("predates hash recording" in note for note in report.notes)


def test_a_directory_with_no_manifest_says_so_instead_of_pretending(tmp_path):
    project = tmp_path / "generated" / "godot" / "handmade"
    project.mkdir(parents=True)

    report = inspect_corrections(project.relative_to(tmp_path).as_posix(), workspace_root=tmp_path)

    assert not report.manifest_found
    assert report.drifted == []
    assert any("No handoff manifest" in note for note in report.notes)


def test_a_manifest_pointing_outside_the_workspace_is_refused(tmp_path):
    """The manifest is a file on disk; a hand edit could point it anywhere."""

    project = _project(tmp_path)
    manifest_path = project / MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["script_paths"] = ["../../../outside.gd"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    _recoverable, engine_only = extract_tweaks(_rel(project, tmp_path), workspace_root=tmp_path)

    assert engine_only == [], "a path escaping the workspace is not read"


def test_the_anchor_pattern_survives_the_alignment_it_is_pasted_from(tmp_path):
    """The real generator aligns its comments in columns; the pattern must not
    depend on a fixed number of spaces."""

    aligned = "extends CharacterBody3D\n@export var move_speed := 8.0          # [MOVE_SPEED]\n"
    assert ANCHOR_RE.search(aligned)
    assert ANCHOR_RE.search("@export var move_speed := -1.5  # [MOVE_SPEED]"), (
        "a negative tuning value is a legitimate edit"
    )


def test_every_spec_backed_anchor_names_a_real_spec_field():
    for anchor, spec_field in SPEC_BACKED_ANCHORS.items():
        assert spec_field.startswith("numeric."), (
            f"{anchor} claims {spec_field}, which is not a numeric field"
        )


def test_the_summary_counts_all_three_kinds(tmp_path):
    project = _project(tmp_path)
    player = project / "scripts" / "player_controller.gd"
    player.write_text(
        PLAYER_SCRIPT.replace("move_speed := 8.0", "move_speed := 11.5").replace(
            "gravity := 18.0", "gravity := 24.0"
        ),
        encoding="utf-8",
    )

    text = summarize_corrections(inspect_corrections(_rel(project, tmp_path), workspace_root=tmp_path))

    assert "1 changed file(s)" in text
    assert "1 value(s) writable back to the spec" in text
    assert "1 engine-only value(s)" in text


def test_the_endpoint_refuses_a_path_outside_the_workspace():
    module = _load_studio_app()
    with pytest.raises(Exception) as excinfo:
        module.corrections_inspect("../../escape")
    assert getattr(excinfo.value, "status_code", None) == 400


def test_the_endpoint_needs_a_project_directory():
    module = _load_studio_app()
    with pytest.raises(Exception) as excinfo:
        module.corrections_inspect("   ")
    assert getattr(excinfo.value, "status_code", None) == 400


def _load_studio_app():
    import importlib.util
    import sys

    root = Path(__file__).resolve().parents[1]
    if str(root / "apps" / "studio") not in sys.path:
        sys.path.insert(0, str(root / "apps" / "studio"))
    spec = importlib.util.spec_from_file_location(
        "studio_main_for_corrections", root / "apps" / "studio" / "app" / "main.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
