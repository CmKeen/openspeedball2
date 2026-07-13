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
