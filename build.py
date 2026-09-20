# -*- coding: utf-8 -*-
"""build.py — generate ModelFit static site from models.json. Run: python build.py
VRAM model: weights (measured GGUF bytes) + overhead. If config.json gave arch,
KV cache is computed exactly (GQA formula); otherwise flat +20%/min 1.5 GB rule.
"""
import json, os, html, re, statistics, urllib.parse
from PIL import Image, ImageDraw, ImageFont

def _font(size):
    for p in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def make_og(path, title, line2, line3):
    """1200x630 social-preview card (dark, brand-green)."""
    img = Image.new("RGB", (1200, 630), "#0d1117")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1200, 8], fill="#3fb950")
    d.text((60, 40), "ModelFit", font=_font(44), fill="#3fb950")
    d.text((60, 100), "Measured VRAM requirements — updated daily from Hugging Face", font=_font(26), fill="#8b98a9")
    # wrap title
    f_t = _font(56)
    words, lines, cur = title.split(), [], ""
    for w in words:
        if d.textlength(cur + " " + w, font=f_t) < 1060:
            cur += (" " if cur else "") + w
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    y = 220
    for ln in lines[:2]:
        d.text((60, y), ln, font=f_t, fill="#e6edf3"); y += 68
    d.text((60, 420), line2, font=_font(34), fill="#e6edf3")
    d.text((60, 475), line3, font=_font(30), fill="#8b98a9")
    d.text((60, 560), "modelfit-eight.vercel.app — updated daily from Hugging Face", font=_font(24), fill="#3fb950")
    img.save(path, "PNG")

BADGE = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20"><rect width="{split}" height="20" fill="#555"/><rect x="{split}" width="{rest}" height="20" fill="#3fb950"/><text x="{tx1}" y="14" fill="#fff" font-family="Verdana" font-size="11">ModelFit</text><text x="{tx2}" y="14" fill="#fff" font-family="Verdana" font-size="11">{label}</text></svg>"""

def make_badge(path, label):
    w1, w2 = 58, 8 * len(label) + 20
    svg = BADGE.format(w=w1 + w2, split=w1, rest=w2, tx1=6, tx2=w1 + 8, label=html.escape(label))
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site")
os.makedirs(OUT, exist_ok=True)
E = html.escape
BASE = os.environ.get("MF_BASE", "https://modelfit-eight.vercel.app")  # ponytail: replace with paid domain when first real money

# Share buttons: JS fills current URL+title — one static template for all pages
SHARE_TMPL = """<span>Share this page:</span>
<a href="#" onclick="window.open('https://twitter.com/intent/tweet?text='+encodeURIComponent(document.title)+' '+encodeURIComponent(location.href),'_blank','width=600,height=400');return false">𝕏 Post</a>
<a href="#" onclick="window.open('https://www.reddit.com/submit?url='+encodeURIComponent(location.href)+'&title='+encodeURIComponent(document.title),'_blank','width=600,height=400');return false">Reddit</a>
<a href="#" onclick="window.open('https://news.ycombinator.com/submitlink?u='+encodeURIComponent(location.href)+'&t='+encodeURIComponent(document.title),'_blank','width=600,height=400');return false">Hacker News</a>
<a href="#" onclick="window.open('https://t.me/share/url?url='+encodeURIComponent(location.href)+'&text='+encodeURIComponent(document.title),'_blank','width=600,height=400');return false">Telegram</a>
<a href="#" onclick="window.open('https://api.whatsapp.com/send?text='+encodeURIComponent(document.title+' '+location.href),'_blank','width=600,height=400');return false">WhatsApp</a>
<a href="#" onclick="if(navigator.share){navigator.share({title:document.title,url:location.href})};return false">More…</a>"""

GPUS = [  # (name, vram_gb)
    ("RTX 3060 12GB", 12), ("RTX 4060 Ti 16GB", 16), ("RTX 3090 24GB", 24), ("RTX 4090 24GB", 24),
    ("RTX 5090 32GB", 32), ("RTX PRO 6000 96GB", 96), ("Mac 16GB unified", 16), ("Mac 32GB unified", 32),
    ("Mac 64GB unified", 64), ("Mac 128GB unified", 128), ("Mac 256GB unified", 256), ("Mac 512GB unified", 512),
    ("32GB system RAM (CPU)", 32), ("64GB system RAM (CPU)", 64), ("128GB system RAM (CPU)", 128),
    ("256GB system RAM (CPU)", 256), ("1TB server RAM (CPU)", 1024), ("2TB server RAM (CPU)", 2048),
]

