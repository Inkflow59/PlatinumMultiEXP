# In-game test checklist (emulator)

Use a **copy** of the patched ROM and a test save. Each line: expected result.

- [ ] Wild battle, 1 participant + 2 other living Pokémon: the participant gains the normal
      EXP; the two others gain the same amount (100 %).
- [ ] Trainer battle: same proportions, trainer bonus (x1.5) kept.
- [ ] Double battle: both Pokémon that fought gain their share; the others gain the same amount.
- [ ] An **egg** in the party: it gains nothing, no EXP message.
- [ ] A **fainted** Pokémon in the party: it gains nothing.
- [ ] A **level 100** Pokémon: it gains nothing, no crash.
- [ ] A Pokémon that levels up without fighting: animation, new moves, evolution offered
      as usual.
- [ ] A Pokémon **holding the Exp. Share**: same gain as without the item (no double gain).
- [ ] Lucky Egg on a non-participant: x1.5 applied.
- [ ] A battle where everyone but one Pokémon is fainted: no crash.
- [ ] Save, quit, reload: the game loads normally.

Done on the French ROM (melonDS): basic behaviour confirmed. US ROMs: not yet played.
