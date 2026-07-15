# Arena Furniture (Tier 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement bounce domes, electrobounces, and star banks — the first
tier of Post-MVP roadmap item #2 ("arena furniture") — as deterministic,
data-driven sim mechanics with placeholder rendering.

**Architecture:** A new `sim/furniture.py` module (parallel to
`sim/scoring.py`) holds a `FurnitureState` dataclass plus one `check_*`
function per item. `Match.tick()` calls these once per tick, right after the
existing multiplier-bank check, using the same "live free ball" trigger
condition already established by `check_multiplier_banks`. Placement/point
values are data-driven (`data/arena.json`, `data/scoring.json`,
`data/physics.json`). `present/renderer.py` gets placeholder-shape drawing
for all three, following the existing primitive-shapes convention.

**Tech Stack:** Python 3.11+, pygame-ce (present-layer only), pytest.

## Global Constraints

- `sim/` stays render-free, wall-clock-free, and free of OS randomness —
  no pygame imports, no `time`/`random` module usage in `sim/furniture.py`
  or `sim/match.py`.
- All tunable numbers (positions, radii, speeds, point values) live in
  `data/*.json`, never hardcoded in `sim/` — matches the existing pattern
  in `data/arena.json`/`data/physics.json`/`data/scoring.json`.
- Distance checks use Chebyshev distance (`Vec.chebyshev`), matching every
  existing range check in this codebase (`pickup_range`, `tackle_range`,
  AI thresholds) — not Euclidean.
- Token/warp-gate pickups are explicitly out of scope for this plan (see
  `docs/superpowers/specs/2026-07-14-arena-furniture-design.md`).
- Full test suite (`python -m pytest`) must stay green after every task.

---

## File Structure

- **Modify** `data/arena.json` — add `bounce_domes`, `electrobounces`,
  `star_banks`.
- **Modify** `data/physics.json` — add `dome_bounce_speed`,
  `electrobounce_speed`, `electrobounce_range`.
- **Modify** `data/scoring.json` — add `dome_bonus_points`,
  `star_bonus_points`, `star_row_bonus_points`.
- **Modify** `tests/test_config.py` — smoke-test the new data loads.
- **Create** `sim/furniture.py` — `FurnitureState`, `check_bounce_domes`,
  `check_electrobounces`, `tick_electrobounce_flash`, `check_star_banks`.
- **Create** `tests/test_furniture.py` — unit tests for all four functions.
- **Modify** `sim/match.py` — wire `FurnitureState` into `Match`, call the
  three checks in `tick()`, mix furniture state into `state_hash()`.
- **Modify** `tests/test_match.py` — integration tests via `Match.tick()`.
- **Modify** `present/renderer.py` — placeholder shapes for all three items.

---

### Task 1: Data — arena/physics/scoring JSON