QUANT_BPW = {  # fallback bits/weight only if no measured file for that tier
    "Q8_0": 8.5, "Q6_K": 6.6, "Q5_K_M": 5.7, "Q4_K_M": 4.9, "Q4_K_S": 4.6, "Q3_K_M": 3.9, "Q2_K": 3.4,
}

def clean_quants(gg):
    """Drop stubs (mmproj/vision files ~<1% of median) and -mtp/-multilingual variants
    when the plain quant exists (same model, auxiliary-module variants only)."""
    if not gg:
        return {}
    med = statistics.median(gg.values())
    gg = {q: s for q, s in gg.items() if s >= med * 0.05}
    plain = {q.split("-")[0] for q in gg}
    return {q: s for q, s in gg.items()
            if "-" not in q or q.split("-")[0] not in plain or not any(v in q.lower() for v in ("mtp", "multilingual", "mmproj", "vision"))}

def kv_cache_gb(arch, ctx):
    """Exact GQA KV: 2 * layers * kv_heads * head_dim * ctx * 2 bytes."""
    L, kvh, hd = arch.get("num_hidden_layers"), arch.get("num_key_value_heads"), arch.get("head_dim")
    if not (L and kvh and hd):
        return None
    return 2 * L * kvh * hd * ctx * 2 / 1e9

def params_b(m):
    if m.get("params"):
        return m["params"] / 1e9
    gg = clean_quants(m["ggufs"])
    big = [s for q, s in gg.items() if q in ("F16", "BF16")]
    if big:
        return max(big) / 2 / 1e9
    return None

def need_gb(weight_bytes, arch):
    """Realistic VRAM/RAM need for 8K context."""
    w = weight_bytes / 1e9
    kv = kv_cache_gb(arch, 8192)
    if kv is None:
        return w * 1.2 + 1.5  # flat heuristic
    return w + kv + max(1.0, w * 0.08)

def fmt_gb(x):
    return f"{x/1000:.2f} TB" if x >= 1000 else f"{x:.1f} GB"

def verdicts(need):
    out = []
    for name, v in GPUS:
        ok = need <= v * 0.92
        out.append((name, v, "yes" if ok else ("tight" if need <= v else "no")))
    return out

