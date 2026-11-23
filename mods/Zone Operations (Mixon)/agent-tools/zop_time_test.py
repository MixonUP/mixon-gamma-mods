r"""Offline LuaJIT checks for Zone Operations (no game needed).
1. every .script compiles under LuaJIT 2.1 (the engine's Lua);
2. zop_census.now() keeps real calendar time across month ends;
3. fix_time / load_state move stamps of the old 31-day-month clock to the new one.
Scripts run in a sandbox with X-Ray stubs (game, RegisterScriptCallback, save_var...).

Setup once:  python -m venv agent-tools\.venv ; agent-tools\.venv\Scripts\python -m pip install lupa
Run:         agent-tools\.venv\Scripts\python -I agent-tools\zop_time_test.py [scripts dir]
Exit code 0 = all passed.
"""
import sys, os, glob
import lupa.luajit21 as lj

SCRIPTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gamedata", "scripts")
lua = lj.LuaRuntime(unpack_returned_tuples=True)

def src(name):
    with open(os.path.join(SCRIPTS, name + ".script"), "rb") as f:
        return f.read().decode("cp1251")

fails = 0
def check(cond, msg):
    global fails
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails += 1

# ---------------------------------------------------------------- 1. syntax
print("1. LuaJIT syntax of every script")
compile_ = lua.eval("function(s, n) local f, e = loadstring(s, n); return e end")
for p in sorted(glob.glob(os.path.join(SCRIPTS, "*.script"))):
    n = os.path.basename(p)
    with open(p, "rb") as f:
        err = compile_(f.read().decode("cp1251"), n)
    check(err is None, n + ("" if err is None else ": " + err))

# ---------------------------------------------------------------- 2. sandbox
lua.execute(r"""
CLOCK = { 2012, 4, 30, 23, 59, 59 }
local function stub()
	local t = {}
	return setmetatable(t, { __index = function(_, k) return stub() end,
		__call = function() return nil end })
end
G = {}
G.game = { get_game_time = function()
	return { get = function() return unpack(CLOCK) end }
end, translate_string = function(s) return s end }
G.CALLBACKS = {}
G.RegisterScriptCallback = function(name, fn)
	G.CALLBACKS[name] = G.CALLBACKS[name] or {}
	table.insert(G.CALLBACKS[name], fn)
end
G.xr_effects, G.xr_conditions = {}, {}
G.task_functor, G.task_status_functor = {}, {}
PSTOR = {}
G.save_var = function(_, k, v) PSTOR[k] = v end
G.load_var = function(_, k, d) local v = PSTOR[k]; if v == nil then return d end; return v end
G.db = { actor = {}, storage = {} }
for _, k in ipairs({ "pairs", "ipairs", "type", "tostring", "tonumber", "math", "string",
	"table", "pcall", "next", "select", "unpack", "setmetatable", "getmetatable", "rawget",
	"rawset", "error", "assert", "print", "os", "bit", "loadstring" }) do
	G[k] = _G[k]
end
setmetatable(G, { __index = function(_, k) return stub() end })

-- load a script as an X-Ray module: its globals become fields of its own table
function load_module(name, source)
	local env = setmetatable({}, { __index = G })
	local f = assert(loadstring(source, name))
	setfenv(f, env)
	f()
	G[name] = env
	return env
end
function reset_callbacks() G.CALLBACKS = {} end
function fire(name, arg) for _, fn in ipairs(G.CALLBACKS[name] or {}) do fn(arg) end end
""")
G = lua.globals().G
load_module = lua.globals().load_module
census = load_module("zop_census", src("zop_census"))

def set_clock(*t):
    lua.execute("CLOCK = {%s}" % ",".join(str(x) for x in t))

def old(y, m, d, h, mi, s):
    return ((((d + m * 31 + y * 372) * 24 + h) * 60 + mi) * 60 + s)

# ---------------------------------------------------------------- 3. clock
print("2. zop_census.now() under LuaJIT")
for a, b, label in [((2012, 4, 30, 23, 59, 59), (2012, 5, 1, 0, 0, 0), "30 Apr -> 1 May"),
                    ((2013, 2, 28, 23, 59, 59), (2013, 3, 1, 0, 0, 0), "28 Feb -> 1 Mar 2013"),
                    ((2012, 2, 28, 23, 59, 59), (2012, 2, 29, 0, 0, 0), "28 Feb -> 29 Feb 2012"),
                    ((2012, 12, 31, 23, 59, 59), (2013, 1, 1, 0, 0, 0), "31 Dec -> 1 Jan")]:
    set_clock(*a); t1 = census.now()
    set_clock(*b); t2 = census.now()
    check(t2 - t1 == 1, "%s: %d s" % (label, t2 - t1))
