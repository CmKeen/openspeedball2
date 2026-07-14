from pathlib import Path

from sim.config import load_config
from sim.entities import Ball
from sim.furniture import (FurnitureState, check_bounce_domes,
                           check_electrobounces, check_star_banks,
                           tick_electrobounce_flash)
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


def test_star_bank_lights_own_star_once():
    bank = CFG.arena["star_banks"][0]  # team 1, left wall
    y = bank["y_min"] + 1
    furniture = FurnitureState()
    score = ScoreState()
    ball = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    hit = check_star_banks(ball, CFG.arena, CFG.scoring, furniture, score,
                           last_thrower_team=1)
    assert hit
    assert furniture.lit_stars_team1 == 0b00001
    assert score.score_team1 == CFG.scoring["star_bonus_points"]

    ball2 = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    check_star_banks(ball2, CFG.arena, CFG.scoring, furniture, score,
                     last_thrower_team=1)
    assert score.score_team1 == CFG.scoring["star_bonus_points"]  # not re-awarded


def test_star_bank_knocks_out_opponent_lit_star():
    bank = CFG.arena["star_banks"][0]  # team 1
    y = bank["y_min"] + 1
    furniture = FurnitureState()
    score = ScoreState()
    lit = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    check_star_banks(lit, CFG.arena, CFG.scoring, furniture, score,
                     last_thrower_team=1)
    assert score.score_team1 == CFG.scoring["star_bonus_points"]

    knockout = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    hit = check_star_banks(knockout, CFG.arena, CFG.scoring, furniture, score,
                           last_thrower_team=2)
    assert hit
    assert furniture.lit_stars_team1 == 0
    assert score.score_team1 == 0


def test_star_bank_full_row_awards_bonus_and_clears():
    bank = CFG.arena["star_banks"][0]  # team 1
    band_height = (bank["y_max"] - bank["y_min"]) // bank["count"]
    furniture = FurnitureState()
    score = ScoreState()
    for i in range(bank["count"]):
        y = bank["y_min"] + i * band_height + 1
        ball = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
        check_star_banks(ball, CFG.arena, CFG.scoring, furniture, score,
                         last_thrower_team=1)
    assert furniture.lit_stars_team1 == 0
    expected = (CFG.scoring["star_bonus_points"] * bank["count"]
               + CFG.scoring["star_row_bonus_points"])
    assert score.score_team1 == expected


def test_star_bank_ignores_held_or_stationary_ball():
    bank = CFG.arena["star_banks"][0]
    y = bank["y_min"] + 1
    furniture = FurnitureState()
    score = ScoreState()
    held = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0), held_by=object())
    assert not check_star_banks(held, CFG.arena, CFG.scoring, furniture, score,
                                last_thrower_team=1)
    stationary = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(0, 0))
    assert not check_star_banks(stationary, CFG.arena, CFG.scoring, furniture,
                                score, last_thrower_team=1)
