"""Mantenimiento diario del mapa de fenómenos anómalos (fenomenos/eventos.json).

Uso:  python3 scripts/fenomenos/revisar_fuentes.py [AAAA-MM-DD] [--comparar]   (por defecto, hoy; la comparación se recalcula los lunes)

Hace, sin tocar los textos:
  1. Corre la ventana de 90 días: "actualizado" = hoy, "desde" = hoy - 90 días, y saca los eventos que terminaron antes de "desde".
  2. Actualiza las trayectorias de los ciclones que tienen fuente de NASA EONET (y su intensidad por viento máximo).
  3. Recalcula la comparación con años anteriores (alertas naranja y roja de GDACS en la misma ventana, 2012 a hoy).
  4. Imprime un INFORME con lo que hay que revisar a mano:
     - alertas naranja/roja de GDACS que no están vinculadas a ningún evento (entran siempre),
     - inundaciones con alerta verde de GDACS con >=1 muerto o >=1.000 afectados no vinculadas,
     - ciclones de EONET activos en el período que no están en el mapa,
     - eventos "en curso" (fin = null) para confirmar si siguen.
Lo que se revisa y NO entra se anota en eventos.json["revisados"] ("eonet": ids EONET_..., "gdacs": ids numéricos) para que no se vuelva a informar.
Solo usa la biblioteca estándar y curl.
"""
import sys, os, json, re, subprocess, datetime as dt
AQUI = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(AQUI, '..', '..', 'fenomenos', 'eventos.json')
G = 'https://www.gdacs.org/gdacsapi/api/events'

def get(url, t=120):
    r = subprocess.run(['curl', '-s', '--fail', '--max-time', str(t), '--retry', '2', url], capture_output=True)
    try: return json.loads(r.stdout)
    except Exception: return None

def gdacs_lista(desde, hasta, alerta, tipos='TC;FL;DR;WF'):
    out, p = [], 1
    while p <= 40:
        d = get(f'{G}/geteventlist/SEARCH?eventlist={tipos}&fromdate={desde}&todate={hasta}&alertlevel={alerta}&pagesize=100&pagenumber={p}')
        if not d: break
        fs = d.get('features', []); out += fs
        if len(fs) < 100: break
        p += 1
    return out

def sendai(tipo, i, paises):
    d = get(f'{G}/geteventdata?eventtype={tipo}&eventid={i}', 90)
    if not d: return 0, 0, []
    muertes = afect = 0; lineas = []
    for x in d['properties'].get('sendai') or []:
        desc = x.get('description', '')
        if not any(p.split()[0].lower() in desc.lower() for p in paises): continue
        try: v = int(float(x.get('sendaivalue') or 0))
        except Exception: v = 0
        if x.get('sendainame') == 'death': muertes += v
        if x.get('sendainame') in ('displaced', 'affected') and '[people]' in desc: afect += v
        lineas.append(desc[:110])
    return muertes, afect, lineas

