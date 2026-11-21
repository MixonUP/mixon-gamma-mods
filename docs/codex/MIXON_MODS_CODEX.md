# Codex handoff: Mixon GAMMA mods (overview)

This repository holds the author's own addons for **S.T.A.L.K.E.R. Anomaly 1.5.3 + Modded Exes (xray-monolith), as packaged in G.A.M.M.A.** Read this file first, then the per-mod handoff for the mod you work on.

You cannot run the game; the author tests in-game. Do **not** commit, push or publish. Leave changes uncommitted for review.

## The mods

| Mod (folder in `mods/`) | Version | What it does | Scripts | Handoff |
|---|---|---|---|---|
| Zone Operations (Mixon) | 1.2.0 | faction operations: lead allied squads, captured places keep a garrison, services and a commander with tasks | `zop_*.script`, `modxml_zop.script` | `docs/codex/ZONE_OPERATIONS_CODEX.md` |
| Mixon Companion Training | 11.0.0 | companion XP, 10 levels, 7 perk branches, PDA-style training window, medic, player knockdown + revive, artefact search, voiced banter (RU/EN) | `cup_*.script`, `a_cup_prehit.script`, `modxml_cup.script` | this file + `mods/Mixon Companion Training/README_RU.txt` |
| Mixon Backpack Upgrades | 1.0.0 | upgrade trees for backpacks at technicians: 4 classes, 5 columns, +1 artefact slot, damage reduction capped at 50% | `a_kreiser_bpu.script`, `kreiser_bpu_mcm.script` | this file |
| Zombie Raid (Mixon) | 1 | zombie horde on F10 or at random, 4 sizes, "repel the attack" task, pay by kills | `zzz_kreiser_zombie_horde*.script` | this file |
| Carry Weight (Mixon) | 1 | +10..150 kg carry weight slider via Experience Framework `weight.add_weight` | `zzz_kreiser_carry_plus50.script`, `zzz_mixon_carry_mcm.script` | this file |
| Legendary Mutants (Mixon) | — | not written yet; full design and task pack | — | `docs/codex/LEGENDARY_MUTANTS_CODEX.md` |

`patches/` holds diffs for other authors' mods (TLRA, ZCP, WTF, FDDA, Dirt & Wear, anti awol, Tasks QoL). They are not our mods; touch them only when asked.

User docs for every mod live in `README.md` (RU) and `README.en.md` (EN): description, MCM table, dependencies, FAQ, CHANGELOG. Keep both languages in sync when behaviour changes.

## Hard rules for every mod (each one already crashed the game)

1. `.script` files: **ASCII only**. Player-visible text goes to xml string tables in **windows-1251**, RU and EN with identical ids.
2. **Never** call `file_list_open_ex` on `$game_meshes$` (native crash). Before `set_visual_name`, check the model exists.
3. `load_state` only copies data; touch objects, squads or the camera on the first `actor_on_update`.
4. Check every engine object for nil before use (`alife():object(id)`, `level.object_by_id`, squad methods); `pcall` where the engine can throw.
5. Callbacks never throw: `pcall` around the body, log with the mod prefix (`[CUP]`, `![ZOP]` ...).
6. Never index a table with an engine constant that may be nil on these exes (e.g. `hit.wound_2`).
7. MCM files must end in `mcm.script` with a global `on_mcm_load()`. Read values with `pcall(ui_mcm.get, ...)` and fall back to defaults.
8. `AddScriptCallback` once at file scope. Task rewards use `reward_item`, task icons must exist.
9. Old saves must keep working: new fields get defaults; one-off fixes go into a migration that runs once.
10. Scripts reload on save load; xml and textures only after a full game restart.
11. Per-frame work tiny; heavy logic on a throttle.
12. Keep line endings as found (e.g. `zop_operations.ltx` is LF).

## Standing decisions by the author

- Never mention Telegram in posts or descriptions.
- Releases (version bump in `meta.ini`, zip in `release/`, ModDB upload) are done by the author with Claude, not by you.

## Open work outside Zone Operations

- **Companion Training:** the author rejected the big "living squad" concept as too complex. Candidate small perks, none chosen yet: weapon specialisation, field repair with a consumable, a short non-stacking accuracy bonus after a kill. Do not implement until the author picks.
- **Legendary Mutants:** ready to implement from its task pack when the author says so.
- **README CHANGELOG:** has no Zone Operations 1.2.0 row (1.2.0: Kholodny's new look, Racuro and Fin tasks, fairer defence waves, Yanov/Rostok/raid fixes, public API).

## What to hand back

Changed files with a one-line reason each; exact in-game test steps for every code change; anything you could not verify statically.
