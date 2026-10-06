#!/usr/bin/env python3
"""Sonda: por que los pasos 2/2b no casan en una tienda.
Uso: python3 probe.py --shop kukirin.es
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scrape import CHROME, UA

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
    print(pg.evaluate("""() => {
      const links = [...document.querySelectorAll('a[href]')];
      const withEuro = links.filter(a => /€/.test(a.innerText || ''));
      const prod = links.filter(a => /product|producto/i.test(a.getAttribute('href') || ''));
      const prodEuro = prod.filter(a => /€/.test(a.innerText || ''));
      let sample = prod.slice(0, 3).map(a =>
        'HREF=' + a.getAttribute('href') + '\\nTEXT=' + (a.innerText || '').slice(0, 250));
      // contenedores: ¿a cuantos niveles esta el € desde un enlace producto?
      let depths = prod.slice(0, 10).map(a => {
        let el = a, d = 0;
        while (el && d < 8) { el = el.parentElement; d++;
          if (el && /€/.test(el.innerText || '')) return d + ':' + (el.innerText || '').length; }
        return 'none';
      });
      return JSON.stringify({links: links.length, withEuro: withEuro.length,
        prod: prod.length, prodEuro: prodEuro.length, depths, sample}, null, 1);
    }"""))
    print("--- HTML tarjeta (3 niveles sobre primer /products) ---")
    print(pg.evaluate("""() => {
      const a = [...document.querySelectorAll('a[href]')]
        .find(x => /\\/products\\//.test(x.getAttribute('href') || ''));
      if (!a) return '(sin enlaces /products)';
      let el = a;
      for (let i = 0; i < 3 && el; i++) el = el.parentElement;
      return (el ? el.outerHTML : '').slice(0, 2500);
    }"""))
    b.close()
