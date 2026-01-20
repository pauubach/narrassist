"""
Verificación de Coherencia Emocional.

Verifica que el comportamiento comunicativo de los personajes
sea coherente con su estado emocional declarado, detectando
inconsistencias entre lo que el narrador dice que siente un
personaje y cómo ese personaje se expresa.

Tipos de coherencia verificados:
- Emoción-Diálogo: Tono del diálogo vs. estado declarado
- Emoción-Acción: Acciones vs. estado emocional
- Evolución Temporal: Cambios emocionales graduales
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..nlp.sentiment import (
    SentimentAnalyzer,
    EmotionalState,
    DeclaredEmotionalState,
    Sentiment,
    Emotion,
    get_sentiment_analyzer,
)

logger = logging.getLogger(__name__)


class IncoherenceType(Enum):
    """Tipos de incoherencia emocional."""
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
    confidence: float
    explanation: str
    suggestion: Optional[str] = None
    chapter_id: Optional[int] = None
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "entity_name": self.entity_name,
            "incoherence_type": self.incoherence_type.value,
            "declared_emotion": self.declared_emotion,
            "actual_behavior": self.actual_behavior,
            "declared_text": self.declared_text,
            "behavior_text": self.behavior_text,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "chapter_id": self.chapter_id,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


# Mapeo de emociones a sentimientos esperados
EMOTION_SENTIMENT_MAP: dict[str, set[str]] = {
    # Emociones negativas → diálogo negativo o neutro
    "furioso": {"negative"},
    "enfadado": {"negative"},
    "enojado": {"negative"},
    "iracundo": {"negative"},
    "rabioso": {"negative"},
    "triste": {"negative", "neutral"},
    "devastado": {"negative"},
    "deprimido": {"negative"},
    "abatido": {"negative"},
    "melancólico": {"negative", "neutral"},
    "asustado": {"negative", "neutral"},
    "aterrado": {"negative"},
    "temeroso": {"negative", "neutral"},
    "miedoso": {"negative"},
    "horrorizado": {"negative"},
    "preocupado": {"negative", "neutral"},
    "ansioso": {"negative", "neutral"},
    "nervioso": {"negative", "neutral"},
    "angustiado": {"negative"},
    "desesperado": {"negative"},
    "asqueado": {"negative"},
    "disgustado": {"negative"},
    # Emociones positivas → diálogo positivo
    "feliz": {"positive"},
    "eufórico": {"positive"},
    "contento": {"positive", "neutral"},
    "alegre": {"positive"},
    "dichoso": {"positive"},
    "radiante": {"positive"},
    "entusiasmado": {"positive"},
    "emocionado": {"positive"},
    "aliviado": {"positive", "neutral"},
    "satisfecho": {"positive", "neutral"},
    "esperanzado": {"positive", "neutral"},
    # Emociones neutras → cualquier tono
    "tranquilo": {"neutral", "positive"},
    "sereno": {"neutral", "positive"},
    "calmado": {"neutral", "positive"},
    "pensativo": {"neutral"},
    "reflexivo": {"neutral"},
    "indiferente": {"neutral"},
}

# Pares de emociones opuestas (cambios extremos)
OPPOSITE_EMOTIONS: set[tuple[str, str]] = {
    ("furioso", "tranquilo"),
    ("furioso", "sereno"),
    ("furioso", "calmado"),
    ("devastado", "eufórico"),
    ("devastado", "feliz"),
    ("deprimido", "eufórico"),
    ("deprimido", "feliz"),
    ("aterrado", "sereno"),
    ("aterrado", "tranquilo"),
    ("desesperado", "esperanzado"),
    ("triste", "alegre"),
    ("triste", "feliz"),
    ("angustiado", "sereno"),
}

# Marcadores de ironía/sarcasmo
IRONY_MARKERS = [
    r"(?:dijo|respondió|añadió|comentó)\s+con\s+ironía",
    r"(?:dijo|respondió|añadió|comentó)\s+sarcástic[oa]",
    r"(?:dijo|respondió|añadió|comentó)\s+con\s+sorna",
    r"(?:dijo|respondió|añadió|comentó)\s+burlón",
    r"(?:dijo|respondió|añadió|comentó)\s+mordaz",
    r"con\s+(?:evidente|clara)\s+ironía",
    r"en\s+tono\s+(?:irónico|sarcástico|burlón)",
]

# Marcadores de disimulo/fingimiento
CONCEALMENT_MARKERS = [
    r"ocultando\s+su\s+\w+",
    r"fingiendo\s+\w+",
    r"aparentando\s+\w+",
    r"disfrazando\s+su\s+\w+",
    r"disimulando\s+su\s+\w+",
    r"escondiendo\s+su\s+\w+",
    r"con\s+(?:falsa|forzada)\s+\w+",
    r"intentando\s+parecer\s+\w+",
    r"haciendo\s+un\s+esfuerzo\s+por\s+\w+",
]


class EmotionalCoherenceChecker:
    """
    Verificador de coherencia emocional.

    Detecta inconsistencias entre estados emocionales declarados
    y el comportamiento comunicativo de los personajes.
    """

    def __init__(
        self,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        min_confidence: float = 0.6,
    ):
        """
        Inicializa el verificador.

        Args:
            sentiment_analyzer: Analizador de sentimiento (usa singleton si None)
            min_confidence: Confianza mínima para reportar incoherencia
        """
        self.sentiment = sentiment_analyzer or get_sentiment_analyzer()
        self.min_confidence = min_confidence

        # Compilar patrones de regex
        self._irony_patterns = [re.compile(p, re.IGNORECASE) for p in IRONY_MARKERS]
        self._concealment_patterns = [re.compile(p, re.IGNORECASE) for p in CONCEALMENT_MARKERS]

    def _has_irony_marker(self, text: str) -> bool:
        """Detecta si hay marcadores de ironía en el texto."""
        for pattern in self._irony_patterns:
            if pattern.search(text):
                return True
        return False

    def _has_concealment_marker(self, text: str) -> bool:
        """Detecta si hay marcadores de disimulo en el texto."""
        for pattern in self._concealment_patterns:
            if pattern.search(text):
                return True
        return False

    def _emotion_to_expected_sentiment(self, emotion: str) -> set[str]:
        """
        Mapea emoción declarada a sentimientos esperados.

        Args:
            emotion: Emoción declarada (ej: "furioso", "triste")

        Returns:
            Conjunto de sentimientos esperados
        """
        return EMOTION_SENTIMENT_MAP.get(emotion.lower(), {"neutral"})

    def _is_coherent(
        self,
        expected_sentiments: set[str],
        actual_sentiment: Sentiment
    ) -> bool:
        """Verifica si el sentimiento actual es coherente con lo esperado."""
        return actual_sentiment.value in expected_sentiments

    def _is_extreme_change(self, emotion1: str, emotion2: str) -> bool:
        """
        Detecta si hay un cambio emocional extremo entre dos emociones.

        Args:
            emotion1: Primera emoción
            emotion2: Segunda emoción

        Returns:
            True si el cambio es extremo
        """
        pair = (emotion1.lower(), emotion2.lower())
        reverse = (emotion2.lower(), emotion1.lower())
        return pair in OPPOSITE_EMOTIONS or reverse in OPPOSITE_EMOTIONS

    def _generate_explanation(
        self,
        entity_name: str,
        declared_emotion: str,
        detected_state: EmotionalState
    ) -> str:
        """Genera explicación de la incoherencia."""
        return (
            f"'{entity_name}' está descrito como '{declared_emotion}', "
            f"pero su diálogo tiene un tono {detected_state.sentiment.value} "
            f"con emoción predominante '{detected_state.primary_emotion.value}'. "
            f"Esto podría ser una inconsistencia no intencional, o bien "
            f"indicar autocontrol, ironía o disimulo del personaje."
        )

    def _generate_suggestion(
        self,
        entity_name: str,
        declared_emotion: str,
        detected_state: EmotionalState
    ) -> str:
        """Genera sugerencia de corrección."""
        expected = self._emotion_to_expected_sentiment(declared_emotion)
        expected_str = "/".join(expected)

        if detected_state.sentiment == Sentiment.POSITIVE and "negative" in expected:
            return (
                f"Si '{entity_name}' realmente está '{declared_emotion}', "
                f"considere ajustar el diálogo para que sea más {expected_str}, "
                f"o añadir una explicación (ironía, disimulo, etc.)."
            )
        elif detected_state.sentiment == Sentiment.NEGATIVE and "positive" in expected:
            return (
                f"Si '{entity_name}' está '{declared_emotion}', "
                f"el diálogo debería reflejar un tono más {expected_str}, "
                f"o justificar por qué habla de forma negativa."
            )
        else:
            return (
                f"Revise si el tono del diálogo de '{entity_name}' "
                f"es coherente con su estado emocional declarado."
            )

    def check_dialogue_coherence(
        self,
        entity_name: str,
        declared_emotion: str,
        dialogue_text: str,
        context: str = "",
        chapter_id: Optional[int] = None,
        start_char: int = 0,
        end_char: int = 0,
    ) -> Optional[EmotionalIncoherence]:
        """
        Verifica coherencia entre emoción declarada y diálogo.

        Args:
            entity_name: Nombre del personaje
            declared_emotion: Emoción declarada ("furioso", "triste")
            dialogue_text: Lo que dice el personaje
            context: Texto circundante
            chapter_id: ID del capítulo
            start_char: Posición inicial
            end_char: Posición final

        Returns:
            EmotionalIncoherence si hay inconsistencia, None si es coherente
        """
        # Verificar marcadores de ironía/disimulo en el contexto
        full_context = f"{context} {dialogue_text}"
        if self._has_irony_marker(full_context):
            logger.debug(f"Ironía detectada para {entity_name}, ignorando incoherencia")
            return None

        if self._has_concealment_marker(context):
            logger.debug(f"Disimulo detectado para {entity_name}, ignorando incoherencia")
            return None

        # Analizar sentimiento del diálogo
        result = self.sentiment.analyze_dialogue(
            dialogue_text=dialogue_text,
            speaker=entity_name,
            context_before=context,
            chapter_id=chapter_id,
            start_char=start_char,
            end_char=end_char,
        )

        if not result.is_success:
            logger.warning(f"No se pudo analizar diálogo de {entity_name}")
            return None

        dialogue_sentiment = result.value

        # Verificar confianza mínima
        if dialogue_sentiment.sentiment_confidence < self.min_confidence:
            logger.debug(f"Confianza baja ({dialogue_sentiment.sentiment_confidence:.2f}), ignorando")
            return None

        # Mapear emoción declarada a sentimiento esperado
        expected_sentiments = self._emotion_to_expected_sentiment(declared_emotion)

        # Verificar coherencia
        if not self._is_coherent(expected_sentiments, dialogue_sentiment.sentiment):
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
                chapter_id=chapter_id,
                start_char=start_char,
                end_char=end_char,
            )

        return None

    def check_temporal_evolution(
        self,
        entity_name: str,
        emotional_states: list[tuple[int, str, str]],  # (chapter, emotion, text)
    ) -> list[EmotionalIncoherence]:
        """
        Verifica que la evolución emocional sea coherente temporalmente.

        Detecta cambios emocionales extremos sin justificación temporal.

        Args:
            entity_name: Nombre del personaje
            emotional_states: Lista de (capítulo, emoción, texto)

        Returns:
            Lista de incoherencias detectadas
        """
        incoherences = []

        if len(emotional_states) < 2:
            return incoherences

        # Ordenar por capítulo
        sorted_states = sorted(emotional_states, key=lambda x: x[0])

        for i in range(1, len(sorted_states)):
            prev_chapter, prev_emotion, prev_text = sorted_states[i - 1]
            curr_chapter, curr_emotion, curr_text = sorted_states[i]

            # Si son capítulos consecutivos y hay cambio extremo
            if curr_chapter == prev_chapter + 1:
                if self._is_extreme_change(prev_emotion, curr_emotion):
                    incoherences.append(EmotionalIncoherence(
                        entity_name=entity_name,
                        incoherence_type=IncoherenceType.TEMPORAL_JUMP,
                        declared_emotion=prev_emotion,
                        actual_behavior=curr_emotion,
                        declared_text=prev_text[:200] if len(prev_text) > 200 else prev_text,
                        behavior_text=curr_text[:200] if len(curr_text) > 200 else curr_text,
                        chapter_id=curr_chapter,
                        confidence=0.7,
                        explanation=(
                            f"'{entity_name}' cambia de '{prev_emotion}' "
                            f"(capítulo {prev_chapter}) a '{curr_emotion}' "
                            f"(capítulo {curr_chapter}) sin transición aparente."
                        ),
                        suggestion=(
                            f"Considere añadir una transición temporal o emocional "
                            f"que justifique el cambio de estado de '{entity_name}'. "
                            f"Por ejemplo, un salto temporal explícito o eventos "
                            f"que expliquen la evolución emocional."
                        ),
                    ))

        return incoherences

    def check_action_coherence(
        self,
        entity_name: str,
        declared_emotion: str,
        action_text: str,
        context: str = "",
        chapter_id: Optional[int] = None,
    ) -> Optional[EmotionalIncoherence]:
        """
        Verifica coherencia entre emoción declarada y acciones.

        Args:
            entity_name: Nombre del personaje
            declared_emotion: Emoción declarada
            action_text: Descripción de la acción
            context: Contexto circundante
            chapter_id: ID del capítulo

        Returns:
            EmotionalIncoherence si hay inconsistencia
        """
        # Patrones de acción incompatibles con emociones
        INCOMPATIBLE_ACTIONS = {
            # Miedo/terror + acciones valientes
            "aterrado": [
                r"avanzó\s+(?:decidid[oa]|valiente)",
                r"se\s+enfrentó",
                r"atacó\s+sin\s+dudar",
                r"corrió\s+hacia",
            ],
            "paralizado": [
                r"(?:corrió|saltó|avanzó)\s+\w+",
                r"se\s+movió\s+(?:rápido|veloz)",
            ],
            # Devastado + acciones energéticas
            "devastado": [
                r"reía\s+a\s+carcajadas",
                r"saltaba\s+de\s+alegría",
                r"bailaba",
            ],
            # Furioso + acciones pacíficas
            "furioso": [
                r"sonrió\s+(?:amable|dulce)",
                r"acarició\s+(?:suave|tierna)",
                r"abrazó\s+(?:con\s+cariño|cariñosa)",
            ],
        }

        emotion_lower = declared_emotion.lower()
        if emotion_lower not in INCOMPATIBLE_ACTIONS:
            return None

        action_lower = action_text.lower()
        patterns = INCOMPATIBLE_ACTIONS[emotion_lower]

        for pattern in patterns:
            if re.search(pattern, action_lower):
                return EmotionalIncoherence(
                    entity_name=entity_name,
                    incoherence_type=IncoherenceType.EMOTION_ACTION,
                    declared_emotion=declared_emotion,
                    actual_behavior=action_text[:100],
                    declared_text=context,
                    behavior_text=action_text,
                    chapter_id=chapter_id,
                    confidence=0.75,
                    explanation=(
                        f"'{entity_name}' está descrito como '{declared_emotion}', "
                        f"pero la acción descrita parece inconsistente con ese estado emocional."
                    ),
                    suggestion=(
                        f"Revise si la acción de '{entity_name}' es coherente "
                        f"con estar '{declared_emotion}', o añada una justificación."
                    ),
                )

        return None

    def analyze_chapter(
        self,
        chapter_text: str,
        entity_names: list[str],
        dialogues: list[tuple[str, str, int, int]],  # (speaker, text, start, end)
        chapter_id: int,
    ) -> list[EmotionalIncoherence]:
        """
        Analiza un capítulo completo buscando incoherencias emocionales.

        Args:
            chapter_text: Texto completo del capítulo
            entity_names: Nombres de entidades a analizar
            dialogues: Lista de diálogos (hablante, texto, inicio, fin)
            chapter_id: ID del capítulo

        Returns:
            Lista de incoherencias encontradas
        """
        incoherences = []

        # Extraer estados emocionales declarados
        declared_states = self.sentiment.extract_declared_emotions(
            chapter_text, entity_names, chapter_id
        )

        # Para cada estado declarado, buscar diálogos cercanos
        for declared in declared_states:
            # Buscar diálogos del mismo personaje cercanos a la declaración
            for speaker, dialogue_text, start, end in dialogues:
                if speaker.lower() != declared.entity_name.lower():
                    continue

                # Verificar proximidad (dentro de 500 caracteres)
                if abs(start - declared.position) > 500:
                    continue

                # Extraer contexto
                context_start = max(0, declared.position - 50)
                context_end = min(len(chapter_text), declared.position + 100)
                context = chapter_text[context_start:context_end]

                # Verificar coherencia
                incoherence = self.check_dialogue_coherence(
                    entity_name=declared.entity_name,
                    declared_emotion=declared.emotion_keyword,
                    dialogue_text=dialogue_text,
                    context=context,
                    chapter_id=chapter_id,
                    start_char=start,
                    end_char=end,
                )

                if incoherence:
                    incoherences.append(incoherence)

        return incoherences


# Singleton
_checker_instance: Optional[EmotionalCoherenceChecker] = None


def get_emotional_coherence_checker() -> EmotionalCoherenceChecker:
    """Obtiene la instancia singleton del verificador."""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = EmotionalCoherenceChecker()
    return _checker_instance


def reset_emotional_coherence_checker() -> None:
    """Resetea el singleton (útil para tests)."""
    global _checker_instance
    _checker_instance = None
