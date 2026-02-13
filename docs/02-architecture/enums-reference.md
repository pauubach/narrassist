# Enums de Referencia

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## Propósito

Este documento define los valores canónicos para todos los enums utilizados en el sistema. Cualquier implementación debe usar estos valores exactos.

> **Actualizado**: 2026-02-13 — sincronizado con código fuente v0.9.4

---

## Estados de Alerta (AlertStatus)

**Fuente**: `src/narrative_assistant/alerts/models.py`

```python
class AlertStatus(Enum):
    NEW = "new"                    # Recién creada
    OPEN = "open"                  # Vista por el usuario pero sin acción
    ACKNOWLEDGED = "acknowledged"  # Usuario vio y registró
    IN_PROGRESS = "in_progress"    # Usuario está trabajando en ella
    RESOLVED = "resolved"          # Usuario corrigió el problema
    DISMISSED = "dismissed"        # Usuario descartó (falso positivo)
    AUTO_RESOLVED = "auto_resolved"  # Se resolvió automáticamente
```

### Transiciones Válidas

```
new → open → acknowledged → in_progress → resolved
               ↓               ↓
           dismissed        dismissed

[cualquiera] → auto_resolved (cuando el texto cambia)
```

---

## Severidad de Alerta (AlertSeverity)

**Fuente**: `src/narrative_assistant/alerts/models.py`

```python
class AlertSeverity(Enum):
    CRITICAL = "critical"  # Debe corregirse (error evidente)
    WARNING = "warning"    # Debería revisarse (posible error)
    INFO = "info"          # Sugerencia (mejora recomendada)
    HINT = "hint"          # Opcional (sugerencia menor)
```

### Mapeo Severidad ↔ Confianza

| Confianza | Severidad | Descripción |
|-----------|-----------|-------------|
| ≥0.9 | critical | Casi seguro que es error |
| 0.7-0.9 | warning | Probablemente error |
| 0.5-0.7 | info | Posible error |
| <0.5 | hint | Incierto, verificar |

---

## Categorías de Alerta (AlertCategory)

**Fuente**: `src/narrative_assistant/alerts/models.py`

```python
class AlertCategory(Enum):
    CONSISTENCY = "consistency"                    # Inconsistencias de atributos/tiempo
    STYLE = "style"                                # Repeticiones, voz, estilo narrativo
    BEHAVIORAL = "behavioral"                      # Inconsistencias de comportamiento
    FOCALIZATION = "focalization"                   # Violaciones de focalización/PDV
    STRUCTURE = "structure"                         # Problemas estructurales
    WORLD = "world"                                # Inconsistencias del mundo narrativo
    ENTITY = "entity"                              # Problemas con entidades
    ORTHOGRAPHY = "orthography"                    # Errores ortográficos
    GRAMMAR = "grammar"                            # Errores gramaticales
    TIMELINE_ISSUE = "timeline"                    # Inconsistencias temporales
    CHARACTER_CONSISTENCY = "character_consistency" # Inconsistencias de personajes
    VOICE_DEVIATION = "voice_deviation"            # Desviaciones de voz/registro
    EMOTIONAL = "emotional"                        # Incoherencias emocionales
    TYPOGRAPHY = "typography"                       # Errores tipográficos
    PUNCTUATION = "punctuation"                    # Puntuación
    REPETITION = "repetition"                      # Repeticiones léxicas cercanas
    AGREEMENT = "agreement"                        # Concordancia gramatical
    DIALOGUE = "dialogue"                          # Problemas de diálogos
    OTHER = "other"                                # Otras alertas no categorizadas
```

---

## Tipos de Entidad (EntityType)

**Fuente**: `src/narrative_assistant/entities/models.py`

```python
class EntityType(Enum):
    # === Seres vivos ===
    CHARACTER = "character"      # Personaje humano
    ANIMAL = "animal"            # Animal (mascota, caballo, lobo)
    CREATURE = "creature"        # Criatura fantástica/monstruo

    # === Lugares ===
    LOCATION = "location"        # Lugar genérico (bosque, playa)
    BUILDING = "building"        # Edificio/estructura (castillo, taberna)
    REGION = "region"            # Región geográfica (reino, país)

    # === Objetos ===
    OBJECT = "object"            # Objeto relevante (espada, anillo, carta)
    VEHICLE = "vehicle"          # Vehículo (barco, carruaje, nave)

    # === Grupos ===
    ORGANIZATION = "organization"  # Organización formal (gremio, ejército)
    FACTION = "faction"            # Facción/grupo informal (rebeldes)
    FAMILY = "family"              # Familia/linaje/casa noble

    # === Temporales ===
    EVENT = "event"              # Evento importante (La Gran Guerra)
    TIME_PERIOD = "time_period"  # Período temporal (Era Oscura)

    # === Conceptuales ===
    CONCEPT = "concept"          # Concepto abstracto (profecía, maldición)
    RELIGION = "religion"        # Religión/culto
    MAGIC_SYSTEM = "magic_system"  # Sistema mágico/poder

    # === Culturales ===
    WORK = "work"                # Obra mencionada (libro, canción, leyenda)
    TITLE = "title"              # Título/rango (Rey del Norte)
    LANGUAGE = "language"        # Idioma/dialecto (Alto Valyrio)
    CUSTOM = "custom"            # Costumbre/tradición
```

---

