# STEP 3.1: Detección de Variantes de Grafía

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P1 (Alto valor) |
| **Prerequisitos** | STEP 2.2 |

---

## Descripción

Detectar variantes de escritura del mismo nombre que pueden ser errores tipográficos o inconsistencias (e.g., "Lucía" vs "Lucia", "María José" vs "Mª José").

---

## Inputs

- Entidades con nombres canónicos
- Aliases existentes

---

## Outputs

- `src/narrative_assistant/analysis/name_variants.py`
- Sugerencias de posibles variantes
- Función de normalización para comparación

---

## Algoritmo

1. Normalizar nombres (quitar acentos, capitalización)
2. Agrupar por forma normalizada
3. Detectar variantes cercanas por Levenshtein
4. Detectar abreviaturas comunes (Mª, D., Dr.)
5. Generar alertas para revisión

---

## Implementación

```python
import unicodedata
import re
from dataclasses import dataclass
from typing import List, Set, Tuple
from difflib import SequenceMatcher

@dataclass
class NameVariantSuggestion:
    name1: str
    name2: str
    similarity: float
    reason: str
    entity1_id: int
    entity2_id: int

def normalize_for_comparison(name: str) -> str:
    """Normaliza un nombre para comparación."""
    # 1. Quitar acentos
    normalized = unicodedata.normalize('NFD', name)
    normalized = ''.join(c for c in normalized
                        if unicodedata.category(c) != 'Mn')

    # 2. Minúsculas
    normalized = normalized.lower()

    # 3. Expandir abreviaturas comunes
    abbreviations = {
        'mª': 'maria',
        'ma.': 'maria',
        'd.': 'don',
        'dª': 'doña',
        'dr.': 'doctor',
        'dra.': 'doctora',
        'sr.': 'señor',
        'sra.': 'señora',
        'fco.': 'francisco',
        'jse.': 'jose',
    }
    for abbr, full in abbreviations.items():
        normalized = normalized.replace(abbr, full)

    # 4. Quitar espacios múltiples
    normalized = ' '.join(normalized.split())

    return normalized

class NameVariantDetector:
    def __init__(self, min_similarity: float = 0.8):
        self.min_similarity = min_similarity

    def detect_variants(
        self,
        entities: List['Entity']
    ) -> List[NameVariantSuggestion]:
        """Detecta posibles variantes de nombres."""
        suggestions = []

        # Crear índice de formas normalizadas
        normalized_index: dict = {}
        for entity in entities:
            norm = normalize_for_comparison(entity.canonical_name)
            if norm not in normalized_index:
                normalized_index[norm] = []
            normalized_index[norm].append(entity)

        # 1. Detectar nombres con misma forma normalizada
        for norm, ents in normalized_index.items():
            if len(ents) > 1:
                for i, e1 in enumerate(ents):
                    for e2 in ents[i+1:]:
                        if e1.canonical_name != e2.canonical_name:
                            suggestions.append(NameVariantSuggestion(
                                name1=e1.canonical_name,
                                name2=e2.canonical_name,
                                similarity=1.0,
                                reason="Misma forma normalizada (¿variante de acento/mayúsculas?)",
                                entity1_id=e1.id,
                                entity2_id=e2.id
                            ))

        # 2. Detectar nombres similares por Levenshtein
        normalized_names = list(normalized_index.keys())
        for i, norm1 in enumerate(normalized_names):
            for norm2 in normalized_names[i+1:]:
                similarity = SequenceMatcher(None, norm1, norm2).ratio()
                if similarity >= self.min_similarity and similarity < 1.0:
                    e1 = normalized_index[norm1][0]
                    e2 = normalized_index[norm2][0]
                    suggestions.append(NameVariantSuggestion(
                        name1=e1.canonical_name,
                        name2=e2.canonical_name,
                        similarity=similarity,
                        reason=f"Nombres similares ({similarity:.0%})",
                        entity1_id=e1.id,
                        entity2_id=e2.id
                    ))

        return sorted(suggestions, key=lambda x: -x.similarity)

    def find_abbreviations(
        self,
        entities: List['Entity']
    ) -> List[NameVariantSuggestion]:
        """Detecta nombres que podrían ser abreviaturas de otros."""
        suggestions = []

        # Patrones de abreviatura
        abbr_patterns = [
            (r'^(\w)\.\s*(\w+)$', r'^\1\w+\s+\2$'),  # J. García -> Juan García
            (r'^(\w+)\s+(\w)\.?$', r'^\1\s+\2\w+$'),  # María J. -> María José
        ]

        names = [(e.canonical_name, e.id) for e in entities]

        for name1, id1 in names:
            for name2, id2 in names:
                if id1 >= id2:
                    continue

                # Comprobar si uno es abreviatura del otro
                if self._is_abbreviation(name1, name2):
                    suggestions.append(NameVariantSuggestion(
                        name1=name1,
                        name2=name2,
                        similarity=0.9,
                        reason="Posible abreviatura",
                        entity1_id=id1,
                        entity2_id=id2
                    ))

        return suggestions

    def _is_abbreviation(self, short: str, long: str) -> bool:
        """Comprueba si short es abreviatura de long."""
        # Caso: "J. García" es abreviatura de "Juan García"
        short_parts = short.replace('.', ' ').split()
        long_parts = long.split()

        if len(short_parts) != len(long_parts):
            return False

        for sp, lp in zip(short_parts, long_parts):
            if len(sp) == 1:
                if not lp.lower().startswith(sp.lower()):
                    return False
            elif sp.lower() != lp.lower():
                return False

        return short != long
```

---

## Criterio de DONE

```python
from narrative_assistant.analysis import NameVariantDetector, normalize_for_comparison

# Test normalización
assert normalize_for_comparison("Lucía") == normalize_for_comparison("lucia")
assert normalize_for_comparison("Mª José") == normalize_for_comparison("Maria Jose")

# Test detección
detector = NameVariantDetector()

class MockEntity:
    def __init__(self, id, name):
        self.id = id
        self.canonical_name = name

entities = [
    MockEntity(1, "Lucía García"),
    MockEntity(2, "Lucia García"),  # Sin acento
    MockEntity(3, "J. Martínez"),
    MockEntity(4, "Juan Martínez"),
]

variants = detector.detect_variants(entities)
assert any(v.name1 == "Lucía García" and v.name2 == "Lucia García" for v in variants)

print(f"✅ Detectadas {len(variants)} posibles variantes")
```

---

## Siguiente

[STEP 3.2: Repeticiones Léxicas](./step-3.2-lexical-repetitions.md)
