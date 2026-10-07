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
import json, re, sys, unicodedata
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
STOP = {"patinete", "patinetes", "electrico", "electricos", "electrica",
        "certificado", "certificada", "homologado", "homologada", "dgt", "vmp",
        "scooter", "version", "versiones", "eu", "e",
        "tipo", "vpl", "vpm", "potencia", "pot", "nominal", "autonomia",
        "velocidad", "vel", "carga", "bateria", "mah", "wh", "w", "kg",
        "km", "neumatico", "neumaticos", "pulgadas",
        "negro", "gris", "blanco", "azul", "plata", "rojo", "verde", "rosa",
        "mate", "brillo", "color", "oscuro", "claro",
        "bongo", "maxima", "maximo", "minima", "minimo", "aprox"}
VARIANT = {"ultra", "max", "pro", "plus", "lite", "dual", "limited", "luxury",
           "evo", "gt", "air", "go"}
NUM_RE = re.compile(r"^\d+(\.\d+)?$")
SPEC_RE = re.compile(r"^\d+(\.\d+)?(v|ah|w)$|^\d+[a-z]*ah$")
MIN_SCORE = 0.60


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def score(modelo, nombre, brand=""):
    a, b = norm(modelo), norm(nombre)
    if not a or not b:
        return 0.0
    stop = STOP | set(norm(brand).split())
    ta = {t for t in a.split() if t not in stop and not SPEC_RE.match(t) and not NUM_RE.match(t)}
    tb = {t for t in b.split() if t not in stop and not NUM_RE.match(t) and not SPEC_RE.match(t)}
    if not ta or not tb:
        return 0.0
    r = SequenceMatcher(None, a, b).ratio()
    inter = len(ta & tb)
    prec = inter / len(tb)
    rec = inter / len(ta)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    s = 0.5 * r + 0.5 * f1
    # palabras que distinguen variantes: con ellas no vale la contencion
    extra = tb - ta
    if ta == tb:
        s = max(s, 0.9)
    elif ta and ta < tb and not (extra & VARIANT):
        # el modelo aparece integro en la oferta: casi seguro
        # (digitos y compuerta anti-cuotas siguen vigilando)
        s = max(s, 0.8)
    elif extra:
        s -= 0.5 * len(extra) / len(tb)
    return max(0.0, s)


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
    shops = json.loads((BASE / "shops.json").read_text(encoding="utf-8"))
    official = {}
    name_cuts = {}
    for s in shops:
        if "brand" in s:
            official[s.get("slot", s["tienda"])] = s["brand"]
        if "name_cut" in s:
            name_cuts[s.get("slot", s["tienda"])] = s["name_cut"]

    report = []
    for of in ofertas:
        raw_name = of["nombre"]
        cut = name_cuts.get(of.get("slot", of["tienda"]))
        if cut:
            raw_name = raw_name.split(cut)[0]
        nb = norm(raw_name)
        best, best_s = None, 0.0
        only_brand = official.get(of.get("slot", of["tienda"]))
        for f in fichas:
            if only_brand:
                # tienda oficial: solo fichas de su marca
                if norm(f["marca"]) != norm(only_brand):
                    continue
            else:
                brand = norm(f["marca"]).split()
                if not any(t in nb for t in brand if len(t) > 2):
                    # la marca de la ficha debe aparecer en el nombre de la oferta
                    # (excepcion: alias comunes)
                    alias = {"ninebot": ["ninebot", "segway"], "xiaomi": ["xiaomi"],
                             "dualtron": ["dualtron", "minimotors"]}
                    extra = alias.get(norm(f["marca"]), [])
                    if not any(t in nb for t in extra):
                        continue
            s = score(f["modelo"], raw_name, f["marca"])
            if s > best_s:
                # los numeros mandan (G2, 4Pro, 6Max...): si ambos tienen
                # numeros y no comparten ninguno, es otra generacion
                nf = set(re.findall(r"\d+", norm(f["modelo"])))
                no = set(re.findall(r"\d+", nb))
                if nf and no and nf.isdisjoint(no):
                    continue
                best, best_s = f, s
        cheap = False
        if best and best_s >= MIN_SCORE and best.get("precio"):
            # compuerta anti-cuotas: oferta <45% del precio conocido = sospechosa
            if of["precio"] < 0.45 * best["precio"]:
                cheap = True
        of["_ficha"] = best["id"] if best and best_s >= MIN_SCORE and not cheap else None
        of["_score"] = round(best_s, 2)
        if cheap:
            status = "BARATO?"
        else:
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
