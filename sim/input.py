from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputState:
    """One tick of intent for one player. dir: 0..7 or None (idle)."""
    dir: int | None = None
    action_a: bool = False   # pass / tackle
    action_b: bool = False   # shoot / slide

IDLE = InputState()
