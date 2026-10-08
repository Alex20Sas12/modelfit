# -*- coding: utf-8 -*-
"""build.py — generate ModelFit static site from models.json. Run: python build.py
VRAM model: weights (measured GGUF bytes) + overhead. If config.json gave arch,
KV cache is computed exactly (GQA formula); otherwise flat +20%/min 1.5 GB rule.
"""
import json, os, html, re, math, statistics, urllib.parse
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

GPUS = [  # (name, vram_gb, bandwidth GB/s)
    ("RTX 3060 12GB", 12, 360), ("RTX 4060 Ti 16GB", 16, 288), ("RTX 3090 24GB", 24, 936), ("RTX 4090 24GB", 24, 1008),
    ("RTX 5090 32GB", 32, 1792), ("RTX PRO 6000 96GB", 96, 1792),
    ("Mac 16GB unified", 16, 100), ("Mac 32GB unified", 32, 150),
    ("Mac 64GB unified", 64, 273), ("Mac 128GB unified", 128, 400),
    ("Mac 256GB unified", 256, 546), ("Mac 512GB unified", 512, 819),
    ("32GB system RAM (CPU)", 32, 50), ("64GB system RAM (CPU)", 64, 50),
    ("128GB system RAM (CPU)", 128, 80), ("256GB system RAM (CPU)", 256, 80),
    ("1TB server RAM (CPU)", 1024, 200), ("2TB server RAM (CPU)", 2048, 200),
]
# ponytail: bandwidth = spec sheets, mid-tier (Max/Pro/Ultra ranges) approximated to one number per entry.
# Tok/s shown as ~value with "estimate" wording; upgrade path = community benchmark table when we have traffic to justify curation.

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
    """KV cache in GB. MLA (DeepSeek) = L*ctx*(kv_lora_rank+qk_rope)/2bytes; else exact GQA."""
    L = arch.get("num_hidden_layers")
    if L and arch.get("kv_lora_rank") and arch.get("qk_rope_head_dim"):
        return L * ctx * (arch["kv_lora_rank"] + arch["qk_rope_head_dim"]) * 2 / 1e9
    kvh, hd = arch.get("num_key_value_heads"), arch.get("head_dim")
    if not (L and kvh and hd):
        return None
    return 2 * L * kvh * hd * ctx * 2 / 1e9

def params_b(m):
    if m.get("params"):
        pb = m["params"] / 1e9
    else:
        gg = clean_quants(m["ggufs"])
        big = [s for q, s in gg.items() if q in ("F16", "BF16")]
        pb = max(big) / 2 / 1e9 if big else None
    # sanity: repo named "27B" must not show 54B (stale safetensors total from merged/aux files)
    nb = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)B", m.get("name", ""), re.I)]
    if nb:
        nm = max(nb)
        if pb is None or pb > nm * 1.6:
            pb = nm
    return pb

def active_frac(arch):
    """Fraction of weights read per token (MoE only activates experts_per_tok/experts + dense part)."""
    ne, nt = arch.get("num_experts"), arch.get("num_experts_per_tok")
    if ne and nt and ne > 1:
        return min(1.0, nt / ne + 0.12)  # ponytail: +12% for attention/shared; real split varies, label says ~
    return 1.0

def tok_s(file_gb, arch, bw_gbs):
    """Rough decode tok/s = memory-bandwidth-bound: bw / bytes read per token."""
    if not file_gb or not bw_gbs:
        return None
    return bw_gbs * 0.75 / (file_gb * active_frac(arch))

def live_need(s, arch):
    """(base_gb, kv1k_gb) for the live JS: need(ctx) = base + kv1k*ctx/1024."""
    w = s / 1e9
    kv1 = kv_cache_gb(arch, 1024)
    if kv1 is not None:
        return w + max(1.0, w * 0.08), kv1
    return w * 1.2 + 1.5, 0.0

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
    for name, v, bw in GPUS:
        ok = need <= v * 0.92
        out.append((name, v, "yes" if ok else ("tight" if need <= v else "no")))
    return out

