from pathlib import Path

from sim.ai import compute_ai_inputs
from sim.config import load_config
from sim.match import Match, player_id
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_ai_covers_all_uncontrolled_players():
    m = Match(CFG, seed=(5, 5))
    human = {player_id(1, 4)}
    inputs = compute_ai_inputs(m, human)
    assert set(inputs) == {player_id(p.team, p.index)
                           for p in m.all_players()} - human


def test_ai_vs_ai_match_is_deterministic_and_produces_play():
    def run():
        m = Match(CFG, seed=(2026, 713))
        touches = 0
        for _ in range(6000):  # 2 in-game minutes
            held_before = m.ball.held_by
            m.tick_with_ai({})
            if m.ball.held_by is not held_before:
                touches += 1
        return m.state_hash(), touches, m.score.score_team1 + m.score.score_team2

    r1, r2 = run(), run()
    assert r1 == r2                    # deterministic
    assert r1[1] > 10                  # possession actually changes hands
    # scoring is not guaranteed in 2 minutes, but the sim must not deadlock:
    assert r1[0] != 0


def test_ai_chases_free_ball():
    m = Match(CFG, seed=(3, 3))
    m.ball.held_by = None
    before = min(p.pos.chebyshev(m.ball.pos) for p in m.players_team2)
    for _ in range(30):
        m.tick_with_ai({})
    after = min(p.pos.chebyshev(m.ball.pos) for p in m.players_team2)
    assert after <= before


def test_carry_roll_fires_only_in_shot_range():
    m = Match(CFG, seed=(11, 11))
    carrier = m.players_team1[4]
    carrier.pos = Vec(320, 900)
    m.ball.held_by = carrier
    m._prev_holder = m.ball.held_by
    m._ai_possession_rolled = False

    state_before = (m.rng.a, m.rng.b)
    compute_ai_inputs(m, set())
    assert (m.rng.a, m.rng.b) == state_before
    assert m._ai_possession_rolled is False

    carrier.pos = Vec(320, 200)
    inputs = compute_ai_inputs(m, set())
    assert (m.rng.a, m.rng.b) != state_before
    assert m._ai_possession_rolled is True
    carrier_input = inputs[player_id(carrier.team, carrier.index)]
    assert carrier_input.action_a or carrier_input.action_b
