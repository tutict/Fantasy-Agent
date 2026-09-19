"""Role instructions, wired from `skills/` into each stage's system prompt.

The gap this closes: `ProductionPipelineStage.owner_agent` has been in the
contract since the pipeline existed, it is rendered in the UI, and nothing in
Python ever read it. Meanwhile seven `skills/*/SKILL.md` files described how the
work should be done, and no stage ever saw one. The two lists did not even use
the same names -- `blender-worker` vs `blender-generator` -- which is why this is
an explicit mapping table rather than a rename: three roles have no counterpart
at all, so renaming could not have made them line up anyway.

The split the tests below pin down: the *stage table* says what the work is
(`purpose`, `outputs`), the *skill* says how to do it (guardrails, workflow). If
a skill's own "inputs"/"outputs" sections were passed along as well, the model
would be reading two lists that can drift, which is the failure mode the
translation table and `exit_checks` were both added to avoid.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fantasy_agent import agent_skills
from fantasy_agent.agent_skills import (
    AGENT_SKILLS,
    MAX_BRIEF_CHARS,
    SKILLS_WITHOUT_AGENT,
    skill_brief,
)
from fantasy_agent.contracts import (
    ProductionPipelineStage,
    ProductionTaskAgent,
    PromptRequest,
)
from fantasy_agent.workflows import run_director_workflow

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
PROMPT = "a stealth courier escapes a haunted train station in ten minutes"
ROUTES = ("Godot 4", "Unreal Engine 5")


def _plan_stages():
    for route in ROUTES:
        pipeline = run_director_workflow(
            PromptRequest(prompt=PROMPT, engine_version=route)
        ).production_pipeline
        assert pipeline is not None
        for stage in pipeline.stages:
            yield route, stage


def _roles_the_pipeline_uses() -> set[str]:
    used: set[str] = set()
    for _route, stage in _plan_stages():
        used.add(stage.owner_agent)
        used.update(stage.participating_agents)
    return used


def test_every_role_the_pipeline_uses_has_an_entry():
    """A missing entry is a stage that runs with no role instruction at all.

    Read off the plans rather than off the contract's Literal: the Literal says
    which roles *may* appear, and only the plans say which ones do.
    """

    used = _roles_the_pipeline_uses()

    missing = sorted(used - set(AGENT_SKILLS))
    assert not missing, f"roles the pipeline uses have no AGENT_SKILLS entry: {missing}"


def test_the_table_covers_the_whole_contract_not_just_todays_plans():
    """Extra entries are how a role stays covered when a stage starts using it."""

    from typing import get_args

    declared = set(get_args(ProductionTaskAgent))

    missing = sorted(declared - set(AGENT_SKILLS))
    assert not missing, f"roles declared by the contract have no entry: {missing}"


def test_a_role_with_no_skill_says_why():
    """An absence with a reason is a decision; an absence without one is a hole.

    Follows `_HIDDEN_ARG_WITHOUT_SOURCE`: the entries that are deliberately None
    are enumerated with their reasons, so "why does director-agent have no
    skill" is answered in the code rather than re-litigated every time.
    """

    without = sorted(role for role, skill in AGENT_SKILLS.items() if skill is None)

    assert without, "nothing is None, so this test would pass for the wrong reason"
    assert without == sorted(SKILLS_WITHOUT_AGENT), (
        "a role without a skill and the table of reasons have drifted apart"
    )
    for role, reason in SKILLS_WITHOUT_AGENT.items():
        assert len(reason) > 40, f"{role}'s reason is too short to be one: {reason!r}"


def test_every_named_skill_directory_exists():
    for role, skill in AGENT_SKILLS.items():
        if skill is None:
            continue
        assert (SKILLS_DIR / skill / "SKILL.md").is_file(), (
            f"{role} points at a skill directory that does not exist: {skill}"
        )


def test_every_skill_directory_is_claimed_by_a_role():
    """The other direction: a skill nobody loads is prose nobody reads.

    Both halves of this guard have been wrong at some point in this project's
    other tables, so both directions are asserted rather than just the one the
    feature happens to exercise today.
    """

    on_disk = {path.name for path in SKILLS_DIR.iterdir() if path.is_dir()}
    claimed = {skill for skill in AGENT_SKILLS.values() if skill is not None}

    assert on_disk, "the skills directory is empty, so this test proves nothing"
    assert sorted(on_disk - claimed) == [], "skill directories no role loads"


def test_the_brief_drops_the_inputs_and_outputs_sections():
    """Those two lists live in the stage table, and a second copy can drift.

    The stage goal is built from `purpose` / `outputs` off `ProductionPipeline`,
    which is the copy the orchestrator gates on. Passing the skill's own copy
    along as well would put two answers in one prompt with nothing deciding
    which one wins.
    """

    brief = skill_brief("gdd-writer")

    assert brief.strip(), "the brief came back empty, so the rest is vacuous"
    assert "## 输入" not in brief
    assert "## 输出" not in brief
    # The sections either side of the dropped pair survive, which is what makes
    # this a strip rather than a truncation.
    assert "## 职责" in brief
    assert "## 护栏" in brief


def test_the_brief_keeps_every_skill_guardrail_section():
    """`护栏` is the half of a skill that is about *how*, so it has to survive."""

    for skill in sorted({s for s in AGENT_SKILLS.values() if s is not None}):
        text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
        if "## 护栏" not in text and "## 规则" not in text:
            continue
        brief = skill_brief(skill)
        assert "## 护栏" in brief or "## 规则" in brief, skill


def test_an_unknown_skill_is_an_empty_brief_rather_than_a_crash():
    """A stage that names a skill nobody wrote runs with the shared prompt.

    Raising here would turn a missing *document* into a dead stage, which is a
    far worse trade than a stage with the generic instructions.
    """

    assert skill_brief("no-such-skill") == ""


def test_the_instructions_carry_the_roles_guardrails():
    """The wiring itself: the role's brief reaches the system prompt."""

    from fantasy_agent.orchestrator import STAGE_INSTRUCTIONS, stage_instructions

    stage = ProductionPipelineStage(
        id="blender_modeling",
        order=1,
        title="probe",
        purpose="produce placeholder meshes",
        owner_agent="blender-worker",
        inputs=["BlenderAssetPlan"],
        outputs=["glb files"],
        mcp_tools=["generate_blender_script"],
    )

    instructions = stage_instructions(stage)

    assert instructions.startswith(STAGE_INSTRUCTIONS)
    assert "## 护栏" in instructions, "the role's guardrails never reached the prompt"
    assert "## 输入" not in instructions
    assert "## 输出" not in instructions


