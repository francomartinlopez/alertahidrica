"""Arma rios_mapa.json: geometría proyectada (SVG) de la cuenca del Plata entre
Asunción y el delta, con los cuatro ríos de los puertos, ríos secundarios,
lagos, países y límites de provincias argentinas, para el mapa de la sección
Ríos. Fuente: Natural Earth 10m (dominio público). El Iguazú no está en la capa
de ríos de Natural Earth: se toma del límite Argentina-Brasil, que sigue su
cauce desde el Paraná hasta la boca del San Antonio.

Solo hace falta volver a correrlo si se cambia el recuadro o las etiquetas.
Necesita shapely (pip install shapely) y estos archivos de
https://github.com/nvkelso/natural-earth-vector/tree/master/geojson en una carpeta:
ne_10m_rivers_lake_centerlines.geojson (guardado como rivers10.geojson),
ne_10m_lakes.geojson (como lakes10.geojson), ne_10m_admin_0_countries.geojson,
ne_10m_admin_1_states_provinces_lines.geojson y
ne_10m_admin_0_boundary_lines_land.geojson.
Uso: python3 armar_rios_mapa.py <carpeta con los geojson> rios_mapa.json
Los puertos no están acá: la web los ubica con lat y lon de datos.json["rios"]."""
import json
import math
import sys
from shapely.geometry import shape, box, LineString, MultiLineString, mapping
from shapely.ops import linemerge, unary_union

DL = sys.argv[1]
OUT = sys.argv[2]

LON0, LON1, LAT0, LAT1 = -61.4, -53.5, -34.3, -24.6   # oeste, este, sur, norte
K = math.cos(math.radians((LAT0 + LAT1) / 2))
S = 100.0
W = round((LON1 - LON0) * K * S)
H = round((LAT1 - LAT0) * S)
CAJA = box(LON0, LAT0, LON1, LAT1)


def xy(lon, lat):
    return ((lon - LON0) * K * S, (LAT1 - lat) * S)


def path_lineas(g, tol):
    g = g.intersection(CAJA).simplify(tol, preserve_topology=False)
    if g.is_empty:
        return ""
    ls = [g] if g.geom_type == "LineString" else [x for x in getattr(g, "geoms", []) if x.geom_type == "LineString"]
    out = []
    for l in ls:
        cs = list(l.coords)
        if len(cs) < 2:
            continue
        out.append("M" + "L".join("%.1f,%.1f" % xy(*c) for c in cs))
    return "".join(out)


