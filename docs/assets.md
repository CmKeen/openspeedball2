# Assets

## Policy

OpenSpeedball is GPLv3 and open source. It must **never** contain ripped
Speedball 2 game data (sprites, sound, music, or any other extracted asset)
in the repository. `assets/` is listed in `.gitignore` and any files placed
there stay local to your machine only.

`Resources/` in the working directory (if present) is your own reference
material — original discs, ROM dumps, notes, etc. It is also gitignored and
is never read or touched by this repo's tooling except as an optional input
path you point at explicitly.

## Generating placeholder sprites

The renderer (`present/renderer.py`) can draw the pitch with either sprites
or primitive shapes; primitives are the default and always work. To exercise
the sprite-loading path without any game files, generate small original
placeholder sprites:

```bash
python -m tools.extract_assets
# or explicitly:
python -m tools.extract_assets --placeholders
```

This draws three 16x16 PNGs offscreen (via pygame, `SDL_VIDEODRIVER=dummy`,
no window opens) and writes them to `assets/sprites/`:

- `player_t1.png` — shaded disc, team 1 color (steel blue)
- `player_t2.png` — shaded disc, team 2 color (crimson)
- `ball.png` — shaded ball

These are original art created by this tool, not extracted from Speedball 2.
They exist purely so the sprite pipeline has real files to load; the
renderer looks for exactly these three filenames under `assets/sprites/`.

## Real extraction (post-MVP)

Ripping actual Speedball 2 sprites from a game copy you own is out of scope
for this tool and for the MVP. It requires the Rust extraction tools from
the upstream reverse-engineering project:

<https://github.com/simon-frankau/speedball2-re>

That project's tools work against a Megadrive ROM dump. To use it:

1. Clone `simon-frankau/speedball2-re`.
2. Build and run its `tools/` extractors against your own ROM/disk copy of
   Speedball 2.
3. Copy the resulting sprite images into this project's `assets/sprites/`,
   renamed to match what the renderer expects (see filenames above).

Running `python -m tools.extract_assets <path-to-your-game-copy>` detects
whether the path looks like an Amiga disk image (`.adf`) or a Megadrive ROM
(`.bin`/`.md`) and prints these same instructions — it does not perform any
extraction itself, and it never bundles or reproduces original game data.

## Expected filenames

The renderer (`present/renderer.py`, `_load_sprites`) looks for these files
under `assets/sprites/` and falls back to primitive shapes if the directory
or any file is missing:

- `assets/sprites/player_t1.png`
- `assets/sprites/player_t2.png`
- `assets/sprites/ball.png`
