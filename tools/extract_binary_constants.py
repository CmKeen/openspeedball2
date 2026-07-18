"""Extract gameplay constants baked into the original Atari ST disk image.

Several REF constants (player movement speed per velocity tier, arena
furniture positions) aren't literals in the decompiled C# source at all --
REF reads them at runtime from a lookup table/struct on the original disk
image via ``Match.GetVelocityXYFromDir``/``Entity`` byte-offset
constructors (see ``Speedball 2 - WIP 02/.../src/Game.cs``,
``Match.cs``, ``GameClasses/Entity.cs``). This tool applies the same
address arithmetic directly to a local disk image and prints the results,
so they can be transcribed into ``data/*.json`` with a citation -- it does
not write or bundle any game data itself (``Resources/`` stays gitignored
per ``docs/assets.md``'s asset policy; only the small derived integers this
prints belong in the repo, the same way other RE-derived constants already
do in ``data/*.json``).

Usage::

    python -m tools.extract_binary_constants [path-to-.st-image]

Defaults to
``Resources/Speedball 2 - Brutal Deluxe (1990)(Bitmap Brothers)[!] - Track 00 filled.st``
relative to the repo root, which is exactly the file REF's own
``Resource.resx`` embeds as ``Atari_Disk`` (a plain ``ResXFileRef`` to that
path, applied with no transformation) -- so this tool's output is provably
the same bytes REF itself reads from, not a guess about disk layout.

Validated by cross-checking the extracted player attribute rosters (health/
initialDir/pos/stat bytes at RAM 0x40A6/0x412A) against known-sane values
(uniform stat=100 default roster, health=128, team1/team2 facing opposite
initial directions, structured position codes 0..4) before trusting the
address math for anything else -- see docs/spec/ai-gap-analysis.md.

NOTE on Amiga vs. Atari: this project's standing preference is that the
Amiga version is the master reference when platforms disagree. This tool
is necessarily Atari-sourced -- REF's own gameplay simulation code
(Game.cs/Match.cs/Player.cs/Entity.cs) reads every constant exclusively
from Game.AtariDisk; Game.AmigaDisk exists in that project but is used
only for sprite/graphics rendering, never gameplay data, so there is no
Amiga-sourced equivalent of this address math to cross-check against.
Treat everything this prints as provisional against an Amiga original,
not as confirmed master data -- see docs/spec/ai-gap-analysis.md's
"Amiga vs. Atari master-version note".
"""
from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_DISK = (
    Path(__file__).resolve().parent.parent / "Resources" /
    "Speedball 2 - Brutal Deluxe (1990)(Bitmap Brothers)[!] - Track 00 filled.st"
)

# Game.cs AtariRamToDisk: ramOffset - 0x400 + 0x4D600
_RAM_TO_DISK_DELTA = -0x400 + 0x4D600

# Entity struct layout (GameClasses/Entity.cs constructor): terrainXY starts
# 20 bytes in (pGfx4 + pFunctionDraw4 + pThink4 + pOpcodes4 + width2 + height2).
_ENTITY_TERRAIN_XY_OFFSET = 20


def ram_to_disk(ram_offset: int) -> int:
    return ram_offset + _RAM_TO_DISK_DELTA


def read_word(data: bytes, offset: int, signed: bool = False) -> int:
    return int.from_bytes(data[offset:offset + 2], "big", signed=signed)


def read_entity_terrain_xy(data: bytes, ram_base: int) -> tuple[int, int]:
    off = ram_to_disk(ram_base) + _ENTITY_TERRAIN_XY_OFFSET
    return read_word(data, off), read_word(data, off + 2)


def read_velocity_table(data: bytes, velocities: range = range(0, 9)) -> dict[int, list[tuple[int, int]]]:
    # Match.cs GetVelocityXYFromDir: offset = 0x6096 + 32*velocity + dir*4
    table = {}
    for vel in velocities:
        row = []
        for d in range(8):
            off = ram_to_disk(0x6096) + 32 * vel + d * 4
            row.append((read_word(data, off, signed=True),
                       read_word(data, off + 2, signed=True)))
        table[vel] = row
    return table


def read_player_roster(data: bytes, ram_base: int) -> list[dict[str, int]]:
    # Attributes struct (GameClasses/Attributes.cs), size 0xB, at
    # Game.cs's attributesTeam1 (0x40A6) / attributesTeam2 (0x412A).
    fields = ["health", "initialDir", "pos", "agr", "att", "def", "spd",
              "thr", "pow", "sta", "int"]
    roster = []
    for i in range(9):
        off = ram_to_disk(ram_base + i * 0xB)
        roster.append(dict(zip(fields, data[off:off + 11])))
    return roster


# Player struct (GameClasses/Player.cs constructor): starts with the 0x28
# (40) byte Entity struct, then _distanceToBall(2) + _targetXY(4) +
# _launchXY(4) + _zoneCenterXY(4), then _zoneXY1/_zoneXY2 interleaved as
# X1,X2,Y1,Y2 (8 bytes total). Player.Size = 0x72.
_PLAYER_SIZE = 0x72
_ZONE_OFFSET = 40 + 2 + 4 + 4 + 4  # = 54


def read_player_zones(data: bytes, ram_base: int) -> list[dict[str, tuple[int, int]]]:
    zones = []
    for i in range(9):
        off = ram_to_disk(ram_base + i * _PLAYER_SIZE) + _ZONE_OFFSET
        z1 = (read_word(data, off), read_word(data, off + 4))
        z2 = (read_word(data, off + 2), read_word(data, off + 6))
        zones.append({"zone1": z1, "zone2": z2})
    return zones


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    disk_path = Path(argv[0]) if argv else DEFAULT_DISK
    if not disk_path.exists():
        print(f"disk image not found: {disk_path}\n"
              f"(expected your own legally obtained copy at that path -- "
              f"see docs/assets.md)")
        return 1
    data = disk_path.read_bytes()

    print("=== validation: team1/team2 default rosters ===")
    for label, base in (("team1", 0x40A6), ("team2", 0x412A)):
        print(label)
        for i, attrs in enumerate(read_player_roster(data, base)):
            print(f"  {i}: {attrs}")

    print("\n=== bounce dome positions (arena.json bounce_domes) ===")
    print("top   (RAM 0x4B0A):", read_entity_terrain_xy(data, 0x4B0A))
    print("bottom(RAM 0x4B34):", read_entity_terrain_xy(data, 0x4B34))

    print("\n=== electrobounce plate positions (arena.json electrobounces) ===")
    print("left  (RAM 0x4B5E):", read_entity_terrain_xy(data, 0x4B5E))
    print("right (RAM 0x4B88):", read_entity_terrain_xy(data, 0x4B88))

    print("\n=== per-player AI zone rectangles (Player.cs _zoneXY1/_zoneXY2) ===")
    print("prerequisite data for porting sub_D742_AII; roster index order")
    print("matches read_player_roster's pos codes above (0 GK,1 DEF,2 DEF,")
    print("3-5 MID,6-7 WING,8 CFWD)")
    for label, base in (("team1", 0x4BB2), ("team2", 0x4FB4)):
        print(label)
        for i, z in enumerate(read_player_zones(data, base)):
            print(f"  {i}: {z}")

    print("\n=== velocity table (dir 0..7 columns, velocity 0..8 rows) ===")
    print("dir:    0=up 1=up-right 2=right 3=down-right 4=down "
          "5=down-left 6=left 7=up-left")
    for vel, row in read_velocity_table(data).items():
        print(f"  velocity {vel}: {row}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
