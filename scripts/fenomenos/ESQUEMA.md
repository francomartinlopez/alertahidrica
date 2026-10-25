# Esquema de fenomenos/eventos.json

{ "actualizado": "AAAA-MM-DD", "desde": "AAAA-MM-DD" (actualizado − 90 días), "nota": "...", "comparacion": {...}, "capas": {...}, "eventos": [ ... ] }

## Cada evento

{
 "id": "region-001",          // único: prefijos pac, atl, asi, eur, afr, oce, nam, cam, sam; agregá un sufijo nuevo (ej. "eur-d01") para no repetir
 "tipo": "<código>",          // ver lista abajo
 "titulo": "corto y neutral",
 "lugar": "Luzón, Filipinas",
 "pais": "Filipinas",          // en español; varios: "Filipinas, Taiwán"
 "inicio": "AAAA-MM-DD",
 "fin": "AAAA-MM-DD" o null,   // null = sigue en curso
 "origen": "noticias" | "gdacs" | "ambos",
 "gdacs": [{"t":"TC|FL|DR|WF","id":1001338,"a":"roja|naranja|verde"}],   // [] si origen = noticias
 "geom": {"t":"punto","c":[lon,lat]} | {"t":"area","c":[lon,lat],"r":km} | {"t":"trayectoria","pts":[[lon,lat],...],"src":"eonet|aprox"} (solo ciclones, hasta 10 puntos),
 "impacto": [lon,lat] o null,  // solo ciclones: lugar principal de los daños
 "muertes": entero o null, "afectados": entero o null, "evacuados": entero o null,
 "texto": "1 a 3 frases neutrales con lo que pasó y las cifras. Sin adjetivos ni causas: nunca mencionar El Niño ni el cambio climático.",
 "intensidad": {"nivel": 1|2|3|null, "medida": "dato físico corto", "ref": "contra qué se compara", "fuente": índice en fuentes o null},
 "danos": {"usd": millones de USD o null, "rango": [min,max] o null, "tipo": "oficial|aseguradora|consultora|prensa" o null, "fuente": índice o null, "texto": "qué se dañó"},
 "efectos": {"corto": [{"cat":"…","t":"…"}], "mediano": [...], "largo": [...]},
 "criterio": "muertes" | "afectados" | "alerta_gdacs" | "emergencia" | "record" | "intensidad",
 "fuentes": [{"t":"Medio u organismo, fecha","u":"https://..."}]
}

Categorías de efectos: servicios, transporte, logistica (comercio internacional: puertos, canales, ríos navegables, pasos fronterizos, exportaciones), agro, salud, vivienda, economia. Corto = días a 2 semanas; mediano = hasta 6 meses; largo = más de 6 meses. Mediano y largo solo si una fuente lo informa o lo prevé (si es previsión, empieza con "Previsto:").

Daños: solo cifras publicadas. Ninguna estimación propia.

## Tipos (familia de color en el mapa)

- Agua: inundacion, lluvia, monzon, marejada, deslizamiento
- Tormentas: ciclon, tornado, granizo, viento, rayos
- Calor y seco: calor, calor_marino, sequia, incendio, polvo
- Frío: frio, nieve

## Criterio de entrada (al menos uno)

≥1 muerto; ≥1.000 personas afectadas, evacuadas, rescatadas o damnificadas; alerta naranja o roja de GDACS (entran todas); emergencia o desastre declarado por un gobierno; récord confirmado por un servicio meteorológico oficial; intensidad física nivel 2 o 3 aunque no haya víctimas. GDACS verde: mismo criterio. Granizo, viento y rayos solo con daños, víctimas o récord. No terremotos, volcanes ni tsunamis. Incendios: solo de vegetación.

## Intensidad (siempre contra lo normal del lugar, no en valores absolutos)

- ciclon: viento máximo sostenido (EONET, Saffir-Simpson): 1 = tormenta tropical o cat. 1-2 (<178 km/h); 2 = cat. 3-4 (178-251); 3 = cat. 5 (≥252). Si hay lluvia récord publicada, vale el mayor.
- lluvia, inundacion, monzon, deslizamiento: 1 = ≥2 veces lo normal o crecida importante; 2 = ≥3 veces lo normal, retorno ≥10 años o "la mayor en décadas"; 3 = récord histórico, retorno ≥50 años o alerta máxima por primera vez. Monzón deficitario: 1 = −10 a −20%; 2 = −20 a −40%; 3 = peor registrado o < −40%.
- calor: 1 = ola de calor oficial; 2 = récords locales; 3 = récord nacional o período más cálido registrado.
- frio, nieve: 1 = inusual para la época; 2 = muy inusual o el mayor en décadas; 3 = récord.
- sequia: 1 = moderada (D1); 2 = severa (D2, ≤50% de lo normal en meses); 3 = extrema o excepcional (D3-D4, récord).
- incendio: 1 = 1.000-9.999 ha; 2 = 10.000-49.999 ha; 3 = ≥50.000 ha o récord de la región.
- tornado: EF0-1 = 1; EF2-3 = 2; EF4-5 = 3. granizo: ≥2 cm = 1; ≥5 cm = 2; ≥10 cm = 3. viento: ráfagas ≥90 km/h = 1; ≥120 = 2; récord = 3.
- marejada: 1 = inundación costera; 2 = entre las 3 mayores registradas; 3 = récord. calor_marino: alerta 1 de Coral Reef Watch o +1 a 2 °C = 1; alerta 2 o +2 a 4 °C = 2; alerta 3+, récord o > +4 °C = 3.
- Sin dato físico publicado: nivel null (no se inventa).

## Bloques que mantienen los scripts

- "comparacion" (revisar_fuentes.py, los lunes): alertas naranja y roja de GDACS en la misma ventana de 2012 a hoy, por tipo. Las alertas de GDACS combinan fuerza del fenómeno con población expuesta.
- "capas" (capas_noaa.py): lluvia y temperatura respecto de lo normal 1991-2020, NOAA CPC, para 7, 30 y 90 días.

## Fuentes sistemáticas

- GDACS: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH y /geteventdata (cifras "sendai" de su recopilación automática de prensa).
- NASA EONET: https://eonet.gsfc.nasa.gov/api/v3/events (ciclones).
- NOAA CPC: ftp.cpc.ncep.noaa.gov (lluvia y temperatura diarias).
