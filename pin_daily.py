# -*- coding: utf-8 -*-
"""pin_daily.py — ежедневный пин: следующий из pin_queue.json → pin_gen → pin_post → пометить.
Для крона (no_agent). Печать — только при событии/ошибке. Сам поднимает окно 9271 и туннель не нужен (Pinterest = прямой IP).
"""
import json, os, subprocess, sys, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 9274
QUEUE = os.path.join(BASE, "pin_queue.json")

def log(msg):
    with open(os.path.join(BASE, "LOG.md"), "a", encoding="utf-8") as f:
        f.write(f"- {time.strftime('%d.%m %H:%M')} pin_daily: {msg}\n")

def port_alive():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3)
        return True
    except Exception:
        return False

def run(args, timeout=600):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=BASE, timeout=timeout)

def main():
    q = json.load(open(QUEUE, encoding="utf-8"))
    todo = [x for x in q if not x.get("posted")]
    if not todo:
        log("очередь пуста — все 28 опубликованы")
        print("🚨 pin_queue: все пины опубликованы, очередь пуста — нужно пополнить")
        return
    item = todo[0]

    # 1. окно Pinterest
    if not port_alive():
        r = subprocess.run([sys.executable, r"C:\Users\Admin\fabrika\chrome-launch.py", "modelfit", str(PORT)],
                           capture_output=True, text=True, timeout=60)
        time.sleep(20)
        if not port_alive():
            log("окно 9271 не поднялось: " + (r.stdout + r.stderr)[-200:])
            print("🚨 pin_daily: окно Pinterest (9271) не поднялось")
            return

    # 2. картинка
    r = run(["pin_gen.py", item["slug"], item["title"]], timeout=180)
    img = os.path.join(BASE, "pins", item["slug"] + ".png")
    if r.returncode != 0 or not os.path.exists(img):
        log(f"pin_gen ПРОВАЛ {item['slug']}: {(r.stdout + r.stderr)[-250:]}")
        print(f"🚨 pin_daily: генерация картинки провалилась ({item['slug']})")
        return

    # 3. публикация
    r = run(["pin_post.py", item["slug"], item["title"], item["desc"], item["link"]], timeout=900)
    ok = r.returncode == 0 and "OK: пин опубликован" in r.stdout
    if not ok:
        log(f"pin_post ПРОВАЛ {item['slug']}: {(r.stdout + r.stderr)[-300:]}")
        print(f"🚨 pin_daily: публикация провалилась ({item['slug']}) — {(r.stdout + r.stderr)[-150:]}")
        return

    # 4. пометить
    item["posted"] = time.strftime("%Y-%m-%d")
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    left = sum(1 for x in q if not x.get("posted"))
    log(f"опубликован пин {item['slug']}, в очереди осталось {left}")
    print(f"✅ pin_daily: опубликован пин «{item['title'][:50]}» → {item['link']} (осталось {left})")

if __name__ == "__main__":
    main()
