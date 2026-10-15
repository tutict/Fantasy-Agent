"""End-to-end: run a Godot orchestration and read the snapshot's checks.

Proves G-02's third acceptance criterion -- after one orchestrated pass, at
least two stages carry non-empty ``checks`` in the snapshot. The field, the
consumer and this script's assertion all arrived together on 2026-10-13: the
orchestrator had a complete exit-check consumer while ``_pipeline_stage`` had
no parameter to fill the field, so every stage declared an empty list and the
consumer was dead code.

The model is stubbed to answer without calling tools, which is the point: the
checks are run by the *orchestrator*, not by the agent, so a pass with zero
model turns still has to produce them. The Godot project is written by the real
``create_godot_project_structure`` tool so the project check has something true
to read.

The scratch workspace lives under ``generated/`` (gitignored) rather than next
to this script: an output directory inside ``scripts/`` is one ``git add -A``
away from committing a whole generated Godot project, which is how the first
version of this script left ``scripts/_g02_e2e/`` in ``git status``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_agent import llm
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.orchestration_state import load_state
from fantasy_agent.orchestrator import Orchestrator
from fantasy_agent.tool_registry import combined_registry
from fantasy_agent.workflows import run_director_workflow

PROMPT = "a stealth courier escapes a haunted train station in ten minutes"
WORKSPACE = Path(__file__).resolve().parents[1] / "generated" / "g02-e2e"
SESSION = "g02-e2e"


def main() -> int:
    plan_doc = run_director_workflow(
        PromptRequest(prompt=PROMPT, engine_version="Godot 4"), use_llm=False
    )
    pipeline = plan_doc.production_pipeline

    registry = combined_registry(WORKSPACE)
    registry.remember_plan(plan_doc.model_dump(mode="json"))
    created = registry.call(
        "create_godot_project_structure", {"write_files": True}, allow_write=True
    )
    print(f"create_godot_project_structure -> {created.status}")

    # The model answers immediately: no tool calls, no turns. Anything the
    # snapshot reports as checked therefore came from the orchestrator.
    def stub(**_kwargs):
        return llm.ModelReply(text="stage complete")

    from fantasy_agent import agent_loop

    agent_loop.complete_with_tools = stub

    orchestrator = Orchestrator(
        session_id=SESSION, workspace_root=WORKSPACE, registry=registry
    )
    result = orchestrator.run(
        pipeline,
        allow_write=True,
        allow_execute=True,
        confirm_stages=[stage.id for stage in pipeline.stages if stage.requires_confirmation],
    )

    print(f"run status: {result.status}")
    for outcome in result.stages:
        print(
            f"  {outcome.stage_id:28s} {outcome.status:20s} checks={outcome.checks}"
            + (f" detail={outcome.detail[:90]}" if outcome.detail else "")
        )

    snapshot = load_state(SESSION, engine_key="godot", workspace_root=WORKSPACE)
    assert snapshot is not None, "no snapshot was written"
    checked = {
        stage.stage_id: stage.checks
        for stage in snapshot.stages
        if stage.checks
    }
    print("\nsnapshot stages with non-empty checks:")
    print(json.dumps(checked, indent=2))

    assert len(checked) >= 2, f"expected >=2 checked stages, got {len(checked)}"
    print(f"\nOK: {len(checked)} stage(s) carry exit checks in the snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