# Cloud GPU rental CTA. Ref codes load from affiliate.json (owner fills once; daily cron picks up).
# Vast: 3% lifetime spend, cashout 75% (needs FRESH referral-only account). RunPod: 3-5% + $5-500 bonus.
try:
    _aff = json.load(open(os.path.join(HERE, "affiliate.json"), encoding="utf-8"))
except Exception:
    _aff = {}
_vast = "https://cloud.vast.ai/?ref_id=" + urllib.parse.quote(_aff["vast_ref"]) if _aff.get("vast_ref") else "https://vast.ai/"
_runpod = "https://www.runpod.io/?ref=" + urllib.parse.quote(_aff["runpod_ref"]) if _aff.get("runpod_ref") else "https://www.runpod.io/"
CLOUD_CTA = ('<div class="calc" style="border-color:var(--warn)"><b>Doesn\'t fit your machine?</b> '
             'Rent a GPU by the hour instead — a 24GB RTX 4090 starts around $0.30-0.50/h '
             f'(<a href="{_vast}" rel="nofollow noopener" target="_blank">Vast.ai</a>, '
             f'<a href="{_runpod}" rel="nofollow noopener" target="_blank">RunPod</a>), '
             + (f'or rent a dedicated GPU server from <a href="{E(_aff["ishosting_url"])}" rel="nofollow noopener" target="_blank">is*hosting</a>. ' if _aff.get("ishosting_url") else "or use the model via a hosted API. ")
             + 'Buying instead? <a href="/which-gpu-should-i-buy/">Which GPU should I buy? →</a></div>')

# Approx used/new street prices, USD. ponytail: knob — used market drifts, refresh by hand ~monthly.
USED_PRICES = [  # (label, vram_gb, usable_factor, price_usd)
    ("Used RTX 3070 8GB", 8, 1.0, 220), ("New RTX 4060 8GB", 8, 1.0, 280),
    ("Used RTX 3060 12GB", 12, 1.0, 250), ("Used RTX 3080 12GB", 12, 1.0, 380),
    ("Used RTX 4070 12GB", 12, 1.0, 430), ("New RTX 4060 Ti 16GB", 16, 1.0, 420),
    ("New RTX 5080 16GB", 16, 1.0, 1000), ("Used RTX 3090 24GB", 24, 1.0, 650),
    ("Used RTX 4090 24GB", 24, 1.0, 1600), ("New RTX 5090 32GB", 32, 1.0, 2500),
    ("MacBook Air 16GB (M-series)", 16, 0.75, 1000), ("MacBook Pro 24GB", 24, 0.75, 1600),
    ("MacBook Pro Max 64GB", 64, 0.75, 3200), ("Mac Studio Ultra 256GB", 256, 0.75, 6000),
]

def cheapest_card(min_need):
    """(price, label) of the cheapest listed hardware that runs a model needing min_need GB, else None."""
    hits = [(pr, lb) for lb, v, f, pr in USED_PRICES if min_need <= v * f * 0.92]
    return min(hits) if hits else None