**Files:**
- Modify: `data/arena.json`, `data/physics.json`, `data/scoring.json`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `cfg.arena["bounce_domes"]` (list of `{"pos": [x, y], "radius": int}`),
  `cfg.arena["electrobounces"]` (list of `{"pos": [x, y], "wall": "left"|"right"}`),
  `cfg.arena["star_banks"]` (list of `{"team": int, "x_min": int, "x_max": int,
  "y_min": int, "y_max": int, "count": int}`), `cfg.physics["dome_bounce_speed"]`,
  `cfg.physics["electrobounce_speed"]`, `cfg.physics["electrobounce_range"]`,
  `cfg.scoring["dome_bonus_points"]`, `cfg.scoring["star_bonus_points"]`,
  `cfg.scoring["star_row_bonus_points"]`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py` (after `test_load_config_shapes`):

```python
def test_furniture_data_shapes():
    cfg = load_config(DATA)
    assert len(cfg.arena["bounce_domes"]) == 2
    for dome in cfg.arena["bounce_domes"]:
        assert len(dome["pos"]) == 2
        assert dome["radius"] > 0

    assert len(cfg.arena["electrobounces"]) == 2
    walls = {p["wall"] for p in cfg.arena["electrobounces"]}
    assert walls == {"left", "right"}

    assert len(cfg.arena["star_banks"]) == 2
    teams = {b["team"] for b in cfg.arena["star_banks"]}
    assert teams == {1, 2}
    for bank in cfg.arena["star_banks"]:
        assert bank["count"] == 5

    assert cfg.physics["dome_bounce_speed"] > 0
    assert cfg.physics["electrobounce_speed"] > 0
    assert cfg.physics["electrobounce_range"] > 0

    assert cfg.scoring["dome_bonus_points"] > 0
    assert cfg.scoring["star_bonus_points"] > 0
    assert cfg.scoring["star_row_bonus_points"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py::test_furniture_data_shapes -v`
Expected: FAIL with `KeyError: 'bounce_domes'`

- [ ] **Step 3: Add the new data**

Edit `data/arena.json` — insert after the `"multiplier_banks"` array (before
the closing `}`):

```json
  "bounce_domes": [
    { "pos": [320, 96],   "radius": 16 },
    { "pos": [320, 1056], "radius": 16 }
  ],
  "electrobounces": [
    { "pos": [16, 560],  "wall": "left" },
    { "pos": [624, 560], "wall": "right" }
  ],
  "star_banks": [
    { "team": 1, "x_min": 0,   "x_max": 24,  "y_min": 160, "y_max": 320, "count": 5 },
    { "team": 2, "x_min": 616, "x_max": 640, "y_min": 832, "y_max": 992, "count": 5 }
  ]
```

(All positions are placeholders — `[tunable — validate]` per
`docs/superpowers/specs/2026-07-14-arena-furniture-design.md` — refine later
via the frame-trace harness.)

Edit `data/physics.json` — add three keys (comma after the last existing key,
`"ai_unmarked_radius": 40`):

```json
  "dome_bounce_speed": 8,
  "electrobounce_speed": 8,
  "electrobounce_range": 16
```

Edit `data/scoring.json` — add three keys (comma after
`"leg_duration_ticks": 13500`):

```json
  "dome_bonus_points": 2,
  "star_bonus_points": 2,
  "star_row_bonus_points": 10
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (all tests in the file, including the new one)

- [ ] **Step 5: Commit**

```bash
git add data/arena.json data/physics.json data/scoring.json tests/test_config.py
git commit -m "data: add tier-1 arena furniture placement and tuning values"
```

---

### Task 2: Bounce domes (`sim/furniture.py`)

**Files:**
- Create: `sim/furniture.py`
- Test: `tests/test_furniture.py`

**Interfaces:**
- Consumes: `sim.entities.Ball`, `sim.scoring.ScoreState`, `sim.vec.Vec`,
  `sim.vec.DIR_VECTORS`, `sim.vec.dir_towards` (all existing).
- Produces: `FurnitureState` dataclass (`lit_stars_team1: int = 0`,
  `lit_stars_team2: int = 0`, `electrobounce_flash_ticks: int = 0`);
  `check_bounce_domes(ball: Ball, arena: dict, physics: dict,
  last_thrower_team: int, score: ScoreState, scoring: dict) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_furniture.py`:

```python
from pathlib import Path

from sim.config import load_config
from sim.entities import Ball
from sim.furniture import FurnitureState, check_bounce_domes
from sim.scoring import ScoreState
from sim.vec import Vec

CFG = load_config(Path(__file__).resolve().parent.parent / "data")


def test_bounce_dome_reflects_ball_and_scores():
    dome = CFG.arena["bounce_domes"][0]
    center = Vec(*dome["pos"])
    ball = Ball(pos=Vec(center.x, center.y - dome["radius"]), vel=Vec(0, -4))
    score = ScoreState()
    hit = check_bounce_domes(ball, CFG.arena, CFG.physics, 1, score, CFG.scoring)
    assert hit
    assert score.score_team1 == CFG.scoring["dome_bonus_points"]
    assert ball.pos.chebyshev(center) == dome["radius"]
    assert ball.vel != Vec(0, 0)


def test_bounce_dome_ignores_held_or_stationary_ball():
    dome = CFG.arena["bounce_domes"][0]
    center = Vec(*dome["pos"])
    score = ScoreState()
    held = Ball(pos=center, vel=Vec(0, 0), held_by=object())
    assert not check_bounce_domes(held, CFG.arena, CFG.physics, 1, score, CFG.scoring)
    stationary = Ball(pos=center, vel=Vec(0, 0))
    assert not check_bounce_domes(stationary, CFG.arena, CFG.physics, 1, score, CFG.scoring)
    assert score.score_team1 == 0


def test_bounce_dome_no_score_when_no_thrower():
    dome = CFG.arena["bounce_domes"][0]
    center = Vec(*dome["pos"])
    ball = Ball(pos=center, vel=Vec(0, -4))
    score = ScoreState()
    hit = check_bounce_domes(ball, CFG.arena, CFG.physics, 0, score, CFG.scoring)
    assert hit
    assert score.score_team1 == 0
    assert score.score_team2 == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_furniture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sim.furniture'`

