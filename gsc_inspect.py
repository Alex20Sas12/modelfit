# -*- coding: utf-8 -*-
"""gsc_inspect.py — «Запросить индексирование» для moneycalcs (порт 9232).
Рецепт скилла 07.09: нав-клик «Проверка URL» → DOM.focus(input.Ax4B8) → insertText → Enter
→ ждать вердикт → trusted-клик SPAN «ЗАПРОСИТЬ ИНДЕКСИРОВАНИЕ» → диалог успеха.
Прогресс: gsc_progress.json. Квота ~1-10/день — скрипт останавливается на «Квота превышена».
Запуск: python gsc_inspect.py [N]  (N = сколько URL попытаться, default 5)
"""
import json, asyncio, os, re, sys, urllib.request, urllib.parse
import websockets

PORT = 9232
BASE = "https://modelfit-eight.vercel.app"
RID = urllib.parse.quote(BASE + "/", safe="")
PROG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gsc_progress.json")

# приоритет: самые денежные запросы
URLS = [
    "/what-llm-can-i-run/",
    "/best-llm-for-24gb-vram/",
    "/best-llm-for-rtx-4090/",
    "/best-llm-for-rtx-3060/",
    "/best-llm-for-16gb-vram/",
    "/best-llm-for-8gb-vram/",
    "/best-llm-for-12gb-vram/",
    "/best-llm-for-rtx-3090/",
    "/best-llm-for-rtx-5090/",
    "/best-llm-for-macbook-pro-m4-24gb/",
    "/best-llm-for-macbook-air-16gb/",
    "/unsloth-kimi-k3-gguf/",
    "/sentieai-sentie1-0-3b-claude-fable-5-gpt5-2-sol-kimi-k3-glm-5-2-gguf/",
    "/atomicchat-kimi-k3-gguf/",
    "/unsloth-gemma-4-12b-it-gguf/",
    "/yuxinlu1-gemma-4-12b-agentic-fable5-composer2-5-v2-3-5x-tau2-gguf/",
    "/huihui-ai-huihui-deepseek-v4-flash-0731-abliterated-gguf/",
    "/jackrong-qwen3-5-9b-deepseek-v4-flash-gguf/",
    "/unsloth-deepseek-v4-flash-0731-gguf/",
    "/bartowski-meta-llama-3-1-8b-instruct-gguf/",
    "/lmstudio-community-meta-llama-3-1-8b-instruct-gguf/",
    "/",
    "/unsloth-qwen3-coder-30b-a3b-instruct-gguf/",
    "/unsloth-qwen3-8-27b-gguf/",
    "/ornith-ai-ornith-1-5-9b-gguf/",
    "/ornith-ai-ornith-1-5-35b-a3b-gguf/",
    "/ornith-ai-ornith-1-0-9b-gguf/",
    "/huihui-ai-huihui-qwen3-8-27b-abliterated-gguf/",
    "/jonathancoletti-qwen3-8-27b-uncensored-gguf/",
    "/hauhaucs-qwen3-8-27b-uncensored-hauhaucs-aggressive-mtp-gguf/",
    "/ornith-ai-ornith-1-0-35b-gguf/",
    "/lmstudio-community-qwen3-8-27b-gguf/",
    "/antirez-deepseek-v4-gguf/",
    "/hauhaucs-gemma-4-e4b-uncensored-hauhaucs-aggressive/",
    "/0bserverx-qwen3-8-27b-heretic-abliterated-uncensored-gguf/",
    "/handy-computer-nemotron-3-5-asr-streaming-0-6b-gguf/",
    "/handy-computer-parakeet-unified-en-0-6b-gguf/",
    "/unsloth-qwen3-5-9b-gguf/",
    "/ggml-org-gemma-4-e4b-it-gguf/",
    "/unsloth-qwen3-8-flash-next-gguf/",
    "/davidau-qwen3-5-9b-the-defiant-fable-uncensored-heretic-neo-imatrix-max-mtp-gguf/",
    "/unsloth-inkling-small-gguf/",
    "/ornith-ai-ornith-1-5-397b-gguf/",
    "/obliteratus-qwen3-8-27b-obliterated/",
    "/ggml-org-qwen3-8-27b-gguf/",
    "/unsloth-qwen3-6-35b-a3b-gguf/",
    "/liquidai-lfm2-5-2-6b-gguf/",
    "/davidau-qwen3-8-27b-turbo-fable-cold-fusion-735-882-heretic-uncensored-neo-coder-max-mtp-gguf/",
    "/unsloth-qwen3-6-27b-mtp-gguf/",
    "/unsloth-qwen3-6-27b-gguf/",
    "/ista-daslab-qwen3-8-27b-gsq-rco-gguf/",
    "/unsloth-qwen3-6-35b-a3b-mtp-gguf/",
    "/legraphista-glm-4-9b-chat-imat-gguf/",
    "/bartowski-endless-frontier-bigbang-v1-gguf/",
    "/hauhaucs-qwen3-6-35b-a3b-uncensored-hauhaucs-aggressive/",
    "/handy-computer-cohere-transcribe-03-2026-gguf/",
    "/unsloth-qwen3-5-4b-gguf/",
    "/unsloth-minimax-h3-gguf/",
    "/bartowski-xyzailab-xyz-aquila-mini-gguf/",
    "/davidau-qwen3-6-27b-fable-fusion-711-uncensored-heretic-nm-dau-neo-max-mtp-gguf/",
    "/final-bench-pocket-35b-gguf/",
    "/empero-ai-qwen3-8-4b-distill-gguf/",
    "/hauhaucs-qwen3-5-9b-uncensored-hauhaucs-aggressive/",
    "/prism-ml-ternary-bonsai-27b-gguf/",
    "/ankitai-parable-qwen3-8b-claude-fable-5-gguf/",
    "/unsloth-glm-5-3-flash-gguf/",
    "/ankitai-parable-qwen3-4b-claude-fable-5-gguf/",
    "/unsloth-qwen3-4b-gguf/",
    "/unsloth-glm-5-3-gguf/",
    "/peculiar-ragdoll-tiel-coder-35b-a3b-gguf/",
    "/qwen-qwen3-4b-gguf/",
    "/tvall43-qwen3-6-14b-a3b-fablevibes-gguf/",
    "/qwen-qwen3-8b-gguf/",
    "/prism-ml-ternary-bonsai-2-27b-gguf/",
    "/unsloth-glm-5-2-gguf/",
    "/tencent-hy-mt2-1-8b-gguf/",
    "/ankitai-parable-granite-4-1-3b-claude-fable-5-gguf/",
    "/ankitai-parable-granite-4-1-8b-claude-fable-5-gguf/",
    "/unsloth-kimi-k2-7-code-gguf/",
    "/ibm-granite-granite-4-2-30b-gguf/",
    "/unsloth-kimi-k2-6-gguf/",
    "/ibm-granite-granite-4-2-8b-gguf/",
    "/ibm-granite-granite-4-2-3b-gguf/",
    "/jackrong-qwen3-5-9b-glm5-1-distill-v1-gguf/",
    "/unsloth-llama-3-2-3b-instruct-gguf/",
    "/qwen-qwen3-14b-gguf/",
    "/bartowski-qwen2-5-7b-instruct-gguf/",
    "/davidau-qwen3-8-27b-twin-turbo-fable-cold-fusion-709-l-uncensored-nm-dau-neo-mtp-gguf/",
    "/unsloth-qwen2-5-vl-7b-instruct-gguf/",
    "/maziyarpanahi-llama-3-2-3b-instruct-gguf/",
    "/maziyarpanahi-qwen2-5-7b-instruct-gguf/",
    "/maziyarpanahi-mistral-small-instruct-2409-gguf/",
    "/openbmb-minicpm5-2b-gguf/",
    "/unsloth-phi-4-mini-instruct-gguf/",
    "/lmstudio-community-llama-3-2-3b-instruct-gguf/",
    "/bartowski-llama-3-2-3b-instruct-gguf/",
    "/ukisai-swift-qwen3-8-27b-gguf/",
    "/bartowski-qwen-qwen3-14b-gguf/",
    "/unsloth-gemma-3-4b-it-gguf/",
    "/lmstudio-community-gemma-3-4b-it-gguf/",
    "/lmstudio-community-qwen3-14b-gguf/",
    "/unsloth-gemma-3-12b-it-gguf/",
    "/bartowski-llama-3-2-3b-instruct-uncensored-gguf/",
    "/lmstudio-community-ministral-3-14b-reasoning-2512-gguf/",
    "/bartowski-google-gemma-3-4b-it-gguf/",
    "/unsloth-mistral-small-3-2-24b-instruct-2506-gguf/",
    "/lmstudio-community-ministral-3-3b-instruct-2512-gguf/",
    "/unsloth-kimi-k2-instruct-gguf/",
    "/dphn-dolphin3-0-llama3-1-8b-gguf/",
    "/unsloth-gemma-3-12b-it-qat-gguf/",
    "/bartowski-microsoft-phi-4-mini-instruct-gguf/",
    "/mistralai-ministral-3-14b-instruct-2512-gguf/",
    "/philbert440-qwen3-8-27b-uncensored-cyber-gguf/",
    "/peculiar-ragdoll-cyber-tiel-coder-35b-a3b-gguf-mtp/",
    "/unsloth-mistral-small-3-1-24b-instruct-2503-gguf/",
    "/lessthanthreeai-qwen3-8-27b-humanlike-chat-gguf/",
    "/ista-daslab-qwen3-8-flash-next-gsq-rco-gguf/",
    "/bartowski-ukisai-swift-qwen3-8-27b-gguf/",
    "/byteshape-qwen3-8-27b-gguf/",
    "/empero-ai-qwen3-8-35b-a3b-distill-gguf/",
    "/unsloth-kimi-k2-5-gguf/",
    "/unsloth-kimi-k2-thinking-gguf/",
    "/best-llm-for-32gb-vram/",
    "/best-llm-for-48gb-vram/",
    "/best-llm-for-64gb-vram/",
    "/best-llm-for-96gb-vram/",
    "/best-llm-for-rtx-5080/",
    "/best-llm-for-rtx-4080/",
    "/best-llm-for-rtx-4070-ti-super/",
    "/best-llm-for-rtx-4060-ti-16gb/",
    "/best-llm-for-rtx-3080/",
    "/best-llm-for-rtx-4060/",
    "/best-llm-for-rtx-3070/",
    "/best-llm-for-mac-studio-m3-ultra/",
]

