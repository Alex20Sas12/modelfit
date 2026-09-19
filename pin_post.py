# -*- coding: utf-8 -*-
"""pin_post.py — Е2Е публикация одного пина: картинка → create-tool → описание/ссылка → доска → Опубликовать.
Usage: python pin_post.py <slug> "<title>" "<desc>" "<link>" [board]
Предусловия: окно 9271 (chrome-launch.py feecalcs), картинка pins/<slug>.png (pin_gen.py).
Порядок ПОЛЕЙ КРИТИЧЕН: сначала описание (по нему активируется выпадашка доски), потом доска.
Заголовок = contenteditable «Опишите ваш пин» (не input!). Клик «Опубликовать» может дать «Изменения сохранены»
(черновик) — тогда открыть черновик и нажать «Опубликовать» повторно.
"""
import json, asyncio, os, sys
import websockets, urllib.request

PORT = 9274
BOARD = "Local LLM Hardware"

def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)

async def main(slug, title, desc, link, board=BOARD):
    img = os.path.abspath(os.path.join(os.path.dirname(__file__), "pins", slug + ".png"))
    assert os.path.exists(img), f"нет картинки {img} — сначала pin_gen.py"
    pin_tabs = [x for x in get_tabs() if x.get("type")=="page" and "pinterest" in x.get("url","")]
    if not pin_tabs:
        # новое окно стартует с newtab/blank: берём любую page-вкладку, в main() наведём её на Pinterest
        pin_tabs = [x for x in get_tabs() if x.get("type")=="page" and x.get("webSocketDebuggerUrl")]
    assert pin_tabs, "окно 9271 есть, но page-вкладок нет"
    t = pin_tabs[0]
    async with websockets.connect(t["webSocketDebuggerUrl"], max_size=40*1024*1024) as ws:
        _id=[0]
        async def call(m,p=None):
            _id[0]+=1
            await ws.send(json.dumps({"id":_id[0],"method":m,"params":p or {}}))
            while True:
                x=json.loads(await ws.recv())
                if x.get("id")==_id[0]: return x.get("result",{})
        async def ev(e):
            return (await call("Runtime.evaluate",{"expression":e,"returnByValue":True})).get("result",{}).get("value")
        async def click(x,y):
            await call("Input.dispatchMouseEvent",{"type":"mouseMoved","x":x,"y":y}); await asyncio.sleep(0.15)
            await call("Input.dispatchMouseEvent",{"type":"mousePressed","x":x,"y":y,"button":"left","clickCount":1}); await asyncio.sleep(0.15)
            await call("Input.dispatchMouseEvent",{"type":"mouseReleased","x":x,"y":y,"button":"left","clickCount":1})
        async def wait_for(js, tries=12, gap=2):
            for _ in range(tries):
                v = await ev(js)
                if v: return v
                await asyncio.sleep(gap)
            return None
        await call("Page.enable"); await call("Page.bringToFront"); await call("DOM.enable")
        await call("Emulation.setFocusEmulationEnabled", {"enabled": True})  # грабля: окно неактивно → Pinterest не гидрируется

        board_url = "https://www.pinterest.com/alexford0289mf/" + board.lower().replace(" ", "-") + "/"
        async def read_count():
            await call("Page.navigate", {"url": board_url})
            await asyncio.sleep(8)
            n = await ev("""(()=>{const m=(document.body.innerText||'').match(/·\\s*(\\d+)\\s*пин/); return m? +m[1] : -1})()""")
            return n if n is not None else -1

        before = await read_count()
        print("0 board count:", before)

        # 1. свежая форма
        await call("Page.navigate", {"url":"https://www.pinterest.com/pin-creation-tool/"})
        await asyncio.sleep(9)
        # 2. файл
        doc = (await call("DOM.getDocument", {"depth":-1}))["root"]["nodeId"]
        fnode = (await call("DOM.querySelector", {"nodeId":doc, "selector":"input[type=file]"})).get("nodeId")
        assert fnode, "нет file input"
        await call("DOM.setFileInputFiles", {"nodeId":fnode, "files":[img]})
        await asyncio.sleep(10)
        # 3. описание (input placeholder)
        r = await ev("""(()=>{const d=document.querySelector('input[placeholder*="описание пина"],textarea[placeholder*="описание пина"]'); if(!d) return null; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(d,''); d.dispatchEvent(new Event('input',{bubbles:true})); d.focus(); return JSON.stringify({ok:1})})()""")
        assert r, "нет поля описания"
        await call("Input.insertText", {"text": desc}); await asyncio.sleep(1.5)
        # 4. ссылка
        r = await ev("""(()=>{const d=document.querySelector('input[type=url]'); if(!d) return null; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(d,''); d.dispatchEvent(new Event('input',{bubbles:true})); d.focus(); return JSON.stringify({ok:1})})()""")
        if r:
            await call("Input.insertText", {"text": link}); await asyncio.sleep(1.5)
        # 5. заголовок (contenteditable) — после описания, иначе съестся
        ce = json.loads(await ev("""(()=>{const d=document.querySelector('[contenteditable=true]'); if(!d) return JSON.stringify({err:1}); d.scrollIntoView({block:'center'}); const r=d.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""") or '{"err":1}')
        if not ce.get("err"):
            await click(ce["x"], ce["y"]); await asyncio.sleep(0.4)
            await call("Input.insertText", {"text": title}); await asyncio.sleep(1)
        # 6. доска
        sel = await ev("""(()=>{const d=document.querySelector('[data-test-id=board-dropdown-item-selected]'); return d?(d.innerText||'').trim():''})()""") or ""
        if board.lower() not in sel.lower():
            p = json.loads(await ev("""(()=>{const d=document.querySelector('[data-test-id=board-dropdown-item-selected],[data-test-id*=board-dropdown]'); if(!d) return JSON.stringify({err:1}); d.scrollIntoView({block:'center'}); const r=d.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""") or '{"err":1}')
            assert not p.get("err"), "нет дропдауна доски"
            await click(p["x"], p["y"]); await asyncio.sleep(3)
            o = json.loads(await ev("""(()=>{const it=[...document.querySelectorAll('[role=option],li,div')].filter(e=>e.offsetParent!==null&&e.children.length===0&&(e.textContent||'').trim()===%s); if(!it.length) return JSON.stringify({err:1}); const r=it[0].getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""" % json.dumps(board)) or '{"err":1}')
            assert not o.get("err"), "нет доски в списке"
            await click(o["x"], o["y"]); await asyncio.sleep(2)
        # 7. Опубликовать
        pub = json.loads(await wait_for("""(()=>{const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent!==null&&!e.disabled&&/^Опубликовать$/i.test((e.textContent||'').trim())); if(!b) return null; const r=b.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""") or '{"err":1}')
        assert not pub.get("err"), "нет активной кнопки Опубликовать"
        await click(pub["x"], pub["y"]); await asyncio.sleep(12)

        # 8. первый клик часто сохраняет ЧЕРНОВИК («Изменения сохранены») — тогда открыть черновик и опубликовать повторно
        frag = json.dumps(desc[:25])
        for attempt in range(2):
            await call("Page.navigate", {"url":"https://www.pinterest.com/pin-creation-tool/"})
            await asyncio.sleep(8)
            has_draft = await ev("(()=>{const els=[...document.querySelectorAll('div,span')].filter(e=>e.offsetParent!==null&&e.textContent.indexOf("+frag+")>=0&&(e.textContent||'').length<160); return els.length>0})()")
            if not has_draft:
                break
            card = json.loads(await ev("(()=>{const els=[...document.querySelectorAll('div,span')].filter(e=>e.offsetParent!==null&&e.textContent.indexOf("+frag+")>=0&&(e.textContent||'').length<160); els.sort((a,b)=>(a.textContent||'').length-(b.textContent||'').length); const e=els[0]; e.scrollIntoView({block:'center'}); const r=e.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()") or '{"err":1}')
            if card.get("err"): break
            await click(card["x"], card["y"]); await asyncio.sleep(5)
            pub2 = json.loads(await wait_for("""(()=>{const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent!==null&&!e.disabled&&/^Опубликовать$/i.test((e.textContent||'').trim())); if(!b) return null; const r=b.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()""", tries=5) or '{"err":1}')
            if pub2.get("err"): break
            await click(pub2["x"], pub2["y"]); await asyncio.sleep(12)

        # 9. верификация по счётчику доски (с ретраями — счётчик обновляется с задержкой)
        after = -1
        for _ in range(6):
            after = await read_count()
            if after > before: break
            await asyncio.sleep(8)
        print(f"PINS ON BOARD: {before} -> {after}")
        assert after > before, f"пин НЕ опубликован (счётчик {before}->{after})"
        print("OK: пин опубликован")

if __name__ == "__main__":
    assert len(sys.argv) >= 5, "usage: pin_post.py <slug> <title> <desc> <link> [board]"
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], *(sys.argv[5:])))
