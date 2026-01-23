# STEP 10.2: Ritmo y Pacing de Capítulos

> **Fase**: 10 - Análisis Narrativo Avanzado (Post-MVP)
> **Complejidad**: L (6-8 horas)
> **Prioridad**: P3
> **Dependencias**: STEP 3.1 (Structure Detector), STEP 8.1 (Sentiment Analysis)

---

## Descripción

Sistema para analizar el ritmo narrativo de cada capítulo. Detecta problemas de pacing como capítulos demasiado lentos, picos de acción mal distribuidos, o transiciones bruscas entre ritmos.

---

## Objetivos

1. Calcular métricas de ritmo para cada capítulo
2. Detectar anomalías de pacing (muy lento, muy rápido, inconsistente)
3. Visualizar curva de tensión narrativa
4. Generar alertas por problemas de ritmo

---

## Conceptos de Pacing

### Elementos que aceleran el ritmo
- Diálogos cortos y rápidos
- Acciones físicas
- Frases cortas
- Escenas de conflicto/tensión
- Revelaciones

### Elementos que ralentizan el ritmo
- Descripciones largas
- Monólogos internos extensos
- Exposición/worldbuilding
- Escenas contemplativas
- Flashbacks

---

## Modelo de Datos

```python
@dataclass
class PacingMetrics:
    """Métricas de ritmo de un capítulo."""
    chapter_index: int
    chapter_title: str

    # Métricas básicas
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    avg_paragraph_length: float

    # Composición
    dialogue_percentage: float       # % de texto en diálogos
    description_percentage: float    # % de descripciones
    action_percentage: float         # % de acciones
    introspection_percentage: float  # % de pensamientos internos

    # Ritmo
    scene_count: int
    scene_changes: int               # Cambios de escena
    time_jumps: int                  # Saltos temporales
    pov_changes: int                 # Cambios de POV

    # Tensión (requiere STEP 8.1)
    tension_start: float             # Tensión al inicio (0-1)
    tension_peak: float              # Pico de tensión
    tension_end: float               # Tensión al final
    tension_curve: list[float]       # Curva de tensión


@dataclass
class PacingScore:
    """Evaluación del pacing de un capítulo."""
    chapter_index: int
    metrics: PacingMetrics

    # Scores (0-100)
    pace_score: float                # Velocidad general
    variance_score: float            # Variedad de ritmo
    flow_score: float                # Fluidez de lectura
    overall_score: float

    # Clasificación
    pace_type: PaceType

    # Problemas
    issues: list[PacingIssue]
    suggestions: list[str]


class PaceType(Enum):
    VERY_SLOW = "very_slow"          # Contemplativo, descriptivo
    SLOW = "slow"                    # Pausado, reflexivo
    MODERATE = "moderate"            # Equilibrado
    FAST = "fast"                    # Dinámico
    VERY_FAST = "very_fast"          # Frenético, acción pura


@dataclass
class PacingIssue:
    """Problema de pacing detectado."""
    code: str
    description: str
    severity: str
    location: str                    # "chapter", "scene", "transition"
    suggestion: str
```

---

## Componentes

### 1. PacingAnalyzer

