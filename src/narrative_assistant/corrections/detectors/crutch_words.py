"""
Detector de muletillas del autor.

Identifica palabras y expresiones que el autor usa con excesiva frecuencia,
sugiriendo alternativas o simplemente señalando el patrón para que el
autor decida si es intencional.
"""

import re
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import CrutchWordsConfig
from ..types import CorrectionCategory

# Muletillas comunes por categoría con alternativas
CRUTCH_CATEGORIES = {
    "adverbios_modo": {
        "realmente": ["verdaderamente", "de verdad", "en realidad", None],
        "obviamente": ["evidentemente", "claramente", None],
        "claramente": ["evidentemente", "sin duda", None],
        "definitivamente": ["sin duda", "decididamente", None],
        "literalmente": ["textualmente", None],
        "básicamente": ["fundamentalmente", "esencialmente", None],
        "simplemente": ["sencillamente", "solo", None],
        "absolutamente": ["completamente", "totalmente", None],
        "totalmente": ["completamente", "del todo", None],
        "increíblemente": ["sorprendentemente", "asombrosamente", None],
        "aparentemente": ["al parecer", "según parece", None],
    },
    "conectores": {
        "sin embargo": ["no obstante", "pero", "aunque", None],
        "por lo tanto": ["por consiguiente", "así pues", None],
        "de hecho": ["en efecto", "efectivamente", None],
        "en realidad": ["realmente", "de verdad", None],
        "por otro lado": ["por otra parte", "además", None],
        "además": ["también", "asimismo", None],
        "aunque": ["si bien", "a pesar de que", None],
        "mientras": ["en tanto que", "al tiempo que", None],
        "entonces": ["en ese momento", "luego", None],
        "después": ["luego", "más tarde", "posteriormente", None],
    },
    "verbos_diccion": {
        "dijo": ["comentó", "respondió", "contestó", "afirmó", "señaló", None],
        "preguntó": ["cuestionó", "inquirió", None],
        "susurró": ["murmuró", "cuchicheó", None],
        "exclamó": ["gritó", "vociferó", None],
        "añadió": ["agregó", "sumó", None],
        "pensó": ["reflexionó", "consideró", "meditó", None],
        "miró": ["observó", "contempló", "vio", None],
        "caminó": ["anduvo", "avanzó", "se dirigió", None],
        "sonrió": ["esbozó una sonrisa", None],
    },
    "intensificadores": {
        "muy": ["sumamente", "extremadamente", "bastante", None],
        "bastante": ["considerablemente", "notablemente", None],
        "mucho": ["enormemente", "sobremanera", None],
        "poco": ["escasamente", "apenas", None],
        "tan": ["tanto", None],
        "demasiado": ["excesivamente", None],
    },
    "coletillas": {
        "¿sabes?": [None],
        "o sea": ["es decir", None],
        "es decir": ["o sea", "esto es", None],
        "en plan": [None],  # Coloquial, mejor eliminar
        "tipo": [None],  # Coloquial
        "como que": [None],
        "la verdad": ["sinceramente", None],
        "de alguna manera": ["de cierto modo", None],
        "en cierto modo": ["de alguna manera", None],
    },
    "inicio_oracion": {
        "de repente": ["súbitamente", "de pronto", None],
        "de pronto": ["súbitamente", "de repente", None],
        "entonces": ["en ese momento", "luego", None],
        "pero": ["sin embargo", "no obstante", None],
        "y": [None],  # A veces intencional
        "bueno": [None],  # Coloquial
        "pues": [None],  # Coloquial
    },
}

# Frecuencias esperadas aproximadas por cada 10,000 palabras
# Basadas en corpus literario español (aproximación)
EXPECTED_FREQUENCIES = {
    "realmente": 5,
    "obviamente": 2,
    "claramente": 4,
    "sin embargo": 8,
    "por lo tanto": 4,
    "de hecho": 6,
    "además": 12,
    "entonces": 15,
    "después": 20,
    "dijo": 40,  # Muy común en diálogos
    "preguntó": 15,
    "pensó": 10,
    "miró": 12,
    "muy": 30,
    "bastante": 8,
    "mucho": 25,
    "de repente": 5,
    "de pronto": 4,
}


