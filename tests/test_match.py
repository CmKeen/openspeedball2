from pathlib import Path

from sim.config import load_config
from sim.input import InputState
from sim.match import Match, player_id

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_kickoff_layout():
    m = Match(CFG)
    assert len(m.players_team1) == 9
    assert len(m.players_team2) == 9
    assert m.ball.pos.x == CFG.arena["kickoff_center"][0]
    # goalkeepers guard opposite ends
    assert m.players_team1[0].pos.y > m.players_team2[0].pos.y


def test_determinism_same_seed_same_hash_stream():
    def run():
        m = Match(CFG, seed=(42, 1337))
        hashes = []
        for t in range(1000):
            # deterministic scripted input for one player
            m.tick({player_id(1, 4): InputState(dir=t % 8)})
            hashes.append(m.state_hash())
        return hashes

    assert run() == run()


def test_different_seed_diverges():
    def run(seed):
        m = Match(CFG, seed=seed)
        for _ in range(300):
            m.tick({player_id(1, 4): InputState(dir=0, action_a=True)})
        return m.state_hash()

    # tackles consume RNG, so different seeds must eventually diverge
    assert run((1, 2)) != run((99, 100))


def test_scoring_a_goal_resets_and_scores():
    m = Match(CFG, seed=(7, 7))
    # teleport ball into the top goal mouth moving in
    from sim.vec import Vec
    m.ball.pos = Vec(320, 10)
    m.ball.held_by = None
    m.tick({})
    assert m.score.score_team1 == CFG.scoring["goal_points"]
    assert m.ball.pos.x == CFG.arena["kickoff_center"][0]


def test_clock_counts_down_to_over():
    m = Match(CFG, seed=(1, 1))
    m.clock_ticks = 3
    for _ in range(3):
        m.tick({})
    assert m.is_over


def test_action_b_alone_does_not_attempt_tackle():
    from sim.vec import Vec

    m = Match(CFG, seed=(3, 4))
    holder = m.players_team2[4]
    tackler = m.players_team1[4]
    holder.pos = Vec(320, 600)
    m.ball.held_by = holder
    tackler.pos = Vec(330, 600)

    rng_before = (m.rng.a, m.rng.b)
    m.tick({player_id(1, 4): InputState(action_b=True)})

    assert (m.rng.a, m.rng.b) == rng_before
    assert m.ball.held_by is holder


def test_kickoff_possession_pins_ball_to_holder():
    from sim.vec import Vec

    m = Match(CFG, seed=(7, 7))
    m.ball.pos = Vec(320, 10)
    m.ball.held_by = None
    m.tick({})

    assert m.ball.held_by is not None
    assert m.ball.pos == m.ball.held_by.pos
