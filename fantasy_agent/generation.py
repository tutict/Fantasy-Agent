from __future__ import annotations

import json
import logging
import os
import re

from fantasy_agent.contracts import (
    GameplaySpec,
    LevelBeat,
    LoopStep,
    ProgressionSpec,
    PromptRequest,
    SystemSpec,
)
from fantasy_agent.i18n import build_i18n_bundle, contains_cjk

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
        ]
    ):
        return "parkour"
    if any(term in text for term in ["stealth", "sneak", "shadow"]):
        return "stealth"
    if any(term in text for term in ["survival", "hunger", "storm", "oxygen"]):
        return "survival"
    if any(term in text for term in ["puzzle", "logic", "switch", "portal"]):
        return "puzzle"
    if any(term in text for term in ["combat", "fight", "boss", "weapon"]):
        return "combat"
    if any(term in text for term in ["race", "speed", "chase"]):
        return "mobility"
    return "systems"


def _verbs_for_axis(axis: str) -> list[str]:
    table = {
        "parkour": ["sprint", "vault", "wall-run", "slide"],
        "stealth": ["scout", "hide", "distract", "extract"],
        "survival": ["gather", "craft", "route", "endure"],
        "puzzle": ["observe", "combine", "trigger", "solve"],
        "combat": ["position", "attack", "evade", "recover"],
        "mobility": ["dash", "steer", "boost", "risk"],
        "career": ["discern", "choose", "compose", "support"],
        "systems": ["explore", "interact", "adapt", "complete"],
    }
    return table[axis]


def _loop_for_axis(axis: str, verbs: list[str]) -> list[LoopStep]:
    if axis == "parkour":
        return [
            LoopStep(
                order=1,
                action="Sprint toward the next checkpoint gate",
                player_decision="Choose the fast exposed lane or the safer recovery lane before momentum drops.",
                feedback="Speed lines, footstep cadence, and checkpoint color show whether momentum is active.",
            ),
            LoopStep(
                order=2,
                action="Vault low blockers to keep the chain alive",
                player_decision="Commit to a vault timing window or slow down and route around the obstacle.",
                feedback="A clean vault extends the combo meter; a late vault costs time but keeps the run recoverable.",
            ),
            LoopStep(
                order=3,
                action="Wall-run across marked panels under timer pressure",
                player_decision="Spend boost for a risky wall-run shortcut or stay on the longer rooftop path.",
                feedback="Wall panels glow while valid, and the pressure timer pulses when the shortcut is missed.",
            ),
            LoopStep(
                order=4,
                action="Slide under hazards and exit through the final gate",
                player_decision="Preserve enough momentum for the final slide or take a checkpoint reset.",
                feedback="The finish gate reports time, broken chain count, best route, and restart affordance.",
            ),
        ]
    if axis == "career":
        return [
            LoopStep(
                order=1,
                action="Discern evaluation noise inside a memory room",
                player_decision="Keep moving toward a clear self-owned goal or follow a loud external judgment marker.",
                feedback="Fog thins around self-owned choices and thickens around borrowed evaluation routes.",
            ),
            LoopStep(
                order=2,
                action="Choose between borrowed plans and a personal route",
                player_decision="Take a safe-looking plan card for short-term time relief or reject it to preserve agency.",
                feedback="Plan cards show immediate comfort but reduce the self-route meter when overused.",
            ),
            LoopStep(
                order=3,
                action="Compose experience fragments into a design board",
                player_decision="Place fragments as mechanics, constraints, or emotional beats before the interview timer ends.",
                feedback="The board converts lived moments into playable objectives, hazards, and support actions.",
            ),
            LoopStep(
                order=4,
                action="Support the team crisis and open the interview gate",
                player_decision="Spend limited focus to patch the weakest team need instead of chasing the flashiest role.",
                feedback="A final score reports clarity, fit, support timing, and which borrowed plans were rejected.",
            ),
        ]
    return [
        LoopStep(
            order=1,
            action=f"{verbs[0].title()} the immediate play space",
            player_decision="Choose a route, target, or interaction before pressure escalates.",
            feedback="Camera framing, UI markers, and audio cues confirm available options.",
        ),
        LoopStep(
            order=2,
            action=f"{verbs[1].title()} to create an opening",
            player_decision="Spend time or a limited resource to improve the next move.",
            feedback="State changes are visible in the level and reflected in the objective tracker.",
        ),
        LoopStep(
            order=3,
            action=f"{verbs[2].title()} under rising pressure",
            player_decision="Commit to the risky play or reset to a safer position.",
            feedback="Enemies, timers, hazards, or resource meters show the consequence quickly.",
        ),
        LoopStep(
            order=4,
            action=f"{verbs[3].title()} the objective and bank progress",
            player_decision="Exit with partial gains or push for a better completion grade.",
            feedback="End screen reports time, failures, optional goals, and restart affordance.",
        ),
    ]


