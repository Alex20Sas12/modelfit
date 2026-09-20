# ModelFit — STATE.md (создан 19.09.2026, SEO-push сессия 2)

## Что это
«Can I run this LLM?» — вердикты VRAM/RAM для свежих нейромоделий. Фишка: цифры —
НЕ формулы и НЕ пресеты, а РЕАЛЬНЫЕ размеры GGUF-файлов из HuggingFace API
(бесплатный, без ключа). Крон ежедневно тянет новые модели и пересобирает сайт.

## ЖИВОЙ URL
https://modelfit-eight.vercel.app (Vercel-проект `modelfit`; modelfit.vercel.app ЗАНЯТ чужим!)

## Масштаб (19.09, после SEO-push)
- 110 страниц моделей + 8 VRAM-tier + 14 GPU/Mac-страниц + picker = 134 URL
- tier-страницы «Best LLM for XGB VRAM» (8-96GB) — HOT-запросы (Google autocomplete 10/10)
- GPU-страницы «Best LLM for RTX 4090/3090/5090/3060, MacBook Pro M4...» — HOT (5-7 подсказок)
- Интерактивный picker /what-llm-can-i-run/ — «what llm can i run locally calculator» = HOT

## SEO (сессия 2, 19.09) — что внедрено
- JSON-LD: FAQPage+BreadcrumbList+Dataset (модели), ItemList+WebSite (главная), ItemList (tiers)
- Видимый FAQ-блок на страницах моделей (совпадает с JSON-LD)
- llms.txt + markdown-двойники каждой страницы (index.md) — AI-цитируемость (Perplexity/ChatGPT/Claude)
- robots.txt: все AI-боты Allow (GPTBot/PerplexityBot/ClaudeBot/Google-Extended/Applebot...)
- Внутренние ссылки: «More models» (8 родственных) + GPU/tier-сетка на каждой tier-странице
- canonical + og:url + twitter:card, sitemap lastmod=сегодня
- Вшиваются в ГЕНЕРАТОР (build.py/tiers.py) — крон-пересборка сохраняет всё

## Верификации
- GSC: modelfit-eight.vercel.app подтверждён АВТОМАТИЧЕСКИ (мета-тег google-site-verification
  dHzB4J-n1_k8XEQgWt9VE2OCG2gO8yiE9adtZGUcN-s = общий на аккаунт alexford0289 для всех сайтов)
  + sitemap.xml отправлен. Квота индексации сегодня съедена другими сайтами — крон добьёт.
- Bing WMT: сайт добавлен + верифицирован (мета-тег msvalidate.01 988EBC0B59488A1F91B3E7D9658B65C3)
  + sitemap в обработке. Bing UI-селектор «застревает» — переключение через _bing_switch2.py.
- IndexNow: 200, 134 URL. ВАЖНО: key=ecc6d98e... (ФАЙЛ indexnow_key.txt в modelsite, НЕ toolsite!)
  + keyLocation обязателен, иначе 403. Ключ-файл живёт в корне сайта.

## Монетизация
- Adsterra сайт 6062424 (категория Filehosts): NativeBanner 31310380 (pl31410879...2376e478...)
  + SocialBar 31310853 (pl31411352...9f5bf63f...). ОБА активны, коды вшиты в build.py, CDN 200.
  Коды в adsterra_codes.json.

## БЭКЛИНКИ
- GitHub: https://github.com/Alex20Sas12/modelfit (публичный репо, README с живой таблицей) — dofollow
- dev.to: пост опубликован (акк kata_omel_3f34301f3ec5928, вход через Google) — dofollow
  https://dev.to/kata_omel_3f34301f3ec5928/i-built-a-can-i-run-this-llm-site-...-3gd4
- AlternativeTo: акк уже существовал (email, не Google) — листинг ShablonyPRO в модерации с 07.09;
  сброс пароля для modelfit не завершён (письмо не пришло за 2 мин). НИЗКИЙ приоритет.

## КРОНЫ (deliver=local, no_agent)
- b0bc91a7d033 modelfit-daily-refresh 09:40 МСК = refresh.py (fetch→test→build→deploy→indexnow)
- f852cc3390ca modelfit-gsc-index 10:45 МСК = modelfit_gsc.py (GSC URL inspection, самолечащаяся обёртка)

## КОНВЕЙЕР
python fetch.py (HF API, 110 моделей) → test_build.py (гейт формул) → build.py → 
site/ → vercel deploy --prod (XDG_DATA_HOME=$APPDATA/xdg.data) → IndexNow. Всё в refresh.py.

## Грабли (записаны в скилл tool-site-factory)
- GGUF-парсер: mtp-/mmproj-/vision-/multilingual-файлы — НЕ полная модель. fetch.py walk()
  пропускает их по имени файла; clean_quants() добивает варианты «Q3_K_M-vision» (plain-квант приоритетнее).
  Без этого Qwen3.8-27B показывал «Q4_0 3.5GB» (это mtp-модуль) — портило tier-рейтинги.
