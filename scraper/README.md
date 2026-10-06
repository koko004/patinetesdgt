# Scraper de ofertas (precios + enlaces exactos por tienda)

Automatiza lo que antes se hacia a mano con agentes: recorre las tiendas,
extrae `nombre + precio + URL de ficha` de cada patinete y fusiona el
mejor precio en `data.js`.

## Requisitos

```bash
pip install playwright
# Chrome del sistema en /opt/google/chrome/chrome (ya instalado aqui)
```

## Uso

```bash
cd scraper
python3 scrape.py                  # todas las tiendas de shops.json (~10-20 min)
python3 scrape.py --shop ecoxtrem  # solo una tienda
python3 scrape.py --max-pages 8    # paginas por tienda (defecto 6)

python3 merge.py --dry-run         # ver emparejamientos sin tocar nada
python3 merge.py                   # aplica: ofertas + mejor precio en data.js
```

## Que hace `merge.py`

Por cada ficha de `data.js` busca sus ofertas por marca + similitud de
nombre y escribe:

```js
ofertas:[{t:"imoveblue",u:"https://.../ficha-exacta",p:599}, ...],
precio: 599,            // = mejor precio encontrado (precioEst:false)
tienda: "imoveblue",   // tienda del mejor precio
buy: "https://.../ficha-exacta"
```

La web muestra el **mejor precio** en la tarjeta y la **lista de tiendas
con su precio y enlace** en la ficha y en el comparador. Fichas sin
ofertas nuevas se dejan como estaban.

Revisa siempre `merge_report.txt`: lineas `??` = emparejamiento dudoso
(no se aplica), `SIN` = sin ficha coincidente.

## Actualizacion periodica de precios

```bash
# cron mensual (ej. dia 1 a las 04:00)
0 4 1 * * cd /root/patinetes-dgt/scraper && python3 scrape.py && python3 merge.py >> cron.log 2>&1
```

Tras el merge: `git add -A && git commit -m "Precios actualizados" && git push`
y Vercel redespliega solo.

## Anti-bots

`scrape.py` usa Chrome real headless + User-Agent de Chrome Windows
comun (misma tecnica que supero tallerdelpatinete.es). Si una tienda
empieza a bloquear, subir `time.sleep(3)` o reducir `--max-pages`.
