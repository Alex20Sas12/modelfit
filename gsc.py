# -*- coding: utf-8 -*-
"""gsc.py — драйвер GSC для moneycalcs (окно dirs 9232, Google alexford0289).
Команды: state | addprop | token | verify | sitemap
UI 2026 по скиллу search-console-indexing: U26fgb/RDPZE, insertText, своя вкладка.
"""
import json, asyncio, sys, urllib.request, urllib.parse
import websockets

PORT = 9232
SITE = "https://modelfit-eight.vercel.app/"
PROP = "https://modelfit-eight.vercel.app/"
GSC = "https://search.google.com/search-console?hl=ru"

def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)

def open_tab(url):
    req = urllib.request.Request(f"http://localhost:{PORT}/json/new?{urllib.parse.quote(url, safe=':/?=&%')}", method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)

class CDP:
    def __init__(self, ws): self.ws, self._id = ws, [1]
    async def call(self, m, p=None):
        self._id[0] += 1
        await self.ws.send(json.dumps({"id": self._id[0], "method": m, "params": p or {}}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == self._id[0]:
                return msg.get("result", {})
    async def ev(self, expr):
        r = await self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return r.get("result", {}).get("value")
    async def click(self, x, y):
        await self.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}); await asyncio.sleep(0.1)
        await self.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1}); await asyncio.sleep(0.1)
        await self.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
    async def type_text(self, text):
        await self.call("Input.insertText", {"text": text})
    async def key(self, key, code=None, vk=None):
        vk = vk or ord(key.upper()) if len(key) == 1 else vk
        base = {"key": key, "code": code or "", "windowsVirtualKeyCode": vk or 0, "nativeVirtualKeyCode": vk or 0}
        await self.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **base})
        await self.call("Input.dispatchKeyEvent", {"type": "char", **base, "text": key, "unmodifiedText": key})
        await self.call("Input.dispatchKeyEvent", {"type": "keyUp", **base})

async def get_cdp(url=None):
    """своя вкладка: найти gsc или создать"""
    tabs = get_tabs()
    t = next((t for t in tabs if t.get("type") == "page" and "search.google.com/search-console" in t.get("url", "")), None)
    if t is None:
        t = open_tab(url or GSC)
        await asyncio.sleep(9)
        tabs = get_tabs()
        t = next((x for x in tabs if x.get("id") == t["id"]), t)
    ws = await websockets.connect(t["webSocketDebuggerUrl"], max_size=60*1024*1024)
    c = CDP(ws)
    await c.call("Page.enable"); await c.call("Runtime.enable")
    await c.call("Page.bringToFront")
    if url:
        await c.call("Page.navigate", {"url": url}); await asyncio.sleep(9)
    return c

async def span_click(c, text_re, scope="document"):
    """клик по .U26fgb-предку span с текстом (не disabled). Возвращает True/False"""
    pos = json.loads(await c.ev(f"""(() => {{
      const els=[...{scope}.querySelectorAll('span,div,button')].filter(e=>e.offsetParent!==null && e.children.length===0 && {text_re}.test((e.innerText||'').trim()));
      for (const e of els) {{
        let p=e, btn=null;
        for (let i=0;i<6 && p;i++) {{ if (p.classList && p.classList.contains('U26fgb')) {{ btn=p; break; }} p=p.parentElement; }}
        const t=btn||e;
        if (t.getAttribute && (t.getAttribute('aria-disabled')==='true' || (t.classList&&t.classList.contains('RDPZE')))) continue;
        t.scrollIntoView({{block:'center'}});
        const r=t.getBoundingClientRect();
        if (r.x<0||r.y<0||r.x>innerWidth||r.y>innerHeight) continue;
        return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),txt:(e.innerText||'').trim().slice(0,30)}});
      }}
      return JSON.stringify({{err:'not found'}});
    }})()"""))
    if pos.get("err"): return False
    await c.click(pos["x"], pos["y"])
    return pos

