"""Tests for the orchestrator that advances a pipeline stage by stage.

The waste this prevents: before this layer, the internal loop was handed one
flat list of all 20 tools and left to work out the order itself, while the
pipeline table that already said the order, each stage's tools and what had to
finish first went unread.

Three things are pinned here, and they are the three that make reading the table
worth doing:

- a stage is only ever offered *its own* tools, so the narrowing is real;
- a stage that cannot run costs zero model turns -- no dispatch, so no tokens;
- a stage's failure stays that stage's failure, and the caller gets the same
  ``status="error"`` it already branches on for the deterministic fallback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from fantasy_agent import llm
from fantasy_agent.contracts import ProductionPipeline, ProductionPipelineStage
from fantasy_agent.orchestrator import (
    AWAITING_CONFIRMATION,
    AWAITING_HUMAN,
    BLOCKED,
    DONE,
    FAILED,
    RUN_DONE,
    RUN_ERROR,
    Orchestrator,
)
from fantasy_agent.pipeline_state import (
    GODOT_STAGE_ORDER,
    RESUMABLE_STAGES,
    load_state,
    stages_before,
)
from fantasy_agent.tool_registry import (
    EXECUTE,
    READ_ONLY,
    WRITE,
    ToolOutcome,
    ToolRegistry,
    ToolSpec,
    combined_registry,
)

# Real tiers, read off `combined_registry()` rather than assumed: the four
# planning tools are read-only, `create_godot_project_structure` writes, and
# `run_godot_import` launches a process. A test that guessed these would pass
# while proving nothing about the gate it is claiming to exercise.
READ_ONLY_TOOL = "extract_idea_seed"
ANOTHER_READ_ONLY_TOOL = "render_gdd"
WRITE_TOOL = "create_godot_project_structure"
EXECUTE_TOOL = "run_godot_import"


def _stage(
    stage_id: str = "gameplay_orchestration",
    *,
    order: int = 1,
    kind: str = "agent",
    tools: tuple[str, ...] = (READ_ONLY_TOOL,),
    depends_on: tuple[str, ...] = (),
    artifacts: tuple[str, ...] = (),
    exit_checks: tuple[str, ...] = (),
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
        artifacts=list(artifacts),
        exit_checks=list(exit_checks),
        requires_confirmation=requires_confirmation,
    )


def _plan(*stages: ProductionPipelineStage) -> ProductionPipeline:
    return ProductionPipeline(
        project_name="probe", goal="prove the orchestrator", stages=list(stages)
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
    """Minimal Responses API stand-in, copied in shape from test_agent_loop.

    Raises rather than returning a default when the queue runs dry, so "the loop
    called the model when it should not have" shows up as a failure instead of
    as a silently shorter list of payloads.
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


def _call(name: str, call_id: str = "c1", **arguments) -> llm.ModelReply:
    return llm.ModelReply(
        text="",
        tool_calls=[llm.ToolCallRequest(id=call_id, name=name, arguments=arguments)],
        raw={"output": [{"type": "function_call", "call_id": call_id, "name": name}]},
    )


# ── scoped registries ────────────────────────────────────────────────────────


def test_a_scoped_registry_shares_the_artifact_store():
    """The reason `scoped` exists at all, asserted on identity rather than shape.

    A copy would look correct in every other test in this file and still break
    the real pipeline: the Godot tool reads `godot_plan` out of this store, so a
    private store per stage builds the project with no gameplay spec.
    """

    everything = combined_registry()
    scoped = everything.scoped([READ_ONLY_TOOL])

    assert scoped.artifacts is everything.artifacts

    # The path the loop actually uses, not just the attribute.
    scoped.remember_plan({"summary": {"godot_plan": {"project_name": "probe"}}})
    assert everything.artifacts["godot_plan"] == {"project_name": "probe"}


def test_scoped_keeps_only_the_names_it_was_given():
    everything = combined_registry()

    assert everything.scoped([READ_ONLY_TOOL, ANOTHER_READ_ONLY_TOOL]).names() == sorted(
        [READ_ONLY_TOOL, ANOTHER_READ_ONLY_TOOL]
    )


def test_scoped_honours_a_tier_ceiling():
    everything = combined_registry()

    assert everything.scoped([WRITE_TOOL], up_to=READ_ONLY).names() == []
    assert everything.scoped([WRITE_TOOL], up_to=WRITE).names() == [WRITE_TOOL]
    assert everything.scoped([EXECUTE_TOOL], up_to=WRITE).names() == []
    assert everything.scoped([EXECUTE_TOOL], up_to=EXECUTE).names() == [EXECUTE_TOOL]


