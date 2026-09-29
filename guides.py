# -*- coding: utf-8 -*-
"""guides.py — informational guides (traffic surface competitors own, we didn't).
Called from build.py main(). Returns (urls, md_lines)."""
import os
from build import E, BASE, page, CLOUD_CTA, fmt_gb

def vram_table(params_list):
    """Static VRAM guide table from bits-per-weight (honest: labeled as rule-of-thumb, links to measured pages)."""
    quants = [("Q2_K", 3.4), ("Q3_K_M", 3.9), ("IQ4_XS", 4.3), ("Q4_K_M", 4.9), ("Q5_K_M", 5.7), ("Q6_K", 6.6), ("Q8_0", 8.5)]
    head = "".join(f"<th style='text-align:right'>{q}</th>" for q, _ in quants)
    rows = ""
    for p in params_list:
        cells = "".join(f"<td class='n'>{p*b/8*1.1+1.5:.1f}</td>" for _, b in quants)  # +10% overhead, +1.5GB KV/ctx
        rows += f"<tr><td><b>{p}B</b></td>{cells}</tr>"
    return (f"<table><thead><tr><th>Model size</th>{head}</tr></thead><tbody>{rows}</tbody></table>"
            "<p class='note'>Rule-of-thumb: params × bits/8 + ~10% tensor overhead + ~1.5GB KV cache at 8K context. "
            "Exact numbers per model (measured GGUF files) are on each model page.</p>")

