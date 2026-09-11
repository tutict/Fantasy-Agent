from __future__ import annotations

import json
import logging
import os
import re

from fantasy_agent.axis_templates import AXIS_TEMPLATES, verb_fields
from fantasy_agent.contracts import (
    EnemySpec,
    GameplaySpec,
    LevelBeat,
    LoopStep,
    ProgressionSpec,
    PromptRequest,
    SystemSpec,
)
from fantasy_agent.i18n import VERB_ZH, build_i18n_bundle, contains_cjk

logger = logging.getLogger(__name__)


def _clean_title(prompt: str) -> str:
    if _looks_like_career_portfolio(prompt):
        return "Road Beyond The Fog"
    if contains_cjk(prompt):
        compact = re.sub(r"\s+", "", prompt.strip())
        return compact[:18] or "Untitled Prototype"
    words = re.findall(r"[A-Za-z0-9]+", prompt)
    if not words:
        return "Untitled Prototype"
    meaningful = [word for word in words if len(word) > 2][:5]
    return " ".join(meaningful).title() or "Untitled Prototype"


def _looks_like_career_portfolio(prompt: str) -> bool:
    text = prompt.lower()
    return any(
        term in text or term in prompt
        for term in [
            "应聘",
            "求职",
            "作品集",
            "游戏策划",
            "转职",
            "他人评价",
            "自己的道路",
            "自废武功",
            "外部 plan",
            "external plan",
            "borrowed plan",
            "game design applicant",
            "portfolio",
            "career pivot",
            "interview gate",
            "memory room",
        ]
    )


def _detect_axis(prompt: str) -> str:
    text = prompt.lower()
    if _looks_like_career_portfolio(prompt):
        return "career"
    if any(
        term in text
        for term in [
            "parkour",
            "free-run",
            "freerun",
            "rooftop",
            "wall-run",
            "wall run",
            "vault",
            "slide",
            # Chinese
            "跑酷",
            "翻越",
            "墙跑",
            "滑铲",
            "屋顶",
            "飞檐走壁",
        ]
    ):
        return "parkour"
    if any(
        term in text
        for term in ["stealth", "sneak", "shadow", "潜行", "躲藏", "暗杀", "潜入"]
    ):
        return "stealth"
    if any(
        term in text
        for term in ["survival", "hunger", "storm", "oxygen", "生存", "饥饿", "求生"]
    ):
        return "survival"
    if any(
        term in text
        for term in ["puzzle", "logic", "switch", "portal", "解谜", "谜题", "机关", "传送门"]
    ):
        return "puzzle"
    if any(
        term in text
        for term in ["combat", "fight", "boss", "weapon", "战斗", "格斗", "武器", "打斗"]
    ):
        return "combat"
    if any(
        term in text
        for term in [
            # "racing" does not contain the substring "race", so both forms are
            # listed — the obvious spelling is also the easiest one to miss.
            "race",
            "racing",
            "racer",
            "time trial",
            "lap time",
            "speed",
            "chase",
            "竞速",
            "赛车",
            "追逐",
            "竞赛",
            "跑圈",
            "计时赛",
        ]
    ):
        return "mobility"
    return "systems"


def _verbs_for_axis(axis: str) -> list[str]:
    return list(AXIS_TEMPLATES[axis].verbs)


def _loop_for_axis(axis: str, verbs: list[str]) -> list[LoopStep]:
    """Build the core loop from the axis template.

    Steps may contain ``{verb_N}`` placeholders (the generic ``systems`` axis
    relies on them); specialised axes name their actions outright and simply
    have nothing to substitute.
    """
    fields = verb_fields(verbs, [VERB_ZH.get(verb, verb) for verb in verbs])
    return [
        LoopStep(
            order=index,
            action=step.action.format(**fields),
            player_decision=step.player_decision.format(**fields),
            feedback=step.feedback.format(**fields),
        )
        for index, step in enumerate(AXIS_TEMPLATES[axis].loop, start=1)
    ]


