# -*- coding: utf-8 -*-
"""pin_warmup.py — прогрев feecalcs: ищет чужие пины по фин-запросам и сохраняет 6-8 на свою доску.
Правило pinterest-factory #5: новый акк сначала прогрев (сохранения), потом 1 свой пин/день.
Поведение обычного пользователя; RepinResource/create — проверенный эндпоинт (chicfinds pin2_warmup.py).
"""
import json, asyncio, urllib.request, random
import websockets

PORT = 9274
BOARD_ID = "1122311238331228592"  # Local LLM Hardware
QUERIES = ["local llm setup", "ollama tips", "llama.cpp", "gaming pc build", "rtx 4090 setup",
           "ai tools", "home lab server", "gpu build", "chatgpt alternatives", "open source ai"]

def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)

async def main():
    tabs = get_tabs()
    t = next((x for x in tabs if x.get("type")=="page" and "pinterest" in x.get("url","")), None)
    if not t:
        print("NO TAB"); return
    async with websockets.connect(t["webSocketDebuggerUrl"], max_size=20*1024*1024) as ws:
        _id=[1]
        async def call(method, params=None):
            _id[0]+=1
            await ws.send(json.dumps({"id":_id[0],"method":method,"params":params or {}}))
            while True:
                m=json.loads(await ws.recv())
                if m.get("id")==_id[0]: return m.get("result",{})
        async def ev(expr):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return r.get("result",{}).get("value")
        await call("Runtime.enable"); await call("Page.enable"); await call("Page.bringToFront")
        await call("Emulation.setFocusEmulationEnabled", {"enabled": True})  # грабля: окно неактивно → Pinterest не гидрируется
        csrf = await ev("(() => (document.cookie.match(/csrftoken=([^;]+)/)||[])[1] || null)()")
        if not csrf:
            print("NO CSRF"); return

        queries = random.sample(QUERIES, 3)  # 3 запроса за раз = человек, не робот
        total = 0
        for q in queries:
            await call("Page.navigate", {"url": "https://www.pinterest.com/search/pins/?q=" + q.replace(" ", "%20")})
            await asyncio.sleep(random.uniform(8, 12))
            ids = json.loads(await ev("""
            (() => { const ids=[];
              document.querySelectorAll('div[data-test-id="pin"] a[href*="/pin/"], a[href*="/pin/"]').forEach(a => {
                const m=a.getAttribute('href').match(/\\/pin\\/(\\d+)\\//); if (m) ids.push(m[1]); });
              return JSON.stringify([...new Set(ids)].slice(0,20)); })()""") or "[]")
            random.shuffle(ids)
            for pid in ids[:random.randint(2,3)]:
                r = await ev("""
                (async () => { try {
                  const data = { options: { pin_id: '%s', board_id: '%s', description: '' }, context: {} };
                  const body = 'source_url=' + encodeURIComponent('https://www.pinterest.com/') + '&data=' + encodeURIComponent(JSON.stringify(data));
                  const resp = await fetch('/resource/RepinResource/create/', { method:'POST', credentials:'include',
                    headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':'%s','X-Requested-With':'XMLHttpRequest','X-Pinterest-AppState':'active'} , body});
                  return String(resp.status);
                } catch(e){ return 'ERR:'+e } })()""" % (pid, BOARD_ID, csrf))
                if r == "200" or r == "201":
                    total += 1
                await asyncio.sleep(random.uniform(6, 14))  # человеческая пауза
        print(f"warmup: сохранено {total} пинов (запросы: {queries})")

asyncio.run(main())