```python
class PacingAnalyzer:
    """Analiza el ritmo de capítulos."""

    def calculate_metrics(self, chapter: Chapter) -> PacingMetrics:
        """Calcula métricas de ritmo."""
        text = chapter.full_text

        # Métricas básicas
        sentences = self._split_sentences(text)
        paragraphs = self._split_paragraphs(text)

        # Composición
        dialogue_pct = self._calculate_dialogue_percentage(text)
        description_pct = self._calculate_description_percentage(text)

        # Tensión (si disponible)
        tension_curve = self._calculate_tension_curve(text)

        return PacingMetrics(
            chapter_index=chapter.index,
            word_count=len(text.split()),
            sentence_count=len(sentences),
            avg_sentence_length=sum(len(s.split()) for s in sentences) / len(sentences),
            dialogue_percentage=dialogue_pct,
            # ...
        )

    def _calculate_dialogue_percentage(self, text: str) -> float:
        """Calcula porcentaje de texto en diálogos."""
        # Detectar texto entre comillas/guiones de diálogo
        dialogue_patterns = [
            r'[""«»].*?[""«»]',           # Comillas
            r'—.*?(?=\n|—|$)',            # Guión largo
        ]
        ...

    def _calculate_tension_curve(self, text: str) -> list[float]:
        """Genera curva de tensión por segmentos."""
        # Dividir en segmentos
        segments = self._split_into_segments(text, n=10)

        # Analizar tensión de cada segmento
        tension_values = []
        for segment in segments:
            tension = self._estimate_tension(segment)
            tension_values.append(tension)

        return tension_values

    def _estimate_tension(self, text: str) -> float:
        """Estima tensión de un fragmento."""
        score = 0.5  # Base neutral

        # Indicadores de alta tensión
        action_words = ["corrió", "gritó", "atacó", "escapó", "murió"]
        conflict_words = ["pero", "sin embargo", "aunque", "a pesar de"]

        # Indicadores de baja tensión
        calm_words = ["tranquilamente", "pausadamente", "en silencio"]
        description_markers = ["era", "tenía", "parecía", "había"]

        # Ajustar score
        for word in action_words:
            if word in text.lower():
                score += 0.1
        # ...

        return min(1.0, max(0.0, score))
```

### 2. PaceClassifier

```python
class PaceClassifier:
    """Clasifica el tipo de ritmo."""

    def classify(self, metrics: PacingMetrics) -> PaceType:
        """Clasifica el ritmo del capítulo."""
        # Factores que aceleran
        fast_factors = (
            metrics.dialogue_percentage * 0.3 +
            metrics.action_percentage * 0.4 +
            (1 / metrics.avg_sentence_length) * 10 * 0.3
        )

        # Factores que ralentizan
        slow_factors = (
            metrics.description_percentage * 0.4 +
            metrics.introspection_percentage * 0.3 +
            metrics.avg_paragraph_length / 100 * 0.3
        )

        pace_score = fast_factors - slow_factors

        if pace_score < -0.3:
            return PaceType.VERY_SLOW
        elif pace_score < -0.1:
            return PaceType.SLOW
        elif pace_score < 0.1:
            return PaceType.MODERATE
        elif pace_score < 0.3:
            return PaceType.FAST
        else:
            return PaceType.VERY_FAST
```

### 3. PacingIssueDetector

```python
class PacingIssueDetector:
    """Detecta problemas de pacing."""

    def detect_issues(
        self,
        chapter_scores: list[PacingScore]
    ) -> list[PacingIssue]:
        """Detecta problemas en la secuencia de capítulos."""
        issues = []

        # Detectar capítulos anómalos
        for score in chapter_scores:
            issues.extend(self._check_individual_chapter(score))

        # Detectar problemas de secuencia
        issues.extend(self._check_sequence(chapter_scores))

        return issues

    def _check_individual_chapter(self, score: PacingScore) -> list[PacingIssue]:
        """Problemas en un capítulo individual."""
        issues = []

        # Capítulo muy largo sin variación
        if score.metrics.word_count > 5000 and score.variance_score < 20:
            issues.append(PacingIssue(
                code="PACE_MONOTONOUS",
                description=f"Capítulo {score.chapter_index} es largo y monótono",
                severity="warning",
                location="chapter",
                suggestion="Considerar añadir variación de ritmo o dividir el capítulo"
            ))

        # Todo acción sin respiro
        if score.pace_type == PaceType.VERY_FAST and score.metrics.word_count > 3000:
            issues.append(PacingIssue(
                code="PACE_EXHAUSTING",
                description=f"Capítulo {score.chapter_index} es acción constante sin pausas",
                severity="info",
                location="chapter",
                suggestion="Añadir momentos de pausa para que el lector respire"
            ))

        return issues

    def _check_sequence(self, scores: list[PacingScore]) -> list[PacingIssue]:
        """Problemas en la secuencia de capítulos."""
        issues = []

        # Cambio brusco de ritmo
        for i in range(1, len(scores)):
            prev = scores[i-1]
            curr = scores[i]

            pace_diff = abs(prev.pace_score - curr.pace_score)
            if pace_diff > 50:  # Cambio de >50 puntos
                issues.append(PacingIssue(
                    code="PACE_JARRING_TRANSITION",
                    description=f"Transición brusca entre caps {prev.chapter_index} y {curr.chapter_index}",
                    severity="warning",
                    location="transition",
                    suggestion="Suavizar la transición con una escena puente"
                ))

        # Muchos capítulos lentos seguidos
        slow_streak = 0
        for score in scores:
            if score.pace_type in [PaceType.VERY_SLOW, PaceType.SLOW]:
                slow_streak += 1
            else:
                slow_streak = 0

            if slow_streak >= 3:
                issues.append(PacingIssue(
                    code="PACE_SAGGING_MIDDLE",
                    description=f"Tres o más capítulos lentos consecutivos",
                    severity="warning",
                    location="sequence",
                    suggestion="El ritmo puede estar decayendo, considerar añadir acción"
                ))
                break

        return issues
```