async def cmd_state():
    c = await get_cdp(GSC)
    print("URL:", await c.ev("location.href"))
    print("TITLE:", await c.ev("document.title"))
    print("ACCOUNT:", await c.ev("""(() => { const m=document.body.innerText.match(/[\\w.+-]+@gmail\\.com/g); return JSON.stringify([...new Set(m||[])]); })()"""))
    print("TEXT:", (await c.ev("document.body.innerText.replace(/\\s+/g,' ')") or "")[:600])
    props = await c.ev("""JSON.stringify([...document.querySelectorAll('[data-property-id],a[href*=resource_id]')].map(e=>e.getAttribute('data-property-id')||e.getAttribute('href')).filter(x=>x&&/https?%3A|sc-domain/.test(x)).slice(0,20))""")
    print("PROPS:", props)

async def cmd_addprop():
    c = await get_cdp(GSC)
    # открыть селектор ресурса → «Добавить ресурс»
    await c.ev("""(() => { const s=document.querySelector('span.truncate'); if(s) s.click(); })()""")
    await asyncio.sleep(2)
    r = await span_click(c, "/добавить ресурс|add property/i")
    print("add property click:", r)
    await asyncio.sleep(3)
    print("DLG:", (await c.ev("document.body.innerText.replace(/\\s+/g,' ')") or "")[:400])
    # UI2026: сначала «Добавить сайт»
    r = await span_click(c, "/^добавить сайт$|add site/i")
    if r:
        print("add site click:", r); await asyncio.sleep(3)
    # правое поле = URL-префикс. Ищем инпут по контексту секции
    pos = json.loads(await c.ev("""(() => {
      const inps=[...document.querySelectorAll('input[type=text],input:not([type])')].filter(i=>i.offsetParent!==null);
      // секция URL-префикс: инпут, у которого в предках текст про https://
      for (const i of inps) {
        let p=i, ok=false;
        for (let k=0;k<8&&p;k++){ if((p.innerText||'').includes('https://') && (p.innerText||'').length<400){ok=true;break;} p=p.parentElement; }
        if (ok || /url|префикс/i.test(i.getAttribute('aria-label')||'')) {
          i.scrollIntoView({block:'center'});
          const r=i.getBoundingClientRect();
          return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),ph:i.placeholder||'',al:i.getAttribute('aria-label')||''});
        }
      }
      return JSON.stringify({err:'no input', n:inps.length, phs:inps.map(i=>i.placeholder).slice(0,5)});
    })()"""))
    print("input:", pos)
    if pos.get("err"): return
    await c.click(pos["x"], pos["y"]); await asyncio.sleep(0.5)
    await c.type_text(PROP); await asyncio.sleep(1)
    print("value:", await c.ev("""(() => { const i=[...document.querySelectorAll('input')].filter(x=>x.offsetParent!==null && x.value.includes('feecalcs'))[0]; return i? i.value : 'EMPTY'; })()"""))
    r = await span_click(c, "/продолжить|continue/i")
    print("continue:", r)
    await asyncio.sleep(4)
    print("AFTER:", (await c.ev("document.body.innerText.replace(/\\s+/g,' ')") or "")[:500])

async def cmd_token():
    c = await get_cdp()
    # раскрыть секцию «Тег HTML»
    r = await span_click(c, "/тег html|html tag/i")
    await asyncio.sleep(2)
    tok = await c.ev("""(() => {
      const tas=[...document.querySelectorAll('textarea')].filter(t=>t.offsetParent!==null && /google-site-verification/.test(t.value||''));
      if (tas.length) return tas[0].value;
      const m=document.body.innerHTML.match(/google-site-verification[\"']? content=[\"']([^\"']+)[\"']/i) || document.body.innerHTML.match(/content=\\\\?[\"']([\\w-]{40,})\\\\?[\"'][^>]*google-site-verification/i);
      return m? m[1] : '';
    })()""")
    print("TOKEN:", tok)
    if tok:
        open("gsc_token_fee.txt", "w").write(tok.strip())
        print("saved gsc_token_fee.txt")

