# STEP 2.3: Extracción de Atributos

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 2.1 |

---

## Descripción

Extraer atributos físicos de personajes (ojos, pelo, edad, altura) del texto circundante a cada mención, con filtro de metáforas.

---

## Inputs

- Entidades con menciones
- Texto circundante a cada mención

---

## Outputs

- `src/narrative_assistant/nlp/attributes.py`
- Atributos físicos detectados
- Confianza por extracción
- Filtro básico de metáforas

---

## Patrones a Implementar

- `[PERSONAJE] tenía/tiene ojos [COLOR]`
- `[PERSONAJE] era/es [ADJETIVO]` (alto, bajo, joven, viejo)
- `los ojos [COLOR] de [PERSONAJE]`
- `[PERSONAJE], de [EDAD] años`

---

## Filtro de Metáforas

⚠️ Ignorar patrones con: "como", "parecía", "cual", "semejante"

Ejemplo: "Sus ojos eran dos luceros" → NO crear atributo

---

## Implementación

```python
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ExtractedAttribute:
    entity_name: str
    attribute_type: str  # 'physical', 'psychological', etc.
    key: str  # 'eye_color', 'hair', 'age'
    value: str
    source_text: str
    start_char: int
    end_char: int
    confidence: float

# Patrones de extracción
ATTRIBUTE_PATTERNS = [
    # Ojos
    (r'(\w+)\s+ten[íi]a\s+(?:unos\s+)?ojos\s+(\w+)', 'eye_color', 0.9),
    (r'los\s+ojos\s+(\w+)\s+de\s+(\w+)', 'eye_color', 0.85),
    (r'(\w+)(?:,\s+de\s+ojos\s+(\w+))', 'eye_color', 0.85),

    # Pelo/cabello
    (r'(\w+)\s+ten[íi]a\s+(?:el\s+)?(?:pelo|cabello)\s+(\w+)', 'hair', 0.9),
    (r'(?:pelo|cabello)\s+(\w+)\s+de\s+(\w+)', 'hair', 0.85),

    # Edad
    (r'(\w+)(?:,\s+de\s+(\d+)\s+años)', 'age', 0.95),
    (r'(\w+)\s+ten[íi]a\s+(\d+)\s+años', 'age', 0.9),

    # Altura/constitución
    (r'(\w+)\s+era\s+(alto|bajo|delgado|corpulento|esbelto)', 'build', 0.8),
]

# Patrones de metáfora a ignorar
METAPHOR_INDICATORS = [
    r'\bcomo\b',
    r'\bparec[íi]a\b',
    r'\bcual\b',
    r'\bsemejante\b',
    r'\btan\s+\w+\s+como\b',
]

class AttributeExtractor:
    def extract_attributes(
        self,
        text: str,
        entity_mentions: List[tuple]  # [(name, start, end), ...]
    ) -> List[ExtractedAttribute]:
        """Extrae atributos del texto."""
        attributes = []

        for pattern, attr_key, base_confidence in ATTRIBUTE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Verificar si es metáfora
                context = text[max(0, match.start()-50):match.end()+50]
                if self._is_metaphor(context):
                    continue

                # Extraer valor y nombre
                groups = match.groups()
                if attr_key == 'eye_color' and len(groups) >= 2:
                    name, value = groups[0], groups[1]
                    if 'de' in text[match.start():match.end()]:
                        name, value = groups[1], groups[0]
                else:
                    name, value = groups[0], groups[1] if len(groups) > 1 else None

                if value:
                    attributes.append(ExtractedAttribute(
                        entity_name=name,
                        attribute_type='physical',
                        key=attr_key,
                        value=value,
                        source_text=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=base_confidence
                    ))

        return attributes

    def _is_metaphor(self, context: str) -> bool:
        """Detecta si el contexto sugiere una metáfora."""
        for pattern in METAPHOR_INDICATORS:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        return False
```

---

## Criterio de DONE

```python
from narrative_assistant.nlp import AttributeExtractor

extractor = AttributeExtractor()
attrs = extractor.extract_attributes(
    "Juan tenía ojos verdes y pelo canoso. María, de 25 años, era alta.",
    []
)

assert any(a.key == "eye_color" and a.value == "verdes" for a in attrs)
assert any(a.key == "hair" and a.value == "canoso" for a in attrs)
assert any(a.key == "age" and a.value == "25" for a in attrs)

print(f"✅ Extraídos {len(attrs)} atributos")
```

---

## Siguiente

[STEP 2.4: Consistencia de Atributos](./step-2.4-attribute-consistency.md)
