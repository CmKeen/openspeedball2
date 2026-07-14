"""Possession, throwing, tackling — formulas per docs/spec/mechanics.md."""
from __future__ import annotations

from sim.entities import Ball
from sim.player import PlayerSim
from sim.rng import Sb2Rng
from sim.vec import DIR_VECTORS, Vec


def try_pickup(ball: Ball, p: PlayerSim, physics: dict) -> bool:
    if ball.held_by is not None or p.falling_ticks > 0:
        return False
    # The thrower can't re-catch their own live throw (same-tick release),
    # but teammates and opponents remain free to intercept/catch it.
    if p is ball.last_thrower and ball.bounce_timer > 0:
        return False
    if ball.pos.chebyshev(p.pos) > physics["pickup_range"]:
        return False
    ball.held_by = p
    ball.vel = Vec(0, 0)
    ball.bounce_timer = 0
    ball.last_thrower = None
    return True


def throw(ball: Ball, p: PlayerSim, physics: dict, shot: bool,
          ball_speed_ref: list[int]) -> None:
    if ball.held_by is not p:
        raise ValueError("throw() requires the thrower to hold the ball")
    speed = physics["shot_speed"] if shot else physics["pass_speed"]
    step = DIR_VECTORS[p.dir]
    ball.held_by = None
    ball.last_thrower = p
    ball.dir = p.dir
    ball.vel = Vec(step.x * speed, step.y * speed)
    ball.bounce_timer = physics["throw_bounce_timer"]
    ball_speed_ref[0] = speed


def tackle_probability(attacker: PlayerSim, defender: PlayerSim,
                       physics: dict) -> int:
    d_att = attacker.stats["att"]
    d_def = defender.stats["def"]
    if defender.position == 0:  # goalkeeper defends harder
        d_def = min(255, d_def * physics["goalkeeper_def_multiplier_num"]
                    // physics["goalkeeper_def_multiplier_den"])
    delta_dir = (defender.dir - attacker.dir + 8) & 7
    d_def -= physics["tackle_def_malus_by_delta_dir"][delta_dir]
    if attacker.sliding_ticks > 0:
        d_def -= physics["tackle_malus_sliding"]
    return (d_att + 256 - d_def) // 2


def apply_tackle_damage(defender: PlayerSim, attacker: PlayerSim) -> None:
    d = max(1, (attacker.stats["pow"] + 150 - defender.stats["sta"]) // 16)
    defender.stats["health"] = max(0, defender.stats["health"] - d)
    hit = max(1, d // 2)
    for key in ("agr", "att", "def", "spd", "thr", "pow", "sta", "int"):
        defender.stats[key] = max(1, defender.stats[key] - hit)


def attempt_tackle(attacker: PlayerSim, defenders: list[PlayerSim],
                   ball: Ball, rng: Sb2Rng, physics: dict) -> PlayerSim | None:
    for dfn in defenders:
        if dfn.falling_ticks > 0:
            continue
        if attacker.pos.chebyshev(dfn.pos) > physics["tackle_range"]:
            continue
        if rng.next_byte() > tackle_probability(attacker, dfn, physics):
            return None  # rolled and missed: one attempt per trigger
        apply_tackle_damage(dfn, attacker)
        speed = (physics["tackle_knockback_speed_sliding"]
                 if attacker.sliding_ticks > 0
                 else physics["tackle_knockback_speed"])
        step = DIR_VECTORS[attacker.dir]
        dfn.falling_ticks = physics["fall_ticks"]
        dfn.knock_vel = Vec(step.x * speed, step.y * speed)
        # Facing after a knockdown mirrors the tackler's facing, matching
        # the reference implementation's tackle knockdown behavior.
        dfn.dir = attacker.dir
        if ball.held_by is dfn:
            ball.held_by = None if attacker.falling_ticks > 0 else attacker
        return dfn
    return None
