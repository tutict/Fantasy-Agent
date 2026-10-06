"""Persistent snapshot of what an orchestration pass did, per session.

The orchestrator itself is deliberately in-memory: `_outcomes` is what stops a
later pass replaying finished stages, and `_confirmed` is what stops it asking
the operator to approve the same stage twice. That is the right trade *within* a
process, and it has one cost -- restart throws both away. The board keeps the
session id in ``localStorage`` precisely so a reload can find its session, so
before this module existed a restarted Studio answered `found: false` to an id
it had itself written down.

``pipeline_state`` already persists half of this (``status`` / ``detail``, with
``refusals`` filed under ``logs``), which is why the gap looked smaller than it
is: the stage ledger the executor resumes from is a *different vocabulary* from
the nine fields a board card draws. It keeps two files on purpose:

1. ``pipeline_state.record_stage`` is a read-modify-write of one model. The
   executor writes it from the single-worker pool while an orchestration request
   runs on a FastAPI worker thread, so the two can interleave. One file means
   one side silently overwrites the other.
2. ``pipeline_state`` speaks the execution layer (``GODOT_STAGE_ORDER``,
   ``--from-stage``). Mirroring a board's nine fields into it would give one
   module two jobs.

So a snapshot may disagree with the stage ledger -- a crash between the two
writes leaves them so. That is accepted rather than transactional: resuming the
executor and reloading the board are separate decisions, and each is internally
consistent on its own.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field

from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.contracts import StrictModel
from fantasy_agent.path_safety import assert_safe_path_segment, resolve_workspace_path
from fantasy_agent.pipeline_state import peek_schema_version

logger = logging.getLogger(__name__)

ORCHESTRATION_STATE_FILENAME = "_orchestration_state.json"


class OrchestrationStageState(StrictModel):
    """Persistent mirror of one ``orchestrator.StageOutcome``.

    Every field here is read back by the board, so this is a mirror and not a
    summary: a field the snapshot does not carry comes back empty on a restored
    board while every test still passes. That is the bug this module exists to
    fix, one level down, so
    ``test_the_snapshot_carries_exactly_the_outcome_fields`` pins the field set
    against the dataclass and is not optional.
    """

    stage_id: str
    status: str
    detail: str = ""
    #: Tools the model was actually offered, after the whitelist and the grant.
    tools: list[str] = Field(default_factory=list)
    #: True when an agent was dispatched. False means zero turns were spent.
    dispatched: bool = False
    tool_calls: int = 0
    #: Stays ``refusals`` here. ``_record`` files it under ``logs`` for the
    #: execution ledger, which is a different vocabulary; renaming it on the way
    #: in would make the round trip lossy in a way nothing else would notice.
    refusals: list[str] = Field(default_factory=list)
    answer: str = ""
    #: Exit checks that ran *and passed*, in declared order.
    checks: list[str] = Field(default_factory=list)


class OrchestrationState(StrictModel):
    """One session's board state, as of the last stage that finished."""

    source: str = "fantasy-agent.orchestration-state"
    schema_version: str = "0.1"
    session_id: str
    engine: str = "godot"
    #: ``ProductionPipeline`` as a json dump, deliberately *not* the model. Plan
    #: schema drift then degrades to "no snapshot" at the one place that can
    #: report it, instead of failing to load a snapshot file at all. Ten of the
    #: fields a card draws (``title`` / ``depends_on`` / ``quality_gates`` /
    #: ``risks`` / ``exit_checks`` / ...) live only in the plan, so a snapshot
    #: without it renders the degenerate board this module is fixing.
    plan: dict[str, Any] = Field(default_factory=dict)
    stages: list[OrchestrationStageState] = Field(default_factory=list)
    #: Stage ids an operator approved, recorded by ``Orchestrator.confirm``.
    #: Restoring these redeems a click; nothing may ever *infer* them, or the
    #: gate in AGENTS.md ("the frontend must not make the confirmation") would
    #: be satisfied by a reconstruction rather than by a person.
    confirmed: list[str] = Field(default_factory=list)
    updated_at: str = ""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def state_path(
    session_id: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> Path:
    """Path of the snapshot file, kept inside the generated sandbox.

    ``session_id`` is checked as a *name*, not just as a path: it is the
    directory the snapshot lives in, and on Windows ``victim.`` and ``victim``
    are one directory. Containment alone cannot catch that, because the
    aliasing happens inside the filesystem.
    """

    assert_safe_path_segment(session_id, label="session_id")
    assert_safe_path_segment(engine_key, label="engine_key")
    relative = (
        f"generated/{engine_key}/sessions/{session_id}/{ORCHESTRATION_STATE_FILENAME}"
    )
    return resolve_workspace_path(
        relative,
        workspace_root=workspace_root,
        required_prefix=f"generated/{engine_key}",
    )


def load_state(
    session_id: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> OrchestrationState | None:
    """Read the snapshot, or None when there is nothing usable.

    Same degradation rule as ``pipeline_state.load_state``: a snapshot this
    cannot read is reported as absent, never partially applied. A half-restored
    board would show some stages `done` and silently re-run others, which is
    worse than an empty board that admits it knows nothing.
    """

    path = state_path(
        session_id, engine_key=engine_key, workspace_root=workspace_root
    )
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # A session that has not run yet, not a fault.
        return None
    except (OSError, ValueError) as exc:
        # The ``ValueError`` is ``UnicodeDecodeError`` from the read, not the
        # JSON: splitting the read out of the parse would otherwise let a
        # non-text file escape every ``except`` here.
        logger.warning("could not read orchestration snapshot at %r: %s", path, exc)
        return None
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        logger.warning(
            "orchestration snapshot at %r is not valid JSON (schema_version %r): %s",
            path,
            peek_schema_version(raw),
            exc,
        )
        return None
    if not isinstance(payload, dict):
        logger.warning("orchestration snapshot at %r is not an object", path)
        return None
    try:
        snapshot = OrchestrationState.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - a bad snapshot must not break a run
        logger.warning(
            "orchestration snapshot at %r does not validate (schema_version %r): %s",
            path,
            # Already a dict here, so the value is read straight off it rather
            # than re-parsing the raw text -- and formatted as a string because
            # a snapshot may carry any JSON type under that key.
            peek_schema_version(raw),
            exc,
        )
        return None
    if snapshot.session_id != session_id:
        # Two ids that differ mean the file was copied or the id was reused
        # across a rename. Adopting it would attach another session's approvals.
        logger.warning(
            "orchestration snapshot at %r holds session %r, not %r",
            path,
            snapshot.session_id,
            session_id,
        )
        return None
    if engine_key != snapshot.engine:
        # The path already encodes the engine, so this only fires on a hand-made
        # file. Explicit beats "it must be fine" -- the snapshot carries
        # approvals, and approvals are the one thing that must not migrate.
        logger.warning(
            "orchestration snapshot at %r is for engine %r, not %r",
            path,
            snapshot.engine,
            engine_key,
        )
        return None
    return snapshot


def save_state(snapshot: OrchestrationState, *, workspace_root: Path | str) -> Path:
    """Write the snapshot atomically and stamp it.

    Atomic because a half-written snapshot is worse than a missing one: a
    missing snapshot degrades to an empty board, a half-written one is
    indistinguishable from a session that never ran.
    """

    snapshot.updated_at = _now()
    path = state_path(
        snapshot.session_id,
        engine_key=snapshot.engine,
        workspace_root=workspace_root,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(
        path,
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
    )
    return path