def _systems_for_axis(axis: str) -> list[SystemSpec]:
    return [
        SystemSpec(
            name=system.name,
            purpose=system.purpose,
            inputs=list(system.inputs),
            outputs=list(system.outputs),
            failure_pressure=system.failure_pressure,
        )
        for system in AXIS_TEMPLATES[axis].systems
    ]


def _progression_for_axis(axis: str) -> ProgressionSpec:
    progression = AXIS_TEMPLATES[axis].progression
    return ProgressionSpec(
        first_minute=progression.first_minute,
        midpoint_shift=progression.midpoint_shift,
        final_minutes=progression.final_minutes,
        unlocks=list(progression.unlocks),
    )


def _beat_durations(target_minutes: int) -> tuple[int, int, int]:
    # PromptRequest allows 5-15 minutes and spec validation requires the beat
    # durations to sum exactly to that target. Short sessions shrink the
    # teaching and final beats; targets >= 7 keep the classic 2/N/3 pacing.
    teaching = 2 if target_minutes >= 7 else 1
    final = 3 if target_minutes >= 7 else 2
    return teaching, target_minutes - teaching - final, final


def _fit_level_beats_to_target(beats: list[LevelBeat], target_minutes: int) -> list[LevelBeat]:
    """Rescale beat durations so they sum exactly to the target.

    Spec validation treats a duration-sum mismatch as an error; the
    deterministic generator guarantees the sum via _beat_durations, and this
    repairs LLM output, which has no arithmetic guarantee. Proportions are
    kept where possible and every duration stays inside the LevelBeat 1..15
    contract.
    """
    if not beats:
        return beats
    if len(beats) > target_minutes:
        # More beats than minutes cannot satisfy >=1 minute per beat.
        beats = beats[:target_minutes]
    durations = [beat.duration_minutes for beat in beats]
    total = sum(durations)
    if total == target_minutes:
        return beats
    scaled = [
        min(15, max(1, round(duration * target_minutes / total)))
        for duration in durations
    ]
    remainder = target_minutes - sum(scaled)
    order = sorted(range(len(scaled)), key=lambda i: durations[i], reverse=remainder > 0)
    while remainder != 0:
        moved = False
        for index in order:
            if remainder > 0 and scaled[index] < 15:
                scaled[index] += 1
                remainder -= 1
                moved = True
            elif remainder < 0 and scaled[index] > 1:
                scaled[index] -= 1
                remainder += 1
                moved = True
            if remainder == 0:
                break
        if not moved:
            break
    return [
        beat.model_copy(update={"duration_minutes": scaled[index]})
        for index, beat in enumerate(beats)
    ]


def _level_beats_for_axis(axis: str, target_minutes: int) -> list[LevelBeat]:
    """Build the beats from the axis template, sized to the target session.

    Every template carries exactly three beats (teaching / mix / finale) — a
    test asserts that, because this function maps them onto the three durations
    from :func:`_beat_durations` positionally.
    """
    teaching_minutes, mid_minutes, final_minutes = _beat_durations(target_minutes)
    durations = (teaching_minutes, mid_minutes, final_minutes)
    beats = AXIS_TEMPLATES[axis].beats
    return [
        LevelBeat(
            name=beat.name,
            duration_minutes=durations[index],
            gameplay_focus=beat.gameplay_focus,
            required_assets=list(beat.required_assets),
            success_condition=beat.success_condition,
        )
        for index, beat in enumerate(beats)
    ]


def _asset_needs_for_axis(axis: str) -> list[str]:
    return list(AXIS_TEMPLATES[axis].assets)


def _prompt_mentions_enemy(prompt: str) -> bool:
    text = prompt.lower()
    return any(
        term in text or term in prompt
        for term in [
            "enemy",
            "enemies",
            "monster",
            "guard",
            "drone",
            "turret",
            "pursuer",
            "chase",
            "hostile",
            "敌人",
            "怪物",
            "追兵",
            "哨兵",
        ]
    )


