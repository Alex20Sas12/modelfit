# POSTS — готовые тексты (публиковать ПОСЛЕ деплоя tier-страниц)

## Show HN (news.ycombinator.com/submit)
Title: Show HN: ModelFit – "Can I run this LLM?" with measured GGUF sizes, not formulas
URL: https://modelfit-eight.vercel.app/

Текст (оставить пустым ИЛИ короткий коммент первым):
> I kept seeing five different VRAM numbers for Kimi K3 across five popular pages
> (594 GB / 1.51 TB / 1.68 TB / "impossible") because they all compute
> params × bits/8. So I built a site that reads the ACTUAL GGUF file sizes from
> the Hugging Face API (summing split shards), adds KV cache from config.json
> where available (exact GQA formula), and regenerates 110+ model pages daily via
> cron. Pipeline is open source: github.com/Alex20Sas12/modelfit.
> Honest limitations: repos without config.json get a flat +20%/min-1.5GB overhead
> rule; MoE counts total size (correct, all experts stay resident); 8K ctx default.

## dev.to (dev.to/new) — canonical на сайт
Title: I built a "Can I run this LLM?" site where every number is measured, not guessed
Tags: llm, productivity, opensource, ai

Тело (markdown):
(см. devto_post.md)

## Reddit r/LocalLLaMA — ЧЕРЕЗ u/kate_makes_sheets, окно 9270, ПРЯМОЙ BY-IP
Заголовок: I measured the real GGUF sizes of 110 models so you stop trusting params×bits/8 estimates
Правила саба: технический контент ОК, прямая ссылка на tool = серая зона → формат
«сделал инструмент, вот данные, критика приветствуется». Первая волна — БЕЗ ссылки,
ссылка в первом комментарии или по вопросу. Карма аккаунта низкая — начать с
полезных ответов в тредах про VRAM, свой пост через 3-5 дней.

## Reddit r/SideProject — ссылка разрешена прямо в посте
Title: I built a VRAM requirements site with MEASURED GGUF sizes (open source, daily cron)
