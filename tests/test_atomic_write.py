"""Tests for the shared atomic write.

The guarantee under test is not "a temporary file is used" -- it is that a
reader never observes a half-written file. Every test here therefore breaks
the publish step and asserts the *old* bytes are still readable, because that
is the failure a caller actually experiences: a settings file that no longer
parses degrades to "not configured" and takes the user's API key with it.
"""

from __future__ import annotations

import errno
import json
import os
import tempfile
from pathlib import Path

import pytest

from fantasy_agent import atomic_write
from fantasy_agent.atomic_write import write_atomic


def _raise_os_error(code: int, message: str):
    def _boom(*args, **kwargs):
        raise OSError(code, message)

    return _boom


def test_a_failed_publish_leaves_the_previous_file_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The definition of the guarantee: crash before the rename, old file survives."""

    target = tmp_path / "state.json"
    write_atomic(target, '{"stage": "old"}')

    def _boom(src, dst):
        raise OSError(13, "publish refused")

    monkeypatch.setattr(atomic_write.os, "replace", _boom)
    with pytest.raises(OSError):
        write_atomic(target, '{"stage": "new"}')

    assert target.read_text(encoding="utf-8") == '{"stage": "old"}'
    assert list(tmp_path.glob("*.tmp")) == []


def test_a_failed_temp_write_leaves_no_residue_no_damage_and_no_leaked_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Failing before the descriptor is handed over must still close it.

    The descriptor belongs to the caller until ``os.fdopen`` takes it over, and
    a leak per failed write is the cost that would make the next caller bypass
    the helper. Asserted directly on the descriptor rather than by counting
    process handles: a snapshot-style check that quietly degrades to comparing
    two empty sets would pass on a real leak.
    """

    target = tmp_path / "state.json"
    write_atomic(target, "old")

    real_mkstemp = tempfile.mkstemp
    handed_out: dict[str, int] = {}

    def _spy_mkstemp(*args, **kwargs):
        fd, name = real_mkstemp(*args, **kwargs)
        handed_out["fd"] = fd
        return fd, name

    monkeypatch.setattr(atomic_write.tempfile, "mkstemp", _spy_mkstemp)
    monkeypatch.setattr(
        atomic_write.os, "fdopen", _raise_os_error(28, "no space left on device")
    )
    with pytest.raises(OSError):
        write_atomic(target, "new")

    fd = handed_out["fd"]
    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob("*.tmp")) == []
    # EBADF ("bad file descriptor") is the proof it was closed: the descriptor
    # number is no longer ours to read.
    with pytest.raises(OSError) as closed:
        os.fstat(fd)
    assert closed.value.errno == errno.EBADF


def test_the_publish_goes_through_a_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The mechanism: a sibling temp file, flushed, then renamed over the target.

    A spy rather than an observation, and deliberately so -- the effect of
    fsync is not observable from inside a test without a crash, and the
    concurrent-reader formulation of that would be flaky rather than stronger.
    What is pinned here is the *mechanism* (temp file -> fsync -> rename), not
    the durability result it buys. ``test_a_failed_publish_leaves_the_previous_
    file_intact`` is the one that carries the guarantee.
    """

    target = tmp_path / "state.json"
    order: list[tuple[str, object]] = []
    real_replace = os.replace
    real_fsync = os.fsync

    def _spy_replace(src, dst):
        order.append(("replace", (Path(src).parent, Path(dst))))
        return real_replace(src, dst)

    def _spy_fsync(fd):
        order.append(("fsync", fd))
        return real_fsync(fd)

    monkeypatch.setattr(atomic_write.os, "replace", _spy_replace)
    monkeypatch.setattr(atomic_write.os, "fsync", _spy_fsync)

    assert write_atomic(target, "payload") == target

    kinds = [name for name, _ in order]
    assert "fsync" in kinds, "the temp file must be flushed before it is published"
    assert kinds.index("fsync") < kinds.index("replace"), (
        "flushing after the rename would leave the new name pointing at "
        "unwritten bytes"
    )
    # os.replace is only atomic within one volume: a temp file elsewhere would
    # quietly stop qualifying the moment the workspace is on another drive.
    temp_parent, target_path = order[kinds.index("replace")][1]
    assert temp_parent == target_path.parent
    assert target.read_text(encoding="utf-8") == "payload"


def test_a_rejected_second_write_still_leaves_a_parseable_file(tmp_path: Path):
    """The settings case, at the level a user would notice.

    ``load_settings`` answers a parse failure with default settings, so a
    truncated file is indistinguishable from "never configured". Keeping the
    previous bytes parseable is what stops an interrupted save from looking
    like a lost key.
    """

    target = tmp_path / "llm-api.json"
    write_atomic(target, json.dumps({"api_key": "old-key"}))
    write_atomic(target, json.dumps({"api_key": "new-key"}))

    assert json.loads(target.read_text(encoding="utf-8"))["api_key"] == "new-key"
    assert list(tmp_path.glob("*.tmp")) == []
