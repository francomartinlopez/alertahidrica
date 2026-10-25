"""Capas de fondo del mapa de fenómenos anómalos: lluvia y temperatura respecto de lo normal (NOAA CPC).

Uso:  python3 scripts/fenomenos/capas_noaa.py            (último día disponible)
      python3 scripts/fenomenos/capas_noaa.py 2026-10-23 (día final elegido)
Requiere numpy y pillow (pip install numpy pillow). Baja unos 550 MB del FTP del CPC (ftp.cpc.ncep.noaa.gov).
Escribe fenomenos/capas/anom_{lluvia,temp}_{7,30,90}.png y actualiza "capas" en fenomenos/eventos.json.
Normal: climatología diaria 1991-2020 del CPC resumida en medias mensuales (clima_cpc_1991_2020.npz), interpolada día por día.
"""
import sys, os, json, gzip, subprocess, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
FEN = os.path.join(RAIZ, 'fenomenos')
NX, NY = 720, 360
CELL = NX * NY
VENT = [7, 30, 90]
FTP = 'https://ftp.cpc.ncep.noaa.gov'

def curl(url, rng=None):
    cmd = ['curl', '-s', '--fail', '--max-time', '300', '--retry', '3', url]
    if rng: cmd[1:1] = ['-r', rng]
    return subprocess.run(cmd, capture_output=True).stdout

def lluvia_dia(d):
    base = f'{FTP}/precip/CPC_UNI_PRCP/GAUGE_GLB/RT/{d.year}/PRCP_CU_GAUGE_V1.0GLB_0.50deg.lnx.{d:%Y%m%d}'
    for suf in ('.RT', '.RT.gz', 'RT.gz'):
        b = curl(base + suf)
        if b[:2] == b'\x1f\x8b':
            try: b = gzip.decompress(b)
            except Exception: b = b''
        if len(b) == 2 * CELL * 4:
            a = np.frombuffer(b[:CELL * 4], '<f4').reshape(NY, NX)
            return np.where(a < -900, np.nan, a / 10.0).astype('f4')
    return None

REC = 4 * CELL * 4  # tmax, nmax, tmin, nmin por día

def temp_anio(y, d0, n):
    """Días d0..d0+n-1 (día del año, base 0) del archivo anual de temperatura del CPC."""
    url = f'{FTP}/precip/PEOPLE/wd52ws/global_temp/CPC_GLOBAL_T_V0.x_0.5deg.lnx.{y}'
    raw = curl(url, f'{d0 * REC}-{(d0 + n) * REC - 1}')
    if len(raw) != n * REC:  # año ya comprimido: leer en flujo
        pr = subprocess.Popen(f"curl -s --max-time 1500 '{url}.gz' | gzip -dc 2>/dev/null", shell=True, stdout=subprocess.PIPE)
        falta = d0 * REC
        while falta > 0:
            ch = pr.stdout.read(min(falta, 1 << 24))
            if not ch: break
            falta -= len(ch)
        raw = pr.stdout.read(n * REC); pr.kill()
    if len(raw) != n * REC: raise RuntimeError(f'temperatura {y}: faltan datos')
    out = []
    for k in range(n):
        r = raw[k * REC:(k + 1) * REC]
        tx = np.frombuffer(r[:CELL * 4], '<f4').reshape(NY, NX); tn = np.frombuffer(r[2 * CELL * 4:3 * CELL * 4], '<f4').reshape(NY, NX)
        out.append(np.where((tx < -900) | (tn < -900), np.nan, (tx + tn) / 2).astype('f4'))
    return out

def ultimo_dia():
    hoy = dt.date.today()
    for k in range(1, 8):
        d = hoy - dt.timedelta(days=k)
        if lluvia_dia(d) is not None: return d
    raise RuntimeError('no hay datos recientes del CPC')

# normal diaria interpolada desde las medias mensuales
CLIM = np.load(os.path.join(AQUI, 'clima_cpc_1991_2020.npz'))
DM = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MID = np.cumsum([0] + DM[:-1]) + np.array(DM) / 2.0  # día del año (base 0) del centro de cada mes
def normal(var, d):
    t = min((d - dt.date(d.year, 1, 1)).days, 364) + 0.5
    m = np.searchsorted(MID, t) % 12; p = (m - 1) % 12
    t0 = MID[p] - (365 if MID[p] > t else 0); t1 = MID[m] + (365 if MID[m] < t else 0)
    w = (t - t0) / (t1 - t0)
    C = CLIM[var]
    return ((1 - w) * C[p].astype('f4') + w * C[m].astype('f4'))

