from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from fantasy_agent import asset_library, atomic_write
from fantasy_agent.asset_library import (
    AssetLibraryError,
    generated_asset_entries,
    ingest_asset,
    library_overview,
    load_asset_library,
    remove_asset,
    save_asset_library,
)
from fantasy_agent.contracts import (
    ArtifactIdentity,
    AssetApprovalDecision,
    AssetApprovalManifest,
    AssetLibrary,
    AssetLibraryEntry,
)
from fantasy_agent.path_safety import assert_safe_path_segment


def _write_asset(root: Path, relative: str, payload: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _ingest(root: Path, **overrides) -> AssetLibraryEntry:
    payload = overrides.pop("payload", b"stub-glb-bytes")
    source = _write_asset(root, "downloads/nature.glb", payload)
    request = {
        "name": "  Kenney Nature Pack  ",
        "source_path": str(source),
        "license": "CC0",
        "author": "Kenney",
        "source_url": "https://kenney.nl/assets/nature-pack",
        "tags": [" nature ", "", "environment"],
    }
    request.update(overrides)
    return ingest_asset(workspace_root=root, **request)


def test_ingest_copies_the_file_and_records_where_it_came_from(tmp_path: Path):
    entry = _ingest(tmp_path)

    assert entry.name == "Kenney Nature Pack"  # trimmed
    assert entry.kind == "mesh"  # inferred from .glb
    assert entry.source == "open_source"
    assert entry.original_name == "nature.glb"
    assert entry.license == "CC0"
    assert entry.tags == ["nature", "environment"]  # blanks dropped
    assert entry.sha256 == hashlib.sha256(b"stub-glb-bytes").hexdigest()
    assert entry.size_bytes == len(b"stub-glb-bytes")

    # The id is a directory name, so the segment rule is the shape it must keep.
    assert_safe_path_segment(entry.id, label="asset id")

    # The copy landed inside the library, under the id, named by the id.
    stored = tmp_path / entry.path
    assert stored.parent == tmp_path / "generated" / "asset-library" / "files" / entry.id
    assert stored.name == f"{entry.id}.glb"
    assert stored.read_bytes() == b"stub-glb-bytes"
    # The user's original download is untouched.
    assert (tmp_path / "downloads" / "nature.glb").read_bytes() == b"stub-glb-bytes"


def test_a_missing_library_reads_as_empty_without_complaining(tmp_path: Path):
    assert load_asset_library(workspace_root=tmp_path).entries == []


def test_ingest_appends_to_an_existing_library(tmp_path: Path):
    first = _ingest(tmp_path)
    second = _ingest(tmp_path, name="Second Asset", payload=b"second")

    library = load_asset_library(workspace_root=tmp_path)
    assert [entry.id for entry in library.entries] == [first.id, second.id]
    assert first.id != second.id


def test_ingest_rejects_sources_it_cannot_use(tmp_path: Path):
    with pytest.raises(AssetLibraryError, match="不存在"):
        _ingest(tmp_path, source_path=str(tmp_path / "downloads" / "nope.glb"))

    with pytest.raises(AssetLibraryError, match="不是文件"):
        ingest_asset(
            name="A Directory",
            source_path=str(tmp_path),
            workspace_root=tmp_path,
        )

    empty = _write_asset(tmp_path, "downloads/empty.png", b"")
    with pytest.raises(AssetLibraryError, match="空的"):
        ingest_asset(name="Empty", source_path=str(empty), workspace_root=tmp_path)

    big = _write_asset(tmp_path, "downloads/big.glb", b"x" * 32)
    original_limit = asset_library.MAX_INGEST_BYTES
    try:
        asset_library.MAX_INGEST_BYTES = 8
        with pytest.raises(AssetLibraryError, match="上限"):
            ingest_asset(name="Too Big", source_path=str(big), workspace_root=tmp_path)
    finally:
        asset_library.MAX_INGEST_BYTES = original_limit


def test_ingest_validates_kind_and_allows_an_override(tmp_path: Path):
    entry = _ingest(tmp_path, kind="audio")
    assert entry.kind == "audio"  # the caller knows better than the extension

    with pytest.raises(AssetLibraryError, match="资产类型"):
        _ingest(tmp_path, kind="video")


def test_relative_source_paths_resolve_against_the_workspace(tmp_path: Path):
    _write_asset(tmp_path, "downloads/nature.glb", b"stub-glb-bytes")
    entry = ingest_asset(
        name="Relative",
        source_path="downloads/nature.glb",
        workspace_root=tmp_path,
    )
    assert (tmp_path / entry.path).read_bytes() == b"stub-glb-bytes"


def test_remove_deletes_the_library_copy_and_keeps_the_original(tmp_path: Path):
    entry = _ingest(tmp_path)

    removed = remove_asset(entry.id, workspace_root=tmp_path)
    assert removed is not None and removed.id == entry.id
    assert not (tmp_path / entry.path).exists()
    assert load_asset_library(workspace_root=tmp_path).entries == []
    # The file the user pointed at is still there.
    assert (tmp_path / "downloads" / "nature.glb").exists()
    # Unknown ids answer None rather than raising, so the endpoint can 404.
    assert remove_asset(entry.id, workspace_root=tmp_path) is None


def test_remove_refuses_a_path_outside_the_library(tmp_path: Path):
    """A hand-edited manifest must not turn delete into delete-anything."""

    outside = _write_asset(tmp_path, "generated/config/llm-api.json", b'{"api_key": "x"}')
    library = AssetLibrary(
        entries=[
            AssetLibraryEntry(
                id="asset-0123456789ab",
                name="Points Outside",
                path="generated/config/llm-api.json",
                size_bytes=outside.stat().st_size,
                sha256=hashlib.sha256(b'{"api_key": "x"}').hexdigest(),
            )
        ]
    )
    save_asset_library(library, workspace_root=tmp_path)

    with pytest.raises(AssetLibraryError, match="拒绝删除"):
        remove_asset("asset-0123456789ab", workspace_root=tmp_path)
    assert outside.read_bytes() == b'{"api_key": "x"}'


def test_a_corrupt_library_raises_instead_of_reading_as_empty(tmp_path: Path):
    path = tmp_path / "generated" / "asset-library" / "library.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("entries: 42\n", encoding="utf-8")

    # Answering "empty" here would let the next ingest silently drop every
    # entry the user cannot see.
    with pytest.raises(ValidationError):
        load_asset_library(workspace_root=tmp_path)


def test_generated_entries_map_the_approval_manifest(tmp_path: Path):
    manifest = AssetApprovalManifest(
        decisions=[
            AssetApprovalDecision(
                asset_id="wall_straight",
                source="blender",
                asset_path="generated/assets/wall_straight.glb",
                gameplay_role="route wall",
                artifact_identity=ArtifactIdentity(digest="a" * 64),
                decision="approved",
            )
        ]
    )
    manifest_path = tmp_path / "generated" / "asset-approval-manifest.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        yaml.safe_dump(manifest.model_dump(mode="json")), encoding="utf-8"
    )

    records = generated_asset_entries(workspace_root=tmp_path)
    assert len(records) == 1
    assert records[0].asset_id == "wall_straight"
    assert records[0].status == "approved"
    assert records[0].sha256 == "a" * 64


