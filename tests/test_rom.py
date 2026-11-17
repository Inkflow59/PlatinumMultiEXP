import pytest

import rom


def test_detect_version_rejects_unsupported_code(tmp_path):
    header = bytearray(0x200)
    header[0x0C:0x10] = b"CPUK"
    path = tmp_path / "fake.nds"
    path.write_bytes(bytes(header))
    with pytest.raises(ValueError):
        rom.detect_version(str(path))


def test_detect_version_rejects_unsupported_revision(tmp_path):
    header = bytearray(0x200)
    header[0x0C:0x10] = b"CPUE"
    header[0x1E] = 2
    path = tmp_path / "fake.nds"
    path.write_bytes(bytes(header))
    with pytest.raises(ValueError):
        rom.detect_version(str(path))


def test_detect_version_accepts_real_rom(rom_path):
    assert rom.detect_version(rom_path) in rom.SUPPORTED_VERSIONS


def test_arm9_is_readable(rom_path):
    assert len(rom.read_arm9(rom_path)) > 0x100000


def test_battle_overlay_is_readable(rom_path):
    overlay = rom.read_battle_overlay(rom_path)
    assert len(overlay) > 0x30000
    assert 0x02200000 < rom.battle_overlay_base(rom_path) < 0x02300000
