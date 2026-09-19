# -*- coding: utf-8 -*-
"""fetch.py — pull live model data from HuggingFace public API (no key).
Output: models.json — list of {id, name, slug, params, downloads, ggufs:{quant:bytes}, arch:{...}}
Run: python fetch.py
"""
import json, re, sys, time, urllib.request, urllib.parse, os

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://huggingface.co/api"
UA = {"User-Agent": "modelfit/1.0"}
HYPE = ["kimi-k3", "gemma-4", "deepseek-v4", "qwen3.8", "glm-5", "kimi-k2"]  # ponytail: refresh list when new wave drops
# low/mid-tier popular models so "best llm for 8/12/16GB" pages have real data
SMALL = ["qwen3-8b", "qwen3-4b", "llama-3.1-8b", "phi-4", "gemma-3-4b", "gemma-3-12b",
         "ministral-3", "qwen2.5-7b", "qwen3-14b", "mistral-small", "llama-3.2-3b", "granite-4"]

def get(url, tries=2):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return None
            time.sleep(1.5)

def search_ids(kw, limit=8):
    j = get(f"{API}/models?filter=gguf&search={urllib.parse.quote(kw)}&sort=downloads&direction=-1&limit={limit}")
    return [m["id"] for m in (j or [])]

def trending_ids(limit=40):
    j = get(f"{API}/models?filter=gguf&sort=trendingScore&direction=-1&limit={limit}")
    return [m["id"] for m in (j or [])]

def top_ids(limit=100):
    """Top GGUF repos by downloads — covers every VRAM tier, not just the hype."""
    j = get(f"{API}/models?filter=gguf&sort=downloads&direction=-1&limit={limit}")
    return [m["id"] for m in (j or [])]

def quant_of(path):
    # "gemma-3-27b-it-Q4_K_M.gguf" -> "Q4_K_M"; split files "-00001-of-00005" collapse
    path = re.sub(r"-\d{4,}-of-\d{4,}", "", path)  # shard suffix first, else every shard becomes its own quant
    m = re.search(r"(Q\d+_\d+(_[SMLX]+)?|IQ\d+_[A-Z_]+|UD-[A-Z0-9_]+|Q\d+_\d|F16|BF16|Q\d+_[A-Z]+_XL)", path)
    if m:
        return m.group(1)
    m = re.search(r"-(Q\d[A-Za-z0-9_.\-]*?)\.gguf", path)
    return m.group(1) if m else None

def clean_name(mid):
    n = mid.split("/", 1)[-1]
    n = re.sub(r"-(GGUF|gguf|IQ\d.*|Q\d.*)$", "", n, flags=re.I)
    n = re.sub(r"[-_]+$", "", n)
    return n

def fetch_model(mid):
    det = get(f"{API}/models/{mid}")
    if not det or det.get("gated") or det.get("private") or det.get("disabled"):
        return None
    ggufs = {}
    def walk(path):
        tree = get(f"{API}/models/{mid}/tree/main/{path}") or []
        for f in tree:
            if f.get("type") == "directory":
                if re.search(r"(Q\d|IQ\d|F16|BF16)", f["path"], re.I):
                    walk(urllib.parse.quote(f["path"]))
            elif f["path"].endswith(".gguf"):
                base = f["path"].rsplit("/", 1)[-1].lower()
                if base.startswith(("mmproj", "mtp", "vision", "clip", "textmm")):
                    continue  # auxiliary modules, not full-model weights
                q = quant_of(f["path"]) or quant_of(f["path"].split("/")[-2] if "/" in f["path"] else "")
                if q:
                    ggufs[q] = ggufs.get(q, 0) + f.get("size", 0)  # sums split shards
    walk("")
    if len(ggufs) < 3:
        return None
    # arch from config.json (best effort; unsloth repos carry it)
    arch = {}
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"https://huggingface.co/{mid}/resolve/main/config.json", headers=UA), timeout=20) as r:
            c = json.loads(r.read().decode("utf-8", "replace"))
            tc = c.get("text_config") or c
            for k in ("num_hidden_layers", "num_key_value_heads", "head_dim", "num_attention_heads",
                      "hidden_size", "num_experts", "model_type", "max_position_embeddings"):
                if isinstance(tc.get(k), int):
                    arch[k] = tc[k]
            arch["model_type"] = tc.get("model_type") or c.get("model_type") or ""
    except Exception:
        pass
    st = (det.get("safetensors") or {}).get("total")
    return {
        "id": mid, "name": clean_name(mid),
        "slug": re.sub(r"[^a-z0-9]+", "-", mid.lower()).strip("-"),
        "params": st, "downloads": det.get("downloads", 0), "likes": det.get("likes", 0),
        "lastModified": det.get("lastModified", "")[:10],
        "ggufs": ggufs, "arch": arch,
        "tags": [t for t in det.get("tags", []) if t in ("moe", "text-generation")],
    }

def main():
    ids = []
    for kw in HYPE + SMALL:
        ids += search_ids(kw, limit=5)
    ids += trending_ids()
    ids += top_ids()
    seen, out = set(), []
    for mid in ids:
        if mid in seen:
            continue
        seen.add(mid)
        m = fetch_model(mid)
        if m:
            out.append(m)
            print("ok", mid, len(m["ggufs"]), "quants", flush=True)
        time.sleep(0.2)
        if len(out) >= 110:
            break
    out.sort(key=lambda x: -x["downloads"])
    with open(os.path.join(HERE, "models.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"saved {len(out)} models -> models.json")

if __name__ == "__main__":
    main()
