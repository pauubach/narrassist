# STEP 8.2: Coherencia Emocional

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (8-10 horas) |
| **Prioridad** | P2 (Post-MVP) |
| **Prerequisitos** | STEP 8.1 |

---

## Descripción

Verificar que el comportamiento comunicativo de los personajes sea coherente con su estado emocional declarado, detectando inconsistencias entre lo que el narrador dice que siente un personaje y cómo ese personaje se expresa.

---

## Tipos de Coherencia a Verificar

### 1. Emoción-Diálogo

El tono del diálogo debe ser coherente con el estado emocional declarado.

| Estado declarado | Diálogo esperado |
|------------------|------------------|
| Enfadado/furioso | Negativo, agresivo, cortante |
| Triste/devastado | Negativo, breve, pausado |
| Feliz/eufórico | Positivo, extenso, entusiasta |
| Asustado/aterrado | Negativo, entrecortado, breve |
| Tranquilo/sereno | Neutro, pausado, reflexivo |

### 2. Emoción-Acción

Las acciones deben ser coherentes con el estado emocional.

```
❌ "Estaba paralizada por el miedo. Avanzó decidida hacia el dragón."
✅ "Estaba paralizada por el miedo. Sus piernas temblaban."
```

### 3. Evolución Temporal

Los cambios emocionales deben ser graduales o estar justificados.

```
❌ Cap 1: "Sumido en la más profunda depresión"
   Cap 2 (mismo día): "Reía a carcajadas"

✅ Cap 1: "Sumido en la más profunda depresión"
   Cap 2: "Tres meses después, empezaba a sonreír de nuevo"
```

---

## Outputs

- `src/narrative_assistant/analysis/emotional_coherence.py`
- Alertas de inconsistencia emocional
- Sugerencias de corrección

---

## Arquitectura Propuesta

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class IncoherenceType(Enum):
    EMOTION_DIALOGUE = "emotion_dialogue"  # Estado vs. cómo habla
    EMOTION_ACTION = "emotion_action"      # Estado vs. qué hace
    TEMPORAL_JUMP = "temporal_jump"        # Cambio emocional abrupto
    NARRATOR_BIAS = "narrator_bias"        # Narrador inconsistente

@dataclass
class EmotionalIncoherence:
    """Incoherencia emocional detectada."""
    entity_name: str
    incoherence_type: IncoherenceType
    declared_emotion: str
    actual_behavior: str
    declared_text: str
    behavior_text: str
    chapter_id: Optional[int]
    confidence: float
    explanation: str
    suggestion: Optional[str]

class EmotionalCoherenceChecker:
    def __init__(
        self,
        sentiment_analyzer,  # De STEP 8.1
        min_confidence: float = 0.6,
    ):
        self.sentiment = sentiment_analyzer
        self.min_confidence = min_confidence

    def check_dialogue_coherence(
        self,
        entity_name: str,
        declared_emotion: str,
        dialogue_text: str,
        context: str,
    ) -> Optional[EmotionalIncoherence]:
        """
        Verifica coherencia entre emoción declarada y diálogo.

        Args:
            entity_name: Nombre del personaje
            declared_emotion: Emoción declarada ("furioso", "triste")
            dialogue_text: Lo que dice el personaje
            context: Texto circundante

        Returns:
            EmotionalIncoherence si hay inconsistencia, None si es coherente
        """
        # Analizar sentimiento del diálogo
        dialogue_sentiment = self.sentiment.analyze_dialogue(
            dialogue_text, entity_name, context
        )

        # Mapear emoción declarada a sentimiento esperado
        expected_sentiment = self._emotion_to_expected_sentiment(declared_emotion)

        # Verificar coherencia
        if not self._is_coherent(expected_sentiment, dialogue_sentiment.sentiment):
            return EmotionalIncoherence(
                entity_name=entity_name,
                incoherence_type=IncoherenceType.EMOTION_DIALOGUE,
                declared_emotion=declared_emotion,
                actual_behavior=f"{dialogue_sentiment.sentiment.value} ({dialogue_sentiment.primary_emotion.value})",
                declared_text=context,
                behavior_text=dialogue_text,
                confidence=dialogue_sentiment.sentiment_confidence,
                explanation=self._generate_explanation(
                    entity_name, declared_emotion, dialogue_sentiment
                ),
                suggestion=self._generate_suggestion(
                    entity_name, declared_emotion, dialogue_sentiment
                ),
            )

        return None

    def _emotion_to_expected_sentiment(self, emotion: str) -> set[str]:
        """Mapea emoción a sentimientos esperados."""
        EMOTION_SENTIMENT_MAP = {
            # Emociones negativas → diálogo negativo o neutro
            "furioso": {"negative"},
            "enfadado": {"negative"},
            "triste": {"negative", "neutral"},
            "devastado": {"negative"},
            "asustado": {"negative", "neutral"},
            "aterrado": {"negative"},
            "preocupado": {"negative", "neutral"},
            "ansioso": {"negative", "neutral"},
            # Emociones positivas → diálogo positivo
            "feliz": {"positive"},
            "eufórico": {"positive"},
            "contento": {"positive", "neutral"},
            "aliviado": {"positive", "neutral"},
            "emocionado": {"positive"},
            # Emociones neutras → cualquier tono
            "tranquilo": {"neutral", "positive"},
            "sereno": {"neutral", "positive"},
            "pensativo": {"neutral"},
            "reflexivo": {"neutral"},
        }
        return EMOTION_SENTIMENT_MAP.get(emotion.lower(), {"neutral"})

    def _is_coherent(
        self,
        expected: set[str],
        actual: "Sentiment"
    ) -> bool:
        """Verifica si el sentimiento actual es coherente con lo esperado."""
        return actual.value in expected

    def check_temporal_evolution(
        self,
        entity_name: str,
        emotional_states: list[tuple[int, str, str]],  # (chapter, emotion, text)
    ) -> list[EmotionalIncoherence]:
        """
        Verifica que la evolución emocional sea coherente temporalmente.

        Detecta cambios emocionales extremos sin justificación temporal.
        """
        incoherences = []

        for i in range(1, len(emotional_states)):
            prev_chapter, prev_emotion, prev_text = emotional_states[i-1]
            curr_chapter, curr_emotion, curr_text = emotional_states[i]

            # Si son capítulos consecutivos y hay cambio extremo
            if curr_chapter == prev_chapter + 1:
                if self._is_extreme_change(prev_emotion, curr_emotion):
                    incoherences.append(EmotionalIncoherence(
                        entity_name=entity_name,
                        incoherence_type=IncoherenceType.TEMPORAL_JUMP,
                        declared_emotion=prev_emotion,
                        actual_behavior=curr_emotion,
                        declared_text=prev_text,
                        behavior_text=curr_text,
                        chapter_id=curr_chapter,
                        confidence=0.7,
                        explanation=(
                            f"'{entity_name}' cambia de '{prev_emotion}' a '{curr_emotion}' "
                            f"entre capítulos consecutivos sin transición aparente."
                        ),
                        suggestion=(
                            f"Considere añadir una transición temporal o emocional "
                            f"que justifique el cambio de estado de '{entity_name}'."
                        ),
                    ))

        return incoherences

    def _is_extreme_change(self, emotion1: str, emotion2: str) -> bool:
        """Detecta cambios emocionales extremos."""
        OPPOSITES = {
            ("furioso", "tranquilo"),
            ("devastado", "eufórico"),
            ("aterrado", "sereno"),
            ("deprimido", "feliz"),
            ("desesperado", "esperanzado"),
        }
        pair = (emotion1.lower(), emotion2.lower())
        reverse = (emotion2.lower(), emotion1.lower())
        return pair in OPPOSITES or reverse in OPPOSITES
