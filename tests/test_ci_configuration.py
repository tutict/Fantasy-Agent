"""Checks for repository CI gates that are easy to remove accidentally."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_ci_enforces_the_ui_metric_budgets():
    workflow = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["frontend"]["steps"]

    assert any(step.get("run") == "python scripts/ui_metrics.py --check" for step in steps)
