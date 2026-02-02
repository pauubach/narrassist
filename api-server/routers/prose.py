"""
Router: prose
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import Query
from typing import Optional, Any
from deps import _get_pacing_label, _get_sticky_recommendation

router = APIRouter()

@router.get("/api/projects/{project_id}/chapter-progress", response_model=ApiResponse)
async def get_chapter_progress(
    project_id: int,
    mode: str = "basic",  # basic, standard, deep
    llm_model: str = "llama3.2",
):
    """
    Obtiene el resumen de avance narrativo por capítulo.

    Incluye:
    - Personajes presentes y sus interacciones por capítulo
    - Eventos significativos detectados (patrones + LLM)
    - Arcos de personajes (trayectoria narrativa)
    - Chekhov's Guns (objetos introducidos sin payoff)
    - Tramas abandonadas (con análisis LLM)

    Modos:
    - basic: Solo patrones, sin LLM (rápido)
    - standard: Análisis LLM con llama3.2
    - deep: Análisis multi-modelo (más preciso, más lento)

    Args:
        project_id: ID del proyecto
        mode: Modo de análisis (basic/standard/deep)
        llm_model: Modelo LLM a usar (llama3.2, qwen2.5, mistral)

    Returns:
        ChapterProgressReport con resúmenes de todos los capítulos
    """
    try:
        from narrative_assistant.analysis.chapter_summary import (
            analyze_chapter_progress,
        )

        # Validar modo
        valid_modes = ["basic", "standard", "deep"]
        if mode not in valid_modes:
            return ApiResponse(
                success=False,
                error=f"Modo inválido. Opciones: {', '.join(valid_modes)}"
            )

        # Analizar
        report = analyze_chapter_progress(
            project_id=project_id,
            mode=mode,
            llm_model=llm_model,
        )

        return ApiResponse(success=True, data=report.to_dict())

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de resumen de capítulos no disponible"
        )
    except Exception as e:
        logger.error(f"Error in chapter progress analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/narrative-templates", response_model=ApiResponse)
def get_narrative_templates(
    project_id: int,
    mode: str = "basic",
    llm_model: str = "llama3.2",
):
    """
    Analiza qué plantillas narrativas encajan con el manuscrito.

    Evalúa Tres Actos, Viaje del Héroe, Save the Cat, Kishotenketsu
    y Cinco Actos (Freytag). Herramienta diagnóstica para el corrector.
    """
    try:
        from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress
        from narrative_assistant.analysis.narrative_templates import NarrativeTemplateAnalyzer

        proj_result = deps.project_manager.get(project_id)
        if proj_result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener datos de capítulos (reusar chapter_progress)
        report = analyze_chapter_progress(
            project_id=project_id,
            mode=mode,
            llm_model=llm_model,
        )

        # Convertir capítulos a formato para el analizador
        chapters_data = []
        for ch in report.chapters:
            chapters_data.append(ch.to_dict())

        # Analizar plantillas
        analyzer = NarrativeTemplateAnalyzer()
        template_report = analyzer.analyze(
            chapters_data=chapters_data,
            total_chapters=report.total_chapters,
        )

        return ApiResponse(success=True, data=template_report.to_dict())

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(success=False, error="Módulo de plantillas narrativas no disponible")
    except Exception as e:
        logger.error(f"Error analyzing narrative templates: {e}", exc_info=True)
        user_msg = e.user_message if hasattr(e, 'user_message') and e.user_message else "Error interno del análisis"
        return ApiResponse(success=False, error=user_msg)


@router.get("/api/projects/{project_id}/narrative-health", response_model=ApiResponse)
def get_narrative_health(
    project_id: int,
    mode: str = "basic",
    llm_model: str = "llama3.2",
):
    """
    Chequeo de salud narrativa del manuscrito.

    Evalúa 12 dimensiones: protagonista, conflicto, objetivo, apuestas,
    clímax, resolución, arco emocional, ritmo, coherencia, estructura,
    equilibrio de personajes y tramas cerradas.
    """
    try:
        from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress
        from narrative_assistant.analysis.narrative_health import NarrativeHealthChecker

        proj_result = deps.project_manager.get(project_id)
        if proj_result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener datos de capítulos
        report = analyze_chapter_progress(
            project_id=project_id,
            mode=mode,
            llm_model=llm_model,
        )

        # Convertir a formato para el checker
        chapters_data = [ch.to_dict() for ch in report.chapters]

        # Obtener entidades del proyecto
        entities_data = []
        try:
            entities = deps.entity_repository.get_by_project(project_id)
            for ent in entities:
                ent_dict = {
                    "entity_type": ent.entity_type if hasattr(ent, 'entity_type') else "character",
                    "name": ent.name if hasattr(ent, 'name') else "",
                    "mention_count": ent.mention_count if hasattr(ent, 'mention_count') else 0,
                    "chapters_present": len(ent.chapter_appearances) if hasattr(ent, 'chapter_appearances') else 0,
                }
                entities_data.append(ent_dict)
        except Exception:
            pass  # Sin entidades, el health check funciona con datos parciales

        # Arcos y elementos Chekhov del chapter progress
        character_arcs = [a.to_dict() for a in report.character_arcs]
        chekhov_elements = [c.to_dict() for c in report.chekhov_elements]
        abandoned_threads = [t.to_dict() for t in report.abandoned_threads]

        # Ejecutar health check
        checker = NarrativeHealthChecker()
        health_report = checker.check(
            chapters_data=chapters_data,
            total_chapters=report.total_chapters,
            entities_data=entities_data,
            character_arcs=character_arcs,
            chekhov_elements=chekhov_elements,
            abandoned_threads=abandoned_threads,
        )

        return ApiResponse(success=True, data=health_report.to_dict())

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(success=False, error="Módulo de salud narrativa no disponible")
    except Exception as e:
        logger.error(f"Error in narrative health check: {e}", exc_info=True)
        user_msg = e.user_message if hasattr(e, 'user_message') and e.user_message else "Error interno del análisis"
        return ApiResponse(success=False, error=user_msg)


@router.get("/api/projects/{project_id}/sticky-sentences", response_model=ApiResponse)
async def get_sticky_sentences(
    project_id: int,
    threshold: float = Query(0.40, ge=0.0, le=1.0, description="Umbral de glue words (0.0-1.0)"),
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo"),
):
    """
    Analiza oraciones pesadas (sticky sentences) en el proyecto.

    Las oraciones pesadas son aquellas con alto porcentaje de palabras funcionales
    (artículos, preposiciones, conjunciones) que dificultan la lectura.
    """
    try:
        from narrative_assistant.nlp.style.sticky_sentences import get_sticky_sentence_detector

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        # Obtener texto de todos los capítulos
        chapters_data = []
        chapters = deps.chapter_repository.get_by_project(project_id)

        detector = get_sticky_sentence_detector()
        global_sticky = []
        global_total_sentences = 0
        global_total_glue = 0
        by_severity = {"critical": 0, "high": 0, "medium": 0}

        for chapter in chapters:
            # Filtrar por capítulo si se especifica
            if chapter_number is not None and chapter.chapter_number != chapter_number:
                continue

            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = detector.analyze(chapter_text, threshold=threshold)
            if result.is_failure:
                continue

            report = result.value
            chapter_sticky = []
            chapter_dist = {"clean": 0, "borderline": 0, "sticky": 0}
            chapter_severity = {"critical": 0, "high": 0, "medium": 0}

            for sent in report.sticky_sentences:
                severity = "medium"
                if sent.glue_percentage >= 0.55:
                    severity = "critical"
                    by_severity["critical"] += 1
                    chapter_severity["critical"] += 1
                elif sent.glue_percentage >= 0.50:
                    severity = "high"
                    by_severity["high"] += 1
                    chapter_severity["high"] += 1
                else:
                    by_severity["medium"] += 1
                    chapter_severity["medium"] += 1

                chapter_sticky.append({
                    "text": sent.text,
                    "glue_percentage": round(sent.glue_percentage * 100, 1),
                    "glue_percentage_display": f"{round(sent.glue_percentage * 100)}%",
                    "glue_words": sent.glue_words,
                    "total_words": sent.total_words,
                    "glue_word_list": sent.glue_word_list[:10],  # Limit to 10
                    "severity": severity,
                    "recommendation": _get_sticky_recommendation(sent.glue_percentage),
                })

            # Distribución de oraciones
            for _ in range(report.total_sentences - len(report.sticky_sentences)):
                chapter_dist["clean"] += 1
            for sent in report.sticky_sentences:
                if sent.glue_percentage >= threshold and sent.glue_percentage < threshold + 0.05:
                    chapter_dist["borderline"] += 1
                else:
                    chapter_dist["sticky"] += 1

            global_sticky.extend(chapter_sticky)
            global_total_sentences += report.total_sentences
            global_total_glue += sum(s["glue_percentage"] for s in chapter_sticky)

            chapters_data.append({
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "sticky_sentences": chapter_sticky,
                "sticky_count": len(chapter_sticky),
                "total_sentences": report.total_sentences,
                "avg_glue_percentage": round(report.avg_glue_percentage * 100, 1) if report.avg_glue_percentage else 0,
                "distribution": chapter_dist,
                "by_severity": chapter_severity,
            })

        # Calcular estadísticas globales
        avg_glue = (global_total_glue / len(global_sticky)) if global_sticky else 0

        recommendations = []
        if by_severity["critical"] > 0:
            recommendations.append(f"Hay {by_severity['critical']} oraciones críticas (>55% glue words). Prioriza su revisión.")
        if len(global_sticky) > global_total_sentences * 0.2:
            recommendations.append("Más del 20% de las oraciones son pesadas. Considera simplificar el estilo.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_sticky_sentences": len(global_sticky),
                    "total_sentences": global_total_sentences,
                    "avg_glue_percentage": round(avg_glue, 1),
                    "by_severity": by_severity,
                },
                "chapters": chapters_data,
                "recommendations": recommendations,
                "threshold_used": threshold,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sticky sentences: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/sentence-energy", response_model=ApiResponse)
def get_sentence_energy(
    project_id: int,
    low_threshold: float = Query(40.0, ge=0.0, le=100.0, description="Umbral de baja energía (0-100)"),
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo"),
):
    """
    Analiza la energía de las oraciones del proyecto.

    Evalúa voz activa/pasiva, fuerza de verbos, estructura y nominalizaciones
    para determinar el dinamismo de cada oración.
    """
    try:
        from narrative_assistant.nlp.style.sentence_energy import get_sentence_energy_detector

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        chapters = deps.chapter_repository.get_by_project(project_id)
        detector = get_sentence_energy_detector()

        chapters_data = []
        global_all_energy = []
        global_low_count = 0
        global_passive_count = 0
        global_weak_count = 0
        global_nom_count = 0
        global_total_sentences = 0
        global_by_level = {}

        for chapter in chapters:
            if chapter_number is not None and chapter.chapter_number != chapter_number:
                continue

            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = detector.analyze(chapter_text, chapter=chapter.chapter_number, low_threshold=low_threshold)
            if result.is_failure:
                continue

            report = result.value
            global_total_sentences += report.total_sentences

            # Recopilar oraciones de baja energía para este capítulo
            chapter_low = []
            for sent in report.low_energy_sentences:
                chapter_low.append(sent.to_dict())

            # Acumular estadísticas globales
            for sent in report.sentences:
                global_all_energy.append(sent.energy_score)

            global_low_count += len(report.low_energy_sentences)
            global_passive_count += report.passive_count
            global_weak_count += report.weak_verb_count
            global_nom_count += report.nominalization_count

            for level_key, count in report.by_level.items():
                global_by_level[level_key] = global_by_level.get(level_key, 0) + count

            chapters_data.append({
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "total_sentences": report.total_sentences,
                "avg_energy": round(report.avg_energy, 1),
                "avg_voice_score": round(report.avg_voice_score, 1),
                "avg_verb_strength": round(report.avg_verb_strength, 1),
                "avg_structure_score": round(report.avg_structure_score, 1),
                "by_level": report.by_level,
                "issues": {
                    "passive_count": report.passive_count,
                    "weak_verb_count": report.weak_verb_count,
                    "nominalization_count": report.nominalization_count,
                },
                "low_energy_sentences": chapter_low,
                "low_energy_count": len(chapter_low),
                "recommendations": report.recommendations,
            })

        # Estadísticas globales
        avg_energy = sum(global_all_energy) / len(global_all_energy) if global_all_energy else 0
        analyzed = len(global_all_energy)

        global_recommendations = []
        if avg_energy < 40 and analyzed > 0:
            global_recommendations.append(
                f"La energía media es baja ({avg_energy:.0f}/100). "
                "El texto podría beneficiarse de más verbos de acción y voz activa."
            )
        if analyzed > 0 and global_passive_count / analyzed > 0.20:
            global_recommendations.append(
                f"El {global_passive_count / analyzed * 100:.0f}% de las oraciones usan voz pasiva."
            )
        if analyzed > 0 and global_weak_count / analyzed > 0.40:
            global_recommendations.append(
                f"Alto uso de verbos débiles ({global_weak_count} oraciones). "
                "Sustituya ser/estar/tener/hacer por verbos más específicos."
            )

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_sentences": global_total_sentences,
                    "analyzed_sentences": analyzed,
                    "avg_energy": round(avg_energy, 1),
                    "low_energy_count": global_low_count,
                    "passive_count": global_passive_count,
                    "weak_verb_count": global_weak_count,
                    "nominalization_count": global_nom_count,
                    "by_level": global_by_level,
                },
                "chapters": chapters_data,
                "recommendations": global_recommendations,
                "threshold_used": low_threshold,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentence energy: {e}", exc_info=True)
        user_msg = e.user_message if hasattr(e, 'user_message') and e.user_message else "Error interno del análisis"
        return ApiResponse(success=False, error=user_msg)


@router.get("/api/projects/{project_id}/echo-report", response_model=ApiResponse)
async def get_echo_report(
    project_id: int,
    min_distance: int = Query(50, ge=10, le=500, description="Distancia mínima entre repeticiones"),
    include_semantic: bool = Query(False, description="Incluir repeticiones semánticas"),
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo")
):
    """
    Analiza repeticiones (ecos) de palabras en el proyecto.

    Detecta palabras repetidas en proximidad que afectan la fluidez del texto.
    """
    try:
        from narrative_assistant.nlp.style.repetition_detector import get_repetition_detector

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        detector = get_repetition_detector()
        chapters = deps.chapter_repository.get_by_project(project_id)

        chapters_data = []
        global_repetitions = []
        global_word_counts = {}
        global_total_words = 0
        by_severity = {"high": 0, "medium": 0, "low": 0}

        for chapter in chapters:
            if chapter_number is not None and chapter.chapter_number != chapter_number:
                continue
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            # Análisis léxico
            result = detector.detect_lexical(chapter_text, min_distance=min_distance)
            if result.is_failure:
                continue

            report = result.value
            chapter_reps = []
            chapter_severity = {"high": 0, "medium": 0, "low": 0}

            for rep in report.repetitions:
                severity = "medium"
                if rep.min_distance < min_distance // 2:
                    severity = "high"
                    by_severity["high"] += 1
                    chapter_severity["high"] += 1
                else:
                    by_severity["medium"] += 1
                    chapter_severity["medium"] += 1

                # Agregar al conteo global
                word = rep.word.lower()
                global_word_counts[word] = global_word_counts.get(word, 0) + rep.count

                chapter_reps.append({
                    "word": rep.word,
                    "count": rep.count,
                    "min_distance": rep.min_distance,
                    "type": "lexical",
                    "severity": severity,
                    "occurrences": [
                        {"text": occ.context, "position": occ.position}
                        for occ in rep.occurrences[:5]
                    ],
                })

            # Análisis semántico si se solicita
            if include_semantic:
                sem_result = detector.detect_semantic(chapter_text, min_distance=min_distance * 2)
                if sem_result.is_success:
                    for rep in sem_result.value.repetitions:
                        chapter_reps.append({
                            "word": rep.word,
                            "count": rep.count,
                            "min_distance": rep.min_distance,
                            "type": "semantic",
                            "severity": "low",
                            "occurrences": [
                                {"text": occ.context, "position": occ.position}
                                for occ in rep.occurrences[:5]
                            ],
                        })
                        by_severity["low"] += 1
                        chapter_severity["low"] += 1

            global_repetitions.extend(chapter_reps)
            global_total_words += report.processed_words

            chapters_data.append({
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "repetitions": chapter_reps,
                "repetition_count": len(chapter_reps),
                "total_words": report.processed_words,
                "by_severity": chapter_severity,
            })

        # Top palabras repetidas
        top_words = sorted(global_word_counts.items(), key=lambda x: x[1], reverse=True)[:20]

        recommendations = []
        if by_severity["high"] > 5:
            recommendations.append(f"Hay {by_severity['high']} repeticiones muy cercanas. Usa sinónimos o reestructura las oraciones.")
        if len(global_repetitions) > 50:
            recommendations.append("Texto con muchas repeticiones. Considera revisar el vocabulario.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_repetitions": len(global_repetitions),
                    "total_words": global_total_words,
                    "by_severity": by_severity,
                    "top_repeated_words": [{"word": w, "count": c} for w, c in top_words],
                },
                "chapters": chapters_data,
                "recommendations": recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing echo report: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/sentence-variation", response_model=ApiResponse)
async def get_sentence_variation(
    project_id: int,
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo")
):
    """
    Analiza la variación en la longitud de las oraciones.

    Proporciona métricas de legibilidad y distribución de oraciones.
    """
    try:
        from narrative_assistant.nlp.style.readability import get_readability_analyzer

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        analyzer = get_readability_analyzer()
        chapters = deps.chapter_repository.get_by_project(project_id)

        chapters_data = []
        global_stats = {
            "total_sentences": 0,
            "total_words": 0,
            "flesch_scores": [],
        }
        global_distribution = {"short": 0, "medium": 0, "long": 0, "very_long": 0}

        for chapter in chapters:
            if chapter_number is not None and chapter.chapter_number != chapter_number:
                continue
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = analyzer.analyze(chapter_text)
            if result.is_failure:
                continue

            report = result.value

            chapters_data.append({
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "flesch_szigriszt": round(report.flesch_szigriszt, 1),
                "level": report.level.value,
                "level_description": report.level_description,
                "statistics": {
                    "total_sentences": report.total_sentences,
                    "total_words": report.total_words,
                    "avg_words_per_sentence": round(report.avg_words_per_sentence, 1),
                    "avg_syllables_per_word": round(report.avg_syllables_per_word, 2),
                },
                "distribution": {
                    "short": report.short_sentences,
                    "medium": report.medium_sentences,
                    "long": report.long_sentences,
                    "very_long": report.very_long_sentences,
                },
                "target_audience": report.target_audience,
            })

            global_stats["total_sentences"] += report.total_sentences
            global_stats["total_words"] += report.total_words
            global_stats["flesch_scores"].append(report.flesch_szigriszt)
            global_distribution["short"] += report.short_sentences
            global_distribution["medium"] += report.medium_sentences
            global_distribution["long"] += report.long_sentences
            global_distribution["very_long"] += report.very_long_sentences

        # Calcular promedios globales
        avg_flesch = sum(global_stats["flesch_scores"]) / len(global_stats["flesch_scores"]) if global_stats["flesch_scores"] else 0
        avg_wps = global_stats["total_words"] / global_stats["total_sentences"] if global_stats["total_sentences"] else 0

        recommendations = []
        if global_distribution["very_long"] > global_stats["total_sentences"] * 0.15:
            recommendations.append("Muchas oraciones muy largas (>35 palabras). Considera dividirlas.")
        if global_distribution["short"] > global_stats["total_sentences"] * 0.6:
            recommendations.append("Texto con predominio de oraciones cortas. Varía la longitud para mejor ritmo.")
        if avg_flesch < 40:
            recommendations.append("El texto es difícil de leer. Simplifica el vocabulario y la estructura.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_sentences": global_stats["total_sentences"],
                    "total_words": global_stats["total_words"],
                    "avg_words_per_sentence": round(avg_wps, 1),
                    "avg_flesch_szigriszt": round(avg_flesch, 1),
                },
                "distribution": global_distribution,
                "chapters": chapters_data,
                "recommendations": recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentence variation: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/pacing-analysis", response_model=ApiResponse)
async def get_pacing_analysis(
    project_id: int,
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo")
):
    """
    Analiza el ritmo narrativo del proyecto.

    Detecta variaciones en el pacing a través de capítulos/escenas.
    """
    try:
        from narrative_assistant.analysis.pacing import get_pacing_analyzer

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        analyzer = get_pacing_analyzer()
        chapters = deps.chapter_repository.get_by_project(project_id)

        chapters_data = []

        for chapter in chapters:
            if chapter_number is not None and chapter.chapter_number != chapter_number:
                continue
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = analyzer.analyze(chapter_text)
            if result.is_failure:
                continue

            report = result.value

            chapters_data.append({
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "pacing_score": round(report.overall_pacing, 2),
                "pacing_label": _get_pacing_label(report.overall_pacing),
                "metrics": {
                    "dialogue_ratio": round(report.dialogue_ratio, 3),
                    "action_ratio": round(report.action_ratio, 3),
                    "description_ratio": round(report.description_ratio, 3),
                    "avg_sentence_length": round(report.avg_sentence_length, 1),
                },
                "segments": [
                    {
                        "type": seg.segment_type.value,
                        "start": seg.start_position,
                        "end": seg.end_position,
                        "pacing": round(seg.pacing_score, 2),
                    }
                    for seg in report.segments[:20]  # Limit segments
                ],
            })

        # Calcular variación de pacing
        pacing_scores = [ch["pacing_score"] for ch in chapters_data]
        pacing_variation = max(pacing_scores) - min(pacing_scores) if pacing_scores else 0

        recommendations = []
        if pacing_variation < 0.2:
            recommendations.append("El ritmo es muy uniforme. Considera variar entre escenas de acción y reflexión.")
        if all(ch["pacing_score"] < 0.4 for ch in chapters_data):
            recommendations.append("El ritmo general es lento. Añade más diálogo o escenas de acción.")
        if all(ch["pacing_score"] > 0.7 for ch in chapters_data):
            recommendations.append("El ritmo es muy acelerado. Incluye momentos de pausa para el lector.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "avg_pacing": round(sum(pacing_scores) / len(pacing_scores), 2) if pacing_scores else 0,
                    "pacing_variation": round(pacing_variation, 2),
                    "chapter_count": len(chapters_data),
                },
                "chapters": chapters_data,
                "recommendations": recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing pacing: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/tension-curve", response_model=ApiResponse)
async def get_tension_curve(
    project_id: int,
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo")
):
    """
    Calcula la curva de tensión narrativa del proyecto.

    Estima la tensión en cada capítulo usando señales textuales:
    - Densidad de verbos de acción
    - Longitud de oraciones (cortas = más tensión)
    - Ratio de diálogo (conflicto)
    - Puntuación expresiva (!, ?)
    - Ritmo de párrafos

    Returns:
        Curva de tensión con puntos por capítulo, tipo de arco narrativo
        y datos para visualización en gráfico.
    """
    try:
        from narrative_assistant.analysis.pacing import compute_tension_curve
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "curve": {"points": [], "avg_tension": 0, "max_tension": 0, "min_tension": 0, "tension_arc_type": "flat"},
                    "message": "No hay capítulos para analizar"
                }
            )

        chapters_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": ch.content or "",
            }
            for ch in chapters
            if ch.content and ch.content.strip()
            and (chapter_number is None or ch.chapter_number == chapter_number)
        ]

        full_text = "\n\n".join(ch.get("content", "") for ch in chapters_data)

        curve = compute_tension_curve(chapters_data, full_text)

        # Clasificar arco en español para frontend
        arc_labels = {
            "rising": "Ascendente (tensión creciente)",
            "falling": "Descendente (tensión decreciente)",
            "mountain": "Montaña (arco clásico: inicio-clímax-desenlace)",
            "valley": "Valle (inversión: alta-baja-alta)",
            "wave": "Ondulante (múltiples picos de tensión)",
            "flat": "Plano (tensión uniforme)",
        }

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "curve": curve.to_dict(),
                "arc_label": arc_labels.get(curve.tension_arc_type, curve.tension_arc_type),
                "stats": {
                    "chapters_analyzed": len(chapters_data),
                    "avg_tension": round(curve.avg_tension, 3),
                    "max_tension": round(curve.max_tension, 3),
                    "min_tension": round(curve.min_tension, 3),
                    "tension_range": round(curve.max_tension - curve.min_tension, 3),
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing tension curve: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/pacing/genre-benchmarks", response_model=ApiResponse)
async def get_genre_benchmarks(
    genre_code: Optional[str] = Query(None, description="Código de género (FIC, MEM, TEC, etc.). Si no se indica, devuelve todos.")
):
    """
    Devuelve benchmarks de referencia de pacing por género literario.

    Incluye rangos esperados de longitud de capítulo, ratio de diálogo,
    longitud de oraciones, tensión narrativa y tipos de arco.
    """
    try:
        from narrative_assistant.analysis.pacing import GENRE_BENCHMARKS, get_genre_benchmarks

        if genre_code:
            benchmarks = get_genre_benchmarks(genre_code.upper())
            if not benchmarks:
                available = list(GENRE_BENCHMARKS.keys())
                return ApiResponse(
                    success=False,
                    error=f"Género '{genre_code}' no encontrado. Disponibles: {', '.join(available)}"
                )
            return ApiResponse(
                success=True,
                data={"benchmarks": benchmarks.to_dict()}
            )

        return ApiResponse(
            success=True,
            data={
                "benchmarks": {
                    code: b.to_dict() for code, b in GENRE_BENCHMARKS.items()
                },
                "genre_count": len(GENRE_BENCHMARKS),
            }
        )
    except Exception as e:
        logger.error(f"Error getting genre benchmarks: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/pacing-analysis/genre-comparison", response_model=ApiResponse)
async def get_pacing_genre_comparison(
    project_id: int,
    genre_code: str = Query(..., description="Código de género para comparar (FIC, MEM, TEC, etc.)")
):
    """
    Compara las métricas de pacing del proyecto contra benchmarks del género.

    Devuelve desviaciones respecto a lo esperado para el tipo de documento.
    """
    try:
        import re

        from narrative_assistant.analysis.pacing import (
            compare_with_benchmarks, compute_tension_curve, get_pacing_analyzer,
        )

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        chapters = deps.chapter_repository.get_by_project(project_id)
        if not chapters:
            return ApiResponse(success=True, data={"comparison": None, "message": "No hay capítulos"})

        chapters_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": ch.content or "",
            }
            for ch in chapters
            if ch.content and ch.content.strip()
        ]

        # Calcular métricas globales
        total_words = 0
        total_sentences = 0
        total_dialogue_words = 0
        total_doc_words = 0
        chapter_word_counts = []

        analyzer = get_pacing_analyzer()
        for ch in chapters_data:
            content = ch["content"]
            words = content.split()
            word_count = len(words)
            total_words += word_count
            chapter_word_counts.append(word_count)

            sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
            total_sentences += len(sentences)

            for line in content.split("\n"):
                line = line.strip()
                if line.startswith(("—", "–", "-", "«", '"')):
                    total_dialogue_words += len(line.split())
                total_doc_words += len(line.split())

        avg_chapter_words = total_words / len(chapters_data) if chapters_data else 0
        avg_sentence_length = total_words / total_sentences if total_sentences > 0 else 0
        dialogue_ratio = total_dialogue_words / total_doc_words if total_doc_words > 0 else 0

        # Calcular tensión
        full_text = "\n\n".join(ch["content"] for ch in chapters_data)
        curve = compute_tension_curve(chapters_data, full_text)

        metrics = {
            "avg_chapter_words": avg_chapter_words,
            "dialogue_ratio": dialogue_ratio,
            "avg_sentence_length": avg_sentence_length,
            "avg_tension": curve.avg_tension,
            "tension_arc_type": curve.tension_arc_type,
        }

        comparison = compare_with_benchmarks(metrics, genre_code.upper())
        if comparison is None:
            from narrative_assistant.analysis.pacing import GENRE_BENCHMARKS
            available = list(GENRE_BENCHMARKS.keys())
            return ApiResponse(
                success=False,
                error=f"Género '{genre_code}' no encontrado. Disponibles: {', '.join(available)}"
            )

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "metrics": {k: round(v, 3) if isinstance(v, float) else v for k, v in metrics.items()},
                "comparison": comparison,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing pacing with genre: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/register/genre-benchmarks", response_model=ApiResponse)
async def get_register_genre_benchmarks_endpoint(
    genre_code: Optional[str] = Query(None, description="Código de género (FIC, MEM, TEC, etc.). Si no se indica, devuelve todos.")
):
    """
    Devuelve benchmarks de referencia de registro por género literario.

    Incluye registro dominante esperado, rangos de consistencia,
    distribución esperada por tipo de registro y tolerancia a cambios bruscos.
    """
    try:
        from narrative_assistant.voice.register import (
            REGISTER_GENRE_BENCHMARKS, get_register_genre_benchmarks,
        )

        if genre_code:
            benchmarks = get_register_genre_benchmarks(genre_code.upper())
            if not benchmarks:
                available = list(REGISTER_GENRE_BENCHMARKS.keys())
                return ApiResponse(
                    success=False,
                    error=f"Género '{genre_code}' no encontrado. Disponibles: {', '.join(available)}"
                )
            return ApiResponse(
                success=True,
                data={"benchmarks": benchmarks.to_dict()}
            )

        return ApiResponse(
            success=True,
            data={
                "benchmarks": {
                    code: b.to_dict() for code, b in REGISTER_GENRE_BENCHMARKS.items()
                },
                "genre_count": len(REGISTER_GENRE_BENCHMARKS),
            }
        )
    except Exception as e:
        logger.error(f"Error getting register genre benchmarks: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/story-bible", response_model=ApiResponse)
async def get_story_bible(
    project_id: int,
    entity_type: Optional[str] = Query(None, description="Filtrar por tipo: character, location, organization, object"),
    include_voice: bool = Query(True, description="Incluir perfiles de voz"),
    include_emotions: bool = Query(True, description="Incluir arcos emocionales"),
    include_knowledge: bool = Query(True, description="Incluir conocimiento inter-personaje"),
    include_vital: bool = Query(True, description="Incluir estado vital"),
):
    """
    Story Bible: Vista wiki consolidada de todas las entidades del proyecto.

    Agrega datos de múltiples fuentes para cada entidad:
    - Datos básicos, aliases, importancia
    - Atributos extraídos (físicos, psicológicos, etc.)
    - Relaciones con otras entidades
    - Timeline de apariciones por capítulo
    - Estado vital (vivo/muerto)
    - Perfil de voz (personajes)
    """
    try:
        from narrative_assistant.analysis.story_bible import StoryBibleBuilder

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        builder = StoryBibleBuilder(project_id=project_id)
        bible = builder.build(
            include_voice=include_voice,
            include_emotions=include_emotions,
            include_knowledge=include_knowledge,
            include_vital=include_vital,
        )

        bible.project_name = result.value.name

        data = bible.to_dict()

        # Filtrar por tipo si se especifica
        if entity_type:
            type_map = {
                "character": ("CHARACTER", "PERSON", "PER"),
                "location": ("LOCATION", "LOC", "GPE", "PLACE"),
                "organization": ("ORGANIZATION", "ORG"),
                "object": ("OBJECT", "MISC"),
            }
            allowed = type_map.get(entity_type.lower(), ())
            if allowed:
                data["entries"] = [
                    e for e in data["entries"]
                    if e.get("entity_type", "").upper() in allowed
                ]

        return ApiResponse(success=True, data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building story bible: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/story-bible/{entity_id}", response_model=ApiResponse)
async def get_story_bible_entry(
    project_id: int,
    entity_id: int,
    include_voice: bool = Query(True),
    include_emotions: bool = Query(True),
    include_knowledge: bool = Query(True),
    include_vital: bool = Query(True),
):
    """
    Story Bible: Ficha detallada de una entidad específica.

    Retorna toda la información agregada sobre la entidad.
    """
    try:
        from narrative_assistant.analysis.story_bible import StoryBibleBuilder

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        builder = StoryBibleBuilder(project_id=project_id)
        bible = builder.build(
            entity_id=entity_id,
            include_voice=include_voice,
            include_emotions=include_emotions,
            include_knowledge=include_knowledge,
            include_vital=include_vital,
        )

        if not bible.entries:
            raise HTTPException(status_code=404, detail=f"Entidad {entity_id} no encontrada")

        return ApiResponse(success=True, data=bible.entries[0].to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building story bible entry: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/sensory-report", response_model=ApiResponse)
def get_sensory_report(
    project_id: int,
    chapter_number: Optional[int] = Query(None, description="Filtrar por capítulo"),
):
    """
    Analiza la presencia de detalles sensoriales (5 sentidos) en el texto.

    Genera un reporte de distribución y densidad sensorial:
    - Vista, Oído, Tacto, Olfato, Gusto
    - Densidad por capítulo
    - Capítulos pobres/ricos en detalles sensoriales
    - Balance entre sentidos
    """
    try:
        from narrative_assistant.nlp.style.sensory_report import (
            get_sensory_analyzer,
            generate_sensory_suggestions,
            SENSE_NAMES,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "total_details": 0,
                    "message": "No hay capítulos para analizar",
                }
            )

        # Filtrar por capítulo si se especifica
        if chapter_number is not None:
            chapters = [ch for ch in chapters if ch.chapter_number == chapter_number]
            if not chapters:
                raise HTTPException(
                    status_code=404,
                    detail=f"Capítulo {chapter_number} no encontrado"
                )

        # Preparar datos de capítulos
        full_text = "\n\n".join(ch.content for ch in chapters if ch.content)
        chapters_data = [
            {
                "number": ch.chapter_number,
                "title": getattr(ch, "title", f"Capítulo {ch.chapter_number}"),
                "start_char": ch.start_char,
                "end_char": ch.end_char,
                "content": ch.content or "",
            }
            for ch in chapters
        ]

        analyzer = get_sensory_analyzer()
        analysis_result = analyzer.analyze(full_text, chapters=chapters_data)

        if analysis_result.is_failure:
            return ApiResponse(success=False, error=str(analysis_result.error))

        report = analysis_result.value
        data = report.to_dict()

        # Añadir nombres en español
        data["sense_names"] = {s.value: name for s, name in SENSE_NAMES.items()}

        # Añadir sugerencias de enriquecimiento
        data["suggestions"] = generate_sensory_suggestions(report)

        return ApiResponse(success=True, data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating sensory report: {e}", exc_info=True)
        user_msg = e.user_message if hasattr(e, 'user_message') and e.user_message else "Error interno del análisis"
        return ApiResponse(success=False, error=user_msg)


@router.get("/api/projects/{project_id}/age-readability", response_model=ApiResponse)
async def get_age_readability(
    project_id: int,
    target_age_group: Optional[str] = Query(None, description="Grupo de edad objetivo (board_book, picture_book, early_reader, chapter_book, middle_grade, young_adult)")
):
    """
    Analiza la legibilidad orientada a grupos de edad infantil/juvenil.

    Proporciona métricas específicas para literatura infantil como:
    - Proporción de palabras de alta frecuencia (sight words)
    - Complejidad del vocabulario
    - Estimación de edad lectora
    """
    try:
        from narrative_assistant.nlp.style.readability import get_readability_analyzer, AgeGroup

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        analyzer = get_readability_analyzer()
        chapters = deps.chapter_repository.get_by_project(project_id)

        # Parsear grupo de edad objetivo
        target_group = None
        if target_age_group:
            try:
                target_group = AgeGroup(target_age_group)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Grupo de edad inválido: {target_age_group}. Valores válidos: board_book, picture_book, early_reader, chapter_book, middle_grade, young_adult"
                )

        # Combinar todo el texto para análisis global
        full_text = "\n\n".join(ch.content or "" for ch in chapters if ch.content)

        if not full_text.strip():
            return ApiResponse(
                success=True,
                data={
                    "message": "No hay contenido para analizar",
                    "estimated_age_group": None,
                }
            )

        result = analyzer.analyze_for_age(full_text, target_age_group=target_group)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        report = result.value

        # Análisis por capítulo
        chapters_data = []
        for chapter in chapters:
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            ch_result = analyzer.analyze_for_age(chapter_text, target_age_group=target_group)
            if ch_result.is_success:
                ch_report = ch_result.value
                chapters_data.append({
                    "chapter_number": chapter.chapter_number,
                    "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                    "estimated_age_group": ch_report.estimated_age_group.value,
                    "estimated_age_range": ch_report.estimated_age_range,
                    "appropriateness_score": round(ch_report.appropriateness_score, 1),
                    "is_appropriate": ch_report.is_appropriate,
                    "metrics": {
                        "avg_words_per_sentence": round(ch_report.avg_words_per_sentence, 1),
                        "avg_syllables_per_word": round(ch_report.avg_syllables_per_word, 2),
                        "sight_word_ratio": round(ch_report.sight_word_ratio * 100, 1),
                    },
                })

        return ApiResponse(
            success=True,
            data={
                **report.to_dict(),
                "chapters": chapters_data,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing age readability: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


