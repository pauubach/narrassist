# 8. Casos de Uso

Este capítulo presenta **cuatro escenarios reales** con flujos de trabajo paso a paso. Cada caso muestra cómo Narrative Assistant se adapta a distintos tipos de manuscritos.

---

## Caso 1: Novela de Ficción

**Perfil**: Escritora de novela negra, 85.000 palabras, 32 capítulos, 14 personajes.

### El Reto

María termina *"La Sombra del Puente"*. Tras 18 meses de escritura, sospecha inconsistencias entre los primeros y últimos capítulos, pero releer todo llevaría semanas.

### Flujo de Trabajo

1. Crear proyecto con preset **"Novela"**, importar `.docx`, analizar (Equilibrada)
2. Limpiar entidades: fusionar "Inspector Ramos" + "Ramos" + "El inspector"
3. Revisar alertas por severidad:

| Severidad | Cantidad | Ejemplos |
|-----------|----------|----------|
| **Crítica** | 3 | Edad imposible, personaje muerto que reaparece |
| **Alta** | 8 | Cambio de color de ojos, relación contradictoria |
| **Media** | 15 | Nombre de calle inconsistente, hora ambigua |

4. Resolver alertas críticas primero:

```
🔴 CRÍTICA | Reaparición post-mortem

Cap. 18: "Encontraron el cuerpo de Mendoza en el río."
Cap. 25: "Mendoza le entregó el sobre en la cafetería."

→ Error real. Mendoza debía ser "Mendía" en cap. 25.
→ Corrige, re-importa, re-analiza → Alerta desaparece ✅
```

5. Segundo pase con calidad **Profunda** (activa LLM) → detecta 4 alertas nuevas de mayor sutileza

**Resultado**: 3 errores críticos corregidos, 8 inconsistencias menores resueltas. Tiempo: 2 horas vs. semanas de relectura.

> **Tip**: En novela negra, presta especial atención a las alertas de timeline. Las coartadas y secuencias temporales son donde más errores se esconden.

---

## Caso 2: Libro Técnico

**Perfil**: Autor de manual de Python, 45.000 palabras, 15 capítulos, ejemplos de código.

### El Reto

Carlos escribe *"Python para Análisis de Datos"*. Necesita terminología consistente: no mezclar "función" con "método" al referirse a lo mismo, ni usar "array" y "arreglo" indistintamente.

### Flujo de Trabajo

1. Crear proyecto con preset **"Técnico"** (sensibilidad terminología: Alta, gramática: Formal)
2. Analizar → foco en alertas específicas de contenido técnico:

| Tipo | Prioridad | Ejemplo |
|------|-----------|---------|
| **Terminología inconsistente** | Alta | "DataFrame" vs "dataframe" vs "data frame" |
| **Referencia cruzada rota** | Alta | "Como vimos en el capítulo 3" (pero está en cap. 4) |
| **Acrónimo sin definir** | Media | Usa "API" sin definirlo la primera vez |
| **Registro mixto** | Baja | Mezcla "usted" y "tú" al dirigirse al lector |

3. Resolver inconsistencias terminológicas:

```
⚠️ ALTA | Terminología Inconsistente

"función" aparece en: cap. 1 (×12), cap. 3 (×8), cap. 5 (×15)
"método" aparece en: cap. 7 (×10), cap. 9 (×6)

→ Carlos decide: "método" para funciones de clase, "función" para independientes.
```

4. Verificar referencias cruzadas (especialmente útil tras reordenar capítulos)

**Resultado**: 23 inconsistencias terminológicas unificadas, 4 referencias cruzadas corregidas. Glosario exportado como Markdown.

> **Tip**: Exporta la lista de entidades como CSV. Es un excelente punto de partida para crear un índice analítico.

---

## Caso 3: Saga de Fantasía

**Perfil**: Escritor de saga épica, 3 tomos publicados + Tomo 4 en escritura. Total: 420.000 palabras.

### El Reto

Alejandro lleva 5 años con *"Las Tierras Quebradas"*. Al empezar el Tomo 4, no recuerda si cierto personaje tenía los ojos grises o marrones, ni si la capital estaba al este o al oeste del río.

### Flujo de Trabajo

1. Crear un proyecto por tomo, analizar cada uno individualmente
2. Limpiar entidades en cada tomo (crucial en fantasía con apodos y títulos):

```
Fusiones Tomo 1:
- "Kael" + "Kael Dravos" + "El Portador" → Kael Dravos
- "Aldara" + "La Ciudad Blanca" + "la capital" → Aldara (LOC)
```

