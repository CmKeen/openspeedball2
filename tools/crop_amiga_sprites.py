"""Crop specific frames out of the Amiga sprite sheet (produced by the
upstream simon-frankau/speedball2-re-amiga extract_images tool) into the
three files present/renderer.py actually loads.

Frame indices below were picked by hand after visually reviewing a contact
sheet of the extracted 32x32 frame strip -- see assets/amiga_extracted/.
Local-use tool only -- see README asset policy. Output goes to the
gitignored assets/ folder and must never be committed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

FRAME_SIZE = 32
IDLE_PLAYER_FRAME = 0
BALL_FRAME = 132

SHEET_TEAM1 = Path("assets/amiga_extracted/sprites/overlay_18.bin-002c80-013a80.png")
SHEET_TEAM2 = Path("assets/amiga_extracted/sprites/overlay_18.bin-002c80-013a80-p1.png")
OUT_DIR = Path("assets/sprites")


def _extract_frame(sheet_path: Path, frame_index: int) -> pygame.Surface:
    sheet = pygame.image.load(str(sheet_path)).convert()
    frame = sheet.subsurface((0, frame_index * FRAME_SIZE, FRAME_SIZE, FRAME_SIZE)).copy()
    frame.set_colorkey((0, 0, 0))
    return frame.convert_alpha()


def main(argv: list[str]) -> int:
    pygame.init()
    pygame.display.set_mode((1, 1))

    for path in (SHEET_TEAM1, SHEET_TEAM2):
        if not path.exists():
            print(f"error: missing {path} -- run the Amiga extraction pipeline first", file=sys.stderr)
            return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pygame.image.save(_extract_frame(SHEET_TEAM1, IDLE_PLAYER_FRAME), str(OUT_DIR / "player_t1.png"))
    pygame.image.save(_extract_frame(SHEET_TEAM2, IDLE_PLAYER_FRAME), str(OUT_DIR / "player_t2.png"))
    pygame.image.save(_extract_frame(SHEET_TEAM1, BALL_FRAME), str(OUT_DIR / "ball.png"))

    for name in ("player_t1.png", "player_t2.png", "ball.png"):
        print(f"wrote {OUT_DIR / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
