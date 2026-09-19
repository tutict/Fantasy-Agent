"""Guards for the Chinese-facing product name.

The tool's Chinese name is 灵构工坊. "Fantasy Agent" stays as the repository,
package and implementation identifier -- AGENTS.md keeps those in English on
purpose. Anything a person reads in the Chinese UI must show 灵构工坊.

The drift this guards against is a brand string hardcoded in JSX: the sidebar
heading and the console heading were both a literal `<h1>Fantasy Agent</h1>`,
so the Chinese locale showed an English product name while every string around
it was translated. Adding the key back to the dictionary would not have fixed
it -- the JSX never asked for a translation.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
I18N_PATH = REPO_ROOT / "apps" / "frontend" / "src" / "shared" / "i18n.ts"
STUDIO_SHELL_PATH = REPO_ROOT / "apps" / "frontend" / "src" / "studio" / "StudioShell.tsx"
FLOW_CONSOLE_PATH = REPO_ROOT / "apps" / "frontend" / "src" / "console" / "FlowConsole.tsx"

ZH_NAME = "灵构工坊"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_chinese_product_name_is_the_one_the_project_uses():
    """Pin the name itself, so a rename is a deliberate edit to this test."""

    source = _source(I18N_PATH)
    assert ZH_NAME in source, (
        f"{ZH_NAME} is missing from i18n.ts; the Chinese UI has no product name"
    )


def test_brand_name_is_translated_not_hardcoded():
    """Neither shell may ship a literal "Fantasy Agent" heading.

    A hardcoded brand string shows English inside a Chinese UI, and no amount of
    dictionary work can fix it because the JSX never calls the translator.
    """
    offenders: list[str] = []

    for path in (STUDIO_SHELL_PATH, FLOW_CONSOLE_PATH):
        for line in _source(path).splitlines():
            stripped = line.strip()
            if "Fantasy Agent" in stripped and stripped.startswith(
                ("<", "aria-label", "aria-label")
            ):
                offenders.append(f"{path.name}: {stripped}")

    assert not offenders, (
        "these brand strings are hardcoded in JSX and will render English in the "
        f'Chinese UI; route them through t("brandName"): {offenders}'
    )


def test_every_dictionary_exposes_a_brand_name_in_both_locales():
    """Both shell dictionaries need the key, or one view shows English.

    The console and the studio shell use separate dictionaries, so a key added
    to only one of them leaves the other view untranslated.
    """

    source = _source(I18N_PATH)

    for dictionary in ("consoleI18n", "studioI18n"):
        block = source.split(f"export const {dictionary}", 1)[1]
        block = block.split("\nexport const ", 1)[0]

        assert "brandName:" in block, (
            f"{dictionary} has no brandName key, so its brand heading falls back "
            "to a fallback or an empty string"
        )
        assert "productLabel:" in block, f"{dictionary} lost its productLabel key"


def test_the_chinese_brand_name_is_not_mixed_with_english():
    """A Chinese label carrying an English suffix is the bug that started this.

    `documentTitle` used to be "灵构工坊 Studio". The English word on a Chinese
    string is what made the two names look like two different products.
    """

    source = _source(I18N_PATH)
    zh_block = source.split('"zh-CN": {', 1)[1]

    offenders = [
        line.strip() for line in zh_block.splitlines() if ZH_NAME in line and "Studio" in line
    ]
    assert not offenders, f"these Chinese labels still carry the English word 'Studio': {offenders}"


def test_the_window_title_is_the_chinese_product_name():
    """The desktop window title is user-facing, so it follows the Chinese rule."""

    from importlib.util import module_from_spec, spec_from_file_location

    launcher_path = REPO_ROOT / "apps" / "studio" / "desktop.py"
    spec = spec_from_file_location("fantasy_agent_desktop_title", launcher_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    import sys

    sys.modules["fantasy_agent_desktop_title"] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("fantasy_agent_desktop_title", None)

    assert module.STUDIO_TITLE == ZH_NAME, (
        f"window title is {module.STUDIO_TITLE!r}; it should be {ZH_NAME!r}"
    )


def test_implementation_identifiers_stay_english():
    """The rename must not leak into package, class or tool identifiers.

    AGENTS.md: implementation identifiers stay English. Renaming
    `fantasy_agent` or the FastAPI app slug would break 39 modules and every
    import in the suite for a cosmetic gain.
    """

    import tomllib

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    assert config["project"]["name"] == "fantasy-agent", (
        "the distribution name must stay 'fantasy-agent'"
    )

    packages = config["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "fantasy_agent*" in packages, packages

    # The Chinese name must not appear as a Python identifier anywhere.
    py_sources = list((REPO_ROOT / "fantasy_agent").rglob("*.py"))
    assert py_sources, "expected Python sources under fantasy_agent/"
    for path in py_sources:
        if ".venv" in str(path):
            continue
        assert ZH_NAME not in path.read_text(encoding="utf-8"), (
            f"{path.name} contains the Chinese product name; keep implementation "
            "identifiers in English"
        )
