"""Tests for the per-session orchestration snapshot."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from fantasy_agent import orchestration_state
from fantasy_agent.orchestration_state import (
    OrchestrationStageState,
    OrchestrationState,
    load_state,
    save_state,
    state_path,
)
from fantasy_agent.path_safety import WorkspacePathError

REPO_ROOT = Path(__file__).resolve().parents[1]


def _snapshot(session_id: str = "snap") -> OrchestrationState:
    return OrchestrationState(
        session_id=session_id,
        engine="godot",
        stages=[
            OrchestrationStageState(
                stage_id="godot_quick_play",
                status="done",
                detail="built",
                tools=["godot_mcp"],
                dispatched=True,
                tool_calls=3,
                refusals=["godot_mcp refused: not allowed"],
                answer="project is playable",
                checks=["godot_mcp.validate"],
            )
        ],
        confirmed=["approval_gate"],
    )


def test_the_snapshot_carries_exactly_the_outcome_fields():
    """The mirror must not fall behind the dataclass it mirrors.

    This is the whole risk of the module: `StageOutcome` grows a tenth field,
    nobody adds it here, and a restored board silently shows one field less --
    with every test still green. `waiting` is a property rather than a field,
    so `dataclasses.fields` is the right comparison and set equality is the
    right shape (a subset assertion would pass just as happily on a duplicate).
    """

    from fantasy_agent.orchestrator import StageOutcome

    mirrored = set(OrchestrationStageState.model_fields)
    source = {entry.name for entry in dataclasses.fields(StageOutcome)}

    assert mirrored == source, (
        "the snapshot mirrors StageOutcome but has drifted from it: "
        f"only in the dataclass {sorted(source - mirrored)}, "
        f"only in the mirror {sorted(mirrored - source)}"
    )


def test_every_snapshot_field_reaches_the_frontend_card():
    """Cross-language half of the same guard.

    `cardsFromSession` maps field by field rather than spreading, so an
    unmapped field is dropped silently -- the Python side would be perfectly
    consistent and the board would still be missing a column. The check is on
    the interface, not on the mapping function, because the interface is what
    the mapping is written against.
    """

    source = (REPO_ROOT / "apps/frontend/src/shared/types.ts").read_text(
        encoding="utf-8"
    )
    block = re.search(
        r"export interface OrchestrationStageCard \{(?P<body>.*?)\n\}",
        source,
        re.DOTALL,
    )
    assert block is not None, "OrchestrationStageCard is gone from types.ts"
    declared = set(re.findall(r"^\s{2}(\w+)\??:", block.group("body"), re.MULTILINE))

    missing = sorted(set(OrchestrationStageState.model_fields) - declared)

    assert not missing, (
        f"the snapshot carries {missing} but the board's card type does not "
        "declare them, so cardsFromSession would drop them"
    )


def test_a_snapshot_round_trips_every_field(tmp_path: Path):
    """Write then read must give back all nine fields, per stage."""

    written = save_state(_snapshot(), workspace_root=tmp_path)

    assert written == state_path("snap", engine_key="godot", workspace_root=tmp_path)
    loaded = load_state("snap", workspace_root=tmp_path)

    assert loaded is not None
    assert loaded.stages[0].model_dump() == written_payload_stage()
    # `refusals` is the field name on both sides. `_record` files the same list
    # under `logs` for the execution ledger, and that rename must not leak into
    # the round trip -- a snapshot that came back with empty `refusals` would
    # look exactly like a run that refused nothing.
    assert loaded.stages[0].refusals == ["godot_mcp refused: not allowed"]
    assert loaded.confirmed == ["approval_gate"]
    assert loaded.updated_at != ""


def written_payload_stage() -> dict:
    return {
        "stage_id": "godot_quick_play",
        "status": "done",
        "detail": "built",
        "tools": ["godot_mcp"],
        "dispatched": True,
        "tool_calls": 3,
        "refusals": ["godot_mcp refused: not allowed"],
        "answer": "project is playable",
        "checks": ["godot_mcp.validate"],
    }


def test_a_snapshot_is_written_atomically(tmp_path: Path):
    """A refused publish must leave the previous snapshot readable.

    Same reason as the ledger: the caller cannot tell a half-written snapshot
    from "this session never ran", and both cost the operator a full board.
    """

    save_state(_snapshot(), workspace_root=tmp_path)
    second = _snapshot()
    second.stages[0].answer = "second pass"

    def _boom(src, dst):
        raise OSError(13, "publish refused")

    original = orchestration_state.write_atomic
    orchestration_state.write_atomic = _boom
    try:
        try:
            save_state(second, workspace_root=tmp_path)
        except OSError:
            pass
        else:  # pragma: no cover - the seam must actually fail
            raise AssertionError("the refused publish was supposed to raise")
    finally:
        orchestration_state.write_atomic = original

    loaded = load_state("snap", workspace_root=tmp_path)
    assert loaded is not None
    assert loaded.stages[0].answer == "project is playable"
    assert list(tmp_path.rglob("*.tmp")) == []


def test_a_snapshot_that_belongs_to_another_session_is_not_adopted(tmp_path: Path):
    """A copied or renamed file must not hand its approvals to a new id."""

    save_state(_snapshot("original"), workspace_root=tmp_path)

    assert load_state("different-id", workspace_root=tmp_path) is None


def test_a_snapshot_from_another_engine_is_not_adopted(tmp_path: Path):
    """The snapshot carries approvals, and approvals are the one thing that
    must not migrate between engines.

    The path already encodes the engine, so this only fires on a hand-made
    file -- which is exactly the case worth refusing loudly.
    """

    path = state_path("snap", engine_key="godot", workspace_root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _snapshot().model_dump(mode="json")
    payload["engine"] = "unreal"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_state("snap", workspace_root=tmp_path) is None


def test_an_unreadable_snapshot_degrades_to_absent(tmp_path: Path):
    """Truncated, non-object, wrong-shape and missing all mean the same thing.

    `None` is the answer the callers branch on, and a partial restore would be
    worse than none: some cards `done`, others silently re-run.
    """

    path = state_path("snap", engine_key="godot", workspace_root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("{not json", encoding="utf-8")
    assert load_state("snap", workspace_root=tmp_path) is None

    path.write_text("[]", encoding="utf-8")
    assert load_state("snap", workspace_root=tmp_path) is None

    path.write_text(json.dumps({"session_id": "snap", "stages": "nope"}), encoding="utf-8")
    assert load_state("snap", workspace_root=tmp_path) is None

    assert load_state("never-ran", workspace_root=tmp_path) is None


def test_the_snapshot_path_stays_inside_the_engine_sandbox(tmp_path: Path):
    """A session id that climbs out of `generated/` must be refused.

    The id comes from the browser, so this is the guard that keeps a crafted id
    from writing wherever it likes.
    """

    for hostile in ("../../escape", "..\\escape", "/etc/passwd", "C:/Windows/x"):
        try:
            state_path(hostile, engine_key="godot", workspace_root=tmp_path)
        except WorkspacePathError as exc:
            # Any refusal will do, but name the shape: this suite also refuses
            # ids that are perfectly safe as paths, so a reader should be able
            # to tell which rule did the refusing.
            assert label_of(exc) == "session_id", exc
        else:  # pragma: no cover - the guard must actually fire
            raise AssertionError(f"{hostile!r} resolved instead of being refused")


def label_of(exc: Exception) -> str:
    """Which rule refused: `session_id` (the name rule) or the prefix rule."""

    return "session_id" if str(exc).startswith("session_id") else "sandbox"


def test_a_session_id_that_the_filesystem_would_rewrite_is_refused(tmp_path: Path):
    """Containment is not enough, because the aliasing happens *below* it.

    On Windows a trailing dot or space is stripped by the filesystem, so
    `sessions/victim.` and `sessions/victim` are one directory -- and
    `resolve_workspace_path` resolves `victim.` happily, reporting success,
    because nothing has been written yet. A snapshot written under the aliased
    name therefore lands on another session's directory, overwriting the
    approvals it stored.

    These ids are asserted by *what Windows does with them*, so the list is
    named rather than generated: `victim.` and `victim ` are the two aliases
    the filesystem collapses, and a newline is here because it is the same
    class of problem one level up (an id that becomes two log records).
    """

    for hostile, because in (
        ("victim.", "a trailing dot is stripped by Windows"),
        ("victim ", "a trailing space is stripped by Windows"),
        ("a\nb", "a newline splits one log record into two"),
        ("a/b", "a separator would add a path segment"),
        ("", "an empty name is not a directory"),
        ("a" * 65, "longer than the length Windows will give back"),
        (".hidden", "a name starting with a dot is not a session id"),
    ):
        try:
            state_path(hostile, engine_key="godot", workspace_root=tmp_path)
        except WorkspacePathError as exc:
            assert "session_id" in str(exc), f"{hostile!r}: {exc}"
        else:  # pragma: no cover - the guard must actually fire
            raise AssertionError(f"{hostile!r} resolved instead of being refused ({because})")


@pytest.mark.skipif(
    os.name != "nt",
    reason="the premise is an NTFS fact: ext4/APFS keep 'victim.' and 'victim' "
    "as two directories, so there is nothing to prove there",
)
def test_the_two_ids_windows_would_collapse_really_do_collapse(tmp_path: Path):
    """Without this, the guard above is guarding against nothing.

    The premise is a filesystem fact, not an assumption: if a future Windows or
    Python stopped stripping the trailing dot, the id test would still pass
    while the aliasing it exists to stop had quietly stopped happening -- and a
    guard protecting against a condition that no longer exists is worse than no
    guard, because it reads as coverage. So assert the condition *is* still
    true, here, on this machine.

    Creating ``victim.`` and then finding ``victim`` already there **is** the
    proof: the first call made the second one fail with ``FileExistsError``.

    The skip is the honest shape of that promise: the guard exists for the
    filesystem that does the collapsing, so the proof runs where the
    collapsing happens. On Linux the premise is not merely unproven, it is
    false, and an assertion written as if it were true there is a lie that
    only ever ran green because nobody ran the suite on Linux.
    """

    sessions = tmp_path / "sessions"
    aliased = sessions / "victim."
    plain = sessions / "victim"

    aliased.mkdir(parents=True)

    assert plain.is_dir(), "Windows did not collapse 'victim.' onto 'victim'"
    assert aliased.resolve() == plain.resolve()
    assert list(sessions.iterdir()) == [plain], (
        f"the two names did not collapse onto one directory: "
        f"{sorted(entry.name for entry in sessions.iterdir())}"
    )


def test_an_unusable_session_id_cannot_forge_a_log_record(tmp_path: Path):
    """The reason for the newline case above, asserted on the log itself.

    `load_state` is reached with a browser-supplied id, and its degradation
    warnings quote the path -- so at `%s` an id carrying a newline writes a
    second line that no reader would attribute to a request. Now that the id
    is refused before a path is built, the warning is about the id and is
    rendered with `%r`.
    """

    logging.basicConfig()
    forged = "snap\n2026-01-01 INFO root: session approved for all stages"
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    logger = logging.getLogger("fantasy_agent.orchestration_state")
    logger.addHandler(handler)
    try:
        try:
            state_path(forged, workspace_root=tmp_path)
        except WorkspacePathError:
            pass
        else:  # pragma: no cover - the guard must actually fire
            raise AssertionError("the forged id resolved")
    finally:
        logger.removeHandler(handler)

    assert not records, "state_path warned instead of refusing; the id is not a path problem"
    # And the refusal message itself must not carry a raw newline either.
    try:
        state_path(forged, workspace_root=tmp_path)
    except WorkspacePathError as exc:
        assert "\n" not in str(exc)
        assert "\\n" in str(exc), f"the id was not repr'd: {exc}"
    else:  # pragma: no cover - the guard must actually fire
        raise AssertionError("the forged id resolved")


def test_the_engine_key_is_checked_as_a_name_too(tmp_path: Path):
    """`engine_key` reaches the same path template, so it gets the same rule.

    It is currently server-chosen, but the GET endpoint takes it as a query
    parameter -- so it is caller-controlled today, and the prefix check alone
    would let `engine=godot/../unreal` through the sandbox.
    """

    for hostile in ("godot/../unreal", "godot.", "godot\x00"):
        try:
            state_path("snap", engine_key=hostile, workspace_root=tmp_path)
        except WorkspacePathError:
            continue
        else:  # pragma: no cover - the guard must actually fire
            raise AssertionError(f"engine_key={hostile!r} resolved")


def test_the_snapshot_models_reject_unknown_fields():
    """A hand-edited snapshot with an extra key is refused, not merged.

    This is what makes "restore goes through `confirm()`" worth anything: the
    file cannot smuggle in a field the model does not know about.
    """

    payload = _snapshot().model_dump(mode="json")
    payload["stages"][0]["approved_by_operator"] = True

    try:
        OrchestrationState.model_validate(payload)
    except ValidationError:
        return
    raise AssertionError("a snapshot with an unknown field was accepted")