def test_scoped_raises_on_a_name_that_resolves_to_nothing():
    """A typo in a hand-written whitelist must fail, not silently narrow.

    Silently dropping it would hand the stage an empty tool set, and the stage
    would read as "nothing to do here" rather than "this whitelist is wrong".
    """

    everything = combined_registry()

    with pytest.raises(ValueError, match="unknown tool"):
        everything.scoped([READ_ONLY_TOOL, "extract_idea_sead"])


def test_scoped_with_no_ceiling_admits_every_tier():
    everything = combined_registry()

    assert everything.scoped([EXECUTE_TOOL]).names() == [EXECUTE_TOOL]


# ── what the model is offered ───────────────────────────────────────────────


def test_each_stage_is_only_offered_its_own_tools(fake_complete, tmp_path):
    fake = fake_complete([llm.ModelReply(text="ok"), llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1, tools=(READ_ONLY_TOOL,)),
        _stage(
            "blender_modeling",
            order=2,
            tools=(ANOTHER_READ_ONLY_TOOL, "decompose_production_tasks"),
        ),
    )

    result = _orchestrator(tmp_path).run(plan)

    assert result.ok
    assert len(fake.payloads) == 2
    first = _offered_from_payload(fake.payloads[0])
    second = _offered_from_payload(fake.payloads[1])

    assert first == [READ_ONLY_TOOL]
    assert second == sorted([ANOTHER_READ_ONLY_TOOL, "decompose_production_tasks"])
    # Narrowing, not just renaming: the whole registry is 20 tools, and neither
    # stage saw anything close to it. Compared against the live registry so this
    # cannot rot into a hard-coded number that stops meaning anything.
    everything = len(combined_registry().names())
    assert len(first) < everything
    assert len(second) < everything


def test_a_tool_outside_the_whitelist_comes_back_as_an_error(fake_complete, tmp_path):
    """The model can ask for anything; the stage's slice decides what exists.

    The outcome has to reach the model as an error it can read, so the loop
    carries on with the tools it does have instead of dying on a bad name.
    """

    fake = fake_complete(
        [
            _call("run_godot_import", call_id="c1"),
            llm.ModelReply(text="carrying on without it"),
        ]
    )
    plan = _plan(_stage(tools=(READ_ONLY_TOOL,)))

    result = _orchestrator(tmp_path).run(plan)

    assert result.ok, "the loop should survive a request for a tool this stage does not have"
    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome is not None
    assert outcome.tool_calls == 1

    fed_back = _tool_outputs(fake.payloads[1])
    assert len(fed_back) == 1
    assert fed_back[0]["status"] == "error"
    assert "unknown tool" in fed_back[0]["content"]


# ── stages that must not cost a model turn ──────────────────────────────────


def test_an_unmet_dependency_blocks_the_stage_and_spends_no_turn(fake_complete, tmp_path):
    records: dict[str, int] = {}
    registry = _counting_registry(records)
    fake = fake_complete([])

    plan = _plan(
        _stage("creative_review", order=1, kind="human", tools=()),
        _stage(
            "asset_integration", order=2, tools=(READ_ONLY_TOOL,), depends_on=("creative_review",)
        ),
    )

    result = _orchestrator(tmp_path, registry=registry).run(plan)

    blocked = result.outcome_for("asset_integration")
    assert blocked is not None
    assert blocked.status == BLOCKED
    assert "creative_review" in blocked.detail
    assert not blocked.dispatched
    assert records.get(READ_ONLY_TOOL, 0) == 0, "a blocked stage ran its tool anyway"
    assert fake.payloads == [], "a blocked stage was dispatched to the model"
    assert result.status == AWAITING_HUMAN, "the human gate is the news, not the queue behind it"


def test_a_human_stage_never_calls_a_tool(fake_complete, tmp_path):
    # Zero replies queued: `_FakeResponses` raises if the model is called at all.
    fake = fake_complete([])
    plan = _plan(_stage("creative_review", kind="human", tools=()))

    result = _orchestrator(tmp_path).run(plan)

    outcome = result.outcome_for("creative_review")
    assert outcome is not None
    assert outcome.status == AWAITING_HUMAN
    assert outcome.tool_calls == 0
    assert not outcome.dispatched
    assert fake.payloads == []
    assert result.status == AWAITING_HUMAN