def _systems_for_axis(axis: str) -> list[SystemSpec]:
    if axis == "parkour":
        return [
            SystemSpec(
                name="Momentum Chain",
                purpose="Rewards clean traversal while keeping failed routes recoverable.",
                inputs=["player velocity", "vault timing", "wall-run duration", "slide windows"],
                outputs=["combo multiplier", "boost charge", "speed feedback"],
                failure_pressure="Dropped momentum costs time and closes optional shortcuts.",
            ),
            SystemSpec(
                name="Checkpoint Route Timer",
                purpose="Keeps the rooftop loop short, readable, and replayable.",
                inputs=["checkpoint overlaps", "elapsed time", "missed gates"],
                outputs=["active gate", "route grade", "restart point"],
                failure_pressure="Missing too many gates forces a checkpoint reset instead of aimless wandering.",
            ),
            SystemSpec(
                name="Traversal Readability Layer",
                purpose="Makes usable ledges, walls, ramps, hazards, and exits legible at speed.",
                inputs=["surface tags", "player approach angle", "hazard proximity"],
                outputs=["affordance color", "valid-move prompts", "failure feedback"],
                failure_pressure="Unreadable surfaces slow the player and break the score chain.",
            ),
        ]
    if axis == "career":
        return [
            SystemSpec(
                name="Evaluation Fog",
                purpose="Turns other people's judgments into readable pressure without making the space aimless.",
                inputs=["player proximity", "borrowed plan count", "self-route meter"],
                outputs=["fog density", "objective clarity", "confidence feedback"],
                failure_pressure="Following too much evaluation noise hides the personal route and forces a restart.",
            ),
            SystemSpec(
                name="Plan Card Tradeoff",
                purpose="Makes external advice useful but risky, so choosing a path is an actual gameplay decision.",
                inputs=["plan card type", "interview timer", "player choice history"],
                outputs=["time relief", "agency cost", "route branch"],
                failure_pressure="Stacking mismatched plans drains agency and locks the applicant out of the final board.",
            ),
            SystemSpec(
                name="Design Board Translation",
                purpose="Converts personal experience fragments into mechanics, constraints, and team support actions.",
                inputs=["memory fragments", "board slots", "team crisis needs"],
                outputs=["prototype pitch score", "support action", "interview gate state"],
                failure_pressure="Fragments placed as decoration do not open the gate; they must change a playable decision.",
            ),
        ]
    return [
        SystemSpec(
            name="Objective State",
            purpose="Keeps the prototype finishable and prevents aimless play.",
            inputs=["player location", "interaction events", "objective triggers"],
            outputs=["active objective", "completion state", "restart state"],
            failure_pressure="The player loses if the primary objective becomes unreachable.",
        ),
        SystemSpec(
            name="Pressure Clock",
            purpose="Creates urgency inside a short vertical slice.",
            inputs=["elapsed time", "alert level", "mistake count"],
            outputs=["hazard intensity", "enemy aggression", "score modifier"],
            failure_pressure="Pressure reaches a cap and forces extraction, defeat, or reset.",
        ),
        SystemSpec(
            name="Readable Interaction Layer",
            purpose="Makes every useful object obvious enough for game-jam iteration.",
            inputs=["overlap events", "line traces", "player inventory"],
            outputs=["interaction prompts", "state changes", "audio/visual feedback"],
            failure_pressure="Bad reads cost time or resources rather than hiding progress.",
        ),
    ]


