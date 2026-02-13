"""
Detector de señales narrativas no lineales.

Identifica marcadores textuales de flashbacks (analepsis) y
flashforwards (prolepsis) mediante patrones lingüísticos:
- Subjuntivo imperfecto ("Si hubiera sabido...")
- Adverbios retrospectivos ("De niño...", "Años atrás...")
- Señales prospectivas ("Años después...", "Algún día...")
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NonLinearSignal:
    """
    Señal de narrativa no lineal detectada en el texto.

    Attributes:
        chapter: Número de capítulo
        start_char: Posición inicio en el texto
        end_char: Posición fin en el texto
        signal_type: Tipo de señal (subjunctive, retrospective, prospective)
        direction: Dirección temporal (past, future)
        excerpt: Fragmento de texto
        confidence: Confianza en la detección (0-1)
    """

    chapter: int
    start_char: int
    end_char: int
    signal_type: str
    direction: str  # "past" o "future"
    excerpt: str
    confidence: float = 0.7


class NonLinearNarrativeDetector:
    """
    Detector de señales de narrativa no lineal.

    Clasifica capítulos como analepsis/prolepsis basándose en la
    acumulación de señales textuales.
    """

    # Subjuntivo imperfecto: indica flashback o irrealis
    SUBJUNCTIVE_IMPERFECT_PATTERNS = [
        r"[Ss]i\s+(?:hubiera|hubiese)\s+\w+",
        r"[Cc]omo\s+si\s+(?:hubiera|hubiese|fuera|fuese)\s+\w+",
        r"[Oo]jalá\s+(?:hubiera|hubiese)\s+\w+",
        r"(?:habría|habrían)\s+(?:podido|querido|sabido|debido)\s+\w+",
    ]

    # Adverbios y expresiones retrospectivas: indican flashback
    RETROSPECTIVE_ADVERB_PATTERNS = [
        r"[Dd]e\s+(?:niño|niña|joven|pequeño|pequeña|muchacho|muchacha)",
        r"[Aa]ños?\s+(?:atrás|antes)",
        r"[Tt]iempo\s+(?:atrás|antes|ha)",
        r"[Ee]n\s+(?:aquella|aquel)\s+(?:época|entonces|tiempo|momento)",
        r"[Cc]uando\s+(?:era|tenía|vivía)\s+\w+",
        r"[Hh]acía\s+(?:mucho|tiempo|años|meses|semanas)",
    ]

    # Señales prospectivas: indican flashforward
    PROSPECTIVE_PATTERNS = [
        r"[Aa]ños?\s+después",
        r"[Mm]eses?\s+después",
        r"[Mm]ucho\s+(?:tiempo\s+)?después",
        r"[Aa]lgún\s+día",
        r"[Ee]n\s+el\s+futuro",
        r"[Ll]o\s+que\s+(?:vendría|ocurriría|sucedería|pasaría)",
        r"[Nn]o\s+(?:sabía|imaginaba|sospechaba)\s+que",
    ]

    def __init__(self) -> None:
        self._compiled_subjunctive = [
            re.compile(p, re.UNICODE) for p in self.SUBJUNCTIVE_IMPERFECT_PATTERNS
        ]
        self._compiled_retrospective = [
            re.compile(p, re.UNICODE) for p in self.RETROSPECTIVE_ADVERB_PATTERNS
        ]
        self._compiled_prospective = [
            re.compile(p, re.UNICODE) for p in self.PROSPECTIVE_PATTERNS
        ]

    def detect_signals(self, text: str, chapter: int) -> list[NonLinearSignal]:
        """
        Detecta señales de narrativa no lineal en un texto.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo

        Returns:
            Lista de señales detectadas
        """
        signals: list[NonLinearSignal] = []

        # Subjuntivo imperfecto → past
        for pattern in self._compiled_subjunctive:
            for match in pattern.finditer(text):
                excerpt = text[
                    max(0, match.start() - 20) : min(len(text), match.end() + 40)
                ]
                signals.append(
                    NonLinearSignal(
                        chapter=chapter,
                        start_char=match.start(),
                        end_char=match.end(),
                        signal_type="subjunctive",
                        direction="past",
                        excerpt=excerpt.strip(),
                        confidence=0.6,
                    )
                )

        # Retrospectivo → past
        for pattern in self._compiled_retrospective:
            for match in pattern.finditer(text):
                excerpt = text[
                    max(0, match.start() - 20) : min(len(text), match.end() + 40)
                ]
                signals.append(
                    NonLinearSignal(
                        chapter=chapter,
                        start_char=match.start(),
                        end_char=match.end(),
                        signal_type="retrospective",
                        direction="past",
                        excerpt=excerpt.strip(),
                        confidence=0.75,
                    )
                )

        # Prospectivo → future
        for pattern in self._compiled_prospective:
            for match in pattern.finditer(text):
                excerpt = text[
                    max(0, match.start() - 20) : min(len(text), match.end() + 40)
                ]
                signals.append(
                    NonLinearSignal(
                        chapter=chapter,
                        start_char=match.start(),
                        end_char=match.end(),
                        signal_type="prospective",
                        direction="future",
                        excerpt=excerpt.strip(),
                        confidence=0.7,
                    )
                )

        return signals

    def classify_chapter(
        self,
        text: str,
        chapter: int,
        min_signals: int = 2,
    ) -> str:
        """
        Clasifica un capítulo como chronological, analepsis o prolepsis.

        Requiere al menos `min_signals` señales en la misma dirección.

        Args:
            text: Texto del capítulo
            chapter: Número de capítulo
            min_signals: Mínimo de señales para clasificar

        Returns:
            "analepsis", "prolepsis" o "chronological"
        """
        signals = self.detect_signals(text, chapter)

        past_count = sum(1 for s in signals if s.direction == "past")
        future_count = sum(1 for s in signals if s.direction == "future")

        if past_count >= min_signals and past_count > future_count:
            return "analepsis"
        elif future_count >= min_signals and future_count > past_count:
            return "prolepsis"

        return "chronological"