## Importancia de Entidad (EntityImportance)

**Fuente**: `src/narrative_assistant/entities/models.py`

```python
class EntityImportance(Enum):
    PRINCIPAL = "principal"  # Importancia máxima (protagonista, lugar central)
    HIGH = "high"            # Importancia alta (co-protagonistas, lugares principales)
    MEDIUM = "medium"        # Importancia media (secundarios recurrentes)
    LOW = "low"              # Importancia baja (personajes menores)
    MINIMAL = "minimal"      # Importancia mínima (solo mencionado una vez)

    # Aliases deprecated (compatibilidad DB)
    SECONDARY = "secondary"  # → MEDIUM
    PRIMARY = "primary"      # → HIGH
```

### Mapeo Legacy

| Valor antiguo | Se resuelve a |
|---------------|---------------|
| `"secondary"` | MEDIUM |
| `"primary"` | HIGH |
| `"main"` | PRINCIPAL |
| `"critical"` | PRINCIPAL |
| `"minor"` | LOW |
| `"background"` | MINIMAL |

---

## Tipos de Atributo (AttributeType)

```python
class AttributeType(Enum):
    PHYSICAL = "physical"            # Color ojos, pelo, altura, edad
    PSYCHOLOGICAL = "psychological"  # Carácter, miedos, deseos
    SOCIAL = "social"                # Profesión, relaciones, estatus
    BACKGROUND = "background"        # Historia, origen, eventos pasados
```

---

## Inconsistencias Temporales (InconsistencyType)

**Fuente**: `src/narrative_assistant/temporal/inconsistencies.py`

```python
class InconsistencyType(Enum):
    AGE_CONTRADICTION = "age_contradiction"                        # Edades que no cuadran
    IMPOSSIBLE_SEQUENCE = "impossible_sequence"                    # Eventos en orden imposible
    TIME_JUMP_SUSPICIOUS = "time_jump_suspicious"                  # Salto temporal sospechoso
    MARKER_CONFLICT = "marker_conflict"                            # Marcadores contradictorios
    CHARACTER_AGE_MISMATCH = "character_age_mismatch"              # Edad no coincide con fechas
    ANACHRONISM = "anachronism"                                    # Referencia anacrónica
    # Level C (cross-chapter)
    CROSS_CHAPTER_AGE_REGRESSION = "cross_chapter_age_regression"  # Edad retrocede sin flashback
    PHASE_AGE_INCOMPATIBLE = "phase_age_incompatible"              # Fase vital incompatible con edad
    BIRTH_YEAR_CONTRADICTION = "birth_year_contradiction"          # Año nacimiento contradictorio
```

---

## Severidad de Inconsistencia (InconsistencySeverity)

**Fuente**: `src/narrative_assistant/temporal/inconsistencies.py`

```python
class InconsistencySeverity(Enum):
    LOW = "low"          # Posible problema menor
    MEDIUM = "medium"    # Problema probable
    HIGH = "high"        # Inconsistencia clara
    CRITICAL = "critical"  # Error evidente
```

---

## Métodos de Detección Temporal (TemporalDetectionMethod)

**Fuente**: `src/narrative_assistant/temporal/inconsistencies.py`

```python
class TemporalDetectionMethod(Enum):
    DIRECT = "direct"          # Análisis directo de fechas/edades
    CONTEXTUAL = "contextual"  # Patrones de transición y contexto
    LLM = "llm"                # LLM local para análisis semántico
    HEURISTICS = "heuristics"  # Heurísticas narrativas
```

---

## Métodos de Detección Ortográfica (DetectionMethod)

**Fuente**: `src/narrative_assistant/nlp/orthography/base.py`

```python
class DetectionMethod(Enum):
    DICTIONARY = "dictionary"      # Diccionario (hunspell/aspell)
    LEVENSHTEIN = "levenshtein"    # Distancia de edición
    REGEX = "regex"                # Patrón regex
    LLM = "llm"                    # LLM local (Ollama)
    CONTEXT = "context"            # Análisis de contexto
```

---

## Fases de Análisis (AnalysisPhase)

**Fuente**: `src/narrative_assistant/pipelines/unified_analysis.py`

```python
class AnalysisPhase(Enum):
    PARSING = "parsing"                    # Leyendo documento
    STRUCTURE = "structure"                # Detectando capítulos/escenas
    BASE_EXTRACTION = "base_extraction"    # NER + atributos iniciales
    RESOLUTION = "resolution"              # Correferencias + fusión
    DEEP_EXTRACTION = "deep_extraction"    # Atributos profundos + relaciones
    QUALITY = "quality"                    # Estilo, voz, ortografía
    CONSISTENCY = "consistency"            # Verificación de consistencia
    ALERTS = "alerts"                      # Generación de alertas
```

---

## Estado de Análisis (AnalysisStatus)

**Fuente**: `src/narrative_assistant/persistence/analysis.py`

```python
class AnalysisStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

---

## Tipos de Focalización (FocalizationType)

```python
class FocalizationType(Enum):
    ZERO = "zero"          # Omnisciente (conoce todo)
    INTERNAL = "internal"  # Limitado a un personaje
    EXTERNAL = "external"  # Solo acciones externas, sin pensamientos
```

### Subtipos de Focalización Interna

```python
class InternalFocalizationType(Enum):
    FIXED = "fixed"        # Siempre el mismo personaje
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
