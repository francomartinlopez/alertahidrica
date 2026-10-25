# Alerta hídrica · Súper Niño 2026-27 en Argentina

Web pública de seguimiento diario del Súper Niño 2026-27 en Argentina: ríos, evacuados, alertas, emergencias y planes por provincia, zonas de riesgo, qué hacer, escenarios, evaluación de la gestión y El Niño en el mundo.

- `index.html`: la página.
- `datos.json`: todo el contenido. Se actualiza todos los días.
- `mapa.json` y `zonas.json`: geometría de provincias y zonas (Natural Earth y departamentos del IGN, SIG 250).
- `fenomenos/`: mapa mundial de fenómenos meteorológicos y climáticos anómalos (página propia, embebida en la sección Mundo). `eventos.json` se actualiza todos los días; `capas/` tiene las anomalías de lluvia y temperatura de NOAA CPC; `mundo.json` es el mapa base (Natural Earth, proyección Equal Earth).
- `scripts/fenomenos/`: mantenimiento del mapa (`TAREA.md`, `ESQUEMA.md`, `revisar_fuentes.py`, `capas_noaa.py`, `validar.py` y la climatología 1991-2020 resumida).

Elaborado por Franco Martín López. Los escenarios, niveles de riesgo y evaluaciones son estimación propia; cada dato observado lleva su fuente.
