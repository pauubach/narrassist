"""
Router: entities
"""

import bisect
from typing import Optional

import deps
from deps import (
    ApiResponse,
    EntityResponse,
    _classify_mention_type,
    _verify_entity_ownership,
    logger,
)
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/api/projects/{project_id}/entities", response_model=ApiResponse)
def list_entities(
    project_id: int,
    min_relevance: Optional[float] = None,
    min_mentions: Optional[int] = None,
    entity_type: Optional[str] = None,
    chapter_number: Optional[int] = Query(
        None, description="Filtrar entidades que aparecen en este capítulo"
    ),
):
    """
    Lista todas las entidades de un proyecto con filtros opcionales.

    La relevancia se calcula como:
    - Densidad de menciones: (menciones / palabras_documento) * factor_normalizacion
    - Entidades con pocas menciones en documentos largos tienen baja relevancia
    - Entidades con varias menciones en documentos cortos tienen alta relevancia

    Args:
        project_id: ID del proyecto
        min_relevance: Score mínimo de relevancia (0-1) para incluir entidad
        min_mentions: Número mínimo de menciones para incluir entidad
        entity_type: Filtrar por tipo (character, location, object, etc.)
        chapter_number: Filtrar entidades que tienen menciones en este capítulo

    Returns:
        ApiResponse con lista de entidades
    """
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id)

        # Obtener word_count del proyecto para calcular densidad
        project_result = deps.project_manager.get(project_id)
        project = project_result.value if project_result.is_success else None
        word_count = (
            project.word_count if project and project.word_count else 50000
        )  # Default

        # Obtener capítulos para calcular first_mention_chapter
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        # Mapa posición→capítulo con bisect: O(log n) en vez de O(n) por búsqueda
        _sorted_chapters = sorted(chapters, key=lambda ch: ch.start_char)
        _chapter_starts = [ch.start_char for ch in _sorted_chapters]

        def get_chapter_for_position(pos: int) -> Optional[int]:
            if pos is None:
                return None
            # bisect_right devuelve el índice tras el último start_char <= pos
            idx = bisect.bisect_right(_chapter_starts, pos) - 1
            if idx >= 0:
                ch = _sorted_chapters[idx]
                if ch.start_char <= pos < ch.end_char:
                    return ch.chapter_number
            return 1  # Default al capítulo 1 si no se encuentra

        # Si se filtra por capítulo, obtener IDs de entidades con menciones en ese capítulo
        chapter_entity_ids: Optional[set] = None
        if chapter_number is not None:
            chapter_entity_ids = set()
            target_chapter = next(
                (ch for ch in chapters if ch.chapter_number == chapter_number), None
            )
            if target_chapter:
                chapter_entity_ids = entity_repo.get_entity_ids_for_chapter(
                    target_chapter.id,  # type: ignore[arg-type]
                    target_chapter.start_char,
                    target_chapter.end_char,
                )

        # Calcular relevance_score para cada entidad
        # Fórmula: menciones / (palabras / 1000) normalizado
        # Una entidad mencionada 5 veces en 1000 palabras es muy relevante
        # Una entidad mencionada 2 veces en 100000 palabras es poco relevante
        words_in_thousands = max(word_count / 1000, 1)

        entities_data = []
        for e in entities:
            mention_count = e.mention_count or 0

            # Calcular relevance_score (0-1)
            # Menciones por cada 1000 palabras, normalizado con sigmoid-like
            mentions_per_k = mention_count / words_in_thousands
            # Sigmoid suave: score = menciones_per_k / (menciones_per_k + 2)
            # Con 2 menciones/1000 palabras -> 0.5
            # Con 5 menciones/1000 palabras -> 0.71
            # Con 10 menciones/1000 palabras -> 0.83
            relevance_score = (
                mentions_per_k / (mentions_per_k + 2) if mention_count > 0 else 0
            )

            # Aplicar filtros
            if chapter_entity_ids is not None and e.id not in chapter_entity_ids:
                continue
            if min_relevance is not None and relevance_score < min_relevance:
                continue
            if min_mentions is not None and mention_count < min_mentions:
                continue
            if entity_type is not None and e.entity_type.value != entity_type:
                continue

            # Calcular first_mention_chapter desde first_appearance_char
            first_mention_chapter = get_chapter_for_position(e.first_appearance_char)  # type: ignore[arg-type]

            entities_data.append(
                EntityResponse(
                    id=e.id,  # type: ignore[arg-type]
                    project_id=e.project_id,
                    entity_type=e.entity_type.value,
                    canonical_name=e.canonical_name,
                    aliases=e.aliases or [],
                    importance=e.importance.value,
                    description=e.description,
                    first_appearance_char=e.first_appearance_char,
                    first_mention_chapter=first_mention_chapter,
                    mention_count=mention_count,
                    is_active=e.is_active if hasattr(e, "is_active") else True,
                    merged_from_ids=e.merged_from_ids or [],
                    relevance_score=round(relevance_score, 3),
                    created_at=(
                        e.created_at.isoformat()
                        if hasattr(e, "created_at") and e.created_at
                        else None
                    ),
                    updated_at=(
                        e.updated_at.isoformat()
                        if hasattr(e, "updated_at") and e.updated_at
                        else None
                    ),
                )
            )

        return ApiResponse(success=True, data=entities_data)
    except Exception as e:
        logger.error(
            f"Error listing entities for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/entities/preview-merge", response_model=ApiResponse
)
def preview_merge_entities(project_id: int, body: deps.EntityIdsRequest):
    """
    Preview de fusión de entidades con análisis de similitud detallado y detección de conflictos.

    Proporciona información detallada antes de confirmar la fusión:
    - Scores de similitud (nombre Levenshtein/Jaro-Winkler + semántica)
    - Preview del resultado fusionado
    - Detección de conflictos de atributos contradictorios

    Args:
        project_id: ID del proyecto
        body: EntityIdsRequest con entity_ids (lista de IDs a fusionar, min 2)

    Returns:
        ApiResponse con preview detallado de la fusión
    """
    try:
        entity_ids = body.entity_ids

        entity_repo = deps.entity_repository

        # Obtener las entidades
        entities = []
        for entity_id in entity_ids:
            entity = entity_repo.get_entity(entity_id)
            if entity and entity.project_id == project_id:
                entities.append(entity)

        if len(entities) < 2:
            return ApiResponse(
                success=False, error="No se encontraron suficientes entidades válidas"
            )

        # =====================================================================
        # 1. Calcular similitud detallada entre pares
        # =====================================================================
        try:
            from narrative_assistant.entities.semantic_fusion import (
                get_semantic_fusion_service,
            )

            semantic_service = get_semantic_fusion_service()
        except ImportError:
            semantic_service = None

        # Calcular similitud por nombre (Levenshtein/SequenceMatcher)
        def compute_name_similarity(name1: str, name2: str) -> dict:
            """Calcula múltiples métricas de similitud por nombre."""
            import unicodedata
            from difflib import SequenceMatcher

            def normalize(s):
                return (
                    unicodedata.normalize("NFKD", s.lower())
                    .encode("ascii", "ignore")
                    .decode()
                )

            n1 = normalize(name1)
            n2 = normalize(name2)

            # SequenceMatcher ratio (similar a Levenshtein normalizado)
            sequence_ratio = SequenceMatcher(None, n1, n2).ratio()

            # Jaro-Winkler approximation (usando quick_ratio para eficiencia)
            quick_ratio = SequenceMatcher(None, n1, n2).quick_ratio()

            # Contención: si un nombre contiene al otro
            containment = 0.0
            if n1 in n2 or n2 in n1:
                shorter = min(len(n1), len(n2))
                longer = max(len(n1), len(n2))
                containment = shorter / longer if longer > 0 else 0

            return {
                "levenshtein": round(sequence_ratio, 3),
                "jaro_winkler": round(quick_ratio, 3),
                "containment": round(containment, 3),
                "combined": round(
                    (sequence_ratio * 0.5 + quick_ratio * 0.3 + containment * 0.2), 3
                ),
            }

        similarity_pairs = []
        for i, ent1 in enumerate(entities):
            for j, ent2 in enumerate(entities):
                if i >= j:
                    continue

                # Similitud por nombre
                name_sim = compute_name_similarity(
                    ent1.canonical_name, ent2.canonical_name
                )

                # Similitud semántica (embeddings)
                semantic_sim = 0.0
                semantic_reason = ""
                if semantic_service:
                    try:
                        semantic_sim = semantic_service.compute_semantic_similarity(
                            ent1, ent2
                        )
                        result = semantic_service.should_merge(ent1, ent2)
                        semantic_reason = result.reason
                    except Exception as e:
                        logger.warning(f"Error computing semantic similarity: {e}")
                        semantic_sim = 0.0

                # Score combinado (40% nombre, 60% semántica si disponible)
                if semantic_sim > 0:
                    combined_score = name_sim["combined"] * 0.4 + semantic_sim * 0.6
                else:
                    combined_score = name_sim["combined"]

                similarity_pairs.append(
                    {
                        "entity1_id": ent1.id,
                        "entity1_name": ent1.canonical_name,
                        "entity2_id": ent2.id,
                        "entity2_name": ent2.canonical_name,
                        "name_similarity": name_sim,
                        "semantic_similarity": round(semantic_sim, 3),
                        "semantic_reason": semantic_reason,
                        "combined_score": round(combined_score, 3),
                        "recommendation": (
                            "merge"
                            if combined_score >= 0.6
                            else "review" if combined_score >= 0.4 else "keep_separate"
                        ),
                    }
                )

        # =====================================================================
        # 2. Calcular preview del resultado fusionado
        # =====================================================================

        # Recopilar todos los nombres/aliases
        all_names = set()
        all_aliases = set()
        for entity in entities:
            all_names.add(entity.canonical_name)
            all_aliases.update(entity.aliases)

        # Calcular menciones totales
        total_mentions = sum(e.mention_count for e in entities)

        # Determinar el tipo más común
        type_counts = {}
        for entity in entities:
            t = entity.entity_type.value
            type_counts[t] = type_counts.get(t, 0) + entity.mention_count
        suggested_type = (
            max(type_counts.keys(), key=lambda x: type_counts[x])
            if type_counts
            else entities[0].entity_type.value
        )

        # Sugerir nombre canónico (el más largo que sea nombre propio)
        def score_canonical_name(name: str) -> int:
            score = 0
            words = name.split()
            # Preferir nombres con 2-3 palabras
            if 2 <= len(words) <= 3:
                score += 20
            # Preferir nombres que empiezan con mayúscula
            if name and name[0].isupper():
                score += 30
            # Penalizar si empieza con artículo
            articles = ["el", "la", "los", "las", "un", "una"]
            if words and words[0].lower() in articles:
                score -= 50
            # Preferir nombres más largos (hasta cierto punto)
            score += min(len(name), 25)
            return score

        suggested_canonical = max(all_names, key=score_canonical_name)
        suggested_aliases = list(all_names - {suggested_canonical}) + list(all_aliases)

        merged_preview = {
            "suggested_canonical_name": suggested_canonical,
            "suggested_aliases": list(set(suggested_aliases)),
            "suggested_type": suggested_type,
            "total_mentions": total_mentions,
            "entities_to_merge": len(entities),
            "all_names": list(all_names),
        }

        # =====================================================================
        # 3. Detectar conflictos de atributos
        # =====================================================================
        conflicts = []
        all_attributes = (
            {}
        )  # {(category, name): [(value, entity_name, entity_id), ...]}

        for entity in entities:
            attrs = entity_repo.get_attributes_by_entity(entity.id)
            for attr in attrs:
                key = (
                    attr.get("attribute_type", attr.get("category", "")),
                    attr.get("attribute_key", attr.get("name", "")),
                )
                value = attr.get("attribute_value", attr.get("value", ""))

                if key not in all_attributes:
                    all_attributes[key] = []
                all_attributes[key].append(
                    {
                        "value": value,
                        "entity_name": entity.canonical_name,
                        "entity_id": entity.id,
                        "confidence": attr.get("confidence", 1.0),
                    }
                )

        # Detectar conflictos (mismo atributo, diferentes valores)
        for (category, attr_name), values in all_attributes.items():
            unique_values = set(v["value"].lower().strip() for v in values)
            if len(unique_values) > 1:
                conflicts.append(
                    {
                        "category": category,
                        "attribute_name": attr_name,
                        "conflicting_values": [
                            {
                                "value": v["value"],
                                "entity_name": v["entity_name"],
                                "entity_id": v["entity_id"],
                                "confidence": v["confidence"],
                            }
                            for v in values
                        ],
                        "severity": (
                            "high" if category in ["physical", "identity"] else "medium"
                        ),
                    }
                )

        # Ordenar conflictos por severidad
        severity_order = {"high": 0, "medium": 1, "low": 2}
        conflicts.sort(key=lambda c: severity_order.get(c["severity"], 2))

        # =====================================================================
        # 4. Calcular recomendación general
        # =====================================================================
        avg_similarity = (
            sum(p["combined_score"] for p in similarity_pairs) / len(similarity_pairs)
            if similarity_pairs
            else 0
        )
        has_high_conflicts = any(c["severity"] == "high" for c in conflicts)

        if avg_similarity >= 0.6 and not has_high_conflicts:
            recommendation = "merge"
            recommendation_reason = "Alta similitud sin conflictos significativos"
        elif avg_similarity >= 0.4:
            recommendation = "review"
            if has_high_conflicts:
                recommendation_reason = "Similitud aceptable pero hay conflictos de atributos que requieren revisión"
            else:
                recommendation_reason = "Similitud media, revisar antes de fusionar"
        else:
            recommendation = "keep_separate"
            recommendation_reason = (
                "Baja similitud, las entidades podrían ser diferentes"
            )

        return ApiResponse(
            success=True,
            data={
                "similarity": {
                    "pairs": similarity_pairs,
                    "average_score": round(avg_similarity, 3),
                },
                "merged_preview": merged_preview,
                "conflicts": conflicts,
                "conflict_count": len(conflicts),
                "has_critical_conflicts": has_high_conflicts,
                "recommendation": recommendation,
                "recommendation_reason": recommendation_reason,
                "entity_count": len(entities),
            },
        )

    except Exception as e:
        logger.error(f"Error previewing entity merge: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/entities/merge", response_model=ApiResponse)