set_clock(2012, 5, 1, 0, 0, 0)
check(census.now() == 1335830400, "1 May 2012 00:00 = unix 1335830400 (%d)" % census.now())

print("3. fix_time")
set_clock(2012, 4, 30, 20, 0, 0)
due_old = old(2012, 4, 30, 18, 0, 0) + 8 * 3600       # 8 h deadline set two hours ago
fixed = census.fix_time(due_old)
check(fixed - census.now() == 6 * 3600, "8h deadline set 2h ago: %g h left" % ((fixed - census.now()) / 3600))
check(census.fix_time(fixed) == fixed, "second pass leaves a new stamp alone")
check(census.fix_time(0) == 0, "0 (services 'send now') untouched")
check(census.fix_time(None) is None, "nil untouched")
set_clock(2012, 5, 1, 1, 59, 59)
check(census.now() < fixed, "not expired at 1 May 01:59:59")
set_clock(2012, 5, 1, 2, 0, 1)
check(census.now() > fixed, "expired at 1 May 02:00:01")

# ---------------------------------------------------------------- 4. migrations
print("4. load_state migrations")
set_clock(2012, 6, 10, 12, 0, 0)
N, O = census.now(), old(2012, 6, 10, 12, 0, 0)
def is_new(v, expect_left):
    return v is not None and abs((v - N) - expect_left) < 1e-6

def module_load(name, data_lua):
    lua.globals().reset_callbacks()
    load_module(name, src(name))
    mod = G[name]
    mod.on_game_start()
    m = lua.eval(data_lua)
    lua.globals().fire("load_state", m)
    return m

m = module_load("zop_raid", "{ zop_raid = { t1 = { deadline = %d }, t2 = { deadline = %d } } }" % (O + 3600, N + 7200))
check(is_new(m.zop_raid.t1.deadline, 3600), "raid: old deadline -> +1h on new clock")
check(is_new(m.zop_raid.t2.deadline, 7200), "raid: new deadline untouched")

m = module_load("zop_merc_story", "{ zop_merc_story = { t = %d, t0 = %d, stage = 'go' } }" % (O - 600, O - 86400))
check(is_new(m.zop_merc_story.t, -600) and is_new(m.zop_merc_story.t0, -86400), "merc_story: t, t0")

try:
    m = module_load("zop_world", "{ zop_world = { owners = {} } }")
    # inject an owner with services after load to call the same code path again
    G.zop_registry.get = lua.eval("function() return nil end")
    m = lua.eval("{ zop_world = { owners = { s1 = { op = 'x', services = { due = %d, due_sec = { a = %d, b = %d }, squads = {} } } } } }"
                 % (O + 100, O + 200, N + 300))
    lua.globals().fire("load_state", m)
    sv = m.zop_world.owners.s1.services
    check(is_new(sv.due, 100) and is_new(sv.due_sec.a, 200) and is_new(sv.due_sec.b, 300), "world: services.due, due_sec")
except Exception as e:
    check(False, "world: %s" % e)

try:
    m = module_load("zop_core", "{ zop = { done = {}, cooldown = { a = %d }, done_at = { b = %d }, active = { t0 = %d, t1 = %d, attack_at = %d } } }"
                    % (O + 86400 * 3, O - 3600, O - 7200, O - 60, N + 50))
    z = m.zop
    check(is_new(z.cooldown.a, 86400 * 3) and is_new(z.done_at.b, -3600), "core: cooldown, done_at")
    check(is_new(z.active.t0, -7200) and is_new(z.active.t1, -60) and is_new(z.active.attack_at, 50), "core: active t0, t1, attack_at")
except Exception as e:
    check(False, "core: %s" % e)

try:
    lua.globals().reset_callbacks()
    cour = load_module("zop_courier", src("zop_courier"))
    cour.on_game_start()
    lua.execute("PSTOR = { task_due = %d }" % (O + 1800))
    overdue = G.xr_conditions.zop_task_overdue
    p = lua.eval("{ 'task' }")
    r = overdue(None, None, p)
    check(r is False and is_new(lua.globals().PSTOR.task_due, 1800), "courier: old _due moved to new clock, not overdue")
    set_clock(2012, 6, 10, 12, 30, 1)
    check(overdue(None, None, p) is True, "courier: overdue 30 min later")
