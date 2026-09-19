"""Which `skills/` brief each production role runs with.

`ProductionPipelineStage.owner_agent` has been in the contract since the
pipeline existed, it is rendered in the UI, and nothing in Python read it. Seven
`skills/*/SKILL.md` files described how each kind of work is done, and no stage
ever saw one. This module is the join between the two.

**Why a table and not a rename.** The two lists do not use the same names
(`blender-worker` vs `blender-generator`), and three roles have no counterpart at
all, so renaming could not have made them line up. `owner_agent` is a `Literal`
in `contracts.py` that travels in JSON and is rendered by the frontend, so
changing it is a breaking change; the skill directory names are prose with no
frontmatter, so changing them buys nothing. Same reasoning as `KNOWN_WITHOUT_UI`
and `_HIDDEN_ARG_WITHOUT_SOURCE`: express the mapping, enumerate the exceptions,
and let a test hold both ends.

**What a brief is for.** The stage table says *what* the work is -- `purpose` and
`outputs`, which the orchestrator already gates on. A skill says *how*: the
guardrails, the workflow, the shape of the document. The two must not overlap,
which is why ``skill_brief`` drops a skill's own "inputs"/"outputs" sections
before it goes into a prompt. Two lists describing the same thing is how they
start to disagree.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fantasy_agent.contracts import ProductionTaskAgent

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

#: Role -> directory under `skills/`, or None when the role has no reusable
#: brief. Every None has an entry in ``SKILLS_WITHOUT_AGENT``.
#:
#: The three absences are not all the same kind of thing, which is the argument
#: for keeping them visible instead of quietly omitting them: `director-agent` is
#: an orchestration role whose capability is split across three other skills,
#: while `godot-builder` and `qa-agent` have no brief because nobody has written
#: one yet.
AGENT_SKILLS: dict[ProductionTaskAgent, str | None] = {
    "director-agent": None,
    "gameplay-agent": "gameplay-designer",
    "gdd-writer": "gdd-writer",
    "level-director": "level-director",
    "blender-worker": "blender-generator",
    "comfyui-worker": "comfyui-generator",
    "creative-review-agent": "creative-reviewer",
    "unreal-builder": "ue-architect",
    "godot-builder": None,
    "qa-agent": None,
}

#: Why a role has no brief. An absence with a reason is a decision; an absence
#: without one is a hole somebody re-opens every few months.
SKILLS_WITHOUT_AGENT: dict[str, str] = {
    "director-agent": (
        "Orchestration role: its output is the pipeline table itself, and the "
        "three skills that would apply here (gameplay-designer, gdd-writer, "
        "level-director) each describe one stage of it. Concatenating all three "
        "would hand every stage guardrails written for a different one -- the "
        "opposite of narrowing."
    ),
    "godot-builder": (
        "No Godot brief exists. The seven directories cover planning, the GDD, "
        "level direction, the asset and visual workers, creative review and "
        "Unreal; 'how to build in Godot' currently lives in godot_mcp's code "
        "generation, which is an implementation rather than an instruction. "
        "Write one before adding an entry here."
    ),
    "qa-agent": (
        "No QA brief exists, and none is needed yet: the QA plan comes from the "
        "deterministic prepare_qa_plan workflow, so there is no craft for a "
        "model to be told how to practise."
    ),
}

#: Sections a brief must not carry, because the stage table already owns them.
#: Named in the language the files are written in -- which is also the reason
#: this is a data table and not a regex on headings in general.
_DROPPED_SECTIONS: tuple[str, ...] = ("输入", "输出")

#: Ceiling for one brief, in characters. It rides in the system prompt of every
#: turn of every stage, so a skill that grew into a document would multiply the
#: cost of an entire run.
MAX_BRIEF_CHARS = 4000


def _strip_sections(text: str) -> str:
    """Drop the named `##` sections, keeping everything around them.

    A strip rather than a truncation: the sections on either side survive, which
    is what keeps a skill's guardrails in the prompt.
    """

    kept: list[str] = []
    dropping = False
    for line in text.splitlines():
        if line.startswith("## "):
            dropping = line[3:].strip() in _DROPPED_SECTIONS
        if not dropping:
            kept.append(line)
    return "\n".join(kept).strip()


@lru_cache(maxsize=len(AGENT_SKILLS))
def skill_brief(name: str) -> str:
    """The prompt fragment for one skill directory, or `""` when there is none.

    Returns empty rather than raising for a name that does not resolve: a
    missing *document* must not turn into a dead stage. The stage then runs on
    the shared instructions, which is the same thing that happens to a role with
    no skill at all -- a degraded run, not a failed one, which is the promise
    AGENTS.md makes about missing local tooling.
    """

    path = SKILLS_DIR / name / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    # The cut is applied here rather than trusted to whoever writes a skill,
    # because this text rides in the system prompt of every turn of every stage:
    # a skill that grew into a document would multiply the cost of a whole run.
    # Today's longest brief is under a quarter of the ceiling, so this is a
    # guard rather than a routine edit -- which is exactly why the test that
    # covers it feeds in an oversized file instead of asserting today's sizes.
    return _strip_sections(text)[:MAX_BRIEF_CHARS]


__all__ = [
    "AGENT_SKILLS",
    "MAX_BRIEF_CHARS",
    "SKILLS_DIR",
    "SKILLS_WITHOUT_AGENT",
    "skill_brief",
]
