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


_POSITION_LOOKAHEAD_TABLE = (0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2)

_CFWD_SUPPORT_LOOKUP = (
    ((208, 208), (208, 176), (224, 160), (240, 144), (256, 128), (272, 112), (240, 144), (272, 112), (352, 96)),
    ((320, 80), (208, 208), (208, 176), (224, 160), (288, 80), (304, 80), (320, 80), (400, 80), (400, 80)),
    ((256, 112), (272, 112), (288, 112), (304, 112), (336, 112), (352, 112), (352, 112), (352, 112), (256, 64)),
    ((288, 144), (304, 144), (336, 144), (368, 144), (256, 48), (352, 144), (240, 64), (224, 96), (384, 64)),
    ((336, 176), (368, 176), (272, 48), (272, 48), (352, 176), (208, 96), (240, 64), (384, 64), (400, 80)),
    ((256, 64), (272, 48), (272, 48), (288, 208), (288, 208), (208, 96), (240, 64), (400, 80), (416, 96)),
)

_WING_SUPPORT_LOOKUP = (
    ((160, 160), (176, 144), (192, 128), (208, 112), (176, 144), (208, 112), (432, 208), (208, 112), (432, 176)),
    ((144, 176), (160, 160), (176, 144), (192, 128), (176, 144), (432, 208), (432, 192), (352, 80), (416, 80)),
    ((320, 112), (320, 112), (320, 112), (320, 112), (432, 208), (432, 192), (192, 112), (192, 112), (192, 112)),
    ((320, 144), (320, 144), (336, 144), (368, 144), (432, 192), (208, 96), (176, 144), (208, 144), (208, 144)),
    ((320, 176), (320, 176), (432, 208), (432, 192), (176, 128), (320, 96), (192, 128), (208, 112), (208, 176)),
    ((432, 208), (432, 208), (432, 192), (352, 208), (176, 144), (208, 96), (176, 144), (192, 128), (208, 112)),
)


def _sort_key(p: PlayerSim, ref: Vec):
    return (p.pos.chebyshev(ref), p.team, p.index)


def _ai_group(match: Match, p: PlayerSim) -> int:
    if p.position != 3:
        return p.position
    return 3 if p.home.x == match.cfg.arena["width"] // 2 else 4


def _pass_thresholds(match: Match, p: PlayerSim) -> tuple[int, ...]:
    # Amiga REF sub_DF2E() (attackers) / sub_DBE8() (everyone else): the
    # cascade width differs by group -- attackers and defenders each try two
    # thresholds, midfielders cascade one level further to a third.
    group = _ai_group(match, p)
    if group >= 3:
        return (3, 2)
    if group == 2:
        return (3, 2, 1)
    if group == 1:
        return (2, 1)
    return (2, 1)


def _support_anchor(match: Match, team: int) -> PlayerSim | None:
    team_players = match.players_team1 if team == 1 else match.players_team2
    return team_players[0] if team_players else None


def _choose_pass_target(match: Match, p: PlayerSim, goal_center: Vec) -> PlayerSim | None:
    # Amiga REF sub_DBE8()/sub_DF2E(): the group-threshold cascade and the
    # `int * 2` observe distance (sub_DE7E_CalcDistanceUnkFromInt) are ported
    # faithfully. The candidate-selection criteria below are a deliberate
    # approximation, not a byte-exact port: the REF picks the *closest-to-
    # the-ball* eligible teammate, filtered by whether the candidate's
    # direction back to the passer matches either of the two nearest
    # opponents' marking directions (sub_E05C) -- a per-player "who's
    # currently marking me" direction pair this sim doesn't track. This
    # instead picks the teammate closest to the opponent's goal among those
    # not within a fixed unmarked radius. Revisit if defenders and
    # midfielders start passing to worse-supported targets than the REF.
    phy = match.cfg.physics
    observe_distance = p.stats["int"] * 2

    for threshold in _pass_thresholds(match, p):
        candidates = []
        for t in match.all_players():
            if t is p or t.team != p.team:
                continue
            if _ai_group(match, t) < threshold:
                continue
            if p.pos.chebyshev(t.pos) > observe_distance:
                continue
            if t.pos.chebyshev(goal_center) >= p.pos.chebyshev(goal_center):
                continue
            marked = any(o.team != p.team
                         and o.pos.chebyshev(t.pos) <= phy["ai_unmarked_radius"]
                         for o in match.all_players())
            if marked:
                continue
            candidates.append(t)
        if candidates:
            return min(candidates, key=lambda q: _sort_key(q, goal_center))
    return None


def _reflect_axis(value: int, low: int, high: int) -> int:
    if value <= low:
        return -value + low * 2
    if value >= high:
        return -value + high * 2
    return value


