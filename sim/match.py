"""Match orchestration: builds two teams, runs fixed ticks, tracks score.

Tick order translated from REF Match.cs Update (see docs/spec/mechanics.md):
1. update_ball_velocity
2. check_multiplier_banks + tick_multipliers; check_bounce_domes;
   check_electrobounces + tick_electrobounce_flash; check_star_banks
3. (distance-to-ball is recomputed implicitly via pickup ordering below)
4. resolve intents: movement for all; action_a/action_b per holder state;
   pickups for a free ball, closest eligible player first
5. check_goal -> award_goal, reset_to_kickoff
6. move_and_bounce ball then all players
7. if ball held: pin ball.pos to holder, set last_thrower_team on throw
8. tick_count += 1; clock_ticks -= 1 while running
"""
from __future__ import annotations

from sim.actions import attempt_tackle, throw, try_pickup
from sim.config import GameConfig
from sim.entities import Ball, move_and_bounce, update_ball_velocity
from sim.furniture import (FurnitureState, check_bounce_domes,
                           check_electrobounces, check_star_banks,
                           tick_electrobounce_flash)
from sim.input import IDLE, InputState
from sim.player import PlayerSim, apply_movement
from sim.rng import Sb2Rng
from sim.scoring import (ScoreState, award_goal, check_goal,
                         check_multiplier_banks, tick_multipliers)
from sim.vec import Vec


def player_id(team: int, idx: int) -> int:
    return team * 100 + idx


# Row Y offsets from the team's own goal mouth, and row X anchors, per
# position (0 GK, 1 DEF, 2 MID, 3 ATT). Concrete numbers (authoritative
# override of a pitch-fraction formula): computed for team 1 (defends the
# bottom goal, y = arena height); mirrored for team 2 via mirror_y.
_ROW_Y_TEAM1 = {0: 1112, 1: 920, 2: 720, 3: 500}
_ROW_XS = {1: (200, 440), 2: (140, 320, 500), 3: (200, 320, 440)}


