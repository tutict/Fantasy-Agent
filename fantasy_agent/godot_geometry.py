"""One owner for the numbers that decide whether the generated route can be walked.

Two code generators have to agree on a single distance: how close an enemy may
get before it does something to the player.

* :mod:`fantasy_agent.gameplay_codegen` writes the enemy controller, which
  measures that distance.
* :mod:`fantasy_agent.godot_mcp` writes the level, which decides where the
  enemies stand relative to the lane the player walks.

They used to agree by coincidence: both spelled ``1.15``. The coincidence was
wrong in the worst possible way -- the enemy lane sat at *exactly* the lethal
radius, so a lane's danger zone reached the corridor centreline. With one enemy
in each lane the 3.0 m corridor had no passable width at all: 301 sampled
points across the tile, 0 of them safe. The generated slice ran 5/5 playtests to
``progress: 0`` about half a second after spawn, and the only thing the report
could say was "no run reached a win".

Keeping the numbers here makes the relation an assertion instead of a
coincidence: :func:`check_lane_layout` is called while the level is being
written, so a layout that cannot be walked fails the generator instead of
shipping.

The enemy radius and the player radius are not invented either -- they are the
two shapes the generated project actually creates (``CapsuleShape3D`` radius
0.4 in ``_GAMEPLAY_SPAWN_GD``, ``SphereShape3D`` radius 0.75 in
``_decorate_enemy``). An enemy whose body would be touching the player is at
:data:`LETHAL_RADIUS`, by construction rather than by tuning.
"""

from __future__ import annotations

#: The generated player capsule's radius, emitted in ``_GAMEPLAY_SPAWN_GD``.
PLAYER_RADIUS = 0.4

#: The generated enemy sphere's radius, emitted in ``_decorate_enemy``.
ENEMY_RADIUS = 0.75

#: Centres this close mean the two shapes overlap: the enemy has the player.
#: Rounded because these numbers are emitted as GDScript literals, and
#: ``1.1500000000000001`` in generated source reads like a tuning accident.
LETHAL_RADIUS = round(PLAYER_RADIUS + ENEMY_RADIUS, 3)

#: Width (x) of every generated route floor tile: ``Vector3(3.0, 0.25, 5.0)``.
CORRIDOR_WIDTH = 3.0
CORRIDOR_HALF = CORRIDOR_WIDTH / 2.0

#: How far past a tile edge an enemy's centre may stand and still read as
#: guarding the walkway. Matches ``ROUTE_SLACK`` in the engine-side check, which
#: allows a patrolling body to cross the edge by up to one frame of travel.
LANE_OVERHANG = 0.5

#: Where the generated enemies stand, laterally. Derived from the lethal radius
#: rather than chosen: the corridor centreline has to be outside the danger zone
#: of every lane, or a player walking straight down the middle -- which is what
#: the playtest bot and most first-time players do -- cannot get past.
#:
#: The 0.6 is the half-width of the slot that is left over, and it is a width
#: budget, not a taste: two lanes spend ``2 * 0.6 = 1.2m`` of the 3.0m corridor
#: on "floor nobody can stand on", which is twice the player's own diameter.
#: At 0.45 the slot is 0.9m -- one diameter plus 10cm, i.e. technically walkable
#: and miserable to walk.
ENEMY_LANE = round(LETHAL_RADIUS + 0.6, 3)

#: The narrowest gap a player may be asked to thread. One player diameter: any
#: less and "walkable" only means "walkable if you are a point".
MIN_WALKABLE_BAND = PLAYER_RADIUS * 2.0


class LevelGeometryError(RuntimeError):
    """A generated layout whose corridor has no walkable width left."""


def kill_zone(lane: float) -> tuple[float, float]:
    """The x interval in which an enemy standing at ``lane`` has the player."""

    return (lane - LETHAL_RADIUS, lane + LETHAL_RADIUS)


def walkable_band(lanes: list[float]) -> tuple[float, float] | None:
    """The widest stretch of corridor x no enemy can reach, or ``None``.

    Every lane contributes a closed interval; the corridor is its own closed
    interval. The answer is the widest gap left between them, clipped to the
    corridor, because a stretch of floor outside the tile is not a route.
    """

    free = [(-CORRIDOR_HALF, CORRIDOR_HALF)]
    for lane in lanes:
        low, high = kill_zone(lane)
        remaining: list[tuple[float, float]] = []
        for start, end in free:
            if high <= start or low >= end:
                remaining.append((start, end))
                continue
            if start < low:
                remaining.append((start, low))
            if high < end:
                remaining.append((high, end))
        free = remaining
    if not free:
        return None
    # Ties are broken towards the centre: the middle of the corridor is the
    # lane a player naturally holds, so it is the one worth reporting.
    return max(free, key=lambda band: (band[1] - band[0], -abs(band[0] + band[1])))


def check_lane_layout(lanes: list[float]) -> None:
    """Raise unless ``lanes`` leaves a corridor a player can actually walk.

    Called while the level is being generated. A layout that fails here used to
    be emitted anyway, and the only thing that noticed was a five-run playtest
    half a minute later saying it had not seen a win -- which reads like a bot
    problem and is a level problem.
    """

    if not lanes:
        return
    for lane in lanes:
        if abs(lane) > CORRIDOR_HALF + LANE_OVERHANG:
            raise LevelGeometryError(
                f"enemy lane {lane:+.2f} is off the route: a 3m tile allows "
                f"|x| <= {CORRIDOR_HALF + LANE_OVERHANG:.2f}"
            )
    band = walkable_band(lanes)
    if band is None:
        raise LevelGeometryError(
            f"lanes {lanes} cover the whole {CORRIDOR_WIDTH:g}m corridor: "
            f"no player can reach the exit"
        )
    width = band[1] - band[0]
    if width < MIN_WALKABLE_BAND:
        raise LevelGeometryError(
            f"lanes {lanes} leave only {width:.2f}m of walkable width "
            f"(x {band[0]:+.2f}..{band[1]:+.2f}), under the "
            f"{MIN_WALKABLE_BAND:.2f}m a player needs"
        )