def test_a_stage_whose_tools_all_exceed_the_grant_waits_instead_of_spinning(
    fake_complete, tmp_path
):
    """An agent with an empty tool list is a wasted turn, not a run.

    The stage declares a real tool that launches a process; with no execution
    grant nothing is visible, so the stage waits for a person rather than being
    dispatched to explore a menu it cannot order from.
    """

    fake = fake_complete([])
    plan = _plan(_stage("godot_quick_play", tools=(EXECUTE_TOOL,)))

    result = _orchestrator(tmp_path).run(plan)

    outcome = result.outcome_for("godot_quick_play")
    assert outcome is not None
    assert outcome.status == AWAITING_CONFIRMATION
    assert outcome.tools == []
    assert outcome.tool_calls == 0
    assert fake.payloads == []
    assert result.status == AWAITING_CONFIRMATION


def test_granting_execution_lets_that_same_stage_run(fake_complete, tmp_path):
    """The counterpart to the test above: it is the grant that changes, nothing else."""

    fake = fake_complete([llm.ModelReply(text="imported")])
    plan = _plan(_stage("godot_quick_play", tools=(EXECUTE_TOOL,)))

    result = _orchestrator(tmp_path, registry=_counting_registry({})).run(plan, allow_execute=True)

    outcome = result.outcome_for("godot_quick_play")
    assert outcome is not None
    assert outcome.status == DONE
    assert outcome.tools == [EXECUTE_TOOL]
    assert outcome.answer == "imported", (
        "the stage was marked done without the model ever answering"
    )
    assert len(fake.payloads) == 1


def test_a_typo_in_a_stage_whitelist_fails_the_stage_instead_of_running_it_empty(
    fake_complete, tmp_path
):
    fake = fake_complete([])
    plan = _plan(_stage(tools=(READ_ONLY_TOOL, "render_gdd_typo")))

    result = _orchestrator(tmp_path).run(plan)

    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome is not None
    assert outcome.status == FAILED
    assert "unknown tool" in outcome.detail
    assert not outcome.dispatched
    assert fake.payloads == []


# ── exit checks ─────────────────────────────────────────────────────────────


def test_a_stage_runs_its_exit_checks_before_it_counts_as_done(fake_complete, tmp_path):
    """`quality_gates` stays prose; `exit_checks` is the machine-checkable part.

    The plan's fourth open question settled it: of the 21 exported quality gates
    not one is machine-checkable, and inventing a check DSL for them is a
    different project. So a stage may name read-only tools instead, and the
    orchestrator runs them itself once the agent has finished.
    """

    records: dict[str, int] = {}
    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage(exit_checks=(ANOTHER_READ_ONLY_TOOL,)))

    result = _orchestrator(tmp_path, registry=_checking_registry(records)).run(plan)

    assert result.ok
    assert records.get(ANOTHER_READ_ONLY_TOOL) == 1, "the stage's exit check never ran"
    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome.status == DONE
    # Recorded separately from `tools` (what the model was offered): a board
    # showing "verified by X" must not be reading the model's menu.
    assert outcome.checks == [ANOTHER_READ_ONLY_TOOL]


def test_an_exit_check_that_reports_a_problem_makes_the_stage_failed(fake_complete, tmp_path):
    """A stage that ran but did not pass its own check is not done.

    Calling it done would unblock the next stage on output the stage itself
    says is wrong -- the failure has to land here, where the rework target is.
    """

    records: dict[str, int] = {}
    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage(exit_checks=(ANOTHER_READ_ONLY_TOOL,)))

    result = _orchestrator(
        tmp_path, registry=_checking_registry(records, failing=(ANOTHER_READ_ONLY_TOOL,))
    ).run(plan)

    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome is not None
    assert outcome.status == FAILED
    assert ANOTHER_READ_ONLY_TOOL in outcome.detail, (
        "the failing check has to be named, or the rework has nowhere to go"
    )
    assert result.status == RUN_ERROR
    assert records[ANOTHER_READ_ONLY_TOOL] == 1


def test_an_exit_check_runs_even_when_it_is_not_in_the_stages_whitelist(fake_complete, tmp_path):
    """The whitelist narrows what the *model* may attempt, not what the stage verifies.

    A check is the pipeline reading its own output, so it is called through the
    full registry. Asserted because routing it through the scoped one would look
    harmless and then quietly skip every check whose name the stage does not
    also offer to the model -- i.e. silently prove nothing.
    """

    records: dict[str, int] = {}
    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(
        _stage(tools=(READ_ONLY_TOOL,), exit_checks=(ANOTHER_READ_ONLY_TOOL,)),
    )

    result = _orchestrator(tmp_path, registry=_checking_registry(records)).run(plan)

    assert result.ok
    assert records.get(ANOTHER_READ_ONLY_TOOL) == 1


