#!/usr/bin/env python3
"""Arma datos-informe.json para la web de informes de Plexum.

Especificación: «Datos que cada web publica para la web de informes de Plexum», v1.3
(parte común y apartado 14, Alerta Hídrica).

Lee datos.json, nino34.json y lluvias.json (y el datos-informe.json anterior, para
los faltantes) y escribe datos-informe.json en la raíz del sitio. No cambia nada de
lo que se ve en la web. No inventa ni estima: publica solo lo que la web ya muestra,
cada dato con su fecha real.

Uso: python3 scripts/informe/generar_datos_informe.py [carpeta del sitio]
Sale con código 1 y no escribe nada si el archivo no pasa la validación.
"""
import calendar, datetime as dt, json, math, pathlib, re, sys, unicodedata

RAIZ = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
WEB = 'Alerta Hídrica'
VERSION = '1.3'
BASE = 'https://francomartinlopez.github.io/alertahidrica/'
EJE = 'Clima y riesgo productivo'
AR = dt.timezone(dt.timedelta(hours=-3))
HOY = dt.datetime.now(AR).date()

PROVINCIAS = ['Buenos Aires', 'CABA', 'Catamarca', 'Chaco', 'Chubut', 'Córdoba', 'Corrientes', 'Entre Ríos',
              'Formosa', 'Jujuy', 'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquén', 'Río Negro', 'Salta',
              'San Juan', 'San Luis', 'Santa Cruz', 'Santa Fe', 'Santiago del Estero', 'Tierra del Fuego', 'Tucumán']
ALIAS_PROV = {'Ciudad de Buenos Aires': 'CABA', 'Ciudad Autónoma de Buenos Aires': 'CABA'}
RUBROS = ['Industria', 'Agro', 'Minería', 'Energía', 'Construcción', 'Comercio y servicios']
EXPOSICION = ['Exporta', 'Importa insumos', 'Deuda en dólares', 'Energía intensiva', 'Mano de obra intensiva',
              'Vende al Estado', 'Vende a minería y energía']
NIVELES = ['mundo', 'país', 'nacional', 'provincia', 'localidad']
TIPOS = ['norma', 'inversión', 'empresa en crisis', 'licitación', 'conflicto', 'elección', 'encuesta',
         'medida comercial', 'clima', 'otro']

# Puertos de la sección Ríos: localidad y provincia (geografía fija; rios no trae la provincia).
PUERTOS = {
    'Itatí': ('Itatí', 'Corrientes'), 'Isla del Cerrito': ('Isla del Cerrito', 'Chaco'),
    'Corrientes': ('Corrientes', 'Corrientes'), 'Barranqueras': ('Barranqueras', 'Chaco'),
    'Goya': ('Goya', 'Corrientes'), 'Reconquista': ('Reconquista', 'Santa Fe'), 'La Paz': ('La Paz', 'Entre Ríos'),
    'Santa Fe': ('Santa Fe', 'Santa Fe'), 'Paraná': ('Paraná', 'Entre Ríos'), 'Rosario': ('Rosario', 'Santa Fe'),
    'Victoria': ('Victoria', 'Entre Ríos'), 'Santo Tomé': ('Santo Tomé', 'Corrientes'),
    'Paso de los Libres': ('Paso de los Libres', 'Corrientes'), 'Concordia': ('Concordia', 'Entre Ríos'),
    'Concepción del Uruguay': ('Concepción del Uruguay', 'Entre Ríos'), 'Puerto Iguazú': ('Puerto Iguazú', 'Misiones'),
    'Puerto Pilcomayo': ('Puerto Pilcomayo', 'Formosa'), 'Formosa': ('Formosa', 'Formosa'),
}
# Mismos nombres que la web (FASES de index.html).
FASES = {'super_nino': 'Súper Niño', 'nino_fuerte': 'El Niño fuerte', 'nino': 'El Niño',
         'nino_retirada': 'El Niño en retirada', 'neutral': 'ENSO neutral', 'nina': 'La Niña',
         'nina_fuerte': 'La Niña fuerte', 'super_nina': 'Súper Niña'}
# Mismas etiquetas que el mapa de provincias de la web.
EST_PROV = {'vigente': 'Emergencia vigente', 'vencida': 'Emergencia vencida', 'plan': 'Plan sin emergencia',
            'sin_datos': 'Sin medidas halladas'}
