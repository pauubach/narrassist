"""
Sub-fases de consistencia narrativa.

Extraído de _analysis_phases.py — cada sub-fase es una función independiente
que analiza un aspecto de la consistencia del manuscrito.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("narrative_assistant.api")


# ---------------------------------------------------------------------------
# Data preparation helpers
# ---------------------------------------------------------------------------


def prepare_chapters_for_analysis(chapters_data: list[dict]) -> list[dict]:
    """Convierte chapters_data al formato esperado por los sub-analizadores."""
    return [
        {
            "number": ch["chapter_number"],
            "content": ch["content"],
            "text": ch["content"],
            "start_char": ch["start_char"],
        }
        for ch in chapters_data
    ]


def prepare_entities_for_analysis(entities: list) -> list[dict]:
    """Convierte entidades al formato dict esperado por los sub-analizadores."""
    return [
        {
            "id": e.id,
            "canonical_name": e.canonical_name,
            "entity_type": (
                e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type)
            ),
            "aliases": e.aliases if hasattr(e, "aliases") else [],
        }
        for e in entities
    ]


def build_temporal_map(ctx: dict) -> Any:
    """Construye TemporalMap para narrativas no lineales (BK-08)."""
    try:
        from narrative_assistant.temporal.temporal_map import TemporalMap

        timeline = ctx.get("timeline")
        if timeline is not None:
            temporal_map = TemporalMap.from_timeline(timeline)
            logger.info(f"Built TemporalMap with {len(temporal_map._slices)} slices")
            return temporal_map
    except Exception as e:
        logger.warning(f"Failed to build TemporalMap: {e}. Falling back to chapter comparison.")
    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.1: Estado vital
# ---------------------------------------------------------------------------


def analyze_vital_status_subphase(
    project_id: int,
    chapters_for_analysis: list[dict],
    entities_for_analysis: list[dict],
    temporal_map: Any,
    db_session: Any,
) -> Any:
    """Analiza estado vital de personajes y persiste resultados."""
    try:
        from narrative_assistant.analysis.vital_status import analyze_vital_status

        vital_result = analyze_vital_status(
            project_id=project_id,
            chapters=chapters_for_analysis,
            entities=entities_for_analysis,
            temporal_map=temporal_map,
        )

        if vital_result.is_success:
            report = vital_result.value
            logger.info(
                f"Vital status analysis: {len(report.death_events)} deaths, "
                f"{len(report.post_mortem_appearances)} post-mortem appearances"
            )

            # Persist vital status events to DB
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        "DELETE FROM vital_status_events WHERE project_id = ?",
                        (project_id,),
                    )
                    for de in report.death_events:
                        conn.execute(
                            """INSERT INTO vital_status_events
                            (project_id, entity_id, entity_name, event_type,
                             chapter, start_char, end_char, excerpt,
                             confidence, death_type)
                            VALUES (?, ?, ?, 'death', ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                de.entity_id,
                                de.entity_name,
                                de.chapter,
                                de.start_char,
                                de.end_char,
                                de.excerpt,
                                de.confidence,
                                de.death_type,
                            ),
                        )
                    for pm in report.post_mortem_appearances:
                        conn.execute(
                            """INSERT INTO vital_status_events
                            (project_id, entity_id, entity_name, event_type,
                             chapter, start_char, end_char, excerpt,
                             confidence, death_chapter, appearance_type, is_valid)
                            VALUES (?, ?, ?, 'post_mortem_appearance', ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                pm.entity_id,
                                pm.entity_name,
                                pm.appearance_chapter,
                                pm.appearance_start_char,
                                pm.appearance_end_char,
                                pm.appearance_excerpt,
                                pm.confidence,
                                pm.death_chapter,
                                pm.appearance_type,
                                1 if pm.is_valid else 0,
                            ),
                        )
                persisted = len(report.death_events) + len(report.post_mortem_appearances)
                logger.info(f"Persisted {persisted} vital status events to DB")
            except Exception as persist_err:
                logger.warning(f"Error persisting vital status (continuing): {persist_err}")

            return report
        else:
            logger.warning(f"Vital status analysis failed: {vital_result.error}")

    except ImportError as e:
        logger.warning(f"Vital status module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in vital status analysis: {e}", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.2: Ubicaciones de personajes
# ---------------------------------------------------------------------------


def analyze_character_locations_subphase(
    project_id: int,
    chapters_for_analysis: list[dict],
    entities_for_analysis: list[dict],
    db_session: Any,
) -> Any:
    """Analiza ubicaciones de personajes y persiste resultados."""
    try:
        from narrative_assistant.analysis.character_location import (
            analyze_character_locations,
        )

        location_result = analyze_character_locations(
            project_id=project_id,
            chapters=chapters_for_analysis,
            entities=entities_for_analysis,
        )

        if location_result.is_success:
            report = location_result.value
            inconsistency_count = (
                len(report.inconsistencies) if hasattr(report, "inconsistencies") else 0
            )
            logger.info(
                f"Character location analysis: {len(report.location_events)} events, "
                f"{inconsistency_count} inconsistencies"
            )

            # Persist character location events to DB
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        "DELETE FROM character_location_events WHERE project_id = ?",
                        (project_id,),
                    )
                    for le in report.location_events:
                        conn.execute(
                            """INSERT INTO character_location_events
                            (project_id, entity_id, entity_name, location_name,
                             chapter, start_char, end_char, excerpt,
                             change_type, confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                le.entity_id,
                                le.entity_name,
                                le.location_name,
                                le.chapter,
                                le.start_char,
                                le.end_char,
                                le.excerpt,
                                le.change_type.value
                                if hasattr(le.change_type, "value")
                                else str(le.change_type),
                                le.confidence,
                            ),
                        )
                logger.info(
                    f"Persisted {len(report.location_events)} character location events to DB"
                )
            except Exception as persist_err:
                logger.warning(f"Error persisting character locations (continuing): {persist_err}")

            return report
        else:
            logger.warning(f"Character location analysis failed: {location_result.error}")

    except ImportError as e:
        logger.warning(f"Character location module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in character location analysis: {e}", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.3: Resumen por capítulo
# ---------------------------------------------------------------------------


def analyze_chapter_progress_subphase(project_id: int) -> Any:
    """Analiza progreso narrativo por capítulo."""
    try:
        from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress

        report = analyze_chapter_progress(
            project_id=project_id,
            db_path=None,
            mode="basic",
        )

        if report:
            logger.info(
                f"Chapter progress analysis: {len(report.chapters)} chapters analyzed"
            )
        return report

    except ImportError as e:
        logger.warning(f"Chapter summary module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in chapter progress analysis: {e}", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.4: Out-of-character
# ---------------------------------------------------------------------------


def analyze_ooc_subphase(
    project_id: int,
    entities: list,
    chapters_data: list[dict],
    db_session: Any,
) -> Any:
    """Detecta comportamiento fuera de personaje y persiste resultados."""
    try:
        from narrative_assistant.analysis.character_profiling import CharacterProfiler
        from narrative_assistant.analysis.out_of_character import OutOfCharacterDetector

        profiler = CharacterProfiler()
        character_entities = [
            e
            for e in entities
            if (
                hasattr(e.entity_type, "value")
                and e.entity_type.value in ("character", "PER", "PERSON")
            )
            or (
                isinstance(e.entity_type, str)
                and e.entity_type in ("character", "PER", "PERSON")
            )
        ]
        if not character_entities:
            return None

        chapter_texts = {ch["chapter_number"]: ch["content"] for ch in chapters_data}
        profiles = profiler.build_profiles(character_entities, chapters_data, chapter_texts)  # type: ignore[arg-type]
        if not profiles:
            return None

        ooc_detector = OutOfCharacterDetector()
        ooc_report = ooc_detector.detect(
            profiles=profiles,
            chapter_texts=chapter_texts,
        )
        logger.info(f"OOC detection: {len(ooc_report.events)} events found")

        # Persist OOC events to DB — always delete old events first so that
        # a re-analysis that finds zero events correctly clears stale rows.
        if ooc_report:
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        "DELETE FROM ooc_events WHERE project_id = ?",
                        (project_id,),
                    )
                    for ev in ooc_report.events:
                        conn.execute(
                            """INSERT INTO ooc_events
                            (project_id, entity_id, entity_name,
                             deviation_type, severity, description,
                             expected, actual, chapter, excerpt,
                             confidence, is_intentional)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                ev.entity_id,
                                ev.entity_name,
                                ev.deviation_type.value
                                if hasattr(ev.deviation_type, "value")
                                else str(ev.deviation_type),
                                ev.severity.value
                                if hasattr(ev.severity, "value")
                                else str(ev.severity),
                                ev.description,
                                ev.expected,
                                ev.actual,
                                ev.chapter,
                                ev.excerpt,
                                ev.confidence,
                                1 if ev.is_intentional else 0,
                            ),
                        )
                logger.info(f"Persisted {len(ooc_report.events)} OOC events to DB")
            except Exception as persist_err:
                logger.warning(f"Error persisting OOC events (continuing): {persist_err}")

        return ooc_report

    except ImportError as e:
        logger.warning(f"OOC detection module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in OOC detection: {e}", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.5: Anacronismos
# ---------------------------------------------------------------------------


def analyze_anachronisms_subphase(full_text: str) -> Any:
    """Detecta anacronismos en el texto."""
    try:
        from narrative_assistant.temporal.anachronisms import AnachronismDetector

        detector = AnachronismDetector()
        report = detector.detect(full_text)
        if report and report.anachronisms:
            logger.info(
                f"Anachronism detection: {len(report.anachronisms)} anachronisms found"
            )
        else:
            logger.info(
                "Anachronism detection: no anachronisms found (period may not be detected)"
            )
        return report

    except ImportError as e:
        logger.warning(f"Anachronism detection module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in anachronism detection: {e}", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.6: Español clásico
# ---------------------------------------------------------------------------


def analyze_classical_spanish_subphase(full_text: str) -> Any:
    """Detecta y normaliza español clásico."""
    try:
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        period = normalizer.detect_period(full_text)
        if period != "modern":
            result = normalizer.normalize(full_text)
            logger.info(
                f"Classical Spanish: period={period}, "
                f"{len(result.replacements)} normalizations"
            )
            return result
        else:
            logger.debug("Classical Spanish: modern text, skipping normalization")

    except ImportError as e:
        logger.warning(f"Classical Spanish module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in classical Spanish detection: {e}", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Sub-fase 7.7: Speech consistency tracking
# ---------------------------------------------------------------------------


def analyze_speech_tracking_subphase(
    entities: list,
    chapters_data: list[dict],
    ctx: dict,
) -> tuple[int, list]:
    """Analiza consistencia del habla de personajes principales.

    Returns:
        Tuple of (speech_change_count, all_speech_alerts).
    """
    try:
        from narrative_assistant.analysis.speech_tracking import (
            ContextualAnalyzer,
            SpeechTracker,
        )
        from narrative_assistant.entities.models import EntityType

        tracker_speech = SpeechTracker(
            window_size=3,
            overlap=1,
            min_words_per_window=200,
            min_confidence=0.6,
        )

        context_analyzer = ContextualAnalyzer()

        # Filtrar solo personajes principales (>50 palabras de diálogo total)
        main_characters = []
        for entity in entities:
            if entity.entity_type not in (
                EntityType.CHARACTER,
                EntityType.ANIMAL,
                EntityType.CREATURE,
            ):
                continue

            total_mentions = entity.mention_count or 0
            estimated_dialogue_words = total_mentions * 10
            if estimated_dialogue_words >= 50:
                main_characters.append(entity)

        logger.info(
            f"Speech tracking: analyzing {len(main_characters)} main characters "
            f"(of {len(entities)} total)"
        )

        all_speech_alerts: list = []
        for entity in main_characters:
            try:
                spacy_nlp = ctx.get("spacy_nlp")
                _fp_project = ctx.get("project")
                document_fingerprint = (
                    getattr(_fp_project, "document_fingerprint", "") if _fp_project else ""
                )

                speech_alerts = tracker_speech.detect_changes(
                    character_id=entity.id,
                    character_name=entity.canonical_name,
                    chapters=chapters_data,
                    spacy_nlp=spacy_nlp,
                    narrative_context_analyzer=context_analyzer,
                    document_fingerprint=document_fingerprint,
                )

                all_speech_alerts.extend(speech_alerts)

                if speech_alerts:
                    logger.info(
                        f"Speech tracking: {entity.canonical_name} → "
                        f"{len(speech_alerts)} change(s) detected"
                    )

            except Exception as e:
                logger.warning(f"Speech tracking failed for {entity.canonical_name}: {e}")
                continue

        speech_change_count = len(all_speech_alerts)
        logger.info(
            f"Speech tracking: {speech_change_count} total changes detected "
            f"across {len(main_characters)} characters"
        )

        return speech_change_count, all_speech_alerts

    except ImportError as e:
        logger.debug(f"Speech tracking module not available: {e}")
    except Exception as e:
        logger.warning(f"Speech consistency tracking failed: {e}", exc_info=True)

    return 0, []