- [ ] **Step 3: Write the minimal implementation**

Create `sim/furniture.py`:

```python
"""Arena furniture: bounce domes, electrobounces, star banks.

Tier-1 furniture per
docs/superpowers/specs/2026-07-14-arena-furniture-design.md. Token/warp-gate
pickups are a separate, future design and out of scope here.

All three effects trigger on a live free ball (held_by is None and
vel != (0, 0)) — the same condition sim/scoring.py's check_multiplier_banks
already uses. Range checks use Chebyshev distance, matching every other
range check in this codebase (pickup_range, tackle_range, AI thresholds).
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.entities import Ball
from sim.scoring import ScoreState
from sim.vec import DIR_VECTORS, Vec, dir_towards


@dataclass(slots=True)
class FurnitureState:
    lit_stars_team1: int = 0
    lit_stars_team2: int = 0
    electrobounce_flash_ticks: int = 0


def _add_score(score: ScoreState, team: int, points: int) -> None:
    if team == 1:
        score.score_team1 += points
    else:
        score.score_team2 += points


def check_bounce_domes(ball: Ball, arena: dict, physics: dict,
                       last_thrower_team: int, score: ScoreState,
                       scoring: dict) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    for dome in arena["bounce_domes"]:
        center = Vec(*dome["pos"])
        if ball.pos.chebyshev(center) > dome["radius"]:
            continue
        d = dir_towards(center, ball.pos)
        step = DIR_VECTORS[d]
        speed = physics["dome_bounce_speed"]
        ball.pos = Vec(center.x + step.x * dome["radius"],
                       center.y + step.y * dome["radius"])
        ball.vel = Vec(step.x * speed, step.y * speed)
        ball.dir = d
        ball.bounce_timer = 0
        if last_thrower_team in (1, 2):
            _add_score(score, last_thrower_team, scoring["dome_bonus_points"])
        return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_furniture.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add sim/furniture.py tests/test_furniture.py
git commit -m "feat: bounce dome collision and scoring"
```

---

### Task 3: Electrobounces (`sim/furniture.py`)

**Files:**
- Modify: `sim/furniture.py`
- Modify: `tests/test_furniture.py`

**Interfaces:**
- Consumes: `FurnitureState` (Task 2).
- Produces: `check_electrobounces(ball: Ball, arena: dict, physics: dict,
  furniture: FurnitureState) -> bool`; `tick_electrobounce_flash(furniture:
  FurnitureState) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_furniture.py` (update the import line first):

```python
from sim.furniture import (FurnitureState, check_bounce_domes,
                           check_electrobounces, tick_electrobounce_flash)
```

Then append:

