"""Crop specific frames out of the Amiga sprite sheets (produced by the
upstream simon-frankau/speedball2-re-amiga extract_images tool) into the
three files present/renderer.py actually loads.

Frame indices below were picked by hand after visually reviewing contact
sheets of the extracted frame strips -- see assets/amiga_extracted/.
Local-use tool only -- see README asset policy. Output goes to the
gitignored assets/ folder and must never be committed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

PLAYER_FRAME_SIZE = 32
IDLE_PLAYER_FRAME = 0

SHEET_TEAM1 = Path("assets/amiga_extracted/sprites/overlay_18.bin-002c80-013a80.png")
SHEET_TEAM2 = Path("assets/amiga_extracted/sprites/overlay_18.bin-002c80-013a80-p1.png")

# The player sheets above are REF's BankEnum.PlayersSpr (Entity.cs Draw:
# pGfx == 0x2C4EA); frame 132 in that same sheet is REF's "big ball" (that
# bank + spriteIndex += 130) -- the ball's *elevated* graphic, not its normal
# size, and it's the same 32x32 cell size as a player. The ball's own bank
# (BankEnum.Entities, pGfx == 0x193EA) is a separate, smaller sheet:
# overlay_18.bin-000000-002c80.png, immediately before the player sheet in
# the same overlay, at 16x16 frames.
#
# Frames 0-6 there are one full bounce cycle, confirmed by eye: frame 0 is
# the ball resting on the ground (its drop shadow merged directly beneath
# it, no gap); 1-3 show it rising, shrinking slightly while the shadow
# separates with a growing gap (frame 3 is the peak: smallest ball, biggest
# gap); 4-6 show it falling back, growing again as the shadow gap closes,
# landing again at frame 6. This is the original's real fake-height trick
# (Player.cs sub_D520/sub_D672: spriteIndex >2 needs a jump to catch, <=2
# doesn't -- i.e. only catchable near the start of that rise). Frames 7-10
# are a second, smaller dampened bounce; not ported since sim/actions.py
# only models a single throw_bounce_timer decay, not multi-bounce settling.
BALL_FRAME_SIZE = 16
BALL_ARC_FRAME_COUNT = 7
SHEET_BALL = Path("assets/amiga_extracted/sprites/overlay_18.bin-000000-002c80.png")

OUT_DIR = Path("assets/sprites")


def _extract_frame(sheet_path: Path, frame_index: int, frame_size: int) -> pygame.Surface:
    sheet = pygame.image.load(str(sheet_path)).convert()
    frame = sheet.subsurface((0, frame_index * frame_size, frame_size, frame_size)).copy()
    frame.set_colorkey((0, 0, 0))
    return frame.convert_alpha()


def _extract_ball_arc_strip(sheet_path: Path, frame_size: int, count: int) -> pygame.Surface:
    strip = pygame.Surface((frame_size, frame_size * count), pygame.SRCALPHA)
    for i in range(count):
        strip.blit(_extract_frame(sheet_path, i, frame_size), (0, i * frame_size))
    return strip


def main(argv: list[str]) -> int:
    pygame.init()
    pygame.display.set_mode((1, 1))

    for path in (SHEET_TEAM1, SHEET_TEAM2, SHEET_BALL):
        if not path.exists():
            print(f"error: missing {path} -- run the Amiga extraction pipeline first", file=sys.stderr)
            return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pygame.image.save(_extract_frame(SHEET_TEAM1, IDLE_PLAYER_FRAME, PLAYER_FRAME_SIZE),
                       str(OUT_DIR / "player_t1.png"))
    pygame.image.save(_extract_frame(SHEET_TEAM2, IDLE_PLAYER_FRAME, PLAYER_FRAME_SIZE),
                       str(OUT_DIR / "player_t2.png"))
    pygame.image.save(_extract_ball_arc_strip(SHEET_BALL, BALL_FRAME_SIZE, BALL_ARC_FRAME_COUNT),
                       str(OUT_DIR / "ball_arc.png"))

    for name in ("player_t1.png", "player_t2.png", "ball_arc.png"):
        print(f"wrote {OUT_DIR / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
