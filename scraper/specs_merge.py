#!/usr/bin/env python3
"""Fusiona specs_xiaomi.json en data.js (solo rellena nulos).

Uso: python3 specs_merge.py --dry-run | --apply
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent

# modelo mi.com -> ids de ficha (sin duplicar generaciones)
MAP = {
    "scooter-4": ["xiaomi-xiaomi-electric-scooter-4-eu-b1010-b1031"],
    "scooter-4-ultra": ["xiaomi-xiaomi-electric-scooter-4-ultra-eu-b1011-b1033"],
    "scooter-4-lite-2nd": ["xiaomi-4-lite-2"],
    "scooter-4-pro-2nd": ["xiaomi-4-pro-2"],
    "scooter-5": ["xiaomi-xiaomi-electric-scooter-5-es-b1079"],
    "scooter-5-max": ["xiaomi-xiaomi-electric-scooter-5-max-es-b1080"],
    "scooter-5-plus": ["xiaomi-xiaomi-electric-scooter-5-plus-es-b1117"],
    "scooter-6-lite": ["xiaomi-xiaomi-electric-scooter-6-lite-gl-b1134"],
    "scooter-6": ["xiaomi-xiaomi-electric-scooter-6-gl-b1133"],
    "scooter-6-pro": ["xiaomi-xiaomi-electric-scooter-6-pro-b1131"],
    "scooter-6-max": ["xiaomi-xiaomi-electric-scooter-6-max-gl-c1014"],
    "scooter-elite": ["xiaomi-xiaomi-electric-scooter-elite-es-b1092"],
}

# duplicados exactos (mismo cert, nombre con sufijo ES): se eliminan
DROPS = ["xiaomi-xiaomi-electric-scooter-4-pro-2nd-gen-es-b1030",
         "xiaomi-xiaomi-electric-scooter-4-lite-2nd-gen-es-b1036"]


def num(s):
    s = re.sub(r"\s+", "", s)
    if "." in s and "," in s:
        s = s.replace(".", "")
    return float(s.replace(",", "."))


def parse(text):
    g = lambda pat: re.search(pat, text, re.S)
    f = {}
    m = g(r"Potencia nominal(?: del motor)?\s*([\d.,]+)\s*W")
    if m: f["potNom"] = int(num(m.group(1)))
    m = g(r"Potencia m[áa]x\.?(?: del motor)?\s*\n?\s*([\d.,]+)\s*W")
    if m: f["potMax"] = int(num(m.group(1)))
    m = g(r"(?:Autonom[íi]a m[áa]x|Autonom[íi]a del patinete|Autonom[íi]a|Duraci[óo]n de la bater[íi]a)\.?\s*\n?\s*(?:Aprox\.?\s*)?([\d.,]+)\s*km")
    if m: f["autonomia"] = num(m.group(1))
    m = g(r"Peso del producto\s*\n?\s*(?:Aprox\.?\s*)?([\d.,]+)\s*kg")
    if m: f["peso"] = num(m.group(1))
    m = g(r"Carga m[áa]x\.?\s*\n?\s*([\d.,]+)\s*kg")
    if m: f["carga"] = int(num(m.group(1)))
    m = g(r'(?:Neum[áa]tico|Ruedas?)[^\n]*?(\d+(?:[.,]\d+)?)\s*"')
    if m: f["rueda"] = num(m.group(1))
    m = g(r"Frenado\s*\n(.+?)(?:\n|$)")
    if m: f["frenos"] = m.group(1).strip()[:120]
    m = g(r"Absorci[óo]n de impactos\s*\n(.+?)(?:\n|$)")
    if m: f["susp"] = m.group(1).strip()[:120]
    m = g(r"Clasificaci[óo]n IP\s*\n?\s*(IPX?\d+)")
    if m: f["ipx"] = m.group(1).strip()
    m = g(r"Tiempo de carga\s*\n?\s*Aprox\.?\s*([\d.,]+)\s*horas?")
    if m: f["cargaH"] = num(m.group(1))
    m = g(r"Capacidad nominal\s*\n?\s*([\d.,\s]+)\s*mAh\s*\/\s*([\d.,\s]+)\s*Wh")
    if m:
        mah = num(m.group(1))
        f["batAh"] = round(mah / 1000, 2) if mah >= 100 else mah
        f["batWh"] = num(m.group(2))
    else:
        m = g(r"Capacidad nominal\s*\n?\s*([\d.,\s]+)\s*Ah\s*\/\s*([\d.,\s]+)\s*Wh")
        if m:
            f["batAh"] = num(m.group(1)); f["batWh"] = num(m.group(2))
        else:
            m = g(r"Energ[íi]a de la bater[íi]a\s*\n?\s*([\d.,\s]+)\s*Wh\s*\(\s*([\d.,\s]+)\s*Ah\s*\)")
            if m:
                f["batWh"] = num(m.group(1)); f["batAh"] = num(m.group(2))
    return f


def main():
    apply = "--apply" in sys.argv
    specs = json.loads((BASE / "specs_xiaomi.json").read_text(encoding="utf-8"))
    src = (ROOT / "data.js").read_text(encoding="utf-8")
    m = re.search(r"ENRICHED\s*=\s*\[(.*?)\];", src, re.S)
    body_q = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', m.group(1))
    body_q = re.sub(r",\s*$", "", body_q.strip())
    fichas = json.loads("[" + body_q + "]")
    by_id = {f["id"]: f for f in fichas}

    parsed = {k: parse(v["text"]) for k, v in specs.items()}
    print("== specs extraidas ==")
    for k, f in parsed.items():
        print(f"  {k}: " + ", ".join(f"{kk}={vv}" for kk, vv in f.items()))

    changed, filled = 0, 0
    for key, ids in MAP.items():
        img = f"img/xiaomi-{key}.jpg"
        for fid in ids:
            f = by_id.get(fid)
            if not f:
                print(f"  !! sin ficha {fid}");
                continue
            for kk, vv in parsed[key].items():
                if f.get(kk) is None:
                    f[kk] = vv; filled += 1
            if not f.get("img"):
                f["img"] = img
            changed += 1
    before = len(fichas)
    fichas = [f for f in fichas if f["id"] not in DROPS]
    print(f"fichas: {before} -> {len(fichas)} (drops {before - len(fichas)}), "
          f"tocadas {changed}, campos rellenados {filled}")
    if apply:
        block = ",\n".join(json.dumps(f, ensure_ascii=False) for f in fichas)
        span = m.span(1)
        (ROOT / "data.js").write_text(src[:span[0]] + "\n" + block + "\n" + src[span[1]:], encoding="utf-8")
        print("data.js actualizado")


if __name__ == "__main__":
    main()
