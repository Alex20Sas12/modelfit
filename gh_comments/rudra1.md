On 4-6 GB cards the OOM is mostly a budgeting problem before it's an offloading problem. Measured GGUF file sizes (Hugging Face API, our daily dataset) for what actually fits at 8K context, KV cache included:

- Llama-3.2-3B Q4_K_M ≈ 2.0 GB file → ~4.0 GB total needed
- Qwen3-4B Q4_K_M ≈ 2.5 GB file → ~4.8 GB total needed
- gemma-3-4b-it Q4_K_M ≈ 2.7 GB file → ~5.1 GB total needed (tight on a 6 GB card, fine to run)

So the rule that stops CUDA OOM crashes here: keep weights + KV + ~8% runtime overhead under ~0.92 × VRAM. KV cache is linear in context — a 4B model at 8K f16 adds roughly 1.0-1.2 GB, at 32K it adds ~4-5 GB and that is exactly where the "context window memory spikes" you describe start eating unallocated space. Cap n_ctx (e.g. -c 4096) before dropping quant size; llama.cpp --list-models-style guessing by parameter count ("14B at Q4 should be 8 GB") is what fills VRAM aggressively.

We built a page that does this per model from real file sizes (no formula estimates) — e.g. https://modelfit-eight.vercel.app/best-llm-for-4gb-vram/ (also 8GB: https://modelfit-eight.vercel.app/best-llm-for-8gb-vram/) and https://modelfit-eight.vercel.app/what-llm-can-i-run/ let you type your exact VRAM and see verdicts. Hope it helps for the fallback presets design: the threshold table can be generated from the same measured data (public JSON dump https://modelfit-eight.vercel.app/api/models.json, CC BY 4.0).