- Split-shard GGUF: quant_of() сначала снимает «-00001-of-00013», иначе каждый шард = свой «квант».
- Bing: native-setter НЕ регистрирует value в React-форме add-site — только реальный insertText клавишами.
- Copilot-попап Bing перекрывает клики — закрывать «Not now» перед add-site.

## PINTEREST-КАНАЛ (запущен 19.09)
- Аккаунт: alexford0289mf (почта alexford0289+mf@gmail.com, читается himalaya -a alex;
  пароль + board_id в pin_creds.json). Окно `chrome-launch.py modelfit` = порт 9274, ПРЯМОЙ BY-IP.
- Доска "Local LLM Hardware" (id 1122311238331228592). Профиль: имя ModelFit, bio+сайт заполнены.
- Первый пин опубликован 19.09 (best-llm-for-24gb-vram), прогрев 7 сохранений — до публикации.
- Очередь pin_queue.json: 20 пинов (tier/GPU/модельные страницы). Картинки = скриншоты сайта
  (pin_gen.py, НЕ AI-генерация — антибан-правило pinterest-factory).
- КРОНЫ: e73c0fefb837 прогрев 15:55 + d31d88483ed4 пин 16:25 (после moneycalcs/feecalcs окон).
- Грабли: pin_post.py board_url захардкожен на юзера; счётчик «N пин» читается с _boards-страницы.

## НЕ СДЕЛАНО (честно)
- Hacker News: reCAPTCHA на регистрации + karma-wall для Show HN (новые акки не постят). Мёртвый путь бесплатно.
- TAAFT / Toolify: листинг $99 (единственная кнопка Pay). Бюджет $0 → skip.
- HuggingFace Space: PENDING. Форма /join в доверенном окне 9232 БЕЗ капчи (email+password→Next→
  username+ToS→Create Account), но multi-step форма капризна: focus «протекает» в пароль, чекбокс ToS
  залипает. username modelfit ЗАНЯТ, свободен (проверено API /api/users/<u>/overview=404): modelfit-hf,
  canirunllm. Почта modelfit6046@uberip.com (mail.tm, пароль Mf9x!Kp2Qz7LmR4v). Вернуться в своей сессии.
- IndieHackers (modelfit продукт): PENDING. Аккаунт shablonypro жив, форма /products/new, но Dropzone
  логотипа не принимает DOM.setFileInputFiles (previews:0), tagline ≤60 символов. Ссылка nofollow → низкий ROI.
- SaaSHub /services/submit: PENDING. Логин жив (shablonypro), форма: url + Continue, но submit молча не уходит
  (guidelines-страница с категориями/конкурентами — нужен полный wizard).
- Reddit r/LocalLLaMA: аудитория живёт там, но kate_makes_sheets (2 дня) постить ссылки НЕЛЬЗЯ = бан домена.
  Нужен НОВЫЙ акк-персона (правило: каналы не переиспользуются): mail.tm + окно 9275 + 2 недели прогрева
  (сабы LocalLLaMA/LocalLLM, комменты без ссылок), потом 1 полезный пост. Отдельная сессия.

## СДЕЛАНО В СЕССИЮ «МАКСИМУМ» (19.09, вечер)
- OG-карточки 1200x630 (Pillow, brand-стиль) на каждой странице + summary_large_image — превью при любом шере.
- Кнопки шаринга на всех 134 страницах: X, Reddit, HN, Telegram, WhatsApp, native share (JS из location).
- Бейджи badge-*.svg + публичный JSON API /api/models.json (CC-BY, attribution ModelFit) — ростовые петли:
  разработчики встраивают бейдж/берут API → бесплатные бэклинки.
- llms.txt дополнен tier-страницами. GitHub profile README (Alex20Sas12/Alex20Sas12) = витрина ModelFit.
- PR #225 в rafska/awesome-local-llm (2.8k звёзд): ModelFit в секцию Hardware рядом с 2 VRAM-калькуляторами.
- Topics репо modelfit: gguf, llama-cpp, llm, local-llm, vram, calculator, hardware.
- IndexNow 200 (134 urls) повторно. Все 4 ключевые страницы 200.
- Грабля: browser_exec capture_screenshot PNG на HF-капче таймаутит — JPEG через cdp напрямую работает.


## СЛЕДУЮЩИЕ ШАГИ (по убыванию ROI)
1. Pinterest-конвейер (новый акк, 1 пин/день на tier/GPU-страницы — визуал = таблицы вердиктов)
2. Reddit r/LocalLLaMA — ПОЛЕЗНЫЙ пост-гайд (не ссылка), акк с прогревом
3. HF Space (Gradio-обёртка picker) = DR90+ бэклинк + встроенный трафик
4. Больше моделей: fetch.py top_ids(200) + языковые страницы (/es/ /de/ /ru/) под geo-спрос
5. Бэклинки из комментов под GitHub-issues «how much vram for X» (полезный ответ + ссылка)
