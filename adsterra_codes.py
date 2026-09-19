# -*- coding: utf-8 -*-
"""adsterra_codes3.py — выдрать коды обоих плейсментов из DLGTEXT регуляром."""
import json, asyncio, re, urllib.request
import websockets
PORT = 9222
def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)
async def main():
    tabs = get_tabs()
    ws_url = next((t["webSocketDebuggerUrl"] for t in tabs if t.get("type")=="page" and "adsterra" in t.get("url","")), None)
    async with websockets.connect(ws_url, max_size=40*1024*1024) as ws:
        _id=[1]
        async def call(m,p=None):
            _id[0]+=1; await ws.send(json.dumps({"id":_id[0],"method":m,"params":p or {}}))
            while True:
                msg=json.loads(await ws.recv())
                if msg.get("id")==_id[0]: return msg.get("result",{})
        async def ev(e):
            r=await call("Runtime.evaluate",{"expression":e,"returnByValue":True}); return r.get("result",{}).get("value")
        async def click(x,y):
            await call("Input.dispatchMouseEvent",{"type":"mouseMoved","x":x,"y":y}); await asyncio.sleep(0.12)
            await call("Input.dispatchMouseEvent",{"type":"mousePressed","x":x,"y":y,"button":"left","clickCount":1}); await asyncio.sleep(0.12)
            await call("Input.dispatchMouseEvent",{"type":"mouseReleased","x":x,"y":y,"button":"left","clickCount":1})
        await call("Page.enable"); await call("Page.bringToFront")
        await call("Page.navigate", {"url": "https://beta.publishers.adsterra.com/websites"})
        await asyncio.sleep(10)
        chev = json.loads(await ev("""(() => {
          const el=[...document.querySelectorAll('*')].filter(e=>e.offsetParent!==null&&e.children.length===0&&/modelfit-eight.vercel.app/.test((e.innerText||'').trim()))[0];
          el.scrollIntoView({block:'center'});
          const row=el.closest('tr');
          const c=row.querySelector('button.MuiIconButton-root');
          const r=c.getBoundingClientRect();
          return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)});
        })()"""))
        await click(chev["x"], chev["y"])
        await asyncio.sleep(3)
        codes={}
        for name in ("NativeBanner", "SocialBar"):
            btn = json.loads(await ev("""(() => {
              const rows=[...document.querySelectorAll('tr')].filter(r=>r.offsetParent!==null && /"""+name+"""_1/.test(r.innerText||''));
              if(!rows.length) return JSON.stringify({err:'no row'});
              const b=[...rows[0].querySelectorAll('button,a')].find(b=>/получить код|get code/i.test(b.innerText||''));
              b.scrollIntoView({block:'center'});
              const r=b.getBoundingClientRect();
              return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)});
            })()"""))
            if btn.get("err"): print(name, btn); continue
            await click(btn["x"], btn["y"])
            await asyncio.sleep(4)
            txt = await ev("""(() => { const d=document.querySelector('[role=dialog],.MuiDialog-root,.MuiPopover-root'); return d? (d.innerText||'') : ''; })()""")
            m = re.findall(r'<script[^>]*src="https://pl\d+\.profitableratecpmnetwork\.com/[^"]*"[^>]*>\s*</script>|<div id="container-[a-f0-9]+"></div>', txt or "")
            if m:
                codes[name.lower()] = " ".join(m)
                print(name, "OK:", m)
            else:
                print(name, "NO CODE. dlg:", (txt or "")[:200])
            # закрыть: кнопка ЗАКРЫВАТЬ
            await ev("""(() => { const b=[...document.querySelectorAll('[role=dialog] button,.MuiDialog-root button,.MuiPopover-root button')].find(b=>/закрывать|закрыть|close/i.test((b.innerText||'').trim())); if(b)b.click(); })()""")
            await asyncio.sleep(2)
        if codes:
            json.dump(codes, open("adsterra_codes.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
            print("SAVED:", list(codes))
asyncio.run(main())
