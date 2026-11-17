from pathlib import Path

import pytest
from unicorn import UC_ARCH_ARM, UC_MODE_THUMB, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_SP

import build_patch as bp
import find_exp
import rom

CTX = 0x02300000  # fake battle context: gainedExp at +0x9C, sharedExp at +0xA0
SP = 0x02380000

# (count_holder site, Pokemon_GetValue address): French and US layouts
LAYOUTS = [(0x022420CC, 0x02074510), (0x02241DE4, 0x02074470)]


def _emulator(code_blocks):
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    uc.mem_map(0x02000000, 0x400000)
    for addr, data in code_blocks.items():
        uc.mem_write(addr, data)
    return uc


def _payloads(layout):
    count_holder, get_value = layout
    sites = find_exp.Sites.from_count_holder(count_holder)
    addr1 = sites.dead_block[0]
    p1 = bp.assemble(bp.payload1_source(sites), addr1)
    addr2 = addr1 + len(p1)
    p2 = bp.assemble(bp.payload2_source(get_value), addr2)
    return sites, addr1, p1, addr2, p2


def _run_payload1(layout, gained):
    sites, addr1, p1, _, _ = _payloads(layout)
    uc = _emulator({addr1: p1})
    uc.mem_write(CTX + 0x9C, gained.to_bytes(4, "little"))
    uc.mem_write(CTX + 0xA0, (0xDEAD).to_bytes(4, "little"))
    uc.reg_write(UC_ARM_REG_R5, CTX)
    uc.emu_start(addr1 | 1, sites.exp_gain_end)
    return int.from_bytes(uc.mem_read(CTX + 0xA0, 4), "little")


def _run_payload2(layout, total_exp, shared, is_egg):
    sites, _, _, addr2, p2 = _payloads(layout)
    stub = bp.assemble(f"movs r0, #{int(is_egg)}\nbx lr", layout[1])  # fake Pokemon_GetValue
    uc = _emulator({addr2: p2, layout[1]: stub})
    uc.mem_write(SP + 0x38, total_exp.to_bytes(4, "little"))  # caller's totalExp
    uc.mem_write(SP + 0x24, CTX.to_bytes(4, "little"))  # caller's battle context pointer
    uc.mem_write(CTX + 0xA0, shared.to_bytes(4, "little"))
    uc.reg_write(UC_ARM_REG_SP, SP)
    uc.reg_write(UC_ARM_REG_R6, 0x02200000)
    return_addr = sites.share_check + 4
    uc.reg_write(UC_ARM_REG_LR, return_addr | 1)
    uc.emu_start(addr2 | 1, return_addr)
    return int.from_bytes(uc.mem_read(SP + 0x38, 4), "little"), uc.reg_read(UC_ARM_REG_SP)


@pytest.fixture(params=LAYOUTS, ids=["fr-layout", "us-layout"])
def layout(request):
    return request.param


def test_non_participant_share_is_full(layout):
    assert bp.NON_PARTICIPANT_SHARE_SHIFT == 0
    assert _run_payload1(layout, 100) == 100
    assert _run_payload1(layout, 101) == 101


def test_non_participant_share_is_never_zero(layout):
    assert _run_payload1(layout, 1) == 1
    assert _run_payload1(layout, 0) == 1


def test_participant_keeps_full_exp_untouched(layout):
    total, sp = _run_payload2(layout, total_exp=77, shared=33, is_egg=False)
    assert total == 77
    assert sp == SP  # stack balanced


def test_non_participant_receives_shared_exp(layout):
    total, sp = _run_payload2(layout, total_exp=0, shared=33, is_egg=False)
    assert total == 33
    assert sp == SP


def test_egg_receives_nothing(layout):
    total, sp = _run_payload2(layout, total_exp=0, shared=33, is_egg=True)
    assert total == 0
    assert sp == SP


def test_payloads_fit_in_dead_block(layout):
    sites, _, _, addr2, p2 = _payloads(layout)
    assert addr2 + len(p2) <= sites.dead_block[1]


def test_patches_only_touch_expected_addresses(rom_path):
    overlay = rom.read_battle_overlay(rom_path)
    base = rom.battle_overlay_base(rom_path)
    patches = bp.build_patches(overlay, base)
    patched = bp.apply_patches(overlay, base, patches)
    changed = {i for i in range(len(overlay)) if overlay[i] != patched[i]}
    allowed = set()
    for addr, data in patches.items():
        allowed.update(range(addr - base, addr - base + len(data)))
    assert changed and changed <= allowed
    assert len(changed) < 120


def test_make_patched_rom_changes_only_overlay_bytes(rom_path, tmp_path):
    out = tmp_path / "patched.nds"
    version = bp.make_patched_rom(rom_path, str(out))
    assert version == rom.detect_version(rom_path)
    src = Path(rom_path).read_bytes()
    dst = out.read_bytes()
    assert len(src) == len(dst)
    diff = [i for i in range(len(src)) if src[i] != dst[i]]
    start = rom.battle_overlay_file_offset(rom_path)
    assert diff and all(start <= i < start + len(rom.read_battle_overlay(rom_path)) for i in diff)
    assert len(diff) < 120


def test_patched_rom_is_recognised_as_already_patched(rom_path, tmp_path):
    """Patching an already patched ROM must fail loudly instead of corrupting it."""
    out = tmp_path / "patched.nds"
    bp.make_patched_rom(rom_path, str(out))
    with pytest.raises(ValueError):
        bp.make_patched_rom(str(out), str(tmp_path / "twice.nds"))
