"""Entities and ball physics.

Rules translated from the documented RE (see docs/spec/mechanics.md):
walls clamp positions to [margin, limit - margin]; the ball reflects and
mirrors its direction; a Y bounce halves the bounce timer. Free-ball
friction decays each velocity axis by 1 per tick, deferred while the
bounce timer outruns the match's recent-throw speed, and suspended in the
goal zones while the ball moves vertically.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sim.vec import Vec, mirror_dir_x, mirror_dir_y


@dataclass(slots=True)
class Entity:
    pos: Vec
    vel: Vec = field(default_factory=lambda: Vec(0, 0))
    dir: int = 0


@dataclass(slots=True)
class Ball(Entity):
    bounce_timer: int = 0
    held_by: object | None = None
    in_bank: bool = False


def _axis(value: int, vel: int, low: int, high: int) -> tuple[int, int, bool]:
    if value > high:
        return high, vel, True
    if value < low:
        return low, vel, True
    return value, vel, False


def move_and_bounce(e: Entity, arena: dict, margin: int, is_ball: bool) -> None:
    x, vx, hit_x = _axis(e.pos.x, e.vel.x, margin, arena["width"] - margin)
    if hit_x and is_ball:
        vx = -vx
        e.dir = mirror_dir_x(e.dir)
    x += vx

    y, vy, hit_y = _axis(e.pos.y, e.vel.y, margin, arena["height"] - margin)
    if hit_y and is_ball:
        vy = -vy
        e.dir = mirror_dir_y(e.dir)
        if isinstance(e, Ball):
            e.bounce_timer -= e.bounce_timer // 2
    y += vy

    e.pos = Vec(x, y)
    e.vel = Vec(vx, vy)


def _decay(v: int) -> int:
    return v - 1 if v > 0 else v + 1 if v < 0 else 0


def update_ball_velocity(ball: Ball, physics: dict,
                         ball_speed_ref: list[int]) -> None:
    if ball.held_by is not None or ball.in_bank:
        return
    if ball.vel == Vec(0, 0):
        return
    if ball.vel.y != 0 and (ball.pos.y < physics["ball_no_friction_y_min"]
                            or ball.pos.y > physics["ball_no_friction_y_max"]):
        return

    if ball.bounce_timer != 0:
        if ball_speed_ref[0] <= ball.bounce_timer:
            ball.bounce_timer -= 1
            return
        ball_speed_ref[0] = ball_speed_ref[0] // 2 + ball_speed_ref[0] // 4

    ball.vel = Vec(_decay(ball.vel.x), _decay(ball.vel.y))
    if ball.bounce_timer != 0:
        ball.bounce_timer -= 1
