# STEP 1.3: Pipeline NER

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 0.1, STEP 1.2 |

---

## Descripción

Extraer entidades nombradas (personas, lugares, organizaciones) del texto usando spaCy con gazetteers dinámicos para mejorar la detección de nombres creativos.

---

## Inputs

- Texto segmentado por capítulos

---

## Outputs

- `src/narrative_assistant/nlp/ner.py`
- Entidades PER, LOC, ORG extraídas
- Índice de menciones por entidad

---

## Advertencias

⚠️ **F1 esperado: ~60-70% en ficción española**

Los modelos NER están entrenados en texto periodístico. Los nombres inventados o creativos (Frodo, Hogwarts) NO se detectarán bien sin gazetteers.

---

## Implementación

```python
import spacy
from dataclasses import dataclass
from typing import List, Set

@dataclass
class ExtractedEntity:
    text: str
    label: str  # PER, LOC, ORG
    start_char: int
    end_char: int
    confidence: float

class NERExtractor:
    def __init__(self):
        self.nlp = spacy.load("es_core_news_lg")
        self.dynamic_gazetteer: Set[str] = set()

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extrae entidades usando spaCy + gazetteers dinámicos."""
        doc = self.nlp(text)
        entities = []

        # 1. Entidades de spaCy
        for ent in doc.ents:
            if ent.label_ in ("PER", "LOC", "ORG"):
                entities.append(ExtractedEntity(
                    text=ent.text,
                    label=ent.label_,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.8  # spaCy no da confianza, asumimos 0.8
                ))

        # 2. Gazetteer dinámico: palabras con mayúscula no reconocidas
        for token in doc:
            if (token.text[0].isupper() and
                not token.is_sent_start and
                token.text not in [e.text for e in entities] and
                len(token.text) > 2 and
                not token.like_num):

                # Posible nombre propio no detectado
                self.dynamic_gazetteer.add(token.text)
                entities.append(ExtractedEntity(
                    text=token.text,
                    label="PER",  # Asumimos personaje por defecto
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    confidence=0.5  # Baja confianza
                ))

        return entities

    def add_to_gazetteer(self, name: str, label: str = "PER"):
        """Añade un nombre al gazetteer dinámico."""
        self.dynamic_gazetteer.add(name)
```

---

## Criterio de DONE

```python
from narrative_assistant.nlp import NERExtractor

extractor = NERExtractor()
entities = extractor.extract_entities("Juan García vive en Madrid con su amigo Frodo.")

# Debe detectar Juan García y Madrid (spaCy)
assert any(e.label == "PER" and "Juan" in e.text for e in entities)
assert any(e.label == "LOC" and "Madrid" in e.text for e in entities)

# Frodo debería detectarse por gazetteer dinámico
assert any("Frodo" in e.text for e in entities)

print("✅ NER funcional")
```

---

## Siguiente

[STEP 1.4: Detector de Diálogos](./step-1.4-dialogue-detector.md)
