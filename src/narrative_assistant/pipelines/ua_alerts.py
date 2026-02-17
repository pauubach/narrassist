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

            # Alertas de incoherencias emocionales
            for inc in context.emotional_incoherences:
                try:
                    result = engine.create_from_emotional_incoherence(
                        project_id=context.project_id,
                        entity_name=inc.get("entity_name", "Personaje"),
                        incoherence_type=inc.get("incoherence_type", "emotion_dialogue"),
                        declared_emotion=inc.get("declared_emotion", ""),
                        actual_behavior=inc.get("actual_behavior", ""),
                        declared_text=inc.get("declared_text", ""),
                        behavior_text=inc.get("behavior_text", ""),
                        explanation=inc.get("explanation", ""),
                        confidence=inc.get("confidence", 0.7),
                        suggestion=inc.get("suggestion"),
                        chapter=inc.get("chapter_id"),
                        start_char=inc.get("start_char"),
                        end_char=inc.get("end_char"),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Emotional incoherence alert failed: {e}")

            # Alertas de violaciones de focalización
            for violation in context.focalization_violations:
                try:
                    vtype = (
                        violation.violation_type.value
                        if hasattr(violation, "violation_type")
                        and hasattr(violation.violation_type, "value")
                        else str(getattr(violation, "violation_type", "unknown"))
                    )
                    excerpt = getattr(violation, "text_excerpt", "") or ""
                    result = engine.create_from_focalization_violation(
                        project_id=context.project_id,
                        violation_type=vtype,
                        declared_focalizer=getattr(violation, "declared_focalizer", "")
                        or "desconocido",
                        violated_rule=getattr(violation, "explanation", "") or vtype,
                        description=f"Violación de focalización: {vtype}",
                        explanation=getattr(violation, "explanation", "") or "",
                        chapter=getattr(violation, "chapter", 0),
                        start_char=getattr(violation, "position", 0),
                        end_char=getattr(violation, "position", 0) + len(excerpt),
                        excerpt=excerpt,
                        confidence=getattr(violation, "confidence", 0.8),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Focalization violation alert failed: {e}")

            # Alertas de estado vital (personajes fallecidos que reaparecen)
            if context.vital_status_report:
                post_mortem = getattr(
                    context.vital_status_report, "post_mortem_appearances", []
                )
                for appearance in post_mortem:
                    if not getattr(appearance, "is_valid", True):
                        try:
                            entity_name = getattr(
                                appearance, "entity_name", "Personaje"
                            )
                            result = engine.create_alert(
                                project_id=context.project_id,
                                alert_type="vital_status_deceased_reappearance",
                                category=AlertCategory.CONSISTENCY,
                                severity=AlertSeverity.CRITICAL,
                                title=f"Personaje fallecido reaparece: {entity_name}",
                                description=(
                                    f"{entity_name} falleció en cap. "
                                    f"{getattr(appearance, 'death_chapter', '?')} "
                                    f"pero reaparece activamente en cap. "
                                    f"{getattr(appearance, 'appearance_chapter', '?')}"
                                ),
                                explanation=(
                                    "Un personaje declarado como fallecido aparece "
                                    "posteriormente hablando o actuando. Esto puede "
                                    "ser un error de continuidad o necesita justificación "
                                    "narrativa (flashback, recuerdo, fantasma)."
                                ),
                                chapter=getattr(appearance, "appearance_chapter", None),
                                start_char=getattr(
                                    appearance, "appearance_start_char", None
                                ),
                                end_char=getattr(
                                    appearance, "appearance_end_char", None
                                ),
                                confidence=getattr(appearance, "confidence", 0.9),
                                extra_data={
                                    "death_chapter": getattr(
                                        appearance, "death_chapter", None
                                    ),
                                    "appearance_excerpt": getattr(
                                        appearance, "appearance_excerpt", ""
                                    ),
                                },
                            )
                            if result.is_success:
                                context.alerts.append(result.value)
                        except Exception as e:
                            logger.debug(f"Vital status alert failed: {e}")

            # Alertas de ubicaciones imposibles de personajes
            for inc in context.location_inconsistencies:
                try:
                    entity_name = getattr(inc, "entity_name", "Personaje")
                    loc1 = getattr(inc, "location1_name", "?")
                    loc2 = getattr(inc, "location2_name", "?")
                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type="character_location_impossibility",
                        category=AlertCategory.CONSISTENCY,
                        severity=AlertSeverity.WARNING,
                        title=f"Ubicación imposible: {entity_name}",
                        description=(
                            f"{entity_name} aparece en {loc1} y en {loc2} "
                            f"simultáneamente o sin transición narrativa"
                        ),
                        explanation=getattr(inc, "explanation", ""),
                        confidence=getattr(inc, "confidence", 0.8),
                        extra_data={
                            "location1": loc1,
                            "location2": loc2,
                            "chapter1": getattr(inc, "location1_chapter", None),
                            "chapter2": getattr(inc, "location2_chapter", None),
                        },
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Location inconsistency alert failed: {e}")

            # Alertas de comportamiento fuera de personaje (OOC)
            for event in context.ooc_events:
                try:
                    if isinstance(event, dict):
                        entity_name = event.get("entity_name", "Personaje")
                        ooc_type = event.get("ooc_type", "behavioral")
                        severity_str = event.get("severity", "warning").upper()
                    else:
                        entity_name = getattr(event, "entity_name", "Personaje")
                        ooc_type = getattr(event, "ooc_type", "behavioral")
                        severity_str = (
                            getattr(event, "severity", "warning")
                            .value
                            if hasattr(getattr(event, "severity", ""), "value")
                            else str(getattr(event, "severity", "warning"))
                        ).upper()

                    severity = getattr(AlertSeverity, severity_str, AlertSeverity.WARNING)
                    ev = event if isinstance(event, dict) else event

                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type=f"ooc_{ooc_type}",
                        category=AlertCategory.BEHAVIORAL,
                        severity=severity,
                        title=f"Fuera de personaje: {entity_name}",
                        description=(
                            ev.get("description", "")
                            if isinstance(ev, dict)
                            else getattr(ev, "description", "")
                        )
                        or f"{entity_name} actúa de forma inconsistente con su perfil",
                        explanation=(
                            ev.get("explanation", "")
                            if isinstance(ev, dict)
                            else getattr(ev, "explanation", "")
                        ),
                        confidence=(
                            ev.get("confidence", 0.7)
                            if isinstance(ev, dict)
                            else getattr(ev, "confidence", 0.7)
                        ),
                        extra_data={
                            "ooc_type": ooc_type,
                            "chapter": (
                                ev.get("chapter")
                                if isinstance(ev, dict)
                                else getattr(ev, "chapter", None)
                            ),
                        },
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"OOC alert failed: {e}")

            # Alertas de hilos narrativos abandonados (Chekhov)
            for thread in context.chekhov_threads:
                try:
                    if isinstance(thread, dict):
                        name = thread.get("entity_name", thread.get("name", "Elemento"))
                        intro_ch = thread.get("introduction_chapter", "?")
                        last_ch = thread.get("last_mention_chapter", "?")
                        description = thread.get("description", "")
                    else:
                        name = getattr(thread, "entity_name", getattr(thread, "name", "Elemento"))
                        intro_ch = getattr(thread, "introduction_chapter", "?")
                        last_ch = getattr(thread, "last_mention_chapter", "?")
                        description = getattr(thread, "description", "")

                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type="chekhov_unfired",
                        category=AlertCategory.STRUCTURE,
                        severity=AlertSeverity.INFO,
                        title=f"Hilo abandonado: {name}",
                        description=description
                        or (
                            f"'{name}' se introduce con detalle en cap. {intro_ch} "
                            f"pero desaparece después de cap. {last_ch}"
                        ),
                        explanation=(
                            "Un personaje u objeto introducido con detalle narrativo "
                            "no vuelve a tener relevancia. Según el principio de Chekhov, "
                            "esto puede frustrar las expectativas del lector."
                        ),
                        confidence=0.6,
                        extra_data={
                            "introduction_chapter": intro_ch,
                            "last_mention_chapter": last_ch,
                        },
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Chekhov alert failed: {e}")

            # Alertas de personajes planos (shallow characters)
            for sc in context.shallow_characters:
                try:
                    name = sc.get("entity_name", "Personaje") if isinstance(sc, dict) else getattr(sc, "entity_name", "Personaje")
                    desc = sc.get("description", "") if isinstance(sc, dict) else getattr(sc, "description", "")

                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type="shallow_character",
                        category=AlertCategory.BEHAVIORAL
                        if hasattr(AlertCategory, "BEHAVIORAL")
                        else AlertCategory.STYLE,
                        severity=AlertSeverity.INFO,
                        title=f"Personaje plano: {name}",
                        description=desc
                        or f"'{name}' tiene muchas menciones pero poco desarrollo narrativo",
                        explanation=(
                            "Este personaje aparece frecuentemente pero tiene pocas "
                            "dimensiones narrativas (atributos, diálogos, acciones). "
                            "Considerar profundizar su desarrollo o reducir su presencia."
                        ),
                        confidence=0.6,
                        extra_data={
                            "mentions": sc.get("mentions", 0) if isinstance(sc, dict) else 0,
                            "chapters_present": sc.get("chapters_present", 0) if isinstance(sc, dict) else 0,
                            "attributes": sc.get("attributes", 0) if isinstance(sc, dict) else 0,
                            "dialogues": sc.get("dialogues", 0) if isinstance(sc, dict) else 0,
                        },
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Shallow character alert failed: {e}")

            # Alertas de anacronismo de conocimiento
            for anach in context.knowledge_anachronisms:
                try:
                    knower = anach.get("knower_name", "Personaje")
                    known = anach.get("known_name", "otro")
                    fact = anach.get("fact_value", "")
                    desc = anach.get("description", "")
                    severity_str = anach.get("severity", "medium")

                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type="knowledge_anachronism",
                        category=AlertCategory.CONSISTENCY,
                        severity=AlertSeverity.WARNING
                        if severity_str == "high"
                        else AlertSeverity.INFO,
                        title=f"Conocimiento prematuro: {knower} → {known}",
                        description=desc,
                        explanation=(
                            f"{knower} demuestra conocimiento sobre '{fact}' de {known} "
                            f"antes de haberlo aprendido en la narrativa."
                        ),
                        chapter_index=anach.get("used_chapter"),
                        extra_data={
                            "used_chapter": anach.get("used_chapter"),
                            "learned_chapter": anach.get("learned_chapter"),
                            "fact_value": fact,
                        },
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Knowledge anachronism alert failed: {e}")

            # Alertas de oraciones de baja energía (voz pasiva, verbos débiles)
            for sent in context.sentence_energy_issues:
                try:
                    energy = getattr(sent, "energy_score", 0)
                    is_passive = getattr(sent, "is_passive", False)
                    has_weak = getattr(sent, "has_weak_verb", False)
                    text = getattr(sent, "text", "")[:150]

                    issues_desc = []
                    if is_passive:
                        issues_desc.append("voz pasiva")
                    if has_weak:
                        issues_desc.append("verbos débiles")

                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type="style_low_energy_sentence",
                        category=AlertCategory.STYLE,
                        severity=AlertSeverity.HINT,
                        title=f"Oración de baja energía ({', '.join(issues_desc) or 'baja'})",
                        description=f"Energía: {energy:.0f}/100 — {text}",
                        explanation=(
                            "Oración con construcciones que restan dinamismo: "
                            + ", ".join(issues_desc)
                            + ". Considerar reescribir con verbos de acción."
                        ),
                        start_char=getattr(sent, "start_char", None),
                        end_char=getattr(sent, "end_char", None),
                        confidence=0.6,
                        extra_data={
                            "energy_score": energy,
                            "is_passive": is_passive,
                            "has_weak_verb": has_weak,
                        },
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Sentence energy alert failed: {e}")

            # Alertas de déficit sensorial
            if context.sensory_report:
                sparse_chapters = context.sensory_report.get("sparse_chapters", [])
                for ch_num in sparse_chapters:
                    try:
                        result = engine.create_alert(
                            project_id=context.project_id,
                            alert_type="style_sensory_deficit",
                            category=AlertCategory.STYLE,
                            severity=AlertSeverity.HINT,
                            title=f"Déficit sensorial: capítulo {ch_num}",
                            description=(
                                f"El capítulo {ch_num} tiene pocas o ninguna "
                                f"descripción sensorial (colores, olores, texturas, "
                                f"sonidos, sabores)."
                            ),
                            explanation=(
                                "Las descripciones sensoriales enriquecen la experiencia "
                                "del lector y hacen la narración más inmersiva."
                            ),
                            confidence=0.5,
                            extra_data={
                                k: (v.value if hasattr(v, "value") else str(v))
                                if not isinstance(v, (str, int, float, bool, type(None), list))
                                else v
                                for k, v in context.sensory_report.items()
                            },
                        )
                        if result.is_success:
                            context.alerts.append(result.value)
                    except Exception as e:
                        logger.debug(f"Sensory deficit alert failed: {e}")

            # Alertas de tipografía
            for issue in context.typography_issues:
                try:
                    issue_type = (
                        issue.issue_type.value
                        if hasattr(issue, "issue_type")
                        and hasattr(issue.issue_type, "value")
                        else str(getattr(issue, "issue_type", "unknown"))
                    )
                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type=f"typography_{issue_type}",
                        category=AlertCategory.TYPOGRAPHY
                        if hasattr(AlertCategory, "TYPOGRAPHY")
                        else AlertCategory.STYLE,
                        severity=AlertSeverity.HINT,
                        title=f"Tipografía: {getattr(issue, 'text', issue_type)}",
                        description=getattr(issue, "text", ""),
                        explanation=getattr(issue, "suggestion", "") or getattr(issue, "explanation", ""),
                        start_char=getattr(issue, "start_char", None),
                        end_char=getattr(issue, "end_char", None),
                        confidence=getattr(issue, "confidence", 0.8),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Typography alert failed: {e}")

            # Alertas de cambio de punto de vista
            for issue in context.pov_issues:
                try:
                    issue_type = (
                        issue.issue_type.value
                        if hasattr(issue, "issue_type")
                        and hasattr(issue.issue_type, "value")
                        else str(getattr(issue, "issue_type", "unknown"))
                    )
                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type=f"pov_{issue_type}",
                        category=AlertCategory.STYLE,
                        severity=AlertSeverity.WARNING,
                        title=f"Punto de vista: {getattr(issue, 'text', issue_type)}",
                        description=getattr(issue, "text", ""),
                        explanation=getattr(issue, "suggestion", "") or getattr(issue, "explanation", ""),
                        start_char=getattr(issue, "start_char", None),
                        end_char=getattr(issue, "end_char", None),
                        confidence=getattr(issue, "confidence", 0.75),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"POV alert failed: {e}")

            # Alertas de referencias bibliográficas
            for issue in context.reference_issues:
                try:
                    issue_type = (
                        issue.issue_type.value
                        if hasattr(issue, "issue_type")
                        and hasattr(issue.issue_type, "value")
                        else str(getattr(issue, "issue_type", "unknown"))
                    )
                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type=f"reference_{issue_type}",
                        category=AlertCategory.STYLE,
                        severity=AlertSeverity.INFO,
                        title=f"Referencia: {getattr(issue, 'text', issue_type)}",
                        description=getattr(issue, "text", ""),
                        explanation=getattr(issue, "suggestion", "") or getattr(issue, "explanation", ""),
                        start_char=getattr(issue, "start_char", None),
                        end_char=getattr(issue, "end_char", None),
                        confidence=getattr(issue, "confidence", 0.8),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Reference alert failed: {e}")

            # Alertas de siglas
            for issue in context.acronym_issues:
                try:
                    issue_type = (
                        issue.issue_type.value
                        if hasattr(issue, "issue_type")
                        and hasattr(issue.issue_type, "value")
                        else str(getattr(issue, "issue_type", "unknown"))
                    )
                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type=f"acronym_{issue_type}",
                        category=AlertCategory.STYLE,
                        severity=AlertSeverity.HINT,
                        title=f"Sigla: {getattr(issue, 'text', issue_type)}",
                        description=getattr(issue, "text", ""),
                        explanation=getattr(issue, "suggestion", "") or getattr(issue, "explanation", ""),
                        start_char=getattr(issue, "start_char", None),
                        end_char=getattr(issue, "end_char", None),
                        confidence=getattr(issue, "confidence", 0.7),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Acronym alert failed: {e}")

            # Alertas de muletillas lingüísticas (FillerDetector)
            for issue in context.filler_issues:
                try:
                    issue_type = (
                        issue.issue_type.value
                        if hasattr(issue, "issue_type")
                        and hasattr(issue.issue_type, "value")
                        else str(getattr(issue, "issue_type", "linguistic_filler"))
                    )
                    result = engine.create_alert(
                        project_id=context.project_id,
                        alert_type=issue_type,  # NO añadir prefijo, usar issue_type directo
                        category=AlertCategory.REPETITION,  # CrutchWords y Filler comparten categoría
                        severity=AlertSeverity.INFO,
                        title=f"Muletilla: {getattr(issue, 'text', '')}",
                        description=getattr(issue, "explanation", ""),
                        explanation=getattr(issue, "explanation", ""),
                        suggestion=getattr(issue, "suggestion", None),
                        start_char=getattr(issue, "start_char", None),
                        end_char=getattr(issue, "end_char", None),
                        confidence=getattr(issue, "confidence", 0.7),
                        extra_data=getattr(issue, "extra_data", {}),
                    )
                    if result.is_success:
                        context.alerts.append(result.value)
                except Exception as e:
                    logger.debug(f"Filler alert failed: {e}")

            context.stats["alerts_created"] = len(context.alerts)

        except Exception as e:
            logger.warning(f"Alert generation failed: {e}")
