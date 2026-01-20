"""
Corrector gramatical multi-método para español.

Combina múltiples técnicas de detección:
1. Reglas propias de español (dequeísmo, queísmo, laísmo, etc.)
2. Análisis de dependencias con spaCy
3. Patrones regex para errores comunes
4. LLM local para análisis contextual (opcional)
5. LanguageTool local (+2000 reglas para español, opcional)

El sistema detecta:
- Concordancia (género, número, sujeto-verbo)
- Uso de preposiciones (dequeísmo, queísmo)
- Pronombres (leísmo, laísmo, loísmo)
- Redundancias y pleonasmos
- Estructura oracional
- Errores contextuales complejos (via LanguageTool)

Configuración:
- Las reglas propias siempre están activas (sin dependencias)
- LanguageTool es opcional (requiere Java + servidor)
- LLM es opcional (requiere Ollama)
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, TYPE_CHECKING

from ...core.result import Result
from ...core.errors import NLPError, ErrorSeverity
from ...core.config import get_config, GrammarConfig
from .base import (
    GrammarIssue,
    GrammarReport,
    GrammarErrorType,
    GrammarSeverity,
    GrammarDetectionMethod,
    GRAMMAR_PATTERNS,
    REDUNDANT_EXPRESSIONS,
    VERB_PREPOSITION_RULES,
    VERBS_WITHOUT_DE_QUE,
    VERBS_WITH_DE_QUE,
)
from .spanish_rules import (
    apply_spanish_rules,
    SpanishRulesConfig,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["GrammarChecker"] = None


def get_grammar_checker() -> "GrammarChecker":
    """Obtener instancia singleton del corrector gramatical."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GrammarChecker()

    return _instance


def reset_grammar_checker() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Error personalizado
# =============================================================================

@dataclass
class GrammarCheckError(NLPError):
    """Error durante el análisis gramatical."""

    text_sample: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"Grammar check error: {self.original_error}"
        self.user_message = (
            "Error al verificar gramática. Continuando con resultados parciales."
        )
        super().__post_init__()