def test_a_role_without_a_skill_gets_the_shared_instructions_unchanged():
    from fantasy_agent.orchestrator import STAGE_INSTRUCTIONS, stage_instructions

    stage = ProductionPipelineStage(
        id="gameplay_orchestration",
        order=1,
        title="probe",
        purpose="plan the production",
        owner_agent="director-agent",
        inputs=["PromptRequest"],
        outputs=["ProductionPipeline"],
        mcp_tools=["extract_idea_seed"],
    )

    assert stage_instructions(stage) == STAGE_INSTRUCTIONS


def test_the_goal_still_carries_purpose_and_outputs_not_the_skills_copy():
    """The other half of the split, asserted together with the brief.

    `stage_instructions` answers "how"; `_stage_goal` answers "what". Pinned in
    one place because the failure mode is overlap: both halves describing the
    outputs, and the two descriptions starting to disagree.
    """

    from fantasy_agent.orchestrator import _stage_goal

    stage = ProductionPipelineStage(
        id="blender_modeling",
        order=1,
        title="probe",
        purpose="produce placeholder meshes",
        owner_agent="blender-worker",
        inputs=["BlenderAssetPlan"],
        outputs=["glb files", "import manifest"],
        mcp_tools=["generate_blender_script"],
    )

    goal = _stage_goal(stage)

    assert goal.startswith("produce placeholder meshes")
    assert "glb files" in goal and "import manifest" in goal
    # The inputs are deliberately not in the goal: the stage's tools are given
    # to it as a whitelist, and a third list naming files would be a guess.
    assert "BlenderAssetPlan" not in goal


@pytest.mark.parametrize("skill", sorted({s for s in AGENT_SKILLS.values() if s is not None}))
def test_every_brief_is_small_enough_to_send_on_every_turn(skill: str):
    """It rides in the system prompt of every stage of every run.

    A skill that grew into a document would multiply the cost of the whole
    pipeline, so the ceiling is asserted rather than left to review. The number
    comes from `MAX_BRIEF_CHARS` rather than being written out again: a second
    copy of the same number is a second thing to forget to change.
    """

    brief = skill_brief(skill)

    assert len(brief) <= MAX_BRIEF_CHARS, f"{skill}'s brief is {len(brief)} chars"


def test_an_oversized_brief_is_cut_to_the_ceiling(tmp_path, monkeypatch):
    """The ceiling has to be *applied*, not merely declared.

    `MAX_BRIEF_CHARS` was exported with a comment promising it bounds what goes
    into every turn's system prompt, and nothing read it -- so the guarantee held
    only for as long as no skill happened to grow. The test above asserts today's
    briefs fit; this one proves the cut exists at all, by feeding in a skill that
    does not fit. Without it, deleting the slice above stays green.
    """

    wordy = tmp_path / "wordy"
    wordy.mkdir()
    (wordy / "SKILL.md").write_text(
        "## 职责\n" + "走查" * (MAX_BRIEF_CHARS + 200), encoding="utf-8"
    )
    monkeypatch.setattr(agent_skills, "SKILLS_DIR", tmp_path)
    try:
        brief = skill_brief("wordy")

        assert len(brief) == MAX_BRIEF_CHARS
        # Cut, not rejected: what fits is still the head of the real brief.
        assert brief.startswith("## 职责")
    finally:
        # `skill_brief` is lru_cached, so a brief read out of the temporary
        # directory would otherwise outlive this test and answer for a real
        # skill name later in the session.
        skill_brief.cache_clear()
