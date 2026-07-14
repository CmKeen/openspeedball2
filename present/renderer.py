"""Pitch/player/ball rendering. Reads match state only — no game logic.

Camera follows the ball holder (or the free ball) the way REF's
CenterScreenOnEntity does: vertical scroll only, since the pitch is exactly
window-wide (640px) at 1:1 scale. Falls back to primitive shapes; if
assets/sprites/ is present (Task 11), sprites are blitted instead.
"""
from __future__ import annotations

from pathlib import Path

import pygame

from sim.match import Match, player_id
from sim.vec import Vec

BG_COLOR = (18, 60, 28)
LINE_COLOR = (230, 230, 230)
GOAL_COLOR = (255, 255, 255)
BANK_DIM = (150, 130, 20)
BANK_LIT = (255, 220, 0)
TEAM1_COLOR = (70, 130, 180)   # steel blue
TEAM2_COLOR = (220, 20, 60)    # crimson
GK_RING_COLOR = (255, 255, 255)
CONTROLLED_RING_COLOR = (255, 255, 0)
BALL_COLOR = (255, 255, 255)
BALL_HELD_COLOR = (160, 160, 160)

PLAYER_RADIUS = 6
BALL_RADIUS = 4

WINDOW_W = 640
WINDOW_H = 480

_SPRITES_DIR = Path("assets/sprites")


def _load_sprites() -> dict[str, pygame.Surface] | None:
    if not _SPRITES_DIR.exists():
        return None
    try:
        sprites = {
            "t1": pygame.image.load(str(_SPRITES_DIR / "player_t1.png")).convert_alpha(),
            "t2": pygame.image.load(str(_SPRITES_DIR / "player_t2.png")).convert_alpha(),
            "ball": pygame.image.load(str(_SPRITES_DIR / "ball.png")).convert_alpha(),
        }
        return sprites
    except (pygame.error, FileNotFoundError, OSError):
        return None


_sprites_cache: dict[str, pygame.Surface] | None = None
_sprites_loaded = False


def _sprites() -> dict[str, pygame.Surface] | None:
    global _sprites_cache, _sprites_loaded
    if not _sprites_loaded:
        _sprites_cache = _load_sprites()
        _sprites_loaded = True
    return _sprites_cache


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _camera(match: Match, controlled_pid: int) -> tuple[int, int]:
    holder = match.ball.held_by
    focus: Vec = holder.pos if holder is not None else match.ball.pos
    arena = match.cfg.arena
    camera_x = _clamp(focus.x - WINDOW_W // 2, 0, arena["width"] - WINDOW_W)
    camera_y = _clamp(focus.y - WINDOW_H // 2, 0, arena["height"] - WINDOW_H)
    return camera_x, camera_y


def _draw_pitch(screen: pygame.Surface, match: Match, cam_x: int, cam_y: int) -> None:
    arena = match.cfg.arena
    screen.fill(BG_COLOR)

    # Center line + circle.
    center_y = arena["height"] // 2 - cam_y
    if -50 <= center_y <= WINDOW_H + 50:
        pygame.draw.line(screen, LINE_COLOR, (0, center_y), (WINDOW_W, center_y), 2)
    center_x = arena["width"] // 2 - cam_x
    pygame.draw.circle(screen, LINE_COLOR, (center_x, center_y), 60, 2)

    # Goal mouths (top and bottom).
    x_min = arena["goal_mouth_x_min"] - cam_x
    x_max = arena["goal_mouth_x_max"] - cam_x
    depth = arena["goal_depth"]
    top_y = 0 - cam_y
    bottom_y = arena["height"] - cam_y
    pygame.draw.rect(screen, GOAL_COLOR, (x_min, top_y, x_max - x_min, depth), 2)
    pygame.draw.rect(screen, GOAL_COLOR,
                     (x_min, bottom_y - depth, x_max - x_min, depth), 2)

    # Multiplier banks.
    lit1 = match.score.multiplier_team1_ticks > 0
    lit2 = match.score.multiplier_team2_ticks > 0
    for bank in arena["multiplier_banks"]:
        lit = lit1 if bank["team_side"] == 1 else lit2
        color = BANK_LIT if lit else BANK_DIM
        rect = pygame.Rect(
            bank["x_min"] - cam_x, bank["y_min"] - cam_y,
            bank["x_max"] - bank["x_min"], bank["y_max"] - bank["y_min"],
        )
        pygame.draw.rect(screen, color, rect)


def _draw_players(screen: pygame.Surface, match: Match, controlled_pid: int,
                   cam_x: int, cam_y: int) -> None:
    sprites = _sprites()
    for p in match.all_players():
        sx = p.pos.x - cam_x
        sy = p.pos.y - cam_y
        pid = player_id(p.team, p.index)
        falling = p.falling_ticks > 0

        if sprites is not None:
            img = sprites["t1"] if p.team == 1 else sprites["t2"]
            rect = img.get_rect(center=(sx, sy))
            screen.blit(img, rect)
        else:
            color = TEAM1_COLOR if p.team == 1 else TEAM2_COLOR
            if falling:
                ellipse_rect = pygame.Rect(0, 0, PLAYER_RADIUS * 2 + 4, PLAYER_RADIUS)
                ellipse_rect.center = (sx, sy)
                pygame.draw.ellipse(screen, color, ellipse_rect)
            else:
                pygame.draw.circle(screen, color, (sx, sy), PLAYER_RADIUS)

        if p.position == 0:
            pygame.draw.circle(screen, GK_RING_COLOR, (sx, sy), PLAYER_RADIUS + 2, 2)
        if pid == controlled_pid:
            pygame.draw.circle(screen, CONTROLLED_RING_COLOR, (sx, sy), PLAYER_RADIUS + 4, 2)


def _draw_ball(screen: pygame.Surface, match: Match, cam_x: int, cam_y: int) -> None:
    ball = match.ball
    sx = ball.pos.x - cam_x
    sy = ball.pos.y - cam_y
    sprites = _sprites()
    if sprites is not None:
        img = sprites["ball"]
        rect = img.get_rect(center=(sx, sy))
        screen.blit(img, rect)
    else:
        color = BALL_HELD_COLOR if ball.held_by is not None else BALL_COLOR
        pygame.draw.circle(screen, color, (sx, sy), BALL_RADIUS)


def draw_frame(screen: pygame.Surface, match: Match, controlled_pid: int, font) -> None:
    cam_x, cam_y = _camera(match, controlled_pid)
    _draw_pitch(screen, match, cam_x, cam_y)
    _draw_players(screen, match, controlled_pid, cam_x, cam_y)
    _draw_ball(screen, match, cam_x, cam_y)