---

## Alertas Generadas

| Código | Descripción | Severidad |
|--------|-------------|-----------|
| `PACE_MONOTONOUS` | Capítulo largo sin variación de ritmo | Warning |
| `PACE_EXHAUSTING` | Acción constante sin pausas | Info |
| `PACE_JARRING_TRANSITION` | Cambio brusco entre capítulos | Warning |
| `PACE_SAGGING_MIDDLE` | Varios capítulos lentos seguidos | Warning |
| `PACE_RUSHED_CLIMAX` | Clímax demasiado corto | Warning |
| `PACE_SLOW_START` | Inicio muy lento | Info |
| `PACE_ANTICLIMACTIC` | Tensión decae antes del final | Warning |

---

## Visualización

### Curva de Tensión

```
Tensión
  1.0 |                    *
      |                   / \
  0.8 |                  /   \
      |       *--*      /     \
  0.6 |      /    \    /       \
      |     /      \  /         \
  0.4 |    /        \/           \
      |   /                       \--*
  0.2 |  /
      | *
  0.0 +--------------------------------
      Cap1  Cap2  Cap3  Cap4  Cap5  Cap6

Leyenda:
* = Pico de tensión
/ = Subida de tensión
\ = Bajada de tensión
```

### Mapa de Calor de Ritmo

```
Cap 1: [████████░░] SLOW (descripción del mundo)
Cap 2: [██████░░░░] MODERATE (introducción personajes)
Cap 3: [████░░░░░░] FAST (primer conflicto)
Cap 4: [██░░░░░░░░] VERY_FAST (acción)
Cap 5: [██████████] VERY_SLOW (recuperación)  ⚠️ Contraste brusco
Cap 6: [████████░░] SLOW (desarrollo)
```

---

## Criterios de Aceptación

- [ ] Cálculo de métricas básicas (longitud, diálogos, descripciones)
- [ ] Clasificación de tipo de ritmo
- [ ] Detección de anomalías individuales
- [ ] Detección de problemas de secuencia
- [ ] Curva de tensión básica (sin sentimiento)
- [ ] Alertas con sugerencias útiles

---

## Notas de Implementación

- Empezar con métricas sintácticas (longitud de frases, párrafos)
- La detección de diálogos es relativamente sencilla
- La curva de tensión mejora significativamente con STEP 8.1
- El género afecta las expectativas: thriller vs romance tienen ritmos distintos
- Permitir configurar preferencias de género

---

## Referencias

- [Structure Detector](../phase-3/step-3.1-structure-detector.md)
- [Sentiment Analysis](../phase-8/step-8.1-sentiment-analysis.md)
- [Chapter Detection](../phase-3/step-3.1-structure-detector.md)
