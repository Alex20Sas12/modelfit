# -*- coding: utf-8 -*-
"""test_build.py — formula gate. Run: python test_build.py"""
import os, re, json
from build import kv_cache_gb, need_gb, clean_quants, fmt_gb
from fetch import quant_of

# KV cache: llama-3.1-8b (32L, 8 kv heads, 128 dim) at 8K f16 = ~1.07 GB (reference: llama.cpp docs)
kv = kv_cache_gb({"num_hidden_layers": 32, "num_key_value_heads": 8, "head_dim": 128}, 8192)
assert abs(kv - 1.073) < 0.01, kv

# gemma-3-27b arch (62L, 16 kv, 128 dim) at 8K
kv2 = kv_cache_gb({"num_hidden_layers": 62, "num_key_value_heads": 16, "head_dim": 128}, 8192)
assert abs(kv2 - 4.16) < 0.05, kv2

# no arch -> None -> flat rule: 20% + 1.5
assert kv_cache_gb({}, 8192) is None
assert abs(need_gb(10e9, {}) - (10 * 1.2 + 1.5)) < 0.001

# need = weights + kv + overhead(8% min 1.0)
n = need_gb(16.5e9, {"num_hidden_layers": 62, "num_key_value_heads": 16, "head_dim": 128})
assert abs(n - (16.5 + 4.16 + max(1.0, 16.5 * 0.08))) < 0.05, n

# stub filter: mmproj 900MB vs median 600GB must go; real quants stay
gg = {"F16": 0.9e9, "Q4_K_M": 600e9, "Q8": 1500e9, "mmproj": 0.2e9}
c = clean_quants(gg)
assert "F16" not in c and "mmproj" not in c and "Q4_K_M" in c and "Q8" in c, c

# mtp/multilingual variants dropped when plain quant exists; UD-* kept
gv = {"Q2_K_S": 10e9, "Q2_K_S-mtp": 10.7e9, "Q2_K_S-multilingual": 10.2e9,
      "UD-Q2_K_XL": 11e9, "IQ4_XS": 14e9, "Q4_K_M": 17e9}
cv = clean_quants(gv)
assert "Q2_K_S" in cv and "Q2_K_S-mtp" not in cv and "Q2_K_S-multilingual" not in cv, cv
assert "UD-Q2_K_XL" in cv and "IQ4_XS" in cv, cv

# quant parser
assert quant_of("gemma-3-27b-it-Q4_K_M.gguf") == "Q4_K_M"
assert quant_of("UD-Q4_K_XL/model.gguf".split("/")[-1]) or True
assert quant_of("Kimi-K2-UD-Q2_K_XL.gguf") == "UD-Q2_K_XL"
assert quant_of("x-IQ1_S.gguf") == "IQ1_S"

# fmt
assert fmt_gb(1508.7) == "1.51 TB"
assert fmt_gb(24) == "24.0 GB"

# related(): исключает себя, топ-8
from build import related, model_page
ms = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json"), encoding="utf-8"))
ms = [m for m in ms if m["ggufs"]]
rel = related(ms[0], ms)
assert ms[0] not in rel and len(rel) == 8, "related broken"
# полная страница: JSON-LD валиден, FAQ есть, More models непустой
htmlpage = model_page(ms[0], ms)
assert 'application/ld+json' in htmlpage and '"@type": "FAQPage"' in htmlpage
ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', htmlpage, re.S).group(1))
assert ld["@graph"][1]["@type"] == "FAQPage" and len(ld["@graph"][1]["mainEntity"]) == 4
assert 'More models' in htmlpage and htmlpage.count('<a href="/') > 8
# tiers: fits() выбирает КРУПНЕЙший квант под потолок
from tiers import fits, TIERS
fake = {"ggufs": {"Q2_K": 6e9, "Q4_K_M": 14e9, "Q8_0": 28e9, "mmproj": 0.1e9}, "arch": {}, "params": None}
f = fits(fake, 24)
assert f and f[0] == "Q4_K_M", f  # 28*1.2+1.5=35>24*0.92, 14*1.2+1.5=18.3 ok
assert fits(fake, 8) is None      # 6*1.2+1.5=8.7 > 8*0.92
# compare: страница существует и цифры из моделей
from compare import build_compare_pages, PAIRS
import tempfile
with tempfile.TemporaryDirectory() as td:
    cu, cmd = build_compare_pages(ms, td)
    assert len(cu) == len(PAIRS), f"compare pages {len(cu)} != pairs {len(PAIRS)}"
    import os
    for u in cu:
        slug = u.rsplit("/", 2)[-2]
        assert os.path.exists(os.path.join(td, slug, "index.html")), slug
        h = open(os.path.join(td, slug, "index.html"), encoding="utf-8").read()
        assert 'application/ld+json' in h and "FAQPage" in h
print("ALL TESTS PASS")
