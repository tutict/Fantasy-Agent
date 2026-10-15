"""The human gate: what moves it is a decision, and only a decision.

Before this file a ``kind="human"`` stage could only ever answer
``awaiting_human``: ``_advance`` returned it unconditionally, the only path that
assigned ``done`` was the dispatch branch a human stage never reaches, and
nothing on the REST surface could write the decision that would unblock the
three stages behind ``creative_review``. A Godot route stopped at ``order=5``
forever and the orchestration layer contributed nothing to "playable and
verified".

What is pinned here, in the order the deadlock was taken apart:

- a decision resolves the gate (``approved`` -> done, dependents unblocked) and
  a refusal fails it (dependents stay blocked) -- the two halves of the
  vocabulary, which are not "approve" and "not approve";
- a plan that *arrives* with ``human_resolution`` already filled does not open
  the gate. ``_advance`` reads the runtime map and never the field, which is the
  same line AGENTS.md draws for ``confirmed``;
- the decision is durable before the stage counts as done, both as the record
  file the stage's ``artifacts`` name and as the snapshot a restart restores
  from -- a board showing ``done`` next to a file nobody wrote is the
  artifact-honesty bug G-03 spent on the playtest report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from fantasy_agent import llm
from fantasy_agent.contracts import ProductionPipeline, ProductionPipelineStage
from fantasy_agent.human_decision import decision_record_path, load_decision_record
from fantasy_agent.orchestration_state import load_state as load_snapshot
from fantasy_agent.orchestrator import (
    AWAITING_HUMAN,
    BLOCKED,
    DONE,
    FAILED,
    RUN_DONE,
    RUN_ERROR,
    Orchestrator,
)
from fantasy_agent.tool_registry import ToolRegistry, combined_registry

# Read off the live registry rather than assumed, same as test_orchestrator:
# the tier a tool sits in is the gate's business, and a test that guessed it
# would pass while proving nothing about the stage it claims to exercise.
READ_ONLY_TOOL = "extract_idea_seed"


def _stage(
    stage_id: str = "creative_review",
    *,
    order: int = 1,
    kind: str = "human",
    tools: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
    requires_confirmation: bool = False,
) -> ProductionPipelineStage:
    return ProductionPipelineStage(
        id=stage_id,
        order=order,
        title=stage_id,
        purpose=f"advance {stage_id}",
        owner_agent="director-agent",
        inputs=["PromptRequest"],
        outputs=[f"{stage_id}-output"],
        mcp_tools=list(tools),
        depends_on=list(depends_on),
        kind=kind,
        requires_confirmation=requires_confirmation,
    )


def _plan(*stages: ProductionPipelineStage) -> ProductionPipeline:
    return ProductionPipeline(
        project_name="probe", goal="prove the human gate", stages=list(stages)
    )


def _orchestrator(
    workspace_root: Path,
    *,
    registry: ToolRegistry | None = None,
    session_id: str = "s1",
) -> Orchestrator:
    return Orchestrator(
        session_id=session_id,
        workspace_root=workspace_root,
        registry=registry if registry is not None else combined_registry(workspace_root),
    )


class _FakeResponses:
    """Minimal Responses API stand-in; raises when the queue runs dry.

    So "the model was called when it should not have been" is a failure rather
    than a silently shorter list of payloads.
    """

    def __init__(self, replies: list[llm.ModelReply]):
        self.replies = list(replies)
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, *, instructions, messages, tools, max_tokens=0, model=None):
        self.payloads.append(
            {"instructions": instructions, "messages": list(messages), "tools": tools}
        )
        if not self.replies:
            raise AssertionError("the model was called more times than replies were queued")
        return self.replies.pop(0)


@pytest.fixture
def fake_complete(monkeypatch):
    def install(replies: list[llm.ModelReply]) -> _FakeResponses:
        fake = _FakeResponses(replies)
        # Patched on `agent_loop`, not on `llm`: the loop binds the name at
        # import time, so patching the source module would not be seen.
        monkeypatch.setattr("fantasy_agent.agent_loop.complete_with_tools", fake)
        return fake

    return install


# ── the decision moves the gate ──────────────────────────────────────────────


def test_a_resolved_human_stage_reaches_done_and_unblocks_dependents(fake_complete, tmp_path):
    """The whole point of the change, in one pass each side of the decision.

    The Godot route's ``creative_review`` is ``order=5``; ``asset_integration``
    and ``godot_quick_play`` sit behind it. A gate that stays
    ``awaiting_human`` forever is a run that never finishes, which is what this
    test would have shown before the HUMAN branch learned to look the decision
    up.
    """

    fake = fake_complete([llm.ModelReply(text="integrated")])
    plan = _plan(
        _stage("creative_review", order=1, kind="human", tools=()),
        _stage(
            "asset_integration",
            order=2,
            kind="agent",
            tools=(READ_ONLY_TOOL,),
            depends_on=("creative_review",),
        ),
    )
    orchestrator = _orchestrator(tmp_path)

    waiting = orchestrator.run(plan)

    assert waiting.outcome_for("creative_review").status == AWAITING_HUMAN
    assert waiting.outcome_for("asset_integration").status == BLOCKED
    assert waiting.status == AWAITING_HUMAN
    assert waiting.pending_human_gates == ["creative_review"]
    assert fake.payloads == [], "a gate nobody decided ran something anyway"

    orchestrator.resolve_human_stage("creative_review", "approved")

    decided = orchestrator.run(plan)

    gate = decided.outcome_for("creative_review")
    assert gate is not None
    assert gate.status == DONE
    assert "approved" in gate.detail
    dependent = decided.outcome_for("asset_integration")
    assert dependent is not None
    assert dependent.status == DONE
    assert dependent.dispatched is True
    assert decided.status == RUN_DONE
    assert decided.pending_human_gates == []
    # One dispatch, and it is the dependent's: the gate itself runs no tools.
    assert len(fake.payloads) == 1


def test_a_rejected_gate_fails_and_what_depends_on_it_stays_blocked(fake_complete, tmp_path):
    """The other half of the vocabulary, and why it is not "not approved".

    Sending a gate back is a real outcome with real consequences: the stages
    behind it must not run past a refusal. Calling it anything other than
    ``failed`` would let a rework hint be the only thing standing between a
    refused review and production.
    """

    fake = fake_complete([])
    plan = _plan(
        _stage("creative_review", order=1, kind="human", tools=()),
        _stage(
            "asset_integration",
            order=2,
            kind="agent",
            tools=(READ_ONLY_TOOL,),
            depends_on=("creative_review",),
        ),
    )
    orchestrator = _orchestrator(tmp_path)
    orchestrator.run(plan)

    orchestrator.resolve_human_stage("creative_review", "rejected")

    result = orchestrator.run(plan)

    assert result.outcome_for("creative_review").status == FAILED
    assert "rejected" in result.outcome_for("creative_review").detail
    assert result.outcome_for("asset_integration").status == BLOCKED
    assert result.status == RUN_ERROR
    assert result.error.startswith("creative_review")
    assert fake.payloads == []


def test_a_decision_given_before_the_plan_arrives_still_lands_on_it(fake_complete, tmp_path):
    """``resolve_human_stage`` is deliberately shaped like ``confirm``.

    Both validate against the translation table rather than against a plan, so
    the same gate can be decided before the plan that contains it is in hand.
    That only works if the next pass stamps the decision onto whatever plan it
    is given -- otherwise a decision taken during one request would be invisible
    to the pass that posted the plan, and the gate would ask again.
    """

    # Installed for its side effect: an empty queue makes "the model was
    # called" a failure rather than a silently shorter list of payloads.
    fake_complete([])
    orchestrator = _orchestrator(tmp_path)
    orchestrator.resolve_human_stage("creative_review", "approved")

    plan = _plan(_stage("creative_review", order=1, kind="human", tools=()))
    result = orchestrator.run(plan)

    assert result.outcome_for("creative_review").status == DONE
    assert plan.stages[0].human_resolution == "approved"


def test_a_second_pass_after_a_decision_does_not_ask_again(fake_complete, tmp_path):
    """Resumption is what makes the gate usable rather than a re-click loop.

    ``run`` is forward-only: a stage already ``done`` is not advanced again, so
    the pass after the decision neither re-asks nor re-records. A gate that
    reverted to ``awaiting_human`` on the next pass would make the board's own
    continue button undo the operator's click.
    """

    fake_complete([])
    plan = _plan(_stage("creative_review", order=1, kind="human", tools=()))
    orchestrator = _orchestrator(tmp_path)
    orchestrator.run(plan)
    orchestrator.resolve_human_stage("creative_review", "approved")

    assert orchestrator.run(plan).outcome_for("creative_review").status == DONE
    assert orchestrator.run(plan).outcome_for("creative_review").status == DONE
    assert orchestrator.pending_human_gates(plan) == []


# ── the field on the plan is a record, not an input ──────────────────────────


def test_a_plan_that_arrives_with_the_field_filled_does_not_open_the_gate(
    fake_complete, tmp_path
):
    """The AGENTS.md line, one field over from ``confirmed``.

    A plan is posted by the browser, and a browser that writes the decision into
    the plan it posts has manufactured an approval nobody gave. ``_advance``
    therefore reads the runtime map and never the field: the stamp is what the
    snapshot carries, not what opens a gate.
    """

    fake = fake_complete([])
    gate = _stage("creative_review", order=1, kind="human", tools=())
    gate.human_resolution = "approved"
    plan = _plan(gate)

    result = _orchestrator(tmp_path).run(plan)

    assert result.outcome_for("creative_review").status == AWAITING_HUMAN
    assert result.pending_human_gates == ["creative_review"]
    assert fake.payloads == []


def test_restoring_redeems_a_decision_the_operator_actually_gave(fake_complete, tmp_path):
    """The mirror of the test above, and the reason the field exists at all.

    The snapshot's plan dump is backend-written state: ``_stamp_plan`` put the
    decision there, so reading it back is redeeming a click rather than
    trusting a browser. The plan is rebuilt from the dump, exactly as the
    endpoint does, so this exercises the real path rather than the in-memory
    object the decision was stamped onto.
    """

    fake = fake_complete([llm.ModelReply(text="integrated")])
    plan = _plan(
        _stage("creative_review", order=1, kind="human", tools=()),
        _stage(
            "asset_integration",
            order=2,
            kind="agent",
            tools=(READ_ONLY_TOOL,),
            depends_on=("creative_review",),
        ),
    )
    source = _orchestrator(tmp_path)
    source.run(plan)
    source.resolve_human_stage("creative_review", "approved")
    source.run(plan)

    snapshot = load_snapshot("s1", engine_key="godot", workspace_root=tmp_path)
    assert snapshot is not None, "the pass after the decision wrote no snapshot"
    plan_from_disk = ProductionPipeline.model_validate(snapshot.plan)

    restored = Orchestrator.restore(snapshot, plan=plan_from_disk, workspace_root=tmp_path)

    assert restored.human_decisions == {"creative_review": "approved"}
    after = restored.run(plan_from_disk)
    assert after.outcome_for("creative_review").status == DONE
    assert after.outcome_for("asset_integration").status == DONE
    assert len(fake.payloads) == 1, "the restored pass re-dispatched a finished stage"


def test_a_restore_refuses_a_decision_outside_the_vocabulary(tmp_path):
    """A hand-edited stamp must fail the whole restore, not part of it.

    Same property, same shape as the confirmation guard: a snapshot carrying
    ``human_resolution: "banana"`` is corrupt in the one field that decides
    whether a gate is open, and a partial restore would re-run some stages
    while silently skipping others.
    """

    plan = _plan(_stage("creative_review", order=1, kind="human", tools=()))
    plan.stages[0].human_resolution = "banana"
    snapshot = _orchestrator(tmp_path).snapshot(plan)

    with pytest.raises(ValueError, match="not one of"):
        Orchestrator.restore(snapshot, plan=plan, workspace_root=tmp_path)


# ── the record on disk ───────────────────────────────────────────────────────


def test_the_decision_record_is_written_before_the_stage_counts_as_done(
    fake_complete, tmp_path
):
    """Artifact honesty, inherited from G-03 rather than re-learned.

    The stage's ``artifacts`` name the decision record. A board showing
    ``done`` next to a file nobody wrote is exactly the shape the playtest
    report had, so the record is durable *before* the outcome turns -- which is
    also why the write lives in the orchestrator and not in the gate's own tool
    list: a human stage runs no tools.
    """

    fake_complete([])
    plan = _plan(_stage("creative_review", order=1, kind="human", tools=()))
    orchestrator = _orchestrator(tmp_path)
    orchestrator.run(plan)

    path = decision_record_path("s1", workspace_root=tmp_path)
    assert not path.exists(), "nothing was decided yet, so nothing should be written"

    orchestrator.resolve_human_stage("creative_review", "approved")
    result = orchestrator.run(plan)

    assert result.outcome_for("creative_review").status == DONE
    assert path.exists(), "the stage reads done next to a file nobody wrote"
    record = load_decision_record("s1", workspace_root=tmp_path)
    assert record is not None
    assert record.source == "fantasy-agent.human-decision"
    assert record.session_id == "s1"
    assert record.stage_id == "creative_review"
    assert record.decision == "approved"
    assert record.decided_at, "an undated record cannot be placed in the session's history"


def test_the_record_is_written_once_per_gate_not_once_per_pass(fake_complete, tmp_path, monkeypatch):
    """A pass that re-wrote the record would churn the file it is meant to trust.

    The gate is decided once; every later pass finds it ``done`` and returns
    early, before the write. Counting the writes rather than the file's
    contents is what makes this deterministic -- a rewrite inside the same
    second would produce byte-identical output and prove nothing.
    """

    fake_complete([])
    calls: list[tuple[str, str]] = []

    def fake_write(session_id, stage_id, decision, *, engine_key, workspace_root):
        calls.append((stage_id, decision))
        return path_placeholder

    path_placeholder = tmp_path / "unused.yaml"
    monkeypatch.setattr("fantasy_agent.orchestrator.write_decision_record", fake_write)

    plan = _plan(_stage("creative_review", order=1, kind="human", tools=()))
    orchestrator = _orchestrator(tmp_path)
    orchestrator.run(plan)
    orchestrator.resolve_human_stage("creative_review", "approved")
    orchestrator.run(plan)
    orchestrator.run(plan)
    orchestrator.run(plan)

    assert calls == [("creative_review", "approved")]


# ── what the board is told ───────────────────────────────────────────────────


def test_pending_human_gates_lists_only_gates_nobody_has_decided(tmp_path):
    """A separate list from ``pending_confirmations``, and on purpose.

    The two ask different things of the operator -- approve a stage so it may
    run, decide a gate so the plan may continue -- so a gate in the approvals
    list would put an approve button on a card that approving cannot move.
    """

    plan = _plan(
        _stage("gameplay_orchestration", order=1, kind="human", tools=()),
        _stage("creative_review", order=2, kind="human", tools=()),
        _stage(
            "asset_integration",
            order=3,
            kind="agent",
            tools=(READ_ONLY_TOOL,),
            requires_confirmation=True,
        ),
    )
    orchestrator = _orchestrator(tmp_path)

    assert orchestrator.pending_human_gates(plan) == [
        "gameplay_orchestration",
        "creative_review",
    ]
    assert orchestrator.pending_confirmations(plan) == ["asset_integration"]

    orchestrator.resolve_human_stage("gameplay_orchestration", "approved")

    assert orchestrator.pending_human_gates(plan) == ["creative_review"]
    assert orchestrator.human_decisions == {"gameplay_orchestration": "approved"}


def test_a_decision_outside_the_vocabulary_is_a_loud_error(tmp_path):
    """A typo must not read as a decision that silently did nothing.

    Storing it would leave the gate waiting forever with nothing to show for
    the click -- the same failure ``confirm`` raises for instead.
    """

    with pytest.raises(ValueError, match="not one of"):
        _orchestrator(tmp_path).resolve_human_stage("creative_review", "maybe")


def test_a_decision_for_an_unknown_stage_is_a_loud_error(tmp_path):
    with pytest.raises(ValueError, match="unknown orchestration stage"):
        _orchestrator(tmp_path).resolve_human_stage("creative_revie", "approved")
