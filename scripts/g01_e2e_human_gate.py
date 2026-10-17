"""End-to-end: a decided gate is what lets a Godot route finish.

Proves G-01's second acceptance criterion -- run the orchestration with every
gated stage confirmed, decide the human gate through the decision endpoint, and
``GET /api/orchestration/{id}`` then shows ``godot_quick_play`` with a real
outcome instead of the permanent ``blocked`` the gate used to guarantee.

Drives the Studio endpoint *functions* directly rather than over HTTP: this
repo's tests and scripts do the same (there is no httpx here, and a live server
would make the script's assertions depend on a port). The calls, the payload
shapes and the session registry are the real ones.

The model is stubbed to answer immediately, and the stub still makes the two
tool calls whose outputs the orchestrator's own exit checks read -- the
planning call, so the three plan checks have a plan, and the project call, so
the Godot project check has a project. A pass that produced neither would fail
its stages for reasons that have nothing to do with the gate, which is the one
thing this script is about.

The scratch workspace lives under ``generated/`` (gitignored) rather than next
to this script, same reasoning as ``g02_e2e_exit_checks.py``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# The planning tool the stub calls goes through `llm_enabled()`, which honours
# this flag before the saved UI toggle. Set explicitly so the script proves the
# same thing on a machine whose settings have the provider switched on.
os.environ["FANTASY_AGENT_USE_LLM"] = "0"

# Imported after the sys.path insert on purpose: this script drives the app
# module from the repo root without installing anything. No `noqa: E402`
# needed -- this repo's ruff set does not enable that rule.
from fantasy_agent import llm
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.human_decision import decision_record_path
from fantasy_agent.workflows import run_director_workflow

PROMPT = "a stealth courier escapes a haunted train station in ten minutes"
WORKSPACE = REPO_ROOT / "generated" / "g01-e2e"


def _load_studio_app():
    module_path = REPO_ROOT / "apps" / "studio" / "app" / "main.py"
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The sandbox, not the repository: an output directory inside the repo is
    # one `git add -A` away from committing a whole generated Godot project.
    module.REPO_ROOT = WORKSPACE
    module._ORCHESTRATION_SESSIONS.clear()
    return module


def _tool_call(name: str, **arguments) -> llm.ModelReply:
    """A reply that asks for one tool, in the shape ``agent_loop`` echoes back."""

    call_id = f"call-{name}"
    return llm.ModelReply(
        text="",
        tool_calls=[llm.ToolCallRequest(id=call_id, name=name, arguments=arguments)],
        raw={"output": [{"type": "function_call", "call_id": call_id, "name": name}]},
    )


def _install_stub() -> dict[str, bool]:
    """Answer immediately, making the two calls the exit checks depend on.

    Which stage is speaking is read off the tools it was offered rather than
    off a call counter: the stub has to behave the same way whichever stage
    dispatches first, and the offered set is the one fact that identifies it.
    """

    from fantasy_agent import agent_loop

    made = {"planned": False, "created": False}

    def stub(*, instructions, messages, tools, max_tokens=0, model=None):
        offered = {spec["name"] for spec in tools}
        if "generate_game_production_plan" in offered and not made["planned"]:
            made["planned"] = True
            return _tool_call(
                "generate_game_production_plan",
                prompt=PROMPT,
                engine_version="Godot 4",
            )
        if "create_godot_project_structure" in offered and not made["created"]:
            made["created"] = True
            return _tool_call("create_godot_project_structure", write_files=True)
        return llm.ModelReply(text="stage complete")

    agent_loop.complete_with_tools = stub
    return made


def _by_id(payload: dict) -> dict[str, dict]:
    return {stage["stage_id"]: stage for stage in payload["stages"]}


def _report(payload: dict) -> None:
    for stage in sorted(payload["stages"], key=lambda entry: entry["order"]):
        print(
            f"  {stage['stage_id']:28s} {stage['status']:20s}"
            + (f" checks={stage['checks']}" if stage["checks"] else "")
            + (f" detail={stage['detail'][:80]}" if stage["detail"] else "")
        )


def main() -> int:
    module = _load_studio_app()
    _install_stub()

    plan_doc = run_director_workflow(
        PromptRequest(prompt=PROMPT, engine_version="Godot 4"), use_llm=False
    )
    gated = [
        stage.id
        for stage in plan_doc.production_pipeline.stages
        if stage.requires_confirmation
    ]
    print(f"plan: {len(plan_doc.production_pipeline.stages)} stages; gated: {gated}")

    # ── pass 1: everything confirmed, the gate still waiting ─────────────────
    first = module.run_orchestration(
        module.OrchestrationRunRequest(
            plan=plan_doc,
            confirm_stages=gated,
            allow_write=True,
            allow_execute=True,
        )
    )
    session_id = first["session_id"]
    print(f"\npass 1 (session {session_id}): status={first['status']}")
    _report(first)

    assert first["status"] == "awaiting_human", first["status"]
    assert first["pending_human_gates"] == ["creative_review"], first["pending_human_gates"]
    gate = _by_id(first)["creative_review"]
    assert gate["kind"] == "human"
    assert gate["status"] == "awaiting_human", gate
    assert gate["human_resolution"] is None, gate
    blocked = _by_id(first)["godot_quick_play"]
    assert blocked["status"] == "blocked", blocked
    assert not blocked["dispatched"], "a stage behind an undecided gate ran anyway"

    # ── the decision, and only the decision ──────────────────────────────────
    decided = module.decide_orchestration_stage(
        session_id,
        "creative_review",
        module.HumanDecisionRequest(decision="approved"),
        engine="godot",
    )
    print(f"\ndecision recorded: {decided['human_decisions']}")
    assert decided["human_decisions"] == {"creative_review": "approved"}
    assert decided["pending_human_gates"] == []
    assert _by_id(decided)["creative_review"]["human_resolution"] == "approved"
    # The endpoint deliberately does not advance the plan; the run endpoint
    # stays the single path that dispatches a stage.
    assert decided["status"] == "awaiting_human", decided["status"]
    record = decision_record_path(session_id, engine_key="godot", workspace_root=WORKSPACE)
    assert not record.exists(), "the record belongs to the stage's own pass, not the click"

    # ── pass 2: the gate resolves and the route finishes ─────────────────────
    second = module.run_orchestration(
        module.OrchestrationRunRequest(
            plan=plan_doc,
            session_id=session_id,
            allow_write=True,
            allow_execute=True,
        )
    )
    print(f"\npass 2: status={second['status']}")
    _report(second)

    assert second["status"] == "done", second["status"]
    cards = _by_id(second)
    assert cards["creative_review"]["status"] == "done", cards["creative_review"]
    # The acceptance criterion, and the reason the gate mattered: the stage the
    # deadlock used to hold at `blocked` forever has now run.
    quick_play = cards["godot_quick_play"]
    assert quick_play["status"] == "done", quick_play
    assert quick_play["dispatched"] is True, quick_play
    assert quick_play["checks"] == ["validate_godot_project"], quick_play
    assert cards["optimization_testing"]["status"] == "done", cards["optimization_testing"]

    # The decision's own record, written by the pass that resolved the gate.
    assert record.exists(), "the gate reads done next to a file nobody wrote"
    written = record.read_text(encoding="utf-8")
    assert "decision: approved" in written, written
    assert f"stage_id: {gate['stage_id']}" in written, written

    # ── a restart after the fact reads the same board ────────────────────────
    module._ORCHESTRATION_SESSIONS.clear()
    read_back = module.orchestration_state(session_id, "godot")
    print(f"\nrestart read-back: found={read_back['found']} status={read_back['status']}")
    _report(read_back)

    assert read_back["found"] is True
    assert read_back["status"] == "done", read_back["status"]
    assert _by_id(read_back)["creative_review"]["status"] == "done"
    assert _by_id(read_back)["creative_review"]["human_resolution"] == "approved"
    assert _by_id(read_back)["godot_quick_play"]["status"] == "done"

    print("\nOK: the decided gate unblocked the route, and a restart still reads it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
