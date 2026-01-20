"""
Detección de interacciones entre entidades en texto narrativo.

Detecta:
- Diálogos dirigidos a otras entidades
- Acciones de una entidad hacia otra
- Pensamientos sobre otra entidad
- Contacto físico
- Intercambio de objetos
"""

import logging
import re
from typing import Optional

from .models import (
    EntityInteraction,
    InteractionType,
    InteractionTone,
    DIALOGUE_VERBS,
    ACTION_VERBS_POSITIVE,
    ACTION_VERBS_NEGATIVE,
    ACTION_VERBS_NEUTRAL,
    THOUGHT_VERBS,
    PHYSICAL_CONTACT_VERBS,
    INTERACTION_TYPE_INTENSITY,
)

logger = logging.getLogger(__name__)


# Palabras clave para clasificar tono
TONE_KEYWORDS = {
    InteractionTone.HOSTILE: [
        "golpeó", "atacó", "gritó", "insultó", "amenazó", "odio", "maldijo",
        "escupió", "empujó", "hirió", "furioso", "rabia", "desprecio",
        "ira", "violencia", "agresión", "furia",
    ],
    InteractionTone.COLD: [
        "ignoró", "evitó", "frialdad", "distante", "indiferente", "seco",
        "cortante", "despectivo", "desdeñoso", "altivo", "desinterés",
    ],
    InteractionTone.WARM: [
        "sonrió", "ayudó", "apoyó", "compartió", "alegró", "amable",
        "cariño", "preocupó", "animó", "gentil", "cordial",
    ],
    InteractionTone.AFFECTIONATE: [
        "abrazó", "besó", "acarició", "amor", "adoraba", "quería",
        "ternura", "dulzura", "cariñosamente", "adoración", "devoción",
    ],
}


