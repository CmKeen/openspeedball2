# OpenSpeedball MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One playable Speedball 2 match — human vs CPU on a scrolling pitch with authentic ball physics, tackling, possession, goals, score-multiplier banks, and a HUD — built on a deterministic, render-free simulation core ready for future lockstep/rollback online multiplayer.

**Architecture:** A pure-Python integer-math simulation package (`sim/`) with zero rendering/input/OS-randomness dependencies, driven at a fixed 50 Hz tick by a thin pygame presentation layer (`present/`). All tunables (arena geometry, physics constants, team stats, scoring values) live in JSON under `data/`. Mechanics are translated from documented reverse-engineering ground truth; the local reference implementation is Kroah's C# source at `Speedball 2 - WIP 02/Speedball 2 - WIP 02/src/` (called **REF** below). Express REF's *logic and constants* in original idiomatic Python — do not copy C# code verbatim.

**Tech Stack:** Python 3.11+, `pygame-ce` (presentation only), `pytest`. **Explicit stack decision (must be stated in README):** Python + pygame chosen over Godot because Godot is not installed in this environment, the sim core must be headless-testable, and the brief permits pygame if the sim core is strictly isolated. The sim core is engine-agnostic by construction and is the asset that survives any future engine port.

## Global Constraints

- **Sim purity:** nothing under `sim/` may import `pygame`, `random`, `time`, `datetime`, `os.urandom`, or anything from `present/`. Enforced by a test.
- **Integer math only in the sim** (the original game is all integer math — this makes cross-platform determinism trivial, which future online lockstep requires). No floats in sim state or logic.
- **All randomness** comes from the seeded `Sb2Rng` instance owned by `Match`. No other randomness anywhere in `sim/`.
- **Fixed timestep:** sim tick = 1/50 s (PAL Amiga frame). Presentation uses an accumulator; never step the sim by variable dt.
- **Data-driven:** arena layout, physics tunables, team stats, scoring values load from `data/*.json`. No gameplay constant hardcoded in logic files (module-level names loaded from JSON are fine).
- **License/assets:** GPLv3 for code. Never commit extracted sprites/sounds; `assets/` is gitignored. `Resources/` and `Speedball 2 - WIP 02*` (the user's local reference material) must be gitignored and never committed.
- **Terrain coordinate system (ground truth, REF `Entity.cs:223-265`):** pitch is 640 × 1152 integer terrain units; x grows right, y grows down; team 1 defends the bottom goal at kickoff. Directions are 0..7 (0 = up/N, clockwise: 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW).
- **Commit style:** conventional commits (`feat:`, `test:`, `chore:`, `docs:`), commit at the end of every task, never commit messages with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Where a constant below is marked **[tunable — validate]**, the value is a concrete working default that must live in JSON and be checked later against REF per the validation method in `docs/spec/mechanics.md`.

## File Structure

```
openspeedball/
├── LICENSE                  GPLv3 full text
├── README.md                stack decision, asset policy, how to run/test
├── .gitignore               assets/, Resources/, Speedball 2 - WIP 02*, venv, caches
├── pyproject.toml           project metadata, pytest config
├── docs/spec/mechanics.md   plain-English extracted physics/AI spec with REF citations
├── data/
│   ├── arena.json           pitch dims, goal mouths, multiplier banks, margins
│   ├── physics.json         friction, speeds, tackle numbers, throw speeds
│   ├── scoring.json         point values, multiplier behavior
│   └── teams.json           two 9-player rosters with 8 stats + health each
├── sim/                     ← the deterministic core (no rendering imports, ever)
│   ├── __init__.py
│   ├── rng.py               Sb2Rng — port of the original 32-bit generator
│   ├── config.py            JSON loading → typed config objects
│   ├── vec.py               Vec(x,y) integer 2-vector + dir helpers
│   ├── entities.py          Entity base, Ball (bounce/friction/walls)
│   ├── player.py            PlayerSim: stats, movement, states
│   ├── input.py             InputState dataclass (the ONLY way intent enters the sim)
│   ├── actions.py           possession, throwing, tackling
│   ├── scoring.py           goal detection, score, multiplier banks
│   ├── ai.py                CPU controller producing InputState per player
│   └── match.py             Match: orchestrates one fixed-order tick
├── present/                 ← thin pygame layer
│   ├── __init__.py
│   ├── app.py               window, fixed-timestep loop, wiring
│   ├── renderer.py          draws sim state; sprites if available, primitives if not
│   ├── hud.py               score / clock / multiplier display
│   └── input_map.py         keyboard → InputState, active-player switching
├── tools/
│   └── extract_assets.py    reads user-owned game files → assets/ (gitignored), with fallback
└── tests/
    ├── test_rng.py
    ├── test_ball.py
    ├── test_player.py
    ├── test_actions.py
    ├── test_scoring.py
    ├── test_match.py
    ├── test_ai.py
    └── test_sim_purity.py
```

---

### Task 1: Repo scaffold, license, README

**Files:**
- Create: `LICENSE`, `README.md`, `.gitignore`, `pyproject.toml`, `sim/__init__.py`, `present/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: a git repo where `python -m pytest` runs (0 tests OK), `pip install -e .[dev]` works.

- [ ] **Step 1: git init and .gitignore**

```bash
git init
```

`.gitignore`:
```gitignore
# extracted game assets — NEVER commit (see README asset policy)
assets/
# user's local reference material — not ours to redistribute
Resources/
Speedball 2 - WIP 02/
Speedball 2 - WIP 02.zip
# python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
*.egg-info/
dist/
build/
```

- [ ] **Step 2: LICENSE**

Download the canonical GPLv3 text:
```bash
curl -fsSL https://www.gnu.org/licenses/gpl-3.0.txt -o LICENSE
```
Verify: file starts with `GNU GENERAL PUBLIC LICENSE` / `Version 3, 29 June 2007`. If offline, copy the GPLv3 text from any locally installed package that ships it, or defer the download to the end of the task — the file must be the unmodified canonical text.

- [ ] **Step 3: README.md**

```markdown
# OpenSpeedball

A modern, open-source remake of **Speedball 2: Brutal Deluxe** (The Bitmap
Brothers, 1990). Current milestone: one playable match — human vs CPU.

## Tech stack (explicit decision)

**Python 3.11+ / pygame-ce**, with a strictly isolated simulation core.

- `sim/` — deterministic, integer-math, render-free match simulation.
  No pygame, no wall-clock, no OS randomness. Headless-testable.
- `present/` — thin pygame layer: draws sim state, feeds it input.
- `data/` — all gameplay tunables as JSON.

Godot 4 was the brief's default recommendation; pygame was chosen because
the sim core must be developed and validated headless. The sim core is
engine-agnostic: porting presentation to Godot (or anything else) later
requires no sim rework. The deterministic, seeded core is also the
foundation for future lockstep/rollback online multiplayer.

## Asset policy (important)

This repository contains **code only** (GPLv3). It does not and will never
contain sprites, sounds, or other assets ripped from Speedball 2. To play
with original graphics, point `tools/extract_assets.py` at your own legally
obtained copy of the game; extracted assets stay in the gitignored
`assets/` folder. Without assets the game runs with built-in placeholder
graphics.

## Run

    pip install -e .[dev]
    python -m present.app          # play
    python -m pytest               # headless sim tests

## Controls

Arrows/WASD: move · Space: pass/tackle · Left Shift: shoot/slide

## Credits & prior work

Mechanics are translated from documented reverse-engineering work:
simon-frankau/speedball2-re (Megadrive), simon-frankau/speedball2-re-amiga,
and Kroah's Speedball 2 Remake research (bringerp.free.fr).
```

- [ ] **Step 4: pyproject.toml**

```toml
[project]
name = "openspeedball"
version = "0.1.0"
description = "Open-source remake of Speedball 2: Brutal Deluxe"
requires-python = ">=3.11"
license = { text = "GPL-3.0-or-later" }
dependencies = ["pygame-ce>=2.4"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["sim", "present", "tools"]
```

- [ ] **Step 5: create empty packages and verify**

Create empty `sim/__init__.py`, `present/__init__.py`, `tests/__init__.py`, `tools/__init__.py`.

Run: `pip install -e .[dev] && python -m pytest`
Expected: `no tests ran` (exit code 5 is fine at this stage).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: scaffold repo — GPLv3, README with stack decision and asset policy"
```

---

### Task 2: Seedable RNG (`sim/rng.py`)

**Files:**
- Create: `sim/rng.py`
- Test: `tests/test_rng.py`

**Interfaces:**
- Produces: `Sb2Rng(a: int = 0x31415926, b: int = 0x53589793)` with `next() -> int` (32-bit), `next_byte(mask: int = 0xFF) -> int`, `next_word(mask: int = 0xFFFF) -> int`, and readable state attrs `a`, `b`.

The original game uses a 32-bit generator over two state words, seeded with the documented constants `0x31415926` / `0x53589793` (π and a truncation of its continued digits — ground truth from the RE work; REF `MyRandom.cs`). One step: split each state word into 16-bit halves; shift the low half of word A left by 1 (carry out); then perform two add-with-carry rounds where the low half of B is added into the low half of A, the pre-add value of A's low half becomes B's new low half, and the halves of A and B are each swapped between rounds; reassemble both words. The new word A is the output.

- [ ] **Step 1: Write the failing test**

`tests/test_rng.py`:
```python
from sim.rng import Sb2Rng

# Golden vector computed from the documented algorithm at the default seed.
GOLDEN = [0x849A49DF, 0xB5DC460A, 0x3A771FD2, 0xF053CBB8,
          0x2ACAD715, 0x1B1E459B, 0x45E93960, 0x6107FDF6]


def test_golden_sequence_from_default_seed():
    rng = Sb2Rng()
    assert [rng.next() for _ in range(8)] == GOLDEN


def test_next_byte_masks_low_bits():
    rng = Sb2Rng()
    assert rng.next_byte() == GOLDEN[0] & 0xFF  # 0xDF == 223
    assert rng.next_byte(0x0F) == GOLDEN[1] & 0x0F


def test_same_seed_same_stream_different_seed_diverges():
    s1 = [Sb2Rng(1, 2).next() for _ in range(50)]
    s2 = [Sb2Rng(1, 2).next() for _ in range(50)]
    s3 = [Sb2Rng(1, 3).next() for _ in range(50)]
    assert s1 == s2
    assert s1 != s3


def test_output_is_32_bit():
    rng = Sb2Rng()
    for _ in range(1000):
        assert 0 <= rng.next() <= 0xFFFFFFFF
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rng.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sim.rng'`

- [ ] **Step 3: Implement `sim/rng.py`**

```python
"""Seedable RNG matching the original Speedball 2 generator.

Algorithm documented by the reverse-engineering projects (see
docs/spec/mechanics.md). Two 32-bit state words; each step shifts and
add-with-carries their 16-bit halves, swapping halves between two rounds.
Default seed constants are the ones the original game boots with.
"""

_M16 = 0xFFFF
_M32 = 0xFFFFFFFF


class Sb2Rng:
    def __init__(self, a: int = 0x31415926, b: int = 0x53589793) -> None:
        self.a = a & _M32
        self.b = b & _M32

    def next(self) -> int:
        a_hi, a_lo = (self.a >> 16) & _M16, self.a & _M16
        b_hi, b_lo = (self.b >> 16) & _M16, self.b & _M16

        a_lo <<= 1
        carry = a_lo > _M16
        a_lo &= _M16

        for _ in range(2):
            pre_add = a_lo
            a_lo += b_lo + (1 if carry else 0)
            carry = a_lo > _M16
            a_lo &= _M16
            b_lo = pre_add
            a_hi, a_lo = a_lo, a_hi
            b_hi, b_lo = b_lo, b_hi

        self.a = ((a_hi << 16) | a_lo) & _M32
        self.b = ((b_hi << 16) | b_lo) & _M32
        return self.a

    def next_byte(self, mask: int = 0xFF) -> int:
        return self.next() & 0xFF & mask

    def next_word(self, mask: int = 0xFFFF) -> int:
        return self.next() & 0xFFFF & mask
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rng.py -v`
Expected: 4 passed. If the golden vector fails, the half-swap ordering is wrong — re-check against the algorithm description; do not change the golden values.

- [ ] **Step 5: Commit**

```bash
git add sim/rng.py tests/test_rng.py && git commit -m "feat: port original seedable RNG with golden-vector tests"
```

---

### Task 3: Data files, config loader, mechanics spec doc

**Files:**
- Create: `data/arena.json`, `data/physics.json`, `data/scoring.json`, `data/teams.json`, `sim/config.py`, `sim/vec.py`, `docs/spec/mechanics.md`
- Test: `tests/test_config.py` (folded into this task; simple loader checks)

**Interfaces:**
- Produces:
  - `Vec` — frozen dataclass `Vec(x: int, y: int)` with `+`, `-`, `manhattan(other) -> int`, `chebyshev(other) -> int`.
  - `DIR_VECTORS: tuple[Vec, ...]` — 8 unit steps indexed by dir 0..7 (0=N=(0,-1), 2=E=(1,0), 4=S=(0,1), 6=W=(-1,0), diagonals combine).
  - `mirror_dir_x(d) -> int`, `mirror_dir_y(d) -> int` — direction reflection for wall bounces.
  - `GameConfig` — frozen dataclass with `.arena`, `.physics`, `.scoring`, `.teams` (plain nested dicts loaded from JSON) via `load_config(data_dir: Path) -> GameConfig`.

- [ ] **Step 1: Write data files**

`data/arena.json` (dimensions are RE ground truth; goal mouth and bank rects are **[tunable — validate]**):
```json
{
  "width": 640,
  "height": 1152,
  "wall_margin_ball": 16,
  "wall_margin_player": 16,
  "goal_mouth_x_min": 272,
  "goal_mouth_x_max": 368,
  "goal_depth": 16,
  "kickoff_center": [320, 576],
  "multiplier_banks": [
    { "team_side": 1, "x_min": 0,   "x_max": 24,  "y_min": 384, "y_max": 480 },
    { "team_side": 2, "x_min": 616, "x_max": 640, "y_min": 672, "y_max": 768 }
  ]
}
```

`data/physics.json` (friction/walls/tackle numbers are RE ground truth; speeds marked tunable):
```json
{
  "ball_friction_per_tick": 1,
  "ball_no_friction_y_min": 48,
  "ball_no_friction_y_max": 1104,
  "player_base_speed": 2,
  "player_speed_bonus_threshold": 192,
  "tackle_range": 30,
  "tackle_knockback_speed": 3,
  "tackle_knockback_speed_sliding": 4,
  "tackle_def_malus_by_delta_dir": [64, 48, 32, 16, 0, 16, 32, 48],
  "tackle_malus_sliding": 32,
  "tackle_malus_jumping": 32,
  "goalkeeper_def_multiplier_num": 3,
  "goalkeeper_def_multiplier_den": 2,
  "pass_speed": 8,
  "shot_speed": 12,
  "throw_bounce_timer": 24,
  "pickup_range": 12
}
```
`player_base_speed`, `pass_speed`, `shot_speed`, `throw_bounce_timer`, `pickup_range`, the two `tackle_malus_*` values and `tackle_def_malus_by_delta_dir` are **[tunable — validate]** (REF pointers: `Player.cs sub_DE88_CalcBonusFromSpd`, `sub_EA62_CalcOpcodesTypeAndVelocityC`, `Match.GetTackleDefMalus`, `Match._tackleUnk01/_tackleUnk02`).

`data/scoring.json` (**[tunable — validate]** against REF `ScoreMultipliers.cs`/`Stars.cs`):
```json
{
  "goal_points": 10,
  "goal_points_multiplied": 20,
  "multiplier_duration_ticks": 1500,
  "leg_duration_ticks": 13500
}
```
(`leg_duration_ticks` = 90 in-game seconds at 50 Hz × 3 = 4.5 real minutes is the placeholder; the original leg is ~90 s of play — keep it data-driven.)

`data/teams.json` — two rosters of **9** on-pitch players (formation: 1 GK, 2 defense, 3 midfield, 3 attack). Stats are the 8 originals: aggression, attack, defence, speed, throwing, power, stamina, intelligence — each 0..255, plus health 0..255. Give team 1 ("Brutal Deluxe") all stats 128, health 255; team 2 ("Super Nashwan") all stats 160, health 255. Structure:
```json
{
  "teams": [
    {
      "name": "Brutal Deluxe",
      "players": [
        { "name": "GK", "position": 0, "agr": 128, "att": 128, "def": 128,
          "spd": 128, "thr": 128, "pow": 128, "sta": 128, "int": 128,
          "health": 255 }
      ]
    }
  ]
}
```
(Write all 9 players per team with `position` 0=GK, 1=defense, 2=midfield, 3=attack; names can be simple like "DEF1". Verify roster size against REF `Match.cs` player-array initialization; if REF differs from 9, follow REF and update this file + formation code.)

- [ ] **Step 2: Write the failing tests**

`tests/test_config.py`:
```python
from pathlib import Path

from sim.config import load_config
from sim.vec import Vec, DIR_VECTORS, mirror_dir_x, mirror_dir_y

DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_config_shapes():
    cfg = load_config(DATA)
    assert cfg.arena["width"] == 640
    assert cfg.arena["height"] == 1152
    assert cfg.physics["ball_friction_per_tick"] == 1
    assert len(cfg.teams["teams"]) == 2
    for team in cfg.teams["teams"]:
        assert len(team["players"]) == 9
        assert team["players"][0]["position"] == 0  # goalkeeper first


def test_dir_vectors():
    assert DIR_VECTORS[0] == Vec(0, -1)   # N
    assert DIR_VECTORS[2] == Vec(1, 0)    # E
    assert DIR_VECTORS[4] == Vec(0, 1)    # S
    assert DIR_VECTORS[6] == Vec(-1, 0)   # W
    assert DIR_VECTORS[1] == Vec(1, -1)   # NE


def test_mirror_dirs():
    assert mirror_dir_x(2) == 6 and mirror_dir_x(6) == 2   # E <-> W
    assert mirror_dir_x(0) == 0 and mirror_dir_x(4) == 4   # N, S unchanged
    assert mirror_dir_y(0) == 4 and mirror_dir_y(4) == 0   # N <-> S
    assert mirror_dir_y(1) == 3 and mirror_dir_y(7) == 5   # NE<->SE, NW<->SW


def test_vec_math():
    assert Vec(1, 2) + Vec(3, -1) == Vec(4, 1)
    assert Vec(5, 5) - Vec(2, 7) == Vec(3, -2)
    assert Vec(0, 0).manhattan(Vec(3, -4)) == 7
    assert Vec(0, 0).chebyshev(Vec(3, -4)) == 4
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `sim/vec.py` and `sim/config.py`**

`sim/vec.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Vec:
    x: int
    y: int

    def __add__(self, o: "Vec") -> "Vec":
        return Vec(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec") -> "Vec":
        return Vec(self.x - o.x, self.y - o.y)

    def manhattan(self, o: "Vec") -> int:
        return abs(self.x - o.x) + abs(self.y - o.y)

    def chebyshev(self, o: "Vec") -> int:
        return max(abs(self.x - o.x), abs(self.y - o.y))


# dir 0..7: 0=N then clockwise
DIR_VECTORS: tuple[Vec, ...] = (
    Vec(0, -1), Vec(1, -1), Vec(1, 0), Vec(1, 1),
    Vec(0, 1), Vec(-1, 1), Vec(-1, 0), Vec(-1, -1),
)

_MIRROR_X = (0, 7, 6, 5, 4, 3, 2, 1)  # reflect east<->west
_MIRROR_Y = (4, 3, 2, 1, 0, 7, 6, 5)  # reflect north<->south


def mirror_dir_x(d: int) -> int:
    return _MIRROR_X[d & 7]


def mirror_dir_y(d: int) -> int:
    return _MIRROR_Y[d & 7]


def dir_towards(src: Vec, dst: Vec) -> int:
    """8-way direction from src toward dst (ties resolve to diagonals)."""
    dx = (dst.x > src.x) - (dst.x < src.x)
    dy = (dst.y > src.y) - (dst.y < src.y)
    return {(0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
            (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
            (0, 0): 0}[(dx, dy)]
```

`sim/config.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 4 passed.

- [ ] **Step 6: Write `docs/spec/mechanics.md`**

Plain-English spec of everything translated so far and its provenance. Content (write it out fully, one section per mechanic):
- **Coordinate system & arena:** 640×1152 terrain units; entities clamp to `[margin, limit-margin]` per axis; the ball reflects velocity and mirrors its direction on wall hit; a Y-wall bounce halves the ball's bounce timer. (REF `Entity.cs MoveAndHandleWallsAndBounce`.)
- **Ball friction:** when free (not held, not inside a multiplier bank, moving), each axis's |velocity| decays by 1 per tick toward 0; no decay while the ball is in the goal zones (y < 48 or y > 1104) and moving vertically; a bounce timer defers friction while high. (REF `Entity.cs UpdateBallVelocity`.)
- **RNG:** algorithm + seed constants + the 8-value golden vector from Task 2.
- **Tackle:** range 30 units; success threshold `(attacker.att + 256 - def_eff) / 2` rolled against a random byte, where `def_eff` = defender.def, ×1.5 capped 255 for goalkeepers, minus a facing-direction malus, minus maluses if the attacker slides or the defender is jumping; knockback speed 3 (4 sliding) in the tackler's facing direction; damage `max(1, (pow + 150 - sta) // 16)` to health and half that (min 1) off all eight stats; ball transfers to the tackler unless the tackler is also falling. (REF `Player.cs` tackle routines.)
- **Match tick order** (REF `Match.cs Update`): ball velocity update → multiplier-bank checks → arena furniture checks → ball-to-player distances → think (AI/human input) → goal check → move everything with wall handling → camera follows ball/holder.
- **Validation method:** the sim is seeded and integer-exact; to validate a tunable, run the same scenario in REF's runnable demo (`Speedball 2 - WIP 02/bin/Speedball 2.exe`) and in our sim with the same seed and compare trajectories/decisions frame by frame; correct our JSON constants until they match. List every **[tunable — validate]** key here with its REF pointer.

- [ ] **Step 7: Commit**

```bash
git add data/ sim/vec.py sim/config.py tests/test_config.py docs/spec/mechanics.md
git commit -m "feat: data-driven config, integer vec math, mechanics spec doc"
```

---

### Task 4: Entity base + ball physics (`sim/entities.py`)

**Files:**
- Create: `sim/entities.py`
- Test: `tests/test_ball.py`

**Interfaces:**
- Consumes: `Vec`, `mirror_dir_x/y` (Task 3), physics/arena dicts.
- Produces:
  - `Entity` — mutable dataclass: `pos: Vec`, `vel: Vec`, `dir: int = 0`.
  - `Ball(Entity)` — adds `bounce_timer: int = 0`, `held_by: object | None = None`, `in_bank: bool = False`.
  - `move_and_bounce(e: Entity, arena: dict, margin: int, is_ball: bool) -> None` — clamp/reflect against walls then advance by velocity.
  - `update_ball_velocity(ball: Ball, physics: dict, ball_speed_ref: list[int]) -> None` — the friction/bounce-timer rule. `ball_speed_ref` is a 1-element list holding the match's decaying "recent throw speed" value so this function can halve-and-quarter it in place (Match owns it from Task 8).

- [ ] **Step 1: Write the failing tests**

`tests/test_ball.py`:
```python
from pathlib import Path

from sim.config import load_config
from sim.entities import Ball, Entity, move_and_bounce, update_ball_velocity
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def make_ball(pos, vel, timer=0):
    b = Ball(pos=pos, vel=vel)
    b.bounce_timer = timer
    return b


def test_ball_reflects_off_right_wall():
    b = make_ball(Vec(650, 600), Vec(5, 0))  # already past the wall
    move_and_bounce(b, CFG.arena, margin=16, is_ball=True)
    # clamped to 640-16=624, velocity reflected, then moved by new velocity
    assert b.vel.x == -5
    assert b.pos.x == 624 - 5


def test_ball_y_bounce_halves_bounce_timer():
    b = make_ball(Vec(320, 1160), Vec(0, 6), timer=20)
    move_and_bounce(b, CFG.arena, margin=16, is_ball=True)
    assert b.vel.y == -6
    assert b.bounce_timer == 10


def test_player_clamps_without_reflecting():
    p = Entity(pos=Vec(700, 600), vel=Vec(3, 0))
    move_and_bounce(p, CFG.arena, margin=16, is_ball=False)
    assert p.vel.x == 3          # players don't bounce
    assert p.pos.x == 624 + 3    # clamped then moved


def test_free_ball_friction_decays_each_axis_by_one():
    b = make_ball(Vec(320, 600), Vec(5, -3))
    update_ball_velocity(b, CFG.physics, [0])
    assert b.vel == Vec(4, -2)


def test_no_friction_in_goal_zone_when_moving_vertically():
    b = make_ball(Vec(320, 40), Vec(2, -4))  # y < 48
    update_ball_velocity(b, CFG.physics, [0])
    assert b.vel == Vec(2, -4)


def test_held_ball_skips_friction():
    b = make_ball(Vec(320, 600), Vec(5, 5))
    b.held_by = object()
    update_ball_velocity(b, CFG.physics, [0])
    assert b.vel == Vec(5, 5)


def test_bounce_timer_defers_friction():
    b = make_ball(Vec(320, 600), Vec(6, 0), timer=10)
    speed_ref = [4]  # match's recent-throw speed below timer -> timer path
    update_ball_velocity(b, CFG.physics, speed_ref)
    assert b.vel == Vec(6, 0)      # friction deferred
    assert b.bounce_timer == 9     # timer ticks down
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ball.py -v` — expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `sim/entities.py`**

```python
"""Entities and ball physics.

Rules translated from the documented RE (see docs/spec/mechanics.md):
walls clamp positions to [margin, limit - margin]; the ball reflects and
mirrors its direction; a Y bounce halves the bounce timer. Free-ball
friction decays each velocity axis by 1 per tick, deferred while the
bounce timer outruns the match's recent-throw speed, and suspended in the
goal zones while the ball moves vertically.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sim.vec import Vec, mirror_dir_x, mirror_dir_y


@dataclass(slots=True)
class Entity:
    pos: Vec
    vel: Vec = field(default_factory=lambda: Vec(0, 0))
    dir: int = 0


@dataclass(slots=True)
class Ball(Entity):
    bounce_timer: int = 0
    held_by: object | None = None
    in_bank: bool = False


def _axis(value: int, vel: int, low: int, high: int) -> tuple[int, int, bool]:
    if value > high:
        return high, vel, True
    if value < low:
        return low, vel, True
    return value, vel, False


def move_and_bounce(e: Entity, arena: dict, margin: int, is_ball: bool) -> None:
    x, vx, hit_x = _axis(e.pos.x, e.vel.x, margin, arena["width"] - margin)
    if hit_x and is_ball:
        vx = -vx
        e.dir = mirror_dir_x(e.dir)
    x += vx

    y, vy, hit_y = _axis(e.pos.y, e.vel.y, margin, arena["height"] - margin)
    if hit_y and is_ball:
        vy = -vy
        e.dir = mirror_dir_y(e.dir)
        if isinstance(e, Ball):
            e.bounce_timer -= e.bounce_timer // 2
    y += vy

    e.pos = Vec(x, y)
    e.vel = Vec(vx, vy)


def _decay(v: int) -> int:
    return v - 1 if v > 0 else v + 1 if v < 0 else 0


def update_ball_velocity(ball: Ball, physics: dict,
                         ball_speed_ref: list[int]) -> None:
    if ball.held_by is not None or ball.in_bank:
        return
    if ball.vel == Vec(0, 0):
        return
    if ball.vel.y != 0 and (ball.pos.y < physics["ball_no_friction_y_min"]
                            or ball.pos.y > physics["ball_no_friction_y_max"]):
        return

    if ball.bounce_timer != 0:
        if ball_speed_ref[0] <= ball.bounce_timer:
            ball.bounce_timer -= 1
            return
        ball_speed_ref[0] = ball_speed_ref[0] // 2 + ball_speed_ref[0] // 4

    ball.vel = Vec(_decay(ball.vel.x), _decay(ball.vel.y))
    if ball.bounce_timer != 0:
        ball.bounce_timer -= 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ball.py -v` — expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add sim/entities.py tests/test_ball.py && git commit -m "feat: entity base and authentic ball wall-bounce/friction physics"
```

---

### Task 5: Players, input, movement (`sim/player.py`, `sim/input.py`)

**Files:**
- Create: `sim/player.py`, `sim/input.py`
- Test: `tests/test_player.py`

**Interfaces:**
- Consumes: `Entity`, `Vec`, `DIR_VECTORS`, config dicts.
- Produces:
  - `InputState` — frozen dataclass: `dir: int | None` (None = no movement), `action_a: bool` (pass/tackle), `action_b: bool` (shoot/slide). This is the ONLY channel by which intent (human or AI) enters the sim — required for future online input-passing.
  - `PlayerSim(Entity)` — fields: `index: int`, `team: int` (1 or 2), `position: int` (0 GK, 1 DEF, 2 MID, 3 ATT), `stats: dict[str, int]` (keys `agr att def spd thr pow sta int health`), `home: Vec` (formation anchor), `falling_ticks: int = 0`, `sliding_ticks: int = 0`, `knock_vel: Vec = Vec(0,0)`.
  - `speed_of(p: PlayerSim, physics: dict) -> int` — base speed + 1 if `spd >= player_speed_bonus_threshold`.
  - `apply_movement(p: PlayerSim, inp: InputState, physics: dict) -> None` — sets `p.vel`/`p.dir` from input; while `falling_ticks > 0` the player is knocked instead (moves by `knock_vel`, decrement counter, ignores input); while `sliding_ticks > 0` keeps sliding in `p.dir` at slide speed, decrement.
  - Constants: `FALL_TICKS = 25`, `SLIDE_TICKS = 12` **[tunable — validate]** (module constants are OK here only as defaults overridden by physics dict keys `fall_ticks`, `slide_ticks` — add both keys to `data/physics.json` with those values).

- [ ] **Step 1: Add `fall_ticks: 25` and `slide_ticks: 12` to `data/physics.json`.**

- [ ] **Step 2: Write the failing tests**

`tests/test_player.py`:
```python
from pathlib import Path

from sim.config import load_config
from sim.input import InputState
from sim.player import PlayerSim, apply_movement, speed_of
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def make_player(spd=128):
    stats = dict(agr=128, att=128, **{"def": 128}, spd=spd, thr=128,
                 pow=128, sta=128, int=128, health=255)
    return PlayerSim(pos=Vec(320, 576), index=0, team=1, position=2,
                     stats=stats, home=Vec(320, 576))


def test_speed_bonus_threshold():
    assert speed_of(make_player(spd=128), CFG.physics) == 2
    assert speed_of(make_player(spd=200), CFG.physics) == 3


def test_movement_sets_velocity_and_dir():
    p = make_player()
    apply_movement(p, InputState(dir=2), CFG.physics)   # East
    assert p.dir == 2
    assert p.vel == Vec(2, 0)


def test_no_input_stops_player():
    p = make_player()
    apply_movement(p, InputState(dir=2), CFG.physics)
    apply_movement(p, InputState(dir=None), CFG.physics)
    assert p.vel == Vec(0, 0)


def test_falling_player_ignores_input_and_recovers():
    p = make_player()
    p.falling_ticks = 2
    p.knock_vel = Vec(0, 3)
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.vel == Vec(0, 3)         # knocked, not steering
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.falling_ticks == 0
    apply_movement(p, InputState(dir=6), CFG.physics)
    assert p.vel == Vec(-2, 0)        # control regained
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_player.py -v` — expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement**

`sim/input.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputState:
    """One tick of intent for one player. dir: 0..7 or None (idle)."""
    dir: int | None = None
    action_a: bool = False   # pass / tackle
    action_b: bool = False   # shoot / slide

IDLE = InputState()
```

`sim/player.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field

from sim.entities import Entity
from sim.input import InputState
from sim.vec import DIR_VECTORS, Vec


@dataclass(slots=True)
class PlayerSim(Entity):
    index: int = 0
    team: int = 1
    position: int = 2  # 0 GK, 1 DEF, 2 MID, 3 ATT
    stats: dict = field(default_factory=dict)
    home: Vec = field(default_factory=lambda: Vec(0, 0))
    falling_ticks: int = 0
    sliding_ticks: int = 0
    knock_vel: Vec = field(default_factory=lambda: Vec(0, 0))


def speed_of(p: PlayerSim, physics: dict) -> int:
    bonus = 1 if p.stats["spd"] >= physics["player_speed_bonus_threshold"] else 0
    return physics["player_base_speed"] + bonus


def apply_movement(p: PlayerSim, inp: InputState, physics: dict) -> None:
    if p.falling_ticks > 0:
        p.falling_ticks -= 1
        p.vel = p.knock_vel
        return
    if p.sliding_ticks > 0:
        p.sliding_ticks -= 1
        step = DIR_VECTORS[p.dir]
        s = physics["tackle_knockback_speed_sliding"]
        p.vel = Vec(step.x * s, step.y * s)
        return
    if inp.dir is None:
        p.vel = Vec(0, 0)
        return
    p.dir = inp.dir
    s = speed_of(p, physics)
    step = DIR_VECTORS[inp.dir]
    p.vel = Vec(step.x * s, step.y * s)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_player.py -v` — expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add sim/player.py sim/input.py tests/test_player.py data/physics.json
git commit -m "feat: player entity, input state, 8-way movement with fall/slide states"
```

---

### Task 6: Possession, throwing, tackling (`sim/actions.py`)

**Files:**
- Create: `sim/actions.py`
- Test: `tests/test_actions.py`

**Interfaces:**
- Consumes: `Ball`, `PlayerSim`, `InputState`, `Sb2Rng`, `Vec`, `DIR_VECTORS`, physics dict.
- Produces:
  - `try_pickup(ball: Ball, p: PlayerSim, physics: dict) -> bool` — free ball within `pickup_range` (chebyshev) → `ball.held_by = p`.
  - `throw(ball: Ball, p: PlayerSim, physics: dict, shot: bool, ball_speed_ref: list[int]) -> None` — releases in `p.dir` at `pass_speed`/`shot_speed`, sets `ball.bounce_timer = throw_bounce_timer`, updates `ball_speed_ref[0]` to the throw speed, clears `held_by`.
  - `tackle_probability(attacker: PlayerSim, defender: PlayerSim, physics: dict) -> int` — the documented formula (see mechanics spec, Task 3 step 6).
  - `attempt_tackle(attacker: PlayerSim, defenders: list[PlayerSim], ball: Ball, rng: Sb2Rng, physics: dict) -> PlayerSim | None` — first defender in range, roll `rng.next_byte() <= p`; on success: defender falls (`falling_ticks = fall_ticks`, `knock_vel` = attacker's dir × knockback speed, 4 if attacker sliding), apply damage, transfer ball if defender held it (unless attacker falling). Returns the hit defender or None.
  - `apply_tackle_damage(defender: PlayerSim, attacker: PlayerSim) -> None` — `d = max(1, (attacker.pow + 150 - defender.sta) // 16)` off health (floor 0); `max(1, d // 2)` off all eight stats (floor 1 each so nobody bottoms out to zero speed).

- [ ] **Step 1: Write the failing tests**

`tests/test_actions.py`:
```python
from pathlib import Path

from sim.actions import (apply_tackle_damage, attempt_tackle,
                         tackle_probability, throw, try_pickup)
from sim.config import load_config
from sim.entities import Ball
from sim.player import PlayerSim
from sim.rng import Sb2Rng
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")
PHY = CFG.physics


def make_player(team=1, pos=Vec(320, 576), position=2, **over):
    stats = dict(agr=128, att=128, **{"def": 128}, spd=128, thr=128,
                 pow=128, sta=128, int=128, health=255)
    stats.update(over)
    return PlayerSim(pos=pos, index=0, team=team, position=position,
                     stats=stats, home=pos)


def test_pickup_in_range_only():
    ball = Ball(pos=Vec(320, 576))
    near = make_player(pos=Vec(325, 580))
    far = make_player(pos=Vec(400, 576))
    assert not try_pickup(ball, far, PHY)
    assert try_pickup(ball, near, PHY)
    assert ball.held_by is near


def test_throw_releases_ball_with_speed_and_bounce_timer():
    ball = Ball(pos=Vec(320, 576))
    p = make_player()
    ball.held_by = p
    p.dir = 2  # East
    speed_ref = [0]
    throw(ball, p, PHY, shot=False, ball_speed_ref=speed_ref)
    assert ball.held_by is None
    assert ball.vel == Vec(PHY["pass_speed"], 0)
    assert ball.bounce_timer == PHY["throw_bounce_timer"]
    assert speed_ref[0] == PHY["pass_speed"]


def test_tackle_probability_formula():
    att = make_player(att=200)
    dfn = make_player(team=2)
    dfn.dir = att.dir  # same facing -> max directional malus for defender? use table
    p = tackle_probability(att, dfn, PHY)
    malus = PHY["tackle_def_malus_by_delta_dir"][0]
    assert p == (200 + 256 - (128 - malus)) // 2


def test_goalkeeper_gets_defense_boost():
    att = make_player(att=128)
    gk = make_player(team=2, position=0)
    fielder = make_player(team=2, position=2)
    assert tackle_probability(att, gk, PHY) < tackle_probability(att, fielder, PHY)


def test_successful_tackle_transfers_ball_and_knocks_down():
    rng = Sb2Rng()          # first byte is 223
    ball = Ball(pos=Vec(320, 576))
    att = make_player(att=255)          # p = (255+256-def_eff)/2 > 223
    dfn = make_player(team=2, pos=Vec(330, 576), **{"def": 0})
    ball.held_by = dfn
    hit = attempt_tackle(att, [dfn], ball, rng, PHY)
    assert hit is dfn
    assert dfn.falling_ticks == PHY["fall_ticks"]
    assert ball.held_by is att
    assert dfn.stats["health"] < 255


def test_out_of_range_tackle_misses():
    rng = Sb2Rng()
    ball = Ball(pos=Vec(320, 576))
    att = make_player()
    dfn = make_player(team=2, pos=Vec(320, 700))
    assert attempt_tackle(att, [dfn], ball, rng, PHY) is None


def test_tackle_damage_floors():
    att = make_player(pow=255)
    dfn = make_player(team=2, sta=0)
    apply_tackle_damage(dfn, att)
    d = (255 + 150 - 0) // 16
    assert dfn.stats["health"] == 255 - d
    assert dfn.stats["spd"] == 128 - max(1, d // 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_actions.py -v` — expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `sim/actions.py`**

```python
"""Possession, throwing, tackling — formulas per docs/spec/mechanics.md."""
from __future__ import annotations

from sim.entities import Ball
from sim.player import PlayerSim
from sim.rng import Sb2Rng
from sim.vec import DIR_VECTORS, Vec


def try_pickup(ball: Ball, p: PlayerSim, physics: dict) -> bool:
    if ball.held_by is not None or p.falling_ticks > 0:
        return False
    if ball.pos.chebyshev(p.pos) > physics["pickup_range"]:
        return False
    ball.held_by = p
    ball.vel = Vec(0, 0)
    ball.bounce_timer = 0
    return True


def throw(ball: Ball, p: PlayerSim, physics: dict, shot: bool,
          ball_speed_ref: list[int]) -> None:
    assert ball.held_by is p
    speed = physics["shot_speed"] if shot else physics["pass_speed"]
    step = DIR_VECTORS[p.dir]
    ball.held_by = None
    ball.dir = p.dir
    ball.vel = Vec(step.x * speed, step.y * speed)
    ball.bounce_timer = physics["throw_bounce_timer"]
    ball_speed_ref[0] = speed


def tackle_probability(attacker: PlayerSim, defender: PlayerSim,
                       physics: dict) -> int:
    d_att = attacker.stats["att"]
    d_def = defender.stats["def"]
    if defender.position == 0:  # goalkeeper defends harder
        d_def = min(255, d_def * physics["goalkeeper_def_multiplier_num"]
                    // physics["goalkeeper_def_multiplier_den"])
    delta_dir = (defender.dir - attacker.dir + 8) & 7
    d_def -= physics["tackle_def_malus_by_delta_dir"][delta_dir]
    if attacker.sliding_ticks > 0:
        d_def -= physics["tackle_malus_sliding"]
    if defender.falling_ticks == 0 and defender.sliding_ticks == 0:
        pass
    return (d_att + 256 - d_def) // 2


def apply_tackle_damage(defender: PlayerSim, attacker: PlayerSim) -> None:
    d = max(1, (attacker.stats["pow"] + 150 - defender.stats["sta"]) // 16)
    defender.stats["health"] = max(0, defender.stats["health"] - d)
    hit = max(1, d // 2)
    for key in ("agr", "att", "def", "spd", "thr", "pow", "sta", "int"):
        defender.stats[key] = max(1, defender.stats[key] - hit)


def attempt_tackle(attacker: PlayerSim, defenders: list[PlayerSim],
                   ball: Ball, rng: Sb2Rng, physics: dict) -> PlayerSim | None:
    for dfn in defenders:
        if dfn.falling_ticks > 0:
            continue
        if attacker.pos.chebyshev(dfn.pos) > physics["tackle_range"]:
            continue
        if rng.next_byte() > tackle_probability(attacker, dfn, physics):
            return None  # rolled and missed: one attempt per trigger
        apply_tackle_damage(dfn, attacker)
        speed = (physics["tackle_knockback_speed_sliding"]
                 if attacker.sliding_ticks > 0
                 else physics["tackle_knockback_speed"])
        step = DIR_VECTORS[attacker.dir]
        dfn.falling_ticks = physics["fall_ticks"]
        dfn.knock_vel = Vec(step.x * speed, step.y * speed)
        dfn.dir = attacker.dir
        if ball.held_by is dfn:
            ball.held_by = None if attacker.falling_ticks > 0 else attacker
        return dfn
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_actions.py -v` — expected: 7 passed. (If `test_tackle_probability_formula` disagrees, check the delta-dir index — `(defender.dir - attacker.dir + 8) & 7` with both dirs 0 gives index 0.)

- [ ] **Step 5: Commit**

```bash
git add sim/actions.py tests/test_actions.py && git commit -m "feat: possession, throwing, and authentic tackle formulas"
```

---

### Task 7: Goals, scoring, multiplier banks (`sim/scoring.py`)

**Files:**
- Create: `sim/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `Ball`, arena/scoring dicts, `Vec`.
- Produces:
  - `ScoreState` — mutable dataclass: `score_team1: int = 0`, `score_team2: int = 0`, `multiplier_team1_ticks: int = 0`, `multiplier_team2_ticks: int = 0` (>0 means that team's next goals score double; decremented each tick by Match).
  - `check_goal(ball: Ball, arena: dict) -> int` — returns 0 (no goal), 1 (team 1 scored, i.e. ball fully crossed the TOP goal line inside the mouth), or 2 (team 2 scored at the BOTTOM). Team 1 attacks the top goal.
  - `award_goal(state: ScoreState, team: int, scoring: dict) -> None` — adds `goal_points` or `goal_points_multiplied` if that team's multiplier is lit.
  - `check_multiplier_banks(ball: Ball, arena: dict, scoring: dict, state: ScoreState, last_thrower_team: int) -> bool` — if the free, moving ball enters a bank rect: stop the ball at the rect edge, light `multiplier_teamN_ticks = multiplier_duration_ticks` for the throwing team, eject the ball horizontally back into play at speed 4, return True.
  - `tick_multipliers(state: ScoreState) -> None` — decrement lit timers.

- [ ] **Step 1: Write the failing tests**

`tests/test_scoring.py`:
```python
from pathlib import Path

from sim.config import load_config
from sim.entities import Ball
from sim.scoring import (ScoreState, award_goal, check_goal,
                         check_multiplier_banks, tick_multipliers)
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_goal_only_inside_mouth():
    in_mouth = Ball(pos=Vec(320, 10))          # top goal, inside mouth
    outside = Ball(pos=Vec(100, 10))           # top line, outside mouth
    midfield = Ball(pos=Vec(320, 576))
    assert check_goal(in_mouth, CFG.arena) == 1
    assert check_goal(outside, CFG.arena) == 0
    assert check_goal(midfield, CFG.arena) == 0
    assert check_goal(Ball(pos=Vec(320, 1145)), CFG.arena) == 2


def test_award_goal_respects_multiplier():
    s = ScoreState()
    award_goal(s, 1, CFG.scoring)
    assert s.score_team1 == CFG.scoring["goal_points"]
    s.multiplier_team1_ticks = 100
    award_goal(s, 1, CFG.scoring)
    assert s.score_team1 == (CFG.scoring["goal_points"]
                             + CFG.scoring["goal_points_multiplied"])


def test_bank_lights_multiplier_and_ejects_ball():
    s = ScoreState()
    bank = CFG.arena["multiplier_banks"][0]
    y = (bank["y_min"] + bank["y_max"]) // 2
    ball = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-6, 0))
    hit = check_multiplier_banks(ball, CFG.arena, CFG.scoring, s,
                                 last_thrower_team=2)
    assert hit
    assert s.multiplier_team2_ticks == CFG.scoring["multiplier_duration_ticks"]
    assert ball.vel.x > 0  # ejected back toward play


def test_multiplier_expires():
    s = ScoreState()
    s.multiplier_team1_ticks = 2
    tick_multipliers(s)
    tick_multipliers(s)
    tick_multipliers(s)
    assert s.multiplier_team1_ticks == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scoring.py -v` — expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `sim/scoring.py`**

```python
"""Goals, score, and the side-wall score-multiplier banks.

Point values and multiplier behavior are data-driven (data/scoring.json)
and marked [tunable — validate] against the reference implementation.
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.entities import Ball
from sim.vec import Vec


@dataclass(slots=True)
class ScoreState:
    score_team1: int = 0
    score_team2: int = 0
    multiplier_team1_ticks: int = 0
    multiplier_team2_ticks: int = 0


def check_goal(ball: Ball, arena: dict) -> int:
    if not (arena["goal_mouth_x_min"] <= ball.pos.x <= arena["goal_mouth_x_max"]):
        return 0
    if ball.pos.y <= arena["goal_depth"]:
        return 1  # crossed top line: team 1 (attacking top) scored
    if ball.pos.y >= arena["height"] - arena["goal_depth"]:
        return 2
    return 0


def award_goal(state: ScoreState, team: int, scoring: dict) -> None:
    lit = (state.multiplier_team1_ticks if team == 1
           else state.multiplier_team2_ticks) > 0
    pts = scoring["goal_points_multiplied"] if lit else scoring["goal_points"]
    if team == 1:
        state.score_team1 += pts
    else:
        state.score_team2 += pts


def check_multiplier_banks(ball: Ball, arena: dict, scoring: dict,
                           state: ScoreState, last_thrower_team: int) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    for bank in arena["multiplier_banks"]:
        if (bank["x_min"] <= ball.pos.x <= bank["x_max"]
                and bank["y_min"] <= ball.pos.y <= bank["y_max"]):
            if last_thrower_team == 1:
                state.multiplier_team1_ticks = scoring["multiplier_duration_ticks"]
            elif last_thrower_team == 2:
                state.multiplier_team2_ticks = scoring["multiplier_duration_ticks"]
            eject = 4 if bank["x_min"] == 0 else -4
            ball.pos = Vec(bank["x_max"] + 8 if eject > 0 else bank["x_min"] - 8,
                           ball.pos.y)
            ball.vel = Vec(eject, 0)
            ball.bounce_timer = 0
            return True
    return False


def tick_multipliers(state: ScoreState) -> None:
    if state.multiplier_team1_ticks > 0:
        state.multiplier_team1_ticks -= 1
    if state.multiplier_team2_ticks > 0:
        state.multiplier_team2_ticks -= 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring.py -v` — expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add sim/scoring.py tests/test_scoring.py && git commit -m "feat: goal detection, scoring, and score-multiplier banks"
```

---

### Task 8: Match orchestration + determinism & purity tests (`sim/match.py`)

**Files:**
- Create: `sim/match.py`
- Test: `tests/test_match.py`, `tests/test_sim_purity.py`

**Interfaces:**
- Consumes: everything from Tasks 2–7.
- Produces:
  - `Match(config: GameConfig, seed: tuple[int, int] | None = None)` — builds ball, 2×9 `PlayerSim` from `teams.json` (formation anchors computed from position: GK at own goal mouth center, DEF row at 1/6 pitch from own goal, MID row at 2/6, ATT row at 3/6; mirror for the other team; kickoff = everyone at anchors, ball at `kickoff_center`), `rng = Sb2Rng(*seed)` (default seed when None), `score = ScoreState()`, `tick_count = 0`, `clock_ticks = leg_duration_ticks`, `ball_speed_ref = [0]`, `last_thrower_team = 0`.
  - `Match.tick(inputs: dict[int, InputState]) -> None` — one fixed step; `inputs` maps *player id* (`team*100+index`) to intent; players without an entry get AI later (Task 9) — for now they get `IDLE`. **Tick order (translated from REF `Match.cs Update`):**
    1. `update_ball_velocity`
    2. `check_multiplier_banks` (+`tick_multipliers`)
    3. recompute every player's distance-to-ball
    4. resolve intents: movement for all; `action_a` = throw pass if holder / attempt tackle if not; `action_b` = shoot if holder / start slide (`sliding_ticks = slide_ticks`) if not; pickup attempts for players near a free ball (closest first)
    5. `check_goal` → on goal: `award_goal`, reset positions to kickoff, ball to center, `ball_speed_ref=[0]`, conceding team gets the ball? No — after a goal the *conceding* team restarts with possession at center (standard SB2 restart) **[tunable — validate]**
    6. `move_and_bounce` ball then all players
    7. if ball held: pin `ball.pos` to holder's pos, set `last_thrower_team` when they throw
    8. `tick_count += 1`; if clock running, `clock_ticks -= 1`
  - `Match.state_hash() -> int` — stable hash over (tick, ball pos/vel, every player pos/vel/dir/health, score, rng state) using only ints (e.g., `hash(tuple(...))` is fine within one process; for cross-process use a rolling sum — implement a deterministic rolling checksum, not builtin `hash`).
  - `Match.is_over -> bool` — `clock_ticks <= 0`.
  - `PLAYER_ID = lambda team, idx: team * 100 + idx` exposed as `player_id(team, idx)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_match.py`:
```python
from pathlib import Path

from sim.config import load_config
from sim.input import InputState
from sim.match import Match, player_id

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_kickoff_layout():
    m = Match(CFG)
    assert len(m.players_team1) == 9
    assert len(m.players_team2) == 9
    assert m.ball.pos.x == CFG.arena["kickoff_center"][0]
    # goalkeepers guard opposite ends
    assert m.players_team1[0].pos.y > m.players_team2[0].pos.y


def test_determinism_same_seed_same_hash_stream():
    def run():
        m = Match(CFG, seed=(42, 1337))
        hashes = []
        for t in range(1000):
            # deterministic scripted input for one player
            m.tick({player_id(1, 4): InputState(dir=t % 8)})
            hashes.append(m.state_hash())
        return hashes

    assert run() == run()


def test_different_seed_diverges():
    def run(seed):
        m = Match(CFG, seed=seed)
        for _ in range(300):
            m.tick({player_id(1, 4): InputState(dir=0, action_a=True)})
        return m.state_hash()

    # tackles consume RNG, so different seeds must eventually diverge
    assert run((1, 2)) != run((99, 100))


def test_scoring_a_goal_resets_and_scores():
    m = Match(CFG, seed=(7, 7))
    # teleport ball into the top goal mouth moving in
    from sim.vec import Vec
    m.ball.pos = Vec(320, 10)
    m.ball.held_by = None
    m.tick({})
    assert m.score.score_team1 == CFG.scoring["goal_points"]
    assert m.ball.pos.x == CFG.arena["kickoff_center"][0]


def test_clock_counts_down_to_over():
    m = Match(CFG, seed=(1, 1))
    m.clock_ticks = 3
    for _ in range(3):
        m.tick({})
    assert m.is_over
```

`tests/test_sim_purity.py`:
```python
import subprocess
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"

FORBIDDEN = ("pygame", "import random", "from random",
             "import time", "from time", "datetime", "urandom")


def test_sim_sources_have_no_forbidden_imports():
    for f in SIM.rglob("*.py"):
        src = f.read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            assert bad not in src, f"{f.name} references {bad!r}"


def test_importing_sim_does_not_load_pygame():
    code = ("import sys; import sim.match; "
            "sys.exit(1 if any(m.startswith('pygame') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_match.py tests/test_sim_purity.py -v` — expected: match tests fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `sim/match.py`**

Follow the tick order above exactly. Key excerpts (write the full class; this is the shape):

```python
from __future__ import annotations

from sim.actions import attempt_tackle, throw, try_pickup
from sim.config import GameConfig
from sim.entities import Ball, move_and_bounce, update_ball_velocity
from sim.input import IDLE, InputState
from sim.player import PlayerSim, apply_movement
from sim.rng import Sb2Rng
from sim.scoring import (ScoreState, award_goal, check_goal,
                         check_multiplier_banks, tick_multipliers)
from sim.vec import Vec


def player_id(team: int, idx: int) -> int:
    return team * 100 + idx


_ROW_FRACTIONS = {0: 18, 1: 3, 2: 6, 3: 2}  # denominator of pitch-height offset
_ROW_XS = {1: (200, 440), 2: (140, 320, 500), 3: (200, 320, 440)}


class Match:
    def __init__(self, config: GameConfig, seed: tuple[int, int] | None = None):
        self.cfg = config
        self.rng = Sb2Rng(*seed) if seed else Sb2Rng()
        self.score = ScoreState()
        self.tick_count = 0
        self.clock_ticks = config.scoring["leg_duration_ticks"]
        self.ball_speed_ref = [0]
        self.last_thrower_team = 0
        self.ball = Ball(pos=Vec(*config.arena["kickoff_center"]))
        self.players_team1 = self._build_team(1)
        self.players_team2 = self._build_team(2)
        self.reset_to_kickoff(possession_team=0)

    # _build_team: read config.teams["teams"][team-1]["players"]; GK home =
    # (arena center x, own goal y ± 40); rows per _ROW_FRACTIONS/_ROW_XS,
    # mirrored vertically for team 1 (defends bottom) vs team 2 (defends top).

    # reset_to_kickoff(possession_team): all players to home anchors, ball to
    # kickoff_center (given to that team's central MID when nonzero),
    # velocities zeroed, bounce timer cleared.

    def all_players(self) -> list[PlayerSim]:
        return self.players_team1 + self.players_team2

    def tick(self, inputs: dict[int, InputState]) -> None:
        arena, phy, sco = self.cfg.arena, self.cfg.physics, self.cfg.scoring
        update_ball_velocity(self.ball, phy, self.ball_speed_ref)
        check_multiplier_banks(self.ball, arena, sco, self.score,
                               self.last_thrower_team)
        tick_multipliers(self.score)

        for p in self.all_players():
            inp = inputs.get(player_id(p.team, p.index), IDLE)
            apply_movement(p, inp, phy)
            if inp.action_a or inp.action_b:
                self._resolve_action(p, inp, phy)

        # pickups: closest eligible player first (deterministic ordering)
        if self.ball.held_by is None:
            for p in sorted(self.all_players(),
                            key=lambda q: (q.pos.chebyshev(self.ball.pos),
                                           q.team, q.index)):
                if try_pickup(self.ball, p, phy):
                    break

        goal = check_goal(self.ball, arena)
        if goal:
            award_goal(self.score, goal, sco)
            self.reset_to_kickoff(possession_team=2 if goal == 1 else 1)
        else:
            move_and_bounce(self.ball, arena, arena["wall_margin_ball"],
                            is_ball=True)
            for p in self.all_players():
                move_and_bounce(p, arena, arena["wall_margin_player"],
                                is_ball=False)
            if self.ball.held_by is not None:
                self.ball.pos = self.ball.held_by.pos
                self.ball.vel = Vec(0, 0)

        self.tick_count += 1
        if self.clock_ticks > 0:
            self.clock_ticks -= 1

    def _resolve_action(self, p: PlayerSim, inp: InputState, phy: dict) -> None:
        holder = self.ball.held_by
        if holder is p:
            self.last_thrower_team = p.team
            throw(self.ball, p, phy, shot=inp.action_b, ball_speed_ref=self.ball_speed_ref)
            return
        if inp.action_b and p.sliding_ticks == 0 and p.falling_ticks == 0:
            p.sliding_ticks = phy["slide_ticks"]
        if holder is not None and holder.team != p.team:
            attempt_tackle(p, [holder], self.ball, self.rng, phy)

    @property
    def is_over(self) -> bool:
        return self.clock_ticks <= 0

    def state_hash(self) -> int:
        acc = 0
        def mix(v: int) -> None:
            nonlocal acc
            acc = (acc * 1000003 + (v & 0xFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
        mix(self.tick_count)
        for v in (self.ball.pos.x, self.ball.pos.y,
                  self.ball.vel.x, self.ball.vel.y, self.ball.bounce_timer):
            mix(v)
        for p in self.all_players():
            for v in (p.pos.x, p.pos.y, p.vel.x, p.vel.y, p.dir,
                      p.falling_ticks, p.stats["health"]):
                mix(v)
        for v in (self.score.score_team1, self.score.score_team2,
                  self.rng.a, self.rng.b):
            mix(v)
        return acc
```

Implement `_build_team` and `reset_to_kickoff` fully per the comments (they are described precisely in the Interfaces block above — GK first, then rows; team 1 anchors in the bottom half, team 2 mirrored to the top half: `mirror_y(y) = arena height - y`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_match.py tests/test_sim_purity.py -v`
Expected: 7 passed. The determinism test is the critical one — if it flakes, hunt for iteration over unordered collections or use of builtin `hash` on strings.

- [ ] **Step 5: Run the whole suite and commit**

Run: `python -m pytest -q` — expected: all green.

```bash
git add sim/match.py tests/test_match.py tests/test_sim_purity.py
git commit -m "feat: deterministic match orchestration with state-hash and purity tests"
```

---

### Task 9: CPU AI (`sim/ai.py`)

**Files:**
- Create: `sim/ai.py`
- Modify: `sim/match.py` (fill missing inputs from AI instead of IDLE)
- Test: `tests/test_ai.py`

The authentic AI lives in REF `Player.cs` (`Think`, `sub_D742_AII` and its ~60 helpers keyed by `_pThink` addresses) — a full translation is its own project. **MVP approach:** implement a faithful *baseline* AI here using the same decision inputs the original uses (distance-to-ball, zone anchors, stats, RNG rolls), structured so behaviors can be swapped for exact translations later. Keep the module's decision functions small and named after the behavior (`decide_goalkeeper`, `decide_chase`, `decide_carry`, `decide_support`, `decide_defend`) so later fidelity passes replace one function at a time against REF.

**Interfaces:**
- Consumes: `Match` state (read-only), `Sb2Rng` (the match's — AI rolls MUST come from the match RNG to stay deterministic), `InputState`, `dir_towards`.
- Produces: `compute_ai_inputs(match, controlled_ids: set[int]) -> dict[int, InputState]` — an InputState for every player NOT in `controlled_ids`.
- Modify `Match.tick` signature contract: `tick(inputs)` stays, but `present`/tests call `compute_ai_inputs` first and merge: `full = compute_ai_inputs(m, set(inputs)) | inputs`. Add convenience `Match.tick_with_ai(human_inputs: dict[int, InputState]) -> None` that does exactly that merge then calls `tick`.

Behavior rules (complete logic — implement as written):
- **Goalkeeper (position 0):** stay on own goal line y; track `ball.pos.x` clamped to the goal mouth ± 16; if ball free and within 60 units, chase it; if holding the ball, immediately pass (action_a) toward the nearest MID teammate's direction.
- **Ball free:** the two players per team closest to the ball chase it (`dir_towards(p.pos, ball.pos)`); everyone else runs `decide_support`.
- **Own team holds ball:**
  - holder (`decide_carry`): run toward the opponent goal mouth center; if within `shot_range = 260` **[tunable — validate]** of the goal line, `action_b` (shoot) — but first, once per possession, roll `rng.next_byte()`; if `< p.stats["int"]`, prefer a pass (`action_a`) when an unmarked teammate (no opponent within 40) is nearer the goal. Track "once per possession" with `match._ai_possession_rolled: bool` reset whenever `ball.held_by` changes (store previous holder on the match).
  - others (`decide_support`): run toward home anchor shifted 1/4 of the way toward the ball (`anchor + (ball - anchor) scaled by //4`).
- **Opponent holds ball (`decide_defend`):** the two defenders closest to the holder run at the holder and fire `action_a` when within `tackle_range` (the tackle roll itself consumes match RNG in `attempt_tackle`); the GK and the rest run `decide_support`.
- All chase/defend target selection must sort with deterministic tie-breakers `(distance, team, index)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_ai.py`:
```python
from pathlib import Path

from sim.ai import compute_ai_inputs
from sim.config import load_config
from sim.match import Match, player_id

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_ai_covers_all_uncontrolled_players():
    m = Match(CFG, seed=(5, 5))
    human = {player_id(1, 4)}
    inputs = compute_ai_inputs(m, human)
    assert set(inputs) == {player_id(p.team, p.index)
                           for p in m.all_players()} - human


def test_ai_vs_ai_match_is_deterministic_and_produces_play():
    def run():
        m = Match(CFG, seed=(2026, 713))
        touches = 0
        for _ in range(6000):  # 2 in-game minutes
            held_before = m.ball.held_by
            m.tick_with_ai({})
            if m.ball.held_by is not held_before:
                touches += 1
        return m.state_hash(), touches, m.score.score_team1 + m.score.score_team2

    r1, r2 = run(), run()
    assert r1 == r2                    # deterministic
    assert r1[1] > 10                  # possession actually changes hands
    # scoring is not guaranteed in 2 minutes, but the sim must not deadlock:
    assert r1[0] != 0


def test_ai_chases_free_ball():
    m = Match(CFG, seed=(3, 3))
    m.ball.held_by = None
    before = min(p.pos.chebyshev(m.ball.pos) for p in m.players_team2)
    for _ in range(30):
        m.tick_with_ai({})
    after = min(p.pos.chebyshev(m.ball.pos) for p in m.players_team2)
    assert after <= before
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai.py -v` — expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `sim/ai.py` and `Match.tick_with_ai`**

Implement exactly the behavior rules above. Skeleton:

```python
"""Baseline CPU AI using the original's decision inputs.

Each decide_* function mirrors a behavior family in the reference AI
(REF Player.cs Think dispatch). Replace individual functions with exact
translations during fidelity passes — keep signatures stable.
"""
from __future__ import annotations

from sim.input import InputState
from sim.match import Match, player_id
from sim.player import PlayerSim
from sim.vec import Vec, dir_towards


def compute_ai_inputs(match: Match, controlled: set[int]) -> dict[int, InputState]:
    out: dict[int, InputState] = {}
    for p in match.all_players():
        pid = player_id(p.team, p.index)
        if pid in controlled:
            continue
        out[pid] = _decide(match, p)
    return out
```

with `_decide` dispatching per the rules (goalkeeper / free-ball chase / carry / support / defend). `shot_range: 260` goes into `data/physics.json` as `"ai_shot_range": 260`, and unmarked radius as `"ai_unmarked_radius": 40`. Add `Match.tick_with_ai`:

```python
def tick_with_ai(self, human_inputs: dict[int, InputState]) -> None:
    from sim.ai import compute_ai_inputs  # local import: no cycle at module load
    ai = compute_ai_inputs(self, set(human_inputs))
    self.tick(ai | human_inputs)
```

Also track possession changes on the match for the once-per-possession pass roll: in `tick`, before returning, compare `self.ball.held_by` with `self._prev_holder`; on change set `self._ai_possession_rolled = False` and update `_prev_holder`. Initialize both in `__init__` (`None` / `False`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai.py -v` — expected: 3 passed. If the AI-vs-AI test shows fewer than 10 possession changes, tackle triggering is the usual culprit: confirm defenders fire `action_a` inside `tackle_range` and that `attempt_tackle` receives the holder.

- [ ] **Step 5: Run full suite and commit**

Run: `python -m pytest -q` — all green.

```bash
git add sim/ai.py sim/match.py tests/test_ai.py data/physics.json
git commit -m "feat: deterministic baseline CPU AI with swappable behavior functions"
```

---

### Task 10: Presentation layer (`present/`)

**Files:**
- Create: `present/app.py`, `present/renderer.py`, `present/hud.py`, `present/input_map.py`

No sim changes allowed in this task. Rendering uses placeholder primitives; if `assets/sprites/` exists (Task 11), the renderer uses those PNGs instead.

**Interfaces:**
- Consumes: `Match`, `InputState`, `player_id`, `load_config`.
- Produces: `python -m present.app` opens a 640×480 window (1 terrain unit = 1 px, camera-scrolled) running the match at fixed 50 Hz.

- [ ] **Step 1: `present/input_map.py`**

```python
"""Keyboard -> InputState. Human controls the team-1 player nearest the ball
(original 'auto-switch' behavior); manual switch on Tab."""
from __future__ import annotations

import pygame

from sim.input import InputState
from sim.match import Match, player_id

_DIR_FROM_KEYS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}


def read_input() -> InputState | None:
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
    d = _DIR_FROM_KEYS.get((dx, dy))
    return InputState(dir=d,
                      action_a=keys[pygame.K_SPACE],
                      action_b=keys[pygame.K_LSHIFT])


def pick_controlled_player(match: Match) -> int:
    """Team-1 outfielder nearest the ball; holder wins outright."""
    holder = match.ball.held_by
    if holder is not None and holder.team == 1:
        return player_id(1, holder.index)
    best = min((p for p in match.players_team1 if p.position != 0),
               key=lambda p: (p.pos.chebyshev(match.ball.pos), p.index))
    return player_id(1, best.index)
```

- [ ] **Step 2: `present/renderer.py`**

Placeholder rendering (complete): dark pitch background with center line/circle and goal mouths drawn from `arena.json`; multiplier banks as yellow rects (bright when lit); players as 12px circles (team 1 steel blue, team 2 crimson, GK ringed white, controlled player ringed yellow, falling players drawn flattened as ellipses); ball as 8px white circle (grey when held). Camera: `camera_y = clamp(focus.y - 240, 0, 1152 - 480)` and `camera_x = clamp(focus.x - 320, 0, 640 - 640) = 0` (pitch is exactly window-wide at 1:1; keep the clamp anyway so window resizing later stays correct); focus = holder or ball (matches REF's `CenterScreenOnEntity`). If `Path("assets/sprites").exists()`, blit `player_t1.png`, `player_t2.png`, `ball.png` at entity positions instead of circles (same camera math).

Write the module with functions `draw_frame(screen, match, controlled_pid, font) -> None` and internal helpers; no game logic — read match state only.

- [ ] **Step 3: `present/hud.py`**

`draw_hud(screen, match, font)`: top strip 640×24, `"T1 {score}  {mm}:{ss}  {score} T2"` using `clock_ticks // 50` seconds remaining; when a team's multiplier is lit, render that team's score in yellow and append `"x2"`.

- [ ] **Step 4: `present/app.py` — fixed-timestep loop**

```python
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
```

- [ ] **Step 5: Manual verification (definition-of-done rehearsal)**

Run: `python -m present.app`
Verify each, fixing before proceeding: window opens and pitch scrolls following the ball · arrows/WASD move the highlighted player · Space passes when holding, tackles nearby · Shift shoots · CPU team chases, passes, and can score · goals update the HUD and reset to kickoff · clock counts down and the app exits at full time. (If a display is unavailable in this environment, set `SDL_VIDEODRIVER=dummy` and assert the loop runs 500 ticks without exception, then flag the interactive check as pending user verification — do not claim it verified.)

- [ ] **Step 6: Run full suite (must stay green — presentation must not break sim tests), commit**

```bash
python -m pytest -q
git add present/ && git commit -m "feat: pygame presentation — scrolling pitch, HUD, human control at fixed 50Hz"
```

---

### Task 11: Asset extraction tool with fallback (`tools/extract_assets.py`)

**Files:**
- Create: `tools/extract_assets.py`, `docs/assets.md`
- Modify: `present/renderer.py` only if sprite loading needs a tweak — no sim changes.

**Interfaces:**
- Produces: `python -m tools.extract_assets [path-to-game-copy]` → populates gitignored `assets/sprites/` or, with `--placeholders`, generates original placeholder PNGs so the game has sprite-path coverage without any game files.

Reality check (documented, not discovered): full sprite ripping from the Amiga ADF requires the Rust tools in `simon-frankau/speedball2-re` (Megadrive ROM) — porting them is post-MVP. The MVP tool must therefore: (1) generate procedural placeholder sprites (our own original art: simple shaded-circle player discs in team colors with position letters, a shaded ball) so the sprite pipeline is exercised end-to-end, and (2) scaffold + document the real extraction path.

- [ ] **Step 1: Implement `tools/extract_assets.py`**

Complete behavior:
- `--placeholders` (default when no path given): use pygame's `Surface` offscreen (`SDL_VIDEODRIVER=dummy` set inside the script before `pygame.init()`) to draw and save `assets/sprites/player_t1.png`, `player_t2.png`, `ball.png` (16×16, our own art). Print what was written.
- With a path argument: verify the file exists; detect type by extension (`.adf`, `.bin`/`.md` ROM); print precise instructions: clone `simon-frankau/speedball2-re`, run its `tools/` extractors against the ROM, copy outputs into `assets/sprites/` with the expected filenames. Exit code 0 with instructions is correct behavior for MVP (documented in `docs/assets.md`); it must NOT pretend to extract.
- Always end by listing `assets/sprites/` contents.

- [ ] **Step 2: `docs/assets.md`**

Document: the asset policy (never committed), the placeholder mode, the real extraction path via the upstream RE tools, expected filenames the renderer looks for, and that `Resources/` in this working directory is the user's own material and is gitignored.

- [ ] **Step 3: Verify**

Run: `python -m tools.extract_assets --placeholders` → three PNGs appear under `assets/sprites/`; `git status` shows **no** new tracked files (gitignore working). Run `python -m present.app` briefly (or dummy-driver smoke) to confirm the renderer picks up sprite mode without crashing.

- [ ] **Step 4: Commit**

```bash
git add tools/extract_assets.py docs/assets.md
git commit -m "feat: asset extraction tool with placeholder fallback and documented rip path"
```

---

### Task 12: Final verification & DoD audit

**Files:**
- Modify: `README.md` (fill in anything that drifted), `docs/spec/mechanics.md` (final tunables list)

- [ ] **Step 1: Full test suite**

Run: `python -m pytest -q` — all green. Record the count in the commit message.

- [ ] **Step 2: DoD checklist against the brief — verify each with a command or a play session:**

1. Window shows scrolling pitch ✅ (Task 10 step 5)
2. Human moves a player, contests ball, scores ✅ (play)
3. CPU plays (chases/passes/tackles/scores) ✅ (play + `test_ai_vs_ai...`)
4. Fixed timestep + seedable RNG ✅ (`test_determinism_same_seed_same_hash_stream`)
5. Sim core has no rendering imports ✅ (`test_sim_purity.py`)
6. Headless unit tests pass ✅ (suite)
7. Data-driven configs ✅ (`data/*.json`, grep sim/ for magic gameplay numbers)
8. README states stack + asset policy; LICENSE is GPLv3 ✅ (read them)

- [ ] **Step 3: Note post-MVP roadmap in README** (short section): AI fidelity passes against REF `Player.cs` · remaining arena furniture (stars, bounce domes, electrobounces, warp gates — REF classes exist for each) · sound · management layer · league/cup + saves · menus · **online multiplayer via lockstep on the deterministic core (exchange `InputState` dicts per tick + periodic `state_hash()` cross-checks)** · register on osgameclones.com + awesome-game-remakes.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "docs: v1 definition-of-done audit and post-MVP roadmap"
```

---

## Post-MVP backlog (explicitly out of scope for this plan)

In priority order, each a future plan of its own:
1. **AI fidelity**: translate REF `Player.cs` think-dispatch behaviors one function at a time, validated frame-by-frame against `bin/Speedball 2.exe` with matched seeds.
2. **Arena furniture**: stars, bounce domes, electrobounces, warp gates, coins/tokens (REF has a class per item).
3. **Sound** (extraction tools exist upstream).
4. **Management layer**: gym, transfers, injuries (Megadrive RE covers the gym).
5. **League/cup + save system.**
6. **Menus/UI.**
7. **Online multiplayer**: lockstep first (deterministic core makes this input-exchange + hash-verify), rollback later.
