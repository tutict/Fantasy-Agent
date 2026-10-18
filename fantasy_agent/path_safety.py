"""Shared workspace path safety helpers.

The execution and asset-ingest modules accept workspace-relative paths from
plans, manifests, and UI requests. Keep the path rules in one small module so
callers get the same traversal checks and error messages.
"""

from __future__ import annotations

import re
from pathlib import Path


class WorkspacePathError(ValueError):
    """Raised when a requested path escapes the configured workspace."""


#: A path segment built from a caller-supplied identifier. Deliberately
#: narrower than "anything without a separator": these end up as **directory
#: names on disk**, and that is where the two rules below come from.
#:
#: 1. No trailing dot. On Windows the filesystem silently strips trailing dots
#:    and spaces, so ``victim.`` and ``victim`` are *one* directory -- an id
#:    that passed a traversal check could still land on top of another
#:    session's files. A containment check cannot see this: it resolves the
#:    path fine and reports success, because the aliasing happens inside the OS.
#:    Spaces are excluded outright, so only the dot needs a rule of its own.
#: 2. No control characters. ``resolve_workspace_path`` rejects ``..`` and
#:    absolute roots, but a newline in an id reaches a log line verbatim, so an
#:    id could forge a second log record that no reader would attribute to a
#:    request.
#:
#: Reserved device names (``CON``, ``NUL``, ``COM1``) are *not* excluded: on
#: Windows they cannot be created as directory names either, so they fail
#: loudly at write time rather than aliasing onto something. The only ids that
#: exist in this repository are ``orch-<hex>`` server-side and
#: ``orch-<base36>-<base36>`` browser-side, so the ceiling is nowhere near the
#: real format.
_SAFE_SEGMENT = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,62}[A-Za-z0-9_-]\Z|\A[A-Za-z0-9]\Z")


def assert_safe_path_segment(value: str, *, label: str) -> str:
    """Return ``value`` if it is usable as one directory name, else raise.

    Call this before interpolating an identifier into a path, and keep it
    separate from :func:`resolve_workspace_path`: that function answers "is
    this path inside the workspace", which is a different question from "is this
    string a name the filesystem will give back to me unchanged".
    """

    if not _SAFE_SEGMENT.match(value):
        raise WorkspacePathError(
            f"{label} must be 1-64 characters of letters, digits, dot, dash or "
            f"underscore, start with a letter or digit and not end with a dot: "
            f"{value!r}"
        )
    return value


def workspace_root_path(workspace_root: Path | str) -> Path:
    return Path(workspace_root).resolve()


def assert_under(path: Path, root: Path | str) -> None:
    resolved_root = workspace_root_path(root)
    try:
        path.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspacePathError(f"Path escapes workspace: {path}") from exc


def is_absolute_path(path: str) -> bool:
    """True for paths that escape relative joining, drive or no drive.

    ``Path("/etc/passwd").is_absolute()`` is **False on Windows** — a path needs
    both a root and a drive to count as absolute there. Such a path is still
    dangerous: joining it onto the workspace silently discards the workspace
    prefix and lands at the drive root. Treating any rooted path as absolute
    keeps the check honest on both platforms.

    The leading backslash is the mirror image on POSIX. ``Path`` reads
    ``\\etc\\passwd`` as an ordinary relative filename there — a backslash is
    a legal name character — but :func:`resolve_workspace_path` normalises
    separators before joining, and ``root / Path("/etc/passwd")`` discards the
    workspace prefix exactly the way the Windows case does. Without this
    clause the input was still refused, but only by the containment backstop
    and with a vaguer message. A leading separator of either kind is a root
    for the purpose of this function.
    """
    candidate = Path(path)
    return candidate.is_absolute() or bool(candidate.root) or path.startswith("\\")


def resolve_workspace_path(
    path: str,
    *,
    workspace_root: Path | str,
    required_prefix: str | None = None,
    allow_absolute: bool = False,
) -> Path:
    """Resolve a workspace path after optional relative-prefix validation."""

    if not allow_absolute and is_absolute_path(path):
        raise WorkspacePathError(f"Absolute paths are not allowed: {path}")
    normalized = Path(path.replace("\\", "/"))
    if ".." in normalized.parts:
        raise WorkspacePathError(f"Parent traversal is not allowed: {path}")
    if required_prefix is not None:
        prefix = Path(required_prefix)
        if normalized.parts[: len(prefix.parts)] != prefix.parts:
            raise WorkspacePathError(f"Path must stay under {required_prefix}: {path}")
    root = workspace_root_path(workspace_root)
    resolved = (root / normalized).resolve()
    assert_under(resolved, root)
    return resolved


def display_workspace_path(path: Path, *, workspace_root: Path | str) -> str:
    return path.resolve().relative_to(workspace_root_path(workspace_root)).as_posix()
