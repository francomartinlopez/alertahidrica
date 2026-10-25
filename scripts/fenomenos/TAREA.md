# Mantenimiento diario del mapa de fenómenos anómalos

El mapa vive en `fenomenos/` (página `index.html`, datos `eventos.json`, mapa base `mundo.json`, capas de fondo en `capas/`) y se ve dentro de la sección "El Niño en el mundo" del tablero. La estructura de cada evento y las reglas están en `scripts/fenomenos/ESQUEMA.md`: leela antes de editar.

Principios: el mapa muestra fenómenos meteorológicos y climáticos fuera de lo común **sin asumir relación con El Niño** (nunca lo menciones en los textos). Separa **el fenómeno** (intensidad física comparada con lo normal del lugar) del **impacto** (muertes, afectados, daños), porque el impacto depende también de la preparación de cada país. Solo cifras publicadas, con fuente abierta y fecha verificada; nada estimado.

## Pasos (todos los días)

1. **Revisión automática:** `python3 scripts/fenomenos/revisar_fuentes.py`
   Corre la ventana de 90 días (saca eventos terminados), actualiza las trayectorias de ciclones desde NASA EONET, los lunes recalcula la comparación con años anteriores, y deja un INFORME con lo que hay que revisar.
2. **Lo que marca el informe:**
   - "GDACS Orange/Red SIN CARGAR": entran siempre. Cargá el evento (criterio `alerta_gdacs`, `origen` "gdacs", o "ambos" si sumás prensa), con el enlace al reporte de GDACS en fuentes y `gdacs: [{"t","id","a"}]`.
   - "GDACS verde con ≥1 muerto o ≥1.000 afectados SIN CARGAR": cargalo con el texto "GDACS registra…" y la aclaración en `danos.texto`; si encontrás prensa, mejor.
   - "Ciclón de EONET no cargado": entra solo si cumple el criterio (víctimas, afectados, emergencia o intensidad nivel 2-3, es decir categoría 3 o más). La trayectoria se toma de EONET (`src: "eonet"`) y hay que sumar la URL del evento de EONET a fuentes.
   - "En curso": actualizá cifras y poné `fin` cuando terminó.
3. **Prensa (hasta 20 búsquedas):** todos los días, una búsqueda global de fenómenos extremos de las últimas 48 horas (inundaciones, tormentas, olas de calor, incendios, nevadas, récords). Además, una región por día: lunes Sudamérica; martes México, Centroamérica y Caribe; miércoles EE.UU. y Canadá; jueves Europa; viernes África y Medio Oriente; sábado Asia (sur, central y oriental); domingo Oceanía y Pacífico. Verificá el año de cada nota (muchos sitios muestran la fecha de hoy en notas viejas). Criterio de entrada: ≥1 muerto; ≥1.000 afectados, evacuados o rescatados; emergencia declarada; récord oficial; o intensidad física nivel 2-3 aunque no haya víctimas. No terremotos, volcanes ni tsunamis.
4. **Intensidad** de cada evento nuevo o con datos nuevos: nivel 1-3 según la tabla de `ESQUEMA.md`, siempre contra lo normal del lugar, con `medida` (dato físico concreto) y `ref` (contra qué se compara). Sin dato físico publicado: `nivel: null`.
5. **Capas de fondo:** `pip install numpy pillow` (si falta) y `python3 scripts/fenomenos/capas_noaa.py`. Baja unos 550 MB del FTP del CPC y tarda alrededor de un minuto. Si falla, dejá las capas anteriores y avisalo al final.
6. **Validación:** `python3 scripts/fenomenos/validar.py` tiene que terminar sin problemas.
7. **Publicación:** sumá `fenomenos/eventos.json` y `fenomenos/capas/` al commit del día, y al artifact los mismos archivos con su ruta (por ejemplo `"fenomenos/eventos.json"` y `"fenomenos/capas/anom_lluvia_7.png"`).

En el mensaje final, una línea con los eventos nuevos más importantes del mundo y, si hubo, los que entraron por intensidad extrema.
