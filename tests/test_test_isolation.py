"""Guards for the test suite's isolation from itself.

Importing a module and *re-executing* it in place are different operations, and
the second one is a hazard the suite has now paid for once: ``importlib.reload``
rebinds every class defined in that module to a new object. Any module that did
``from fantasy_agent.llm import LLMError`` at import time keeps the *old* class,
so after a reload ``except LLMError`` silently stops catching ``llm.LLMError``.

That is a quiet, order-dependent break -- ``tests/test_llm_generation.py`` used
to reload ``fantasy_agent.llm``, and the damage only surfaced in a full run,
where ``tests/test_orchestrator.py`` happened to be the first test that depended
on the exception identity. File ordering, not code, decided the verdict.

The sanctioned alternative, used by the tray, launcher and llm probes, is to
execute a copy of the source in a throwaway module that is registered in
``sys.modules`` before ``exec_module`` runs. Nothing live is touched.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

# Escape hatch, currently unused: a file listed here may reload in place. Keep it
# empty unless there is a written reason the probe pattern does not fit.
ALLOWED: tuple[str, ...] = ()


def _reload_targets(source: str, filename: str = "<probe>") -> list[tuple[int, str]]:
    """In-place ``reload`` calls in ``source``, located through the AST.

    Located through the AST rather than by searching for text on purpose:
    ``test_llm_generation.py`` explains this hazard in a docstring, and a text
    search would flag the explanation that documents the rule. Only real calls
    count -- prose, comments and string literals cannot match.
    """

    tree = ast.parse(source, filename=filename)

    module_aliases = {"importlib"}
    reload_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "importlib":
                    module_aliases.add(alias.asname or "importlib")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "importlib":
            for alias in node.names:
                if alias.name == "reload":
                    reload_aliases.add(alias.asname or "reload")

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        qualified = (
            isinstance(func, ast.Attribute)
            and func.attr == "reload"
            and isinstance(func.value, ast.Name)
            and func.value.id in module_aliases
        )
        bare = isinstance(func, ast.Name) and func.id in reload_aliases
        if qualified or bare:
            found.append((node.lineno, ast.unparse(node)))

    return sorted(found)


def _test_files() -> list[Path]:
    """Every test module in the suite.

    A single source for the list on purpose: when the guard and its floor each
    carried their own copy of this glob, breaking one left the other intact and
    the floor said nothing -- measured, not assumed (mutant I3).
    """

    return sorted(TESTS_DIR.glob("test_*.py"))


def test_no_test_reloads_a_live_module_in_place():
    """A reload rebinds that module's classes and breaks importers of them."""

    offenders: list[str] = []

    for path in _test_files():
        if path.name in ALLOWED:
            continue
        source = path.read_text(encoding="utf-8")
        for lineno, expression in _reload_targets(source, str(path)):
            offenders.append(f"{path.name}:{lineno}: {expression}")

    assert not offenders, (
        "these tests re-execute a live module, which rebinds its classes and makes "
        "`except <SomethingError>` in any importer stop matching; load a copy "
        "through spec_from_file_location + sys.modules instead: " + f"{offenders}"
    )


def test_the_scan_actually_reaches_the_suite():
    """Floor on the file list, so a glob that matches nothing cannot pass."""

    scanned = [path.name for path in _test_files()]

    assert len(scanned) > 30, f"only {len(scanned)} test files matched; the glob is wrong"
    assert "test_llm_generation.py" in scanned, "the file this guard was written for is not scanned"


def test_the_detector_finds_calls_and_ignores_prose():
    """Positive and negative control for the detector itself.

    Without this, a detector that always returned ``[]`` would read as a clean
    suite -- the same vacuous-green shape the guard exists to prevent.
    """

    prose = (
        '"""Reloading via importlib.reload(llm) is forbidden here."""\n'
        "\n"
        "# importlib.reload(llm) used to happen on the next line\n"
        'RELOAD_HINT = "from importlib import reload"\n'
    )
    assert _reload_targets(prose) == [], "the detector matched prose instead of a call"

    qualified = (
        "import importlib\n"
        "from fantasy_agent import llm\n"
        "\n"
        "\n"
        "def refresh():\n"
        "    importlib.reload(llm)\n"
    )
    assert [line for line, _ in _reload_targets(qualified)] == [6], (
        "the detector missed `importlib.reload(x)`"
    )

    aliased = (
        "from importlib import reload as again\n"
        "from fantasy_agent import llm\n"
        "\n"
        "\n"
        "def refresh():\n"
        "    again(llm)\n"
    )
    assert len(_reload_targets(aliased)) == 1, (
        "the detector missed a reload imported by another name"
    )
