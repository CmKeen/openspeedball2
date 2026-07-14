"""Keyboard -> InputState. Human controls the team-1 player nearest the ball
(original 'auto-switch' behavior).

Single-button controls, like the original game: Space is the one action —
throw when holding the ball, sliding tackle when not. It fires on the
key-down edge (passed in by the app's event loop) and deliberately withholds
the movement direction on that tick (dir=None), so the sim's persistent
facing decides where the throw/slide goes. Sampling the raw key state at the
press instant is what broke diagonal passes: three-key chords (two arrows +
Space) commonly drop an arrow (keyboard ghosting / key roll), collapsing the
direction to a cardinal exactly when it mattered.
"""
from __future__ import annotations

import pygame

from sim.input import InputState
from sim.match import Match, player_id

_DIR_FROM_KEYS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}


def compute_input(dx: int, dy: int, action_edge: bool) -> InputState:
    """Pure mapping from movement axes (-1/0/1 each) and the action edge."""
    if action_edge:
        return InputState(dir=None, action_a=True, action_b=True)
    return InputState(dir=_DIR_FROM_KEYS.get((dx, dy)))


def read_input(action_edge: bool) -> InputState:
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
    return compute_input(dx, dy, action_edge)


def pick_controlled_player(match: Match) -> int:
    """Team-1 outfielder nearest the ball; holder wins outright."""
    holder = match.ball.held_by
    if holder is not None and holder.team == 1:
        return player_id(1, holder.index)
    best = min((p for p in match.players_team1 if p.position != 0),
               key=lambda p: (p.pos.chebyshev(match.ball.pos), p.index))
    return player_id(1, best.index)
