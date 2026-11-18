# Codex task pack: Legendary Mutants (Mixon)

Implement a new addon for **S.T.A.L.K.E.R. Anomaly 1.5.3 + Modded Exes (xray-monolith), as packaged in the G.A.M.M.A. modpack**. The game design is final and inlined below (section 3). Write the mod as Lua scripts + configs only: no engine changes, no new models, no new levels.

You cannot run the game. Deliver code that is syntactically valid, defensive at every engine call, and easy to test in-game by the author. Section 8 lists exactly what to hand back.

---

## 1. Where to work

- Repository root = your `cwd` (`mixon-gamma-mods`). Work only inside it.
- Create the mod here: `mods/Legendary Mutants (Mixon)/`
  - `meta.ini` (copy the format of `mods/Mixon Companion Training/meta.ini`, `version=0.1.0`, `comments=Legendary Mutants (Mixon): named procedural mutant legends, hunts and trophies`)
  - `gamedata/scripts/lgm_*.script`
  - `gamedata/configs/text/eng/lgm.xml` and `gamedata/configs/text/rus/lgm.xml`
  - `gamedata/configs/items/items/items_lgm.ltx` (trophy items, phase 4) if needed
  - `README_RU.txt` short install notes (RU), like the other mods
- Do **not** touch other mods, `README*.md`, `patches/`, `release/`. Do **not** commit; leave everything uncommitted for review.

## 2. Hard rules (each one comes from a real crash we already hit)

1. **Encoding.** `.script` files: **ASCII only** (no Cyrillic, not even in comments). All player-visible text goes to the xml string tables. XML files: **windows-1251** with header `<?xml version="1.0" encoding="windows-1251"?>`, root `<string_table>`, CRLF line endings. Keep RU and EN files with identical string ids.
2. **MCM** only scans files whose name ends in `mcm.script` → the settings file must be `lgm_mcm.script` with a global `function on_mcm_load()` returning the options table. Read values with `pcall(ui_mcm.get, "mixon_lgm/<key>")` and fall back to defaults (see `mods/Mixon Companion Training/gamedata/scripts/cup_mcm.script` lines ~40-60 for the exact pattern).
3. **Never index a table with an engine constant** (e.g. `hit.wound_2` is `nil` on these exes → `t[nil]` crashes). Compare hit types with `==` against values you read safely, or skip.
4. **`load_state` only copies data.** Never touch game objects, cameras, squads or spawn anything during loading. Apply loaded state on the first `actor_on_update` / `actor_on_first_update` (engine calls during load crash natively and `pcall` cannot catch it).
5. **Every engine call on an object that might be gone** (`alife_object(id)`, `level.object_by_id(id)`, squad methods, `register_member`) must check for `nil` first and be wrapped in `pcall` where the engine may throw. Treat `id == false/nil` as "gone". (We just fixed crashes in ZCP, WTF and FDDA that were exactly this.)
6. **Callbacks must never throw.** Wrap the body of each registered callback in `pcall` and log with `printf("LGM: ...")` on error. A thrown error in a callback becomes a "Busy Hands" script-engine failure for the whole game.
7. Scripts reload on save load; xml/text only on a full game restart. Do not rely on hot-reloading text.
8. Keep per-frame work tiny: heavy logic on a 1 s (real time) throttle inside `actor_on_update`.

## 3. Game design (final, from the design doc)

### 3.1 Concept
Every few in-game days a **named legendary mutant** appears: stronger than normal, with 1–3 random **affixes** and a generated name. The player hears about it from PDA rumours, tracks it, kills it for money, a named trophy and a bestiary entry. Each legend is procedural. A legend is an ordinary mutant whose parameters and behaviour are changed by scripts. Displayed names: EN "Legendary Mutants (Mixon)", RU "Легенды Зоны (Mixon)".

Loop: rumour in PDA → contract + search area → tracks narrow the area → fight (affixes) → may flee to a lair and heal → killed → trophy + reward + bestiary.

### 3.2 Generation (all persisted in the save)
**Species by danger belt of the level** (only species that exist on that level):

| Belt | Levels (examples) | Species |
|---|---|---|
| Low | Cordon, Great Swamps, Garbage | blind dog, pseudodog, flesh, boar |
| Mid | Dark Valley, Agroprom, Zaton, Yantar | bloodsucker, snork, lurker, fracture |
| High | Red Forest, Radar, Jupiter, Limansk | chimera, pseudogiant, controller, burer |

Pick mutant **sections** that exist in `ini_sys` (check with `ini_sys:section_exist`). Keep the species→sections list in one table at the top of `lgm_gen.script` so it is easy to edit.

**Rank:**