def merge_entities(project_id: int, body: deps.MergeEntitiesRequest):
    """
    Fusiona múltiples entidades en una sola entidad principal.

    Args:
        project_id: ID del proyecto
        body: MergeEntitiesRequest con primary_entity_id y entity_ids

    Returns:
        ApiResponse con resultado de la fusión
    """
    try:
        primary_entity_id = body.primary_entity_id
        entity_ids = body.entity_ids

        entity_repo = deps.entity_repository

        # Verificar que la entidad principal existe
        primary_entity = entity_repo.get_entity(primary_entity_id)
        if not primary_entity or primary_entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad principal no encontrada")

        # Fase 1: Leer entidades fuente (no transaccional)
        source_entities = []
        combined_aliases = set(primary_entity.aliases)

        for entity_id in entity_ids:
            if entity_id == primary_entity_id:
                continue

            entity = entity_repo.get_entity(entity_id)
            if not entity or entity.project_id != project_id:
                continue

            source_entities.append(
                {
                    "id": entity_id,
                    "canonical_name": entity.canonical_name,
                    "entity_type": entity.entity_type.value,
                    "aliases": entity.aliases,
                    "mention_count": entity.mention_count,
                }
            )
            combined_aliases.add(entity.canonical_name)
            combined_aliases.update(entity.aliases)

        # Fase 2: Fusión atómica (todas las escrituras en una transacción)
        combined_aliases.discard(primary_entity.canonical_name)
        source_entity_ids = [e["id"] for e in source_entities]
        new_merged_ids = list(
            set(primary_entity.merged_from_ids + source_entity_ids)
        )
        total_mentions = sum(e.get("mention_count", 0) for e in source_entities)

        merged_count = entity_repo.merge_entities_atomic(
            project_id=project_id,
            primary_entity_id=primary_entity_id,
            source_entities=source_entities,
            combined_aliases=list(combined_aliases),
            new_merged_ids=new_merged_ids,
            total_mention_delta=total_mentions,
            merged_by="user",
        )

        # Apply attribute conflict resolutions
        resolutions_applied = 0
        if body.attribute_resolutions and merged_count > 0:
            attrs = entity_repo.get_attributes_by_entity(primary_entity_id)
            for resolution in body.attribute_resolutions:
                # Find all attributes with this key
                matching = [
                    a
                    for a in attrs
                    if a.get("attribute_key") == resolution.attribute_name
                ]
                if not matching:
                    continue

                # Keep one with the chosen value, delete the rest
                kept = False
                for attr in matching:
                    if (
                        attr.get("attribute_value") == resolution.chosen_value
                        and not kept
                    ):
                        kept = True
                        continue
                    # Delete duplicate/conflicting attribute
                    entity_repo.delete_attribute(attr["id"])
                    resolutions_applied += 1

                # If chosen value doesn't match any existing, update the first one
                if not kept and matching:
                    entity_repo.update_attribute(
                        attribute_id=matching[0]["id"],
                        attribute_value=resolution.chosen_value,
                        is_verified=True,
                    )
                    resolutions_applied += 1

            if resolutions_applied > 0:
                logger.info(
                    f"Applied {resolutions_applied} attribute resolutions for entity {primary_entity_id}"
                )

        logger.info(
            f"Merged {merged_count} entities into entity {primary_entity_id} ({primary_entity.canonical_name})"
        )

        # Obtener la entidad actualizada para retornarla
        updated_entity = entity_repo.get_entity(primary_entity_id)

        return ApiResponse(
            success=True,
            data={
                "primary_entity_id": primary_entity_id,
                "merged_count": merged_count,
                "merged_entity_ids": source_entity_ids,
                "result_entity": (
                    {
                        "id": updated_entity.id,
                        "canonical_name": updated_entity.canonical_name,
                        "aliases": updated_entity.aliases,
                        "mention_count": updated_entity.mention_count,
                        "merged_from_ids": updated_entity.merged_from_ids,
                    }
                    if updated_entity
                    else None
                ),
            },
            message=f"Se fusionaron {merged_count} entidades en '{primary_entity.canonical_name}'",
        )

    except Exception as e:
        logger.error(
            f"Error merging entities for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")
    else:
        # Invalidación granular (S8c) — best-effort, no bloquea respuesta
        try:
            from routers._invalidation import emit_invalidation_event

            all_ids = [body.primary_entity_id] + source_entity_ids
            emit_invalidation_event(deps.get_database(), project_id, "merge", all_ids)
        except Exception:
            pass