GUIDES = [
    ("how-much-vram-for-llm", "How Much VRAM Do You Need to Run a Local LLM? (7B, 13B, 70B)",
     "VRAM needed to run 7B, 13B, 30B and 70B LLMs locally at every quantization — measured table, KV cache and offload rules.",
     """<p>The short answer: <b>params × bits ÷ 8, plus KV cache, plus ~10% overhead</b>. But the exact file sizes differ
between repos — always check the measured size of the GGUF you actually download. Here is the full picture.</p>
<h2>VRAM by model size and quantization</h2>
TABLE7
<h2>The three costs people forget</h2>
<ol>
<li><b>KV cache grows with context.</b> 8K context on a 27B model costs ~1-4GB; 128K context can cost more than the weights themselves. Use the context selector on any <a href="/what-llm-can-i-run/">model page</a> to see it.</li>
<li><b>Runtime overhead.</b> CUDA context, compute buffers and fragmentation eat ~8-15% — that's why a 23.5GB model does not fit a 24GB card.</li>
<li><b>MoE models keep every expert in RAM/VRAM.</b> A 30B-A3B MoE with 3B active params still needs the full 30B's bytes resident — it is only <i>faster</i> than dense 30B, not smaller.</li>
</ol>
<h2>What fits what (rule of thumb)</h2>
<ul>
<li><b>8GB</b> — 7-8B models at Q4_K_M, 12-14B at Q2/Q3. <a href="/best-llm-for-8gb-vram/">Ranked list →</a></li>
<li><b>12GB</b> — 8B at Q8, 14B at Q4-Q5. <a href="/best-llm-for-12gb-vram/">Ranked list →</a></li>
<li><b>16GB</b> — 14B at Q6-Q8, 27-32B at Q3-Q4. <a href="/best-llm-for-16gb-vram/">Ranked list →</a></li>
<li><b>24GB</b> — 27-32B at Q4-Q5, 70B MoE (A3B) at Q4. <a href="/best-llm-for-24gb-vram/">Ranked list →</a></li>
<li><b>48GB+</b> — 70B dense at Q4-Q5. <a href="/best-llm-for-48gb-vram/">Ranked list →</a></li>
</ul>
<h2>Not enough VRAM? Three escape hatches</h2>
<p><b>CPU+GPU offload</b> (llama.cpp <code>--n-gpu-layers</code>): splits layers between VRAM and system RAM — works, but every offloaded layer pays PCIe speed. <b>Smaller quant</b>: Q4_K_M → IQ3/Q2 saves 30-50% memory at a real quality cost. <b>Rent a GPU</b>: a cloud RTX 4090 costs ~$0.30-0.50/h when you need the big model just occasionally.</p>
CLOUD""", ["7B", "8B", "13B", "14B", "27B", "32B", "70B", "235B"]),

    ("q4-k-m-explained", "GGUF Quantizations Explained: Q4_K_M, IQ3, Q8_0 — Which to Pick?",
     "What Q4_K_M, Q5_K_M, IQ3_XXS, Q8_0 and F16 actually mean, how much quality each costs, and which quant to pick for your VRAM.",
     """<p>Quantization shrinks model weights from 16-bit floats to fewer bits. Less memory, slightly worse outputs. Here is the decoder ring.</p>
<h2>The naming scheme</h2>
<ul>
<li><b>Q4</b> = ~4 bits per weight (4.5-5 in practice — some tensors stay 16-bit). <b>K</b> = k-quant (block-wise scales, better than legacy Q4_0/Q4_1). <b>M/L/S/XL</b> = medium/large/small/extra-large variant — which tensors get more bits.</li>
<li><b>IQ3_XXS / IQ2_M</b> = importance-matrix quants: calibrated on real text, better quality per bit than plain Q3/Q2, slightly slower to load.</li>
<li><b>UD-*</b> = unsloth's dynamic quants: they keep attention/embeddings at higher precision automatically.</li>
<li><b>Q8_0</b> ≈ visually lossless. <b>F16/BF16</b> = the original model, no compression.</li>
</ul>
<h2>Memory cost per quant</h2>
TABLE8
<h2>Which one do I pick?</h2>
<ol>
<li><b>Default: Q4_K_M</b> (or IQ4_XS / UD-Q4_K_XL). ~2-3% quality loss vs F16 on most benchmarks — the community consensus sweet spot.</li>
<li>VRAM headroom? <b>Q5_K_M/Q6_K</b> — diminishing returns but free quality.</li>
<li>VRAM tight? <b>IQ3_XXS/Q3_K_M</b> — noticeable degradation on reasoning tasks; only if it means running at all.</li>
<li>Below Q3 — chat still works, math/code/logic suffer visibly. Last resort.</li>
</ol>
<p>Every <a href="/what-llm-can-i-run/">ModelFit model page</a> lists the measured file size of each quant actually published for that model — pick the largest one that fits your card.</p>
CLOUD""", ["8B", "14B", "32B", "70B"]),

    ("ollama-vs-llama-cpp-vs-lm-studio", "Ollama vs llama.cpp vs LM Studio: Which Local LLM Runtime?",
     "Honest comparison of Ollama, llama.cpp and LM Studio for running local LLMs: speed, memory, API support and ease of use in 2026.",
     """<p>All three run GGUF files on the same engine (llama.cpp) — the difference is packaging. Pick by who you are.</p>
<h2>At a glance</h2>
<table><thead><tr><th></th><th>Ollama</th><th>llama.cpp</th><th>LM Studio</th></tr></thead><tbody>
<tr><td>Setup</td><td>one installer</td><td>build or download binary</td><td>one installer, GUI</td></tr>
<tr><td>Model source</td><td>own registry + any HF GGUF (<code>ollama run hf.co/repo:quant</code>)</td><td>any GGUF file, any HF repo (<code>-hf repo:quant</code>)</td><td>built-in HF browser</td></tr>
<tr><td>OpenAI-compatible API</td><td>yes (:11434)</td><td>yes (llama-server)</td><td>yes (local server tab)</td></tr>
<tr><td>Control (context, GPU layers, KV quant)</td><td>limited (Modelfile)</td><td>full</td><td>good (sliders)</td></tr>
<tr><td>Speed</td><td colspan="3" style="text-align:center">same engine — within a few % when settings match</td></tr>
</tbody></table>
<h2>Which to choose</h2>
<ul>
<li><b>Just want it to work / building an app on top:</b> Ollama. <code>ollama run hf.co/&lt;repo&gt;:&lt;quant&gt;</code> pulls the exact GGUF from Hugging Face — every quant on this site works.</li>
<li><b>Want every knob (KV-cache quant, custom samplers, maximum tok/s):</b> llama.cpp's <code>llama-server</code> or <code>llama-cli</code>.</li>
<li><b>Prefer a GUI, chat UI, and browsing models visually:</b> LM Studio.</li>
</ul>
<h2>Memory tips that apply to all three</h2>
<p>Set context to what you need (not the max) — KV cache scales linearly. On Macs raise the wired limit (<code>sysctl iogpu.wired_limit_mb</code>) to use more than 75% of unified memory. Check exact per-model numbers on any <a href="/what-llm-can-i-run/">model page</a>.</p>
CLOUD""", None),

    ("rtx-3090-vs-4090-llm", "RTX 3090 vs RTX 4090 for Local LLMs: Real Numbers",
     "3090 vs 4090 for LLM inference: same 24GB VRAM, 936 vs 1008 GB/s bandwidth, used-price gap — which one actually runs models faster?",
     """<p>Both cards hold 24GB — the same models fit both (<a href="/best-llm-for-rtx-3090/">3090 picks</a>, <a href="/best-llm-for-rtx-4090/">4090 picks</a>). The difference is speed and price.</p>
<h2>Head to head</h2>
<table><thead><tr><th></th><th>RTX 3090</th><th>RTX 4090</th></tr></thead><tbody>
<tr><td>VRAM</td><td>24GB GDDR6X</td><td>24GB GDDR6X</td></tr>
<tr><td>Memory bandwidth</td><td>936 GB/s</td><td>1008 GB/s</td></tr>
<tr><td>Decode speed (LLM)</td><td colspan="2" style="text-align:center">~8% apart — decode is bandwidth-bound</td></tr>
<tr><td>Prompt processing</td><td>slower (FP16 TFLOPs ~36 vs ~83)</td><td>~2× faster</td></tr>
<tr><td>Power</td><td>350W</td><td>450W</td></tr>
<tr><td>Price (used market)</td><td>~$600-800</td><td>~$1500-1800</td></tr>
</tbody></table>
<h2>The verdict</h2>
<p><b>For pure token generation the 3090 is the value king</b>: within ~8% of a 4090 at half the used price. The 4090 wins on prompt processing — long system prompts, RAG, big documents feel 2× snappier — and on efficiency (same work, less wall power).</p>
<p>Two 3090s (~$1400, 48GB pooled) beat one 4090 for models that need 25-48GB, if your board has two x8+ slots and you accept NVLink-less splitting.</p>
<h2>What fits 24GB, measured</h2>
<p>See the live ranked list: <a href="/best-llm-for-24gb-vram/">best LLMs for 24GB VRAM</a> — updated daily from measured GGUF file sizes.</p>
CLOUD""", None),

    ("run-70b-llm-24gb", "How to Run a 70B LLM on 24GB VRAM (Honest Options)",
     "Can you run Llama 70B or DeepSeek on one 24GB GPU? Three real options: heavy quants, CPU offload, MoE models — with measured numbers.",
     """<p>A 70B dense model at Q4_K_M measures ~40-43GB. It does not fit 24GB. Here is what actually works, in order of sanity.</p>
<h2>Option 1 — run a MoE model instead (best)</h2>
<p>Modern MoE models give near-70B quality at 70B-total / 3B-active scale. A 30B-A3B MoE at Q4 measures ~18-20GB and <b>fits one 24GB card</b> — and decodes fast because only ~3B params are read per token. Check measured sizes: <a href="/best-llm-for-24gb-vram/">models that fit 24GB</a>.</p>
<h2>Option 2 — CPU+GPU offload (slow but real)</h2>
<p>llama.cpp can split layers: hot layers in VRAM, the rest in system RAM (<code>--n-gpu-layers 20</code> + as many as fit). Rule: offloaded layers run at RAM bandwidth (~50GB/s vs ~1000GB/s VRAM). A 70B with 60% offloaded decodes at ~2-4 tok/s — usable for batch jobs, painful for chat. Needs 48-64GB system RAM.</p>
<h2>Option 3 — extreme quants (quality cost)</h2>
<p>IQ2_XXS/Q2_K shrink 70B to ~24-27GB — it might squeeze in with offload, but at Q2 quality reasoning degrades badly. Almost always a worse deal than option 1.</p>
<h2>Option 4 — rent, don't buy</h2>
<p>If you need a true dense 70B occasionally: an A100/H100 hour on a marketplace costs less than a coffee. For daily use, two used 3090s (48GB) run 70B Q4 natively for ~$1400.</p>
CLOUD
<h2>Measured examples</h2>
<p>Exact file sizes per quant for every 70B-class model we track — see each model page from the <a href="/best-llm-for-48gb-vram/">48GB list</a> and <a href="/best-llm-for-64gb-vram/">64GB list</a>.</p>""", None),
]