def page(rel, title, desc, body, canonical, jsonld=None, og_image="og.png"):
    # AUDIT FIX 9.1: ad-скрипты fires только после cookie consent (баннер = равные Accept/Reject)
    ad = """<div class="ad-zone" data-ad="https://pl31410879.profitableratecpmnetwork.com/2376e478c4be448f43fb6b09e2fff78d/invoke.js"></div> <div id="container-2376e478c4be448f43fb6b09e2fff78d"></div>"""
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
<meta name="p:domain_verify" content="79ae4d87e6e8290cafb22cb5e885966a">
<link rel="alternate" type="application/rss+xml" title="ModelFit Feed" href="{BASE}/feed.xml">
<link rel="icon" href="/favicon.ico" sizes="any"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#0d1117">
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
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
button{{min-height:44px}}
@media (prefers-reduced-motion: reduce) {{*{{animation:none !important;transition:none !important}}}}
@media (max-width:640px) {{table{{font-size:13px}}td,th{{padding:6px 7px}}.grid{{grid-template-columns:1fr 1fr}}}}
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
<script>/* GPU autodetect: WEBGL_debug_renderer_info, nothing leaves the browser */
try{{const c=document.createElement('canvas');const gl=c.getContext('webgl');
if(gl){{const d=gl.getExtension('WEBGL_debug_renderer_info');
if(d){{const r=gl.getParameter(d.UNMASKED_RENDERER_WEBGL)||'';
const m=r.match(/RTX\\s?(\\d{4})|Radeon\\sRX\\s(\\d{4})|(Apple\\sM\\d)/i);
const el=document.getElementById('myvram')||document.getElementById('v');
const note=document.createElement('p');note.className='note';
if(el&&m&&!el.value){{note.textContent='Detected GPU: '+r.slice(0,60)+' — pick your memory size above to get exact verdicts.';el.parentNode.insertBefore(note,el.nextSibling);}}
else if(el){{note.textContent='Detected GPU: '+r.slice(0,60)+' (nothing leaves your browser).';el.parentNode.insertBefore(note,el.nextSibling);}}}}}}}}catch(e){{}}</script>
<footer><div class="wrap">ModelFit — every number is measured from real GGUF files via the Hugging Face API, updated daily. Not affiliated with Hugging Face.<br>Data: Hugging Face API. Sizes: community GGUF uploads (unsloth, bartowski, lmstudio-community).<br><a href="/about/">About ModelFit</a> · <a href="/guides/">Guides</a> · <a href="/api/models.json">Public API (JSON, CC BY 4.0)</a> · <a href="/llms.txt">llms.txt</a> · <a href="/feed.xml">RSS</a> · <a href="/privacy/">Privacy</a></div></footer>
<div id="ccbar" style="position:fixed;bottom:0;left:0;right:0;background:var(--card);border-top:1px solid var(--line);padding:12px 16px;display:none;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap;font-size:14px;z-index:99"><span>Our ads partner and this site use storage on your device to work. No personal data is tracked.</span><button id="ccok" style="background:var(--acc);color:#0d1117;border:0;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer">Accept</button><button id="ccno" style="background:var(--bg);color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer">Reject</button></div>
<script>(function(){{try{{var g=localStorage.getItem('mf-consent');if(g==='1')run();else if(g==='0'){{}}else{{var b=document.getElementById('ccbar');b.style.display='flex';document.getElementById('ccok').onclick=function(){{localStorage.setItem('mf-consent','1');b.style.display='none';run()}};document.getElementById('ccno').onclick=function(){{localStorage.setItem('mf-consent','0');b.style.display='none'}}}}}}catch(e){{run()}}
function run(){{document.querySelectorAll('.ad-zone[data-ad]').forEach(function(z){{var s=document.createElement('script');s.async=true;s.src=z.getAttribute('data-ad');z.appendChild(s)}});var sb=document.createElement('script');sb.src='https://pl31411352.profitableratecpmnetwork.com/9f/5b/f6/9f5bf63f2ad6bcc4b9a12888c7acf0bc.js';document.body.appendChild(sb)}}}})()</script>
</body></html>"""

def related(m, all_models, n=8):
    """Same-family cluster first (name prefix), then top-downloads filler."""
    fam = re.split(r"[-\s]", m["name"].lower())[0]
    pool = [o for o in all_models if o["slug"] != m["slug"]]
    same = [o for o in pool if o["name"].lower().startswith(fam)]
    rest = [o for o in pool if o not in same]
    return (same + rest)[:n]

def run_commands(m, rec_q):
    """Copy-paste commands. llama.cpp/Ollama both resolve `hf.co/<repo>` GGUF directly — no guessing ollama library names."""
    hf = E(m["id"])
    return (f'<div class="calc"><b>Run {E(m["name"])} ({E(rec_q)}) — copy-paste:</b>'
            f'<pre style="overflow-x:auto;background:var(--bg);padding:10px;border-radius:8px;font-size:13px">'
            f'# llama.cpp (auto-downloads the GGUF)\nllama-cli -hf {hf}:{E(rec_q)}\n\n'
            f'# Ollama (pulls straight from Hugging Face)\nollama run hf.co/{hf}:{E(rec_q)}\n\n'
            f'# LM Studio: search "{hf}" in the model browser</pre>'
            f'<p class="note">Commands load the exact quant measured on this page.</p></div>')

def model_page(m, all_models):
    gg = clean_quants(m["ggufs"])
    order = sorted(gg.items(), key=lambda x: x[1])
    arch = m["arch"]
    name = m["name"]
    p = params_b(m)
    kv_exact = kv_cache_gb(arch, 8192) is not None
    kv1k = kv_cache_gb(arch, 1024)  # GB per 1K tokens — feeds the live context selector
    rows = []
    for q, s in order:
        need = need_gb(s, arch)
        v = verdicts(need)
        best = [n for n, gb, st in v if st == "yes"][:1]
        if best:
            verdict, cls = best[0], "yes"
        elif any(st == "tight" for _, _, st in v):
            verdict, cls = "borderline", "tight"
        else:
            verdict, cls = f"{math.ceil(need/24)}×24GB (server-grade)", "no"
        rows.append(f"<tr><td><b>{E(q)}</b></td><td class='n'>{fmt_gb(s/1e9)}</td>"
                    f"<td class='n'>{fmt_gb(need)}</td><td><span class='pill {cls}'>{E(verdict)}</span></td></tr>")
    # GPU matrix for the recommended quant (smallest need <= 40% of median = sweet spot Q4-ish)
    med = statistics.median(s for _, s in order)
    rec_q, rec_s = min(order, key=lambda x: abs(x[1] - med * 0.55)) if len(order) > 3 else order[len(order)//2]
    rec_need = need_gb(rec_s, arch)
    rec_w = rec_s / 1e9
    gpu_rows = ""
    for (gn, gb, st), (_, _, bw) in zip(verdicts(rec_need), GPUS):
        speed = tok_s(rec_w, arch, bw) if st != "no" else None
        sp = f"~{speed:.0f} tok/s" if speed and speed >= 1 else (f"~{speed:.1f} tok/s" if speed else "")
        gpu_rows += (f"<tr><td>{E(gn)}</td><td class='n'>{gb} GB</td>"
                     f"<td><span class='pill {st}'>{'RUNS' if st=='yes' else ('tight' if st=='tight' else 'no')}</span></td>"
                     f"<td class='n'>{sp}</td></tr>")
    ptxt = f"~{p:.1f}B parameters" if p else ""
    kvnote = (("KV cache computed exactly from the model config (" + ("MLA" if arch.get("kv_lora_rank") else "GQA") + " formula, 8K context).")
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
    spd4090 = tok_s(rec_w, arch, 1008)
    faqs = [
        (f"How much VRAM does {name} need?",
         f"The measured answer: {fmt_gb(rec_need)} at the {rec_q} quant with 8K context. The smallest published build needs {fmt_gb(need_gb(order[0][1], arch))}; the lossless (F16/BF16) build needs {fmt_gb(need_gb(order[-1][1], arch))}. These are real GGUF file sizes from Hugging Face, not formula estimates."),
        (f"Can I run {name} on a 24GB GPU (RTX 3090/4090)?", a24),
        (f"How fast will {name} run?",
         (f"Decode speed is memory-bandwidth-bound. At {rec_q}: roughly {spd4090:.0f} tok/s on an RTX 4090, "
          f"{tok_s(rec_w, arch, 936):.0f} tok/s on an RTX 3090, {tok_s(rec_w, arch, 400):.0f} tok/s on an M-series Mac with 128GB, "
          f"and {tok_s(rec_w, arch, 50):.1f} tok/s on CPU with dual-channel DDR4 — estimates from measured file size, MoE active-parameter share and memory bandwidth.")
         if spd4090 else "Speed depends on your memory bandwidth: roughly bandwidth(GB/s) ÷ model size(GB), less for dense models, more for MoE with few active parameters. The GPU table above shows per-card estimates."),
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
    # live JS data: per-quant base+overhead, kv per 1K tokens → recompute need for ANY context
    data = {"name": name, "kv1k": round(kv_cache_gb(arch, 1024) or 0, 4),
            "q": {q: [round(x, 2) for x in live_need(s, arch)] for q, s in order}}
    gpu_opts = "".join(f'<option value="{gb}">{E(gn)}</option>' for gn, gb, _ in GPUS)
    body = f"""<div class="crumb"><a href="/">All models</a> › {E(name)}</div>
