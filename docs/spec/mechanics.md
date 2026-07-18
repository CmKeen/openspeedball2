# Speedball 2: Brutal Deluxe — Mechanics Spec

This document is the plain-English translation of the game mechanics implemented
so far, together with where each number and rule comes from. All numeric
constants live in `data/*.json`, not in code, so tuning a value never requires
touching simulation logic. Values marked **[tunable — validate]** below are our
best current guess and still need to be checked frame-by-frame against the
reverse-engineered (RE) original before we treat them as ground truth; every
other value listed here is already confirmed against the RE source.

## Coordinate system & arena

The pitch is a fixed 640×1152 rectangle in integer "terrain units" (`data/arena.json`
`width`/`height`), with (0, 0) at the top-left corner and Y increasing downward.
Every entity — ball and players alike — is clamped to `[margin, limit - margin]`
on each axis, where `margin` is `wall_margin_ball` (32) for the ball and
`wall_margin_player` (48) for players. **Corrected this pass** (previously 16
for both, mislabeled RE ground truth without having actually been checked
against the call sites): REF's `Match.MoveBallPlayersMedicsHandleWallsAndBounce`
calls `Entity.MoveAndHandleWallsAndBounce(margin)` with `margin = 48` for every
player/medic, and `margin = 24` for the ball, bumped to `32` whenever the
ball's `_spriteIndex <= 2` (its normal in-flight sprite range — the same
range `CheckGoal` and `Player.cs sub_D672` gate on before treating the ball
as "in open play"). Since our sim has no equivalent ball-sprite-index state
to distinguish the 24-vs-32 cases, `wall_margin_ball` is set to the `32`
branch as the closer default (the ball is normally in that sprite range
during free flight) — still **[tunable — validate]** for the 24-vs-32
distinction specifically, but no longer using the unsupported `16`. `wall_margin_player`
(48) is unambiguous RE ground truth. When the ball reaches a wall it doesn't
just stop: its velocity component on that axis is reflected (negated) and its
direction is mirrored through `mirror_dir_x`/`mirror_dir_y` so its facing/travel
direction flips consistently with the bounce. A bounce off a Y-wall (top or
bottom) additionally halves the ball's bounce timer, making the ball settle
faster the more it bounces off the end walls. This whole flow — clamp position,
reflect velocity, mirror direction, adjust the bounce timer — is one routine in
the original game. REF: `Entity.cs MoveAndHandleWallsAndBounce`.

The goal mouth is the horizontal span `goal_mouth_x_min`..`goal_mouth_x_max`
(272..368) cut into the north and south walls — RE ground truth, confirmed
byte-for-byte against `Match.cs CheckGoal`'s `_terrainXY.X < 272` /
`> 368` literals. `goal_depth` is **corrected this pass** from 16 to 32: `CheckGoal`
tests `_terrainXY.Y < 32` (top) / `> 1120` (i.e. `height - 32`, bottom) before
awarding a goal, which is the *same* 32-unit band as the ball's wall-bounce
margin above — the goal mouth is simply the gap left open in that wall band
across the `goal_mouth_x_min..x_max` columns, so the two constants are the
same physical boundary and must match. `kickoff_center` ([320, 576]) is where
the ball is placed to restart play — plausible (pitch center) but not
independently verified against REF this pass. The two `multiplier_banks`
rectangles remain **[tunable — validate]** — not checked against REF's
`ScoreMultipliers.cs` this pass.

## Ball friction

While the ball is free — not currently held by a player and not sitting inside
a multiplier bank — and moving, each axis of its velocity decays independently
by `ball_friction_per_tick` (1 unit) per tick, moving toward zero (never
overshooting past zero). This decay is suspended while the ball is between
`ball_no_friction_y_min` (48) and `ball_no_friction_y_max` (1104) — i.e. away
from the very top/bottom goal-line strip — and still has vertical velocity;
this keeps long goal-bound shots from losing pace before they arrive. A bounce
timer (set whenever the ball bounces high, e.g. off a wall or after a shot)
also defers friction application while it's counting down, modelling the ball
being airborne rather than rolling. All three constants (`ball_friction_per_tick`,
`ball_no_friction_y_min`, `ball_no_friction_y_max`) are RE ground truth. REF:
`Entity.cs UpdateBallVelocity`.

## RNG

The simulation uses a deterministic, seedable generator ported bit-for-bit from
the original game's routine (`sim/rng.py`, `Sb2Rng`), so that any match replay
is fully reproducible from its seed. It carries two 32-bit state words (`a`,
`b`); each call to `next()` splits both words into 16-bit halves, doubles the
low half of `a` with carry, then runs two rounds of add-with-carry between the
halves of `a` and `b`, swapping halves between rounds, and returns the updated
`a` as the next 32-bit output. `next_byte()`/`next_word()` mask that output down
to 8 or 16 bits for consumers that need a smaller range.

