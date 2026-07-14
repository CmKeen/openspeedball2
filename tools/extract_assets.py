"""Asset extraction tool with placeholder fallback.

OpenSpeedball never bundles ripped Speedball 2 game data -- ``assets/`` is
gitignored and must stay empty in the repo. This tool gives the sprite
pipeline (``present/renderer.py``) something to load in two ways:

1. ``--placeholders`` (default, no arguments): draws small, original
   placeholder sprites (shaded discs in team colors, a shaded ball) offscreen
   with pygame and writes them to ``assets/sprites/``. These are our own art,
   not extracted from any copyrighted source.
2. A path to a game copy (Amiga ``.adf`` or Megadrive ROM ``.bin``/``.md``):
   this tool does NOT extract sprites itself. Real sprite ripping requires
   the upstream reverse-engineering project's tools. This mode verifies the
   file exists, detects its type, and prints precise instructions for using
   ``simon-frankau/speedball2-re`` to produce the files this tool expects.

See docs/assets.md for the full asset policy.
"""
from __future__ import annotations

import os

# Must be set before pygame.init() so pygame never tries to open a real
# display/window -- this tool always runs headless.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys
from pathlib import Path

import pygame

SPRITES_DIR = Path("assets/sprites")

TEAM1_COLOR = (70, 130, 180)   # steel blue
TEAM2_COLOR = (220, 20, 60)    # crimson
BALL_COLOR = (235, 235, 235)

EXPECTED_FILES = ["player_t1.png", "player_t2.png", "ball.png"]

ROM_EXTENSIONS = {".bin", ".md"}
ADF_EXTENSIONS = {".adf"}


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def _draw_player_disc(color: tuple[int, int, int]) -> pygame.Surface:
    """A simple shaded-circle player disc, 16x16, with a lit rim for depth."""
    size = 16
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    radius = 7
    dark = _shade(color, 0.55)
    light = _shade(color, 1.25)
    pygame.draw.circle(surf, dark, center, radius)
    pygame.draw.circle(surf, color, center, radius - 1)
    # Highlight arc, upper-left, to fake a light source and give shading.
    pygame.draw.circle(surf, light, (center[0] - 2, center[1] - 2), 3)
    pygame.draw.circle(surf, (20, 20, 20), center, radius, 1)
    return surf


def _draw_ball() -> pygame.Surface:
    """A simple shaded ball, 16x16."""
    size = 16
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    radius = 6
    dark = _shade(BALL_COLOR, 0.6)
    pygame.draw.circle(surf, dark, center, radius)
    pygame.draw.circle(surf, BALL_COLOR, center, radius - 1)
    pygame.draw.circle(surf, (255, 255, 255), (center[0] - 2, center[1] - 2), 2)
    pygame.draw.circle(surf, (20, 20, 20), center, radius, 1)
    return surf


def generate_placeholders() -> list[Path]:
    """Draw and save the three original placeholder sprites. Returns paths written."""
    pygame.init()
    pygame.display.set_mode((1, 1))  # required by SDL dummy driver before Surface ops

    SPRITES_DIR.mkdir(parents=True, exist_ok=True)

    sprites = {
        "player_t1.png": _draw_player_disc(TEAM1_COLOR),
        "player_t2.png": _draw_player_disc(TEAM2_COLOR),
        "ball.png": _draw_ball(),
    }

    written = []
    for filename, surf in sprites.items():
        out_path = SPRITES_DIR / filename
        pygame.image.save(surf, str(out_path))
        written.append(out_path)
        print(f"wrote {out_path} (16x16, placeholder art)")

    return written


def _detect_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in ADF_EXTENSIONS:
        return "Amiga disk image (.adf)"
    if ext in ROM_EXTENSIONS:
        return "Megadrive/Genesis ROM"
    return "unknown"


def print_extraction_instructions(path: Path) -> None:
    kind = _detect_kind(path)
    print(f"Found file: {path}")
    print(f"Detected type: {kind}")
    print()
    print("This tool does not extract sprites itself -- real Speedball 2 sprite")
    print("data must never be ripped or bundled by this repository. To extract")
    print("sprites from your own copy of the game, use the upstream")
    print("reverse-engineering project's tools:")
    print()
    print("  1. Clone https://github.com/simon-frankau/speedball2-re")
    print("  2. Follow its README to build/run the tools/ extractors against")
    print(f"     your {kind} ({path.name}).")
    print("  3. Copy the resulting sprite images into this project's")
    print(f"     {SPRITES_DIR}/ directory, named to match what the renderer")
    print("     expects:")
    for name in EXPECTED_FILES:
        print(f"       - {SPRITES_DIR / name}")
    print()
    print("assets/ is gitignored -- extracted files stay local and are never")
    print("committed. See docs/assets.md for the full asset policy.")


def list_sprites_dir() -> None:
    print()
    print(f"{SPRITES_DIR}/ contents:")
    if not SPRITES_DIR.exists():
        print("  (directory does not exist)")
        return
    entries = sorted(SPRITES_DIR.iterdir())
    if not entries:
        print("  (empty)")
        return
    for entry in entries:
        print(f"  {entry.name}")


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--placeholders"]

    if not args:
        generate_placeholders()
        list_sprites_dir()
        return 0

    path = Path(args[0])
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        list_sprites_dir()
        return 1

    print_extraction_instructions(path)
    list_sprites_dir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