class InteractionDetector:
    """
    Detecta interacciones entre entidades en texto.

    Usa múltiples técnicas:
    - Patrones de verbos + objeto directo
    - Análisis de diálogos
    - Detección de contacto físico
    - Clasificación de tono por keywords y sentimiento
    """

    def __init__(self, sentiment_analyzer=None):
        """
        Inicializa el detector.

        Args:
            sentiment_analyzer: Analizador de sentimiento opcional
                               para clasificación más precisa del tono.
        """
        self.sentiment_analyzer = sentiment_analyzer
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compila patrones regex para detección."""
        # Patrón para diálogos: —texto— o "texto"
        self.dialogue_pattern = re.compile(
            r'[—«"]([^—»"]+)[—»"]',
            re.UNICODE
        )

        # Patrón para verbos de acción con objeto
        all_action_verbs = (
            ACTION_VERBS_POSITIVE +
            ACTION_VERBS_NEGATIVE +
            ACTION_VERBS_NEUTRAL
        )
        verbs_pattern = "|".join(all_action_verbs)
        self.action_pattern = re.compile(
            rf"(?P<subject>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+({verbs_pattern})\s+(?:a\s+)?(?P<object>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            re.IGNORECASE
        )

        # Patrón para pensamientos
        thought_verbs_pattern = "|".join(THOUGHT_VERBS)
        self.thought_pattern = re.compile(
            rf"(?P<subject>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+({thought_verbs_pattern})\s+(?:en\s+)?(?P<object>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            re.IGNORECASE
        )

        # Patrón para contacto físico
        physical_verbs_pattern = "|".join(PHYSICAL_CONTACT_VERBS)
        self.physical_pattern = re.compile(
            rf"(?P<subject>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+({physical_verbs_pattern})\s+(?:a\s+)?(?P<object>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            re.IGNORECASE
        )

    def detect_all(
        self,
        text: str,
        entities: list[str],
        chapter: int = 0,
        start_offset: int = 0,
    ) -> list[EntityInteraction]:
        """
        Detecta todas las interacciones en un texto.

        Args:
            text: Texto a analizar
            entities: Lista de nombres de entidades a considerar
            chapter: Número de capítulo
            start_offset: Offset de caracteres desde inicio del documento

        Returns:
            Lista de interacciones detectadas
        """
        interactions = []

        # Detectar acciones
        interactions.extend(
            self.detect_actions(text, entities, chapter, start_offset)
        )

        # Detectar pensamientos
        interactions.extend(
            self.detect_thoughts(text, entities, chapter, start_offset)
        )

        # Detectar contacto físico (con mayor prioridad que acciones genéricas)
        physical = self.detect_physical_contact(text, entities, chapter, start_offset)
        # Marcar interacciones de acción que son en realidad contacto físico
        for p in physical:
            for i, action in enumerate(interactions):
                if (action.initiator_name == p.initiator_name and
                    action.receiver_name == p.receiver_name and
                    abs(action.start_char - p.start_char) < 50):
                    interactions[i] = p
                    break
            else:
                interactions.append(p)

        # Eliminar duplicados
        return self._deduplicate_interactions(interactions)

    def detect_actions(
        self,
        text: str,
        entities: list[str],
        chapter: int = 0,
        start_offset: int = 0,
    ) -> list[EntityInteraction]:
        """
        Detecta acciones de una entidad hacia otra.

        Args:
            text: Texto a analizar
            entities: Entidades conocidas
            chapter: Número de capítulo
            start_offset: Offset de caracteres

        Returns:
            Lista de interacciones de tipo acción
        """
        interactions = []
        entities_lower = {e.lower() for e in entities}

        for match in self.action_pattern.finditer(text):
            subject = match.group("subject")
            obj = match.group("object")
            verb = match.group(0).split()[1] if len(match.group(0).split()) > 1 else ""

            # Verificar que ambas son entidades conocidas
            if subject.lower() not in entities_lower or obj.lower() not in entities_lower:
                continue

            # Clasificar tono basado en el verbo
            tone = self._classify_tone_from_verb(verb)

            # Extraer contexto
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            excerpt = text[context_start:context_end]

            interaction = EntityInteraction(
                initiator_name=subject,
                receiver_name=obj,
                interaction_type=InteractionType.ACTION_TOWARDS,
                tone=tone,
                chapter=chapter,
                text_excerpt=excerpt,
                start_char=start_offset + match.start(),
                end_char=start_offset + match.end(),
                intensity=INTERACTION_TYPE_INTENSITY[InteractionType.ACTION_TOWARDS],
                confidence=0.7,
                detection_method="pattern",
            )

            interactions.append(interaction)

        return interactions

    def detect_thoughts(
        self,
        text: str,
        entities: list[str],
        chapter: int = 0,
        start_offset: int = 0,
    ) -> list[EntityInteraction]:
        """
        Detecta pensamientos de una entidad sobre otra.

        Returns:
            Lista de interacciones de tipo pensamiento
        """
        interactions = []
        entities_lower = {e.lower() for e in entities}

        for match in self.thought_pattern.finditer(text):
            subject = match.group("subject")
            obj = match.group("object")

            if subject.lower() not in entities_lower or obj.lower() not in entities_lower:
                continue

            # Extraer contexto más amplio para pensamientos
            context_start = max(0, match.start() - 100)
            context_end = min(len(text), match.end() + 100)
            excerpt = text[context_start:context_end]

            # Clasificar tono del pensamiento
            tone = self.classify_tone(excerpt)

            interaction = EntityInteraction(
                initiator_name=subject,
                receiver_name=obj,
                interaction_type=InteractionType.THOUGHT_ABOUT,
                tone=tone,
                chapter=chapter,
                text_excerpt=excerpt,
                start_char=start_offset + match.start(),
                end_char=start_offset + match.end(),
                intensity=INTERACTION_TYPE_INTENSITY[InteractionType.THOUGHT_ABOUT],
                confidence=0.6,
                detection_method="pattern",
            )

            interactions.append(interaction)

        return interactions

    def detect_physical_contact(
        self,
        text: str,
        entities: list[str],
        chapter: int = 0,
        start_offset: int = 0,
    ) -> list[EntityInteraction]:
        """
        Detecta contacto físico entre entidades.

        Returns:
            Lista de interacciones de tipo contacto físico
        """
        interactions = []
        entities_lower = {e.lower() for e in entities}

        for match in self.physical_pattern.finditer(text):
            subject = match.group("subject")
            obj = match.group("object")
            verb = match.group(0).split()[1] if len(match.group(0).split()) > 1 else ""

            if subject.lower() not in entities_lower or obj.lower() not in entities_lower:
                continue

            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            excerpt = text[context_start:context_end]

            tone = self._classify_tone_from_verb(verb)

            interaction = EntityInteraction(
                initiator_name=subject,
                receiver_name=obj,
                interaction_type=InteractionType.PHYSICAL_CONTACT,
                tone=tone,
                chapter=chapter,
                text_excerpt=excerpt,
                start_char=start_offset + match.start(),
                end_char=start_offset + match.end(),
                intensity=INTERACTION_TYPE_INTENSITY[InteractionType.PHYSICAL_CONTACT],
                confidence=0.8,
                detection_method="pattern",
            )

            interactions.append(interaction)

        return interactions

    def detect_dialogue_interaction(
        self,
        dialogue_text: str,
        speaker: str,
        context_entities: list[str],
        chapter: int = 0,
        start_char: int = 0,
        end_char: int = 0,
    ) -> Optional[EntityInteraction]:
        """
        Detecta a quién se dirige un diálogo.

        Args:
            dialogue_text: Texto del diálogo
            speaker: Nombre del hablante
            context_entities: Entidades presentes en el contexto
            chapter: Número de capítulo
            start_char: Posición inicial
            end_char: Posición final

        Returns:
            Interacción detectada o None
        """
        if not context_entities:
            return None

        # Buscar menciones directas en el diálogo
        receiver = None

        for entity in context_entities:
            if entity.lower() != speaker.lower():
                # Verificar si la entidad es mencionada o hay pronombres de 2da persona
                if entity.lower() in dialogue_text.lower():
                    receiver = entity
                    break
                # Si hay "tú", "usted", "te", asumir que es la otra entidad
                if re.search(r'\b(tú|usted|te|ti)\b', dialogue_text, re.IGNORECASE):
                    if len(context_entities) == 1 or (len(context_entities) == 2 and speaker in context_entities):
                        for e in context_entities:
                            if e.lower() != speaker.lower():
                                receiver = e
                                break
                    break

        if not receiver:
            # Si solo hay una entidad en contexto además del speaker
            other_entities = [e for e in context_entities if e.lower() != speaker.lower()]
            if len(other_entities) == 1:
                receiver = other_entities[0]

        if not receiver:
            return None

        tone = self.classify_tone(dialogue_text)

        return EntityInteraction(
            initiator_name=speaker,
            receiver_name=receiver,
            interaction_type=InteractionType.DIALOGUE,
            tone=tone,
            chapter=chapter,
            text_excerpt=dialogue_text[:200] + ("..." if len(dialogue_text) > 200 else ""),
            start_char=start_char,
            end_char=end_char,
            intensity=INTERACTION_TYPE_INTENSITY[InteractionType.DIALOGUE],
            confidence=0.6,
            detection_method="dialogue_analysis",
        )

    def classify_tone(self, text: str) -> InteractionTone:
        """
        Clasifica el tono de un texto.

        Usa keywords y opcionalmente análisis de sentimiento.

        Args:
            text: Texto a clasificar

        Returns:
            Tono detectado
        """
        # Si hay analizador de sentimiento, usarlo primero
        if self.sentiment_analyzer:
            try:
                result = self.sentiment_analyzer.analyze_text(
                    text, speaker="", chapter_id=0, start_char=0, end_char=len(text)
                )
                if result.is_success and result.value:
                    # Convertir Sentiment enum a score numérico
                    state = result.value
                    sentiment_name = state.sentiment.value if hasattr(state.sentiment, 'value') else str(state.sentiment)
                    confidence = state.sentiment_confidence

                    # Mapear sentiment a score base
                    if sentiment_name == "positive":
                        base_score = 0.5
                    elif sentiment_name == "negative":
                        base_score = -0.5
                    else:
                        base_score = 0.0

                    # Ajustar por confianza
                    score = base_score * confidence
                    return InteractionTone.from_score(score)
            except Exception as e:
                logger.debug(f"Error en análisis de sentimiento: {e}")

        # Fallback a keywords
        return self._classify_tone_from_keywords(text)

    def _classify_tone_from_keywords(self, text: str) -> InteractionTone:
        """Clasifica tono basándose en keywords."""
        text_lower = text.lower()

        scores = {tone: 0 for tone in InteractionTone}

        for tone, keywords in TONE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[tone] += 1

        max_score = max(scores.values())
        if max_score > 0:
            for tone, score in scores.items():
                if score == max_score:
                    return tone

        return InteractionTone.NEUTRAL

    def _classify_tone_from_verb(self, verb: str) -> InteractionTone:
        """Clasifica tono basándose en el verbo de acción."""
        verb_lower = verb.lower()

        if verb_lower in [v.lower() for v in ACTION_VERBS_POSITIVE]:
            return InteractionTone.WARM
        elif verb_lower in [v.lower() for v in ACTION_VERBS_NEGATIVE]:
            return InteractionTone.HOSTILE
        else:
            return InteractionTone.NEUTRAL

    def _deduplicate_interactions(
        self,
        interactions: list[EntityInteraction],
    ) -> list[EntityInteraction]:
        """Elimina interacciones duplicadas."""
        seen = {}

        for interaction in interactions:
            # Clave: participantes + posición aproximada
            key = (
                interaction.initiator_name.lower(),
                interaction.receiver_name.lower(),
                interaction.chapter,
                interaction.start_char // 100,  # Agrupar por bloques de 100 chars
            )

            if key not in seen:
                seen[key] = interaction
            elif interaction.confidence > seen[key].confidence:
                seen[key] = interaction

        return list(seen.values())


def detect_interactions_in_text(
    text: str,
    entities: list[str],
    chapter: int = 0,
    sentiment_analyzer=None,
) -> list[EntityInteraction]:
    """
    Función de conveniencia para detectar interacciones.

    Args:
        text: Texto a analizar
        entities: Lista de nombres de entidades
        chapter: Número de capítulo
        sentiment_analyzer: Analizador de sentimiento opcional

    Returns:
        Lista de interacciones detectadas
    """
    detector = InteractionDetector(sentiment_analyzer)
    return detector.detect_all(text, entities, chapter)
