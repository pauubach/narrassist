# Backend - NLP Module

Ubicación: `src/narrative_assistant/nlp/`

## NER (`ner.py`)

### Enum `EntityLabel`

| Valor | Descripción |
|-------|-------------|
| `PER` | Persona (personaje) |
| `LOC` | Lugar |
| `ORG` | Organización |
| `MISC` | Miscelánea |

### Dataclass `ExtractedEntity`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `text` | `str` | Texto de la entidad |
| `label` | `EntityLabel` | Tipo de entidad |
| `start_char` | `int` | Posición de inicio |
| `end_char` | `int` | Posición de fin |
| `confidence` | `float` | Confianza 0.0-1.0 |
| `source` | `str` | Fuente ("spacy", "gazetteer", "heuristic") |
| `canonical_form` | `Optional[str]` | Forma normalizada |

### Dataclass `NERResult`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `entities` | `list[ExtractedEntity]` | Entidades extraídas |
| `processed_chars` | `int` | Caracteres procesados |
| `gazetteer_candidates` | `set[str]` | Candidatos heurísticos |

| Método/Propiedad | Firma | Retorno |
|------------------|-------|---------|
| `get_by_label` | `(label: EntityLabel) -> list[ExtractedEntity]` | Entidades filtradas |
| `get_persons` | `() -> list[ExtractedEntity]` | Entidades PER |
| `get_locations` | `() -> list[ExtractedEntity]` | Entidades LOC |
| `get_organizations` | `() -> list[ExtractedEntity]` | Entidades ORG |
| `unique_entities` | `@property -> dict[str, ExtractedEntity]` | Entidades únicas |

### Clase `NERExtractor`

```python
from narrative_assistant.nlp.ner import NERExtractor, get_ner_extractor

extractor = get_ner_extractor()  # Singleton
```

#### Constructor

```python
NERExtractor(
    enable_gazetteer: bool = True,
    min_entity_confidence: float = 0.5,
    enable_gpu: Optional[bool] = None,
)
```

#### Métodos

| Método | Firma | Retorno |
|--------|-------|---------|
| `extract_entities` | `(text: str) -> Result[NERResult]` | Entidades extraídas |
| `add_to_gazetteer` | `(name: str, label: EntityLabel = EntityLabel.PER) -> None` | - |
| `remove_from_gazetteer` | `(name: str) -> bool` | Éxito |
| `clear_gazetteer` | `() -> None` | - |
| `get_gazetteer_stats` | `() -> dict[str, int]` | Estadísticas |

### Factory Functions

```python
from narrative_assistant.nlp.ner import get_ner_extractor, reset_ner_extractor, extract_entities

extractor = get_ner_extractor()  # Singleton
reset_ner_extractor()  # Reset para tests
result = extract_entities("Juan vive en Madrid.")  # Atajo
```

| Función | Firma |
|---------|-------|
| `get_ner_extractor` | `(enable_gazetteer: bool = True, enable_gpu: Optional[bool] = None) -> NERExtractor` |
| `reset_ner_extractor` | `() -> None` |
| `extract_entities` | `(text: str) -> Result[NERResult]` |

---

## Embeddings (`embeddings.py`)

### Clase `EmbeddingsModel`

```python
from narrative_assistant.nlp.embeddings import EmbeddingsModel, get_embeddings_model

model = get_embeddings_model()  # Singleton
```

#### Constructor

```python
EmbeddingsModel(
    model_name: Optional[str] = None,
    device: Optional[str] = None,  # "cuda", "mps", "cpu", None (auto)
    batch_size: Optional[int] = None,
)
```

#### Métodos

| Método | Firma | Retorno |
|--------|-------|---------|
| `encode` | `(sentences: Union[str, list[str]], normalize: bool = True, show_progress: bool = False) -> np.ndarray` | Embeddings |
| `similarity` | `(text1: Union[str, list[str]], text2: Union[str, list[str]]) -> Union[float, np.ndarray]` | Similitud coseno |
| `find_similar` | `(query: str, candidates: list[str], top_k: int = 5, threshold: float = 0.0) -> list[tuple[int, str, float]]` | Resultados similares |
| `get_device_info` | `() -> dict` | Info del dispositivo |
| `warmup` | `() -> None` | Calienta el modelo |

### Factory Functions

```python
from narrative_assistant.nlp.embeddings import get_embeddings_model, encode_texts, reset_embeddings_model

model = get_embeddings_model()  # Singleton
embeddings = encode_texts(["texto 1", "texto 2"])  # Atajo
reset_embeddings_model()  # Reset para tests
```

| Función | Firma |
|---------|-------|
| `get_embeddings_model` | `(model_name: Optional[str] = None, device: Optional[str] = None) -> EmbeddingsModel` |
| `encode_texts` | `(texts: Union[str, list[str]], normalize: bool = True) -> np.ndarray` |
| `reset_embeddings_model` | `() -> None` |

---

## Attributes (`attributes.py`)

### Enum `AttributeCategory`

| Valor | Descripción |
|-------|-------------|
| `PHYSICAL` | Ojos, pelo, altura, edad |
| `PSYCHOLOGICAL` | Personalidad, temperamento |
| `SOCIAL` | Profesión, rol, relaciones |
| `ABILITY` | Habilidades, poderes |
| `GEOGRAPHIC` | Ubicación, clima, terreno |
| `ARCHITECTURAL` | Estilo, tamaño, estado |
| `MATERIAL` | De qué está hecho |
| `APPEARANCE` | Color, forma, tamaño |
| `FUNCTION` | Para qué sirve |
| `STATE` | Condición actual |

