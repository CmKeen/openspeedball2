from __future__ import annotations

from pathlib import Path

import pygame

from present.hud import draw_hud
from present.input_map import pick_controlled_player, read_input
from present.renderer import draw_frame
from sim.config import load_config
from sim.match import Match

TICK_MS = 20  # 50 Hz, PAL frame


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("OpenSpeedball")
    font = pygame.font.SysFont("consolas", 16)
    clock = pygame.time.Clock()

    cfg = load_config(Path(__file__).resolve().parent.parent / "data")
    match = Match(cfg)

    acc = 0
    running = True
    while running and not match.is_over:
        acc += clock.tick(250)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        while acc >= TICK_MS:
            acc -= TICK_MS
            pid = pick_controlled_player(match)
            match.tick_with_ai({pid: read_input()})
        draw_frame(screen, match, pick_controlled_player(match), font)
        draw_hud(screen, match, font)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
