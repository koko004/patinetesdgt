#!/usr/bin/env python3
"""Fusiona ofertas.json en data.js.

- Empareja cada oferta (tienda, nombre, precio, url) con su ficha ENRICHED
  por marca + similitud de nombre.
- Guarda en la ficha: ofertas:[{t,u,p}...], y actualiza precio/tienda/buy
  al mejor precio encontrado (precioEst=False: precio real observado).
- Sin ofertas para una ficha: se deja como estaba.

Uso:
    python3 merge.py --dry-run     # solo informe, no toca data.js
    python3 merge.py               # aplica cambios + informe

Genera: merge_report.txt (emparejados, dudosos, sin emparejar)
"""
import json, re, sys
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
MIN_SCORE = 0.55


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def score(modelo, nombre):
    a, b = norm(modelo), norm(nombre)
    if not a or not b:
        return 0.0
    r = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    overlap = len(ta & tb) / max(1, len(ta))
    base = 0.6 * r + 0.4 * overlap
    if ta and ta <= tb:
        # el modelo aparece integro en el nombre de la oferta: casi seguro
        base = max(base, 0.65)
    return base


def load_enriched(src):
    m = re.search(r"ENRICHED\s*=\s*\[(.*?)\];", src, re.S)
    if not m:
        raise SystemExit("No se encontro bloque ENRICHED en data.js")
    body = m.group(1)
    body_q = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', body)
    body_q = re.sub(r",\s*$", "", body_q.strip())
    return json.loads("[" + body_q + "]"), m.span(1)


def main():
    dry = "--dry-run" in sys.argv
    src = (ROOT / "data.js").read_text(encoding="utf-8")
    fichas, span = load_enriched(src)
    ofertas = json.loads((BASE / "ofertas.json").read_text(encoding="utf-8"))

    report = []
    for of in ofertas:
        nb = norm(of["nombre"])
        best, best_s = None, 0.0
        for f in fichas:
            brand = norm(f["marca"]).split()
            if not any(t in nb for t in brand if len(t) > 2):
                # la marca de la ficha debe aparecer en el nombre de la oferta
                # (excepcion: alias comunes)
                alias = {"ninebot": ["ninebot", "segway"], "xiaomi": ["xiaomi"],
                         "cecoc": ["cecotec"], "dualtron": ["dualtron", "minimotors"]}
                extra = alias.get(norm(f["marca"]), [])
                if not any(t in nb for t in extra):
                    continue
            s = score(f["modelo"], of["nombre"])
            if s > best_s:
                best, best_s = f, s
        of["_ficha"] = best["id"] if best and best_s >= MIN_SCORE else None
        of["_score"] = round(best_s, 2)
        status = "OK " if of["_ficha"] else ("?? " if best else "SIN")
        report.append(f"{status} [{of['_score']}] {of['tienda']} | {of['nombre']} | {of['precio']} EUR "
                      f"-> {of['_ficha'] or ('dudoso:' + best['id'] if best else 'sin ficha')}")

    matched = [o for o in ofertas if o["_ficha"]]
    by_ficha = {}
    for o in matched:
        by_ficha.setdefault(o["_ficha"], []).append(
            {"t": o["tienda"], "u": o["url"], "p": o["precio"]})

    changed = 0
    for f in fichas:
        if f["id"] in by_ficha:
            offs = sorted(by_ficha[f["id"]], key=lambda o: o["p"])
            # dedup por tienda: mejor precio de cada tienda
            seen_t, uniq = set(), []
            for o in offs:
                if o["t"] not in seen_t:
                    seen_t.add(o["t"])
                    uniq.append(o)
            f["ofertas"] = uniq
            f["precio"] = uniq[0]["p"]
            f["precioEst"] = False
            f["tienda"] = uniq[0]["t"]
            f["buy"] = uniq[0]["u"]
            changed += 1

    rep = [f"# fichas actualizadas: {changed}/{len(fichas)}",
           f"# ofertas emparejadas: {len(matched)}/{len(ofertas)}", ""] + report
    (BASE / "merge_report.txt").write_text("\n".join(rep), encoding="utf-8")
    print("\n".join(rep[:3]))
    print(f"informe completo -> scraper/merge_report.txt")

    if not dry:
        block = ",\n".join(json.dumps(f, ensure_ascii=False) for f in fichas)
        new_src = src[:span[0]] + "\n" + block + "\n" + src[span[1]:]
        (ROOT / "data.js").write_text(new_src, encoding="utf-8")
        print(f"data.js actualizado ({changed} fichas)")


if __name__ == "__main__":
    main()
