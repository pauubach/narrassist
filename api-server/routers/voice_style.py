"""
Router: voice_style
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import Query
from typing import Optional, Any
from datetime import datetime

router = APIRouter()

@router.get("/api/projects/{project_id}/voice-profiles", response_model=ApiResponse)
async def get_voice_profiles(
    project_id: int,
    force_refresh: bool = Query(False, description="Forzar recálculo ignorando caché")
):
    """
    Obtiene perfiles de voz de los personajes del proyecto.

    Construye perfiles estilísticos basados en los diálogos de cada personaje,
    incluyendo métricas como longitud de intervención, riqueza léxica (TTR),
    formalidad, muletillas y patrones de puntuación.

    Los perfiles se cachean en BD tras el primer cálculo. Use force_refresh=true
    para recalcular.

    Returns:
        ApiResponse con perfiles de voz por personaje
    """
    try:
        import json as json_mod

        from narrative_assistant.voice.profiles import VoiceProfileBuilder
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Intentar devolver caché si no se fuerza recálculo
        if not force_refresh and deps.get_database:
            try:
                db = deps.get_database()
                with db.connect() as conn:
                    cached_rows = conn.execute(
                        """SELECT entity_id, characteristic_words
                           FROM voice_profiles
                           WHERE project_id = ?""",
                        (project_id,)
                    ).fetchall()

                if cached_rows:
                    cached_profiles = []
                    for row in cached_rows:
                        try:
                            profile_data = json_mod.loads(row[1]) if row[1] else None
                            if profile_data and isinstance(profile_data, dict) and "metrics" in profile_data:
                                cached_profiles.append(profile_data)
                        except (json_mod.JSONDecodeError, TypeError):
                            pass

                    if cached_profiles:
                        logger.debug(f"Returning {len(cached_profiles)} cached voice profiles for project {project_id}")
                        return ApiResponse(
                            success=True,
                            data={
                                "project_id": project_id,
                                "profiles": cached_profiles,
                                "stats": {
                                    "characters_analyzed": len(cached_profiles),
                                    "total_dialogues": 0,
                                    "chapters_analyzed": 0,
                                },
                                "cached": True,
                            }
                        )
            except Exception as cache_err:
                logger.debug(f"Cache miss for voice profiles: {cache_err}")

        # Obtener entidades (solo personajes)
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        if not characters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "profiles": [],
                    "message": "No hay personajes para analizar"
                }
            )

        # Obtener capítulos y extraer diálogos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        dialogues = []
        for chapter in chapters:
            dialogue_result = detect_dialogues(chapter.content)
            if dialogue_result.is_success:
                for d in dialogue_result.value.dialogues:
                    dialogues.append({
                        "text": d.text,
                        "speaker_id": d.speaker_id,
                        "speaker_hint": d.speaker_hint,
                        "chapter": chapter.chapter_number,
                        "position": d.start_char,
                    })

        if not dialogues:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "profiles": [],
                    "message": "No se encontraron diálogos para analizar"
                }
            )

        # Construir perfiles de voz
        entity_data = [
            {"id": e.id, "name": e.canonical_name, "aliases": e.aliases}
            for e in characters
        ]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entity_data)

        # Serializar perfiles
        profiles_data = []
        for profile in profiles:
            profile_dict = profile.to_dict()
            profiles_data.append(profile_dict)

        # Cachear perfiles en BD
        if deps.get_database and profiles_data:
            try:
                db = deps.get_database()
                with db.connect() as conn:
                    # Limpiar caché anterior del proyecto
                    conn.execute("DELETE FROM voice_profiles WHERE project_id = ?", (project_id,))

                    for profile_dict in profiles_data:
                        entity_id = profile_dict.get("entity_id")
                        metrics = profile_dict.get("metrics", {})
                        conn.execute(
                            """INSERT OR REPLACE INTO voice_profiles
                               (project_id, entity_id, avg_sentence_length,
                                vocabulary_richness, formality_score, dialogue_count,
                                characteristic_words, filler_words,
                                exclamation_ratio, question_ratio, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                            (
                                project_id,
                                entity_id,
                                metrics.get("avg_sentence_length", 0),
                                metrics.get("type_token_ratio", 0),
                                metrics.get("formality_score", 0),
                                metrics.get("total_interventions", 0),
                                json_mod.dumps(profile_dict),  # Full profile in characteristic_words column
                                json_mod.dumps(metrics.get("top_fillers", [])),
                                metrics.get("exclamation_ratio", 0),
                                metrics.get("question_ratio", 0),
                            )
                        )
                    conn.commit()
                    logger.debug(f"Cached {len(profiles_data)} voice profiles for project {project_id}")
            except Exception as cache_err:
                logger.warning(f"Failed to cache voice profiles: {cache_err}")

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "profiles": profiles_data,
                "stats": {
                    "characters_analyzed": len(profiles_data),
                    "total_dialogues": len(dialogues),
                    "chapters_analyzed": len(chapters),
                },
                "cached": False,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice profiles: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/voice-profiles/compare", response_model=ApiResponse)