except Exception as e:
    check(False, "courier: %s" % e)

# ---------------------------------------------------------------- 5. raid cleanup
print("5. zop_raid_cleanup (on_complete / on_fail / on_cancel)")
try:
    lua.execute(r"""
	SQUADS_ALIVE = {}   -- [id] = section
	STEERED = {}
	G.zop_spawn = {
		valid_squad = function(id, section)
			local sec = id and SQUADS_ALIVE[id]
			if not sec or (section and sec ~= section) then return nil end
			return { id = id }
		end,
		steer = function(se, target, rush) STEERED[#STEERED + 1] = se.id end,
	}
	G.zop_spawn.steer_by_id = function(id, t, r)
		local se = G.zop_spawn.valid_squad(id); if se then G.zop_spawn.steer(se, t, r) end
	end
	""")
    m = module_load("zop_raid", "{ zop_raid = { a = { squad = 10, section = 'raid_sq' }, "
                    "b = { squad = 20, section = 'raid_sq' }, c = { squad = 30 } } }")
    cleanup = G.xr_effects.zop_raid_cleanup
    lua.execute("SQUADS_ALIVE = { [10] = 'raid_sq', [20] = 'stranger_sq', [30] = 'old_sq' }")
    for t in ("a", "b", "c"):
        cleanup(None, None, lua.eval("{ '%s' }" % t))
    steered = sorted(lua.globals().STEERED.values())
    check(steered == [10, 30], "own squad released, stranger with reused id untouched, old save (no section) released: %s" % steered)
    check(m.zop_raid.a is None and m.zop_raid.b is None and m.zop_raid.c is None, "raid records removed")
    cleanup(None, None, lua.eval("{ 'a' }"))
    check(True, "second cleanup of the same task is harmless")
except Exception as e:
    check(False, "raid cleanup: %s" % e)

# ---------------------------------------------------------------- 6. raid routes
print("6. zop_raid routes: ready() and setup() agree, ambush stays on the actor's level")
try:
    lua.execute(r"""
	local V = {}
	V.__index = V
	function V:distance_to(o) local dx, dy, dz = self.x - o.x, self.y - o.y, self.z - o.z
		return math.sqrt(dx * dx + dy * dy + dz * dz) end
	function vec(x, z) return setmetatable({ x = x, y = 0, z = z or 0 }, V) end
	OBJ = {}
	-- game vertex id = level id in this sandbox
	G.game_graph = function() return { vertex = function(_, g) return { level_id = function() return g end } end } end
	G.alife = function() return {
		actor = function() return { m_game_vertex_id = 1 } end,
		object = function(_, id) return OBJ[id] end,
	} end
	G.db = { actor = { position = function() return vec(0, 0) end, id = function() return 0 end }, storage = {} }
	G.AC_ID = 0
	G.get_speaker = function() return nil end
	G.ini_sys = { section_exist = function() return true end }
	G.printf = function() end
	SPAWNED = 0
	G.zop_spawn = { squad_at_smart = function() SPAWNED = SPAWNED + 1; return { id = 900 + SPAWNED } end,
		valid_squad = function() return nil end, steer = function() end, steer_by_id = function() end }
	function smart(id, x, z, level, base)
		local s = { id = id, position = vec(x, z), m_game_vertex_id = level,
			props = { base = base and 1 or 0 }, name = function() return "smart_" .. id end }
		OBJ[id] = s
		return s
	end
	function board(list)
		G.SIMBOARD = { smarts = {} }
		for _, s in ipairs(list) do G.SIMBOARD.smarts[s.id] = { smrt = s } end
	end
	""")
    load_module("zop_raid", src("zop_raid"))
    lua.globals().reset_callbacks()
    G.zop_raid.on_game_start()
    ready, setup = G.xr_conditions.zop_raid_ready, G.xr_effects.zop_raid_setup
    L = lua.globals()

    # convoy: starts P (400 m) and Q (380 m); only P has a destination > 450 m away (R at -60)
    L.board(lua.eval("{ smart(1, 400, 0, 1), smart(2, 380, 0, 1), smart(3, -60, 0, 1) }"))
    lua.execute("math.randomseed(7)")
    bad = 0
    for i in range(200):
        if ready(None, None, lua.eval("{ 'convoy' }")):
            L.SPAWNED = 0
            setup(None, None, lua.eval("{ 'convoy_task', 'convoy', 'bandit' }"))
            if L.SPAWNED != 1:
                bad += 1
    check(bad == 0, "convoy: 200 x ready()+setup(), route lost after ready(): %d" % bad)

    # ambush: the giver's base is on level 2 at the same coordinates as level-1 smarts
    L.board(lua.eval("{ smart(1, 600, 0, 1), smart(2, 700, 0, 1), smart(10, 0, 0, 2, true) }"))
    lua.execute("OBJ[50] = { m_smart_terrain_id = 10 }")
    npc = lua.eval("{ id = function() return 50 end }")
    check(not ready(None, npc, lua.eval("{ 'ambush' }")), "ambush: base on another level -> no route")
    lua.execute("OBJ[10].m_game_vertex_id = 1")
    check(bool(ready(None, npc, lua.eval("{ 'ambush' }"))), "ambush: base on the actor's level -> route")

    # giver_of fallback (no speaker): nearest base within 200 m, only on the actor's level
    L.board(lua.eval("{ smart(20, 50, 0, 2, true), smart(21, 150, 0, 1, true) }"))
    g = G.zop_raid.giver_of(None)
    check(g is not None and g.m_smart_terrain_id == 21, "giver_of: base of another level skipped (got %s)" % (g and g.m_smart_terrain_id))
