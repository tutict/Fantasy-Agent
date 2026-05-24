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
        "stealth": ["scout", "hide", "distract", "extract"],
        "survival": ["gather", "craft", "route", "endure"],
        "puzzle": ["observe", "combine", "trigger", "solve"],
        "combat": ["position", "attack", "evade", "recover"],
        "mobility": ["dash", "steer", "boost", "risk"],
        "systems": ["explore", "interact", "adapt", "complete"],
    }
    return table[axis]


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
        core_loop=[
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
        ],
        systems=[
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
        ],
        progression=ProgressionSpec(
            first_minute="Teach movement, camera, and the first objective without punishment.",
            midpoint_shift="Combine the main verb with pressure so the player must plan ahead.",
            final_minutes="Ask the player to execute the full loop with a clear win/fail result.",
            unlocks=[
                "Optional shortcut after first objective",
                "Second interaction type after midpoint",
                "End-state scoring after completion",
            ],
        ),
        win_state="Complete the primary objective and reach the exit before pressure caps out.",
        failure_states=[
            "Pressure clock reaches maximum",
            "Player health or critical resource reaches zero",
            "Required objective actor is destroyed or abandoned",
        ],
        level_beats=[
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
        ],
        asset_needs=[
            "Greybox arena kit",
            "Objective prop set",
            "Hazard marker set",
            "Readable exit gate",
            "Simple UI objective tracker",
        ],
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
    )
    spec.i18n = build_i18n_bundle(request, spec, axis, verbs)
    return spec
