# Zone Operations (Mixon) — общие инструкции для агентов

Этот файл читают **оба агента**: Codex (`AGENTS.md`) и Claude Code (`CLAUDE.md` ссылается сюда).
Правила проекта меняются только здесь. Текущая работа описана в `HANDOFF.md`, его читать сразу после этого файла.

С пользователем говорить по-русски. Пользователь — автор мода, в игре проверяет сам.

## 1. Что это

Аддон для S.T.A.L.K.E.R. Anomaly 1.5.3 в сборке G.A.M.M.A. под MO2 (движок xray-monolith, LuaJIT = Lua 5.1).
Игрок ведёт отряды своей группировки в операции. Захваченные точки остаются за группировкой: туда приходят гарнизон и сервисные NPC.
Кроме операций в моде есть рейды, курьеры, вылазки и ветка наёмников в Мёртвом городе.
Версия — в `meta.ini`, сейчас 1.3.0.

## 2. Пути

| Что | Где |
|---|---|
| Рабочая папка (правки здесь, игра читает отсюда через MO2) | `E:\GAMMA\GAMMA RC3\mods\Zone Operations (Mixon)\` |
| Git-репозиторий (GitHub `MixonUP/mixon-gamma-mods`, ветка `main`) | `E:\GAMMA\mixon-gamma-mods\` → `mods\Zone Operations (Mixon)\` |
| Документация мода | в репо: `README.md`, `README.en.md`, `docs\zop_quests_ru.md`, `docs\zop_api.md`, `docs\zop_mercs*.md`, `docs\design\` |
| Карточка проекта в Obsidian | `E:\Krea_tren_AI\Knowledge\01_Project\Mixon_Zone_Operations.md` |
| MCP к игре (`stalker`) | `E:\GAMMA\stalker-mcp\` (подключён и в Claude, и в Codex) |
| Лог движка | `E:\Anomaly\appdata\logs\xray_ohrem_6c67u02.log` |

Синхронизация в репо (из рабочей папки, зеркалом):

```powershell
robocopy "E:\GAMMA\GAMMA RC3\mods\Zone Operations (Mixon)" "E:\GAMMA\mixon-gamma-mods\mods\Zone Operations (Mixon)" /MIR /NJH /NJS /NP
```

В архив релиза идут только `gamedata\` и `meta.ini`. Файлы `AGENTS.md`, `CLAUDE.md`, `HANDOFF.md` и папка `agent-tools\` в архив **не попадают**.

## 3. Архитектура (`gamedata\scripts\`)

| Файл | Роль |
|---|---|
| `zop_registry` | читает и проверяет `configs\misc\zone_ops\zop_operations.ltx`; сломанная операция отключается с записью в лог |
| `zop_core` | машина состояний операции (одна активная): assault `muster → assault → [counter] → success/fail`, defense `wait → defend(волны) → success/fail`; передача баз, кулдауны, `migrate()` старых сейвов; состояние в `m_data.zop` |
| `zop_world` | владельцы захваченных смартов, гарнизоны, пополнение, сервисные NPC (торговец, механик и т. д.) |
| `zop_spawn` | спавн отрядов и управление ими через `scripted_target` |
| `zop_census` | подсчёт живых бойцов у смарта; **общие игровые часы мода** `now()` / `fix_time` |
| `zop_battle` | делает бой у базы настоящим: снимает combat_ignore и неуязвимость, защищает своих сюжетных NPC |
| `zop_raid` | рейды для заданий: конвой, засада, лагерь, снабжение |
| `zop_courier` | курьерские задания между базами, сроки заданий |
| `zop_sortie` | вылазки со сканером в аномальное поле |
| `zop_task_dialog` | больше 10 шагов «есть ещё работа?» в диалоге заданий |
| `zop_merc`, `zop_merc_heli`, `zop_roof_fire`, `zop_merc_story` | ветка наёмников: оборона штаба, вертолёт «Сокол-1», огонь с крыши, история «Особый человек» |
| `zop_radio` | очередь озвученных реплик по рации (`sounds\zop\radio\<id>_<lang>.ogg`) |
| `zop_visuals` | новый облик сервисных NPC, которые уже есть в сохранении |
| `zop_api` | публичное API для других модов (VERSION = 1, имена не меняются, только добавляются) |
| `modxml_zop` | DXML: диалог предложения операции, профили NPC |
| `zop_mcm` | настройки MCM |

Конфиги:
- `configs\misc\zone_ops\zop_operations.ltx` — все операции, концы строк **LF**;
- `configs\misc\task\mod_task_manager_zop.ltx` — задания;
- `configs\text\{rus,eng}\ui_st_zop.xml` — тексты в **windows-1251**, одинаковые id в обоих языках;
- `configs\mod_system_zop.ltx` — предметы и NPC.

Подробности по каждому модулю есть в шапке `--[[ ... ]]` его файла. Прочитай шапку, прежде чем править модуль.

## 4. Жёсткие правила (каждое уже роняло игру)

1. Файлы `.script` — **только ASCII**. Текст для игрока пишется в xml-таблицы строк (RU и EN, одинаковые id).
2. **Никогда** не вызывать `file_list_open_ex` на `$game_meshes$`: это нативный вылет. Перед `set_visual_name` проверять, что файл модели существует.
3. `load_state` только копирует данные. С объектами и отрядами работать с первого `actor_on_update`.
4. Любой вызов движка для объекта, который мог исчезнуть (`alife():object(id)`, `level.object_by_id`, методы отряда), проверяет `nil`. Где вызов может бросить ошибку, он обёрнут в `pcall`.
5. Колбэки не бросают ошибок: тело в `pcall`, ошибка в лог через `printf("![ZOP] ...")`.
6. `AddScriptCallback` вызывается один раз на уровне файла, как в `zop_api`. Повторный вызов даёт ошибку «callback already exists».
7. Награда за задание — `reward_item`, не `give_item`. Иконки заданий — только существующие.
8. Задания NPC ищутся по префиксу id, равному id его профиля (`zop_csky_racuro_medic_task_N`).
9. Старые сохранения должны работать. Новое состояние ставится за значениями по умолчанию, разовые исправления — в `zop_core.migrate()` с флагом в `st.fixed`.
10. Работа в каждом кадре минимальная, тяжёлая логика — по таймеру.
11. Время берётся только из `zop_census.now()`, своих расчётов календаря не делать.
12. `npc:command()` в этой сборке движка подвешивает игру, не использовать.

## 5. Решения автора (не менять)

- Операции Чистого Неба выдаёт **Холод**, не Лебедев.
- Холодный: экзоскелет, берет, имплант на челюсти, чёрная повязка на глазу. Ракуро — медик, Фин — повар.
- В постах и описаниях никогда не упоминать Telegram.
- Коммит — только как часть передачи (раздел 7) или по просьбе пользователя. **Push, публикация на ModDB и GitHub-релизы — только по явной просьбе.**
- Сохранения пользователя не перезаписывать.

## 6. Проверка

1. **Статика, игра не нужна** — обязательна после любой правки:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "E:\GAMMA\GAMMA RC3\mods\Zone Operations (Mixon)\agent-tools\check_zop.ps1"
   ```
   Скрипт проверяет:
   - ASCII в скриптах;
   - нет `file_list_open_ex` на `$game_meshes$`;
   - LF в `zop_operations.ltx`;
   - xml читаются в cp1251, id в RU и EN совпадают;
   - каждый буквальный `st_zop_...` из `.script` и `.ltx` есть в таблице строк.

   Папка называется `agent-tools`, а не `.agents`: `.agents` у Codex служебная и закрыта для записи.