<h1>{E(name)} requirements — can you run it?</h1>
<p class="sub">{E(ptxt)} · {len(gg)} quantizations measured · updated {E(m['lastModified'] or 'daily')} · source: <a href="https://huggingface.co/{E(m['id'])}" rel="nofollow">{E(m['id'])}</a></p>
<div class="calc"><label style="color:var(--mut);font-size:13px">Pick your hardware (or type memory in GB) — verdicts update live:</label>
<select id="mypick" onchange="document.getElementById('myvram').value=this.value;fit()"><option value="">— choose GPU / Mac / RAM —</option>{gpu_opts}</select>
<div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap">
<input type="number" id="myvram" min="1" max="4096" placeholder="e.g. 24 GB" oninput="fit()" style="flex:1;min-width:140px">
<select id="myctx" onchange="fit()" style="flex:1;min-width:140px"><option value="4096">4K context</option><option value="8192" selected>8K context</option><option value="32768">32K context</option><option value="131072">128K context</option></select></div>
<div id="myverdict" style="margin-top:10px"></div></div>
{run_commands(m, rec_q)}
<h2>Every quantization: real file size vs what you actually need</h2>
<table><thead><tr><th>Quant</th><th style="text-align:right">File (measured)</th><th style="text-align:right">VRAM/RAM needed (8K ctx)</th><th>Runs on (first fit)</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="note">{E(kvnote)} MoE models keep all experts in memory — total size counts, not just active params. Longer context grows the KV cache — use the selector above.</p>
<h2>Can I run {E(name)} on my GPU? ({E(rec_q)} recommended quant)</h2>
<table><thead><tr><th>Hardware</th><th style="text-align:right">Memory</th><th>Verdict</th><th style="text-align:right">Est. speed</th></tr></thead><tbody>{gpu_rows}</tbody></table>
<p class="note">Speed = decode tok/s estimated from memory bandwidth ÷ measured file size (× MoE active share). Real numbers vary ±30% by runtime and settings.</p>
{'<div id="cloudcta" style="display:none">' + CLOUD_CTA + '</div>'}
<h2>How much VRAM does {E(name)} need?</h2>
<p>The honest answer: <b>{fmt_gb(rec_need)}</b> at the {E(rec_q)} quant with 8K context — that is the measured
file size ({fmt_gb(rec_s/1e9)}) plus KV cache and runtime overhead. The smallest published build needs
{fmt_gb(need_gb(order[0][1], arch))}; the lossless one needs {fmt_gb(need_gb(order[-1][1], arch))}.
{('<br>Cheapest hardware that runs it: <b>' + E(cheapest_card(rec_need)[1]) + '</b> (~$' + str(cheapest_card(rec_need)[0]) + ', used market) — see <a href="/which-gpu-should-i-buy/">which GPU to buy</a>.') if cheapest_card(rec_need) else ''}</p>
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
const DATA={json.dumps(data, ensure_ascii=False)};
function needOf(q,ctx){{const [w,o]=DATA.q[q];return w+DATA.kv1k*ctx/1024+o;}}
function fit(){{const v=+document.getElementById('myvram').value;const ctx=+document.getElementById('myctx').value;
const d=document.getElementById('myverdict');const cta=document.getElementById('cloudcta');
if(!v){{d.innerHTML='';if(cta)cta.style.display='none';return;}}
let ok=[],tight=[];
for(const q of Object.keys(DATA.q)){{const n=needOf(q,ctx);if(n<=v*0.92)ok.push([q,n]);else if(n<=v)tight.push(q);}}
ok.sort((a,b)=>b[1]-a[1]);
if(cta)cta.style.display=ok.length?'none':'block';
d.innerHTML=ok.length?'<span class="pill yes">RUNS</span> '+DATA.name+' at: <b>'+ok.map(x=>x[0]).join(', ')+'</b>'
+(tight.length?' <span class="pill tight">tight</span> '+tight.join(', '):'')
:'<span class="pill no">NO</span> nothing fits in '+v+' GB at '+Math.round(ctx/1024)+'K context — smallest needs '+Math.min(...Object.keys(DATA.q).map(q=>needOf(q,ctx))).toFixed(1)+' GB. Rent a GPU below, or pick a smaller model.';}}
</script>"""
    return page(f"{m['slug']}/index.html", f"{name} VRAM Requirements — Can You Run It? | ModelFit",
                f"{name} needs {fmt_gb(rec_need)} VRAM at {rec_q} (measured). Full quant-by-quant table, GPU verdicts for every card from RTX 3060 to Mac Studio 512GB.",
                body, f"{m['slug']}/", jsonld)

def index_page(models):
    from compare import PAIRS
    by_slug = {m["slug"]: m for m in models}
    cmp_cards = "".join(
        '<a href="/compare-' + short + '/">' + E(by_slug[sa]["name"]) + " vs " + E(by_slug[sb]["name"]) + '<small>measured hardware comparison</small></a>'
        for short, sa, sb in PAIRS if sa in by_slug and sb in by_slug)
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
<a href="/guides/">Guides: VRAM, quants, runtimes<small>how it all works</small></a>
<a href="/which-gpu-should-i-buy/">Which GPU should I buy?<small>cheapest hardware per model</small></a>
</div>
<h2 style="font-size:19px;margin:22px 0 6px">Head-to-head comparisons</h2>
<div class="grid">{cmp_cards}</div>
<div class="calc"><input id="q" placeholder="Filter models… (type a name)" oninput="flt()"></div>
<div class="grid" id="cards">{''.join(cards)}</div>
<h2 style="font-size:19px;margin:22px 0 6px">Frequently asked questions</h2>
<h3>How do I know if I can run an LLM on my PC?</h3>
<p>Compare your VRAM (GPU) or system RAM (CPU inference) with the model's GGUF file size plus KV-cache overhead. Rough guide: an 8B model at Q4_K_M needs ~6 GB VRAM at 8K context, a 27-30B model needs ~18-20 GB, and 70B+ needs multi-GPU or CPU offload. Every ModelFit page lists the measured file size for each quantization so you can match it to your exact hardware.</p>
<h3>Where do ModelFit's numbers come from?</h3>
<p>Directly from the Hugging Face API, refreshed daily: the actual published GGUF file sizes from community repos (unsloth, Bartowski and others) plus KV-cache and runtime overhead for 8K context. Nothing is estimated from parameter-count formulas.</p>
<h3>Which quantization should I pick?</h3>
<p>Q4_K_M is the standard balance of quality and size. Drop to IQ3/Q3 only when VRAM is tight; choose Q5/Q6 when you have headroom and want maximum quality. Each model page shows what every quantization needs on your hardware.</p>
<script>
const CARDS=[...document.querySelectorAll('#cards a')];
function flt(){{const q=document.getElementById('q').value.toLowerCase();
CARDS.forEach(c=>c.style.display=c.textContent.toLowerCase().includes(q)?'':'none');}}
</script>"""
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "ModelFit", "url": BASE + "/",
         "description": "Can I run this LLM? Measured GGUF sizes and VRAM/RAM requirements for every trending local model, updated daily from the Hugging Face API.",
         "publisher": {"@type": "Organization", "name": "ModelFit", "url": BASE}},
        {"@type": "Organization", "name": "ModelFit", "url": BASE + "/",
         "description": "Measured VRAM/RAM requirements for local LLMs, updated daily from the Hugging Face API",
         "contactPoint": {"@type": "ContactPoint", "email": "alexford0289+mf@gmail.com",
                          "contactType": "customer", "availableLanguage": "English"},
         "sameAs": ["https://github.com/Alex20Sas12/modelfit", "https://dev.to/kata_omel"]},
        {"@type": "ItemList", "name": "Trending LLMs with measured requirements",
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/{m['slug']}/", "name": m["name"]}
                             for i, m in enumerate(models[:30])]},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "How do I know if I can run an LLM on my PC?",
             "acceptedAnswer": {"@type": "Answer", "text": "Compare your VRAM or system RAM with the model's GGUF file size plus KV-cache overhead: an 8B model at Q4_K_M needs ~6 GB VRAM at 8K context, 27-30B needs ~18-20 GB, 70B+ needs multi-GPU or CPU offload."}},
            {"@type": "Question", "name": "Where do ModelFit's numbers come from?",
             "acceptedAnswer": {"@type": "Answer", "text": "Directly from the Hugging Face API, refreshed daily: actual published GGUF file sizes from community repos plus KV-cache and runtime overhead. Nothing is estimated from formulas."}},
            {"@type": "Question", "name": "Which quantization should I pick?",
             "acceptedAnswer": {"@type": "Answer", "text": "Q4_K_M is the standard balance of quality and size; drop to IQ3/Q3 when VRAM is tight, choose Q5/Q6 with headroom for maximum quality."}},
        ]},
    ]}
    return page("index.html", "ModelFit — Can I Run This LLM? VRAM & RAM Requirements, updated daily",
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
    urls = [f"{BASE}/", f"{BASE}/about/", f"{BASE}/privacy/"]
    md_lines = ["# ModelFit — Can I Run This LLM?", "",
                "> Measured GGUF file sizes and real VRAM/RAM requirements, updated daily from the Hugging Face API.",
                "Every number below is the actual published file size plus KV-cache and runtime overhead — not a formula estimate.", "",
                "## Models", ""]
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
    from tiers import build_tier_pages, build_picker, build_buy_page
    from compare import build_compare_pages
    from guides import build_guides
    tu, tmd = build_tier_pages(models, OUT)
    pu, pmd = build_picker(models, OUT)
    bu, bmd = build_buy_page(models, OUT)
    cu, cmd = build_compare_pages(models, OUT)
    gu, gmd = build_guides(models, OUT)
    urls += tu + pu + bu + cu + gu
    md_lines += tmd + pmd + bmd + cmd + gmd
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
    # GEO-файлы для ИИ-краулеров (общий генератор geo_patch/geo_files.py)
    def _geo_write(path, content):
        full = os.path.join(OUT, path.lstrip("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "geo_patch"))
    from geo_files import emit_geo
    _items = [("/", "ModelFit — Can I Run This LLM?", "Measured VRAM/RAM requirements for local LLMs")]
    _items += [(f"/{m['slug']}/", m["name"], f"{m['name']} GGUF sizes and VRAM requirements") for m in models[:60]]
    _faqs = [
        ("How do I know if I can run an LLM on my PC?", "Compare your VRAM or system RAM with the model's GGUF file size plus KV-cache overhead: an 8B model at Q4_K_M needs ~6 GB VRAM at 8K context, 27-30B needs ~18-20 GB, 70B+ needs multi-GPU or CPU offload."),
        ("Where do ModelFit's numbers come from?", "Directly from the Hugging Face API, refreshed daily: actual published GGUF file sizes from community repos plus KV-cache and runtime overhead. Nothing is estimated from formulas."),
        ("Which quantization should I pick?", "Q4_K_M is the standard balance of quality and size; drop to IQ3/Q3 when VRAM is tight, choose Q5/Q6 with headroom for maximum quality."),
    ]
    emit_geo(_geo_write, BASE, "ModelFit",
             "Can I run this LLM? Measured GGUF sizes and VRAM/RAM requirements for every trending local model, updated daily from the Hugging Face API.",
             _items, _faqs)
    _geo_write("about/index.html", page("about/index.html", "About ModelFit",
        "ModelFit measures real GGUF file sizes and VRAM/RAM requirements for local LLMs, updated daily from the Hugging Face API.",
        '<h1>About ModelFit</h1><p class="sub">Measured requirements, not formulas.</p>'
        '<p>ModelFit answers one question: can your PC run a given local LLM? Every number comes from the Hugging Face API — the actual published GGUF file sizes from community repos (unsloth, bartowski, lmstudio-community) plus KV-cache and runtime overhead for 8K context. Nothing is estimated from parameter-count formulas.</p>'
        '<h2>Who runs it</h2><p>ModelFit is an independent, free tool. Source code: <a href="https://github.com/Alex20Sas12/modelfit">github.com/Alex20Sas12/modelfit</a>. Not affiliated with Hugging Face.</p>'
        '<h2>For AI assistants and developers</h2><p>Machine-readable: <a href="/llms.txt">/llms.txt</a>, <a href="/api/models.json">/api/models.json</a> (full dataset, CC BY 4.0), <a href="/feed.xml">/feed.xml</a>. Data is CC BY 4.0 with attribution to ModelFit.</p>',
        "about/", None, og_image=None))
    # AUDIT FIX 9.2: privacy-страница (ссылка есть в футере каждой страницы)
    _geo_write("privacy/index.html", page("privacy/index.html", "Privacy Policy — ModelFit",
        "What ModelFit does and does not collect: nothing server-side; ad scripts run only after your choice.",
        '<h1>Privacy Policy</h1><p class="sub">Last updated: ' + today + '</p>'
        '<p>ModelFit is a fully static site. There are no accounts, no server-side analytics, no forms: your GPU detection and VRAM input never leave your browser.</p>'
        '<h2>Advertising</h2><p>We show non-personalized ads served by Adsterra. Their scripts load only after you pick "Accept" in the banner at the bottom of this site; your choice is stored locally in your browser and we keep no copy of it. If you pick "Reject", no ad scripts or storage run at all. The ad partner operates under its own policy: <a href="https://adsterra.com/privacy/">adsterra.com/privacy</a>.</p>'
        '<h2>Your choices</h2><p>Clearing site data for this domain in your browser removes your saved consent; the banner will ask again. No personal data is sold or shared.</p>'
        '<h2>Contact</h2><p>Questions: open an issue at <a href="https://github.com/Alex20Sas12/modelfit">github.com/Alex20Sas12/modelfit</a> or see <a href="/about/">/about/</a>.</p>',
        "privacy/", None, og_image=None))
    # AUDIT FIX 10.1: свой 404 (Vercel отдаёт /404.html для несуществующих путей)
    _geo_write("404.html", page("404.html", "Page not found — ModelFit",
        "The catalog rotates daily with Hugging Face trending, so an old model page may be gone.",
        '<h1>404 — page not found</h1><p class="sub">Model pages rotate with the Hugging Face trending list, so an old link may be gone.</p>'
        '<p>Try: <a href="/">all models</a> · <a href="/what-llm-can-i-run/">VRAM picker</a> · <a href="/guides/">guides</a> · <a href="/best-llm-for-8gb-vram/">best LLMs by VRAM tier</a>.</p>',
        "404.html", None, og_image=None))
    # AUDIT FIX 10.2: manifest + apple-touch-icon
    _geo_write("manifest.webmanifest", json.dumps(
        {"name": "ModelFit", "short_name": "ModelFit", "start_url": "/", "display": "standalone",
         "background_color": "#0d1117", "theme_color": "#0d1117",
         "icons": [{"src": "/favicon.ico", "sizes": "64x64", "type": "image/x-icon"},
                   {"src": "/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"}]}))
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
    # 08.10 грабля: HF ротирует топ — прошлые страницы моделей оставались в site/ вечно
    # (движок, дубликаты контента, 200-е на мёртвых compare). Чистим папки вне urls + whitelist.
    import shutil
    keep = {u[len(BASE):].strip("/").split("/")[0] for u in urls} | {"api", "assets"}
    # urls содержит /privacy/ -> keep включает "privacy"
    for d in os.listdir(OUT):
        full = os.path.join(OUT, d)
        if os.path.isdir(full) and not d.startswith(".") and d not in keep:
            shutil.rmtree(full)
    # favicon.ico (PIL) — раньше /favicon.ico отдавал 404
    try:
        Image.open(os.path.join(OUT, "og.png")).resize((64, 64)).save(
            os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (64, 64)])
        Image.open(os.path.join(OUT, "og.png")).resize((180, 180)).save(
            os.path.join(OUT, "apple-touch-icon.png"))
    except Exception as e:
        print("favicon skip:", e)

if __name__ == "__main__":
    main()