# proyección Equal Earth igual que mundo.json
W = json.load(open(os.path.join(FEN, 'mundo.json')))
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = np.sqrt(3) / 2
ESC = 1.6
PW, PH = int(W['w'] * ESC), int(round(W['h'] * ESC))
def malla():
    yy, xx = np.mgrid[0:PH, 0:PW] + 0.5
    x = (xx / ESC - W['ox']) / W['k']; y = (W['oy'] - yy / ESC) / W['k']
    t = y.copy()
    for _ in range(12):
        t2 = t * t; t6 = t2 ** 3
        t = t - (t * (A1 + A2 * t2 + A3 * t6 + A4 * t6 * t2) - y) / (A1 + 3 * A2 * t2 + 7 * A3 * t6 + 9 * A4 * t6 * t2)
    t2 = t * t; t6 = t2 ** 3
    lon = np.degrees(x * 3 * (A1 + 3 * A2 * t2 + 7 * A3 * t6 + 9 * A4 * t6 * t2) / (2 * np.sqrt(3) * np.cos(t)))
    lat = np.degrees(np.arcsin(np.clip(np.sin(t) / M, -1, 1)))
    ok = np.abs(lon) <= 180
    ix = np.floor((lon % 360) / 0.5).astype(int) % NX
    iy = np.clip(np.floor((lat + 90) / 0.5).astype(int), 0, NY - 1)
    return ok, ix, iy

COL = {'lluvia': ['#8C510A', '#BF812D', '#DFC27D', None, '#80CDC1', '#35978F', '#01665E'],
       'temp': ['#2166AC', '#67A9CF', '#D1E5F0', None, '#FDDBC7', '#EF8A62', '#B2182B']}
CORTES = {'lluvia': [0.25, 0.5, 0.8, 1.25, 2.0, 3.0], 'temp': [-3, -1.5, -0.5, 0.5, 1.5, 3]}
MINLL = {7: 7.0, 30: 20.0, 90: 45.0}  # mm normales mínimos para mostrar el cociente

def png(val, var, ruta, ok, ix, iy):
    cls = np.digitize(val, CORTES[var])
    rgba = np.zeros((NY, NX, 4), np.uint8)
    for c, h in enumerate(COL[var]):
        if h is None: continue
        m = (cls == c) & ~np.isnan(val)
        rgba[m, :3] = [int(h[i:i + 2], 16) for i in (1, 3, 5)]; rgba[m, 3] = 255
    img = rgba[iy, ix]; img[~ok] = 0
    Image.fromarray(img, 'RGBA').quantize(colors=8, method=Image.Quantize.FASTOCTREE).save(ruta, optimize=True)

def main():
    fin = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else ultimo_dia()
    dias = [fin - dt.timedelta(days=k) for k in range(max(VENT))][::-1]
    print('ventana', dias[0], '->', fin, flush=True)
    with ThreadPoolExecutor(6) as ex: ll = list(ex.map(lluvia_dia, dias))
    if any(x is None for x in ll): raise RuntimeError('faltan días de lluvia')
    tt = []
    for y in sorted({d.year for d in dias}):
        ds = [d for d in dias if d.year == y]
        tt += temp_anio(y, (ds[0] - dt.date(y, 1, 1)).days, len(ds))
    LL, TT = np.stack(ll), np.stack(tt)
    NL = np.stack([normal('lluvia', d) for d in dias]); NT = np.stack([normal('temp', d) for d in dias])
    ok, ix, iy = malla()
    os.makedirs(os.path.join(FEN, 'capas'), exist_ok=True)
    arch = {'lluvia': {}, 'temp': {}}
    for w in VENT:
        s = slice(-w, None)
        act = np.nansum(LL[s], 0); act[np.isnan(LL[s]).sum(0) > w * 0.2] = np.nan
        nor = NL[s].sum(0)
        rat = np.where(nor < MINLL[w], np.nan, act / np.where(nor > 0, nor, np.nan))
        png(rat, 'lluvia', os.path.join(FEN, 'capas', f'anom_lluvia_{w}.png'), ok, ix, iy)
        tm = np.nanmean(TT[s], 0); tm[np.isnan(TT[s]).sum(0) > w * 0.2] = np.nan
        png(tm - NT[s].mean(0), 'temp', os.path.join(FEN, 'capas', f'anom_temp_{w}.png'), ok, ix, iy)
        arch['lluvia'][str(w)] = f'capas/anom_lluvia_{w}.png'; arch['temp'][str(w)] = f'capas/anom_temp_{w}.png'
        print('listo', w, 'días', flush=True)
    ev_path = os.path.join(FEN, 'eventos.json')
    D = json.load(open(ev_path))
    D['capas'] = {'archivos': arch, 'hasta': fin.isoformat(),
                  'nota': 'Datos: NOAA CPC (análisis diario con estaciones, grilla de 0,5°, solo sobre tierra). Normal: 1991-2020. En zonas con pocas estaciones, como gran parte de África, el dato es menos confiable.'}
    json.dump(D, open(ev_path, 'w'), ensure_ascii=False, indent=1)
    print('capas actualizadas al', fin)

if __name__ == '__main__':
    main()
