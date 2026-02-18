# 5. Timeline y Eventos

La vista de **Timeline** te permite visualizar la línea temporal de tu manuscrito y los **eventos narrativos** que el sistema detecta automáticamente. Es la herramienta clave para verificar que la cronología de tu historia es coherente.

---

## La Línea Temporal

### ¿Qué muestra?

El timeline reconstruye la secuencia de eventos de tu historia basándose en marcadores temporales del texto: fechas explícitas, estaciones, expresiones como "tres días después" o "la semana pasada".

```
┌────────────────────────────────────────────────────────────┐
│ Timeline Temporal         23 eventos  5 anclas  2 analepsis│
├────────────────────────────────────────────────────────────┤
│ La historia abarca desde marzo 1985 hasta junio 1987      │
│ (2 años y 3 meses)                                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Mar 1985 ──●── Jun 1985 ──●── Dic 1985 ──●── Jun 1987   │
│          Cap.1          Cap.5          Cap.12       Cap.20 │
│                                                            │
│  ● Cronológico    ● Analepsis (flashback)                  │
│                   ● Prolepsis (flashforward)                │
└────────────────────────────────────────────────────────────┘
```

### Conceptos Clave

| Concepto | Descripción |
|----------|-------------|
| **Ancla temporal** | Fecha absoluta explícita en el texto ("15 de marzo de 1985") |
| **Marcador relativo** | Expresión temporal relativa ("tres días después", "la semana pasada") |
| **Analepsis** | Flashback: evento narrado fuera de orden, mirando al pasado |
| **Prolepsis** | Flashforward: anticipación de un evento futuro |
| **Salto temporal** | Transición explícita en el tiempo ("Pasaron dos años") |
| **Día offset** | Cuando no hay fechas absolutas, el sistema usa Día 0, Día +1, etc. |

---

## Modos de Vista

El timeline ofrece **dos modos** que puedes alternar con los botones de la barra:

### Vista Horizontal (vis-timeline)

Línea temporal interactiva donde los eventos se representan como puntos en un eje. Puedes hacer zoom y desplazarte para explorar. Ideal para ver la distribución temporal global.

### Vista Lista

Lista vertical de eventos organizados secuencialmente. Muestra más detalle por evento: descripción completa, personajes involucrados, capítulo y confianza.

**Opciones de la vista lista**:
- **Agrupar por capítulo**: Agrupa eventos bajo encabezados de capítulo
- **Ordenar por**: Fecha de la historia o posición en el texto
- **Filtrar por tipo**: Cronológico, analepsis o prolepsis

---

## Eventos Narrativos

### ¿Qué son?

Los **eventos narrativos** son los acontecimientos significativos que hacen avanzar la trama: una promesa, una traición, una muerte, un encuentro. Narrative Assistant los detecta automáticamente y los clasifica en **49 tipos** organizados en 3 niveles de prioridad.

### Tier 1: Eventos Críticos (21 tipos)

Esenciales para la continuidad narrativa. Se detectan siempre, independientemente del género.

| Grupo | Eventos |
|-------|---------|
| **Vida/Muerte** | Primera aparición, muerte, retorno de personaje |
| **Compromisos** | Promesa, promesa rota, confesión, mentira |
| **Objetos** | Adquisición de objeto/habilidad, pérdida |
| **Daño** | Herida, curación |
| **Estructura** | Inicio/fin de flashback, cambio de PDV, salto temporal, secuencia onírica, intrusión del narrador |
| **Relaciones** | Traición, alianza, revelación, decisión importante |

### Tier 2: Enriquecimiento Narrativo (15 tipos)

Eventos de prioridad media que añaden profundidad al análisis.

| Grupo | Eventos |
|-------|---------|
| **Relaciones** | Primer encuentro, reencuentro, separación, inicio/resolución de conflicto |
| **Transformaciones** | Cambio psicológico, cambio social, cambio de escenario, cambio de poder |
| **Trama** | Clímax, giro argumental, prefiguración, callback |
| **Meta** | Inicio/fin de capítulo |

### Tier 3: Eventos por Género (13 tipos)

Eventos especializados que se activan según el género del manuscrito.

| Género | Eventos |
|--------|---------|
| **Thriller** | Descubrimiento de pista, pista falsa, escalada de peligro, inicio de persecución |
| **Fantasía/Sci-Fi** | Uso de magia, profecía, worldbuilding, cruce de portal |
| **Romance** | Tensión romántica, declaración de amor, ruptura, reconciliación |
| **Universal** | Transferencia de conocimiento |

---

## Continuidad de Eventos

Una de las funciones más potentes del timeline: el sistema **rastrea pares de eventos** que deberían ocurrir juntos y alerta si falta uno.

### Pares Rastreados

```
Promesa         ──→  ¿Se cumple o se rompe?
Herida          ──→  ¿Se cura?
Adquisición     ──→  ¿Se pierde o se conserva?
Mentira         ──→  ¿Se confiesa?
Inicio flashback ──→ ¿Se cierra?
Inicio conflicto ──→ ¿Se resuelve?
Separación      ──→  ¿Hay reencuentro?
Alianza         ──→  ¿Hay traición?
```

### Ejemplo de Alerta de Continuidad

```
⚠️ Promesa sin resolución

Cap. 4: "Te prometo que volveré antes del invierno", dijo Alonso.

El personaje Alonso hizo una promesa en el capítulo 4,
pero no hay ningún evento posterior donde la cumpla o la rompa.

→ ¿Olvidaste resolver esta promesa?
→ ¿O es un hilo argumental abierto intencionalmente?
```