@router.get(
    "/api/projects/{project_id}/entities/merge-history", response_model=ApiResponse
)
def get_merge_history(project_id: int):
    """
    Obtiene el historial de fusiones de entidades del proyecto.

    Returns:
        ApiResponse con lista de fusiones realizadas
    """
    try:
        entity_repo = deps.entity_repository

        # Obtener historial de fusiones
        history = entity_repo.get_merge_history(project_id)

        return ApiResponse(
            success=True,
            data={"merges": [h.to_dict() for h in history], "total": len(history)},
        )

    except Exception as e:
        logger.error(f"Error getting merge history: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/entities/undo-merge/{merge_id}",
    response_model=ApiResponse,
)
def undo_entity_merge(project_id: int, merge_id: int):
    """
    Deshace una fusión de entidades via HistoryManager unificado.

    Restaura entidades originales, redistribuye menciones y atributos.

    Args:
        project_id: ID del proyecto
        merge_id: ID del registro de fusión a deshacer

    Returns:
        ApiResponse con resultado de la operación
    """
    try:
        from narrative_assistant.persistence.history import HistoryManager

        history = HistoryManager(project_id)
        result = history.undo(merge_id)

        if not result.success:
            return ApiResponse(
                success=False,
                error=result.message or "No se pudo deshacer la fusión",
                data={"conflicts": result.conflicts} if result.conflicts else None,
            )

        # Extraer source_entity_ids del entry para el frontend
        entry = history.get_entry(merge_id)
        restored_ids: list[int] = []
        if entry and entry.old_value:
            restored_ids = entry.old_value.get("source_entity_ids", [])

        # Invalidación granular (S8c)
        try:
            from routers._invalidation import emit_invalidation_event

            all_ids = restored_ids + ([entry.target_id] if entry and entry.target_id else [])
            emit_invalidation_event(
                deps.get_database(), project_id, "undo_merge", all_ids
            )
        except Exception:
            pass

        return ApiResponse(
            success=True,
            data={
                "restored_entity_ids": restored_ids,
                "entry_id": merge_id,
                "message": result.message,
            },
            message=result.message or "Fusión deshecha exitosamente",
        )

    except Exception as e:
        logger.error(f"Error undoing merge {merge_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/entities/{entity_id}", response_model=ApiResponse
)
def get_entity(project_id: int, entity_id: int):
    """
    Obtiene una entidad por su ID.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con los datos de la entidad
    """
    try:
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        # Calcular first_mention_chapter desde first_appearance_char
        first_mention_chapter = None
        if entity.first_appearance_char is not None:
            chapter_repo = get_chapter_repository()
            chapters = chapter_repo.get_by_project(project_id)
            for ch in chapters:
                if ch.start_char <= entity.first_appearance_char < ch.end_char:
                    first_mention_chapter = ch.chapter_number
                    break

        entity_data = EntityResponse(
            id=entity.id,
            project_id=entity.project_id,
            entity_type=entity.entity_type.value,
            canonical_name=entity.canonical_name,
            aliases=entity.aliases or [],
            importance=entity.importance.value,
            description=entity.description,
            first_appearance_char=entity.first_appearance_char,
            first_mention_chapter=first_mention_chapter,
            mention_count=entity.mention_count or 0,
            is_active=entity.is_active if hasattr(entity, "is_active") else True,
            merged_from_ids=entity.merged_from_ids or [],
            relevance_score=None,  # Calculate if needed
            created_at=(
                entity.created_at.isoformat()
                if hasattr(entity, "created_at") and entity.created_at
                else None
            ),
            updated_at=(
                entity.updated_at.isoformat()
                if hasattr(entity, "updated_at") and entity.updated_at
                else None
            ),
        )

        return ApiResponse(success=True, data=entity_data)

    except Exception as e:
        logger.error(f"Error getting entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.put(
    "/api/projects/{project_id}/entities/{entity_id}", response_model=ApiResponse
)
def update_entity(
    project_id: int, entity_id: int, body: deps.UpdateEntityRequest
):
    """
    Actualiza una entidad existente.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad a actualizar
        body: UpdateEntityRequest con campos a actualizar (name, canonical_name, importance, aliases, description)

    Returns:
        ApiResponse con la entidad actualizada
    """
    try:
        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        # Capturar valores anteriores para historial
        old_name = entity.canonical_name
        old_type = entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type)
        old_importance = entity.importance.value if hasattr(entity.importance, 'value') else str(entity.importance)

        # Mapear campos del request a parámetros del repositorio
        canonical_name = body.name or body.canonical_name
        aliases = body.aliases
        importance_str = body.importance
        description = body.description

        # Convertir importance string a enum si se proporciona
        importance = None
        if importance_str:
            from narrative_assistant.entities.models import EntityImportance

            importance_map = {
                "main": EntityImportance.MAIN,
                "secondary": EntityImportance.SECONDARY,
                "minor": EntityImportance.MINOR,
            }
            importance = importance_map.get(importance_str.lower())

        # Actualizar la entidad
        entity_repo = deps.entity_repository
        updated = entity_repo.update_entity(
            entity_id=entity_id,
            canonical_name=canonical_name,
            aliases=aliases,
            importance=importance,
            description=description,
        )

        if not updated:
            return ApiResponse(success=False, error="No se pudo actualizar la entidad")

        # Obtener la entidad actualizada
        updated_entity = entity_repo.get_entity(entity_id)

        logger.info(f"Updated entity {entity_id} ({updated_entity.canonical_name})")

        # Registrar en historial para undo
        try:
            from narrative_assistant.persistence.history import ChangeType, HistoryManager
            history = HistoryManager(project_id)
            history.record(
                action_type=ChangeType.ENTITY_UPDATED,
                target_type="entity",
                target_id=entity_id,
                old_value={
                    "canonical_name": old_name,
                    "entity_type": old_type,
                    "importance": old_importance,
                },
                new_value={
                    "canonical_name": updated_entity.canonical_name,
                    "entity_type": updated_entity.entity_type.value,
                    "importance": updated_entity.importance.value,
                },
                note=f"'{old_name}' editada",
            )
        except Exception:
            logger.debug("Could not log entity update to history", exc_info=True)

        return ApiResponse(
            success=True,
            data={
                "id": updated_entity.id,
                "canonical_name": updated_entity.canonical_name,
                "entity_type": updated_entity.entity_type.value,
                "importance": updated_entity.importance.value,
                "aliases": updated_entity.aliases,
                "description": updated_entity.description,
                "mention_count": updated_entity.mention_count,
            },
            message="Entidad actualizada correctamente",
        )

    except Exception as e:
        logger.error(f"Error updating entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete(
    "/api/projects/{project_id}/entities/{entity_id}", response_model=ApiResponse
)
def delete_entity(project_id: int, entity_id: int, hard_delete: bool = False):
    """
    Desactiva (soft-delete) una entidad.

    Siempre usa soft-delete para compatibilidad con undo/redo.
    El parámetro hard_delete se mantiene por compatibilidad pero se ignora.
    """
    try:
        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        entity_name = entity.canonical_name
        entity_type = getattr(entity, "entity_type", "")
        if hasattr(entity_type, "value"):
            entity_type = entity_type.value

        # Siempre soft-delete (undo-compatible)
        entity_repo = deps.entity_repository
        deleted = entity_repo.delete_entity(entity_id, hard_delete=False)

        if not deleted:
            return ApiResponse(success=False, error="No se pudo eliminar la entidad")

        # Registrar en historial para undo
        try:
            from narrative_assistant.persistence.history import ChangeType, HistoryManager
            history = HistoryManager(project_id)
            history.record(
                action_type=ChangeType.ENTITY_DELETED,
                target_type="entity",
                target_id=entity_id,
                old_value={
                    "canonical_name": entity_name,
                    "entity_type": entity_type,
                    "is_active": 1,
                },
                new_value={"is_active": 0},
                note=f"Entidad '{entity_name}' eliminada",
            )
        except Exception as hist_err:
            logger.warning(f"No se pudo registrar en historial: {hist_err}")

        logger.info(f"Entity {entity_id} ({entity_name}) desactivada")

        return ApiResponse(
            success=True,
            data={"id": entity_id, "name": entity_name, "action": "deleted"},
            message=f"Entidad '{entity_name}' eliminada",
        )

    except Exception as e:
        logger.error(f"Error deleting entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/entities/{entity_id}/timeline",
    response_model=ApiResponse,
)
def get_entity_timeline(project_id: int, entity_id: int):
    """
    Obtiene la línea temporal de una entidad basada en sus menciones.

    Agrupa las menciones por capítulo y genera eventos con:
    - Primera aparición en cada capítulo
    - Cambios de atributos detectados
    - Número de menciones por capítulo

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con timeline de eventos:
        - chapter: Número de capítulo
        - description: Descripción del evento
        - type: Tipo de evento (appearance, attribute_change, mention_count)
        - mentionCount: Número de menciones en ese capítulo
    """
    try:
        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        # Obtener menciones de la entidad
        entity_repo = deps.entity_repository
        mentions = entity_repo.get_mentions_by_entity(entity_id)

        if not mentions:
            return ApiResponse(success=True, data=[])

        # Obtener capítulos para mapear chapter_id a chapter_number
        chapters = (
            deps.chapter_repository.get_by_project(project_id)
            if deps.chapter_repository
            else []
        )
        chapter_map = {ch.id: ch for ch in chapters}

        # Agrupar menciones por capítulo
        mentions_by_chapter: dict[int, list] = {}
        for mention in mentions:
            ch_id = mention.chapter_id or 0
            if ch_id not in mentions_by_chapter:
                mentions_by_chapter[ch_id] = []
            mentions_by_chapter[ch_id].append(mention)

        # Obtener atributos para detectar cambios
        attributes = entity_repo.get_attributes_by_entity(entity_id)
        attrs_by_chapter: dict[int, list] = {}
        for attr in attributes:
            # Si el atributo tiene chapter_id o first_mention_chapter
            ch = (
                getattr(attr, "chapter_id", None)
                or getattr(attr, "first_mention_chapter", None)
                or 0
            )
            if ch not in attrs_by_chapter:
                attrs_by_chapter[ch] = []
            attrs_by_chapter[ch].append(attr)

        # Generar timeline.
        # Ordenamos por chapter_number narrativo (si existe) para que la
        # "primera aparición" sea coherente aunque los chapter_id no sean secuenciales.
        timeline_events = []
        sorted_chapters = sorted(
            mentions_by_chapter.keys(),
            key=lambda cid: (
                chapter_map[cid].chapter_number
                if cid in chapter_map and chapter_map[cid] is not None
                else cid
            ),
        )

        for idx, ch_id in enumerate(sorted_chapters):
            ch_mentions = mentions_by_chapter[ch_id]
            ch_info = chapter_map.get(ch_id)
            ch_number = ch_info.chapter_number if ch_info else ch_id
            ch_title = ch_info.title if ch_info else f"Capítulo {ch_number}"

            # Primera aparición
            if idx == 0:
                # Si hay posiciones, usar la mención más temprana del capítulo.
                # Evita depender del orden no determinista del repositorio.
                first_mention = sorted(
                    ch_mentions, key=lambda m: getattr(m, "start_char", 0)
                )[0]
                context = first_mention.context_before or ""
                context += f"**{first_mention.surface_form}**"
                context += first_mention.context_after or ""
                timeline_events.append(
                    {
                        "chapter": ch_number,
                        "chapterTitle": ch_title,
                        "description": f'Primera aparición: "{first_mention.surface_form}"',
                        "type": "first_appearance",
                        "mentionCount": len(ch_mentions),
                        "context": context[:200] if context else None,
                    }
                )
            else:
                # Aparición en capítulo posterior
                timeline_events.append(
                    {
                        "chapter": ch_number,
                        "chapterTitle": ch_title,
                        "description": f"{len(ch_mentions)} menciones en este capítulo",
                        "type": "appearance",
                        "mentionCount": len(ch_mentions),
                    }
                )

            # Atributos nuevos en este capítulo
            if ch_id in attrs_by_chapter or ch_number in attrs_by_chapter:
                ch_attrs = list(attrs_by_chapter.get(ch_id, []))
                # Evita duplicar el mismo lote cuando chapter_id == chapter_number.
                if ch_number != ch_id:
                    ch_attrs.extend(attrs_by_chapter.get(ch_number, []))
                for attr in ch_attrs:
                    attr_name = getattr(attr, "attribute_key", None) or getattr(
                        attr, "name", "atributo"
                    )
                    attr_value = getattr(attr, "attribute_value", None) or getattr(
                        attr, "value", ""
                    )
                    timeline_events.append(
                        {
                            "chapter": ch_number,
                            "chapterTitle": ch_title,
                            "description": f"Se menciona: {attr_name} = {attr_value}",
                            "type": "attribute",
                            "mentionCount": 0,
                        }
                    )

        # Ordenar por capítulo
        timeline_events.sort(
            key=lambda x: (x["chapter"], x["type"] != "first_appearance")
        )

        return ApiResponse(success=True, data=timeline_events)

    except Exception as e:
        logger.error(
            f"Error getting timeline for entity {entity_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/entities/{entity_id}/mentions",
    response_model=ApiResponse,
)
def get_entity_mentions(
    project_id: int,
    entity_id: int,
    chapter_number: Optional[int] = Query(
        None, description="Filtrar menciones por número de capítulo"
    ),
):
    """
    Obtiene todas las menciones de una entidad en el texto.

    Returns:
        Lista de menciones con posiciones, contexto y capítulo.
    """
    try:
        entity_repo = deps.entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener menciones de la entidad
        mentions = entity_repo.get_mentions_by_entity(entity_id)

        if not mentions:
            return ApiResponse(success=True, data={"mentions": [], "total": 0})

        # Obtener capítulos para mapear chapter_id a chapter_number y título
        chapters = (
            deps.chapter_repository.get_by_project(project_id)
            if deps.chapter_repository
            else []
        )
        chapter_map = {ch.id: ch for ch in chapters}

        # Si se filtra por capítulo, obtener el chapter_id correspondiente
        target_chapter_id: Optional[int] = None
        target_chapter_obj = None
        if chapter_number is not None:
            target_chapter_obj = next(
                (ch for ch in chapters if ch.chapter_number == chapter_number), None
            )
            if target_chapter_obj:
                target_chapter_id = target_chapter_obj.id

        # Serializar menciones con información de capítulo
        mentions_data = []
        for mention in mentions:
            ch_info = (
                chapter_map.get(mention.chapter_id) if mention.chapter_id else None
            )

            # Filtrar por capítulo si se especificó
            if chapter_number is not None:
                mention_in_chapter = False
                if target_chapter_id and mention.chapter_id == target_chapter_id:
                    mention_in_chapter = True
                elif target_chapter_obj and (
                    target_chapter_obj.start_char
                    <= mention.start_char
                    < target_chapter_obj.end_char
                ):
                    mention_in_chapter = True
                if not mention_in_chapter:
                    continue

            # Deserializar metadata usando property existente (Mejora 1)
            metadata = mention.metadata_dict or {}

            mentions_data.append(
                {
                    "id": mention.id,
                    "entityId": entity_id,
                    "surfaceForm": mention.surface_form,
                    "startChar": mention.start_char,
                    "endChar": mention.end_char,
                    "chapterId": mention.chapter_id,
                    "chapterNumber": ch_info.chapter_number if ch_info else None,
                    "chapterTitle": ch_info.title if ch_info else None,
                    "contextBefore": mention.context_before,
                    "contextAfter": mention.context_after,
                    "confidence": mention.confidence,
                    "source": mention.source,
                    # Campos de validación adaptativa (Mejora 1)
                    "validationMethod": metadata.get("validation_method"),
                    "validationReasoning": metadata.get("validation_reasoning"),
                }
            )

        # Ordenar por posición (start_char)
        mentions_data.sort(key=lambda m: (m["chapterNumber"] or 0, m["startChar"]))

        logger.info(
            f"Entity {entity_id} ({entity.canonical_name}): Found {len(mentions_data)} raw mentions from DB (entity.mention_count={entity.mention_count})"
        )

        # Log muestra de posiciones para debug
        if mentions_data:
            sample = mentions_data[:5]
            logger.info(
                f"Entity {entity_id}: Sample positions: {[(m['chapterId'], m['startChar'], m['endChar']) for m in sample]}"
            )

        # Filtrar duplicados: menciones que se solapan
        # Estrategia conservadora basada en discusión de expertos:
        # 1. Límites duros: puntuación indica que hemos ido demasiado lejos
        # 2. Artículo + sustantivo común no es parte del nombre
        # 3. Preferir nombre más largo SOLO si es estructura válida de nombre
        # 4. Preferir más larga solo si confianza >= 85% de la corta
        import re

        def has_invalid_extension(text: str) -> bool:
            """Detecta si el texto contiene patrones inválidos para un nombre."""
            # Puntuación que indica límite de nombre
            if re.search(r"[,;:\.\!\?]", text):
                return True
            # Artículo + sustantivo común (aposición)
            # "María la vecina", "Pedro el viejo"
            if re.search(r"\s+(el|la|los|las)\s+[a-záéíóúñ]+$", text, re.IGNORECASE):
                # Excepciones: partículas de apellido válidas
                valid_particles = ["de la", "del", "de los", "de las", "de"]
                text_lower = text.lower()
                if not any(
                    f" {p} " in text_lower or text_lower.endswith(f" {p}")
                    for p in valid_particles
                ):
                    return True
            return False

        def is_valid_name_extension(short_text: str, long_text: str) -> bool:
            """Verifica si la extensión del nombre corto al largo es válida."""
            extension = long_text[len(short_text) :].strip()
            if not extension:
                return True
            # Partículas de apellido válidas
            if re.match(r"^(de la|del|de los|de las|de)\s+[A-ZÁÉÍÓÚÑ]", extension):
                return True
            # Apellido simple (empieza con mayúscula, sin puntuación)
            if re.match(
                r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?$", extension
            ):
                return True
            return False

        filtered_mentions = []
        removed_count = 0

        def normalize_surface_form(text: str) -> str:
            """Normaliza texto para comparación (minúsculas, sin espacios extra)."""
            text = text.lower().strip()
            text = " ".join(text.split())  # Normalizar espacios
            return text

        def calculate_iou(start1: int, end1: int, start2: int, end2: int) -> float:
            """Calcula Intersection over Union de dos spans."""
            intersection_start = max(start1, start2)
            intersection_end = min(end1, end2)
            if intersection_end <= intersection_start:
                return 0.0
            intersection = intersection_end - intersection_start
            union = max(end1, end2) - min(start1, start2)
            return intersection / union if union > 0 else 0.0

        for mention in mentions_data:
            dominated = False
            to_remove = None

            for existing in filtered_mentions:
                # Verificar solapamiento de posiciones (INDEPENDIENTE del capítulo)
                # Menciones con misma posición pero diferente chapter_id son duplicados
                # debido a errores de asignación durante NER
                overlaps = not (
                    mention["endChar"] <= existing["startChar"]
                    or mention["startChar"] >= existing["endChar"]
                )

                # Calcular IoU para solapamientos parciales
                iou = calculate_iou(
                    mention["startChar"],
                    mention["endChar"],
                    existing["startChar"],
                    existing["endChar"],
                )

                # Si IoU > 70%, considerarlas como la misma mención (diferente chapter_id o no)
                high_overlap = iou > 0.7

                # Deduplicar menciones con mismo texto normalizado muy cercanas (< 10 chars)
                # Esto captura menciones duplicadas que no se solapan exactamente
                same_text = normalize_surface_form(
                    existing["surfaceForm"]
                ) == normalize_surface_form(mention["surfaceForm"])
                distance = min(
                    abs(mention["startChar"] - existing["endChar"]),
                    abs(existing["startChar"] - mention["endChar"]),
                )
                very_close = same_text and distance < 10

                if very_close and not overlaps:
                    # Son la misma mención con posiciones ligeramente diferentes
                    dominated = True
                    removed_count += 1
                    logger.debug(
                        f"Dedupe: '{mention['surfaceForm']}' muy cercana a '{existing['surfaceForm']}' (dist={distance})"
                    )
                    break

                # Si hay alto solapamiento (IoU > 70%), deduplicar aunque chapter_id difiera
                if high_overlap and not overlaps:
                    # IoU alto pero sin solapamiento exacto - preferir el de mayor confianza
                    if mention["confidence"] >= existing["confidence"]:
                        to_remove = existing
                    else:
                        dominated = True
                    removed_count += 1
                    logger.debug(
                        f"Dedupe IoU: '{mention['surfaceForm']}' vs '{existing['surfaceForm']}' (IoU={iou:.2f})"
                    )
                    break

                if overlaps or high_overlap:
                    # Determinar cuál es más larga y cuál más corta
                    if len(mention["surfaceForm"]) > len(existing["surfaceForm"]):
                        longer, shorter = mention, existing
                        longer_is_new = True
                    else:
                        longer, shorter = existing, mention
                        longer_is_new = False

                    # Mismo texto (ignorando mayúsculas) → duplicado exacto
                    if (
                        existing["surfaceForm"].lower()
                        == mention["surfaceForm"].lower()
                    ):
                        dominated = True
                        if mention["confidence"] > existing["confidence"]:
                            to_remove = existing
                        removed_count += 1
                        break

                    # Verificar si la extensión es válida
                    longer_has_invalid = has_invalid_extension(longer["surfaceForm"])
                    extension_valid = is_valid_name_extension(
                        shorter["surfaceForm"], longer["surfaceForm"]
                    )

                    # Si la larga tiene patrones inválidos → preferir corta
                    if longer_has_invalid or not extension_valid:
                        if longer_is_new:
                            dominated = True  # Descartar la nueva (larga)
                        else:
                            to_remove = existing  # Reemplazar existente (larga) por nueva (corta)
                        removed_count += 1
                        break

                    # La larga es válida → verificar confianza (85% threshold)
                    confidence_ok = longer["confidence"] >= shorter["confidence"] * 0.85
                    if confidence_ok:
                        # Preferir la más larga
                        if longer_is_new:
                            to_remove = existing
                        else:
                            dominated = True
                    else:
                        # Confianza insuficiente → preferir corta
                        if longer_is_new:
                            dominated = True
                        else:
                            to_remove = existing
                    removed_count += 1
                    break

            if to_remove:
                filtered_mentions.remove(to_remove)
                filtered_mentions.append(mention)
            elif not dominated:
                filtered_mentions.append(mention)

        # Re-ordenar después de filtrar
        filtered_mentions.sort(key=lambda m: (m["chapterNumber"] or 0, m["startChar"]))

        if removed_count > 0:
            logger.info(
                f"Entity {entity_id} ({entity.canonical_name}): Filtered {removed_count} overlapping mentions, returning {len(filtered_mentions)}"
            )

        return ApiResponse(
            success=True,
            data={
                "mentions": filtered_mentions,
                "total": len(filtered_mentions),
                "entityName": entity.canonical_name,
                "entityType": entity.entity_type.value if entity.entity_type else None,
                # Debug info
                "_debug": {
                    "raw_mentions_in_db": len(mentions),
                    "after_serialization": len(mentions_data),
                    "after_filtering": len(filtered_mentions),
                    "entity_mention_count_field": entity.mention_count,
                    "removed_duplicates": removed_count,
                },
            },
        )

    except Exception as e:
        logger.error(
            f"Error getting mentions for entity {entity_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/entities/{entity_id}/coreference",
    response_model=ApiResponse,
)
def get_entity_coreference_info(project_id: int, entity_id: int):
    """
    Obtiene información de correferencia para una entidad.

    Retorna datos sobre cómo se resolvieron las menciones de la entidad,
    incluyendo la contribución de cada método de detección.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con información de correferencia:
        - methodContributions: Contribución de cada método
        - mentionsByType: Menciones agrupadas por tipo
        - overallConfidence: Confianza promedio
        - totalMentions: Total de menciones
    """
    try:
        entity_repo = deps.entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener menciones de la entidad
        mentions = entity_repo.get_mentions_by_entity(entity_id)

        if not mentions:
            return ApiResponse(
                success=True,
                data={
                    "entityId": entity_id,
                    "entityName": entity.canonical_name,
                    "methodContributions": [],
                    "mentionsByType": {},
                    "overallConfidence": 0.0,
                    "totalMentions": 0,
                },
            )

        # Agrupar menciones por fuente/método de detección
        method_counts: dict[str, int] = {}
        type_mentions: dict[str, list] = {}
        total_confidence = 0.0
        confidence_count = 0

        # Mapeo de fuentes del backend a nombres legibles
        source_labels = {
            "ner": "NER (spaCy)",
            "spacy": "NER (spaCy)",
            "embeddings": "Embeddings",
            "llm": "LLM (Ollama)",
            "morpho": "Morfosintáctico",
            "heuristics": "Heurísticas",
            "coreference": "Correferencia",
            "coref": "Correferencia",
            "manual": "Manual",
            "fusion": "Fusión",
            "pronoun": "Pronombre resuelto",
        }

        # Lista de resoluciones con detalle de votación
        voting_reasoning: list[dict] = []

        for mention in mentions:
            source = mention.source or "unknown"
            source_lower = source.lower()

            # Contar por método
            method_counts[source_lower] = method_counts.get(source_lower, 0) + 1

            # Agrupar por tipo de mención (basado en el texto)
            surface = mention.surface_form or ""
            mention_type = _classify_mention_type(surface)

            if mention_type not in type_mentions:
                type_mentions[mention_type] = []
            type_mentions[mention_type].append(
                {
                    "text": surface,
                    "confidence": mention.confidence,
                    "source": source,
                }
            )

            # Sumar confianza para promedio
            if mention.confidence is not None:
                total_confidence += mention.confidence
                confidence_count += 1

            # Extraer detalle de votación de metadata (menciones con source='coref')
            if source_lower == "coref" and mention.metadata:
                try:
                    import json

                    meta = (
                        json.loads(mention.metadata)
                        if isinstance(mention.metadata, str)
                        else mention.metadata
                    )
                    if meta and "method_votes" in meta:
                        voting_reasoning.append(
                            {
                                "mentionText": meta.get("anaphor_text", surface),
                                "startChar": meta.get(
                                    "anaphor_start", mention.start_char
                                ),
                                "endChar": meta.get("anaphor_end", mention.end_char),
                                "resolvedTo": meta.get("resolved_to", ""),
                                "finalScore": meta.get(
                                    "final_score", mention.confidence
                                ),
                                "contextBefore": mention.context_before or "",
                                "contextAfter": mention.context_after or "",
                                "methodVotes": [
                                    {
                                        "method": method_name,
                                        "methodLabel": source_labels.get(
                                            method_name, method_name.capitalize()
                                        ),
                                        "score": vote_data.get("score", 0),
                                        "weight": vote_data.get("weight", 0),
                                        "weightedScore": vote_data.get(
                                            "weighted_score", 0
                                        ),
                                        "reasoning": vote_data.get("reasoning", ""),
                                    }
                                    for method_name, vote_data in meta[
                                        "method_votes"
                                    ].items()
                                ],
                            }
                        )
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

        # Calcular contribuciones con formato para MethodVotingBar
        total_mentions = len(mentions)
        method_contributions = []

        for source, count in sorted(method_counts.items(), key=lambda x: -x[1]):
            percentage = (count / total_mentions * 100) if total_mentions > 0 else 0
            method_contributions.append(
                {
                    "name": source_labels.get(source, source.capitalize()),
                    "method": source,
                    "count": count,
                    "score": percentage / 100,  # Normalizado 0-1 para MethodVotingBar
                    "agreed": percentage
                    >= 20,  # Consideramos "de acuerdo" si aporta >= 20%
                }
            )

        # Calcular confianza promedio
        overall_confidence = (
            (total_confidence / confidence_count) if confidence_count > 0 else 0.0
        )

        return ApiResponse(
            success=True,
            data={
                "entityId": entity_id,
                "entityName": entity.canonical_name,
                "methodContributions": method_contributions,
                "mentionsByType": type_mentions,
                "votingReasoning": voting_reasoning,
                "overallConfidence": overall_confidence,
                "totalMentions": total_mentions,
            },
        )

    except Exception as e:
        logger.error(
            f"Error getting coreference info for entity {entity_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/coreference-corrections", response_model=ApiResponse
)
def list_coreference_corrections(project_id: int):
    """Lista todas las correcciones manuales de correferencias de un proyecto."""
    try:
        db = deps.get_database()
        with db.connect() as conn:
            rows = conn.execute(
                """SELECT cc.id, cc.mention_start_char, cc.mention_end_char,
                          cc.mention_text, cc.chapter_number,
                          cc.original_entity_id, cc.corrected_entity_id,
                          cc.correction_type, cc.notes, cc.created_at,
                          e_orig.canonical_name AS original_entity_name,
                          e_corr.canonical_name AS corrected_entity_name
                   FROM coreference_corrections cc
                   LEFT JOIN entities e_orig ON cc.original_entity_id = e_orig.id
                   LEFT JOIN entities e_corr ON cc.corrected_entity_id = e_corr.id
                   WHERE cc.project_id = ?
                   ORDER BY cc.created_at DESC""",
                (project_id,),
            ).fetchall()

        corrections = []
        for row in rows:
            corrections.append(
                {
                    "id": row[0],
                    "mentionStartChar": row[1],
                    "mentionEndChar": row[2],
                    "mentionText": row[3],
                    "chapterNumber": row[4],
                    "originalEntityId": row[5],
                    "correctedEntityId": row[6],
                    "correctionType": row[7],
                    "notes": row[8],
                    "createdAt": row[9],
                    "originalEntityName": row[10],
                    "correctedEntityName": row[11],
                }
            )

        return ApiResponse(
            success=True,
            data={
                "projectId": project_id,
                "corrections": corrections,
                "totalCorrections": len(corrections),
            },
        )
    except Exception as e:
        logger.error(f"Error listing coreference corrections: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/coreference-corrections", response_model=ApiResponse
)
def create_coreference_correction(
    project_id: int, payload: deps.CoreferenceCorrectionRequest
):
    """
    Crea una corrección manual de correferencia.

    Body JSON:
    - mention_start_char: Posición inicio de la mención
    - mention_end_char: Posición fin de la mención
    - mention_text: Texto de la mención
    - chapter_number: Número de capítulo (opcional)
    - original_entity_id: Entidad asignada automáticamente (nullable)
    - corrected_entity_id: Entidad correcta según el usuario (nullable = desvincular)
    - correction_type: "reassign" | "unlink" | "confirm"
    - notes: Notas del corrector (opcional)
    """
    try:
        mention_start = payload.mention_start_char
        mention_end = payload.mention_end_char
        mention_text = payload.mention_text
        chapter_number = payload.chapter_number
        original_entity_id = payload.original_entity_id
        corrected_entity_id = payload.corrected_entity_id
        correction_type = payload.correction_type
        notes = payload.notes

        db = deps.get_database()
        with db.connect() as conn:
            # Verificar si ya existe corrección para esta mención
            existing = conn.execute(
                """SELECT id FROM coreference_corrections
                   WHERE project_id = ? AND mention_start_char = ? AND mention_end_char = ?""",
                (project_id, mention_start, mention_end),
            ).fetchone()

            if existing:
                # Actualizar corrección existente
                conn.execute(
                    """UPDATE coreference_corrections
                       SET corrected_entity_id = ?, correction_type = ?, notes = ?,
                           created_at = datetime('now')
                       WHERE id = ?""",
                    (corrected_entity_id, correction_type, notes, existing[0]),
                )
                correction_id = existing[0]
            else:
                # Crear nueva corrección
                cursor = conn.execute(
                    """INSERT INTO coreference_corrections
                       (project_id, mention_start_char, mention_end_char, mention_text,
                        chapter_number, original_entity_id, corrected_entity_id,
                        correction_type, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        project_id,
                        mention_start,
                        mention_end,
                        mention_text,
                        chapter_number,
                        original_entity_id,
                        corrected_entity_id,
                        correction_type,
                        notes,
                    ),
                )
                correction_id = cursor.lastrowid

            # Aplicar corrección: actualizar entity_mentions
            if correction_type == "reassign" and corrected_entity_id is not None:
                conn.execute(
                    """UPDATE entity_mentions
                       SET entity_id = ?
                       WHERE entity_id = ? AND start_char = ? AND end_char = ?""",
                    (
                        corrected_entity_id,
                        original_entity_id,
                        mention_start,
                        mention_end,
                    ),
                )
            elif correction_type == "unlink" and original_entity_id is not None:
                conn.execute(
                    """DELETE FROM entity_mentions
                       WHERE entity_id = ? AND start_char = ? AND end_char = ?""",
                    (original_entity_id, mention_start, mention_end),
                )

            conn.commit()

        return ApiResponse(
            success=True,
            data={
                "correctionId": correction_id,
                "correctionType": correction_type,
                "applied": True,
            },
        )
    except Exception as e:
        logger.error(f"Error creating coreference correction: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete(
    "/api/projects/{project_id}/coreference-corrections/{correction_id}",
    response_model=ApiResponse,
)
def delete_coreference_correction(project_id: int, correction_id: int):
    """Elimina una corrección manual de correferencia."""
    try:
        db = deps.get_database()
        with db.connect() as conn:
            # Obtener la corrección antes de eliminar
            row = conn.execute(
                """SELECT original_entity_id, corrected_entity_id, mention_start_char,
                          mention_end_char, correction_type
                   FROM coreference_corrections
                   WHERE id = ? AND project_id = ?""",
                (correction_id, project_id),
            ).fetchone()

            if not row:
                return ApiResponse(success=False, error="Corrección no encontrada")

            original_id, corrected_id, start_char, end_char, corr_type = row

            # Revertir: si fue reassign, restaurar entity_id original
            if (
                corr_type == "reassign"
                and original_id is not None
                and corrected_id is not None
            ):
                conn.execute(
                    """UPDATE entity_mentions
                       SET entity_id = ?
                       WHERE entity_id = ? AND start_char = ? AND end_char = ?""",
                    (original_id, corrected_id, start_char, end_char),
                )

            conn.execute(
                "DELETE FROM coreference_corrections WHERE id = ? AND project_id = ?",
                (correction_id, project_id),
            )
            conn.commit()

        return ApiResponse(success=True, data={"deleted": True, "reverted": True})
    except Exception as e:
        logger.error(f"Error deleting coreference correction: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/entities/rejected", response_model=ApiResponse)
def list_rejected_entities(project_id: int):
    """
    Lista las entidades rechazadas por el usuario para un proyecto.

    Las entidades rechazadas no se volverán a detectar en futuros análisis.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de entidades rechazadas
    """
    try:

        db = deps.get_database()
        rows = db.fetchall(
            """
            SELECT id, entity_text, rejection_reason, created_at
            FROM rejected_entities
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            (project_id,),
        )

        rejected = [
            {
                "id": row["id"],
                "text": row["entity_text"],
                "reason": row["rejection_reason"],
                "rejectedAt": row["created_at"],
            }
            for row in rows
        ]

        return ApiResponse(success=True, data=rejected)

    except Exception as e:
        logger.error(
            f"Error listing rejected entities for project {project_id}: {e}",
            exc_info=True,
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/entities/{entity_id}/reject", response_model=ApiResponse)
def reject_entity_by_id(project_id: int, entity_id: int, body: dict | None = None):
    """
    Rechaza una entidad por su ID.

    Busca la entidad, obtiene su texto canónico y la rechaza
    para que no se vuelva a detectar en futuros análisis.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        body: Opcional, con campo 'reason'
    """
    if body is None:
        body = {}
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.nlp.entity_validator import get_entity_validator

        entity_repo = get_entity_repository()
        entity = entity_repo.get_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail="Entidad no encontrada")

        if entity.project_id != project_id:
            raise HTTPException(status_code=404, detail="Entidad no encontrada")

        entity_text = entity.canonical_name
        reason = body.get("reason", "") if isinstance(body, dict) else ""

        validator = get_entity_validator(db=deps.get_database())
        success = validator.reject_entity(project_id, entity_text)

        if success:
            if reason:
                db = deps.get_database()
                db.execute(
                    """
                    UPDATE rejected_entities
                    SET rejection_reason = ?
                    WHERE project_id = ? AND entity_text = ?
                    """,
                    (reason, project_id, entity_text.lower().strip()),
                )

            try:
                from routers._invalidation import emit_invalidation_event

                emit_invalidation_event(
                    deps.get_database(),
                    project_id,
                    "reject",
                    [],
                    detail={"entity_text": entity_text, "entity_id": entity_id},
                )
            except Exception:
                pass

            return ApiResponse(
                success=True,
                data={"message": f"Entidad '{entity_text}' rechazada correctamente"},
            )
        else:
            return ApiResponse(success=False, error="Error al rechazar entidad")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error rejecting entity {entity_id} for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/entities/reject", response_model=ApiResponse)