async def compare_voice_profiles(
    project_id: int,
    entity_a: int = Query(..., description="ID de la primera entidad"),
    entity_b: int = Query(..., description="ID de la segunda entidad"),
):
    """
    Compara los perfiles de voz de dos personajes.

    Devuelve las metricas de ambos perfiles lado a lado con deltas
    y un indice de similitud global.

    Returns:
        ApiResponse con comparacion de perfiles
    """
    try:
        from narrative_assistant.voice.profiles import VoiceProfileBuilder
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        entity_map = {e.id: e for e in characters}
        if entity_a not in entity_map:
            raise HTTPException(status_code=404, detail=f"Entidad {entity_a} no encontrada")
        if entity_b not in entity_map:
            raise HTTPException(status_code=404, detail=f"Entidad {entity_b} no encontrada")

        # Obtener dialogos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        dialogues = []
        for chapter in chapters:
            dialogue_result = detect_dialogues(chapter.content)
            if dialogue_result.is_success:
                for d in dialogue_result.value.dialogues:
                    dialogues.append({
                        "text": d.text,
                        "speaker_id": d.speaker_id,
                        "speaker_hint": d.speaker_hint,
                        "chapter": chapter.chapter_number,
                        "position": d.start_char,
                    })

        if not dialogues:
            return ApiResponse(success=False, error="No se encontraron diálogos para analizar")

        # Construir perfiles
        entity_data = [
            {"id": e.id, "name": e.canonical_name, "aliases": e.aliases}
            for e in characters
        ]
        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entity_data)
        profiles_map = {p.entity_id: p for p in profiles}

        profile_a = profiles_map.get(entity_a)
        profile_b = profiles_map.get(entity_b)

        if not profile_a or not profile_b:
            missing = []
            if not profile_a:
                missing.append(entity_map[entity_a].canonical_name)
            if not profile_b:
                missing.append(entity_map[entity_b].canonical_name)
            return ApiResponse(
                success=False,
                error=f"No hay suficientes diálogos para: {', '.join(missing)}"
            )

        # Comparar metricas
        ma = profile_a.metrics
        mb = profile_b.metrics

        def safe_delta(va: float, vb: float) -> float:
            return round(va - vb, 3)

        def similarity_ratio(va: float, vb: float) -> float:
            """0 = opuestos, 1 = identicos."""
            if va == 0 and vb == 0:
                return 1.0
            max_val = max(abs(va), abs(vb))
            if max_val == 0:
                return 1.0
            return round(1.0 - abs(va - vb) / (max_val * 2), 3)

        metrics_comparison = {
            "avg_intervention_length": {
                "a": round(ma.avg_intervention_length, 1),
                "b": round(mb.avg_intervention_length, 1),
                "delta": safe_delta(ma.avg_intervention_length, mb.avg_intervention_length),
            },
            "type_token_ratio": {
                "a": round(ma.type_token_ratio, 3),
                "b": round(mb.type_token_ratio, 3),
                "delta": safe_delta(ma.type_token_ratio, mb.type_token_ratio),
            },
            "formality_score": {
                "a": round(ma.formality_score, 3),
                "b": round(mb.formality_score, 3),
                "delta": safe_delta(ma.formality_score, mb.formality_score),
            },
            "filler_ratio": {
                "a": round(ma.filler_ratio, 3),
                "b": round(mb.filler_ratio, 3),
                "delta": safe_delta(ma.filler_ratio, mb.filler_ratio),
            },
            "exclamation_ratio": {
                "a": round(ma.exclamation_ratio, 3),
                "b": round(mb.exclamation_ratio, 3),
                "delta": safe_delta(ma.exclamation_ratio, mb.exclamation_ratio),
            },
            "question_ratio": {
                "a": round(ma.question_ratio, 3),
                "b": round(mb.question_ratio, 3),
                "delta": safe_delta(ma.question_ratio, mb.question_ratio),
            },
            "avg_sentence_length": {
                "a": round(ma.avg_sentence_length, 1),
                "b": round(mb.avg_sentence_length, 1),
                "delta": safe_delta(ma.avg_sentence_length, mb.avg_sentence_length),
            },
            "subordinate_clause_ratio": {
                "a": round(ma.subordinate_clause_ratio, 3),
                "b": round(mb.subordinate_clause_ratio, 3),
                "delta": safe_delta(ma.subordinate_clause_ratio, mb.subordinate_clause_ratio),
            },
        }

        # Indice de similitud global (media de similitudes individuales)
        similarities = [
            similarity_ratio(ma.avg_intervention_length, mb.avg_intervention_length),
            similarity_ratio(ma.type_token_ratio, mb.type_token_ratio),
            similarity_ratio(ma.formality_score, mb.formality_score),
            similarity_ratio(ma.filler_ratio, mb.filler_ratio),
            similarity_ratio(ma.exclamation_ratio, mb.exclamation_ratio),
            similarity_ratio(ma.question_ratio, mb.question_ratio),
            similarity_ratio(ma.avg_sentence_length, mb.avg_sentence_length),
            similarity_ratio(ma.subordinate_clause_ratio, mb.subordinate_clause_ratio),
        ]
        overall_similarity = round(sum(similarities) / len(similarities), 3)

        # Palabras caracteristicas compartidas vs unicas
        words_a = set(w for w, _ in profile_a.characteristic_words[:15])
        words_b = set(w for w, _ in profile_b.characteristic_words[:15])
        shared_words = sorted(words_a & words_b)
        unique_a = sorted(words_a - words_b)
        unique_b = sorted(words_b - words_a)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "entity_a": {
                    "id": entity_a,
                    "name": entity_map[entity_a].canonical_name,
                    "total_interventions": ma.total_interventions,
                    "total_words": ma.total_words,
                    "confidence": profile_a.confidence,
                },
                "entity_b": {
                    "id": entity_b,
                    "name": entity_map[entity_b].canonical_name,
                    "total_interventions": mb.total_interventions,
                    "total_words": mb.total_words,
                    "confidence": profile_b.confidence,
                },
                "metrics_comparison": metrics_comparison,
                "overall_similarity": overall_similarity,
                "vocabulary": {
                    "shared_words": shared_words,
                    "unique_to_a": unique_a,
                    "unique_to_b": unique_b,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing voice profiles: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/voice-deviations", response_model=ApiResponse)
async def get_voice_deviations(
    project_id: int,
    min_severity: str = Query("low", description="Severidad mínima: low, medium, high"),
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo"),
):
    """
    Detecta desviaciones en la voz de los personajes.

    Compara los diálogos de cada personaje contra su perfil de voz establecido
    y reporta desviaciones significativas (cambios de formalidad, longitud atípica,
    vocabulario inusual, cambio en muletillas, etc.).

    Returns:
        ApiResponse con desviaciones detectadas por personaje
    """
    try:
        from narrative_assistant.voice.profiles import VoiceProfileBuilder
        from narrative_assistant.voice.deviations import VoiceDeviationDetector
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener entidades (solo personajes)
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        if not characters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "deviations": [],
                    "message": "No hay personajes para analizar"
                }
            )

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if chapter_number is not None:
            chapters = [ch for ch in chapters if ch.chapter_number == chapter_number]

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "deviations": [],
                    "message": "No hay capítulos para analizar"
                }
            )

        # Extraer diálogos de cada capítulo
        dialogues = []
        for chapter in chapters:
            dialogue_result = detect_dialogues(chapter.content)
            if dialogue_result.is_success:
                for d in dialogue_result.value.dialogues:
                    dialogues.append({
                        "text": d.text,
                        "speaker_id": d.speaker_id,
                        "speaker_hint": d.speaker_hint,
                        "chapter": chapter.chapter_number,
                        "position": d.start_char,
                    })

        if not dialogues:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "deviations": [],
                    "message": "No se encontraron diálogos para analizar"
                }
            )

        # Construir perfiles de voz
        entity_data = [
            {"id": e.id, "name": e.canonical_name, "aliases": e.aliases}
            for e in characters
        ]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entity_data)

        if not profiles:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "deviations": [],
                    "message": "No se pudieron construir perfiles de voz"
                }
            )

        # Detectar desviaciones
        detector = VoiceDeviationDetector()
        deviations = detector.detect_deviations(profiles, dialogues)

        # Filtrar por severidad mínima
        severity_order = {"low": 0, "medium": 1, "high": 2}
        min_sev_value = severity_order.get(min_severity, 0)
        filtered = [
            dev for dev in deviations
            if severity_order.get(dev.severity.value, 0) >= min_sev_value
        ]

        # Serializar
        deviations_data = [dev.to_dict() for dev in filtered]

        # Agrupar por personaje para resumen
        by_character: dict = {}
        for dev in filtered:
            name = dev.entity_name
            if name not in by_character:
                by_character[name] = {"entity_id": dev.entity_id, "count": 0, "types": set()}
            by_character[name]["count"] += 1
            by_character[name]["types"].add(dev.deviation_type.value)

        summary = {
            name: {"entity_id": info["entity_id"], "count": info["count"], "types": list(info["types"])}
            for name, info in by_character.items()
        }

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "deviations": deviations_data,
                "summary_by_character": summary,
                "stats": {
                    "total_deviations": len(filtered),
                    "characters_with_deviations": len(by_character),
                    "profiles_built": len(profiles),
                    "dialogues_analyzed": len(dialogues),
                    "chapters_analyzed": len(chapters),
                    "min_severity_filter": min_severity,
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting voice deviations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/register-analysis", response_model=ApiResponse)
async def get_register_analysis(
    project_id: int,
    min_severity: str = Query("medium", description="Severidad mínima: low, medium, high"),
    chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo")
):
    """
    Analiza el registro narrativo del proyecto.

    Detecta cambios de registro narrativo (formal/informal, técnico/coloquial)
    que pueden indicar inconsistencias en la voz del narrador o entre escenas.

    Returns:
        ApiResponse con análisis de registro y cambios detectados
    """
    try:
        from narrative_assistant.voice.register import (
            RegisterChangeDetector,
            RegisterAnalyzer,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "analyses": [],
                    "changes": [],
                    "summary": {},
                    "message": "No hay capítulos para analizar"
                }
            )

        # Construir segmentos: (texto, capítulo, posición, es_diálogo)
        segments = []
        for chapter in chapters:
            if chapter_number is not None and chapter.chapter_number != chapter_number:
                continue
            # Detectar diálogos para separar narración de diálogo
            dialogue_result = detect_dialogues(chapter.content)
            dialogue_ranges = []
            if dialogue_result.is_success:
                dialogue_ranges = [
                    (d.start_char, d.end_char)
                    for d in dialogue_result.value.dialogues
                ]

            # Dividir contenido en párrafos
            paragraphs = chapter.content.split('\n\n')
            position = 0

            for para in paragraphs:
                if para.strip():
                    # Determinar si es diálogo
                    is_dialogue = any(
                        start <= position <= end
                        for start, end in dialogue_ranges
                    )
                    segments.append((
                        para.strip(),
                        chapter.chapter_number,
                        position,
                        is_dialogue
                    ))
                position += len(para) + 2  # +2 por '\n\n'

        if not segments:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "analyses": [],
                    "changes": [],
                    "summary": {},
                    "message": "No hay segmentos para analizar"
                }
            )

        # Analizar registro
        detector = RegisterChangeDetector()
        analyses = detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity)
        summary = detector.get_summary()

        # Serializar resultados
        analyses_data = [
            {
                "segment_index": i,
                "chapter": segments[i][1],
                "is_dialogue": segments[i][3],
                "primary_register": a.primary_register.value,
                "register_scores": {k.value: v for k, v in a.register_scores.items()},
                "confidence": a.confidence,
                "formal_indicators": list(a.formal_indicators)[:5],
                "colloquial_indicators": list(a.colloquial_indicators)[:5],
            }
            for i, a in enumerate(analyses)
        ]

        changes_data = [
            {
                "from_register": c.from_register.value,
                "to_register": c.to_register.value,
                "severity": c.severity,
                "explanation": c.explanation,
                "chapter": c.chapter,
                "position": c.position,
                "context_before": c.context_before[:100] if c.context_before else "",
                "context_after": c.context_after[:100] if c.context_after else "",
            }
            for c in changes
        ]

        # Build per-chapter summaries
        chapter_summaries = {}
        for i, a in enumerate(analyses):
            ch = segments[i][1]
            if ch not in chapter_summaries:
                chapter_summaries[ch] = {"registers": {}, "total": 0, "changes": 0}
            reg = a.primary_register.value
            chapter_summaries[ch]["registers"][reg] = chapter_summaries[ch]["registers"].get(reg, 0) + 1
            chapter_summaries[ch]["total"] += 1

        for c in changes:
            ch = c.chapter
            if ch in chapter_summaries:
                chapter_summaries[ch]["changes"] += 1

        per_chapter = []
        for ch_num in sorted(chapter_summaries.keys()):
            cs = chapter_summaries[ch_num]
            dominant = max(cs["registers"], key=cs["registers"].get) if cs["registers"] else "neutral"
            consistency = (cs["registers"].get(dominant, 0) / cs["total"] * 100) if cs["total"] > 0 else 100
            per_chapter.append({
                "chapter_number": ch_num,
                "dominant_register": dominant,
                "consistency_pct": round(consistency, 1),
                "segment_count": cs["total"],
                "change_count": cs["changes"],
                "distribution": cs["registers"],
            })

        # Compute aggregated stats
        total_segs = summary.get("total_segments", 0)
        distribution = summary.get("distribution", {})
        dominant = summary.get("dominant_register")
        if total_segs > 0 and dominant:
            consistency_pct = round(distribution.get(dominant, 0) / total_segs * 100, 1)
            distribution_pct = {
                reg: round(count / total_segs * 100, 1)
                for reg, count in distribution.items()
            }
        else:
            consistency_pct = 100.0
            distribution_pct = {}

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "analyses": analyses_data,
                "changes": changes_data,
                "summary": {
                    **summary,
                    "consistency_pct": consistency_pct,
                    "distribution_pct": distribution_pct,
                },
                "per_chapter": per_chapter,
                "stats": {
                    "segments_analyzed": len(analyses),
                    "changes_detected": len(changes),
                    "chapters_analyzed": len(chapters),
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing register: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/speaker-corrections", response_model=ApiResponse)
async def list_speaker_corrections(
    project_id: int,
    chapter_number: Optional[int] = Query(None, description="Filtrar por capítulo")
):
    """Lista correcciones manuales de atribución de hablantes."""
    try:
        db = deps.get_database()
        with db.connect() as conn:
            if chapter_number is not None:
                rows = conn.execute(
                    """SELECT sc.id, sc.chapter_number, sc.dialogue_start_char,
                              sc.dialogue_end_char, sc.dialogue_text,
                              sc.original_speaker_id, sc.corrected_speaker_id,
                              sc.notes, sc.created_at,
                              e_orig.canonical_name AS original_speaker_name,
                              e_corr.canonical_name AS corrected_speaker_name
                       FROM speaker_corrections sc
                       LEFT JOIN entities e_orig ON sc.original_speaker_id = e_orig.id
                       LEFT JOIN entities e_corr ON sc.corrected_speaker_id = e_corr.id
                       WHERE sc.project_id = ? AND sc.chapter_number = ?
                       ORDER BY sc.dialogue_start_char""",
                    (project_id, chapter_number)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT sc.id, sc.chapter_number, sc.dialogue_start_char,
                              sc.dialogue_end_char, sc.dialogue_text,
                              sc.original_speaker_id, sc.corrected_speaker_id,
                              sc.notes, sc.created_at,
                              e_orig.canonical_name AS original_speaker_name,
                              e_corr.canonical_name AS corrected_speaker_name
                       FROM speaker_corrections sc
                       LEFT JOIN entities e_orig ON sc.original_speaker_id = e_orig.id
                       LEFT JOIN entities e_corr ON sc.corrected_speaker_id = e_corr.id
                       WHERE sc.project_id = ?
                       ORDER BY sc.chapter_number, sc.dialogue_start_char""",
                    (project_id,)
                ).fetchall()

        corrections = []
        for row in rows:
            corrections.append({
                "id": row[0],
                "chapterNumber": row[1],
                "dialogueStartChar": row[2],
                "dialogueEndChar": row[3],
                "dialogueText": row[4],
                "originalSpeakerId": row[5],
                "correctedSpeakerId": row[6],
                "notes": row[7],
                "createdAt": row[8],
                "originalSpeakerName": row[9],
                "correctedSpeakerName": row[10],
            })

        return ApiResponse(success=True, data={
            "projectId": project_id,
            "corrections": corrections,
            "totalCorrections": len(corrections),
        })
    except Exception as e:
        logger.error(f"Error listing speaker corrections: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/speaker-corrections", response_model=ApiResponse)
async def create_speaker_correction(project_id: int, payload: deps.DialogueCorrectionRequest):
    """
    Crea una corrección manual de atribución de hablante.

    Body JSON:
    - chapter_number: Número de capítulo
    - dialogue_start_char: Posición inicio del diálogo
    - dialogue_end_char: Posición fin del diálogo
    - dialogue_text: Texto del diálogo
    - original_speaker_id: Hablante asignado automáticamente (nullable)
    - corrected_speaker_id: Hablante correcto según el usuario
    - notes: Notas del corrector (opcional)
    """
    try:
        chapter_num = payload.chapter_number
        dialogue_start = payload.dialogue_start_char
        dialogue_end = payload.dialogue_end_char
        dialogue_text = payload.dialogue_text
        original_speaker_id = payload.original_speaker_id
        corrected_speaker_id = payload.corrected_speaker_id
        notes = payload.notes

        db = deps.get_database()
        with db.connect() as conn:
            # Verificar si ya existe corrección para este diálogo
            existing = conn.execute(
                """SELECT id FROM speaker_corrections
                   WHERE project_id = ? AND chapter_number = ?
                   AND dialogue_start_char = ? AND dialogue_end_char = ?""",
                (project_id, chapter_num, dialogue_start, dialogue_end)
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE speaker_corrections
                       SET corrected_speaker_id = ?, notes = ?, created_at = datetime('now')
                       WHERE id = ?""",
                    (corrected_speaker_id, notes, existing[0])
                )
                correction_id = existing[0]
            else:
                cursor = conn.execute(
                    """INSERT INTO speaker_corrections
                       (project_id, chapter_number, dialogue_start_char, dialogue_end_char,
                        dialogue_text, original_speaker_id, corrected_speaker_id, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (project_id, chapter_num, dialogue_start, dialogue_end,
                     dialogue_text, original_speaker_id, corrected_speaker_id, notes)
                )
                correction_id = cursor.lastrowid

            conn.commit()

        return ApiResponse(success=True, data={
            "correctionId": correction_id,
            "applied": True,
        })
    except Exception as e:
        logger.error(f"Error creating speaker correction: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/projects/{project_id}/speaker-corrections/{correction_id}", response_model=ApiResponse)
async def delete_speaker_correction(project_id: int, correction_id: int):
    """Elimina una corrección manual de atribución de hablante."""
    try:
        db = deps.get_database()
        with db.connect() as conn:
            result = conn.execute(
                "DELETE FROM speaker_corrections WHERE id = ? AND project_id = ?",
                (correction_id, project_id)
            )
            conn.commit()

            if result.rowcount == 0:
                return ApiResponse(success=False, error="Corrección no encontrada")

        return ApiResponse(success=True, data={"deleted": True})
    except Exception as e:
        logger.error(f"Error deleting speaker correction: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/focalization", response_model=ApiResponse)
async def get_project_focalizations(project_id: int):
    """Obtiene todas las declaraciones de focalización de un proyecto."""
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        declarations = service.get_all_declarations(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "declarations": [d.to_dict() for d in declarations],
                "total": len(declarations),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting focalizations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/focalization", response_model=ApiResponse)
async def create_focalization(project_id: int, data: dict):
    """Crea una nueva declaración de focalización para un capítulo/escena."""
    try:
        from narrative_assistant.focalization import (
            FocalizationType,
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter = data.get("chapter")
        if not chapter:
            return ApiResponse(success=False, error="Se requiere número de capítulo")

        foc_type_str = data.get("focalization_type", "zero")
        try:
            foc_type = FocalizationType(foc_type_str)
        except ValueError:
            return ApiResponse(success=False, error=f"Tipo de focalización inválido: {foc_type_str}")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        declaration = service.declare_focalization(
            project_id=project_id,
            chapter=chapter,
            focalization_type=foc_type,
            focalizer_ids=data.get("focalizer_ids", []),
            scene=data.get("scene"),
            notes=data.get("notes", ""),
        )

        return ApiResponse(success=True, data=declaration.to_dict())
    except ValueError as e:
        return ApiResponse(success=False, error="Error interno del servidor")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.put("/api/projects/{project_id}/focalization/{declaration_id}", response_model=ApiResponse)
async def update_focalization(project_id: int, declaration_id: int, data: dict):
    """Actualiza una declaración de focalización existente."""
    try:
        from narrative_assistant.focalization import (
            FocalizationType,
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        foc_type = None
        if "focalization_type" in data:
            try:
                foc_type = FocalizationType(data["focalization_type"])
            except ValueError:
                return ApiResponse(success=False, error=f"Tipo inválido: {data['focalization_type']}")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        declaration = service.update_focalization(
            declaration_id=declaration_id,
            focalization_type=foc_type,
            focalizer_ids=data.get("focalizer_ids"),
            notes=data.get("notes"),
        )

        return ApiResponse(success=True, data=declaration.to_dict())
    except ValueError as e:
        return ApiResponse(success=False, error="Error interno del servidor")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/projects/{project_id}/focalization/{declaration_id}", response_model=ApiResponse)
async def delete_focalization(project_id: int, declaration_id: int):
    """Elimina una declaración de focalización."""
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        deleted = service.delete_focalization(declaration_id)

        if deleted:
            return ApiResponse(success=True, message="Declaración eliminada")
        return ApiResponse(success=False, error="Declaración no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/focalization/violations", response_model=ApiResponse)
async def detect_focalization_violations(project_id: int):
    """Detecta violaciones de focalización en todo el proyecto."""
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            FocalizationViolationDetector,
            SQLiteFocalizationRepository,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository
        from narrative_assistant.entities.repository import get_entity_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(success=True, data={"violations": [], "stats": {"total": 0}})

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        detector = FocalizationViolationDetector(service, characters)

        all_violations = []
        by_chapter = {}

        for chapter in chapters:
            violations = detector.detect_violations(
                project_id=project_id,
                text=chapter.content,
                chapter=chapter.chapter_number,
            )
            by_chapter[chapter.chapter_number] = {
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "violations_count": len(violations),
                "violations": [v.to_dict() for v in violations],
            }
            all_violations.extend([v.to_dict() for v in violations])

        stats = {
            "total": len(all_violations),
            "by_type": {},
            "by_severity": {},
            "chapters_with_violations": sum(1 for ch in by_chapter.values() if ch["violations_count"] > 0),
        }
        for v in all_violations:
            stats["by_type"][v["violation_type"]] = stats["by_type"].get(v["violation_type"], 0) + 1
            stats["by_severity"][v["severity"]] = stats["by_severity"].get(v["severity"], 0) + 1

        return ApiResponse(success=True, data={"violations": all_violations, "by_chapter": by_chapter, "stats": stats})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting focalization violations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/register-analysis/genre-comparison", response_model=ApiResponse)
async def get_register_genre_comparison(
    project_id: int,
    genre_code: str = Query(..., description="Código de género para comparar (FIC, MEM, TEC, etc.)"),
    min_severity: str = Query("low", description="Severidad mínima para contar cambios: low, medium, high"),
):
    """
    Compara las métricas de registro del proyecto contra benchmarks del género.

    Devuelve desviaciones de consistencia, registro dominante y distribución
    respecto a lo esperado para el tipo de documento.
    """
    try:
        from narrative_assistant.voice.register import (
            RegisterChangeDetector,
            REGISTER_GENRE_BENCHMARKS,
            compare_register_with_benchmarks,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(success=True, data={"comparison": None, "message": "No hay capítulos"})

        # Construir segmentos
        segments = []
        for chapter in chapters:
            dialogue_result = detect_dialogues(chapter.content)
            dialogue_ranges = []
            if dialogue_result.is_success:
                dialogue_ranges = [
                    (d.start_char, d.end_char)
                    for d in dialogue_result.value.dialogues
                ]

            paragraphs = chapter.content.split('\n\n')
            position = 0
            for para in paragraphs:
                if para.strip():
                    is_dialogue = any(
                        start <= position <= end
                        for start, end in dialogue_ranges
                    )
                    segments.append((
                        para.strip(),
                        chapter.chapter_number,
                        position,
                        is_dialogue
                    ))
                position += len(para) + 2

        if not segments:
            return ApiResponse(success=True, data={"comparison": None, "message": "No hay segmentos"})

        # Analizar registro
        detector = RegisterChangeDetector()
        detector.analyze_document(segments)
        changes = detector.detect_changes("low")
        summary = detector.get_summary()

        high_severity = sum(1 for c in changes if c.severity == "high")

        comparison = compare_register_with_benchmarks(
            summary, genre_code.upper(), len(changes), high_severity
        )

        if comparison is None:
            available = list(REGISTER_GENRE_BENCHMARKS.keys())
            return ApiResponse(
                success=False,
                error=f"Género '{genre_code}' no encontrado. Disponibles: {', '.join(available)}"
            )

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "summary": summary,
                "changes_count": len(changes),
                "high_severity_count": high_severity,
                "comparison": comparison,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing register with genre: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


