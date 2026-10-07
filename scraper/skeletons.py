#!/usr/bin/env python3
"""Crea fichas esqueleticas para marcas del listado DGT aun sin ficha.

Toma los modelos de DGT_LIST de las marcas indicadas y los añade a ENRICHED
con specs a null (se muestran como "—"). El merge posterior rellena
precio/tienda/buy/enlace desde las ofertas raspadas.

Uso: python3 skeletons.py [--apply]
  sin flags: informa cuantos crearia (no toca nada)
  --apply:   inserta en data.js
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent

PROPER = {
    "CECOTEC": "Cecotec", "E-TWOW": "E-TWOW", "HIKERBOY": "Hikerboy",
    "ISINWHEEL": "iSinwheel", "KUICKWHEEL": "Kuickwheel", "OLSSON": "Olsson",
    "PLATUM": "Platum", "PURE": "PURE ELECTRIC", "RCB": "RCB",
    "SEGWAY": "Segway", "SKATEFLASH": "Skateflash", "VOLTROCK": "Voltrock",
    "XIAOMI": "XIAOMI", "WISPEED": "Wispeed", "SABWAY": "Sabway",
}


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def main():
    apply = "--apply" in sys.argv
    src = (ROOT / "data.js").read_text(encoding="utf-8")
    m = re.search(r"ENRICHED\s*=\s*\[(.*?)\];", src, re.S)
    body_q = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', m.group(1))
    body_q = re.sub(r",\s*$", "", body_q.strip())
    fichas = json.loads("[" + body_q + "]")
    have = {f["marca"] + "|" + f["modelo"] for f in fichas}

    md = re.search(r"DGT_LIST\s*=\s*(\[.*?\]);", src, re.S)
    dgt = json.loads(md.group(1))

    new = []
    for marca_dgt, modelo, cert in dgt:
        if marca_dgt.upper() not in PROPER:
            continue
        marca = PROPER[marca_dgt.upper()]
        if marca + "|" + modelo in have:
            continue
        new.append({
            "id": f"{slug(marca)}-{slug(modelo)}-{slug(cert)}"[:90],
            "marca": marca, "modelo": modelo, "cert": cert,
            "precio": None, "precioEst": False,
            "potNom": None, "potMax": None, "batWh": None, "batAh": None,
            "volt": None, "autonomia": None, "velMax": 25, "velReal": None,
            "peso": None, "carga": None, "rueda": None, "frenos": None,
            "susp": None, "ipx": None, "cargaH": None,
            "tienda": None, "buy": None, "img": None,
        })
    print(f"esqueletos nuevos: {len(new)}")
    for f in new[:12]:
        print(f"  {f['marca']} | {f['modelo'][:50]} | {f['cert']}")
    if len(new) > 12:
        print(f"  ... y {len(new) - 12} mas")

    if apply and new:
        block = ",\n".join(json.dumps(f, ensure_ascii=False) for f in fichas + new)
        span = m.span(1)
        new_src = src[:span[0]] + "\n" + block + "\n" + src[span[1]:]
        (ROOT / "data.js").write_text(new_src, encoding="utf-8")
        print(f"data.js: {len(fichas)} -> {len(fichas) + len(new)} fichas")


if __name__ == "__main__":
    main()