def reject_entity_text(project_id: int, body: deps.RejectEntityRequest):
    """
    Rechaza un texto de entidad para que no se vuelva a detectar.

    El texto rechazado se guarda normalizado (lowercase) y se aplicará
    en futuros análisis NER del proyecto.

    Args:
        project_id: ID del proyecto
        body: RejectEntityRequest con entity_text (texto a rechazar) y reason (opcional)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.nlp.entity_validator import get_entity_validator

        entity_text = body.entity_text.strip()
        reason = body.reason

        # Usar el validador para rechazar la entidad
        validator = get_entity_validator(db=deps.get_database())
        success = validator.reject_entity(project_id, entity_text)

        if success:
            # Guardar razón si se proporcionó
            if reason:
                db = deps.get_database()
                db.execute(
                    """
                    UPDATE rejected_entities
                    SET rejection_reason = ?
                    WHERE project_id = ? AND entity_text = ?
                    """,
                    (reason, project_id, entity_text.lower().strip()),
                )

            # Invalidación granular (S8c)
            try:
                from routers._invalidation import emit_invalidation_event

                emit_invalidation_event(
                    deps.get_database(),
                    project_id,
                    "reject",
                    [],
                    detail={"entity_text": entity_text},
                )
            except Exception:
                pass

            return ApiResponse(
                success=True,
                data={"message": f"Entidad '{entity_text}' rechazada correctamente"},
            )
        else:
            return ApiResponse(success=False, error="Error al rechazar entidad")

    except Exception as e:
        logger.error(
            f"Error rejecting entity for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete(
    "/api/projects/{project_id}/entities/reject/{entity_text}",
    response_model=ApiResponse,
)
def unreject_entity_text(project_id: int, entity_text: str):
    """
    Quita un texto de entidad de la lista de rechazadas.

    La entidad podrá volver a detectarse en futuros análisis.

    Args:
        project_id: ID del proyecto
        entity_text: Texto de la entidad a des-rechazar (URL encoded)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.nlp.entity_validator import get_entity_validator

        if not entity_text:
            return ApiResponse(success=False, error="entity_text es requerido")

        # Usar el validador para des-rechazar la entidad
        validator = get_entity_validator(db=deps.get_database())
        success = validator.unreject_entity(project_id, entity_text)

        if success:
            return ApiResponse(
                success=True,
                data={"message": f"Entidad '{entity_text}' restaurada correctamente"},
            )
        else:
            return ApiResponse(
                success=False, error="Entidad no encontrada en lista de rechazadas"
            )

    except Exception as e:
        logger.error(
            f"Error unrejecting entity for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/entity-filters/stats", response_model=ApiResponse)
