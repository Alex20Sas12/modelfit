# -*- coding: utf-8 -*-
"""devto_guides.py — публикация поста про гайды ModelFit на dev.to (акк kata_omel, окно 9232).
Если сессия жива — публикует сразу; иначе magic-link логин (код из почты alex).
Адаптация pipeline-factory/devto_all.py под modelsite payload + canonical_url."""
import json, re, subprocess, sys, time, urllib.request, websocket

PORT = 9232
EMAIL = "alexford0289@gmail.com"
ACC = "alex"
PAYLOAD = json.load(open("C:/Users/Admin/fabrika/modelsite/_devto_guides_payload.json", encoding="utf-8"))
HIM = ["himalaya"]

def run(h_args, timeout=60):
    return subprocess.run(HIM + h_args, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace").stdout

ts = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=8))
tab = next((t for t in ts if t.get("type") == "page" and "dev.to" in t.get("url", "")), None)
if not tab:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?https://dev.to/dashboard", data=b"", method="PUT")
    tab = json.load(urllib.request.urlopen(req, timeout=10))
ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
mid = [0]
def send(m, **p):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": m, "params": p}))
    t0 = time.time()
    while time.time() - t0 < 55:
        x = json.loads(ws.recv())
        if x.get("id") == mid[0]: return x.get("result", {})
def js(e):
    r = send("Runtime.evaluate", expression=e, returnByValue=True, awaitPromise=True)
    res = r.get("result", {})
    return "JSERR:" + str(res.get("description"))[:140] if res.get("subtype") == "error" else res.get("value")
send("Page.enable")
send("Emulation.setFocusEmulationEnabled", enabled=True)

def publish():
    body = json.dumps({"article": {"title": PAYLOAD["title"], "body_markdown": PAYLOAD["article_body_markdown"],
                                   "tag_list": PAYLOAD["tag_list"].split(), "published": True,
                                   "canonical_url": PAYLOAD["canonical_url"]}})
    expr = """(async () => {
      const csrf = window.CSRF_TOKEN || document.querySelector('meta[name=csrf-token]')?.content || '';
      const r = await fetch('/articles', {method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Requested-With':'XMLHttpRequest'},
        body: %s});
      return r.status + ' | ' + (await r.text()).slice(0,300);
    })()""" % json.dumps(body)
    r = send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    return r.get("result", {}).get("value") or str(r.get("exceptionDetails"))[:200]

# пробуем сразу — вдруг сессия жива
signed = js("document.querySelector('meta[name=user-signed-in]')?.content")
print("signed-in:", signed, "| url:", js("location.href")[:80])
if signed == "true":
    print("POST:", publish())
    ws.close(); sys.exit(0)

# magic-link логин
base = run(["envelope", "list", "-a", ACC, "--page-size", "1"])
m = re.search(r"│\s*(\d+)\s*[│┆]", base)
base_id = int(m.group(1)) if m else 0
print("base msg id:", base_id)
js("location.href='https://dev.to/magic_links/new'")
time.sleep(6)
# дождаться реальной загрузки формы (вкладка могла открыться about:blank)
for _ in range(10):
    u = js("location.href") or ""
    if "magic_links" in u or "dev.to" in u:
        break
    time.sleep(3)
    js("location.href='https://dev.to/magic_links/new'")
    time.sleep(5)
time.sleep(3)
print("email:", js("""(() => {
  const inp = document.querySelector('input#email');
  if (!inp) return 'NO_INPUT';
  const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  s.call(inp, '%s');
  inp.dispatchEvent(new Event('input',{bubbles:true}));
  inp.dispatchEvent(new Event('change',{bubbles:true}));
  return inp.value;
})()""" % EMAIL))
print("send:", js("""(() => {
  const b = document.querySelector('input[name=commit]');
  if (b) { b.click(); return 'clicked'; } return 'NO_BTN';
})()"""))
code = None
for i in range(12):
    time.sleep(10)
    out = run(["envelope", "list", "-a", ACC, "--page-size", "3"])
    ids = [int(x) for x in re.findall(r"│\s*(\d+)\s*[│┆]", out)]
    new = [x for x in ids if x > base_id]
    if new:
        body = run(["message", "read", str(max(new)), "-a", ACC])
        c = re.search(r"\*{4,}\s*(\d{6,8})\s*\*{4,}", body) or re.search(r"\b(\d{6,8})\b", body)
        if c:
            code = c.group(1); print("code:", code, "(msg", max(new), ")"); break
if not code:
    print("NO CODE"); ws.close(); sys.exit(1)
print("submit:", js("""(() => {
  const inps=[...document.querySelectorAll('input')].filter(e=>e.offsetParent&&e.type!=='hidden'&&e.name!=='q');
  if(!inps.length) return 'NO_INPUTS:'+document.body.innerText.slice(0,120);
  const set=(el,v)=>{const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));};
  set(inps[0], '%s');
  const b=[...document.querySelectorAll('button,input[type=submit]')].find(e=>e.offsetParent&&/verify|continue|sign|log|submit/i.test(e.textContent||e.value||''));
  if(b){b.click();return 'submitted';}
  return 'set-no-btn';
})()""" % code))
time.sleep(8)
print("url:", js("location.href"))
signed = js("document.querySelector('meta[name=user-signed-in]')?.content")
print("signed-in:", signed)
if signed != "true":
    print("BODY:", (js("document.body.innerText||''") or "").replace("\n", " | ")[:250])
    ws.close(); sys.exit(1)
print("POST:", publish())
ws.close()