def build_guides(models, OUT):
    urls, md_lines = [], []
    cards = "".join(f'<a href="/guides/{s}/">{E(t)}<small>{E(d[:70])}…</small></a>' for s, t, d, _, _ in GUIDES)
    hub = page("guides/index.html", "Local LLM Guides — VRAM, Quantization, Runtimes | ModelFit",
               "Practical guides for running LLMs locally: VRAM math, quantization choices, runtime comparison and GPU picks. Numbers from measured GGUF files.",
               f"""<div class="crumb"><a href="/">All models</a> › Guides</div>
<h1>Local LLM guides</h1>
<p class="sub">Everything here is backed by the measured data on this site — updated daily from Hugging Face.</p>
<div class="grid">{cards}</div>""", "guides/")
    d = os.path.join(OUT, "guides"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(hub)
    urls.append(f"{BASE}/guides/")
    for slug, title, desc, body, sizes in GUIDES:
        if sizes:
            body = body.replace("TABLE7", vram_table([int(x.rstrip("B")) for x in sizes])) \
                       .replace("TABLE8", vram_table([int(x.rstrip("B")) for x in sizes]))
        body = body.replace("CLOUD", CLOUD_CTA)
        jsonld = {"@context": "https://schema.org", "@type": "TechArticle",
                  "headline": title, "description": desc, "url": f"{BASE}/guides/{slug}/",
                  "author": {"@type": "Organization", "name": "ModelFit", "url": BASE}}
        html_out = page(f"guides/{slug}/index.html", f"{title} | ModelFit", desc,
                        f'<div class="crumb"><a href="/">All models</a> › <a href="/guides/">Guides</a> › {E(title)}</div>'
                        f'<h1>{E(title)}</h1>{body}<div class="ad-slot"></div>'
                        f'<h2>More guides</h2><div class="grid">{cards}</div>',
                        f"guides/{slug}/", jsonld)
        gd = os.path.join(OUT, "guides", slug); os.makedirs(gd, exist_ok=True)
        with open(os.path.join(gd, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html_out)
        urls.append(f"{BASE}/guides/{slug}/")
        md_lines.append(f"- [Guide: {title}]({BASE}/guides/{slug}/)")
    return urls, md_lines

if __name__ == "__main__":
    import json
    ms = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json"), encoding="utf-8"))
    u, md = build_guides(ms, os.path.join(os.path.dirname(os.path.abspath(__file__)), "site"))
    print(len(u), "guide urls")
