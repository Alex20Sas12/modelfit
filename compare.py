# -*- coding: utf-8 -*-
"""compare.py — программные страницы «X vs Y» под подтверждённый autocomplete-спрос.
Пары хардкожены (проверены Google autocomplete 21.09) — генератор пар не нужен, YAGNI.
Сайт-фича: сравнение hardware-требований из ИЗМЕРЕННЫХ GGUF-размеров.
"""
import json, os, statistics
from build import E, BASE, clean_quants, need_gb, fmt_gb, params_b, page, make_og

# (short-slug, model_slug_a, model_slug_b) — ОБА должны существовать в models.json
PAIRS = [
    ("kimi-k3-vs-deepseek-v4", "unsloth-kimi-k3-gguf", "antirez-deepseek-v4-gguf"),
    ("deepseek-v4-vs-gemma-4", "antirez-deepseek-v4-gguf", "ggml-org-gemma-4-e4b-it-gguf"),
    ("deepseek-v4-vs-gemma-4-12b", "antirez-deepseek-v4-gguf", "unsloth-gemma-4-12b-it-gguf"),
    ("kimi-k3-vs-qwen3-27b", "unsloth-kimi-k3-gguf", "unsloth-qwen3-8-27b-gguf"),
    ("qwen3-27b-vs-qwen3-coder-30b", "unsloth-qwen3-8-27b-gguf", "unsloth-qwen3-coder-30b-a3b-instruct-gguf"),
    ("glm-5-3-vs-qwen3-27b", "unsloth-glm-5-3-gguf", "unsloth-qwen3-8-27b-gguf"),
]

GPUS = [("RTX 3060 12GB", 12), ("RTX 4070 12GB", 12), ("RTX 4090 24GB", 24), ("RTX 5090 32GB", 32), ("Mac 24GB", 18), ("Mac 64GB", 48)]

