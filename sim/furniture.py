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


def check_electrobounces(ball: Ball, arena: dict, physics: dict,
                         furniture: FurnitureState) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    plates = arena["electrobounces"]
    hit_range = physics["electrobounce_range"]
    for plate in plates:
        pos = Vec(*plate["pos"])
        if ball.pos.chebyshev(pos) > hit_range:
            continue
        other = next(p for p in plates if p is not plate)
        speed = physics["electrobounce_speed"]
        push = -speed if plate["wall"] == "left" else speed
        ball.pos = Vec(other["pos"][0], ball.pos.y)
        ball.vel = Vec(push, 0)
        ball.bounce_timer = 0
        furniture.electrobounce_flash_ticks = 2
        return True
    return False


def tick_electrobounce_flash(furniture: FurnitureState) -> None:
    if furniture.electrobounce_flash_ticks > 0:
        furniture.electrobounce_flash_ticks -= 1


def _star_mask(furniture: FurnitureState, team: int) -> int:
    return furniture.lit_stars_team1 if team == 1 else furniture.lit_stars_team2


def _set_star_mask(furniture: FurnitureState, team: int, mask: int) -> None:
    if team == 1:
        furniture.lit_stars_team1 = mask
    else:
        furniture.lit_stars_team2 = mask


def _star_band_index(ball: Ball, bank: dict) -> int:
    band_height = (bank["y_max"] - bank["y_min"]) // bank["count"]
    idx = (ball.pos.y - bank["y_min"]) // band_height
    return min(bank["count"] - 1, max(0, idx))


def _light_star(furniture: FurnitureState, bank: dict, idx: int,
                score: ScoreState, scoring: dict) -> None:
    team = bank["team"]
    mask = _star_mask(furniture, team)
    if mask & (1 << idx):
        return
    mask |= (1 << idx)
    _add_score(score, team, scoring["star_bonus_points"])
    full_mask = (1 << bank["count"]) - 1
    if mask == full_mask:
        _add_score(score, team, scoring["star_row_bonus_points"])
        mask = 0
    _set_star_mask(furniture, team, mask)


def _unlight_star(furniture: FurnitureState, bank: dict, idx: int,
                  score: ScoreState, scoring: dict) -> None:
    team = bank["team"]
    mask = _star_mask(furniture, team)
    if not (mask & (1 << idx)):
        return
    mask &= ~(1 << idx)
    _add_score(score, team, -scoring["star_bonus_points"])
    _set_star_mask(furniture, team, mask)


def check_star_banks(ball: Ball, arena: dict, scoring: dict,
                     furniture: FurnitureState, score: ScoreState,
                     last_thrower_team: int) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    for bank in arena["star_banks"]:
        if not (bank["x_min"] <= ball.pos.x <= bank["x_max"]
                and bank["y_min"] <= ball.pos.y <= bank["y_max"]):
            continue
        idx = _star_band_index(ball, bank)
        if last_thrower_team == bank["team"]:
            _light_star(furniture, bank, idx, score, scoring)
        elif last_thrower_team in (1, 2):
            _unlight_star(furniture, bank, idx, score, scoring)
        eject = 4 if bank["x_max"] <= arena["width"] // 2 else -4
        ball.pos = Vec(bank["x_max"] + 8 if eject > 0 else bank["x_min"] - 8,
                       ball.pos.y)
        ball.vel = Vec(eject, 0)
        ball.bounce_timer = 0
        return True
    return False
