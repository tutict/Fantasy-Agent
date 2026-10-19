"""Local library of game assets: ingested open-source files + what was generated.

Two questions the Studio UI could not answer before this module:

- *What assets does this project actually have?* -- the generated side was
  recorded only in ``generated/asset-approval-manifest.yaml``, visible solely
  during the approval gate stage of one execution run.
- *Where did this open-source asset come from, and under what license?* -- it
  had no answer at all: the files sat in the user's download folder with no
  relationship to the workbench.

Design decisions worth knowing before editing:

**Ingestion copies from a local file; it never fetches.** The whole product is
local-first -- Studio listens on ``127.0.0.1`` only and a remote ComfyUI
endpoint needs explicit authorization. Downloading from a pasted URL would open
a network egress the product does not otherwise have, together with content
type, size, and archive-extraction (zip-slip) hazards. Those deserve their own
round with their own confirmation gate, not a ride-along. See
``docs/superpowers/plans/2026-10-18-asset-library.md`` §1.1.

**The library file is a decision input, so it is written atomically.** The
panel reads it back to list, count, and delete; a half-written manifest would
parse as a smaller library rather than as a failed save. Same judgement as the
approval manifest and ``llm-api.json`` -- the test is "is it read back to
decide", not "is it important".

**The copy lands before the manifest is saved.** If the save fails after a
successful copy the residue is an unreferenced file, which is harmless; the
reverse order would leave a manifest entry pointing at a file that was never
written, which the UI would render as a broken asset.

**Disk names are ``<id><ext>``, never the user's file name.** ``Path(name).name``
does not protect against Windows trailing-dot folding -- ``victim.`` and
``victim`` are one directory, and the aliasing happens inside the filesystem
where a containment check cannot see it. The user's original name is kept in
the ``original_name`` field, which is metadata and never a path.

**A missing file is an empty library, not a fault.** No warning is logged for
it, for the same reason ``api_settings`` and ``pipeline_state`` stay quiet: a
line per first run drowns the real signal.

**Deletion only ever removes our copy.** ``remove_asset`` re-resolves the
entry's path and requires it to sit under the library's own files directory
before unlinking -- a hand-edited manifest that points an entry at, say, the
LLM settings file must not be able to delete it through this endpoint. The
user's original download is never touched.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from fantasy_agent.approval_manifest import (
    DEFAULT_APPROVAL_MANIFEST_PATH,
    load_asset_approval_manifest,
)
from fantasy_agent.artifact_identity import compute_artifact_identity
from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.contracts import (
    AssetLibrary,
    AssetLibraryEntry,
    AssetLibraryOverview,
    GeneratedAssetRecord,
)
from fantasy_agent.godot_mcp import DEFAULT_WORKSPACE_ROOT, GodotMCPSafetyError
from fantasy_agent.path_safety import WorkspacePathError, resolve_workspace_path

#: Workspace-relative directory that holds the manifest and every ingested copy.
LIBRARY_DIR = "generated/asset-library"
#: Workspace-relative manifest. Read back to decide, written atomically.
LIBRARY_PATH = "generated/asset-library/library.yaml"
#: Workspace-relative directory the ingested copies live in.
FILES_SUBDIR = "generated/asset-library/files"

#: One ingested file may not exceed this. A jam asset pack that does is either
#: a mistake or something that belongs in the engine project directly; the
#: limit is enforced at ingest time and reported, never silently truncated.
MAX_INGEST_BYTES = 256 * 1024 * 1024

_KIND_BY_EXTENSION: dict[str, str] = {
    ".glb": "mesh",
    ".fbx": "mesh",
    ".obj": "mesh",
    ".dae": "mesh",
    ".blend": "mesh",
    ".png": "texture",
    ".jpg": "texture",
    ".jpeg": "texture",
    ".webp": "texture",
    ".tga": "texture",
    ".wav": "audio",
    ".ogg": "audio",
    ".mp3": "audio",
    ".flac": "audio",
}
_VALID_KINDS = ("mesh", "texture", "audio", "other")


class AssetLibraryError(ValueError):
    """A request the library cannot honour, with a message for the UI."""


def _resolve(path: str, *, workspace_root: Path | str) -> Path:
    try:
        return resolve_workspace_path(path, workspace_root=workspace_root)
    except WorkspacePathError as exc:
        raise AssetLibraryError(str(exc)) from exc


def load_asset_library(
    *,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetLibrary:
    """Read the library manifest.

    A missing file is an empty library. A file that exists but cannot be
    parsed raises -- silently answering "empty" to a corrupt manifest would
    let the next ingest overwrite the entries the user cannot see.
    """

    path = _resolve(LIBRARY_PATH, workspace_root=workspace_root)
    if not path.exists():
        return AssetLibrary()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AssetLibrary.model_validate(data)


def save_asset_library(
    library: AssetLibrary,
    *,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> Path:
    path = _resolve(LIBRARY_PATH, workspace_root=workspace_root)
    return write_atomic(
        path,
        yaml.safe_dump(library.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
    )


def _new_entry_id() -> str:
    return f"asset-{uuid.uuid4().hex[:12]}"


def ingest_asset(
    *,
    name: str,
    source_path: str,
    license: str = "",
    author: str = "",
    source_url: str = "",
    notes: str = "",
    tags: list[str] | None = None,
    kind: str | None = None,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetLibraryEntry:
    """Copy a local file into the library and record where it came from.

    ``source_path`` is a path on this machine. An absolute path is taken as
    the user pointing at a file they already have -- the same nature as
    ``open_manual_correction_target`` -- and a relative one is resolved
    against the workspace. The original is never moved or modified.
    """

    display_name = name.strip()
    if not display_name:
        raise AssetLibraryError("资产名不能为空")
    if kind is not None and kind not in _VALID_KINDS:
        raise AssetLibraryError(f"资产类型必须是 {', '.join(_VALID_KINDS)} 之一：{kind!r}")

    source = Path(source_path)
    if not source.is_absolute():
        source = Path(workspace_root) / source
    if not source.exists():
        raise AssetLibraryError(f"资产文件不存在：{source_path!r}")
    if not source.is_file():
        raise AssetLibraryError(f"资产路径不是文件：{source_path!r}")
    try:
        size_bytes = source.stat().st_size
    except OSError as exc:
        raise AssetLibraryError(f"资产文件无法读取：{exc}") from exc
    if size_bytes == 0:
        raise AssetLibraryError(f"资产文件是空的（下载可能没完成）：{source_path!r}")
    if size_bytes > MAX_INGEST_BYTES:
        limit_mib = MAX_INGEST_BYTES // (1024 * 1024)
        raise AssetLibraryError(f"资产文件超过 {limit_mib} MiB 上限：{size_bytes} 字节")

    extension = source.suffix.lower()
    entry_kind = kind or _KIND_BY_EXTENSION.get(extension, "other")
    entry_id = _new_entry_id()
    # The id is the only caller-controlled part of the destination, and it is
    # generated here; resolving still goes through the shared helper so the
    # containment rule is enforced by the same code as everywhere else.
    destination = _resolve(
        f"{FILES_SUBDIR}/{entry_id}/{entry_id}{extension}",
        workspace_root=workspace_root,
    )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    except OSError as exc:
        raise AssetLibraryError(f"资产无法复制进库：{exc}") from exc

    entry = AssetLibraryEntry(
        id=entry_id,
        name=display_name,
        kind=entry_kind,  # type: ignore[arg-type]
        original_name=source.name,
        path=destination.relative_to(Path(workspace_root).resolve()).as_posix(),
        size_bytes=size_bytes,
        sha256=compute_artifact_identity(destination).digest,
        license=license.strip(),
        author=author.strip(),
        source_url=source_url.strip(),
        notes=notes.strip(),
        tags=[tag.strip() for tag in (tags or []) if tag.strip()],
        ingested_at=datetime.now(UTC).isoformat(),
    )

    library = load_asset_library(workspace_root=workspace_root)
    library.entries.append(entry)
    save_asset_library(library, workspace_root=workspace_root)
    return entry


def remove_asset(
    asset_id: str,
    *,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetLibraryEntry | None:
    """Drop one entry and delete its library copy. Returns None if unknown.

    The entry's path is re-resolved and required to sit under the library's
    own files directory before anything is unlinked: the manifest is a file a
    user can hand-edit, and an entry rewritten to point outside must not turn
    this endpoint into a delete-anything button. The user's original download
    is not reachable from here by construction.
    """

    library = load_asset_library(workspace_root=workspace_root)
    entry = next((item for item in library.entries if item.id == asset_id), None)
    if entry is None:
        return None

    files_root = _resolve(FILES_SUBDIR, workspace_root=workspace_root)
    try:
        target = _resolve(entry.path, workspace_root=workspace_root)
    except AssetLibraryError as exc:
        raise AssetLibraryError(f"条目路径不在工作区内，拒绝删除：{exc}") from exc
    if files_root not in target.parents:
        raise AssetLibraryError(f"条目文件不在资产库目录内，拒绝删除：{entry.path!r}")

    try:
        target.unlink(missing_ok=True)
    except OSError as exc:
        raise AssetLibraryError(f"库内文件无法删除：{exc}") from exc
    library.entries = [item for item in library.entries if item.id != asset_id]
    save_asset_library(library, workspace_root=workspace_root)
    return entry


def generated_asset_entries(
    *,
    manifest_path: str = DEFAULT_APPROVAL_MANIFEST_PATH,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> list[GeneratedAssetRecord]:
    """Creative Review decisions as library records.

    A missing manifest means no review has been written yet -- an empty list,
    not an error. A manifest that exists but cannot be read raises, because
    answering "nothing was generated" to a broken file is a lie the panel
    would render as a fact.
    """

    try:
        manifest = load_asset_approval_manifest(manifest_path, workspace_root=workspace_root)
    except FileNotFoundError:
        return []
    except GodotMCPSafetyError as exc:
        raise AssetLibraryError(str(exc)) from exc
    return [
        GeneratedAssetRecord(
            asset_id=decision.asset_id,
            source=decision.source,
            asset_path=decision.asset_path,
            gameplay_role=decision.gameplay_role,
            status=decision.decision,
            sha256=decision.artifact_identity.digest if decision.artifact_identity else None,
        )
        for decision in manifest.decisions
    ]


def library_overview(
    *,
    manifest_path: str = DEFAULT_APPROVAL_MANIFEST_PATH,
    workspace_root: Path | str = DEFAULT_WORKSPACE_ROOT,
) -> AssetLibraryOverview:
    """Everything the asset panel renders, from the two files of record."""

    resolved_manifest = _resolve(manifest_path, workspace_root=workspace_root)
    return AssetLibraryOverview(
        entries=load_asset_library(workspace_root=workspace_root).entries,
        generated=generated_asset_entries(
            manifest_path=manifest_path, workspace_root=workspace_root
        ),
        library_path=LIBRARY_PATH,
        generated_manifest_path=manifest_path,
        generated_manifest_present=resolved_manifest.exists(),
    )
