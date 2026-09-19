# -*- coding: utf-8 -*-
"""list_tabs.py <port> — напечатать page-вкладки окна."""
import json, sys, urllib.request
port = sys.argv[1] if len(sys.argv) > 1 else "9222"
try:
    with urllib.request.urlopen(f"http://localhost:{port}/json", timeout=5) as r:
        tabs = json.load(r)
    for t in tabs:
        if t.get("type") == "page":
            print(t.get("url", "")[:100])
except Exception as e:
    print("DEAD", e)
