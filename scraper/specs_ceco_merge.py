#!/usr/bin/env python3
"""Fusiona specs_cecotec.json en data.js (solo rellena nulos).
Uso: python3 specs_ceco_merge.py --dry-run | --apply
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent

MAP = {
    "bongo-d20e": ["cecotec-d20e-connected-a1169"],
    "bongo-serie-a": ["cecotec-7303-a1000"],
    "bongo-s-max-infinity": ["cecotec-7304-a1002"],
    "bongo-s-max-unlimited": ["cecotec-7305-a1003"],
    "bongo-d40-xl": ["cecotec-bongo-d40-xl-connected-a1101"],
}


def num(s):
    s = re.sub(r"\s+", "", s)
    if "." in s and "," in s:
        s = s.replace(".", "")
    return float(s.replace(",", "."))


def parse(text):
    f = {}
    lines = [l.strip() for l in re.split(r"\n\s*\n", text)
             if l.strip() and len(l.strip()) < 80 and "\n" not in l.strip()]
    table = {}
    for i in range(len(lines) - 1):
        if lines[i] not in table:
            table[lines[i]] = lines[i + 1]
    get = lambda *names: next((table[k] for k in table if any(n.lower() in k.lower() for n in names)), None)

    def ok(k, v, lo, hi):
        return v is not None and lo <= v <= hi or None
    v = get("Potencia nominal")
    if v and re.search(r"\d", v):
        v = int(num(re.search(r"[\d.,]+", v).group(0)))
        if 100 <= v <= 3000: f["potNom"] = v
    v = get("Autonomía máxima")
    if v and re.search(r"\d", v):
        v = num(re.search(r"[\d.,]+", v).group(0))
        if 10 <= v <= 200: f["autonomia"] = v
    v = get("Peso máximo de usuario")
    if v and re.search(r"\d", v):
        v = int(num(re.search(r"[\d.,]+", v).group(0)))
        if 50 <= v <= 200: f["carga"] = v
    v = get("Tipo de freno")
    if v and len(v) > 2 and not re.search(r"€|añadir|cesta", v, re.I): f["frenos"] = v[:120]
    v = get("Tipo de suspensión")
    if v: f["susp"] = "Sin suspensión" if v.strip().lower() == "no" else v[:120]
    v = get("Protección contra agua")
    if v and re.search(r"\d", v): f["ipx"] = "IPX" + re.search(r"\d+", v).group(0)
    m = re.search(r"Potencia máxima \(w\)\s*\n?\s*([\d.,]+)", text)
    if m:
        v = int(num(m.group(1)))
        if 100 <= v <= 12000: f["potMax"] = v
    if "potMax" not in f:
        m = re.search(r"Potencia máxima de ([\d.,]+)\s*W", text)
        if m:
            v = int(num(m.group(1)))
            if 100 <= v <= 12000: f["potMax"] = v
    return f
    m = re.search(r"[Rr]uedas?\s+[^\n|]{0,40}?(\d+(?:[.,]\d+)?)\s*[”\"]", text)
    if m: f["rueda"] = num(m.group(1))
    m = re.search(r"Tiempo de carga[^\n|]*?([\d.,]+)\s*horas?", text)
    if m: f["cargaH"] = num(m.group(1))
    m = re.search(r"(\d[\d\s.,]*)\s*mAh", text)
    if m:
        mah = num(m.group(1))
        f["batAh"] = round(mah / 1000, 2) if mah >= 100 else mah
    m = re.search(r"(\d[\d\s.,]*)\s*Wh", text)
    if m: f["batWh"] = num(m.group(1))
    m = re.search(r"[Pp]eso del producto\s*\n?\s*([\d.,]+)\s*kg", text)
    if m:
        v = num(m.group(1))
        if 8 <= v <= 60: f["peso"] = v
    return f


def main():
    apply = "--apply" in sys.argv
    specs = json.loads((BASE / "specs_cecotec.json").read_text(encoding="utf-8"))
    src = (ROOT / "data.js").read_text(encoding="utf-8")
    m = re.search(r"ENRICHED\s*=\s*\[(.*?)\];", src, re.S)
    body_q = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', m.group(1))
    body_q = re.sub(r",\s*$", "", body_q.strip())
    fichas = json.loads("[" + body_q + "]")
    by_id = {f["id"]: f for f in fichas}
    changed, filled = 0, 0
    for key, ids in MAP.items():
        if key not in specs:
            continue
        f = parse(specs[key]["text"])
        print(f"  {key}: " + ", ".join(f"{k}={v}" for k, v in f.items()))
        for fid in ids:
            fo = by_id.get(fid)
            if not fo:
                print(f"  !! sin ficha {fid}"); continue
            for k, v in f.items():
                if fo.get(k) is None:
                    fo[k] = v; filled += 1
            img = f"img/cecotec-{key}.jpg"
            if not fo.get("img") and (ROOT / img).exists():
                fo["img"] = img
            changed += 1
    print(f"tocadas {changed}, campos {filled}")
    if apply:
        block = ",\n".join(json.dumps(x, ensure_ascii=False) for x in fichas)
        span = m.span(1)
        (ROOT / "data.js").write_text(src[:span[0]] + "\n" + block + "\n" + src[span[1]:], encoding="utf-8")
        print("data.js actualizado")


if __name__ == "__main__":
    main()
