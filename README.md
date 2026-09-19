# ModelFit — Can I Run This LLM?

**Measured** VRAM/RAM requirements for trending local LLMs. Every number is the actual GGUF
file size published on Hugging Face (split shards summed) + KV cache (GQA formula from
config.json where available) + runtime overhead — not a params x bits/8 estimate.

Live site: **https://modelfit-eight.vercel.app** (updated daily by cron, 40+ models,
per-quant tables, GPU verdicts from RTX 3060 to Mac Studio 512GB).

Why: for Kimi K3 five popular pages showed four different VRAM numbers
(594 GB / 1.51 TB / 1.68 TB / "impossible") because they all guess. Measured files don't lie.

## Top models by downloads (smallest published build)

| Model | Downloads | Smallest build |
|---|---|---|
| [Qwen3.8-27B](https://modelfit-eight.vercel.app/unsloth-qwen3-8-27b-gguf/) | 7628k | 6.2 GB |
| [Huihui-Qwen3.8-27B-abliterated](https://modelfit-eight.vercel.app/huihui-ai-huihui-qwen3-8-27b-abliterated-gguf/) | 2832k | 10.0 GB |
| [Qwen3.8-27B-Uncensored](https://modelfit-eight.vercel.app/jonathancoletti-qwen3-8-27b-uncensored-gguf/) | 2363k | 1.7 GB |
| [Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP](https://modelfit-eight.vercel.app/hauhaucs-qwen3-8-27b-uncensored-hauhaucs-aggressive-mtp-gguf/) | 2282k | 10.3 GB |
| [Qwen3.8-27B](https://modelfit-eight.vercel.app/lmstudio-community-qwen3-8-27b-gguf/) | 2052k | 16.8 GB |
| [Gemma-4-E4B-Uncensored-HauhauCS-Aggressive](https://modelfit-eight.vercel.app/hauhaucs-gemma-4-e4b-uncensored-hauhaucs-aggressive/) | 1995k | 4.4 GB |
| [deepseek-v4](https://modelfit-eight.vercel.app/antirez-deepseek-v4-gguf/) | 1964k | 3.8 GB |
| [Qwen3.8-27B-Heretic-Abliterated-Uncensored](https://modelfit-eight.vercel.app/0bserverx-qwen3-8-27b-heretic-abliterated-uncensored-gguf/) | 1884k | 10.2 GB |
| [gemma-4-E4B-it](https://modelfit-eight.vercel.app/ggml-org-gemma-4-e4b-it-gguf/) | 1507k | 4.7 GB |
| [Qwen3.8-Flash-Next](https://modelfit-eight.vercel.app/unsloth-qwen3-8-flash-next-gguf/) | 1469k | 72.5 GB |
| [Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NEO-CODER-MAX-MTP](https://modelfit-eight.vercel.app/davidau-qwen3-8-27b-turbo-fable-cold-fusion-735-882-heretic-uncensored-neo-coder-max-mtp-gguf/) | 1197k | 23.8 GB |
| [gemma-4-12B-it-qat](https://modelfit-eight.vercel.app/unsloth-gemma-4-12b-it-qat-gguf/) | 1164k | 6.7 GB |
| [Qwen3.8-27B-GSQ-RCO](https://modelfit-eight.vercel.app/ista-daslab-qwen3-8-27b-gsq-rco-gguf/) | 1078k | 17.2 GB |
| [gemma-4-12b-it](https://modelfit-eight.vercel.app/unsloth-gemma-4-12b-it-gguf/) | 779k | 4.2 GB |
| [gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2](https://modelfit-eight.vercel.app/yuxinlu1-gemma-4-12b-agentic-fable5-composer2-5-v2-3-5x-tau2-gguf/) | 703k | 6.1 GB |
| [gemma-4-26B-A4B-it-qat](https://modelfit-eight.vercel.app/unsloth-gemma-4-26b-a4b-it-qat-gguf/) | 663k | 1.2 GB |
| [GLM-5.3-Flash](https://modelfit-eight.vercel.app/unsloth-glm-5-3-flash-gguf/) | 595k | 1.1 GB |
| [Huihui-DeepSeek-V4-Flash-0731-abliterated](https://modelfit-eight.vercel.app/huihui-ai-huihui-deepseek-v4-flash-0731-abliterated-gguf/) | 527k | 86.7 GB |
| [Kimi-K3](https://modelfit-eight.vercel.app/unsloth-kimi-k3-gguf/) | 494k | 466.4 GB |
| [GLM-5.3](https://modelfit-eight.vercel.app/unsloth-glm-5-3-gguf/) | 476k | 216.7 GB |

## Data pipeline

- `fetch.py` — pulls trending GGUF repos from the public HF API (no key), walks repo trees,
  sums shard sizes per quant, parses config.json for exact KV math.
- `build.py` — static site generator: one page per model + llms.txt + markdown twins + FAQPage/Dataset/BreadcrumbList JSON-LD.
- `test_build.py` — formula gate (KV cache verified against llama.cpp reference numbers).
- `refresh.py` — daily cron: fetch -> test -> build -> deploy -> IndexNow ping (Bing/Yandex).

## License

Code: MIT. Data derived from Hugging Face public API; model sizes belong to their uploaders
(unsloth, bartowski, lmstudio-community, etc.).
