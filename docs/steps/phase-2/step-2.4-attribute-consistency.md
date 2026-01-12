# STEP 2.4: Detector de Inconsistencias de Atributos

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 2.3 |

---

## Descripción

Detectar cuando un personaje tiene valores contradictorios para el mismo atributo (e.g., "ojos verdes" en cap. 2 vs "ojos azules" en cap. 5).

---

## Inputs

- Atributos extraídos por entidad
- Embeddings para comparación semántica

---

## Outputs

- `src/narrative_assistant/analysis/attribute_consistency.py`
- Alertas cuando hay valores contradictorios
- Fórmula de confianza documentada

---

## Algoritmo

1. Agrupar atributos por (entidad, attribute_key)
2. Si hay >1 valor diferente para mismo key:
   a. Calcular similitud semántica (embeddings)
   b. Si similitud < 0.7 → posible inconsistencia
   c. Verificar si son antónimos (verde/azul, alto/bajo)
3. Generar alerta con ambos valores y fuentes

---

## Implementación

```python
from dataclasses import dataclass
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np

@dataclass
class AttributeInconsistency:
    entity_id: int
    entity_name: str
    attribute_key: str
    value1: str
    value1_source: dict  # {chapter, page, excerpt}
    value2: str
    value2_source: dict
    confidence: float
    explanation: str

class AttributeConsistencyChecker:
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # Antónimos conocidos
        self.antonyms = {
            'verde': ['azul', 'marrón', 'negro', 'gris'],
            'azul': ['verde', 'marrón', 'negro'],
            'alto': ['bajo', 'pequeño'],
            'joven': ['viejo', 'anciano', 'mayor'],
            'rubio': ['moreno', 'castaño', 'pelirrojo'],
        }

    def check_consistency(
        self,
        attributes: List['Attribute']
    ) -> List[AttributeInconsistency]:
        """Detecta inconsistencias en atributos."""
        inconsistencies = []

        # Agrupar por (entity_id, key)
        grouped: Dict[tuple, List] = {}
        for attr in attributes:
            key = (attr.entity_id, attr.attribute_key)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(attr)

        # Buscar inconsistencias
        for (entity_id, attr_key), attrs in grouped.items():
            if len(attrs) < 2:
                continue

            # Comparar cada par
            for i, attr1 in enumerate(attrs):
                for attr2 in attrs[i+1:]:
                    if attr1.value.lower() == attr2.value.lower():
                        continue  # Mismo valor

                    # Calcular confianza de inconsistencia
                    confidence = self._calculate_confidence(
                        attr1.value, attr2.value, attr_key
                    )

                    if confidence > 0.5:
                        inconsistencies.append(AttributeInconsistency(
                            entity_id=entity_id,
                            entity_name=attrs[0].entity_name,
                            attribute_key=attr_key,
                            value1=attr1.value,
                            value1_source={
                                'chapter': attr1.source_chapter,
                                'excerpt': attr1.source_excerpt
                            },
                            value2=attr2.value,
                            value2_source={
                                'chapter': attr2.source_chapter,
                                'excerpt': attr2.source_excerpt
                            },
                            confidence=confidence,
                            explanation=self._generate_explanation(
                                attr_key, attr1.value, attr2.value, confidence
                            )
                        ))

        return inconsistencies

    def _calculate_confidence(
        self,
        value1: str,
        value2: str,
        attr_key: str
    ) -> float:
        """Calcula confianza de que sea una inconsistencia real."""
        v1, v2 = value1.lower(), value2.lower()

        # 1. ¿Son antónimos conocidos?
        if v1 in self.antonyms and v2 in self.antonyms[v1]:
            return 0.95

        # 2. Similitud semántica
        embeddings = self.model.encode([value1, value2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )

        # Baja similitud = alta probabilidad de inconsistencia
        if similarity < 0.3:
            return 0.9
        elif similarity < 0.5:
            return 0.7
        elif similarity < 0.7:
            return 0.5
        else:
            return 0.3  # Valores similares, probablemente sinónimos

    def _generate_explanation(
        self,
        attr_key: str,
        value1: str,
        value2: str,
        confidence: float
    ) -> str:
        """Genera explicación legible de la inconsistencia."""
        return (
            f"El atributo '{attr_key}' tiene valores diferentes: "
            f"'{value1}' y '{value2}'. "
            f"Confianza: {confidence:.0%}"
        )
```

---

## Criterio de DONE

```python
from narrative_assistant.analysis import AttributeConsistencyChecker
from narrative_assistant.db.models import Attribute

checker = AttributeConsistencyChecker()

# Simular atributos contradictorios
attrs = [
    Attribute(id=1, entity_id=1, entity_name="María",
              attribute_type="physical", attribute_key="eye_color",
              value="verdes", source_chapter=2, source_excerpt="ojos verdes"),
    Attribute(id=2, entity_id=1, entity_name="María",
              attribute_type="physical", attribute_key="eye_color",
              value="azules", source_chapter=5, source_excerpt="ojos azules"),
]

alerts = checker.check_consistency(attrs)
assert len(alerts) == 1
assert alerts[0].confidence > 0.8

print(f"✅ Detectada inconsistencia: {alerts[0].explanation}")
```

---

## Siguiente

[STEP 3.1: Variantes de Grafía](../phase-3/step-3.1-name-variants.md)
