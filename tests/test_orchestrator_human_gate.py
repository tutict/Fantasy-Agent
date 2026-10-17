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
from fantasy_agent.orchestration_state import save_state
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


def test_a_forged_field_does_not_survive_the_snapshot_either(fake_complete, tmp_path):
    """The half of that line a live pass cannot show.

    ``_advance`` reading the map is enough for the pass in front of you, and
    that is all the test above proves. The stamp is also what the snapshot's
    plan dump carries, and ``restore`` redeems from that dump -- so a forged
    field that survives into the file is a decision nobody gave, arriving one
    restart later with the live check already behind it. Measured before the
    fix: a posted ``human_resolution: "approved"`` rode into the dump, the
    restore redeemed it into ``_human_decisions``, and the gate came back
    ``done`` on the next restart with no decision anywhere.

    The dump therefore has to be a pure function of the map. That is what makes
    "restoring redeems rather than trusts" a property rather than an intention,
    and it is the same reason ``snapshot`` writes ``confirmed`` from the set
    instead of reading it off the plan.
    """

    fake = fake_complete([])
    gate = _stage("creative_review", order=1, kind="human", tools=())
    gate.human_resolution = "approved"
    plan = _plan(gate)
    source = _orchestrator(tmp_path)
    source.run(plan)

    snapshot = load_snapshot("s1", engine_key="godot", workspace_root=tmp_path)
    assert snapshot is not None, "the pass wrote no snapshot"
    dumped = {
        entry["id"]: entry.get("human_resolution") for entry in snapshot.plan["stages"]
    }
    assert dumped == {"creative_review": None}, "the dump carried a forged stamp"

    plan_from_disk = ProductionPipeline.model_validate(snapshot.plan)
    restored = Orchestrator.restore(
        snapshot, plan=plan_from_disk, workspace_root=tmp_path
    )

    assert restored.human_decisions == {}, "restore redeemed a forged stamp"
    after = restored.run(plan_from_disk)
    assert after.outcome_for("creative_review").status == AWAITING_HUMAN
    assert after.pending_human_gates == ["creative_review"]
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


def test_a_decision_given_on_a_restored_board_survives_the_next_restart(
    fake_complete, tmp_path
):
    """The window the endpoint claims to have closed, closed.

    A restarted Studio rebuilds the session from its snapshot and renders a
    board from it, so the operator's next click lands on a *restored*
    orchestrator. ``resolve_human_stage`` stamps the plan the instance holds,
    and a restored instance held none -- so the endpoint's ``save_state``
    persisted a dump that predated the click. Measured before the fix: a second
    restart read the gate back as ``awaiting_human`` with ``human_decisions``
    empty, after the person had already approved it, and the endpoint's own
    docstring claimed that window was shut.

    ``restore`` now adopts the snapshot's plan as the instance's, which is the
    session's plan of record until the next ``run`` re-points it at the posted
    copy. Nothing else changes: the map is still the only authority.
    """

    fake_complete([llm.ModelReply(text="integrated")])
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

    # Restart #1: the board is rebuilt from what is on disk.
    snapshot = load_snapshot("s1", engine_key="godot", workspace_root=tmp_path)
    assert snapshot is not None
    plan_one = ProductionPipeline.model_validate(snapshot.plan)
    restored = Orchestrator.restore(snapshot, plan=plan_one, workspace_root=tmp_path)
    assert restored.human_decisions == {}

    # The operator decides on that board. Nothing has run yet, so no pass has
    # re-pointed the instance at a posted plan -- this is the whole window.
    restored.resolve_human_stage("creative_review", "approved")
    save_state(restored.snapshot(plan_one), workspace_root=tmp_path)

    # Restart #2: the decision has to still be there.
    snapshot_two = load_snapshot("s1", engine_key="godot", workspace_root=tmp_path)
    assert snapshot_two is not None
    plan_two = ProductionPipeline.model_validate(snapshot_two.plan)
    restored_two = Orchestrator.restore(
        snapshot_two, plan=plan_two, workspace_root=tmp_path
    )

    assert restored_two.human_decisions == {"creative_review": "approved"}
    after = restored_two.run(plan_two)
    assert after.outcome_for("creative_review").status == DONE
    assert after.pending_human_gates == []