2. **Синтаксис Lua** — в запущенной игре через MCP `stalker`, инструмент `game_lua`:
   ```lua
   local p = getFS():update_path("$game_scripts$", "zop_core.script")
   local f, err = loadfile(p); return err or "ok"
   ```
   Офлайн-интерпретатора Lua на машине нет. Если игра не запущена, напиши в HANDOFF.md, что синтаксис в игре не проверен.
3. **Поведение** — `game_lua`, например `zop_core.debug_state()`, плюс `game_log` с фильтром `ZOP`. После вылета — `game_crash`.
   Автор проверяет сам: для каждой правки кода напиши точные шаги проверки в игре (какой сейв, какой NPC, что должно произойти, какая строка в логе).

## 7. Передача между агентами (Codex ⇄ Claude)

Контекст между агентами переносят файлы, а не память чата.

**Принять работу:**
1. Прочитать `AGENTS.md`, затем `HANDOFF.md`.
2. Посмотреть последние коммиты: `git -C E:\GAMMA\mixon-gamma-mods log --oneline -5`.
3. Сравнить рабочую папку с репо: `robocopy <рабочая> <репо> /MIR /L /NJH /NJS /NP /NDL`. Так видно, что изменено после последней передачи.
4. Работать только в своей задаче. Чужие файлы из раздела «Не трогать» в HANDOFF.md не править.