| Rank | Chance | Health | Affixes | Flees when wounded |
|---|---|---|---|---|
| Mature | 60% | ×3 | 1 | no |
| Alpha | 30% | ×5 | 2 | at 25% health, once |
| Ancient | 10% | ×8 | 3 | at 40% and 20% health |

"Ancient" in the mid and high belts appears only after the first legend has been killed.

**Affixes**: drawn without repeats, respecting incompatible pairs and per-affix allowed species.

**Name**: template "epithet + species + place", the epithet hints at the main affix (e.g. "Iron Hide, boar of Agroprom" / RU "Железная Шкура, кабан с Агропрома"). Build from string-table lists of epithets per affix + species names + level names; RU and EN.

**Spawn rules:**
- Every N in-game days (MCM, default 3, range 1–10) roll a chance to create a legend.
- Level: neighbours of the actor's level or levels already visited. Point: a smart terrain usable by mutants, ≥300 m from faction bases, ≥200 m from the actor.
- At most 3 legends in the world (MCM 1–5), max one per level.
- An untouched legend lives 7 days (MCM 3–14), then "leaves" with a PDA message ("Nobody has seen the Warden since. They say he went to the Red Forest.") and is released.
- Legends are **immune to anomalies and emissions** (so the Zone does not kill them before the player arrives).
- No new legends during an emission; after an emission the chance is doubled for 24 h.

### 3.3 Affixes (12)
Each must change tactics and have a counter, not just add HP.

| Affix | Effect | Counter | Species | Implementation |
|---|---|---|---|---|
| Armoured | −60% bullet damage except armour-piercing | AP ammo, explosives | all | hit callback: scale hit power by ammo type |
| Front-proof | head/chest damage −80% from the front | flank, shoot the back | boar, flesh, pseudogiant | hit callback: angle between hit direction and mutant facing |
| Regeneration | +2% health/s after 3 s without damage | no pauses, incendiary | all | 1 s update while online |
| Pack leader | in combat every 40 s summons 2–3 kin, max 6 alive | kill the leader fast, pack flees | **all** (see 3.8 default) | spawn near it; pack panics when leader dies |
| Berserk | below 50% health +50% damage, never retreats | keep distance, finish with bursts | all melee | damage multiplier in the hit-on-actor callback |
| Radioactive | radiation aura 8 m, corpse irradiates for 24 h | antirad, protective suit, range | all | radiation to actor by distance, particles on mutant |
| Psi aura | psi damage within 15 m, screen blur | psi helmet, psi-block | controller, burer, bloodsucker | psi hit on actor + post-effect |
| Shadow | invisible in darkness and rain, visible in light | hunt by day, NVG | bloodsucker | vanilla bloodsucker invisibility by hour and weather |
| Swift | speed +40%, side dashes | shotgun, narrow passages | **all** | mutant speed multiplier (**verify API exists; if not, skip affix and log**) |
| Anomalous | on death an anomaly and an artefact appear at the corpse | detector, caution at the corpse | all | spawn anomaly + artefact in the death callback |
| Cunning | dodges aim, attacks from behind, avoids traps | companions cover the back, tight rooms | fracture, lurker, chimera | move-to-point orders behind the actor |
| Man-eater | eats corpses to heal 20%, gnawed corpses are its tracks | remove corpses, keep it fighting | bloodsucker, pseudodog, blind dog | find nearby corpses, vanilla corpse-eating |

Incompatible pairs: Armoured + Regeneration; Shadow + Radioactive.
Every legend has a visual marker: faint glow or particles in the colour of its main affix (pick a vanilla particle effect; if attaching to a bone is not possible, play it at the position on each update).

### 3.4 Hunt
- **Rumours**: on spawn, a PDA message from a random stalker hints at the level and the main affix. Then every 4–8 in-game hours a new rumour reveals one more affix. Templates per affix in the string tables (e.g. Armoured: "I hit it with buckshot — like shooting a wall").
- **Contract**: offered by traders, scientists, and the factions **Duty, Freedom and Mercenaries** (they pay for legends near their bases). Dialog line "Got any work on a legend?" Gives a map marker of the area (~150 m radius) and a money reward. **Before a contract and tracks the legend is not on the map.** Killing without a contract gives the trophy but no money.
- **Tracks**: 2–3 track points in the area (a stalker corpse with a note, a gnawed carcass, a torn backpack). Inspecting a track narrows the marker to ~40 m.
- **Fight**: the legend announces itself with a species-specific **roar** audible ~100 m when the actor is near its lair (sound files will be produced later with ElevenLabs: reference `sounds\lgm\roar_<species>.ogg`; if the file does not exist, fall back to a vanilla monster sound of that species). At the health thresholds from the rank table it flees to its **lair** (another smart on the same level) and heals +25% per in-game hour; it leaves a blood trail and the marker moves to the lair. It never leaves its level and never chases the actor further than 200 m from its lair.
- **Outcomes**: killed by actor/companions → full reward. Killed by someone else (NPC, anomaly) → trophy stays on the corpse, no money, PDA message "The legend was taken down by Duty". Not killed in 7 days → leaves, contract fails without penalty. Legend killed the actor → PDA obituary, its reward grows +25%.