---

## Inconsistencias Temporales

El sistema detecta contradicciones en la cronología del manuscrito:

| Tipo | Ejemplo | Severidad |
|------|---------|-----------|
| **Edad imposible** | Personaje tiene 25 años en cap. 3 y 30 en cap. 5 (pasan 2 meses) | Crítica |
| **Orden violado** | Evento B ocurre "antes" de A, pero se narra después sin flashback | Alta |
| **Duración imposible** | Viaje de Madrid a Tokio en "unas horas" (sin avión mencionado) | Media |
| **Anacronismo** | Teléfono móvil en una novela ambientada en 1950 | Alta |
| **Paradoja temporal** | Personaje recuerda algo que aún no ha pasado | Crítica |

Las inconsistencias temporales aparecen tanto en la vista de Timeline como en el [panel de alertas](04-alerts.md) (categoría: temporal).

---

## Inspector de Capítulos

Dentro de la vista de lista, al **agrupar por capítulo** puedes inspeccionar la densidad de eventos de cada capítulo:

```
▼ Capítulo 3: "El reencuentro"                    5 eventos
  ● Primer encuentro: María conoce a Rodrigo
  ● Revelación: María descubre el secreto
  ● Promesa: Rodrigo promete protegerla
  ↕ 3 días después
  ● Traición: Rodrigo informa al enemigo
  ● Separación: María huye de la ciudad

▶ Capítulo 4: "La huida"                          2 eventos
▶ Capítulo 5: "Nuevos aliados"                    7 eventos
```

**Indicadores de gap**: Entre eventos consecutivos, el sistema muestra el **tiempo transcurrido** (si se puede calcular). Esto ayuda a detectar saltos temporales no explícitos.

---

## Estadísticas de Eventos

Haz clic en el icono de **estadísticas** para ver un resumen de la distribución de eventos:

- **Densidad por capítulo**: Qué capítulos tienen más/menos eventos
- **Distribución por tipo**: Cuántos eventos de cada tipo se detectaron
- **Clusters temporales**: Momentos de alta concentración de eventos
- **Analepsis y prolepsis**: Cuántos saltos temporales hay y dónde

**Uso práctico**: Un capítulo con 0 eventos puede indicar un capítulo de transición (normal) o un capítulo que necesita más desarrollo. Un capítulo con 15 eventos puede estar sobrecargado.

---

## Exportar Timeline y Eventos

Dos botones de exportación en la barra de herramientas:

- **Timeline temporal** (botón descarga): Exporta en JSON con eventos, marcadores y fechas
- **Eventos narrativos** (botón exportar): CSV o JSON con tipo, descripción, capítulo, personajes y confianza

```csv
Tipo,Descripción,Capítulo,Personajes,Confianza,Tier
promise,"Te prometo que volveré",4,"Alonso",85%,Tier 1
first_meeting,"María conoce a Rodrigo",3,"María;Rodrigo",92%,Tier 2
betrayal,"Rodrigo informa al enemigo",3,"Rodrigo",78%,Tier 1
```

---

## Casos de Uso Prácticos

### Novela policíaca: seguir las pistas

1. Abre el **Timeline** de tu novela de misterio
2. Filtra por eventos Tier 3 de género Thriller: **descubrimiento de pista** y **pista falsa**
3. Verifica que cada pista plantada tiene resolución
4. Comprueba que el lector tiene acceso a las pistas antes de la revelación final
5. Revisa las alertas de continuidad: ¿alguna pista quedó sin resolver?

### Saga de fantasía: coherencia entre tomos

1. Analiza cada tomo por separado
2. Revisa **profecías**, **adquisiciones** y **alianzas** entre tomos
3. Exporta eventos en CSV para seguimiento cruzado en hoja de cálculo

### Novela romántica: arcos emocionales

1. Filtra eventos Tier 3 de Romance: **tensión romántica**, **declaración**, **ruptura**, **reconciliación**
2. Verifica que el arco sigue una progresión lógica y se distribuye bien en el manuscrito

### Memorias/biografía: cronología estricta

1. Verifica que hay suficientes **anclas temporales** (fechas absolutas)
2. Revisa inconsistencias de **edad** y que los **saltos temporales** estén señalizados

---

## Consejos

- ✅ Un manuscrito sin marcadores temporales producirá un timeline vacío; añade referencias temporales explícitas si quieres usar esta función
- ✅ Agrupa por capítulo para una revisión sistemática de la cronología
- ✅ Presta atención a los **gaps temporales**: un salto grande entre eventos puede ser un hueco narrativo
- ✅ Exporta los eventos a CSV para mantener una "biblia de la serie" actualizada
- ⚠️ Los eventos de Tier 3 solo son relevantes si tu manuscrito es del género correspondiente
- ⚠️ La confianza de detección de eventos es generalmente menor que la de alertas gramaticales; revisa con criterio los eventos detectados con confianza < 70%

---

## Próximos Pasos

- **Colecciones y Sagas**: [Capítulo 6](06-collections-sagas.md)
- **Configuración**: [Capítulo 7](07-settings.md)
- **Casos de Uso Completos**: [Capítulo 8](08-use-cases.md)

---

**Tip**: El timeline es especialmente útil en la **segunda lectura** del manuscrito. Después de resolver las alertas de inconsistencia principales ([Capítulo 4](04-alerts.md)), usa el timeline para verificar que la cronología global tiene sentido.
