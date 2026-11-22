# Zone Operations: mercenaries — "Defense of the Administration" (plan)

Status: plan for review, nothing implemented yet.

## What the author asked for

- The mercenary operations start with this one; it opens at **1000 reputation** (to confirm: community goodwill with `killer`, or the actor's reputation shown in the PDA).
- Place: Dead City, the Administration building where the player stands (smart `cit_killers_vs_bandits`, base smart).
- After the player takes the task, **5 real minutes** later elite army spetsnaz attack the merc base: **~40 soldiers**, several squads with **legends**; on the neighbouring high-rises **spetsnaz snipers** on the rooftops, and an **RPG gunner** on a roof.
- When the attack starts, an **army helicopter** flies in to support them.
- **3 minutes** after the attack starts, merc reinforcements arrive, then **one merc squad every 5 minutes**.
- **Mortar fire simulation** during the battle.

## Correction from the author (supersedes the target above)

- When the quest starts, **the Administration is already held by elite army spetsnaz** (the quest puts them there: `occupy`-style squads inside and on its roof).
- They **shout on the radio** (PDA news / radio chatter lines) that the operation to liquidate the mercenaries has begun.
- **5 minutes** after the quest is taken they **attack the merc base** (`cit_killers`, Dushman's HQ 113 m north); the helicopter flies in to support them; rooftop spetsnaz snipers and the RPG gunner cover the attack.
- Merc reinforcements: first at +3 min after the attack starts, then one squad every 5 min.
- So the defense target is **`cit_killers`** (the merc HQ), and the Administration (`cit_killers_vs_bandits`) is the army's staging point. Likely finale (to confirm with the author): after the attack is beaten, the mercs storm the Administration and take it back (assault phase, capture = true).

## Data from the running game (player standing in the Administration)

- Player: `l09_deadcity`, pos (-48.3, 7.4, -68.3), level vertex 102623, game vertex 2400, community `actor_killer`. Goodwill with `killer` = 0, reputation = 40.
- Smarts by distance from the player:
  - `cit_killers_vs_bandits` 15 m (-62,2,-70) base=1 ← the Administration (defense target)
  - `zombie_smart_ds_mlr_1` 90 m (-131,1,-33)
  - `cit_bandits` 94 m (45,1,-74)
  - `cit_bandits_2` 99 m (-142,1,-100)
  - `cit_killers` 126 m (-44,1,57) base=1 ← merc HQ: Dushman (id 20744, story `cit_killers_merc_trader_stalker`), mechanic Hog, medic Surgeon (-28,12,29)
  - `cit_kanaliz1` 179 m (-198,5,-166), `cit_killers_2` 180 m (99,1,35), `zombie_smart_ds_mlr_2` 182 m, `cit_kanaliz2` 200 m (128,-7,-160)
- AI-mesh rooftops (level vertices with y > 9 within 260 m, best vertex per 15 m cell):
  - **Roof A** (sniper): vertex 75919 (-94, 15.8, -35), 57 m from the player, 96 vertices; also 73443 (-100,15.7,-28), 70960 (-106,15.6,-37)
  - **Roof B** (sniper / RPG): vertex 112270 (-34, 14.7, -326) and 115396 (-29,13.4,-326), ~258 m south
  - **Roof C**: vertex 117858 (-26, 11.3, 24), 96 m, next to the merc HQ (behind merc lines — probably not for the army)
  - Administration roof itself: vertices 105137 (-45,13.7,-65), 99169 (-53,13.7,-65), 112544 (-34,13.7,-77)
  - The y≈9-10 vertices at x≈-195..-237 are probably raised ground at the west edge, not roofs.

## Proposed implementation

### 1. Operation descriptor (reuse the defense engine)

New section `killer_deadcity` in `zop_operations.ltx`:

```
[killer_deadcity]
actor_faction  = killer
giver          = cit_killers_merc_trader_stalker   ; Dushman
type           = defense
targets        = cit_killers_vs_bandits
enemy          = army
waves          = zop_army_spetsnaz:3, zop_army_spetsnaz:3, zop_army_spetsnaz_legend:2   ; ~40 men total
wave_spawn     = <south approach, x,y,z@lv@gv>       ; to pick
delay_seconds  = 300                                  ; NEW: real seconds instead of delay_hours
radius         = 70
defender_squad = zop_killer_assault
defender_count = 2
reinforce_schedule = 180:2, 300:1                     ; NEW: first 2 squads at +3 min, then 1 every 5 min
roof_squads    = zop_army_sniper@75919, zop_army_sniper@112270, zop_army_rpg@115396   ; NEW
heli           = simulation_helicopter_strong@<spawn pos>   ; NEW
mortar         = <period_s>:<radius_m>:<count>          ; NEW
requires_goodwill = killer:1000                         ; NEW (or requires_reputation)
reward_money   = 80000
goodwill       = 300
```

New squads in `squad_descr_zop.ltx`: `zop_army_spetsnaz` (sim_default_military_4/5), `zop_army_spetsnaz_legend` (one new legend profile `zop_army_legend` + 4/5), `zop_army_sniper` (one man with a sniper rifle), `zop_army_rpg` (one man with an RPG-7), `zop_killer_assault` (killer_3/4).

### 2. New engine features (zop_core / new zop_fx.script)

1. **`delay_seconds`**: real-time countdown before the first wave (the current `delay_hours` is game time). Saved in the op state; the countdown keeps running across saves.
2. **`reinforce_schedule`**: timed merc reinforcements from the moment the first wave is spawned: `t:count` pairs, the last pair repeats until the defense ends. Spawned at a merc smart (`cit_killers`) and steered to the target, like `defender_squad`.
3. **`roof_squads`** (`squad@level_vertex`): one-man squads spawned at the rooftop vertex. Problem to solve: keep them on the roof. Options:
   a. spawn at the vertex and re-steer each tick with `npc:set_dest_level_vertex_id(vertex)` when out of combat or > 5 m away (combat scheme may override);
   b. a scripted `[logic]` with `camper@...` or `walker@...` and a one-point patrol path — needs a way/patrol on that roof (no `.way` files in the mod yet; can patrols be created at runtime?);
   c. give the NPC `xr_logic` custom data with `sniper` style camper and `no_retreat`.
   Wish: they never come down, fire from the roof, despawn/stay dead after the battle.
4. **`heli`**: spawn `simulation_helicopter_strong` (stock) like New Tasks does (`nta_utils.spawn_helicopter`: `alife_create`, `utils_stpk.get_heli_data/set_heli_data` with `veh_mi2_01`, `helicopter\aaa.anm`). Needs: fly to the Administration, circle, shoot at mercs (not only the actor), leave or be shot down; release on operation end. Open question: how to make the stock heli fight NPCs (heli combat scheme mainly targets the actor) — `heli:SetEnemy(obj)` per tick on the nearest merc?
5. **`mortar`**: every N seconds pick a point within R m of the target (avoid the player's exact spot, bias toward merc fighters), play an incoming whistle sound 1.5-2 s before, then an explosion: either spawn and explode a grenade/explosive object (`alife_create("grenade_f1"...)` + `obj:explode(0)`) or particles + sound + `level.add_cam_effector` shake + area `hit` on NPCs/actor within ~6 m. Stops when the defense ends.
6. **Start condition** `requires_goodwill = killer:1000` checked in `zop_core.available()` (or via `zop_api.add_condition`).

### 3. Texts

`st_zop_killer_deadcity_name/_offer/_muster/_won/_failed/_attack/_wave2/_wave3`, news for the helicopter, the reinforcements (`st_zop_killer_reinforce`) and the mortar barrage, in RU and EN (cp1251).

## Questions for the reviewer

1. Is extending the existing defense engine right, or is this better as its own scripted event (one-off script) given the timers, heli and rooftops?
2. Best reliable way to keep rooftop NPCs on the roof in Anomaly 1.5.3 / GAMMA AI Rework, firing at mercs.
3. Helicopter: the most reliable way to have the stock heli attack NPC enemies around a point and leave/die cleanly; save/load safety of a scripted heli.
4. Mortar: safest explosion method (crash-free, works with the player's actor damage balancer mods), sound choice from stock files.
5. 40 online soldiers + mercs + heli in Dead City: performance and the GAMMA online-squad limits; should waves be staggered?
6. Anything in the plan that conflicts with save/load (all timers in real seconds) or with the Dead City story (Dushman's own quests, the bandits/mercs war of `cit_killers_vs_bandits`).

## Fable review (2026-11-22), key decisions

- Hybrid: keep `type = defense` in zop_core; core gets `delay_seconds` (saved as seconds left, like `counter_left`), `reinforce_schedule` + `reinforce_from` (cap ~12 live defenders, old count-based reinforce off), `requires_goodwill` (community_goodwill(op.faction) in `available()`, bypass in debug_start), and a separate `s.roof` set. Heli, mortar and RPG go to a new `zop_fx.script` driven by `zop_on_wave` / `zop_on_operation_end`, state in `st.active.fx`, plus a saved `st.cleanup = {[id]=section}` processed before the `if not s` early return.
- Roof shooters: one-man squads created with `se:create_npc(nil, pos, lvid, gvid)` (passing a smart ignores the position), no smart assignment, never a number in `scripted_target` (sim_squad_scripted:139 crash); hold each tick with `assigned_target_id = current_target_id = sq.id`, `current_action = 1`, `idle_time` huge; NPC section `zop_army_roof_sniper : sim_default_military_3_sniper` with `custom_data = scripts\zop\zop_roof.ltx` (`remark` + `combat_type = camper`, as in Contract on Your Head). Roof B (258 m) is beyond eye_range 220: use roof A and the Administration roof, or a point < 150 m.
- RPG: simulated (shoot sound from the roof + the mortar explosion) while the gunner lives.
- Heli: own section `zop_army_heli : simulation_helicopter_strong`, spawn data `custom_data = "[logic]\nzop = true"` so bind_heli skips heli_alife and stock combat; manual control: `GoPatrolByRoundPath(center, 60-70)`, `LookAtPoint`, every 5-8 s `SetEnemy(nearest visible merc, rarely the actor)`, mgun only; leaves after 4-5 min or at the end, released when far; only the id is saved, re-validated each use.
- Mortar: real S_EXPLO object `zop_mortar_shell : explosive_grenade` (blast 2.5, radius 7, no frags), whistle `weapons\rocket_fly`, `alife_create` then `explode(0)` on the first online tick; points on the AI mesh, not within 12 m of the player, not within 40 m of the HQ / story NPCs, open sky (ray_pick).
- Load: waves already go one at a time (13-15 attackers at once); keep <= 15 attackers and 12-15 defenders.
- Risks: dead Dushman/Hog/Surgeon from mortar or heli; instant loss before the first reinforcement (count the live player in radius as a holder); stale ids after load.
- Found bug: `zop_spawn.script:24` passes the smart, so `wave_spawn` waves appear at the smart, not at the given point (affects csky_rostok).
- Build order: goodwill + delay + section/squads -> reinforce schedule -> one roof sniper -> one mortar shell -> heli (spawn/circle, fire, leave, shot down, save/load, night) -> RPG + texts, full run with FPS.

## Fable addendum for the corrected scenario

- Two linked operations, not one: `killer_deadcity` (defense of `cit_killers`) and `killer_admin` (assault on `cit_killers_vs_bandits`, `requires = killer_deadcity`, `capture = true`, `garrison_squad`, `muster = cit_killers`). New field `on_success_start = killer_admin`: `finish(true)` sets a saved `st.pending_start = {op, left = 8}` and the tick starts it 8 s later. One quest for the player, two states in the engine.
- First op: `staging = cit_killers_vs_bandits` (bases are never picked as staging), `staging_squad / staging_count` for the spetsnaz holding the Administration from the start (kept in `s.occupiers`, not the first wave); waves spawn in the Administration at attack time and run to the HQ; on success the occupiers and roof shooters are carried over (`st.carry`) to the assault instead of released. Radio via `start_news`. Reinforcements from `cit_killers_2` (east of the HQ), `defender_count` 0-1 (HQ already full).
- Risk changes: no instant loss (story NPCs always hold the HQ), but then the defense can only fail by DEFENSE_HOURS unless a real loss rule is added. Mortar on the HQ is the main danger for Dushman/Hog/Surgeon: open sky only, >= 15-20 m from story NPCs, and force invulnerability for own story NPCs in `zop_battle.need_inv_wrapper` during the op. 12 merc veterans at `cit_bandits` (94 m) may start the fight early: keep only roof shooters and 1-2 squads in the Administration before the attack. If the player is within 40 m of the staging point, spawn waves at a fallback smart.
- Roofs: A ~105 m to the HQ and the Administration roof ~122 m are fine; B ~380 m useless; C is behind merc lines. In the assault the roof shooters count as enemies near the target: mark them or skip them.
- Open decisions: a real loss condition for the HQ defense; heli and mortar stop at the end of the defense (Fable's suggestion).

## Author's marked spot (2026-11-22)

- The author stood on the Administration roof and said "the military are here": pos (-38.06, 13.70, -62.91), level vertex 110144, game vertex 2397, 28 m from the smart `cit_killers_vs_bandits`, 121 m from the merc HQ. Use it as the army roof post on the Administration (sniper / RPG) and a staging reference.

## Fable: what to add (ranked by impact vs cost)

1. Radio drama on a timeline (small): call signs Granit (commander in the Administration), Kedr (roofs), Molot (mortar), Sokol-1 (heli); Dushman answers. Event -> text id table, sent like `dynamic_news_helper.send_tip` (tasks_skyfall.script:61); said-flags in `s.said`.
2. Spotter on the Administration roof (vertex 110144) (small): while he lives the mortar is frequent and accurate; killed -> "Kedr is silent", fire rare and inaccurate.
3. Ranging and creeping barrage (small): first shells fall short, each next one closer, with Molot on the radio (`fx.mortar_n`).
4. RPG from Dushman + heli as a bonus target (small-medium): "one tube, two rockets"; `heli_on_hit_callback` (bind_heli:262) with SetfHealth so two player hits bring it down; bonus pay.
5. Heli fly-over above the HQ before circling (small): one waypoint at speed 40, height >= y 55.
6. Breach charge before the Administration assault (small): Dushman counts down, explosion at the entrance on muster -> assault.
7. Commander Granit in the finale (medium): named NPC with a mark; his PDA with the liquidation order as a trophy Dushman buys.
8. Merc-style pay and aftermath: 80 000 + bonus per confirmed kill + heli; the Administration becomes a merc forward post; heli wreck as a prop.
9. Film mode (small): debug commands per episode (heli, mortar, wave, breach) and an MCM option to hide red marks.
- Not now: weather change, surrender animations, real NPC RPG.
- Trailer shots: Granit intercept with spetsnaz on the roof; 0:10 timer and closer ranging shells; heli fly-over; RPG and Sokol falling; scope on the spotter and the mortar going quiet; breach and the merc rush; Dushman with Granit's PDA, "contract closed".
- Order: 1, 2, 3, 9 with the base build; then 4-6; 7 and 8 with the assault operation.

## Agreed plan and build 1 (2026-11-23)

Agreed with the author:
- Dushman (`cit_killers_merc_trader_stalker`) gives `killer_deadcity` at merc goodwill >= 1000 (debug_start skips it).
- Start: radio a01, a02, d01; 6 spetsnaz squads (~20 men, `zop_army_spetsnaz_hold`) occupy the Administration and stay there; 5 real minutes countdown with reminders.
- Attack: wave 1 = 6 squads (30) from the front of the Administration + 2 squads (10) from the west flank; heli Sokol-1 (medium armour) comes in from the north; radio a03, a06.
- +3 min: merc roof team on the HQ — sniper Gyurza (Barrett M82) and RPG gunner Kuvalda; they work the heli (scripted hits, radio m01–m06), then the infantry (m07, m08). Same time the first merc reinforcement from `cit_killers_2` (d03), then one every 5 minutes (cap 6 live squads).
- Wave 2 = 6 squads (30), radio a09. Heli down: a08, d04.
- Won: a10, d05; reward 60 000 / +300; `killer_admin` starts 90 s later: assault on the Administration, 5 mines before the entrance (anybody sets them off), d06 near the door, d07 on success; capture + merc garrison; reward 90 000 / +400.
- Loss: Dushman dead, the player > 300 m from the HQ for 2 real minutes, or 12 game hours. HQ story NPCs are invulnerable during the defense.
- Not in build 1: mortar (a04/a05), spotter Kedr (a07), Dushman's RPG gift (d02).

Code: `zop_merc.script` (operation logic), `zop_merc_heli.script` (heli + roof duel), `zop_radio.script` (voiced radio queue, RU/EN via MCM `voice_lang`), core fields `delay_seconds`, `requires_goodwill`, `on_success_start/_delay`, core helpers `active_state`, `add_squad`, `end_active`; `zop_spawn` wave_spawn fix.