def page(rel, title, desc, body, canonical, jsonld=None, og_image="og.png"):
    ad = """<script async="async" data-cfasync="false" src="https://pl31410879.profitableratecpmnetwork.com/2376e478c4be448f43fb6b09e2fff78d/invoke.js"></script> <div id="container-2376e478c4be448f43fb6b09e2fff78d"></div>"""
    body = body.replace('<div class="ad-slot"></div>', f'<div class="ad-slot">{ad}</div>')
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    og_img = f'<meta property="og:image" content="{BASE}/{og_image}"><meta name="twitter:image" content="{BASE}/{og_image}">' if og_image else ""
    share = f'<div class="share">{SHARE_TMPL}</div>'
    if ad not in body:  # index/tier pages have no ad-slot div — append at the end
        body = body + f'<div class="ad-slot">{ad}</div>'
    body = body + share
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<meta name="google-site-verification" content="dHzB4J-n1_k8XEQgWt9VE2OCG2gO8yiE9adtZGUcN-s">
<meta name="msvalidate.01" content="988EBC0B59488A1F91B3E7D9658B65C3">
<link rel="canonical" href="{BASE}/{canonical}">
<meta property="og:type" content="website"><meta property="og:url" content="{BASE}/{canonical}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
{og_img}
{ld}
<style>
:root{{--bg:#0d1117;--card:#161b26;--tx:#e6edf3;--mut:#8b98a9;--acc:#3fb950;--warn:#d29922;--bad:#f85149;--line:#252d3a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 system-ui,Segoe UI,Roboto,sans-serif}}
a{{color:var(--acc)}}.wrap{{max-width:920px;margin:0 auto;padding:0 20px}}
header{{border-bottom:1px solid var(--line);padding:14px 0;background:var(--card)}}
header .logo{{font-weight:800;font-size:19px;color:var(--tx);text-decoration:none}}header .logo span{{color:var(--acc)}}
main{{padding:26px 0 60px}}h1{{font-size:26px;margin:0 0 8px}}.sub{{color:var(--mut);margin:0 0 22px}}
table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:15px}}
td,th{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}}
.pill{{display:inline-block;border-radius:999px;padding:1px 10px;font-size:13px;font-weight:600}}
.yes{{background:#12331c;color:var(--acc)}}.tight{{background:#3a2d0e;color:var(--warn)}}.no{{background:#3a1416;color:var(--bad)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin:14px 0}}
.grid a{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;text-decoration:none;color:var(--tx);font-weight:600}}
.grid a:hover{{border-color:var(--acc)}}.grid a small{{display:block;color:var(--mut);font-weight:400;margin-top:3px}}
.note{{color:var(--mut);font-size:14px}}input,select{{width:100%;background:var(--bg);border:1px solid var(--line);color:var(--tx);border-radius:8px;padding:10px;font-size:16px}}
.calc{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:18px 0}}
footer{{border-top:1px solid var(--line);color:var(--mut);font-size:13px;padding:20px 0;text-align:center}}
details{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:8px 0}}details summary{{cursor:pointer;font-weight:600}}
.crumb{{font-size:13px;color:var(--mut);margin-bottom:10px}}.crumb a{{color:var(--mut)}}
.ad-slot{{min-height:90px;margin:18px 0}}
.share{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:26px 0 6px}}
.share span{{color:var(--mut);font-size:14px}}
.share a{{display:inline-flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:7px 13px;text-decoration:none;color:var(--tx);font-size:14px;font-weight:600}}
.share a:hover{{border-color:var(--acc)}}
</style></head><body>
<header><div class="wrap"><a class="logo" href="/">Model<span>Fit</span></a>
<span class="note" style="margin-left:10px">Can I run this LLM? Real file sizes, live from Hugging Face.</span></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">ModelFit — every number is measured from real GGUF files via the Hugging Face API, updated daily. Not affiliated with Hugging Face.<br>Data: Hugging Face API. Sizes: community GGUF uploads (unsloth, bartowski, lmstudio-community).</div></footer>
<script src="https://pl31411352.profitableratecpmnetwork.com/9f/5b/f6/9f5bf63f2ad6bcc4b9a12888c7acf0bc.js"></script>
</body></html>"""

def related(m, all_models, n=8):
    """ponytail: top-downloads models excluding self; keyword-based clusters add when pages >200."""
    return [o for o in all_models if o["slug"] != m["slug"]][:n]

def model_page(m, all_models):
    gg = clean_quants(m["ggufs"])
    order = sorted(gg.items(), key=lambda x: x[1])
    arch = m["arch"]
    name = m["name"]
    p = params_b(m)
    kv_exact = kv_cache_gb(arch, 8192) is not None
    rows = []
    for q, s in order:
        need = need_gb(s, arch)
        v = verdicts(need)
        best = [n for n, gb, st in v if st == "yes"][:1]
        verdict = best[0] if best else ("borderline" if any(st == "tight" for _, _, st in v) else "server-grade")
        cls = "yes" if best else ("tight" if verdict != "server-grade" else "no")
        rows.append(f"<tr><td><b>{E(q)}</b></td><td class='n'>{fmt_gb(s/1e9)}</td>"
                    f"<td class='n'>{fmt_gb(need)}</td><td><span class='pill {cls}'>{E(verdict)}</span></td></tr>")
    # GPU matrix for the recommended quant (smallest need <= 40% of median = sweet spot Q4-ish)
    med = statistics.median(s for _, s in order)
    rec_q, rec_s = min(order, key=lambda x: abs(x[1] - med * 0.55)) if len(order) > 3 else order[len(order)//2]
    rec_need = need_gb(rec_s, arch)
    gpu_rows = "".join(
        f"<tr><td>{E(n)}</td><td class='n'>{gb} GB</td><td><span class='pill {st}'>{'RUNS' if st=='yes' else ('tight' if st=='tight' else 'no')}</span></td></tr>"
        for n, gb, st in verdicts(rec_need))
    ptxt = f"~{p:.1f}B parameters" if p else ""
    kvnote = ("KV cache computed exactly from the model config (GQA formula, 8K context)."
              if kv_exact else
              "KV cache uses a flat +20% context/overhead rule because this repo does not publish its config; "
              "exact numbers may differ for long contexts.")
    fit24 = [q for q, s in order if need_gb(s, arch) <= 24]
    a24 = (f"Yes — at {rec_q} ({fmt_gb(rec_need)})" if rec_need <= 24 else
           f"Not at {rec_q} ({fmt_gb(rec_need)})") + ". "
    if fit24:
        a24 += f"Quants that fit 24GB: {', '.join(fit24)}."
    else:
        a24 += f"Nothing fits 24GB — the smallest build needs {fmt_gb(need_gb(order[0][1], arch))}. Use the hosted API or a smaller model."
    faqs = [
        (f"How much VRAM does {name} need?",
         f"The measured answer: {fmt_gb(rec_need)} at the {rec_q} quant with 8K context. The smallest published build needs {fmt_gb(need_gb(order[0][1], arch))}; the lossless (F16/BF16) build needs {fmt_gb(need_gb(order[-1][1], arch))}. These are real GGUF file sizes from Hugging Face, not formula estimates."),
        (f"Can I run {name} on a 24GB GPU (RTX 3090/4090)?", a24),
        (f"Can I run {name} on CPU with system RAM?",
         f"Yes, if your usable RAM is at least the file size. At {rec_q} you need ~{fmt_gb(rec_need)} of RAM. CPU generation is memory-bandwidth-bound: expect single-digit tok/s for large MoE models, 10-30 tok/s for small active params, and below 1 tok/s when experts page from disk."),
        (f"Why do VRAM numbers for {name} differ between sites?",
         "Most sites compute weights from a formula (params x bits/8). ModelFit uses the actual GGUF file sizes published on Hugging Face, which include the embedding table, unquantized tensors, and container overhead — so our numbers reflect what you really download and load."),
    ]
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "All models", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": name, "item": f"{BASE}/{m['slug']}/"}]},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
            {"@type": "Dataset", "name": f"{name} GGUF sizes and VRAM requirements",
             "description": f"Measured GGUF file sizes and real VRAM/RAM requirements for {name}, updated daily from the Hugging Face API.",
             "url": f"{BASE}/{m['slug']}/", "dateModified": m.get("lastModified") or "",
             "license": "https://creativecommons.org/licenses/by/4.0/",
             "creator": {"@type": "Organization", "name": "ModelFit", "url": BASE}},
        ],
    }
    faq_html = "".join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in faqs)
    body = f"""<div class="crumb"><a href="/">All models</a> › {E(name)}</div>
