from __future__ import annotations

import re

from fantasy_agent.contracts import IdeaDiscoveryRequest, IdeaSeed, PromptRequest


ANSWER_ALIASES: dict[str, tuple[str, ...]] = {
    "player_fantasy": ("player_fantasy", "fantasy", "role"),
    "emotional_target": ("emotional_target", "mood", "feeling", "emotion"),
    "core_action": ("core_action", "first_action", "verb", "action"),
    "tension_source": ("tension_source", "pressure", "risk", "failure_lesson"),
    "must_keep": ("must_keep", "keep", "non_negotiable"),
    "can_cut": ("can_cut", "cut", "scope"),
    "reference_feel": ("reference_feel", "reference", "feel"),
    "playable_loop_candidate": ("playable_loop", "loop", "best_moment"),
}

KNOWN_ACTIONS = {
    "parkour": "chain wall-runs, vaults, slides, boosts, and checkpoints through a compact route",
    "wall-run": "chain wall-runs, vaults, slides, boosts, and checkpoints through a compact route",
    "stealth": "read patrol pressure, move quietly, use cover, and escape with a clear objective",
    "puzzle": "observe a spatial rule, manipulate the level state, and confirm the result",
    "combat": "read enemy intent, choose a verb, and recover position after each exchange",
    "racing": "choose a route, manage speed, and recover from mistakes without losing flow",
}


def _answer_lookup(request: IdeaDiscoveryRequest, key: str) -> str:
    aliases = ANSWER_ALIASES[key]
    for answer in request.answers:
        normalized = answer.question_id.strip().lower().replace("-", "_")
        if normalized in aliases:
            return answer.answer.strip()
    return ""


def _split_items(value: str) -> list[str]:
    items = [
        item.strip(" -;\t")
        for item in re.split(r"[\n,，;；]+", value)
        if item.strip(" -;\t")
    ]
    return items[:6]


def _infer_core_action(raw_idea: str) -> str:
    lowered = raw_idea.lower()
    for keyword, action in KNOWN_ACTIONS.items():
        if keyword in lowered:
            return action
    return "perform one readable core action, receive feedback, and decide whether to push forward or retry"


def _infer_must_keep(raw_idea: str) -> list[str]:
    candidates = []
    lowered = raw_idea.lower()
    for keyword in ["wall-run", "vault", "slide", "boost", "checkpoint", "stealth", "combat", "puzzle"]:
        if keyword in lowered:
            candidates.append(keyword)
    if candidates:
        return [f"{item} must affect a player decision" for item in candidates[:5]]
    return ["the clearest player fantasy from the raw idea"]


def _open_questions(seed: dict[str, object]) -> list[str]:
    questions: list[str] = []
    if "raw idea" in str(seed["player_fantasy"]).lower():
        questions.append("What role should the player feel they are performing moment to moment?")
    if "readable" in str(seed["core_action"]).lower():
        questions.append("What is the first concrete action the player should perform in the first 30 seconds?")
    if len(seed["must_keep"]) <= 1:
        questions.append("Which single mechanic is non-negotiable for the prototype?")
    if not seed["can_cut"]:
        questions.append("Which features should be cut if the prototype needs to stay game jam scale?")
    return questions[:4]


def extract_idea_seed(request: IdeaDiscoveryRequest) -> IdeaSeed:
    raw_idea = request.raw_idea.strip()
    player_fantasy = _answer_lookup(request, "player_fantasy") or f"Player fantasy implied by: {raw_idea}"
    emotional_target = _answer_lookup(request, "emotional_target") or "focused, readable mastery under pressure"
    core_action = _answer_lookup(request, "core_action") or _infer_core_action(raw_idea)
    tension_source = _answer_lookup(request, "tension_source") or "route pressure, visible hazards, and recoverable mistakes"
    must_keep = _split_items(_answer_lookup(request, "must_keep")) or _infer_must_keep(raw_idea)
    can_cut = _split_items(_answer_lookup(request, "can_cut")) or [
        "secondary modes that do not change the core decision loop",
        "large decorative spaces without gameplay pressure",
    ]
    reference_feel = (
        _answer_lookup(request, "reference_feel")
        or "compact game jam prototype with strong objective readability"
    )
    playable_loop = _answer_lookup(request, "playable_loop_candidate") or (
        f"{core_action}; face {tension_source}; get immediate feedback; improve the next attempt."
    )
    constraints = [*request.constraints]
    if request.target_minutes:
        constraints.append(f"{request.target_minutes}-minute vertical slice")
    constraints.append("gameplay-first scope")

    seed_data: dict[str, object] = {
        "raw_idea": raw_idea,
        "player_fantasy": player_fantasy,
        "emotional_target": emotional_target,
        "core_action": core_action,
        "tension_source": tension_source,
        "must_keep": must_keep,
        "can_cut": can_cut,
        "reference_feel": reference_feel,
        "playable_loop_candidate": playable_loop,
        "constraints": constraints,
    }
    open_questions = _open_questions(seed_data)
    next_prompt = (
        f"Create a {request.target_minutes}-minute {request.engine_version} playable prototype from this idea seed. "
        f"Player fantasy: {player_fantasy}. Emotional target: {emotional_target}. "
        f"Core action: {core_action}. Tension source: {tension_source}. "
        f"Playable loop: {playable_loop}. Must keep: {', '.join(must_keep)}. "
        f"Can cut: {', '.join(can_cut)}. Reference feel: {reference_feel}. "
        "Prioritize a coherent greybox loop over visual polish."
    )
    return IdeaSeed(
        raw_idea=raw_idea,
        player_fantasy=player_fantasy,
        emotional_target=emotional_target,
        core_action=core_action,
        tension_source=tension_source,
        must_keep=must_keep,
        can_cut=can_cut,
        reference_feel=reference_feel,
        playable_loop_candidate=playable_loop,
        constraints=constraints,
        open_questions=open_questions,
        next_prompt=next_prompt,
    )


def prompt_request_from_seed(seed: IdeaSeed, request: IdeaDiscoveryRequest) -> PromptRequest:
    return PromptRequest(
        prompt=seed.next_prompt,
        target_minutes=request.target_minutes,
        engine_version=request.engine_version,
        platforms=request.platforms,
        jam_scope=True,
        constraints=seed.constraints,
        source_locale=request.source_locale,
        output_locales=request.output_locales,
    )
