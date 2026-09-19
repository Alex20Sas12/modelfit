# -*- coding: utf-8 -*-
"""cdp.py — универсальный CDP-драйвер для окна <port>. Команды:
  python cdp.py <port> nav <url>
  python cdp.py <port> state                     # url + title + innerText[:400]
  python cdp.py <port> js "<expr>"               # evaluate
  python cdp.py <port> click <x> <y>             # trusted click
  python cdp.py <port> type "<text>"             # insertText в фокус
  python cdp.py <port> shot <file>               # скриншот
"""
import asyncio, base64, json, sys, urllib.request
import websockets

async def main():
    port, cmd = sys.argv[1], sys.argv[2]
    with urllib.request.urlopen(f"http://localhost:{port}/json", timeout=5) as r:
        tabs = json.load(r)
    tab = next((t for t in tabs if t.get("type") == "page" and not t.get("url", "").startswith("devtools")), None)
    if not tab:
        print("NO TAB"); return
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=40 * 1024 * 1024) as ws:
        _id = [1]
        async def call(m, p=None):
            _id[0] += 1
            await ws.send(json.dumps({"id": _id[0], "method": m, "params": p or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == _id[0]:
                    return msg.get("result", {})
        async def ev(e, aw=False):
            r = await call("Runtime.evaluate", {"expression": e, "returnByValue": True, "awaitPromise": aw})
            return r.get("result", {}).get("value")
        await call("Page.enable")
        await call("Emulation.setFocusEmulationEnabled", {"enabled": True})
        if cmd == "nav":
            await call("Page.navigate", {"url": sys.argv[3]})
            await asyncio.sleep(8)
            print(await ev("location.href + ' | ' + document.title"))
        elif cmd == "state":
            print(await ev("JSON.stringify({url:location.href,title:document.title,text:document.body.innerText.replace(/\\s+/g,' ').slice(0,400)})"))
        elif cmd == "js":
            v = await ev(sys.argv[3])
            print(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
        elif cmd == "click":
            x, y = int(sys.argv[3]), int(sys.argv[4])
            await call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
            await asyncio.sleep(0.12)
            await call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
            await asyncio.sleep(0.12)
            await call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
            print("clicked", x, y)
        elif cmd == "type":
            await call("Input.insertText", {"text": sys.argv[3]})
            print("typed")
        elif cmd == "shot":
            r = await call("Page.captureScreenshot", {"format": "png"})
            open(sys.argv[3], "wb").write(base64.b64decode(r["data"]))
            print("saved", sys.argv[3])

asyncio.run(main())
