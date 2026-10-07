#!/usr/bin/env python3
"""Extrae specs + foto de fichas Bongo cecotec.es. Uso: python3 specs_ceco.py"""
import json, time, urllib.request
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
IMG = ROOT / "img"

MODELS = {
    "bongo-d20e": "https://cecotec.es/es/patinetes-electricos/bongo-d20e-connected",
    "bongo-serie-a": "https://cecotec.es/es/patinetes-electricos/bongo-serie-a-connected",
    "bongo-s-max-infinity": "https://cecotec.es/es/patinetes-electricos/bongo-serie-s-max-infinity",
    "bongo-s-max-unlimited": "https://cecotec.es/es/patinetes-electricos/bongo-serie-s-max-unlimited",
    "bongo-d40-xl": "https://cecotec.es/es/patinetes-electricos/bongo-d40-xl-suspension-connected",
    "bongo-d30-dream": "https://cecotec.es/es/patinetes-electricos/bongo-d30-dream",
}

EXTRACT = r"""() => ({
  img: (document.querySelector('meta[property="og:image"]') || {}).content || '',
  text: (document.body.innerText || '').slice(0, 15000),
})"""


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
                time.sleep(5)
                d = pg.evaluate(EXTRACT)
                imgfile = None
                if d["img"]:
                    imgurl = d["img"] if d["img"].startswith("http") else "https:" + d["img"]
                    imgfile = f"cecotec-{key}.jpg"
                    try:
                        req = urllib.request.Request(imgurl, headers={"User-Agent": UA})
                        (IMG / imgfile).write_bytes(urllib.request.urlopen(req, timeout=30).read())
                    except Exception as e:
                        print(f"  !! img {e}", flush=True)
                        imgfile = None
                out[key] = {"url": url, "img": imgfile, "text": d["text"]}
                print(f"  len={len(d['text'])} img={imgfile}", flush=True)
            except Exception as e:
                print(f"  !! error {key}: {e}", flush=True)
        b.close()
    (BASE / "specs_cecotec.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[specs] {len(out)} modelos -> specs_cecotec.json")


if __name__ == "__main__":
    main()