class GrammarChecker:
    """
    Corrector gramatical multi-método.

    Combina:
    - Reglas propias de español (siempre activas, sin dependencias)
    - Análisis de dependencias spaCy
    - Patrones regex
    - LLM para análisis contextual (opcional)
    - LanguageTool local (+2000 reglas, opcional)

    La configuración se lee de AppConfig.grammar o se puede pasar explícitamente.
    """

    def __init__(self, config: Optional[GrammarConfig] = None):
        """
        Inicializar el corrector.

        Args:
            config: Configuración de gramática (opcional, usa config global si no se pasa)
        """
        self._config = config or get_config().grammar
        self._nlp = None
        self._lt_client = None
        self._load_spacy()
        if self._config.use_languagetool:
            self._load_languagetool()

    def _load_spacy(self) -> None:
        """Cargar modelo spaCy si está disponible."""
        try:
            from ..spacy_gpu import load_spacy_model
            self._nlp = load_spacy_model()
            logger.info("spaCy cargado para análisis gramatical")
        except Exception as e:
            logger.warning(f"spaCy no disponible: {e}")

    def _load_languagetool(self) -> None:
        """Cargar cliente LanguageTool, iniciando el servidor si es necesario."""
        try:
            from .languagetool_client import get_languagetool_client
            from .languagetool_manager import ensure_languagetool_running, is_languagetool_installed

            self._lt_client = get_languagetool_client()

            # Si no está disponible pero está instalado, intentar iniciarlo
            if not self._lt_client.is_available():
                if is_languagetool_installed():
                    logger.info("LanguageTool instalado pero no corriendo, iniciando servidor...")
                    if ensure_languagetool_running():
                        # Refrescar estado del cliente
                        self._lt_client.refresh_availability()
                        logger.info("LanguageTool iniciado correctamente")
                    else:
                        logger.warning("No se pudo iniciar LanguageTool automáticamente")
                else:
                    logger.info("LanguageTool no instalado. Ejecutar: python scripts/setup_languagetool.py")

            if self._lt_client.is_available():
                logger.info("LanguageTool disponible para análisis gramatical avanzado")
            else:
                self._lt_client = None

        except Exception as e:
            logger.warning(f"LanguageTool no disponible: {e}")
            self._lt_client = None

    @property
    def languagetool_available(self) -> bool:
        """Verificar si LanguageTool está disponible."""
        return self._lt_client is not None and self._lt_client.is_available()

    def reload_languagetool(self) -> bool:
        """
        Recargar LanguageTool (útil después de activarlo en settings).

        Returns:
            True si LanguageTool está ahora disponible
        """
        self._lt_client = None
        self._load_languagetool()
        return self.languagetool_available

    def check(
        self,
        text: str,
        use_llm: Optional[bool] = None,
        use_languagetool: Optional[bool] = None,
        check_style: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Result[GrammarReport]:
        """
        Analizar texto en busca de errores gramaticales.

        Args:
            text: Texto a analizar
            use_llm: Usar LLM para análisis (None = usar config)
            use_languagetool: Usar LanguageTool si disponible (None = usar config)
            check_style: Incluir sugerencias de estilo
            progress_callback: Callback para reportar progreso (0.0-1.0, mensaje)

        Returns:
            Result con GrammarReport
        """
        if not text or not text.strip():
            return Result.success(GrammarReport())

        # Usar valores de config si no se especifican
        use_llm = use_llm if use_llm is not None else self._config.use_llm
        use_languagetool = use_languagetool if use_languagetool is not None else self._config.use_languagetool

        report = GrammarReport()
        errors: list[NLPError] = []

        try:
            # Fase 1: Reglas propias de español (0.0 - 0.4)
            # Estas siempre se ejecutan, son nuestras reglas sin dependencias
            if progress_callback:
                progress_callback(0.0, "Aplicando reglas de español...")

            spanish_issues = self._check_with_spanish_rules(text)
            for issue in spanish_issues:
                report.add_issue(issue)

            # Fase 2: Patrones regex adicionales (0.4 - 0.5)
            if progress_callback:
                progress_callback(0.4, "Buscando patrones adicionales...")

            pattern_issues = self._check_patterns(text)
            for issue in pattern_issues:
                report.add_issue(issue)

            # Fase 3: Estructura oracional (0.5 - 0.6)
            if check_style and self._config.check_sentence_structure:
                if progress_callback:
                    progress_callback(0.5, "Analizando estructura...")

                structure_issues = self._check_sentence_structure(text)
                for issue in structure_issues:
                    report.add_issue(issue)

            # Fase 4: LanguageTool - OPCIONAL (0.6 - 0.8)
            if use_languagetool and self._lt_client:
                if progress_callback:
                    progress_callback(0.6, "Análisis avanzado...")
                try:
                    lt_issues = self._check_with_languagetool(text, report.issues)
                    for issue in lt_issues:
                        report.add_issue(issue)
                    logger.debug(f"LanguageTool detectó {len(lt_issues)} errores adicionales")
                except Exception as e:
                    logger.warning(f"Error en análisis LanguageTool: {e}")
                    errors.append(GrammarCheckError(
                        text_sample=text[:100],
                        original_error=f"LanguageTool: {e}"
                    ))

            # Fase 5: LLM contextual - OPCIONAL (0.8 - 0.95)
            if use_llm:
                if progress_callback:
                    progress_callback(0.8, "Análisis contextual...")
                try:
                    llm_issues = self._check_with_llm(text, report.issues)
                    for issue in llm_issues:
                        report.add_issue(issue)
                except Exception as e:
                    logger.warning(f"Error en análisis LLM: {e}")
                    errors.append(GrammarCheckError(
                        text_sample=text[:100],
                        original_error=str(e)
                    ))

            # Fase 6: Consolidar (0.95 - 1.0)
            if progress_callback:
                progress_callback(0.95, "Consolidando resultados...")

            report = self._consolidate_report(report)

            # Calcular confianza mínima efectiva basada en herramientas activas
            # Las herramientas adicionales (LT, LLM) validan los resultados de spaCy
            # reduciendo falsos positivos. Sin ellas, necesitamos umbral más alto.
            #
            # Niveles de ajuste:
            # - spaCy solo: +0.15 (más falsos positivos sin validación)
            # - spaCy + LT: +0.05 (LT valida concordancia y errores comunes)
            # - spaCy + LLM: +0.05 (LLM valida contextualmente)
            # - spaCy + LT + LLM: +0.0 (máxima precisión, usar confianza base)
            #
            lt_active = use_languagetool and self._lt_client is not None
            llm_active = use_llm

            confidence_adjustment = 0.0
            tools_active = ["spaCy"]

            if not lt_active and not llm_active:
                # Solo spaCy: mayor riesgo de falsos positivos
                confidence_adjustment = 0.15
            elif lt_active and not llm_active:
                # spaCy + LT: LT valida muchos casos
                confidence_adjustment = 0.05
                tools_active.append("LanguageTool")
            elif not lt_active and llm_active:
                # spaCy + LLM: LLM valida contextualmente
                confidence_adjustment = 0.05
                tools_active.append("LLM")
            else:
                # spaCy + LT + LLM: máxima precisión
                confidence_adjustment = 0.0
                tools_active.extend(["LanguageTool", "LLM"])

            effective_min_confidence = min(
                self._config.min_confidence + confidence_adjustment,
                0.85  # Tope máximo para no filtrar todo
            )

            if confidence_adjustment > 0:
                logger.debug(
                    f"Herramientas activas: {', '.join(tools_active)}. "
                    f"Confianza mínima ajustada: {self._config.min_confidence} → {effective_min_confidence}"
                )

            # Filtrar por confianza mínima
            report.issues = [
                i for i in report.issues
                if i.confidence >= effective_min_confidence
            ]

            # Estadísticas
            report.processed_chars = len(text)
            report.processed_sentences = len(self._split_sentences(text))

            if progress_callback:
                progress_callback(1.0, "Análisis completado")

        except Exception as e:
            logger.error(f"Error en análisis gramatical: {e}")
            errors.append(GrammarCheckError(
                text_sample=text[:100] if text else "",
                original_error=str(e)
            ))

        if errors:
            return Result.partial(report, errors)
        return Result.success(report)

    def _check_with_spanish_rules(self, text: str) -> list[GrammarIssue]:
        """
        Aplicar reglas propias de español.

        Estas reglas no tienen dependencias externas (solo spaCy que ya usamos).
        """
        if not self._nlp:
            return []

        try:
            doc = self._nlp(text)

            # Configurar qué reglas aplicar desde la config
            rules_config = SpanishRulesConfig(
                check_dequeismo=self._config.check_dequeismo,
                check_queismo=self._config.check_queismo,
                check_laismo=self._config.check_laismo,
                check_loismo=self._config.check_loismo,
                check_gender=self._config.check_gender_agreement,
                check_number=self._config.check_number_agreement,
                check_redundancy=self._config.check_redundancy,
                check_punctuation=self._config.check_punctuation,
                check_other=True,
                use_spacy_analysis=self._config.use_spacy_analysis,
                min_confidence=self._config.min_confidence,
            )

            return apply_spanish_rules(doc, rules_config)

        except Exception as e:
            logger.warning(f"Error aplicando reglas españolas: {e}")
            return []

    def _check_patterns(self, text: str) -> list[GrammarIssue]:
        """Buscar errores mediante patrones regex."""
        issues: list[GrammarIssue] = []

        for pattern, error_type, explanation in GRAMMAR_PATTERNS:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matched_text = match.group(0)
                    start = match.start()
                    end = match.end()
                    sentence = self._extract_sentence(text, start)

                    # Generar sugerencia
                    suggestion = self._generate_suggestion(
                        matched_text, error_type
                    )

                    issues.append(GrammarIssue(
                        text=matched_text,
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=error_type,
                        severity=GrammarSeverity.WARNING,
                        suggestion=suggestion,
                        confidence=0.8,
                        detection_method=GrammarDetectionMethod.REGEX,
                        explanation=explanation,
                        rule_id=f"REGEX_{error_type.value.upper()}"
                    ))
            except re.error as e:
                logger.warning(f"Error en patrón regex: {e}")

        return issues

    def _check_redundancies(self, text: str) -> list[GrammarIssue]:
        """Detectar expresiones redundantes."""
        issues: list[GrammarIssue] = []
        text_lower = text.lower()

        for redundant, correction in REDUNDANT_EXPRESSIONS.items():
            pattern = rf'\b{re.escape(redundant)}\b'
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                start = match.start()
                end = match.end()
                original = text[start:end]  # Preservar mayúsculas originales
                sentence = self._extract_sentence(text, start)

                issues.append(GrammarIssue(
                    text=original,
                    start_char=start,
                    end_char=end,
                    sentence=sentence,
                    error_type=GrammarErrorType.REDUNDANCY,
                    severity=GrammarSeverity.STYLE,
                    suggestion=correction,
                    confidence=0.9,
                    detection_method=GrammarDetectionMethod.RULE,
                    explanation=f"Expresión redundante: '{redundant}' → '{correction}'",
                    rule_id="REDUNDANCY"
                ))

        return issues

    def _check_with_spacy(self, text: str) -> list[GrammarIssue]:
        """Análisis gramatical con spaCy."""
        issues: list[GrammarIssue] = []

        if not self._nlp:
            return issues

        try:
            doc = self._nlp(text)

            # Verificar concordancia sujeto-verbo
            for sent in doc.sents:
                sent_issues = self._check_sentence_agreement(sent, text)
                issues.extend(sent_issues)

            # Verificar uso de pronombres
            pronoun_issues = self._check_pronouns(doc, text)
            issues.extend(pronoun_issues)

        except Exception as e:
            logger.warning(f"Error en análisis spaCy: {e}")

        return issues

    def _check_sentence_agreement(
        self,
        sent: Any,  # spacy.tokens.Span
        full_text: str
    ) -> list[GrammarIssue]:
        """Verificar concordancia en una oración."""
        issues: list[GrammarIssue] = []

        for token in sent:
            # Verificar concordancia artículo-sustantivo
            if token.pos_ == "DET" and token.head.pos_ == "NOUN":
                det = token
                noun = token.head

                # Obtener género y número
                det_morph = det.morph
                noun_morph = noun.morph

                det_gender = det_morph.get("Gender", [""])[0] if det_morph.get("Gender") else ""
                det_number = det_morph.get("Number", [""])[0] if det_morph.get("Number") else ""
                noun_gender = noun_morph.get("Gender", [""])[0] if noun_morph.get("Gender") else ""
                noun_number = noun_morph.get("Number", [""])[0] if noun_morph.get("Number") else ""

                # Verificar concordancia de género
                if det_gender and noun_gender and det_gender != noun_gender:
                    start = det.idx
                    end = noun.idx + len(noun.text)
                    sentence = self._extract_sentence(full_text, start)

                    issues.append(GrammarIssue(
                        text=full_text[start:end],
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=GrammarErrorType.GENDER_AGREEMENT,
                        severity=GrammarSeverity.ERROR,
                        confidence=0.85,
                        detection_method=GrammarDetectionMethod.SPACY_DEP,
                        explanation=f"Discordancia de género: '{det.text}' ({det_gender}) + '{noun.text}' ({noun_gender})",
                        affected_words=[det.text, noun.text],
                        grammatical_context={
                            "det_gender": det_gender,
                            "noun_gender": noun_gender,
                        }
                    ))

                # Verificar concordancia de número
                if det_number and noun_number and det_number != noun_number:
                    start = det.idx
                    end = noun.idx + len(noun.text)
                    sentence = self._extract_sentence(full_text, start)

                    issues.append(GrammarIssue(
                        text=full_text[start:end],
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=GrammarErrorType.NUMBER_AGREEMENT,
                        severity=GrammarSeverity.ERROR,
                        confidence=0.85,
                        detection_method=GrammarDetectionMethod.SPACY_DEP,
                        explanation=f"Discordancia de número: '{det.text}' ({det_number}) + '{noun.text}' ({noun_number})",
                        affected_words=[det.text, noun.text],
                        grammatical_context={
                            "det_number": det_number,
                            "noun_number": noun_number,
                        }
                    ))

            # Verificar concordancia sujeto-verbo
            if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                subj = token
                verb = token.head

                subj_morph = subj.morph
                verb_morph = verb.morph

                subj_number = subj_morph.get("Number", [""])[0] if subj_morph.get("Number") else ""
                verb_number = verb_morph.get("Number", [""])[0] if verb_morph.get("Number") else ""

                if subj_number and verb_number and subj_number != verb_number:
                    # Evitar falsos positivos con pronombres relativos
                    if subj.text.lower() not in ["que", "quien", "cual", "cuyo"]:
                        start = min(subj.idx, verb.idx)
                        end = max(subj.idx + len(subj.text), verb.idx + len(verb.text))
                        sentence = self._extract_sentence(full_text, start)

                        issues.append(GrammarIssue(
                            text=full_text[start:end],
                            start_char=start,
                            end_char=end,
                            sentence=sentence,
                            error_type=GrammarErrorType.SUBJECT_VERB_AGREEMENT,
                            severity=GrammarSeverity.ERROR,
                            confidence=0.75,
                            detection_method=GrammarDetectionMethod.SPACY_DEP,
                            explanation=f"Discordancia sujeto-verbo: '{subj.text}' ({subj_number}) + '{verb.text}' ({verb_number})",
                            affected_words=[subj.text, verb.text],
                            grammatical_context={
                                "subj_number": subj_number,
                                "verb_number": verb_number,
                            }
                        ))

        return issues

    def _check_pronouns(
        self,
        doc: Any,  # spacy.tokens.Doc
        full_text: str
    ) -> list[GrammarIssue]:
        """Verificar uso correcto de pronombres (leísmo, laísmo, loísmo)."""
        issues: list[GrammarIssue] = []

        # Detectar laísmo y loísmo (más claros que leísmo)
        for token in doc:
            if token.text.lower() in ["la", "las", "lo", "los"]:
                # Verificar si es complemento indirecto (debería ser le/les)
                if token.dep_ == "iobj":
                    # Es un probable laísmo/loísmo
                    if token.text.lower() in ["la", "las"]:
                        error_type = GrammarErrorType.LAISMO
                        suggestion = "le" if token.text.lower() == "la" else "les"
                    else:
                        error_type = GrammarErrorType.LOISMO
                        suggestion = "le" if token.text.lower() == "lo" else "les"

                    sentence = self._extract_sentence(full_text, token.idx)

                    issues.append(GrammarIssue(
                        text=token.text,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        sentence=sentence,
                        error_type=error_type,
                        severity=GrammarSeverity.WARNING,
                        suggestion=suggestion,
                        confidence=0.6,  # Requiere verificación
                        detection_method=GrammarDetectionMethod.SPACY_DEP,
                        explanation=f"Posible {error_type.value}: usar '{suggestion}' para complemento indirecto",
                        affected_words=[token.text],
                    ))

        return issues

    def _check_prepositions(self, text: str) -> list[GrammarIssue]:
        """Verificar uso correcto de preposiciones."""
        issues: list[GrammarIssue] = []

        # Dequeísmo: verbos que NO llevan "de" antes de "que"
        for verb in VERBS_WITHOUT_DE_QUE:
            pattern = rf'\b{verb}\s+de\s+que\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                end = match.end()
                sentence = self._extract_sentence(text, start)

                # Sugerencia: quitar "de"
                original = match.group(0)
                suggestion = re.sub(r'\s+de\s+', ' ', original)

                issues.append(GrammarIssue(
                    text=original,
                    start_char=start,
                    end_char=end,
                    sentence=sentence,
                    error_type=GrammarErrorType.DEQUEISMO,
                    severity=GrammarSeverity.ERROR,
                    suggestion=suggestion,
                    confidence=0.9,
                    detection_method=GrammarDetectionMethod.RULE,
                    explanation=f"Dequeísmo: '{verb}' no lleva 'de' antes de 'que'",
                    rule_id="DEQUEISMO"
                ))

        # Queísmo: verbos que SÍ llevan "de" antes de "que"
        for verb in VERBS_WITH_DE_QUE:
            # Buscar verbo seguido de "que" sin "de"
            pattern = rf'\b{verb}\s+que\b(?!\s*de)'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                end = match.end()
                sentence = self._extract_sentence(text, start)

                # Verificar que no haya ya un "de" antes
                context_before = text[max(0, start-10):start].lower()
                if "de" not in context_before:
                    original = match.group(0)
                    suggestion = original.replace(" que", " de que")

                    issues.append(GrammarIssue(
                        text=original,
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=GrammarErrorType.QUEISMO,
                        severity=GrammarSeverity.WARNING,
                        suggestion=suggestion,
                        confidence=0.7,
                        detection_method=GrammarDetectionMethod.RULE,
                        explanation=f"Queísmo: '{verb}' requiere 'de' antes de 'que'",
                        rule_id="QUEISMO"
                    ))

        return issues

    def _check_sentence_structure(self, text: str) -> list[GrammarIssue]:
        """Verificar estructura de oraciones."""
        issues: list[GrammarIssue] = []
        sentences = self._split_sentences(text)

        # Lemas de verbos copulativos y auxiliares que inician oraciones válidas
        # Usar lemas permite cubrir todas las formas conjugadas automáticamente
        copulative_lemmas = {'ser', 'estar', 'parecer', 'haber', 'tener'}

        for sent_start, sent_end, sentence in sentences:
            word_count = len(sentence.split())

            # Oraciones muy largas (>60 palabras)
            if word_count > 60:
                issues.append(GrammarIssue(
                    text=sentence[:50] + "...",
                    start_char=sent_start,
                    end_char=sent_end,
                    sentence=sentence,
                    error_type=GrammarErrorType.RUN_ON_SENTENCE,
                    severity=GrammarSeverity.STYLE,
                    confidence=0.7,
                    detection_method=GrammarDetectionMethod.HEURISTIC,
                    explanation=f"Oración muy larga ({word_count} palabras). Considerar dividirla.",
                    rule_id="LONG_SENTENCE"
                ))

            # Oraciones sin verbo principal (fragmentos)
            # Ignorar texto entre comillas (diálogos, descripciones, citas)
            sentence_stripped = sentence.strip()
            is_quoted = (
                (sentence_stripped.startswith('"') or sentence_stripped.startswith("'") or
                 sentence_stripped.startswith('«') or sentence_stripped.startswith('"')) or
                (sentence_stripped.endswith('"') or sentence_stripped.endswith("'") or
                 sentence_stripped.endswith('»') or sentence_stripped.endswith('"'))
            )

            # Ignorar listas descriptivas (secuencias de adjetivos/sustantivos separados por comas)
            # Patrón: "Cabello negro, ojos azules, piel morena" - típico de descripciones de personajes
            is_descriptive_list = (
                sentence.count(',') >= 1 and
                word_count < 15 and
                not any(word.lower() in ['que', 'pero', 'porque', 'cuando', 'donde', 'como', 'si']
                       for word in sentence.split())
            )

            # Necesitamos spaCy para análisis de lemas y estructura
            if word_count > 5 and self._nlp and not is_quoted and not is_descriptive_list:
                try:
                    doc = self._nlp(sentence)

                    # Verificar si empieza con verbo copulativo (usando lema)
                    first_token = doc[0] if len(doc) > 0 else None
                    starts_with_copulative = (
                        first_token is not None and
                        first_token.lemma_.lower() in copulative_lemmas
                    )

                    # Ignorar construcciones literarias con adjetivos yuxtapuestos después de coma
                    # "Era un hombre muy alto, delgado como un junco."
                    has_literary_adjective_pattern = (
                        starts_with_copulative and
                        ',' in sentence and
                        self._has_adjective_after_comma(doc)
                    )

                    # Si empieza con copulativo o tiene patrón literario, no es fragmento
                    if starts_with_copulative or has_literary_adjective_pattern:
                        continue

                    # Buscar verbo principal: VERB con dep ROOT/ccomp/xcomp
                    # O AUX con dep ROOT (verbos copulativos como "era", "estaba")
                    has_main_verb = any(
                        (t.pos_ == "VERB" and t.dep_ in ["ROOT", "ccomp", "xcomp"]) or
                        (t.pos_ == "AUX" and t.dep_ == "ROOT")
                        for t in doc
                    )
                    if not has_main_verb:
                        issues.append(GrammarIssue(
                            text=sentence[:50] + "..." if len(sentence) > 50 else sentence,
                            start_char=sent_start,
                            end_char=sent_end,
                            sentence=sentence,
                            error_type=GrammarErrorType.SENTENCE_FRAGMENT,
                            severity=GrammarSeverity.WARNING,
                            confidence=0.5,
                            detection_method=GrammarDetectionMethod.SPACY_DEP,
                            explanation="Posible fragmento de oración (sin verbo principal)",
                            rule_id="FRAGMENT"
                        ))
                except Exception:
                    pass

            # Coma-splice: coma donde debería ir punto
            comma_splice_pattern = r'[a-záéíóúñ]+,\s+[a-záéíóúñ]+\s+[a-záéíóúñ]+,'
            for match in re.finditer(comma_splice_pattern, sentence):
                # Verificar que no sea una enumeración
                context = sentence[max(0, match.start()-20):match.end()+20]
                if not re.search(r',\s*y\s*', context):
                    issues.append(GrammarIssue(
                        text=match.group(0),
                        start_char=sent_start + match.start(),
                        end_char=sent_start + match.end(),
                        sentence=sentence,
                        error_type=GrammarErrorType.COMMA_SPLICE,
                        severity=GrammarSeverity.INFO,
                        confidence=0.4,
                        detection_method=GrammarDetectionMethod.HEURISTIC,
                        explanation="Posible coma-splice: considerar usar punto o conjunción",
                        rule_id="COMMA_SPLICE"
                    ))

        return issues

    def _check_with_llm(
        self,
        text: str,
        existing_issues: list[GrammarIssue]
    ) -> list[GrammarIssue]:
        """Usar LLM para análisis contextual avanzado."""
        try:
            from ...llm.client import get_llm_client

            client = get_llm_client()
            if not client or not client.is_available():
                return []

            # Preparar contexto de issues existentes
            existing_texts = {i.text for i in existing_issues}

            prompt = f"""Analiza el siguiente texto en español y encuentra errores gramaticales que no estén ya detectados.
Errores ya detectados (NO incluir): {', '.join(list(existing_texts)[:10])}

Texto:
{text[:2000]}

Busca específicamente:
- Concordancia de género y número
- Uso incorrecto de preposiciones
- Tiempos verbales incorrectos
- Oraciones mal estructuradas

Responde SOLO con un JSON array de errores encontrados:
[{{"text": "fragmento con error", "correction": "corrección", "type": "tipo de error", "explanation": "explicación"}}]

Si no hay errores adicionales, responde: []"""

            response = client.generate(prompt, max_tokens=500)
            if not response:
                return []

            # Parsear respuesta
            import json
            try:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    errors = json.loads(json_match.group())
                    issues = []
                    for err in errors:
                        err_text = err.get("text", "")
                        if err_text and err_text not in existing_texts:
                            pos = text.find(err_text)
                            if pos >= 0:
                                # Mapear tipo de error
                                error_type = self._map_llm_error_type(
                                    err.get("type", "")
                                )

                                issues.append(GrammarIssue(
                                    text=err_text,
                                    start_char=pos,
                                    end_char=pos + len(err_text),
                                    sentence=self._extract_sentence(text, pos),
                                    error_type=error_type,
                                    severity=GrammarSeverity.WARNING,
                                    suggestion=err.get("correction"),
                                    confidence=0.6,
                                    detection_method=GrammarDetectionMethod.LLM,
                                    explanation=err.get("explanation", "Detectado por LLM")
                                ))
                    return issues
            except json.JSONDecodeError:
                pass

        except Exception as e:
            logger.debug(f"LLM check failed: {e}")

        return []

    def _check_with_languagetool(
        self,
        text: str,
        existing_issues: list[GrammarIssue]
    ) -> list[GrammarIssue]:
        """
        Usar LanguageTool para análisis gramatical avanzado.

        LanguageTool proporciona +2000 reglas para español incluyendo:
        - Análisis contextual (distingue "de que" correcto vs incorrecto)
        - Concordancia compleja
        - Errores tipográficos contextuales
        - Reglas de estilo específicas

        Args:
            text: Texto a analizar
            existing_issues: Issues ya detectadas (para evitar duplicados)

        Returns:
            Lista de GrammarIssue adicionales
        """
        if not self._lt_client:
            return []

        issues: list[GrammarIssue] = []

        # Posiciones ya detectadas por otros métodos
        existing_positions = {
            (issue.start_char, issue.end_char)
            for issue in existing_issues
        }

        # Usar check_chunked para manejar textos largos
        result = self._lt_client.check_chunked(text)

        if result.is_failure:
            logger.warning(f"LanguageTool check failed: {result.error}")
            return []

        lt_result = result.value

        for match in lt_result.matches:
            # Evitar duplicados por posición
            pos_key = (match.offset, match.offset + match.length)
            if pos_key in existing_positions:
                continue

            # Mapear categoría de LT a nuestro GrammarErrorType
            error_type = self._map_lt_category(match.rule_category, match.rule_id)

            # Mapear severidad
            severity = self._map_lt_severity(match.rule_category)

            # Extraer texto del error
            error_text = text[match.offset:match.offset + match.length]

            # Primera sugerencia como corrección
            suggestion = match.replacements[0] if match.replacements else None

            # Extraer oración de contexto
            sentence = self._extract_sentence(text, match.offset)

            issues.append(GrammarIssue(
                text=error_text,
                start_char=match.offset,
                end_char=match.offset + match.length,
                sentence=sentence,
                error_type=error_type,
                severity=severity,
                suggestion=suggestion,
                confidence=0.85,  # Alta confianza en LT
                detection_method=GrammarDetectionMethod.LANGUAGETOOL,
                explanation=match.message,
                rule_id=match.rule_id,
            ))

            # Marcar posición como usada
            existing_positions.add(pos_key)

        return issues

    def _map_lt_category(self, category: str, rule_id: str) -> GrammarErrorType:
        """Mapear categoría de LanguageTool a GrammarErrorType."""
        category_lower = category.lower()
        rule_id_lower = rule_id.lower()

        # Mapeo por rule_id específico
        if "dequeismo" in rule_id_lower:
            return GrammarErrorType.DEQUEISMO
        if "queismo" in rule_id_lower:
            return GrammarErrorType.QUEISMO
        if "laismo" in rule_id_lower:
            return GrammarErrorType.LAISMO
        if "leismo" in rule_id_lower:
            return GrammarErrorType.LEISMO
        if "loismo" in rule_id_lower:
            return GrammarErrorType.LOISMO

        # Mapeo por categoría
        category_mapping = {
            "grammar": GrammarErrorType.OTHER,
            "typos": GrammarErrorType.OTHER,
            "punctuation": GrammarErrorType.PUNCTUATION,
            "style": GrammarErrorType.OTHER,
            "redundancy": GrammarErrorType.REDUNDANCY,
            "typography": GrammarErrorType.OTHER,
            "gender": GrammarErrorType.GENDER_AGREEMENT,
            "agreement": GrammarErrorType.SUBJECT_VERB_AGREEMENT,
            "preposition": GrammarErrorType.WRONG_PREPOSITION,
        }

        for key, error_type in category_mapping.items():
            if key in category_lower:
                return error_type

        return GrammarErrorType.OTHER

    def _map_lt_severity(self, category: str) -> GrammarSeverity:
        """Mapear categoría de LanguageTool a severidad."""
        category_lower = category.lower()

        # Errores graves
        if any(k in category_lower for k in ["grammar", "agreement"]):
            return GrammarSeverity.ERROR

        # Advertencias
        if any(k in category_lower for k in ["typos", "punctuation"]):
            return GrammarSeverity.WARNING

        # Estilo
        if any(k in category_lower for k in ["style", "redundancy", "typography"]):
            return GrammarSeverity.STYLE

        return GrammarSeverity.INFO

    def _consolidate_report(self, report: GrammarReport) -> GrammarReport:
        """Consolidar y deduplicar issues."""
        # Deduplicar por posición
        unique: dict[str, GrammarIssue] = {}

        for issue in report.issues:
            key = f"{issue.start_char}:{issue.end_char}:{issue.error_type.value}"
            if key not in unique or issue.confidence > unique[key].confidence:
                unique[key] = issue

        # Crear nuevo report
        consolidated = GrammarReport()
        for issue in unique.values():
            consolidated.add_issue(issue)

        return consolidated

    def _split_sentences(self, text: str) -> list[tuple[int, int, str]]:
        """Dividir texto en oraciones con posiciones."""
        sentences = []
        pattern = r'[.!?]+\s*'

        last_end = 0
        for match in re.finditer(pattern, text):
            end = match.end()
            sentence = text[last_end:end].strip()
            if sentence:
                sentences.append((last_end, end, sentence))
            last_end = end

        # Última oración sin puntuación final
        if last_end < len(text):
            sentence = text[last_end:].strip()
            if sentence:
                sentences.append((last_end, len(text), sentence))

        return sentences

    def _extract_sentence(self, text: str, position: int) -> str:
        """Extraer la oración que contiene la posición dada."""
        # Buscar inicio
        start = position
        while start > 0 and text[start-1] not in '.!?\n':
            start -= 1

        # Buscar fin
        end = position
        while end < len(text) and text[end] not in '.!?\n':
            end += 1

        sentence = text[start:end+1].strip()

        # Limitar longitud
        if len(sentence) > 200:
            word_start = position - start
            context_start = max(0, word_start - 80)
            context_end = min(len(sentence), word_start + 80)
            sentence = "..." + sentence[context_start:context_end] + "..."

        return sentence

    def _generate_suggestion(
        self,
        text: str,
        error_type: GrammarErrorType
    ) -> Optional[str]:
        """Generar sugerencia de corrección."""
        text_lower = text.lower()

        if error_type == GrammarErrorType.DEQUEISMO:
            return re.sub(r'\s+de\s+que', ' que', text, flags=re.IGNORECASE)

        if error_type == GrammarErrorType.QUEISMO:
            return re.sub(r'\s+que\b', ' de que', text, flags=re.IGNORECASE)

        if error_type == GrammarErrorType.INFINITIVE_ERROR:
            if "habemos" in text_lower:
                return text.replace("habemos", "hay").replace("Habemos", "Hay")

        if error_type == GrammarErrorType.GENDER_AGREEMENT:
            # Intentar corregir artículo
            if text_lower.startswith("el "):
                return "la " + text[3:]
            if text_lower.startswith("la "):
                return "el " + text[3:]

        return None

    def _has_adjective_after_comma(self, doc) -> bool:
        """
        Detectar si hay adjetivos después de una coma (construcción literaria).

        Patrones válidos:
        - "Era un hombre muy alto, delgado como un junco."
        - "Tenía los ojos azules, brillantes como el mar."
        - "Parecía una mujer joven, bella y misteriosa."

        Args:
            doc: Documento spaCy ya procesado

        Returns:
            True si hay al menos un adjetivo después de una coma
        """
        comma_found = False

        for token in doc:
            if token.text == ',':
                comma_found = True
            elif comma_found and token.pos_ == 'ADJ':
                return True

        return False

    def _map_llm_error_type(self, llm_type: str) -> GrammarErrorType:
        """Mapear tipo de error del LLM a enum."""
        llm_type_lower = llm_type.lower()

        mapping = {
            "concordancia": GrammarErrorType.GENDER_AGREEMENT,
            "género": GrammarErrorType.GENDER_AGREEMENT,
            "número": GrammarErrorType.NUMBER_AGREEMENT,
            "sujeto": GrammarErrorType.SUBJECT_VERB_AGREEMENT,
            "verbo": GrammarErrorType.SUBJECT_VERB_AGREEMENT,
            "preposición": GrammarErrorType.WRONG_PREPOSITION,
            "dequeísmo": GrammarErrorType.DEQUEISMO,
            "queísmo": GrammarErrorType.QUEISMO,
            "redundancia": GrammarErrorType.REDUNDANCY,
            "estructura": GrammarErrorType.WORD_ORDER,
        }

        for key, error_type in mapping.items():
            if key in llm_type_lower:
                return error_type

        return GrammarErrorType.OTHER