EST_RIO = {'evacuacion': 'sobre la cota de evacuación', 'alerta': 'sobre la cota de alerta'}
NIV_RUBRO = {'alto': 'Riesgo alto', 'medio': 'Riesgo medio', 'bajo': 'Riesgo bajo', 'favorable': 'Favorable',
             'mixto': 'Mixto', 'sin_datos': 'Sin datos'}
# Rubros y exposición de cada tarjeta de «Otros rubros».
RUBRO_MAP = {'hidro': (['Energía'], ['Energía intensiva']),
             'fluvial': (['Agro', 'Industria', 'Comercio y servicios'], ['Exporta', 'Importa insumos']),
             'construccion': (['Construcción'], []),
             'energia': (['Energía'], ['Energía intensiva'])}
# Regiones del pronóstico de lluvias, igual que la web (sección Lluvias, «Por región»). Amazonia queda afuera.
REGIONES = {'Cuenca alta (sur de Brasil, Paraguay, Misiones)': [-30, -20, -58, -48], 'Litoral y NEA': [-33, -26, -62, -57],
            'Región núcleo': [-36, -31, -64, -58], 'Sur bonaerense y La Pampa': [-40, -36, -66, -58],
            'NOA': [-28, -22, -68, -63], 'Cuyo': [-36, -28, -70, -66], 'Comahue': [-42, -37, -72, -65],
            'Río Uruguay y sur de Brasil': [-33, -27, -57, -50]}
MESES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'set': 9,
         'oct': 10, 'nov': 11, 'dic': 12}
MES_NOMBRE = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
              'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}

MESES_TXT = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

faltantes = []


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def limpio(s):
    """Saca el marcado de la web (**negrita** y [texto](url))."""
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s or '')
    return re.sub(r'\s+', ' ', s.replace('**', '')).strip()


def corto(s, n=60):
    """Hasta n palabras, cortando en una oración completa si se puede."""
    s = limpio(s)
    if len(s.split()) <= n:
        return s
    frases = re.split(r'(?<=[.;])\s+', s)
    out = ''
    for f in frases:
        prueba = (out + ' ' + f).strip()
        if len(prueba.split()) > n:
            break
        out = prueba
    return out if out else ' '.join(s.split()[:n - 1]) + '…'