States: Rumour → Contract → Tracks → Fight → (health threshold) Flee to lair → back to Tracks via blood trail; Fight → Killed; Rumour/Contract → Gone after the lifetime.

### 3.5 Rewards

| What | Mature | Alpha | Ancient |
|---|---|---|---|
| Contract money, RU | 10 000–15 000 | 15 000–20 000 | 25 000–40 000 (see 3.8) |
| Trophy | normal mutant part ×3 | named part | named part + artefact |
| XP (Experience Framework, optional) | as 3 mutants | as 6 | as 12 |

- **Named part**: a new item based on the species' normal part (heart, hoof, tentacles) with the legend's name in the description; worth 5–10× the normal part; usable in GAMMA crafting as a rare component. Property by main affix: Armoured → armour-upgrade part; Regeneration/Man-eater → medicine ingredient; Psi aura → psi-protection component; Radioactive/Anomalous → artefact container filler. (Phase 4. In phases 1–3 give the normal part ×N.)
- **Special hide**: small chance to also get a rare hide of a different colour: base properties of the species plus, with an extra chance, one property of the killed legend; only for species whose value is balanced by hand. Very rare. (Phase 4.)
- **Bestiary** in the PDA: name, species, affixes, date, how it died. At 30 legends: title "Hunter" and a small trader discount.
- **Companion Training link** (optional, detect `cup_core` at runtime): companions who fought get XP as for 10 kills (`cup_core.add_xp`, see `mods/Mixon Companion Training/gamedata/scripts/cup_core.script`).

### 3.6 Balance
- Legend damage to the actor never more than ×1.5 of normal, even with Berserk.
- Every affix has a counter sold by the nearest trader of that belt.
- Rumours reveal affixes before the fight.
- Contract money on the level of a hard trader task of that belt.

### 3.7 MCM (section "Legendary Mutants (Mixon)", id `mixon_lgm`)

| Key | Setting | Default | Range |
|---|---|---|---|
| `enabled` | Enable mod | on | on/off |
| `interval_days` | Spawn interval, in-game days | 3 | 1–10 |
| `max_alive` | Max legends in the world | 3 | 1–5 |
| `lifetime_days` | Untouched legend lifetime, days | 7 | 3–14 |
| `hp_mult` | Health multiplier | 1.0 | 0.5–2.0 |
| `reward_mult` | Reward multiplier | 1.0 | 0.5–3.0 |
| `allow_flee` | Allow fleeing | on | on/off |
| `map_without_contract` | Show marker without contract | off | on/off |
| `debug` | Debug log + test key | off | on/off |
| `debug_key` | Test key: spawn a legend near the actor | none | key bind, works only with `debug` on |

### 3.8 Defaults chosen for the two open questions
Implement these defaults (the author may change them later):
- **Pack leader on strong species** (chimera, pseudogiant, controller, burer): summon **1–2 weak servants** (blind dogs or zombified) instead of kin of the same strength. Other species summon kin as in the table.
- **Ancient reward**: **25 000–40 000 RU**.

## 4. Architecture

| File | Responsibility |
|---|---|
| `lgm_core.script` | legend registry keyed by object id, spawn timer, lifetime, save/load, debug commands |
| `lgm_gen.script` | rolls: species, rank, affixes, name, smart selection; data tables at the top |
| `lgm_affix.script` | affix behaviour: hit callbacks, 1 s update, death effects, visual markers |
| `lgm_hunt.script` | rumours, contract dialog hooks, tracks, map markers, flee to lair, outcomes |
| `lgm_reward.script` | money, trophies, bestiary, title, Companion Training / Experience Framework hooks |
| `lgm_mcm.script` | MCM options + `get(key)` helper with defaults |
| `a_lgm_prehit.script` | chains `_G.CBaseMonster__BeforeHitCallback` for damage-taken affixes and flee thresholds (see section 5) |

Save data in `m_data.lgm = { v = 1, legends = {...}, bestiary = {...}, kills = n, ancient_unlocked = bool, next_roll = time }`. Store only plain Lua values (numbers, strings, booleans, tables of those). Use in-game time (`game.get_game_time()`; store as numbers via `game.get_game_time():diffSec(...)` relative to a stored epoch, or as day/hour fields) — never userdata.