def path_poli(g, tol):
    g = g.intersection(CAJA).simplify(tol, preserve_topology=True)
    if g.is_empty:
        return ""
    ps = [g] if g.geom_type == "Polygon" else [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon"]
    out = []
    for p in ps:
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            out.append("M" + "L".join("%.1f,%.1f" % xy(*c) for c in cs[:-1]) + "Z")
    return "".join(out)


def cargar(n):
    return json.load(open(f"{DL}/{n}", encoding="utf-8"))["features"]


# --- países
PAISES = {"ARG": "Argentina", "PRY": "Paraguay", "URY": "Uruguay", "BRA": "Brasil"}
paises = []
for f in cargar("ne_10m_admin_0_countries.geojson"):
    a3 = f["properties"].get("ADM0_A3")
    if a3 in PAISES:
        d = path_poli(shape(f["geometry"]), 0.008)
        if d:
            paises.append({"id": a3, "n": PAISES[a3], "d": d})

# --- límites de provincias argentinas
prov = []
for f in cargar("ne_10m_admin_1_states_provinces_lines.geojson"):
    if f["properties"].get("ADM0_NAME") == "Argentina":
        prov.append(shape(f["geometry"]))
provincias = path_lineas(unary_union(prov), 0.008)

# --- ríos
R = cargar("rivers10.geojson")
par2 = next(f for f in R if f["properties"]["name"] == "Paraná" and f["properties"]["scalerank"] == 2 and f["properties"]["featurecla"] == "River")
par4 = next(f for f in R if f["properties"]["name"] == "Paraná" and f["properties"]["scalerank"] == 4 and f["properties"]["featurecla"] == "River")
par4l = next(f for f in R if f["properties"]["name"] == "Paraná" and f["properties"]["scalerank"] == 4 and f["properties"]["featurecla"] == "Lake Centerline")
uru = next(f for f in R if f["properties"]["name"] == "Uruguay")
p2 = par2["geometry"]["coordinates"]
paraguay = LineString(p2[0])                      # de Mato Grosso a la confluencia, frente a Corrientes
parana_bajo = MultiLineString(p2[1:])             # de la confluencia al Río de la Plata (con los brazos del delta)
parana_alto = MultiLineString(par4["geometry"]["coordinates"] + par4l["geometry"]["coordinates"])
parana = unary_union([parana_bajo, parana_alto])

# Iguazú: límite Argentina-Brasil al norte de -25,72 y al oeste de -53,90
ig = []
for f in cargar("ne_10m_admin_0_boundary_lines_land.geojson"):
    p = f["properties"]
    if {p.get("ADM0_LEFT"), p.get("ADM0_RIGHT")} == {"Argentina", "Brazil"}:
        g = shape(f["geometry"])
        for l in ([g] if g.geom_type == "LineString" else g.geoms):
            cs = list(l.coords)
            if all(c[1] > -25.72 and c[0] <= -53.905 for c in cs):
                ig.append(l)
iguazu = linemerge(ig)

rios = [
    {"id": "Paraná", "d": path_lineas(parana, 0.004)},
    {"id": "Uruguay", "d": path_lineas(shape(uru["geometry"]), 0.004)},
    {"id": "Paraguay", "d": path_lineas(paraguay, 0.004)},
    {"id": "Iguazú", "d": path_lineas(iguazu, 0.002)},
]

SEC = {"Bermejo", "Pilcomayo", "Salado", "Ibicuí", "Negro", "Carcarañá", "Jejui Guazu", "Gualeguay", "Corriente", "Tebicuary", "Aguapey", "Miriñay"}
secundarios = []
for f in R:
    n = f["properties"].get("name")
    if n in SEC and f["geometry"]:
        d = path_lineas(shape(f["geometry"]), 0.006)
        if d:
            secundarios.append({"n": n, "d": d})

lagos = []
for f in cargar("lakes10.geojson"):
    p = f["properties"]
    if p.get("name") and f["geometry"]:
        g = shape(f["geometry"])
        if g.intersects(CAJA):
            d = path_poli(g, 0.004)
            if d:
                lagos.append({"n": p["name"], "d": d})

# etiquetas fijas (coordenadas del mapa, x e y en las unidades del viewBox)
etiquetas = [
    {"t": "PARAGUAY", "x": 480, "y": 150, "c": "pais"},
    {"t": "BRASIL", "x": 628, "y": 600, "c": "pais"},
    {"t": "URUGUAY", "x": 480, "y": 830, "c": "pais"},
    {"t": "FORMOSA", "x": 170, "y": 105, "c": "prov"},
    {"t": "CHACO", "x": 105, "y": 245, "c": "prov"},
    {"t": "SANTA FE", "x": 40, "y": 520, "c": "prov", "a": "start"},
    {"t": "CORRIENTES", "x": 300, "y": 410, "c": "prov"},
    {"t": "MISIONES", "x": 578, "y": 215, "c": "prov"},
    {"t": "ENTRE RÍOS", "x": 212, "y": 700, "c": "prov"},
    {"t": "BUENOS AIRES", "x": 30, "y": 955, "c": "prov", "a": "start"},
    {"t": "Paraná", "x": 168, "y": 545, "c": "rio", "a": "start", "rio": "Paraná"},
    {"t": "Paraná", "x": 392, "y": 312, "c": "rio", "rio": "Paraná"},
    {"t": "Paraguay", "x": 296, "y": 220, "c": "rio", "a": "start", "rio": "Paraguay"},
    {"t": "Uruguay", "x": 334, "y": 600, "c": "rio", "a": "start", "rio": "Uruguay"},
    {"t": "Iguazú", "x": 628, "y": 80, "c": "rio", "rio": "Iguazú"},
]

out = {
    "fuente": "Natural Earth 10m (dominio público). El Iguazú, del límite Argentina-Brasil.",
    "etiquetas": etiquetas,
    "w": W, "h": H,
    "proj": {"lon0": LON0, "lat1": LAT1, "k": round(K, 6), "s": S},
    "paises": paises, "provincias": provincias, "rios": rios,
    "secundarios": secundarios, "lagos": lagos,
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("listo", W, H, "países", [p["id"] for p in paises], "ríos", [(r["id"], len(r["d"])) for r in rios],
      "secundarios", [s["n"] for s in secundarios], "lagos", [l["n"] for l in lagos])
