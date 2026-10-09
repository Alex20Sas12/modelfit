# -*- coding: utf-8 -*-
"""tiers.py — programmatic SEO pages: "Best LLM for XGB VRAM" + interactive picker.
Called from build.py main(). Returns (urls, md_lines) to fold into sitemap/llms.txt."""
import json, html, re, statistics
from build import E, BASE, clean_quants, need_gb, fmt_gb, params_b, page, CLOUD_CTA, make_og

TIERS = [4, 8, 12, 16, 24, 32, 48, 64, 96]  # 4GB добавлен 08.10: GH-лид Rudra1725#1 + hot-запрос laptop GPUs
JUNK = re.compile(r"(uncensored|abliterated|heretic|obliterated|nsfw|erp|roleplay|jailbr)", re.I)
OFFICIAL = ("unsloth", "bartowski", "lmstudio-community", "ggml-org")

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

def _family(m):
    """Dedup key: first two name tokens, e.g. 'Qwen3.8-27B-Heretic...' -> 'qwen3.827b'."""
    toks = re.split(r"[\s\-_.]+", m["name"].lower())
    return "".join(toks[:2])[:24]

def rank_for(models, cap):
    """Clean ranking: no junk-named uploads, official repos win ties, one pick per model family."""
    ranked = []
    for m in models:
        if JUNK.search(m["name"]):
            continue
        f = fits(m, cap)
        if f:
            p = params_b(m) or 0
            off = 1 if m["id"].lower().split("/")[0] in OFFICIAL else 0
            ranked.append((p, off, m, f))
    ranked.sort(key=lambda x: (-x[0], -x[1], -x[2]["downloads"]))
    seen, top = set(), []
    for p, off, m, f in ranked:
        key = _family(m)
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
                        body, f"{slug}/", jsonld, og_image=f"{slug}/og.png")
        d = os.path.join(OUT, slug); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html_out)
        make_og(os.path.join(d, "og.png"), f"Best LLM for {label}",
                f"#1: {top[0][1]['name']} ({top[0][2][0]})", "Measured GGUF sizes, updated daily")
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
    # static 24GB table (no-JS + crawler-visible; 24GB = biggest search tier)
    static_rows = "".join(
        f"<tr><td><a href='/{m['slug']}/'>{E(m['name'])}</a></td><td><b>{E(q)}</b></td>"
        f"<td class='n'>{fmt_gb(n)}</td><td class='n'>{p:.0f}B</td></tr>"
        for p, m, (q, n, s) in rank_for(models, 24))
    gpu_opts = "".join(f'<option value="{g[2]*g[3]:.0f}">{E(g[1])}</option>' for g in GPUS)
    body = """<h1>What LLM can I run? Pick your GPU / VRAM / RAM</h1>
<p class="sub">Choose your hardware below. Every model that fits is listed with its
best quant — computed from measured GGUF file sizes, 8K context, ~8% headroom. Data refreshes daily from Hugging Face.</p>
<div class="calc"><label style="color:var(--mut);font-size:13px">Pick your hardware (or type memory in GB):</label>
<select id="pick" onchange="document.getElementById('v').value=this.value;go()"><option value="">— choose GPU / Mac / RAM —</option>GPU_OPTS</select>
<div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap">
<input type="number" id="v" min="1" max="4096" placeholder="e.g. 24 GB" oninput="go()" style="flex:1;min-width:140px">
<select id="ctx" onchange="go()" style="flex:1;min-width:140px"><option value="1">8K context (standard)</option><option value="4">32K context (+KV)</option><option value="15">128K context (+KV)</option></select></div>
<div id="out" style="margin-top:12px"></div></div>
<div id="cloudcta" style="display:none">CLOUD_CTA</div>
<h2>Best LLMs for a 24GB GPU (RTX 3090 / 4090) — static list</h2>
<table><thead><tr><th>Model</th><th>Best quant that fits</th><th style="text-align:right">VRAM needed</th><th style="text-align:right">Params</th></tr></thead>
<tbody>STATIC_ROWS</tbody></table>
<p class="note">Full ranked list: <a href="/best-llm-for-24gb-vram/">best LLM for 24GB VRAM</a>. Other tiers: <a href="/best-llm-for-8gb-vram/">8GB</a> · <a href="/best-llm-for-12gb-vram/">12GB</a> · <a href="/best-llm-for-16gb-vram/">16GB</a> · <a href="/best-llm-for-32gb-vram/">32GB</a>.</p>
<div class="ad-slot"></div>
<h2>Popular tiers</h2>
<div class="grid">TIERS_HTML</div>
<script>
const M=DATA_JSON;
function go(){const v=+document.getElementById('v').value;const k=+document.getElementById('ctx').value;const o=document.getElementById('out');const cta=document.getElementById('cloudcta');
if(!v){o.innerHTML='';cta.style.display='none';return;}
const hits=[];for(const m of M){let best=null;for(const[q,n]of Object.entries(m.q)){const nn=n*k;if(nn<=v*0.92&&(!best||best[1]<nn))best=[q,nn];}
if(best)hits.push({m,q:best[0],n:Math.round(best[1]*10)/10,size:Object.values(m.q).reduce((a,b)=>a+b,0)});}
hits.sort((a,b)=>b.size-a.size||b.m.d-a.m.d);
cta.style.display=hits.length?'none':'block';
o.innerHTML=hits.length?'<table><thead><tr><th>Model</th><th>Best quant</th><th style="text-align:right">Needs</th></tr></thead><tbody>'+
hits.slice(0,25).map(h=>`<tr><td><a href="/${h.m.s}/">${h.m.n}</a></td><td><b>${h.q}</b></td><td class="n">${h.n} GB</td></tr>`).join('')+'</tbody></table>'
+(hits.length>25?`<p class="note">+${hits.length-25} more models fit.</p>`:'')
:'<span class="pill no">NO</span> nothing fits in '+v+' GB — smallest model needs '+Math.min(...M.flatMap(m=>Object.values(m.q))).toFixed(1)+' GB. Rent a bigger GPU below.';}
</script>"""
    tiers_html = "".join(f'<a href="/best-llm-for-{t}gb-vram/">{t}GB VRAM<small>ranked picks</small></a>' for t in TIERS)
    body = (body.replace("TIERS_HTML", tiers_html).replace("DATA_JSON", json.dumps(data, ensure_ascii=False))
            .replace("GPU_OPTS", gpu_opts).replace("STATIC_ROWS", static_rows).replace("CLOUD_CTA", CLOUD_CTA))
    html_out = page("what-llm-can-i-run/index.html",
                    "What LLM Can I Run? VRAM Calculator for Every Model (2026)",
                    "Type your VRAM or RAM — instantly see every LLM that fits, with the best quant. Measured GGUF sizes from Hugging Face, updated daily.",
                    body, "what-llm-can-i-run/")
    d = os.path.join(OUT, "what-llm-can-i-run"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html_out)
    return [f"{BASE}/what-llm-can-i-run/"], ["- [What LLM can I run?]({}/what-llm-can-i-run/): interactive VRAM/RAM picker over all catalogued models".format(BASE)]

