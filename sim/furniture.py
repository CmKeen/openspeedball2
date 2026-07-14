"""Arena furniture: bounce domes, electrobounces, star banks.

Tier-1 furniture per
docs/superpowers/specs/2026-07-14-arena-furniture-design.md. Token/warp-gate
pickups are a separate, future design and out of scope here.

All three effects trigger on a live free ball (held_by is None and
vel != (0, 0)) — the same condition sim/scoring.py's check_multiplier_banks
already uses. Range checks use Chebyshev distance, matching every other
range check in this codebase (pickup_range, tackle_range, AI thresholds).
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.entities import Ball
from sim.scoring import ScoreState
from sim.vec import DIR_VECTORS, Vec, dir_towards


@dataclass(slots=True)
class FurnitureState:
    lit_stars_team1: int = 0
    lit_stars_team2: int = 0
    electrobounce_flash_ticks: int = 0


def _add_score(score: ScoreState, team: int, points: int) -> None:
    if team == 1:
        score.score_team1 += points
    else:
        score.score_team2 += points


def check_bounce_domes(ball: Ball, arena: dict, physics: dict,
                       last_thrower_team: int, score: ScoreState,
                       scoring: dict) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    for dome in arena["bounce_domes"]:
        center = Vec(*dome["pos"])
        if ball.pos.chebyshev(center) > dome["radius"]:
            continue
        d = dir_towards(center, ball.pos)
        step = DIR_VECTORS[d]
        speed = physics["dome_bounce_speed"]
        ball.pos = Vec(center.x + step.x * dome["radius"],
                       center.y + step.y * dome["radius"])
        ball.vel = Vec(step.x * speed, step.y * speed)
        ball.dir = d
        ball.bounce_timer = 0
        if last_thrower_team in (1, 2):
            _add_score(score, last_thrower_team, scoring["dome_bonus_points"])
        return True
    return False
