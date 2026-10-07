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

PRICE_RE = re.compile(
    r"(?:(\d[\d.\s]*[,\.]\d{2}|\d[\d.\s]{2,})\s*€|"
    r"€\s*(\d[\d.\s]*[,\.]\d{2}|\d[\d.\s]{2,}))")
# accesorios/recambios: no son patinetes completos
EXCLUDE_RE = re.compile(
    r"recambi|repuesto|manillar|controladora|pantalla|vinilo|cubierta|"
    r"cargador|pastilla|camara|neumatico|\bfreno\b|\bkit\b|tornillo|"
    r"display|gatillo|acelerador|puño|guardabarros|sillin|asiento|casco|"
    r"candado|soporte|bolsa|mochila|guante|luz\b|reflectante|camiseta|sudadera|"
    r"bicicleta|kart|triciclo|\bmoto\b|ciclomotor|quad|"
    r"glove|helmet|\block\b|tire|tyre|charger|pump|\bbell\b|mirror|holder|"
    r"basket|seat\b|saddle|griptape",
    re.I)


def parse_price(txt):
    """Devuelve el MENOR precio valido del texto (oferta < tachado)."""
    if not txt:
        return None
    vals = []
    for m in PRICE_RE.finditer(txt.replace("\u00a0", " ")):
        num = (m.group(1) or m.group(2)).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            v = float(num)
            if 50 <= v <= 5000:
                vals.append(v)
        except ValueError:
            pass
    return min(vals) if vals else None


