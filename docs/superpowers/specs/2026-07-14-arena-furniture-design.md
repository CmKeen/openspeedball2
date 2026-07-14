# Arena furniture (tier 1): stars, bounce domes, electrobounces

Post-MVP roadmap item #2. Scope for this design: **stars, bounce domes, and
electrobounces only**. The Token system (floating power-up pickups, ~10
effects including the warp-gate teleport and stat buffs) is a separate,
larger, semi-independent subsystem and gets its own future design.

## Reference behavior (from REF `GameClasses/`)

- **`Stars.cs`**: two 5-star banks, one per team, on the left/right walls.
  Hitting your own bank with a live throw lights an unlit star (+points,
  once per star). Hitting the opponent's bank where a star is already lit
  knocks it out (-points to them). All 5 lit on one bank → bonus points,
  then that bank's bits clear. Banks swap sides at halftime in REF
  (`SwitchSide`) — not applicable here (see Decisions).
- **`BounceDomes.cs`**: two domes (near each goal in REF). A live ball
  passing near a dome gets redirected away from the dome's center at fixed
  speed; awards bonus points to whoever last threw the ball.
- **`Electrobounces.cs`**: two wall plates (left/right, mid-pitch in REF). A
  live ball hitting a plate teleports to the opposite plate's wall (same Y),
  continuing at a speed scaled from the thrower's `thr` stat. No score
  bonus. REF also lights the plate for a couple of ticks (`_lightTimer`) as
  a visual cue.

REF positions these via raw Atari-disk memory offsets, not human-readable
coordinates — decoding them precisely needs disk extraction/tracing
comparable to the AI-fidelity roadmap item. Exact placement is out of scope
here (see Decisions).

## Decisions

- **Placement fidelity**: use reasonable pitch-relative placeholder
  positions now (domes near each goal mouth, electrobounces on side walls
  mid-pitch, star banks flanking the existing multiplier banks). Mark them
  `[tunable — validate]` in `data/arena.json`, same convention already used
  in `scoring.json`. Refine via the frame-trace harness later, not blocking
  this work.
- **Star wall assignment**: fixed for the whole match — team 1's bank is the
  left wall, team 2's is the right wall. No halftime/end-switching exists in
  the sim yet (single leg, teams stay on their sides), so REF's
  `SwitchSide` behavior doesn't apply. Revisit if/when halftime is added.
- **Trigger condition**: all three effects trigger on `ball.held_by is None
  and ball.vel != Vec(0, 0)` (a live free-flying ball) — the same condition
  `check_multiplier_banks` already uses. This substitutes for REF's
  `_pThink`/`_spriteIndex` opcode-state checks, which have no equivalent in
  this sim.
- **Electrobounce "team flag"**: REF sets a generic `Bit3_IsTeam1_...` flag
  on the ball when a plate is hit. This bit is reused across several REF
  classes as a generic "team 1" flag unrelated to electrobounce-specific
  behavior, and the sim already tracks equivalent info via
  `last_thrower_team`. Not ported as a separate field.

## Data (`data/arena.json`)

```json
"bounce_domes": [
  {"pos": [320, 96],  "radius": 16},
  {"pos": [320, 1056], "radius": 16}
],
"electrobounces": [
  {"pos": [16, 560],  "wall": "left"},
  {"pos": [624, 560], "wall": "right"}
],
"star_banks": [
  {"team": 1, "x_min": 0,   "x_max": 24,  "y_min": 160, "y_max": 320, "count": 5},
  {"team": 2, "x_min": 616, "x_max": 640, "y_min": 832, "y_max": 992, "count": 5}
]
```

Point values (`dome_bonus_points`, `star_bonus_points`,
`star_row_bonus_points`) and any fixed-speed constants go into
`data/scoring.json` / `data/physics.json` alongside the existing
`goal_points`, `multiplier_duration_ticks`, etc. — not hardcoded, matching
the current data-driven pattern.

## Sim module: `sim/furniture.py`

