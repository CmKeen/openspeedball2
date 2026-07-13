from pathlib import Path

from sim.config import load_config
from sim.input import InputState
from sim.player import PlayerSim, apply_movement, speed_of
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def make_player(spd=128):
    stats = dict(agr=128, att=128, **{"def": 128}, spd=spd, thr=128,
                 pow=128, sta=128, int=128, health=255)
    return PlayerSim(pos=Vec(320, 576), index=0, team=1, position=2,
                     stats=stats, home=Vec(320, 576))


def test_speed_bonus_threshold():
    assert speed_of(make_player(spd=128), CFG.physics) == 2
    assert speed_of(make_player(spd=200), CFG.physics) == 3
    assert speed_of(make_player(spd=192), CFG.physics) == 3


def test_movement_sets_velocity_and_dir():
    p = make_player()
    apply_movement(p, InputState(dir=2), CFG.physics)   # East
    assert p.dir == 2
    assert p.vel == Vec(2, 0)


def test_no_input_stops_player():
    p = make_player()
    apply_movement(p, InputState(dir=2), CFG.physics)
    apply_movement(p, InputState(dir=None), CFG.physics)
    assert p.vel == Vec(0, 0)


def test_falling_player_ignores_input_and_recovers():
    p = make_player()
    p.falling_ticks = 2
    p.knock_vel = Vec(0, 3)
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.vel == Vec(0, 3)         # knocked, not steering
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.falling_ticks == 0
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.vel == Vec(-2, 0)        # control regained


def test_sliding_player_ignores_input_and_recovers():
    p = make_player()
    p.dir = 2                          # facing East
    p.sliding_ticks = 2
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.vel == Vec(4, 0)          # sliding East, ignoring West input
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.sliding_ticks == 0
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.vel == Vec(-2, 0)         # control regained, moving West
