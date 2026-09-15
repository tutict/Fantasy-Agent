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
from pathlib import Path

from scripts import mutation_check_all_guards as harness

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The only node-id shape the harness uses: ``tests/test_foo.py::test_bar``.
#: A parametrised id would not match, which is deliberate -- a case that needs
#: one has to say so here rather than quietly collecting the wrong test.
NODE_ID = re.compile(r"^(tests/[\w./-]+\.py)::(\w+)$")


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
            stale.append(f"{label!r}: needle appears {count}x in {relative}")
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
    """

    missing = []
    for label, _target, _needle, _mutant, test in _cases():
        match = NODE_ID.match(test)
        if match is None:
            missing.append(f"{label!r}: unrecognised node id {test!r}")
            continue
        path, name = match.group(1), match.group(2)
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        if re.search(rf"^def {name}\(", source, re.MULTILINE) is None:
            missing.append(f"{label!r}: {name} is not defined in {path}")
    assert missing == [], "\n".join(missing)


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
