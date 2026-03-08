"""
Emisión de alertas a partir de resultados de análisis.

Extraído de _analysis_phases.py — convierte grammar_issues, correction_issues,
inconsistencias de atributos, estado vital, ubicación, OOC y anacronismos en
alertas estructuradas a través del AlertEngine.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("narrative_assistant.api")


def _to_optional_int(value: Any) -> int | None:
    """Convierte un valor potencialmente heterogéneo a int."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if normalized and normalized.lstrip("-").isdigit():
            return int(normalized)
    return None


def _find_chapter_number_for_position(
    chapters_data: list[dict[str, Any]],
    start_char: int | None,
) -> int | None:
    """Resuelve número de capítulo a partir de una posición global."""
    if start_char is None:
        return None

    for chapter in chapters_data:
        ch_start = _to_optional_int(chapter.get("start_char"))
        ch_end = _to_optional_int(chapter.get("end_char"))
        ch_number = _to_optional_int(chapter.get("chapter_number"))
        if ch_start is None or ch_end is None or ch_number is None:
            continue
        if ch_start <= start_char < ch_end:
            return ch_number

    candidates = []
    for chapter in chapters_data:
        ch_start = _to_optional_int(chapter.get("start_char"))
        ch_number = _to_optional_int(chapter.get("chapter_number"))
        if ch_start is not None and ch_number is not None:
            candidates.append((abs(ch_start - start_char), ch_number))

    if candidates:
        candidates.sort()
        return candidates[0][1]

    return None


# ---------------------------------------------------------------------------
# Grammar & correction alerts
# ---------------------------------------------------------------------------


