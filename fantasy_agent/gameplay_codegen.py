"""Generate real playable GDScript from a GameplaySpec (M6a/M6b).

Two paths:
- LLM (llm.complete_json): asks the model to implement the spec's core_verbs as
  a CharacterBody3D controller and the win/fail states as a game_manager with a
  Label-based HUD. Returns {filename: gdscript}.
- Deterministic fallback: axis-aware templates that are richer than the old
  WASD+jump greybox (e.g. parkour gets wall-run/slide/sprint) plus simple M6b
  enemies, so the demo is always playable even without an LLM.

The executor validates LLM output via a real Godot headless import and falls
back to the deterministic scripts if the import reports script errors.

M6b scope: declared enemies get simple greybox behavior and fail-state pressure.

Axis coverage
-------------

The deterministic path used to specialise only ``parkour``; every other axis
fell through to the same WASD+jump body, so a stealth design shipped a script
that could not crouch. :data:`_AXIS_MECHANICS` closes that: one record per
mechanic axis with the GDScript it owns.

Two invariants keep the table honest, both asserted in
``tests/test_gameplay_codegen.py``:

1. ``_AXIS_MECHANICS`` and ``axis_templates.AXIS_TEMPLATES`` have the same keys,
   so adding a design axis without mechanics fails the suite.
2. Every input action a mechanics block reads exists in the generated
   ``project.godot`` — actions come from ``spec.core_verbs`` via
   ``workflows.prepare_godot_project``, so a block that presses an action the
   project never declares would raise "Request for nonexistent InputMap action"
   the moment the prototype runs.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from fantasy_agent.axis_templates import AXIS_TEMPLATES
from fantasy_agent.contracts import GameplaySpec, ProductionSpecBundle
from fantasy_agent.godot_mcp import _godot_identifier

logger = logging.getLogger(__name__)

# Filenames the executor mounts; keep stable so the scene wiring matches.
PLAYER_SCRIPT = "scripts/player_controller.gd"
GAME_MANAGER_SCRIPT = "scripts/game_manager.gd"
ENEMY_SCRIPT = "scripts/enemy_controller.gd"

#: Actions every generated project declares regardless of axis
#: (see ``workflows.prepare_godot_project``).
BASE_INPUT_ACTIONS = (
    "move_forward",
    "move_back",
    "move_left",
    "move_right",
    "jump",
    "restart_run",
)


def action_name(verb: str) -> str:
    """InputMap action name for a core verb.

    Mirrors what ``workflows.prepare_godot_project`` registers so the generated
    GDScript only ever presses actions the project actually declares.
    """
    return _godot_identifier(verb.lower())


def generate_gameplay_scripts(
    spec: GameplaySpec,
    *,
    use_llm: bool | None = None,
    production_spec_bundle: ProductionSpecBundle | None = None,
) -> dict[str, str]:
    """Return {filename: gdscript} implementing the spec's mechanics + win/fail.

    Tries the LLM when use_llm is True (or the FANTASY_AGENT_USE_LLM env flag is
    set); on any failure returns the deterministic fallback. Always returns a
    usable dict — never raises.
    """
    import os

    if use_llm is None:
        use_llm = os.environ.get("FANTASY_AGENT_USE_LLM", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    if production_spec_bundle is not None:
        return deterministic_gameplay_scripts(
            spec, production_spec_bundle=production_spec_bundle
        )

    if use_llm:
        try:
            return _generate_with_llm(spec)
        except Exception as exc:  # noqa: BLE001 - degrade to deterministic
            logger.warning("LLM gameplay codegen failed (%s); using deterministic.", exc)

    return deterministic_gameplay_scripts(spec)


# ──────────────────────────────────────────────────────────────────────────
# Deterministic fallback
# ──────────────────────────────────────────────────────────────────────────

def _axis_from_verbs(spec: GameplaySpec) -> str:
    """Infer the mechanic family from core_verbs.

    Scores every axis in ``AXIS_TEMPLATES`` by how many of its verbs the spec
    declares, so a new axis is picked up without touching this function.
    """
    verbs = {v.strip().lower() for v in spec.core_verbs}
    best_axis = "generic"
    best_score = 0
    for axis, template in AXIS_TEMPLATES.items():
        score = len({v.lower() for v in template.verbs} & verbs)
        if score > best_score:
            best_axis = axis
            best_score = score
    return best_axis


def deterministic_gameplay_scripts(
    spec: GameplaySpec,
    *,
    production_spec_bundle: ProductionSpecBundle | None = None,
) -> dict[str, str]:
    """Axis-aware scripts, preferring compiled production-spec values."""
    axis = _axis_from_verbs(spec)
    move_speed = (
        production_spec_bundle.numeric.player_move_speed
        if production_spec_bundle is not None
        else 8.0
    )
    player_hp = (
        production_spec_bundle.numeric.player_hp
        if production_spec_bundle is not None
        else 5
    )
    return {
        PLAYER_SCRIPT: _player_controller(axis, move_speed=move_speed, player_hp=player_hp),
        GAME_MANAGER_SCRIPT: _game_manager(
            spec, axis=axis, production_spec_bundle=production_spec_bundle
        ),
        ENEMY_SCRIPT: _enemy_controller(axis),
    }


@dataclass(frozen=True)
class AxisMechanics:
    """The GDScript one mechanic axis contributes to the player controller.

    ``physics`` is spliced into ``_physics_process`` before the gravity/jump
    block, so it may rewrite ``velocity.x/z`` (parkour does) or add state.
    ``helpers`` is appended after it at column 0.

    ``enemy_contact`` is the failure text the enemy script reports, so a
    playtest can tell which axis just killed the player.

    Enemy *behaviors* are deliberately not here: they come from
    ``AxisTemplate.enemies``, which is the one place a design declares its
    roster. An axis that declares none gets a patrol-only guard so the script
    still compiles.
    """

    exports: str = ""
    state: str = ""
    physics: str = ""
    helpers: str = ""
    enemy_contact: str = "Enemy contact"


def _notify_helper(extra: str = "") -> str:
    """GDScript plumbing: call a method on the game_manager group."""
    return '''

func _notify_game_manager(method: String, arg: Variant = null) -> void:
    var manager := get_tree().get_first_node_in_group("game_manager")
    if manager == null or not manager.has_method(method):
        return
    if arg == null:
        manager.call(method)
    else:
        manager.call(method, arg)
''' + extra


_PARKOUR_PHYSICS = '''
    # [SPRINT] hold to accelerate
    var speed := move_speed
    if Input.is_action_pressed("sprint"):
        speed *= sprint_multiplier
    velocity.x = direction.x * speed
    velocity.z = direction.z * speed

    # [WALL_RUN] cling + glide along a wall while airborne and moving into it
    if not is_on_floor() and is_on_wall() and direction.length() > 0.1:
        velocity.y = maxf(velocity.y, -wall_run_fall)
        _wall_running = true
    else:
        _wall_running = false

    # [VAULT] hop a low blocker while keeping forward momentum
    if is_on_floor() and Input.is_action_just_pressed("vault"):
        velocity.y = vault_velocity
        _vaulting = true
    elif is_on_floor():
        _vaulting = false

    # [SLIDE] crouch-slide on the ground gives a forward burst.
    # Held over a few frames: an impulse that survives exactly one frame moves
    # the player 6/60 m, i.e. not at all as far as anyone playing can tell.
    if is_on_floor() and Input.is_action_just_pressed("slide"):
        _slide_time = slide_duration
    if _slide_time > 0.0:
        _slide_time = maxf(0.0, _slide_time - delta)
        velocity.x += direction.x * slide_boost
        velocity.z += direction.z * slide_boost
'''

_STEALTH_PHYSICS = '''
    # [HIDE] hold to move slowly and shrink the noise profile
    var speed := move_speed
    if Input.is_action_pressed("hide"):
        speed *= hide_speed_multiplier
        noise = maxf(0.0, noise - hide_quiet_rate * delta)
    else:
        noise = minf(1.0, noise + (noise_gain if direction.length() > 0.1 else 0.0) * delta)
    velocity.x = direction.x * speed
    velocity.z = direction.z * speed

    # [SCOUT] hold to mark nearby threats before committing to a lane
    _scouting = Input.is_action_pressed("scout")

    # [DISTRACT] throw a decoy that pulls attention off the runner
    if Input.is_action_just_pressed("distract") and decoys > 0:
        decoys -= 1
        _decoy_timer = decoy_duration
    if _decoy_timer > 0.0:
        _decoy_timer -= delta
        noise = maxf(0.0, noise - decoy_pull * delta)

    # [EXTRACT] the exit only opens while the runner is quiet
    if Input.is_action_just_pressed("extract"):
        if noise <= extract_noise_limit:
            _notify_game_manager("reach_exit")
        else:
            _notify_game_manager("fail_from_enemy", "Extraction was called while exposed")
'''

_COMBAT_PHYSICS = '''
    # [POSITION] hold to brace: slower movement, steadier footing
    var speed := move_speed
    if Input.is_action_pressed("position"):
        speed *= brace_speed_multiplier
        _bracing = true
    else:
        _bracing = false
    velocity.x = direction.x * speed
    velocity.z = direction.z * speed

    # [EVADE] a short burst dash on a cooldown.
    # The burst is held for a moment, not one frame: a single-frame addition is
    # 7/60 m, which reads as "evade does nothing".
    _evade_cooldown = maxf(0.0, _evade_cooldown - delta)
    if Input.is_action_just_pressed("evade") and _evade_cooldown <= 0.0:
        _evade_cooldown = evade_cooldown
        _evade_time = evade_duration
    if _evade_time > 0.0:
        _evade_time = maxf(0.0, _evade_time - delta)
        velocity.x += direction.x * evade_impulse
        velocity.z += direction.z * evade_impulse

    # [ATTACK] strike the closest enemy inside reach on a cooldown
    _attack_cooldown = maxf(0.0, _attack_cooldown - delta)
    if Input.is_action_just_pressed("attack") and _attack_cooldown <= 0.0:
        _attack_cooldown = attack_cooldown
        _strike_closest_enemy()

    # [RECOVER] stand still to regain stamina between exchanges
    if Input.is_action_pressed("recover") and direction.length() <= 0.1:
        _stamina = minf(1.0, _stamina + recover_rate * delta)
'''

_STRIKE_HELPER = '''

func _strike_closest_enemy() -> void:
    var closest: Node3D = null
    var closest_distance := attack_reach
    for node in get_tree().get_nodes_in_group("enemy"):
        if not node is Node3D:
            continue
        var distance := global_position.distance_to(node.global_position)
        if distance <= closest_distance:
            closest = node
            closest_distance = distance
    if closest != null and closest.has_method("take_damage"):
        closest.take_damage(attack_damage)
'''

_SURVIVAL_PHYSICS = '''
    # [ROUTE] hold to travel light: faster, but the drain bites harder
    var speed := move_speed
    if Input.is_action_pressed("route"):
        speed *= route_speed_multiplier
    velocity.x = direction.x * speed
    velocity.z = direction.z * speed

    # [GATHER] pull in supplies while standing still
    if Input.is_action_pressed("gather") and direction.length() <= 0.1:
        supplies = minf(max_supplies, supplies + gather_rate * delta)

    # [ENDURE] sheltering slows the drain but stops the repair
    var drain := supply_drain
    if Input.is_action_pressed("endure"):
        drain *= endure_drain_multiplier
    supplies = maxf(0.0, supplies - drain * delta)
    if supplies <= 0.0:
        _notify_game_manager("fail_from_enemy", "Supplies ran out before the route was secure")

    # [CRAFT] spend supplies to restore warmth
    if Input.is_action_just_pressed("craft") and supplies >= craft_cost:
        supplies -= craft_cost
        _warmth = minf(1.0, _warmth + craft_restore)
'''

_PUZZLE_PHYSICS = '''
    # [OBSERVE] hold to scan: a full sweep yields one fragment
    _scanning = Input.is_action_pressed("observe")
    if _scanning:
        _scan_progress += scan_rate * delta
        if _scan_progress >= 1.0:
            _scan_progress = 0.0
            _fragments += 1

    # [COMBINE] merge two fragments into one usable key
    if Input.is_action_just_pressed("combine") and _fragments >= 2:
        _fragments -= 2
        _keys += 1

    # [TRIGGER] fire the linked device in front of the player
    if Input.is_action_just_pressed("trigger"):
        _trigger_count += 1
        _notify_game_manager("register_trigger")

    # [SOLVE] submit the solution once enough keys are held
    if Input.is_action_just_pressed("solve"):
        if _keys >= required_keys:
            _notify_game_manager("reach_exit")
        else:
            _notify_game_manager("fail_from_enemy", "Solution submitted with too few keys")
'''

_MOBILITY_PHYSICS = '''
    # [STEER] rotate the facing with left/right input
    if absf(input_dir.x) > 0.1:
        rotate_y(-input_dir.x * steer_rate * delta)

    # [BOOST] hold to spend the boost meter for sustained speed
    var speed := move_speed
    if Input.is_action_pressed("boost") and _boost > 0.0:
        _boost = maxf(0.0, _boost - boost_drain * delta)
        speed *= boost_multiplier
    velocity.x = direction.x * speed
    velocity.z = direction.z * speed

    # [DASH] burst along the current facing.
    # Two things were wrong with it. It added to velocity *before* the pair of
    # assignments above, so the assignment erased the whole impulse on the same
    # frame -- measured, dashing covered the same 0.80m in 6 frames as not
    # dashing. And even in the right order a one-frame impulse is worth
    # 9/60 m, which no player can feel. It now runs after them and lasts a
    # moment.
    _dash_cooldown = maxf(0.0, _dash_cooldown - delta)
    if Input.is_action_just_pressed("dash") and _dash_cooldown <= 0.0:
        _dash_cooldown = dash_cooldown
        _dash_time = dash_duration
    if _dash_time > 0.0:
        _dash_time = maxf(0.0, _dash_time - delta)
        velocity += -transform.basis.z * dash_impulse

    # [RISK] hold to run hot: faster, but contact ends the run
    _risking = Input.is_action_pressed("risk")
    if _risking:
        velocity.x *= risk_multiplier
        velocity.z *= risk_multiplier
'''

_CAREER_PHYSICS = '''
    # [DISCERN] hold to study the options in front of the player
    if Input.is_action_pressed("discern"):
        _insight = minf(1.0, _insight + insight_rate * delta)

    # [CHOOSE] commit to the studied option
    if Input.is_action_just_pressed("choose") and _insight >= 0.5:
        _insight = 0.0
        _choices += 1
        _notify_game_manager("register_progress", 1)

    # [COMPOSE] turn two committed choices into one portfolio piece
    if Input.is_action_just_pressed("compose") and _choices >= 2:
        _choices -= 2
        _portfolio += 1

    # [SUPPORT] spend a portfolio piece to steady the run
    if Input.is_action_just_pressed("support") and _portfolio >= 1:
        _portfolio -= 1
        _confidence = minf(1.0, _confidence + support_gain)
'''

_SYSTEMS_PHYSICS = '''
    # [EXPLORE] walking a new area marks it as surveyed
    if direction.length() > 0.1:
        _surveyed = minf(1.0, _surveyed + survey_rate * delta)

    # [INTERACT] engage the nearest system node
    if Input.is_action_just_pressed("interact"):
        _interactions += 1
        _notify_game_manager("register_progress", 1)

    # [ADAPT] cycle the active response mode and retune the baseline speed
    if Input.is_action_just_pressed("adapt"):
        _mode = (_mode + 1) % 3
        move_speed = base_move_speed + float(_mode) * adapt_speed_step

    # [COMPLETE] close the loop once enough nodes are engaged
    if Input.is_action_just_pressed("complete"):
        if _interactions >= required_interactions:
            _notify_game_manager("reach_exit")
        else:
            _notify_game_manager("fail_from_enemy", "Loop closed before the systems were stable")
'''


_AXIS_MECHANICS: dict[str, AxisMechanics] = {
    "parkour": AxisMechanics(
        exports=(
            "@export var sprint_multiplier := 1.6   # [SPRINT_MULTIPLIER]\n"
            "@export var wall_run_fall := 1.5       # [WALL_RUN_FALL]\n"
            "@export var vault_velocity := 7.5      # [VAULT_VELOCITY]\n"
            "@export var slide_boost := 6.0         # [SLIDE_BOOST]\n"
            "@export var slide_duration := 0.22     # [SLIDE_DURATION]\n"
        ),
        state="var _wall_running := false\nvar _vaulting := false\nvar _slide_time := 0.0\n",
        physics=_PARKOUR_PHYSICS,
        enemy_contact="Pursuer drone clipped the runner",
    ),
    "stealth": AxisMechanics(
        exports=(
            "@export var hide_speed_multiplier := 0.45  # [HIDE_SPEED_MULTIPLIER]\n"
            "@export var hide_quiet_rate := 0.8         # [HIDE_QUIET_RATE]\n"
            "@export var noise_gain := 0.35             # [NOISE_GAIN]\n"
            "@export var decoys := 3                    # [DECOYS]\n"
            "@export var decoy_duration := 2.5          # [DECOY_DURATION]\n"
            "@export var decoy_pull := 0.9              # [DECOY_PULL]\n"
            "@export var extract_noise_limit := 0.35    # [EXTRACT_NOISE_LIMIT]\n"
        ),
        state="var noise := 0.0\nvar _scouting := false\nvar _decoy_timer := 0.0\n",
        physics=_STEALTH_PHYSICS,
        helpers=_notify_helper(),
        enemy_contact="A guard spotted the runner",
    ),
    "combat": AxisMechanics(
        exports=(
            "@export var attack_damage := 1          # [ATTACK_DAMAGE]\n"
            "@export var attack_reach := 2.4         # [ATTACK_REACH]\n"
            "@export var attack_cooldown := 0.55     # [ATTACK_COOLDOWN]\n"
            "@export var evade_impulse := 7.0        # [EVADE_IMPULSE]\n"
            "@export var evade_cooldown := 1.1       # [EVADE_COOLDOWN]\n"
            "@export var evade_duration := 0.18      # [EVADE_DURATION]\n"
            "@export var brace_speed_multiplier := 0.6  # [BRACE_SPEED_MULTIPLIER]\n"
            "@export var recover_rate := 0.5         # [RECOVER_RATE]\n"
        ),
        state=(
            "var _attack_cooldown := 0.0\n"
            "var _evade_cooldown := 0.0\n"
            "var _evade_time := 0.0\n"
            "var _bracing := false\n"
            "var _stamina := 1.0\n"
        ),
        physics=_COMBAT_PHYSICS,
        helpers=_notify_helper(_STRIKE_HELPER),
        enemy_contact="Combat contact cost the player footing",
    ),
    "survival": AxisMechanics(
        exports=(
            "@export var max_supplies := 10.0           # [MAX_SUPPLIES]\n"
            "@export var gather_rate := 2.5             # [GATHER_RATE]\n"
            "@export var supply_drain := 0.6            # [SUPPLY_DRAIN]\n"
            "@export var route_speed_multiplier := 1.35 # [ROUTE_SPEED_MULTIPLIER]\n"
            "@export var endure_drain_multiplier := 0.5 # [ENDURE_DRAIN_MULTIPLIER]\n"
            "@export var craft_cost := 3.0              # [CRAFT_COST]\n"
            "@export var craft_restore := 0.4           # [CRAFT_RESTORE]\n"
        ),
        state="var supplies := 6.0\nvar _warmth := 1.0\n",
        physics=_SURVIVAL_PHYSICS,
        helpers=_notify_helper(),
        enemy_contact="The stalker caught the player in the open",
    ),
    "puzzle": AxisMechanics(
        exports=(
            "@export var scan_rate := 0.7          # [SCAN_RATE]\n"
            "@export var required_keys := 2        # [REQUIRED_KEYS]\n"
        ),
        state=(
            "var _scanning := false\n"
            "var _scan_progress := 0.0\n"
            "var _fragments := 0\n"
            "var _keys := 0\n"
            "var _trigger_count := 0\n"
        ),
        physics=_PUZZLE_PHYSICS,
        helpers=_notify_helper(),
        enemy_contact="A patrol interrupted the solution",
    ),
    "mobility": AxisMechanics(
        exports=(
            "@export var steer_rate := 2.4       # [STEER_RATE]\n"
            "@export var dash_impulse := 9.0     # [DASH_IMPULSE]\n"
            "@export var dash_cooldown := 1.2    # [DASH_COOLDOWN]\n"
            "@export var dash_duration := 0.18   # [DASH_DURATION]\n"
            "@export var boost_multiplier := 1.5 # [BOOST_MULTIPLIER]\n"
            "@export var boost_drain := 0.4      # [BOOST_DRAIN]\n"
            "@export var risk_multiplier := 1.25 # [RISK_MULTIPLIER]\n"
        ),
        state=(
            "var _boost := 1.0\n"
            "var _dash_cooldown := 0.0\n"
            "var _dash_time := 0.0\n"
            "var _risking := false\n"
        ),
        physics=_MOBILITY_PHYSICS,
        enemy_contact="A barrier clipped the racer at speed",
    ),
    "career": AxisMechanics(
        exports=(
            "@export var insight_rate := 0.8   # [INSIGHT_RATE]\n"
            "@export var support_gain := 0.35  # [SUPPORT_GAIN]\n"
        ),
        state=(
            "var _insight := 0.0\n"
            "var _choices := 0\n"
            "var _portfolio := 0\n"
            "var _confidence := 0.5\n"
        ),
        physics=_CAREER_PHYSICS,
        helpers=_notify_helper(),
        enemy_contact="Borrowed plans collapsed under review",
    ),
    "systems": AxisMechanics(
        exports=(
            "@export var survey_rate := 0.25         # [SURVEY_RATE]\n"
            "@export var adapt_speed_step := 1.5     # [ADAPT_SPEED_STEP]\n"
            "@export var required_interactions := 3  # [REQUIRED_INTERACTIONS]\n"
        ),
        state=(
            "var _surveyed := 0.0\n"
            "var _interactions := 0\n"
            "var _mode := 0\n"
            "var base_move_speed := move_speed\n"
        ),
        physics=_SYSTEMS_PHYSICS,
        helpers=_notify_helper(),
        enemy_contact="A system hazard caught the player",
    ),
}


def _player_controller(axis: str, *, move_speed: float = 8.0, player_hp: int = 5) -> str:
    mechanics = _AXIS_MECHANICS.get(axis)
    exports = mechanics.exports if mechanics else ""
    state = mechanics.state if mechanics else ""
    physics = mechanics.physics if mechanics else ""
    helpers = mechanics.helpers if mechanics else ""
    return f'''extends CharacterBody3D

@export var move_speed := {move_speed}        # [MOVE_SPEED]
@export var max_hp := {player_hp}              # [PLAYER_HP]
@export var jump_velocity := 6.0     # [JUMP_VELOCITY]
@export var gravity := 18.0          # [GRAVITY]
{exports}{state}
func _physics_process(delta: float) -> void:
    var input_dir := Vector2.ZERO
    input_dir.x = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
    input_dir.y = Input.get_action_strength("move_back") - Input.get_action_strength("move_forward")
    var direction := Vector3(input_dir.x, 0.0, input_dir.y).normalized()
    velocity.x = direction.x * move_speed
    velocity.z = direction.z * move_speed
{physics}
    if not is_on_floor():
        velocity.y -= gravity * delta
    elif Input.is_action_just_pressed("jump"):
        velocity.y = jump_velocity
    move_and_slide()
{helpers}
'''


#: Words a spec's own failure text uses when it means "you left the route".
_BOUNDARY_WORDS = (
    "boundary",
    "leaves",
    "leave",
    "out of bounds",
    "off the route",
    "fell",
    "falls",
)


def _boundary_failure(fails: list[str], fallback: str) -> str:
    """The spec's own wording for losing the route, when it has one.

    Falling was the one failure the generated game manager could not report at
    all. The route is 3m wide, so stepping off the side is one keypress away --
    and the run then ended only when the pressure clock ran out, which is ten
    minutes of falling. Matching on the spec's words rather than indexing the
    list, because which position a failure state occupies is not fixed.

    ``fallback`` is not the pressure-clock text: a spec that never enumerated
    "left the route" would otherwise be quoted as having failed for the one
    reason it did not.
    """

    for text in fails:
        lowered = text.casefold()
        if any(word in lowered for word in _BOUNDARY_WORDS):
            return text.replace('"', "'")
    return fallback


def _game_manager(
    spec: GameplaySpec,
    *,
    axis: str = "generic",
    production_spec_bundle: ProductionSpecBundle | None = None,
) -> str:
    if production_spec_bundle is not None:
        narrative = production_spec_bundle.narrative
        win = (narrative.hud_text.get("objective") or narrative.objective_copy[-1]).replace('"', "'")
        fails = narrative.failure_feedback or ["Pressure reached maximum"]
        title = production_spec_bundle.gameplay_spec_title.replace('"', "'")
        pressure_limit = float(production_spec_bundle.numeric.pressure_clock_seconds)
    else:
        win = spec.win_state.replace('"', "'")
        fails = spec.failure_states or ["Pressure reached maximum"]
        title = spec.title.replace('"', "'")
        pressure_limit = float(spec.target_session_minutes * 60)
    fail0 = fails[0].replace('"', "'")
    boundary = _boundary_failure(fails, "Left the active route")
    return f'''extends Node

# Real win/fail判定 + HUD, derived from the GameplaySpec (M6a).
@export var pressure_limit := {pressure_limit}   # [PRESSURE_LIMIT] seconds before failure
@export var auto_return := 3.0       # [AUTO_RETURN] seconds on end screen
@export var fall_limit := -12.0      # [FALL_LIMIT] below this the route is lost

var _elapsed := 0.0
var _ended := false
var _progress := 0
var _hud: Label


func _ready() -> void:
    add_to_group("game_manager")
    _hud = Label.new()
    _hud.name = "FA_HUD"
    _hud.position = Vector2(24, 24)
    var layer := CanvasLayer.new()
    layer.name = "FA_HUDLayer"
    layer.add_child(_hud)
    add_child(layer)
    _update_hud("{title} — objective: {win}")


func _process(delta: float) -> void:
    if _ended:
        return
    _elapsed += delta
    var remaining := maxf(0.0, pressure_limit - _elapsed)
    _update_hud("Time left: %0.1fs  |  progress: %d" % [remaining, _progress])
    if remaining <= 0.0:
        _fail("{fail0}")
        return
    var player := _find_player()
    if player != null and player.global_position.y < fall_limit:
        _fail("{boundary}")


func _find_player() -> Node3D:
    # Looked up rather than bound at spawn: a project produced without gameplay
    # scripts has no player at all, and the manager still has to run.
    return get_tree().get_first_node_in_group("player") as Node3D


func reach_exit() -> void:
    # Called by the exit gate's body_entered signal when the player arrives.
    if _ended:
        return
    _win()


func fail_from_enemy(reason: String) -> void:
    if _ended:
        return
    _fail(reason)


func register_progress(amount: int) -> void:
    # Axis mechanics (career choices, system interactions) bank progress here.
    if _ended:
        return
    _progress += amount


func register_trigger() -> void:
    # Puzzle-style axes count device triggers as one step of progress.
    if _ended:
        return
    _progress += 1


func _win() -> void:
    _ended = true
    _update_hud("WIN — {win}")
    _schedule_return()


func _fail(reason: String) -> void:
    _ended = true
    _update_hud("FAIL — " + reason)
    _schedule_return()


func _schedule_return() -> void:
    var timer := get_tree().create_timer(auto_return)
    timer.timeout.connect(func() -> void: get_tree().reload_current_scene())


func _update_hud(text: String) -> void:
    if _hud:
        _hud.text = text
'''


def _enemy_controller(axis: str) -> str:
    """Enemy script scoped to the axis: only its declared behaviors, its own
    contact text, and a damage hook the combat axis can actually call."""
    mechanics = _AXIS_MECHANICS.get(axis)
    template = AXIS_TEMPLATES.get(axis)
    declared = [behavior for _name, behavior, _hp, _count in getattr(template, "enemies", [])]
    # One source of truth: the roster the design template declares. An axis
    # with no enemies still gets a patrol guard so the script stays valid.
    behaviors = list(dict.fromkeys(declared or ["patrol"]))
    if "patrol" not in behaviors:
        # patrol is also the ``match`` default branch, so its function has to
        # exist even on an axis that never declares a patrolling enemy.
        behaviors.append("patrol")
    default_behavior = behaviors[0]
    enemy_hp = template.enemies[0][2] if template and template.enemies else 3
    enemy_name = template.enemies[0][0] if template and template.enemies else "Patrol Guard"
    contact = (mechanics.enemy_contact if mechanics else "Enemy contact").replace('"', "'")
    branches = "\n".join(
        f'        "{behavior}":\n            _{behavior}(delta)' for behavior in behaviors
    )
    body_funcs = "\n".join(
        _ENEMY_BEHAVIOR_FUNCS[behavior](contact) for behavior in behaviors
    )
    return f'''extends Area3D

@export var behavior := "{default_behavior}"      # [ENEMY_BEHAVIOR]
@export var hp := {enemy_hp}                   # [ENEMY_HP]
@export var move_speed := 2.4         # [ENEMY_MOVE_SPEED]
@export var patrol_radius := 2.5      # [PATROL_RADIUS]
@export var detection_radius := 6.0   # [DETECTION_RADIUS]
@export var ranged_interval := 1.6    # [RANGED_INTERVAL]

var _origin := Vector3.ZERO
var _direction := 1.0
var _ranged_timer := 0.0
var _player: Node3D
var _game_manager: Node
var _label := "{enemy_name}"


func setup(enemy_name: String, enemy_behavior: String, enemy_hp: int, game_manager: Node) -> void:
    _label = enemy_name
    behavior = enemy_behavior
    hp = enemy_hp
    _game_manager = game_manager


func _ready() -> void:
    _origin = global_position
    monitoring = true
    add_to_group("enemy")
    body_entered.connect(_on_body_entered)


func take_damage(amount: int) -> void:
    # Called by the combat axis player controller when a strike lands.
    hp -= amount
    if hp <= 0:
        queue_free()


func _physics_process(delta: float) -> void:
    if _player == null:
        _player = get_tree().get_first_node_in_group("player")
    match behavior:
{branches}
        _:
            _patrol(delta)

{body_funcs}

func _fail_if_player_close(reason: String) -> void:
    if _player != null and global_position.distance_to(_player.global_position) <= 1.15:
        _notify_failure(reason)


func _on_body_entered(body: Node) -> void:
    if body.is_in_group("player") or body.name == "FA_Player":
        _notify_failure("{contact}")


func _notify_failure(reason: String) -> void:
    if _game_manager != null and _game_manager.has_method("fail_from_enemy"):
        _game_manager.fail_from_enemy(reason)
'''


def _patrol_func(contact: str) -> str:
    return f'''

func _patrol(delta: float) -> void:
    # Along ``z``: that is the axis the greybox route runs on, so a patrol stays
    # on the walkway. Walking ``x`` sent it across the 3m width and off the edge
    # after the first leg -- a guard floating beside the route it is meant to
    # guard.
    position.z += _direction * move_speed * delta
    if abs(position.z - _origin.z) >= patrol_radius:
        _direction *= -1.0
    _fail_if_player_close("{contact}")
'''


def _chase_func(contact: str) -> str:
    return f'''

func _chase(delta: float) -> void:
    if _player == null:
        return
    var offset := _player.global_position - global_position
    if offset.length() <= detection_radius:
        global_position += offset.normalized() * move_speed * delta
    _fail_if_player_close("{contact}")
'''


def _stationary_func(contact: str) -> str:
    return f'''

func _stationary(_delta: float) -> void:
    _fail_if_player_close("{contact}")
'''


def _ranged_func(contact: str) -> str:
    return f'''

func _ranged(delta: float) -> void:
    if _player == null:
        return
    var distance := global_position.distance_to(_player.global_position)
    if distance > detection_radius:
        return
    _ranged_timer += delta
    if _ranged_timer >= ranged_interval:
        _ranged_timer = 0.0
        _notify_failure("{contact}")
'''


_ENEMY_BEHAVIOR_FUNCS: dict[str, object] = {
    "patrol": _patrol_func,
    "chase": _chase_func,
    "stationary": _stationary_func,
    "ranged": _ranged_func,
}


def declared_input_actions(spec: GameplaySpec) -> set[str]:
    """The InputMap actions the generated project will register for this spec."""
    actions = {action_name(a) for a in BASE_INPUT_ACTIONS}
    actions |= {action_name(verb) for verb in spec.core_verbs[:4]}
    return actions


def referenced_input_actions(script: str) -> set[str]:
    """Every InputMap action a GDScript reads — used by the contract tests."""
    return set(re.findall(r'Input\.is_action_(?:pressed|just_pressed)\("([^"]+)"\)', script))


# ──────────────────────────────────────────────────────────────────────────
# LLM path
# ──────────────────────────────────────────────────────────────────────────

def _build_codegen_system_prompt() -> str:
    return (
        "You generate Godot 4 GDScript for a playable 3D greybox prototype.\n\n"
        "Output ONLY a JSON object mapping filename to GDScript source:\n"
        '{ "scripts/player_controller.gd": "...", "scripts/game_manager.gd": "...", '
        '"scripts/enemy_controller.gd": "..." }\n\n'
        "Hard rules:\n"
        "- player_controller.gd: extends CharacterBody3D, implement EVERY core_verb "
        "as real movement (e.g. sprint/vault/wall-run/slide), using move_and_slide().\n"
        "- game_manager.gd: extends Node, implement the win_state and failure_states "
        "as real logic with a CanvasLayer+Label HUD; expose reach_exit() for the exit "
        "gate to call; expose fail_from_enemy(reason) for enemy_controller.gd; reload "
        "the scene a few seconds after win/fail.\n"
        "- enemy_controller.gd: extends Area3D; implement only the declared enemies "
        "with simple patrol/chase/stationary/ranged behavior and call "
        "game_manager.fail_from_enemy(reason) on contact or ranged pressure.\n"
        "- Valid Godot 4 GDScript only (4-space indent, typed where natural). No @tool. "
        "No external resources. Tunables get a # [NAME] anchor comment.\n"
        "- Output strictly the JSON object, no prose, no markdown fences."
    )


def _generate_with_llm(spec: GameplaySpec) -> dict[str, str]:
    from fantasy_agent import llm

    payload = {
        "title": spec.title,
        "core_verbs": spec.core_verbs,
        "core_loop": [s.model_dump() for s in spec.core_loop],
        "systems": [s.model_dump() for s in spec.systems],
        "win_state": spec.win_state,
        "failure_states": spec.failure_states,
        "enemies": [e.model_dump() for e in spec.enemies],
    }
    user = (
        "Implement playable GDScript for this gameplay spec.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\nReturn the JSON {filename: gdscript} now."
    )
    data = llm.complete_json(system=_build_codegen_system_prompt(), user=user, max_tokens=6000)

    scripts: dict[str, str] = {}
    for name in (PLAYER_SCRIPT, GAME_MANAGER_SCRIPT, ENEMY_SCRIPT):
        value = data.get(name)
        if not isinstance(value, str) or "extends" not in value:
            raise ValueError(f"LLM output missing valid GDScript for {name}")
        scripts[name] = value.strip()
    return scripts
