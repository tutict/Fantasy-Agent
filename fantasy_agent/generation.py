from __future__ import annotations

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


def _clean_title(prompt: str) -> str:
    if contains_cjk(prompt):
        compact = re.sub(r"\s+", "", prompt.strip())
        return compact[:18] or "Untitled Prototype"
    words = re.findall(r"[A-Za-z0-9]+", prompt)
    if not words:
        return "Untitled Prototype"
    meaningful = [word for word in words if len(word) > 2][:5]
    return " ".join(meaningful).title() or "Untitled Prototype"


def _detect_axis(prompt: str) -> str:
    text = prompt.lower()
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
    return [
        "Greybox arena kit",
        "Objective prop set",
        "Hazard marker set",
        "Readable exit gate",
        "Simple UI objective tracker",
    ]


def design_from_prompt(request: PromptRequest) -> GameplaySpec:
    """Create a scoped first-pass gameplay design without pretending assets exist."""

    axis = _detect_axis(request.prompt)
    title = _clean_title(request.prompt)
    verbs = _verbs_for_axis(axis)
    target_minutes = request.target_minutes

    spec = GameplaySpec(
        title=title,
        logline=(
            f"A {target_minutes}-minute playable prototype about {request.prompt.strip()} "
            "built around readable decisions, fast feedback, and a finishable objective."
        ),
        target_session_minutes=target_minutes,
        player_fantasy=f"Master a compact {axis}-driven challenge through repeatable skill.",
        design_pillars=[
            "One readable objective at all times",
            "Every mechanic changes a player decision",
            "Failure teaches the next attempt",
            "Assets exist to clarify play space",
        ],
        core_verbs=verbs,
        core_loop=_loop_for_axis(axis, verbs),
        systems=_systems_for_axis(axis),
        progression=_progression_for_axis(axis),
        win_state="Complete the primary objective and reach the exit before pressure caps out.",
        failure_states=[
            "Pressure clock reaches maximum",
            "Player health or critical resource reaches zero",
            "Required objective actor is destroyed or abandoned",
        ],
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
        notes_for_comfyui=[
            "Generate visual references only after gameplay readability needs are known.",
            "Prioritize objective, hazard, route, material, and UI clarity over style exploration.",
            "Treat generated images as reviewed references, not direct proof of playable progress.",
        ],
    )
    spec.i18n = build_i18n_bundle(request, spec, axis, verbs)
    return spec