### Enum `AttributeKey`

| Valor | Descripción |
|-------|-------------|
| `EYE_COLOR` | Color de ojos |
| `HAIR_COLOR` | Color de pelo |
| `HAIR_TYPE` | Tipo de pelo |
| `AGE` | Edad |
| `HEIGHT` | Altura |
| `BUILD` | Constitución física |
| `SKIN` | Piel |
| `DISTINCTIVE_FEATURE` | Rasgo distintivo |
| `PERSONALITY` | Personalidad |
| `TEMPERAMENT` | Temperamento |
| `FEAR` | Miedo |
| `DESIRE` | Deseo |
| `PROFESSION` | Profesión |
| `TITLE` | Título |
| `RELATIONSHIP` | Relación |
| `NATIONALITY` | Nacionalidad |
| `CLIMATE` | Clima |
| `TERRAIN` | Terreno |
| `SIZE` | Tamaño |
| `LOCATION` | Ubicación |
| `MATERIAL` | Material |
| `COLOR` | Color |
| `CONDITION` | Condición |
| `OTHER` | Otro |

### Dataclass `ExtractedAttribute`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `entity_name` | `str` | Nombre de la entidad |
| `category` | `AttributeCategory` | Categoría |
| `key` | `AttributeKey` | Clave del atributo |
| `value` | `str` | Valor extraído |
| `source_text` | `str` | Texto original |
| `start_char` | `int` | Posición de inicio |
| `end_char` | `int` | Posición de fin |
| `confidence` | `float` | Confianza 0.0-1.0 |
| `is_negated` | `bool` | Si está negado |
| `is_metaphor` | `bool` | Si es metáfora |
| `chapter_id` | `Optional[int]` | ID del capítulo |

| Método | Firma |
|--------|-------|
| `to_dict` | `() -> dict` |

### Dataclass `AttributeExtractionResult`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `attributes` | `list[ExtractedAttribute]` | Atributos extraídos |
| `processed_chars` | `int` | Caracteres procesados |
| `metaphors_filtered` | `int` | Metáforas filtradas |

| Propiedad | Retorno |
|-----------|---------|
| `by_entity` | `dict[str, list[ExtractedAttribute]]` |
| `by_key` | `dict[str, list[ExtractedAttribute]]` |

### Clase `AttributeExtractor`

```python
from narrative_assistant.nlp.attributes import AttributeExtractor, get_attribute_extractor

extractor = get_attribute_extractor()  # Singleton
```

#### Constructor

```python
AttributeExtractor(
    filter_metaphors: bool = True,
    min_confidence: float = 0.5,
    use_dependency_extraction: bool = True,
)
```

#### Métodos

| Método | Firma | Retorno |
|--------|-------|---------|
| `extract_attributes` | `(text: str, entity_mentions: Optional[list[tuple[str, int, int]]] = None, chapter_id: Optional[int] = None) -> Result[AttributeExtractionResult]` | Atributos extraídos |
| `extract_from_context` | `(entity_name: str, context: str, context_start: int = 0) -> list[ExtractedAttribute]` | Atributos del contexto |

### Factory Functions

```python
from narrative_assistant.nlp.attributes import get_attribute_extractor, extract_attributes, reset_attribute_extractor

extractor = get_attribute_extractor()  # Singleton
result = extract_attributes("Juan tenía ojos verdes.")  # Atajo
reset_attribute_extractor()  # Reset para tests
```

| Función | Firma |
|---------|-------|
| `get_attribute_extractor` | `(filter_metaphors: bool = True, min_confidence: float = 0.5) -> AttributeExtractor` |
| `extract_attributes` | `(text: str, entity_mentions: Optional[list[tuple[str, int, int]]] = None) -> Result[AttributeExtractionResult]` |
| `reset_attribute_extractor` | `() -> None` |

---

## Errores Comunes

### Error: `'NERExtractor' object has no attribute 'process'`

**Incorrecto:**
```python
result = extractor.process(text)
```

**Correcto:**
```python
result = extractor.extract_entities(text)
```

### Error: `'EmbeddingsModel' object has no attribute 'embed'`

**Incorrecto:**
```python
embeddings = model.embed(texts)
```

**Correcto:**
```python
embeddings = model.encode(texts)
```

### Error: `'AttributeExtractor' object has no attribute 'extract'`

**Incorrecto:**
```python
result = extractor.extract(text)
```

**Correcto:**
```python
result = extractor.extract_attributes(text)
```

### Error: `'AttributeExtractor' object has no attribute 'extract_for_entity'`

**Incorrecto:**
```python
result = extractor.extract_for_entity(entity_name, text, min_confidence=0.5)
```

**Correcto:**
```python
# Usar extract_attributes con entity_mentions
result = extractor.extract_attributes(
    text=text,
    entity_mentions=[(entity_name, start_char, end_char)],
    chapter_id=None,
)
# Acceder a los atributos extraídos
if result.is_success:
    for attr in result.value.attributes:
        print(f"{attr.entity_name}: {attr.key} = {attr.value}")
```

### Error: Obtener extractor sin singleton

**Incorrecto:**
```python
extractor = NERExtractor()  # Crea nueva instancia
```

**Correcto:**
```python
extractor = get_ner_extractor()  # Usa singleton
```
