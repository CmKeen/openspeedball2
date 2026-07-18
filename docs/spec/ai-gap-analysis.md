# AI/behavior gap analysis: REF `Player.cs` vs `sim/`

Durable, resumable map of REF's decompiled AI/tackle subroutines
(`Speedball 2 - WIP 02/Speedball 2 - WIP 02/src/GameClasses/Player.cs`,
`Entity.cs`) against their `sim/` equivalents. Built by reading REF source
function-by-function (no .NET toolchain is installed to run/trace the REF
exe itself, per project decision — see `README.md`). Each row is a REF sub,
its line range in `Player.cs` at time of writing, its `sim/` counterpart (or
"none"), and a verdict: **Equivalent** (verified matching logic/constants),
**Diverges** (ported but with a real behavioral difference, described), or
**Missing** (no `sim/` counterpart at all). Resume future passes by picking
the next high-impact **Diverges**/**Missing** row.

## Tackling (`Player.cs` 1757–1854) — this pass

| REF sub | Lines | `sim/` counterpart | Verdict |
|---|---|---|---|
| `sub_ED56_TackleCheckHit` / `sub_ED92_TackleCheckHit_Helper` | 1757–1813 | `Match._resolve_action` (`sim/match.py`) + `attempt_tackle` (`sim/actions.py`) | **Fixed this pass.** REF scans the *entire* opposing roster (roster-index order) for the first player within `tackle_range` (30) — tackling is not gated on that player holding the ball. Our `_resolve_action` previously only ever passed `[holder]` as the candidate list, i.e. a player could only ever be tackled while they held the ball. `attempt_tackle`'s own "first eligible candidate, one roll, stop" logic already matched REF's `continue`/`return` pattern — only the candidate list was wrong. Fixed by passing the full opposing roster (`sim/match.py:_resolve_action`); added `tests/test_match.py::test_action_a_can_tackle_a_nearby_opponent_not_holding_the_ball`. |
| `sub_EE9C_CalcTackleProbability` | 1815–1830 | `tackle_probability` (`sim/actions.py`) | **Equivalent**, with one **Missing** piece. `d4 = attacker.att`, `d5 = defender.def` (×3/2 capped 255 if defender is GK), `d5 -= tackle_def_malus_by_delta_dir[deltaDir]`, `d5 -= tackle_malus_sliding` if attacker is tackling/blocking, return `(d4+256-d5)/2` — all byte-for-byte match `sim/actions.py::tackle_probability` and `data/physics.json`. **Missing**: REF also subtracts `tackleUnk02` (`data/physics.json`'s already-present-but-unused `tackle_malus_jumping`, 32) when the *defender* (`this` in that method) `Bit1_IsJumping`. `sim/` has no jump state on `PlayerSim` at all — jumping isn't modeled as a mechanic yet. Out of scope for this pass (would require a new player state, not just a formula tweak); tracked here for a future pass. |
| `sub_EEFC_HitByTackle` | 1832–1854 | `apply_tackle_damage` (`sim/actions.py`) | **Equivalent** for health/stat-drain math: `d = max(1, (attacker.pow+150-defender.sta)//16)`, health -= d (floor 0), hit = max(1, d//2) applied to agr/att/def/spd/thr/pow/sta/int — byte-for-byte match. **Missing**: trailing `sub_FF3A_UnequipEquipment(match)` call — no-op for us since the equipment/token system (REF's `Token.cs`) is explicitly out of scope per `README.md`'s roadmap ("Token/warp-gate pickups ... a separate, larger follow-up design, not yet implemented"). |
| `sub_FC24` (token-shield check gating tackle eligibility) | 2243–2248 | none | **Missing**, but inert: only returns `false` (skip this candidate) when a player is currently holding the shield-type token (`_heldSpriteIndex == 64`). Since tokens aren't implemented, this always evaluates `true` in `sim/`, which is the correct behavior until tokens exist. No action needed until token work starts.

## Top-level AI decision dispatch (`Player.cs` 406–548) — surveyed, not yet ported

| REF sub | Lines | `sim/` counterpart | Verdict |
|---|---|---|---|
| `sub_D742_AII` (master per-tick AI dispatch for a non-human-controlled player) | 406–516 | `sim/ai.py::_decide` | **Diverges — largest remaining gap, deferred.** REF's dispatch is materially different from `_decide`'s simplified "closest-2-chase / support / defend / carry" tree: it branches on aggression-stat dice rolls (`_agr/2 > _random`) to decide between direct ball-pursuit and a computed `_targetXY`, applies an onscreen-margin check, computes two nearest-opponent direction bits (`sub_D902`) and threads them through further sub-dispatches (`sub_DCCC`, `sub_DA86`/`sub_DB32` direction-bit comparisons) to choose between "run to target" (`sub_EB7A`) and position-dependent pass/hold logic (`sub_DBE8` for defenders/GK, `sub_DF2E` for attackers — both of which *are* already ported into `sim/ai.py`'s `_choose_pass_target`/`decide_carry` per their inline REF citations). It also folds in item/token avoidance (`sub_D97E_AII_Items`/`sub_D9DC_AII`) which is out of scope until tokens exist. **This sub was read in full this pass but not ported**: the branch structure is intricate enough (8+ nested conditions, decompiler-named `DirBits`/`_zoneCenterXY`/`_zoneXY1`/`_zoneXY2` fields with no `sim/` equivalent representation yet) that a rushed port risks a wrong translation being worse than the current honest approximation. Recommended next step for a future pass: introduce a `DirBits`-equivalent (two-nearest-opponent direction pair) and `zoneXY1`/`zoneXY2` fields on `PlayerSim`/formation data, then translate `sub_D742_AII` as a single dedicated pass with its own frame-by-frame test scenarios (not bundled with an unrelated fix). |
| `sub_D902` (two-nearest-opponent direction-bit pair, feeds the dispatch above) | 518–548 | none | **Missing** — prerequisite for `sub_D742_AII` above. |

**Update**: one of `sub_D742_AII`'s two prerequisites is now unblocked.
`data/formations.json` (new) holds the real per-player `_zoneXY1`/`_zoneXY2`
patrol rectangles, extracted from the disk image the same way as the other
binary constants above (`tools/extract_binary_constants.py`) — clean,
structured, position-shaped data (e.g. team1's two wingers get mirrored
left/right zones in the attacking third, the center-forward gets a centered
zone between them, matching the `pos=3` vs `pos=4` attribute distinction
found in the same extraction pass). Not yet wired into `sim/` — `PlayerSim`
has no zone fields and nothing reads this file yet — staged for whenever
`sub_D742_AII` gets its dedicated pass. The **other** prerequisite, a
`DirBits`-equivalent (two-nearest-opponent direction-bit representation,
`sub_D902` above), is still unbuilt and still the harder half: it threads
through direction comparisons (`sub_DA86`/`sub_DB32`) that assume an 8-way
bitmask notion of "direction" our `Vec`/`dir_towards` model doesn't have.
| `sub_E61A_GoalUnk` | 1332–1485 | `decide_goalkeeper` (`sim/ai.py`) | **Diverges (partially ported, documented approximation)** — see the inline "Amiga REF sub_E61A_GoalUnk()" comment already in `sim/ai.py`; the loose-ball-lunge and goal-line-locked predicted-lane logic are ported, but this is REF's largest sub (120+ lines) covering additional goalkeeper animation/state transitions not modeled since `sim/` has no animation opcode system. |
| `sub_DBE8`, `sub_DF2E`, `sub_E05C`, `sub_E382`, `sub_E218`, `sub_F364`, `sub_CEEA_InitGoalerAnim` (anim-state part), `get_predicted_ball_position_for_goalie` | various | `_choose_pass_target`, `decide_team_support`, `_attacker_lookup_target`, `_predicted_target`, `_goalie_predicted_target` (`sim/ai.py`) | **Equivalent or documented-approximation** — already ported with inline REF citations in `sim/ai.py`; verified consistent with the source read this pass. No change needed. |

## Reactive tackling (`sub_E854`, `Player.cs` 1508–1560) — surveyed, blocked on an architecture conflict

REF's `sub_D742_AII` calls `sub_E854` first, before any of the dispatch
above, for any player not currently holding the ball: it scans the *entire*
opposing roster for anyone within `tackle_range` and, if found, auto-attacks
them when the player is a goalkeeper, that opponent holds the ball, or a
per-tick aggression-stat dice roll (`_attributes._agr > _random`) succeeds —
where `_random` is one `NextByte()` rolled **unconditionally, once per
player per tick**, at the very top of `sub_D742_AII` (line 409), regardless
of whether a candidate is even found nearby.

This is a real, well-understood, self-contained piece of REF's AI (unlike
`sub_D742_AII`'s main body it needs no zone data), but porting it faithfully
means every non-ball-holding AI player consumes one RNG byte every tick,
unconditionally. That directly conflicts with a deliberate design decision
already encoded in `tests/test_ai.py::test_carry_roll_fires_only_in_shot_range`,
which asserts `compute_ai_inputs` leaves the RNG stream untouched when no
AI decision actually needs a roll (i.e. today's `sim/ai.py` economizes RNG
consumption — it only rolls when a choice is actually contested, not on a
fixed per-player-per-tick cadence). Adopting REF's cadence is a legitimate
option but is a cross-cutting change to the AI module's RNG-consumption
philosophy, not a local fix, and would need the existing test's intent
revisited deliberately rather than incidentally broken by an unrelated
change. Deferred; flagged here as a **Missing** item requiring a scoped
design decision before implementation, not a straightforward port.

## Arena/goal geometry corrections (`Entity.cs`, `Match.cs`) — this pass

Not part of the `Player.cs` AI survey above, but found while chasing why
`goal_depth` felt inconsistent with REF's actual `CheckGoal` while reading
adjacent code:

| Constant | Was | Now | REF source |
|---|---|---|---|
| `wall_margin_player` | 16 | **48** | `Match.cs MoveBallPlayersMedicsHandleWallsAndBounce`: `player.MoveAndHandleWallsAndBounce(48)` for every player/medic. Unambiguous. |
| `wall_margin_ball` | 16 | **32** (still `[tunable — validate]` for the 24-vs-32 split below) | Same call site: ball margin is `24`, bumped to `32` when `_entityBall._spriteIndex <= 2` (its normal in-flight sprite range). `sim/` has no ball-sprite-index state to pick between the two, so `32` was chosen as the closer default. |
| `goal_depth` | 16 | **32** | `Match.cs CheckGoal`: goal awarded when `_terrainXY.Y < 32` (top) / `> 1120` i.e. `height - 32` (bottom) — the same 32-unit band as the corrected ball wall margin (the goal mouth is the gap left open in that wall band across `goal_mouth_x_min..x_max`). |

`goal_mouth_x_min`/`goal_mouth_x_max` (272/368) were independently confirmed
correct against `CheckGoal`'s literals — no change needed there.
`multiplier_banks` remain unchecked against `ScoreMultipliers.cs` this pass.

Re-ran the headless smoke check after this fix (on top of the tackle fix
above): 5000 ticks, seed `(5, 5)` → score 12–38, 416 possession changes (vs.
0–2/370 with only the tackle fix, and the original 50–0 rout). Goals are now
actually happening at a normal-feeling rate instead of a near-scoreless
stalemate; the balance itself (team 2 favored 3:1) is not yet validated
against REF and is a candidate for the next pass once `sub_D742_AII` lands.

## Arena furniture geometry (`ScoreMultipliers.cs`, `Stars.cs`) — this pass

`data/arena.json`'s `multiplier_banks` and `star_banks` rectangles were
placed near each team's own goal line, entirely wrong: REF's
`ScoreMultipliers.cs CheckEnter` and `Stars.cs CheckHit` put both pairs on
the *side walls near mid-pitch*, not near the goals.

| Bank | Was | Now | REF source |
|---|---|---|---|
| `multiplier_banks[0]` (left) | x 0–24, y 384–480 | x **24–64**, y **576–640** | `ScoreMultipliers.cs CheckEnter`: outer gate `X<24 \|\| X>616 → return`; left branch `X<64`, `d2=576,d3=640`. |
| `multiplier_banks[1]` (right) | x 616–640, y 672–768 | x **576–616**, y **512–576** | Same method, right branch `X>576`, `d2=512,d3=576`. |
| `star_banks[0]` (team 1, left) | x 0–24, y 160–320 | x **0–32**, y **384–544** | `Stars.cs CheckHit`: `X<=32`, `Y` in `[384,544)` (5 bands of 32). |
| `star_banks[1]` (team 2, right) | x 616–640, y 832–992 | x **608–640**, y **608–768** | Same method, `X>=608`, `Y` in `[608,768)`. |

Verified safe to change: every test that exercises these banks
(`tests/test_scoring.py`, `tests/test_furniture.py`, `tests/test_match.py`)
derives its ball positions from `CFG.arena[...]` at test time rather than
hardcoding literal coordinates, so none needed updating.

**Not fixed, and not fixable from source alone this pass**: `bounce_domes`
and `electrobounces` positions. Unlike the banks above, REF constructs
`BounceDomes`/`Electrobounces`' entities directly from decoded Atari-disk
byte offsets (`new Entity(Game.AtariDisk, Game.AtariRamToDisk(0x4B0A))` etc.)
rather than literal X/Y constants in `Player.cs`/`Match.cs`-adjacent source
— their real positions live in binary game data this repo doesn't ship
(see `README.md`'s asset policy) and would need either a real disk image
run through `Game.AtariRamToDisk`'s address translation, or the equivalent
Amiga data, to extract. `data/arena.json`'s current dome/electrobounce
`pos` values remain unverified placeholder guesses — flagged
**[tunable — validate]**, blocked on data extraction rather than a source
read.

Also unresolved this pass: `ScoreMultipliers.cs`'s actual entry mechanic is
a *directional pocket* (only a ball moving straight up/down within a few
units of the bank's inner edge "enters" and lights the LED counter;
anything else just bounces off it like a wall) and a **2-hit LED counter**
per team (`UpdateLeds`) rather than a flat on/off duration flag — materially
different from `sim/scoring.py check_multiplier_banks`'s current
"any entry within the rect immediately activates a flat-duration
multiplier" model. The rectangle position is now correct; the trigger
mechanic itself is a separate, larger follow-up (new "directional entry"
concept, no `sim/` equivalent yet).

## Amiga vs. Atari master-version note

The user's standing preference: when Speedball 2 reference material across
platforms disagrees, **the Amiga version is master**. The binary-data
extraction below is necessarily **Atari-sourced**: REF's own gameplay
simulation code (`Game.cs`, `Match.cs`, `Player.cs`, `Entity.cs`) reads
constants exclusively from `Game.AtariDisk` — there is no
`AmigaRamToDisk`/Amiga gameplay-data path in that project at all;
`Game.AmigaDisk` is used only for sprite/graphics/palette rendering there
(`SpriteManager`, `Stars.cs Draw`, `Field.cs`, `Entity.cs` animation). So
every constant extracted this pass (velocity table, furniture positions,
AI zone rectangles) is provisional against an Amiga original, not because
of any specific reason to doubt it, but because it was never actually
cross-checked against one — REF simply doesn't offer that path. Treat as
correct-until-shown-otherwise, not as confirmed-master. Visual/sprite
extraction already follows the Amiga-preferred convention
(`tools/crop_amiga_sprites.py`, `assets/amiga_extracted/`).

## Binary-data-blocked items — resolved via `tools/extract_binary_constants.py`

The three items above that were blocked on disk-resident data (player
movement speed tiers, `bounce_domes`/`electrobounces` positions) are now
**resolved**: `Resources/` (gitignored, user-supplied, legally-owned game
copy) already contains the exact Atari ST disk image REF's own
`Resource.resx` embeds byte-for-byte as `Atari_Disk` (`ResXFileRef` to that
path, no transformation) — REF's own address formulas
(`Game.AtariRamToDisk`, `Entity`'s byte layout) apply directly. Validated
before trusting the results by extracting the default player-attribute
roster (health/initialDir/pos/stat bytes) and confirming it's clean,
structured data (uniform stat=100 roster, health=128, team1/team2 facing
opposite `initialDir`, a plausible 0..4 position-code spread) rather than
garbage, i.e. the address math is provably correct, not assumed. New tool:
`tools/extract_binary_constants.py` (prints results for manual transcription
into `data/*.json` with a citation; never writes/bundles game data itself).

**Player movement speed** (`Player.cs` 1580–1593 etc. call
`Match.GetVelocityXYFromDir(dir, velocity)`): the extracted table shows
velocity index maps *linearly* to per-axis terrain-units/tick (velocity `n`
→ magnitude `n` along the facing axis/axes) — confirming REF's 4-tier
ladder (base 4, +1 per `SpeedMaxForVelocity4/5/6` threshold exceeded, max 7)
translates directly to real speeds 4–7. Fixed `data/physics.json`
(`player_base_speed: 4`, new `player_speed_tier_thresholds: [140, 170, 200]`
replacing the old flat `player_speed_bonus_threshold`) and
`sim/player.py::speed_of` to implement the 3-threshold ladder instead of a
single bonus. `tests/test_player.py` updated to the new tier values.

**Bounce dome positions**: top `(320, 320)`, bottom `(320, 832)` (previously
guessed `(320, 96)`/`(320, 1056)` — extraction confirms they *are*
vertically mirrored around the pitch center, `320` and `1152 - 320 = 832`,
just not where the placeholders guessed). Radius stays `16`, already
confirmed from `BounceDomes.cs`'s literal `deltaX`/`deltaY > 16` checks —
only the positions were data-dependent.

**Electrobounce positions**: left `(20, 884)`, right `(620, 276)` (disk
gives `terrainXY` `(20, 880)`/`(620, 272)`; REF's `UnkInRect` compares
against `terrainXY.Y + originXY.Y`, and both entities' disk-loaded
`originXY.Y` is `4`, so the effective trigger center is `+4`; folded in).
Also mirrored point-symmetrically through the pitch center (`880 + 272 =
1152`), not at equal heights as the old placeholder assumed.
`electrobounce_range` corrected `16 → 15` (REF's literal `UnkInRect(..., 15)
> 15`, not 16).

**Electrobounce mechanic itself was also wrong, discovered while fixing the
positions above**: applying the real (620, 276)/(20, 884) coordinates to
the *old* `check_electrobounces` logic — which teleported the ball to the
*other* plate's exact X — immediately broke `tests/test_match.py`, because
620 sits past the corrected `wall_margin_ball` clamp (608) and the ball got
re-bounced the same tick. Investigating why surfaced that the whole
"teleport to the opposite plate" model was never something REF actually
does: `Electrobounces.cs CheckHitOne` snaps the ball's X to a fixed
same-side literal (`32`/`608`, i.e. exactly `wall_margin_ball`/`width -
wall_margin_ball` post-correction — not the opposite wall) and redirects it
via a direction vector from the plate toward the ball
(`GetDirBitsToTargetBetter` + `GetVelocityXYFromDir(dir, 8)`), plus sets
`Bit3_IsTeam1_IsElectrobounced = true`, a flag that flips which team's
roster several `Player.cs` AI/possession routines treat as attacking for as
long as the ball stays "charged" (see `sub_D672`, and the `players =
Bit3_IsTeam1_IsElectrobounced ? PlayersTeam2 : PlayersTeam1` pattern
throughout `Player.cs`). Fixed `sim/furniture.py::check_electrobounces`'
destination-X formula to the correct same-side literal (confirmed exact);
left the direction-vector redirect and team-flip flag as a documented
approximation (still a simple away-from-the-wall push, no team-flip) since
neither has a `sim/` equivalent yet (needs the same `DirBits` system
`sub_D742_AII` is blocked on). Updated
`tests/test_furniture.py`/`tests/test_match.py`'s electrobounce tests to
the corrected same-side-snap model.

## Not yet surveyed (future pass starting points)

`Entity.cs` beyond the wall/bounce/friction routines already covered in
`docs/spec/mechanics.md`; `Player.cs`'s injury (`sub_F6DC_InjuredInitMedic`),
equipment (`sub_FF3A_UnequipEquipment` and friends), and animation-opcode
subs (`sub_EA62_CalcOpcodesTypeAndVelocityC`, `sub_ECF6_...A`,
`sub_F25C_...B`, `sub_F5A8_SetOpcodesAndVelocityFromDir`) — all deferred
because `sim/` intentionally has no animation/opcode state machine or
injury/equipment system yet (see `README.md` roadmap items 2–4). Triage
these once those systems are actually being built, not before.