# ── the rework path ───────────────────────────────────────────────────────────


def test_rewinding_a_decided_gate_asks_again(fake_complete, tmp_path):
    """The rework path, for the other vocabulary.

    ``rewind_from`` drops the outcome *and* the confirmation so a reworked stage
    runs what was approved rather than what was. A decision is the same shape of
    state and was left out: measured with it in place, the pass after a rewind
    replayed the earlier refusal as ``failed`` with no question asked -- and
    because a decided gate is absent from ``pending_human_gates``, the board had
    no button to offer either. The decision was unreachable from the UI and
    unresettable from the API.
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
    refused = orchestrator.run(plan)
    assert refused.outcome_for("creative_review").status == FAILED

    dropped = orchestrator.rewind_from(plan, "creative_review")

    # Everything at or after the cutoff goes, which is the documented shape:
    # a rework of the gate redoes what the gate gates.
    assert dropped == ["creative_review", "asset_integration"]
    assert orchestrator.human_decisions == {}
    after = orchestrator.run(plan)
    assert after.outcome_for("creative_review").status == AWAITING_HUMAN
    assert after.pending_human_gates == ["creative_review"]
    assert fake.payloads == []


def test_restore_redeems_only_gate_stamps(tmp_path):
    """A stamp on a stage that is not a gate is not a decision.

    Three layers answer "may this stage be decided" and they have to agree: the
    endpoint refuses an agent stage, the pass only looks at ``kind="human"``,
    and restore took whatever the dump carried. A plan hand-edited to stamp an
    agent stage therefore had a decision installed for it that no live path
    could ever read -- inert today, and the shape that makes the next reader
    wrong. The refusal and the pass already say no; restore says no too.
    """

    plan = _plan(
        _stage("creative_review", order=1, kind="human", tools=()),
        _stage(
            "asset_integration",
            order=2,
            kind="agent",
            tools=(READ_ONLY_TOOL,),
        ),
    )
    plan.stages[1].human_resolution = "approved"
    snapshot = _orchestrator(tmp_path).snapshot(plan)

    restored = Orchestrator.restore(snapshot, plan=plan, workspace_root=tmp_path)

    assert restored.human_decisions == {}, "an agent stage's stamp was redeemed"


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


def test_a_decision_that_cannot_be_written_still_advances_the_gate(
    fake_complete, tmp_path, monkeypatch, caplog
):
    """The documented trade, pinned where the two halves can silently disagree.

    ``_record_decision`` logs and returns rather than raising, because the
    person did decide and losing the stage over the record of it would be the
    worse trade. That leaves one place where the gate's progress and its named
    artifact can disagree, and a ``done`` card next to a file nobody wrote is
    the artifact-honesty bug G-03 spent on the playtest report -- so the log
    line that says so is load-bearing, not decoration.
    """

    fake_complete([])

    def boom(session_id, stage_id, decision, *, engine_key, workspace_root):
        raise OSError("disk is full")

    monkeypatch.setattr("fantasy_agent.orchestrator.write_decision_record", boom)

    plan = _plan(_stage("creative_review", order=1, kind="human", tools=()))
    orchestrator = _orchestrator(tmp_path)
    orchestrator.run(plan)
    orchestrator.resolve_human_stage("creative_review", "approved")

    with caplog.at_level("ERROR", logger="fantasy_agent.orchestrator"):
        result = orchestrator.run(plan)

    assert result.outcome_for("creative_review").status == DONE
    assert not decision_record_path("s1", workspace_root=tmp_path).exists()
    assert any(
        "could not record the decision" in record.message for record in caplog.records
    ), "a missing record has to say so"


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