The default boot seed is `a = 0x31415926`, `b = 0x53589793` (recognizable as
digits of pi and e — the original developers' seed choice). Advancing the
generator eight times from that seed produces the golden vector used to pin
this port down in `tests/test_rng.py`:

```
0x849A49DF, 0xB5DC460A, 0x3A771FD2, 0xF053CBB8,
0x2ACAD715, 0x1B1E459B, 0x45E93960, 0x6107FDF6
```

Any future change to `sim/rng.py` must keep reproducing this exact sequence
from the default seed.

## Tackle

A tackle is attempted against the first eligible opposing player (in roster
order) within `tackle_range` (30 units) of the attacker — **not** only the
ball carrier; any nearby opponent, on the ball or off it, can be knocked
down. (This was previously modeled as ball-carrier-only in `sim/`; fixed to
match REF `Player.cs sub_ED56_TackleCheckHit`/`sub_ED92_TackleCheckHit_Helper`,
which scan the whole opposing roster with no possession check at all — see
`docs/spec/ai-gap-analysis.md`.) Success is decided by rolling a random byte
from the RNG against a
threshold of `(attacker.att + 256 - def_eff) / 2`, where `def_eff` starts as
the defender's raw `def` stat. If the defender is the goalkeeper, `def_eff` is
scaled up by `goalkeeper_def_multiplier_num / goalkeeper_def_multiplier_den`
(3/2, i.e. ×1.5) and capped at 255, reflecting keepers being harder to dispossess
in their own box. `def_eff` is then reduced by a facing-direction malus looked
up from `tackle_def_malus_by_delta_dir` — indexed by how far off-axis the
attacker's approach direction is from the defender's facing direction (0 units
apart = 0 malus, straight-on tackles are hardest to make since the defender is
watching; up to 64 units malus for approaches from directly behind/unexpected
angles) — and further reduced by `tackle_malus_sliding` (32) if the attacker is
sliding into the tackle, or `tackle_malus_jumping` (32) if the defender is
mid-jump when tackled. If the roll succeeds, the ball carrier is knocked back
along the tackler's facing direction at `tackle_knockback_speed` (3 units/tick),
or `tackle_knockback_speed_sliding` (4) if the tackle was a slide tackle.
Damage on a successful tackle is `max(1, (pow + 150 - sta) // 16)` off the
defender's health, and half that value (minimum 1) is also subtracted from all
eight of the defender's stats, representing cumulative wear from repeated
punishment. Possession of the ball transfers to the tackler, unless the
tackler is also in a falling/diving state, in which case the ball is loose.
REF: `Player.cs sub_ED56_TackleCheckHit`, `sub_EE9C_CalcTackleProbability`,
`sub_EEFC_HitByTackle`. The overall formula shapes (which terms are added,
subtracted, or capped, and in what order) for tackle probability and damage
are confirmed against that source read function-by-function; `tackle_malus_jumping`
is defined but currently **unused** in `sim/` — REF applies it when the
*defender* is mid-jump, but `sim/` has no jump state on players yet (tracked
in `docs/spec/ai-gap-analysis.md`).

`player_base_speed`, `pass_speed`, `shot_speed`, `throw_bounce_timer`,
`pickup_range`, `tackle_malus_sliding`, `tackle_malus_jumping`, and
`tackle_def_malus_by_delta_dir`'s exact magnitudes are still **[tunable —
validate]** (REF itself carries these as unnamed decompiled constants, e.g.
`_tackleUnk01`/`_tackleUnk02`, so the formula shape is confirmed but the
numeric value isn't independently named in the source); `tackle_range`,
`tackle_knockback_speed`, `tackle_knockback_speed_sliding`,
`goalkeeper_def_multiplier_num`, and `goalkeeper_def_multiplier_den` are RE
ground truth.

## Match tick order

Each simulation tick runs the following phases in order, matching the
original's main update loop so that timing-sensitive interactions (e.g. a
tackle landing in the same tick a pass arrives) resolve identically:

1. **Ball velocity update** — apply friction/bounce-timer countdown to the ball.
2. **Multiplier-bank checks** — detect the ball entering/leaving a bank rectangle
   and update the active scoring multiplier.
3. **Arena furniture checks** — collide the ball against fixed pitch obstacles.
4. **Ball-to-player distances** — recompute proximity for pickup/tackle range
   checks used later in the tick.