```python
def test_electrobounce_teleports_left_hit_to_right_plate():
    left, right = CFG.arena["electrobounces"]
    ball = Ball(pos=Vec(*left["pos"]), vel=Vec(-4, 0))
    furniture = FurnitureState()
    hit = check_electrobounces(ball, CFG.arena, CFG.physics, furniture)
    assert hit
    assert ball.pos.x == right["pos"][0]
    assert ball.vel.x < 0  # pushed away from the right wall, back onto the pitch
    assert furniture.electrobounce_flash_ticks == 2


def test_electrobounce_teleports_right_hit_to_left_plate():
    left, right = CFG.arena["electrobounces"]
    ball = Ball(pos=Vec(*right["pos"]), vel=Vec(4, 0))
    furniture = FurnitureState()
    hit = check_electrobounces(ball, CFG.arena, CFG.physics, furniture)
    assert hit
    assert ball.pos.x == left["pos"][0]
    assert ball.vel.x > 0  # pushed away from the left wall, back onto the pitch


def test_electrobounce_ignores_held_or_stationary_ball():
    left, _ = CFG.arena["electrobounces"]
    furniture = FurnitureState()
    held = Ball(pos=Vec(*left["pos"]), vel=Vec(0, 0), held_by=object())
    assert not check_electrobounces(held, CFG.arena, CFG.physics, furniture)
    stationary = Ball(pos=Vec(*left["pos"]), vel=Vec(0, 0))
    assert not check_electrobounces(stationary, CFG.arena, CFG.physics, furniture)


def test_tick_electrobounce_flash_counts_down_and_floors_at_zero():
    furniture = FurnitureState(electrobounce_flash_ticks=2)
    tick_electrobounce_flash(furniture)
    assert furniture.electrobounce_flash_ticks == 1
    tick_electrobounce_flash(furniture)
    assert furniture.electrobounce_flash_ticks == 0
    tick_electrobounce_flash(furniture)
    assert furniture.electrobounce_flash_ticks == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_furniture.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_electrobounces'`

- [ ] **Step 3: Write the minimal implementation**

Append to `sim/furniture.py`:

```python
def check_electrobounces(ball: Ball, arena: dict, physics: dict,
                         furniture: FurnitureState) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    plates = arena["electrobounces"]
    hit_range = physics["electrobounce_range"]
    for plate in plates:
        pos = Vec(*plate["pos"])
        if ball.pos.chebyshev(pos) > hit_range:
            continue
        other = next(p for p in plates if p is not plate)
        speed = physics["electrobounce_speed"]
        push = -speed if plate["wall"] == "left" else speed
        ball.pos = Vec(other["pos"][0], ball.pos.y)
        ball.vel = Vec(push, 0)
        ball.bounce_timer = 0
        furniture.electrobounce_flash_ticks = 2
        return True
    return False


def tick_electrobounce_flash(furniture: FurnitureState) -> None:
    if furniture.electrobounce_flash_ticks > 0:
        furniture.electrobounce_flash_ticks -= 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_furniture.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add sim/furniture.py tests/test_furniture.py
git commit -m "feat: electrobounce wall-to-wall ball teleport"
```

---

### Task 4: Star banks (`sim/furniture.py`)

**Files:**
- Modify: `sim/furniture.py`
- Modify: `tests/test_furniture.py`

**Interfaces:**
- Consumes: `FurnitureState`, `_add_score` (Task 2, internal).
- Produces: `check_star_banks(ball: Ball, arena: dict, scoring: dict,
  furniture: FurnitureState, score: ScoreState, last_thrower_team: int) -> bool`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_furniture.py` (update the import line first):

```python
from sim.furniture import (FurnitureState, check_bounce_domes,
                           check_electrobounces, check_star_banks,
                           tick_electrobounce_flash)
```

Then append:

```python
def test_star_bank_lights_own_star_once():
    bank = CFG.arena["star_banks"][0]  # team 1, left wall
    y = bank["y_min"] + 1
    furniture = FurnitureState()
    score = ScoreState()
    ball = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    hit = check_star_banks(ball, CFG.arena, CFG.scoring, furniture, score,
                           last_thrower_team=1)
    assert hit
    assert furniture.lit_stars_team1 == 0b00001
    assert score.score_team1 == CFG.scoring["star_bonus_points"]

    ball2 = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    check_star_banks(ball2, CFG.arena, CFG.scoring, furniture, score,
                     last_thrower_team=1)
    assert score.score_team1 == CFG.scoring["star_bonus_points"]  # not re-awarded


