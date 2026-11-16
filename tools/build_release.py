"""Build one BPS patch per ROM given on the command line.

Usage: python tools/build_release.py <out_dir> <rom1.nds> [<rom2.nds> ...]
Writes <out_dir>/platinum-multiexp-<version>.bps (version: fr, us, us-rev1).
"""
import os
import sys
import tempfile

import build_patch
import make_bps


def build_release(rom_path: str, out_dir: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        patched_path = os.path.join(tmp, "patched.nds")
        version = build_patch.make_patched_rom(rom_path, patched_path)
        with open(rom_path, "rb") as f1, open(patched_path, "rb") as f2:
            bps = make_bps.create_bps(f1.read(), f2.read())
    out_path = os.path.join(out_dir, f"platinum-multiexp-{version.tag}.bps")
    with open(out_path, "wb") as f:
        f.write(bps)
    return out_path


if __name__ == "__main__":
    os.makedirs(sys.argv[1], exist_ok=True)
    for path in sys.argv[2:]:
        print("Written:", build_release(path, sys.argv[1]))
