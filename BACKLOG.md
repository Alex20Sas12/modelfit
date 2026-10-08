# ModelFit — BACKLOG (аудит 27.09, сессия «разбор по полочкам»)
Конкуренты сняты в _comp/*.html (8 сайтов). Приоритет = ROI/трудозатраты. Всё $0.

## P0 — точность данных (доверие = весь сайт)
1. **MLA KV-cache для DeepSeek** — kv_cache_gb() считает GQA-формулой (kv_heads×head_dim);
   у DeepSeek V3/V4 MLA: KV = layers × (kv_lora_rank + qk_rope_head_dim) × ctx × 2 байта.
   Сейчас KV завышен в разы → вердикты «no» там, где «yes». vramcalculator.com и fitllm.run
   это явно моделируют и хвастаются этим. Фикс: if arch.model_type in (deepseek_v2,v3,v4) → MLA-формула,
   читать kv_lora_rank/qk_rope_head_dim из config.json (fetch.py уже тянет — добавить ключи).
2. **Мусор в каталоге** — топ-1 на /best-llm-for-24gb-vram/ = «Qwen3.8-27B-Heretic-Abliterated-Uncensored»
   (ноунейм-аплоадер, params показывает 54B при имени 27B — баг safetensors-пола). Фильтр:
   приоритет unsloth/bartowski/lmstudio-community при дублях модели; params sanity-check (имя 27B ≠ 54B → null).
   + brand-safety: «Uncensored/Abliterated» в заголовках tier-страниц = риск для Adsterra/серпов.
3. **Контекст-слайдер** — KV зафиксирован на 8K. Все серьёзные конкуренты дают выбор ctx (4K/8K/32K/128K).
   Фикс: на модельной странице input ctx → JS пересчитывает need (данные arch уже в DATA).

## P1 — фичи, которых нет и которые закрывают интент
4. **tok/s оценка** — ГЛАВНЫЙ пробел. canirunthisllm/localllmchecker/canitrun/softperceptron показывают скорость.
   Формула бесплатна: tok/s ≈ bandwidth_GBps / активные_байты_веса (decode memory-bound).
   Нужна таблица bandwidth для ~20 GPU/Mac (одноразово, хардкод в build.py, как GPUS сейчас).
   Для CPU: DDR4/DDR5 dual-channel ~50-80 GB/s.
5. **Копипаст-команды** на каждой модельной странице: `ollama run …`, `lmstudio`, llama.cpp-флаг.
   canirunthismodel.sefarai.com делает — резко растит dwell time и «полезность».
   Осторожно: ollama-имя ≠ HF-id; безопасно — llama.cpp-команда с прямой ссылкой на GGUF-файл.
6. **Picker: dropdown GPU вместо ручного ввода VRAM** — люди не знают свои ГБ.
   GPUS-список уже есть в build.py → <select> рядом с <input>. 10 строк.
7. **«What should I buy?» (обратная задача)** — localllmchecker: модель → самая дешёвая карта.
   У нас есть verdicts() → добавить блок «Cheapest way to run: used RTX 3090 ~$650 / 2×3060 / Mac M-series 64GB»
   со СТАТИЧНОЙ таблицей б/у-цен (обновлять раз в месяц вручную). Позже — партнёрки (см. Монетизация).
8. **Multi-GPU** — вместо голого «server-grade»: «needs 2×24GB» (ceil(need/24)). Одна строка.
9. **WebGL-автоопределение GPU** — navigator.gpu / WEBGL_debug_renderer_info → предзаполнить picker.
   ~15 строк JS, вау-эффект. (конкуренты боятся — «nothing leaves your browser» у всех; у нас тоже ок).

## P2 — SEO/контент
10. **Гайды (5-8 штук)** — у canitrun «Featured Guides», у vramcalculator блог (BlogPosting JSON-LD).
    Информационный спрос: «how much vram for 70b», «q4_k_m vs q5_k_m», «what is kv cache»,
    «ollama vs llama.cpp vs lm studio», «3090 vs 4090 for llm». Каждая — 600-900 слов + внутренний линк.
    Это единственная незакрытая поверхность поиска (инструментальные запросы мы уже покрыли).
11. **hreflang + /es/ /de/ /ru/** — STATE уже планирует; llmconfigurator единственный с hreflang.
    Делать ПОСЛЕ гайдов (EN-спрос сначала).
12. **Статические no-JS таблицы на tier-страницах** — canitrun дублирует вердикты текстом «for search engines».
    У нас таблицы и так в HTML — проверить что picker-страница не пустая без JS (сейчас пустая!).
13. **GSC-квота** — gsc_progress.json: QUOTA/TIMEOUT. Крон 10:05 уже первый в очереди. Просто ждать индексацию.

## P3 — дистрибуция (из STATE «НЕ СДЕЛАНО», переприоритизировано)
14. **Reddit r/LocalLLaMA** — аудитория живёт там. Новый акк+прогрев 2 нед (по плану STATE).
    Пост-гайд «I measured GGUF sizes of 110 models, here's the real VRAM table» — данные у нас уникальные.
15. **GitHub-комменты** — issues «how much VRAM for X» → полезный ответ + ссылка на страницу модели. Крон-поиск по GH search API.
16. **HF Space** — тупик (hCaptcha Enterprise, записано в STATE). Скип до платного решателя или помощи владельца руками.
17. **AlternativeTo/SaaSHub** — довести wizard'ы (низкий ROI, но бесплатно).

## Монетизация (когда пойдёт трафик, ≥500 визитов/день)
- Партнёрки GPU-хостингов: RunPod/Vast.ai/TensorDock/Hyperstack/DataCrunch (у всех есть программы, USDT/PayPal).
  НИ ОДИН конкурент их не использует (проверено: affiliate_links=[] у всех 8) — будем первыми.
  Место вставки: блок «Cloud instead? rent RTX 4090 from $0.4/h» на страницах с вердиктом «server-grade»/«no» —
  максимальный интент (модель не влезает → человек ГОТОВ арендовать).
- AdSense заявка позже (SocialBar Adsterra сейчас ест CWV — не снимать до AdSense-аппрува, деньги важнее).

## Мелочи (сделать за компанию с P0-P1)
- [ ] title главной «ModelFit — Can I Run This LLM? VRAM & RAM Requirements (2026)» — год зашит, забыть обновить к 2027.
- [ ] og.png один на все страницы — для tier/compare сделать свои (make_og уже умеет, вызвать в tiers.py).
- [ ] related() = топ-8 по downloads на КАЖДОЙ странице (одинаковые блоки везде) → кластеризовать по семейству/тиру.
- [ ] В футер — ссылку на /api/models.json и бейджи (ростовая петля заявлена, но入口 спрятан в /about/).
- [ ] fetch.py HYPE-лист стареет («ponytail: refresh») — trending_ids уже покрывает, но раз в месяц глазами.
