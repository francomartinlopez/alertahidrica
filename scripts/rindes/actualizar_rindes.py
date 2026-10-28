"""Arma rindes.json (bloque "El rinde en años Niño, neutrales y Niña" de Impacto y fondos)
a partir de AgroENSO: Monzon, J.P., Aramburu-Merlos, F. y Mercau, J.L. (2026). AgroENSO —
Efecto del ENSO sobre el rendimiento de cultivos en Argentina, Brasil y Uruguay [aplicación web].
https://agroenso.netlify.app (acceso libre, citando la fuente).

Uso (desde la raíz del repositorio):  python3 scripts/rindes/actualizar_rindes.py
Baja la página de AgroENSO (para leer la versión de los datos y la clasificación ENSO por campaña),
los archivos d/ar_depto, d/ar_provincia y d/ar_pais (.stats.json y .geo.json), y reescribe rindes.json.
Hace falta acceso a agroenso.netlify.app. No se corre todos los días: solo si los autores publican
datos nuevos (cambia la versión, que queda en rindes.json["version"]).
"""
import json,re,math,sys,os,urllib.request,tempfile
RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
URL='https://agroenso.netlify.app/'
def bajar(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'alertahidrica'}),timeout=120) as r: return r.read().decode('utf8')
html=bajar(URL)
app=html
VER=re.search(r'const DATA_VER\s*=\s*"([0-9a-f]+)"',app).group(1)
B=tempfile.mkdtemp();os.makedirs(os.path.join(B,'d'))
for k in ['ar_depto','ar_provincia','ar_pais']:
    for s in ['stats','geo']:
        open(os.path.join(B,'d',f'{k}.{s}.json'),'w',encoding='utf8').write(bajar(f'{URL}d/{k}.{s}.json?v={VER}'))
OUT=os.path.join(RAIZ,'rindes.json')
YE={int(k):v for k,v in json.loads(re.search(r'const YEAR_ENSO\s*=\s*(\{.*?\});',app).group(1)).items()}
OND={int(k):v for k,v in json.loads(re.search(r'const YEAR_OND\s*=\s*(\{.*?\});',app).group(1)).items()}
BASE=1990
CROPS=['Maíz','Soja 1ra','Soja 2da','Trigo','Girasol','Cebada']
FUERTES=[y for y in sorted(OND) if y>=BASE and OND[y]>=2.0]   # Niños muy fuertes del período (ONI oct-dic >= 2,0)
gd=json.load(open(os.path.join(B,'d','ar_depto.geo.json')));gp=json.load(open(os.path.join(B,'d','ar_provincia.geo.json')))
# proyección: equirrectangular con coseno de la latitud media
pts=[c for f in gd['features'] for poly in (f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]) for ring in poly for c in ring]
lo0=min(p[0] for p in pts);lo1=max(p[0] for p in pts);la0=min(p[1] for p in pts);la1=max(p[1] for p in pts)
kx=math.cos(math.radians((la0+la1)/2));S=1000/((lo1-lo0)*kx);pad=6
X=lambda lon:(lon-lo0)*kx*S+pad;Y=lambda lat:(la1-lat)*S+pad
W=round((lo1-lo0)*kx*S+2*pad);H=round((la1-la0)*S+2*pad)
def path(geom):
    polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
    out=[]
    for poly in polys:
        for ring in poly:
            q=[];last=None
            for lon,lat in ring:
                p=(round(X(lon),1),round(Y(lat),1))
                if p!=last:q.append(p);last=p
            if len(q)>=3: out.append('M'+'L'.join(f'{a:g} {b:g}' for a,b in q)+'Z')
    return ''.join(out)
def fila(d):
    sc=d.get('sc') or [];m=d.get('overall_mean')
    if m is None:return None
    r=[m,len(sc)]
    for i in range(3):
        e=(d.get('enso') or [None]*3)[i]
        yrs=[v for x,v in sc if YE.get(BASE+x)==i]
        if e: r+= [round(e[2]-100,1), e[1], (None if e[3] is None else round(e[3],4)), sum(1 for v in yrs if v>m)]
        else: r+= [None,0,None,0]
    f=[]
    dic=dict((BASE+x,v) for x,v in sc)
    for y in FUERTES: f.append(round((dic[y]/m-1)*100,1) if y in dic and m else None)
    r+=[f, d.get('r'), d.get('rp')]
    return r
def bloque(nivel):
    S_=json.load(open(os.path.join(B,'d',f'ar_{nivel}.stats.json')))
    return {uid:{c:fila(v[c]) for c in CROPS if c in v and fila(v[c])} for uid,v in S_.items()}
dep=bloque('depto');prov=bloque('provincia');pais=bloque('pais')['PAIS']
R={'version':VER,'fuertes':FUERTES,'w':W,'h':H,'cultivos':CROPS,
   'campos':['promedio','campanas','nino_dif','nino_n','nino_p','nino_sobre','neutral_dif','neutral_n','neutral_p','neutral_sobre','nina_dif','nina_n','nina_p','nina_sobre','fuertes','r','p_r'],
   'provs':[{'id':f['properties']['id'],'n':f['properties']['nombre'],'d':path(f['geometry'])} for f in gp['features']],
   'deptos':[{'id':f['properties']['id'],'n':f['properties']['nombre'],'p':f['properties']['parent'],'d':path(f['geometry'])} for f in gd['features']],
   'datos':{'pais':pais,'prov':prov,'depto':dep}}
s=json.dumps(R,ensure_ascii=False,separators=(',',':'))
open(OUT,'w',encoding='utf8').write(s)
print('w,h',W,H,'fuertes',FUERTES,'bytes',len(s.encode()),'deptos',len(R['deptos']),'provs',len(R['provs']))