def test_star_bank_knocks_out_opponent_lit_star():
    bank = CFG.arena["star_banks"][0]  # team 1
    y = bank["y_min"] + 1
    furniture = FurnitureState()
    score = ScoreState()
    lit = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    check_star_banks(lit, CFG.arena, CFG.scoring, furniture, score,
                     last_thrower_team=1)
    assert score.score_team1 == CFG.scoring["star_bonus_points"]

    knockout = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
    hit = check_star_banks(knockout, CFG.arena, CFG.scoring, furniture, score,
                           last_thrower_team=2)
    assert hit
    assert furniture.lit_stars_team1 == 0
    assert score.score_team1 == 0


def test_star_bank_full_row_awards_bonus_and_clears():
    bank = CFG.arena["star_banks"][0]  # team 1
    band_height = (bank["y_max"] - bank["y_min"]) // bank["count"]
    furniture = FurnitureState()
    score = ScoreState()
    for i in range(bank["count"]):
        y = bank["y_min"] + i * band_height + 1
        ball = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0))
        check_star_banks(ball, CFG.arena, CFG.scoring, furniture, score,
                         last_thrower_team=1)
    assert furniture.lit_stars_team1 == 0
    expected = (CFG.scoring["star_bonus_points"] * bank["count"]
               + CFG.scoring["star_row_bonus_points"])
    assert score.score_team1 == expected


