"""Advance a ``ProductionPipeline`` stage by stage, without deciding for the model.

Before this module the internal agent loop was offered one flat list of ~20
tools and told to work out the order itself. The pipeline table already said
what the order was, which tools each stage runs and what has to finish first --
and nothing read it. This layer reads it, and does one thing: for each stage in
``order``, work out whether it may run, and if so hand the loop a registry
containing only that stage's tools.

What it deliberately does NOT do:

- **It never decides whether an action is allowed.** Grants come in from the
  caller, the gate stays in ``ToolRegistry``, and ``permission_ceiling`` is the
  same rule the loop already applied. Narrowing the tool list changes *what the
  model can attempt*, never *what it may do*.
- **It does not pick a tool.** A stage's ``mcp_tools`` is the whole menu; the
  model still chooses within it, and still gets refusals back as tool results.
- **It does not replace the deterministic pipeline.** ``run_agent`` already
  returns ``status="error"`` rather than raising when the provider fails, so a
  broken orchestrated run leaves the caller exactly where a broken agent run
  left it.

What it does add on the way out: a stage that declares ``exit_checks`` has those
read-only tools run against its result, and a check that does not report ``ok``
makes the stage ``failed`` rather than ``done``. ``quality_gates`` stays prose
for a human to read -- none of the 21 exported entries is machine-checkable --
so the field is wired and currently empty on every stage; the contract guard
keeps that empty set from hiding a write tool.

Stage status is a *runtime* vocabulary and is deliberately not the plan-time one
``ProductionTaskStatus`` (``pending`` / ``ready`` / ``blocked`` / ``done``) that
``contracts.py`` generates the pipeline with. That field is written once when
the plan is authored and never changes; a board that read it would show a run
that never starts. ``StageOutcome.status`` is what this run actually did.

Where the record goes: ``pipeline_state.record_stage``, under the orchestration
stage id. That file is shared with the executor's own stage records, which use a
different vocabulary (``preflight`` / ``create`` / ``validate`` ...). The two
coexist safely -- resume computes its skip set from ``stages_before``, which
reads the ``order`` tuple and never the recorded names, and
``executor._skippable_stages`` intersects with ``RESUMABLE_STAGES`` -- but the
overlap is pinned by a test rather than left to hold by accident. Translating
one vocabulary into the other is the plan's Task 4.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from fantasy_agent.agent_loop import DEFAULT_MAX_TURNS, AgentRunResult, run_agent
from fantasy_agent.agent_skills import AGENT_SKILLS, skill_brief
from fantasy_agent.contracts import ProductionPipeline, ProductionPipelineStage
from fantasy_agent.human_decision import write_decision_record
from fantasy_agent.orchestration_state import (
    OrchestrationStageState,
    OrchestrationState,
    save_state,
)
from fantasy_agent.pipeline_state import (
    StageState,
    executor_stages_for,
    orchestration_stages_for,
    record_stage,
    resume_stage_for,
)
from fantasy_agent.tool_registry import (
    EXECUTE,
    READ_ONLY,
    WRITE,
    ToolRegistry,
    combined_registry,
)

logger = logging.getLogger(__name__)

#: Mirrors ``contracts.ProductionStageKind``. Spelled out here because a ``Literal``
#: alias has no runtime value to compare against.
HUMAN_STAGE_KIND = "human"

#: What a person may decide about a human gate. ``approved`` lets the stage
#: count as done and unblocks what depends on it; ``rejected`` fails it, which
#: is the honest reading of "the operator sent this back" -- the dependents
#: stay blocked rather than running past a gate somebody refused.
HUMAN_DECISIONS: tuple[str, ...] = ("approved", "rejected")

# ── runtime stage status ─────────────────────────────────────────────────────

READY = "ready"
RUNNING = "running"
BLOCKED = "blocked"
AWAITING_HUMAN = "awaiting_human"
AWAITING_CONFIRMATION = "awaiting_confirmation"
DONE = "done"
FAILED = "failed"

STAGE_STATUSES: tuple[str, ...] = (
    READY,
    RUNNING,
    BLOCKED,
    AWAITING_HUMAN,
    AWAITING_CONFIRMATION,
    DONE,
    FAILED,
)

#: Statuses that mean a person has to act before this stage can move.
WAITING_STATUSES: tuple[str, ...] = (AWAITING_HUMAN, AWAITING_CONFIRMATION)

# ── run status ───────────────────────────────────────────────────────────────

# The run-level vocabulary is not the stage-level one, and on purpose: the
# plan's Task 2 asks for the *stage* to read ``failed`` while the *caller* reads
# ``status="error"``. ``error`` is what a caller branches on to fall back to the
# deterministic pipeline, and it is the same word ``run_agent`` already uses.
RUN_DONE = "done"
RUN_ERROR = "error"

RUN_STATUSES: tuple[str, ...] = (
    RUN_DONE,
    BLOCKED,
    AWAITING_HUMAN,
    AWAITING_CONFIRMATION,
    RUN_ERROR,
)

STAGE_INSTRUCTIONS = (
    "You are advancing one stage of a game production pipeline. Use only the "
    "tools you were given -- they are this stage's inputs, and every other part "
    "of the pipeline is another stage's job. Tool results marked 'refused' were "
    "not executed and cannot be retried by asking again: work with what you "
    "have and say what is missing."
)


def stage_instructions(stage: ProductionPipelineStage) -> str:
    """The system prompt for one stage: the shared rules, plus its role's brief.

    The two halves answer different questions and are deliberately kept apart.
    ``_stage_goal`` builds the *task* out of ``purpose`` and ``outputs`` -- the
    fields the orchestrator gates on. This carries the *manner*: the guardrails
    and workflow from the owner role's skill, which is the part that was written
    down in ``skills/`` and never reached a model.

    They must not overlap, which is why ``skill_brief`` strips a skill's own
    "inputs"/"outputs" sections: two descriptions of the same thing in one prompt
    is how they start to disagree, with nothing deciding which one wins.

    A role with no skill (or a skill directory nobody wrote) gets the shared
    instructions unchanged -- a degraded run rather than a failed one.
    """

    skill = AGENT_SKILLS.get(stage.owner_agent)
    if not skill:
        return STAGE_INSTRUCTIONS
    brief = skill_brief(skill)
    if not brief:
        return STAGE_INSTRUCTIONS
    return f"{STAGE_INSTRUCTIONS}\n\n{brief}"


@dataclass
class StageOutcome:
    """What one stage did, in the runtime vocabulary above."""

    stage_id: str
    status: str
    detail: str = ""
    #: Tools the model was actually offered, after the whitelist and the grant.
    tools: list[str] = field(default_factory=list)
    #: True when an agent was dispatched. False means zero turns were spent,
    #: which is the point of the blocked / awaiting branches.
    dispatched: bool = False
    tool_calls: int = 0
    refusals: list[str] = field(default_factory=list)
    answer: str = ""
    #: Exit checks that ran *and passed*, in the order the stage declared them.
    #: Empty covers both "declares none" and "never got that far" -- ``status``
    #: is what tells those apart, which is why this is not a count of attempts.
    checks: list[str] = field(default_factory=list)

    @property
    def waiting(self) -> bool:
        return self.status in WAITING_STATUSES


@dataclass
class OrchestrationResult:
    """What one ``Orchestrator.run`` pass did to the whole plan."""

    status: str
    stages: list[StageOutcome] = field(default_factory=list)
    error: str = ""
    #: Stages this plan declares need a person, and that nobody has confirmed
    #: yet -- at the end of the pass, so a confirmed stage drops off the list.
    #:
    #: Separate from the per-stage ``awaiting_confirmation`` status because the
    #: two are different user actions. This one means "approve me and I run";
    #: the status alone would also cover "I am allowed to start but not to
    #: write", which approving does not fix. The board needs the first list.
    pending_confirmations: list[str] = field(default_factory=list)
    #: Human gates in this plan nobody has decided yet, at the end of the pass.
    #: A gate is not "approved", it is *decided*, so it has its own list: the
    #: board's summary line has to offer a decision where it offers an approval,
    #: and mixing the two would put an approve button on a card that approving
    #: cannot move.
    pending_human_gates: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == RUN_DONE

    def outcome_for(self, stage_id: str) -> StageOutcome | None:
        return next((entry for entry in self.stages if entry.stage_id == stage_id), None)


class Orchestrator:
    """Walks a plan's stages in ``order`` and dispatches the ones that may run.

    One ``run`` is one **pass**, not one whole production: it walks every stage
    once, dispatches what it can, and reports what each stage is waiting for.
    That is what makes a human gate usable -- the caller acts, calls ``run``
    again, and the pass resumes rather than replaying.

    Resumption is what the per-instance outcome map is for. A stage already
    ``done`` is not dispatched again; without that, confirming stage 5 of 8
    would replay the four expensive stages before it. Re-running a *finished*
    stage is the rework path's job (the plan's Task 4), which resets from an
    explicit target -- ``run`` only ever moves forward.
    """

    def __init__(
        self,
        *,
        session_id: str,
        workspace_root: Path | str,
        engine_key: str = "godot",
        project_dir: str = "",
        registry: ToolRegistry | None = None,
    ) -> None:
        self.session_id = session_id
        self.workspace_root = workspace_root
        self.engine_key = engine_key
        self.project_dir = project_dir
        # The full registry is the source the per-stage slices are cut from.
        self._registry = registry if registry is not None else combined_registry(workspace_root)
        self._outcomes: dict[str, StageOutcome] = {}
        #: Stage ids an operator has approved this session. Kept here rather
        #: than passed once, so the pass after the approval does not ask again.
        self._confirmed: set[str] = set()
        #: Decisions an operator gave for ``kind="human"`` gates, stage id to
        #: decision. Separate from ``_confirmed`` and on purpose: approving a
        #: stage answers "may this run", deciding a gate answers "what did the
        #: person say", and the two have different vocabularies, different
        #: failure modes (a refusal blocks, a decision resolves) and different
        #: writers. Written only by :meth:`resolve_human_stage`.
        self._human_decisions: dict[str, str] = {}
        #: The plan of the pass in flight, kept only so ``_record`` can write a
        #: snapshot. Ten of the fields a board card draws exist nowhere else, so
        #: a snapshot without the plan renders the degenerate board this exists
        #: to fix. Not part of any restore path -- the caller always has the
        #: plan it is posting.
        self._plan: ProductionPipeline | None = None

    @property
    def confirmed(self) -> frozenset[str]:
        """Stages approved so far, so a board can show what it already answered."""

        return frozenset(self._confirmed)

    @property
    def outcomes(self) -> dict[str, StageOutcome]:
        """Per-stage outcomes from every pass so far, keyed by stage id."""

        return dict(self._outcomes)

    @property
    def run_status(self) -> str:
        """The run-level fold of everything that has run, or ``"pending"``.

        The board's read-back endpoint needs the same fold the run response
        got, without running anything: a reload adopted the session and then
        rendered a header with no status at all, because only the run response
        carried one.
        """

        if not self._outcomes:
            return "pending"
        return _run_status(list(self._outcomes.values()))

    def run(
        self,
        plan: ProductionPipeline,
        *,
        allow_write: bool = False,
        allow_execute: bool = False,
        max_turns: int = DEFAULT_MAX_TURNS,
        confirm_stages: Iterable[str] = (),
    ) -> OrchestrationResult:
        """Advance every stage of ``plan`` once, in ``order``.

        Every stage is visited even after one of them stops early: a stage that
        is blocked is not a reason to skip an independent one, and the board
        wants a status for each. ``depends_on`` is what actually stops work.

        ``confirm_stages`` is the per-stage approval, and it is the only thing
        that answers ``requires_confirmation``. The global grants are a
        different question -- *what a stage may do* once it is allowed to start
        -- and deliberately do not imply each other: one switch that authorised
        every stage in a plan is exactly what a per-stage field exists to avoid.
        Confirmations accumulate on the instance, so the pass after an operator
        clicks approve does not ask again.

        Raises:
            ValueError: for a confirmed id that is not a known orchestration
                stage. A typo would otherwise read as "nothing was confirmed",
                and the same stage would wait silently forever.
        """

        self.confirm(confirm_stages)
        self._plan = plan
        # Re-stamped on every pass rather than only when a decision arrives: a
        # decision given before the plan was in hand has no plan to land on, and
        # each pass re-points the session at a freshly posted copy whose stages
        # arrive without stamps. Without this the second pass would show a
        # decided gate as waiting again -- the deadlock this whole change exists
        # to remove, reintroduced one POST later.
        self._stamp_plan()
        ceiling = _ceiling(allow_write=allow_write, allow_execute=allow_execute)
        outcomes: list[StageOutcome] = []
        for stage in sorted(plan.stages, key=lambda entry: entry.order):
            outcome = self._advance(
                stage,
                ceiling=ceiling,
                allow_write=allow_write,
                allow_execute=allow_execute,
                max_turns=max_turns,
            )
            self._outcomes[stage.id] = outcome
            outcomes.append(outcome)
            self._record(stage, outcome)
        return OrchestrationResult(
            status=_run_status(outcomes),
            stages=outcomes,
            error=_first_failure(outcomes),
            pending_confirmations=self.pending_confirmations(plan),
            pending_human_gates=self.pending_human_gates(plan),
        )

    @classmethod
    def restore(
        cls,
        snapshot: OrchestrationState,
        *,
        plan: ProductionPipeline,
        workspace_root: Path | str,
        registry: ToolRegistry | None = None,
    ) -> Orchestrator:
        """Rebuild an orchestrator from a snapshot, so a restart resumes.

        The in-memory outcome map is the thing that makes resumption cheap, and
        a restart used to throw it away: the board still held the session id it
        had written to `localStorage`, and the answer was an empty board. This
        puts the two halves back.

        `_registry` is not restored because it was never state -- it is derived
        from ``workspace_root``, so a fresh instance recomputes it.

        Confirmations come back through :meth:`confirm` rather than by assigning
        ``_confirmed``. That is the whole safety property: ``confirm`` validates
        every id against the translation table, so a hand-edited snapshot naming
        a stage that does not exist fails the whole restore instead of quietly
        installing an approval nobody gave. AGENTS.md forbids the *frontend*
        manufacturing a confirmation; redeeming one the operator actually gave is
        the opposite of that, and this is where the difference is kept.

        Gate decisions come back through :meth:`resolve_human_stage`, read off
        the plan the snapshot carries. Same property, same reason: the plan dump
        is backend-written state (``_stamp_plan`` wrote the decision onto it), so
        restoring from it is redeeming a decision rather than trusting a browser.

        Ids the restored plan does not contain are dropped rather than rejected:
        the same session id can be re-run against a different route, and an
        approval for a stage that is no longer there has nothing to apply to.

        Raises:
            ValueError: when the snapshot names a confirmation that is not a
                known orchestration stage. Partial restore is never returned --
                a half-restored board re-runs some stages and silently skips
                others, which is worse than either extreme.
        """

        self = cls(
            session_id=snapshot.session_id,
            workspace_root=workspace_root,
            engine_key=snapshot.engine,
            registry=registry,
        )
        for entry in snapshot.stages:
            self._outcomes[entry.stage_id] = StageOutcome(
                stage_id=entry.stage_id,
                status=entry.status,
                detail=entry.detail,
                tools=list(entry.tools),
                dispatched=entry.dispatched,
                tool_calls=entry.tool_calls,
                refusals=list(entry.refusals),
                answer=entry.answer,
                checks=list(entry.checks),
            )
        in_plan = {stage.id for stage in plan.stages}
        # Validate, then narrow. This comment used to claim the order was load
        # bearing -- that dropping first "would skip the very check that makes
        # this safe". Measured, it does not: `_confirmed` is still an empty set
        # at this point, so `&= in_plan` is a no-op on it and the swapped order
        # raises exactly the same `ValueError`. What actually carries the
        # property is that the assignments below go through `confirm()` at all
        # (mutation B2 pins that, not the order). Written this way so the two
        # intents stay legible instead of one being credited with the other's
        # guarantee.
        self.confirm(snapshot.confirmed)
        # Then narrow. A legitimate id that this route does not contain has
        # nothing to apply to -- the same session id can be re-run against a
        # different route -- and refusing it would make an unrelated plan change
        # look like a corrupt file.
        self._confirmed &= in_plan
        # Decisions come back the same way and for the same reason: through
        # ``resolve_human_stage``, which validates the value against
        # ``HUMAN_DECISIONS`` and the id against the translation table. The
        # stamps are read off the plan the snapshot carries rather than off the
        # browser's copy, so this redeems a decision the operator actually gave
        # -- the exact mirror of what ``confirmed`` restores, and the reason a
        # plan merely arriving with the field filled does not open a gate:
        # ``_advance`` reads this map, never the field.
        for stage in plan.stages:
            if stage.human_resolution is None:
                continue
            self.resolve_human_stage(stage.id, stage.human_resolution)
        return self

    def snapshot(self, plan: ProductionPipeline) -> OrchestrationState:
        """This instance's board state, as a persistable snapshot.

        Written after ``confirm`` and after every stage, so the stored
        confirmations are by construction the ones an operator clicked rather
        than ones this method inferred from a status -- inferring them is what
        AGENTS.md calls writing the confirmation at the call site, and it would
        hand out an approval nobody gave.
        """

        return OrchestrationState(
            session_id=self.session_id,
            engine=self.engine_key,
            plan=plan.model_dump(mode="json"),
            stages=[
                OrchestrationStageState(
                    stage_id=outcome.stage_id,
                    status=outcome.status,
                    detail=outcome.detail,
                    tools=list(outcome.tools),
                    dispatched=outcome.dispatched,
                    tool_calls=outcome.tool_calls,
                    refusals=list(outcome.refusals),
                    answer=outcome.answer,
                    checks=list(outcome.checks),
                )
                for outcome in self._outcomes.values()
            ],
            confirmed=sorted(self._confirmed),
        )

    def confirm(self, stage_ids: Iterable[str]) -> None:
        """Record an operator's approval for the stages it names.

        Validated against the translation table rather than against a plan, so
        the same id can be confirmed before the plan that contains it is in
        hand. Raises for an unknown id rather than storing it: a stored typo
        would look like a confirmation that never takes effect, and the stage it
        was meant for would wait forever with nothing to show for it.
        """

        for stage_id in stage_ids:
            executor_stages_for(stage_id)  # raises ValueError for an unknown id
            self._confirmed.add(stage_id)

    def pending_confirmations(self, plan: ProductionPipeline) -> list[str]:
        """Stages in ``plan`` that a person has to approve before they can run.

        Ordered as the plan is, so the board can show them in the same sequence
        as the cards. A human gate is not included: approving it would not make
        it run, so offering the operator an approve button for one would be a
        dead end that looks like a control. What a gate needs is a *decision*,
        which is what :meth:`pending_human_gates` lists.
        """

        return [
            stage.id
            for stage in sorted(plan.stages, key=lambda entry: entry.order)
            if stage.requires_confirmation
            and stage.kind != HUMAN_STAGE_KIND
            and stage.id not in self._confirmed
        ]

    @property
    def human_decisions(self) -> dict[str, str]:
        """Decisions given so far, keyed by stage id, so a board can show them."""

        return dict(self._human_decisions)

    def resolve_human_stage(self, stage_id: str, decision: str) -> None:
        """Record a person's decision for a human gate.

        The only writer of ``_human_decisions``, and deliberately shaped like
        :meth:`confirm`: the id is validated against the translation table
        rather than a plan, so the same gate can be decided before the plan
        that contains it is in hand, and an unknown id raises rather than
        storing -- a stored typo would look like a decision that never takes
        effect, and the gate would wait forever with nothing to show for it.

        The decision is also stamped onto the plan the instance is holding (if
        it has one), because the plan dump is what the snapshot carries: that
        is how a decision survives a restart, and it is the same discipline
        ``confirmed`` uses -- the record rides in backend-written state, never
        in something the browser authored. A plan that merely *arrives* with
        ``human_resolution`` already filled does not open the gate, because
        ``_advance`` reads this map and not the field.

        Raises:
            ValueError: for an unknown stage id, or a decision outside
                ``HUMAN_DECISIONS``. Both would otherwise read as a decision
                that silently did nothing.
        """

        executor_stages_for(stage_id)  # raises ValueError for an unknown id
        if decision not in HUMAN_DECISIONS:
            raise ValueError(
                f"decision {decision!r} is not one of {list(HUMAN_DECISIONS)}"
            )
        self._human_decisions[stage_id] = decision
        self._stamp_plan()

    def _stamp_plan(self) -> None:
        """Write the decisions onto the plan, so the snapshot's dump carries them.

        The plan is the session's record, not the browser's: every pass
        re-points the session at the plan that was posted, and a posted plan
        arrives without the stamps (the frontend has no business writing
        them). Stamping here is what keeps "what was decided" attached to the
        session instead of to whichever copy of the plan happened to be posted.
        """

        if self._plan is None:
            return
        for stage in self._plan.stages:
            decision = self._human_decisions.get(stage.id)
            if decision is not None:
                stage.human_resolution = decision

    def pending_human_gates(self, plan: ProductionPipeline) -> list[str]:
        """Gates in ``plan`` still waiting for a person's decision.

        Separate from ``pending_confirmations`` because the two ask different
        things of the operator -- approve a stage so it may run, decide a gate
        so the plan may continue -- and the board's summary line says which.
        Ordered as the plan is, like the other pending list.
        """

        return [
            stage.id
            for stage in sorted(plan.stages, key=lambda entry: entry.order)
            if stage.kind == HUMAN_STAGE_KIND
            and stage.id not in self._human_decisions
        ]

    def rewind_from(self, plan: ProductionPipeline, stage_id: str) -> list[str]:
        """Forget ``stage_id`` and everything after it, so the next pass redoes them.

        The rework path, and the reason ``run`` can stay forward-only. A stage
        that failed, or whose *inputs* were fixed by hand, has to actually run
        again; without this the outcome map would answer every later pass with
        the cached result and the only way to redo a node would be a fresh
        session -- the full replay the stage table exists to avoid.

        A rewound stage also loses its operator confirmation. What the reworked
        stage will run is not what was approved before, so the gate has to ask
        again: leaving ``_confirmed`` intact would let the next pass dispatch
        straight through a stage the person only ever approved in its earlier
        form.

        Stops at the plan rather than at the drill-down table: only stages the
        plan actually contains are dropped, which is what keeps a Godot rework
        from disturbing an Unreal plan that shares the same instance.

        Returns:
            The ids dropped, in `order`. Empty when nothing had run yet.

        Raises:
            ValueError: when ``stage_id`` is not a stage of ``plan``. A typo
                here would otherwise rewind either everything or nothing, and
                both read as "the rework did not help" much later.
        """

        order = {stage.id: stage.order for stage in plan.stages}
        if stage_id not in order:
            raise ValueError(f"{stage_id!r} is not a stage of this plan")
        cutoff = order[stage_id]
        dropped = sorted(
            (
                other
                for other, position in order.items()
                if position >= cutoff and other in self._outcomes
            ),
            key=lambda other: order[other],
        )
        for name in dropped:
            del self._outcomes[name]
            self._confirmed.discard(name)
        return dropped

    def rewind_for_rework(
        self,
        plan: ProductionPipeline,
        *,
        rework_target: str,
        code: str = "",
    ) -> str | None:
        """Turn a rework hint into "resume from this card on the board".

        Three vocabularies in a row, and each hop is a real translation:

        - the hint (``godot_plan``) says what to *fix*;
        - ``resume_stage_for`` turns it into the execution stage to re-run
          (``create``);
        - ``orchestration_stages_for`` turns that into the board cards that own
          the step (``godot_quick_play`` here, ``unreal_production`` too in the
          abstract).

        When more than one card owns the step, the earliest one still present in
        this plan wins: rewinding further back is the conservative direction,
        since the stages skipped in between would otherwise be reused after
        their inputs stopped being valid.

        Returns:
            The card that was rewound, or None when the hint resolves to nothing
            this plan runs -- which leaves the run untouched so the caller can
            fall back rather than silently restart.
        """

        executor_stage = resume_stage_for(rework_target, code)
        if executor_stage is None:
            return None
        order = {stage.id: stage.order for stage in plan.stages}
        owned = [name for name in orchestration_stages_for(executor_stage) if name in order]
        if not owned:
            return None
        target = min(owned, key=lambda name: order[name])
        self.rewind_from(plan, target)
        return target

    def _advance(
        self,
        stage: ProductionPipelineStage,
        *,
        ceiling: str,
        allow_write: bool,
        allow_execute: bool,
        max_turns: int,
    ) -> StageOutcome:
        prior = self._outcomes.get(stage.id)
        if prior is not None and prior.status == DONE:
            return prior

        # Checked before the human gate on purpose. A human stage whose inputs
        # do not exist yet must read as "not yet", not as "your decision is
        # needed" -- asking someone to approve something they cannot see is how
        # a gate gets clicked through without being read.
        unmet = [dep for dep in stage.depends_on if not self._is_done(dep)]
        if unmet:
            return StageOutcome(
                stage.id,
                BLOCKED,
                detail=f"waiting on: {', '.join(unmet)}",
            )

        if stage.kind == HUMAN_STAGE_KIND:
            # A gate is not "approved", it is *decided*, and the decision is
            # looked up here rather than read off the plan: a plan that arrives
            # with the field filled must not open a gate nobody decided, which
            # is the same line AGENTS.md draws for ``confirmed``.
            decision = self._human_decisions.get(stage.id)
            if decision is None:
                return StageOutcome(
                    stage.id,
                    AWAITING_HUMAN,
                    detail="this stage is a person's decision; no tools are run for it",
                )
            # The decision is durable before the stage counts as done: the
            # stage's ``artifacts`` name a record, and a board showing ``done``
            # next to a file nobody wrote is the artifact-honesty bug G-03
            # spent on the playtest report. A failure to write is logged, not
            # raised -- the person did decide, and losing the stage over the
            # record of it would be the worse trade.
            self._record_decision(stage, decision)
            if decision == "approved":
                return StageOutcome(
                    stage.id,
                    DONE,
                    detail=f"decision recorded: {decision}",
                )
            return StageOutcome(
                stage.id,
                FAILED,
                detail=(
                    f"decision recorded: {decision} -- the operator sent this "
                    f"gate back, so what depends on it stays blocked"
                ),
            )

        # Before the tool list is even resolved, on purpose. Until somebody has
        # approved the stage there is nothing to say about its tools -- and
        # reporting "your whitelist has a typo" for a stage the operator has not
        # agreed to run yet would be answering a question nobody asked. The
        # mis-declaration still surfaces, one approval later.
        if stage.requires_confirmation and stage.id not in self._confirmed:
            return StageOutcome(
                stage.id,
                AWAITING_CONFIRMATION,
                detail=(
                    "this stage declares requires_confirmation and has not been "
                    "approved for this session; a global write/execute grant is a "
                    "different question and does not answer it"
                ),
            )

        if not stage.mcp_tools:
            # Task 1's contract guard makes this unreachable from a generated
            # plan. It can still arrive from a hand-written one, and the honest
            # reading is "this stage is mis-declared", not "nothing to do".
            return StageOutcome(
                stage.id,
                FAILED,
                detail="an agent stage that declares no mcp_tools has nothing to run",
            )

        try:
            visible = self._registry.scoped(stage.mcp_tools, up_to=ceiling)
        except ValueError as exc:
            return StageOutcome(stage.id, FAILED, detail=str(exc))

        offered = visible.names()
        if not offered:
            # Every tool this stage declares is real, and every one of them is
            # above the grant. Dispatching here would spend a model turn on an
            # agent with an empty tool list, so the stage waits for the human
            # instead -- which is the whole point of a stage-level grant.
            return StageOutcome(
                stage.id,
                AWAITING_CONFIRMATION,
                detail=(
                    f"all {len(stage.mcp_tools)} tool(s) this stage declares need a "
                    f"grant above {ceiling}: {', '.join(stage.mcp_tools)}"
                ),
                tools=[],
            )

        return self._dispatch(
            stage,
            visible,
            offered=offered,
            ceiling=ceiling,
            allow_write=allow_write,
            allow_execute=allow_execute,
            max_turns=max_turns,
        )

    def _dispatch(
        self,
        stage: ProductionPipelineStage,
        registry: ToolRegistry,
        *,
        offered: list[str],
        ceiling: str,
        allow_write: bool,
        allow_execute: bool,
        max_turns: int,
    ) -> StageOutcome:
        logger.info("stage %s: dispatching %d tool(s)", stage.id, len(offered))
        result: AgentRunResult = run_agent(
            _stage_goal(stage),
            registry=registry,
            max_turns=max_turns,
            allow_write=allow_write,
            allow_execute=allow_execute,
            permission_ceiling=ceiling,
            instructions=stage_instructions(stage),
        )

        outcome = StageOutcome(
            stage.id,
            DONE,
            detail="",
            tools=offered,
            dispatched=True,
            tool_calls=result.tool_calls,
            refusals=list(result.refusals),
            answer=result.answer,
        )
        if result.status == RUN_ERROR:
            # run_agent turns an LLMError into status="error" instead of
            # raising, so a provider failure is one stage's failure and not a
            # dead run: the stages that already finished keep their outcomes.
            outcome.status = FAILED
            outcome.detail = result.error
            return outcome
        if result.status != DONE:
            # max_turns / no_provider: the stage did not reach its own end.
            # Calling that "done" would let an unfinished stage unblock the
            # ones behind it.
            outcome.status = FAILED
            outcome.detail = f"the agent stopped before finishing the stage ({result.status})"
            return outcome
        self._run_exit_checks(stage, outcome)
        return outcome

    def _run_exit_checks(self, stage: ProductionPipelineStage, outcome: StageOutcome) -> None:
        """Read the stage's own output, and fail the stage if it does not hold up.

        ``quality_gates`` is prose a human reads; ``exit_checks`` is the part a
        machine can settle. A stage that ran but does not pass its own check is
        ``failed``, not ``done`` -- calling it done would unblock the next stage
        on output this stage says is wrong, and the failure would surface at the
        end of the run instead of at the node that caused it.

        Called through the **full** registry, not the stage's slice: the slice
        narrows what the *model* may attempt, and a check is the pipeline reading
        its own output. Routing it through the scoped registry would look
        harmless and then silently skip every check whose name the stage does
        not also offer -- verifying nothing while reporting success.

        No grant is asked for, and that is safe for the one reason the contract
        guard pins: every name in ``exit_checks`` resolves to a read-only tool.
        A name that would need a grant is refused by the registry like any other
        call and lands here as a failed check, which is the honest reading of a
        stage whose table asks to launch something on the way out.
        """

        for name in stage.exit_checks:
            if self._registry.get(name) is None:
                outcome.status = FAILED
                outcome.detail = (
                    f"exit check {name} is not a registered tool, so this stage "
                    "would have been reported verified without being checked"
                )
                return
            check = self._registry.call(name, {})
            if check.status != "ok":
                outcome.status = FAILED
                outcome.detail = f"exit check {name} did not pass: {check.content}"
                return
            outcome.checks.append(name)

    def _is_done(self, stage_id: str) -> bool:
        prior = self._outcomes.get(stage_id)
        return prior is not None and prior.status == DONE

    def _record(self, stage: ProductionPipelineStage, outcome: StageOutcome) -> None:
        """Persist this stage's outcome where the rest of the run can read it.

        Every outcome is recorded, including the ones that are still waiting.
        A board that only saw finished stages could not tell "blocked" from
        "not reached yet", which is the whole difference the status field
        exists to carry.

        Two files, on purpose. The stage ledger is the executor's vocabulary and
        answers "which node may I skip"; the snapshot is the board's and answers
        "what did that card do". They also have different concurrency: the
        ledger is a read-modify-write of one model that the single-worker pool
        and a request thread can both touch, while the snapshot is written whole.
        Folding one into the other would mean one silently overwriting the other.

        Each write is independent and neither failure discards the other: the
        stage already ran, and throwing away an outcome that cost model turns to
        produce, over a record of it, is the worse outcome.
        """

        try:
            record_stage(
                self.session_id,
                StageState(
                    name=stage.id,
                    status=outcome.status,
                    detail=outcome.detail,
                    artifacts=list(stage.artifacts),
                    logs=list(outcome.refusals),
                ),
                engine_key=self.engine_key,
                project_dir=self.project_dir,
                workspace_root=self.workspace_root,
            )
        except Exception:
            # Deliberately without a noqa directive, and that is a fact about
            # ruff rather than an oversight: BLE001 exempts a blind handler that
            # logs the exception, so writing the directive here makes RUF100
            # flag it as unused. (Naming the directive literally in this comment
            # is what ruff's own noqa scanner would pick up -- hence the
            # paraphrase.)
            #
            # The stage already ran; failing here would throw away an outcome
            # that cost model turns to produce, over a record of it.
            logger.exception("could not record stage %s", stage.id)

        if self._plan is None:
            # Only reachable if a caller drives `_record` outside a `run`, which
            # nothing does. Writing a snapshot without the plan would render a
            # board whose cards have no titles.
            return
        try:
            save_state(self.snapshot(self._plan), workspace_root=self.workspace_root)
        except Exception:
            logger.exception("could not snapshot stage %s", stage.id)

    def _record_decision(
        self, stage: ProductionPipelineStage, decision: str
    ) -> None:
        """Write the decision to disk, where the rest of the session reads it.

        The stage counts as done only after this file exists: a human stage's
        ``artifacts`` name the record, and a board showing ``done`` next to a
        file nobody wrote is the artifact-honesty problem G-03 spent on the
        playtest report. The decision is therefore durable *before* the outcome
        turns, which is why ``_advance`` calls this on the way out rather than
        leaving it to the stage's own tool list -- a gate runs no tools.

        A failure to write is logged, not raised. The person did decide, and
        losing the stage over the record of it would be the worse trade; the
        stage still advances, and the log line says the file is missing.
        """

        try:
            path = write_decision_record(
                self.session_id,
                stage.id,
                decision,
                engine_key=self.engine_key,
                workspace_root=self.workspace_root,
            )
        except Exception:
            # Same shape and same reason as ``_record``: a blind handler that
            # logs is exempt, so naming the directive would be flagged unused.
            logger.exception("could not record the decision for stage %s", stage.id)
            return
        logger.info(
            "decision %r for stage %s recorded at %s", decision, stage.id, path
        )


def _ceiling(*, allow_write: bool, allow_execute: bool) -> str:
    """Highest tier to even offer, following the grants.

    Same rule ``run_agent`` applies on its own; computed here as well because
    the orchestrator has to know the answer *before* dispatch, to tell an
    unaffordable stage from a runnable one.
    """

    if allow_execute:
        return EXECUTE
    if allow_write:
        return WRITE
    return READ_ONLY


def _stage_goal(stage: ProductionPipelineStage) -> str:
    """The stage's purpose, plus what it is supposed to produce.

    Task 6 of the plan wants the role instruction layered on top of exactly
    these two fields, so the goal carries them and nothing else: the system
    prompt says *how* to work, this says *what* the work is.
    """

    lines = [stage.purpose]
    if stage.outputs:
        lines.append("This stage produces: " + ", ".join(stage.outputs))
    return "\n".join(lines)


def _run_status(outcomes: list[StageOutcome]) -> str:
    """Fold per-stage statuses into one the caller can branch on.

    ``error`` outranks the waiting states: if something broke, that is the news,
    even when another stage is also waiting for a person. An empty plan is
    ``done`` -- there was nothing to advance and nothing went wrong.
    """

    statuses = {outcome.status for outcome in outcomes}
    if FAILED in statuses:
        return RUN_ERROR
    if AWAITING_HUMAN in statuses:
        return AWAITING_HUMAN
    if AWAITING_CONFIRMATION in statuses:
        return AWAITING_CONFIRMATION
    if BLOCKED in statuses:
        return BLOCKED
    return RUN_DONE


def _first_failure(outcomes: list[StageOutcome]) -> str:
    for outcome in outcomes:
        if outcome.status == FAILED:
            return f"{outcome.stage_id}: {outcome.detail}" if outcome.detail else outcome.stage_id
    return ""


__all__ = [
    "AWAITING_CONFIRMATION",
    "AWAITING_HUMAN",
    "BLOCKED",
    "DONE",
    "FAILED",
    "HUMAN_STAGE_KIND",
    "READY",
    "RUNNING",
    "RUN_DONE",
    "RUN_ERROR",
    "RUN_STATUSES",
    "STAGE_STATUSES",
    "WAITING_STATUSES",
    "OrchestrationResult",
    "Orchestrator",
    "StageOutcome",
]
