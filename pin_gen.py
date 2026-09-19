# -*- coding: utf-8 -*-
"""pin_gen.py — пины-карточки 1000x1500 из РЕАЛЬНОГО скриншота калькулятора (не AI).
Usage: python pin_gen.py <slug> ["Заголовок"]
Сохраняет pins/<slug>.png
"""
import json, asyncio, base64, os, sys, io
import websockets, urllib.request
from PIL import Image, ImageDraw, ImageFont

PORT = 9274
BASE = "https://modelfit-eight.vercel.app/"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pins")
os.makedirs(OUT, exist_ok=True)

SLUG, TITLE = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""

def font(size):
    for p in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeuib.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_tabs():
    with urllib.request.urlopen(f"http://localhost:{PORT}/json", timeout=5) as r:
        return json.load(r)

def open_tab(url):
    req = urllib.request.Request(f"http://localhost:{PORT}/json/new?{url}", method="PUT")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)

def close_tab(tid):
    urllib.request.urlopen(f"http://localhost:{PORT}/json/close/{tid}", timeout=5).read()

async def shot():
    tab = open_tab(BASE + SLUG + "/")   # своя вкладка — Pinterest-вкладку не трогаем
    await asyncio.sleep(2)
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=80*1024*1024) as ws:
        _id=[0]
        async def call(m,p=None):
            _id[0]+=1
            await ws.send(json.dumps({"id":_id[0],"method":m,"params":p or {}}))
            while True:
                x=json.loads(await ws.recv())
                if x.get("id")==_id[0]: return x.get("result",{})
        await call("Page.enable")
        await call("Emulation.setFocusEmulationEnabled", {"enabled": True})  # грабля: без этого окно неактивно и Pinterest не гидрируется
        await call("Emulation.setDeviceMetricsOverride", {"width":480,"height":900,"deviceScaleFactor":2,"mobile":False})
        await asyncio.sleep(7)
        r = await call("Page.captureScreenshot", {"format":"png", "clip":{"x":0,"y":0,"width":480,"height":820,"scale":2}})
        await call("Emulation.clearDeviceMetricsOverride")
    close_tab(tab["id"])
    return base64.b64decode(r["data"])

raw = asyncio.run(shot())
shot_img = Image.open(io.BytesIO(raw)).convert("RGB")

# карточка 1000x1500: фон, заголовок, скрин, подвал
card = Image.new("RGB", (1000, 1500), "#0B3D2E")
d = ImageDraw.Draw(card)
d.rectangle([0, 0, 1000, 260], fill="#0B3D2E")
d.rectangle([0, 260, 1000, 268], fill="#3ECF8E")
f_big = font(58); f_sm = font(34); f_ft = font(30)
title = TITLE or SLUG.replace("-", " ").title()
# перенос заголовка по словам
words, lines, cur = title.split(), [], ""
for w in words:
    if d.textlength(cur + " " + w, font=f_big) < 900: cur += (" " if cur else "") + w
    else: lines.append(cur); cur = w
if cur: lines.append(cur)
y = 210 - len(lines)*70
for ln in lines[:2]:
    d.text((50, y), ln, font=f_big, fill="#FFFFFF"); y += 72
# скрин по центру
sw = 900; sh = int(shot_img.height * sw / shot_img.width)
if sh > 1050: sh = 1050; sw = int(shot_img.width * sh / shot_img.height)
s = shot_img.resize((sw, sh))
card.paste(s, ((1000-sw)//2, 300))
d.rectangle([(1000-sw)//2-3, 300-3, (1000+sw)//2+3, 300+sh+3], outline="#3ECF8E", width=4)
d.text((50, 1420), "ModelFit — measured VRAM, updated daily", font=f_ft, fill="#9FD9C0")
path = os.path.join(OUT, SLUG + ".png")
card.save(path, "PNG")
print("saved", path, card.size)