def _predicted_target(match: Match, p: PlayerSim, pos: Vec, vel: Vec) -> Vec:
    # Amiga REF sub_F364(): intelligence buckets select a left-shift applied
    # to target velocity, then the point is reflected back inside the
    # playable pitch rectangle via sub_F3A2_sub_F3C4(). Verified against the
    # decompiled source: formula and reflection boundaries (32/608, 32/1120)
    # match byte-for-byte once translated from the fixed 640x1152 arena.
    int_bucket = max(0, min((p.stats["int"] - 100) // 10, len(_POSITION_LOOKAHEAD_TABLE) - 1))
    lookahead_shift = _POSITION_LOOKAHEAD_TABLE[int_bucket]
    target = Vec(
        pos.x + (vel.x << lookahead_shift),
        pos.y + (vel.y << lookahead_shift),
    )
    return Vec(
        _reflect_axis(target.x, 32, match.cfg.arena["width"] - 32),
        _reflect_axis(target.y, 32, match.cfg.arena["height"] - 32),
    )


def _attacker_lookup_target(match: Match, p: PlayerSim, holder: PlayerSim) -> Vec | None:
    # Amiga REF sub_E382(): the lookup is keyed off the ball holder's
    # *predicted* position (pos + vel). The pitch-half mirror applied going
    # into the table uses that predicted position, but the mirror applied
    # coming back out uses the holder's actual (non-predicted) position --
    # the two can disagree when the holder is near the center line.
    if _ai_group(match, p) < 3:
        return None

    width = match.cfg.arena["width"]
    height = match.cfg.arena["height"]
    predicted = Vec(holder.pos.x + holder.vel.x, holder.pos.y + holder.vel.y)
    lookup_x = predicted.x
    lookup_y = predicted.y
    mirror_x_in = lookup_x >= width // 2

    if mirror_x_in:
        lookup_x = (width - 1) - lookup_x
    if p.team == 2:
        lookup_y = (height - 1) - lookup_y

    if lookup_y >= 208:
        return None

    col = max(0, min((lookup_x - 32) // 32, 8))
    row = max(0, min((lookup_y - 32) // 32, 5))
    table = _WING_SUPPORT_LOOKUP if _ai_group(match, p) == 4 else _CFWD_SUPPORT_LOOKUP
    target_x, target_y = table[row][col]

    mirror_x_out = holder.pos.x >= width // 2
    if mirror_x_out:
        target_x = (width - 1) - target_x
    if p.team == 2:
        target_y = (height - 1) - target_y

    return Vec(target_x, target_y)


def _goalie_predicted_target(match: Match, p: PlayerSim, pos: Vec, vel: Vec) -> Vec:
    # Amiga REF get_predicted_ball_position_for_goalie(): use the same
    # intelligence-based lookahead buckets, but back off Y lookahead if the
    # prediction would run behind the keeper's defending line.
    int_bucket = max(0, min((p.stats["int"] - 100) // 10, len(_POSITION_LOOKAHEAD_TABLE) - 1))
    lookahead_shift = _POSITION_LOOKAHEAD_TABLE[int_bucket]

    target_y = pos.y
    remaining_shift = lookahead_shift
    while True:
        dy = vel.y << remaining_shift
        predicted_y = target_y + dy
        if remaining_shift == 0:
            target_y = predicted_y
            break
        if p.team == 1 and predicted_y > p.home.y:
            remaining_shift -= 1
            continue
        if p.team == 2 and predicted_y < p.home.y:
            remaining_shift -= 1
            continue
        target_y = predicted_y
        break

    return Vec(pos.x + (vel.x << remaining_shift), target_y)


def _closest_ids(players: list[PlayerSim], ref: Vec, n: int) -> set[int]:
    ranked = sorted(players, key=lambda q: _sort_key(q, ref))
    return {id(q) for q in ranked[:n]}


def _move_to(p: PlayerSim, target: Vec) -> InputState:
    if target == p.pos:
        return InputState(dir=None)
    return InputState(dir=dir_towards(p.pos, target))


def _opp_goal_center(match: Match, p: PlayerSim) -> Vec:
    return match._opp_goal_center(p)


def decide_goalkeeper(match: Match, p: PlayerSim) -> InputState:
    ball = match.ball
    if ball.held_by is p:
        teammates = [q for q in match.all_players()
                     if q.team == p.team and q.position == 2]
        if teammates:
            target_p = min(teammates, key=lambda q: _sort_key(q, p.pos))
            return InputState(dir=dir_towards(p.pos, target_p.pos), action_a=True)
        return InputState(dir=None)

    # Amiga REF sub_E61A_GoalUnk(): a loose ball close enough to lunge for is
    # grabbed directly, bypassing the goal-line-locked predicted lane below.
    if ball.held_by is None and p.pos.chebyshev(ball.pos) <= 60:
        return _move_to(p, ball.pos)

    arena = match.cfg.arena
    margin = arena["wall_margin_player"]
    lo = max(margin, arena["goal_mouth_x_min"] - 16)
    hi = min(arena["width"] - margin, arena["goal_mouth_x_max"] + 16)
    target_obj = ball.held_by if ball.held_by is not None else ball
    predicted = _goalie_predicted_target(match, p, target_obj.pos, target_obj.vel)
    target_x = min(max(predicted.x, lo), hi)
    target_y = p.home.y
    return _move_to(p, Vec(target_x, target_y))


def decide_chase(match: Match, p: PlayerSim) -> InputState:
    target = _predicted_target(match, p, match.ball.pos, match.ball.vel)
    return _move_to(p, target)


def decide_support(match: Match, p: PlayerSim) -> InputState:
    anchor = p.home
    ball = match.ball.pos
    delta = ball - anchor
    target = anchor + Vec(delta.x // 4, delta.y // 4)
    return _move_to(p, target)


def decide_team_support(match: Match, p: PlayerSim, holder: PlayerSim) -> InputState:
    if _ai_group(match, p) >= 3 and _ai_group(match, holder) >= 3:
        lookup_target = _attacker_lookup_target(match, p, holder)
        if lookup_target is not None:
            return _move_to(p, lookup_target)

    # Amiga REF sub_E218(): when a defender's teammate in a more advanced
    # position holds the ball, the defender anchors off their own team's
    # roster-index-0 player (the goalkeeper), not another defender.
    if _ai_group(match, p) == 1 and _ai_group(match, holder) >= 2:
        support_target = _support_anchor(match, p.team)
        if support_target is not None:
            return _move_to(p, support_target.pos)
    return decide_support(match, p)


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
            target_p = _choose_pass_target(match, p, goal_center)
            if target_p is not None:
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
        return decide_team_support(match, p, holder)

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
