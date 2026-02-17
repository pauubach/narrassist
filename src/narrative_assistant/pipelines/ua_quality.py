"""
Mixin de pipeline unificado: Phase 5: Spelling, grammar, repetitions, coherence, register, pacing.

Extraido de unified_analysis.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .unified_analysis import AnalysisContext

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

logger = logging.getLogger(__name__)


def _ch_val(ch, key: str, default=None):
    """Extrae valor de un dict o de un objeto con atributo."""
    if isinstance(ch, dict):
        return ch.get(key, default)
    return getattr(ch, key, default)


def _ch_num(ch, fallback=0):
    """Obtiene el número de capítulo de un dict o objeto."""
    return _ch_val(ch, "number") or _ch_val(ch, "chapter_number") or fallback


def _ch_content(ch):
    """Obtiene el contenido de texto de un dict o objeto."""
    return _ch_val(ch, "content") or _ch_val(ch, "text") or ""


class PipelineQualityMixin:
    """
    Mixin: Phase 5: Spelling, grammar, repetitions, coherence, register, pacing.

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    if TYPE_CHECKING:
        from .unified_analysis import UnifiedConfig

        config: UnifiedConfig

        def _run_parallel_tasks(
            self, tasks: list, context: AnalysisContext
        ) -> None: ...

    def _phase_5_quality(self, context: AnalysisContext) -> Result[None]:
        """
        Fase 5: Ortografía, gramática, repeticiones.

        Parallelizable: Cada análisis es independiente.
        """
        phase_start = datetime.now()

        tasks = []

        if self.config.run_spelling:
            tasks.append(("spelling", self._run_spelling_check))

        if self.config.run_grammar:
            tasks.append(("grammar", self._run_grammar_check))

        if self.config.run_lexical_repetitions:
            tasks.append(("lexical_rep", self._run_lexical_repetitions))

        if self.config.run_semantic_repetitions:
            tasks.append(("semantic_rep", self._run_semantic_repetitions))

        if self.config.run_coherence:
            tasks.append(("coherence", self._run_coherence_check))

        if self.config.run_register_analysis:
            tasks.append(("register", self._run_register_analysis))

        if self.config.run_pacing:
            tasks.append(("pacing", self._run_pacing_analysis))

        if self.config.run_sticky_sentences:
            tasks.append(("sticky", self._run_sticky_sentences))

        if self.config.run_sentence_energy:
            tasks.append(("sentence_energy", self._run_sentence_energy))

        if self.config.run_sensory_report:
            tasks.append(("sensory", self._run_sensory_report))

        if self.config.run_typography:
            tasks.append(("typography", self._run_typography_check))

        if self.config.run_pov_check:
            tasks.append(("pov", self._run_pov_check))

        if self.config.run_references_check:
            tasks.append(("references", self._run_references_check))

        if self.config.run_acronyms_check:
            tasks.append(("acronyms", self._run_acronyms_check))

        # Muletillas lingüísticas (catálogo prescriptivo)
        # Complementa CrutchWordsDetector (análisis estadístico)
        if getattr(self.config, 'run_filler_detection', True):
            tasks.append(("fillers", self._run_filler_detection))

        # Ejecutar en paralelo si está configurado
        if self.config.parallel_extraction and len(tasks) > 1:
            self._run_parallel_tasks(tasks, context)
        else:
            for name, func in tasks:
                try:
                    func(context)
                except Exception as e:
                    logger.warning(f"{name} failed: {e}")

        context.phase_times["quality"] = (datetime.now() - phase_start).total_seconds()
        return Result.success(None)

    @staticmethod
    def _find_chapter_for_position(
        position: int, chapters: list
    ) -> int | None:
        """
        Mapea una posición global de carácter al número de capítulo correspondiente.

        Args:
            position: Posición (start_char) en el texto completo
            chapters: Lista de objetos Chapter con start_char, end_char, number

        Returns:
            Número de capítulo o None si no se encuentra
        """
        for ch in chapters:
            start = _ch_val(ch, "start_char") or 0
            end = _ch_val(ch, "end_char") or 0
            if start <= position < end:
                return _ch_num(ch)  # type: ignore[no-any-return]
        return None

    def _assign_chapters_to_issues(
        self, issues: list, chapters: list
    ) -> None:
        """
        Asigna el número de capítulo a cada issue según su posición global.

        Args:
            issues: Lista de SpellingIssue o GrammarIssue con start_char
            chapters: Lista de Chapter con start_char, end_char, number
        """
        if not chapters:
            return
        for issue in issues:
            if hasattr(issue, "chapter") and hasattr(issue, "start_char"):
                issue.chapter = self._find_chapter_for_position(
                    issue.start_char, chapters
                )

    def _run_spelling_check(self, context: AnalysisContext) -> None:
        """Verificar ortografía."""
        try:
            from ..nlp.orthography import get_spelling_checker

            checker = get_spelling_checker()

            # Añadir entidades conocidas al diccionario
            known_entities = [e.canonical_name for e in context.entities]
            checker.add_to_dictionary(known_entities)

            result = checker.check(
                context.full_text,
                known_entities=known_entities,
                use_llm=self.config.use_llm,
            )

            if result.is_success and result.value is not None:
                # Filtrar por confianza
                context.spelling_issues = [
                    issue
                    for issue in result.value.issues
                    if issue.confidence >= self.config.spelling_min_confidence
                ]
                # Mapear posición global → capítulo
                self._assign_chapters_to_issues(
                    context.spelling_issues, context.chapters
                )
                context.stats["spelling_issues"] = len(context.spelling_issues)

        except Exception as e:
            logger.warning(f"Spelling check failed: {e}")

    def _run_grammar_check(self, context: AnalysisContext) -> None:
        """Verificar gramática."""
        try:
            from ..nlp.grammar import get_grammar_checker

            checker = get_grammar_checker()
            result = checker.check(
                context.full_text,
                use_llm=self.config.use_llm,
            )

            if result.is_success and result.value is not None:
                context.grammar_issues = [
                    issue
                    for issue in result.value.issues
                    if issue.confidence >= self.config.grammar_min_confidence
                ]
                # Mapear posición global → capítulo
                self._assign_chapters_to_issues(
                    context.grammar_issues, context.chapters
                )
                context.stats["grammar_issues"] = len(context.grammar_issues)

        except Exception as e:
            logger.warning(f"Grammar check failed: {e}")

    def _run_lexical_repetitions(self, context: AnalysisContext) -> None:
        """Detectar repeticiones léxicas."""
        try:
            from ..nlp.style import get_repetition_detector

            detector = get_repetition_detector()
            result = detector.detect_lexical(
                context.full_text, min_distance=self.config.repetition_min_distance
            )

            if result.is_success and result.value is not None:
                context.lexical_repetitions = result.value.repetitions
                context.stats["lexical_repetitions"] = len(context.lexical_repetitions)

        except ImportError:
            # Módulo aún no implementado
            pass
        except Exception as e:
            logger.warning(f"Lexical repetition detection failed: {e}")

    def _run_semantic_repetitions(self, context: AnalysisContext) -> None:
        """Detectar repeticiones semánticas."""
        try:
            from ..nlp.style import get_repetition_detector

            detector = get_repetition_detector()
            result = detector.detect_semantic(
                context.full_text, min_distance=self.config.repetition_min_distance
            )

            if result.is_success and result.value is not None:
                context.semantic_repetitions = result.value.repetitions
                context.stats["semantic_repetitions"] = len(context.semantic_repetitions)

        except ImportError:
            # Módulo aún no implementado
            pass
        except Exception as e:
            logger.warning(f"Semantic repetition detection failed: {e}")

    def _run_coherence_check(self, context: AnalysisContext) -> None:
        """Detectar saltos de coherencia narrativa entre párrafos/segmentos."""
        try:
            from ..nlp.style import get_coherence_detector

            detector = get_coherence_detector(
                similarity_threshold=self.config.coherence_similarity_threshold
            )

            # Analizar por capítulos si hay estructura detectada
            if context.chapters:
                chapters_data = [
                    {
                        "id": ch.get("number"),
                        "content": ch.get("content", ""),
                        "title": ch.get("title", ""),
                    }
                    for ch in context.chapters
                ]
                result = detector.detect_in_chapters(chapters_data)
            else:
                # Analizar texto completo
                result = detector.detect(context.full_text)

            if result.is_success and result.value is not None:
                context.coherence_breaks = result.value.breaks
                context.stats["coherence_breaks"] = len(context.coherence_breaks)
                context.stats["coherence_avg_similarity"] = result.value.avg_similarity
                context.stats["coherence_min_similarity"] = result.value.min_similarity

        except ImportError:
            logger.debug("Coherence detector not available")
        except Exception as e:
            logger.warning(f"Coherence check failed: {e}")

    def _run_register_analysis(self, context: AnalysisContext) -> None:
        """
        Detectar cambios de registro narrativo (formal/coloquial/técnico/poético).

        Útil para:
        - Detectar inconsistencias tonales en la narración
        - Identificar saltos abruptos de estilo
        - Alertar sobre mezcla inadecuada de registros
        """
        try:
            from ..voice.register import (
                RegisterAnalyzer,
                RegisterChangeDetector,
            )

            detector = RegisterChangeDetector()

            # Preparar segmentos: (texto, capítulo, posición, es_diálogo)
            segments = []

            if context.chapters:
                for ch in context.chapters:
                    content = ch.get("content", "")
                    chapter_num = ch.get("number", 1)
                    start_char = ch.get("start_char", 0)

                    # Dividir en párrafos para análisis granular
                    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                    current_pos = start_char

                    for para in paragraphs:
                        # Detectar si es diálogo (empieza con guión o comillas)
                        is_dialogue = para.startswith(("—", "-", "«", '"', "'"))

                        if len(para) > 50:  # Solo párrafos sustanciales
                            segments.append((para, chapter_num, current_pos, is_dialogue))

                        current_pos += len(para) + 2  # +2 por \n\n
            else:
                # Sin estructura de capítulos, analizar texto completo
                paragraphs = [p.strip() for p in context.full_text.split("\n\n") if p.strip()]
                current_pos = 0

                for para in paragraphs:
                    is_dialogue = para.startswith(("—", "-", "«", '"', "'"))
                    if len(para) > 50:
                        segments.append((para, 1, current_pos, is_dialogue))
                    current_pos += len(para) + 2

            if not segments:
                return

            # Analizar documento
            analyses = detector.analyze_document(segments)

            # Detectar cambios significativos (medium o superior)
            changes = detector.detect_changes(min_severity="medium")

            context.register_changes = [ch.to_dict() for ch in changes]
            context.stats["register_segments_analyzed"] = len(analyses)
            context.stats["register_changes_detected"] = len(changes)

            # Obtener distribución de registros
            summary = detector.get_summary()
            context.stats["register_distribution"] = summary.get("distribution", {})
            context.stats["dominant_register"] = summary.get("dominant_register")

            logger.info(f"Register analysis: {len(changes)} changes in {len(analyses)} segments")

        except ImportError as e:
            logger.debug(f"Register analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Register analysis failed: {e}")

    def _run_pacing_analysis(self, context: AnalysisContext) -> None:
        """
        Analizar ritmo narrativo del documento.

        Detecta:
        - Capítulos desproporcionados
        - Ratio diálogo/narración
        - Bloques de texto densos
        - Desequilibrios estructurales
        """
        if not context.chapters:
            return

        try:
            from ..analysis.pacing import analyze_pacing

            result = analyze_pacing(
                chapters=context.chapters,
                full_text=context.full_text,
            )

            context.pacing_analysis = result.to_dict()

            # Estadísticas
            context.stats["pacing_issues"] = len(result.issues)
            if result.summary:
                context.stats["avg_chapter_words"] = result.summary.get("avg_chapter_words", 0)
                context.stats["chapter_word_variance"] = result.summary.get(
                    "chapter_word_variance", 0
                )
                context.stats["avg_dialogue_ratio"] = result.summary.get("avg_dialogue_ratio", 0)

            logger.info(
                f"Pacing analysis: {len(result.issues)} issues in {len(context.chapters)} chapters"
            )

        except ImportError as e:
            logger.debug(f"Pacing analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Pacing analysis failed: {e}")

    def _run_sticky_sentences(self, context: AnalysisContext) -> None:
        """Detectar oraciones pesadas (sticky sentences)."""
        try:
            from ..nlp.style.sticky_sentences import get_sticky_sentence_detector

            detector = get_sticky_sentence_detector()

            all_sticky: list = []
            for ch in context.chapters:
                ch_num = _ch_num(ch)
                ch_content = _ch_content(ch)
                ch_start_offset = _ch_val(ch, "start_char", 0)

                result = detector.analyze(ch_content, chapter=ch_num)
                if result.is_success and result.value is not None:
                    # Ajustar posiciones: relativas al capítulo → absolutas al documento
                    for sticky in result.value.sticky_sentences:
                        if hasattr(sticky, 'start_char') and sticky.start_char is not None:
                            sticky.start_char += ch_start_offset
                        if hasattr(sticky, 'end_char') and sticky.end_char is not None:
                            sticky.end_char += ch_start_offset

                    all_sticky.extend(result.value.sticky_sentences)

            context.sticky_sentences = all_sticky
            context.stats["sticky_sentences"] = len(all_sticky)
            logger.info(f"Sticky sentences: {len(all_sticky)} detected")

        except ImportError as e:
            logger.debug(f"Sticky sentence detector not available: {e}")
        except Exception as e:
            logger.warning(f"Sticky sentence analysis failed: {e}")

    def _run_sentence_energy(self, context: AnalysisContext) -> None:
        """Detectar oraciones de baja energía (voz pasiva, verbos débiles)."""
        try:
            from ..nlp.style.sentence_energy import get_sentence_energy_detector

            detector = get_sentence_energy_detector()

            all_issues: list = []
            for ch in context.chapters:
                ch_num = _ch_num(ch)
                ch_content = _ch_content(ch)
                ch_start_offset = _ch_val(ch, "start_char", 0)

                result = detector.analyze(ch_content, chapter=ch_num)
                if result.is_success and result.value is not None:
                    # Ajustar posiciones: relativas al capítulo → absolutas al documento
                    for issue in result.value.low_energy_sentences:
                        if hasattr(issue, 'start_char') and issue.start_char is not None:
                            issue.start_char += ch_start_offset
                        if hasattr(issue, 'end_char') and issue.end_char is not None:
                            issue.end_char += ch_start_offset

                    all_issues.extend(result.value.low_energy_sentences)

            context.sentence_energy_issues = all_issues
            context.stats["sentence_energy_issues"] = len(all_issues)
            logger.info(f"Sentence energy: {len(all_issues)} low-energy sentences")

        except ImportError as e:
            logger.debug(f"Sentence energy detector not available: {e}")
        except Exception as e:
            logger.warning(f"Sentence energy analysis failed: {e}")

    def _run_sensory_report(self, context: AnalysisContext) -> None:
        """Detectar déficit de descripciones sensoriales por capítulo."""
        try:
            from ..nlp.style.sensory_report import get_sensory_analyzer

            analyzer = get_sensory_analyzer()
            result = analyzer.analyze(
                text=context.full_text,
                chapters=[
                    {
                        "number": _ch_num(ch, fallback=i + 1),
                        "content": _ch_content(ch),
                    }
                    for i, ch in enumerate(context.chapters)
                ]
                if context.chapters
                else None,
            )

            if result.is_success and result.value is not None:
                report = result.value
                context.sensory_report = {
                    "overall_density": report.overall_density,
                    "overall_level": report.overall_density_level.value
                    if hasattr(report.overall_density_level, "value")
                    else str(report.overall_density_level),
                    "sparse_chapters": getattr(report, "sparse_chapters", []),
                    "by_sense": getattr(report, "by_sense", {}),
                }
                context.stats["sensory_density"] = report.overall_density
                context.stats["sensory_sparse_chapters"] = len(
                    getattr(report, "sparse_chapters", [])
                )
                logger.info(
                    f"Sensory report: density={report.overall_density:.1f}, "
                    f"sparse chapters={len(getattr(report, 'sparse_chapters', []))}"
                )

        except ImportError as e:
            logger.debug(f"Sensory analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Sensory report failed: {e}")

    def _run_typography_check(self, context: AnalysisContext) -> None:
        """Detectar errores tipográficos (guiones, comillas, espacios dobles)."""
        try:
            from ..corrections.detectors.typography import TypographyDetector

            detector = TypographyDetector()

            all_issues: list = []
            if context.chapters:
                for ch in context.chapters:
                    ch_num = _ch_num(ch)
                    ch_content = _ch_content(ch)
                    ch_start_offset = _ch_val(ch, "start_char", 0)

                    issues = detector.detect(ch_content, chapter_index=ch_num)

                    # Ajustar posiciones: relativas al capítulo → absolutas al documento
                    for issue in issues:
                        if hasattr(issue, 'start_char') and issue.start_char is not None:
                            issue.start_char += ch_start_offset
                        if hasattr(issue, 'end_char') and issue.end_char is not None:
                            issue.end_char += ch_start_offset

                    all_issues.extend(issues)
            else:
                all_issues = detector.detect(context.full_text)

            context.typography_issues = all_issues
            context.stats["typography_issues"] = len(all_issues)
            logger.info(f"Typography: {len(all_issues)} issues detected")

        except ImportError as e:
            logger.debug(f"Typography detector not available: {e}")
        except Exception as e:
            logger.warning(f"Typography check failed: {e}")

    def _run_pov_check(self, context: AnalysisContext) -> None:
        """Detectar cambios de punto de vista narrativo (1a/3a persona, tú/usted)."""
        try:
            from ..corrections.detectors.pov import POVDetector

            detector = POVDetector()

            all_issues: list = []
            if context.chapters:
                for ch in context.chapters:
                    ch_num = _ch_num(ch)
                    ch_content = _ch_content(ch)
                    ch_start_offset = _ch_val(ch, "start_char", 0)

                    issues = detector.detect(ch_content, chapter_index=ch_num)

                    # Ajustar posiciones: relativas al capítulo → absolutas al documento
                    for issue in issues:
                        if hasattr(issue, 'start_char') and issue.start_char is not None:
                            issue.start_char += ch_start_offset
                        if hasattr(issue, 'end_char') and issue.end_char is not None:
                            issue.end_char += ch_start_offset

                    all_issues.extend(issues)
            else:
                all_issues = detector.detect(context.full_text)

            context.pov_issues = all_issues
            context.stats["pov_issues"] = len(all_issues)
            logger.info(f"POV: {len(all_issues)} issues detected")

        except ImportError as e:
            logger.debug(f"POV detector not available: {e}")
        except Exception as e:
            logger.warning(f"POV check failed: {e}")

    def _run_references_check(self, context: AnalysisContext) -> None:
        """Detectar inconsistencias en referencias bibliográficas."""
        try:
            from ..corrections.config import ReferencesConfig
            from ..corrections.detectors.references import ReferencesDetector

            config = ReferencesConfig(enabled=True)
            detector = ReferencesDetector(config=config)
            all_issues = detector.detect(context.full_text)

            context.reference_issues = all_issues
            context.stats["reference_issues"] = len(all_issues)
            logger.info(f"References: {len(all_issues)} issues detected")

        except ImportError as e:
            logger.debug(f"References detector not available: {e}")
        except Exception as e:
            logger.warning(f"References check failed: {e}")

    def _run_acronyms_check(self, context: AnalysisContext) -> None:
        """Detectar siglas sin definir o con formato inconsistente."""
        try:
            from ..corrections.config import AcronymConfig
            from ..corrections.detectors.acronyms import AcronymDetector

            config = AcronymConfig(enabled=True)
            detector = AcronymDetector(config=config)
            all_issues = detector.detect(context.full_text)

            context.acronym_issues = all_issues
            context.stats["acronym_issues"] = len(all_issues)
            logger.info(f"Acronyms: {len(all_issues)} issues detected")

        except ImportError as e:
            logger.debug(f"Acronym detector not available: {e}")
        except Exception as e:
            logger.warning(f"Acronym check failed: {e}")

    def _run_filler_detection(self, context: AnalysisContext) -> None:
        """Detectar muletillas lingüísticas (catálogo prescriptivo)."""
        try:
            from ..corrections.base import CorrectionIssue
            from ..corrections.types import CorrectionCategory
            from ..nlp.style.filler_detector import get_filler_detector

            detector = get_filler_detector()
            result = detector.detect(context.full_text)

            if result.is_failure:
                logger.debug(f"Filler detection failed: {result.error}")
                context.filler_issues = []
                context.stats["filler_issues"] = 0
                return

            report = result.value
            filler_issues = []

            # Convertir FillerReport a CorrectionIssues
            for filler in report.fillers:
                if not filler.is_excessive:
                    continue

                # Reportar primeras 5 ocurrencias de cada muletilla excesiva
                for occ in filler.occurrences[:5]:
                    issue = CorrectionIssue(
                        category=CorrectionCategory.CRUTCH_WORDS.value,
                        issue_type="linguistic_filler",
                        start_char=occ.start_char,
                        end_char=occ.end_char,
                        text=occ.text,
                        explanation=(
                            f"Muletilla lingüística '{filler.phrase}' "
                            f"({filler.count} veces, {filler.frequency_per_1000:.1f} por 1000 palabras). "
                            f"{filler.suggestion}"
                        ),
                        suggestion=filler.suggestion,
                        confidence=0.7 if filler.severity.value == "high" else 0.6,
                        context=occ.context,
                        chapter_index=None,  # TODO: Mapear posición a capítulo
                        rule_id=f"filler_{filler.normalized}",
                        extra_data={
                            "filler_type": filler.filler_type.value,
                            "severity": filler.severity.value,
                            "total_occurrences": filler.count,
                            "frequency_per_1000": filler.frequency_per_1000,
                            "in_dialogue": occ.in_dialogue,
                        },
                    )
                    filler_issues.append(issue)

            context.filler_issues = filler_issues
            context.stats["filler_issues"] = len(filler_issues)
            logger.info(
                f"Fillers: {len(filler_issues)} issues from "
                f"{report.excessive_fillers} excessive fillers "
                f"({report.total_fillers} total types)"
            )

        except ImportError as e:
            logger.debug(f"Filler detector not available: {e}")
            context.filler_issues = []
            context.stats["filler_issues"] = 0
        except Exception as e:
            logger.warning(f"Filler detection failed: {e}")
            context.filler_issues = []
            context.stats["filler_issues"] = 0
