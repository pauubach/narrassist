# STEP 3.3: Detector de Repeticiones Semánticas

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 3.2 |

---

## Descripción

Detectar repeticiones de **concepto** aunque las palabras sean diferentes. Usar embeddings para encontrar oraciones o frases semánticamente similares que pueden indicar redundancia.

Ejemplos:
- "El anciano caminaba lentamente" vs "El viejo avanzaba despacio"
- "Sintió miedo" vs "El terror la invadió"

---

## Inputs

- Texto segmentado en oraciones
- Modelo de embeddings (sentence-transformers)
- Umbral de similitud configurable

---

## Outputs

- `src/narrative_assistant/analysis/semantic_repetitions.py`
- Pares de oraciones semánticamente similares
- Score de similitud
- Contexto para revisión

---

## Algoritmo

1. Segmentar texto en oraciones
2. Generar embeddings por oración
3. Calcular similitud coseno entre oraciones cercanas
4. Filtrar por umbral y distancia máxima
5. Agrupar repeticiones relacionadas

---

## Implementación

```python
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
import re

@dataclass
class SemanticRepetition:
    sentence1: str
    sentence2: str
    position1: int  # Índice de oración
    position2: int
    similarity: float
    distance_sentences: int
    chapter1: Optional[int] = None
    chapter2: Optional[int] = None

@dataclass
class SemanticConfig:
    similarity_threshold: float = 0.75  # Mínima similitud para reportar
    max_sentence_distance: int = 50  # Máxima distancia en oraciones
    min_sentence_length: int = 5  # Palabras mínimas por oración
    batch_size: int = 32  # Para procesamiento de embeddings

class SemanticRepetitionDetector:
    def __init__(
        self,
        model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        config: Optional[SemanticConfig] = None
    ):
        self.model = SentenceTransformer(model_name)
        self.config = config or SemanticConfig()

    def detect(
        self,
        text: str,
        chapter_boundaries: Optional[List[int]] = None
    ) -> List[SemanticRepetition]:
        """Detecta repeticiones semánticas en el texto."""
        # Segmentar en oraciones
        sentences = self._segment_sentences(text)

        # Filtrar oraciones muy cortas
        valid_sentences = [
            (i, s) for i, s in enumerate(sentences)
            if len(s.split()) >= self.config.min_sentence_length
        ]

        if len(valid_sentences) < 2:
            return []

        # Generar embeddings
        indices = [i for i, _ in valid_sentences]
        texts = [s for _, s in valid_sentences]
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=False
        )

        # Normalizar para similitud coseno
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Buscar pares similares
        repetitions = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                orig_i, orig_j = indices[i], indices[j]
                distance = orig_j - orig_i

                # Solo comparar oraciones cercanas
                if distance > self.config.max_sentence_distance:
                    continue

                # Calcular similitud
                similarity = float(np.dot(embeddings[i], embeddings[j]))

                if similarity >= self.config.similarity_threshold:
                    # Determinar capítulos si hay boundaries
                    ch1 = ch2 = None
                    if chapter_boundaries:
                        ch1 = self._get_chapter(orig_i, chapter_boundaries)
                        ch2 = self._get_chapter(orig_j, chapter_boundaries)

                    repetitions.append(SemanticRepetition(
                        sentence1=texts[i],
                        sentence2=texts[j],
                        position1=orig_i,
                        position2=orig_j,
                        similarity=similarity,
                        distance_sentences=distance,
                        chapter1=ch1,
                        chapter2=ch2
                    ))

        # Ordenar por similitud descendente
        return sorted(repetitions, key=lambda r: -r.similarity)

    def _segment_sentences(self, text: str) -> List[str]:
        """Segmenta texto en oraciones."""
        # Patrón simple para español
        # Considera: . ! ? ... y saltos de párrafo
        pattern = r'[.!?]+[\s]+|\.{3,}[\s]+|\n\n+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_chapter(
        self,
        sentence_index: int,
        boundaries: List[int]
    ) -> int:
        """Determina el capítulo de una oración."""
        for i, boundary in enumerate(boundaries):
            if sentence_index < boundary:
                return i
        return len(boundaries)

    def find_thematic_clusters(
        self,
        repetitions: List[SemanticRepetition],
        cluster_threshold: float = 0.6
    ) -> List[List[SemanticRepetition]]:
        """Agrupa repeticiones que comparten tema común."""
        if not repetitions:
            return []

        # Clustering simple basado en oraciones compartidas
        clusters: List[List[SemanticRepetition]] = []

        for rep in repetitions:
            added = False
            for cluster in clusters:
                # Ver si comparte oración con alguna del cluster
                for existing in cluster:
                    if (rep.sentence1 == existing.sentence1 or
                        rep.sentence1 == existing.sentence2 or
                        rep.sentence2 == existing.sentence1 or
                        rep.sentence2 == existing.sentence2):
                        cluster.append(rep)
                        added = True
                        break
                if added:
                    break

            if not added:
                clusters.append([rep])

        return clusters

    def generate_report(
        self,
        repetitions: List[SemanticRepetition]
    ) -> str:
        """Genera reporte legible de repeticiones."""
        if not repetitions:
            return "No se detectaron repeticiones semánticas significativas."

        lines = [
            f"# Repeticiones Semánticas Detectadas: {len(repetitions)}",
            ""
        ]

        for i, rep in enumerate(repetitions[:20], 1):  # Top 20
            lines.extend([
                f"## {i}. Similitud: {rep.similarity:.1%}",
                f"**Distancia:** {rep.distance_sentences} oraciones",
                "",
                f"> \"{rep.sentence1[:100]}...\"" if len(rep.sentence1) > 100 else f"> \"{rep.sentence1}\"",
                "",
                f"> \"{rep.sentence2[:100]}...\"" if len(rep.sentence2) > 100 else f"> \"{rep.sentence2}\"",
                "",
                "---",
                ""
            ])

        return "\n".join(lines)
```

---

## Consideraciones de Rendimiento

⚠️ **Este STEP es computacionalmente intensivo.**

- Para novelas largas (100k+ palabras), puede haber 5000+ oraciones
- Comparar todas las combinaciones: O(n²)
- **Optimizaciones aplicadas:**
  - Solo comparar oraciones dentro de ventana de distancia
  - Procesamiento por lotes de embeddings
  - Normalización previa para similitud coseno eficiente

---

## Criterio de DONE

```python
from narrative_assistant.analysis import SemanticRepetitionDetector, SemanticConfig

detector = SemanticRepetitionDetector(
    config=SemanticConfig(similarity_threshold=0.7)
)

text = """
El anciano caminaba lentamente por el sendero del bosque.
Los pájaros cantaban entre las ramas de los árboles.
El viejo avanzaba despacio por el camino del monte.
Las hojas crujían bajo sus pies cansados.
"""

repetitions = detector.detect(text)

# Debe detectar similitud entre "anciano caminaba lentamente" y "viejo avanzaba despacio"
assert len(repetitions) >= 1
assert repetitions[0].similarity > 0.7

print(f"✅ Detectadas {len(repetitions)} repeticiones semánticas")
print(detector.generate_report(repetitions))
```

---

## Siguiente

[STEP 4.1: Marcadores Temporales](../phase-4/step-4.1-temporal-markers.md)
