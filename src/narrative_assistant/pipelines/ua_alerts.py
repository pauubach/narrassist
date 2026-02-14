"""
Mixin de pipeline unificado: Alert generation from detected issues.

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


class PipelineAlertsMixin:
    """
    Mixin: Alert generation from detected issues.

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    if TYPE_CHECKING:
        from .unified_analysis import UnifiedConfig

        config: UnifiedConfig

    def _generate_all_alerts(self, context: AnalysisContext) -> None:
        """Generar todas las alertas desde los issues detectados."""
        try:
            from ..alerts.engine import get_alert_engine
            from ..alerts.models import AlertCategory, AlertSeverity

            engine = get_alert_engine()

            # Alertas de inconsistencias de atributos
            for inc in context.inconsistencies:
                # Convertir attribute_key enum a string para la API
                attr_key_str = (
                    inc.attribute_key.value
                    if hasattr(inc.attribute_key, "value")
                    else str(inc.attribute_key)
                )
                result = engine.create_from_attribute_inconsistency(
                    project_id=context.project_id,
                    entity_name=inc.entity_name,
                    entity_id=context.entity_map.get(inc.entity_name.lower(), 0),
                    attribute_key=attr_key_str,
                    value1=inc.value1,
                    value2=inc.value2,
                    value1_source={
                        "chapter": inc.value1_chapter,
                        "excerpt": inc.value1_excerpt,
                        "start_char": inc.value1_position,
                        "end_char": inc.value1_position + len(inc.value1_excerpt)
                        if inc.value1_excerpt
                        else 0,
                    },
                    value2_source={
                        "chapter": inc.value2_chapter,
                        "excerpt": inc.value2_excerpt,
                        "start_char": inc.value2_position,
                        "end_char": inc.value2_position + len(inc.value2_excerpt)
                        if inc.value2_excerpt
                        else 0,
                    },
                    explanation=inc.explanation,
                    confidence=inc.confidence,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de inconsistencias temporales
            for tinc in context.temporal_inconsistencies:
                inc_type = (
                    tinc.inconsistency_type.value
                    if hasattr(tinc.inconsistency_type, "value")
                    else str(tinc.inconsistency_type)
                )
                result = engine.create_from_temporal_inconsistency(
                    project_id=context.project_id,
                    inconsistency_type=inc_type,
                    description=tinc.description,
                    explanation=tinc.suggestion or tinc.description,
                    chapter=tinc.chapter,
                    start_char=tinc.position,
                    end_char=tinc.position + 50,  # Approximate span
                    excerpt=tinc.expected or "",
                    confidence=tinc.confidence,
                    extra_data={
                        "expected": tinc.expected,
                        "found": tinc.found,
                        "severity": tinc.severity.value
                        if hasattr(tinc.severity, "value")
                        else str(tinc.severity),
                        "methods_agreed": tinc.methods_agreed,
                    },
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de ortografía
            for issue in context.spelling_issues:
                result = engine.create_from_spelling_issue(
                    project_id=context.project_id,
                    word=issue.word,
                    start_char=issue.start_char,
                    end_char=issue.end_char,
                    sentence=issue.sentence,
                    error_type=issue.error_type.value,
                    suggestions=issue.suggestions,
                    confidence=issue.confidence,
                    explanation=issue.explanation,
                    chapter=issue.chapter,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de gramática
            for issue in context.grammar_issues:
                result = engine.create_from_grammar_issue(
                    project_id=context.project_id,
                    text=issue.text,
                    start_char=issue.start_char,
                    end_char=issue.end_char,
                    sentence=issue.sentence,
                    error_type=issue.error_type.value,
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                    explanation=issue.explanation,
                    rule_id=issue.rule_id,
                    chapter=issue.chapter,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de repeticiones léxicas (word echo)
            for rep in context.lexical_repetitions:
                word = rep.word if hasattr(rep, "word") else str(rep)
                occurrences = []
                if hasattr(rep, "occurrences"):
                    for occ in rep.occurrences:
                        if hasattr(occ, "start_char"):
                            occurrences.append(
                                {
                                    "start_char": occ.start_char,
                                    "end_char": occ.end_char,
                                    "context": occ.context[:100]
                                    if hasattr(occ, "context") and occ.context
                                    else "",
                                }
                            )
                        elif isinstance(occ, dict):
                            occurrences.append(occ)

                result = engine.create_from_word_echo(
                    project_id=context.project_id,
                    word=word,
                    occurrences=occurrences,
                    min_distance=self.config.repetition_min_distance,
                    chapter=rep.chapter if hasattr(rep, "chapter") else None,
                    confidence=rep.confidence if hasattr(rep, "confidence") else 0.7,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de repeticiones semánticas
            for rep in context.semantic_repetitions:
                word = rep.word if hasattr(rep, "word") else str(rep)
                count = rep.count if hasattr(rep, "count") else 0
                result = engine.create_alert(
                    project_id=context.project_id,
                    alert_type="style_semantic_repetition",
                    category=AlertCategory.STYLE,
                    severity=AlertSeverity.INFO,
                    title=f"Repetición semántica: '{word}'",
                    description=f"La palabra '{word}' y sus sinónimos aparecen {count} veces en proximidad",
                    explanation=f"Se detectó repetición semántica de '{word}' y palabras similares. Esto puede indicar sobrecarga conceptual en el texto.",
                    extra_data={
                        "word": word,
                        "similar_words": rep.similar_words if hasattr(rep, "similar_words") else [],
                        "count": count,
                        "repetition_type": "semantic",
                    },
                    confidence=rep.confidence if hasattr(rep, "confidence") else 0.6,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de saltos de coherencia narrativa
            for brk in context.coherence_breaks:
                severity_map = {
                    "high": AlertSeverity.WARNING,
                    "medium": AlertSeverity.INFO,
                    "low": AlertSeverity.HINT,
                }
                severity = severity_map.get(
                    brk.severity.value if hasattr(brk.severity, "value") else brk.severity,
                    AlertSeverity.INFO,
                )

                result = engine.create_alert(
                    project_id=context.project_id,
                    alert_type="coherence_break",
                    category=AlertCategory.STYLE,
                    severity=severity,
                    title=f"Salto de coherencia: {brk.break_type.value if hasattr(brk.break_type, 'value') else brk.break_type}",
                    description="Posible discontinuidad narrativa entre segmentos",
                    explanation=brk.explanation,
                    extra_data={
                        "break_type": brk.break_type.value
                        if hasattr(brk.break_type, "value")
                        else str(brk.break_type),
                        "similarity_score": brk.similarity_score,
                        "expected_similarity": brk.expected_similarity,
                        "text_before": brk.text_before[:100] if brk.text_before else "",
                        "text_after": brk.text_after[:100] if brk.text_after else "",
                        "position_char": brk.position_char,
                        "chapter_id": brk.chapter_id,
                    },
                    confidence=brk.confidence,
                    position=brk.position_char,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de desviaciones de voz/comportamiento
            for deviation in context.voice_deviations:
                entity_name = deviation.get("entity_name", "Personaje")
                severity_str = deviation.get("severity", "medium").upper()
                severity = getattr(AlertSeverity, severity_str, AlertSeverity.INFO)
                explanation = deviation.get("explanation", "Comportamiento fuera de carácter")

                result = engine.create_alert(
                    project_id=context.project_id,
                    alert_type="behavior_deviation",
                    category=AlertCategory.BEHAVIORAL,
                    severity=severity,
                    title=f"Inconsistencia de comportamiento: {entity_name}",
                    description=f"Posible desviación del comportamiento esperado de {entity_name}",
                    explanation=explanation,
                    entity_id=deviation.get("entity_id"),
                    entity_name=entity_name,
                    extra_data={
                        "chapter": deviation.get("chapter"),
                        "violation_text": deviation.get("violation_text"),
                        "expectation": deviation.get("expectation"),
                        "consensus_score": deviation.get("consensus_score"),
                        "detection_methods": deviation.get("detection_methods"),
                    },
                    confidence=deviation.get("consensus_score", 0.5),
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de ritmo narrativo (pacing)
            if context.pacing_analysis:
                issues = context.pacing_analysis.get("issues", [])
                for issue in issues:
                    if isinstance(issue, dict):
                        result = engine.create_from_pacing_issue(
                            project_id=context.project_id,
                            issue_type=issue.get("issue_type", "unknown"),
                            severity_level=issue.get("severity", "info"),
                            chapter=issue.get("segment_id"),
                            segment_type=issue.get("segment_type", "chapter"),
                            description=issue.get("description", ""),
                            explanation=issue.get("explanation", ""),
                            suggestion=issue.get("suggestion", ""),
                            actual_value=issue.get("actual_value", 0.0),
                            expected_range=tuple(issue.get("expected_range", (0.0, 0.0))),
                            comparison_value=issue.get("comparison_value"),
                        )
                        if result.is_success:
                            context.alerts.append(result.value)

            # Alertas de oraciones pesadas (sticky sentences)
            for sent in context.sticky_sentences:
                severity_val = (
                    sent.severity.value if hasattr(sent.severity, "value") else str(sent.severity)
                )
                # Solo alertar a partir de severidad medium
                if severity_val in ("medium", "high", "critical"):
                    result = engine.create_from_sticky_sentence(
                        project_id=context.project_id,
                        sentence=sent.text[:200] if len(sent.text) > 200 else sent.text,
                        glue_percentage=sent.glue_percentage,
                        chapter=sent.chapter if hasattr(sent, "chapter") else None,
                        start_char=sent.start_char if hasattr(sent, "start_char") else None,
                        end_char=sent.end_char if hasattr(sent, "end_char") else None,
                        severity_level=severity_val,
                        confidence=0.75,
                    )
                    if result.is_success:
                        context.alerts.append(result.value)

            # Alertas de cambios de registro narrativo
            for change in context.register_changes:
                if isinstance(change, dict):
                    reg_severity: str = change.get("severity", "medium")
                    if reg_severity in ("medium", "high", "critical"):
                        result = engine.create_from_register_change(
                            project_id=context.project_id,
                            from_register=change.get("from_register", "unknown"),
                            to_register=change.get("to_register", "unknown"),
                            severity_level=reg_severity,
                            chapter=change.get("chapter", 0),
                            position=change.get("position", 0),
                            context_before=change.get("context_before", "")[:200],
                            context_after=change.get("context_after", "")[:200],
                            explanation=change.get("explanation", "Cambio de registro detectado"),
                            confidence=change.get("confidence", 0.7),
                        )
                        if result.is_success:
                            context.alerts.append(result.value)

            # Alertas de variantes de nombres de entidades
            try:
                from ..analysis.name_variant_detector import detect_name_variants
                from ..entities.repository import get_entity_repository

                entity_repo = get_entity_repository()
                mentions_by_entity: dict[int, list] = {}
                for entity in context.entities:
                    eid = getattr(entity, "id", None)
                    if eid is not None:
                        mentions_by_entity[eid] = entity_repo.get_mentions_by_entity(eid)

                dialogue_spans = [
                    (d.get("start_char", 0), d.get("end_char", 0))
                    for d in context.dialogues
                    if d.get("start_char") is not None and d.get("end_char") is not None
                ]

                name_variants = detect_name_variants(
                    entities=context.entities,
                    mentions_by_entity=mentions_by_entity,
                    dialogue_spans=dialogue_spans if dialogue_spans else None,
                )

                for nv in name_variants:
                    result = engine.create_from_name_variant(
                        project_id=context.project_id,
                        entity_id=nv.entity_id,
                        entity_name=nv.entity_name,
                        canonical_form=nv.canonical_form,
                        variant_form=nv.variant_form,
                        canonical_count=nv.canonical_count,
                        variant_count=nv.variant_count,
                        variant_mentions=nv.variant_mentions,
                        all_in_dialogue=nv.all_in_dialogue,
                        confidence=nv.confidence,
                    )
                    if result.is_success:
                        context.alerts.append(result.value)

            except Exception as e:
                logger.warning(f"Name variant detection failed: {e}")

            context.stats["alerts_created"] = len(context.alerts)

        except Exception as e:
            logger.warning(f"Alert generation failed: {e}")