def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)

def load_prog():
    try:
        return json.load(open(PROG, encoding="utf-8"))
    except Exception:
        return {}

async def main(limit=5):
    prog = load_prog()
    todo = [u for u in URLS if prog.get(u) in (None, "QUOTA", "TIMEOUT", "NOT_INDEXED_NO_BTN", "NOT_INDEXED_REQUEST_TIMEOUT")][:limit]
    if not todo:
        print("ALL DONE"); return
    tabs = get_tabs()
    t = next((x for x in tabs if x.get("type") == "page" and "search.google.com/search-console" in x.get("url", "")), None)
    if t is None:
        print("NO GSC TAB"); sys.exit(1)
    async with websockets.connect(t["webSocketDebuggerUrl"], max_size=60 * 1024 * 1024) as ws:
        _id = [1]
        async def call(m, p=None):
            _id[0] += 1
            await ws.send(json.dumps({"id": _id[0], "method": m, "params": p or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == _id[0]:
                    return msg.get("result", {})
        async def ev(e):
            r = await call("Runtime.evaluate", {"expression": e, "returnByValue": True})
            return r.get("result", {}).get("value")
        async def click(x, y):
            await call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}); await asyncio.sleep(0.15)
            await call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1}); await asyncio.sleep(0.15)
            await call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        async def enter():
            base = {"key": "Enter", "code": "Enter", "text": "\r", "unmodifiedText": "\r",
                    "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13}
            await call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **base})
            await call("Input.dispatchKeyEvent", {"type": "char", **base})
            await call("Input.dispatchKeyEvent", {"type": "keyUp", **base})
        await call("Page.enable"); await call("DOM.enable")
        await call("Page.bringToFront")

        async def click_text(rx):
            ok = await ev("""(() => {
              const re=new RegExp(%s,'i');
              const el=[...document.querySelectorAll('span,div,button,a')].find(e=>e.offsetWidth>0 && e.children.length===0 && re.test((e.textContent||'').trim()));
              if(!el) return false; el.scrollIntoView({block:'center'}); return true;
            })()""" % json.dumps(rx))
            if not ok: return False
            await asyncio.sleep(0.7)
            p = json.loads(await ev("""(() => {
              const re=new RegExp(%s,'i');
              const el=[...document.querySelectorAll('span,div,button,a')].find(e=>e.offsetWidth>0 && e.children.length===0 && re.test((e.textContent||'').trim()));
              if(!el) return JSON.stringify({err:1});
              const r=el.getBoundingClientRect();
              return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)});
            })()""" % json.dumps(rx)))
            if p.get("err"): return False
            await click(p["x"], p["y"])
            return True

        async def focus_inspect():
            doc = await call("DOM.getDocument", {"depth": -1})
            root = doc["root"]["nodeId"]
            for sel in ["input.Ax4B8", "input[aria-label*='Проверка']", "input.whsOnd"]:
                try:
                    r = await call("DOM.querySelector", {"nodeId": root, "selector": sel})
                    if r.get("nodeId"):
                        await call("DOM.focus", {"nodeId": r["nodeId"]})
                        return sel
                except Exception:
                    continue
            return None

        quota_hit = False
        for u in todo:
            if quota_hit: break
            full = BASE + u
            await call("Page.navigate", {"url": f"https://search.google.com/search-console?resource_id={RID}&hl=ru"})
            await asyncio.sleep(9)
            if "inspect" not in (await ev("location.href") or ""):
                await click_text("^(search\\s*)?проверка url$")
                await asyncio.sleep(3)
            sel = await focus_inspect()
            if not sel:
                prog[u] = "NO_INPUT"; json.dump(prog, open(PROG, "w", encoding="utf-8")); print(u, "NO_INPUT"); continue
            await call("Input.insertText", {"text": full})
            v = await ev("""(() => { const i=document.querySelector('input.Ax4B8')||document.querySelector('input[aria-label*=Проверка]'); return i? i.value : ''; })()""")
            if v != full:
                prog[u] = f"BAD_VALUE:{v[:50]}"; json.dump(prog, open(PROG, "w", encoding="utf-8")); print(u, "BAD_VALUE"); continue
            await enter()
            # ждать вердикт до 150с
            verdict = None
            for _ in range(30):
                await asyncio.sleep(5)
                txt = (await ev("document.body.innerText.replace(/\\s+/g,' ')") or "")
                for pat, name in [("URL нет в индексе Google", "NOT_INDEXED"), ("URL есть в Google", "INDEXED"),
                                  ("Квота превышена", "QUOTA"), ("Не удалось проверить", "FAIL_CHECK"),
                                  ("индексируется", "INDEXING")]:
                    if pat.lower() in txt.lower():
                        verdict = name; break
                if verdict: break
            if not verdict:
                prog[u] = "TIMEOUT"; json.dump(prog, open(PROG, "w", encoding="utf-8")); print(u, "TIMEOUT"); continue
            print(u, verdict)
            if verdict == "QUOTA":
                prog[u] = "QUOTA"; json.dump(prog, open(PROG, "w", encoding="utf-8")); quota_hit = True; break
            if verdict in ("INDEXED", "INDEXING"):
                prog[u] = verdict; json.dump(prog, open(PROG, "w", encoding="utf-8")); continue
            # кнопка ЗАПРОСИТЬ ИНДЕКСИРОВАНИЕ (SPAN, trusted-клик)
            ok = await click_text("запросить индексирование")
            if not ok:
                prog[u] = verdict + "_NO_BTN"; json.dump(prog, open(PROG, "w", encoding="utf-8")); print(u, "NO_BTN"); continue
            res = None
            for _ in range(24):
                await asyncio.sleep(5)
                txt = (await ev("document.body.innerText.replace(/\\s+/g,' ')") or "")
                if "отправлен запрос" in txt.lower() or "приоритетную очередь" in txt.lower():
                    res = "REQUESTED"; break
                if "квота превышена" in txt.lower():
                    res = "QUOTA"; break
            if res is None:
                # может, идёт проверка живого URL (до 2 мин)
                for _ in range(12):
                    await asyncio.sleep(10)
                    txt = (await ev("document.body.innerText.replace(/\\s+/g,' ')") or "")
                    if "отправлен запрос" in txt.lower(): res = "REQUESTED"; break
                    if "квота превышена" in txt.lower(): res = "QUOTA"; break
            prog[u] = res or verdict + "_REQUEST_TIMEOUT"
            json.dump(prog, open(PROG, "w", encoding="utf-8"), ensure_ascii=False)
            print(u, "->", prog[u])
            if res == "QUOTA": quota_hit = True
    print("DONE batch. progress:", json.dumps(load_prog(), ensure_ascii=False)[:300])

if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 5))
