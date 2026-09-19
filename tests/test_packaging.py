"""Guards for scripts/package_desktop.py.

Packaging is where a mistake is most expensive and least visible: the bug shows
up on a user's machine, in a bundle nobody can easily inspect. The tests here
cover the parts that are checkable without building anything --

  * the version comes from pyproject.toml, never a second copy;
  * a cross-target build is refused rather than half-attempted;
  * the payload list matches what is actually on disk, so a rename cannot
    silently ship a bundle missing a directory;
  * the unsigned claim stays honest.

Actually building a bundle is left to the platform runners in
.github/workflows/release.yml, because the toolchains (Inno Setup, hdiutil,
dpkg-deb) only exist there.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGER_PATH = REPO_ROOT / "scripts" / "package_desktop.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"
ISS_PATH = REPO_ROOT / "scripts" / "installer" / "windows.iss"


def _load_packager():
    """Import scripts/package_desktop.py by path, registering it first."""
    module_name = "fantasy_agent_package_desktop"
    spec = importlib.util.spec_from_file_location(module_name, PACKAGER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


def test_the_version_is_read_from_pyproject_not_duplicated():
    """A second copy of the version is how an installer gets misnamed.

    The tag says 0.4.0, the installer says 0.3.1, and the artifact that reaches
    a user is named after a release that never existed.
    """

    module = _load_packager()
    version = module.read_version()

    assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
    assert version in (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    source = PACKAGER_PATH.read_text(encoding="utf-8")
    # No hardcoded fallback version anywhere in the module.
    assert not re.search(r'["\']\d+\.\d+\.\d+["\']', source), (
        "package_desktop.py must not carry its own version string"
    )


def test_every_payload_entry_exists():
    """A rename that misses this list ships a bundle with holes in it.

    The failure is silent at build time and fatal at run time -- the Studio
    answers 503 on the UI routes when apps/frontend/dist is absent.
    """

    module = _load_packager()

    missing = [entry for entry in module.PAYLOAD if not (REPO_ROOT / entry).exists()]
    assert missing == [], f"payload entries missing from the tree: {missing}"

    # The two that matter most, named explicitly so a careless edit to PAYLOAD
    # cannot quietly drop them.
    assert "apps/frontend/dist" in module.PAYLOAD
    assert "apps/studio" in module.PAYLOAD
    assert "fantasy_agent" in module.PAYLOAD


def test_building_for_another_platform_is_refused():
    """Cross-compiling silently is worse than not compiling.

    The staged runtime is a copy of the current platform's interpreter, and a
    copy does not change architecture; a .deb additionally needs dpkg-deb. A
    build that "succeeds" for another platform produces a bundle that cannot
    start there.
    """

    module = _load_packager()
    native = module.current_target()

    other = next(target for target in module.SUPPORTED_TARGETS if target != native)
    with pytest.raises(RuntimeError, match="does not change architecture"):
        module.build(other)


def test_an_unknown_target_is_rejected_before_any_work():
    module = _load_packager()
    with pytest.raises(ValueError, match="unknown target"):
        module.build("solaris")


def test_the_display_name_and_the_bundle_name_stay_separate():
    """Chinese for people, ASCII for paths and packaging.

    AGENTS.md keeps implementation identifiers English. Letting the Chinese
    name into a package name or a directory breaks dpkg and the paths in
    shortcuts, and it is the kind of change that looks harmless in a diff.
    """

    module = _load_packager()

    assert module.DISPLAY_NAME_ZH == "灵构工坊"
    assert module.BUNDLE_NAME.isascii()
    assert module.APP_ID.isascii()
    assert re.fullmatch(r"[a-z][a-z0-9-]*", module.BUNDLE_NAME), module.BUNDLE_NAME


def test_the_packaging_never_claims_to_sign_anything():
    """An unsigned artefact described as signed is worse than an unsigned one."""

    source = PACKAGER_PATH.read_text(encoding="utf-8")

    assert "not signed" in source or "UNSIGNED" in source
    assert "--sign" not in source
    assert "signtool" not in source.lower()
    assert "codesign" not in source

    # The stamp that ships inside the bundle says so too.
    assert '"signed": False' in source


def test_the_installer_script_refuses_to_guess_a_version():
    """Compiling windows.iss by hand is a supported mistake to make hard."""

    source = ISS_PATH.read_text(encoding="utf-8")
    assert "#error" in source, "the .iss must fail loudly on a missing define"
    assert "/DAppVersion" in source, "the .iss must document how it is compiled"
    # No hardcoded version: everything arrives as a define.
    assert not re.search(r"AppVersion=\{?[\d.]+\}?", source)


def test_the_release_workflow_builds_on_each_native_runner():
    """The matrix is the whole reason this can work at all.

    A single ubuntu job trying to emit a .dmg would look reasonable and never
    produce one.
    """

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "windows-latest" in workflow
    assert "macos-latest" in workflow
    assert "ubuntu-latest" in workflow
    assert "package_desktop.py --target" in workflow

    # Draft, not published: a human decides whether unsigned artefacts go out.
    assert "draft: true" in workflow
    assert "未签名" in workflow, "the release notes must say the artefacts are unsigned"


def test_the_release_workflow_does_not_publish_on_every_push():
    """Releases are tag-driven. A push to main must not upload binaries."""

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    # The `release` job is gated on a tag push specifically.
    assert "github.event_name == 'push'" in workflow
    assert 'tags: ["v*"]' in workflow


def test_the_bundle_stages_the_interpreter_it_runs_on(tmp_path: Path):
    """The launchers point at ``runtime/``; the build has to create it.

    A launcher referencing an interpreter the build never staged ships a
    bundle that cannot start anywhere -- and CI would upload it to a draft
    release as if it were a deliverable.
    """

    module = _load_packager()

    # A fake interpreter tree with the layout the copy must preserve.
    base = tmp_path / "base-python"
    (base / "bin").mkdir(parents=True)
    (base / "bin" / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
    site = base / "lib" / "python3.13" / "site-packages"
    site.mkdir(parents=True)
    (site / "pip").mkdir()
    (site / "pip" / "__init__.py").write_text("", encoding="utf-8")

    # Dependencies installed into a venv, outside the base: they must be
    # merged into the staged runtime's site-packages.
    venv_site = tmp_path / "venv" / "site-packages"
    venv_site.mkdir(parents=True)
    (venv_site / "pywebview").mkdir()
    (venv_site / "pywebview" / "__init__.py").write_text("", encoding="utf-8")

    stage = tmp_path / "stage"
    stage.mkdir()
    runtime = module._stage_runtime(stage, base_prefix=base, purelib=venv_site)

    assert (runtime / "bin" / "python3").exists(), "interpreter copy is missing"
    merged = runtime / "lib" / "python3.13" / "site-packages"
    assert (merged / "pywebview" / "__init__.py").exists(), "venv deps were not merged"
    assert (merged / "pip" / "__init__.py").exists(), "base deps were lost in the copy"


def test_the_runtime_copy_leaves_the_build_machine_behind(tmp_path: Path):
    """Caches and editable-install finders must not travel with the bundle.

    An ``__editable__*`` finder points at the build machine's checkout; on a
    user's machine it is a dead path at best and a shadowing import hook at
    worst. The payload already carries the code it would import.
    """

    module = _load_packager()

    base = tmp_path / "base-python"
    site = base / "lib" / "python3.13" / "site-packages"
    site.mkdir(parents=True)
    (site / "stale" / "__pycache__").mkdir(parents=True)
    (site / "stale" / "__pycache__" / "x.pyc").write_text("", encoding="utf-8")

    venv_site = tmp_path / "venv" / "site-packages"
    venv_site.mkdir(parents=True)
    (venv_site / "__editable__fantasy_agent_finder.py").write_text("", encoding="utf-8")

    stage = tmp_path / "stage"
    stage.mkdir()
    runtime = module._stage_runtime(stage, base_prefix=base, purelib=venv_site)
    merged = runtime / "lib" / "python3.13" / "site-packages"

    assert not list(merged.rglob("__editable__*"))
    assert not list(runtime.rglob("__pycache__"))
    assert not list(runtime.rglob("*.pyc"))


def test_the_launchers_reference_a_runtime_the_build_stages():
    """Every entry point must point at a directory ``build()`` actually creates.

    This is the guard for the failure this suite shipped with once: the
    launchers named ``runtime/`` and nothing ever staged it, so all three
    platform artefacts were dead on arrival while every static check stayed
    green.
    """

    source = PACKAGER_PATH.read_text(encoding="utf-8")

    # The launchers name the runtime ...
    assert 'runtime\\\\pythonw.exe' in source, "the Windows launcher must use the staged runtime"
    assert '"$HERE/runtime/bin/python3"' in source, "the sh launcher must use the staged runtime"
    # ... and build() stages it before writing them.
    assert "_copy_payload(stage)\n    print(\"staging runtime\")" in source.replace(
        "\r\n", "\n"
    ), "build() must stage the runtime before the launchers are written"
    assert "_stage_runtime(stage)" in source


def test_the_frozen_exe_path_is_gone_for_good():
    """The PyInstaller path was removed, not fixed, and must not creep back.

    Its three halves disagreed: the spec's ``datas`` was a list of strings
    where PyInstaller wants (src, dest) tuples, its output directory collided
    with the staged payload, and no launcher or installer ever referenced the
    frozen exe. The staged runtime replaced it; a reintroduction has to wire
    all three ends at once, which is what this guard asks for.
    """

    source = PACKAGER_PATH.read_text(encoding="utf-8")
    assert "pyinstaller" not in source.lower()

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pyinstaller" not in workflow.lower()


def test_only_the_release_job_holds_write_access():
    """Building needs read; write belongs to the job that drafts the release."""

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "permissions:\n      contents: read" in workflow.replace("\r\n", "\n"), (
        "the build job must scope its permissions down to read"
    )
    assert "permissions:\n  contents: write" in workflow.replace("\r\n", "\n"), (
        "the draft-release job still needs write"
    )