def build_buy_page(models, OUT):
    """Reverse picker: choose a model → cheapest hardware that runs it (BACKLOG P1.7)."""
    import os
    from build import USED_PRICES
    # per model: need at recommended quant
    data = []
    for m in models:
        gg = clean_quants(m["ggufs"])
        if not gg:
            continue
        order = sorted(gg.items(), key=lambda x: x[1])
        med = statistics.median(s for _, s in order)
        rec_q, rec_s = min(order, key=lambda x: abs(x[1] - med * 0.55)) if len(order) > 3 else order[len(order)//2]
        data.append({"n": m["name"], "s": m["slug"], "q": rec_q,
                     "need": round(need_gb(rec_s, m["arch"]), 1),
                     "min": round(need_gb(order[0][1], m["arch"]), 1)})
    prices = [[lb, v, f, pr] for lb, v, f, pr in USED_PRICES]
    cards = "".join(f'<option value="{gb}GB VRAM">{E(lb)} — ~${pr}</option>'
                    for lb, v, f, pr in prices for gb in [round(v * f * 0.92)])
    body = """<h1>Which GPU should I buy to run LLMs locally? (2026)</h1>
<p class="sub">Pick any model — we show the <b>cheapest hardware that runs it</b>, from measured GGUF sizes at the
recommended quant. Prices are street/used-market approximations (USD), refreshed monthly.</p>
<div class="calc"><label style="color:var(--mut);font-size:13px">Or start from your budget — see the best model it buys:</label>
<select id="card" onchange="byCard()"><option value="">— choose a card —</option>CARDS</select>
<div id="cardout" style="margin-top:12px"></div></div>
<div class="calc"><label style="color:var(--mut);font-size:13px">…or pick the model you want to run:</label>
<input id="mq" placeholder="Filter models… (e.g. Qwen, Kimi, Gemma)" oninput="flt()" list="mlist">
<datalist id="mlist">DATALIST</datalist>
<div id="mout" style="margin-top:12px"></div></div>
<h2>Cheapest hardware by memory tier (static table)</h2>
<table><thead><tr><th>Hardware</th><th style="text-align:right">Usable VRAM</th><th style="text-align:right">Street price</th><th>Runs (recommended quant, 8K)</th></tr></thead>
<tbody>STATIC</tbody></table>
<p class="note">Usable = physical × 0.92 (fragmentation headroom); Macs × 0.75 (macOS wired limit).
Two cheap 3090s (48GB pooled, ~$1300) beat one 4090 for models needing 25-48GB if your board has 2× x8 slots.</p>
<div class="ad-slot"></div>
CLOUD
<script>
const M=DATA_JSON;const P=PRICE_JSON;
function cheapest(need){let best=null;for(const[lb,v,f,pr]of P){if(need<=v*f*0.92&&(!best||pr<best[1]))best=[lb,pr];}return best;}
function byCard(){const v=parseFloat(document.getElementById('card').value)||0;const o=document.getElementById('cardout');if(!v){o.innerHTML='';return;}
const hits=M.filter(m=>m.need<=v).sort((a,b)=>b.need-a.need||b.n.localeCompare(a.n));
o.innerHTML=hits.length?'<table><thead><tr><th>Best models for this card</th><th>Quant</th><th style="text-align:right">Needs</th></tr></thead><tbody>'+
hits.slice(0,12).map(h=>`<tr><td><a href="/${h.s}/">${h.n}</a></td><td><b>${h.q}</b></td><td class="n">${h.need} GB</td></tr>`).join('')+'</tbody></table>'
:'<span class="pill no">NO</span> nothing fits at the recommended quant — smallest needs '+Math.min(...M.map(m=>m.need)).toFixed(1)+' GB.';}
function flt(){const q=document.getElementById('mq').value.toLowerCase();const o=document.getElementById('mout');
const hits=M.filter(m=>m.n.toLowerCase().includes(q)).slice(0,10);
if(!q){o.innerHTML='';return;}
o.innerHTML=hits.map(m=>{const c=cheapest(m.need);return `<div style="padding:6px 0;border-bottom:1px solid var(--line)"><a href="/${m.s}/">${m.n}</a> — ${m.q} needs <b>${m.need} GB</b>: `+(c?`cheapest = <b>${c[0]}</b> (~$${c[1]})`:'multi-GPU/server or CPU offload only')+'</div>';}).join('')||'no match';}
</script>"""
    # static per-card examples (crawler-visible): top-2 models each card runs at rec quant
    rows2 = ""
    for lb, v, f, pr in prices:
        cap = v * f * 0.92
        ex = [m["name"] for m in sorted(models, key=lambda x: -x["downloads"])
              if clean_quants(m["ggufs"]) and need_gb(sorted(clean_quants(m["ggufs"]).values(), key=lambda s: s)[len(clean_quants(m["ggufs"]))//2], m["arch"]) <= cap][:2]
        rows2 += f"<tr><td>{E(lb)}</td><td class='n'>{cap:.0f} GB</td><td class='n'>~${pr}</td><td>{E(', '.join(ex) or 'small models only')}</td></tr>"
    body = (body.replace("CARDS", cards).replace("STATIC", rows2).replace("CLOUD", CLOUD_CTA)
            .replace("DATA_JSON", json.dumps(data, ensure_ascii=False))
            .replace("PRICE_JSON", json.dumps(prices))
            .replace("DATALIST", "".join(f'<option value="{E(m["n"])}">' for m in data)))
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is the cheapest GPU that runs LLMs?",
             "acceptedAnswer": {"@type": "Answer", "text": "A used RTX 3060 12GB (~$250) runs 8B models at Q8 and 14B at Q4. The used RTX 3090 24GB (~$650) is the community value king: it runs 27-32B models at Q4 and decodes within ~8% of a $1600 RTX 4090."}},
            {"@type": "Question", "name": "Should I buy a GPU or rent one for LLMs?",
             "acceptedAnswer": {"@type": "Answer", "text": "Buy if you run models most days (a used 3090 pays for itself vs ~$0.35/h cloud rentals after ~2000 GPU-hours). Rent if you need big models occasionally or want to try before buying."}},
        ]},
    ]}
    html_out = page("which-gpu-should-i-buy/index.html",
                    "Which GPU Should I Buy to Run LLMs? Cheapest Picks by Model (2026)",
                    "Pick a model — see the cheapest GPU that runs it, from measured GGUF sizes. Used-market street prices, multi-GPU tips and buy-vs-rent math.",
                    body, "which-gpu-should-i-buy/", jsonld)
    d = os.path.join(OUT, "which-gpu-should-i-buy"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html_out)
    make_og(os.path.join(d, "og.png"), "Which GPU should I buy?",
            "Cheapest hardware per model", "Measured GGUF sizes, street prices")
    return [f"{BASE}/which-gpu-should-i-buy/"], ["- [Which GPU should I buy?]({}/which-gpu-should-i-buy/): reverse picker, model → cheapest hardware".format(BASE)]
