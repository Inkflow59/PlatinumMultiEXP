"""Locate the experience distribution code in the battle overlay (overlay 16).

See docs/notes/exp-routine.md. The code is identical in every supported version except
for its load address and absolute call targets, so each patch site is found by searching
for a byte signature in which `bl` instructions are wildcards (`........`).
"""
import re
from dataclasses import dataclass

import capstone

# Each signature starts SIGNATURE_LEAD bytes before the site it identifies.
SIGNATURE_LEAD = 0x30
SIGNATURES = {
    "count_holder": "696f4910c907490f6918a4310968084202d00198401c0190301c06210022........0004010c281c0122........332802d10098401c0090381c0021641c........",
    "shared_zero": "281ca0300068002819d10120a035286015e00199........291c9c310860281c9c300068002803d1281c01219c3001600020a035286002e0281c........0020",
    "loop_break": "........854226da119880000a90206800212a1c........06210022061c........0004000c01210522........332811d0281c........021c61680a984018",
    "share_check": "a1210022........642800d185e060680990281c........11998a0009998918a4310968084203d009989c3000680e900698332806d10998a030099001680e98",
}
EXPECTED_TEXT = {
    "count_holder": "bne #{count_target:#x}",
    "shared_zero": "movs r0, #0",
    "loop_break": "beq #{loop_target:#x}",
    "share_check": "ldr r0, [sp, #0x18]",
}


@dataclass(frozen=True)
class Sites:
    """Absolute RAM addresses of everything the patch touches or branches to."""

    count_holder: int  # BtlCmd_CalcExpGain: `bne` that skips counting an Exp. Share holder
    shared_zero: int  # BtlCmd_CalcExpGain: `movs r0, #0` (sharedExp = 0)
    loop_break: int  # BattleScript_GetExpTask: `beq` that selects a mon in the party loop
    share_check: int  # BattleScript_GetExpTask: item-effect test before adding sharedExp

    @classmethod
    def from_count_holder(cls, count_holder: int) -> "Sites":
        """All other sites sit at fixed distances from this one in every version."""
        return cls(count_holder, count_holder + 0xB0, count_holder + 0x70EC, count_holder + 0x724C)

    # Derived addresses (same fixed layout)
    @property
    def count_target(self) -> int:
        return self.count_holder + 8

    @property
    def exp_gain_end(self) -> int:
        return self.shared_zero + 0xE  # end of BtlCmd_CalcExpGain

    @property
    def loop_target(self) -> int:
        return self.loop_break + 0x26  # first instruction after the party selection loop

    @property
    def share_done(self) -> int:
        return self.share_check + 0x14  # code that follows the old Exp. Share addition

    @property
    def get_value_call(self) -> int:
        return self.count_holder - 0x12  # a `bl Pokemon_GetValue`: its target is readable

    @property
    def dead_block(self) -> tuple:
        """Old "Exp. Share holders" branch of BtlCmd_CalcExpGain, unreachable after the patch."""
        return (self.count_holder + 0x50, self.count_holder + 0x92)


def _signature_regex(signature: str) -> bytes:
    pattern = b""
    for i in range(0, len(signature), 2):
        chunk = signature[i : i + 2]
        pattern += b"." if chunk == ".." else re.escape(bytes.fromhex(chunk))
    return pattern


def locate_sites(overlay: bytes, base: int) -> Sites:
    """Find the patch sites in a battle overlay loaded at `base`; raise if not recognised."""
    found = {}
    for name, signature in SIGNATURES.items():
        matches = [m.start() for m in re.finditer(_signature_regex(signature), overlay, re.DOTALL)]
        if len(matches) != 1:
            raise ValueError(f"Signature {name!r} matched {len(matches)} times (expected 1)")
        found[name] = base + matches[0] + SIGNATURE_LEAD
    sites = Sites.from_count_holder(found["count_holder"])
    for name, address in found.items():
        if getattr(sites, name) != address:
            raise ValueError(f"Unexpected layout: {name} at {address:#x}")
    cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    for name, template in EXPECTED_TEXT.items():
        address = getattr(sites, name)
        offset = address - base
        ins = next(cs.disasm(overlay[offset : offset + 4], address))
        expected = template.format(count_target=sites.count_target, loop_target=sites.loop_target)
        if f"{ins.mnemonic} {ins.op_str}" != expected:
            raise ValueError(f"{name} @ {address:#x}: found {ins.mnemonic} {ins.op_str!r}")
    return sites


def get_value_address(overlay: bytes, base: int, sites: Sites) -> int:
    """Address of Pokemon_GetValue, read from a `bl` next to the patch sites."""
    offset = sites.get_value_call - base
    cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    ins = next(cs.disasm(overlay[offset : offset + 4], sites.get_value_call))
    if ins.mnemonic != "bl":
        raise ValueError("Pokemon_GetValue call not found")
    return int(ins.op_str[1:], 0)


def branches_into(overlay: bytes, base: int, low: int, high: int) -> list:
    """Addresses of Thumb branches (b, b<cond>, bl) whose target lies in ]low, high[."""
    cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    cs.skipdata = True
    hits = []
    for ins in cs.disasm(overlay, base):
        if ins.mnemonic.startswith("b") and ins.mnemonic not in ("bic", "bics", "bkpt", "bx", "blx"):
            if ins.op_str.startswith("#") and low < int(ins.op_str[1:], 0) < high:
                hits.append(ins.address)
    return hits