New module, parallel to `scoring.py`. Kept separate from `scoring.py`
because domes/electrobounces mutate ball trajectory (a physics concern),
not just score/state, even though stars are pure scoring.

```python
@dataclass(slots=True)
class FurnitureState:
    lit_stars_team1: int = 0   # bitmask, 5 bits
    lit_stars_team2: int = 0
    electrobounce_flash_ticks: int = 0  # cosmetic timer

def check_bounce_domes(ball, arena, last_thrower_team, score, scoring) -> None: ...
def check_electrobounces(ball, arena, physics, furniture, last_thrower_team) -> None: ...
def check_star_banks(ball, arena, scoring, furniture, score, last_thrower_team) -> None: ...
```

`FurnitureState` lives on `Match` (like `ball_speed_ref`), not folded into
`ScoreState` — `ScoreState` stays pure score numbers; `FurnitureState` is
collision/animation state.

**Effects:**

- **Bounce dome**: ball within `radius` of dome center → reflect velocity
  away from the dome's center at a fixed speed (`physics.json`); award
  `dome_bonus_points` to `last_thrower_team`.
- **Electrobounce**: ball within range of a wall plate → teleport `x` to
  the opposite plate's `x` (same `y`), continue moving away from that
  opposite plate at a speed scaled from the thrower's `thr` stat; set
  `electrobounce_flash_ticks` for the present-layer visual cue. No score
  bonus.
- **Star bank**: ball hits a bank rect (like multiplier banks) → own bank,
  unlit star at that index → light it (+`star_bonus_points`), once per
  star. Opponent's bank, lit star at that index → un-light it and subtract
  `star_bonus_points` from them. All 5 lit on one team → award
  `star_row_bonus_points`, then clear that team's bits. Bank rects eject
  the ball back onto the pitch, same as multiplier banks.

## Tick integration (`sim/match.py`)

`Match.__init__` gains `self.furniture = FurnitureState()`. In `tick()`,
immediately after the existing multiplier-bank checks (same phase —
pre-movement, ball-state checks):

```python
check_multiplier_banks(...)
tick_multipliers(self.score)
check_bounce_domes(self.ball, arena, self.last_thrower_team, self.score, sco)
check_electrobounces(self.ball, arena, phy, self.furniture, self.last_thrower_team)
check_star_banks(self.ball, arena, sco, self.furniture, self.score, self.last_thrower_team)
```

Order among the three is inconsequential: they occupy disjoint pitch
regions, so a single ball position triggers at most one.

`state_hash()` in `match.py` mixes in `furniture.lit_stars_team1/2` (and
`electrobounce_flash_ticks` if it affects observable behavior) so
replay/lockstep determinism covers the new state.

## Rendering (`present/renderer.py`)

Placeholder shapes, following the existing convention (primitive shapes, no
bundled art):

- Bounce dome: filled circle (grey/silver) at its `pos`.
- Electrobounce: small diamond on the wall, brighter/flashing while
  `flash_ticks > 0`.
- Star bank: 5 small squares per team's bank rect — outline when unlit,
  filled yellow when lit.

## Testing plan (TDD)

- `tests/test_furniture.py`: unit tests per effect, constructing minimal
  `Ball`/`arena`/`scoring` dicts (no full `Match` needed), following
  existing test style:
  - Bounce dome reflects velocity + awards points on hit; no-op when ball
    held or stationary.
  - Electrobounce teleports ball to the opposite wall, preserves
    thrower-scaled speed; no-op conditions match.
  - Star bank: lights own star once (+points), doesn't re-light an
    already-lit star, knocks out opponent's lit star (-points), full row
    triggers bonus and clears only that team's bits.
- Integration test (in `tests/test_match.py` or similar): a scripted ball
  trajectory into a dome/electrobounce/star bank via `Match.tick()`
  produces the expected score, `FurnitureState`, and ball-position changes
  — mirrors how `check_multiplier_banks` is already covered.