def main():
    arg = [a for a in sys.argv[1:] if not a.startswith('--')]
    hoy = dt.date.fromisoformat(arg[0]) if arg else dt.date.today()
    desde = hoy - dt.timedelta(days=90)
    D = json.load(open(EV))
    eventos = D['eventos']
    informe = []

    # 1. ventana
    antes = len(eventos)
    eventos = [e for e in eventos if not e.get('fin') or e['fin'] >= desde.isoformat()]
    D['eventos'] = eventos; D['actualizado'] = hoy.isoformat(); D['desde'] = desde.isoformat()
    informe.append(f'Ventana {desde} a {hoy}: salieron {antes - len(eventos)} eventos terminados antes de {desde}.')

    # 2. ciclones con EONET
    for e in eventos:
        if e['tipo'] != 'ciclon': continue
        u = next((f['u'] for f in e['fuentes'] if 'eonet.gsfc.nasa.gov/api/v3/events/' in f['u']), None)
        if not u: continue
        d = get(u)
        if not d or not d.get('geometry'): continue
        pts = [g['coordinates'] for g in d['geometry']]
        k = min(10, len(pts))
        sel = [pts[round(j * (len(pts) - 1) / (k - 1))] for j in range(k)] if k > 1 else pts
        e['geom'] = {'t': 'trayectoria', 'pts': [[round(a, 2), round(b, 2)] for a, b in sel], 'src': 'eonet'}
        kt = max((g.get('magnitudeValue') or 0) for g in d['geometry']); kmh = round(kt * 1.852)
        I = e.get('intensidad') or {}
        if 'vientos máximos sostenidos' in (I.get('medida') or '') or not I.get('nivel'):
            nv = 1 if kmh < 178 else 2 if kmh < 252 else 3
            cat = 'tormenta tropical' if kmh < 119 else f"categoría {1 if kmh < 154 else 2 if kmh < 178 else 3 if kmh < 209 else 4 if kmh < 252 else 5}"
            e['intensidad'] = {'nivel': nv, 'medida': f'vientos máximos sostenidos de {kmh} km/h ({cat})', 'ref': 'pico de la tormenta según NASA EONET; escala Saffir-Simpson', 'fuente': None}
        if d.get('closed') and not e.get('fin'):
            informe.append(f"EONET cerró {e['id']} ({e['titulo']}) el {d['closed'][:10]}: revisar 'fin'.")
    nombres = ' '.join(e['titulo'].lower() for e in eventos if e['tipo'] == 'ciclon')
    REV = D.setdefault('revisados', {'eonet': [], 'gdacs': []})  # ids revisados que no entraron (no se vuelven a informar)
    st = get(f'https://eonet.gsfc.nasa.gov/api/v3/events?start={desde}&end={hoy}&status=all&category=severeStorms&limit=500') or {}
    for s in st.get('events', []):
        n = s['title'].split()[-1].lower()
        if n not in nombres and s['id'] not in REV.get('eonet', []):
            mx = max((g.get('magnitudeValue') or 0) for g in s['geometry'])
            informe.append(f"Ciclón de EONET no cargado: {s['title']} ({s['geometry'][0]['date'][:10]} a {s['geometry'][-1]['date'][:10]}, {round(mx * 1.852)} km/h) {s['id']}. Entra solo si cumple el criterio.")

    # 3. comparación con años anteriores (los lunes, o con --comparar; tarda varios minutos)
    anios = []
    for y in (range(2012, hoy.year + 1) if (hoy.weekday() == 0 or '--comparar' in sys.argv) else []):
        a, b = dt.date(y, desde.month, desde.day), dt.date(y, hoy.month, hoy.day)
        if a > b: a = dt.date(y - 1, desde.month, desde.day)
        fs = gdacs_lista(a.isoformat(), b.isoformat(), 'Orange;Red')
        c = {t: sum(1 for x in fs if x['properties']['eventtype'] == t) for t in ('TC', 'FL', 'DR', 'WF')}
        anios.append({'a': y, **c, 'rojas': sum(1 for x in fs if x['properties']['alertlevel'].lower() == 'red')})
    if not anios:
        pass
    elif all(sum(v for k, v in x.items() if k in ('TC', 'FL', 'DR', 'WF')) == 0 for x in anios):
        informe.append('No se pudo recalcular la comparación (GDACS no respondió): se dejó la anterior.')
    else:
        MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        D['comparacion']['anios'] = anios
        D['comparacion']['ventana'] = f'{desde.day} de {MES[desde.month - 1]} a {hoy.day} de {MES[hoy.month - 1]}'

    # 4. GDACS no vinculado
    vinc = {g['id'] for e in eventos for g in e.get('gdacs', [])} | set(REV.get('gdacs', []))
    for f in gdacs_lista(desde.isoformat(), hoy.isoformat(), 'Orange;Red'):
        p = f['properties']
        if p['eventid'] not in vinc:
            informe.append(f"GDACS {p['alertlevel']} SIN CARGAR (entra siempre): {p['eventtype']} {p['eventid']} {p['name']} | {p['country']} | {p['fromdate'][:10]} a {p['todate'][:10]} | {p.get('severitydata', {}).get('severitytext', '')} | https://www.gdacs.org/report.aspx?eventid={p['eventid']}&eventtype={p['eventtype']}")
    for f in gdacs_lista(desde.isoformat(), hoy.isoformat(), 'Green', 'FL'):
        p = f['properties']
        # solo las que se actualizaron en los últimos 10 días (las anteriores ya se revisaron otros días)
        if p['eventid'] in vinc or p['todate'][:10] < (hoy - dt.timedelta(days=10)).isoformat(): continue
        m, a, L = sendai('FL', p['eventid'], [c['countryname'] for c in p.get('affectedcountries', [])] or [p['country']])
        if m >= 1 or a >= 1000:
            informe.append(f"GDACS verde con {m} muertos / {a} afectados SIN CARGAR: FL {p['eventid']} {p['country']} {p['fromdate'][:10]} a {p['todate'][:10]} | " + ' ; '.join(L[:5]))

    for e in eventos:
        if not e.get('fin'):
            informe.append(f"En curso, confirmar si sigue: {e['id']} {e['titulo']} (desde {e['inicio']})")

    json.dump(D, open(EV, 'w'), ensure_ascii=False, indent=1)
    print('\n'.join(informe))

if __name__ == '__main__':
    main()
