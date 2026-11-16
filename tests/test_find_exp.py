import pytest

import find_exp
import rom


def test_locate_sites_rejects_unknown_overlay():
    with pytest.raises(ValueError):
        find_exp.locate_sites(bytes(0x35B80), 0x0223B320)


def test_sites_layout_is_consistent():
    sites = find_exp.Sites.from_count_holder(0x022420CC)  # French layout
    assert sites.shared_zero == 0x0224217C
    assert sites.loop_break == 0x022491B8
    assert sites.share_check == 0x02249318
    assert sites.dead_block == (0x0224211C, 0x0224215E)


def test_locate_sites_on_real_rom(rom_path):
    overlay = rom.read_battle_overlay(rom_path)
    base = rom.battle_overlay_base(rom_path)
    sites = find_exp.locate_sites(overlay, base)
    assert sites.count_holder - base in range(0x6000, 0x7000)
    assert 0x02070000 < find_exp.get_value_address(overlay, base, sites) < 0x02080000


def test_dead_block_has_no_incoming_branches(rom_path):
    overlay = rom.read_battle_overlay(rom_path)
    base = rom.battle_overlay_base(rom_path)
    low, high = find_exp.locate_sites(overlay, base).dead_block
    # Branches inside the block are normal; none may come from outside.
    outside = [a for a in find_exp.branches_into(overlay, base, low, high) if not low <= a < high]
    assert outside == []
