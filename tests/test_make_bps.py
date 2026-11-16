import random
from pathlib import Path

import pytest

import build_patch
import make_bps


def test_bps_round_trip():
    rnd = random.Random(1)
    src = bytes(rnd.randrange(256) for _ in range(20000))
    dst = bytearray(src)
    for pos in (0, 5, 4999, 19999):
        dst[pos] ^= 0xFF
    patch = make_bps.create_bps(src, bytes(dst))
    assert make_bps.apply_bps(src, patch) == bytes(dst)
    assert len(patch) < 100


def test_bps_rejects_wrong_source():
    src = bytes(100)
    patch = make_bps.create_bps(src, bytes([1]) + bytes(99))
    with pytest.raises(ValueError):
        make_bps.apply_bps(bytes([2]) + bytes(99), patch)


def test_bps_rejects_corrupt_patch():
    src = bytes(100)
    patch = bytearray(make_bps.create_bps(src, bytes([1]) + bytes(99)))
    patch[6] ^= 0x01
    with pytest.raises(ValueError):
        make_bps.apply_bps(src, bytes(patch))


def test_real_rom_patch_round_trip(rom_path, tmp_path):
    out = tmp_path / "p.nds"
    build_patch.make_patched_rom(rom_path, str(out))
    src = Path(rom_path).read_bytes()
    dst = out.read_bytes()
    patch = make_bps.create_bps(src, dst)
    assert len(patch) < 1000
    assert make_bps.apply_bps(src, patch) == dst