def _enemies_for_axis(axis: str, prompt: str = "") -> list[EnemySpec]:
    """Default enemy roster per mechanic axis, taken from the axis template.

    Empty where enemies do not fit. Axes with no roster still honour an
    explicit request for hostile pressure in the prompt.
    """
    roster = AXIS_TEMPLATES[axis].enemies
    if roster:
        return [
            EnemySpec(name=name, behavior=behavior, hp=hp, count=count)
            for name, behavior, hp, count in roster
        ]
    if _prompt_mentions_enemy(prompt):
        return [EnemySpec(name="Pressure Drone", behavior="chase", hp=2, count=1)]
    return []


def design_from_prompt_deterministic(request: PromptRequest) -> GameplaySpec:
    """Create a scoped first-pass gameplay design without pretending assets exist.

    Deterministic, keyword-driven baseline. Always succeeds and always returns a
    valid GameplaySpec, so it doubles as the fallback when the LLM backend is
    unavailable or produces unusable output.
    """

    axis = _detect_axis(request.prompt)
    title = _clean_title(request.prompt)
    verbs = _verbs_for_axis(axis)
    target_minutes = request.target_minutes
    template = AXIS_TEMPLATES[axis]
    narrative = template.narrative
    if axis == "career":
        # The logline is the one field that stays prompt-shaped rather than
        # axis-shaped: it has to name the applicant story, not the mechanic.
        logline = (
            f"A {target_minutes}-minute Godot-friendly portfolio prototype about turning personal "
            "fog, borrowed plans, and a game-design career pivot into a playable proof of fit."
        )
    else:
        logline = (
            f"A {target_minutes}-minute playable prototype about {request.prompt.strip()} "
            "built around readable decisions, fast feedback, and a finishable objective."
        )
    player_fantasy = narrative.player_fantasy
    design_pillars = list(narrative.design_pillars)
    win_state = narrative.win_state
    failure_states = list(narrative.failure_states)
    notes_for_comfyui = list(narrative.notes_for_comfyui)

    spec = GameplaySpec(
        title=title,
        logline=logline,
        target_session_minutes=target_minutes,
        player_fantasy=player_fantasy,
        design_pillars=design_pillars,
        core_verbs=verbs,
        core_loop=_loop_for_axis(axis, verbs),
        systems=_systems_for_axis(axis),
        progression=_progression_for_axis(axis),
        win_state=win_state,
        failure_states=failure_states,
        level_beats=_level_beats_for_axis(axis, target_minutes),
        asset_needs=_asset_needs_for_axis(axis),
        enemies=_enemies_for_axis(axis, request.prompt),
        qa_focus=[
            "Can a new player finish in one to three attempts?",
            "Does every failure state explain itself?",
            "Can the loop be replayed without restarting the editor?",
        ],
        notes_for_unreal=[
            "Use Blueprint-first implementation for the first slice.",
            "Keep mechanics in independent actors with explicit events.",
            "Expose tunables for pressure, cooldowns, and objective timing.",
        ],
        notes_for_blender=[
            "Generate scale-correct greybox meshes before styled assets.",
            "Prefer modular props with collision-friendly silhouettes.",
            "Name exports by gameplay role, not visual theme.",
        ],
        notes_for_comfyui=notes_for_comfyui,
    )
    spec.i18n = build_i18n_bundle(request, spec, axis, verbs)
    return spec


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _build_llm_system_prompt() -> str:
    schema_hint = json.dumps(
        {
            "title": "str",
            "logline": "str",
            "target_session_minutes": "int 5-15",
            "player_fantasy": "str",
            "design_pillars": ["str (3 to 5 items)"],
            "core_verbs": ["str (>=3 items)"],
            "core_loop": [
                {"order": "int", "action": "str", "player_decision": "str", "feedback": "str"}
            ],
            "systems": [
                {
                    "name": "str",
                    "purpose": "str",
                    "inputs": ["str"],
                    "outputs": ["str"],
                    "failure_pressure": "str",
                }
            ],
            "progression": {
                "first_minute": "str",
                "midpoint_shift": "str",
                "final_minutes": "str",
                "unlocks": ["str"],
            },
            "win_state": "str",
            "failure_states": ["str"],
            "level_beats": [
                {
                    "name": "str",
                    "duration_minutes": "int 1-15 (must sum to target_session_minutes)",
                    "gameplay_focus": "str",
                    "required_assets": ["str"],
                    "success_condition": "str",
                }
            ],
            "asset_needs": ["str"],
            "qa_focus": ["str"],
            "notes_for_unreal": ["str"],
            "notes_for_blender": ["str"],
            "notes_for_comfyui": ["str"],
            "enemies": [
                {
                    "name": "str",
                    "behavior": "patrol | chase | stationary | ranged",
                    "hp": "int >=1",
                    "count": "int 1-12",
                }
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
    return (
        "You are the Gameplay Agent for an AI game-production pipeline. Turn a raw "
        "game idea into a single playable vertical slice design.\n\n"
        "Hard rules:\n"
        "- Output ONLY a JSON object, no prose, no markdown fences.\n"
        "- core_loop, systems, and core_verbs must each have at least 3 entries.\n"
        "- design_pillars must have 3 to 5 entries.\n"
        "- Every mechanic must change a player decision and be testable in a greybox.\n"
        "- Enemy rosters should be empty when enemies do not serve the loop; when present, keep count small and behavior readable.\n"
        "- level_beats duration_minutes values MUST sum exactly to target_session_minutes.\n"
        "- Keep scope to one cohesive loop sized for the target session minutes.\n\n"
        "JSON shape (types are hints, not literals):\n"
        f"{schema_hint}"
    )


def _design_with_llm(request: PromptRequest) -> GameplaySpec:
    """Generate a GameplaySpec via the LLM backend. Raises on any failure."""

    from fantasy_agent import llm

    user_prompt = (
        f"Game idea:\n{request.prompt.strip()}\n\n"
        f"Target session length: {request.target_minutes} minutes.\n"
        f"Engine: {request.engine_version}. Platforms: {', '.join(request.platforms)}.\n"
    )
    if request.constraints:
        user_prompt += "Constraints:\n" + "\n".join(f"- {c}" for c in request.constraints) + "\n"
    user_prompt += "\nReturn the GameplaySpec JSON now."

    data = llm.complete_json(
        system=_build_llm_system_prompt(),
        user=user_prompt,
        temperature=0.7,
    )
    # Pydantic enforces the contract (extra="forbid", min_length, etc.).
    spec = GameplaySpec.model_validate(data)
    # LLMs miss exact-arithmetic constraints; production spec validation
    # requires the beat durations to sum to the session target, so repair
    # the durations before the spec feeds the bundle.
    spec.level_beats = _fit_level_beats_to_target(
        spec.level_beats, spec.target_session_minutes
    )

    # Attach i18n using deterministic axis/verb detection, matching the
    # deterministic path so downstream localization stays consistent.
    axis = _detect_axis(request.prompt)
    spec.i18n = build_i18n_bundle(request, spec, axis, _verbs_for_axis(axis))
    return spec


def design_from_prompt(request: PromptRequest, *, use_llm: bool | None = None) -> GameplaySpec:
    """Create a first-pass gameplay design, optionally using the LLM backend.

    Args:
        request: The prompt and scope constraints.
        use_llm: If True, try the LLM backend first. If None (default), read the
            ``FANTASY_AGENT_USE_LLM`` environment variable. If the LLM path fails
            for any reason (missing package or key, API error, invalid output),
            this falls back to the deterministic generator and never raises.

    Returns:
        A valid GameplaySpec, always.
    """

    if use_llm is None:
        use_llm = _env_flag("FANTASY_AGENT_USE_LLM")

    if use_llm:
        try:
            return _design_with_llm(request)
        except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully
            logger.warning("LLM gameplay design failed (%s); using deterministic fallback.", exc)

    return design_from_prompt_deterministic(request)
