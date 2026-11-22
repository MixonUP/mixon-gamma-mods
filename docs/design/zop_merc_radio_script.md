# Radio script: mercenary operation (Dead City)

Two voices:
- **Army (Granit and the other call signs):** RU "Alexey I" (gRp20jh5cr1dR3Lhhapi), EN "Andy - Rough, War Character" (kVBPcEMsUF1nsAO1oNWw).
- **Dushman:** "Alex" (c1DsJsmpE3jFybtMpqIm, Russian speaker) for both RU and EN.
- **Gyurza / Viper** (merc sniper on the HQ roof, Barrett M82): "Wladimir - Low-Pitched & Atmospheric" (Ep3Y4SsCIRz1gD3edazw), RU and EN.
- **Kuvalda / Sledge** (merc RPG gunner on the HQ roof): "Dzmitry - Expressive Russian Narrator" (BQ8zKfpkxw79bVmxuCXa), RU and EN.

Radio effect: Arma-style handheld (350–3200 Hz, mild tanh saturation), pink-noise static with slow swell and velvet crackle, PTT click in, noise burst out; 44.1 kHz mono Ogg Vorbis. Build script: scratchpad `radio_hard.ps1` (re-renders from `clean/`).

Files: `docs/media/zop/radio/<id>_<lang>.ogg` (radio-processed) and `_clean.mp3`. Sounds go to the mod as `sounds\zop\radio\<id>_<lang>.ogg`.

| id | who | event | RU | EN |
|---|---|---|---|---|
| a01 | army | operation start | Гранит — всем позывным. Начинаем операцию «Чистое поле». Наёмников в Мёртвом городе ликвидировать. Пленных не брать. Как поняли, приём! | Granite to all call signs. Operation Clean Field is a go. Mercenaries in the Dead City are to be eliminated. No prisoners. How copy, over! |
| a02 | army | countdown | Гранит — Кедру. Пять минут до выхода. Крыши держать, цели отмечать. | Granite to Cedar. Five minutes to step-off. Hold the roofs, mark your targets. |
| a03 | army | attack | Всем — вперёд! Штурм пошёл! Молот, работай по штабу! | All units, move! Assault is go! Hammer, hit their HQ! |
| a04 | army | mortar ranging | Молот, недолёт. Ближе полсотни. Огонь! | Hammer, short. Add fifty. Fire! |
| a05 | army | mortar on target | Молот, есть накрытие. Беглым — огонь! | Hammer, on target. Fire for effect! |
| a06 | army | heli arrives | Сокол-один, захожу с севера. Вижу цели, работаю. | Falcon One, coming in from the north. Targets in sight, engaging. |
| a07 | army | spotter killed | Кедр, ответь Граниту! Кедр!.. Кедр не отвечает. | Cedar, Granite, respond! Cedar!.. Cedar is down. |
| a08 | army | heli shot down | Сокол-один, меня подбили! Падаю, падаю! | Falcon One, I'm hit! Going down, going down! |
| a09 | army | next wave | Гранит — второй группе. Пошли, пошли! Давить их! | Granite to second group. Go, go! Crush them! |
| a10 | army | army retreats | Гранит — всем. Отходим к Администрации! Отход! | Granite to all. Fall back to the Administration! Fall back! |
| d01 | Dushman | operation start | Слышали эфир? Вояки решили нас зачистить. Пять минут. Кто не на позиции — тот труп. | You hear that? The army wants us gone. Five minutes. Anyone not in position is a dead man. |
| d02 | Dushman | gives the RPG | Держи тубус. Два выстрела. Вертушку увидишь — не жалей. | Take the tube. Two rockets. You see that chopper, don't hold back. |
| d03 | Dushman | reinforcements | Наши на подходе с востока. Держитесь, мужики! | Our boys are coming in from the east. Hold on! |
| d04 | Dushman | heli down | Вертушку сняли! Премию выпишу. | Chopper's down! That's a bonus for you. |
| d05 | Dushman | defense won | Отбились. Теперь наша очередь — берём Администрацию. | We held. Now it's our turn — we take the Administration. |
| d06 | Dushman | breach | Заряд на дверь. Три... два... один! | Charge on the door. Three... two... one! |
| d07 | Dushman | operation won | Контракт закрыт. Мёртвый город — наш. | Contract closed. The Dead City is ours. |
| m01 | Gyurza | roof team arrives | Гюрза — на крыше. Вертушку вижу. Работаю по кабине. | Viper on the roof. Eyes on the bird. Working the cockpit. |
| m02 | Kuvalda | roof team arrives | Кувалда на позиции! Тубус заряжен, жду, пока подставит брюхо. | Sledge in position! Tube's loaded, waiting for him to show his belly. |
| m03 | Gyurza | hits the heli | Есть попадание! Стекло в кабине — в крошку. Он дымит! | Hit! Cockpit glass is gone. He's smoking! |
| m04 | Kuvalda | fires RPG | Кувалда — выстрел! Ракета пошла! | Sledge, firing! Rocket away! |
| m05 | Kuvalda | RPG miss | Мимо, зараза! Перезаряжаюсь! | Missed, damn it! Reloading! |
| m06 | Kuvalda | heli down (before a08) | Есть! Птичка горит! Падает, падает! | Got him! Bird's burning! She's going down! |
| m07 | Gyurza | switches to infantry | Гюрза — перехожу на пехоту. Снимаю пулемётчиков. | Viper, switching to infantry. Taking out their gunners. |
| m08 | Kuvalda | switches to infantry | Кувалда — работаю по пехоте! Кучкуются у забора — сейчас разгоню! | Sledge, hitting the infantry! They're bunching up by the fence — breaking them up! |
| a11 | army | defense lost | Гранит — всем. Операция «Чистое поле» выполнена. База наёмников зачищена. Отбой. | Granite to all. Operation Clean Field complete. The mercenary base is cleared. Out. |
