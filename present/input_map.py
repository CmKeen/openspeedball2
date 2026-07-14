"""Keyboard -> InputState. Human controls the team-1 player nearest the ball
(original 'auto-switch' behavior); manual switch on Tab."""
from __future__ import annotations

import pygame

from sim.input import InputState
from sim.match import Match, player_id

_DIR_FROM_KEYS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}


def read_input() -> InputState | None:
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
    d = _DIR_FROM_KEYS.get((dx, dy))
    return InputState(dir=d,
                      action_a=keys[pygame.K_SPACE],
                      action_b=keys[pygame.K_LSHIFT])


def pick_controlled_player(match: Match) -> int:
    """Team-1 outfielder nearest the ball; holder wins outright."""
    holder = match.ball.held_by
    if holder is not None and holder.team == 1:
        return player_id(1, holder.index)
    best = min((p for p in match.players_team1 if p.position != 0),
               key=lambda p: (p.pos.chebyshev(match.ball.pos), p.index))
    return player_id(1, best.index)
