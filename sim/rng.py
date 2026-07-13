"""Seedable RNG matching the original Speedball 2 generator.

Algorithm documented by the reverse-engineering projects (see
docs/spec/mechanics.md). Two 32-bit state words; each step shifts and
add-with-carries their 16-bit halves, swapping halves between two rounds.
Default seed constants are the ones the original game boots with.
"""

_M16 = 0xFFFF
_M32 = 0xFFFFFFFF


class Sb2Rng:
    def __init__(self, a: int = 0x31415926, b: int = 0x53589793) -> None:
        self.a = a & _M32
        self.b = b & _M32

    def next(self) -> int:
        a_hi, a_lo = (self.a >> 16) & _M16, self.a & _M16
        b_hi, b_lo = (self.b >> 16) & _M16, self.b & _M16

        a_lo <<= 1
        carry = a_lo > _M16
        a_lo &= _M16

        for _ in range(2):
            pre_add = a_lo
            a_lo += b_lo + (1 if carry else 0)
            carry = a_lo > _M16
            a_lo &= _M16
            b_lo = pre_add
            a_hi, a_lo = a_lo, a_hi
            b_hi, b_lo = b_lo, b_hi

        self.a = ((a_hi << 16) | a_lo) & _M32
        self.b = ((b_hi << 16) | b_lo) & _M32
        return self.a

    def next_byte(self, mask: int = 0xFF) -> int:
        return self.next() & 0xFF & mask

    def next_word(self, mask: int = 0xFFFF) -> int:
        return self.next() & 0xFFFF & mask
