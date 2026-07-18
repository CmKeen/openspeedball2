from __future__ import annotations

from pathlib import Path

import pygame

from present.hud import draw_hud
from present.input_map import pick_controlled_player, read_input
from present.renderer import draw_frame
from sim.config import load_config
from sim.match import Match

TICK_MS = 20  # 50 Hz, PAL frame
KICKOFF_PAUSE_TICKS = 75  # ~1.5s: teams squared up before a kickoff goes live


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
    kickoff_ticks_left = KICKOFF_PAUSE_TICKS  # hold the opening kickoff too
    while running and not match.is_over:
        acc += clock.tick(250)
        space_edge = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                space_edge = True  # edge-triggered: taps between frames still fire
        while acc >= TICK_MS:
            acc -= TICK_MS
            if kickoff_ticks_left > 0:
                kickoff_ticks_left -= 1
                space_edge = False
                continue
            pid = pick_controlled_player(match)
            match.tick_with_ai({pid: read_input(space_edge)})
            space_edge = False  # consumed by the first sim tick of this frame
            if match.goal_scored:
                kickoff_ticks_left = KICKOFF_PAUSE_TICKS
        draw_frame(screen, match, pick_controlled_player(match), font)
        draw_hud(screen, match, font, kickoff_ticks_left)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
