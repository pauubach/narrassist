# H1: Coherencia del Mundo Ficcional

[← Volver a Heurísticas](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Esta familia verifica que el mundo ficcional sea internamente consistente: que los objetos, lugares y personajes mantengan sus propiedades, y que las reglas del mundo se apliquen uniformemente.

**Viabilidad técnica**: MEDIA-ALTA

---

## H1.1 — Consistencia de Entidades

### Descripción
Los personajes, objetos y lugares mantienen sus propiedades establecidas a lo largo del texto.

### Señal
**Débil** - Una mención contradictoria puede ser error o intención.

### Contexto de aplicación
Siempre activa, pero modulada por fiabilidad del narrador.

### Cuándo NO aplicar
- Narrador explícitamente no fiable
- Cambio de focalización a personaje con información diferente
- Transformación diegética justificada (magia, paso del tiempo)

### Cómo puede fallar
- **Falso positivo**: Sinónimos o descripciones parciales tomadas como contradicción
- **Falso positivo**: Información que el narrador oculta deliberadamente

### Implementación técnica
```python
# Detectar contradicciones en atributos
def check_entity_consistency(entity: Entity) -> List[Alert]:
    alerts = []
    for attr_key, values in entity.attributes_by_key().items():
        if len(set(v.value for v in values)) > 1:
            alerts.append(Alert(
                type='ATTRIBUTE_CONTRADICTION',
                severity='HIGH',
                entity=entity,
                attribute=attr_key,
                conflicting_values=values
            ))
    return alerts
```

### Ejemplo de alerta
```
⚠️ INCONSISTENCIA DE ATRIBUTO

Personaje: Juan García
Atributo: "Ojos"

Cap.2, pág.56: "sus ojos VERDES brillaban..."
Cap.3, pág.78: "se perdió en el AZUL de sus ojos..."

[Mantener "verdes"] [Mantener "azules"] [Ignorar]
```

---

## H1.2 — Consistencia de Reglas del Mundo

### Descripción
Las reglas físicas, mágicas o sociales del mundo se aplican uniformemente.

### Señal
**Media** - Las violaciones suelen ser más visibles.

### Contexto de aplicación
Requiere modelo explícito del mundo (realista por defecto).

### Cuándo NO aplicar
- Mundos con reglas declaradamente inconsistentes (absurdo)
- Violaciones que son el punto de la trama (descubrimiento de excepción)

### Cómo puede fallar
- **Falso positivo**: Reglas implícitas que el sistema no ha inferido
- **Falso negativo**: Violaciones sutiles que requieren conocimiento extratextual

### Implementación técnica
```python
# Las reglas del mundo se declaran manualmente
# El sistema verifica que no se violen
world_rules = [
    Rule(
        name="La magia solo funciona de noche",
        type="magic",
        source=SourceRef(chapter=2, page=34)
    )
]

def check_rule_violations(rules: List[Rule], events: List[Event]) -> List[Alert]:
    # Buscar eventos que contradigan reglas establecidas
    ...
```

### Ejemplo de alerta
```
⚠️ REGLA DEL MUNDO VIOLADA

Regla establecida: "La magia solo funciona de noche"
Cap.2, pág.34: "Los hechizos pierden poder bajo el sol..."

Posible violación:
Cap.18, pág.378: "A plena luz del día, lanzó el conjuro..."

[Es excepción justificada] [Es error] [Ignorar]
```

---

## H1.3 — Consistencia Espacial

### Descripción
El espacio narrativo es navegable coherentemente.

### Señal
**Media-alta** - Los errores espaciales son relativamente objetivos.

### Contexto de aplicación
Escenas con movimiento o descripción espacial.

### Cuándo NO aplicar
- Espacios explícitamente oníricos o simbólicos
- Narradores que distorsionan el espacio (percepción alterada)

### Cómo puede fallar
- **Falso positivo**: Elipsis espaciales implícitas
- **Falso negativo**: El sistema no ha construido modelo espacial adecuado

### Tipos de inconsistencias espaciales

| Tipo | Ejemplo | Severidad |
|------|---------|-----------|
| Descripción contradictoria | 2 pisos vs 3 pisos | 🟠 Alta |
| Distancia imposible | "a 10 min andando" vs "a 2 horas" | 🟠 Alta |
| Clima inconsistente | Nieve en julio (hemisferio norte) | 🟡 Media |
| Lugar no establecido | Personaje en lugar no descrito | 🔵 Info |
| Posible duplicado | "la mansión" ≈ "Casa Mendoza" | 🟡 Media |

### Ejemplo de alerta
```
⚠️ INCONSISTENCIA ESPACIAL

Lugar: Casa de los Mendoza
Atributo: "Número de plantas"

Cap.4, pág.89: "Subió al SEGUNDO piso, el último de la casa..."
Cap.12, pág.201: "Desde el TERCER piso podía ver todo el valle..."

[Mantener "2 plantas"] [Mantener "3 plantas"] [Ignorar]
```

---

## H1.4 — Consistencia Temporal

### Descripción
La cronología interna es reconstruible y coherente.

### Señal
**Media** - Los errores temporales son comunes y detectables.

### Contexto de aplicación
Siempre, especialmente con analepsis/prolepsis.

### Cuándo NO aplicar
- Narraciones deliberadamente atemporales
- Distorsión temporal como tema (percepción del tiempo)

### Cómo puede fallar
- **Falso positivo**: Ambigüedad temporal intencional
- **Complejidad**: Textos con múltiples líneas temporales

### Tipos de inconsistencias temporales

| Tipo | Ejemplo | Severidad |
|------|---------|-----------|
| Personaje actúa post-mortem | Juan oficia boda tras morir | 🔴 Crítica |
| Evento antes de causa | "Recordó el viaje" antes del viaje | 🟠 Alta |
| Duración imposible | Embarazo de 14 meses | 🟠 Alta |
| Secuencia ilógica | Llega antes de partir | 🟠 Alta |
| Anacronismo histórico | Teléfono móvil en 1920 | 🟡 Media |
| Salto temporal no marcado | Cambio de época sin indicar | 🔵 Info |

### Ejemplo de alerta
```
🔴 ALERTA CRÍTICA: ANACRONISMO

Juan no puede oficiar la boda en Año 3 porque murió en Año 2:

EVENTO 1: "Muerte de Juan"
Cap.8, pág.156: "Juan exhaló su último suspiro aquella noche..."
Fecha narrativa: Año 2, Otoño

EVENTO 2: "Boda oficiada por Juan"
Cap.14, pág.289: "El padre Juan los declaró marido y mujer..."
Fecha narrativa: Año 3, Primavera

Posibles soluciones:
• ¿Es otro Juan? [Crear personaje separado]
• ¿Error en fecha? [Editar evento]
• ¿Flashback no marcado? [Marcar como analepsis]
```

---

## STEPs Relacionados

| STEP | Capacidad | Heurísticas |
|------|-----------|-------------|
| [1.3](../../steps/phase-1/step-1.3-ner-pipeline.md) | Pipeline NER | H1.1 (entidades) |
| [2.3](../../steps/phase-2/step-2.3-attribute-extraction.md) | Extractor atributos | H1.1 |
| [2.4](../../steps/phase-2/step-2.4-attribute-consistency.md) | Inconsistencias | H1.1 |
| [4.1](../../steps/phase-4/step-4.1-temporal-markers.md) | Marcadores temporales | H1.4 |
| [4.2](../../steps/phase-4/step-4.2-timeline-builder.md) | Constructor timeline | H1.4 |
| [4.3](../../steps/phase-4/step-4.3-temporal-inconsistencies.md) | Inconsistencias temporales | H1.4 |

---

## Siguiente

Ver [H2: Coherencia de Personajes](./heuristics-h2-characters.md).