def test_an_exit_check_that_names_nothing_fails_the_stage_instead_of_being_skipped(
    fake_complete, tmp_path
):
    """A check nobody can run is a check that verified nothing.

    Skipping an unresolvable name would turn a typo in the pipeline table into a
    stage that reports itself verified.
    """

    records: dict[str, int] = {}
    fake = fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage(exit_checks=("render_gdd_typo",)))

    result = _orchestrator(tmp_path, registry=_checking_registry(records)).run(plan)

    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome is not None
    assert outcome.status == FAILED
    assert "render_gdd_typo" in outcome.detail
    assert len(fake.payloads) == 1, "the agent still ran; only the exit check is missing"


def test_a_human_stage_runs_no_exit_check(fake_complete, tmp_path):
    """Nothing ran, so there is nothing to check -- and the gate is not bypassed."""

    records: dict[str, int] = {}
    fake_complete([])
    plan = _plan(
        _stage("creative_review", kind="human", tools=(), exit_checks=(ANOTHER_READ_ONLY_TOOL,))
    )

    result = _orchestrator(tmp_path, registry=_checking_registry(records)).run(plan)

    assert result.outcome_for("creative_review").status == AWAITING_HUMAN
    assert records.get(ANOTHER_READ_ONLY_TOOL, 0) == 0


# ── failure containment ─────────────────────────────────────────────────────


def test_one_broken_stage_does_not_take_the_others_down(monkeypatch, tmp_path):
    """A provider failure is one stage's failure, and the caller gets `error`.

    Independent stages on either side keep their outcomes: the point is that the
    run reports what got done rather than discarding it.
    """

    seen = {"calls": 0}

    def flaky(**_kwargs):
        seen["calls"] += 1
        if seen["calls"] == 2:
            raise llm.LLMError("provider unreachable")
        return llm.ModelReply(text="ok")

    monkeypatch.setattr("fantasy_agent.agent_loop.complete_with_tools", flaky)

    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("blender_modeling", order=2),
        _stage("godot_quick_play", order=3),
    )

    result = _orchestrator(tmp_path).run(plan)

    assert result.status == RUN_ERROR
    assert result.ok is False
    assert "blender_modeling" in result.error
    assert "unreachable" in result.error

    assert result.outcome_for("gameplay_orchestration").status == DONE
    assert result.outcome_for("blender_modeling").status == FAILED
    assert "unreachable" in result.outcome_for("blender_modeling").detail
    assert result.outcome_for("godot_quick_play").status == DONE, (
        "a failure in one stage stopped an independent one"
    )


def test_a_stage_whose_agent_stops_early_is_not_called_done(monkeypatch, tmp_path):
    """`max_turns` is not success: an unfinished stage must not unblock the next."""

    monkeypatch.setattr(
        "fantasy_agent.agent_loop.complete_with_tools",
        lambda **_kwargs: _call("extract_idea_seed", call_id="c"),
    )
    plan = _plan(_stage(tools=(READ_ONLY_TOOL,)))

    result = _orchestrator(tmp_path).run(plan, max_turns=2)

    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome is not None
    assert outcome.status == FAILED
    assert "max_turns" in outcome.detail
    assert result.status == RUN_ERROR


# ── advancing rather than restarting ────────────────────────────────────────


def test_a_finished_stage_is_not_dispatched_a_second_time(fake_complete, tmp_path):
    """`run` advances a plan; it does not restart one.

    This is what makes the human gate usable: confirming a late stage re-enters
    `run`, and without the outcome map that pass would replay every expensive
    stage before it.
    """

    fake = fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("creative_review", order=2, kind="human", tools=()),
    )
    orchestrator = _orchestrator(tmp_path)

    first = orchestrator.run(plan)
    second = orchestrator.run(plan)

    assert first.outcome_for("gameplay_orchestration").status == DONE
    assert second.outcome_for("gameplay_orchestration").status == DONE
    assert second.outcome_for("creative_review").status == AWAITING_HUMAN
    assert len(fake.payloads) == 1, "the second pass replayed a stage that had already finished"


