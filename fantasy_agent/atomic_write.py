"""Whole-file replacement that a reader never sees half of.

Every write in this repository used to be a bare ``Path.write_text``. That is
fine until the process dies mid-write: a settings file truncated to half its
JSON no longer parses, and every loader in the tree answers a parse failure by
degrading rather than by complaining. The user-visible form of that is a saved
API key silently becoming "not configured" because the save was interrupted
once.

This module is the one way to write a file that a later *decision* depends on.
It writes a sibling temporary file, flushes it to the platter, and then renames
it over the target -- so a concurrent reader sees either the old bytes or the
new ones, never a prefix.

What it deliberately does NOT cover
----------------------------------

This section is the *argument* for the exclusions; the other two places that
have to stay in sync are ``process_runner._truncate``'s comment (the on-site
reminder, for whoever edits that function) and AGENTS.md's durability section
(the rule list). Change one, read all three.

**``mcp_bridge._write_text`` and the artifact writes in ``executor.py``.** Not
an oversight -- measured, on this machine:

    replace-while-open:  FAILED PermissionError (13, '拒绝访问。')
    write_text-while-open: OK

``process_runner._pump`` holds engine log files open with ``path.open("a")``
for the life of the subprocess, and ``godot_mcp`` / ``unreal_mcp`` /
``blender_mcp`` / ``comfyui_mcp`` then write *the same two paths* through
``_write_text``. The pump's ``finally`` closes the handle on the normal path,
but ``run_streaming`` returns after ``pump.join(timeout=PUMP_JOIN_TIMEOUT)`` --
a join that is allowed to time out. In that window the handle is still open and
an atomic replace raises. Routing the bridges through here would therefore turn
a slow engine log write into a failed tool call.

It would also buy nothing: an artifact is only torn when the process dies
*during* its write, and by then the run is dead and a re-run rewrites the same
files. It is not a decision input. If a torn artifact ever does cause a real
failure (Godot import reading half a ``main.tscn``), the right fix is an
engine-side check that reads the artifact back -- not an ``fsync`` on 40 call
sites.

**``process_runner``'s streaming logs.** Atomic append would mean a
read-modify-write of the whole log per line -- quadratic -- and replacing the
file changes its inode, which breaks the ``tail -f`` over a live run that
``run_streaming``'s docstring explicitly promises.

Why there is no checksum here
-----------------------------

``os.replace`` removes the only corruption source that actually occurs in
practice (a crash during a write). A checksum would then trade a rare
half-written file for a rare *silent* full replay, because the loaders answer
"unreadable" the same way they answer "corrupt" -- and the user cannot tell
those apart. Adding one would make the expensive outcome more likely and less
diagnosable. Backing files would need a retention policy and a tested restore
path, in exchange for a risk the rename already covers.

The readable half of durability is therefore not a checksum but a log line:
see the ``logger.warning`` calls next to the loaders that degrade.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

__all__ = ["write_atomic"]


def write_atomic(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Write ``text`` to ``path`` so a reader sees the old or the new file.

    Returns ``path`` so callers can chain.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    # Same directory on purpose: os.replace is only atomic within one volume,
    # and a temp file in the system temp dir would silently stop qualifying
    # the moment the workspace lives on another drive.
    handle, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f"{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    # fdopen takes ownership of the descriptor on success. Until then it is
    # still ours, and the failure path below has to close it -- a leaked handle
    # per failed write is exactly the kind of cost that makes a helper get
    # bypassed for being "slow".
    stream = None
    try:
        try:
            stream = os.fdopen(handle, "w", encoding=encoding)
            handle = -1
            stream.write(text)
            stream.flush()
            # Without this the bytes may still be in the OS cache when the
            # rename lands, and a power cut can leave the name pointing at
            # nothing.
            os.fsync(stream.fileno())
        finally:
            if stream is not None:
                stream.close()
            elif handle != -1:
                with contextlib.suppress(OSError):
                    os.close(handle)
        os.replace(tmp, path)
        _fsync_directory(path.parent)
    except BaseException:
        # A leftover ".tmp" is the visible sign of a failed write, so it goes
        # away with the failure -- on every path, not just a refused rename,
        # because a half-written temp file is the residue a reader sees in
        # the directory listing. After a successful os.replace there is nothing
        # to clean: the temp name no longer exists.
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return path


def _fsync_directory(directory: Path) -> None:
    """Persist the rename itself, where the platform has such a concept.

    POSIX needs the *directory* synced for the new name to survive a crash.
    Windows has no equivalent, and asking for one is not a no-op -- it raises
    ``PermissionError (13, 'Permission denied')`` -- so it is skipped by
    ``os.name`` rather than suppressed at random. NTFS journals its own
    metadata, which is what this call would otherwise be buying.
    """

    if os.name == "nt":
        return
    with contextlib.suppress(OSError):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
