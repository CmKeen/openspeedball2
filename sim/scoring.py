"""Goals, score, and the side-wall score-multiplier banks.

Point values and multiplier behavior are data-driven (data/scoring.json)
and marked [tunable — validate] against the reference implementation.
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.entities import Ball
from sim.vec import Vec


@dataclass(slots=True)
class ScoreState:
    score_team1: int = 0
    score_team2: int = 0
    multiplier_team1_ticks: int = 0
    multiplier_team2_ticks: int = 0


def check_goal(ball: Ball, arena: dict) -> int:
    if ball.held_by is not None:
        return 0  # carrying the ball across the line does not score
    if not (arena["goal_mouth_x_min"] <= ball.pos.x <= arena["goal_mouth_x_max"]):
        return 0
    if ball.pos.y <= arena["goal_depth"]:
        return 1  # crossed top line: team 1 (attacking top) scored
    if ball.pos.y >= arena["height"] - arena["goal_depth"]:
        return 2
    return 0


def award_goal(state: ScoreState, team: int, scoring: dict) -> None:
    lit = (state.multiplier_team1_ticks if team == 1
           else state.multiplier_team2_ticks) > 0
    pts = scoring["goal_points_multiplied"] if lit else scoring["goal_points"]
    if team == 1:
        state.score_team1 += pts
    else:
        state.score_team2 += pts


def check_multiplier_banks(ball: Ball, arena: dict, scoring: dict,
                           state: ScoreState, last_thrower_team: int) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    for bank in arena["multiplier_banks"]:
        if (bank["x_min"] <= ball.pos.x <= bank["x_max"]
                and bank["y_min"] <= ball.pos.y <= bank["y_max"]):
            if last_thrower_team == 1:
                state.multiplier_team1_ticks = scoring["multiplier_duration_ticks"]
            elif last_thrower_team == 2:
                state.multiplier_team2_ticks = scoring["multiplier_duration_ticks"]
            # Eject toward the pitch center: banks hugging the left wall
            # (right edge at or left of mid-width) push the ball rightward,
            # right-wall banks push it leftward.
            eject = 4 if bank["x_max"] <= arena["width"] // 2 else -4
            ball.pos = Vec(bank["x_max"] + 8 if eject > 0 else bank["x_min"] - 8,
                           ball.pos.y)
            ball.vel = Vec(eject, 0)
            ball.bounce_timer = 0
            return True
    return False


def tick_multipliers(state: ScoreState) -> None:
    if state.multiplier_team1_ticks > 0:
        state.multiplier_team1_ticks -= 1
    if state.multiplier_team2_ticks > 0:
        state.multiplier_team2_ticks -= 1