def test_a_repeated_pass_reports_the_same_stage_states(fake_complete, tmp_path):
    fake = fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("godot_quick_play", order=2, tools=(EXECUTE_TOOL,)),
    )
    orchestrator = _orchestrator(tmp_path)

    first = orchestrator.run(plan)
    second = orchestrator.run(plan)

    assert [o.status for o in first.stages] == [DONE, AWAITING_CONFIRMATION]
    assert [o.status for o in second.stages] == [DONE, AWAITING_CONFIRMATION]
    assert len(fake.payloads) == 1, (
        "the second pass spent a model turn the first pass had already paid for"
    )


def test_an_empty_plan_is_done_rather_than_an_error(tmp_path):
    result = _orchestrator(tmp_path).run(_plan())

    assert result.status == RUN_DONE
    assert result.stages == []


# ── stage-level confirmation ────────────────────────────────────────────────


def test_a_stage_that_asks_for_confirmation_waits_for_a_person(fake_complete, tmp_path):
    """Six of the seven measured stages declare `requires_confirmation`.

    If that field only meant "show a badge", a run would walk the whole
    expensive chain on the strength of a checkbox nobody clicked.
    """

    fake = fake_complete([])
    plan = _plan(_stage(tools=(WRITE_TOOL,), requires_confirmation=True))

    result = _orchestrator(tmp_path, registry=_counting_registry({})).run(
        plan, allow_write=True
    )

    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome.status == AWAITING_CONFIRMATION
    assert not outcome.dispatched
    assert fake.payloads == [], "an unconfirmed stage was dispatched to the model"
    assert result.status == AWAITING_CONFIRMATION


def test_a_global_grant_does_not_answer_a_stage_level_question(fake_complete, tmp_path):
    """`allow_write` says what a stage *may* do, not whether it may start.

    Collapsing the two would mean one global switch silently authorises every
    stage in the plan -- which is the whole reason `requires_confirmation` is a
    per-stage field.
    """

    records: dict[str, int] = {}
    fake_complete([])
    plan = _plan(_stage(tools=(WRITE_TOOL,), requires_confirmation=True))

    result = _orchestrator(tmp_path, registry=_counting_registry(records)).run(
        plan, allow_write=True, allow_execute=True
    )

    assert result.outcome_for("gameplay_orchestration").status == AWAITING_CONFIRMATION
    assert records.get(WRITE_TOOL, 0) == 0, "an unconfirmed stage ran its write tool anyway"
    assert records.get(EXECUTE_TOOL, 0) == 0


def test_confirming_the_stage_lets_it_run(fake_complete, tmp_path):
    fake_complete([llm.ModelReply(text="built it")])
    plan = _plan(_stage(requires_confirmation=True))

    result = _orchestrator(tmp_path).run(
        plan, confirm_stages=("gameplay_orchestration",)
    )

    outcome = result.outcome_for("gameplay_orchestration")
    assert outcome.status == DONE
    assert outcome.answer == "built it"
    assert result.status == RUN_DONE


def test_confirming_a_stage_does_not_widen_its_permissions(fake_complete, tmp_path):
    """Two different questions, and only the first is answered by `confirm_stages`.

    The stage is allowed to start; it is still not allowed to write. The write
    tool is not even offered -- `scoped(up_to=...)` cuts the set before the
    model sees it -- so the model gets `unknown tool` rather than `refused`.
    That is one step earlier than a refusal, not a weaker answer: what is
    asserted here is that the *tool set* did not change, because that is the
    thing a confirmation would have had to move to be a back door.
    """

    records: dict[str, int] = {}
    fake = fake_complete(
        [
            _call(WRITE_TOOL, call_id="c1"),
            llm.ModelReply(text="carrying on without writing"),
        ]
    )
    plan = _plan(_stage(tools=(READ_ONLY_TOOL, WRITE_TOOL), requires_confirmation=True))

    result = _orchestrator(tmp_path, registry=_counting_registry(records)).run(
        plan, confirm_stages=("gameplay_orchestration",)
    )

    outcome = result.outcome_for("gameplay_orchestration")
    assert result.ok
    assert outcome.tools == [READ_ONLY_TOOL], "the confirmation widened the stage's tool set"
    assert records.get(WRITE_TOOL, 0) == 0, "a confirmed stage wrote without a write grant"
    fed_back = _tool_outputs(fake.payloads[1])
    assert [entry["status"] for entry in fed_back] == ["error"]
    assert "unknown tool" in fed_back[0]["content"]


def test_a_confirmation_survives_the_next_pass(fake_complete, tmp_path):
    """The board confirms once; the pass after that must not ask again."""

    fake = fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage(requires_confirmation=True))
    orchestrator = _orchestrator(tmp_path)

    first = orchestrator.run(plan, confirm_stages=("gameplay_orchestration",))
    second = orchestrator.run(plan)

    assert first.outcome_for("gameplay_orchestration").status == DONE
    assert second.outcome_for("gameplay_orchestration").status == DONE
    assert len(fake.payloads) == 1