def get_filter_stats(project_id: Optional[int] = None):
    """
    Obtiene estadísticas del sistema de filtros de entidades.

    Args:
        project_id: ID del proyecto (opcional, para stats por proyecto)

    Returns:
        ApiResponse con estadísticas de filtros
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        stats = repo.get_filter_stats(project_id)

        return ApiResponse(success=True, data=stats)

    except Exception as e:
        logger.error(f"Error getting filter stats: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/entity-filters/system-patterns", response_model=ApiResponse)
def list_system_patterns(language: str = "es", only_active: bool = False):
    """
    Lista los patrones de falsos positivos del sistema.

    Estos son patrones predefinidos para filtrar expresiones comunes
    que no son entidades (artículos, marcadores temporales, etc.).

    Args:
        language: Idioma (default: "es")
        only_active: Si True, solo retorna patrones activos

    Returns:
        ApiResponse con lista de patrones del sistema
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        patterns = repo.get_system_patterns(language, only_active)

        # Agrupar por categoría para la UI
        by_category: dict = {}
        for pattern in patterns:
            cat = pattern.category or "other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(
                {
                    "id": pattern.id,
                    "pattern": pattern.pattern,
                    "patternType": pattern.pattern_type.value,
                    "entityType": pattern.entity_type,
                    "description": pattern.description,
                    "isActive": pattern.is_active,
                }
            )

        return ApiResponse(
            success=True,
            data={
                "patterns": [
                    {
                        "id": p.id,
                        "pattern": p.pattern,
                        "patternType": p.pattern_type.value,
                        "entityType": p.entity_type,
                        "category": p.category,
                        "description": p.description,
                        "isActive": p.is_active,
                    }
                    for p in patterns
                ],
                "byCategory": by_category,
                "totalCount": len(patterns),
                "activeCount": sum(1 for p in patterns if p.is_active),
            },
        )

    except Exception as e:
        logger.error(f"Error listing system patterns: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.patch(
    "/api/entity-filters/system-patterns/{pattern_id}", response_model=ApiResponse
)
def toggle_system_pattern(pattern_id: int, body: deps.TogglePatternRequest):
    """
    Activa o desactiva un patrón del sistema.

    Args:
        pattern_id: ID del patrón
        body: TogglePatternRequest con is_active (bool)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        is_active = body.is_active

        repo = get_filter_repository()
        success = repo.toggle_system_pattern(pattern_id, is_active)

        if success:
            return ApiResponse(
                success=True,
                data={
                    "message": f"Patrón {'activado' if is_active else 'desactivado'} correctamente"
                },
            )
        else:
            return ApiResponse(success=False, error="Patrón no encontrado")

    except Exception as e:
        logger.error(f"Error toggling system pattern {pattern_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/entity-filters/user-rejections", response_model=ApiResponse)
def list_user_rejections():
    """
    Lista los rechazos globales del usuario.

    Estas son entidades que el usuario ha rechazado y que se filtrarán
    en todos sus proyectos.

    Returns:
        ApiResponse con lista de rechazos globales
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        rejections = repo.get_user_rejections()

        return ApiResponse(
            success=True,
            data=[
                {
                    "id": r.id,
                    "entityName": r.entity_name,
                    "entityType": r.entity_type,
                    "reason": r.reason,
                    "rejectedAt": r.rejected_at,
                }
                for r in rejections
            ],
        )

    except Exception as e:
        logger.error(f"Error listing user rejections: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/entity-filters/user-rejections", response_model=ApiResponse)
