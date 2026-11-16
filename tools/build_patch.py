"""Build the Multi EXP patch: modifies the battle overlay (overlay 16) of Pokemon Platinum.

See docs/notes/exp-routine.md for the rationale behind each change.
Usage: python tools/build_patch.py <original_rom.nds> <patched_rom.nds>
Supported ROMs: French, US, US Rev 1 (detected automatically).
"""
import sys

from keystone import KS_ARCH_ARM, KS_MODE_THUMB, Ks

import find_exp
import rom as rommod
from find_exp import Sites

# Fraction of the EXP a Pokemon receives when it did not take part in the battle,
# relative to a participant: participant EXP >> SHIFT.
# SHIFT = 1 -> 50 % (like Gen 6/7); SHIFT = 0 -> 100 %.
NON_PARTICIPANT_SHARE_SHIFT = 1

MON_DATA_IS_EGG = 0x4C


def assemble(source: str, address: int) -> bytes:
    data, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(source, address)
    return bytes(data)


def payload1_source(sites: Sites) -> str:
    """sharedExp = max(1, gainedExp >> SHIFT), then return to the end of BtlCmd_CalcExpGain.

    Input: r5 = battle context (gainedExp at +0x9C, sharedExp at +0xA0).
    """
    shift = (
        f"lsrs r0, r0, #{NON_PARTICIPANT_SHARE_SHIFT}"
        if NON_PARTICIPANT_SHARE_SHIFT
        else "movs r0, r0"
    )
    return f"""
        adds r0, r5, #0
        adds r0, #0x9c
        ldr  r0, [r0]
        {shift}
        bne  store
        movs r0, #1
    store:
        adds r5, #0xa0
        str  r0, [r5]
        b    {sites.exp_gain_end:#x}
    """


def payload2_source(get_value: int) -> str:
    """Called with `bl` from BattleScript_GetExpTask (caller's sp is 4 lower after the push).

    Participant ([sp+0x38] != 0 in the caller): leave the EXP untouched. Otherwise, unless
    the Pokemon (r6) is an egg, its EXP becomes sharedExp (at [[sp+0x24] + 0xA0]).
    """
    return f"""
        push {{lr}}
        ldr  r0, [sp, #0x3c]
        cmp  r0, #0
        bne  done
        adds r0, r6, #0
        movs r1, #{MON_DATA_IS_EGG:#x}
        movs r2, #0
        bl   {get_value:#x}
        cmp  r0, #0
        bne  done
        ldr  r0, [sp, #0x28]
        adds r0, #0xa0
        ldr  r0, [r0]
        str  r0, [sp, #0x3c]
    done:
        pop  {{pc}}
    """


def build_patches(overlay: bytes, base: int) -> dict:
    """Return {ram_address: bytes} to write into the overlay; checks the original code first."""
    sites = find_exp.locate_sites(overlay, base)
    get_value = find_exp.get_value_address(overlay, base, sites)

    payload1_addr = sites.dead_block[0]
    payload1 = assemble(payload1_source(sites), payload1_addr)
    payload2_addr = payload1_addr + len(payload1)
    payload2 = assemble(payload2_source(get_value), payload2_addr)
    if payload2_addr + len(payload2) > sites.dead_block[1]:
        raise ValueError("The added code does not fit in the dead block")

    return {
        sites.count_holder: assemble(f"b {sites.count_target:#x}", sites.count_holder),
        sites.shared_zero: assemble(f"b {payload1_addr:#x}", sites.shared_zero),
        sites.loop_break: assemble(f"b {sites.loop_target:#x}", sites.loop_break),
        sites.share_check: assemble(f"bl {payload2_addr:#x}", sites.share_check)
        + assemble(f"b {sites.share_done:#x}", sites.share_check + 4),
        payload1_addr: payload1,
        payload2_addr: payload2,
    }


def apply_patches(overlay: bytes, base: int, patches: dict) -> bytes:
    out = bytearray(overlay)
    for addr, data in patches.items():
        out[addr - base : addr - base + len(data)] = data
    return bytes(out)


def make_patched_rom(rom_path: str, out_path: str) -> rommod.RomVersion:
    """Write a patched copy of the ROM (only overlay 16 bytes change). Returns the version."""
    version = rommod.detect_version(rom_path)
    base = rommod.battle_overlay_base(rom_path)
    patches = build_patches(rommod.read_battle_overlay(rom_path), base)
    file_offset = rommod.battle_overlay_file_offset(rom_path)
    with open(rom_path, "rb") as f:
        data = bytearray(f.read())
    for addr, payload in patches.items():
        start = file_offset + (addr - base)
        data[start : start + len(payload)] = payload
    with open(out_path, "wb") as f:
        f.write(data)
    return version


if __name__ == "__main__":
    detected = make_patched_rom(sys.argv[1], sys.argv[2])
    print(f"Patched ROM written ({detected.tag}): {sys.argv[2]}")
