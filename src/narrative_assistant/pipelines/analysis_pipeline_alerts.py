"""Creación de alertas especializadas extraída de `analysis_pipeline`."""

from __future__ import annotations

import logging

from ..alerts.engine import get_alert_engine
from ..alerts.models import Alert, AlertCategory, AlertSeverity
from ..analysis.attribute_consistency import AttributeInconsistency
from ..analysis.emotional_coherence import EmotionalIncoherence, IncoherenceType
from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from ..entities.repository import get_entity_repository
from ..focalization import FocalizationViolation
from ..temporal import TemporalInconsistency
from ..voice import VoiceDeviation

logger = logging.getLogger(__name__)


def create_alerts_from_inconsistencies(
    project_id: int,
    inconsistencies: list[AttributeInconsistency],
    min_confidence: float,
) -> Result[list[Alert]]:
    """Convierte inconsistencias de atributos en alertas."""
    try:
        engine = get_alert_engine()
        entity_repo = get_entity_repository()
        alerts = []

        logger.info("Processing %s inconsistencies for alerts...", len(inconsistencies))
        for incon in inconsistencies:
            logger.debug(
                "Processing inconsistency: %s.%s = %s vs %s, confidence=%s",
                incon.entity_name,
                incon.attribute_key.value,
                incon.value1,
                incon.value2,
                incon.confidence,
            )

            if incon.confidence < min_confidence:
                logger.debug("  -> Skipped: confidence %s < %s", incon.confidence, min_confidence)
                continue

            entity_id = incon.entity_id
            if entity_id == 0:
                found_entities = entity_repo.find_entities_by_name(
                    project_id=project_id,
                    name=incon.entity_name,
                )
                if not found_entities:
                    found_entities = entity_repo.find_entities_by_name(
                        project_id=project_id,
                        name=incon.entity_name,
                        fuzzy=True,
                    )
                if found_entities:
                    entity_id = found_entities[0].id
                    logger.debug("Found entity_id=%s for '%s'", entity_id, incon.entity_name)
                else:
                    logger.warning("Entity not found: %s, skipping alert", incon.entity_name)
                    continue

            if incon.conflicting_values and len(incon.conflicting_values) > 0:
                sources = [
                    {
                        "chapter": cv.chapter,
                        "position": cv.position,
                        "start_char": cv.position,
                        "end_char": cv.position + 100,
                        "text": cv.excerpt,
                        "value": cv.value,
                    }
                    for cv in incon.conflicting_values
                ]
                value1_source = sources[0] if len(sources) >= 1 else {}
                value2_source = sources[1] if len(sources) >= 2 else {}
            else:
                value1_source = {
                    "chapter": incon.value1_chapter,
                    "position": incon.value1_position,
                    "start_char": incon.value1_position,
                    "end_char": incon.value1_position + 100,
                    "text": incon.value1_excerpt,
                    "value": incon.value1,
                }
                value2_source = {
                    "chapter": incon.value2_chapter,
                    "position": incon.value2_position,
                    "start_char": incon.value2_position,
                    "end_char": incon.value2_position + 100,
                    "text": incon.value2_excerpt,
                    "value": incon.value2,
                }
                sources = [value1_source, value2_source]

            alert_result = engine.create_from_attribute_inconsistency(
                project_id=project_id,
                entity_name=incon.entity_name,
                entity_id=entity_id,
                attribute_key=incon.attribute_key.value,
                value1=incon.value1,
                value2=incon.value2,
                value1_source=value1_source,
                value2_source=value2_source,
                explanation=incon.explanation,
                confidence=incon.confidence,
                sources=sources,
            )

            if alert_result.is_success:
                alerts.append(alert_result.value)
            else:
                logger.warning("Failed to create alert: %s", alert_result.error)

        logger.info("Created %s alerts from %s inconsistencies", len(alerts), len(inconsistencies))
        return Result.success(alerts)

    except Exception as exc:
        return Result.failure(
            NarrativeError(
                message=f"Alert creation failed: {exc}",
                severity=ErrorSeverity.RECOVERABLE,
            )
        )