def test_the_result_lists_who_is_still_waiting_on_a_person(fake_complete, tmp_path):
    """The board needs the list, not just each card's status.

    Filtering `stages` for `awaiting_*` would conflate "needs your approval"
    with "needs a grant", which are different actions for the user to take.
    """

    fake = fake_complete([])
    plan = _plan(
        _stage("gameplay_orchestration", order=1, requires_confirmation=True),
        _stage("blender_modeling", order=2, requires_confirmation=True),
        _stage("creative_review", order=3, kind="human", tools=(), requires_confirmation=True),
    )

    result = _orchestrator(tmp_path).run(plan)

    assert sorted(result.pending_confirmations) == ["blender_modeling", "gameplay_orchestration"]
    # The human gate is not in the list: it is waiting for a decision, not for
    # an approval that would let it run.
    assert fake.payloads == []


def test_a_human_gate_still_reads_as_a_human_gate(fake_complete, tmp_path):
    """`creative_review` carries both flags; the person's decision is the sharper one.

    Reporting it as "unconfirmed" would offer the operator an approve button for
    a stage that no amount of approving can run.
    """

    fake_complete([])
    plan = _plan(
        _stage("creative_review", kind="human", tools=(), requires_confirmation=True)
    )

    result = _orchestrator(tmp_path).run(plan)

    assert result.outcome_for("creative_review").status == AWAITING_HUMAN


def test_a_stage_that_needs_no_confirmation_is_unaffected(fake_complete, tmp_path):
    """The field is opt-in: a plan that never sets it behaves exactly as before."""

    fake = fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage(requires_confirmation=False))

    result = _orchestrator(tmp_path).run(plan)

    assert result.outcome_for("gameplay_orchestration").status == DONE
    assert result.pending_confirmations == []
    assert len(fake.payloads) == 1


def test_confirming_an_unknown_stage_is_a_loud_error(fake_complete, tmp_path):
    """A typo in the board's payload must not read as "nothing was confirmed"."""

    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage(requires_confirmation=True))

    with pytest.raises(ValueError, match="unknown orchestration stage"):
        _orchestrator(tmp_path).run(plan, confirm_stages=("gameplay_orchestratoin",))


# ── rework: rewinding instead of replaying ───────────────────────────────────


def test_rewinding_from_a_stage_makes_the_next_pass_redo_it(fake_complete, tmp_path):
    """The point of the rework path: one node's fix, not the whole run again.

    Without a rewind the outcome map is permanently "already finished", so the
    only way to redo a stage would be a fresh session -- which is exactly the
    full replay that `depends_on` and the stage table were added to avoid.
    """

    fake = fake_complete([llm.ModelReply(text="ok") for _ in range(3)])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("godot_quick_play", order=2, tools=(EXECUTE_TOOL,)),
    )
    orchestrator = _orchestrator(tmp_path, registry=_counting_registry({}))

    orchestrator.run(plan, allow_execute=True)
    assert len(fake.payloads) == 2

    # One stage's outputs were fixed by hand; only it and what follows re-runs.
    dropped = orchestrator.rewind_from(plan, "godot_quick_play")
    assert dropped == ["godot_quick_play"]

    orchestrator.run(plan, allow_execute=True)
    assert len(fake.payloads) == 3, (
        "the rewound stage was not re-dispatched, or an earlier one was replayed"
    )


def test_rewinding_keeps_the_stages_before_the_target(fake_complete, tmp_path):
    """Rewind is "from here on", so work that the fix does not invalidate stays paid for."""

    fake = fake_complete([llm.ModelReply(text="ok") for _ in range(5)])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("blender_modeling", order=2),
        _stage("godot_quick_play", order=3),
    )
    orchestrator = _orchestrator(tmp_path)

    orchestrator.run(plan)
    orchestrator.rewind_from(plan, "blender_modeling")
    result = orchestrator.run(plan)

    assert result.outcome_for("gameplay_orchestration").status == DONE
    # Three dispatches in the first pass, two in the second: only the target and
    # the stage behind it were redone.
    assert len(fake.payloads) == 5