class Match:
    def __init__(self, config: GameConfig, seed: tuple[int, int] | None = None):
        self.cfg = config
        self.rng = Sb2Rng(*seed) if seed else Sb2Rng()
        self.score = ScoreState()
        self.furniture = FurnitureState()
        self.tick_count = 0
        self.clock_ticks = config.scoring["leg_duration_ticks"]
        self.ball_speed_ref = [0]
        self.last_thrower_team = 0
        # Set True only on a tick where a goal is actually scored (as
        # opposed to a furniture bonus like a dome/star/multiplier award,
        # which also changes score but isn't a kickoff-worthy event).
        self.goal_scored = False
        self.ball = Ball(pos=Vec(*config.arena["kickoff_center"]))
        self.players_team1 = self._build_team(1)
        self.players_team2 = self._build_team(2)
        self._prev_holder = None
        self._ai_possession_rolled = False
        self.reset_to_kickoff(possession_team=0)

    def _build_team(self, team: int) -> list[PlayerSim]:
        """Build the 9 PlayerSims for `team` from teams.json, in list order
        (GK, DEF x2, MID x3, ATT x3). Team 1 defends the bottom goal (large
        y); team 2 defends the top goal (small y) and is a vertical mirror
        of team 1's anchors: mirror_y(y) = arena height - y.
        """
        arena = self.cfg.arena
        height = arena["height"]
        center_x = arena["width"] // 2
        roster = self.cfg.teams["teams"][team - 1]["players"]

        def_i = 0
        mid_i = 0
        att_i = 0
        players: list[PlayerSim] = []
        for idx, pdata in enumerate(roster):
            pos = pdata["position"]
            if pos == 0:
                x, y = center_x, _ROW_Y_TEAM1[0]
            elif pos == 1:
                x = _ROW_XS[1][def_i]
                y = _ROW_Y_TEAM1[1]
                def_i += 1
            elif pos == 2:
                x = _ROW_XS[2][mid_i]
                y = _ROW_Y_TEAM1[2]
                mid_i += 1
            else:
                x = _ROW_XS[3][att_i]
                y = _ROW_Y_TEAM1[3]
                att_i += 1

            if team == 2:
                y = height - y

            home = Vec(x, y)
            stats = {k: v for k, v in pdata.items()
                     if k not in ("name", "position")}
            players.append(PlayerSim(
                pos=home, index=idx, team=team, position=pos,
                stats=stats, home=home,
            ))
        return players

    def all_players(self) -> list[PlayerSim]:
        return self.players_team1 + self.players_team2

    def reset_to_kickoff(self, possession_team: int) -> None:
        for p in self.all_players():
            p.pos = p.home
            p.vel = Vec(0, 0)
            p.dir = 0 if p.team == 1 else 4
            p.falling_ticks = 0
            p.sliding_ticks = 0
            p.knock_vel = Vec(0, 0)

        self.ball.pos = Vec(*self.cfg.arena["kickoff_center"])
        self.ball.vel = Vec(0, 0)
        self.ball.bounce_timer = 0
        self.ball.held_by = None
        self.ball.in_bank = False
        self.ball.last_thrower = None

        if possession_team in (1, 2):
            team_players = (self.players_team1 if possession_team == 1
                            else self.players_team2)
            holder = team_players[4]  # central MID (x=320)
            self.ball.held_by = holder
            self.ball.pos = holder.pos

        self.ball_speed_ref[0] = 0
        self.last_thrower_team = 0

    def tick(self, inputs: dict[int, InputState]) -> None:
        arena, phy, sco = self.cfg.arena, self.cfg.physics, self.cfg.scoring
        self.goal_scored = False
        update_ball_velocity(self.ball, phy, self.ball_speed_ref)
        check_multiplier_banks(self.ball, arena, sco, self.score,
                               self.last_thrower_team)
        tick_multipliers(self.score)
        check_bounce_domes(self.ball, arena, phy, self.last_thrower_team,
                           self.score, sco)
        check_electrobounces(self.ball, arena, phy, self.furniture)
        tick_electrobounce_flash(self.furniture)
        check_star_banks(self.ball, arena, sco, self.furniture, self.score,
                         self.last_thrower_team)

        for p in self.all_players():
            inp = inputs.get(player_id(p.team, p.index), IDLE)
            apply_movement(p, inp, phy)
            if inp.action_a or inp.action_b:
                self._resolve_action(p, inp, phy)

        # pickups: closest eligible player first (deterministic ordering)
        if self.ball.held_by is None:
            for p in sorted(self.all_players(),
                            key=lambda q: (q.pos.chebyshev(self.ball.pos),
                                           q.team, q.index)):
                if try_pickup(self.ball, p, phy):
                    break

        goal = check_goal(self.ball, arena)
        if goal:
            award_goal(self.score, goal, sco)
            self.goal_scored = True
            self.reset_to_kickoff(possession_team=2 if goal == 1 else 1)
        else:
            move_and_bounce(self.ball, arena, arena["wall_margin_ball"],
                            is_ball=True)
            for p in self.all_players():
                move_and_bounce(p, arena, arena["wall_margin_player"],
                                is_ball=False)
            if self.ball.held_by is not None:
                self.ball.pos = self.ball.held_by.pos
                self.ball.vel = Vec(0, 0)

        self.tick_count += 1
        if self.clock_ticks > 0:
            self.clock_ticks -= 1

        if self.ball.held_by is not self._prev_holder:
            self._ai_possession_rolled = False
            self._prev_holder = self.ball.held_by

    def tick_with_ai(self, human_inputs: dict[int, InputState]) -> None:
        # Lockstep invariant: the AI must produce identical inputs on every
        # peer for a given match state, since it consumes match rng here
        # (same stream all peers replay) rather than any local-only source.
        from sim.ai import compute_ai_inputs  # local import: no cycle at module load
        ai = compute_ai_inputs(self, set(human_inputs))
        self.tick(ai | human_inputs)

    def _resolve_action(self, p: PlayerSim, inp: InputState, phy: dict) -> None:
        holder = self.ball.held_by
        if holder is p:
            self.last_thrower_team = p.team
            if inp.action_a and inp.action_b:
                # Single-button human throw: no separate pass/shoot input
                # exists, so pick the same way the AI's decide_carry does --
                # shoot once within shot range of the opponent's goal,
                # otherwise a softer pass. Without this, a raw action_b=True
                # always fires, and pass_speed becomes unreachable for humans.
                shot = p.pos.chebyshev(self._opp_goal_center(p)) <= phy["ai_shot_range"]
            else:
                shot = inp.action_b
            throw(self.ball, p, phy, shot=shot, ball_speed_ref=self.ball_speed_ref)
            return
        if inp.action_b and p.sliding_ticks == 0 and p.falling_ticks == 0:
            p.sliding_ticks = phy["slide_ticks"]
        if inp.action_a and holder is not None and holder.team != p.team:
            attempt_tackle(p, [holder], self.ball, self.rng, phy)

    def _opp_goal_center(self, p: PlayerSim) -> Vec:
        arena = self.cfg.arena
        depth = arena["goal_depth"]
        goal_line_y = depth if p.team == 1 else arena["height"] - depth
        goal_x = (arena["goal_mouth_x_min"] + arena["goal_mouth_x_max"]) // 2
        return Vec(goal_x, goal_line_y)

    @property
    def is_over(self) -> bool:
        return self.clock_ticks <= 0

    def state_hash(self) -> int:
        acc = 0

        def mix(v: int) -> None:
            nonlocal acc
            acc = (acc * 1000003 + (v & 0xFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF

        mix(self.tick_count)
        for v in (self.ball.pos.x, self.ball.pos.y,
                  self.ball.vel.x, self.ball.vel.y, self.ball.bounce_timer):
            mix(v)
        holder = self.ball.held_by
        mix(player_id(holder.team, holder.index) if holder is not None else 0)
        mix(int(self.ball.in_bank))
        for p in self.all_players():
            for v in (p.pos.x, p.pos.y, p.vel.x, p.vel.y, p.dir,
                      p.falling_ticks, p.sliding_ticks,
                      p.knock_vel.x, p.knock_vel.y):
                mix(v)
            for key in ("health", "agr", "att", "def", "spd",
                       "thr", "pow", "sta", "int"):
                mix(p.stats[key])
        for v in (self.score.score_team1, self.score.score_team2,
                  self.score.multiplier_team1_ticks,
                  self.score.multiplier_team2_ticks,
                  self.furniture.lit_stars_team1,
                  self.furniture.lit_stars_team2,
                  self.furniture.electrobounce_flash_ticks,
                  int(self.furniture.electrobounce_cooldown),
                  self.rng.a, self.rng.b,
                  self.clock_ticks, self.last_thrower_team):
            mix(v)
        return acc