EXTRACT_JS = r"""() => {
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
              const price = o.price || o.lowPrice || null;
              if (!g.name && !price) continue;
              out.push({name: g.name || '', price, url: g.url || o.url || location.href});
            }
          }
          if (types.includes('ItemList')) {
            for (const el of (g.itemListElement || [])) {
              const it = el.item || {};
              if (!it.name) continue;
              const offers = it.offers || {};
              out.push({name: it.name || '', price: offers.price || offers.lowPrice || null, url: it.url || el.url || ''});
            }
          }
        }
      }
    } catch (e) {}
  }
  // 2) Fallback DOM: enlaces cuyo texto contiene precio en EUR
  function cleanSlug(pathname) {
    const parts = (pathname || '').split('/').filter(Boolean);
    let slug = parts.pop() || '';
    return slug.replace(/\.(html?|php|aspx?)$/i, '')
               .replace(/[-_]+/g, ' ').replace(/^\d[\d\s]*/, '').trim();
  }
  for (const a of document.querySelectorAll('a[href]')) {
    const txt = (a.innerText || '').slice(0, 200);
    if (!/€/.test(txt)) continue;
    const img = a.querySelector('img');
    const head = a.querySelector('h2,h3,h4');
    let name = ((head && head.innerText.trim()) || '');
    if (!name) {
      let el = a;
      for (let i = 0; i < 4 && el; i++) {
        el = el.parentElement;
        if (!el) break;
        const h = el.querySelector('h2,h3');
        if (h && h.innerText.trim().length > 3) { name = h.innerText.trim(); break; }
      }
    }
    if (!name && img && img.alt && img.alt.trim().length > 3 &&
        !/^(thumbnail|product thumbnail|imagen|image|foto.*)$/i.test(img.alt.trim()))
      name = img.alt.trim();
    if (!name) name = cleanSlug(a.pathname);
    name = name.slice(0, 120);
    if (name.length < 3) continue;
    // prefiere el precio de oferta al tachado
    let raw = txt.slice(0, 200);
    let elp = a;
    for (let i = 0; i < 5 && elp; i++) {
      elp = elp.parentElement;
      if (!elp) break;
      const pr = elp.querySelector('.price:not(.compare-at-price):not(s):not(del), '
        + '.product-price .amount, .woocommerce-Price-amount');
      if (pr && /€/.test(pr.innerText || '')) { raw = pr.innerText.slice(0, 200); break; }
    }
    out.push({name, price: null, raw, url: a.href});
  }
  // 2b) Precio fuera del enlace: subir al contenedor producto
  const SKIP_URL = /#|javascript:|cart|checkout|cuenta|account|login|search|buscar|wishlist|compar/i;
  for (const a of document.querySelectorAll('a[href]')) {
    const txt = (a.innerText || '').slice(0, 200);
    if (/€/.test(txt)) continue;  // ya capturado en paso 2
    if (SKIP_URL.test(a.getAttribute('href') || '')) continue;
    const boxes = [];
    let el = a;
    for (let i = 0; i < 7 && el; i++) {
      el = el.parentElement;
      if (!el) break;
      const t = (el.innerText || '');
      if (/€/.test(t) && t.length < 2000) boxes.push(el);
    }
    boxes.sort((x, y) => (x.innerText || '').length - (y.innerText || '').length);
    for (const box of boxes) {
      const h = box.querySelector('h2,h3');
      const img = box.querySelector('img');
      let name = (h && h.innerText.trim()) || '';
      if (!name && img && img.alt && img.alt.trim().length > 3 &&
          !/^(thumbnail|product thumbnail|imagen|image|foto.*)$/i.test(img.alt.trim()))
        name = img.alt.trim();
      if (!name) name = cleanSlug(a.pathname);
      name = name.slice(0, 120);
      if (name.length < 3) continue;
      let raw = (box.innerText || '').slice(0, 400);
      const pr = box.querySelector('.price:not(.compare-at-price):not(s):not(del), '
        + '.product-price .amount, .woocommerce-Price-amount');
      if (pr && /€/.test(pr.innerText || '')) raw = pr.innerText.slice(0, 200);
      out.push({name, price: null, raw, url: a.href});
      break;
    }
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
        for _ in range(8):
            time.sleep(2)
            ready = page.evaluate(
                "() => /€/.test(document.body.innerText || '') && "
                "document.querySelectorAll('a[href]').length > 20")
            if ready:
                break
        page.evaluate("""() => {
          for (const b of document.querySelectorAll('button')) {
            if (/aceptar|accept|rechazar|reject|consentir|entendido|vale/i.test(b.innerText || '')) {
              const r = b.getBoundingClientRect();
              if (r.width > 0 && r.height > 0) { b.click(); break; }
            }
          }
        }""")
        time.sleep(2)
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
            name = it["name"].strip()[:140]
            if EXCLUDE_RE.search(name):
                continue
            results.append({"tienda": tienda, "nombre": name,
                            "precio": round(price, 2), "url": u})
        nxt = data.get("next")
        if not nxt or nxt == url:
            break
        url = nxt
    return results


PRODUCT_JS = r"""() => {
  let name = '', price = null;
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
            if (g.name) name = g.name;
            const off = g.offers || {};
            const o = Array.isArray(off) ? off[0] : off;
            price = o.price || o.lowPrice || price;
          }
        }
      }
    } catch (e) {}
  }
  if (!name) {
    const h = document.querySelector('h1');
    if (h) name = h.innerText.trim();
  }
  let raw = '';
  if (price == null) {
    const m = document.querySelector('main') || document.body;
    raw = (m.innerText || '').slice(0, 3000);
  }
  return {name, price, raw};
}"""


def scrape_products(page, tienda, urls, max_products=150):
    """Modo fichas: visita cada URL de producto y saca nombre+precio."""
    out, seen = [], set()
    for u in urls[:max_products]:
        if u in seen:
            continue
        seen.add(u)
        try:
            page.goto(u, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)
            d = page.evaluate(PRODUCT_JS)
            name = (d.get("name") or "").strip()[:140]
            price = d.get("price")
            try:
                price = float(price) if price else None
            except (TypeError, ValueError):
                price = None
            if price is None:
                price = parse_price(d.get("raw", ""))
            if len(name) < 3 or price is None or EXCLUDE_RE.search(name):
                continue
            out.append({"tienda": tienda, "nombre": name,
                        "precio": round(price, 2), "url": u})
        except Exception:
            continue
    return out


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
                if "collect" in s:
                    # recoge URLs de producto y visita cada ficha
                    page.goto(s["url"], wait_until="domcontentloaded", timeout=45000)
                    time.sleep(4)
                    links = page.evaluate(
                        """(re) => [...document.querySelectorAll('a[href]')]
                          .map(a => a.href).filter((v, i, arr) =>
                            new RegExp(re).test(v) && arr.indexOf(v) === i)""",
                        s["collect"])
                    print(f"  -> {len(links)} fichas", flush=True)
                    items = scrape_products(page, s["tienda"], links)
                else:
                    items = scrape_shop(page, s["tienda"], s["url"], maxp)
                print(f"  -> {len(items)} ofertas", flush=True)
                slot = s.get("slot", s["tienda"])
                for it in items:
                    it["slot"] = slot
                (BASE / f"ofertas_{slot}.json").write_text(
                    json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as e:
                print(f"  !! error {s['tienda']}: {e}", flush=True)
        browser.close()
    # combina todos los ficheros por tienda (persisten entre pasadas)
    for f in sorted(BASE.glob("ofertas_*.json")):
        if f.name == "ofertas.json":
            continue
        try:
            all_items.extend(json.loads(f.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            pass
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
