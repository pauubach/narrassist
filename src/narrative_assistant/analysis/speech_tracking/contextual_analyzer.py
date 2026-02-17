"""
ContextualAnalyzer - Detección de eventos narrativos que justifican cambios de habla.

Analiza capítulos entre ventanas para identificar eventos dramáticos que
podrían explicar cambios abruptos en la forma de hablar de un personaje.
"""

import logging
import re
from typing import Optional

from .types import NarrativeContext

logger = logging.getLogger(__name__)


class ContextualAnalyzer:
    """
    Detecta eventos narrativos dramáticos en capítulos.

    Eventos detectados:
    - Muerte: pérdida de un ser querido, luto
    - Boda: matrimonio, compromiso
    - Pelea: conflicto violento, discusión grave
    - Trauma: accidente, agresión, shock emocional
    - Enfermedad: diagnóstico grave, hospitalización
    - Viaje: cambio de ubicación significativo
    """

    # Diccionario de keywords por tipo de evento
    DRAMATIC_EVENTS = {
        "muerte": [
            "murió",
            "muerto",
            "falleció",
            "fallecimiento",
            "funeral",
            "entierro",
            "luto",
            "difunto",
            "cadáver",
            "asesinato",
            "suicidio",
            "pérdida",
            "velatorio",
            "cementerio",
        ],
        "boda": [
            "boda",
            "casó",
            "casaron",
            "matrimonio",
            "esposa",
            "esposo",
            "ceremonia",
            "altar",
            "votos",
            "anillos",
            "luna de miel",
        ],
        "pelea": [
            "pelea",
            "pelearon",
            "discutieron",
            "gritó",
            "gritaron",
            "furioso",
            "enojado",
            "ira",
            "golpeó",
            "puñetazo",
            "batalla",
            "confrontación",
            "conflicto",
        ],
        "trauma": [
            "accidente",
            "herido",
            "herida",
            "sangre",
            "hospital",
            "emergencia",
            "shock",
            "trauma",
            "violación",
            "abuso",
            "agresión",
            "secuestro",
            "tortura",
        ],
        "enfermedad": [
            "enfermedad",
            "enfermo",
            "diagnóstico",
            "cáncer",
            "tumor",
            "grave",
            "médico",
            "tratamiento",
            "quimioterapia",
            "terminal",
        ],
        "viaje": [
            "viaje",
            "viajó",
            "partió",
            "mudanza",
            "emigró",
            "exilio",
            "destierro",
            "alejó",
            "regresó",
            "retorno",
        ],
        "revelacion": [
            "secreto",
            "reveló",
            "confesó",
            "verdad",
            "descubrió",
            "mentira",
            "engaño",
            "traición",
            "infidelidad",
        ],
    }

    # Pesos por tipo de evento (qué tanto justifica cambio de habla)
    EVENT_WEIGHTS = {
        "muerte": 1.0,  # Máxima justificación
        "trauma": 0.9,
        "enfermedad": 0.8,
        "revelacion": 0.7,
        "pelea": 0.6,
        "boda": 0.5,
        "viaje": 0.4,
    }

    def analyze(self, chapters: list) -> NarrativeContext:
        """
        Analiza capítulos para detectar eventos dramáticos.

        Args:
            chapters: Lista de capítulos a analizar (entre dos ventanas)

        Returns:
            NarrativeContext con evento detectado (si hay)
        """
        if not chapters:
            return NarrativeContext(has_dramatic_event=False)

        # Combinar texto de todos los capítulos
        combined_text = ""
        for chapter in chapters:
            if hasattr(chapter, "text"):
                combined_text += " " + chapter.text
            elif hasattr(chapter, "content"):
                combined_text += " " + chapter.content

        if not combined_text:
            return NarrativeContext(has_dramatic_event=False)

        # Normalizar texto
        combined_text = combined_text.lower()

        # Buscar eventos
        detected_events = []

        for event_type, keywords in self.DRAMATIC_EVENTS.items():
            keywords_found = []

            for keyword in keywords:
                # Buscar keyword con word boundaries
                pattern = r"\b" + re.escape(keyword) + r"\b"
                matches = re.findall(pattern, combined_text, flags=re.IGNORECASE)

                if matches:
                    keywords_found.extend(matches)

            if keywords_found:
                # Calcular score del evento
                weight = self.EVENT_WEIGHTS.get(event_type, 0.5)
                score = len(keywords_found) * weight

                detected_events.append(
                    {
                        "type": event_type,
                        "keywords": keywords_found,
                        "score": score,
                    }
                )

        # Si no hay eventos, retornar contexto vacío
        if not detected_events:
            return NarrativeContext(has_dramatic_event=False)

        # Seleccionar evento con mayor score
        detected_events.sort(key=lambda e: e["score"], reverse=True)
        top_event = detected_events[0]

        # Determinar capítulo del evento (aproximado)
        event_chapter = None
        if chapters:
            # Usar capítulo del medio como aproximación
            event_chapter = (
                chapters[len(chapters) // 2].chapter_number
                if hasattr(chapters[len(chapters) // 2], "chapter_number")
                else None
            )

        logger.info(
            f"Detected dramatic event: {top_event['type']} "
            f"(score={top_event['score']:.2f}, "
            f"keywords={len(top_event['keywords'])})"
        )

        return NarrativeContext(
            has_dramatic_event=True,
            event_type=top_event["type"],
            event_chapter=event_chapter,
            keywords_found=top_event["keywords"][:5],  # Top 5 keywords
        )

    def should_reduce_severity(
        self, event_type: Optional[str], confidence: float
    ) -> bool:
        """
        Determina si la severidad de la alerta debe reducirse dado el contexto.

        Args:
            event_type: Tipo de evento detectado
            confidence: Confianza de la alerta de cambio

        Returns:
            True si debe reducirse severidad
        """
        if not event_type:
            return False

        # Eventos muy traumáticos siempre justifican cambios
        high_impact_events = {"muerte", "trauma", "enfermedad"}
        if event_type in high_impact_events:
            return True

        # Eventos medios solo reducen si confianza no es muy alta
        medium_impact_events = {"revelacion", "pelea"}
        if event_type in medium_impact_events and confidence < 0.85:
            return True

        return False