5. **Think** — run AI decision-making for CPU players and read human input for
   controlled players, producing each player's intended action for the tick.
6. **Goal check** — test whether the ball has crossed a goal line inside the
   goal mouth and, if so, register the score and prepare for kickoff.
7. **Move everything with wall handling** — apply velocities to the ball and
   all players, clamping to arena bounds and running the wall-bounce/mirror
   logic described above.
8. **Camera follows ball/holder** — update the presentation-layer camera
   target; this has no effect on simulation state.

REF: `Match.cs Update`.

## Validation method

The simulation is fully seeded and integer-exact: given the same RNG seed and
the same sequence of player inputs, it must produce bit-identical outcomes
every run. This determinism is what makes validation against the original
tractable. To validate any **[tunable — validate]** constant, we set up the
same scenario (same starting positions, same seed, same scripted inputs) in
both the RE project's runnable demo (`Speedball 2 - WIP 02/bin/Speedball 2.exe`)
and in our sim, then compare ball/player trajectories and AI decisions
frame by frame. Any mismatch means our JSON constant is wrong; we adjust it
and re-run until the two traces agree, then mark the value as confirmed in
this document.

Tunable keys currently pending validation, with their REF pointers:

- `data/arena.json`: `goal_mouth_x_min`, `goal_mouth_x_max`, `goal_depth`,
  `multiplier_banks` (all four rect bounds, both entries) — no specific REF
  pointer recorded yet beyond the arena/entity source files; validate against
  the original's collision boxes.
- `data/physics.json`: `player_base_speed`, `pass_speed`, `shot_speed`,
  `throw_bounce_timer`, `pickup_range`, `tackle_malus_sliding`,
  `tackle_malus_jumping`, `tackle_def_malus_by_delta_dir` — REF:
  `Player.cs sub_DE88_CalcBonusFromSpd`, `sub_EA62_CalcOpcodesTypeAndVelocityC`,
  `Match.GetTackleDefMalus`, `Match._tackleUnk01`/`_tackleUnk02`.
- `data/scoring.json`: `goal_points`, `goal_points_multiplied`,
  `multiplier_duration_ticks`, `leg_duration_ticks` — REF: `ScoreMultipliers.cs`,
  `Stars.cs`. Note: `leg_duration_ticks` (13500) is a placeholder derived from
  90 in-game seconds at 50 Hz × 3 (4.5 real minutes); the original leg is
  roughly 90 seconds of play, and this value is kept data-driven precisely so
  it can be corrected without touching code once confirmed.
- `data/teams.json`: player stat blocks (`agr`, `att`, `def`, `spd`, `thr`,
  `pow`, `sta`, `int`, `health`) and the 9-player-per-team roster size/formation
  are placeholders pending verification against `Match.cs` player-array
  initialization; if the original roster size differs from 9, this file and
  the formation logic must be updated together.

### Known hardcoded exceptions (not yet in `data/*.json`)

The Task 12 DoD audit (grep of `sim/` for numeric literals) confirmed the
overwhelming majority of gameplay values already flow through
`data/*.json` via `GameConfig`. A handful of constants are still literals
in code, tracked as future data-driven cleanup (see README "Post-MVP
roadmap"):

- `sim/match.py` `_ROW_Y_TEAM1` / `_ROW_XS` — formation anchor coordinates
  (row Y offsets and per-row X positions used to place all 18 players at
  kickoff). This was an authoritative controller decision for v1 rather
  than a translated RE value; it should become a `data/formations.json` (or
  similar) once formation variety is on the roadmap.
- `sim/ai.py` — the goalkeeper's ball-chase trigger distance (60), the
  goal-mouth AI positioning margin (16), the support-shadow divisor (4),
  and the "closest N teammates react" count (2) used by `_closest_ids`.
  These are baseline-AI approximations, not RE ground truth; they'll be
  replaced or moved to config during the AI fidelity pass.
- `sim/actions.py` `apply_tackle_damage` — the damage formula's `150` and
  `16` constants.
- `sim/scoring.py` `check_multiplier_banks` — the bank-eject horizontal
  speed (4) and reposition offset (8) used to kick the ball back out of a
  multiplier bank.

Numbers considered structural rather than gameplay-tunable (and therefore
fine as literals) include: byte/word masks (`0xFF`, `0xFFFF`, `0xFFFFFFFF`),
the 8 compass directions and their mirror tables in `sim/vec.py`, the
`state_hash()` mixing multiplier `1000003` (an arbitrary but fixed hash
constant, not a gameplay value), player-id encoding (`team * 100 + idx`),
and small structural indices like array position `[4]` for "the central
midfielder" in a fixed 9-player roster order.