def create_alerts_from_temporal_inconsistencies(
    project_id: int,
    inconsistencies: list[TemporalInconsistency],
) -> Result[list[Alert]]:
    """Crea alertas a partir de inconsistencias temporales."""
    try:
        from ..alerts.repository import get_alert_repository

        alert_repo = get_alert_repository()
        alerts = []
        severity_map = {
            "critical": AlertSeverity.CRITICAL,
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.INFO,
        }
        category_map = {
            "age_contradiction": AlertCategory.CHARACTER_CONSISTENCY,
            "impossible_sequence": AlertCategory.TIMELINE_ISSUE,
            "time_jump_suspicious": AlertCategory.TIMELINE_ISSUE,
            "marker_conflict": AlertCategory.TIMELINE_ISSUE,
            "character_age_mismatch": AlertCategory.CHARACTER_CONSISTENCY,
            "anachronism": AlertCategory.TIMELINE_ISSUE,
        }

        for incon in inconsistencies:
            severity = severity_map.get(incon.severity.value, AlertSeverity.INFO)
            category = category_map.get(incon.inconsistency_type.value, AlertCategory.TIMELINE_ISSUE)
            title = f"Inconsistencia temporal: {incon.inconsistency_type.value.replace('_', ' ').title()}"
            description = incon.description
            if incon.expected and incon.found:
                description += f"\n\nEsperado: {incon.expected}\nEncontrado: {incon.found}"
            if incon.suggestion:
                description += f"\n\nSugerencia: {incon.suggestion}"

            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=None,
                category=category.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=incon.chapter,
                source_position=incon.position,
                confidence=incon.confidence,
            )
            if alert_id:
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)

        logger.info("Created %s temporal alerts", len(alerts))
        return Result.success(alerts)

    except Exception as exc:
        logger.exception("Error creating temporal alerts")
        return Result.failure(
            NarrativeError(
                message=f"Failed to create temporal alerts: {exc}",
                severity=ErrorSeverity.RECOVERABLE,
            )
        )


def create_alerts_from_voice_deviations(
    project_id: int,
    deviations: list[VoiceDeviation],
) -> Result[list[Alert]]:
    """Crea alertas a partir de desviaciones de voz."""
    from ..alerts.repository import get_alert_repository
    from ..voice.deviations import DeviationType

    try:
        alert_repo = get_alert_repository()
        alerts = []
        severity_map = {
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }
        category_map = {
            DeviationType.FORMALITY_SHIFT.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.LENGTH_ANOMALY.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.VOCABULARY_SHIFT.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.FILLER_ANOMALY.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.PUNCTUATION_SHIFT.value: AlertCategory.VOICE_DEVIATION,
        }

        for deviation in deviations:
            severity = severity_map.get(deviation.severity.value, AlertSeverity.INFO)
            category = category_map.get(
                deviation.deviation_type.value,
                AlertCategory.CHARACTER_CONSISTENCY,
            )
            title = f"Desviación de voz: {deviation.entity_name}"
            description = deviation.description
            if deviation.text:
                preview = deviation.text[:150] + "..." if len(deviation.text) > 150 else deviation.text
                description += f'\n\nTexto: "{preview}"'

            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=deviation.entity_id,
                category=category.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=deviation.chapter,
                source_position=deviation.position,
                confidence=deviation.confidence,
            )
            if alert_id:
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)

        logger.info("Created %s voice alerts", len(alerts))
        return Result.success(alerts)

    except Exception as exc:
        logger.exception("Error creating voice alerts")
        return Result.failure(
            NarrativeError(
                message=f"Failed to create voice alerts: {exc}",
                severity=ErrorSeverity.RECOVERABLE,
            )
        )


