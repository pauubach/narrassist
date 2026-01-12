# H6: Gestión de Información

[← Volver a Heurísticas](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Esta familia verifica la gestión de información narrativa: suficiencia, redundancia y revelaciones.

**Viabilidad técnica**: MEDIA

---

## H6.1 — Suficiencia Informativa

### Descripción
El lector recibe información suficiente para seguir la historia.

### Señal
**Débil** - Muy subjetiva.

### Contexto de aplicación
Siempre.

### Cuándo NO aplicar
- Confusión deliberada (misterio, experimental)
- Información diferida estratégicamente

### Cómo puede fallar
- **Falso positivo**: El sistema tiene menos tolerancia a la ambigüedad que el lector ideal
- **Problema**: Definir "suficiente" es circular

### Lo que NO es error
- Ambigüedad deliberada
- Información diferida estratégicamente
- Huecos que el lector debe llenar (participación activa)

### Implementación limitada
Esta heurística es difícil de automatizar. El sistema puede:
1. Detectar **personajes no introducidos** que aparecen actuando
2. Detectar **lugares sin descripción** donde ocurren escenas clave
3. Dejar el resto al criterio del corrector

---

## H6.2 — Evitación de Redundancia

### Descripción
La información no se repite innecesariamente.

### Señal
**Media** - Las repeticiones son detectables.

### Contexto de aplicación
Información factual.

### Cuándo NO aplicar
- Repetición como recurso (énfasis, tema)
- Recordatorio necesario por distancia textual

### Cómo puede fallar
- **Falso positivo**: Repetición funcional tomada como error
- **Dificultad**: Distinguir redundancia de resonancia

### Tipos de redundancia

| Tipo | Descripción | Detección |
|------|-------------|-----------|
| Exposición repetida | Mismo dato explicado varias veces | Embeddings + cercanía |
| "As you know, Bob" | Información en diálogo que ambos conocen | Patrones + contexto |
| Recordatorio excesivo | Mencionar algo muy reciente | Distancia textual |

### Ejemplo de alerta
```
⚠️ INFORMACIÓN REDUNDANTE

El hecho de que María es adoptada se menciona 3 veces en 20 páginas:

1. Cap.3, pág.45: "María, que había sido adoptada de pequeña..."
2. Cap.3, pág.52: "Como niña adoptada, María siempre..."
3. Cap.4, pág.64: "Su condición de adoptada la marcó..."

¿Es intencional (tema central) o redundancia?
[Es recurso temático] [Es redundante] [Ignorar]
```

---

## Modelo de Hechos

### Estructura de datos

```python
@dataclass
class NarrativeFact:
    """Un hecho del mundo ficcional."""
    id: int
    type: str  # 'world_rule', 'character_fact', 'event', 'object'
    description: str
    category: str  # 'mutable', 'immutable'
    sources: List[SourceRef]
    validated: bool = False

@dataclass
class FactContradiction:
    """Contradicción entre dos fuentes del mismo hecho."""
    fact_id: int
    source_1: SourceRef
    value_1: str
    source_2: SourceRef
    value_2: str
    resolution: Optional[str] = None  # 'keep_1', 'keep_2', 'both_valid', 'ignore'
```

### Categorías de hechos

| Categoría | Descripción | Ejemplos |
|-----------|-------------|----------|
| **Reglas del mundo** | Leyes físicas/mágicas/sociales | "La magia solo funciona de noche" |
| **Hechos de personajes** | Afirmaciones sobre personajes | "María no sabe conducir" |
| **Eventos establecidos** | Sucesos del pasado narrativo | "La guerra terminó en 1945" |
| **Objetos significativos** | Artefactos con propiedades | "La espada está rota" |

### Mutabilidad

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| **Inmutable** | No puede cambiar sin explicación | Color de ojos natural |
| **Mutable** | Puede cambiar justificadamente | Estado civil, ubicación |
| **Condicional** | Cambia bajo ciertas condiciones | Poder mágico que se pierde |

---

## Alertas de Coherencia Factual

### Tipos de alertas

| Tipo | Ejemplo | Severidad |
|------|---------|-----------|
| Hecho contradictorio | "No sabe conducir" pero conduce | 🟠 Alta |
| Regla del mundo violada | Magia de día cuando solo funciona de noche | 🟡 Media |
| Objeto destruido reaparece | Espada rota usada después | 🟠 Alta |
| Conocimiento imposible | Personaje sabe algo que no podría | 🟠 Alta |
| Capacidad no establecida | Personaje hace algo nunca mencionado | 🔵 Info |

### Ejemplo de alerta
```
⚠️ CONTRADICCIÓN FACTUAL

Hecho: "María nunca aprendió a conducir"
Cap.3, pág.67: "María siempre dependía de otros para moverse..."

Contradicción encontrada:
Cap.15, pág.312: "María arrancó el coche y pisó el acelerador..."

[Es error: mantener "no sabe conducir"]
[Aprendió entre medias: añadir evento]
[Ignorar alerta]
```

---

## Implementación

### Flujo de trabajo

1. **Extracción**: Detectar afirmaciones factuales en el texto
2. **Normalización**: Agrupar hechos similares
3. **Verificación**: Buscar contradicciones
4. **Revisión**: Corrector valida alertas

### Limitaciones

- La extracción automática de hechos es **imprecisa**
- Muchos hechos están **implícitos** en el texto
- Se requiere **validación manual** extensiva

### Enfoque recomendado

```python
# Enfoque híbrido: extracción + declaración manual

class FactManager:
    def extract_potential_facts(self, text: str) -> List[NarrativeFact]:
        """Extrae hechos candidatos automáticamente."""
        # NLP básico: patrones como "X es Y", "X nunca V", etc.
        ...

    def add_manual_fact(self, fact: NarrativeFact) -> None:
        """Permite al corrector añadir hechos manualmente."""
        ...

    def check_contradictions(self) -> List[FactContradiction]:
        """Verifica contradicciones entre hechos."""
        ...
```

---

## STEPs Relacionados

| STEP | Capacidad | Heurísticas |
|------|-----------|-------------|
| [2.3](../../steps/phase-2/step-2.3-attribute-extraction.md) | Extractor atributos | H6.1 (hechos de personaje) |
| [2.4](../../steps/phase-2/step-2.4-attribute-consistency.md) | Inconsistencias | H6.1, H6.2 |
| [4.2](../../steps/phase-4/step-4.2-timeline-builder.md) | Constructor timeline | H6.1 (eventos) |

---

## Volver

[← Índice de Heurísticas](./README.md)