async def cmd_verify():
    c = await get_cdp()
    # кнопка ПОДТВЕРДИТЬ после textarea с токеном
    pos = json.loads(await c.ev("""(() => {
      const ta=[...document.querySelectorAll('textarea')].filter(t=>/google-site-verification/.test(t.value||''))[0];
      const taY = ta? ta.getBoundingClientRect().y : -1e9;
      const els=[...document.querySelectorAll('span,div')].filter(e=>e.offsetParent!==null && e.children.length===0 && /подтвердить|verify/i.test((e.innerText||'').trim()));
      let best=null;
      for (const e of els) {
        let p=e, btn=null;
        for (let i=0;i<6&&p;i++){ if(p.classList&&p.classList.contains('U26fgb')){btn=p;break;} p=p.parentElement; }
        const t=btn||e;
        if (t.classList&&t.classList.contains('RDPZE')) continue;
        t.scrollIntoView({block:'center'});
        const r=t.getBoundingClientRect();
        if (r.y<taY-50) continue;
        if (!best || r.y<best.y) best={x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),txt:(e.innerText||'').trim()};
      }
      return JSON.stringify(best||{err:'no verify btn'});
    })()"""))
    print("verify btn:", pos)
    if pos.get("err"): return
    await c.click(pos["x"], pos["y"])
    for i in range(12):
        await asyncio.sleep(5)
        txt = (await c.ev("document.body.innerText.replace(/\\s+/g,' ')") or "")
        if "подтвержден" in txt.lower() or "владелец" in txt.lower() or "verified" in txt.lower():
            print(f"[{i}] VERIFIED:", txt[:300]); return
        print(f"[{i}]", txt[:160])
    print("TIMEOUT — проверить вручную")

async def cmd_sitemap():
    rid = urllib.parse.quote(PROP, safe="")
    c = await get_cdp(f"https://search.google.com/search-console/sitemaps?resource_id={rid}&hl=ru")
    # инпут по aria-label
    ok = await c.ev("""(() => {
      const i=[...document.querySelectorAll('input')].filter(x=>x.offsetParent!==null && /sitemap/i.test(x.getAttribute('aria-label')||''))[0];
      if(!i) return 'no input';
      i.scrollIntoView({block:'center'}); i.focus();
      return 'focused:'+document.activeElement.tagName;
    })()""")
    print("sitemap input:", ok)
    if not ok.startswith("focused"): return
    pos = json.loads(await c.ev("""(() => { const i=[...document.querySelectorAll('input')].filter(x=>x.offsetParent!==null && /sitemap/i.test(x.getAttribute('aria-label')||''))[0]; const r=i.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}); })()"""))
    await c.click(pos["x"], pos["y"]); await asyncio.sleep(0.5)
    # insertText + точка отдельно (грабли скилла)
    await c.type_text("sitemap")
    await c.call("Input.dispatchKeyEvent", {"type": "char", "key": ".", "text": ".", "windowsVirtualKeyCode": 190, "nativeVirtualKeyCode": 190})
    await c.type_text("xml")
    val = await c.ev("""(() => { const i=[...document.querySelectorAll('input')].filter(x=>x.offsetParent!==null && /sitemap/i.test(x.getAttribute('aria-label')||''))[0]; return i.value; })()""")
    print("value:", val)
    if val != "sitemap.xml":
        print("ЗНАЧЕНИЕ НЕВЕРНО — не отправляю"); return
    r = await span_click(c, "/^отправить$|submit/i")
    print("submit:", r)
    await asyncio.sleep(6)
    print("AFTER:", (await c.ev("document.body.innerText.replace(/\\s+/g,' ')") or "")[:400])

CMDS = {"state": cmd_state, "addprop": cmd_addprop, "token": cmd_token, "verify": cmd_verify, "sitemap": cmd_sitemap}
if __name__ == "__main__":
    asyncio.run(CMDS[sys.argv[1]]())