def _pick(gg, arch):
    order = sorted(gg.items(), key=lambda x: x[1])
    med = statistics.median(s for _, s in order)
    rec_q, rec_s = min(order, key=lambda x: abs(x[1] - med * 0.55)) if len(order) > 3 else order[len(order)//2]
    return {
        "smallest": (order[0][0], need_gb(order[0][1], arch)),
        "rec": (rec_q, need_gb(rec_s, arch)),
        "lossless": (order[-1][0], need_gb(order[-1][1], arch)),
        "n": len(order),
    }

def build_compare_pages(models, OUT):
    by_slug = {m["slug"]: m for m in models}
    urls, md_lines = [], []
    for short, sa, sb in PAIRS:
        a, b = by_slug.get(sa), by_slug.get(sb)
        if not a or not b:
            continue
        pa, pb = _pick(clean_quants(a["ggufs"]), a["arch"]), _pick(clean_quants(b["ggufs"]), b["arch"])
        name_a, name_b = a["name"], b["name"]
        slug = f"compare-{short}"
        pba, pbb = params_b(a), params_b(b)
        def pill(need, gb):
            cls = "yes" if need <= gb * 0.92 else ("tight" if need <= gb else "no")
            txt = {"yes": "fits", "tight": "tight", "no": "no"}[cls]
            return '<span class="pill ' + cls + '">' + txt + '</span>'
        rows = "".join(
            f"<tr><td>{E(g)}</td><td class='n'>{gb} GB</td>"
            f"<td>{pill(pa['rec'][1], gb)}</td>"
            f"<td>{pill(pb['rec'][1], gb)}</td></tr>"
            for g, gb in GPUS)
        verdict = ("About the same hardware-wise." if abs(pa['rec'][1]-pb['rec'][1]) < 2 else
                   (f"{name_a} needs more memory at the recommended quant." if pa['rec'][1] > pb['rec'][1]
                    else f"{name_b} needs more memory at the recommended quant."))
        body = f"""<div class="crumb"><a href="/">All models</a> › {E(name_a)} vs {E(name_b)}</div>
<h1>{E(name_a)} vs {E(name_b)} — hardware requirements compared (measured)</h1>
<p class="sub">Both sides use real GGUF file sizes from Hugging Face — not params×bits formulas. Updated daily.</p>
<table><thead><tr><th></th><th>{E(name_a)}</th><th>{E(name_b)}</th></tr></thead><tbody>
<tr><td>Parameters</td><td class='n'>{f"{pba:.0f}B" if pba else "?"}</td><td class='n'>{f"{pbb:.0f}B" if pbb else "?"}</td></tr>
<tr><td>Downloads (30d)</td><td class='n'>{a['downloads']//1000}k</td><td class='n'>{b['downloads']//1000}k</td></tr>
<tr><td>Quantizations published</td><td class='n'>{pa['n']}</td><td class='n'>{pb['n']}</td></tr>
<tr><td>Smallest build needs</td><td class='n'>{fmt_gb(pa['smallest'][1])} ({E(pa['smallest'][0])})</td><td class='n'>{fmt_gb(pb['smallest'][1])} ({E(pb['smallest'][0])})</td></tr>
<tr><td><b>Recommended quant needs</b></td><td class='n'><b>{fmt_gb(pa['rec'][1])}</b> ({E(pa['rec'][0])})</td><td class='n'><b>{fmt_gb(pb['rec'][1])}</b> ({E(pb['rec'][0])})</td></tr>
<tr><td>Lossless build needs</td><td class='n'>{fmt_gb(pa['lossless'][1])}</td><td class='n'>{fmt_gb(pb['lossless'][1])}</td></tr>
</tbody></table>
<p><b>Verdict:</b> {E(verdict)} Capability is a different question (see benchmark leaderboards) — this page answers only <i>“which one fits my machine, and at what quality cost?”</i></p>
<h2>Will it run on your GPU?</h2>
<p class="note">At the recommended quant, 8K context:</p>
<table><thead><tr><th>Hardware</th><th style="text-align:right">VRAM/RAM</th><th>{E(name_a)}</th><th>{E(name_b)}</th></tr></thead><tbody>{rows}</tbody></table>
<div class="ad-slot"></div>
<h2>Full measured tables</h2>
<div class="grid"><a href="/{E(a['slug'])}/">{E(name_a)}<small>every quant, exact GB</small></a>
<a href="/{E(b['slug'])}/">{E(name_b)}<small>every quant, exact GB</small></a></div>"""
        jsonld = {"@context": "https://schema.org", "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "All models", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": f"{name_a} vs {name_b}", "item": f"{BASE}/{slug}/"}]},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": f"Which needs more VRAM, {name_a} or {name_b}?",
                 "acceptedAnswer": {"@type": "Answer", "text": f"At the recommended quant {name_a} needs {fmt_gb(pa['rec'][1])} and {name_b} needs {fmt_gb(pb['rec'][1])} (measured GGUF sizes + KV cache + overhead). {verdict}"}},
                {"@type": "Question", "name": f"Can I run {name_a} and {name_b} on 24GB?",
                 "acceptedAnswer": {"@type": "Answer", "text": f"{name_a}: {'yes' if pa['rec'][1] <= 24*0.92 else 'not at the recommended quant'} ({fmt_gb(pa['rec'][1])}). {name_b}: {'yes' if pb['rec'][1] <= 24*0.92 else 'not at the recommended quant'} ({fmt_gb(pb['rec'][1])})."}}]},
        ]}
        html_out = page(f"{slug}/index.html",
                        f"{name_a} vs {name_b}: VRAM & RAM requirements (measured, 2026)",
                        f"{name_a} needs {fmt_gb(pa['rec'][1])}, {name_b} needs {fmt_gb(pb['rec'][1])} at their recommended quants. Side-by-side hardware verdicts from measured GGUF files.",
                        body, f"{slug}/", jsonld)
        d = os.path.join(OUT, slug); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html_out)
        md = [f"# {name_a} vs {name_b} — hardware requirements (measured)", "",
              f"Page: {BASE}/{slug}/", "",
              f"| | {name_a} | {name_b} |", "|---|---|---|",
              f"| Params | {pba:.0f}B | {pbb:.0f}B |" if pba and pbb else "| Params | ? | ? |",
              f"| Recommended quant | {pa['rec'][0]} ({fmt_gb(pa['rec'][1])}) | {pb['rec'][0]} ({fmt_gb(pb['rec'][1])}) |",
              f"| Smallest build | {fmt_gb(pa['smallest'][1])} | {fmt_gb(pb['smallest'][1])} |",
              f"| Lossless | {fmt_gb(pa['lossless'][1])} | {fmt_gb(pb['lossless'][1])} |"]
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(md) + "\n")
        urls.append(f"{BASE}/{slug}/")
        md_lines.append(f"- [{name_a} vs {name_b}]({BASE}/{slug}/index.md): {fmt_gb(pa['rec'][1])} vs {fmt_gb(pb['rec'][1])}")
        make_og(os.path.join(d, "og.png"), f"{name_a} vs {name_b}",
                f"{fmt_gb(pa['rec'][1])} vs {fmt_gb(pb['rec'][1])}", "Measured hardware requirements")
    return urls, md_lines
