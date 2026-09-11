"""Tests for `scripts/run_tests.py`, the sandbox-proof pytest entry point.

The runner exists because pytest's own exit code and summary line are unreliable
on this machine: a host guardrail intercepts the bulk delete of old temp dirs and
kills pytest during shutdown. The whole value of the runner is that its verdict
comes from the junit report instead -- so the report parsing and the verdict are
the parts worth pinning down here.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import run_tests


def _write_suite(path: Path, **counts: int) -> Path:
    """Write a minimal junit report shaped like pytest's own output."""

    attributes = " ".join(f'{key}="{value}"' for key, value in counts.items())
    path.write_text(f"<testsuites><testsuite {attributes} /></testsuites>", encoding="utf-8")
    return path


def test_read_report_counts_a_passing_suite(tmp_path: Path) -> None:
    path = _write_suite(tmp_path / "r.xml", tests=484, failures=0, errors=0, skipped=8)
    assert run_tests._read_report(path) == {
        "tests": 484,
        "failures": 0,
        "errors": 0,
        "skipped": 8,
        "passed": 476,
    }


def test_read_report_counts_failures_and_errors(tmp_path: Path) -> None:
    path = _write_suite(tmp_path / "r.xml", tests=10, failures=2, errors=1, skipped=3)
    counts = run_tests._read_report(path)
    assert counts is not None
    assert counts["passed"] == 4


def test_read_report_rejects_a_missing_or_corrupt_report(tmp_path: Path) -> None:
    assert run_tests._read_report(tmp_path / "absent.xml") is None

    corrupt = tmp_path / "corrupt.xml"
    corrupt.write_text("<testsuites><testsuite", encoding="utf-8")
    assert run_tests._read_report(corrupt) is None


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ({"tests": 484, "failures": 0, "errors": 0, "skipped": 8}, 0),
        ({"tests": 10, "failures": 1, "errors": 0, "skipped": 0}, 1),
        ({"tests": 10, "failures": 0, "errors": 1, "skipped": 0}, 1),
        # Nothing collected is a broken invocation, never a green suite.
        ({"tests": 0, "failures": 0, "errors": 0, "skipped": 0}, 2),
    ],
)
def test_verdict_maps_a_report_to_an_exit_code(counts: dict[str, int], expected: int) -> None:
    assert run_tests._verdict(counts) == expected


def test_failing_cases_names_the_tests_that_failed(tmp_path: Path) -> None:
    path = tmp_path / "r.xml"
    path.write_text(
        '<testsuites><testsuite tests="2" failures="1">'
        '<testcase classname="tests.test_x" name="test_ok" />'
        '<testcase classname="tests.test_x" name="test_bad">'
        '<failure message="AssertionError: nope">traceback</failure>'
        "</testcase></testsuite></testsuites>",
        encoding="utf-8",
    )
    found = run_tests._failing_cases(path)
    assert len(found) == 1
    assert "test_bad" in found[0]


def test_a_run_without_a_report_never_claims_success() -> None:
    """An unusable run must report 2, not 0 -- a false green is the whole risk."""

    captured = io.StringIO()
    # The bogus flag makes pytest bail before it can write a report.
    with contextlib.redirect_stderr(captured):
        code = run_tests.main(["--basetemp-is-not-a-pytest-flag"])
    assert code == 2
    assert "No usable junit report" in captured.getvalue()