def add_user_rejection(body: deps.UserRejectionRequest):
    """
    Añade un rechazo global del usuario.

    La entidad se filtrará en todos los proyectos del usuario.

    Args:
        body: UserRejectionRequest con entity_name, entity_type (opcional), reason (opcional)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        entity_name = body.entity_name.strip()
        entity_type = body.entity_type
        reason = body.reason

        repo = get_filter_repository()
        rejection_id = repo.add_user_rejection(entity_name, entity_type, reason)

        return ApiResponse(
            success=True,
            data={
                "id": rejection_id,
                "message": f"Entidad '{entity_name}' añadida a filtros globales",
            },
        )

    except Exception as e:
        logger.error(f"Error adding user rejection: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete(
    "/api/entity-filters/user-rejections/{rejection_id}", response_model=ApiResponse
)
def remove_user_rejection(rejection_id: int):
    """
    Elimina un rechazo global del usuario.

    La entidad podrá volver a detectarse en todos los proyectos.

    Args:
        rejection_id: ID del rechazo a eliminar

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        # Primero obtener el nombre de la entidad
        db = deps.get_database()
        row = db.fetchone(
            "SELECT entity_name, entity_type FROM user_rejected_entities WHERE id = ?",
            (rejection_id,),
        )

        if not row:
            return ApiResponse(success=False, error="Rechazo no encontrado")

        repo = get_filter_repository()
        success = repo.remove_user_rejection(row["entity_name"], row["entity_type"])

        if success:
            return ApiResponse(
                success=True, data={"message": "Rechazo eliminado correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Error eliminando rechazo")

    except Exception as e:
        logger.error(
            f"Error removing user rejection {rejection_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/entity-filters/overrides", response_model=ApiResponse
)
def list_project_overrides(project_id: int):
    """
    Lista los overrides de entidades de un proyecto.

    Estos son ajustes específicos del proyecto que tienen la máxima prioridad:
    - force_include: Fuerza que una entidad se incluya aunque esté filtrada globalmente
    - reject: Rechaza una entidad solo en este proyecto

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de overrides
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        overrides = repo.get_project_overrides(project_id)

        return ApiResponse(
            success=True,
            data=[
                {
                    "id": o.id,
                    "entityName": o.entity_name,
                    "entityType": o.entity_type,
                    "action": o.action.value,
                    "reason": o.reason,
                    "createdAt": o.created_at,
                }
                for o in overrides
            ],
        )

    except Exception as e:
        logger.error(
            f"Error listing project overrides for {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/entity-filters/overrides", response_model=ApiResponse
)
def add_project_override(project_id: int, body: deps.ProjectOverrideRequest):
    """
    Añade un override de entidad para un proyecto.

    Args:
        project_id: ID del proyecto
        body: ProjectOverrideRequest con entity_name, action ('reject' o 'force_include'),
              entity_type (opcional), reason (opcional)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import FilterAction, get_filter_repository

        entity_name = body.entity_name.strip()
        action = body.action
        entity_type = body.entity_type
        reason = body.reason

        repo = get_filter_repository()
        override_id = repo.add_project_override(
            project_id=project_id,
            entity_name=entity_name,
            action=FilterAction(action),
            entity_type=entity_type,
            reason=reason,
        )

        action_text = (
            "rechazada en este proyecto" if action == "reject" else "forzada a incluir"
        )
        return ApiResponse(
            success=True,
            data={
                "id": override_id,
                "message": f"Entidad '{entity_name}' {action_text}",
            },
        )

    except Exception as e:
        logger.error(
            f"Error adding project override for {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete(
    "/api/projects/{project_id}/entity-filters/overrides/{override_id}",
    response_model=ApiResponse,
)
def remove_project_override(project_id: int, override_id: int):
    """
    Elimina un override de entidad de un proyecto.

    Args:
        project_id: ID del proyecto
        override_id: ID del override a eliminar

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        # Primero obtener el nombre de la entidad
        db = deps.get_database()
        row = db.fetchone(
            """SELECT entity_name, entity_type FROM project_entity_overrides
               WHERE id = ? AND project_id = ?""",
            (override_id, project_id),
        )

        if not row:
            return ApiResponse(success=False, error="Override no encontrado")

        repo = get_filter_repository()
        success = repo.remove_project_override(
            project_id, row["entity_name"], row["entity_type"]
        )

        if success:
            return ApiResponse(
                success=True, data={"message": "Override eliminado correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Error eliminando override")

    except Exception as e:
        logger.error(
            f"Error removing project override {override_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/entity-filters/check", response_model=ApiResponse)
def check_entity_filter(body: deps.CheckFilterRequest):
    """
    Verifica si una entidad sería filtrada por el sistema.

    Útil para debug y para mostrar al usuario por qué una entidad
    no aparece en los resultados.

    Args:
        body: CheckFilterRequest con entity_name, entity_type (opcional), project_id (opcional)

    Returns:
        ApiResponse con resultado de la evaluación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        entity_name = body.entity_name.strip()
        entity_type = body.entity_type
        project_id = body.project_id

        repo = get_filter_repository()
        decision = repo.should_filter_entity(entity_name, entity_type, project_id)

        return ApiResponse(
            success=True,
            data={
                "shouldFilter": decision.should_filter,
                "reason": decision.reason,
                "level": decision.level,
                "ruleId": decision.rule_id,
            },
        )

    except Exception as e:
        logger.error(f"Error checking entity filter: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/entities/{entity_id}/attributes",
    response_model=ApiResponse,
)
def list_entity_attributes(project_id: int, entity_id: int):
    """
    Lista todos los atributos de una entidad.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con lista de atributos
    """
    try:
        entity_repo = deps.entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener atributos
        attributes = entity_repo.get_attributes_by_entity(entity_id)

        return ApiResponse(success=True, data=attributes)

    except Exception as e:
        logger.error(
            f"Error listing attributes for entity {entity_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/entities/{entity_id}/attributes",
    response_model=ApiResponse,
)
def create_entity_attribute(
    project_id: int, entity_id: int, body: deps.CreateAttributeRequest
):
    """
    Crea un nuevo atributo para una entidad.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        body: CreateAttributeRequest con category, name, value

    Returns:
        ApiResponse con el atributo creado
    """
    try:
        entity_repo = deps.entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Extraer datos del request
        category = body.category
        name = body.name
        value = body.value
        confidence = body.confidence

        entity_type = (
            entity.entity_type.value
            if hasattr(entity, "entity_type") and hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
            if hasattr(entity, "entity_type")
            else None
        )
        if not deps.is_valid_attribute_category(entity_type, category):
            allowed = sorted(deps.get_allowed_attribute_categories(entity_type))
            return ApiResponse(
                success=False,
                error=(
                    f"Categoría '{category}' no permitida para tipo '{entity_type}'. "
                    f"Permitidas: {', '.join(allowed)}"
                ),
            )

        # Crear atributo
        attribute_id = entity_repo.create_attribute(
            entity_id=entity_id,
            attribute_type=category,
            attribute_key=name,
            attribute_value=value,
            confidence=confidence,
        )

        logger.info(
            f"Created attribute {attribute_id} for entity {entity_id}: {name}={value}"
        )

        # Registrar en historial para undo
        try:
            from narrative_assistant.persistence.history import ChangeType, HistoryManager
            history = HistoryManager(project_id)
            history.record(
                action_type=ChangeType.ATTRIBUTE_ADDED,
                target_type="attribute",
                target_id=attribute_id,
                old_value=None,
                new_value={
                    "entity_id": entity_id,
                    "category": category,
                    "name": name,
                    "value": value,
                    "confidence": confidence,
                },
                note=f"{entity.canonical_name}: {name} = {value}",
            )
        except Exception:
            logger.debug("Could not log attribute create to history", exc_info=True)

        # Invalidación granular (S8c)
        try:
            from routers._invalidation import emit_invalidation_event

            emit_invalidation_event(
                deps.get_database(),
                project_id,
                "attribute_create",
                [entity_id],
                detail={"attribute": name, "value": value},
            )
        except Exception:
            pass

        return ApiResponse(
            success=True,
            data={
                "id": attribute_id,
                "entity_id": entity_id,
                "category": category,
                "name": name,
                "value": value,
                "confidence": confidence,
            },
            message="Atributo creado correctamente",
        )

    except Exception as e:
        logger.error(
            f"Error creating attribute for entity {entity_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.put(
    "/api/projects/{project_id}/entities/{entity_id}/attributes/{attribute_id}",
    response_model=ApiResponse,
)
def update_entity_attribute(
    project_id: int,
    entity_id: int,
    attribute_id: int,
    body: deps.UpdateAttributeRequest,
):
    """
    Actualiza un atributo existente.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        attribute_id: ID del atributo
        body: UpdateAttributeRequest con name, value, is_verified

    Returns:
        ApiResponse con el atributo actualizado
    """
    try:
        entity_repo = deps.entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Capturar valor anterior para historial
        old_attrs = entity_repo.get_attributes_by_entity(entity_id)
        old_attr = next((a for a in old_attrs if a["id"] == attribute_id), None)

        # Actualizar atributo
        updated = entity_repo.update_attribute(
            attribute_id=attribute_id,
            attribute_key=body.name,
            attribute_value=body.value,
            is_verified=body.is_verified,
        )

        if not updated:
            return ApiResponse(success=False, error="No se pudo actualizar el atributo")

        logger.info(f"Updated attribute {attribute_id} for entity {entity_id}")

        # Registrar en historial para undo
        try:
            from narrative_assistant.persistence.history import ChangeType, HistoryManager
            change_type = (
                ChangeType.ATTRIBUTE_VERIFIED
                if body.is_verified is not None and old_attr and not old_attr.get("is_verified")
                else ChangeType.ATTRIBUTE_UPDATED
            )
            history = HistoryManager(project_id)
            history.record(
                action_type=change_type,
                target_type="attribute",
                target_id=attribute_id,
                old_value={
                    "entity_id": entity_id,
                    "name": old_attr["name"] if old_attr else None,
                    "value": old_attr["value"] if old_attr else None,
                    "is_verified": old_attr.get("is_verified", False) if old_attr else False,
                },
                new_value={
                    "entity_id": entity_id,
                    "name": body.name,
                    "value": body.value,
                    "is_verified": body.is_verified,
                },
                note=f"{entity.canonical_name}: {body.name}",
            )
        except Exception:
            logger.debug("Could not log attribute update to history", exc_info=True)

        # Invalidación granular (S8c)
        try:
            from routers._invalidation import emit_invalidation_event

            emit_invalidation_event(
                deps.get_database(),
                project_id,
                "attribute_edit",
                [entity_id],
                detail={"attribute_id": attribute_id},
            )
        except Exception:
            pass

        return ApiResponse(
            success=True,
            data={"id": attribute_id},
            message="Atributo actualizado correctamente",
        )

    except Exception as e:
        logger.error(f"Error updating attribute {attribute_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete(
    "/api/projects/{project_id}/entities/{entity_id}/attributes/{attribute_id}",
    response_model=ApiResponse,
)
def delete_entity_attribute(project_id: int, entity_id: int, attribute_id: int):
    """
    Elimina un atributo.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        attribute_id: ID del atributo

    Returns:
        ApiResponse con resultado de la eliminación
    """
    try:
        entity_repo = deps.entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Capturar valor anterior para historial
        old_attrs = entity_repo.get_attributes_by_entity(entity_id)
        old_attr = next((a for a in old_attrs if a["id"] == attribute_id), None)

        # Eliminar atributo
        deleted = entity_repo.delete_attribute(attribute_id)

        if not deleted:
            return ApiResponse(success=False, error="No se pudo eliminar el atributo")

        logger.info(f"Deleted attribute {attribute_id} from entity {entity_id}")

        # Registrar en historial para undo
        if old_attr:
            try:
                from narrative_assistant.persistence.history import ChangeType, HistoryManager
                history = HistoryManager(project_id)
                history.record(
                    action_type=ChangeType.ATTRIBUTE_DELETED,
                    target_type="attribute",
                    target_id=attribute_id,
                    old_value={
                        "entity_id": entity_id,
                        "category": old_attr["category"],
                        "name": old_attr["name"],
                        "value": old_attr["value"],
                        "confidence": old_attr.get("confidence"),
                        "is_verified": old_attr.get("is_verified", False),
                    },
                    new_value=None,
                    note=f"{entity.canonical_name}: {old_attr['name']} eliminado",
                )
            except Exception:
                logger.debug("Could not log attribute delete to history", exc_info=True)

        # Invalidación granular (S8c)
        try:
            from routers._invalidation import emit_invalidation_event

            emit_invalidation_event(
                deps.get_database(),
                project_id,
                "attribute_delete",
                [entity_id],
                detail={"attribute_id": attribute_id},
            )
        except Exception:
            pass

        return ApiResponse(
            success=True,
            data={"id": attribute_id},
            message="Atributo eliminado correctamente",
        )

    except Exception as e:
        logger.error(f"Error deleting attribute {attribute_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")
