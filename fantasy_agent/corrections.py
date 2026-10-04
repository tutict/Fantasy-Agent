"""Reading hand edits back out of a generated Godot project.

The console sends operators out to Blender, ComfyUI and the Godot editor with
an "open" button. Whatever they change over there lives only in those tools:
this module is the way back. Two questions, in order:

1. **Did anything change at all?** The generator records a sha256 per produced
   file, so a drifted file is a fact rather than a suspicion. Without that,
   "my edit survived" is unfalsifiable -- the next generation silently
   overwrites it.
2. **Can the change be saved?** Every tunable in the generated GDScript carries
   a ``# [ANCHOR]`` tag, so the edited value can be read back exactly. Whether
   it can be written *back* is a different question: only a handful of anchors
   come from the DSL, and the rest are hardcoded engine constants. Those are
   reported as unrecoverable rather than patched, because a patch that
   silently goes nowhere is worse than an honest gap.

Nothing here writes to the project. A hand edit is the operator's work; this
module's job is to make it visible before the next run replaces it.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from fantasy_agent.contracts import CorrectionDrift, CorrectionReport, CorrectionTweak
from fantasy_agent.path_safety import WorkspacePathError, resolve_workspace_path

MANIFEST_FILENAME = "fantasy-agent-godot-manifest.json"

#: ``@export var move_speed := 8.0   # [MOVE_SPEED]``
#:
#: Anchored on the declaration and the tag together: a bare ``[NAME]`` also
#: appears in behaviour comments (``# [SPRINT] hold to accelerate``), and
#: reading one of those would report a hand edit that is not an editable
#: number at all.
ANCHOR_RE = re.compile(
    r"^@export\s+var\s+(?P<var>[a-z_][a-z0-9_]*)\s*:=\s*(?P<value>-?\d+(?:\.\d+)?)\s*"
    r"(?:#[^\n]*?)?#\s*\[(?P<anchor>[A-Z][A-Z0-9_]*)\]",
    re.MULTILINE,
)

#: The only anchors that are filled from the spec bundle. Everything else with
#: a tag is a literal in the generator, and a hand edit to it has no DSL home.
#: Kept as data rather than inferred so that adding a tunable to the DSL is a
#: one-line change and cannot drift from what this module claims it can save.
SPEC_BACKED_ANCHORS: dict[str, str] = {
    "MOVE_SPEED": "numeric.player_move_speed",
    "PLAYER_HP": "numeric.player_hp",
    "ENEMY_HP": "numeric.enemy_pressure.enemy_hp",
    "PRESSURE_LIMIT": "numeric.pressure_clock_seconds",
}


def file_sha256(path: Path) -> str:
    """Content hash of one file, or an empty string when it cannot be read."""

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _kind_for(path: str) -> str:
    if path.endswith(".gd"):
        return "script"
    if path.endswith(".tscn"):
        return "scene"
    if path.endswith("project.godot"):
        return "project"
    return "other"


def _read_manifest(manifest_path: Path) -> dict | None:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _recorded_hashes(manifest: dict) -> dict[str, str]:
    """The hash table, accepting both the current field name and ``None``."""

    recorded = manifest.get("artifact_sha256")
    if isinstance(recorded, dict):
        return {str(key): str(value) for key, value in recorded.items() if isinstance(value, str)}
    return {}


def _artifact_paths(manifest: dict) -> list[str]:
    paths: list[str] = []
    for key in ("script_paths", "scene_paths"):
        value = manifest.get(key)
        if isinstance(value, list):
            paths.extend(str(item) for item in value)
    for key in ("project_file", "main_scene_path"):
        value = manifest.get(key)
        if isinstance(value, str):
            paths.append(value)
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _resolve_project(project_dir: Path | str, workspace_root: Path | str) -> Path:
    """Resolve the caller's project directory against the workspace.

    Done once, by the entry point, because the manifest lookup and the
    per-artifact lookups have to agree on where the project is: a relative
    path read from one base and resolved against another silently reports "no
    manifest" for a project that has one. A path outside the workspace raises,
    matching every other caller-supplied path in this repo.

    Each public function resolves its own argument, so a relative path is
    interpreted against the workspace rather than against the process cwd.
    """

    return resolve_workspace_path(str(project_dir), workspace_root=workspace_root)


def detect_drift(project_dir: Path | str, *, workspace_root: Path | str) -> list[CorrectionDrift]:
    """Compare every artifact's hash now against the hash recorded at build.

    A file with no recorded hash is reported with ``hash_unknown`` rather than
    skipped: projects generated before hashing existed cannot be vouched for,
    and silence would read as "unchanged".
    """

    project = _resolve_project(project_dir, workspace_root)
    manifest = _read_manifest(project / MANIFEST_FILENAME)
    if manifest is None:
        return []
    recorded = _recorded_hashes(manifest)
    drifted: list[CorrectionDrift] = []
    for relative in _artifact_paths(manifest):
        resolved = _safe_artifact(project, relative, workspace_root)
        if resolved is None:
            continue
        current = file_sha256(resolved)
        expected = recorded.get(relative, "")
        if not expected:
            drifted.append(
                CorrectionDrift(
                    path=relative,
                    kind=_kind_for(relative),
                    current_sha256=current,
                    hash_unknown=True,
                )
            )
            continue
        if current and current != expected:
            drifted.append(
                CorrectionDrift(
                    path=relative,
                    kind=_kind_for(relative),
                    recorded_sha256=expected,
                    current_sha256=current,
                )
            )
    return drifted


def _safe_artifact(project: Path, relative: str, workspace_root: Path | str) -> Path | None:
    """Resolve a manifest path, refusing anything outside the workspace.

    The manifest is a file on disk that a hand edit could rewrite, so its
    contents are treated as untrusted input rather than as our own record.
    """

    if not relative or Path(relative).is_absolute():
        return None
    try:
        resolved = resolve_workspace_path(relative, workspace_root=workspace_root)
    except WorkspacePathError:
        return None
    try:
        resolved.relative_to(Path(project).resolve())
    except ValueError:
        return None
    return resolved


def extract_tweaks(
    project_dir: Path | str,
    *,
    workspace_root: Path | str,
    only_changed: bool = True,
) -> tuple[list[CorrectionTweak], list[CorrectionTweak]]:
    """Read edited anchor values out of the generated GDScript.

    ``only_changed`` compares each value against the one the generator would
    produce, not just against the file's hash. A hand edit anywhere in a
    script leaves every other line intact, so filtering on the hash alone
    would report all ~50 anchors in that file as edited -- which buries the
    one or two the operator actually changed.

    Returns ``(recoverable, engine_only)``. Both are sorted by path and line so
    two runs over the same tree produce the same report.
    """

    project = _resolve_project(project_dir, workspace_root)
    manifest = _read_manifest(project / MANIFEST_FILENAME) or {}
    recorded = _recorded_hashes(manifest)
    generated_by_script = {path for path in _artifact_paths(manifest) if path.endswith(".gd")}
    baselines = _generated_anchors(manifest)

    recoverable: list[CorrectionTweak] = []
    engine_only: list[CorrectionTweak] = []
    for relative in sorted(generated_by_script):
        resolved = _safe_artifact(project, relative, workspace_root)
        if resolved is None or not resolved.is_file():
            continue
        if only_changed:
            current = file_sha256(resolved)
            if not current or current == recorded.get(relative, ""):
                continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in ANCHOR_RE.finditer(text):
            anchor = match.group("anchor")
            # `float` on a widened pattern's word would raise and take the whole
            # scan down; a value we cannot read is not a value we can report.
            try:
                value = float(match.group("value"))
            except ValueError:
                continue
            generated_value = baselines.get((relative, anchor))
            if only_changed and generated_value is not None and _same_number(value, generated_value):
                continue
            # No baseline means no evidence, which is not the same as "unchanged":
            # such an anchor is reported (with `generated_value` left empty) so
            # the operator sees it as unverified rather than confirmed.
            spec_field = SPEC_BACKED_ANCHORS.get(anchor, "")
            tweak = CorrectionTweak(
                anchor=anchor,
                variable=match.group("var"),
                value=value,
                generated_value=generated_value,
                spec_field=spec_field,
                script_path=relative,
                line_number=text.count("\n", 0, match.start()) + 1,
            )
            (recoverable if spec_field else engine_only).append(tweak)
    return recoverable, engine_only


def _same_number(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-9


def _generated_anchors(manifest: dict) -> dict[tuple[str, str], float]:
    """The anchor values this build produced, keyed by ``(path, anchor)``.

    Read from the manifest rather than regenerated from the bundle: the
    manifest already records what this run wrote, so the baseline cannot drift
    from the artifacts it describes. A hand-edited manifest cannot invent
    plausible-looking edits either -- it would have to change a recorded value
    *and* the script together, and the hash check is what notices.
    """

    table = manifest.get("artifact_anchors")
    if not isinstance(table, dict):
        return {}
    anchors: dict[tuple[str, str], float] = {}
    for path, values in table.items():
        if not isinstance(values, dict):
            continue
        for anchor, value in values.items():
            if isinstance(value, int | float) and not isinstance(value, bool):
                anchors[(str(path), str(anchor))] = float(value)
    return anchors


def inspect_corrections(project_dir: str, *, workspace_root: Path | str) -> CorrectionReport:
    """Full read-only pass: what drifted, what can be saved, what cannot."""

    root = Path(workspace_root)
    project = _resolve_project(project_dir, root)
    manifest_path = project / MANIFEST_FILENAME
    report = CorrectionReport(
        project_dir=project_dir,
        manifest_path=manifest_path.as_posix(),
        manifest_found=manifest_path.is_file(),
        inspected_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    if not report.manifest_found:
        report.notes.append(
            "No handoff manifest in this project, so nothing here was produced by "
            "this pipeline and there is no generated state to compare against."
        )
        return report

    report.drifted = detect_drift(project_dir, workspace_root=root)
    recoverable, engine_only = extract_tweaks(project_dir, workspace_root=root)
    report.recoverable = recoverable
    report.engine_only = engine_only

    unknown = sum(1 for item in report.drifted if item.hash_unknown)
    if unknown:
        report.notes.append(
            f"{unknown} artifact(s) have no recorded hash: this project predates hash "
            "recording, so 'unchanged' cannot be claimed for them."
        )
    if report.drifted:
        report.notes.append(
            "The next generation overwrites every file listed above. Copy anything you "
            "want to keep out of the project directory first."
        )
    if engine_only:
        report.notes.append(
            f"{len(engine_only)} edited value(s) are engine constants with no field in the "
            "gameplay DSL. They are listed so the gap is visible, but there is nowhere to "
            "write them back to -- closing it means adding the field to the spec."
        )
    if not report.drifted and not engine_only:
        report.notes.append("No hand edits found: the project matches what this run produced.")
    return report


def summarize_corrections(report: CorrectionReport) -> str:
    """One paragraph for the activity log."""

    parts = [
        f"{len(report.drifted)} changed file(s)",
        f"{len(report.recoverable)} value(s) writable back to the spec",
        f"{len(report.engine_only)} engine-only value(s) with no DSL home",
    ]
    return "Correction scan: " + ", ".join(parts) + "."
