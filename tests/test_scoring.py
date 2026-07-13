from pathlib import Path

from sim.config import load_config
from sim.entities import Ball
from sim.scoring import (ScoreState, award_goal, check_goal,
                         check_multiplier_banks, tick_multipliers)
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_goal_only_inside_mouth():
    in_mouth = Ball(pos=Vec(320, 10))          # top goal, inside mouth
    outside = Ball(pos=Vec(100, 10))           # top line, outside mouth
    midfield = Ball(pos=Vec(320, 576))
    assert check_goal(in_mouth, CFG.arena) == 1
    assert check_goal(outside, CFG.arena) == 0
    assert check_goal(midfield, CFG.arena) == 0
    assert check_goal(Ball(pos=Vec(320, 1145)), CFG.arena) == 2


def test_award_goal_respects_multiplier():
    s = ScoreState()
    award_goal(s, 1, CFG.scoring)
    assert s.score_team1 == CFG.scoring["goal_points"]
    s.multiplier_team1_ticks = 100
    award_goal(s, 1, CFG.scoring)
    assert s.score_team1 == (CFG.scoring["goal_points"]
                             + CFG.scoring["goal_points_multiplied"])


def test_bank_lights_multiplier_and_ejects_ball():
    s = ScoreState()
    bank = CFG.arena["multiplier_banks"][0]
    y = (bank["y_min"] + bank["y_max"]) // 2
    ball = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-6, 0))
    hit = check_multiplier_banks(ball, CFG.arena, CFG.scoring, s,
                                 last_thrower_team=2)
    assert hit
    assert s.multiplier_team2_ticks == CFG.scoring["multiplier_duration_ticks"]
    assert ball.vel.x > 0  # ejected back toward play


def test_multiplier_expires():
    s = ScoreState()
    s.multiplier_team1_ticks = 2
    tick_multipliers(s)
    tick_multipliers(s)
    tick_multipliers(s)
    assert s.multiplier_team1_ticks == 0
