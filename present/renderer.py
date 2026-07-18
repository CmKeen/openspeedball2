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
from sim.vec import DIR_VECTORS, Vec

BG_COLOR = (18, 60, 28)
LINE_COLOR = (230, 230, 230)
GOAL_COLOR = (255, 255, 255)
BANK_DIM = (150, 130, 20)
BANK_LIT = (255, 220, 0)
DOME_COLOR = (180, 180, 190)
ELECTRO_DIM = (0, 110, 130)
ELECTRO_LIT = (0, 220, 255)
TEAM1_COLOR = (70, 130, 180)   # steel blue
TEAM2_COLOR = (220, 20, 60)    # crimson
GK_RING_COLOR = (255, 255, 255)
CONTROLLED_RING_COLOR = (255, 255, 0)
BALL_COLOR = (255, 255, 255)
BALL_HELD_COLOR = (160, 160, 160)

PLAYER_RADIUS = 6
BALL_RADIUS = 4
FACING_COLOR = (20, 20, 20)
FACING_LEN = PLAYER_RADIUS + 5
# tools/crop_amiga_sprites.py crops ball_arc.png as a 7-frame vertical strip
# from REF's real ball bank (Entity.cs Draw: pGfx == 0x193EA ->
# BankEnum.Entities), a 16x16-per-frame sheet distinct from the player
# sheet -- so each frame is already correctly proportioned (half a player's
# 32x32), no baseline scale needed.
#
# Those 7 frames are one full bounce cycle: frame 0 is the ball resting on
# the ground (its drop shadow merged directly beneath it); 1-3 show it
# rising, shrinking slightly as the shadow separates with a growing gap
# (frame 3 is the peak -- smallest ball, biggest gap); 4-6 show it falling
# back, growing again as the shadow gap closes, landing at frame 6. This is
# the original's actual fake-height trick (ball shrinks and casts a
# separating shadow when elevated -- not a uniform scale-up) and matches
# Player.cs sub_D520/sub_D672's spriteIndex >2 needs-a-jump-to-catch cutoff
# (only frames 0-2, near the start of the rise, are catchable normally).
# We drive frame selection from the existing bounce_timer countdown, purely
# in the presentation layer so it can't affect sim determinism.
BALL_ARC_FRAME_SIZE = 16
BALL_ARC_FRAME_COUNT = 7
# REF (`Match.cs` MoveBallPlayersMedicsHandleWallsAndBounce) never draws the
# held ball at full size in the player's center -- it offsets it to a small
# hand position derived from the holder's own sprite frame (GetBallDeltasXY).
# We approximate that hand offset/size without porting the per-frame table.
BALL_HELD_SCALE = 0.6
BALL_HAND_OFFSET = PLAYER_RADIUS
# Primitive-shape fallback (no assets/sprites/) has no frames to select
# between, so it keeps a continuous size dip approximating the same arc.
BALL_PRIMITIVE_TROUGH_SCALE = 0.6

WINDOW_W = 640
WINDOW_H = 480

_SPRITES_DIR = Path("assets/sprites")


def _tint(img: pygame.Surface, color: tuple[int, int, int]) -> pygame.Surface:
    # Real extracted sprites (tools/crop_amiga_sprites.py) don't carry the
    # original's runtime per-team palette swap, so both teams' raw pixels
    # come out looking identical. Multiply-tint here guarantees team1/team2
    # stay visually distinct regardless of the source sprite's own colors.
    tinted = img.copy()
    tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


def _slice_ball_arc(strip: pygame.Surface) -> list[pygame.Surface]:
    fs = BALL_ARC_FRAME_SIZE
    return [strip.subsurface((0, i * fs, fs, fs)).copy()
            for i in range(BALL_ARC_FRAME_COUNT)]


def _load_sprites() -> dict[str, object] | None:
    if not _SPRITES_DIR.exists():
        return None
    try:
        t1_raw = pygame.image.load(str(_SPRITES_DIR / "player_t1.png")).convert_alpha()
        t2_raw = pygame.image.load(str(_SPRITES_DIR / "player_t2.png")).convert_alpha()
        ball_strip = pygame.image.load(str(_SPRITES_DIR / "ball_arc.png")).convert_alpha()
        sprites = {
            "t1": _tint(t1_raw, TEAM1_COLOR),
            "t2": _tint(t2_raw, TEAM2_COLOR),
            "ball_arc": _slice_ball_arc(ball_strip),
        }
        return sprites
    except (pygame.error, FileNotFoundError, OSError):
        return None


_sprites_cache: dict[str, object] | None = None
_sprites_loaded = False


