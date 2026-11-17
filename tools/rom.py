"""Reading Pokemon Platinum ROMs (French, US, US Rev 1).

The battle code, including the experience distribution, lives in overlay 16, which is
stored uncompressed in the ROM. Its load address depends on the game version.
"""
import struct
from typing import NamedTuple

import ndspy.rom

BATTLE_OVERLAY_ID = 16


class RomVersion(NamedTuple):
    game_code: str
    revision: int
    tag: str  # short name used in patch file names


SUPPORTED_VERSIONS = [
    RomVersion("CPUF", 0, "fr"),
    RomVersion("CPUE", 0, "us"),
    RomVersion("CPUE", 1, "us-rev1"),
    RomVersion("CPUE", 10, "eu"),  # "Europe" dump, header says CPUE rev 10
]


def detect_version(rom_path: str) -> RomVersion:
    """Return the supported version of the ROM, or raise ValueError."""
    with open(rom_path, "rb") as f:
        header = f.read(0x200)
    code = header[0x0C:0x10].decode("ascii", errors="replace")
    revision = header[0x1E]
    for version in SUPPORTED_VERSIONS:
        if (version.game_code, version.revision) == (code, revision):
            return version
    raise ValueError(f"Unsupported ROM: game code {code!r}, revision {revision}")


def read_arm9(rom_path: str) -> bytes:
    detect_version(rom_path)
    return bytes(ndspy.rom.NintendoDSRom.fromFile(rom_path).arm9)


def _battle_overlay(rom_path: str):
    detect_version(rom_path)
    overlay = ndspy.rom.NintendoDSRom.fromFile(rom_path).loadArm9Overlays()[BATTLE_OVERLAY_ID]
    if overlay.compressed:
        raise ValueError("Overlay 16 is compressed: not supported")
    return overlay


def read_battle_overlay(rom_path: str) -> bytes:
    """Overlay 16 (battle), as stored in the ROM."""
    return bytes(_battle_overlay(rom_path).data)


def battle_overlay_base(rom_path: str) -> int:
    """RAM address the battle overlay is loaded at."""
    return _battle_overlay(rom_path).ramAddress


def battle_overlay_file_offset(rom_path: str) -> int:
    """Offset of the first byte of overlay 16 inside the .nds file."""
    file_id = _battle_overlay(rom_path).fileID
    with open(rom_path, "rb") as f:
        f.seek(0x48)
        fat_offset = struct.unpack("<I", f.read(4))[0]
        f.seek(fat_offset + 8 * file_id)
        start, _end = struct.unpack("<II", f.read(8))
    return start
