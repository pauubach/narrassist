"""
Mixin de pipeline unificado: Phase 6: Consistency checks (attributes, temporal, focalization, voice, emotional, sentiment).

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


class PipelineConsistencyMixin:
    """
    Mixin: Phase 6: Consistency checks (attributes, temporal, focalization, voice, emotional, sentiment).

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    if TYPE_CHECKING:
        from .unified_analysis import UnifiedConfig

        config: UnifiedConfig

    def _phase_6_consistency(self, context: AnalysisContext) -> Result[None]:
        """Fase 6: Análisis de consistencia."""
        phase_start = datetime.now()

        try:
            if self.config.run_consistency and context.attributes:
                self._run_attribute_consistency(context)

            if self.config.run_temporal_consistency and context.temporal_markers:
                self._run_temporal_consistency(context)

            if self.config.run_focalization and context.focalization_segments:
                self._run_focalization_consistency(context)

            if self.config.run_voice_deviations and context.voice_profiles:
                self._run_voice_deviation_detection(context)

            if self.config.run_emotional and context.chapters:
                self._run_emotional_coherence(context)

            if self.config.run_sentiment and context.chapters:
                self._run_sentiment_analysis(context)

            context.phase_times["consistency"] = (datetime.now() - phase_start).total_seconds()
            return Result.success(None)

        except Exception as e:
            return Result.failure(
                NarrativeError(
                    message=f"Consistency check failed: {str(e)}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
            )

    def _run_attribute_consistency(self, context: AnalysisContext) -> None:
        """Verificar consistencia de atributos."""
        try:
            from ..analysis.attribute_consistency import AttributeConsistencyChecker

            checker = AttributeConsistencyChecker()
            result = checker.check_consistency(context.attributes)

            if result.is_success and result.value is not None:
                context.inconsistencies = result.value
                context.stats["inconsistencies"] = len(context.inconsistencies)

        except Exception as e:
            logger.warning(f"Attribute consistency check failed: {e}")

    def _run_temporal_consistency(self, context: AnalysisContext) -> None:
        """Verificar consistencia temporal usando marcadores detectados."""
        if not context.temporal_markers:
            return

        try:
            from ..temporal.inconsistencies import (
                TemporalDetectionConfig,
                VotingTemporalChecker,
            )
            from ..temporal.markers import TemporalMarker
            from ..temporal.timeline import TimelineBuilder

            # Filtrar solo TemporalMarker objects (no dicts)
            markers = [m for m in context.temporal_markers if isinstance(m, TemporalMarker)]
            if not markers:
                logger.debug("No TemporalMarker objects available for consistency check")
                return

            # Construir timeline desde marcadores
            builder = TimelineBuilder()
            chapter_data = [
                {
                    "number": ch.get("number", i + 1)
                    if isinstance(ch, dict)
                    else getattr(ch, "chapter_number", i + 1),
                    "title": ch.get("title", "")
                    if isinstance(ch, dict)
                    else getattr(ch, "title", ""),
                    "start_position": ch.get("start_char", 0)
                    if isinstance(ch, dict)
                    else getattr(ch, "start_char", 0),
                    "content": ch.get("content", "")
                    if isinstance(ch, dict)
                    else getattr(ch, "content", ""),
                }
                for i, ch in enumerate(context.chapters)
            ]
            timeline = builder.build_from_markers(markers, chapter_data)

            # Configurar sin LLM por defecto (rápido)
            config = TemporalDetectionConfig(use_llm=self.config.use_llm)

            # Ejecutar verificación con votación
            checker = VotingTemporalChecker(config)
            result = checker.check(
                timeline=timeline,
                markers=markers,
                text=context.full_text,
            )

            if result.inconsistencies:
                context.stats["temporal_inconsistencies"] = len(result.inconsistencies)
                logger.info(f"Found {len(result.inconsistencies)} temporal inconsistencies")

                # Almacenar para generación de alertas
                context.temporal_inconsistencies.extend(result.inconsistencies)

        except ImportError as e:
            logger.debug(f"Temporal inconsistency module not available: {e}")
        except Exception as e:
            logger.warning(f"Temporal consistency check failed: {e}")

    def _run_focalization_consistency(self, context: AnalysisContext) -> None:
        """Verificar violaciones de focalización si hay declaraciones."""
        try:
            from ..focalization.declaration import FocalizationDeclarationService
            from ..focalization.violations import FocalizationViolationDetector

            service = FocalizationDeclarationService()
            declarations = service.get_all_declarations(context.project_id)

            if not declarations:
                logger.debug("No focalization declarations, skipping check")
                return

            # Crear detector con entidades
            detector = FocalizationViolationDetector(service, context.entities)

            all_violations = []
            for ch in context.chapters:
                content = ch.get("content", "")
                chapter_num = ch.get("number", 0)

                if content:
                    violations = detector.detect_violations(
                        project_id=context.project_id,
                        text=content,
                        chapter=chapter_num,
                    )
                    all_violations.extend(violations)

            if all_violations:
                context.stats["focalization_violations"] = len(all_violations)
                logger.info(f"Found {len(all_violations)} focalization violations")

                # Almacenar para generación de alertas
                if not hasattr(context, "focalization_violations"):
                    context.focalization_violations = []
                context.focalization_violations.extend(all_violations)

        except ImportError:
            logger.debug("Focalization module not available")
        except Exception as e:
            logger.warning(f"Focalization consistency check failed: {e}")

    def _run_voice_deviation_detection(self, context: AnalysisContext) -> None:
        """
        Detectar desviaciones de comportamiento usando perfiles generados.

        Compara el comportamiento observado contra las expectativas
        para detectar inconsistencias.
        """
        if not context.voice_profiles:
            return

        try:
            from ..llm.expectation_inference import detect_expectation_violations

            for entity in context.entities:
                if entity.id not in context.voice_profiles:
                    continue

                # Analizar cada capítulo buscando violaciones
                for ch in context.chapters:
                    content = ch.get("content", "")
                    if not content:
                        continue

                    violations = detect_expectation_violations(
                        character_id=entity.id,
                        text=content,
                        chapter_number=ch["number"],
                        position=ch.get("start_char", 0),
                    )

                    for violation in violations:
                        context.voice_deviations.append(
                            {
                                "entity_id": entity.id,
                                "entity_name": entity.canonical_name,
                                "chapter": ch["number"],
                                "violation_text": violation.violation_text,
                                "explanation": violation.explanation,
                                "severity": violation.severity.value
                                if hasattr(violation.severity, "value")
                                else str(violation.severity),
                                "expectation": violation.expectation.to_dict()
                                if hasattr(violation.expectation, "to_dict")
                                else str(violation.expectation),
                                "consensus_score": violation.consensus_score,
                                "detection_methods": violation.detection_methods,
                            }
                        )

            context.stats["voice_deviations"] = len(context.voice_deviations)

        except ImportError:
            logger.debug("LLM module not available for voice deviation detection")
        except Exception as e:
            logger.warning(f"Voice deviation detection failed: {e}")

    def _run_emotional_coherence(self, context: AnalysisContext) -> None:
        """
        Verificar coherencia emocional de personajes.

        Detecta inconsistencias entre:
        - Estado emocional declarado ("María estaba furiosa")
        - Comportamiento comunicativo (cómo habla María)
        - Acciones (qué hace María)
        """
        if not context.chapters:
            return

        try:
            from ..analysis.emotional_coherence import (
                EmotionalCoherenceChecker,
                get_emotional_coherence_checker,
            )

            checker = get_emotional_coherence_checker()

            all_incoherences = []

            # Necesitamos diálogos por capítulo
            dialogues_by_chapter: dict[int, list] = {}
            for d in context.dialogues:
                chapter = d.get("chapter", 0)
                if chapter not in dialogues_by_chapter:
                    dialogues_by_chapter[chapter] = []
                dialogues_by_chapter[chapter].append(d)

            # Analizar cada capítulo
            for ch in context.chapters:
                chapter_num = ch.get("number", 0)
                content = ch.get("content", "")

                if not content:
                    continue

                chapter_dialogues = dialogues_by_chapter.get(chapter_num, [])

                # El checker analiza el capítulo completo
                # analyze_chapter() retorna list[EmotionalIncoherence] directamente
                result = checker.analyze_chapter(
                    chapter_text=content,
                    chapter_id=chapter_num,
                    dialogues=chapter_dialogues,
                    entity_names=[e.canonical_name for e in context.entities],
                )

                # Manejar tanto Result como list directa
                if hasattr(result, "is_success"):
                    incoherences = result.value if result.is_success else []  # type: ignore[union-attr, attr-defined]
                else:
                    incoherences = result if isinstance(result, list) else []

                if incoherences:
                    for incoherence in incoherences:
                        all_incoherences.append(
                            {
                                "entity_name": incoherence.entity_name,
                                "incoherence_type": incoherence.incoherence_type.value,
                                "declared_emotion": incoherence.declared_emotion,
                                "actual_behavior": incoherence.actual_behavior,
                                "declared_text": incoherence.declared_text,
                                "behavior_text": incoherence.behavior_text,
                                "confidence": incoherence.confidence,
                                "explanation": incoherence.explanation,
                                "suggestion": incoherence.suggestion,
                                "chapter_id": incoherence.chapter_id,
                            }
                        )

            if all_incoherences:
                context.emotional_incoherences = all_incoherences
                context.stats["emotional_incoherences"] = len(all_incoherences)
                logger.info(f"Found {len(all_incoherences)} emotional incoherences")

        except ImportError as e:
            logger.debug(f"Emotional coherence module not available: {e}")
        except Exception as e:
            logger.warning(f"Emotional coherence check failed: {e}")

    def _run_sentiment_analysis(self, context: AnalysisContext) -> None:
        """
        Analizar arco emocional de cada capítulo.

        Usa pysentimiento para detectar:
        - Sentimiento general (positivo/negativo/neutro)
        - Emociones primarias (joy, sadness, anger, fear, surprise, disgust)
        - Evolución emocional a lo largo del capítulo
        """
        if not context.chapters:
            return

        try:
            from ..nlp.sentiment import SentimentAnalyzer

            analyzer = SentimentAnalyzer()

            sentiment_arcs = []

            for ch in context.chapters:
                chapter_num = ch.get("number", 0)
                content = ch.get("content", "")

                if not content:
                    continue

                # Analizar arco emocional del capítulo
                arc_result = analyzer.analyze_emotional_arc(  # type: ignore[call-arg]
                    text=content,
                    chapter_id=chapter_num,
                    segment_size=500,  # Dividir en segmentos de ~500 chars
                )

                if hasattr(arc_result, "is_success") and arc_result.is_success and arc_result.value:  # type: ignore[union-attr, attr-defined]
                    arc = arc_result.value  # type: ignore[union-attr, attr-defined]
                    sentiment_arcs.append(
                        {
                            "chapter": chapter_num,
                            "overall_sentiment": arc.overall_sentiment.value,
                            "overall_confidence": arc.overall_confidence,
                            "dominant_emotion": arc.dominant_emotion.value
                            if arc.dominant_emotion
                            else "neutral",
                            "emotion_variance": arc.emotion_variance,
                            "sentiment_shifts": arc.sentiment_shifts,
                            "segments": [
                                {
                                    "position": seg.start_char,
                                    "sentiment": seg.sentiment.value,
                                    "emotion": seg.primary_emotion.value,
                                    "confidence": seg.sentiment_confidence,
                                }
                                for seg in arc.segments[:10]  # Limitar a 10 segmentos
                            ],
                        }
                    )

            if sentiment_arcs:
                context.sentiment_arcs = sentiment_arcs
                context.stats["chapters_with_sentiment"] = len(sentiment_arcs)

                # Estadísticas agregadas
                avg_variance = sum(a["emotion_variance"] for a in sentiment_arcs) / len(
                    sentiment_arcs
                )
                context.stats["avg_emotional_variance"] = round(avg_variance, 3)

                total_shifts = sum(a["sentiment_shifts"] for a in sentiment_arcs)
                context.stats["total_sentiment_shifts"] = total_shifts

                logger.info(f"Sentiment analysis: {len(sentiment_arcs)} chapters analyzed")

        except ImportError as e:
            logger.debug(f"Sentiment analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
