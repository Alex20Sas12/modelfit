---
title: "I built a \"Can I run this LLM?\" site where every VRAM number is measured, not guessed"
published: true
tags: llm, ai, opensource, productivity
canonical_url: https://dev.to/alex20sas12
---

## The problem: five sites, four different answers

When Kimi K3 dropped, I searched "kimi k3 vram requirements" like everyone else.
Five popular pages gave me:

- 594 GB
- 1.51 TB
- 1.68 TB
- "you can't run it, period"
- one page said Q4 fits in "about 800 GB", another said 1.2 TB

They can't all be right. And they're not all wrong either — they're **computing
different things with the same formula**: `params × bits / 8`. That formula
ignores the embedding table (often unquantized even in Q2 builds), attention
tensors kept in higher precision, the output head, and container overhead.
For a 1T-parameter MoE like Kimi K3, those "small" omissions add up to
hundreds of gigabytes.

## The fix: stop computing, start measuring

Every GGUF quant of every popular model is **already published as a file** on
Hugging Face. The file size IS the answer — it's what you download, what loads
into memory. No formula needed.

So I built [ModelFit](https://modelfit-eight.vercel.app):

1. **fetch.py** walks the HF API (public, no key): trending GGUF repos + top by
   downloads + hype keywords. For each repo it walks the tree (big models store
   quants in `Q4_K_M/` subdirs, shards like `-00001-of-00012.gguf` get summed),
   and pulls `config.json` for exact KV-cache math.
2. **build.py** computes need = weights + KV cache + overhead, and renders one
   page per model: quant-by-quant table, verdicts for every GPU from RTX 3060
   to Mac Studio 512GB, an interactive "type your VRAM" checker, FAQ with
   JSON-LD.
3. **KV cache** is exact when config.json is available (GQA formula:
   `2 × layers × kv_heads × head_dim × ctx × 2 bytes`), otherwise a flat
   +20%/min-1.5GB heuristic — and the page **says which one it used**.
4. A daily cron re-fetches, re-tests (formula gate against llama.cpp reference
   numbers), rebuilds, deploys to Vercel, and pings IndexNow. New model release
   → page live within 24h, usually before the blog posts.

## What the measured numbers actually show

Kimi K3 (from unsloth's repo, shards summed):

| Quant | Measured file | VRAM/RAM needed (8K ctx) |
|---|---|---|
| UD-Q1_0 | 466.4 GB | 561.1 GB |
| UD-Q4_K_XL | 1.51 TB | ~1.6 TB |
| F16 | ~3 TB | server farm |

So the "594 GB" pages were roughly right for Q1, the "1.51 TB" pages were right
for Q4 — and the people arguing in the comments were both right about different
quants. The site kills the argument by showing the whole ladder.

## The honest limitations

- Repos without a readable config.json get the flat overhead rule (~20% +
  1.5GB). Marked on-page.
- MoE models count **total** size — all experts stay resident in memory even
  though only some fire per token. This surprises people used to "active params"
  marketing numbers.
- Default context is 8K. KV cache grows linearly; each page explains the math.
- CPU inference speed is a different question (memory bandwidth, not capacity)
  — the FAQ gives rough tok/s bands instead of pretending to precision.

Everything is open source: [github.com/Alex20Sas12/modelfit](https://github.com/Alex20Sas12/modelfit).
If your favorite model is missing or a number looks wrong, the pipeline is
three files — PRs welcome.

*Data: Hugging Face public API. Model sizes belong to their uploaders
(unsloth, bartowski, lmstudio-community and others — the community doing the
real quantization work).*
