# Multi EXP for Pokémon Platinum

A patch that gives experience to **the whole team** after a battle, like in recent
Pokémon games, without having to hold the Exp. Share.

- Pokémon that fought keep their full share.
- Other living Pokémon (eggs excluded) receive **the same full share** (100 %).
- The held Exp. Share no longer stacks with this behaviour.

## Supported ROMs

| Version | Game code | Patch file |
|---|---|---|
| French | `CPUF`, rev 0 | `platinum-multiexp-fr.bps` |
| US | `CPUE`, rev 0 | `platinum-multiexp-us.bps` |
| US Rev 1 | `CPUE`, rev 1 | `platinum-multiexp-us-rev1.bps` |
| Europe | `CPUE`, rev 10 | `platinum-multiexp-eu.bps` |
| Japanese | `CPUJ`, rev 0 | `platinum-multiexp-jp.bps` |
| Spanish | `CPUS`, rev 0 | `platinum-multiexp-es.bps` |
| German | `CPUD`, rev 0 | `platinum-multiexp-de.bps` |
| Italian | `CPUI`, rev 0 | `platinum-multiexp-it.bps` |

Other versions are not supported: the tool refuses to patch an unknown ROM, and a
`.bps` patch refuses to apply to a ROM it was not made for (CRC check).

Status: the French patch was tested in melonDS. The other patches were not played in an
emulator yet, but they are built by the same code, and the automated tests run against
all eight ROMs. Back up your save before using any patch.

## Applying a patch

With [Floating IPS](https://www.smwcentral.net/?p=section&a=details&id=11474) or any
BPS-compatible tool, apply the `.bps` matching your ROM to your original ROM. A patch only
contains the differences (109 bytes); it contains no part of the game.

## Rebuilding the patches

```bash
python -m pip install -r requirements.txt
python tools/build_release.py build/release "<rom1>.nds" "<rom2>.nds" ...
```

To produce a patched ROM directly instead:

```bash
python tools/build_patch.py "<rom>.nds" "<patched>.nds"
```

## Changing the share of non-participants

In `tools/build_patch.py`, `NON_PARTICIPANT_SHARE_SHIFT = 0` gives 100 % (current); `1` gives 50 %.
Rebuild the patches afterwards.

## How it works

The battle code lives in overlay 16 (not in the ARM9). Four small edits and two short
routines (placed in a block of code that becomes unreachable) hijack the Exp. Share logic.
Details: [docs/notes/exp-routine.md](docs/notes/exp-routine.md). Each patch site is found
by a byte signature, so the same code supports every version above.

## Tests

```bash
set PLATINUM_ROMS=<rom1>.nds;<rom2>.nds;<rom3>.nds    # os.pathsep-separated
python -m pytest tests
```

Without `PLATINUM_ROMS`, the tests that need real ROMs are skipped. ROM files (`*.nds`)
are git-ignored and must never be committed.

A manual in-game checklist is in [docs/notes/checklist-tests.md](docs/notes/checklist-tests.md).