def test_star_bank_ignores_held_or_stationary_ball():
    bank = CFG.arena["star_banks"][0]
    y = bank["y_min"] + 1
    furniture = FurnitureState()
    score = ScoreState()
    held = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(-4, 0), held_by=object())
    assert not check_star_banks(held, CFG.arena, CFG.scoring, furniture, score,
                                last_thrower_team=1)
    stationary = Ball(pos=Vec(bank["x_max"] - 2, y), vel=Vec(0, 0))
    assert not check_star_banks(stationary, CFG.arena, CFG.scoring, furniture,
                                score, last_thrower_team=1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_furniture.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_star_banks'`

- [ ] **Step 3: Write the minimal implementation**

Append to `sim/furniture.py`:

```python
def _star_mask(furniture: FurnitureState, team: int) -> int:
    return furniture.lit_stars_team1 if team == 1 else furniture.lit_stars_team2


def _set_star_mask(furniture: FurnitureState, team: int, mask: int) -> None:
    if team == 1:
        furniture.lit_stars_team1 = mask
    else:
        furniture.lit_stars_team2 = mask


def _star_band_index(ball: Ball, bank: dict) -> int:
    band_height = (bank["y_max"] - bank["y_min"]) // bank["count"]
    idx = (ball.pos.y - bank["y_min"]) // band_height
    return min(bank["count"] - 1, max(0, idx))


def _light_star(furniture: FurnitureState, bank: dict, idx: int,
                score: ScoreState, scoring: dict) -> None:
    team = bank["team"]
    mask = _star_mask(furniture, team)
    if mask & (1 << idx):
        return
    mask |= (1 << idx)
    _add_score(score, team, scoring["star_bonus_points"])
    full_mask = (1 << bank["count"]) - 1
    if mask == full_mask:
        _add_score(score, team, scoring["star_row_bonus_points"])
        mask = 0
    _set_star_mask(furniture, team, mask)


def _unlight_star(furniture: FurnitureState, bank: dict, idx: int,
                  score: ScoreState, scoring: dict) -> None:
    team = bank["team"]
    mask = _star_mask(furniture, team)
    if not (mask & (1 << idx)):
        return
    mask &= ~(1 << idx)
    _add_score(score, team, -scoring["star_bonus_points"])
    _set_star_mask(furniture, team, mask)


def check_star_banks(ball: Ball, arena: dict, scoring: dict,
                     furniture: FurnitureState, score: ScoreState,
                     last_thrower_team: int) -> bool:
    if ball.held_by is not None or ball.vel == Vec(0, 0):
        return False
    for bank in arena["star_banks"]:
        if not (bank["x_min"] <= ball.pos.x <= bank["x_max"]
                and bank["y_min"] <= ball.pos.y <= bank["y_max"]):
            continue
        idx = _star_band_index(ball, bank)
        if last_thrower_team == bank["team"]:
            _light_star(furniture, bank, idx, score, scoring)
        elif last_thrower_team in (1, 2):
            _unlight_star(furniture, bank, idx, score, scoring)
        eject = 4 if bank["x_max"] <= arena["width"] // 2 else -4
        ball.pos = Vec(bank["x_max"] + 8 if eject > 0 else bank["x_min"] - 8,
                       ball.pos.y)
        ball.vel = Vec(eject, 0)
        ball.bounce_timer = 0
        return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_furniture.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add sim/furniture.py tests/test_furniture.py
git commit -m "feat: star bank lighting, knockout, and full-row bonus"
```

---

### Task 5: Wire furniture into `Match.tick()`

**Files:**
- Modify: `sim/match.py`
- Test: `tests/test_match.py`

**Interfaces:**
- Consumes: `sim.furniture.FurnitureState`, `check_bounce_domes`,
  `check_electrobounces`, `tick_electrobounce_flash`, `check_star_banks`
  (Tasks 2-4).
- Produces: `Match.furniture: FurnitureState` (new public attribute).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_match.py`:

```python
def test_bounce_dome_integration_via_tick():
    m = Match(CFG, seed=(5, 5))
    dome = CFG.arena["bounce_domes"][0]
    from sim.vec import Vec
    m.ball.pos = Vec(dome["pos"][0], dome["pos"][1] - dome["radius"])
    m.ball.vel = Vec(0, -4)
    m.ball.held_by = None
    m.last_thrower_team = 1
    score_before = m.score.score_team1
    m.tick({})
    assert m.score.score_team1 == score_before + CFG.scoring["dome_bonus_points"]


def test_star_bank_integration_via_tick():
    m = Match(CFG, seed=(6, 6))
    bank = CFG.arena["star_banks"][0]
    from sim.vec import Vec
    y = bank["y_min"] + 1
    m.ball.pos = Vec(bank["x_max"] - 2, y)
    m.ball.vel = Vec(-4, 0)
    m.ball.held_by = None
    m.last_thrower_team = 1
    m.tick({})
    assert m.furniture.lit_stars_team1 == 0b00001
    assert m.score.score_team1 == CFG.scoring["star_bonus_points"]


def test_electrobounce_integration_via_tick():
    m = Match(CFG, seed=(9, 9))
    left, right = CFG.arena["electrobounces"]
    from sim.vec import Vec
    m.ball.pos = Vec(*left["pos"])
    m.ball.vel = Vec(-4, 0)
    m.ball.held_by = None
    m.tick({})
    speed = CFG.physics["electrobounce_speed"]
    assert m.ball.pos.x == right["pos"][0] - speed
    assert m.furniture.electrobounce_flash_ticks == 1  # set to 2, ticked once


def test_state_hash_reflects_furniture_state():
    m1 = Match(CFG, seed=(3, 3))
    m2 = Match(CFG, seed=(3, 3))
    assert m1.state_hash() == m2.state_hash()
    m1.furniture.lit_stars_team1 = 0b00001
    assert m1.state_hash() != m2.state_hash()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_match.py -v -k "furniture or dome or electrobounce or star_bank"`
Expected: FAIL with `AttributeError: 'Match' object has no attribute 'furniture'`

- [ ] **Step 3: Wire `FurnitureState` into `Match`**

In `sim/match.py`, update the import block (currently lines 16-24):

```python
from sim.actions import attempt_tackle, throw, try_pickup
from sim.config import GameConfig
from sim.entities import Ball, move_and_bounce, update_ball_velocity
from sim.furniture import (FurnitureState, check_bounce_domes,
                           check_electrobounces, check_star_banks,
                           tick_electrobounce_flash)
from sim.input import IDLE, InputState
from sim.player import PlayerSim, apply_movement
from sim.rng import Sb2Rng
from sim.scoring import (ScoreState, award_goal, check_goal,
                         check_multiplier_banks, tick_multipliers)
from sim.vec import Vec
```

In `Match.__init__` (currently lines 40-53), add `self.furniture` after
`self.score = ScoreState()`:

```python
        self.cfg = config
        self.rng = Sb2Rng(*seed) if seed else Sb2Rng()
        self.score = ScoreState()
        self.furniture = FurnitureState()
        self.tick_count = 0
```

(leave the rest of `__init__` unchanged.)

In `Match.tick()` (currently lines 128-139), insert the three furniture
checks between `tick_multipliers(self.score)` and the player-input loop:

```python
    def tick(self, inputs: dict[int, InputState]) -> None:
        arena, phy, sco = self.cfg.arena, self.cfg.physics, self.cfg.scoring
        update_ball_velocity(self.ball, phy, self.ball_speed_ref)
        check_multiplier_banks(self.ball, arena, sco, self.score,
                               self.last_thrower_team)
        tick_multipliers(self.score)
        check_bounce_domes(self.ball, arena, phy, self.last_thrower_team,
                           self.score, sco)
        check_electrobounces(self.ball, arena, phy, self.furniture)
        tick_electrobounce_flash(self.furniture)
        check_star_banks(self.ball, arena, sco, self.furniture, self.score,
                         self.last_thrower_team)

        for p in self.all_players():
```

(the rest of `tick()`, from the player-input loop onward, is unchanged.)

In `Match.state_hash()` (currently lines 194-222), add the furniture mixes
right after the existing score mixes (inside the final `for v in (...)`
tuple that mixes `self.score.score_team1`, etc.):

```python
        for v in (self.score.score_team1, self.score.score_team2,
                  self.score.multiplier_team1_ticks,
                  self.score.multiplier_team2_ticks,
                  self.furniture.lit_stars_team1,
                  self.furniture.lit_stars_team2,
                  self.furniture.electrobounce_flash_ticks,
                  self.rng.a, self.rng.b,
                  self.clock_ticks, self.last_thrower_team):
            mix(v)
        return acc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_match.py -v`
Expected: PASS (all tests in the file, including the 4 new ones)

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: PASS, no regressions

- [ ] **Step 6: Commit**

```bash
git add sim/match.py tests/test_match.py
git commit -m "feat: wire bounce domes, electrobounces, and star banks into Match.tick"
```

---

### Task 6: Placeholder rendering

**Files:**
- Modify: `present/renderer.py`

**Interfaces:**
- Consumes: `match.cfg.arena["bounce_domes"/"electrobounces"/"star_banks"]`,
  `match.furniture` (Task 5).
- No new public functions — extends the existing `_draw_pitch` internal.

- [ ] **Step 1: Add color constants**

In `present/renderer.py`, add after the existing color constants (after
`BANK_LIT = (255, 220, 0)`, before `TEAM1_COLOR`):

```python
DOME_COLOR = (180, 180, 190)
ELECTRO_DIM = (0, 110, 130)
ELECTRO_LIT = (0, 220, 255)
```

- [ ] **Step 2: Draw the three item types in `_draw_pitch`**

In `present/renderer.py`, append to the end of `_draw_pitch` (after the
existing multiplier-bank loop, still inside the function):

```python
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
```

- [ ] **Step 3: Headless smoke verification**

Renderer has no existing pytest coverage in this codebase (verified by
`python -m present.app` runs per the MVP plan's convention) — verify with a
headless dummy-driver smoke check instead of a new test file:

Run:
```bash
SDL_VIDEODRIVER=dummy python -c "
import pygame
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((640, 480))
font = pygame.font.SysFont(None, 20)
from pathlib import Path
from sim.config import load_config
from sim.match import Match
from present.renderer import draw_frame
cfg = load_config(Path('data'))
m = Match(cfg, seed=(1, 1))
for _ in range(5):
    m.tick({})
draw_frame(screen, m, 100, font)
print('OK')
"
```
Expected: prints `OK`, no traceback.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest`
Expected: PASS, no regressions

- [ ] **Step 5: Commit**

```bash
git add present/renderer.py
git commit -m "feat: placeholder rendering for bounce domes, electrobounces, star banks"
```