```

---

## Integración con el Sistema de Alertas

```python
# En phase-7/alert_engine.py

from narrative_assistant.analysis.emotional_coherence import (
    EmotionalCoherenceChecker,
    IncoherenceType,
)

def generate_emotional_alerts(checker, entities, dialogues):
    """Genera alertas de coherencia emocional."""
    alerts = []

    for entity in entities:
        # Obtener estados emocionales declarados
        declared_emotions = get_declared_emotions(entity)

        # Obtener diálogos del personaje
        entity_dialogues = get_dialogues_by_speaker(entity.name, dialogues)

        for emotion_state, dialogue in match_emotions_to_dialogues(
            declared_emotions, entity_dialogues
        ):
            incoherence = checker.check_dialogue_coherence(
                entity_name=entity.name,
                declared_emotion=emotion_state.value,
                dialogue_text=dialogue.text,
                context=dialogue.context,
            )

            if incoherence:
                alerts.append(Alert(
                    type=AlertType.EMOTIONAL_INCOHERENCE,
                    severity=AlertSeverity.WARNING,
                    entity=entity.name,
                    message=incoherence.explanation,
                    suggestion=incoherence.suggestion,
                    location=AlertLocation(
                        chapter=incoherence.chapter_id,
                        start_char=dialogue.start_char,
                    ),
                ))

    return alerts
```

---

## Casos Especiales

### 1. Ironía/Sarcasmo

Cuando el personaje dice lo contrario de lo que siente intencionalmente:

```python
# Detectar marcadores de ironía
IRONY_MARKERS = [
    "—dijo con ironía",
    "—respondió sarcástico",
    "—añadió con sorna",
]
```

### 2. Disimulo intencional

Cuando el personaje oculta sus emociones:

```python
# Detectar disimulo
CONCEALMENT_MARKERS = [
    "ocultando su",
    "fingiendo",
    "aparentando",
    "disfrazando su",
]
```

### 3. Personajes complejos

Algunos personajes tienen rasgos que permiten incoherencias:
- Psicópatas (sin empatía, emociones superficiales)
- Espías (entrenados para disimular)
- Actores (pueden fingir cualquier emoción)

---

## Criterio de DONE

```python
from narrative_assistant.analysis.emotional_coherence import (
    EmotionalCoherenceChecker,
    IncoherenceType,
)

checker = EmotionalCoherenceChecker(sentiment_analyzer)

# Test: personaje furioso hablando amablemente
result = checker.check_dialogue_coherence(
    entity_name="Juan",
    declared_emotion="furioso",
    dialogue_text="Claro, no hay ningún problema. Adelante.",
    context="Juan estaba furioso con María."
)

assert result is not None
assert result.incoherence_type == IncoherenceType.EMOTION_DIALOGUE
assert "furioso" in result.explanation

print("✅ Coherencia emocional funcionando")
```

---

## Referencias

- Ekman, P. (1992). "An argument for basic emotions"
- Plutchik, R. (2001). "The nature of emotions"
- Mohammad, S. (2016). "Sentiment Analysis: Detecting Valence, Emotions, and Other Affectual States from Text"

---

## Siguiente

Esta fase es post-MVP. Ver [Roadmap](../../README.md) para más información.
