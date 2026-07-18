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


def test_action_a_can_tackle_a_nearby_opponent_not_holding_the_ball():
    # REF sub_ED56_TackleCheckHit scans the whole opposing roster for anyone
    # within tackle_range -- it is not gated on that opponent holding the
    # ball. Put the ball far away (held by a third player) so only the
    # off-ball proximity check can explain a successful tackle here.
    from sim.vec import Vec

    m = Match(CFG, seed=(11, 13))
    holder = m.players_team2[0]
    victim = m.players_team2[4]
    tackler = m.players_team1[4]
    holder.pos = Vec(320, 50)
    m.ball.held_by = holder
    victim.pos = Vec(330, 600)
    tackler.pos = Vec(325, 600)

    for _ in range(50):
        m.tick({player_id(1, 4): InputState(action_a=True)})
        if victim.falling_ticks > 0:
            break

    assert victim.falling_ticks > 0
    assert m.ball.held_by is holder  # tackle target was off-ball; possession untouched


def test_kickoff_possession_pins_ball_to_holder():
    from sim.vec import Vec

    m = Match(CFG, seed=(7, 7))
    m.ball.pos = Vec(320, 10)
    m.ball.held_by = None
    m.tick({})

    assert m.ball.held_by is not None
    assert m.ball.pos == m.ball.held_by.pos


def test_throw_escapes_thrower():
    m = Match(CFG, seed=(11, 22))
    thrower = m.players_team1[4]
    m.ball.held_by = thrower
    m.ball.pos = thrower.pos
    m._prev_holder = thrower
    thrower.dir = 0  # facing open field, away from any wall

    m.tick({player_id(1, 4): InputState(dir=thrower.dir, action_a=True)})

    assert m.ball.held_by is not thrower
    assert m.ball.held_by is None

    positions = []
    for _ in range(5):
        m.tick({})
        positions.append(m.ball.pos)
    assert len(set(positions)) > 1


def test_carried_ball_does_not_score_thrown_ball_does():
    from sim.vec import Vec

    m = Match(CFG, seed=(5, 6))
    holder = m.players_team1[4]
    holder.pos = Vec(320, 10)
    m.ball.held_by = holder
    m.ball.pos = holder.pos

    before1, before2 = m.score.score_team1, m.score.score_team2
    m.tick({})
    assert (m.score.score_team1, m.score.score_team2) == (before1, before2)

    m2 = Match(CFG, seed=(5, 6))
    m2.ball.held_by = None
    m2.ball.pos = Vec(320, 10)
    m2.ball.vel = Vec(0, -4)
    m2.tick({})
    assert m2.score.score_team1 == CFG.scoring["goal_points"]


def test_bounce_dome_integration_via_tick():
    m = Match(CFG, seed=(5, 5))
    dome = CFG.arena["bounce_domes"][0]
    from sim.vec import Vec
    m.ball.pos = Vec(dome["pos"][0], dome["pos"][1] - dome["radius"])
    m.ball.vel = Vec(0, -4)
    m.ball.held_by = None
    m.last_thrower_team = 1
    score_before = m.score.score_team1
    m.tick({})
    assert m.score.score_team1 == score_before + CFG.scoring["dome_bonus_points"]


def test_star_bank_integration_via_tick():
    m = Match(CFG, seed=(6, 6))
    bank = CFG.arena["star_banks"][0]
    from sim.vec import Vec
    y = bank["y_min"] + 1
    m.ball.pos = Vec(bank["x_max"] - 2, y)
    m.ball.vel = Vec(-4, 0)
    m.ball.held_by = None
    m.last_thrower_team = 1
    m.tick({})
    assert m.furniture.lit_stars_team1 == 0b00001
    assert m.score.score_team1 == CFG.scoring["star_bonus_points"]


def test_electrobounce_integration_via_tick():
    m = Match(CFG, seed=(9, 9))
    left, right = CFG.arena["electrobounces"]
    from sim.vec import Vec
    m.ball.pos = Vec(*left["pos"])
    m.ball.vel = Vec(-4, 0)
    m.ball.held_by = None
    m.tick({})
    speed = CFG.physics["electrobounce_speed"]
    assert m.ball.pos.x == right["pos"][0] - speed
    assert m.furniture.electrobounce_flash_ticks == 1  # set to 2, ticked once


def test_electrobounce_does_not_ping_pong_across_ticks():
    m = Match(CFG, seed=(9, 9))
    left, right = CFG.arena["electrobounces"]
    from sim.vec import Vec
    m.ball.pos = Vec(*left["pos"])
    m.ball.vel = Vec(-4, 0)
    m.ball.held_by = None
    for _ in range(20):
        m.tick({})
    # A single crossing, not an infinite left<->right bounce: the ball
    # should settle on the right side of the pitch, not oscillate back
    # to the left plate's x.
    assert m.ball.pos.x > (left["pos"][0] + right["pos"][0]) // 2


def test_state_hash_reflects_furniture_state():
    m1 = Match(CFG, seed=(3, 3))
    m2 = Match(CFG, seed=(3, 3))
    assert m1.state_hash() == m2.state_hash()
    m1.furniture.lit_stars_team1 = 0b00001
    assert m1.state_hash() != m2.state_hash()
