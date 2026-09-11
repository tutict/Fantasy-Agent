#!/usr/bin/env python
"""Run pytest so the verdict survives a hostile sandbox.

Why this exists
---------------
pytest's default temp scheme keeps numbered base directories under the OS temp
root (``pytest-of-<user>/pytest-<n>``) and garbage-collects the older ones by
deleting whole trees. On this machine a host guardrail intercepts bulk deletes:
the delete is refused, pytest dies during interpreter shutdown, and the summary
line is replaced by a guardrail notice. The suite may have passed, but neither
the exit code nor stdout can be trusted any more -- which is exactly the
situation where a green run gets reported as a failure, or worse, a red one gets
missed.

How it is fixed
---------------
1. Every run gets a *fresh* ``--basetemp`` under ``generated/test-tmp/``. pytest
   never has an older numbered base dir to garbage-collect, so it never needs a
   bulk delete. Nothing is removed at the end either, which is why stale run
   directories accumulate -- they are gitignored, and this script reports the
   count rather than deleting them (deleting is the very thing that breaks).
2. The machine-readable report goes to a file, and the verdict is read back from
   that file. pytest's own exit code is kept only as a cross-check, so a
   corrupted shutdown cannot turn a passing run into a failure.

Usage
-----
    python scripts/run_tests.py                     # whole suite
    python scripts/run_tests.py tests/test_llm.py   # extra args go to pytest
    python scripts/run_tests.py -k unreal -x

Exit codes: 0 all passed, 1 failures or errors, 2 no report was produced.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# `generated/*` is gitignored, so run directories never show up in git status.
RUN_ROOT = REPO_ROOT / "generated" / "test-tmp"


def _read_report(xml_path: Path) -> dict[str, int] | None:
    """Return the counts from a junit report, or None if it is unusable."""

    if not xml_path.is_file():
        return None
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return None

    keys = ("tests", "failures", "errors", "skipped")
    if root.tag == "testsuites":
        counts = {key: sum(int(suite.get(key, 0)) for suite in root) for key in keys}
    else:
        counts = {key: int(root.get(key, 0)) for key in keys}
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    return counts


def _verdict(counts: dict[str, int]) -> int:
    """Exit code implied by a report.

    A run that collected nothing is a broken invocation, not a green suite:
    reporting it as success is how "the tests still pass" quietly becomes untrue.
    """

    if counts["tests"] == 0:
        return 2
    return 1 if counts["failures"] or counts["errors"] else 0


def _failing_cases(xml_path: Path) -> list[str]:
    """Names of the tests that failed or errored, in report order."""

    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        return []

    names: list[str] = []
    for case in root.iter("testcase"):
        bad = list(case.findall("failure")) + list(case.findall("error"))
        if bad:
            label = f"{case.get('classname', '')}::{case.get('name', '')}"
            names.append(f"{label}  <- {bad[0].get('message', '').splitlines()[:1]}")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run pytest with a fresh basetemp and report from junit XML."
    )
    # parse_known_args keeps pytest's own flags (-k, -x, -q, ...) out of
    # argparse's hands, so they reach pytest instead of being rejected here.
    _, pytest_args = parser.parse_known_args(argv)

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    base_temp = RUN_ROOT / f"pytest-{stamp}"
    xml_path = RUN_ROOT / f"pytest-{stamp}.xml"
    RUN_ROOT.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--basetemp={base_temp}",
        f"--junit-xml={xml_path}",
        *pytest_args,
    ]
    print(f"basetemp: {base_temp.relative_to(REPO_ROOT)}", flush=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)

    counts = _read_report(xml_path)
    if counts is None:
        print(
            f"\nNo usable junit report at {xml_path}.\n"
            "pytest probably failed before running any test; its exit code was "
            f"{completed.returncode}.",
            file=sys.stderr,
        )
        return 2

    print(
        f"\ntests={counts['tests']} passed={counts['passed']} "
        f"failed={counts['failures']} errors={counts['errors']} skipped={counts['skipped']}"
    )
    for name in _failing_cases(xml_path):
        print(f"  FAIL {name}")

    if counts["tests"] == 0:
        print(
            "\nNo tests were collected -- check the arguments and testpaths.",
            file=sys.stderr,
        )

    if completed.returncode != 0 and not (counts["failures"] or counts["errors"]):
        print(
            f"\nnote: pytest exited {completed.returncode} while the report shows no "
            "failure -- that is the sandbox guardrail, not a test failure.",
            file=sys.stderr,
        )

    stale = sorted(RUN_ROOT.glob("pytest-*"))
    print(
        f"\nkept {len(stale)} run dir/report(s) under generated/test-tmp. They are "
        "gitignored and deliberately not pruned here: deleting them is the bulk-"
        "delete operation this script exists to avoid."
    )

    return _verdict(counts)


if __name__ == "__main__":
    sys.exit(main())