class CrutchWordsDetector(BaseDetector):
    """
    Detector de muletillas y palabras sobreutilizadas.

    Analiza la frecuencia de uso de palabras y expresiones comunes,
    comparándolas con frecuencias esperadas para identificar
    sobreuso.
    """

    def __init__(self, config: Optional["CrutchWordsConfig"] = None):
        self.config = config or CrutchWordsConfig()
        self._patterns = self._compile_patterns()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.CRUTCH_WORDS

    @property
    def requires_spacy(self) -> bool:
        return False  # Funciona con regex

    def _compile_patterns(self) -> dict[str, re.Pattern]:
        """Compila patrones regex para cada muletilla."""
        patterns = {}
        for _category, words in CRUTCH_CATEGORIES.items():
            if isinstance(words, (list, set, tuple)):
                for word in words:
                    # Patrón case insensitive, palabra completa
                    patterns[word] = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        return patterns

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta muletillas sobreutilizadas en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Contar palabras totales para normalizar
        word_count = len(text.split())
        if word_count < 100:
            return []  # Texto demasiado corto para análisis estadístico (min 100 palabras)

        # Contar ocurrencias de cada muletilla
        occurrences: dict[str, list[tuple[int, int]]] = {}

        for word, pattern in self._patterns.items():
            # Filtrar por categoría según configuración
            if not self._is_category_enabled(word):
                continue

            matches = list(pattern.finditer(text))
            if matches:
                occurrences[word] = [(m.start(), m.end()) for m in matches]

        # Analizar frecuencias
        for word, positions in occurrences.items():
            count = len(positions)

            # Verificar mínimo de ocurrencias
            if count < self.config.min_occurrences:
                continue

            # Calcular frecuencia por 10,000 palabras
            frequency = (count / word_count) * 10000

            # Obtener frecuencia esperada
            expected = EXPECTED_FREQUENCIES.get(word, 5)

            # Calcular z-score aproximado
            # Asumimos desviación estándar = esperado * 0.5 (simplificación)
            std_dev = max(expected * 0.5, 1)
            z_score = (frequency - expected) / std_dev

            # Verificar si supera el umbral
            if z_score >= self.config.z_score_threshold:
                # Obtener alternativas
                alternatives = self._get_alternatives(word)

                # Crear issue para la primera ocurrencia
                # (las demás se pueden ver con "buscar en texto")
                first_pos = positions[0]

                explanation = (
                    f'"{word}" aparece {count} veces '
                    f"({frequency:.1f} por 10.000 palabras). "
                    f"Frecuencia esperada: ~{expected}. "
                    f"Considere variar el vocabulario."
                )

                suggestion = None
                if alternatives:
                    valid_alternatives = [a for a in alternatives if a is not None]
                    if valid_alternatives:
                        suggestion = f"Alternativas: {', '.join(valid_alternatives)}"

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type="overused_word",
                        start_char=first_pos[0],
                        end_char=first_pos[1],
                        text=word,
                        explanation=explanation,
                        suggestion=suggestion,
                        confidence=min(0.5 + (z_score - 2) * 0.1, self.config.base_confidence),
                        context=self._extract_context(text, first_pos[0], first_pos[1]),
                        chapter_index=chapter_index,
                        rule_id=f"crutch_{word.replace(' ', '_')}",
                        extra_data={
                            "count": count,
                            "frequency_per_10k": round(frequency, 2),
                            "expected_frequency": expected,
                            "z_score": round(z_score, 2),
                            "all_positions": positions[:20],  # Limitar a 20
                            "alternatives": alternatives,
                        },
                    )
                )

        # Ordenar por z-score (más severos primero)
        issues.sort(key=lambda x: x.extra_data.get("z_score", 0), reverse=True)

        return issues

    def _is_category_enabled(self, word: str) -> bool:
        """Verifica si la categoría de una palabra está habilitada."""
        for category, words in CRUTCH_CATEGORIES.items():
            if isinstance(words, (list, set, tuple)) and word in words:
                if category == "adverbios_modo":
                    return self.config.check_adverbs
                elif category == "conectores":
                    return self.config.check_connectors
                elif category == "verbos_diccion":
                    return self.config.check_speech_verbs
                elif category == "intensificadores":
                    return self.config.check_intensifiers
                elif category in ("coletillas", "inicio_oracion"):
                    return self.config.check_filler_phrases
        return True  # Por defecto habilitado

    def _get_alternatives(self, word: str) -> list[str | None]:
        """Obtiene alternativas para una muletilla."""
        for _category, words in CRUTCH_CATEGORIES.items():
            if isinstance(words, dict) and word in words:
                return words[word]
        return []

    def get_summary(self, text: str) -> dict:
        """
        Genera un resumen de las muletillas encontradas.

        Útil para mostrar estadísticas al usuario.

        Args:
            text: Texto a analizar

        Returns:
            Diccionario con estadísticas
        """
        word_count = len(text.split())
        if word_count < 100:
            return {"word_count": word_count, "analysis": "Texto demasiado corto"}

        summary = {
            "word_count": word_count,
            "by_category": {},
            "top_overused": [],
        }

        for category, words in CRUTCH_CATEGORIES.items():
            category_total = 0
            if isinstance(words, (list, set, tuple)):
                for word in words:
                    pattern = self._patterns.get(word)
                    if pattern:
                        matches = len(pattern.findall(text))
                        if matches > 0:
                            category_total += matches
            summary["by_category"][category] = category_total

        # Top 5 más sobreutilizadas
        all_counts = []
        for word, pattern in self._patterns.items():
            count = len(pattern.findall(text))
            if count >= 3:
                frequency = (count / word_count) * 10000
                expected = EXPECTED_FREQUENCIES.get(word, 5)
                if frequency > expected * 1.5:
                    all_counts.append(
                        {
                            "word": word,
                            "count": count,
                            "frequency": round(frequency, 2),
                            "expected": expected,
                        }
                    )

        all_counts.sort(key=lambda x: x["frequency"], reverse=True)
        summary["top_overused"] = all_counts[:5]

        return summary
