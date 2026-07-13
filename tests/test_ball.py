from pathlib import Path

from sim.config import load_config
from sim.entities import Ball, Entity, move_and_bounce, update_ball_velocity
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def make_ball(pos, vel, timer=0):
    b = Ball(pos=pos, vel=vel)
    b.bounce_timer = timer
    return b


def test_ball_reflects_off_right_wall():
    b = make_ball(Vec(650, 600), Vec(5, 0))  # already past the wall
    move_and_bounce(b, CFG.arena, margin=16, is_ball=True)
    # clamped to 640-16=624, velocity reflected, then moved by new velocity
    assert b.vel.x == -5
    assert b.pos.x == 624 - 5


def test_ball_y_bounce_halves_bounce_timer():
    b = make_ball(Vec(320, 1160), Vec(0, 6), timer=20)
    move_and_bounce(b, CFG.arena, margin=16, is_ball=True)
    assert b.vel.y == -6
    assert b.bounce_timer == 10


def test_player_clamps_without_reflecting():
    p = Entity(pos=Vec(700, 600), vel=Vec(3, 0))
    move_and_bounce(p, CFG.arena, margin=16, is_ball=False)
    assert p.vel.x == 3          # players don't bounce
    assert p.pos.x == 624 + 3    # clamped then moved


def test_free_ball_friction_decays_each_axis_by_one():
    b = make_ball(Vec(320, 600), Vec(5, -3))
    update_ball_velocity(b, CFG.physics, [0])
    assert b.vel == Vec(4, -2)


def test_no_friction_in_goal_zone_when_moving_vertically():
    b = make_ball(Vec(320, 40), Vec(2, -4))  # y < 48
    update_ball_velocity(b, CFG.physics, [0])
    assert b.vel == Vec(2, -4)


def test_held_ball_skips_friction():
    b = make_ball(Vec(320, 600), Vec(5, 5))
    b.held_by = object()
    update_ball_velocity(b, CFG.physics, [0])
    assert b.vel == Vec(5, 5)


def test_bounce_timer_defers_friction():
    b = make_ball(Vec(320, 600), Vec(6, 0), timer=10)
    speed_ref = [4]  # match's recent-throw speed below timer -> timer path
    update_ball_velocity(b, CFG.physics, speed_ref)
    assert b.vel == Vec(6, 0)      # friction deferred
    assert b.bounce_timer == 9     # timer ticks down
