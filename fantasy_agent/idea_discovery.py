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

PORTFOLIO_STORY_TERMS = (
    "应聘",
    "求职",
    "经历",
    "休学",
    "他人评价",
    "自己的道路",
    "自废武功",
    "学历",
    "就业",
    "游戏策划",
    "转职",
    "作品集",
    "portfolio",
    "career",
    "interview",
    "resume",
)


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
    if _looks_like_portfolio_story(raw_idea):
        return (
            "navigate memory rooms, reject unsuitable external plans, translate lived experience "
            "into design choices, and support the team at a critical moment"
        )
    for keyword, action in KNOWN_ACTIONS.items():
        if keyword in lowered:
            return action
    return "perform one readable core action, receive feedback, and decide whether to push forward or retry"


def _infer_must_keep(raw_idea: str) -> list[str]:
    if _looks_like_portfolio_story(raw_idea):
        return [
            "walking out of other people's evaluation fog must be playable",
            "route choices must show the risk of self-negating progress",
            "the code-editor-to-planning transition must become a concrete interaction",
            "the player should prove value by supporting a team during a crisis",
        ]
    candidates = []
    lowered = raw_idea.lower()
    for keyword in ["wall-run", "vault", "slide", "boost", "checkpoint", "stealth", "combat", "puzzle"]:
        if keyword in lowered:
            candidates.append(keyword)
    if candidates:
        return [f"{item} must affect a player decision" for item in candidates[:5]]
    return ["the clearest player fantasy from the raw idea"]


def _looks_like_portfolio_story(raw_idea: str) -> bool:
    lowered = raw_idea.lower()
    return any(term in raw_idea or term in lowered for term in PORTFOLIO_STORY_TERMS)


def _portfolio_story_seed(request: IdeaDiscoveryRequest, raw_idea: str) -> dict[str, object]:
    if request.source_locale == "zh-CN":
        return {
            "player_fantasy": (
                "玩家扮演一个准备应聘游戏策划的人，把迷雾、他人评价、外部 plan "
                "和转职焦虑转化成一段能证明自己价值的可玩作品。"
            ),
            "emotional_target": "从被评价困住，到主动选择自己的道路，并在团队关键时刻发挥价值。",
            "core_action": (
                "在记忆房间中辨认评价噪音，选择自己的路线，把经历碎片转译成策划方案，"
                "并在团队危机中补位。"
            ),
            "tension_source": (
                "他人的 plan 会提供短期安全感但削弱自我路线；面试倒计时要求玩家取舍、表达和交付。"
            ),
            "must_keep": [
                "走出他人评价的迷雾必须成为可操作目标",
                "路线选择要表现“照别人的路走可能自废武功”的风险",
                "从代码编辑器到 WPS/策划案的转职必须是核心互动",
                "玩家最终要像团队里的战地庸医一样在危机中发挥价值",
            ],
            "can_cut": [
                "直接复刻被引用游戏的角色、场景和剧情",
                "大型 RPG 成长系统",
                "复杂战斗数值",
                "高成本美术演出",
            ],
            "reference_feel": "适合应聘展示的 10 分钟 Godot 互动寓言，重点是清晰表达、可玩取舍和作品集叙事。",
            "playable_loop_candidate": (
                "进入一间记忆房间，收集经历碎片；判断并改写外部 plan；"
                "把碎片放入策划板形成可执行方案；在最终团队危机中选择补位动作并打开应聘大门。"
            ),
        }
    return {
        "player_fantasy": (
            "Play as a game design applicant turning personal fog, external judgment, borrowed "
            "plans, and a career pivot into a playable proof of value."
        ),
        "emotional_target": "Move from being trapped by evaluation to choosing a path and helping a team when it matters.",
        "core_action": (
            "navigate memory rooms, reject unsuitable external plans, translate lived experience "
            "into design choices, and support the team at a critical moment"
        ),
        "tension_source": (
            "borrowed plans offer short-term safety but weaken the player's own route while an interview timer demands delivery"
        ),
        "must_keep": _infer_must_keep(raw_idea),
        "can_cut": [
            "direct copies of referenced game characters, scenes, or stories",
            "large RPG progression",
            "complex combat math",
            "high-cost art set pieces",
        ],
        "reference_feel": "a 10-minute Godot portfolio fable focused on readable choices and a finishable proof-of-fit loop",
        "playable_loop_candidate": (
            "enter a memory room, collect experience fragments, revise an external plan, place fragments "
            "onto a design board, then support a team crisis to open the interview gate"
        ),
    }


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
    portfolio_defaults = _portfolio_story_seed(request, raw_idea) if _looks_like_portfolio_story(raw_idea) else {}
    player_fantasy = (
        _answer_lookup(request, "player_fantasy")
        or str(portfolio_defaults.get("player_fantasy") or f"Player fantasy implied by: {raw_idea}")
    )
    emotional_target = (
        _answer_lookup(request, "emotional_target")
        or str(portfolio_defaults.get("emotional_target") or "focused, readable mastery under pressure")
    )
    core_action = (
        _answer_lookup(request, "core_action")
        or str(portfolio_defaults.get("core_action") or _infer_core_action(raw_idea))
    )
    tension_source = (
        _answer_lookup(request, "tension_source")
        or str(portfolio_defaults.get("tension_source") or "route pressure, visible hazards, and recoverable mistakes")
    )
    must_keep = (
        _split_items(_answer_lookup(request, "must_keep"))
        or list(portfolio_defaults.get("must_keep") or [])
        or _infer_must_keep(raw_idea)
    )
    can_cut = (
        _split_items(_answer_lookup(request, "can_cut"))
        or list(portfolio_defaults.get("can_cut") or [])
        or [
            "secondary modes that do not change the core decision loop",
            "large decorative spaces without gameplay pressure",
        ]
    )
    reference_feel = (
        _answer_lookup(request, "reference_feel")
        or str(
            portfolio_defaults.get("reference_feel")
            or "compact game jam prototype with strong objective readability"
        )
    )
    playable_loop = (
        _answer_lookup(request, "playable_loop_candidate")
        or str(
            portfolio_defaults.get("playable_loop_candidate")
            or f"{core_action}; face {tension_source}; get immediate feedback; improve the next attempt."
        )
    )
    constraints = [*request.constraints]
    if request.target_minutes:
        constraints.append(f"{request.target_minutes}-minute vertical slice")
    constraints.append("gameplay-first scope")
    if portfolio_defaults:
        constraints.append("portfolio-friendly personal story")
        constraints.append("do not copy named game IP; translate references into original playable metaphors")

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
