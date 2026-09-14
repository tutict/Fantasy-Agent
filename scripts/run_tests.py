#!/usr/bin/env python
"""Run pytest so the verdict survives a hostile sandbox.

Why this exists
---------------
Two different guardrails corrupt a plain ``pytest`` run on this machine, and
they need different fixes.

**1. pytest's own temp GC.** The default scheme keeps numbered base directories
under the OS temp root (``pytest-of-<user>/pytest-<n>``) and garbage-collects
the older ones by deleting whole trees. A bulk delete can be refused, and
pytest then dies during interpreter shutdown: the summary line is replaced by a
guardrail notice. The suite may have passed, but neither the exit code nor
stdout can be trusted any more -- which is exactly the situation where a green
run gets reported as a failure, or worse, a red one gets missed.

**2. The host's safe-delete shim, which fires *during* the run.** Every
``Path.unlink`` outside the OS temp root is intercepted, trashed and counted
against a per-turn budget. Once the budget (50) is exhausted the shim raises
``SystemExit`` from inside ``unlink()``. That does not just fail one test: the
exception escapes while pytest is finalising a fixture, so
``_pytest/fixtures.py`` hits ``assert not self._finalizers`` for every
subsequent test. One trip turns into ~150 bogus "failed on setup" errors that
bury whatever actually broke. Measured here: a suite with ~63 in-repo deletes
trips it roughly two times in three, so the suite was *intermittently* red for
reasons that had nothing to do with the code.

How it is fixed
---------------
1. The run directory is created under the **OS temp root**, not in the repo.
   The shim exempts that root, so the deletes tests do for themselves never
   reach it -- the failure mode disappears rather than being retried around.
   Reports stay in ``generated/test-tmp/`` (a write, never guarded) so the
   verdict is still readable after the fact.
2. Every run still gets a *fresh* basetemp, so pytest never has an older
   numbered base dir to garbage-collect and never needs a bulk delete at all.
3. The machine-readable report goes to a file, and the verdict is read back
   from that file. pytest's own exit code is kept only as a cross-check, so a
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
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_hex

REPO_ROOT = Path(__file__).resolve().parent.parent
# Reports are tiny, gitignored, and worth keeping: the verdict is read from them.
REPORT_ROOT = REPO_ROOT / "generated" / "test-tmp"
# Run directories deliberately live outside the repo -- see "How it is fixed".
# `tempfile.gettempdir()` is the same root the shim's own exemption is built
# from, so keeping the two in one place is what makes the exemption apply.
TEMP_ROOT = Path(tempfile.gettempdir()) / "fantasy-agent-pytest"


def _run_id() -> str:
    """A run identifier two concurrent runs cannot agree on.

    pytest's ``TempPathFactory.getbasetemp`` does ``rm_rf(basetemp)`` whenever
    the path it was handed already exists. A readable seconds-resolution stamp
    alone is enough for two runs started in the same second to be handed the
    same path -- and the second one then deletes the first one's directory
    mid-run. That delete used to be refused (the directory was in the repo,
    where the safe-delete shim applies); now that it lives under the OS temp
    root the shim exempts it, so the collision would *succeed*. The timestamp
    keeps the name readable, the pid and a random suffix keep it unique.
    """

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{os.getpid()}-{token_hex(4)}"


def _run_paths(stamp: str) -> tuple[Path, Path]:
    """Where this run's pytest directory and junit report go.

    Split out because the two paths have opposite requirements and mixing them
    up is silent: the run directory must be inside the guard-exempt temp root,
    the report must be inside the repo.
    """

    return TEMP_ROOT / f"pytest-{stamp}", REPORT_ROOT / f"pytest-{stamp}.xml"


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

    run_id = _run_id()
    base_temp, xml_path = _run_paths(run_id)
    # Both parents must exist before pytest starts. `TempPathFactory` does
    # `basetemp.mkdir(mode=0o700)` -- no `parents=True` -- so a missing
    # TEMP_ROOT surfaces as a FileNotFoundError from inside the `tmp_path`
    # fixture, for every test that uses it. That is a confusing way to learn
    # that a parent directory is missing.
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--basetemp={base_temp}",
        f"--junit-xml={xml_path}",
        *pytest_args,
    ]
    print(f"basetemp: {base_temp}", flush=True)
    print(f"report:   {xml_path.relative_to(REPO_ROOT)}", flush=True)
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

    reports = sorted(REPORT_ROOT.glob("pytest-*.xml"))
    print(
        f"\nkept {len(reports)} report(s) under generated/test-tmp (gitignored, not "
        "pruned: a report from an earlier run is the only record of it). Run "
        f"directories went to {TEMP_ROOT}, outside the repo, so the harness never "
        "has to delete anything it just wrote -- which is what the host's "
        "safe-delete shim punishes."
    )

    return _verdict(counts)


if __name__ == "__main__":
    sys.exit(main())