def _sprites() -> dict[str, object] | None:
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

    # Bounce domes.
    for dome in arena["bounce_domes"]:
        cx = dome["pos"][0] - cam_x
        cy = dome["pos"][1] - cam_y
        pygame.draw.circle(screen, DOME_COLOR, (cx, cy), dome["radius"])

    # Electrobounces.
    flashing = match.furniture.electrobounce_flash_ticks > 0
    for plate in arena["electrobounces"]:
        color = ELECTRO_LIT if flashing else ELECTRO_DIM
        px = plate["pos"][0] - cam_x
        py = plate["pos"][1] - cam_y
        points = [(px, py - 8), (px + 8, py), (px, py + 8), (px - 8, py)]
        pygame.draw.polygon(screen, color, points)

    # Star banks.
    for bank in arena["star_banks"]:
        lit_mask = (match.furniture.lit_stars_team1 if bank["team"] == 1
                   else match.furniture.lit_stars_team2)
        band_height = (bank["y_max"] - bank["y_min"]) // bank["count"]
        for i in range(bank["count"]):
            lit = bool(lit_mask & (1 << i))
            color = BANK_LIT if lit else BANK_DIM
            y0 = bank["y_min"] + i * band_height
            rect = pygame.Rect(
                bank["x_min"] - cam_x, y0 - cam_y,
                bank["x_max"] - bank["x_min"], band_height - 2,
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

        if not falling:
            step = DIR_VECTORS[p.dir]
            tip = (sx + step.x * FACING_LEN, sy + step.y * FACING_LEN)
            pygame.draw.line(screen, FACING_COLOR, (sx, sy), tip, 2)

        if p.position == 0:
            pygame.draw.circle(screen, GK_RING_COLOR, (sx, sy), PLAYER_RADIUS + 2, 2)
        if pid == controlled_pid:
            pygame.draw.circle(screen, CONTROLLED_RING_COLOR, (sx, sy), PLAYER_RADIUS + 4, 2)


def _ball_arc_progress(match: Match) -> float:
    ball = match.ball
    if ball.bounce_timer <= 0:
        return 0.0
    total = match.cfg.physics["throw_bounce_timer"]
    if total <= 0:
        return 0.0
    progress = 1.0 - (ball.bounce_timer / total)
    return max(0.0, min(1.0, progress))


def _ball_arc_frame_index(match: Match) -> int:
    # Frames 0-6 already encode the whole ground -> peak -> ground cycle in
    # order (see BALL_ARC_FRAME_COUNT comment above), so progress maps to
    # frame index directly -- no separate up/down split needed.
    idx = round(_ball_arc_progress(match) * (BALL_ARC_FRAME_COUNT - 1))
    return max(0, min(BALL_ARC_FRAME_COUNT - 1, idx))


def _primitive_ball_scale(match: Match) -> float:
    progress = _ball_arc_progress(match)
    return 1.0 - (1.0 - BALL_PRIMITIVE_TROUGH_SCALE) * 4 * progress * (1 - progress)


def _draw_ball(screen: pygame.Surface, match: Match, cam_x: int, cam_y: int) -> None:
    ball = match.ball
    held = ball.held_by is not None
    if held:
        step = DIR_VECTORS[ball.held_by.dir]
        sx = ball.pos.x + step.x * BALL_HAND_OFFSET - cam_x
        sy = ball.pos.y + step.y * BALL_HAND_OFFSET - cam_y
    else:
        sx = ball.pos.x - cam_x
        sy = ball.pos.y - cam_y
    sprites = _sprites()
    if sprites is not None:
        arc = sprites["ball_arc"]
        img = arc[0] if held else arc[_ball_arc_frame_index(match)]
        if held and BALL_HELD_SCALE != 1.0:
            w, h = img.get_size()
            img = pygame.transform.smoothscale(img, (max(1, round(w * BALL_HELD_SCALE)),
                                                      max(1, round(h * BALL_HELD_SCALE))))
        rect = img.get_rect(center=(sx, sy))
        screen.blit(img, rect)
    else:
        scale = BALL_HELD_SCALE if held else _primitive_ball_scale(match)
        color = BALL_HELD_COLOR if held else BALL_COLOR
        pygame.draw.circle(screen, color, (sx, sy), max(1, round(BALL_RADIUS * scale)))


def draw_frame(screen: pygame.Surface, match: Match, controlled_pid: int, font) -> None:
    cam_x, cam_y = _camera(match, controlled_pid)
    _draw_pitch(screen, match, cam_x, cam_y)
    _draw_players(screen, match, controlled_pid, cam_x, cam_y)
    _draw_ball(screen, match, cam_x, cam_y)