def links(md):
    return re.findall(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', md or '')


def fecha_corta(txt, ref):
    """'25 nov' -> date, con el año de la actualización (o el anterior si el mes queda adelante)."""
    m = re.match(r'\s*(\d{1,2})\s+([a-zé]{3})', txt or '', re.I)
    if not m or m.group(2).lower()[:3] not in MESES:
        return None
    mes, dia = MESES[m.group(2).lower()[:3]], int(m.group(1))
    anio = ref.year - (1 if mes > ref.month + 1 else 0)
    try:
        return dt.date(anio, mes, dia)
    except ValueError:
        return None


def fin_de_mes(anio, mes):
    return dt.date(anio, mes, calendar.monthrange(anio, mes)[1])


def alcance(nivel, provincia='', localidad='', pais='Argentina'):
    return {'nivel': nivel, 'provincia': provincia, 'localidad': localidad, 'pais': pais}


def prov_ok(p):
    p = ALIAS_PROV.get(p, p)
    return p if p in PROVINCIAS else None


def redondeo(x):  # igual que Math.round de la web
    return int(math.floor(x + 0.5))


def leer(nombre):
    with open(RAIZ / nombre, encoding='utf-8') as f:
        return json.load(f)


D = leer('datos.json')
N = leer('nino34.json')
L = leer('lluvias.json')
try:
    ANTES = leer('datos-informe.json')
except (FileNotFoundError, json.JSONDecodeError):
    ANTES = {}
ACT = dt.date.fromisoformat(D['meta']['actualizado'])
ult_antes = {i['id']: i.get('fecha_dato') for i in ANTES.get('indicadores', [])}
ult_antes.update({f['id']: f.get('ultimo_dato') for f in ANTES.get('faltantes', []) if f['id'] not in ult_antes})


def falta(id_, nombre, motivo):
    faltantes.append({'id': id_, 'nombre': nombre, 'motivo': motivo, 'ultimo_dato': ult_antes.get(id_)})


def ind(id_, nombre, valor, unidad, fecha, fuente, url, alc, rubros=(), subrubros=(), expo=(), variacion=None, periodo=None):
    r = {'id': id_, 'nombre': nombre, 'valor': valor, 'unidad': unidad}
    if variacion:
        r['variacion'] = variacion
    r['fecha_dato'] = fecha.isoformat()
    if periodo:
        r['periodo'] = periodo
    r.update({'fuente_original': fuente, 'eje': EJE, 'alcance': alc, 'rubros': list(rubros),
              'subrubros': list(subrubros), 'exposicion': list(expo), 'url': url})
    return r


indicadores, novedades, agenda = [], [], []

# 1. Estado del fenómeno ENSO
F = D.get('fase') or {}
if F.get('clave') in FASES:
    fn = F.get('fecha_noaa')
    if not fn:
        m = re.search(r'discusión del (\d{1,2}) ([a-z]{3})', F.get('fuente', ''))
        fn = fecha_corta(f'{m.group(1)} {m.group(2)}', dt.date.fromisoformat(F['revisado'])).isoformat() if m else F.get('revisado')
    indicadores.append(ind('estado-enso', 'Estado del fenómeno ENSO (El Niño o La Niña) según NOAA', FASES[F['clave']], '',
                           dt.date.fromisoformat(fn), 'NOAA CPC', BASE + '#nino', alcance('mundo', pais='')))
else:
    falta('estado-enso', 'Estado del fenómeno ENSO (El Niño o La Niña) según NOAA', 'Falta la fase del fenómeno en los datos de la web')

# 2. ONI y RONI (trimestre más reciente que muestra la web)
for clave, id_, nom in (('oni', 'oni', 'Índice ONI de NOAA (anomalía de Niño-3.4, promedio de tres meses)'),
                        ('roni', 'roni', 'Índice relativo RONI de NOAA (Niño-3.4 menos el resto de los trópicos, promedio de tres meses)')):
    txt = F.get(clave) or ''
    m = re.match(r'\s*([+\-−]?\d+(?:,\d+)?)\s*°C\s*\(([^)]*)\)', txt)
    meses = re.findall(r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)', m.group(2)) if m else []
    anios = re.findall(r'(\d{4})', m.group(2)) if m else []
    if m and meses and anios:
        v = float(m.group(1).replace('−', '-').replace(',', '.'))
        indicadores.append(ind(id_, f'{nom}: {m.group(2)}', v, '°C', fin_de_mes(int(anios[-1]), MES_NOMBRE[meses[-1]]),
                               'NOAA CPC', BASE + '#nino', alcance('mundo', pais='')))
    else:
        falta(id_, nom, 'El dato de la web no tiene el formato esperado')

# 3. Niño-3.4 diario, absoluto y relativo
try:
    f0, v0 = N['ultimo']
    f0 = dt.date.fromisoformat(f0)
    serie = N['anios'][str(f0.year)]
    rel = N['relativo']['anios'][str(f0.year)]
    i = (f0 - dt.date(f0.year, 1, 1)).days
    assert len(serie) == i + 1 and abs(serie[i] - v0) < 1e-9
    prev = serie[i - 1] if i else N['anios'][str(f0.year - 1)][-1]
    indicadores.append(ind('nino34-diario', 'Anomalía diaria de la temperatura del mar en la región Niño-3.4', round(v0, 2), '°C', f0,
                           'NOAA PSL (OISST v2.1)', BASE + '#nino', alcance('mundo', pais=''),
                           variacion={'valor': round(v0 - prev, 2), 'unidad': '°C', 'contra': 'día anterior'}))
    if len(rel) == len(serie):
        rprev = rel[i - 1] if i else N['relativo']['anios'][str(f0.year - 1)][-1]
        indicadores.append(ind('nino34-relativo-diario', 'Índice relativo diario de Niño-3.4 (descuenta el calentamiento del resto de los trópicos)',
                               round(rel[i], 2), '°C', f0, 'NOAA PSL (OISST v2.1) y NOAA ERSSTv5', BASE + '#nino',
                               alcance('mundo', pais=''),
                               variacion={'valor': round(rel[i] - rprev, 2), 'unidad': '°C', 'contra': 'día anterior'}))
    else:
        falta('nino34-relativo-diario', 'Índice relativo diario de Niño-3.4', 'La serie relativa no está al día')
except Exception:
    falta('nino34-diario', 'Anomalía diaria de la temperatura del mar en la región Niño-3.4', 'La serie diaria no tiene el formato esperado')

# 4. Altura de los ríos en cada puerto
for r in D.get('rios', []):
    loc, prov = PUERTOS.get(r['puerto'], ('', ''))
    id_ = 'altura-rio-' + slug(r['puerto'])
    nom = f"Altura del río {r['rio']} en {r['puerto']}"
    hist = [h for h in r.get('hist') or [] if isinstance(h[1], (int, float))]
    if not hist:
        falta(id_, nom, 'Sin medición publicada')
        continue
    fh, vh = hist[-1]
    var = None
    if len(hist) > 1:
        var = {'valor': round(vh - hist[-2][1], 2), 'unidad': 'm', 'contra': f'medición anterior ({hist[-2][0]})'}
    alc = alcance('localidad', prov, loc) if prov else alcance('nacional')
    indicadores.append(ind(id_, nom, vh, 'm', dt.date.fromisoformat(fh), 'Prefectura Naval Argentina e INA',
                           BASE + '#rios', alc, variacion=var))
    if r.get('estado') in EST_RIO:
        m2 = lambda x: f'{x:.2f}'.replace('.', ',')
        donde = r['puerto'] if (not prov or prov == r['puerto']) else f"{r['puerto']} ({prov})"
        umb = f"la cota de alerta es {m2(r['alerta'])} m y la de evacuación, {m2(r['evac'])} m"
        novedades.append({'id': f"rio-{slug(r['puerto'])}-{r['estado']}", 'fecha_dato': fh,
                          'titulo': f"El río {r['rio']} en {r['puerto']} está {EST_RIO[r['estado']]}",
                          'resumen': corto(f"El {r['rio']} marcó {m2(vh)} m en {donde} el {dt.date.fromisoformat(fh).day} de {MESES_TXT[dt.date.fromisoformat(fh).month - 1]}; {umb}."),
                          'tipo': 'clima', 'eje': EJE, 'alcance': alc, 'rubros': [], 'subrubros': [], 'exposicion': [],
                          'url': BASE + '#rios'})

# 5. Pronóstico trimestral de lluvia por región (primer trimestre, igual que «Por región» en la web)
try:
    G = L['grilla'][0]
    trim = L['trimestres'][0]
    emit = dt.date.fromisoformat(L['emitido'])
    for reg, (a, b, c, e) in REGIONES.items():
        sa = sb = k = 0
        idx = 0
        for la in L['lats']:
            for lo in L['lons']:
                v = G[idx]; idx += 1
                if v and a <= la <= b and c <= lo <= e:
                    sa += v[0]; sb += v[2]; k += 1
        for cual, val, txt in (('sobre', sa, 'sobre'), ('bajo', sb, 'bajo')):
            id_ = f'lluvia-pronostico-{cual}-normal-{slug(reg)}'
            nom = f'Probabilidad de lluvia {txt} lo normal en {trim} (pronóstico NOAA NMME): {reg}'
            if k:
                indicadores.append(ind(id_, nom, redondeo(val / k), '%', emit, 'NOAA CPC (NMME)', BASE + '#lluvias',
                                       alcance('nacional')))
            else:
                falta(id_, nom, 'Sin pronóstico para la región en este trimestre')
except Exception:
    falta('lluvia-pronostico', 'Pronóstico trimestral de lluvia por región', 'El pronóstico no tiene el formato esperado')

# 6. Desplazados por provincia
serie_ev = (D.get('evacuados') or {}).get('serie') or {}
for p in (D.get('evacuados') or {}).get('provs', []):
    prov = prov_ok(p.get('prov', ''))
    fe = fecha_corta(p.get('fecha', ''), ACT)
    if not prov or not fe or not isinstance(p.get('total'), (int, float)):
        continue
    s = [x for x in serie_ev.get(p['prov'], []) if x[0] < fe.isoformat() and x[1] != p['total']]
    var = {'valor': p['total'] - s[-1][1], 'unidad': 'personas', 'contra': f'dato anterior ({s[-1][0]})'} if s else None
    fuente = (links(p.get('fuente'))[0][0].split(',')[0] if links(p.get('fuente')) else 'Partes oficiales y prensa')
    indicadores.append(ind('desplazados-' + slug(prov), f'Personas evacuadas y autoevacuadas por las crecidas: {prov}',
                           p['total'], 'personas', fe, fuente, BASE + '#hoy-mas', alcance('provincia', prov), variacion=var))

# 7. Emergencia hídrica por provincia
for nombre, p in (D.get('provincias') or {}).items():
    prov = prov_ok(nombre)
    if prov and p.get('estado') in EST_PROV:
        indicadores.append(ind('emergencia-' + slug(prov), f'Emergencia hídrica o climática provincial: {prov}', EST_PROV[p['estado']], '',
                               ACT, 'Boletines oficiales y gobiernos provinciales', BASE + '#mapa', alcance('provincia', prov)))

# 8. Riesgo climático por rubro (sección «Otros rubros»)
RB = D.get('rubros') or {}
for it in RB.get('items', []):
    rub, expo = RUBRO_MAP.get(it['id'], ([], []))
    if it.get('nivel') in NIV_RUBRO and RB.get('actualizado'):
        indicadores.append(ind('riesgo-climatico-' + slug(it['id']), f"Riesgo climático: {it['rubro']}", NIV_RUBRO[it['nivel']], '',
                               dt.date.fromisoformat(RB['actualizado']), 'Alerta Hídrica, con datos de las fuentes de la sección',
                               BASE + '#rubros', alcance('nacional'), rub, [], expo))
    else:
        falta('riesgo-climatico-' + slug(it['id']), f"Riesgo climático: {it.get('rubro', it['id'])}", 'Sin nivel de riesgo publicado')

# Novedades: alertas del SMN del día
A = D.get('alertas_smn') or {}
if A.get('fecha') and dt.date.fromisoformat(A['fecha']) >= ACT:
    lk = links(A.get('fuente'))
    url = next((u for t, u in lk if 'smn.gob.ar' in u), lk[0][1] if lk else 'https://www.smn.gob.ar/alertas')
    for nombre, x in (A.get('prov') or {}).items():
        prov = prov_ok(nombre)
        if not prov:
            continue
        novedades.append({'id': f"{A['fecha']}-alerta-smn-{slug(prov)}", 'fecha_dato': A['fecha'],
                          'titulo': f"Alerta {x.get('nivel', '')} del SMN en {prov}",
                          'resumen': corto(x.get('fen', '')), 'tipo': 'clima', 'eje': EJE,
                          'alcance': alcance('provincia', prov), 'rubros': [], 'subrubros': [], 'exposicion': [], 'url': url})

# Novedades: temporales severos de los últimos 90 días
TIPOS_T = {'granizo': 'granizo', 'viento': 'viento', 'tornado': 'tornado', 'lluvia': 'lluvia intensa'}
for e in (D.get('tormentas') or {}).get('eventos', []):
    try:
        f = dt.date.fromisoformat(e['f'])
    except (KeyError, ValueError):
        continue
    if (HOY - f).days > 90:
        continue
    prov = prov_ok(e.get('prov', ''))
    lugar = re.sub(r'\s*\([^)]*\)', '', e.get('lugar', '')).strip()
    loc = lugar if lugar and not re.search(r',| y |otras', lugar) else ''
    tip = [TIPOS_T[t] for t in TIPOS_T if t in e.get('tipos', [])]
    tip_txt = ', '.join(tip[:-1]) + ' y ' + tip[-1] if len(tip) > 1 else (tip[0] if tip else 'tormenta')
    lk = links(e.get('fuente'))
    novedades.append({'id': f"{e['f']}-temporal-{slug(lugar)[:40]}", 'fecha_dato': e['f'],
                      'titulo': f"Temporal con {tip_txt} en {lugar}" + (f' ({prov})' if prov else ''),
                      'resumen': corto(f"{e.get('texto', '')} {e.get('danos', '')}"), 'tipo': 'clima', 'eje': EJE,
                      'alcance': alcance('localidad' if (loc and prov) else 'provincia', prov, loc) if prov else alcance('nacional'),
                      'rubros': [], 'subrubros': [], 'exposicion': [],
                      'url': lk[0][1] if lk else BASE + '#tormentas'})
novedades.sort(key=lambda n: n['fecha_dato'], reverse=True)

# Agenda: publicación de los pronósticos que usa la web, próximos 60 días
def segundo_jueves(a, m):
    d = dt.date(a, m, 1)
    return d + dt.timedelta(days=(3 - d.weekday()) % 7 + 7)


fin = HOY + dt.timedelta(days=60)
a, m = HOY.year, HOY.month
for _ in range(3):
    for fecha, evento, url, alc in (
        (dt.date(a, m, 5), 'Pronóstico estacional del ECMWF (SEAS5): Niño-3.4 y lluvias de los próximos meses',
         'https://www.ecmwf.int/en/forecasts/datasets/nino-plumes-seasonal-forecast-seas5', alcance('mundo', pais='')),
        (dt.date(a, m, 9), 'Pronóstico trimestral de lluvias y de Niño-3.4 de NOAA (NMME), que usa la sección Lluvias',
         'https://www.cpc.ncep.noaa.gov/products/NMME/', alcance('nacional')),
        (segundo_jueves(a, m), 'Discusión mensual de NOAA sobre El Niño: estado del fenómeno ENSO e índices ONI y RONI',
         'https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml', alcance('mundo', pais='')),
        (dt.date(a, m, 13), 'Pronóstico estacional multimodelo de Copernicus (C3S)',
         'https://climate.copernicus.eu/seasonal-forecasts', alcance('mundo', pais=''))):
        if HOY < fecha <= fin:
            agenda.append({'fecha': fecha.isoformat(), 'evento': evento, 'eje': EJE, 'alcance': alc, 'rubros': [], 'url': url})
    a, m = (a + 1, 1) if m == 12 else (a, m + 1)
agenda.sort(key=lambda x: x['fecha'])

# Faltantes fijos: lo que pide el apartado 14 y la web no muestra
falta('reserva-agua-suelo', 'Reserva de agua en el suelo por provincia', 'La web no muestra la reserva de agua en el suelo')
falta('anomalia-lluvia-observada-provincia', 'Anomalía de lluvia observada por provincia',
      'La web muestra la lluvia observada solo como mapa (capas de NOAA), sin valores por provincia; se publica el pronóstico trimestral por región')
# Indicadores que estaban en el archivo anterior y esta vez no salieron
ids_ahora = {i['id'] for i in indicadores} | {f['id'] for f in faltantes}
for i in ANTES.get('indicadores', []):
    if i['id'] not in ids_ahora:
        falta(i['id'], i.get('nombre', i['id']), 'Sin dato en esta actualización')
for f in ANTES.get('faltantes', []):
    if f['id'] not in ids_ahora and f['id'] not in {x['id'] for x in faltantes} and not any(f['id'].startswith(p) for p in ('reserva-', 'anomalia-')):
        faltantes.append(f)

# Versión 1.3: tipo de valor, frecuencia, comparaciones, serie y grupos
TIPOS_VALOR = ['tasa', 'nivel', 'estado']
FRECUENCIAS = ['diaria', 'semanal', 'mensual', 'trimestral', 'semestral', 'anual']
ESCALA_EMERGENCIA = ['Sin medidas halladas', 'Plan sin emergencia', 'Emergencia vencida', 'Emergencia vigente']


def serie_fin_de_mes(puntos, n=25):
    """Un valor por mes (el último de cada mes, con su fecha real), del más viejo al más nuevo."""
    por_mes = {}
    for f, v in sorted(puntos):
        if isinstance(v, (int, float)):
            por_mes[f[:7]] = (f, v)
    return [{'fecha': f, 'valor': v} for f, v in sorted(por_mes.values())][-n:]


def puntos_nino(anios, hasta):
    """Valores diarios de nino34.json desde dos años antes hasta la fecha del último dato."""
    pts = []
    for anio in range(hasta.year - 2, hasta.year + 1):
        for k, v in enumerate(anios.get(str(anio), [])):
            f = dt.date(anio, 1, 1) + dt.timedelta(days=k)
            if f <= hasta and v is not None:
                pts.append((f.isoformat(), round(v, 2)))
    return pts


def comparaciones(serie):
    if len(serie) < 2:
        return []
    c = ['mensual']
    if dt.date.fromisoformat(serie[0]['fecha']) <= dt.date.fromisoformat(serie[-1]['fecha']) - dt.timedelta(days=365):
        c.append('interanual')
    return c


RIOS_POR_ID = {'altura-rio-' + slug(r['puerto']): r for r in D.get('rios', [])}
for i in indicadores:
    id_ = i['id']
    serie, grupo = None, None
    if id_ == 'estado-enso':
        tv, fr = 'estado', 'mensual'
    elif id_ in ('oni', 'roni'):
        tv, fr = 'tasa', 'mensual'
    elif id_ in ('nino34-diario', 'nino34-relativo-diario'):
        tv, fr = 'tasa', 'diaria'
        anios = N['anios'] if id_ == 'nino34-diario' else N['relativo']['anios']
        serie = serie_fin_de_mes(puntos_nino(anios, dt.date.fromisoformat(i['fecha_dato'])))
    elif id_.startswith('altura-rio-'):
        tv, fr = 'nivel', 'diaria'
        serie = serie_fin_de_mes([tuple(h) for h in RIOS_POR_ID[id_].get('hist') or []])
    elif id_.startswith('lluvia-pronostico-'):
        tv, fr = 'tasa', 'mensual'
        cual = 'sobre' if '-sobre-' in id_ else 'bajo'
        grupo = {'id': f'lluvia-pronostico-{cual}-normal-por-region',
                 'nombre': f'Probabilidad de lluvia {cual} lo normal en el próximo trimestre, por región',
                 'dimension': 'otro', 'clave': i['nombre'].rsplit(': ', 1)[1]}
    elif id_.startswith('desplazados-'):
        tv, fr = 'nivel', 'diaria'
        nombre_prov = next(k for k in serie_ev if prov_ok(k) == i['alcance']['provincia'])
        pts = [tuple(x) for x in serie_ev.get(nombre_prov, []) if x[0] < i['fecha_dato']] + [(i['fecha_dato'], i['valor'])]
        serie = serie_fin_de_mes(pts)
    elif id_.startswith('emergencia-'):
        tv, fr = 'estado', 'diaria'
        grupo = {'id': 'emergencia-por-provincia', 'nombre': 'Emergencia hídrica o climática por provincia',
                 'dimension': 'provincia', 'clave': i['alcance']['provincia'], 'escala': ESCALA_EMERGENCIA}
    elif id_.startswith('riesgo-climatico-'):
        tv, fr = 'estado', 'diaria'
    else:
        tv, fr = 'estado' if isinstance(i['valor'], str) else 'nivel', 'diaria'
    i['tipo_valor'], i['frecuencia'] = tv, fr
    if serie and len(serie) >= 2:
        i['serie'] = serie
    i['comparar'] = comparaciones(i.get('serie', []))
    if grupo:
        i['grupo'] = grupo

salida = {'web': WEB, 'version': VERSION, 'generado': dt.datetime.now(AR).isoformat(timespec='seconds'),
          'indicadores': indicadores, 'novedades': novedades, 'agenda': agenda, 'faltantes': faltantes}


# Validación
def validar(o):
    err = []
    fecha_ok = lambda s: isinstance(s, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', s) is not None
    def alc_ok(x, donde):
        if x['nivel'] not in NIVELES: err.append(f'{donde}: nivel {x["nivel"]}')
        if x['provincia'] and x['provincia'] not in PROVINCIAS: err.append(f'{donde}: provincia {x["provincia"]}')
        if x['nivel'] in ('provincia', 'localidad') and not x['provincia']: err.append(f'{donde}: falta provincia')
    ids = set()
    for i in o['indicadores']:
        d = f"indicador {i['id']}"
        if i['id'] in ids or not re.fullmatch(r'[a-z0-9-]+', i['id']): err.append(f'{d}: id repetido o inválido')
        ids.add(i['id'])
        if not isinstance(i['valor'], (int, float, str)) or i['valor'] in ('', None): err.append(f'{d}: valor')
        if isinstance(i['valor'], float) and math.isnan(i['valor']): err.append(f'{d}: NaN')
        if not fecha_ok(i['fecha_dato']) or i['fecha_dato'] > HOY.isoformat(): err.append(f'{d}: fecha_dato')
        if i['eje'] != EJE: err.append(f'{d}: eje')
        if not i.get('fuente_original') or not i.get('url', '').startswith('https://'): err.append(f'{d}: fuente o url')
        if any(r not in RUBROS for r in i['rubros']) or any(x not in EXPOSICION for x in i['exposicion']): err.append(f'{d}: rubros o exposición')
        alc_ok(i['alcance'], d)
        # versión 1.3
        if i.get('tipo_valor') not in TIPOS_VALOR or i.get('frecuencia') not in FRECUENCIAS: err.append(f'{d}: tipo_valor o frecuencia')
        if not isinstance(i.get('comparar'), list) or any(c not in ('mensual', 'interanual') for c in i['comparar']): err.append(f'{d}: comparar')
        s = i.get('serie')
        if s is not None:
            if i['tipo_valor'] == 'estado' or len(s) < 2: err.append(f'{d}: serie en un indicador sin historia numérica')
            fechas = [x.get('fecha') for x in s]
            if not all(fecha_ok(f) for f in fechas) or fechas != sorted(set(fechas)): err.append(f'{d}: fechas de la serie')
            if not all(isinstance(x.get('valor'), (int, float)) and not isinstance(x.get('valor'), bool) for x in s): err.append(f'{d}: valores de la serie')
            if s and (s[-1]['fecha'] != i['fecha_dato'] or s[-1]['valor'] != i['valor']): err.append(f'{d}: el último de la serie no es el valor publicado')
        if 'interanual' in i.get('comparar', []) and not (s and dt.date.fromisoformat(s[0]['fecha']) <= dt.date.fromisoformat(s[-1]['fecha']) - dt.timedelta(days=365)):
            err.append(f'{d}: interanual sin un año de serie')
        g = i.get('grupo')
        if g and (g.get('dimension') not in ('provincia', 'rubro', 'pais', 'otro') or not g.get('clave')): err.append(f'{d}: grupo')
        if g and g['dimension'] == 'provincia' and g['clave'] not in PROVINCIAS: err.append(f'{d}: clave de provincia')
        if g and g['dimension'] == 'rubro' and g['clave'] not in RUBROS: err.append(f'{d}: clave de rubro')
        if g and 'escala' in g and i['valor'] not in g['escala']: err.append(f'{d}: valor fuera de la escala')
    grupos = {}
    for i in o['indicadores']:
        if i.get('grupo'):
            grupos.setdefault(i['grupo']['id'], []).append(i)
    for gid, ms in grupos.items():
        if len(ms) < 3: err.append(f'grupo {gid}: menos de 3 miembros')
        for campo in (lambda x: x['grupo']['nombre'], lambda x: x['grupo']['dimension'], lambda x: x['unidad'],
                      lambda x: x['fecha_dato'], lambda x: json.dumps(x['grupo'].get('escala'))):
            if len({campo(x) for x in ms}) > 1: err.append(f'grupo {gid}: miembros distintos en nombre, dimensión, unidad, fecha o escala')
        if len({x['grupo']['clave'] for x in ms}) < len(ms): err.append(f'grupo {gid}: clave repetida')
    nids = set()
    for n in o['novedades']:
        d = f"novedad {n['id']}"
        if n['id'] in nids: err.append(f'{d}: id repetido')
        nids.add(n['id'])
        if not fecha_ok(n['fecha_dato']) or (HOY - dt.date.fromisoformat(n['fecha_dato'])).days > 90: err.append(f'{d}: fecha')
        if n['tipo'] not in TIPOS or not n['titulo'] or not n['resumen']: err.append(f'{d}: tipo, título o resumen')
        if len(n['resumen'].split()) > 60: err.append(f'{d}: resumen de más de 60 palabras')
        if not n.get('url', '').startswith('http'): err.append(f'{d}: url')
        alc_ok(n['alcance'], d)
    for ev in o['agenda']:
        if not fecha_ok(ev['fecha']) or not (HOY < dt.date.fromisoformat(ev['fecha']) <= HOY + dt.timedelta(days=60)): err.append(f"agenda {ev['evento']}: fecha")
    for f in o['faltantes']:
        if f['ultimo_dato'] is not None and not fecha_ok(f['ultimo_dato']): err.append(f"faltante {f['id']}: ultimo_dato")
        if f['id'] in ids: err.append(f"faltante {f['id']}: también está en indicadores")
    return err


errores = validar(salida)
if errores:
    print('ERROR: datos-informe.json no se escribió:\n  ' + '\n  '.join(errores))
    sys.exit(1)
(RAIZ / 'datos-informe.json').write_text(json.dumps(salida, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f"datos-informe.json OK: {len(indicadores)} indicadores, {len(novedades)} novedades, {len(agenda)} fechas de agenda, {len(faltantes)} faltantes.")
