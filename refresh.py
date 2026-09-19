# -*- coding: utf-8 -*-
"""refresh.py — daily pipeline: fetch HF data -> tests -> build -> deploy -> IndexNow.
Run: python refresh.py  (cron-safe, prints only on failure or summary line)"""
import subprocess, sys, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "refresh.log")

def run(cmd, timeout=600):
    r = subprocess.run(cmd, shell=True, cwd=HERE, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-800:]

def main():
    lines = []
    rc, out = run("python fetch.py", 900)
    if rc != 0:
        lines.append(f"FETCH FAIL rc={rc}: {out}")
    else:
        n = len(json.load(open(os.path.join(HERE, "models.json"), encoding="utf-8")))
        lines.append(f"fetch ok, {n} models")
    rc, out = run("python test_build.py")
    if rc != 0:
        lines.append(f"TESTS FAIL: {out}")
        print("\n".join(lines)); sys.exit(1)
    rc, out = run("python build.py")
    if rc != 0:
        lines.append(f"BUILD FAIL: {out}"); print("\n".join(lines)); sys.exit(1)
    # deploy (Vercel creds live in XDG_DATA_HOME)
    env = dict(os.environ)
    env["XDG_DATA_HOME"] = os.path.join(os.environ.get("APPDATA", ""), "xdg.data").replace("\\", "/")
    r = subprocess.run("npx vercel deploy --prod --yes", shell=True, cwd=os.path.join(HERE, "site"),
                       capture_output=True, text=True, timeout=420, env=env)
    if r.returncode != 0:
        lines.append(f"DEPLOY FAIL rc={r.returncode}: {(r.stdout+r.stderr)[-400:]}")
    else:
        lines.append("deploy ok")
    # IndexNow (keyLocation обязателен — без него api.indexnow.org отдаёт 403)
    key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
    urls = open(os.path.join(HERE, "urls.txt")).read().split()
    payload = json.dumps({"host": "modelfit-eight.vercel.app", "key": key,
                          "keyLocation": f"https://modelfit-eight.vercel.app/{key}.txt", "urlList": urls})
    open(os.path.join(HERE, "indexnow_payload.json"), "w").write(payload)
    rc, out = run(f'curl -s -o NUL -w "%{{http_code}}" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -X POST "https://api.indexnow.org/indexnow" -H "Content-Type: application/json" --data @indexnow_payload.json')
    lines.append(f"indexnow {out.strip()} ({len(urls)} urls)")
    with open(LOG, "a", encoding="utf-8") as f:
        import datetime
        f.write(datetime.datetime.now().isoformat(timespec="seconds") + " | " + " | ".join(lines) + "\n")
    print(" | ".join(lines))
    sys.exit(1 if any("FAIL" in l for l in lines) else 0)

if __name__ == "__main__":
    main()
