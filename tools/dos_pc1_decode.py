"""Decode Atari-ST Degas Elite .PC1 screens (used by the DOS Speedball 2 port)
into PNGs for local reference/testing.

.PC1 is a well-documented, decades-old format: a 2-byte resolution+compressed
flag, a 16-color palette (3-bit-per-channel ST RGB), then PackBits-compressed
320x200x4bpp planar bitmap data.

Local-use tool only -- see README asset policy. Output goes to the gitignored
assets/ folder and must never be committed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pygame

WIDTH, HEIGHT, PLANES = 320, 200, 4
BYTES_PER_LINE_PER_PLANE = WIDTH // 16 * 2  # 40 bytes
DECOMPRESSED_SIZE = BYTES_PER_LINE_PER_PLANE * PLANES * HEIGHT  # 32000


def _unpack_bits(data: bytes, out_size: int) -> bytes:
    out = bytearray()
    i = 0
    while len(out) < out_size and i < len(data):
        n = data[i]
        i += 1
        if n < 128:
            count = n + 1
            out.extend(data[i:i + count])
            i += count
        elif n > 128:
            count = 257 - n
            out.extend(bytes([data[i]]) * count)
            i += 1
        # n == 128: no-op
    return bytes(out[:out_size])


def _st_palette(raw: bytes) -> list[tuple[int, int, int]]:
    colors = []
    for i in range(16):
        word = (raw[i * 2] << 8) | raw[i * 2 + 1]
        r = (word >> 8) & 0x7
        g = (word >> 4) & 0x7
        b = word & 0x7
        colors.append(tuple(int(c * 255 / 7) for c in (r, g, b)))
    return colors


def decode_pc1(path: Path) -> pygame.Surface:
    data = path.read_bytes()
    resolution = (data[0] << 8) | data[1]
    if resolution & 0x7FFF != 0:
        raise ValueError(f"{path}: only low-res (320x200x16) PC1 supported, got resolution word {resolution:#06x}")

    palette = _st_palette(data[2:34])
    bitmap = _unpack_bits(data[34:], DECOMPRESSED_SIZE)

    surf = pygame.Surface((WIDTH, HEIGHT))
    px = pygame.PixelArray(surf)

    words_per_line = BYTES_PER_LINE_PER_PLANE // 2  # 20 words/plane/line
    for y in range(HEIGHT):
        line_off = y * BYTES_PER_LINE_PER_PLANE * PLANES
        for wx in range(words_per_line):
            plane_words = []
            for p in range(PLANES):
                off = line_off + p * BYTES_PER_LINE_PER_PLANE + wx * 2
                plane_words.append((bitmap[off] << 8) | bitmap[off + 1])
            for bit in range(16):
                shift = 15 - bit
                idx = 0
                for p in range(PLANES):
                    idx |= ((plane_words[p] >> shift) & 1) << p
                x = wx * 16 + bit
                px[x, y] = palette[idx]

    del px
    return surf


def main(argv: list[str]) -> int:
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))

    if not argv:
        print("usage: python -m tools.dos_pc1_decode <src_dir_with_pc1> <out_dir>", file=sys.stderr)
        return 1

    src_dir = Path(argv[0])
    out_dir = Path(argv[1]) if len(argv) > 1 else Path("assets/screens")
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for pc1_path in sorted(src_dir.glob("*.PC1")):
        try:
            surf = decode_pc1(pc1_path)
        except ValueError as e:
            print(f"skip: {e}")
            continue
        out_path = out_dir / (pc1_path.stem + ".png")
        pygame.image.save(surf, str(out_path))
        print(f"wrote {out_path}")
        count += 1

    print(f"decoded {count} screen(s) into {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
