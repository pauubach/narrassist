# Timeline Extreme Cases 2026-02-13

## Scope
Este documento consolida casos extremos para la logica temporal del producto (backend, frontend, reglas funcionales y QA), incluyendo:
- casos de identidad temporal (misma persona en multiples edades simultaneas),
- zonas horarias y cambios de calendario,
- viajes espaciales/relativistas,
- planetas con ciclos diarios no-24h,
- robustez, rendimiento y UX.

## Caso base de referencia
Escenario canonico:
- Persona A tiene 40 anos.
- Viaja 5 anos al futuro.
- Coexisten A@40 y A@45.
- Deben tratarse como la misma entidad canonica, pero como dos instancias temporales distintas que pueden interactuar.

Comportamiento esperado:
- Misma `canonical_entity_id`.
- Distinto `temporal_instance_id`.
- Alertas de edad/estado vital evaluadas por instancia, no solo por entidad canonica.

## Recomendaciones de modelo minimo
Para cubrir los casos de abajo, el modelo temporal deberia separar:
- `canonical_entity_id`: identidad narrativa base.
- `temporal_instance_id`: clon/instancia temporal concreta.
- `timeline_frame_id`: linea temporal o rama.
- `instant_utc`: instante absoluto para orden fisico.
- `local_datetime` + `timezone_id`: hora civil del lugar.
- `proper_time_seconds`: tiempo subjetivo acumulado por instancia (envejecimiento).
- `calendar_system_id` o `planetary_day_length_hours`: para mundos no-24h.

## Catalogo de casos extremos

### A. Identidad temporal y causalidad
1. Misma persona con 2 instancias simultaneas (A@40 y A@45).
   Esperado: interaccion valida sin duplicar identidad canonica.
2. Misma persona con 3+ instancias (A@40, A@45, A@52).
   Esperado: reglas de relacion y memoria por instancia.
3. Muerte parcial de instancia.
   Esperado: muerte de A@45 no mata automaticamente a A@40.
4. Rejuvenecimiento aparente en discurso.
   Esperado: no disparar inconsistencia si hay salto temporal valido.
5. Bucle causal cerrado (evento causa su propio origen).
   Esperado: alerta de paradoja causal explicita.
6. Conocimiento divergente entre instancias.
   Esperado: no marcar anacronismo si el conocimiento pertenece a instancia distinta.
7. Transferencia de informacion entre instancias.
   Esperado: registrar cambio de causalidad y dependencia narrativa.
8. Objeto unico presente en dos tiempos a la vez.
   Esperado: advertencia de duplicacion temporal de artefacto.
9. Creacion de rama temporal alternativa.
   Esperado: soporte de `timeline_frame_id` y vista por ramas.
10. Fusion de ramas con hechos incompatibles.
   Esperado: politica de resolucion (prioridad, coexistencia o conflicto pendiente).

### B. Tiempo civil (zona horaria, calendario, vuelos)
11. Cambio de zona horaria con salto de fecha (incluye linea internacional de cambio de fecha).
   Esperado: fecha local puede cambiar de dia sin romper orden global.
12. Vuelo que llega con hora local anterior a la salida.
   Esperado: UI muestra "llega antes (hora local)" sin marcar error cronologico.
13. Dia con duracion no estandar por DST o cambios de zona.
   Esperado: no asumir que todo dia tiene 24h en calculos.
14. Evento en medianoche exacta con cambio de zona.
   Esperado: manejo correcto de limites de dia y capitulo.
15. Fechas limite (29-feb, fin de mes, anio bisiesto/no bisiesto).
   Esperado: sin crashes, sin normalizaciones silenciosas incorrectas.
16. Marcadores ambiguos ("manana", "ayer", "la semana pasada") tras salto temporal.
   Esperado: resolver respecto al marco temporal activo, no respecto al reloj del sistema.

### C. Relatividad, espacio y otros planetas
17. Estancia prolongada en espacio con dilatacion temporal.
   Esperado: diferencia entre tiempo subjetivo del viajero y tiempo terrestre.
18. Viaje de alta velocidad con envejecimiento diferencial.
   Esperado: alertas de edad basadas en `proper_time_seconds`, no solo en fecha local.
19. Gravedad extrema (dilatacion gravitacional).
   Esperado: permitir discrepancias de edad entre instancias sin falso positivo.
20. Planeta con dia no-24h (ej. 30h, 10h, o variable).
   Esperado: calendario configurable por mundo/planeta.
21. Planeta con anio y estaciones distintas a Tierra.
   Esperado: no hardcodear reglas gregorianas para toda narrativa.
22. Cambio de planeta en la misma linea argumental.
   Esperado: eventos comparables por instante absoluto y convertibles por calendario local.

### D. Robustez funcional, UX y rendimiento
23. Proyecto sin fechas absolutas (solo `day_offset`).
   Esperado: timeline util, ordenado y explicable en UI.
24. Offsets extremos (ej. -10000 / +10000 dias).
   Esperado: sin overflow, sin degradacion grave de rendimiento.
25. Reordenado editorial de capitulos (discurso != historia).
   Esperado: deteccion de analepsis/prolepsis estable y entendible para usuario.
26. Persistencia y recarga con instancias temporales.
   Esperado: no perder `temporal_instance_id`, rama, offsets ni badges.
27. Escala alta (50k-100k eventos).
   Esperado: virtualizacion/listas eficientes, sin congelar UI.
28. Integridad cross-modulo (timeline, vital status, knowledge, alerts).
   Esperado: decisiones coherentes entre modulos en saltos temporales complejos.

## Casos que deben cubrir tests (minimo)
- Unit:
  - parsing temporal por zona horaria y DST,
  - conversion entre `instant_utc` y `local_datetime`,
  - edad por `proper_time_seconds`.
- Integration:
  - timeline <-> vital_status para instancias multiples,
  - timeline <-> knowledge_anachronisms con ramas temporales,
  - persistencia/reload sin perdida de campos.
- UI/E2E:
  - mostrar simultaneamente A@40 y A@45,
  - mostrar llegada con hora local anterior sin error falso,
  - visualizacion por rama temporal y por tiempo subjetivo.
- Performance:
  - 10k, 50k y 100k eventos con filtros y agrupacion activos.

## Criterios de aceptacion recomendados
1. Ningun caso anterior produce crash ni bloqueo de UI.
2. Las alertas de edad/estado vital son correctas por instancia temporal.
3. El orden cronologico global usa instante absoluto, no solo hora local.
4. La UI explica diferencias entre tiempo local, tiempo global y tiempo subjetivo.
5. Persistencia y recarga mantienen semantica temporal completa.

## Riesgo actual si no se cubre
- Falsos positivos de inconsistencias temporales.
- Alertas de edad o muerte incorrectas.
- Confusion editorial por lineas de tiempo aparentemente "rotas".
- Perdida de confianza del usuario en la herramienta para narrativas no lineales avanzadas.
