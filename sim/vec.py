from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Vec:
    x: int
    y: int

    def __add__(self, o: "Vec") -> "Vec":
        return Vec(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec") -> "Vec":
        return Vec(self.x - o.x, self.y - o.y)

    def manhattan(self, o: "Vec") -> int:
        return abs(self.x - o.x) + abs(self.y - o.y)

    def chebyshev(self, o: "Vec") -> int:
        return max(abs(self.x - o.x), abs(self.y - o.y))


# dir 0..7: 0=N then clockwise
DIR_VECTORS: tuple[Vec, ...] = (
    Vec(0, -1), Vec(1, -1), Vec(1, 0), Vec(1, 1),
    Vec(0, 1), Vec(-1, 1), Vec(-1, 0), Vec(-1, -1),
)

_MIRROR_X = (0, 7, 6, 5, 4, 3, 2, 1)  # reflect east<->west
_MIRROR_Y = (4, 3, 2, 1, 0, 7, 6, 5)  # reflect north<->south


def mirror_dir_x(d: int) -> int:
    return _MIRROR_X[d & 7]


def mirror_dir_y(d: int) -> int:
    return _MIRROR_Y[d & 7]


def dir_towards(src: Vec, dst: Vec) -> int:
    """8-way direction from src toward dst (ties resolve to diagonals)."""
    dx = (dst.x > src.x) - (dst.x < src.x)
    dy = (dst.y > src.y) - (dst.y < src.y)
    return {(0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
            (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
            (0, 0): 0}[(dx, dy)]
