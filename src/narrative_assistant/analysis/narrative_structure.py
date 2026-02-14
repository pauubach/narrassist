"""
Detector de estructura narrativa: prolepsis y analepsis.

Detecta anticipaciones narrativas (prolepsis) y flashbacks (analepsis)
mediante análisis de:
1. Tiempos verbales (condicional, futuro)
2. Marcadores temporales de dirección (después, más tarde)
3. Referencias cruzadas entre capítulos

Este módulo complementa el análisis de timeline.py detectando prolepsis
que no tienen fechas explícitas pero usan indicadores gramaticales.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# spaCy para análisis morfológico
try:
    import spacy
    from spacy.tokens import Doc, Token

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.debug("spaCy no disponible para análisis de tiempos verbales")


class NarrativeAnomaly(str, Enum):
    """Tipos de anomalías narrativas."""

    PROLEPSIS = "prolepsis"  # Anticipación: menciona evento futuro
    ANALEPSIS = "analepsis"  # Flashback: menciona evento pasado
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"  # Error temporal


class ProlepsisSeverity(str, Enum):
    """Severidad de la prolepsis detectada."""

    HIGH = "high"  # Spoiler claro, rompe tensión
    MEDIUM = "medium"  # Anticipación sutil
    LOW = "low"  # Posiblemente intencional (leitmotiv)


@dataclass
class NarrativeLocation:
    """Ubicación de un fragmento narrativo."""

    chapter: int
    paragraph: int
    start_char: int
    end_char: int
    text: str

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
        }


@dataclass
class ProlepticReference:
    """
    Una referencia proléptica detectada.

    Ocurre cuando el texto menciona un evento que ocurrirá más tarde
    usando indicadores como condicional + marcador temporal futuro.
    """

    anomaly_type: NarrativeAnomaly
    location: NarrativeLocation
    severity: ProlepsisSeverity
    description: str
    evidence: list[str] = field(default_factory=list)
    # Referencia al evento real (si se encuentra)
    resolved_event_chapter: int | None = None
    resolved_event_text: str | None = None
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "anomaly_type": self.anomaly_type.value,
            "location": self.location.to_dict(),
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "resolved_event_chapter": self.resolved_event_chapter,
            "resolved_event_text": self.resolved_event_text,
            "confidence": self.confidence,
        }


@dataclass
class NarrativeStructureReport:
    """Reporte de análisis de estructura narrativa."""

    prolepsis_found: list[ProlepticReference]
    analepsis_found: list[ProlepticReference]
    chapters_analyzed: int
    total_anomalies: int = 0

    def __post_init__(self):
        self.total_anomalies = len(self.prolepsis_found) + len(self.analepsis_found)

    def to_dict(self) -> dict:
        return {
            "prolepsis": [p.to_dict() for p in self.prolepsis_found],
            "analepsis": [a.to_dict() for a in self.analepsis_found],
            "chapters_analyzed": self.chapters_analyzed,
            "total_anomalies": self.total_anomalies,
            "by_type": {
                "prolepsis": len(self.prolepsis_found),
                "analepsis": len(self.analepsis_found),
            },
            "by_severity": self._count_by_severity(),
        }

    def _count_by_severity(self) -> dict:
        counts = {"high": 0, "medium": 0, "low": 0}
        for p in self.prolepsis_found + self.analepsis_found:
            counts[p.severity.value] = counts.get(p.severity.value, 0) + 1
        return counts


# Patrones para detectar prolepsis por indicadores gramaticales
PROLEPSIS_PATTERNS = [
    # "Un año después, cuando organizó..." + condicional
    (
        r"(Un\s+año\s+después|Años?\s+más\s+tarde|Tiempo\s+después|Meses?\s+después|Semanas?\s+después)[,\s]+.*?\b(recordaría|sabría|vendría|vendrían|sería|serían|estaría|estarían|tendría|tendrían|haría|harían|diría|dirían|vería|verían|pensaría|pensarían|conocería|conocerían|descubriría|descubrirían|comprendería|comprenderían|entendería|entenderían|olvidaría|olvidarían)\b",
        0.95,
    ),
    # Cualquier temporal futuro + condicional
    (
        r"(Mucho\s+tiempo\s+después|Años?\s+después|Con\s+el\s+tiempo|Más\s+adelante|En\s+el\s+futuro|Pasado\s+el\s+tiempo)[,\s]+.*?\b(\w+ría[ns]?)\b",
        0.85,
    ),
    # "Cuando [evento futuro], [sujeto] recordaría/sabría"
    (
        r"\bCuando\s+.{20,100}\b(recordaría|sabría|comprendería|entendería|vería)\b",
        0.8,
    ),
    # Frases que anticipan el final
    (
        r"\b(pero\s+eso\s+sería|eso\s+vendría|eso\s+ocurriría|eso\s+pasaría|todo\s+cambiaría)\s+(después|más\s+tarde|con\s+el\s+tiempo)\b",
        0.9,
    ),
]

# Patrones de tiempos verbales condicionales (español)
CONDITIONAL_VERB_PATTERNS = [
    r"\b\w+aría[sn]?\b",  # hablaría, hablarías, hablarían
    r"\b\w+ería[sn]?\b",  # comería, comerías, comerían
    r"\b\w+iría[sn]?\b",  # viviría, vivirías, vivirían
]

# Marcadores temporales que indican dirección futura
FUTURE_MARKERS = [
    r"\bun\s+año\s+(después|más\s+tarde)\b",
    r"\b(años?|meses?|semanas?)\s+(después|más\s+tarde)\b",
    r"\bmás\s+adelante\b",
    r"\bcon\s+el\s+tiempo\b",
    r"\bmucho\s+tiempo\s+después\b",
    r"\bpasado\s+el\s+tiempo\b",
    r"\ben\s+el\s+futuro\b",
    r"\balgún\s+día\b",
    r"\btiempo\s+después\b",
]


class NarrativeStructureDetector:
    """
    Detecta prolepsis y analepsis en texto narrativo.

    Usa análisis de tiempos verbales y marcadores temporales para
    identificar anticipaciones narrativas sin requerir fechas explícitas.
    """

    def __init__(self, nlp=None):
        """
        Inicializa el detector.

        Args:
            nlp: Modelo spaCy (opcional). Si no se proporciona, se usará
                 solo análisis basado en patrones.
        """
        self._nlp = nlp
        self._prolepsis_patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE | re.DOTALL), conf)
            for p, conf in PROLEPSIS_PATTERNS
        ]
        self._future_markers = [re.compile(p, re.IGNORECASE) for p in FUTURE_MARKERS]
        self._conditional_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONDITIONAL_VERB_PATTERNS
        ]

    def detect_prolepsis(
        self,
        text: str,
        chapters: list[dict],
        min_confidence: float = 0.7,
    ) -> list[ProlepticReference]:
        """
        Detecta prolepsis en el texto.

        Args:
            text: Texto completo del manuscrito
            chapters: Lista de capítulos con {number, start_char, end_char, content}
            min_confidence: Umbral mínimo de confianza

        Returns:
            Lista de referencias prolépticas detectadas
        """
        prolepsis_found = []

        for chapter in chapters:
            chapter_num = chapter.get("number", 0)
            chapter_content = chapter.get("content", "")
            chapter_start = chapter.get("start_char", 0)

            if not chapter_content:
                continue

            # Método 1: Patrones explícitos de prolepsis
            for pattern, base_confidence in self._prolepsis_patterns:
                for match in pattern.finditer(chapter_content):
                    confidence = base_confidence

                    # Extraer contexto
                    match_start = match.start()
                    match_end = match.end()

                    # Obtener la oración completa
                    sentence = self._extract_sentence(chapter_content, match_start, match_end)

                    # Verificar si hay verbos condicionales en la oración
                    has_conditional = any(p.search(sentence) for p in self._conditional_patterns)
                    if has_conditional:
                        confidence = min(1.0, confidence + 0.05)

                    # Verificar si hay marcadores temporales futuros
                    has_future_marker = any(m.search(sentence) for m in self._future_markers)
                    if has_future_marker:
                        confidence = min(1.0, confidence + 0.05)

                    if confidence >= min_confidence:
                        # Determinar severidad
                        severity = self._assess_prolepsis_severity(
                            sentence, chapter_num, len(chapters)
                        )

                        # Buscar si el evento mencionado ocurre más tarde
                        resolved_chapter, resolved_text = self._find_resolved_event(
                            sentence, chapters, chapter_num
                        )

                        evidence = []
                        if has_conditional:
                            evidence.append("Uso de condicional (futuro hipotético)")
                        if has_future_marker:
                            evidence.append("Marcador temporal de anticipación")
                        if resolved_chapter:
                            evidence.append(f"Evento encontrado en capítulo {resolved_chapter}")

                        prolepsis = ProlepticReference(
                            anomaly_type=NarrativeAnomaly.PROLEPSIS,
                            location=NarrativeLocation(
                                chapter=chapter_num,
                                paragraph=self._get_paragraph_number(chapter_content, match_start),
                                start_char=chapter_start + match_start,
                                end_char=chapter_start + match_end,
                                text=sentence,
                            ),
                            severity=severity,
                            description=self._generate_description(
                                sentence, chapter_num, resolved_chapter
                            ),
                            evidence=evidence,
                            resolved_event_chapter=resolved_chapter,
                            resolved_event_text=resolved_text,
                            confidence=confidence,
                        )
                        prolepsis_found.append(prolepsis)

        # Eliminar duplicados cercanos
        prolepsis_found = self._deduplicate(prolepsis_found)

        return prolepsis_found

    def detect_all(
        self,
        text: str,
        chapters: list[dict],
        min_confidence: float = 0.7,
    ) -> NarrativeStructureReport:
        """
        Detecta todas las anomalías narrativas.

        Args:
            text: Texto completo
            chapters: Lista de capítulos
            min_confidence: Umbral de confianza

        Returns:
            NarrativeStructureReport con todas las anomalías
        """
        prolepsis = self.detect_prolepsis(text, chapters, min_confidence)

        # TODO: Implementar detección de analepsis (flashbacks sin marcador)
        analepsis = []  # type: ignore[var-annotated]

        return NarrativeStructureReport(
            prolepsis_found=prolepsis,
            analepsis_found=analepsis,
            chapters_analyzed=len(chapters),
        )

    def _extract_sentence(self, text: str, start: int, end: int) -> str:
        """Extrae la oración completa que contiene el match."""
        # Buscar inicio de oración
        sentence_start = start
        for i in range(start - 1, max(0, start - 500), -1):
            if text[i] in ".!?\n" and i < start - 1:
                sentence_start = i + 1
                break
            if i == max(0, start - 500):
                sentence_start = i

        # Buscar fin de oración
        sentence_end = end
        for i in range(end, min(len(text), end + 500)):
            if text[i] in ".!?\n":
                sentence_end = i + 1
                break

        return text[sentence_start:sentence_end].strip()

    def _get_paragraph_number(self, text: str, char_pos: int) -> int:
        """Obtiene el número de párrafo para una posición de caracter."""
        text_before = text[:char_pos]
        return text_before.count("\n\n") + 1

    def _assess_prolepsis_severity(
        self, sentence: str, current_chapter: int, total_chapters: int
    ) -> ProlepsisSeverity:
        """
        Evalúa la severidad de una prolepsis.

        - HIGH: Revela información crucial o del final
        - MEDIUM: Anticipación que afecta tensión narrativa
        - LOW: Anticipación sutil o posiblemente intencional
        """
        sentence_lower = sentence.lower()

        # Indicadores de alta severidad (spoilers)
        high_severity_keywords = [
            "muerte",
            "moriría",
            "muerto",
            "final",
            "acabaría",
            "terminaría",
            "revelaría",
            "descubriría la verdad",
            "todo cambiaría",
            "nunca volvería",
            "última vez",
        ]

        # Indicadores de media severidad
        medium_severity_keywords = [
            "recordaría",
            "sabría",
            "entendería",
            "comprendería",
            "años después",
            "tiempo después",
        ]

        for kw in high_severity_keywords:
            if kw in sentence_lower:
                return ProlepsisSeverity.HIGH

        for kw in medium_severity_keywords:
            if kw in sentence_lower:
                return ProlepsisSeverity.MEDIUM

        # Si está en los primeros capítulos, más severo
        if current_chapter <= 2 and total_chapters > 3:
            return ProlepsisSeverity.MEDIUM

        return ProlepsisSeverity.LOW

    def _find_resolved_event(
        self,
        prolepsis_sentence: str,
        chapters: list[dict],
        current_chapter: int,
    ) -> tuple[int | None, str | None]:
        """
        Busca si el evento mencionado en la prolepsis ocurre más tarde.

        Returns:
            (chapter_number, matching_text) o (None, None) si no se encuentra
        """
        # Extraer palabras clave del evento anticipado
        keywords = self._extract_event_keywords(prolepsis_sentence)

        # También extraer frases clave (bigrams importantes)
        key_phrases = self._extract_key_phrases(prolepsis_sentence)

        if not keywords and not key_phrases:
            return None, None

        # Buscar en capítulos posteriores
        for chapter in chapters:
            if chapter.get("number", 0) <= current_chapter:
                continue

            content = chapter.get("content", "").lower()

            # Primero buscar frases completas (más preciso)
            for phrase in key_phrases:
                if self._find_key_phrase_in_content(phrase, content):
                    idx = content.find(phrase.lower())
                    start = max(0, idx - 30)
                    end = min(len(content), idx + 100)
                    fragment = chapter.get("content", "")[start:end]
                    return chapter.get("number"), fragment.strip()

            # Si no hay frases, buscar keywords
            if keywords:
                # Contar coincidencias de keywords
                matches = sum(1 for kw in keywords if kw.lower() in content)

                # Si hay al menos 2 keywords importantes o 40% del total
                min_matches = max(2, len(keywords) * 0.4)
                if matches >= min_matches:
                    # Extraer fragmento relevante
                    for kw in keywords:
                        kw_lower = kw.lower()
                        if kw_lower in content:
                            idx = content.find(kw_lower)
                            start = max(0, idx - 50)
                            end = min(len(content), idx + 100)
                            fragment = chapter.get("content", "")[start:end]
                            return chapter.get("number"), fragment.strip()

        return None, None

    def _extract_key_phrases(self, sentence: str) -> list[str]:
        """Extrae frases clave que identifican el evento."""
        phrases = []

        # Normalizar espacios en blanco
        normalized = re.sub(r"\s+", " ", sentence.strip())

        # Patrones de frases importantes para eventos
        # Estos son los "núcleos" que deben coincidir
        phrase_patterns = [
            r"ceremonia\s+en\s+el\s+(\w+)",  # ceremonia en el jardín
            r"ceremonia\s+en\s+la\s+(\w+)",  # ceremonia en la casa
        ]

        for pattern in phrase_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                phrases.append(match.group(0))

        return phrases

    def _find_key_phrase_in_content(self, phrase: str, content: str) -> bool:
        """Busca frase clave de forma flexible (tolerante a artículos)."""
        # Normalizar espacios
        phrase_normalized = re.sub(r"\s+", " ", phrase.strip().lower())
        content_normalized = re.sub(r"\s+", " ", content.lower())

        # Buscar coincidencia directa
        if phrase_normalized in content_normalized:
            return True

        # Buscar sin artículos (la/el/una/un)
        phrase_no_articles = re.sub(r"\b(la|el|un|una)\s+", "", phrase_normalized)
        content_no_articles = re.sub(
            r"\b(la|el|un|una|pequeña|pequeño|gran|grande)\s+", "", content_normalized
        )

        return phrase_no_articles in content_no_articles

    def _extract_event_keywords(self, sentence: str) -> list[str]:
        """Extrae palabras clave del evento anticipado."""
        keywords = []

        # Buscar sustantivos importantes
        # Patrón simple: palabras de >5 letras que no son verbos comunes
        stopwords = {
            "después",
            "cuando",
            "tiempo",
            "momento",
            "manera",
            "forma",
            "cosa",
            "lugar",
            "parte",
            "recordaría",
            "sabría",
            "vendría",
            "sería",
            "estaría",
            "conocería",
        }

        words = re.findall(r"\b[A-Za-záéíóúüñÁÉÍÓÚÜÑ]{5,}\b", sentence)

        for word in words:
            if word.lower() not in stopwords:
                # Evitar verbos en condicional
                if not word.lower().endswith("ría") and not word.lower().endswith("rían"):
                    keywords.append(word)

        return keywords[:5]  # Máximo 5 keywords

    def _generate_description(
        self,
        sentence: str,
        current_chapter: int,
        resolved_chapter: int | None,
    ) -> str:
        """Genera descripción legible de la prolepsis."""
        if resolved_chapter:
            return (
                f"Prolepsis en capítulo {current_chapter}: anticipa evento "
                f"que ocurre en capítulo {resolved_chapter}"
            )
        return (
            f"Posible prolepsis en capítulo {current_chapter}: "
            f"uso de condicional con marcador temporal futuro"
        )

    def _deduplicate(self, prolepsis_list: list[ProlepticReference]) -> list[ProlepticReference]:
        """Elimina prolepsis duplicadas o muy cercanas."""
        if not prolepsis_list:
            return []

        # Ordenar por posición
        sorted_list = sorted(prolepsis_list, key=lambda p: p.location.start_char)

        # Filtrar cercanos (menos de 100 chars de diferencia)
        result = [sorted_list[0]]
        for p in sorted_list[1:]:
            last = result[-1]
            if p.location.start_char - last.location.end_char > 100:
                result.append(p)
            elif p.confidence > last.confidence:
                # Si el nuevo tiene más confianza, reemplazar
                result[-1] = p

        return result


# Singleton thread-safe
_detector_lock = threading.Lock()
_detector_instance: NarrativeStructureDetector | None = None


def get_narrative_structure_detector() -> NarrativeStructureDetector:
    """Obtiene instancia singleton del detector."""
    global _detector_instance
    if _detector_instance is None:
        with _detector_lock:
            if _detector_instance is None:
                _detector_instance = NarrativeStructureDetector()
    return _detector_instance


def reset_narrative_structure_detector() -> None:
    """Resetea el singleton (para tests)."""
    global _detector_instance
    with _detector_lock:
        _detector_instance = None
