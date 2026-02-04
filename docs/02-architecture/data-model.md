# Modelo de Datos

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## Diagrama de Entidades

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ENTIDADES CORE                                   │
│                                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │CHARACTER │    │ LOCATION │    │  OBJECT  │    │  EVENT   │         │
│   └─────┬────┘    └─────┬────┘    └─────┬────┘    └─────┬────┘         │
│         │               │               │               │                │
│         └───────────────┴───────────────┼───────────────┘                │
│                                         │                                │
│                                         ▼                                │
│                          ┌─────────────────────┐                         │
│                          │  TEXT_REFERENCE     │  ← Vincula todo al     │
│                          │  (entity_type,      │    texto original      │
│                          │   entity_id,        │                         │
│                          │   chapter_id,       │                         │
│                          │   start_offset,     │                         │
│                          │   end_offset)       │                         │
│                          └─────────────────────┘                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Entidad Principal: Entity

La tabla `entity` es el núcleo del modelo. Almacena personajes, lugares, objetos y organizaciones.

```python
@dataclass
class Entity:
    id: int
    project_id: int
    entity_type: str  # 'character', 'location', 'object', 'organization', 'event'
    canonical_name: str
    aliases: List[str]  # JSON array
    importance: str  # 'protagonist', 'main', 'secondary', 'minor', 'mentioned'
    first_chapter: Optional[int]
    last_chapter: Optional[int]
    validated_by_user: bool
```

### Tipos de entidad

| Tipo | Descripción | Fuente de detección |
|------|-------------|---------------------|
| `character` | Personajes | NER (PER) |
| `location` | Lugares | NER (LOC) |
| `object` | Objetos significativos | Manual / Patrones |
| `organization` | Organizaciones | NER (ORG) |
| `event` | Eventos importantes | Manual / Extracción |

### Importancia

| Nivel | Criterio |
|-------|----------|
| `protagonist` | POV principal, >30% de menciones |
| `main` | Personajes clave, >10% de menciones |
| `secondary` | Apariciones regulares |
| `minor` | Pocas apariciones |
| `mentioned` | Solo mencionados, sin acción |

---

## Referencias al Texto

Toda información extraída mantiene referencia a su posición original.

```python
@dataclass
class TextReference:
    id: int
    entity_id: int
    chapter_id: Optional[int]
    start_char: int  # Posición absoluta
    end_char: int
    surface_form: str  # Texto tal como aparece
    detection_method: str  # 'ner', 'coref', 'manual', 'pattern'
    confidence: float  # 0.0 - 1.0
```

### Métodos de detección

| Método | Descripción | Confianza típica |
|--------|-------------|------------------|
| `ner` | Detectado por NER | 0.7-0.9 |
| `coref` | Resuelto por correferencia | 0.5-0.7 |
| `manual` | Añadido por el usuario | 1.0 |
| `pattern` | Detectado por regex/patrones | 0.8-0.9 |

---

## Atributos

Los atributos almacenan características de las entidades con trazabilidad completa.

```python
@dataclass
class Attribute:
    id: int
    entity_id: int
    attribute_type: str  # 'physical', 'psychological', 'social', 'background'
    attribute_key: str   # 'eye_color', 'age', 'profession'
    value: str
    normalized_value: Optional[str]  # Para comparación
    source_chapter: Optional[int]
    source_page: Optional[int]
    source_line: Optional[int]
    source_excerpt: str  # Fragmento de texto
    extraction_method: str  # 'auto', 'manual'
    confidence: float
    validated_by_user: bool
```

### Tipos de atributo

| Tipo | Ejemplos | Mutabilidad |
|------|----------|-------------|
| `physical` | color_ojos, altura, edad | Mayormente inmutable |
| `psychological` | temperamento, miedos | Puede evolucionar |
| `social` | profesión, estado_civil | Mutable |
| `background` | lugar_nacimiento, educación | Inmutable |

### Normalización de valores

La normalización permite comparar valores semánticamente:

```python
# Ejemplos de normalización
"verdes" → "verde"
"verdosos" → "verde"
"treinta años" → "30"
"unos treinta" → "30~"
```

---

## Alertas

Las alertas representan posibles inconsistencias detectadas.

```python
@dataclass
class Alert:
    id: int
    project_id: int
    alert_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    confidence: float  # 0.0 - 1.0
    title: str
    description: str
    source_references: List[Dict]  # JSON: [{chapter, page, excerpt}]
    related_entity_ids: List[int]
    status: str  # 'pending', 'accepted', 'dismissed', 'false_positive'
    resolution_note: Optional[str]
```

### Tipos de alerta

| Tipo | Descripción | Severidad típica |
|------|-------------|------------------|
| `attribute_inconsistency` | Valores contradictorios | high |
| `name_variant` | Posible duplicado | medium |
| `repetition_lexical` | Repetición cercana | low |
| `repetition_semantic` | Paráfrasis | low |
| `voice_deviation` | Cambio de estilo en diálogo | medium |
| `register_change` | Cambio brusco de registro | medium |
| `focalization_violation` | Acceso a mente no focal | high |
| `temporal_inconsistency` | Anacronismo | high |

### Estados de alerta

```
pending ──► accepted ──► (resuelto)
   │
   └──────► dismissed ──► (ignorado)
   │
   └──────► false_positive ──► (marca para mejorar modelo)
```

---

## Diálogos y Voz

```python
@dataclass
class Dialogue:
    id: int
    project_id: int
    chapter_id: Optional[int]
    speaker_id: Optional[int]  # Entity ID del hablante
    start_char: int
    end_char: int
    text_content: str
    attribution_method: str  # 'explicit', 'proximity', 'manual'
    attribution_confidence: float

@dataclass
class VoiceProfile:
    entity_id: int
    avg_sentence_length: float
    vocabulary_richness: float  # TTR
    formality_score: float  # 0-1
    common_phrases: List[str]  # Muletillas
    sample_dialogues: List[str]
    word_count: int
```

---

## Timeline y Eventos

```python
@dataclass
class Event:
    id: int
    project_id: int
    description: str
    event_type: str  # 'birth', 'death', 'marriage', 'travel', 'general'
    temporal_marker: str  # Expresión original
    normalized_time: Optional[str]  # Formato normalizado
    time_certainty: str  # 'exact', 'approximate', 'uncertain'
    chapter_id: Optional[int]
    source_excerpt: str
    related_entities: List[int]
```

### Normalización temporal

| Marcador original | Normalizado | Certeza |
|-------------------|-------------|---------|
| "15 de marzo de 1985" | "1985-03-15" | exact |
| "tres días después" | "REL:+3D" | approximate |
| "aquella mañana" | None | uncertain |
| "en primavera" | "SEASON:SPRING" | approximate |

---

## Historial de Fusiones

Para deshacer fusiones de entidades:

```python
@dataclass
class MergeHistory:
    id: int
    project_id: int
    result_entity_id: int
    source_entity_ids: List[int]
    merged_at: datetime
    merged_by: str  # 'user' o 'auto'
    undone_at: Optional[datetime]
```

---

## Relaciones entre Tablas

```
project (1) ──── (n) chapter
    │                   │
    │                   └── (n) scene
    │
    ├── (n) entity ──── (n) text_reference
    │       │
    │       ├── (n) attribute
    │       │
    │       └── (1) voice_profile
    │
    ├── (n) dialogue
    │
    ├── (n) event
    │
    ├── (n) alert
    │
    ├── (n) note
    │
    └── (n) relationship
```

---

## Siguiente

Ver [Schema BD](./database-schema.md) para el SQL completo.
