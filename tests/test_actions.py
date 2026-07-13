from pathlib import Path

from sim.actions import (apply_tackle_damage, attempt_tackle,
                         tackle_probability, throw, try_pickup)
from sim.config import load_config
from sim.entities import Ball
from sim.player import PlayerSim
from sim.rng import Sb2Rng
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")
PHY = CFG.physics


def make_player(team=1, pos=Vec(320, 576), position=2, **over):
    stats = dict(agr=128, att=128, **{"def": 128}, spd=128, thr=128,
                 pow=128, sta=128, int=128, health=255)
    stats.update(over)
    return PlayerSim(pos=pos, index=0, team=team, position=position,
                     stats=stats, home=pos)


def test_pickup_in_range_only():
    ball = Ball(pos=Vec(320, 576))
    near = make_player(pos=Vec(325, 580))
    far = make_player(pos=Vec(400, 576))
    assert not try_pickup(ball, far, PHY)
    assert try_pickup(ball, near, PHY)
    assert ball.held_by is near


def test_throw_releases_ball_with_speed_and_bounce_timer():
    ball = Ball(pos=Vec(320, 576))
    p = make_player()
    ball.held_by = p
    p.dir = 2  # East
    speed_ref = [0]
    throw(ball, p, PHY, shot=False, ball_speed_ref=speed_ref)
    assert ball.held_by is None
    assert ball.vel == Vec(PHY["pass_speed"], 0)
    assert ball.bounce_timer == PHY["throw_bounce_timer"]
    assert speed_ref[0] == PHY["pass_speed"]


def test_tackle_probability_formula():
    att = make_player(att=200)
    dfn = make_player(team=2)
    dfn.dir = att.dir  # same facing -> max directional malus for defender? use table
    p = tackle_probability(att, dfn, PHY)
    malus = PHY["tackle_def_malus_by_delta_dir"][0]
    assert p == (200 + 256 - (128 - malus)) // 2


def test_goalkeeper_gets_defense_boost():
    att = make_player(att=128)
    gk = make_player(team=2, position=0)
    fielder = make_player(team=2, position=2)
    assert tackle_probability(att, gk, PHY) < tackle_probability(att, fielder, PHY)


def test_successful_tackle_transfers_ball_and_knocks_down():
    rng = Sb2Rng()          # first byte is 223
    ball = Ball(pos=Vec(320, 576))
    att = make_player(att=255)          # p = (255+256-def_eff)/2 > 223
    dfn = make_player(team=2, pos=Vec(330, 576), **{"def": 0})
    ball.held_by = dfn
    hit = attempt_tackle(att, [dfn], ball, rng, PHY)
    assert hit is dfn
    assert dfn.falling_ticks == PHY["fall_ticks"]
    assert ball.held_by is att
    assert dfn.stats["health"] < 255


def test_out_of_range_tackle_misses():
    rng = Sb2Rng()
    ball = Ball(pos=Vec(320, 576))
    att = make_player()
    dfn = make_player(team=2, pos=Vec(320, 700))
    assert attempt_tackle(att, [dfn], ball, rng, PHY) is None


def test_tackle_damage_floors():
    att = make_player(pow=255)
    dfn = make_player(team=2, sta=0)
    apply_tackle_damage(dfn, att)
    d = (255 + 150 - 0) // 16
    assert dfn.stats["health"] == 255 - d
    assert dfn.stats["spd"] == 128 - max(1, d // 2)