def _progression_for_axis(axis: str) -> ProgressionSpec:
    if axis == "parkour":
        return ProgressionSpec(
            first_minute="Teach sprint, vault, and checkpoint gates on a flat rooftop with no lethal failure.",
            midpoint_shift="Combine wall-run panels, slide barriers, and optional boost shortcuts.",
            final_minutes="Ask the player to chain sprint, vault, wall-run, slide, and extraction under one timer.",
            unlocks=[
                "Boost shortcut after the first clean checkpoint chain",
                "Wall-run route after the first vault section",
                "End-state route grade after reaching the extraction gate",
            ],
        )
    if axis == "career":
        return ProgressionSpec(
            first_minute="Teach movement, fog readability, and the first choice between a judgment marker and a self-route marker.",
            midpoint_shift="Introduce plan cards that reduce the timer but weaken agency if they do not fit the player's route.",
            final_minutes="Ask the player to assemble a design board from memory fragments and support a team crisis before the interview gate closes.",
            unlocks=[
                "Self-route meter after rejecting the first mismatched plan",
                "Design board after collecting three experience fragments",
                "Team support action after the board forms a coherent prototype pitch",
            ],
        )
    return ProgressionSpec(
        first_minute="Teach movement, camera, and the first objective without punishment.",
        midpoint_shift="Combine the main verb with pressure so the player must plan ahead.",
        final_minutes="Ask the player to execute the full loop with a clear win/fail result.",
        unlocks=[
            "Optional shortcut after first objective",
            "Second interaction type after midpoint",
            "End-state scoring after completion",
        ],
    )


def _level_beats_for_axis(axis: str, target_minutes: int) -> list[LevelBeat]:
    if axis == "parkour":
        return [
            LevelBeat(
                name="Warmup Rooftop",
                duration_minutes=2,
                gameplay_focus="Teach sprinting, vault timing, and checkpoint gate language.",
                required_assets=["start marker", "checkpoint gate", "low vault blockers"],
                success_condition="Player reaches the second gate without losing the route.",
            ),
            LevelBeat(
                name="Momentum Mix",
                duration_minutes=max(2, target_minutes - 5),
                gameplay_focus="Chain vaults, wall-runs, slides, and one boost shortcut.",
                required_assets=["wall-run panels", "slide barriers", "boost pad", "fall hazard markers"],
                success_condition="Player keeps enough momentum to open the final rooftop line.",
            ),
            LevelBeat(
                name="Extraction Sprint",
                duration_minutes=3,
                gameplay_focus="Run the full chain under pressure and choose speed versus recovery.",
                required_assets=["final gap ramp", "pressure timer UI", "extraction gate"],
                success_condition="Player exits before the timer expires and receives a route grade.",
            ),
        ]
    if axis == "career":
        return [
            LevelBeat(
                name="Fog of Evaluation",
                duration_minutes=2,
                gameplay_focus="Teach the player to read judgment noise, self-route markers, and recoverable wrong turns.",
                required_assets=["fog corridor", "judgment marker", "self-route marker", "confidence UI"],
                success_condition="Player reaches the first clear route marker without losing all confidence.",
            ),
            LevelBeat(
                name="Borrowed Plan Crossroads",
                duration_minutes=max(2, target_minutes - 5),
                gameplay_focus="Choose, reject, or revise plan cards while collecting experience fragments for the design board.",
                required_assets=["plan card kiosks", "memory fragment props", "design board", "timer UI"],
                success_condition="Player fills the board with fragments that change mechanics instead of decoration.",
            ),
            LevelBeat(
                name="Interview Gate Triage",
                duration_minutes=3,
                gameplay_focus="Use the completed design board to support the team need that matters most under time pressure.",
                required_assets=["team crisis stations", "support action prompt", "interview gate", "fit score UI"],
                success_condition="Player resolves one critical team need and opens the interview gate with a readable score.",
            ),
        ]
    return [
        LevelBeat(
            name="Onboarding Pocket",
            duration_minutes=2,
            gameplay_focus="Learn controls and identify the objective language.",
            required_assets=["start marker", "objective prop", "interaction prompt"],
            success_condition="Player completes the first low-risk interaction.",
        ),
        LevelBeat(
            name="System Mix",
            duration_minutes=max(2, target_minutes - 5),
            gameplay_focus="Use the core verbs while pressure changes the route.",
            required_assets=["arena blockers", "hazard markers", "feedback props"],
            success_condition="Player completes the central objective chain.",
        ),
        LevelBeat(
            name="Final Push",
            duration_minutes=3,
            gameplay_focus="Resolve the complete loop with win/fail stakes.",
            required_assets=["exit gate", "final hazard", "score trigger"],
            success_condition="Player reaches the exit and receives performance feedback.",
        ),
    ]


