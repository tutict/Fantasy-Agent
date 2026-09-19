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

    PyInstaller does not cross-compile, and a .deb needs dpkg-deb. A build that
    "succeeds" for another platform produces a bundle that cannot start there.
    """

    module = _load_packager()
    native = module.current_target()

    other = next(target for target in module.SUPPORTED_TARGETS if target != native)
    with pytest.raises(RuntimeError, match="does not cross-compile"):
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
