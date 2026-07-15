from pathlib import Path

from sim.config import load_config
from sim.vec import Vec, DIR_VECTORS, mirror_dir_x, mirror_dir_y

DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_config_shapes():
    cfg = load_config(DATA)
    assert cfg.arena["width"] == 640
    assert cfg.arena["height"] == 1152
    assert cfg.physics["ball_friction_per_tick"] == 1
    assert len(cfg.teams["teams"]) == 2
    for team in cfg.teams["teams"]:
        assert len(team["players"]) == 9
        assert team["players"][0]["position"] == 0  # goalkeeper first


def test_furniture_data_shapes():
    cfg = load_config(DATA)
    assert len(cfg.arena["bounce_domes"]) == 2
    for dome in cfg.arena["bounce_domes"]:
        assert len(dome["pos"]) == 2
        assert dome["radius"] > 0

    assert len(cfg.arena["electrobounces"]) == 2
    walls = {p["wall"] for p in cfg.arena["electrobounces"]}
    assert walls == {"left", "right"}

    assert len(cfg.arena["star_banks"]) == 2
    teams = {b["team"] for b in cfg.arena["star_banks"]}
    assert teams == {1, 2}
    for bank in cfg.arena["star_banks"]:
        assert bank["count"] == 5

    assert cfg.physics["dome_bounce_speed"] > 0
    assert cfg.physics["electrobounce_speed"] > 0
    assert cfg.physics["electrobounce_range"] > 0

    assert cfg.scoring["dome_bonus_points"] > 0
    assert cfg.scoring["star_bonus_points"] > 0
    assert cfg.scoring["star_row_bonus_points"] > 0


def test_dir_vectors():
    assert DIR_VECTORS[0] == Vec(0, -1)   # N
    assert DIR_VECTORS[2] == Vec(1, 0)    # E
    assert DIR_VECTORS[4] == Vec(0, 1)    # S
    assert DIR_VECTORS[6] == Vec(-1, 0)   # W
    assert DIR_VECTORS[1] == Vec(1, -1)   # NE


def test_mirror_dirs():
    assert mirror_dir_x(2) == 6 and mirror_dir_x(6) == 2   # E <-> W
    assert mirror_dir_x(0) == 0 and mirror_dir_x(4) == 4   # N, S unchanged
    assert mirror_dir_y(0) == 4 and mirror_dir_y(4) == 0   # N <-> S
    assert mirror_dir_y(1) == 3 and mirror_dir_y(7) == 5   # NE<->SE, NW<->SW


def test_vec_math():
    assert Vec(1, 2) + Vec(3, -1) == Vec(4, 1)
    assert Vec(5, 5) - Vec(2, 7) == Vec(3, -2)
    assert Vec(0, 0).manhattan(Vec(3, -4)) == 7
    assert Vec(0, 0).chebyshev(Vec(3, -4)) == 4