def emit_grammar_alerts(ctx: dict, tracker: Any) -> None:
    """Emite alertas de gramática y correcciones editoriales (parcial, tras run_grammar)."""
    from narrative_assistant.alerts.engine import get_alert_engine

    project_id = ctx["project_id"]
    chapters_data = ctx.get("chapters_data", [])
    grammar_issues = ctx.get("grammar_issues", [])
    correction_issues = ctx.get("correction_issues", [])

    alerts_created = 0
    alert_engine = get_alert_engine()

    # Alertas de errores gramaticales
    if grammar_issues:
        for issue in grammar_issues:
            try:
                issue_chapter = _to_optional_int(getattr(issue, "chapter", None))
                if issue_chapter is None:
                    issue_chapter = _find_chapter_number_for_position(
                        chapters_data,
                        _to_optional_int(getattr(issue, "start_char", None)),
                    )

                alert_result = alert_engine.create_from_grammar_issue(
                    project_id=project_id,
                    text=issue.text,
                    start_char=issue.start_char,
                    end_char=issue.end_char,
                    sentence=issue.sentence,
                    error_type=(
                        issue.error_type.value
                        if hasattr(issue.error_type, "value")
                        else str(issue.error_type)
                    ),
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                    explanation=issue.explanation,
                    rule_id=issue.rule_id if hasattr(issue, "rule_id") else "",
                    chapter=issue_chapter,
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating grammar alert: {e}")

    # Alertas de correcciones editoriales
    if correction_issues:
        for issue in correction_issues:
            try:
                issue_chapter = _to_optional_int(getattr(issue, "chapter_index", None))
                if issue_chapter is None:
                    issue_chapter = _find_chapter_number_for_position(
                        chapters_data,
                        _to_optional_int(getattr(issue, "start_char", None)),
                    )

                alert_result = alert_engine.create_from_correction_issue(
                    project_id=project_id,
                    category=issue.category,
                    issue_type=issue.issue_type,
                    text=issue.text,
                    start_char=issue.start_char,
                    end_char=issue.end_char,
                    explanation=issue.explanation,
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                    context=issue.context,
                    chapter=issue_chapter,
                    rule_id=issue.rule_id or "",
                    extra_data=issue.extra_data,
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating correction alert: {e}")

    if tracker is not None:
        tracker.update_storage(metrics_update={"alerts_generated": alerts_created})
    logger.info(f"Grammar alerts emitted: {alerts_created} alerts")

    ctx.setdefault("alerts_created", 0)
    ctx["alerts_created"] += alerts_created
    ctx["_grammar_alerts_emitted"] = True


# ---------------------------------------------------------------------------
# Consistency alerts (attributes, vital status, location, OOC, anachronisms)
# ---------------------------------------------------------------------------


def _build_attr_source(
    chapters_data: list[dict[str, Any]],
    value: Any,
    chapter: Any,
    excerpt: Any,
    start_char: Any,
) -> dict[str, Any]:
    normalized_start = _to_optional_int(start_char) or 0
    normalized_chapter = _to_optional_int(chapter)
    if normalized_chapter is None:
        normalized_chapter = _find_chapter_number_for_position(chapters_data, normalized_start)

    normalized_excerpt = str(excerpt or "")
    excerpt_window = len(normalized_excerpt.strip()) or 80

    return {
        "chapter": normalized_chapter,
        "start_char": normalized_start,
        "end_char": normalized_start + excerpt_window,
        "excerpt": normalized_excerpt,
        "value": str(value or ""),
    }


def emit_consistency_alerts(ctx: dict, tracker: Any) -> None:
    """Emite alertas de consistencia narrativa (tras run_consistency)."""
    from narrative_assistant.alerts.engine import AlertCategory, AlertSeverity, get_alert_engine

    project_id = ctx["project_id"]
    chapters_data = ctx.get("chapters_data", [])
    inconsistencies = ctx.get("inconsistencies", [])
    vital_status_report = ctx.get("vital_status_report")
    location_report = ctx.get("location_report")
    ooc_report = ctx.get("ooc_report")
    anachronism_report = ctx.get("anachronism_report")

    alerts_created = 0
    alert_engine = get_alert_engine()

    # Alertas de inconsistencias de atributos
    if inconsistencies:
        for inc in inconsistencies:
            try:
                def _inc_field(field_name: str, default: Any = None, _inc: Any = inc) -> Any:
                    if isinstance(_inc, dict):
                        return _inc.get(field_name, default)
                    return getattr(_inc, field_name, default)

                sources: list[dict[str, Any]] = []

                conflicting_values = _inc_field("conflicting_values", []) or []
                if isinstance(conflicting_values, list):
                    for cv in conflicting_values:
                        if isinstance(cv, dict):
                            cv_value = cv.get("value", "")
                            cv_chapter = cv.get("chapter")
                            cv_excerpt = cv.get("excerpt", "")
                            cv_position = cv.get("position", 0)
                        else:
                            cv_value = getattr(cv, "value", "")
                            cv_chapter = getattr(cv, "chapter", None)
                            cv_excerpt = getattr(cv, "excerpt", "")
                            cv_position = getattr(cv, "position", 0)

                        sources.append(
                            _build_attr_source(
                                chapters_data,
                                value=cv_value,
                                chapter=cv_chapter,
                                excerpt=cv_excerpt,
                                start_char=cv_position,
                            )
                        )

                sources.sort(
                    key=lambda source: (
                        source.get("chapter") is None,
                        _to_optional_int(source.get("chapter")) or 10**9,
                        _to_optional_int(source.get("start_char")) or 10**9,
                    )
                )

                deduped_sources: list[dict[str, Any]] = []
                seen_source_keys: set[tuple[str, int | None, int | None]] = set()
                for source in sources:
                    key = (
                        str(source.get("value", "")).strip().lower(),
                        _to_optional_int(source.get("chapter")),
                        _to_optional_int(source.get("start_char")),
                    )
                    if key in seen_source_keys:
                        continue
                    seen_source_keys.add(key)
                    deduped_sources.append(source)
                sources = deduped_sources

                fallback_value1_source = _build_attr_source(
                    chapters_data,
                    value=_inc_field("value1", ""),
                    chapter=_inc_field("value1_chapter"),
                    excerpt=_inc_field("value1_excerpt", ""),
                    start_char=_inc_field("value1_position", 0),
                )
                fallback_value2_source = _build_attr_source(
                    chapters_data,
                    value=_inc_field("value2", ""),
                    chapter=_inc_field("value2_chapter"),
                    excerpt=_inc_field("value2_excerpt", ""),
                    start_char=_inc_field("value2_position", 0),
                )

                if len(sources) < 2:
                    sources = [fallback_value1_source, fallback_value2_source]

                value1_source = sources[0] if sources else fallback_value1_source
                value2_source = (
                    sources[1]
                    if len(sources) > 1
                    else fallback_value2_source
                )
                attr_key = _inc_field("attribute_key")

                alert_result = alert_engine.create_from_attribute_inconsistency(
                    project_id=project_id,
                    entity_name=_inc_field("entity_name", ""),
                    entity_id=_to_optional_int(_inc_field("entity_id")) or 0,
                    attribute_key=(
                        attr_key.value
                        if hasattr(attr_key, "value")
                        else str(attr_key or "")
                    ),
                    value1=str(_inc_field("value1", "")),
                    value2=str(_inc_field("value2", "")),
                    value1_source=value1_source,
                    value2_source=value2_source,
                    explanation=str(_inc_field("explanation", "")),
                    confidence=float(_inc_field("confidence", 0.8)),
                    sources=sources,
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating attribute inconsistency alert: {e}")

    # Alertas de estado vital
    if vital_status_report and hasattr(vital_status_report, "post_mortem_appearances"):
        for appearance in vital_status_report.post_mortem_appearances:
            if appearance.is_valid:
                continue
            try:
                alert_result = alert_engine.create_from_deceased_reappearance(
                    project_id=project_id,
                    entity_id=appearance.entity_id,
                    entity_name=appearance.entity_name,
                    death_chapter=appearance.death_chapter,
                    appearance_chapter=appearance.appearance_chapter,
                    appearance_start_char=appearance.appearance_start_char,
                    appearance_end_char=appearance.appearance_end_char,
                    appearance_excerpt=appearance.appearance_excerpt,
                    appearance_type=appearance.appearance_type,
                    confidence=appearance.confidence,
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating deceased reappearance alert: {e}")

    # Alertas de inconsistencias de ubicación
    if location_report and hasattr(location_report, "inconsistencies"):
        for loc_inc in location_report.inconsistencies:
            try:
                location_chapter = _to_optional_int(getattr(loc_inc, "location2_chapter", None))
                if location_chapter is None:
                    location_chapter = _to_optional_int(getattr(loc_inc, "location1_chapter", None))

                alert_result = alert_engine.create_alert(
                    project_id=project_id,
                    category=AlertCategory.CONSISTENCY,
                    severity=AlertSeverity.WARNING,
                    alert_type="location_inconsistency",
                    title=f"Inconsistencia de ubicación: {loc_inc.entity_name}",
                    description=(
                        f"{loc_inc.entity_name} aparece en {loc_inc.location1_name} "
                        f"(cap {loc_inc.location1_chapter}) "
                        f"y en {loc_inc.location2_name} "
                        f"(cap {loc_inc.location2_chapter})"
                    ),
                    explanation=loc_inc.explanation,
                    confidence=loc_inc.confidence,
                    chapter=location_chapter,
                    excerpt=getattr(loc_inc, "location2_excerpt", "")
                    or getattr(loc_inc, "location1_excerpt", ""),
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating location inconsistency alert: {e}")

    # Alertas OOC
    if ooc_report and hasattr(ooc_report, "events"):
        for event in ooc_report.events:
            try:
                severity = (
                    AlertSeverity.WARNING if event.severity.value == "high" else AlertSeverity.INFO
                )
                alert_result = alert_engine.create_alert(
                    project_id=project_id,
                    category=AlertCategory.CONSISTENCY,
                    severity=severity,
                    alert_type="out_of_character",
                    title=f"Comportamiento atípico: {event.character_name}",
                    description=event.description,
                    explanation=event.explanation,
                    confidence=event.confidence,
                    chapter=(event.chapter_number if hasattr(event, "chapter_number") else None),
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating OOC alert: {e}")

    # Alertas de anacronismos
    if anachronism_report and anachronism_report.anachronisms:
        for anach in anachronism_report.anachronisms:
            try:
                anach_position = _to_optional_int(getattr(anach, "position", None))
                anach_chapter = _find_chapter_number_for_position(chapters_data, anach_position)
                anach_term = str(getattr(anach, "term", ""))

                alert_result = alert_engine.create_alert(
                    project_id=project_id,
                    category=AlertCategory.TIMELINE_ISSUE,
                    severity=AlertSeverity.WARNING,
                    alert_type="anachronism",
                    title=f"Posible anacronismo: {anach.term}",
                    description=(
                        f"'{anach.term}' aparece en un contexto temporal donde no existía "
                        f"({anach.expected_period})"
                    ),
                    explanation=anach.explanation,
                    confidence=anach.confidence,
                    chapter=anach_chapter,
                    start_char=anach_position,
                    end_char=((anach_position or 0) + max(len(anach_term), 1))
                    if anach_position is not None
                    else None,
                    excerpt=getattr(anach, "context", ""),
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating anachronism alert: {e}")

    ctx.setdefault("alerts_created", 0)
    ctx["alerts_created"] += alerts_created
    ctx["_consistency_alerts_emitted"] = True
    logger.info(f"Consistency alerts emitted: {alerts_created} alerts")