<h1>{E(name)} requirements — can you run it?</h1>
<p class="sub">{E(ptxt)} · {len(gg)} quantizations measured · updated {E(m['lastModified'] or 'daily')} · source: <a href="https://huggingface.co/{E(m['id'])}" rel="nofollow">{E(m['id'])}</a></p>
<div class="calc"><label style="color:var(--mut);font-size:13px">Your VRAM (GPU) or usable RAM (CPU), GB — verdicts update live:</label>
<input type="number" id="myvram" min="1" max="4096" placeholder="e.g. 24" oninput="fit()">
<div id="myverdict" style="margin-top:10px"></div></div>
<h2>Every quantization: real file size vs what you actually need</h2>
<table><thead><tr><th>Quant</th><th style="text-align:right">File (measured)</th><th style="text-align:right">VRAM/RAM needed (8K ctx)</th><th>Runs on (first fit)</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="note">{E(kvnote)} MoE models keep all experts in memory — total size counts, not just active params.</p>
<h2>Can I run {E(name)} on my GPU? ({E(rec_q)} recommended quant)</h2>
<table><thead><tr><th>Hardware</th><th style="text-align:right">Memory</th><th>Verdict</th></tr></thead><tbody>{gpu_rows}</tbody></table>
<h2>How much VRAM does {E(name)} need?</h2>
<p>The honest answer: <b>{fmt_gb(rec_need)}</b> at the {E(rec_q)} quant with 8K context — that is the measured
file size ({fmt_gb(rec_s/1e9)}) plus KV cache and runtime overhead. The smallest published build needs
{fmt_gb(need_gb(order[0][1], arch))}; the lossless one needs {fmt_gb(need_gb(order[-1][1], arch))}.</p>
<details><summary>Can I run it with CPU offload?</summary><p>Yes, if combined RAM+VRAM ≥ file size — but generation speed
is limited by memory bandwidth. Expect roughly: DDR5 dual channel ~10-30 tok/s for small MoE actives, single digits for big ones,
0.1-1 tok/s when experts page from disk. CPU-only is fine for batch jobs, painful for chat.</p></details>
<details><summary>Why do other sites show different numbers?</summary><p>Most pages compute weights from a formula
(params × bits/8). We use the <b>actual file sizes</b> published in GGUF repos, which include the embedding table,
unquantized tensors, and container overhead — that is why our numbers can differ from a naive calculation.</p></details>
<h2>FAQ</h2>
{faq_html}
<div class="ad-slot"></div>
<h2>More models</h2><div class="grid">{''.join(f'<a href="/{o["slug"]}/">{E(o["name"])}<small>measured requirements</small></a>' for o in related(m, all_models))}</div>
<script>
const DATA={json.dumps({"name":name,"quants":{q:round(need_gb(s,arch),1) for q,s in order}},ensure_ascii=False)};
function fit(){{const v=+document.getElementById('myvram').value;const d=document.getElementById('myverdict');
if(!v){{d.innerHTML='';return;}}
let ok=Object.entries(DATA.quants).filter(([q,n])=>n<=v*0.92).map(([q])=>q);
let tight=Object.entries(DATA.quants).filter(([q,n])=>n>v*0.92&&n<=v).map(([q])=>q);
d.innerHTML=ok.length?'<span class="pill yes">RUNS</span> '+DATA.name+' at: <b>'+ok.join(', ')+'</b>'
+(tight.length?' <span class="pill tight">tight</span> '+tight.join(', '):'')
:'<span class="pill no">NO</span> nothing fits in '+v+' GB — smallest needs '+Math.min(...Object.values(DATA.quants)).toFixed(1)+' GB. Use the API or a smaller model.';}}
</script>"""
    return page(f"{m['slug']}/index.html", f"{name} VRAM Requirements — Can You Run It? | ModelFit",
                f"{name} needs {fmt_gb(rec_need)} VRAM at {rec_q} (measured). Full quant-by-quant table, GPU verdicts for every card from RTX 3060 to Mac Studio 512GB.",
                body, f"{m['slug']}/", jsonld)

def index_page(models):
    cards = []
    for m in models:
        gg = clean_quants(m["ggufs"])
        if not gg:
            continue
        order = sorted(gg.items(), key=lambda x: x[1])
        need = need_gb(order[len(order)//2][1], m["arch"])
        p = params_b(m)
        ptxt = f"{p:.0f}B" if p else "?"
        cards.append(f"<a href=\"/{m['slug']}/\">{E(m['name'])}<small>{E(ptxt)} params · smallest build {fmt_gb(need_gb(order[0][1], m['arch']))} · {m['downloads']//1000}k downloads</small></a>")
    body = f"""<h1>Can I run this LLM? Requirements for every model, measured from real files.</h1>
