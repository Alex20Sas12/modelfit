# -*- coding: utf-8 -*-
"""tiers.py — programmatic SEO pages: "Best LLM for XGB VRAM" + interactive picker.
Called from build.py main(). Returns (urls, md_lines) to fold into sitemap/llms.txt."""
import json, html, statistics
from build import E, BASE, clean_quants, need_gb, fmt_gb, params_b, page

TIERS = [8, 12, 16, 24, 32, 48, 64, 96]

# (slug-part, display name, vram GB, usable factor). Macs: unified memory, ~75% usable for GPU by default.
GPUS = [
    ("rtx-5090", "RTX 5090", 32, 1.0), ("rtx-4090", "RTX 4090", 24, 1.0),
    ("rtx-3090", "RTX 3090", 24, 1.0), ("rtx-5080", "RTX 5080", 16, 1.0),
    ("rtx-4080", "RTX 4080", 16, 1.0), ("rtx-4070-ti-super", "RTX 4070 Ti Super", 16, 1.0),
    ("rtx-5070-ti", "RTX 5070 Ti", 16, 1.0),
    ("rtx-4070-super", "RTX 4070 Super", 12, 1.0), ("rtx-4070", "RTX 4070", 12, 1.0),
    ("rtx-4060-ti-16gb", "RTX 4060 Ti 16GB", 16, 1.0), ("rtx-3080", "RTX 3080 12GB", 12, 1.0),
    ("rtx-3060", "RTX 3060 12GB", 12, 1.0), ("rtx-4060", "RTX 4060 8GB", 8, 1.0),
    ("rtx-3070", "RTX 3070 8GB", 8, 1.0), ("macbook-pro-m4-24gb", "MacBook Pro M4 (24GB)", 24, 0.75),
    ("macbook-air-16gb", "MacBook Air M3/M4 (16GB)", 16, 0.75),
    ("macbook-air-m2", "MacBook Air M2 (16GB)", 16, 0.75),
    ("macbook-pro-m4-max", "MacBook Pro M4 Max (64GB)", 64, 0.75),
    ("mac-studio-m3-ultra", "Mac Studio M3 Ultra (512GB)", 512, 0.75),
    ("system-ram-32gb", "32GB system RAM (CPU inference)", 32, 1.0),
    ("system-ram-64gb", "64GB system RAM (CPU inference)", 64, 1.0),
    ("system-ram-128gb", "128GB system RAM (CPU inference)", 128, 1.0),
]

def fits(m, cap_gb):
    """Best (largest) quant that comfortably fits cap; returns (quant, need, size) or None."""
    gg = clean_quants(m["ggufs"])
    best = None
    for q, s in gg.items():
        n = need_gb(s, m["arch"])
        if n <= cap_gb * 0.92 and (best is None or s > best[2]):
            best = (q, n, s)
    return best

def rank_for(models, cap):
    ranked = []
    for m in models:
        f = fits(m, cap)
        if f:
            p = params_b(m) or 0
            ranked.append((p, m, f))
    ranked.sort(key=lambda x: (-x[0], -x[1]["downloads"]))
    seen, top = set(), []
    for p, m, f in ranked:
        key = m["name"].lower().replace("-", "").replace("_", "")[:24]
        if key in seen:
            continue
        seen.add(key)
        top.append((p, m, f))
        if len(top) >= 12:
            break
    return top