def create_alerts_from_focalization_violations(
    project_id: int,
    violations: list[FocalizationViolation],
) -> Result[list[Alert]]:
    """Crea alertas a partir de violaciones de focalización."""
    from ..alerts.repository import get_alert_repository

    try:
        alert_repo = get_alert_repository()
        alerts = []
        severity_map = {
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }

        for violation in violations:
            severity = severity_map.get(violation.severity.value, AlertSeverity.INFO)
            title = f"Violación de focalización: {violation.violation_type.value.replace('_', ' ').title()}"
            if violation.entity_name:
                title = f"Violación de focalización: {violation.entity_name}"

            description = violation.explanation
            if violation.declared_focalizer:
                description += f"\n\nFocalizador declarado: {violation.declared_focalizer}"
            if violation.suggestion:
                description += f"\n\nSugerencia: {violation.suggestion}"
            if violation.text_excerpt:
                excerpt = (
                    violation.text_excerpt[:150] + "..."
                    if len(violation.text_excerpt) > 150
                    else violation.text_excerpt
                )
                description += f'\n\nTexto: "{excerpt}"'

            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=violation.entity_involved,
                category=AlertCategory.FOCALIZATION.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=violation.chapter,
                source_position=violation.position,
                confidence=violation.confidence,
            )
            if alert_id:
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)

        logger.info("Created %s focalization alerts", len(alerts))
        return Result.success(alerts)

    except Exception as exc:
        logger.exception("Error creating focalization alerts")
        return Result.failure(
            NarrativeError(
                message=f"Failed to create focalization alerts: {exc}",
                severity=ErrorSeverity.RECOVERABLE,
            )
        )


def create_alerts_from_emotional_incoherences(
    project_id: int,
    incoherences: list[EmotionalIncoherence],
) -> Result[list[Alert]]:
    """Crea alertas a partir de incoherencias emocionales."""
    from ..alerts.repository import get_alert_repository

    try:
        alert_repo = get_alert_repository()
        alerts = []
        severity_map = {
            IncoherenceType.EMOTION_DIALOGUE: AlertSeverity.WARNING,
            IncoherenceType.EMOTION_ACTION: AlertSeverity.INFO,
            IncoherenceType.TEMPORAL_JUMP: AlertSeverity.INFO,
            IncoherenceType.NARRATOR_BIAS: AlertSeverity.HINT,
        }
        type_labels = {
            IncoherenceType.EMOTION_DIALOGUE: "Diálogo incoherente con emoción",
            IncoherenceType.EMOTION_ACTION: "Acción incoherente con emoción",
            IncoherenceType.TEMPORAL_JUMP: "Cambio emocional abrupto",
            IncoherenceType.NARRATOR_BIAS: "Inconsistencia del narrador",
        }

        for incoherence in incoherences:
            if incoherence.confidence >= 0.8:
                severity = AlertSeverity.WARNING
            elif incoherence.confidence >= 0.6:
                severity = severity_map.get(incoherence.incoherence_type, AlertSeverity.INFO)
            else:
                severity = AlertSeverity.HINT

            title = type_labels.get(
                incoherence.incoherence_type,
                f"Incoherencia emocional: {incoherence.incoherence_type.value}",
            )
            if incoherence.entity_name:
                title = f"{incoherence.entity_name}: {title}"

            description = incoherence.explanation
            if incoherence.declared_emotion and incoherence.actual_behavior:
                description += (
                    f"\n\nEmoción declarada: {incoherence.declared_emotion}"
                    f"\nComportamiento detectado: {incoherence.actual_behavior}"
                )
            if incoherence.behavior_text:
                excerpt = (
                    incoherence.behavior_text[:150] + "..."
                    if len(incoherence.behavior_text) > 150
                    else incoherence.behavior_text
                )
                description += f'\n\nTexto: "{excerpt}"'
            if incoherence.suggestion:
                description += f"\n\nSugerencia: {incoherence.suggestion}"

            entity_id = None
            if incoherence.entity_name:
                entity_repo = get_entity_repository()
                entity = entity_repo.find_by_name(project_id, incoherence.entity_name)
                if entity:
                    entity_id = entity.id

            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=entity_id,
                category=AlertCategory.EMOTIONAL.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=incoherence.chapter_id,
                source_position=incoherence.start_char,
                confidence=incoherence.confidence,
            )
            if alert_id:
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)

        logger.info("Created %s emotional alerts", len(alerts))
        return Result.success(alerts)

    except Exception as exc:
        logger.exception("Error creating emotional alerts")
        return Result.failure(
            NarrativeError(
                message=f"Failed to create emotional alerts: {exc}",
                severity=ErrorSeverity.RECOVERABLE,
            )
        )
