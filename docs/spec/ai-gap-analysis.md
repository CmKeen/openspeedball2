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
| `sub_E61A_GoalUnk` | 1332–1485 | `decide_goalkeeper` (`sim/ai.py`) | **Diverges (partially ported, documented approximation)** — see the inline "Amiga REF sub_E61A_GoalUnk()" comment already in `sim/ai.py`; the loose-ball-lunge and goal-line-locked predicted-lane logic are ported, but this is REF's largest sub (120+ lines) covering additional goalkeeper animation/state transitions not modeled since `sim/` has no animation opcode system. |
| `sub_DBE8`, `sub_DF2E`, `sub_E05C`, `sub_E382`, `sub_E218`, `sub_F364`, `sub_CEEA_InitGoalerAnim` (anim-state part), `get_predicted_ball_position_for_goalie` | various | `_choose_pass_target`, `decide_team_support`, `_attacker_lookup_target`, `_predicted_target`, `_goalie_predicted_target` (`sim/ai.py`) | **Equivalent or documented-approximation** — already ported with inline REF citations in `sim/ai.py`; verified consistent with the source read this pass. No change needed. |

## Not yet surveyed (future pass starting points)

`Entity.cs` beyond the wall/bounce/friction routines already covered in
`docs/spec/mechanics.md`; `Player.cs`'s injury (`sub_F6DC_InjuredInitMedic`),
equipment (`sub_FF3A_UnequipEquipment` and friends), and animation-opcode
subs (`sub_EA62_CalcOpcodesTypeAndVelocityC`, `sub_ECF6_...A`,
`sub_F25C_...B`, `sub_F5A8_SetOpcodesAndVelocityFromDir`) — all deferred
because `sim/` intentionally has no animation/opcode state machine or
injury/equipment system yet (see `README.md` roadmap items 2–4). Triage
these once those systems are actually being built, not before.
