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
"""

from __future__ import annotations

import json
import logging

from fantasy_agent.contracts import GameplaySpec

logger = logging.getLogger(__name__)

# Filenames the executor mounts; keep stable so the scene wiring matches.
PLAYER_SCRIPT = "scripts/player_controller.gd"
GAME_MANAGER_SCRIPT = "scripts/game_manager.gd"
ENEMY_SCRIPT = "scripts/enemy_controller.gd"


def generate_gameplay_scripts(
    spec: GameplaySpec, *, use_llm: bool | None = None
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
    """Infer the mechanic family from core_verbs (matches generation.py axes)."""
    verbs = {v.lower() for v in spec.core_verbs}
    if {"wall-run", "vault", "slide", "sprint"} & verbs:
        return "parkour"
    if {"scout", "hide", "distract", "extract"} & verbs:
        return "stealth"
    if {"dash", "steer", "boost"} & verbs:
        return "mobility"
    return "generic"


def deterministic_gameplay_scripts(spec: GameplaySpec) -> dict[str, str]:
    """Axis-aware player controller + game manager. Always valid GDScript."""
    axis = _axis_from_verbs(spec)
    return {
        PLAYER_SCRIPT: _player_controller(axis),
        GAME_MANAGER_SCRIPT: _game_manager(spec),
        ENEMY_SCRIPT: _enemy_controller(),
    }


def _player_controller(axis: str) -> str:
    # Parkour adds sprint + wall-run + slide on top of the base WASD+jump.
    parkour_extras = ""
    if axis == "parkour":
        parkour_extras = """
    # [SPRINT] hold to accelerate
    var speed := move_speed
    if Input.is_action_pressed("sprint"):
        speed *= sprint_multiplier
    velocity.x = direction.x * speed
    velocity.z = direction.z * speed

    # [WALL_RUN] cling + glide along a wall while airborne and moving into it
    if not is_on_floor() and is_on_wall() and direction.length() > 0.1:
        velocity.y = max(velocity.y, -wall_run_fall)
        _wall_running = true
    else:
        _wall_running = false

    # [SLIDE] crouch-slide on the ground gives a forward burst
    if is_on_floor() and Input.is_action_just_pressed("slide"):
        velocity.x += direction.x * slide_boost
        velocity.z += direction.z * slide_boost
"""
    extra_exports = ""
    extra_state = ""
    if axis == "parkour":
        extra_exports = (
            "@export var sprint_multiplier := 1.6  # [SPRINT_MULTIPLIER]\n"
            "@export var wall_run_fall := 1.5      # [WALL_RUN_FALL]\n"
            "@export var slide_boost := 6.0        # [SLIDE_BOOST]\n"
        )
        extra_state = "var _wall_running := false\n"
    return f'''extends CharacterBody3D

@export var move_speed := 8.0        # [MOVE_SPEED]
@export var jump_velocity := 6.0     # [JUMP_VELOCITY]
@export var gravity := 18.0          # [GRAVITY]
{extra_exports}{extra_state}

func _physics_process(delta: float) -> void:
    var input_dir := Vector2.ZERO
    input_dir.x = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
    input_dir.y = Input.get_action_strength("move_back") - Input.get_action_strength("move_forward")
    var direction := Vector3(input_dir.x, 0.0, input_dir.y).normalized()
    velocity.x = direction.x * move_speed
    velocity.z = direction.z * move_speed
{parkour_extras}
    if not is_on_floor():
        velocity.y -= gravity * delta
    elif Input.is_action_just_pressed("jump"):
        velocity.y = jump_velocity
    move_and_slide()
'''


def _game_manager(spec: GameplaySpec) -> str:
    win = spec.win_state.replace('"', "'")
    fails = spec.failure_states or ["Pressure reached maximum"]
    fail0 = fails[0].replace('"', "'")
    title = spec.title.replace('"', "'")
    return f'''extends Node

# Real win/fail判定 + HUD, derived from the GameplaySpec (M6a).
@export var pressure_limit := 60.0   # [PRESSURE_LIMIT] seconds before failure
@export var auto_return := 3.0       # [AUTO_RETURN] seconds on end screen

var _elapsed := 0.0
var _ended := false
var _hud: Label


func _ready() -> void:
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
    _update_hud("Time left: %0.1fs" % remaining)
    if remaining <= 0.0:
        _fail("{fail0}")


func reach_exit() -> void:
    # Called by the exit gate's body_entered signal when the player arrives.
    if _ended:
        return
    _win()


func fail_from_enemy(reason: String) -> void:
    if _ended:
        return
    _fail(reason)


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


def _enemy_controller() -> str:
    return """extends Area3D

@export var behavior := "patrol"      # [ENEMY_BEHAVIOR]
@export var hp := 3                   # [ENEMY_HP]
@export var move_speed := 2.4         # [ENEMY_MOVE_SPEED]
@export var patrol_radius := 2.5      # [PATROL_RADIUS]
@export var detection_radius := 6.0   # [DETECTION_RADIUS]
@export var ranged_interval := 1.6    # [RANGED_INTERVAL]

var _origin := Vector3.ZERO
var _direction := 1.0
var _ranged_timer := 0.0
var _player: Node3D
var _game_manager: Node
var _label := ""


func setup(enemy_name: String, enemy_behavior: String, enemy_hp: int, game_manager: Node) -> void:
    _label = enemy_name
    behavior = enemy_behavior
    hp = enemy_hp
    _game_manager = game_manager


func _ready() -> void:
    _origin = global_position
    monitoring = true
    body_entered.connect(_on_body_entered)


func _physics_process(delta: float) -> void:
    if _player == null:
        _player = get_tree().get_first_node_in_group("player")
    match behavior:
        "chase":
            _chase(delta)
        "patrol":
            _patrol(delta)
        "ranged":
            _ranged(delta)
        "stationary":
            _stationary()
        _:
            _patrol(delta)


func _patrol(delta: float) -> void:
    position.x += _direction * move_speed * delta
    if abs(position.x - _origin.x) >= patrol_radius:
        _direction *= -1.0
    _fail_if_player_close("Patrol caught the player")


func _chase(delta: float) -> void:
    if _player == null:
        return
    var offset := _player.global_position - global_position
    if offset.length() <= detection_radius:
        global_position += offset.normalized() * move_speed * delta
    _fail_if_player_close("Chaser reached the player")


func _stationary() -> void:
    _fail_if_player_close("Sentry zone was breached")


func _ranged(delta: float) -> void:
    if _player == null:
        return
    var distance := global_position.distance_to(_player.global_position)
    if distance > detection_radius:
        return
    _ranged_timer += delta
    if _ranged_timer >= ranged_interval:
        _ranged_timer = 0.0
        _notify_failure("Ranged pressure pinned the player")


func _fail_if_player_close(reason: String) -> void:
    if _player != null and global_position.distance_to(_player.global_position) <= 1.15:
        _notify_failure(reason)


func _on_body_entered(body: Node) -> void:
    if body.is_in_group("player") or body.name == "FA_Player":
        _notify_failure("Enemy contact: " + _label)


func _notify_failure(reason: String) -> void:
    if _game_manager != null and _game_manager.has_method("fail_from_enemy"):
        _game_manager.fail_from_enemy(reason)
"""



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