def test_rewinding_an_unknown_stage_is_a_loud_error(fake_complete, tmp_path):
    """A typo must not silently rewind the whole plan."""

    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage("gameplay_orchestration", order=1))
    orchestrator = _orchestrator(tmp_path)

    with pytest.raises(ValueError, match="not a stage of this plan"):
        orchestrator.rewind_from(plan, "godot_quick_play")


def test_a_rework_target_lands_on_the_orchestration_stage_that_owns_the_node(fake_complete, tmp_path):
    """A pre-flight hint is in executor vocabulary; the board is in orchestration's.

    `godot_plan` is not a stage in either vocabulary -- it is a *rework target*,
    resolved by `resume_stage_for` to the execution stage `create`, whose owning
    orchestration stage is `godot_quick_play`. Both hops have to happen or the
    hint cannot be turned into "resume here".
    """

    fake_complete([llm.ModelReply(text="ok"), llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("godot_quick_play", order=2),
    )
    orchestrator = _orchestrator(tmp_path)

    orchestrator.run(plan)
    landed = orchestrator.rewind_for_rework(plan, rework_target="godot_plan")

    assert landed == "godot_quick_play"


def test_a_rework_target_resolves_through_the_per_issue_override(fake_complete, tmp_path):
    """`flags` covers two unrelated switches; the code decides which one moved.

    Resuming from the wrong one either wastes a node or skips the one that
    needed to run, which is why `REWORK_CODE_STAGES` exists at all.
    """

    fake_complete([llm.ModelReply(text="ok"), llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("blender_modeling", order=2),
    )
    orchestrator = _orchestrator(tmp_path)

    orchestrator.run(plan)

    assert (
        orchestrator.rewind_for_rework(
            plan, rework_target="flags", code="assets_declared_not_enabled"
        )
        == "blender_modeling"
    )


def test_an_unrecognised_hint_leaves_the_run_alone(fake_complete, tmp_path):
    """An unrecognised hint must not silently rewind anything.

    The caller gets None and can fall back. What it must not get is a rewind
    invented from a default: `resume_stage_for` already refuses unknown targets
    precisely so a typo surfaces, and defaulting the *second* hop would undo
    that one layer later.

    The plan here deliberately contains `godot_quick_play`, which is what an
    invented `create` translation would rewind -- so a silent fallback cannot
    hide behind "there was nothing to rewind anyway".
    """

    fake = fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage("godot_quick_play", order=1))
    orchestrator = _orchestrator(tmp_path)

    orchestrator.run(plan)
    before = orchestrator.outcomes

    assert orchestrator.rewind_for_rework(plan, rework_target="not_a_target") is None
    assert orchestrator.outcomes == before
    # The stage is still finished, so a second pass spends no turn on it.
    assert len(fake.payloads) == 1


def test_a_rewind_lets_a_human_gate_be_re_answered(fake_complete, tmp_path):
    """`creative_review` translates to no process step, which is not a dead end.

    Its own rewind is the human-gate path: a later pass asks again instead of
    reading the previous pass's answer as final.
    """

    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1),
        _stage("creative_review", order=2, kind="human", tools=()),
    )
    orchestrator = _orchestrator(tmp_path)

    orchestrator.run(plan)
    assert orchestrator.rewind_from(plan, "creative_review") == ["creative_review"]

    # Gone from the map, so the next pass re-evaluates it rather than returning
    # the cached `awaiting_human`.
    assert "creative_review" not in orchestrator.outcomes
    assert orchestrator.run(plan).outcome_for("creative_review").status == AWAITING_HUMAN


# ── what lands on disk ──────────────────────────────────────────────────────


def test_every_stage_outcome_is_recorded_including_the_waiting_ones(fake_complete, tmp_path):
    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(
        _stage("gameplay_orchestration", order=1, artifacts=("generated/gameplay-spec.yaml",)),
        _stage("creative_review", order=2, kind="human", tools=()),
        _stage(
            "asset_integration", order=3, tools=(READ_ONLY_TOOL,), depends_on=("creative_review",)
        ),
    )

    _orchestrator(tmp_path).run(plan)

    state = load_state("s1", workspace_root=tmp_path)
    assert state is not None
    statuses = {stage.name: stage.status for stage in state.stages}

    # A board that only saw finished stages could not tell "blocked" from "not
    # reached yet", which is the whole difference the status field carries.
    assert statuses == {
        "gameplay_orchestration": DONE,
        "creative_review": AWAITING_HUMAN,
        "asset_integration": BLOCKED,
    }
    recorded = state.get("gameplay_orchestration")
    assert recorded is not None
    assert recorded.artifacts == ["generated/gameplay-spec.yaml"]


