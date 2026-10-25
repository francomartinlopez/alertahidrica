"""Valida fenomenos/eventos.json antes de publicar.  Uso: python3 scripts/fenomenos/validar.py"""
import json, os, re, sys, datetime as dt
EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'fenomenos', 'eventos.json')
TIPOS = set('inundacion lluvia monzon marejada deslizamiento ciclon tornado granizo viento rayos calor calor_marino sequia incendio polvo frio nieve'.split())
CATS = set('servicios transporte logistica agro salud vivienda economia'.split())
CRIT = set('muertes afectados alerta_gdacs emergencia record intensidad'.split())
D = json.load(open(EV))
err = []
def e_(i, m): err.append(f'{i}: {m}')
for k in ('actualizado', 'desde', 'nota', 'comparacion', 'eventos'):
    if k not in D: err.append(f'falta la clave {k}')
ids = set()
for e in D['eventos']:
    i = e.get('id', '?')
    if i in ids: e_(i, 'id repetido')
    ids.add(i)
    for k in ('tipo', 'titulo', 'lugar', 'pais', 'inicio', 'fin', 'origen', 'gdacs', 'geom', 'muertes', 'afectados', 'evacuados', 'texto', 'intensidad', 'danos', 'efectos', 'criterio', 'fuentes'):
        if k not in e: e_(i, f'falta {k}')
    if e.get('tipo') not in TIPOS: e_(i, f"tipo inválido {e.get('tipo')}")
    if e.get('criterio') not in CRIT: e_(i, f"criterio inválido {e.get('criterio')}")
    try:
        dt.date.fromisoformat(e['inicio'])
        if e['fin']:
            dt.date.fromisoformat(e['fin'])
            if e['fin'] < e['inicio']: e_(i, 'fin antes de inicio')
            if e['fin'] < D['desde']: e_(i, 'terminó antes de "desde": sacarlo')
        if e['inicio'] > D['actualizado']: e_(i, 'empieza después de "actualizado"')
    except Exception: e_(i, 'fecha inválida')
    if e.get('origen') not in ('noticias', 'gdacs', 'ambos'): e_(i, 'origen inválido')
    if (e.get('origen') == 'noticias') != (not e.get('gdacs')): e_(i, 'origen y gdacs no coinciden')
    g = e.get('geom', {})
    if g.get('t') not in ('punto', 'area', 'trayectoria'): e_(i, 'geom inválida')
    if e.get('tipo') == 'ciclon' and (g.get('t') != 'trayectoria' or not 1 <= len(g.get('pts', [])) <= 10): e_(i, 'ciclón sin trayectoria de 1 a 10 puntos')
    if e.get('tipo') != 'ciclon' and g.get('t') == 'trayectoria': e_(i, 'trayectoria en algo que no es ciclón')
    for lo, la in (g.get('pts') or [g.get('c', [0, 0])]):
        if not (-180 <= lo <= 180 and -60 <= la <= 85): e_(i, 'coordenadas fuera de rango')
    if g.get('t') == 'area' and not (0 < g.get('r', 0) <= 2500): e_(i, 'radio inválido')
    F = e.get('fuentes') or []
    if not F: e_(i, 'sin fuentes')
    for f in F:
        if not str(f.get('u', '')).startswith('https://'): e_(i, f"fuente sin https: {f.get('u')}")
    if len({f.get('u') for f in F}) != len(F): e_(i, 'fuente repetida')
    d = e.get('danos', {})
    if d.get('fuente') is not None and not 0 <= d['fuente'] < len(F): e_(i, 'danos.fuente fuera de rango')
    if (d.get('usd') is not None or d.get('rango')) and d.get('tipo') not in ('oficial', 'aseguradora', 'consultora', 'prensa'): e_(i, 'daños sin tipo de estimación')
    I = e.get('intensidad') or {}
    if I.get('nivel') not in (None, 1, 2, 3): e_(i, 'nivel de intensidad inválido')
    if I.get('fuente') is not None and not 0 <= I['fuente'] < len(F): e_(i, 'intensidad.fuente fuera de rango')
    for p in ('corto', 'mediano', 'largo'):
        for x in (e.get('efectos') or {}).get(p, []):
            if x.get('cat') not in CATS: e_(i, f"categoría de efecto inválida {x.get('cat')}")
    if re.search(r'El Niño|La Niña|cambio climático', e.get('texto', '')): e_(i, 'el texto atribuye causas (El Niño / cambio climático)')
    if 'TODO' in json.dumps(e, ensure_ascii=False): e_(i, 'TODO')
C = D.get('capas')
if C:
    for v in ('lluvia', 'temp'):
        for w in ('7', '30', '90'):
            f = os.path.join(os.path.dirname(EV), C['archivos'][v][w])
            if not os.path.exists(f): err.append(f'falta la capa {f}')
print(f"{len(D['eventos'])} eventos; {len(err)} problemas")
for x in err: print(' -', x)
sys.exit(1 if err else 0)