Removing the mod mid-save must be safe: legends just remain normal mutants.

## 5. Proven patterns already in this repo (read them, copy the approach)

- **Callback registration, save/load, MCM read**: `mods/Mixon Companion Training/gamedata/scripts/cup_core.script` (`on_game_start`, `save_state(m_data)`, `load_state(m_data)` around lines 790-830) and `cup_mcm.script`.
- **Spawning a squad on a level via alife, finding smarts, PDA result message**: `mods/Zombie Raid (Mixon)/gamedata/scripts/zzz_kreiser_zombie_horde.script` (`alife_create`, `SIMBOARD.smarts`, `SIMBOARD:setup_squad_and_group`, `news_manager.send_tip`, `save_state`/`load_state` with `m_data`). Note: that file contains Cyrillic in some strings — **do not copy that**; put text in xml.
- **NPC news with portrait**: `dynamic_news_helper.send_tip(text, header, nil, seconds, icon, "beep_1", "npc")` (used in `cup_core.script` ~line 282).
- **Hit modification before damage on mutants (proven)**: `mods/Mixon Companion Training/gamedata/scripts/a_cup_prehit.script`, function `install()`: it wraps the engine hook `_G.CBaseMonster__BeforeHitCallback(monster, shit, bone_id)` (and `_G.CAI_Stalker__BeforeHitCallback` for humans), changes `shit.power` inside `pcall`, then calls the original. Use the same chaining approach for Armoured / Front-proof / flee thresholds — chain, never replace, so other mods keep working. The script name starts with `a_` so it loads early; name yours `a_lgm_prehit.script` if you need the same. For hits **on the actor** (Berserk) use the `actor_on_before_hit` callback.
- **Death counting**: `monster_on_death_callback`, `npc_on_death_callback` (zombie raid script).
- Callbacks available on these exes and already used by us: `actor_on_update`, `actor_on_first_update`, `save_state`, `load_state`, `on_option_change`, `monster_on_death_callback`, `monster_on_net_destroy`, `npc_on_death_callback`, `npc_on_before_hit`, `actor_on_before_hit`, `on_key_press`, `actor_on_sleep`. To re-apply health/particles when a legend comes online, check each legend id in the 1 s update (`level.object_by_id(id)` becomes non-nil when online) instead of relying on a spawn callback whose name is not confirmed. If any callback name you want is not in the list above, assume it may not exist: register it inside `pcall`, log once and degrade gracefully.

## 6. Implementation order (do all four; each phase must leave a playable build)

1. **Core**: generation (species, rank, name), spawn, save/load, health by rank (re-applied when the mutant comes online), anomaly/emission immunity, PDA spawn message, money on kill, MCM, debug spawn key.
2. **Affixes**: first the 6 callback-only ones (Armoured, Front-proof, Regeneration, Berserk, Radioactive, Anomalous), then the 6 behavioural ones (Pack leader, Psi aura, Shadow, Swift, Cunning, Man-eater). Visual markers.
3. **Hunt**: rumour templates, contract dialog (traders, scientists, Duty, Freedom, Mercenaries), tracks, map markers, flee to lair + healing, all outcomes, lifetime.
4. **Rewards & links**: named parts (new item sections based on existing part sections), special hide, bestiary + title + discount, Companion Training XP, Experience Framework XP.

If an engine capability you need does not exist (e.g. speed multiplier for Swift, attaching particles to a bone), implement the closest safe fallback, mark it with `-- TODO(verify-ingame):` and list it in your report. Never fake a working feature.

## 7. Self-checks before you finish

- Every `.script` compiles: run `luac -p` (or `luajit -bl`, or any Lua 5.1 parser available) on each file; if no Lua is installed, write a small Python check with `luaparser` or similar, and say which you used.
- Grep: no non-ASCII bytes in `.script` files; every string id used in scripts exists in both `eng/lgm.xml` and `rus/lgm.xml`; xml files are valid windows-1251.
- Grep: every `alife_object(`, `level.object_by_id(` result is nil-checked before use.
- Every registered callback body is wrapped in `pcall`.

## 8. What to hand back

1. The mod folder `mods/Legendary Mutants (Mixon)/` complete for phases 1–4.
2. A short report:
   - files created and what each does;
   - which engine APIs you relied on that you could not verify (to be checked in-game);
   - `TODO(verify-ingame)` list;
   - **in-game test checklist** for the author: how to enable debug, the debug key, what to look for per phase (spawn message, health, each affix, rumours, contract, tracks, flee, rewards, save/load round-trip).
3. Nothing committed. No changes outside the mod folder.
