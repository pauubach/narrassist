"""
Detector de muletillas (filler words/phrases) en español.

Detecta expresiones que se repiten excesivamente y pueden debilitar la prosa:
- Muletillas lingüísticas: "en realidad", "o sea", "básicamente", "literalmente"
- Adverbios débiles: "realmente", "muy", "bastante"
- Conectores sobreusados: "entonces", "luego", "después"
- Intensificadores vacíos: "totalmente", "completamente", "absolutamente"
- Coletillas: "¿sabes?", "¿no?", "¿vale?"

El sistema es configurable y puede ignorar contextos donde las muletillas
son apropiadas (diálogos informales, caracterización de personajes).
"""

import logging
import re
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...core.result import Result
from ...core.errors import NLPError, ErrorSeverity

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["FillerDetector"] = None


def get_filler_detector() -> "FillerDetector":
    """Obtener instancia singleton del detector de muletillas."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = FillerDetector()

    return _instance


def reset_filler_detector() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================

class FillerType(Enum):
    """Tipos de muletillas detectadas."""
    LINGUISTIC = "linguistic"          # Muletillas del habla: "o sea", "en realidad"
    WEAK_ADVERB = "weak_adverb"       # Adverbios débiles: "muy", "bastante"
    CONNECTOR = "connector"            # Conectores sobreusados: "entonces", "después"
    INTENSIFIER = "intensifier"        # Intensificadores vacíos: "totalmente"
    TAG_QUESTION = "tag_question"      # Coletillas: "¿sabes?", "¿no?"
    HEDGE = "hedge"                    # Atenuadores: "quizás", "tal vez", "un poco"


class FillerSeverity(Enum):
    """Severidad del uso de muletillas."""
    HIGH = "high"          # Muy frecuente, debilita significativamente
    MEDIUM = "medium"      # Frecuente, notable
    LOW = "low"            # Presente pero no excesivo


@dataclass
class FillerOccurrence:
    """Una ocurrencia de una muletilla."""
    text: str              # Texto exacto encontrado
    start_char: int        # Posición inicio en el documento
    end_char: int          # Posición fin
    context: str           # Oración o contexto
    in_dialogue: bool = False  # Si está dentro de diálogo


@dataclass
class Filler:
    """Una muletilla detectada con sus estadísticas."""

    # Muletilla
    phrase: str                         # La expresión/palabra
    normalized: str = ""                # Forma normalizada

    # Tipo y severidad
    filler_type: FillerType = FillerType.LINGUISTIC
    severity: FillerSeverity = FillerSeverity.MEDIUM

    # Ocurrencias
    occurrences: list[FillerOccurrence] = field(default_factory=list)
    count: int = 0                      # Número total de apariciones
    count_in_narrative: int = 0         # Apariciones fuera de diálogo
    count_in_dialogue: int = 0          # Apariciones en diálogo

    # Métricas
    frequency_per_1000: float = 0.0     # Frecuencia por 1000 palabras
    is_excessive: bool = False          # Si supera el umbral

    # Sugerencia
    suggestion: str = ""                # Sugerencia de mejora

    def __post_init__(self):
        if not self.count:
            self.count = len(self.occurrences)
        if not self.normalized:
            self.normalized = self.phrase.lower().strip()

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "phrase": self.phrase,
            "normalized": self.normalized,
            "filler_type": self.filler_type.value,
            "severity": self.severity.value,
            "count": self.count,
            "count_in_narrative": self.count_in_narrative,
            "count_in_dialogue": self.count_in_dialogue,
            "frequency_per_1000": round(self.frequency_per_1000, 2),
            "is_excessive": self.is_excessive,
            "suggestion": self.suggestion,
            "occurrences": [
                {
                    "text": occ.text,
                    "start_char": occ.start_char,
                    "end_char": occ.end_char,
                    "context": occ.context[:100] + "..." if len(occ.context) > 100 else occ.context,
                    "in_dialogue": occ.in_dialogue,
                }
                for occ in self.occurrences[:10]  # Limitar a 10 ejemplos
            ],
        }


@dataclass
class FillerReport:
    """Reporte completo de muletillas detectadas."""

    fillers: list[Filler] = field(default_factory=list)
    total_fillers: int = 0
    excessive_fillers: int = 0
    word_count: int = 0
    overall_filler_ratio: float = 0.0  # % de palabras que son muletillas

    # Desglose por tipo
    by_type: dict[FillerType, int] = field(default_factory=dict)

    # Top muletillas
    top_fillers: list[tuple[str, int]] = field(default_factory=list)

    # Recomendación general
    quality_score: float = 1.0  # 1.0 = sin problemas, 0.0 = muy problemático
    recommendation: str = ""

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "fillers": [f.to_dict() for f in self.fillers],
            "total_fillers": self.total_fillers,
            "excessive_fillers": self.excessive_fillers,
            "word_count": self.word_count,
            "overall_filler_ratio": round(self.overall_filler_ratio, 4),
            "by_type": {t.value: c for t, c in self.by_type.items()},
            "top_fillers": self.top_fillers[:10],
            "quality_score": round(self.quality_score, 2),
            "recommendation": self.recommendation,
        }


# =============================================================================
# Diccionarios de muletillas en español
# =============================================================================

# Muletillas lingüísticas del habla
LINGUISTIC_FILLERS = {
    # Expresiones de relleno
    "o sea": "considerar eliminar o reformular",
    "en realidad": "usar solo cuando realmente contraste información",
    "básicamente": "eliminar si no añade significado",
    "literalmente": "usar solo para significado literal real",
    "de hecho": "usar solo para contrastar o añadir énfasis",
    "en plan": "evitar en prosa formal",
    "tipo": "evitar como muletilla ('era tipo alto')",
    "como que": "reformular para mayor claridad",
    "o algo así": "ser más específico",
    "y eso": "completar la idea",
    "y tal": "ser más específico",
    "pues": "evaluar si es necesario",
    "bueno": "eliminar si no aporta",
    "mira": "eliminar en narración (válido en diálogo)",
    "vamos": "eliminar si no aporta",
    "es decir": "usar con moderación",
    "digamos": "ser más directo",
    "por así decirlo": "ser más preciso",
    "más o menos": "ser más específico cuando sea posible",
}

# Adverbios débiles
WEAK_ADVERBS = {
    "muy": "buscar adjetivos más precisos",
    "bastante": "cuantificar o usar adjetivo más fuerte",
    "realmente": "eliminar si no añade énfasis necesario",
    "verdaderamente": "usar con moderación",
    "prácticamente": "ser más preciso",
    "simplemente": "eliminar si no es necesario",
    "solamente": "evaluar necesidad",
    "apenas": "usar con precisión",
}

# Intensificadores vacíos
EMPTY_INTENSIFIERS = {
    "totalmente": "usar con moderación",
    "completamente": "evaluar si es necesario",
    "absolutamente": "reservar para énfasis real",
    "tremendamente": "buscar descripción más vívida",
    "increíblemente": "usar solo si es realmente increíble",
    "extremadamente": "cuantificar o describir mejor",
    "enormemente": "ser más específico",
    "sumamente": "usar con moderación",
}

# Conectores frecuentemente sobreusados
OVERUSED_CONNECTORS = {
    "entonces": "variar conectores",
    "luego": "alternar con otros conectores temporales",
    "después": "variar estructura de oraciones",
    "además": "usar con moderación",
    "también": "evaluar necesidad",
    "sin embargo": "no abusar",
    "no obstante": "usar con moderación",
    "por otro lado": "evitar exceso",
    "asimismo": "variar conectores",
    "igualmente": "considerar alternativas",
}

# Atenuadores (hedges)
HEDGES = {
    "quizás": "usar con intención, no por inseguridad",
    "tal vez": "ser más directo cuando sea posible",
    "un poco": "cuantificar o eliminar",
    "algo": "ser más específico ('algo triste' → 'melancólico')",
    "como": "evitar como atenuador ('era como alto')",
    "casi": "usar con precisión",
    "aproximadamente": "ser preciso cuando sea posible",
    "relativamente": "cuantificar mejor",
}

# Coletillas de diálogo (menos problemáticas en diálogos)
TAG_QUESTIONS = {
    "¿sabes?": "válido en diálogo informal",
    "¿no?": "válido en diálogo informal",
    "¿vale?": "válido en diálogo informal",
    "¿entiendes?": "válido en diálogo",
    "¿verdad?": "válido en diálogo",
    "¿eh?": "válido en diálogo informal",
    "¿sí?": "válido en diálogo",
}

# Umbrales por tipo (ocurrencias por 1000 palabras antes de ser excesivo)
THRESHOLDS = {
    FillerType.LINGUISTIC: 5.0,    # Más estricto
    FillerType.WEAK_ADVERB: 10.0,  # Moderado
    FillerType.INTENSIFIER: 3.0,   # Muy estricto
    FillerType.CONNECTOR: 15.0,    # Más permisivo
    FillerType.HEDGE: 8.0,         # Moderado
    FillerType.TAG_QUESTION: 20.0, # Muy permisivo (común en diálogos)
}


# =============================================================================
# Detector
# =============================================================================

class FillerDetector:
    """
    Detector de muletillas en textos narrativos.

    Identifica expresiones que debilitan la prosa y proporciona
    sugerencias de mejora.
    """

    def __init__(
        self,
        ignore_dialogues: bool = False,
        custom_thresholds: Optional[dict[FillerType, float]] = None,
    ):
        """
        Inicializar detector.

        Args:
            ignore_dialogues: Si True, no cuenta muletillas en diálogos
            custom_thresholds: Umbrales personalizados por tipo
        """
        self.ignore_dialogues = ignore_dialogues
        self.thresholds = custom_thresholds or THRESHOLDS.copy()

        # Compilar patrones
        self._compile_patterns()

    def _compile_patterns(self):
        """Compilar expresiones regulares para búsqueda eficiente."""
        # Combinar todas las muletillas con sus tipos
        self._filler_map: dict[str, tuple[FillerType, str]] = {}

        for phrase, suggestion in LINGUISTIC_FILLERS.items():
            self._filler_map[phrase.lower()] = (FillerType.LINGUISTIC, suggestion)

        for phrase, suggestion in WEAK_ADVERBS.items():
            self._filler_map[phrase.lower()] = (FillerType.WEAK_ADVERB, suggestion)

        for phrase, suggestion in EMPTY_INTENSIFIERS.items():
            self._filler_map[phrase.lower()] = (FillerType.INTENSIFIER, suggestion)

        for phrase, suggestion in OVERUSED_CONNECTORS.items():
            self._filler_map[phrase.lower()] = (FillerType.CONNECTOR, suggestion)

        for phrase, suggestion in HEDGES.items():
            self._filler_map[phrase.lower()] = (FillerType.HEDGE, suggestion)

        for phrase, suggestion in TAG_QUESTIONS.items():
            self._filler_map[phrase.lower()] = (FillerType.TAG_QUESTION, suggestion)

        # Crear patrón regex combinado
        # Ordenar por longitud descendente para capturar frases más largas primero
        sorted_phrases = sorted(self._filler_map.keys(), key=len, reverse=True)
        escaped_phrases = [re.escape(p) for p in sorted_phrases]
        self._pattern = re.compile(
            r'\b(' + '|'.join(escaped_phrases) + r')\b',
            re.IGNORECASE
        )

        # Patrón para detectar diálogos
        self._dialogue_pattern = re.compile(
            r"(?:^|\n)\s*[-\u2014].*?(?:\n|$)|\"[^\"]*\"|«[^»]*»|\u2018[^\u2019]*\u2019",
            re.MULTILINE | re.DOTALL
        )

    def detect(
        self,
        text: str,
        chapter_id: Optional[int] = None,
    ) -> Result[FillerReport]:
        """
        Detectar muletillas en un texto.

        Args:
            text: Texto a analizar
            chapter_id: ID del capítulo (opcional)

        Returns:
            Result con FillerReport
        """
        if not text or not text.strip():
            return Result.success(FillerReport())

        try:
            # Contar palabras
            words = text.split()
            word_count = len(words)

            if word_count == 0:
                return Result.success(FillerReport(word_count=0))

            # Identificar regiones de diálogo
            dialogue_regions = self._find_dialogue_regions(text)

            # Buscar muletillas
            filler_occurrences: dict[str, list[FillerOccurrence]] = defaultdict(list)

            for match in self._pattern.finditer(text):
                phrase = match.group(1).lower()
                start = match.start()
                end = match.end()

                # Determinar si está en diálogo
                in_dialogue = any(
                    d_start <= start < d_end
                    for d_start, d_end in dialogue_regions
                )

                # Obtener contexto
                context = self._get_context(text, start, end)

                occ = FillerOccurrence(
                    text=match.group(1),
                    start_char=start,
                    end_char=end,
                    context=context,
                    in_dialogue=in_dialogue,
                )

                filler_occurrences[phrase].append(occ)

            # Construir objetos Filler
            fillers: list[Filler] = []
            total_count = 0
            by_type: dict[FillerType, int] = defaultdict(int)

            for phrase, occurrences in filler_occurrences.items():
                filler_type, suggestion = self._filler_map[phrase]

                # Contar por contexto
                count_narrative = sum(1 for o in occurrences if not o.in_dialogue)
                count_dialogue = sum(1 for o in occurrences if o.in_dialogue)

                # Calcular frecuencia
                effective_count = count_narrative if self.ignore_dialogues else len(occurrences)
                freq_per_1000 = (effective_count / word_count) * 1000

                # Determinar si es excesivo
                threshold = self.thresholds.get(filler_type, 10.0)
                is_excessive = freq_per_1000 > threshold

                # Determinar severidad
                if freq_per_1000 > threshold * 2:
                    severity = FillerSeverity.HIGH
                elif freq_per_1000 > threshold:
                    severity = FillerSeverity.MEDIUM
                else:
                    severity = FillerSeverity.LOW

                filler = Filler(
                    phrase=phrase,
                    filler_type=filler_type,
                    severity=severity,
                    occurrences=occurrences,
                    count=len(occurrences),
                    count_in_narrative=count_narrative,
                    count_in_dialogue=count_dialogue,
                    frequency_per_1000=freq_per_1000,
                    is_excessive=is_excessive,
                    suggestion=suggestion,
                )

                fillers.append(filler)
                total_count += len(occurrences)
                by_type[filler_type] += len(occurrences)

            # Ordenar por frecuencia descendente
            fillers.sort(key=lambda f: f.frequency_per_1000, reverse=True)

            # Calcular métricas del reporte
            excessive_count = sum(1 for f in fillers if f.is_excessive)
            overall_ratio = total_count / word_count if word_count > 0 else 0

            # Top muletillas
            top_fillers = [(f.phrase, f.count) for f in fillers[:10]]

            # Calcular score de calidad (1.0 = perfecto, 0.0 = muy problemático)
            if excessive_count == 0:
                quality_score = 1.0
            elif excessive_count <= 2:
                quality_score = 0.8
            elif excessive_count <= 5:
                quality_score = 0.6
            elif excessive_count <= 10:
                quality_score = 0.4
            else:
                quality_score = 0.2

            # Generar recomendación
            if excessive_count == 0:
                recommendation = "El texto tiene un buen equilibrio de expresiones. No se detectan muletillas excesivas."
            elif excessive_count <= 2:
                recommendation = f"Se detectaron {excessive_count} expresiones usadas con frecuencia. Considere revisarlas."
            elif excessive_count <= 5:
                recommendation = f"Se detectaron {excessive_count} muletillas frecuentes. Se recomienda revisión del estilo."
            else:
                recommendation = f"Se detectaron {excessive_count} muletillas excesivas. El texto podría beneficiarse de una revisión estilística significativa."

            report = FillerReport(
                fillers=fillers,
                total_fillers=total_count,
                excessive_fillers=excessive_count,
                word_count=word_count,
                overall_filler_ratio=overall_ratio,
                by_type=dict(by_type),
                top_fillers=top_fillers,
                quality_score=quality_score,
                recommendation=recommendation,
            )

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error detectando muletillas: {e}", exc_info=True)
            error = NLPError(
                message=f"Error en detección de muletillas: {e}",
                severity=ErrorSeverity.MEDIUM,
            )
            return Result.failure(error)

    def _find_dialogue_regions(self, text: str) -> list[tuple[int, int]]:
        """Encontrar regiones de texto que son diálogo."""
        regions = []
        for match in self._dialogue_pattern.finditer(text):
            regions.append((match.start(), match.end()))
        return regions

    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Obtener contexto alrededor de una posición."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)

        # Ajustar a límites de palabra
        while context_start > 0 and text[context_start - 1] not in ' \n':
            context_start -= 1
        while context_end < len(text) and text[context_end] not in ' \n':
            context_end += 1

        return text[context_start:context_end].strip()

    def get_filler_categories(self) -> dict[str, list[str]]:
        """Obtener las categorías de muletillas y sus ejemplos."""
        return {
            "Muletillas lingüísticas": list(LINGUISTIC_FILLERS.keys()),
            "Adverbios débiles": list(WEAK_ADVERBS.keys()),
            "Intensificadores vacíos": list(EMPTY_INTENSIFIERS.keys()),
            "Conectores sobreusados": list(OVERUSED_CONNECTORS.keys()),
            "Atenuadores": list(HEDGES.keys()),
            "Coletillas": list(TAG_QUESTIONS.keys()),
        }
