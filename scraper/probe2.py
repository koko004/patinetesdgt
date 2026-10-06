#!/usr/bin/env python3
"""Prueba el EXTRACT_JS real sobre una tienda y vuelca items en crudo.
Uso: python3 probe2.py --shop electyum
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scrape import CHROME, UA, EXTRACT_JS, parse_price, EXCLUDE_RE

shop = sys.argv[sys.argv.index("--shop") + 1]
shops = json.loads((Path(__file__).parent / "shops.json").read_text(encoding="utf-8"))
url = (sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv
       else next(s["url"] for s in shops if s["tienda"] == shop))

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True,
                          args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    pg = b.new_context(user_agent=UA, locale="es-ES").new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    time.sleep(4)
    data = pg.evaluate(EXTRACT_JS)
    items = data["items"]
    print(f"items brutos: {len(items)}")
    for it in items[:6]:
        price = None
        try:
            price = float(it.get("price")) if it.get("price") else None
        except (TypeError, ValueError):
            pass
        if price is None:
            price = parse_price(it.get("raw", ""))
        excl = bool(EXCLUDE_RE.search((it.get("name") or "")[:140]))
        print(f"  price={price} excl={excl} name={it.get('name','')[:60]!r} raw={it.get('raw','')[:60]!r}")
    print("next:", (data.get("next") or "")[:80])
    b.close()