**Отдать работу:**
1. Запустить `check_zop.ps1`.
2. Обновить `HANDOFF.md`: кто передаёт и когда, задача, что сделано (файлы), чем проверено, что осталось, открытые вопросы, что не трогать.
3. Зафиксировать передачу: robocopy в репо, затем коммит **только своих файлов**. Чужие незакоммиченные правки, в том числе правки параллельных сессий, в коммит не добавлять.
   ```powershell
   git -C E:\GAMMA\mixon-gamma-mods add -- "mods/Zone Operations (Mixon)/HANDOFF.md" <свои файлы>
   git -C E:\GAMMA\mixon-gamma-mods commit -m "handoff(<from>-><to>): <кратко>"
   ```
   Без push.
4. По возможности записать итог в журнал Obsidian (карточка проекта, раздел 2).

**Вызвать другого агента напрямую** (cwd — рабочая папка мода; задание пишется в HANDOFF.md, в промпте ссылка на него):

- Claude → Codex. `codex` не в PATH, путь меняется с обновлениями:
  ```powershell
  [Console]::OutputEncoding = [Text.Encoding]::UTF8   # иначе кириллица из Codex приходит кракозябрами
  $codex = (Get-ChildItem "$env:LOCALAPPDATA\OpenAI\Codex\bin\*\codex.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
  & $codex exec -C "E:\GAMMA\GAMMA RC3\mods\Zone Operations (Mixon)" -s workspace-write --skip-git-repo-check -c model_reasoning_effort='"medium"' -o "$env:TEMP\codex_last.txt" "Прочитай AGENTS.md и HANDOFF.md, выполни задачу из HANDOFF.md, обнови HANDOFF.md по разделу 7 AGENTS.md. Без коммита."
  ```
  Итог читать из файла: `Get-Content "$env:TEMP\codex_last.txt" -Encoding UTF8`. Для ревью без правок: `-s read-only`. Ошибки MCP-серверов miro/houdini в выводе — шум, их можно не читать.
- Codex → Claude (`claude` есть в PATH):
  ```powershell
  claude -p "Прочитай AGENTS.md и HANDOFF.md, выполни задачу из HANDOFF.md, обнови HANDOFF.md по разделу 7 AGENTS.md. Без коммита." --permission-mode acceptEdits
  ```
  Запускать из рабочей папки мода. CLI `claude` авторизуется отдельно от приложения Claude Desktop. Если в ответ пришло «OAuth session expired», пользователь один раз запускает `claude` в терминале и выполняет `/login`. Claude нужен интернет: если песочница Codex его режет, запроси разрешение на запуск вне песочницы.

Коммит передачи делает тот, кто отдаёт работу пользователю. При прямом вызове это вызывающий агент: он проверяет результат.