3. Crear colección, vincular 34 entidades entre tomos (ver [Capítulo 6](06-collections-sagas.md))
4. Ejecutar análisis cross-book:

```
Alertas Cross-Book: 12
🔴 Lord Maren muere en T2 cap. 28, pero aparece en T4 cap. 3
🔴 Aldara "al este del Río Gris" (T1) vs "al oeste" (T3)
⚠️ Ojos de Ithrin: "grises" (T1) → "plateados" (T2) → "grises" (T3)
⚠️ Kael tiene 19 años (T1), pasan 2 años, tiene 25 (T3)
```

5. Resolver y documentar decisiones:
   - Lord Maren en T4 → flashback, añade contexto → "Resuelta - intencional"
   - Aldara este/oeste → error real, corrige T3 → "Resuelta - corregida"
   - Ojos de Ithrin → "plateados" es variación poética → "Rechazada"

6. Flujo continuo: cada avance en T4 → re-importar → análisis cross-book → resolver nuevas alertas

**Resultado**: 2 errores críticos de continuidad descubiertos, base de datos de 34 personajes rastreados. Confianza para escribir sin releer los 3 tomos anteriores.

> **Tip**: Vincula también **lugares** y **objetos mágicos**. Un artefacto que cambia de propiedades entre tomos es tan problemático como un personaje inconsistente.

---

## Caso 4: Memoria / Biografía

**Perfil**: Editora revisando autobiografía de 65.000 palabras, eventos de 1960 a 2020.

### El Reto

Susana recibe *"Bajo el Almendro"*, una autobiografía que mezcla recuerdos de distintas épocas. Sospecha que hay fechas y edades inconsistentes a lo largo de 60 años de relato.

### Flujo de Trabajo

1. Crear proyecto con preset **"Memoria"** (timeline: Muy alta, detección de fechas: Agresiva)
2. Analizar → la **Timeline** es la herramienta principal:

```
Timeline: Bajo el Almendro
─────────────────────────────────────────────────
1960  │ Nace en Sevilla
1966  │ Empieza el colegio (6 años) ✅
1972  │ "A los 14 años, en el instituto" ⚠️ (debería tener 12)
1978  │ Empieza la carrera en Madrid
1980  │ "Tras 4 años de carrera" ⚠️ (solo pasaron 2)
1985  │ Nace su hija Ana
1990  │ "Ana empezó el colegio con 6 años" ⚠️ (tendría 5)
2015  │ Se jubila "a los 58" ⚠️ (tendría 55)
```

3. Clasificar alertas y preparar informe para el autor:
   - Exportar alertas como **CSV** → Abrir en Excel
   - Añadir columna "Pregunta para el autor"
   - Enviar con dudas concretas

4. Corregir tras respuesta del autor y re-analizar:

```
Antes:  18 alertas de timeline
Ronda 1: 12 corregidas, 3 rechazadas (intencionales), 3 pendientes
Ronda 2: 3 pendientes resueltas tras consultar al autor
Final:   0 alertas activas ✅
```

**Resultado**: 12 errores cronológicos corregidos. Proceso editorial: 2 días vs. la semana habitual.

> **Tip**: Exporta la timeline como Markdown. Es un recurso valioso que el autor puede usar como referencia personal.

---

## Resumen Comparativo

| Aspecto | Novela | Técnico | Saga Fantasía | Memoria |
|---------|--------|---------|---------------|---------|
| **Preset** | Novela | Técnico | Novela | Memoria |
| **Herramienta clave** | Alertas | Terminología | Colecciones | Timeline |
| **Prioridad** | Personajes | Consistencia | Cross-book | Cronología |
| **Calidad análisis** | Equilibrada → Profunda | Equilibrada | Profunda | Equilibrada |
| **Tiempo típico** | 2-4 horas | 1-2 horas | 4-8 horas | 2-3 horas |

---

## Próximos Pasos

- **Primera vez**: [Capítulo 2 - Primer Análisis](02-first-analysis.md)
- **Gestionar entidades**: [Capítulo 3 - Entidades](03-entities.md)
- **Trabajar con sagas**: [Capítulo 6 - Colecciones](06-collections-sagas.md)
- **Ajustar configuración**: [Capítulo 7 - Configuración](07-settings.md)

---

**Tip**: Estos casos de uso son puntos de partida. Cada manuscrito es único, y lo mejor de Narrative Assistant es que se adapta a tu flujo de trabajo, no al revés.