def test_generated_entries_are_empty_without_a_manifest(tmp_path: Path):
    assert generated_asset_entries(workspace_root=tmp_path) == []


def test_overview_reports_both_sides(tmp_path: Path):
    entry = _ingest(tmp_path)

    overview = library_overview(workspace_root=tmp_path)
    assert [item.id for item in overview.entries] == [entry.id]
    assert overview.generated == []
    assert overview.library_path == "generated/asset-library/library.yaml"
    assert overview.generated_manifest_present is False


def test_an_interrupted_save_keeps_the_previous_library(tmp_path: Path, monkeypatch):
    """A refused publish must not cost the user the entries already in the library.

    The manifest is read back to list, count and delete, so a half-written one
    parses as a smaller library rather than as a failed save -- the same
    failure the atomic helper exists for, in the shape this module's docstring
    promises it cannot have.
    """

    _ingest(tmp_path)

    def _boom(src, dst):
        raise OSError(13, "publish refused")

    monkeypatch.setattr(atomic_write.os, "replace", _boom)
    with pytest.raises(OSError):
        _ingest(tmp_path, name="Second Asset", payload=b"second")

    library = load_asset_library(workspace_root=tmp_path)
    assert [entry.name for entry in library.entries] == ["Kenney Nature Pack"], (
        "the interrupted save destroyed a working library"
    )
    assert list((tmp_path / "generated" / "asset-library").glob("*.tmp")) == []


def test_a_failed_manifest_save_leaves_no_entry_behind(tmp_path: Path, monkeypatch):
    """The copy lands before the manifest is written.

    With the save refused, the documented order leaves an unreferenced file
    and no entry. The residue is harmless; an entry pointing at a file that
    was never written is not -- the panel would render it as a broken asset.
    The residue is read here as the signature of the order, not cleaned up as
    a defect.
    """

    def _boom(*args, **kwargs):
        raise OSError(13, "manifest refused")

    monkeypatch.setattr(asset_library, "save_asset_library", _boom)
    with pytest.raises(OSError):
        _ingest(tmp_path)

    copies = list((tmp_path / "generated" / "asset-library" / "files").rglob("*.glb"))
    assert len(copies) == 1, "the copy landed before the manifest, or not at all"
    assert not (tmp_path / "generated" / "asset-library" / "library.yaml").exists()
