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

print("\nFAILS:", fails)
sys.exit(1 if fails else 0)
