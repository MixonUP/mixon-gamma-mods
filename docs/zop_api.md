# Zone Operations: API for other mods

`zop_api.script` is how other mods talk to Zone Operations (Mixon). Its names stay the same between versions; new versions only add things. `zop_api.VERSION` is `1`.

## Check that Zone Operations is installed

```lua
if zop_api and zop_api.VERSION then
    -- Zone Operations is installed
end
```

When you touch the global `zop_api`, Anomaly loads the file, and the file declares the callbacks. After that, the stock `RegisterScriptCallback` and `UnregisterScriptCallback` also work with these names.

## Events

```lua
function on_game_start()
    if not (zop_api and zop_api.VERSION) then return end
    zop_api.on("zop_on_operation_end", function(op_id, success, info)
        if success and info.faction == "freedom" then
            -- your reward, news, quest stage...
        end
    end)
end
```

| Callback | Arguments | When |
|---|---|---|
| `zop_on_operation_start` | `op_id, info` | The player accepted an operation. |
| `zop_on_operation_end` | `op_id, success, info` | The operation was won (`true`) or lost (`false`). |
| `zop_on_target_taken` | `op_id, smart_name, index, info` | One assault target was cleared. `index` counts from 1. |
| `zop_on_wave` | `op_id, wave, info` | A defence wave set out (1, 2, ...). |
| `zop_on_base_captured` | `smart_name, faction, op_id` | A smart now belongs to a faction. |
| `zop_on_base_released` | `smart_name, faction, op_id` | A failed operation gave back a smart it had taken. |
| `zop_on_services_arrived` | `smart_name, faction, op_id` | The base's trader, mechanic and the rest walked in. |

- **`info` is a copy.** It is a copy of the operation's config plus `done` and `available`. Changing it has no effect on Zone Operations.
- **The operation's config fields** include `id`, `faction`, `enemy`, `kind` (`assault`/`defense`), `giver`, `targets`, `reward`, `goodwill`, `capture` and `services`.
- **Listener errors are contained.** If your listener throws an error, Zone Operations writes it to the log and the operation goes on.

## Queries

| Function | Returns |
|---|---|
| `zop_api.operations()` | The ids of all loaded operations, in config order. |
| `zop_api.operation(op_id)` | A copy of the operation's config plus `done` and `available`, or `nil`. |
| `zop_api.operations_of(story_id)` | The ids of the operations this commander offers. |
| `zop_api.is_done(op_id)` | Whether the operation was won. |
| `zop_api.is_available(op_id)` | Whether the commander would offer it now. |
| `zop_api.active()` | `{ op_id, stage, target, wave }` for the running operation, or `nil`. |
| `zop_api.owner(smart_name)` | The faction that holds a smart through Zone Operations, or `nil`. |
| `zop_api.bases()` | `{ [smart_name] = { faction, op } }` for every captured smart. |
| `zop_api.bases_of(faction)` | A sorted list of the smarts held by one faction. |

`stage` is one of the following:
- `muster`, `assault`, `counter_wait`, `counter` for assaults;
- `wait`, `defend` for defences.

## Control

```lua
-- start an operation as if its commander gave it; all of its conditions still apply
zop_api.start("freedom_garbage")      -- true / false

-- hold operations back: return false to block. The key is any unique string of yours.
zop_api.add_condition("my_mod", function(op_id, info)
    if op_id == "freedom_rostok" and not has_alife_info("my_mod_rostok_ready") then
        return false
    end
end)
zop_api.add_condition("my_mod", nil)  -- remove it
```

## Add your own operation (no script needed)

Add a DLTX file `gamedata\configs\misc\zone_ops\mod_zop_operations_<yourmod>.ltx`:

```ini
![zop_ops]
list_mymod = mymod_op_1

[mymod_op_1]
actor_faction  = freedom
giver          = mil_smart_terrain_7_7_freedom_leader_stalker
; ... the same keys as the operations in zop_operations.ltx
```

How it works:
- **Several mods don't clash.** Zone Operations reads every `[zop_ops]` key whose name starts with `list`, so mods that add operations never overwrite each other's lists. If an id is listed twice, only the first one is kept.
- **The commander gets the offer dialog automatically.** The `giver` is the commander's story id, which equals their character profile id.
- **Texts.** The operation's strings follow the same ids as the stock operations (`st_zop_<op_id>_...`); put them in your own `configs\text\eng|rus\` file.
- **Broken operations are skipped.** An operation with a wrong section, squad or smart is not loaded and gets a `![ZOP]` line in the log.