def build_tier_pages(models, OUT):
    import os, datetime
    today = datetime.date.today().isoformat()
    urls, md_lines = [], []
    targets = [(f"best-llm-for-{t}gb-vram", f"{t}GB VRAM", f"{t}GB VRAM", t) for t in TIERS]
    targets += [(f"best-llm-for-{g[0]}", g[1], g[1], round(g[2] * g[3])) for g in GPUS]
    for slug, label, hlabel, cap in targets:
        top = rank_for(models, cap)
        if not top:
            continue
        is_mac = "mac" in slug
        rows = "".join(
            f"<tr><td><a href='/{m['slug']}/'>{E(m['name'])}</a></td>"
            f"<td class='n'>{p:.0f}B</td><td><b>{E(q)}</b></td>"
            f"<td class='n'>{fmt_gb(n)}</td><td class='n'>{m['downloads']//1000}k</td></tr>"
            for p, m, (q, n, s) in top)
        body = f"""<div class="crumb"><a href="/">All models</a> › Best for {E(hlabel)}</div>
<h1>Best LLMs for {E(hlabel)} in 2026 — ranked by measured file sizes</h1>
<p class="sub">Every pick below <b>comfortably fits {E(label)}</b> at the listed quant with 8K context.
Ranking = largest model (more capable) that still fits, ties broken by real download counts.
Sizes are measured GGUF files from Hugging Face, updated daily — not formula estimates.</p>
<table><thead><tr><th>Model</th><th style="text-align:right">Params</th><th>Best quant that fits</th><th style="text-align:right">VRAM needed</th><th style="text-align:right">Downloads</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">Leaves ~8% headroom for fragmentation. Long contexts (>8K) grow the KV cache — open the model page for exact math.{" On Macs the budget is ~75% of unified memory (macOS default GPU limit — adjustable via sysctl iogpu.wired_limit_mb)." if is_mac else ""}</p>
<div class="ad-slot"></div>
<h2>How we pick</h2>
<p>A model qualifies when its <i>measured</i> GGUF file plus KV cache plus runtime overhead stays under {cap}GB x 0.92.
We choose the largest such quant (bigger quant = less degradation), then rank models by parameter count —
at {E(label)} the best model you can run is almost always the largest one that still fits.
MoE models count their <b>total</b> size (all experts live in memory), not just active params.</p>
<h2>By GPU</h2>
<div class="grid">{''.join(f'<a href="/best-llm-for-{g[0]}/">{E(g[1])}<small>best models that fit</small></a>' for g in GPUS)}</div>
<h2>By VRAM tier</h2>
<div class="grid">{''.join(f'<a href="/best-llm-for-{t}gb-vram/">{t}GB VRAM<small>ranked picks</small></a>' for t in TIERS)}</div>"""
        jsonld = {"@context": "https://schema.org", "@type": "ItemList",
                  "name": f"Best LLMs for {label} (2026)",
                  "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                       "name": m["name"], "url": f"{BASE}/{m['slug']}/"}
                                      for i, (p, m, f) in enumerate(top)]}
        html_out = page(f"{slug}/index.html",
                        f"Best LLM for {label} (2026) — {top[0][1]['name']} & {len(top)-1} more that actually fit",
                        f"Ranked list of LLMs that comfortably fit {label} at 8K context, by measured GGUF file sizes. Updated daily from Hugging Face.",
                        body, f"{slug}/", jsonld)
        d = os.path.join(OUT, slug); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html_out)
        md = [f"# Best LLMs for {label} (measured, {today})", "",
              f"Page: {BASE}/{slug}/", "", "| Model | Params | Best quant | VRAM needed | Downloads |", "|---|---|---|---|---|"]
        md += [f"| {m['name']} | {p:.0f}B | {q} | {fmt_gb(n)} | {m['downloads']//1000}k |" for p, m, (q, n, s) in top]
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(md) + "\n")
        urls.append(f"{BASE}/{slug}/")
        md_lines.append(f"- [Best LLM for {label}]({BASE}/{slug}/index.md): top pick {top[0][1]['name']} at {top[0][2][0]}")
    return urls, md_lines

def build_picker(models, OUT):
    import os
    # per model: quant -> need (rounded), name, slug, params
    data = []
    for m in models:
        gg = clean_quants(m["ggufs"])
        if not gg:
            continue
        data.append({"n": m["name"], "s": m["slug"], "d": m["downloads"],
                     "q": {q: round(need_gb(s, m["arch"]), 1) for q, s in gg.items()}})
    body = """<h1>What LLM can I run? Pick your VRAM / RAM</h1>
<p class="sub">Type your GPU VRAM (or usable system RAM for CPU inference). Every model that fits is listed with its
best quant — computed from measured GGUF file sizes, 8K context, ~8% headroom. Data refreshes daily from Hugging Face.</p>
<div class="calc"><label style="color:var(--mut);font-size:13px">Your memory, GB:</label>
<input type="number" id="v" min="1" max="4096" placeholder="e.g. 24" oninput="go()">
<div id="out" style="margin-top:12px"></div></div>
<div class="ad-slot"></div>
<h2>Popular tiers</h2>
<div class="grid">TIERS_HTML</div>
<script>
const M=DATA_JSON;
function go(){const v=+document.getElementById('v').value;const o=document.getElementById('out');if(!v){o.innerHTML='';return;}
const hits=[];for(const m of M){let best=null;for(const[q,n]of Object.entries(m.q)){if(n<=v*0.92&&(!best||m.q[best[0]]<n))best=[q,n];}
if(best)hits.push({m,q:best[0],n:best[1],size:Object.values(m.q).reduce((a,b)=>a+b,0)});}
hits.sort((a,b)=>b.size-a.size||b.m.d-a.m.d);
o.innerHTML=hits.length?'<table><thead><tr><th>Model</th><th>Best quant</th><th style="text-align:right">Needs</th></tr></thead><tbody>'+
hits.slice(0,25).map(h=>`<tr><td><a href="/${h.m.s}/">${h.m.n}</a></td><td><b>${h.q}</b></td><td class="n">${h.n} GB</td></tr>`).join('')+'</tbody></table>'
+(hits.length>25?`<p class="note">+${hits.length-25} more models fit.</p>`:'')
:'<span class="pill no">NO</span> nothing fits in '+v+' GB — smallest model needs '+Math.min(...M.flatMap(m=>Object.values(m.q))).toFixed(1)+' GB.';}
</script>"""
    tiers_html = "".join(f'<a href="/best-llm-for-{t}gb-vram/">{t}GB VRAM<small>ranked picks</small></a>' for t in TIERS)
    body = body.replace("TIERS_HTML", tiers_html).replace("DATA_JSON", json.dumps(data, ensure_ascii=False))
    html_out = page("what-llm-can-i-run/index.html",
                    "What LLM Can I Run? VRAM Calculator for Every Model (2026)",
                    "Type your VRAM or RAM — instantly see every LLM that fits, with the best quant. Measured GGUF sizes from Hugging Face, updated daily.",
                    body, "what-llm-can-i-run/")
    d = os.path.join(OUT, "what-llm-can-i-run"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html_out)
    return [f"{BASE}/what-llm-can-i-run/"], ["- [What LLM can I run?]({}/what-llm-can-i-run/): interactive VRAM/RAM picker over all catalogued models".format(BASE)]
