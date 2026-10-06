#!/usr/bin/env python3
"""Diagnostico rapido: por que una tienda da 0 ofertas.

Uso: python3 diag.py --shop ecoxtrem
Muestra titulo, nº de JSON-LD, nº de '€' en texto, nº de enlaces,
y un volcado de texto para ajustar el extractor.
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scrape import CHROME, UA

shop = sys.argv[sys.argv.index("--shop") + 1]
shops = json.loads((Path(__file__).parent / "shops.json").read_text(encoding="utf-8"))
url = next(s["url"] for s in shops if s["tienda"] == shop)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True,
                          args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    pg = b.new_context(user_agent=UA, locale="es-ES").new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    time.sleep(4)
    print("titulo:", pg.title())
    print("ld+json:", pg.evaluate("() => document.querySelectorAll('script[type=\"application/ld+json\"]').length"))
    print("euros:", pg.evaluate("() => (document.body.innerText.match(/€/g) || []).length"))
    print("enlaces:", pg.evaluate("() => document.querySelectorAll('a[href]').length"))
    print("--- enlaces tipo producto/coleccion ---")
    print(pg.evaluate("""() => [...document.querySelectorAll('a[href]')]
      .map(a => a.getAttribute('href'))
      .filter(h => /product|collection|categoria|tienda|shop|patinete|scooter/i.test(h || ''))
      .filter((v, i, arr) => arr.indexOf(v) === i).slice(0, 25).join('\\n')"""))
    print("--- ejemplo tarjeta producto ---")
    print(pg.evaluate("""() => {
      const a = [...document.querySelectorAll('a[href]')]
        .find(x => /product|producto/i.test(x.getAttribute('href') || ''));
      return a ? a.innerText.slice(0, 400) : '(sin enlaces /products)';
    }"""))
    print("--- texto (primeros 1500) ---")
    print(pg.evaluate("() => document.body.innerText.slice(0,1500)"))
    b.close()
