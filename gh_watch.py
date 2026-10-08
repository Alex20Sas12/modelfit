# -*- coding: utf-8 -*-
"""gh_watch.py — GitHub leads: люди ПУБЛИЧНО спрашивают «сколько VRAM для модели X».
Копит в gh_watch.json, печатает 🚨-строки (подхватит вечерняя сводка). Ответ — полезный
коммент РУКАМИ через агента (массовый авто-спам = бан, правило answer/2801973).
Запуск: python gh_watch.py  (вызывается из refresh.py)"""
import json, os, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "gh_watch.json")
QUERIES = [
    '"how much vram" llama OR qwen OR gemma OR deepseek created:>%(since)s',
    '"vram requirements" gguf created:>%(since)s',
    '"can I run" ollama gpu created:>%(since)s',
    '"out of memory" gguf q4 created:>%(since)s',
    'llama.cpp "how much ram" created:>%(since)s',
]

def search(q):
    r = subprocess.run(["gh", "search", "issues", q, "--limit", "15", "--json",
                        "title,url,repository,createdAt,author"],
                       capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout or "[]")
    except Exception:
        return []

def main():
    data = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    seen = {x["url"] for x in data}
    since = (datetime.date.today() - datetime.timedelta(days=21)).isoformat()
    fresh = []
    for q in QUERIES:
        for it in search(q % {"since": since}):
            u = it.get("url", "")
            repo = it.get("repository", {}).get("nameWithOwner", "")
            # багрепорты самих llama.cpp/ollama = поддержка, не лиды; ищем личные/форк-issues
            # 08.10: сепар — trending-фермы (elicify/PrismBay/gittok) постят списки, не вопросы
            title = (it.get("title") or "")
            if not u or u in seen or repo.split("/")[0] in ("ggml-org", "ollama", "unslothai"):
                continue
            if re.search(r"Hugging Face Trending|\[OPEN-MESH\]|Registry disagreements", title, re.I):
                continue
            seen.add(u)
            fresh.append({"url": u, "repo": repo, "title": (it.get("title") or "")[:100],
                          "author": it.get("author", {}).get("login", ""),
                          "created": it.get("createdAt", "")[:10],
                          "found": datetime.date.today().isoformat()})
    if fresh:
        data.extend(fresh)
        json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for f in fresh[:5]:
        print(f"🚨 MF-GH: {f['repo']} — {f['title']} ({f['url']})")
    print(f"gh_watch: +{len(fresh)} (всего {len(data)})")

if __name__ == "__main__":
    main()
