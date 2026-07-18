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
   python -m tools.frame_trace trace-sim --scenario ai-smoke --output sim_trace.jsonl

## Frame Validation Harness

Use `python -m tools.frame_trace trace-sim ...` to emit deterministic JSONL
frame traces from the packaged sim, `python -m tools.frame_trace compare ...`
to diff two traces, and `python -m tools.frame_trace prepare-ref ...` to stage
scenario metadata plus a sim trace for a local REF build at
`Speedball 2 - WIP 02/bin/Speedball 2.exe`. The harness is ready in this repo;
the REF executable/export side was not available in this environment, so only
the sim/comparison half was exercised here.

## Controls

Arrows/WASD: move · Space: the single action button, like the original —
throw (in the direction you're facing) when holding the ball, sliding
tackle when not.

## Credits & prior work

Mechanics are translated from documented reverse-engineering work:
simon-frankau/speedball2-re (Megadrive), simon-frankau/speedball2-re-amiga,
and Kroah's Speedball 2 Remake research (bringerp.free.fr).

## Status

v1 milestone (one playable match, human vs CPU) is complete: 65 headless
tests passing, sim core verified render-free and deterministic. A
headless smoke run (`Match.tick_with_ai()` for 2000 ticks under
`SDL_VIDEODRIVER=dummy`, no human input) exercises movement, pickup,
tackling, and throwing end-to-end without exceptions (a companion run
with scripted human inputs also produced a thrown goal); a human
has not yet interactively verified feel/controls. See
`docs/dod-audit.md` for the definition-of-done audit summary.

## Post-MVP roadmap

In priority order, each a future plan of its own:

1. **AI fidelity**: translate REF `Player.cs` think-dispatch behaviors one
   function at a time, validated frame-by-frame against
   `bin/Speedball 2.exe` with matched seeds. In progress via static source
   comparison (no .NET toolchain is installed to build/trace the REF exe
   here): see `docs/spec/ai-gap-analysis.md` for the sub-by-sub map and
   status. First pass (2026-07-18) fixed tackling to target any nearby
   opponent, not just the ball holder (REF `sub_ED56_TackleCheckHit` has no
   possession gate); the top-level AI dispatch (`sub_D742_AII`) is surveyed
   but not yet ported — it's the next highest-priority item.
2. **Arena furniture**: tier 1 (stars, bounce domes, electrobounces) is
   implemented — sim logic, data-driven placement (marked `[tunable —
   validate]` in `data/arena.json` pending frame-trace validation), and
   placeholder rendering. Token/warp-gate pickups (REF's `Token` class:
   freeze, reverse-joystick, stat buffs, the warp-gate teleport, etc.) are
   a separate, larger follow-up design, not yet implemented.
3. **Sound** (extraction tools exist upstream).
4. **Management layer**: gym, transfers, injuries (Megadrive RE covers the
   gym).
5. **League/cup + save system.**
6. **Menus/UI.**
7. **Online multiplayer**: lockstep first — the deterministic core makes
   this an input-exchange problem: each peer runs the same seeded sim and
   exchanges per-tick `InputState` dicts, cross-checking `state_hash()`
   periodically to catch desync; rollback netcode later if lockstep's
   input-delay feel needs improving.
8. **Discoverability**: register the project on osgameclones.com and
   awesome-game-remakes.

Also tracked as a small data-driven cleanup once AI fidelity work starts:
a few gameplay constants are still hardcoded in `sim/` rather than sourced
from `data/*.json` — most notably the formation anchor coordinates
(`_ROW_Y_TEAM1`, `_ROW_XS` in `sim/match.py`), which were an authoritative
controller decision for v1, plus several AI thresholds in `sim/ai.py`
(chase/keeper-margin distances, the support-shadow divisor, "closest N
players" count) and a couple of scoring/tackle formula constants in
`sim/scoring.py` and `sim/actions.py`. None of these break the "sim core
is data-driven" property in spirit (the *rules* are code, only a few of
the *numbers* aren't yet in JSON) but they should move to `data/*.json`
during the AI fidelity pass so they can be tuned without touching code.
