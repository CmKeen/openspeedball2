from sim.rng import Sb2Rng

# Golden vector computed from the documented algorithm at the default seed.
GOLDEN = [0x849A49DF, 0xB5DC460A, 0x3A771FD2, 0xF053CBB8,
          0x2ACAD715, 0x1B1E459B, 0x45E93960, 0x6107FDF6]


def test_golden_sequence_from_default_seed():
    rng = Sb2Rng()
    assert [rng.next() for _ in range(8)] == GOLDEN


def test_next_byte_masks_low_bits():
    rng = Sb2Rng()
    assert rng.next_byte() == GOLDEN[0] & 0xFF  # 0xDF == 223
    assert rng.next_byte(0x0F) == GOLDEN[1] & 0x0F


def test_same_seed_same_stream_different_seed_diverges():
    s1 = [Sb2Rng(1, 2).next() for _ in range(50)]
    s2 = [Sb2Rng(1, 2).next() for _ in range(50)]
    s3 = [Sb2Rng(1, 3).next() for _ in range(50)]
    assert s1 == s2
    assert s1 != s3


def test_output_is_32_bit():
    rng = Sb2Rng()
    for _ in range(1000):
        assert 0 <= rng.next() <= 0xFFFFFFFF
