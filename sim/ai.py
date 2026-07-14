"""Baseline CPU AI using the original's decision inputs.

Each decide_* function mirrors a behavior family in the reference AI
(REF Player.cs Think dispatch). Replace individual functions with exact
translations during fidelity passes — keep signatures stable.
"""
from __future__ import annotations

from sim.input import InputState
from sim.match import Match, player_id
from sim.player import PlayerSim
from sim.vec import Vec, dir_towards


def _sort_key(p: PlayerSim, ref: Vec):
    return (p.pos.chebyshev(ref), p.team, p.index)


def _closest_ids(players: list[PlayerSim], ref: Vec, n: int) -> set[int]:
    ranked = sorted(players, key=lambda q: _sort_key(q, ref))
    return {id(q) for q in ranked[:n]}


def _move_to(p: PlayerSim, target: Vec) -> InputState:
    if target == p.pos:
        return InputState(dir=None)
    return InputState(dir=dir_towards(p.pos, target))


def _opp_goal_center(match: Match, p: PlayerSim) -> Vec:
    height = match.cfg.arena["height"]
    depth = match.cfg.arena["goal_depth"]
    goal_line_y = depth if p.team == 1 else height - depth
    return Vec(320, goal_line_y)


def decide_goalkeeper(match: Match, p: PlayerSim) -> InputState:
    ball = match.ball
    if ball.held_by is p:
        teammates = [q for q in match.all_players()
                     if q.team == p.team and q.position == 2]
        if teammates:
            target_p = min(teammates, key=lambda q: _sort_key(q, p.pos))
            return InputState(dir=dir_towards(p.pos, target_p.pos), action_a=True)
        return InputState(dir=None)

    if ball.held_by is None and p.pos.chebyshev(ball.pos) <= 60:
        return _move_to(p, ball.pos)

    arena = match.cfg.arena
    margin = arena["wall_margin_player"]
    lo = max(margin, arena["goal_mouth_x_min"] - 16)
    hi = min(arena["width"] - margin, arena["goal_mouth_x_max"] + 16)
    target_x = min(max(ball.pos.x, lo), hi)
    target_y = p.home.y
    return _move_to(p, Vec(target_x, target_y))


def decide_chase(match: Match, p: PlayerSim) -> InputState:
    return _move_to(p, match.ball.pos)


def decide_support(match: Match, p: PlayerSim) -> InputState:
    anchor = p.home
    ball = match.ball.pos
    delta = ball - anchor
    target = anchor + Vec(delta.x // 4, delta.y // 4)
    return _move_to(p, target)


def decide_carry(match: Match, p: PlayerSim) -> InputState:
    phy = match.cfg.physics
    goal_center = _opp_goal_center(match, p)

    dist = p.pos.chebyshev(goal_center)
    if dist > phy["ai_shot_range"]:
        return _move_to(p, goal_center)

    if not match._ai_possession_rolled:
        roll = match.rng.next_byte()
        match._ai_possession_rolled = True
        if roll < p.stats["int"]:
            candidates = []
            for t in match.all_players():
                if t is p or t.team != p.team:
                    continue
                if t.pos.chebyshev(goal_center) >= p.pos.chebyshev(goal_center):
                    continue
                marked = any(o.team != p.team
                             and o.pos.chebyshev(t.pos) <= phy["ai_unmarked_radius"]
                             for o in match.all_players())
                if not marked:
                    candidates.append(t)
            if candidates:
                target_p = min(candidates, key=lambda q: _sort_key(q, goal_center))
                return InputState(dir=dir_towards(p.pos, target_p.pos), action_a=True)

    return InputState(dir=dir_towards(p.pos, goal_center), action_b=True)


def decide_defend(match: Match, p: PlayerSim, holder: PlayerSim) -> InputState:
    phy = match.cfg.physics
    dist = p.pos.chebyshev(holder.pos)
    if dist <= phy["tackle_range"]:
        return InputState(dir=dir_towards(p.pos, holder.pos), action_a=True)
    return _move_to(p, holder.pos)


def _outfield(players: list[PlayerSim]) -> list[PlayerSim]:
    return [p for p in players if p.position != 0]


def _decide(match: Match, p: PlayerSim) -> InputState:
    if p.position == 0:
        return decide_goalkeeper(match, p)

    holder = match.ball.held_by
    team_players = match.players_team1 if p.team == 1 else match.players_team2
    outfield = _outfield(team_players)

    if holder is None:
        closest = _closest_ids(outfield, match.ball.pos, 2)
        if id(p) in closest:
            return decide_chase(match, p)
        return decide_support(match, p)

    if holder.team == p.team:
        if holder is p:
            return decide_carry(match, p)
        return decide_support(match, p)

    # opponent holds the ball
    closest = _closest_ids(outfield, holder.pos, 2)
    if id(p) in closest:
        return decide_defend(match, p, holder)
    return decide_support(match, p)


def compute_ai_inputs(match: Match, controlled: set[int]) -> dict[int, InputState]:
    out: dict[int, InputState] = {}
    for p in match.all_players():
        pid = player_id(p.team, p.index)
        if pid in controlled:
            continue
        out[pid] = _decide(match, p)
    return out
