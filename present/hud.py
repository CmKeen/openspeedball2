"""Top HUD strip: score, clock, multiplier indicators. Reads match state only."""
from __future__ import annotations

import pygame

from sim.match import Match

HUD_HEIGHT = 24
HUD_BG = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 0)


def draw_hud(screen: pygame.Surface, match: Match, font) -> None:
    strip = pygame.Rect(0, 0, 640, HUD_HEIGHT)
    pygame.draw.rect(screen, HUD_BG, strip)

    seconds = match.clock_ticks // 50
    mm, ss = divmod(seconds, 60)

    lit1 = match.score.multiplier_team1_ticks > 0
    lit2 = match.score.multiplier_team2_ticks > 0

    t1_text = f"T1 {match.score.score_team1}" + ("x2" if lit1 else "")
    clock_text = f"{mm:02d}:{ss:02d}"
    t2_text = f"{match.score.score_team2} T2" + ("x2" if lit2 else "")

    t1_color = YELLOW if lit1 else WHITE
    t2_color = YELLOW if lit2 else WHITE

    t1_surf = font.render(t1_text, True, t1_color)
    clock_surf = font.render(clock_text, True, WHITE)
    t2_surf = font.render(t2_text, True, t2_color)

    y = (HUD_HEIGHT - t1_surf.get_height()) // 2
    screen.blit(t1_surf, (8, y))
    screen.blit(clock_surf, (640 // 2 - clock_surf.get_width() // 2, y))
    screen.blit(t2_surf, (640 - 8 - t2_surf.get_width(), y))