<p class="sub">{len(models)} models × every quantization × every GPU. Sizes are pulled daily from Hugging Face GGUF repos — not computed from formulas, so what you see is what you download.</p>
<div class="grid" style="margin-bottom:18px">
<a href="/what-llm-can-i-run/" style="border-color:var(--acc)">What LLM can I run?<small>interactive picker — type your VRAM</small></a>
<a href="/best-llm-for-24gb-vram/">Best LLM for 24GB VRAM<small>ranked, measured</small></a>
<a href="/best-llm-for-rtx-4090/">Best LLM for RTX 4090<small>24GB, ranked</small></a>
<a href="/best-llm-for-rtx-3060/">Best LLM for RTX 3060<small>12GB, ranked</small></a>
<a href="/best-llm-for-8gb-vram/">Best LLM for 8GB VRAM<small>ranked, measured</small></a>
</div>
<div class="calc"><input id="q" placeholder="Filter models… (type a name)" oninput="flt()"></div>
<div class="grid" id="cards">{''.join(cards)}</div>
<script>
const CARDS=[...document.querySelectorAll('#cards a')];
function flt(){{const q=document.getElementById('q').value.toLowerCase();
CARDS.forEach(c=>c.style.display=c.textContent.toLowerCase().includes(q)?'':'none');}}
</script>"""
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "ModelFit", "url": BASE + "/",
         "description": "Can I run this LLM? Measured GGUF sizes and VRAM/RAM requirements for every trending local model, updated daily from the Hugging Face API.",
         "publisher": {"@type": "Organization", "name": "ModelFit", "url": BASE}},
        {"@type": "ItemList", "name": "Trending LLMs with measured requirements",
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/{m['slug']}/", "name": m["name"]}
                             for i, m in enumerate(models[:30])]},
    ]}
    return page("index.html", "ModelFit — Can I Run This LLM? VRAM & RAM Requirements (2026)",
                "Measured GGUF sizes and honest VRAM requirements for Kimi K3, Gemma 4, DeepSeek V4, Qwen, GLM and more. Verdicts for every GPU from RTX 3060 to Mac Studio 512GB. Updated daily from Hugging Face.",
                body, "", jsonld)

def main():
    models = json.load(open(os.path.join(HERE, "models.json"), encoding="utf-8"))
    models = [m for m in models if clean_quants(m["ggufs"])]
    models.sort(key=lambda m: -m["downloads"])
    # global OG card (used by index, picker, all model pages)
    make_og(os.path.join(OUT, "og.png"), "Can I run this LLM?",
            f"{len(models)} models measured", "Real GGUF file sizes, not formulas")
    # badges for README linking (growth loop: devs embed badge -> free backlink)
    for label in ["can-i-run", "vram", "gguf", "local-llm"]:
        make_badge(os.path.join(OUT, f"badge-{label}.svg"), label)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page(models))
    today = __import__("datetime").date.today().isoformat()
    urls = [f"{BASE}/"]
    md_lines = ["# ModelFit — Can I Run This LLM?", "",
                "Measured GGUF file sizes and real VRAM/RAM requirements, updated daily from the Hugging Face API.",
                "Every number below is the actual published file size plus KV-cache and runtime overhead — not a formula estimate.", ""]
    for m in models:
        d = os.path.join(OUT, m["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(model_page(m, models))
        urls.append(f"{BASE}/{m['slug']}/")
        # markdown twin for AI engines + llms.txt
        gg = clean_quants(m["ggufs"])
        order = sorted(gg.items(), key=lambda x: x[1])
        med = statistics.median(s for _, s in order)
        rec_q, rec_s = min(order, key=lambda x: abs(x[1] - med * 0.55)) if len(order) > 3 else order[len(order)//2]
        md = [f"# {m['name']} — VRAM/RAM requirements (measured)", "",
              f"Source: https://huggingface.co/{m['id']} (community GGUF). Updated {today}. Page: {BASE}/{m['slug']}/", "",
              f"- Recommended quant {rec_q}: needs ~{fmt_gb(need_gb(rec_s, m['arch']))} (file {fmt_gb(rec_s/1e9)})",
              f"- Smallest build needs ~{fmt_gb(need_gb(order[0][1], m['arch']))}",
              f"- Lossless build needs ~{fmt_gb(need_gb(order[-1][1], m['arch']))}", "",
              "| Quant | File (measured) | VRAM/RAM needed (8K ctx) |", "|---|---|---|"]
        md += [f"| {q} | {fmt_gb(s/1e9)} | {fmt_gb(need_gb(s, m['arch']))} |" for q, s in order]
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
        md_lines.append(f"- [{m['name']}]({BASE}/{m['slug']}/index.md): recommended {rec_q} ~{fmt_gb(need_gb(rec_s, m['arch']))}, smallest ~{fmt_gb(need_gb(order[0][1], m['arch']))}")
    from tiers import build_tier_pages, build_picker
    tu, tmd = build_tier_pages(models, OUT)
    pu, pmd = build_picker(models, OUT)
    urls += tu + pu
    md_lines += tmd + pmd
    with open(os.path.join(OUT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + "".join(f"<url><loc>{E(u)}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq></url>" for u in urls)
                + "</urlset>")
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"""User-agent: *
Allow: /

# AI engines — cite freely
User-agent: GPTBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-User
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: anthropic-ai
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Applebot-Extended
Allow: /
User-agent: Bytespider
Allow: /

Sitemap: {BASE}/sitemap.xml
""")
    with open(os.path.join(HERE, "urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    # public JSON dump — developers cite/link tools that give them data (growth loop #2)
    api_dir = os.path.join(OUT, "api")
    os.makedirs(api_dir, exist_ok=True)
    slim = [{"id": m["id"], "name": m["name"], "downloads": m["downloads"],
             "page": f"{BASE}/{m['slug']}/",
             "ggufs_gb": {q: round(s / 1e9, 2) for q, s in sorted(clean_quants(m["ggufs"]).items(), key=lambda x: x[1])}}
            for m in models]
    with open(os.path.join(api_dir, "models.json"), "w", encoding="utf-8") as f:
        json.dump({"updated": today, "source": "Hugging Face API (measured GGUF file sizes)",
                   "license": "CC BY 4.0 — attribution: ModelFit (modelfit-eight.vercel.app)",
                   "models": slim}, f, ensure_ascii=False)
    print(f"built {len(models)} model pages + index + llms.txt + og/badges/api -> site/")

if __name__ == "__main__":
    main()
