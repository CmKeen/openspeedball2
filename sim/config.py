from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GameConfig:
    arena: dict
    physics: dict
    scoring: dict
    teams: dict


def load_config(data_dir: Path) -> GameConfig:
    def load(name: str) -> dict:
        return json.loads((data_dir / name).read_text(encoding="utf-8"))

    return GameConfig(
        arena=load("arena.json"),
        physics=load("physics.json"),
        scoring=load("scoring.json"),
        teams=load("teams.json"),
    )