except Exception as e:
    check(False, "raid routes: %s" % e)

# ---------------------------------------------------------------- 7. recycled squad ids
print("7. squad sets keep sections: a squad that got a dead squad's id is not ours")
try:
    lua.execute(r"""
	G.clsid = { online_offline_group_s = 7 }
	STEER = {}
	function squad(id, section, count)
		OBJ[id] = { id = id, clsid = function() return 7 end,
			section_name = function() return section end,
			npc_count = function() return count or 4 end,
			squad_members = function() return function() return nil end end }
		return OBJ[id]
	end
	""")
    spawn = load_module("zop_spawn", src("zop_spawn"))
    real_steer = spawn.steer
    lua.execute("G.zop_spawn.steer = function(se, t, r) STEER[se.id] = t or 'sim' end")
    load_module("zop_census", src("zop_census"))
    vs = spawn.valid_squad
    L = lua.globals()
    lua.execute("OBJ = {}; squad(1, 'zop_wave_sq'); squad(2, 'stalker_sim_sq')")
    check(vs(1, "zop_wave_sq") is not None and vs(2, "zop_wave_sq") is None, "valid_squad: section string is checked")
    check(vs(2, True) is not None, "valid_squad: true (old save) = id check only")

    # a wave squad died; its id 2 now belongs to a simulation squad of 4 men
    alive = G.zop_census.alive_in_squads(lua.eval("{ [1] = 'zop_wave_sq', [2] = 'zop_wave_sq' }"))
    check(alive == 4, "alive_in_squads counts only the real wave squad: %d (old code: 8)" % alive)

    # upgrade of an old save: true -> section, dead ids dropped
    st_ = lua.eval("{ [1] = true, [2] = 'zop_wave_sq', [3] = true }")
    spawn.upgrade_set(st_)
    check(st_[1] == "zop_wave_sq" and st_[2] == "zop_wave_sq" and st_[3] is None, "upgrade_set: true -> section, dead id dropped, strings kept")

    # world: adopt keeps sections, release lets go only of its own squads
    load_module("zop_world", src("zop_world"))
    lua.execute("G.zop_registry = { get = function() return nil end }; G.zop_api = { emit = function() end }")
    W = G.zop_world
    W.all()["base"] = lua.eval("{ faction = 'csky', op = 'op1', garrison = {} }")
    W.adopt("base", lua.eval("{ [1] = 'zop_wave_sq', [2] = 'zop_garrison_sq' }"))
    g = W.all()["base"].garrison
    check(g[1] == "zop_wave_sq" and g[2] is None, "adopt: own squad kept with section, recycled id skipped")
    lua.execute("STEER = {}")
    W.release("base", "op1")
    st2 = dict(L.STEER.items())
    check(st2 == {1: "sim"}, "release: only the real garrison squad goes back to the simulation: %s" % st2)
except Exception as e:
    check(False, "squad sets: %s" % e)

