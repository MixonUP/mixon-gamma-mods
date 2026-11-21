# Codex handoff: Zone Operations (Mixon)

You are taking over an existing, released addon for **S.T.A.L.K.E.R. Anomaly 1.5.3 + Modded Exes (xray-monolith), as packaged in G.A.M.M.A.** Current version is **1.2.0** (commit `6e0b0fe`, published to ModDB 2026-11-21, awaiting moderation).

You cannot run the game. The author tests in-game. Deliver code that is syntactically valid, defensive at every engine call, and easy to test. Do **not** commit, push or publish; leave changes uncommitted for review.

---

## 1. Where things are

- Repo root = your `cwd` (`mixon-gamma-mods`). The mod: `mods/Zone Operations (Mixon)/`.
- The installed copy the author plays is `E:\GAMMA\GAMMA RC3\mods\Zone Operations (Mixon)\`. The repo is synced from it with `robocopy /MIR`. **Edit in the repo only**; the author copies to the live folder.
- Docs: `README.md` / `README.en.md` (Zone Operations section), `docs/zop_quests_ru.md` (every operation and task), `docs/zop_api.md` (public API), `docs/posts/zone_operations_moddb.html` (ModDB page text).
- Do not touch other mods, `patches/`, `release/`, `tools/`, or untracked media.

### Scripts (`gamedata/scripts/`)

| File | Role |
|---|---|
| `zop_registry.script` | reads `[zop_ops]` list* keys and each operation section from `configs/misc/zone_ops/zop_operations.ltx` |
| `zop_core.script` | operation state machine: start, step_assault, step_wait, step_defend (waves), finish, hand_over (`lose_as`), cooldowns, `migrate()` for old saves, save/load |
| `zop_world.script` | `capture(smart, op, no_top_up)`, garrisons, service NPCs arriving at captured bases |
| `zop_spawn.script` | squad spawning, steering, `squad_ids(name)`, `evacuate` |
| `zop_census.script` | counts live fighters at a target (`count`, `members`, `release_forced`) |
| `zop_battle.script` | invulnerability wrappers, engagement, `own_story` protection |
| `zop_raid.script` | raid tasks: convoy / ambush / camp / supply (`zop_raid_setup`, `zop_raid_ready`, status/target functors) |
| `zop_courier.script` | courier tasks between bases, `zop_task_deadline` / `zop_task_overdue` |
| `zop_api.script` | public API (VERSION = 1): events + queries, see `docs/zop_api.md` |
| `modxml_zop.script` | dialog injection |

### Configs

- `configs/misc/zone_ops/zop_operations.ltx`: all operations. **LF line endings** — keep them LF.
- `configs/misc/task/mod_task_manager_zop.ltx`: all tasks (Kholodny, Viking, Kompas, Yastreb, Colonel Mixon, Racuro, Fin).
- `configs/text/eng/ui_st_zop.xml`, `configs/text/rus/ui_st_zop.xml`: **windows-1251**, identical ids in both.
- `configs/mod_system_zop.ltx`: items (e.g. `zop_courier_serum`).

## 2. Hard rules (each one already crashed the game)

1. `.script` files are **ASCII only**. Player-visible text goes to the xml string tables (cp1251, RU and EN with the same ids).
2. **Never** call `file_list_open_ex` on `$game_meshes$` (native crash). Before `set_visual_name`, check the model file exists.
3. `load_state` only copies data. Touch objects/squads on the first `actor_on_update`.
4. Every engine call on something that may be gone (`alife():object(id)`, `level.object_by_id`, squad methods) checks for nil and is wrapped in `pcall` where it can throw.
5. Callbacks never throw: wrap bodies in `pcall`, log with `printf("![ZOP] ...")`.
6. `AddScriptCallback` once at file scope (as in `zop_api.script`); calling it again errors "callback already exists".
7. Task rewards: `reward_item` (gives to the actor), not `give_item`. Task icons must be existing ones.
8. A task NPC's tasks are found by id prefix = its character profile id (`zop_csky_racuro_medic_task_N`).
9. Old saves must keep working: new state goes behind defaults, one-off fixes go into `zop_core.migrate()` with a flag in `st.fixed`.
10. Per-frame work tiny; heavy logic on a throttle.

## 3. Design decisions already made by the author (do not reverse)

- Clear Sky operations are given by **Cold (Холод)**, not Lebedev.
- Kholodny (Jupiter checkpoint commander) wears an exoskeleton, beret, jaw implant and black eye patch. Racuro = medic, Fin = cook/barman at the checkpoint.
- Never mention Telegram in any post or description.

## 4. Backlog (in priority order)

### A. Doc fixes (no game needed) — start here

Check each against the code/config first, then fix README.md, README.en.md, `docs/zop_quests_ru.md` and `docs/posts/zone_operations_moddb.html` consistently:
1. Hideout Furniture is written as "optional"; verify whether bases actually need it and word it correctly.
2. Operation Factory has 4 targets, not 3 stages (check `zop_operations.ltx`).
3. "Cooldown after each operation" — check which operations really have a cooldown and word it precisely.
4. The reinforcement rule (2 squads when ≤3 fighters remain) applies only to the operations that define it in the ltx; say which.
5. Loki's tasks (if any exist in `mod_task_manager_zop.ltx`) are missing from `zop_quests_ru.md`.

### B. Quick features

1. **Why is an operation unavailable?** In the giver's dialog, when no operation is available, say the reason (cooldown hours left, previous operation not done, story condition such as Brain Scorcher). Build on `zop_core.available()` / `zop_api.check_conditions`.
2. **Base summary**: a PDA news tip or dialog line listing the player's faction bases (`zop_api.bases_of`).
3. **Paid garrison top-up** at a captured base commander.
4. MCM options for any new events (file must end in `mcm.script`, global `on_mcm_load()`).

### C. Events (bigger, design with the author first)

Base counterattacks, supply caravans, a commander's call for help, waves after an emission. Use the `zop_api` events.

## 5. Not yet verified in-game (tell the author what to test after your change)

- Defence waves: the timer counts only while the actor is near; stragglers are pulled back up to 3 times.
- Yanov handover to Duty (`lose_as = duty_yanov`) if Freedom loses the defence.
- Own-side story NPC invulnerability in battle.

## 6. What to hand back

- A short list of changed files and what changed in each.
- For every code change: the exact in-game steps to test it (which save situation, which NPC, what should happen, which log line to expect).
- Anything you could not verify statically.
