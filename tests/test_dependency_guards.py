"""Guards for dependency and lint configuration.

These started as a one-off manual checklist during the TypeScript 7 upgrade:
verify the lockfile had not been poisoned with a mirror host, that every package
carried an integrity hash, that the platform-specific binaries were all present
for the CI runner, and that lint had not been narrowed. Every one of them is the
kind of thing that passes review by hand and then silently regresses, so they
live here and run on every `pytest`.

Failure messages deliberately spell out the consequence, because the fix is
rarely obvious from the assertion alone.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / "package-lock.json"
PACKAGE_JSON_PATH = REPO_ROOT / "package.json"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

OFFICIAL_NPM_HOST = "https://registry.npmjs.org/"

# ruff's default rule set. The project follows it on purpose: a new ruff release
# that enables a rule should turn CI red and get read, instead of being pinned
# away. See the note above [tool.pytest.ini_options] in pyproject.toml.
RUFF_DEFAULT_SELECT = {"E4", "E7", "E9", "F"}


def _lock() -> dict:
    with LOCK_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_lockfile_resolves_only_from_the_official_registry() -> None:
    """A mirror host in `resolved` would make CI fetch packages elsewhere."""

    lock = _lock()
    offenders = [
        f"{name} -> {entry['resolved']}"
        for name, entry in lock["packages"].items()
        if entry.get("resolved") and not entry["resolved"].startswith(OFFICIAL_NPM_HOST)
    ]
    assert not offenders, (
        "package-lock.json resolves outside the official registry. Installing through a "
        f"mirror rewrites these hosts; they must be restored before committing: {offenders}"
    )


def test_every_locked_package_has_an_integrity_hash() -> None:
    """Without `integrity` there is nothing to verify a downloaded tarball against."""

    lock = _lock()
    missing = [
        name
        for name, entry in lock["packages"].items()
        if name and not entry.get("link") and not entry.get("integrity")
    ]
    assert not missing, f"locked packages without an integrity hash: {missing}"


def test_every_declared_dependency_is_recorded_in_the_lock() -> None:
    """Every declared dependency must appear somewhere in the lock.

    This is what keeps the per-platform binaries complete. `typescript` v7 and
    `rolldown` publish one binary package per OS/CPU and list them all as
    dependencies; npm writes every one into the lock even on a machine that can
    only install its own. A lock produced on a single platform with the others
    dropped still installs fine locally and then fails `npm ci` on a different
    runner -- the one failure the developer cannot see on their own machine.

    Matched by path suffix because a conflicting version is nested under its
    parent (`node_modules/vitest/node_modules/...`) instead of hoisted.
    """

    lock = _lock()
    packages = lock["packages"]
    keys = tuple(packages)
    missing: list[str] = []

    for name, entry in packages.items():
        declared = {
            **(entry.get("dependencies") or {}),
            **(entry.get("optionalDependencies") or {}),
        }
        for dependency in declared:
            suffix = f"node_modules/{dependency}"
            if not any(key == suffix or key.endswith(f"/{suffix}") for key in keys):
                missing.append(f"{name} declares {dependency}")

    assert not missing, (
        "the lock does not record every declared dependency, so `npm ci` will fail on "
        "the platforms whose variants are missing: " + ", ".join(missing)
    )


def test_dependency_ranges_are_pinned_not_latest() -> None:
    """`"latest"` in package.json lets a fresh install drift without a diff."""

    with PACKAGE_JSON_PATH.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    unpinned = [
        f"{section}.{name}"
        for section in ("dependencies", "devDependencies")
        for name, spec in (manifest.get(section) or {}).items()
        if spec.strip().lower() in {"latest", "*", ""}
    ]
    assert not unpinned, (
        f"these dependencies are unpinned, so the installed version can change with no "
        f"commit to review: {unpinned}"
    )


def test_ruff_is_not_narrowed_away_from_its_default_rule_set() -> None:
    """A `select` key replaces ruff's default rule set, so it silently drops rules.

    An earlier `select = ["E4", "E7", "E9", "F"]` pin kept the tree green while
    skipping 63 real findings. Narrowing again is a deliberate, reviewable change,
    so this guard fails and forces that conversation.

    Only `select` is guarded: `extend-select` adds rules on top of the defaults,
    which makes lint stricter and needs no guard.
    """

    with PYPROJECT_PATH.open("rb") as handle:
        config = tomllib.load(handle)

    lint = config.get("tool", {}).get("ruff", {}).get("lint", {})
    selected = lint.get("select")
    assert selected is None, (
        f"[tool.ruff.lint] select = {selected} narrows lint away from ruff's defaults "
        f"({sorted(RUFF_DEFAULT_SELECT)}). If a rule genuinely does not apply, ignore it "
        "at the site with a reason (`# noqa: CODE - why`) instead of dropping the whole "
        "rule category for every file."
    )


# The directories CI's Ruff step covers (`python -m ruff check fantasy_agent
# tests apps scripts`). A shebang outside them is invisible to ruff, so it is
# none of this guard's business.
RUFF_CHECKED_DIRS = ("fantasy_agent", "tests", "apps", "scripts")


def test_every_shebang_script_is_executable_in_the_git_index() -> None:
    """A shebang is a promise of executability that only Linux ever calls in.

    ruff's EXE001 (shebang present, file not executable) reads the filesystem
    mode, so on Windows -- where every file answers `os.access(path, os.X_OK)`
    with True -- it never fires and the tree stays green locally. It fired on
    CI the day ruff 0.16.10 put it in the default set (2026-10-04), and the
    backend job died at the Ruff step before pytest ran even once.

    The bit lives in the git index, which reports the same thing on every
    platform, so that is what this reads. Two honest ways to satisfy the rule:
    set the bit (`git update-index --chmod=+x <file>`) or drop the shebang.
    Executable-without-a-shebang is not a default rule and is not guarded.
    """

    listed = subprocess.run(
        ["git", "ls-files", "--stage", "-z", "--", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )

    offenders: list[str] = []
    for record in listed.stdout.split(b"\0"):
        if not record:
            continue
        metadata, _, path = record.partition(b"\t")
        if path.decode().split("/", 1)[0] not in RUFF_CHECKED_DIRS:
            continue
        mode = metadata.split(b" ")[0].decode()
        head = (REPO_ROOT / path.decode()).read_bytes().split(b"\n", 1)[0]
        if head.startswith(b"#!") and mode != "100755":
            offenders.append(f"{path.decode()} has mode {mode}")

    assert not offenders, (
        "these tracked scripts declare a shebang but are not executable in the git "
        "index, so ruff's EXE001 fails the Ruff step on Linux while every local run "
        f"stays green: {offenders}. Set the bit with "
        "`git update-index --chmod=+x <file>`, or delete the shebang if the script "
        "is only ever run as `python <file>`."
    )