# ---------------------------------------------------------------- 8. spawn failures
print("8. spawn failures: empty squads removed, waves retried then skipped (no instant win)")
try:
    # 8a. squad_at_smart: create_npc gave no members -> removed, nil
    lua.execute(r"""
	REMOVED = 0
	G.vector = function() return { set = function(self) return self end } end
	G.alife_create = function(section)
		return { id = 77, npc_count = function() return 0 end,
			create_npc = function() error("no npc") end,
			remove_squad = function() REMOVED = REMOVED + 1 end,
			squad_members = function() return function() return nil end end }
	end
	G.SIMBOARD = { assign_squad_to_smart = function() end }
	""")
    spawn = load_module("zop_spawn", src("zop_spawn"))
    r = spawn.squad_at_smart("zop_wave_sq", lua.eval("{ position = {}, m_level_vertex_id = 1, m_game_vertex_id = 1 }"), "t")
    check(r is None and lua.globals().REMOVED == 1, "squad_at_smart: squad without members removed, returns nil")

    # 8b. a defense: wave 1 beaten, wave 2 cannot be spawned for 30 s, then it can
    lua.execute(r"""
	T = 0
	G.time_global = function() return T end
	G.SIMBOARD = {}            -- no smarts_by_names: migrate() waits
	SPAWN_OK_AT = 1e9
	G.zop_spawn = setmetatable({
		squad_at_smart = function() if T >= SPAWN_OK_AT then return { id = 500 + T } end return nil end,
		section_of = function() return "zop_wave_sq" end,
		valid_squad = function() return nil end,
	}, { __index = function() return function() end end })
	G.zop_census = setmetatable({
		alive_in_squads = function(set) local n = 0; for _ in pairs(set or {}) do n = n + 4 end; return n end,
		now = function() return 1e9 end, fix_time = function(t) return t end,
		fix_map = function() end, fix_fields = function() end,
		smart_by_name = function() return { id = 1, position = {}, name = function() return "t" end } end,
		actor_near = function() return false end, count = function() return 0 end,
		members = function() return {}, nil end,
	}, { __index = function() return function() end end })
	OP = { id = "op1", kind = "defense", targets = { "t" }, faction = "csky", enemy = "bandit",
		waves = { { section = "w1", count = 1 }, { section = "w2", count = 1 } },
		evacuate = {}, peace_on_success = {}, services = {}, reward = 0, reward_max = 0,
		goodwill = 0, cooldown = 1, radius = 50 }
	G.zop_registry = { get = function(id) if id == "op1" then return OP end end }
	G.zop_world = setmetatable({ all = function() return {} end }, { __index = function() return function() end end })
	G.zop_api = setmetatable({ operation = function() return {} end }, { __index = function() return function() end end })
	G.zop_battle = setmetatable({}, { __index = function() return function() end end })
	G.task_manager = { get_task_manager = function() return setmetatable({}, { __index = function() return function() end end }) end }
	""")
    lua.globals().reset_callbacks()
    core = load_module("zop_core", src("zop_core"))
    core.on_game_start()
    def load_core(active):
        lua.globals().fire("load_state", lua.eval("{ zop = { done = {}, cooldown = {}, done_at = {}, active = %s } }" % active))
    def tick(n=1):
        for _ in range(n):
            lua.execute("T = T + 1000")
            lua.globals().fire("actor_on_update")
    ACTIVE = "{ op = 'op1', stage = 'defend', wave = 1, squads = {}, staging = 'stg', t1 = 1e9 }"

    lua.execute("T = 0; SPAWN_OK_AT = 1e9")
    load_core(ACTIVE)
    tick(30)
    s = core.debug_state().active
    check(s is not None and s.spawn_wave == 2, "wave 2 failing: no win after 30 s, retry pending (spawn_wave=%s)" % (s and s.spawn_wave))
    lua.execute("SPAWN_OK_AT = T + 1")
    tick(1)
    s = core.debug_state().active
    check(s is not None and s.wave == 2 and s.spawn_wave is None and next(iter(dict(s.squads.items())), None) is not None,
          "spawn works again: wave 2 comes, operation goes on")

    lua.execute("SPAWN_OK_AT = 1e9")   # T keeps running: zop_core remembers its next tick
    load_core(ACTIVE)
    tick(59)
    check(core.debug_state().active is not None, "wave 2 never spawns: still running after 59 s")
    tick(3)
    check(core.debug_state().active is None, "after 60 s wave 2 is skipped; no wave 3 -> the defense ends (author's call)")
except Exception as e:
    import traceback; traceback.print_exc()
    check(False, "spawn failures: %s" % e)

print("\nFAILS:", fails)
sys.exit(1 if fails else 0)
