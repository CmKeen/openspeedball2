"""Tests for the pure keyboard-mapping logic and the facing-based throw.

The action tick deliberately withholds direction (dir=None) so the sim's
persistent facing decides the throw/slide direction — this is what makes
diagonal passes immune to key ghosting at the press instant.
"""
from pathlib import Path

from present.input_map import compute_input
from sim.config import load_config
from sim.input import InputState
from sim.match import Match, player_id
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_movement_axes_map_to_all_eight_dirs():
    assert compute_input(0, -1, False) == InputState(dir=0)   # N
    assert compute_input(1, -1, False) == InputState(dir=1)   # NE
    assert compute_input(1, 0, False) == InputState(dir=2)    # E
    assert compute_input(1, 1, False) == InputState(dir=3)    # SE
    assert compute_input(0, 1, False) == InputState(dir=4)    # S
    assert compute_input(-1, 1, False) == InputState(dir=5)   # SW
    assert compute_input(-1, 0, False) == InputState(dir=6)   # W
    assert compute_input(-1, -1, False) == InputState(dir=7)  # NW


def test_no_keys_is_idle():
    assert compute_input(0, 0, False) == InputState(dir=None)


def test_action_edge_is_single_button_and_withholds_dir():
    # Space fires both sim actions (throw for a holder, slide-tackle
    # otherwise) and never overrides the player's persistent facing —
    # even if direction keys read cardinal/empty on the press tick.
    for dx, dy in ((1, -1), (0, -1), (0, 0)):
        inp = compute_input(dx, dy, True)
        assert inp.dir is None
        assert inp.action_a and inp.action_b


def test_diagonal_throw_uses_persistent_facing():
    # Run NE for a few ticks, then press the action button on a tick where
    # the direction read is empty (ghosted): the ball must fly NE anyway.
    # Start within shot range of the opponent's goal so the single-button
    # throw resolves as a shot (see test_action_button_passes_outside_shot_range
    # for the complementary pass case).
    m = Match(CFG, seed=(9, 9))
    p = m.players_team1[4]
    p.pos = Vec(320, 200)
    m.ball.held_by = p
    m._prev_holder = p
    pid = player_id(1, 4)
    for _ in range(3):
        m.tick({pid: compute_input(1, -1, False)})  # move NE, facing NE
    m.tick({pid: compute_input(0, 0, True)})        # action tick, no dir read
    assert m.ball.held_by is None
    shot = CFG.physics["shot_speed"]
    assert m.ball.vel == Vec(shot, -shot)           # NE diagonal


def test_action_button_passes_outside_shot_range():
    # Regression test: the single-button refactor set both action_a and
    # action_b true on every press, which made shot=inp.action_b always
    # True and pass_speed unreachable for humans. Far from goal, the button
    # must resolve as a pass (pass_speed), matching the AI's own
    # decide_carry threshold (ai_shot_range).
    m = Match(CFG, seed=(9, 9))
    p = m.players_team1[4]
    p.pos = Vec(320, 720)  # home row, far outside ai_shot_range of either goal
    p.dir = 0  # facing north
    m.ball.held_by = p
    m._prev_holder = p
    pid = player_id(1, 4)
    m.tick({pid: compute_input(0, 0, True)})
    assert m.ball.held_by is None
    pass_speed = CFG.physics["pass_speed"]
    assert m.ball.vel == Vec(0, -pass_speed)