def test_an_orchestration_record_never_tells_the_executor_to_skip_a_node(fake_complete, tmp_path):
    """The two stage vocabularies share one state file. Only one of them resumes.

    Orchestration ids (`creative_review`) are not execution stages (`preflight`),
    and the executor's skip set is `stages_before(...) & done_stages() &
    RESUMABLE_STAGES`. Every term of that intersection is filtered against the
    executor's own names, so an orchestration record cannot make an expensive
    node look already-run. Pinned rather than argued: the plan's Task 4 is
    exactly about translating between the two, and this is the boundary it must
    not cross by accident.
    """

    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage("gameplay_orchestration", order=1))

    result = _orchestrator(tmp_path, session_id="orchestrated").run(plan)
    assert result.ok

    state = load_state("orchestrated", workspace_root=tmp_path)
    assert state is not None
    assert state.done_stages() == {"gameplay_orchestration"}

    for target in GODOT_STAGE_ORDER:
        skip = stages_before(target) & state.done_stages() & RESUMABLE_STAGES
        assert skip == set(), f"an orchestration record made {target} skip {skip}"


def test_a_state_write_failure_does_not_lose_the_stage_outcome(
    fake_complete, monkeypatch, tmp_path
):
    """The stage already ran; losing model turns over a record of it is the worse loss."""

    fake_complete([llm.ModelReply(text="ok")])
    plan = _plan(_stage("gameplay_orchestration", order=1))

    def boom(*_args, **_kwargs):
        raise OSError("disk is full")

    monkeypatch.setattr("fantasy_agent.orchestrator.record_stage", boom)

    result = _orchestrator(tmp_path).run(plan)

    assert result.status == RUN_DONE
    assert result.outcome_for("gameplay_orchestration").status == DONE


# ── helpers ─────────────────────────────────────────────────────────────────


def _offered_from_payload(payload: dict[str, Any]) -> list[str]:
    """Tool names the model was handed in one call."""

    return sorted(spec["name"] for spec in payload["tools"])


def _tool_outputs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """What each tool call was answered with, parsed back out of the messages."""

    return [
        json.loads(message["output"])
        for message in payload["messages"]
        if isinstance(message, dict) and message.get("type") == "function_call_output"
    ]


def _counting_registry(records: dict[str, int]) -> ToolRegistry:
    """A registry whose handlers count, so "never called" is an assertion.

    Built by hand rather than reusing `combined_registry()` because the engine
    tools would launch real processes; the names, however, are the real ones so
    the tests and the pipeline table talk about the same tools.
    """

    registry = ToolRegistry()

    def counter(name: str):
        def handler(_arguments: dict[str, Any]) -> dict[str, Any]:
            records[name] = records.get(name, 0) + 1
            return {"message": f"{name} ran", "data": {}}

        return handler

    for name in (READ_ONLY_TOOL, ANOTHER_READ_ONLY_TOOL):
        registry.register(
            ToolSpec(
                name=name,
                description=name,
                input_schema={"type": "object", "properties": {}},
                handler=counter(name),
            )
        )
    registry.register(
        ToolSpec(
            name=WRITE_TOOL,
            description=WRITE_TOOL,
            input_schema={"type": "object", "properties": {}},
            handler=counter(WRITE_TOOL),
            permission=WRITE,
        )
    )
    registry.register(
        ToolSpec(
            name=EXECUTE_TOOL,
            description=EXECUTE_TOOL,
            input_schema={"type": "object", "properties": {}},
            handler=counter(EXECUTE_TOOL),
            permission=EXECUTE,
        )
    )
    return registry


def _checking_registry(records: dict[str, int], *, failing: tuple[str, ...] = ()) -> ToolRegistry:
    """Like `_counting_registry`, but a named check can report a problem.

    The failure is returned as a `ToolOutcome`, which is how a real read-only
    tool reports one, rather than raised: an exit check that raised would be
    indistinguishable from a registry that could not find it.
    """

    registry = ToolRegistry()

    def counter(name: str):
        def handler(_arguments: dict[str, Any]) -> Any:
            records[name] = records.get(name, 0) + 1
            if name in failing:
                return ToolOutcome(name, "error", f"{name} found a problem")
            return {"message": f"{name} ok", "data": {}}

        return handler

    for name in (READ_ONLY_TOOL, ANOTHER_READ_ONLY_TOOL):
        registry.register(
            ToolSpec(
                name=name,
                description=name,
                input_schema={"type": "object", "properties": {}},
                handler=counter(name),
            )
        )
    return registry
