#!/usr/bin/env python3
"""Scraper reutilizable de ofertas de patinetes.

Recorre las tiendas de shops.json con Chrome real (evita anti-bots),
extrae por cada producto: nombre, precio y URL exacta de la ficha,
y guarda todo en ofertas.json.

Uso:
    python3 scrape.py                  # todas las tiendas
    python3 scrape.py --shop ecoxtrem  # solo una tienda
    python3 scrape.py --max-pages 8    # paginacion (defecto 6)

Requisitos: pip install playwright  (navegador: Chrome del sistema)
"""
import json, re, sys, time
from pathlib import Path
from urllib.parse import urljoin

CHROME = "/opt/google/chrome/chrome"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
BASE = Path(__file__).parent

PRICE_RE = re.compile(r"(\d[\d.\s]*[,\.]\d{2}|\d[\d.\s]{2,})\s*€")


def parse_price(txt):
    if not txt:
        return None
    m = PRICE_RE.search(txt.replace("\u00a0", " "))
    if not m:
        return None
    num = m.group(1).replace(" ", "").replace(".", "").replace(",", ".")
    try:
        v = float(num)
        return v if 50 <= v <= 15000 else None
    except ValueError:
        return None


EXTRACT_JS = """() => {
  const out = [];
  // 1) JSON-LD (schema.org): lo mas fiable
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const data = JSON.parse(s.textContent);
      const items = Array.isArray(data) ? data : [data];
      for (const d of items) {
        const graph = d['@graph'] || [d];
        for (const g of graph) {
          const t = (g['@type'] || '');
          const types = Array.isArray(t) ? t : [t];
          if (types.includes('Product')) {
            const offers = g.offers || {};
            const olist = Array.isArray(offers) ? offers : [offers];
            for (const o of olist) {
              out.push({name: g.name || '', price: o.price || o.lowPrice || null, url: g.url || o.url || location.href});
            }
          }
          if (types.includes('ItemList')) {
            for (const el of (g.itemListElement || [])) {
              const it = el.item || {};
              const offers = it.offers || {};
              out.push({name: it.name || '', price: offers.price || offers.lowPrice || null, url: it.url || el.url || ''});
            }
          }
        }
      }
    } catch (e) {}
  }
  // 2) Fallback DOM: enlaces cuyo texto cercano tiene precio en EUR
  for (const a of document.querySelectorAll('a[href]')) {
    const txt = (a.innerText || '').slice(0, 200);
    if (!/€/.test(txt)) continue;
    const img = a.querySelector('img');
    const head = a.querySelector('h2,h3,h4');
    let name = ((head && head.innerText.trim()) || (img && img.alt.trim()) || '');
    if (!name) {
      const parts = (a.pathname || '').split('/').filter(Boolean);
      name = (parts.pop() || '').replace(/[-_]+/g, ' ');
    }
    name = name.slice(0, 120);
    if (name.length < 3) continue;
    out.push({name, price: null, raw: txt.slice(0, 200), url: a.href});
  }
  // 3) Enlace a pagina siguiente
  let next = null;
  const rel = document.querySelector('a[rel="next"]');
  if (rel) next = rel.href;
  else {
    for (const a of document.querySelectorAll('a')) {
      if (/^\\s*(siguiente|next|>)\\s*$/i.test(a.innerText || '')) { next = a.href; break; }
    }
  }
  return {items: out, next};
}"""


def scrape_shop(page, tienda, url, max_pages):
    seen, results = set(), []
    for _ in range(max_pages):
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)
        data = page.evaluate(EXTRACT_JS)
        for it in data["items"]:
            u = urljoin(url, it.get("url") or "")
            key = (it.get("name", "").strip().lower(), u)
            if not u or len(key[0]) < 3 or key in seen:
                continue
            seen.add(key)
            price = it.get("price")
            try:
                price = float(price) if price else None
            except (TypeError, ValueError):
                price = None
            if price is None:
                price = parse_price(it.get("raw", ""))
            if price is None:
                continue
            results.append({"tienda": tienda, "nombre": it["name"].strip()[:140],
                            "precio": round(price, 2), "url": u})
        nxt = data.get("next")
        if not nxt or nxt == url:
            break
        url = nxt
    return results


def main():
    args = sys.argv[1:]
    only = args[args.index("--shop") + 1] if "--shop" in args else None
    maxp = int(args[args.index("--max-pages") + 1]) if "--max-pages" in args else 6
    shops = json.loads((BASE / "shops.json").read_text(encoding="utf-8"))
    if only:
        shops = [s for s in shops if s["tienda"] == only]
    from playwright.sync_api import sync_playwright
    all_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME, headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
        ctx = browser.new_context(user_agent=UA, locale="es-ES")
        page = ctx.new_page()
        for s in shops:
            try:
                print(f"[scrape] {s['tienda']} ...", flush=True)
                items = scrape_shop(page, s["tienda"], s["url"], maxp)
                print(f"  -> {len(items)} ofertas", flush=True)
                all_items.extend(items)
            except Exception as e:
                print(f"  !! error {s['tienda']}: {e}", flush=True)
        browser.close()
    # dedup por (tienda, url): quedarnos el menor precio visto
    best = {}
    for it in all_items:
        k = (it["tienda"], it["url"])
        if k not in best or it["precio"] < best[k]["precio"]:
            best[k] = it
    out = sorted(best.values(), key=lambda x: (x["tienda"], x["precio"]))
    (BASE / "ofertas.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[scrape] total {len(out)} ofertas -> ofertas.json")


if __name__ == "__main__":
    main()
