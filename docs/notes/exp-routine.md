# Experience routine in Pokémon Platinum

Found by disassembling (capstone) the **battle overlay (overlay 16)** and cross-checking
with the public pret/pokeplatinum decompilation (`BtlCmd_CalcExpGain` and
`BattleScript_GetExpTask` in `battle_script.c`). The ARM9 holds nothing relevant: the
original design targeted it by mistake.

Addresses below are for the French ROM (overlay base `0x0223B320`). The code is the same in
the other ROMs (e.g. US base `0x0223B140`, everything 0x2E8 lower; JP `0x0223A540`); the tools find each site with a
byte signature, so nothing is hard-coded per version.

Constants: Exp. Share hold effect = `0x33`, Lucky Egg = `0x42`, `MON_DATA_IS_EGG` = `0x4C`,
`Pokemon_GetValue` = `0x02074510` (FR) / `0x02074470` (US), called with `bl`.
Battle context fields: `gainedExp` at `+0x9C`, `sharedExp` at `+0xA0`.

## Original behaviour
- `BtlCmd_CalcExpGain` (about `0x2242070`-`0x224218E`): counts the Pokémon that gain EXP
  (`[sp+4]`) and those holding the Exp. Share (`[sp]`). If at least one holder exists:
  `gainedExp = (exp/2)/participants`, `sharedExp = (exp/2)/holders`. Otherwise:
  `gainedExp = exp/participants`, `sharedExp = 0`.
- `BattleScript_GetExpTask` (`0x224915C`): walks the party; a Pokémon is processed if it
  holds the Exp. Share or fought. Its gain is `gainedExp` (if it fought) plus `sharedExp`
  (if it holds the item), then Lucky Egg, trainer and trade bonuses. Fainted Pokémon and
  level 100 are filtered out later (HP and level tests).

## Changes
| Address (FR) | Original | New | Effect |
|---|---|---|---|
| `0x022420CC` | `bne 0x22420D4` | `b 0x22420D4` | nobody counts as a holder: the "no Exp. Share" branch is always taken |
| `0x0224217C` | `movs r0,#0` | `b payload1` | `sharedExp = max(1, gainedExp >> SHIFT)` instead of 0 (SHIFT = 0: 100 %) |
| `0x022491B8` | `beq 0x22491DE` | `b 0x22491DE` | the selection loop processes every party member |
| `0x02249318` | `ldr r0,[sp,#0x18]` | `bl payload2` | non-participant (and not an egg): its gain is `sharedExp` |
| `0x0224931C` | `bne 0x224932C` | `b 0x224932C` | the rest of the old Exp. Share test is skipped |
| `0x0224211C`-`0x0224215C` | old "holders" branch (now dead) | payload1 + payload2 | room for the added code |
