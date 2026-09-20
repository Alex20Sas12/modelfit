# ModelFit — Can I run this LLM?

[![ModelFit can-i-run](https://modelfit-eight.vercel.app/badge-can-i-run.svg)](https://modelfit-eight.vercel.app/what-llm-can-i-run/)

**Live site: https://modelfit-eight.vercel.app**

VRAM/RAM requirements for 110+ trending local LLMs — Kimi K3, Gemma 4, DeepSeek V4, Qwen 3.8, GLM-5, Llama 3.1 and every model trending on Hugging Face GGUF.

## Why this site is different

Every number is **measured, not computed**:

- Sizes come from the **actual GGUF files** published on Hugging Face (unsloth, bartowski, ggml-org, lmstudio-community repos), pulled daily via the public HF API.
- Other sites use the naive `params × bits/8` formula and disagree with each other by 2× on the same model (Kimi K3: 594 GB vs 1.51 TB across five guides). The formula ignores embedding tables, unquantized tensors, and container overhead. The file size never lies.
- KV cache is computed exactly from `config.json` (GQA formula) when published.
- Auxiliary files (mmproj/mtp/vision modules) are filtered out — they are NOT full-model weights (a common source of wrong "requirements" numbers elsewhere).

## What you get

| Page | Example |
|---|---|
| Per-model verdicts + quant tables | [/unsloth-kimi-k3-gguf/](https://modelfit-eight.vercel.app/unsloth-kimi-k3-gguf/) |
| Ranked "best LLM for X" | [/best-llm-for-rtx-4090/](https://modelfit-eight.vercel.app/best-llm-for-rtx-4090/), [/best-llm-for-24gb-vram/](https://modelfit-eight.vercel.app/best-llm-for-24gb-vram/), [/best-llm-for-macbook-pro-m4-24gb/](https://modelfit-eight.vercel.app/best-llm-for-macbook-pro-m4-24gb/) |
| Interactive picker | [/what-llm-can-i-run/](https://modelfit-eight.vercel.app/what-llm-can-i-run/) |
| Machine-readable data | [/api/models.json](https://modelfit-eight.vercel.app/api/models.json) |
| For AI engines | [/llms.txt](https://modelfit-eight.vercel.app/llms.txt), markdown twin at `<any-page>/index.md` |

## Use the data in your own tools

```
GET https://modelfit-eight.vercel.app/api/models.json
```

```json
{
  "updated": "2026-09-19",
  "models": [{
    "id": "unsloth/Kimi-K3-GGUF",
    "name": "Kimi-K3",
    "downloads": 2197706,
    "page": "https://modelfit-eight.vercel.app/unsloth-kimi-k3-gguf/",
    "ggufs_gb": {"UD-Q1_0": 466.44, "UD-Q4_K_XL": 1508.7, "...": 0}
  }]
}
```

License: **CC BY 4.0** — free for anything, attribution required: `Data: ModelFit (modelfit-eight.vercel.app), measured from Hugging Face GGUF files`.

Badge for your README (links here):

```markdown
[![ModelFit](https://modelfit-eight.vercel.app/badge-can-i-run.svg)](https://modelfit-eight.vercel.app/what-llm-can-i-run/)
```

## How it works (this repo)

```
fetch.py    HF API (no key) -> models.json (tree walk, shard-aware, aux-file filter)
build.py    -> 134 static pages + llms.txt + og cards + api dump
tiers.py    -> "best LLM for XGB/GPU" ranked pages
test_build.py  formula gate (KV cache vs llama.cpp reference tables)
refresh.py  fetch -> test -> build -> vercel deploy -> IndexNow  (daily cron)
```

The site regenerates itself daily — when a new model lands on Hugging Face trending,
its verdict page exists within ~24h, usually before any human writes a guide.

## License

Code: MIT. Data: CC BY 4.0 (attribution above). Not affiliated with Hugging Face.
