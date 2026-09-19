# -*- coding: utf-8 -*-
"""adsterra_add.py — добавить modelfit-eight.vercel.app в Adsterra (окно 9222).
Запуск: python adsterra_add.py"""
import json, asyncio, sys, urllib.request
import websockets

PORT = 9222
SITE = "https://modelfit-eight.vercel.app"

async def main():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        tabs = json.load(r)
    ws_url = next((t["webSocketDebuggerUrl"] for t in tabs
                   if t.get("type") == "page" and "adsterra" in t.get("url", "")), None)
    if not ws_url:
        print("NO ADSTERRA TAB"); sys.exit(1)
    async with websockets.connect(ws_url, max_size=40 * 1024 * 1024) as ws:
        _id = [1]
        async def call(method, params=None):
            _id[0] += 1
            await ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == _id[0]:
                    return msg.get("result", {})
        async def ev(expr, await_p=False):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_p})
            return r.get("result", {}).get("value")
        await call("Page.enable")
        await call("Emulation.setFocusEmulationEnabled", {"enabled": True})
        if "sites/create" not in await ev("location.href"):
            await call("Page.navigate", {"url": "https://publishers.adsterra.com/sites/create"})
            await asyncio.sleep(6)
        state = await ev("JSON.stringify({url:location.href, body:document.body.innerText.replace(/\\s+/g,' ').slice(0,600), inputs:[...document.querySelectorAll('input,select,textarea')].filter(i=>i.offsetParent!==null).map(i=>({n:i.name,id:i.id,ph:i.placeholder,t:i.type,opts:i.tagName=='SELECT'?[...i.options].map(o=>o.value+':'+o.text).slice(0,10):undefined}))})")
        print("STATE:", state)

asyncio.run(main())