def _asset_needs_for_axis(axis: str) -> list[str]:
    if axis == "parkour":
        return [
            "Modular rooftop floor kit",
            "Low vault blocker set",
            "Wall-run panel set",
            "Slide barrier set",
            "Boost pad marker",
            "Checkpoint gate",
            "Fall hazard marker set",
            "Extraction gate",
            "Route timer UI proxy",
        ]
    if axis == "career":
        return [
            "Fog corridor greybox kit",
            "Judgment marker set",
            "Self-route marker set",
            "Borrowed plan card kiosk",
            "Memory fragment pickup set",
            "Design board UI proxy",
            "Team crisis station set",
            "Interview gate",
            "Fit score UI proxy",
        ]
    return [
        "Greybox arena kit",
        "Objective prop set",
        "Hazard marker set",
        "Readable exit gate",
        "Simple UI objective tracker",
    ]


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
    if axis == "career":
        logline = (
            f"A {target_minutes}-minute Godot-friendly portfolio prototype about turning personal "
            "fog, borrowed plans, and a game-design career pivot into a playable proof of fit."
        )
        player_fantasy = (
            "Prove value as a game design applicant by transforming personal experience into "
            "clear mechanics and supporting a team at the right moment."
        )
        design_pillars = [
            "Personal history becomes playable decisions",
            "Borrowed plans help only when they fit the player's route",
            "Failure clarifies the next self-owned choice",
            "Support actions matter more than flashy power",
        ]
        win_state = "Open the interview gate by building a coherent design board and resolving one critical team need."
        failure_states = [
            "Evaluation fog hides the self-route after too many mismatched plans",
            "Interview timer expires before the design board becomes actionable",
            "Team crisis is ignored in favor of decorative or unfocused choices",
        ]
        notes_for_comfyui = [
            "Generate original visual metaphors for fog, plan cards, design boards, and interview gates; do not copy named game IP.",
            "Prioritize icon-like readability for judgment noise, self-route markers, and support prompts.",
            "Use references as portfolio mood boards only after the greybox loop proves readable.",
        ]
    else:
        logline = (
            f"A {target_minutes}-minute playable prototype about {request.prompt.strip()} "
            "built around readable decisions, fast feedback, and a finishable objective."
        )
        player_fantasy = f"Master a compact {axis}-driven challenge through repeatable skill."
        design_pillars = [
            "One readable objective at all times",
            "Every mechanic changes a player decision",
            "Failure teaches the next attempt",
            "Assets exist to clarify play space",
        ]
        win_state = "Complete the primary objective and reach the exit before pressure caps out."
        failure_states = [
            "Pressure clock reaches maximum",
            "Player health or critical resource reaches zero",
            "Required objective actor is destroyed or abandoned",
        ]
        notes_for_comfyui = [
            "Generate visual references only after gameplay readability needs are known.",
            "Prioritize objective, hazard, route, material, and UI clarity over style exploration.",
            "Treat generated images as reviewed references, not direct proof of playable progress.",
        ]

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
                    "duration_minutes": "int",
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
