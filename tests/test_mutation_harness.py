"""The mutation harness is the layer that keeps the other guards honest.

It is also the layer whose own failure is invisible. A case whose needle stopped
matching prints ``SKIP``; a case whose guard id was renamed exits non-zero for
the wrong reason, which the harness would read as a caught mutation if it went
by exit code alone. Either way the case checks nothing while the run still
reports that the work was done.

So the harness's *inputs* are checked here: every needle, every named guard,
every target file. It is all static -- no mutation is applied -- so it runs in
CI on every push, where the harness itself only runs when somebody remembers to.
The heavy half, proving each guard really goes red, stays a deliberate run:

    python scripts/mutation_check_all_guards.py
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from scripts import mutation_check_all_guards as harness

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The node-id shapes the harness uses: ``tests/test_foo.py::test_bar``, and the
#: parametrised ``tests/test_foo.py::test_bar[axis]`` for a guard that is one leg
#: of a parametrised test.
#:
#: The bare name of a parametrised test is the id that has to be rejected: pytest
#: collects *every* leg for it, so a case meant to pin one axis would run the
#: whole roster and call whatever failed first "caught". A pinned parameter is
#: checked against the module's own source below.
NODE_ID = re.compile(r"^(tests/[\w./-]+\.py)::(\w+)(?:\[([^\]]+)\])?$")

#: A parametrisation decorator sitting above the guard it names, allowing other
#: decorators in between (a parametrised test that also carries a skipif).
_PARAMETRIZED = re.compile(
    r"@pytest\.mark\.parametrize\(.*?\)\s*\n(?:\s*@[^\n]*\n)*\s*def (\w+)\(", re.DOTALL
)


def _cases() -> list[tuple[str, str, bytes, bytes, str]]:
    return list(harness.CASES)


def test_case_labels_are_unique():
    """The label is how a case is identified in the summary and in exemptions."""

    labels = [case[0] for case in _cases()]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    assert duplicates == [], f"duplicate case labels: {duplicates}"


def test_every_case_targets_a_file_that_exists():
    missing = sorted({case[1] for case in _cases() if not (REPO_ROOT / case[1]).is_file()})
    assert missing == [], f"cases mutate files that are gone: {missing}"


def test_every_needle_still_matches_exactly_once():
    """A needle matching 0 or 2 times mutates nothing.

    The harness reports that as ``SKIP`` and fails -- but only the next time
    somebody runs it. Checked here so a rename or a reformat is caught by CI
    instead, and with the same line-ending normalisation the harness applies:
    the index is LF while most of the working tree is CRLF, so a probe written
    with ``\\n`` matches nothing in a CRLF file and the failure looks like a
    dead guard rather than a stale needle.
    """

    stale = []
    for label, relative, needle, _mutant, _test in _cases():
        original = (REPO_ROOT / relative).read_bytes()
        eol = b"\r\n" if b"\r\n" in original else b"\n"
        count = original.count(harness._as_eol(needle, eol))
        if count != 1:
            # The instinct is to fix the needle. For a file nobody edited the
            # needle is not what is wrong: a run killed mid-case leaves its
            # mutation on disk, and `finally` does not run on a kill.
            stale.append(
                f"{label!r}: needle appears {count}x in {relative} -- a rename, or the "
                f"residue of a killed run; `git diff {relative}` first"
            )
    assert stale == [], "\n".join(stale)


def test_no_case_replaces_a_needle_with_itself():
    """A mutant equal to the needle rewrites the file to what it already said."""

    no_ops = [case[0] for case in _cases() if case[2] == case[3]]
    assert no_ops == [], f"these cases would mutate nothing: {no_ops}"


def test_line_endings_are_normalised_to_the_file_on_disk():
    """The normalisation is what makes a CRLF tree and an LF tree behave alike."""

    probe = b"a\nb\n"

    assert harness._as_eol(probe, b"\r\n") == b"a\r\nb\r\n"
    assert harness._as_eol(probe, b"\n") == b"a\nb\n"
    # A probe written with CRLF is normalised first, so it cannot end up with
    # doubled carriage returns on either kind of file.
    assert harness._as_eol(b"a\r\nb\n", b"\r\n") == b"a\r\nb\r\n"
    assert harness._as_eol(b"a\r\nb\n", b"\n") == b"a\nb\n"


def test_every_named_guard_exists():
    """A renamed guard is indistinguishable from a caught mutation by exit code.

    That is why the harness reads the runner's counts instead -- and why the
    names are pinned here as well: a case that points at nothing would otherwise
    only be discovered by the one run where it suddenly means nothing.

    A pinned parameter (``test_bar[axis]``) is checked against the file it lives
    in. This does not prove pytest collects the leg -- a parametrisation built
    from an expression such as ``sorted(BURST_VERBS)`` cannot be resolved without
    importing the module -- but the harness fails a case it cannot collect
    (``NO RUN (unproven)``), so a wrong parameter surfaces there; what this
    catches is the typo, before anyone spends a run on it.
    """

    problems = _node_id_problems(_cases(), _read_source)
    assert problems == [], "\n".join(problems)


def _read_source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _node_id_problems(
    cases: list[tuple[str, str, bytes, bytes, str]],
    read: Callable[[str], str],
) -> list[str]:
    """Every reason a pinned guard id is unusable, for one case list.

    Separated from the check that runs it so the rule can be handed a case list
    that breaks it -- see ``test_a_bare_id_for_a_parametrised_guard_is_rejected``
    for why that matters.
    """

    problems: list[str] = []
    sources: dict[str, str] = {}
    parametrised: dict[str, set[str]] = {}
    for label, _target, _needle, _mutant, test in cases:
        match = NODE_ID.match(test)
        if match is None:
            problems.append(f"{label!r}: unrecognised node id {test!r}")
            continue
        path, name, parameter = match.group(1), match.group(2), match.group(3)
        if path not in sources:
            sources[path] = read(path)
            parametrised[path] = {
                found.group(1) for found in _PARAMETRIZED.finditer(sources[path])
            }
        source = sources[path]
        if re.search(rf"^def {name}\(", source, re.MULTILINE) is None:
            problems.append(f"{label!r}: {name} is not defined in {path}")
        elif parameter is None and name in parametrised[path]:
            problems.append(
                f"{label!r}: {name} is parametrised, so the bare id collects every "
                "leg -- pin the one this case is about"
            )
        elif parameter is not None and parameter not in source:
            problems.append(
                f"{label!r}: {name} pins [{parameter}], which appears nowhere in {path}"
            )
    return problems


#: One guard, parametrised, as its own module: the smallest thing that can be
#: checked against the rules above without touching the repository.
_SYNTHETIC_PARAMETRISED = '''\
import pytest


@pytest.mark.parametrize("axis", ["a", "b"])
def test_one_leg_per_axis(axis):
    assert axis
'''

_SYNTHETIC_PLAIN = '''\
def test_not_parametrised():
    assert True
'''


def test_a_bare_id_for_a_parametrised_guard_is_rejected():
    """The rule needs a subject, and the case list has stopped providing one.

    Every parametrised pin in ``CASES`` now names its leg, so nothing in the real
    list ever reaches the branch that rejects a bare id -- it would pass whether
    the rule worked or had been deleted. That is the same failure mode this whole
    module exists to catch, one level up, so the rule is handed a synthetic case
    that breaks it.
    """

    sources = {"tests/test_synthetic.py": _SYNTHETIC_PARAMETRISED}

    def read(path: str) -> str:
        return sources[path]

    bare = [
        ("X1", "tests/test_synthetic.py", b"a", b"b", "tests/test_synthetic.py::test_one_leg_per_axis")
    ]
    problems = _node_id_problems(bare, read)
    assert len(problems) == 1, problems
    assert "parametrised" in problems[0], problems

    # The same guard, pinned: nothing to complain about.
    pinned = [
        (
            "X1",
            "tests/test_synthetic.py",
            b"a",
            b"b",
            "tests/test_synthetic.py::test_one_leg_per_axis[a]",
        )
    ]
    assert _node_id_problems(pinned, read) == []

    # A parameter that is not in the file at all, and a guard that is not in it
    # either, both still have to be caught.
    sources["tests/test_synthetic.py"] = _SYNTHETIC_PARAMETRISED
    typo = [
        (
            "X1",
            "tests/test_synthetic.py",
            b"a",
            b"b",
            "tests/test_synthetic.py::test_one_leg_per_axis[axes]",
        )
    ]
    assert "appears nowhere" in _node_id_problems(typo, read)[0]

    sources["tests/test_synthetic.py"] = _SYNTHETIC_PLAIN
    gone = [
        ("X1", "tests/test_synthetic.py", b"a", b"b", "tests/test_synthetic.py::test_missing")
    ]
    assert "is not defined" in _node_id_problems(gone, read)[0]


def test_engine_requirements_name_cases_that_still_exist():
    """The mapping excuses a case, so an orphaned key hides a guard."""

    labels = {case[0] for case in _cases()}
    orphaned = sorted(set(harness.ENGINE_REQUIREMENTS) - labels)
    assert orphaned == [], (
        f"ENGINE_REQUIREMENTS no longer matches a case label: {orphaned}. "
        "A renamed label would excuse no case -- the guard would simply run "
        "again and fail on a machine that has no engine."
    )


def test_engine_requirements_name_engines_the_harness_can_probe():
    """An unprobeable engine name would crash the run instead of excusing a case."""

    known = set(harness._engine_probes())
    unknown = sorted(set(harness.ENGINE_REQUIREMENTS.values()) - known)
    assert unknown == [], f"no probe for {unknown}; known engines are {sorted(known)}"
