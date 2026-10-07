#!/usr/bin/env python3
"""Extrae specs + foto de fichas oficiales mi.com.

1. Visita cada URL, clica la pestana Especificaciones, vuelca el texto.
2. Descarga la imagen principal (og:image) a img/.
3. Guarda specs_xiaomi.json para fusion posterior.

Uso: python3 specs_mi.py
"""
import json, re, time, urllib.request
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
IMG = ROOT / "img"

MODELS = {
    "scooter-4": "https://www.mi.com/es/product/xiaomi-electric-scooter-4/",
    "scooter-4-ultra": "https://www.mi.com/es/product/xiaomi-electric-scooter-4-ultra/",
    "scooter-4-lite-2nd": "https://www.mi.com/es/product/xiaomi-electric-scooter-4-lite-2nd-gen/",
    "scooter-4-pro-2nd": "https://www.mi.com/es/product/xiaomi-electric-scooter-4-pro-2nd-gen/",
    "scooter-5": "https://www.mi.com/es/product/xiaomi-electric-scooter-5/",
    "scooter-5-max": "https://www.mi.com/es/product/xiaomi-electric-scooter-5-max/",
    "scooter-5-plus": "https://www.mi.com/es/product/xiaomi-electric-scooter-5-plus/",
    "scooter-6-lite": "https://www.mi.com/es/product/xiaomi-electric-scooter-6-lite/",
    "scooter-6": "https://www.mi.com/es/product/xiaomi-electric-scooter-6/",
    "scooter-6-pro": "https://www.mi.com/es/product/xiaomi-electric-scooter-6-pro/",
    "scooter-6-max": "https://www.mi.com/es/product/xiaomi-electric-scooter-6-max/",
    "scooter-6-ultra": "https://www.mi.com/es/product/xiaomi-electric-scooter-6-ultra/",
    "scooter-elite": "https://www.mi.com/es/product/xiaomi-electric-scooter-elite/",
}

EXTRACT = r"""() => {
  let tab = null;
  for (const el of document.querySelectorAll('a, button')) {
    if (/^\s*especificaciones\s*$/i.test(el.innerText || '')) { tab = el; break; }
  }
  if (tab) tab.click();
  return 'clicked:' + !!tab;
}"""

SPECS = r"""() => {
  const t = document.body.innerText || '';
  const img = (document.querySelector('meta[property="og:image"]') || {}).content || '';
  return {len: t.length, img, text: t.slice(0, 12000)};
}"""


def main():
    import sys
    sys.path.insert(0, str(BASE))
    from scrape import CHROME, UA
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, headless=True,
                              args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
        pg = b.new_context(user_agent=UA, locale="es-ES").new_page()
        for key, url in MODELS.items():
            try:
                print(f"[specs] {key} ...", flush=True)
                pg.goto(url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(4)
                clicked = pg.evaluate(EXTRACT)
                time.sleep(4)
                d = pg.evaluate(SPECS)
                # foto
                imgfile = None
                if d["img"]:
                    imgurl = d["img"] if d["img"].startswith("http") else "https:" + d["img"]
                    imgfile = f"xiaomi-{key}.jpg"
                    try:
                        req = urllib.request.Request(imgurl, headers={"User-Agent": UA})
                        (IMG / imgfile).write_bytes(urllib.request.urlopen(req, timeout=30).read())
                    except Exception as e:
                        print(f"  !! img {e}", flush=True)
                        imgfile = None
                out[key] = {"url": url, "clicked": clicked, "img": imgfile,
                            "text": d["text"]}
                print(f"  clicked={clicked} len={d['len']} img={imgfile}", flush=True)
            except Exception as e:
                print(f"  !! error {key}: {e}", flush=True)
        b.close()
    (BASE / "specs_xiaomi.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[specs] {len(out)} modelos -> specs_xiaomi.json")


if __name__ == "__main__":
    main()
