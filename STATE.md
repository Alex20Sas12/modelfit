# ModelFit — STATE.md (создан 19.09.2026)

## Что это
«Can I run this LLM?» — вердикты VRAM/RAM для свежих нейромоделий. Фишка: цифры —
НЕ формулы и НЕ пресеты, а РЕАЛЬНЫЕ размеры GGUF-файлов из HuggingFace API
(tree API, суммирует сплит-шарды) + KV-cache из config.json где доступен + overhead 15%.
Автообновление кроном = страница для новой модели появляется раньше, чем блогеры напишут гайд.

## Координаты
- Сайт: https://modelfit-eight.vercel.app (канон! modelfit.vercel.app занят чужим «Roperly»)
- Vercel-проект: modelfit (аккаунт keyt9750-7169), деплой из site/
- Штаб: fabrika/modelsite/ (fetch.py, build.py, test_build.py, refresh.py, models.json, urls.txt)
- Adsterra: сайт 6062424, категория «Файловые хостинги», блоки NativeBanner_1 (31310380)
  + SocialBar_1 (31310853), оба Активные; коды в adsterra_codes.json, вшиты в build.py
- GSC: ресурс https://modelfit-eight.vercel.app/ верифицирован АВТОМАТИЧЕСКИ
  аккаунт-токеном dHzB4J-n1_k8XEQgWt9VE2OCG2gO8yiE9adtZGUcN-s (мета-тег в build.py;
  тот же токен что feecalcs/moneycalcs — наследуется от Google alexford0289)
- Sitemap: /sitemap.xml отправлен в GSC 19.09
- IndexNow: 41 URL принят (202) 19.09, key ecc6d98e…txt лежит в корне сайта

## Кроны
- b0bc91a7d033 modelfit-daily-refresh 09:40 МСК (no_agent): refresh.py =
  fetch -> тесты -> build -> vercel deploy -> IndexNow. Молча при успехе, алерт при ошибке.
- f852cc3390ca modelfit-gsc-index 10:45 МСК (no_agent): батч 3 URL/день «Запросить
  индексирование» (окно 9232, gsc_inspect.py, прогресс gsc_progress.json).
  Квота GSC общая со всеми сайтами, сброс ~10:00 МСК.

## Конвейер (повтор = refresh.py, всё остальное вручную не нужно)
python fetch.py -> python test_build.py -> python build.py -> cd site && vercel deploy --prod --yes

## НЕ СДЕЛАНО (следующие шаги)
1. Pinterest-трафик: нужен НОВЫЙ аккаунт + новое окно (не переиспользовать существующие —
   приказ владельца). Образец: fabrika/feesite/pin_reg.py + pin_warmup.py + pin_daily.py,
   окно 9272. Пины = скриншоты вердиктов («Kimi K3: 466 GB minimum — honest answer inside»).
2. Reddit (u/kate_makes_sheets): r/LocalLLaMA — там живёт ЦА. Правила: 10:1, без прямых
   ссылок-спама; формат «посчитал требования Kimi K3 по реальным файлам, вот таблица» + ссылка.
3. Соцбар Adsterra проверять на показы через 2-3 дня (зона новая).
4. Первые центы: 2-4 недели (как MoneyCalcs). Не oversell.

## Грабли (записаны)
- modelfit.vercel.app ЗАНИМАЕТ чужой проект — Vercel дал суффикс -eight.
- Диалог Adsterra: опция «Другой»/форматы за краем вьюпорта — ОБЯЗАТЕЛЬНО
  scrollIntoView({block:'center'}) перед кликом.
- Вкладки 9222 убивает крон-чистильщик bffc58293608 (>30 мин) — Adsterra-скрипты
  должны сами открывать вкладку (_nav9222.py) и не зависеть от долгоживущих.
- tree API пагинирует подпапки: GGUF больших моделей лежат в Q*/IQ*-директориях — fetch.py
  ходит рекурсивно.
- HF API без ключа: rate-limit мягкий, 40 моделей за ~4 мин ок.
