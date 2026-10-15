"""The record a person's decision for a human gate leaves on disk.

A decided gate is not only a status. The stage's ``artifacts`` name a decision
record, and a stage that reads ``done`` while nothing was written where it said
it would write is exactly the shape G-03 spent a bug on: the playtest report's
path was recorded as a stage artifact by a session that never wrote it, and the
board showed a file nobody had produced. So the decision is durable here, in
the session's own directory, next to the orchestration snapshot -- a decision
and the board state it changes are one session's facts, and splitting them
across two trees would let one survive a cleanup the other did not.

The write is atomic for the same reason the approval manifest's is: this file
is read back to decide whether a run may proceed, and a half-written record
would parse as a missing gate rather than as a failed save.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.contracts import HumanDecisionRecord
from fantasy_agent.path_safety import (
    WorkspacePathError,
    assert_safe_path_segment,
    resolve_workspace_path,
)

#: Inside the session directory, next to ``_orchestration_state.json``.
DECISION_RECORD_FILENAME = "human-decision.yaml"


def decision_record_path(
    session_id: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> Path:
    """Where this session's gate decision lives, confined to the session dir.

    Both segments are checked as *names*, not just as path pieces: on Windows
    ``victim.`` and ``victim`` are one directory, and the aliasing happens
    inside the filesystem where containment alone cannot see it.
    """

    assert_safe_path_segment(session_id, label="session_id")
    assert_safe_path_segment(engine_key, label="engine_key")
    relative = (
        f"generated/{engine_key}/sessions/{session_id}/{DECISION_RECORD_FILENAME}"
    )
    return resolve_workspace_path(
        relative,
        workspace_root=workspace_root,
        required_prefix=f"generated/{engine_key}",
    )


def write_decision_record(
    session_id: str,
    stage_id: str,
    decision: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> Path:
    """Record one decision and return the path it was written to."""

    record = HumanDecisionRecord(
        session_id=session_id,
        stage_id=stage_id,
        decision=decision,
        decided_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    path = decision_record_path(
        session_id, engine_key=engine_key, workspace_root=workspace_root
    )
    write_atomic(
        path,
        yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
    )
    return path


def load_decision_record(
    session_id: str,
    *,
    engine_key: str = "godot",
    workspace_root: Path | str,
) -> HumanDecisionRecord | None:
    """Read the record back, or None when there is nothing usable.

    Same degradation rule as the snapshot loaders: an unreadable record is
    reported as absent rather than partially applied, because a half-read
    decision would read as "nobody decided" on a session that did.
    """

    try:
        path = decision_record_path(
            session_id, engine_key=engine_key, workspace_root=workspace_root
        )
    except WorkspacePathError:
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # A session whose gate has not decided yet, not a fault.
        return None
    except (OSError, ValueError):
        # ``ValueError`` is ``UnicodeDecodeError`` from the read, not the YAML:
        # splitting the read out of the parse would otherwise let a non-text
        # file escape both handlers.
        return None
    try:
        payload = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return HumanDecisionRecord.model_validate(payload)
    except Exception:  # noqa: BLE001 - a bad record is absent, never fatal
        return None
