"""
Corrector ortográfico multi-método para español.

Combina múltiples técnicas de detección:
1. Diccionario (hunspell/aspell o fallback interno)
2. Distancia de Levenshtein para typos
3. Patrones regex para errores comunes
4. LLM local para análisis contextual

El sistema usa votación ponderada para determinar
si una palabra es realmente un error.
"""

import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ...core.errors import ErrorSeverity, NLPError
from ...core.result import Result
from .base import (
    COMMON_ACCENT_ERRORS,
    COMMON_HOMOPHONES,
    COMMONLY_CONFUSED,
    DetectionMethod,
    SpellingErrorType,
    SpellingIssue,
    SpellingReport,
    SpellingSeverity,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["SpellingChecker"] = None


def get_spelling_checker() -> "SpellingChecker":
    """Obtener instancia singleton del corrector ortográfico."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SpellingChecker()

    return _instance


def reset_spelling_checker() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Error personalizado
# =============================================================================


@dataclass
class SpellingCheckError(NLPError):
    """Error durante el análisis ortográfico."""

    text_sample: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: str | None = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"Spelling check error: {self.original_error}"
        self.user_message = "Error al verificar ortografía. Continuando con resultados parciales."
        super().__post_init__()


# =============================================================================
# Diccionario español básico
# =============================================================================

# Palabras muy comunes que NO son errores (para evitar falsos positivos)
COMMON_SPANISH_WORDS = {
    # Artículos y preposiciones
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "de",
    "del",
    "al",
    "a",
    "en",
    "con",
    "por",
    "para",
    "sin",
    "sobre",
    "bajo",
    "entre",
    "hacia",
    "hasta",
    "desde",
    "durante",
    # Pronombres
    "yo",
    "tú",
    "él",
    "ella",
    "nosotros",
    "vosotros",
    "ellos",
    "ellas",
    "me",
    "te",
    "se",
    "nos",
    "os",
    "le",
    "les",
    "lo",
    "mi",
    "tu",
    "su",
    "nuestro",
    "vuestro",
    "mío",
    "tuyo",
    "suyo",
    "este",
    "esta",
    "esto",
    "estos",
    "estas",
    "ese",
    "esa",
    "eso",
    "aquel",
    "aquella",
    "aquello",
    "que",
    "quien",
    "cual",
    "cuyo",
    # Verbos comunes (infinitivos)
    "ser",
    "estar",
    "tener",
    "hacer",
    "poder",
    "decir",
    "ir",
    "ver",
    "dar",
    "saber",
    "querer",
    "llegar",
    "pasar",
    "deber",
    "poner",
    "parecer",
    "quedar",
    "creer",
    "hablar",
    "llevar",
    "dejar",
    "seguir",
    "encontrar",
    "llamar",
    "venir",
    "pensar",
    "salir",
    "volver",
    "tomar",
    # Conjugaciones comunes
    "es",
    "era",
    "fue",
    "sido",
    "soy",
    "eres",
    "somos",
    "son",
    "eran",
    "está",
    "estaba",
    "estuvo",
    "estoy",
    "estás",
    "estamos",
    "están",
    "tiene",
    "tenía",
    "tuvo",
    "tengo",
    "tienes",
    "tenemos",
    "tienen",
    "hace",
    "hacía",
    "hizo",
    "hago",
    "haces",
    "hacemos",
    "hacen",
    "puede",
    "podía",
    "pudo",
    "puedo",
    "puedes",
    "podemos",
    "pueden",
    "dice",
    "decía",
    "dijo",
    "digo",
    "dices",
    "decimos",
    "dicen",
    "va",
    "iba",
    "voy",
    "vas",
    "vamos",
    "van",
    "hay",
    "había",
    "hubo",
    "habrá",
    # Adverbios
    "no",
    "sí",
    "ya",
    "más",
    "muy",
    "bien",
    "mal",
    "siempre",
    "nunca",
    "también",
    "tampoco",
    "ahora",
    "después",
    "antes",
    "aquí",
    "allí",
    "hoy",
    "ayer",
    "mañana",
    "luego",
    "pronto",
    "tarde",
    "apenas",
    # Conjunciones
    "y",
    "e",
    "o",
    "u",
    "pero",
    "sino",
    "porque",
    "aunque",
    "si",
    "como",
    "cuando",
    "donde",
    "mientras",
    "pues",
    "ni",
    # Adjetivos comunes
    "todo",
    "toda",
    "todos",
    "todas",
    "otro",
    "otra",
    "otros",
    "otras",
    "mismo",
    "misma",
    "mismos",
    "mismas",
    "nuevo",
    "nueva",
    "bueno",
    "malo",
    "grande",
    "pequeño",
    "primero",
    "último",
    "mejor",
    "peor",
    # Números
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "cien",
    "mil",
    "segundo",
    "tercero",
    # Otras palabras muy comunes
    "cosa",
    "vez",
    "día",
    "año",
    "tiempo",
    "vida",
    "mundo",
    "hombre",
    "mujer",
    "parte",
    "caso",
    "momento",
    "forma",
    "manera",
    "lugar",
    "punto",
    "noche",
    "agua",
    "mano",
    "ojo",
    "casa",
    "gente",
    "país",
    "nombre",
    "hijo",
    "hija",
    "padre",
    "madre",
    "familia",
    "trabajo",
}

# Patrones regex para detectar errores
SPELLING_PATTERNS = [
    # Letras repetidas (más de 2 veces), excluyendo números romanos (III, VIII, etc.)
    (r"(?<![IVXLCDM])(\w)\1{2,}(?![IVXLCDM])", SpellingErrorType.REPEATED_CHAR, "Letras repetidas"),
    # Espacios múltiples en la misma línea (NO saltos de párrafo \n\n)
    (r"[^\S\n]{2,}", SpellingErrorType.TYPO, "Espacios múltiples"),
    # Puntuación duplicada (4+ puntos, o 2+ de ! o ?)
    # NOTA: Excluye ... (puntos suspensivos, que son 3 puntos exactamente)
    (r"\.{4,}", SpellingErrorType.TYPO, "Demasiados puntos (usar ... para suspensivos)"),
    (r"([!?])\1+", SpellingErrorType.TYPO, "Puntuación duplicada"),
    # Coma o punto seguido de letra sin espacio
    (r"[,.](?=[a-záéíóúñ])", SpellingErrorType.TYPO, "Falta espacio después de puntuación"),

    # ============================================================================
    # QUICK WINS - Panel de Expertos (2026-02)
    # ============================================================================

    # 1. "etc..." - redundancia (etc. + puntos suspensivos)
    # Consenso: Alta prioridad, 0% falsos positivos
    (r'\b(etc|etcétera)\.{2,}', SpellingErrorType.TYPO, 'Redundancia: "etc." ya implica continuación (usar "etc." o "...")'),
    (r'\b(etc|etcétera)\.\s*\.{2,}', SpellingErrorType.TYPO, 'Redundancia: "etc." ya implica continuación (usar "etc." o "...")'),

    # 2. Espacio antes de puntuación (excepto apertura ¿ ¡)
    # Consenso: Alta prioridad, <1% falsos positivos
    (r'\s+([,;:!?)\]])', SpellingErrorType.TYPO, 'Espacio antes de puntuación (debe eliminarse)'),

    # 3. Redundancias espaciales comunes
    # Consenso: Alta prioridad, <2% falsos positivos
    (r'\bsubir\s+arriba\b', SpellingErrorType.REDUNDANCY, 'Redundancia: "subir arriba" (usar solo "subir")'),
    (r'\bbajar\s+abajo\b', SpellingErrorType.REDUNDANCY, 'Redundancia: "bajar abajo" (usar solo "bajar")'),
    (r'\bsalir\s+(?:a\s+)?fuera\b', SpellingErrorType.REDUNDANCY, 'Redundancia: "salir fuera" (usar solo "salir")'),
    (r'\bentrar\s+(?:a\s+)?dentro\b', SpellingErrorType.REDUNDANCY, 'Redundancia: "entrar dentro" (usar solo "entrar")'),
    (r'\bvolver\s+a\s+regresar\b', SpellingErrorType.REDUNDANCY, 'Redundancia: "volver a regresar" (usar solo "volver" o "regresar")'),
]


class SpellingChecker:
    """
    Corrector ortográfico multi-método.

    Combina:
    - Diccionario de palabras conocidas
    - Análisis de patrones regex
    - Detección de errores comunes en español
    - LLM para análisis contextual (opcional)
    """

    def __init__(self):
        """Inicializar el corrector."""
        self._hunspell = None
        self._custom_dictionary: set[str] = set()
        self._load_hunspell()

    def _load_hunspell(self) -> None:
        """Intentar cargar hunspell si está disponible."""
        try:
            import hunspell

            # Buscar diccionario español
            dict_paths = [
                "/usr/share/hunspell/es_ES",
                "/usr/share/myspell/es_ES",
                "C:/Program Files/LibreOffice/share/extensions/dict-es/es_ES",
                str(Path(__file__).parent / "dictionaries" / "es_ES"),
            ]
            for path in dict_paths:
                aff_path = f"{path}.aff"
                dic_path = f"{path}.dic"
                if Path(aff_path).exists() and Path(dic_path).exists():
                    self._hunspell = hunspell.HunSpell(dic_path, aff_path)
                    logger.info(f"Hunspell cargado desde {path}")
                    return
            logger.warning("Diccionario hunspell no encontrado, usando fallback")
        except ImportError:
            logger.info("Hunspell no instalado, usando diccionario básico")
        except Exception as e:
            logger.warning(f"Error cargando hunspell: {e}")

    def add_to_dictionary(self, words: list[str]) -> None:
        """Añadir palabras al diccionario personalizado."""
        self._custom_dictionary.update(w.lower() for w in words)

    def check(
        self,
        text: str,
        known_entities: list[str] | None = None,
        use_llm: bool = False,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> Result[SpellingReport]:
        """
        Analizar texto en busca de errores ortográficos.

        Args:
            text: Texto a analizar
            known_entities: Nombres propios conocidos (no marcar como error)
            use_llm: Usar LLM para análisis contextual
            progress_callback: Callback para reportar progreso (0.0-1.0, mensaje)

        Returns:
            Result con SpellingReport
        """
        if not text or not text.strip():
            return Result.success(SpellingReport())

        report = SpellingReport()
        errors: list[NLPError] = []

        # Preparar set de palabras conocidas
        known_words = COMMON_SPANISH_WORDS.copy()
        known_words.update(self._custom_dictionary)
        if known_entities:
            # Añadir entidades y sus variantes
            for entity in known_entities:
                known_words.add(entity.lower())
                # Añadir partes del nombre
                for part in entity.split():
                    known_words.add(part.lower())

        try:
            # Fase 1: Análisis por diccionario (0.0 - 0.3)
            if progress_callback:
                progress_callback(0.0, "Verificando diccionario...")

            dict_issues = self._check_dictionary(text, known_words)
            for issue in dict_issues:
                report.add_issue(issue)

            # Fase 2: Patrones regex (0.3 - 0.4)
            if progress_callback:
                progress_callback(0.3, "Buscando patrones de error...")

            pattern_issues = self._check_patterns(text)
            for issue in pattern_issues:
                report.add_issue(issue)

            # Fase 2.5: Errores semánticos (palabras correctas fuera de contexto) (0.4 - 0.5)
            if progress_callback:
                progress_callback(0.4, "Analizando contexto semántico...")

            semantic_issues = self._check_semantic(text)
            for issue in semantic_issues:
                report.add_issue(issue)

            # Fase 3: Errores comunes en español (0.5 - 0.7)
            if progress_callback:
                progress_callback(0.5, "Analizando errores comunes...")

            common_issues = self._check_common_errors(text, known_words)
            for issue in common_issues:
                report.add_issue(issue)

            # Fase 4: LLM contextual (0.7 - 0.95)
            if use_llm:
                if progress_callback:
                    progress_callback(0.7, "Análisis contextual con LLM...")
                try:
                    llm_issues = self._check_with_llm(text, report.issues)
                    for issue in llm_issues:
                        report.add_issue(issue)
                except Exception as e:
                    logger.warning(f"Error en análisis LLM: {e}")
                    errors.append(SpellingCheckError(text_sample=text[:100], original_error=str(e)))

            # Fase 5: Deduplicar y consolidar (0.95 - 1.0)
            if progress_callback:
                progress_callback(0.95, "Consolidando resultados...")

            report = self._consolidate_report(report)

            # Estadísticas finales
            report.processed_chars = len(text)
            report.processed_words = len(text.split())

            if progress_callback:
                progress_callback(1.0, "Análisis completado")

        except Exception as e:
            logger.error(f"Error en análisis ortográfico: {e}")
            errors.append(
                SpellingCheckError(text_sample=text[:100] if text else "", original_error=str(e))
            )

        if errors:
            # Result.partial devuelve el tipo correcto
            return Result.partial(report, errors)
        return Result.success(report)

    def _check_dictionary(self, text: str, known_words: set[str]) -> list[SpellingIssue]:
        """Verificar palabras contra diccionario."""
        issues: list[SpellingIssue] = []

        # Tokenizar texto
        word_pattern = re.compile(r"\b([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)\b")

        for match in word_pattern.finditer(text):
            word = match.group(1)
            word_lower = word.lower()
            start = match.start()
            end = match.end()

            # Ignorar palabras conocidas
            if word_lower in known_words:
                continue

            # Ignorar palabras muy cortas (1-2 caracteres)
            if len(word) <= 2:
                continue

            # Ignorar si parece nombre propio (mayúscula inicial) y no está
            # al inicio de oración
            if word[0].isupper() and start > 0 and text[start - 1] not in ".!?\n":
                continue

            # Verificar con hunspell si disponible
            is_error = False
            suggestions: list[str] = []

            if self._hunspell:
                if not self._hunspell.spell(word):
                    is_error = True
                    suggestions = self._hunspell.suggest(word)[:5]
            else:
                # Fallback: verificar si parece español válido
                is_error = self._looks_like_error(word)
                if is_error:
                    suggestions = self._generate_suggestions(word)

            if is_error:
                # Obtener contexto (oración)
                sentence = self._extract_sentence(text, start)

                issues.append(
                    SpellingIssue(
                        word=word,
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=SpellingErrorType.MISSPELLING,
                        severity=SpellingSeverity.WARNING,
                        suggestions=suggestions,
                        confidence=0.7 if self._hunspell else 0.5,
                        detection_method=DetectionMethod.DICTIONARY,
                        explanation="Palabra no encontrada en diccionario",
                    )
                )

        return issues

    def _check_patterns(self, text: str) -> list[SpellingIssue]:
        """Buscar errores mediante patrones regex."""
        issues: list[SpellingIssue] = []

        for pattern, error_type, explanation in SPELLING_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                word = match.group(0)
                start = match.start()
                end = match.end()
                sentence = self._extract_sentence(text, start)

                # Generar sugerencia según el tipo
                suggestion = self._fix_pattern_error(word, error_type)

                issues.append(
                    SpellingIssue(
                        word=word,
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=error_type,
                        severity=SpellingSeverity.WARNING,
                        suggestions=[suggestion] if suggestion else [],
                        confidence=0.9,
                        detection_method=DetectionMethod.REGEX,
                        explanation=explanation,
                    )
                )

        return issues

    def _check_semantic(self, text: str) -> list[SpellingIssue]:
        """
        Detectar errores semánticos (palabras correctas fuera de contexto).

        Usa semantic_checker para detectar confusiones como:
        - "riegos de seguridad" (debería ser "riesgos")
        - "actitud necesaria" (debería ser "aptitud")
        - etc.
        """
        try:
            from .semantic_checker import check_semantic_context

            return check_semantic_context(text)
        except Exception as e:
            logger.warning(f"Error en verificación semántica: {e}")
            return []

    def _check_common_errors(self, text: str, known_words: set[str]) -> list[SpellingIssue]:
        """Buscar errores comunes en español."""
        issues: list[SpellingIssue] = []

        # Verificar errores de tildes
        for wrong, correct in COMMON_ACCENT_ERRORS.items():
            # Buscar la palabra sin tilde en contextos donde debería llevarla
            pattern = rf"\b{re.escape(wrong)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                word = match.group(0)
                start = match.start()
                end = match.end()

                # Analizar contexto para determinar si es error
                if self._needs_accent_in_context(text, start, wrong, correct):
                    sentence = self._extract_sentence(text, start)
                    issues.append(
                        SpellingIssue(
                            word=word,
                            start_char=start,
                            end_char=end,
                            sentence=sentence,
                            error_type=SpellingErrorType.ACCENT,
                            severity=SpellingSeverity.WARNING,
                            suggestions=[correct],
                            confidence=0.6,  # Requiere verificación contextual
                            detection_method=DetectionMethod.CONTEXT,
                            explanation=f"Posible falta de tilde: '{wrong}' → '{correct}'",
                        )
                    )

        # Verificar confusiones de homófonos
        for word, alternatives in COMMON_HOMOPHONES.items():
            pattern = rf"\b{re.escape(word)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                end = match.end()

                # Solo marcar si el contexto sugiere confusión
                if self._suggests_homophone_confusion(text, start, word):
                    sentence = self._extract_sentence(text, start)
                    issues.append(
                        SpellingIssue(
                            word=match.group(0),
                            start_char=start,
                            end_char=end,
                            sentence=sentence,
                            error_type=SpellingErrorType.HOMOPHONE,
                            severity=SpellingSeverity.INFO,
                            suggestions=alternatives,
                            confidence=0.4,  # Baja confianza, requiere revisión
                            detection_method=DetectionMethod.CONTEXT,
                            explanation=f"Verificar: ¿'{word}' o '{alternatives[0]}'?",
                        )
                    )

        # Verificar palabras comúnmente confundidas
        for word, alternatives in COMMONLY_CONFUSED.items():
            pattern = rf"\b{re.escape(word)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                # Solo sugerir si el contexto indica posible confusión
                context = text[max(0, start - 30) : min(len(text), start + len(word) + 30)]
                if self._context_suggests_confusion(context, word, alternatives):
                    sentence = self._extract_sentence(text, start)
                    issues.append(
                        SpellingIssue(
                            word=match.group(0),
                            start_char=start,
                            end_char=match.end(),
                            sentence=sentence,
                            error_type=SpellingErrorType.HOMOPHONE,
                            severity=SpellingSeverity.INFO,
                            suggestions=alternatives[:3],
                            confidence=0.3,
                            detection_method=DetectionMethod.CONTEXT,
                            explanation=f"Verificar uso de '{word}'",
                        )
                    )

        return issues

    def _check_with_llm(
        self, text: str, existing_issues: list[SpellingIssue]
    ) -> list[SpellingIssue]:
        """Usar LLM para análisis contextual avanzado."""
        try:
            from ...llm.client import get_llm_client

            client = get_llm_client()
            if not client or not getattr(client, "is_available", lambda: False)():
                return []

            # Preparar prompt con el texto y issues existentes
            existing_words = {i.word for i in existing_issues}

            prompt = f"""Analiza el siguiente texto en español y encuentra errores ortográficos que no estén ya detectados.
NO incluyas estas palabras ya detectadas: {", ".join(existing_words)}

Texto:
{text[:2000]}

Responde SOLO con un JSON array de errores encontrados, cada uno con:
- "word": palabra con error
- "suggestion": corrección sugerida
- "explanation": breve explicación

Si no hay errores adicionales, responde con un array vacío: []"""

            response = client.generate(prompt, max_tokens=500)
            if not response:
                return []

            # Parsear respuesta
            import json

            try:
                # Buscar JSON en la respuesta
                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    errors = json.loads(json_match.group())
                    issues = []
                    for err in errors:
                        word = err.get("word", "")
                        if word and word not in existing_words:
                            # Encontrar posición en texto
                            pos = text.find(word)
                            if pos >= 0:
                                issues.append(
                                    SpellingIssue(
                                        word=word,
                                        start_char=pos,
                                        end_char=pos + len(word),
                                        sentence=self._extract_sentence(text, pos),
                                        error_type=SpellingErrorType.MISSPELLING,
                                        severity=SpellingSeverity.WARNING,
                                        suggestions=[err.get("suggestion", "")],
                                        confidence=0.6,
                                        detection_method=DetectionMethod.LLM,
                                        explanation=err.get("explanation", "Detectado por LLM"),
                                    )
                                )
                    return issues
            except json.JSONDecodeError:
                pass

        except Exception as e:
            logger.debug(f"LLM check failed: {e}")

        return []

    def _consolidate_report(self, report: SpellingReport) -> SpellingReport:
        """Consolidar y deduplicar issues."""
        # Usar diccionario para deduplicar por posición
        unique = report.unique_issues

        # Crear nuevo report con issues únicos
        consolidated = SpellingReport()
        consolidated.ignored_words = report.ignored_words

        for issue in unique.values():
            consolidated.add_issue(issue)

        return consolidated

    def _extract_sentence(self, text: str, position: int) -> str:
        """Extraer la oración que contiene la posición dada."""
        # Buscar inicio de oración
        start = position
        while start > 0 and text[start - 1] not in ".!?\n":
            start -= 1

        # Buscar fin de oración
        end = position
        while end < len(text) and text[end] not in ".!?\n":
            end += 1

        sentence = text[start : end + 1].strip()
        # Limitar longitud
        if len(sentence) > 200:
            # Centrar en la palabra
            word_start = position - start
            context_start = max(0, word_start - 80)
            context_end = min(len(sentence), word_start + 80)
            sentence = "..." + sentence[context_start:context_end] + "..."

        return sentence

    def _looks_like_error(self, word: str) -> bool:
        """Heurística para detectar si una palabra parece error."""
        word_lower = word.lower()

        # Patrones que sugieren error
        error_patterns = [
            r"(.)\1{2,}",  # Más de 2 letras repetidas
            r"[qwx]{2,}",  # Combinaciones raras
            r"^[^aeiouáéíóú]+$",  # Sin vocales (>3 letras)
            r"[bcdfghjklmnñpqrstvwxyz]{4,}",  # 4+ consonantes seguidas
        ]

        if len(word) > 3 and not any(c in word_lower for c in "aeiouáéíóú"):
            return True

        return any(re.search(pattern, word_lower) for pattern in error_patterns)

    def _generate_suggestions(self, word: str) -> list[str]:
        """Generar sugerencias para una palabra."""
        suggestions = []

        # Sugerencia 1: Quitar letras repetidas
        deduped = re.sub(r"(.)\1+", r"\1\1", word)
        if deduped != word:
            suggestions.append(re.sub(r"(.)\1+", r"\1", word))

        # Sugerencia 2: Añadir/quitar tilde común
        accent_map = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}
        for plain, accented in accent_map.items():
            if plain in word.lower():
                suggestions.append(word.lower().replace(plain, accented, 1))

        return suggestions[:5]

    def _fix_pattern_error(self, word: str, error_type: SpellingErrorType) -> str:
        """Generar corrección para error de patrón."""
        if error_type == SpellingErrorType.REPEATED_CHAR:
            return re.sub(r"(.)\1{2,}", r"\1\1", word)
        elif error_type == SpellingErrorType.TYPO:
            if "  " in word:
                return " "
            if re.match(r"([.!?])\1+", word):
                return word[0]
        return ""

    def _needs_accent_in_context(self, text: str, position: int, word: str, accented: str) -> bool:
        """Determinar si la palabra necesita tilde según contexto."""
        # Obtener contexto
        context_start = max(0, position - 20)
        context_end = min(len(text), position + len(word) + 20)
        context = text[context_start:context_end].lower()

        # Caso especial: "mi" vs "mí"
        if word == "mi":
            return self._mi_needs_accent(text, position)

        # Reglas contextuales para tildes diacríticas
        # NOTA: Estas reglas deben ser MUY conservadoras para evitar falsos positivos
        rules = {
            "mas": lambda c: "pero" not in c and "sin embargo" not in c,
            "si": lambda c: "?" in c or "!" in c or "claro" in c or "por supuesto" in c,
            "el": lambda c: position > 0 and text[position - 1] in ".,;:",
            "tu": lambda c: "?" in c or "eres" in c or "tienes" in c,
        }

        if word in rules:
            return rules[word](context)

        return False

    def _mi_needs_accent(self, text: str, position: int) -> bool:
        """
        Determinar si 'mi' necesita tilde.

        'mí' (con tilde) = pronombre personal preposicional
        - Ejemplos: para mí, a mí, de mí, por mí, ante mí

        'mi' (sin tilde) = adjetivo posesivo
        - Ejemplos: mi casa, mi hermana, mi sobrina

        La tilde SOLO se requiere cuando va precedido inmediatamente por una preposición.
        """
        # Verificar caracteres previos a "mi"
        if position < 1:
            return False

        # Obtener las palabras anteriores (hasta 20 caracteres)
        # NO hacer strip() para no perder espacios al final
        preceding_text = text[max(0, position - 20):position].lower()

        # Preposiciones que requieren "mí" con tilde
        # El patrón verifica que termine con la preposición + espacios antes de "mi"
        prep_patterns = [
            r'\bpara\s+$',      # para mí
            r'\ba\s+$',          # a mí
            r'\bde\s+$',         # de mí
            r'\bpor\s+$',        # por mí
            r'\bante\s+$',       # ante mí
            r'\bcontra\s+$',     # contra mí
            r'\bentre\s+$',      # entre ... y mí
            r'\bhacia\s+$',      # hacia mí
            r'\bsin\s+$',        # sin mí
            r'\bcon\s+$',        # con mí (poco común pero válido)
        ]

        for pattern in prep_patterns:
            if re.search(pattern, preceding_text):
                return True

        return False

    def _suggests_homophone_confusion(self, text: str, position: int, word: str) -> bool:
        """Determinar si el contexto sugiere confusión de homófonos."""
        # Por ahora, solo marcar casos muy específicos
        context_start = max(0, position - 30)
        context_end = min(len(text), position + len(word) + 30)
        context = text[context_start:context_end].lower()

        # "a" vs "ha" (verbo haber)
        if word.lower() == "a":
            return self._a_should_be_ha(text, position)

        # "haber" vs "a ver"
        if word.lower() == "haber":
            if "vamos" in context or "veamos" in context:
                return True
        elif word.lower() == "a ver" and ("podido" in context or "debido" in context):
            return True

        # "hay" vs "ahí" vs "ay"
        return bool(word.lower() == "hay" and ("allí" in context or "aquí" in context))

    def _a_should_be_ha(self, text: str, position: int) -> bool:
        """
        Determinar si 'a' (preposición) debería ser 'ha' (verbo haber).

        'a' (sin h) = preposición de movimiento/dirección
        - Ejemplos: voy a casa, salió a comprar

        'ha' (con h) = verbo haber (3ª persona singular presente)
        - Ejemplos: ha estado, ha venido, ha comido

        Indicadores: participios (terminados en -ado, -ido, -to, -cho, etc.)
        """
        # Verificar si hay un participio después de "a"
        following_text = text[position + 1:min(len(text), position + 30)].strip().lower()

        # Participios regulares e irregulares comunes
        participle_patterns = [
            r'^\s*(estado|sido|tenido|habido)',  # haber
            r'^\s*\w+ado\b',   # participios -ado (hablado, comido, etc.)
            r'^\s*\w+ido\b',   # participios -ido (vendido, vivido, etc.)
            r'^\s*(hecho|dicho|visto|puesto|escrito|roto|abierto|cubierto|vuelto|muerto)',  # irregulares
        ]

        for pattern in participle_patterns:
            if re.search(pattern, following_text):
                return True

        return False

    def _context_suggests_confusion(self, context: str, word: str, alternatives: list[str]) -> bool:
        """Determinar si el contexto sugiere confusión entre palabras."""
        # Solo retornar True para casos muy claros
        # Por defecto, no marcar para evitar demasiados falsos positivos
        return False
