# Enums de Referencia

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## Propósito

Este documento define los valores canónicos para todos los enums utilizados en el sistema. Cualquier implementación debe usar estos valores exactos.

---

## Estados de Alerta (AlertState)

```python
class AlertState(Enum):
    # Estados iniciales
    NEW = "new"              # Recién detectada, no vista por usuario
    REVIEWED = "reviewed"    # Usuario la vio pero no actuó

    # Estados de trabajo
    PENDING = "pending"      # Marcada para revisar después

    # Estados de resolución
    DISMISSED = "dismissed"  # Ignorada permanentemente (falso positivo o no relevante)
    RESOLVED = "resolved"    # Corregida en el manuscrito
    VERIFIED = "verified"    # Corrección verificada en reimportación

    # Estados automáticos
    AUTO_RESOLVED = "auto_resolved"  # El texto cambió y la alerta ya no aplica
    REOPENED = "reopened"            # Alerta resuelta que reaparece
    OBSOLETE = "obsolete"            # El texto fue eliminado
```

### Transiciones Válidas

```
new → reviewed → pending → resolved → verified
         ↓          ↓         ↓
      dismissed  dismissed  reopened
                              ↓
                           resolved

[cualquiera] → obsolete (cuando el texto desaparece)
[cualquiera] → auto_resolved (cuando el texto cambia)
```

---

## Severidad de Alerta (AlertSeverity)

```python
class AlertSeverity(Enum):
    CRITICAL = "critical"  # Error objetivo que debe corregirse
    WARNING = "warning"    # Problema probable, revisar
    INFO = "info"          # Información útil, no necesariamente error
    HINT = "hint"          # Sugerencia menor, ignorable
```

### Mapeo Severidad ↔ Confianza

| Confianza | Severidad | Descripción |
|-----------|-----------|-------------|
| ≥0.9 | critical | Casi seguro que es error |
| 0.7-0.9 | warning | Probablemente error |
| 0.5-0.7 | info | Posible error |
| <0.5 | hint | Incierto, verificar |

---

## Tipos de Entidad (EntityType)

```python
class EntityType(Enum):
    CHARACTER = "character"      # Personaje (humano, animal, criatura)
    LOCATION = "location"        # Lugar (ciudad, edificio, paisaje)
    OBJECT = "object"            # Objeto significativo
    ORGANIZATION = "organization" # Grupo, institución
    EVENT = "event"              # Evento nombrado
```

---

## Importancia de Entidad (EntityImportance)

```python
class EntityImportance(Enum):
    PROTAGONIST = "protagonist"  # Personaje principal
    MAIN = "main"                # Personajes principales secundarios
    SECONDARY = "secondary"      # Personajes con rol menor
    MINOR = "minor"              # Apariciones puntuales
    MENTIONED = "mentioned"      # Solo nombrados, sin aparición
```

---

## Tipos de Atributo (AttributeType)

```python
class AttributeType(Enum):
    PHYSICAL = "physical"        # Color ojos, pelo, altura, edad
    PSYCHOLOGICAL = "psychological"  # Carácter, miedos, deseos
    SOCIAL = "social"            # Profesión, relaciones, estatus
    BACKGROUND = "background"    # Historia, origen, eventos pasados
```

---

## Tipos de Alerta (AlertType)

```python
class AlertType(Enum):
    # H1: Mundo
    ENTITY_DUPLICATE = "entity_duplicate"
    LOCATION_INCONSISTENCY = "location_inconsistency"

    # H2: Personajes
    ATTRIBUTE_INCONSISTENCY = "attribute_inconsistency"
    NAME_VARIANT = "name_variant"
    CHARACTER_RESURRECTION = "character_resurrection"

    # H3: Estructura
    SETUP_WITHOUT_PAYOFF = "setup_without_payoff"
    PAYOFF_WITHOUT_SETUP = "payoff_without_setup"

    # H4: Voz
    LEXICAL_REPETITION = "lexical_repetition"
    SEMANTIC_REPETITION = "semantic_repetition"
    VOICE_DEVIATION = "voice_deviation"
    REGISTER_INCONSISTENCY = "register_inconsistency"

    # H5: Focalización
    FOCALIZATION_VIOLATION = "focalization_violation"

    # H6: Información
    TIMELINE_INCONSISTENCY = "timeline_inconsistency"
```

---

## Métodos de Detección (DetectionMethod)

```python
class DetectionMethod(Enum):
    NER = "ner"          # Reconocimiento de entidades nombradas
    COREF = "coref"      # Resolución de correferencia
    PATTERN = "pattern"  # Patrones regex/heurísticos
    MANUAL = "manual"    # Anotación del usuario
    EMBEDDING = "embedding"  # Similaridad semántica
```

---

## Fases de Análisis (AnalysisPhase)

```python
class AnalysisPhase(Enum):
    PENDING = "pending"           # No iniciado
    PARSING = "parsing"           # Leyendo DOCX
    STRUCTURE = "structure"       # Detectando capítulos/escenas
    NER = "ner"                   # Reconocimiento de entidades
    COREFERENCE = "coreference"   # Resolución de correferencias
    ATTRIBUTES = "attributes"     # Extracción de atributos
    CONSISTENCY = "consistency"   # Verificación de consistencia
    STYLE = "style"               # Análisis de estilo
    VOICE = "voice"               # Perfiles de voz
    TEMPORAL = "temporal"         # Análisis temporal
    COMPLETE = "complete"         # Finalizado
    ERROR = "error"               # Error en algún paso
```

---

## Tipos de Focalización (FocalizationType)

```python
class FocalizationType(Enum):
    ZERO = "zero"        # Omnisciente (conoce todo)
    INTERNAL = "internal"  # Limitado a un personaje
    EXTERNAL = "external"  # Solo acciones externas, sin pensamientos
```

### Subtipos de Focalización Interna

```python
class InternalFocalizationType(Enum):
    FIXED = "fixed"      # Siempre el mismo personaje
    VARIABLE = "variable"  # Cambia entre personajes (por capítulo)
    MULTIPLE = "multiple"  # Múltiples simultáneos
```

---

## Métodos de Relocalización (RelocationMethod)

```python
class RelocationMethod(Enum):
    EXACT_MATCH = "exact_match"      # Texto idéntico encontrado
    STRUCTURAL = "structural"         # Mismo cap/párrafo/oración
    CONTEXT_MATCH = "context_match"  # Contexto circundante coincide
    FUZZY_MATCH = "fuzzy_match"      # Coincidencia aproximada
    NOT_FOUND = "not_found"          # No se pudo relocalizar
```

---

## Siguiente

Ver [Schema de Base de Datos](./database-schema.md) para la implementación SQL de estos enums.
