# -*- coding: utf-8 -*-
"""pin_board.py — создать доску ModelFit (окно 9274, юзер alexford0289mf)."""
import json, asyncio
import websockets, urllib.request

PORT = 9274
BOARD = "Local LLM Hardware"

def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)

async def main():
    t = next(x for x in get_tabs() if x.get("type") == "page" and "pinterest" in x.get("url", ""))
    async with websockets.connect(t["webSocketDebuggerUrl"], max_size=40 * 1024 * 1024) as ws:
        _id = [0]
        async def call(m, p=None):
            _id[0] += 1
            await ws.send(json.dumps({"id": _id[0], "method": m, "params": p or {}}))
            while True:
                x = json.loads(await ws.recv())
                if x.get("id") == _id[0]:
                    return x.get("result", {})
        async def ev(e):
            return (await call("Runtime.evaluate", {"expression": e, "returnByValue": True})).get("result", {}).get("value")
        async def click(x, y):
            await call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}); await asyncio.sleep(0.15)
            await call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1}); await asyncio.sleep(0.15)
            await call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        async def wait_for(js_expr, tries=12, gap=1.5):
            for _ in range(tries):
                v = await ev(js_expr)
                if v: return v
                await asyncio.sleep(gap)
            return None
        await call("Page.enable"); await call("Page.bringToFront")
        await call("Emulation.setFocusEmulationEnabled", {"enabled": True})
        await call("Page.navigate", {"url": "https://www.pinterest.com/alexford0289mf/_boards/"})
        await asyncio.sleep(10)
        p = json.loads(await wait_for("""(()=>{const els=[...document.querySelectorAll('*')].filter(e=>e.offsetParent!==null&&e.children.length===0&&/Создать доску/i.test((e.textContent||'').trim())); if(!els.length) return null; const r=els[0].getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""") or '{"err":1}')
        print("1 create-board:", p)
        if p.get("err"):
            print("PAGE:", (await ev("document.body.innerText") or "")[:300].replace("\n", " "))
            return
        await click(p["x"], p["y"])
        inp = json.loads(await wait_for("""(()=>{const i=document.querySelector('input[placeholder*=название],input[placeholder*=Name]'); if(!i||!i.offsetParent) return null; const r=i.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""") or '{"err":1}')
        print("2 name input:", inp)
        if inp.get("err"):
            print("PAGE:", (await ev("document.body.innerText") or "")[:300]); return
        await click(inp["x"], inp["y"]); await asyncio.sleep(0.5)
        await call("Input.insertText", {"text": BOARD}); await asyncio.sleep(1.5)
        print("3 value:", await ev("document.querySelector('input[placeholder*=название],input[placeholder*=Name]').value"))
        ok = json.loads(await wait_for("""(()=>{const b=[...document.querySelectorAll('button')].filter(e=>e.offsetParent!==null&&!e.disabled&&/^Создать$|^Create$/i.test((e.textContent||'').trim())); if(!b.length) return null; const d=b[b.length-1]; const r=d.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""", tries=6) or '{"err":1}')
        print("4 submit:", ok)
        if ok.get("err"): return
        await click(ok["x"], ok["y"]); await asyncio.sleep(8)
        print("5 URL:", await ev("location.href"))
        print("5 TEXT:", (await ev("document.body.innerText") or "")[:250].replace("\n", " "))

asyncio.run(main())
