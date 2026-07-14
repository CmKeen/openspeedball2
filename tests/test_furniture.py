from pathlib import Path

from sim.config import load_config
from sim.entities import Ball
from sim.furniture import (FurnitureState, check_bounce_domes,
                           check_electrobounces, tick_electrobounce_flash)
from sim.scoring import ScoreState
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_bounce_dome_reflects_ball_and_scores():
    dome = CFG.arena["bounce_domes"][0]
    center = Vec(*dome["pos"])
    ball = Ball(pos=Vec(center.x, center.y - dome["radius"]), vel=Vec(0, -4))
    score = ScoreState()
    hit = check_bounce_domes(ball, CFG.arena, CFG.physics, 1, score, CFG.scoring)
    assert hit
    assert score.score_team1 == CFG.scoring["dome_bonus_points"]
    assert ball.pos.chebyshev(center) == dome["radius"]
    assert ball.vel != Vec(0, 0)


def test_bounce_dome_ignores_held_or_stationary_ball():
    dome = CFG.arena["bounce_domes"][0]
    center = Vec(*dome["pos"])
    score = ScoreState()
    held = Ball(pos=center, vel=Vec(0, 0), held_by=object())
    assert not check_bounce_domes(held, CFG.arena, CFG.physics, 1, score, CFG.scoring)
    stationary = Ball(pos=center, vel=Vec(0, 0))
    assert not check_bounce_domes(stationary, CFG.arena, CFG.physics, 1, score, CFG.scoring)
    assert score.score_team1 == 0


def test_bounce_dome_no_score_when_no_thrower():
    dome = CFG.arena["bounce_domes"][0]
    center = Vec(*dome["pos"])
    ball = Ball(pos=center, vel=Vec(0, -4))
    score = ScoreState()
    hit = check_bounce_domes(ball, CFG.arena, CFG.physics, 0, score, CFG.scoring)
    assert hit
    assert score.score_team1 == 0
    assert score.score_team2 == 0


def test_electrobounce_teleports_left_hit_to_right_plate():
    left, right = CFG.arena["electrobounces"]
    ball = Ball(pos=Vec(*left["pos"]), vel=Vec(-4, 0))
    furniture = FurnitureState()
    hit = check_electrobounces(ball, CFG.arena, CFG.physics, furniture)
    assert hit
    assert ball.pos.x == right["pos"][0]
    assert ball.vel.x < 0  # pushed away from the right wall, back onto the pitch
    assert furniture.electrobounce_flash_ticks == 2


def test_electrobounce_teleports_right_hit_to_left_plate():
    left, right = CFG.arena["electrobounces"]
    ball = Ball(pos=Vec(*right["pos"]), vel=Vec(4, 0))
    furniture = FurnitureState()
    hit = check_electrobounces(ball, CFG.arena, CFG.physics, furniture)
    assert hit
    assert ball.pos.x == left["pos"][0]
    assert ball.vel.x > 0  # pushed away from the left wall, back onto the pitch


def test_electrobounce_ignores_held_or_stationary_ball():
    left, _ = CFG.arena["electrobounces"]
    furniture = FurnitureState()
    held = Ball(pos=Vec(*left["pos"]), vel=Vec(0, 0), held_by=object())
    assert not check_electrobounces(held, CFG.arena, CFG.physics, furniture)
    stationary = Ball(pos=Vec(*left["pos"]), vel=Vec(0, 0))
    assert not check_electrobounces(stationary, CFG.arena, CFG.physics, furniture)


def test_tick_electrobounce_flash_counts_down_and_floors_at_zero():
    furniture = FurnitureState(electrobounce_flash_ticks=2)
    tick_electrobounce_flash(furniture)
    assert furniture.electrobounce_flash_ticks == 1
    tick_electrobounce_flash(furniture)
    assert furniture.electrobounce_flash_ticks == 0
    tick_electrobounce_flash(furniture)
    assert furniture.electrobounce_flash_ticks == 0
