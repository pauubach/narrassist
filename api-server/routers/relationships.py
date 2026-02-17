"""
Router: relationships
"""

from typing import Optional

import deps
from deps import ApiResponse, convert_numpy_types, logger
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

@router.get("/api/projects/{project_id}/relationships", response_model=ApiResponse)
def get_project_relationships(project_id: int):
    """
    Obtiene análisis de relaciones entre personajes de un proyecto.

    Incluye:
    - Relaciones inferidas (co-ocurrencia, clustering)
    - Clusters de personajes
    - Menciones dirigidas (quién habla de quién)
    - Opiniones detectadas
    - Asimetrías de conocimiento

    Returns:
        ApiResponse con datos de relaciones
    """
    logger.info(f"[RELATIONSHIPS-API] Solicitando relaciones para proyecto {project_id}")

    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "character_network", allow_stale=True)  # type: ignore[misc]
    if cached:
        # Transform cached CharacterNetworkReport format (nodes/edges)
        # to the frontend-expected format (entities/relations)
        if "nodes" in cached and "entities" not in cached:
            cached["entities"] = [
                {
                    "id": n.get("entity_id"),
                    "name": n.get("entity_name", ""),
                    "type": "character",
                    "importance": 1,
                    "mentionCount": 0,
                }
                for n in cached.get("nodes", [])
            ]
            cached["relations"] = [
                {
                    "entity1_id": e.get("source"),
                    "entity2_id": e.get("target"),
                    "entity1_name": e.get("source_name", ""),
                    "entity2_name": e.get("target_name", ""),
                    "co_occurrences": e.get("interactions", 1),
                    "confidence": min(1.0, e.get("weight", 0.5)),
                    "chapters": e.get("chapters", []),
                    "contexts": [],
                }
                for e in cached.get("edges", [])
            ]
            cached.setdefault("project_id", project_id)
            cached.setdefault("entity_count", len(cached["entities"]))
            cached.setdefault("clusters", [])
            cached.setdefault("mentions", [])
            cached.setdefault("opinions", [])
            cached.setdefault("asymmetries", [])
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.analysis import (
            CharacterKnowledgeAnalyzer,
            RelationshipClusteringEngine,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar que el proyecto existe
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        _ = result.value

        # Obtener entidades del proyecto
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        logger.info(f"[RELATIONSHIPS-API] Entidades encontradas: {len(entities) if entities else 0}")

        if not entities:
            logger.warning(f"[RELATIONSHIPS-API] Proyecto {project_id} sin entidades")
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "entity_count": 0,
                    "entities": [],
                    "relations": [],
                    "clusters": [],
                    "mentions": [],
                    "opinions": [],
                    "asymmetries": [],
                    "message": "No hay entidades para analizar relaciones"
                }
            )

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        logger.info(f"[RELATIONSHIPS-API] Capítulos encontrados: {len(chapters) if chapters else 0}")

        # Obtener menciones de entidades — query batch con JOIN (evita N+1)
        all_mentions = entity_repo.get_mentions_by_project(project_id)
        logger.info(f"[RELATIONSHIPS-API] Menciones totales: {len(all_mentions)}")

        # 1. Análisis de clustering/relaciones
        clustering_engine = RelationshipClusteringEngine(use_embeddings=False)

        # Ajustar umbrales según tamaño del documento
        # Para documentos pequeños (<10k palabras), ser más permisivo
        # Para documentos grandes (>50k palabras), ser más estricto
        total_mentions = len(all_mentions)
        total_chars = sum(len(c.content) for c in chapters)

        if total_mentions < 20 or total_chars < 20000:
            # Documento pequeño: umbral mínimo de 1 co-ocurrencia
            clustering_engine.COOCCURRENCE_THRESHOLD = 1
            clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.2
        elif total_mentions < 100 or total_chars < 100000:
            # Documento mediano
            clustering_engine.COOCCURRENCE_THRESHOLD = 2
            clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.3
        else:
            # Documento grande
            clustering_engine.COOCCURRENCE_THRESHOLD = 3
            clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.4

        # Extraer co-ocurrencias de menciones
        chapters_data = [
            {
                "id": c.id,  # ID de BD para mapear menciones
                "chapter_number": c.chapter_number,
                "start_char": c.start_char,
                "end_char": c.end_char,
                "content": c.content,
            }
            for c in chapters
        ]

        # Crear mapeo de chapter_id (BD) a chapter_number
        chapter_id_to_number = {c["id"]: c["chapter_number"] for c in chapters_data}

        # Agrupar menciones por capítulo y buscar co-ocurrencias
        mentions_by_chapter = {}
        unmatched_mentions = 0
        for m in all_mentions:
            # Usar chapter_id de la mención (más fiable que buscar por posición)
            ch_id = m.get("chapter_id")
            ch_num = chapter_id_to_number.get(ch_id)

            if ch_num is None:
                # Fallback: buscar por posición si chapter_id no está o no existe
                for ch in chapters_data:
                    if ch["start_char"] <= m["start_char"] <= ch["end_char"]:
                        ch_num = ch["chapter_number"]
                        break

            if ch_num is not None:
                if ch_num not in mentions_by_chapter:
                    mentions_by_chapter[ch_num] = []
                mentions_by_chapter[ch_num].append(m)
            else:
                unmatched_mentions += 1

        if unmatched_mentions > 0:
            logger.warning(f"[RELATIONSHIPS-API] {unmatched_mentions} menciones no coinciden con ningún capítulo")

        # Detectar co-ocurrencias (menciones cercanas)
        WINDOW = 500  # caracteres
        cooccurrence_count = 0
        logger.info(f"[RELATIONSHIPS-API] Capítulos con menciones: {len(mentions_by_chapter)}")

        # Crear lookup de chapter_number a chapter_data
        chapter_by_number = {c["chapter_number"]: c for c in chapters_data}

        for ch_num, ch_mentions in mentions_by_chapter.items():
            logger.debug(f"[RELATIONSHIPS-API] Capítulo {ch_num}: {len(ch_mentions)} menciones")
            ch_mentions.sort(key=lambda x: x["start_char"])

            # Obtener datos del capítulo
            chapter_data = chapter_by_number.get(ch_num, {})
            chapter_content = chapter_data.get("content", "")
            chapter_start = chapter_data.get("start_char", 0)  # Offset del capítulo

            for i, m1 in enumerate(ch_mentions):
                for m2 in ch_mentions[i+1:]:
                    if m1["entity_id"] == m2["entity_id"]:
                        continue

                    distance = m2["start_char"] - m1["end_char"]
                    if distance > WINDOW:
                        break

                    # Extraer contexto usando posiciones relativas al capítulo
                    # Las menciones tienen posiciones absolutas, convertir a relativas
                    rel_start = m1["start_char"] - chapter_start
                    rel_end = m2["end_char"] - chapter_start

                    context_start = max(0, rel_start - 50)
                    context_end = min(len(chapter_content), rel_end + 50)
                    context = chapter_content[context_start:context_end] if chapter_content and context_end > context_start else ""

                    clustering_engine.add_cooccurrence(
                        entity1_id=m1["entity_id"],
                        entity2_id=m2["entity_id"],
                        entity1_name=m1["entity_name"],
                        entity2_name=m2["entity_name"],
                        chapter=ch_num,
                        distance_chars=distance,
                        context=context[:200],  # Limitar contexto
                    )
                    cooccurrence_count += 1

        logger.info(f"[RELATIONSHIPS-API] Co-ocurrencias detectadas: {cooccurrence_count}")

        # Ejecutar análisis de clustering
        clustering_result = clustering_engine.analyze()

        # 2. Análisis de conocimiento/opiniones
        knowledge_analyzer = CharacterKnowledgeAnalyzer(project_id=project_id)

        # Registrar entidades
        for entity in entities:
            knowledge_analyzer.register_entity(
                entity_id=entity.id,
                name=entity.canonical_name,
                aliases=entity.aliases,
            )

        # Analizar contenido de capítulos
        for chapter in chapters:
            # Analizar narración
            knowledge_analyzer.analyze_narration(
                text=chapter.content,
                chapter=chapter.chapter_number,
                start_char=chapter.start_char,
            )

            # Analizar intenciones
            knowledge_analyzer.analyze_intentions(
                text=chapter.content,
                chapter=chapter.chapter_number,
                start_char=chapter.start_char,
            )

        # Obtener asimetrías para pares de personajes más relacionados
        asymmetries = []
        character_entities = [e for e in entities if e.entity_type.value == "character"]

        for i, e1 in enumerate(character_entities[:10]):  # Limitar a 10 personajes
            for e2 in character_entities[i+1:10]:
                report = knowledge_analyzer.get_asymmetry_report(e1.id, e2.id)
                if report.a_mentions_b_count > 0 or report.b_mentions_a_count > 0:
                    asymmetries.append(report.to_dict())

        # Construir respuesta y convertir tipos numpy a Python nativos
        relations_count = len(clustering_result.get("relations", []))
        clusters_count = len(clustering_result.get("clusters", []))
        logger.info(f"[RELATIONSHIPS-API] Resultado: {relations_count} relaciones, {clusters_count} clusters, {len(asymmetries)} asimetrías")

        response_data = {
            "project_id": project_id,
            "entity_count": len(entities),
            # Incluir entidades para el grafo del frontend
            "entities": [
                {
                    "id": e.id,
                    "name": e.canonical_name,
                    "type": e.entity_type.value,
                    "importance": e.importance or 1,
                    "mentionCount": e.mention_count or 0,
                }
                for e in entities
            ],
            "relations": clustering_result.get("relations", []),
            "clusters": clustering_result.get("clusters", []),
            "dendrogram_data": clustering_result.get("dendrogram_data"),
            "mentions": [m.to_dict() for m in knowledge_analyzer.get_all_mentions()],
            "opinions": [o.to_dict() for o in knowledge_analyzer.get_all_opinions()],
            "intentions": [i.to_dict() for i in knowledge_analyzer.get_all_intentions()],
            "asymmetries": asymmetries,
        }

        return ApiResponse(
            success=True,
            data=convert_numpy_types(response_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RELATIONSHIPS-API] Error proyecto {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/relationships/asymmetry/{entity_a_id}/{entity_b_id}", response_model=ApiResponse)
def get_knowledge_asymmetry(project_id: int, entity_a_id: int, entity_b_id: int):
    """
    Obtiene reporte detallado de asimetría de conocimiento entre dos personajes.

    Args:
        project_id: ID del proyecto
        entity_a_id: ID del primer personaje
        entity_b_id: ID del segundo personaje

    Returns:
        ApiResponse con reporte de asimetría
    """
    try:
        from narrative_assistant.analysis import CharacterKnowledgeAnalyzer
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Obtener entidades
        entity_repo = get_entity_repository()
        entity_a = entity_repo.get_entity(entity_a_id)
        entity_b = entity_repo.get_entity(entity_b_id)

        if not entity_a or not entity_b:
            raise HTTPException(status_code=404, detail="Entidad no encontrada")

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        # Analizar conocimiento
        analyzer = CharacterKnowledgeAnalyzer(project_id=project_id)

        # Registrar todas las entidades del proyecto
        all_entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        for entity in all_entities:
            analyzer.register_entity(entity.id, entity.canonical_name, entity.aliases)  # type: ignore[arg-type]

        # Analizar capítulos
        for chapter in chapters:
            analyzer.analyze_narration(chapter.content, chapter.chapter_number, chapter.start_char)
            analyzer.analyze_intentions(chapter.content, chapter.chapter_number, chapter.start_char)

        # Generar reporte
        report = analyzer.get_asymmetry_report(entity_a_id, entity_b_id)

        return ApiResponse(
            success=True,
            data=report.to_dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asymmetry report: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/characters/{entity_id}/knowledge", response_model=ApiResponse)
def get_character_knowledge(
    project_id: int,
    entity_id: int,
    mode: str = Query("auto", description="Modo: auto, rules, llm, hybrid")
):
    """
    Obtiene el conocimiento que un personaje tiene sobre otros.

    Analiza el texto para detectar qué sabe el personaje sobre otros personajes:
    - Atributos físicos/psicológicos
    - Ubicación
    - Secretos
    - Historia pasada

    Args:
        project_id: ID del proyecto
        entity_id: ID del personaje
        mode: Modo de extracción (auto, rules, llm, hybrid)

    Returns:
        ApiResponse con hechos de conocimiento del personaje
    """
    try:
        from narrative_assistant.analysis.character_knowledge import (
            CharacterKnowledgeAnalyzer,
            KnowledgeExtractionMode,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener entidad
        entity_repo = get_entity_repository()
        entity = entity_repo.get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Personaje {entity_id} no encontrado")

        # Determinar modo
        mode_map = {
            "auto": None,
            "rules": KnowledgeExtractionMode.RULES,
            "llm": KnowledgeExtractionMode.LLM,
            "hybrid": KnowledgeExtractionMode.HYBRID,
        }
        extraction_mode = mode_map.get(mode.lower())

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "entity_id": entity_id,
                    "entity_name": entity.canonical_name,
                    "knowledge_facts": [],
                    "message": "No hay capítulos para analizar"
                }
            )

        # Analizar conocimiento
        analyzer = CharacterKnowledgeAnalyzer(project_id=project_id)

        # Registrar todas las entidades del proyecto
        all_entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        for e in all_entities:
            analyzer.register_entity(e.id, e.canonical_name, e.aliases)

        # Analizar capítulos
        for chapter in chapters:
            analyzer.analyze_narration(
                chapter.content,
                chapter.chapter_number,
                chapter.start_char,
                extraction_mode=extraction_mode
            )

        # Filtrar hechos donde este personaje es el "knower"
        all_knowledge = analyzer.get_all_knowledge()
        character_knowledge = [
            k for k in all_knowledge
            if k.knower_entity_id == entity_id
        ]

        # También obtener qué otros saben de este personaje
        knowledge_about = [
            k for k in all_knowledge
            if k.known_entity_id == entity_id
        ]

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "entity_id": entity_id,
                "entity_name": entity.canonical_name,
                "knows_about_others": [k.to_dict() for k in character_knowledge],
                "others_know_about": [k.to_dict() for k in knowledge_about],
                "stats": {
                    "facts_known": len(character_knowledge),
                    "facts_about": len(knowledge_about),
                    "chapters_analyzed": len(chapters),
                    "extraction_mode": mode,
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character knowledge: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/knowledge/anachronisms", response_model=ApiResponse)
def get_knowledge_anachronisms(
    project_id: int,
    mode: str = Query("rules", description="Modo: rules, llm, hybrid"),
):
    """
    Detecta anachronismos temporales de conocimiento entre personajes.

    Un anachronismo ocurre cuando un personaje referencia conocimiento
    en un capítulo anterior al capítulo donde lo adquiere.

    Args:
        project_id: ID del proyecto
        mode: Modo de extracción (rules=rápido, llm=preciso, hybrid=mixto)

    Returns:
        ApiResponse con lista de anachronismos detectados
    """
    try:
        from narrative_assistant.analysis.character_knowledge import (
            CharacterKnowledgeAnalyzer,
            KnowledgeExtractionMode,
            detect_knowledge_anachronisms,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Determinar modo
        mode_map = {
            "rules": KnowledgeExtractionMode.RULES,
            "llm": KnowledgeExtractionMode.LLM,
            "hybrid": KnowledgeExtractionMode.HYBRID,
        }
        extraction_mode = mode_map.get(mode.lower(), KnowledgeExtractionMode.RULES)

        # Obtener entidades y capítulos
        entity_repo = get_entity_repository()
        chapter_repo = get_chapter_repository()
        all_entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "anachronisms": [],
                    "stats": {"chapters_analyzed": 0, "entities_analyzed": 0,
                              "facts_extracted": 0, "anachronisms_found": 0},
                }
            )

        # Analizar conocimiento de todos los capítulos
        analyzer = CharacterKnowledgeAnalyzer(project_id=project_id)
        for e in all_entities:
            analyzer.register_entity(e.id, e.canonical_name, e.aliases)

        for chapter in chapters:
            analyzer.extract_knowledge_facts(
                chapter.content,
                chapter.chapter_number,
                chapter.start_char,
                mode=extraction_mode,
            )

        # Detectar anachronismos
        all_facts = analyzer.get_all_knowledge()
        anachronisms = detect_knowledge_anachronisms(all_facts)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "anachronisms": anachronisms,
                "stats": {
                    "chapters_analyzed": len(chapters),
                    "entities_analyzed": len(all_entities),
                    "facts_extracted": len(all_facts),
                    "anachronisms_found": len(anachronisms),
                    "extraction_mode": mode,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting knowledge anachronisms: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/relationships", response_model=ApiResponse)
def create_relationship(project_id: int, payload: deps.CreateRelationshipRequest):
    """
    Crea una nueva relación entre dos entidades.

    Body JSON:
        source_entity_id: ID de la entidad origen
        target_entity_id: ID de la entidad destino
        relation_type: Tipo de relación (ej: "friend", "family", "enemy", "love", "colleague")
        description: Descripción opcional de la relación
        bidirectional: Si la relación es bidireccional (default: true)

    Returns:
        ApiResponse con la relación creada
    """
    try:
        import uuid
        from datetime import datetime

        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.relationships.models import EntityRelationship, RelationType
        from narrative_assistant.relationships.repository import (
            get_relationship_repository,  # type: ignore[attr-defined]
        )

        source_entity_id = payload.source_entity_id
        target_entity_id = payload.target_entity_id
        relation_type_str = payload.relation_type
        description = payload.description
        bidirectional = payload.bidirectional

        # Obtener nombres de entidades
        entity_repo = get_entity_repository()
        source_entity = entity_repo.get_entity(source_entity_id)
        target_entity = entity_repo.get_entity(target_entity_id)

        if not source_entity or not target_entity:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Mapear tipo de relación
        type_mapping = {
            "friend": RelationType.FRIEND,
            "family": RelationType.FAMILY,  # type: ignore[attr-defined]
            "enemy": RelationType.ENEMY,
            "love": RelationType.LOVE,  # type: ignore[attr-defined]
            "colleague": RelationType.COLLEAGUE,
            "mentor": RelationType.MENTOR,
            "rival": RelationType.RIVAL,
            "ally": RelationType.ALLY,
            "acquaintance": RelationType.ACQUAINTANCE,
        }
        relation_type = type_mapping.get(relation_type_str.lower(), RelationType.OTHER)  # type: ignore[attr-defined]

        # Crear relación
        relationship = EntityRelationship(
            id=str(uuid.uuid4()),
            project_id=project_id,
            source_entity_id=source_entity_id,  # type: ignore[arg-type]
            target_entity_id=target_entity_id,  # type: ignore[arg-type]
            source_entity_name=source_entity.canonical_name,
            target_entity_name=target_entity.canonical_name,
            relation_type=relation_type,
            bidirectional=bidirectional,
            confidence=1.0,  # Relación manual, confianza total
            user_confirmed=True,
            evidence_texts=[description] if description else [],
            created_at=datetime.now(),
        )

        rel_repo = get_relationship_repository()
        rel_id = rel_repo.create_relationship(relationship)

        # Registrar en historial para undo
        try:
            from narrative_assistant.persistence.history import ChangeType, HistoryManager
            history = HistoryManager(project_id)
            history.record(
                action_type=ChangeType.RELATIONSHIP_CREATED,
                target_type="relationship",
                target_id=None,
                old_value=None,
                new_value={
                    "id": rel_id,
                    "source_entity_id": source_entity_id,
                    "target_entity_id": target_entity_id,
                    "relation_type": relation_type.value,
                    "description": description,
                    "bidirectional": bidirectional,
                },
                note=f"{source_entity.canonical_name} → {target_entity.canonical_name} ({relation_type.value})",
            )
        except Exception:
            logger.debug("Could not log relationship create to history", exc_info=True)

        return ApiResponse(
            success=True,
            data={
                "id": rel_id,
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relation_type": relation_type.value,
                "description": description,
                "bidirectional": bidirectional,
            }
        )

    except Exception as e:
        logger.error(f"Error creating relationship: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/projects/{project_id}/relationships/{relationship_id}", response_model=ApiResponse)
def delete_relationship(project_id: int, relationship_id: str):
    """
    Elimina una relación entre entidades.

    Args:
        project_id: ID del proyecto
        relationship_id: ID de la relación a eliminar

    Returns:
        ApiResponse con resultado de la eliminación
    """
    try:
        from narrative_assistant.relationships.repository import (
            get_relationship_repository,  # type: ignore[attr-defined]
        )

        rel_repo = get_relationship_repository()

        # Capturar datos antes de eliminar para historial
        old_rel = rel_repo.get_relationship(relationship_id)

        success = rel_repo.delete_relationship(relationship_id)

        if success:
            # Registrar en historial para undo
            if old_rel:
                try:
                    from narrative_assistant.persistence.history import ChangeType, HistoryManager
                    history = HistoryManager(project_id)
                    history.record(
                        action_type=ChangeType.RELATIONSHIP_DELETED,
                        target_type="relationship",
                        target_id=None,
                        old_value={
                            "id": relationship_id,
                            "source_entity_id": old_rel.source_entity_id,
                            "target_entity_id": old_rel.target_entity_id,
                            "source_entity_name": old_rel.source_entity_name,
                            "target_entity_name": old_rel.target_entity_name,
                            "relation_type": old_rel.relation_type.value if hasattr(old_rel.relation_type, 'value') else str(old_rel.relation_type),
                            "bidirectional": old_rel.bidirectional,
                            "confidence": old_rel.confidence,
                            "evidence_texts": old_rel.evidence_texts,
                        },
                        new_value=None,
                        note=f"{old_rel.source_entity_name} → {old_rel.target_entity_name} eliminada",
                    )
                except Exception:
                    logger.debug("Could not log relationship delete to history", exc_info=True)

            return ApiResponse(success=True, data={"deleted": relationship_id})
        else:
            return ApiResponse(success=False, error="Relación no encontrada")

    except Exception as e:
        logger.error(f"Error deleting relationship {relationship_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/characters/{character_id}/analyze-behavior", response_model=ApiResponse)
def analyze_character_behavior(project_id: int, character_id: int):
    """
    Analiza el comportamiento de un personaje usando LLM para inferir expectativas.

    Args:
        project_id: ID del proyecto
        character_id: ID del personaje

    Returns:
        ApiResponse con perfil comportamental del personaje
    """
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.llm import (
            ExpectationInferenceEngine,
            is_llm_available,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not is_llm_available():
            return ApiResponse(
                success=False,
                error="El asistente de IA no está disponible. Configúralo desde Configuración → Análisis"
            )

        # Obtener entidad
        entity_repo = get_entity_repository()
        entity = entity_repo.get_entity(character_id)

        if not entity or entity.project_id != project_id:
            raise HTTPException(status_code=404, detail="Personaje no encontrado")

        # Obtener menciones del personaje
        mentions = entity_repo.get_mentions_by_entity(character_id)

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        chapters_dict = {c.id: c for c in chapters}

        # Extraer fragmentos de texto donde aparece el personaje
        text_samples = []
        chapter_numbers = []
        CONTEXT_SIZE = 500  # caracteres alrededor de la mención

        for mention in mentions[:20]:  # Limitar a 20 menciones
            chapter = chapters_dict.get(mention.chapter_id)
            if not chapter:
                continue

            # Extraer contexto
            start = max(0, mention.start_char - chapter.start_char - CONTEXT_SIZE)
            end = min(len(chapter.content), mention.end_char - chapter.start_char + CONTEXT_SIZE)
            context = chapter.content[start:end]

            if context.strip():
                text_samples.append(context)
                chapter_numbers.append(chapter.chapter_number)

        if not text_samples:
            return ApiResponse(
                success=False,
                error="No hay suficiente contexto para analizar el personaje"
            )

        # Obtener atributos existentes
        existing_attrs = {}  # type: ignore[var-annotated]
        for attr in entity.attributes:  # type: ignore[attr-defined]
            if attr.attribute_name not in existing_attrs:
                existing_attrs[attr.attribute_name] = []
            existing_attrs[attr.attribute_name].append(attr.value)

        # Leer configuración LLM actual
        _ql, _sens = "rapida", 5.0
        try:
            from narrative_assistant.persistence.database import get_database as _get_db
            _db = _get_db()
            with _db.get_connection() as _conn:
                _row = _conn.execute(
                    "SELECT quality_level, sensitivity FROM llm_config LIMIT 1"
                ).fetchone()
            if _row:
                _ql = _row[0] or "rapida"
                _sens = float(_row[1]) if _row[1] is not None else 5.0
        except Exception:
            pass

        # Analizar con LLM
        from narrative_assistant.llm.expectation_inference import InferenceConfig
        engine = ExpectationInferenceEngine(
            config=InferenceConfig(quality_level=_ql, sensitivity=_sens)
        )
        profile = engine.analyze_character(
            character_id=character_id,
            character_name=entity.canonical_name,
            text_samples=text_samples,
            chapter_numbers=chapter_numbers,
            existing_attributes=existing_attrs,
        )

        if not profile:
            return ApiResponse(
                success=False,
                error="Error analizando personaje con LLM"
            )

        return ApiResponse(
            success=True,
            data=profile.to_dict()
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Import error for LLM module: {e}")
        return ApiResponse(
            success=False,
            error="Módulo LLM no disponible. Verifica la instalación de dependencias."
        )
    except Exception as e:
        logger.error(f"Error analyzing character behavior: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/characters/{character_id}/detect-violations", response_model=ApiResponse)
def detect_character_violations(
    project_id: int,
    character_id: int,
    chapter_number: Optional[int] = None
):
    """
    Detecta violaciones de expectativas para un personaje.

    Args:
        project_id: ID del proyecto
        character_id: ID del personaje
        chapter_number: Capítulo específico a analizar (opcional)

    Returns:
        ApiResponse con lista de violaciones detectadas
    """
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.llm import (
            ExpectationInferenceEngine,
            is_llm_available,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not is_llm_available():
            return ApiResponse(
                success=False,
                error="El asistente de IA no está disponible. Configúralo desde Configuración → Análisis"
            )

        # Verificar que existe perfil del personaje
        engine = ExpectationInferenceEngine()
        profile = engine.get_profile(character_id)

        if not profile:
            return ApiResponse(
                success=False,
                error="Primero debe analizar el comportamiento del personaje"
            )

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if chapter_number:
            chapters = [c for c in chapters if c.chapter_number == chapter_number]

        # Obtener menciones del personaje en los capítulos
        entity_repo = get_entity_repository()
        mentions = entity_repo.get_mentions_by_entity(character_id)
        chapters_dict = {c.id: c for c in chapters}

        all_violations = []
        CONTEXT_SIZE = 800

        for mention in mentions:
            chapter = chapters_dict.get(mention.chapter_id)
            if not chapter:
                continue

            # Extraer contexto
            start = max(0, mention.start_char - chapter.start_char - CONTEXT_SIZE)
            end = min(len(chapter.content), mention.end_char - chapter.start_char + CONTEXT_SIZE)
            context = chapter.content[start:end]

            if not context.strip():
                continue

            # Detectar violaciones
            violations = engine.detect_violations(
                character_id=character_id,
                text=context,
                chapter_number=chapter.chapter_number,
                position=mention.start_char,
            )

            all_violations.extend(violations)

        return ApiResponse(
            success=True,
            data={
                "character_id": character_id,
                "character_name": profile.character_name,
                "violations_count": len(all_violations),
                "violations": [v.to_dict() for v in all_violations],
            }
        )

    except HTTPException:
        raise
    except ImportError:
        return ApiResponse(
            success=False,
            error="Módulo LLM no disponible. Verifica la instalación de dependencias."
        )
    except Exception as e:
        logger.error(f"Error detecting violations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/characters/{character_id}/expectations", response_model=ApiResponse)
def get_character_expectations(project_id: int, character_id: int):
    """
    Obtiene las expectativas comportamentales de un personaje.

    Args:
        project_id: ID del proyecto
        character_id: ID del personaje

    Returns:
        ApiResponse con lista de expectativas
    """
    try:
        from narrative_assistant.llm import ExpectationInferenceEngine

        engine = ExpectationInferenceEngine()
        profile = engine.get_profile(character_id)

        if not profile:
            return ApiResponse(
                success=True,
                data={
                    "character_id": character_id,
                    "expectations": [],
                    "message": "No se ha analizado aún. Use el endpoint analyze-behavior primero."
                }
            )

        return ApiResponse(
            success=True,
            data={
                "character_id": character_id,
                "character_name": profile.character_name,
                "expectations": [e.to_dict() for e in profile.expectations],
                "personality_traits": profile.personality_traits,
                "values": profile.values,
                "goals": profile.goals,
            }
        )

    except ImportError:
        return ApiResponse(
            success=False,
            error="Módulo LLM no disponible."
        )
    except Exception as e:
        logger.error(f"Error getting expectations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/emotional-analysis", response_model=ApiResponse)
def get_emotional_analysis(project_id: int):
    """
    Obtiene el análisis de coherencia emocional de un proyecto.

    Devuelve las incoherencias emocionales detectadas:
    - Diálogos incoherentes con el estado emocional declarado
    - Acciones incoherentes con el estado emocional
    - Cambios emocionales abruptos sin justificación narrativa
    """
    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "emotional_analysis", allow_stale=True)  # type: ignore[misc]
    if cached:
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.analysis.emotional_coherence import (
            get_emotional_coherence_checker,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Obtener capítulos del proyecto
        chapters = deps.chapter_repository.get_by_project(project_id)  # type: ignore[attr-defined]
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "incoherences": [],
                    "stats": {"total": 0}
                },
                message="No hay capítulos para analizar"
            )

        # Obtener entidades (personajes)
        entities = deps.entity_repository.get_entities_by_project(project_id)  # type: ignore[attr-defined]
        # entity_type es un enum, usar .value para comparar
        character_names = [
            e.canonical_name for e in entities
            if (hasattr(e.entity_type, 'value') and e.entity_type.value in ["character", "animal", "creature"])
            or e.entity_type in ["character", "PER", "animal", "creature"]
        ]

        if not character_names:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "incoherences": [],
                    "stats": {"total": 0}
                },
                message="No hay personajes para analizar"
            )

        # Ejecutar análisis
        checker = get_emotional_coherence_checker()
        all_incoherences = []

        for chapter in chapters:
            # Extraer diálogos
            dialogue_result = detect_dialogues(chapter.content)
            if dialogue_result.is_success:
                dialogues = [
                    (
                        d.speaker_hint or "desconocido",
                        d.text,
                        d.start_char,
                        d.end_char,
                    )
                    for d in dialogue_result.value.dialogues  # type: ignore[union-attr]
                ]
            else:
                dialogues = []

            # Analizar capítulo
            chapter_incoherences = checker.analyze_chapter(
                chapter_text=chapter.content,
                entity_names=character_names,
                dialogues=dialogues,
                chapter_id=chapter.chapter_number,
            )
            all_incoherences.extend(chapter_incoherences)

        # Agrupar por tipo
        by_type = {}
        for inc in all_incoherences:
            inc_type = inc.incoherence_type.value
            if inc_type not in by_type:
                by_type[inc_type] = 0
            by_type[inc_type] += 1

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "incoherences": [inc.to_dict() for inc in all_incoherences],
                "stats": {
                    "total": len(all_incoherences),
                    "by_type": by_type,
                    "chapters_analyzed": len(chapters),
                }
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis emocional no disponible"
        )
    except Exception as e:
        logger.error(f"Error in emotional analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/characters/{character_name}/emotional-profile", response_model=ApiResponse)
def get_character_emotional_profile(project_id: int, character_name: str):
    """
    Obtiene el perfil emocional de un personaje específico.

    Incluye:
    - Estados emocionales declarados a lo largo del texto
    - Evolución emocional por capítulo
    - Incoherencias relacionadas con el personaje
    """
    try:
        from narrative_assistant.analysis.emotional_coherence import (
            get_emotional_coherence_checker,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.nlp.sentiment import get_sentiment_analyzer

        # Obtener capítulos
        chapters = deps.chapter_repository.get_by_project(project_id)  # type: ignore[attr-defined]
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "character_name": character_name,
                    "emotional_states": [],
                    "evolution": [],
                    "incoherences": [],
                }
            )

        sentiment_analyzer = get_sentiment_analyzer()
        checker = get_emotional_coherence_checker()

        all_states = []
        all_incoherences = []
        evolution = []

        for chapter in chapters:
            # Extraer estados emocionales declarados del personaje
            states = sentiment_analyzer.extract_declared_emotions(
                text=chapter.content,
                entity_names=[character_name],
                chapter_id=chapter.chapter_number,
            )

            chapter_states = [s for s in states if s.entity_name.lower() == character_name.lower()]
            all_states.extend(chapter_states)

            # Analizar incoherencias
            dialogue_result = detect_dialogues(chapter.content)
            dialogues = []
            if dialogue_result.is_success:
                dialogues = [
                    (d.speaker_hint or "desconocido", d.text, d.start_char, d.end_char)
                    for d in dialogue_result.value.dialogues  # type: ignore[union-attr]
                ]

            chapter_incoherences = checker.analyze_chapter(
                chapter_text=chapter.content,
                entity_names=[character_name],
                dialogues=dialogues,
                chapter_id=chapter.chapter_number,
            )
            all_incoherences.extend(chapter_incoherences)

            # Evolución emocional
            if chapter_states:
                dominant_emotion = max(
                    set(s.emotion_keyword for s in chapter_states),
                    key=lambda x: sum(1 for s in chapter_states if s.emotion_keyword == x)
                )
                evolution.append({
                    "chapter": chapter.chapter_number,
                    "dominant_emotion": dominant_emotion,
                    "emotion_count": len(chapter_states),
                    "has_incoherences": len(chapter_incoherences) > 0,
                })

        return ApiResponse(
            success=True,
            data={
                "character_name": character_name,
                "emotional_states": [
                    {
                        "emotion": s.emotion_keyword,
                        "intensity": s.intensity.value if hasattr(s, 'intensity') else "medium",
                        "chapter": s.chapter_id,
                        "position": s.position,
                        "context": s.context_text[:100] if hasattr(s, 'context_text') else "",
                    }
                    for s in all_states
                ],
                "evolution": evolution,
                "incoherences": [inc.to_dict() for inc in all_incoherences],
                "stats": {
                    "total_states": len(all_states),
                    "total_incoherences": len(all_incoherences),
                    "chapters_with_presence": len(evolution),
                }
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis emocional no disponible"
        )
    except Exception as e:
        logger.error(f"Error getting emotional profile: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/vital-status", response_model=ApiResponse)
def get_vital_status_analysis(project_id: int):
    """
    Obtiene el análisis de estado vital de personajes.

    Detecta:
    - Eventos de muerte de personajes
    - Reapariciones de personajes fallecidos
    - Inconsistencias narrativas (muerto que actúa)

    Returns:
        Reporte con eventos de muerte y posibles inconsistencias
    """
    try:
        from narrative_assistant.analysis.vital_status import (
            analyze_vital_status,
        )

        # Obtener capítulos
        chapters = deps.chapter_repository.get_by_project(project_id)  # type: ignore[attr-defined]
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "death_events": [],
                    "post_mortem_appearances": [],
                    "inconsistencies_count": 0,
                    "entities_status": {},
                }
            )

        # Obtener entidades (personajes, animales, criaturas)
        all_entities = deps.entity_repository.get_by_project(project_id)  # type: ignore[attr-defined]

        entities = [
            e.to_dict() for e in all_entities
            if e.entity_type.value in ["character", "animal", "creature"]
        ]

        # Preparar datos de capítulos
        chapters_data = [
            {
                "number": ch.chapter_number,
                "content": ch.content,
                "start_char": ch.start_char,
            }
            for ch in chapters
        ]

        # Analizar
        result = analyze_vital_status(
            project_id=project_id,
            chapters=chapters_data,
            entities=entities,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        report = result.value

        return ApiResponse(
            success=True,
            data=report.to_dict()  # type: ignore[union-attr]
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis de estado vital no disponible"
        )
    except Exception as e:
        logger.error(f"Error in vital status analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/vital-status/generate-alerts", response_model=ApiResponse)
def generate_vital_status_alerts(project_id: int):
    """
    Genera alertas a partir del análisis de estado vital.

    Crea alertas para cada reaparición de personaje fallecido
    que no sea una referencia válida (flashback, recuerdo, etc.).
    """
    try:
        from narrative_assistant.alerts import get_alert_engine
        from narrative_assistant.analysis.vital_status import analyze_vital_status

        # Obtener capítulos
        chapters = deps.chapter_repository.get_by_project(project_id)  # type: ignore[attr-defined]
        if not chapters:
            return ApiResponse(
                success=True,
                data={"alerts_created": 0, "message": "No hay capítulos para analizar"}
            )

        # Obtener entidades
        all_entities = deps.entity_repository.get_by_project(project_id)  # type: ignore[attr-defined]

        entities = [
            e.to_dict() for e in all_entities
            if e.entity_type.value in ["character", "animal", "creature"]
        ]

        # Preparar datos de capítulos
        chapters_data = [
            {
                "number": ch.chapter_number,
                "content": ch.content,
                "start_char": ch.start_char,
            }
            for ch in chapters
        ]

        # Analizar
        result = analyze_vital_status(
            project_id=project_id,
            chapters=chapters_data,
            entities=entities,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        report = result.value

        # Generar alertas para inconsistencias
        engine = get_alert_engine()
        alerts_created = 0

        for appearance in report.inconsistencies:  # type: ignore[union-attr]
            # Buscar el evento de muerte correspondiente
            death_event = next(
                (e for e in report.death_events if e.entity_id == appearance.entity_id),  # type: ignore[union-attr]
                None
            )

            alert_result = engine.create_from_deceased_reappearance(
                project_id=project_id,
                entity_id=appearance.entity_id,
                entity_name=appearance.entity_name,
                death_chapter=appearance.death_chapter,
                appearance_chapter=appearance.appearance_chapter,
                appearance_start_char=appearance.appearance_start_char,
                appearance_end_char=appearance.appearance_end_char,
                appearance_excerpt=appearance.appearance_excerpt,
                appearance_type=appearance.appearance_type,
                death_excerpt=death_event.excerpt if death_event else "",
                confidence=appearance.confidence,
            )

            if alert_result.is_success:
                alerts_created += 1

        return ApiResponse(
            success=True,
            data={
                "alerts_created": alerts_created,
                "death_events_found": len(report.death_events),  # type: ignore[union-attr]
                "inconsistencies_found": len(report.inconsistencies),  # type: ignore[union-attr]
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis de estado vital no disponible"
        )
    except Exception as e:
        logger.error(f"Error generating vital status alerts: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/character-locations", response_model=ApiResponse)
def get_character_locations(project_id: int):
    """
    Obtiene el análisis de ubicaciones de personajes.

    Detecta:
    - Movimientos de personajes entre ubicaciones
    - Inconsistencias (personaje en dos lugares a la vez)
    - Última ubicación conocida de cada personaje

    Returns:
        Reporte con eventos de ubicación e inconsistencias
    """
    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "character_locations", allow_stale=True)  # type: ignore[misc]
    if cached:
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.analysis.character_location import (
            analyze_character_locations,
        )

        # Obtener capítulos
        chapters = deps.chapter_repository.get_by_project(project_id)  # type: ignore[attr-defined]
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "location_events": [],
                    "inconsistencies": [],
                    "inconsistencies_count": 0,
                    "current_locations": {},
                    "characters_tracked": 0,
                    "locations_found": 0,
                }
            )

        # Obtener entidades (personajes y ubicaciones)
        all_entities = deps.entity_repository.get_by_project(project_id)  # type: ignore[attr-defined]

        entities = [
            {
                "id": e.id,
                "name": e.canonical_name,
                "entity_type": "PER" if e.entity_type.value in ["character", "animal", "creature"] else
                              "LOC" if e.entity_type.value == "location" else
                              e.entity_type.value,
            }
            for e in all_entities
        ]

        # Preparar datos de capítulos
        chapters_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": ch.content,
            }
            for ch in chapters
        ]

        # Analizar
        result = analyze_character_locations(
            project_id=project_id,
            chapters=chapters_data,
            entities=entities,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(success=True, data=result.value.to_dict())  # type: ignore[union-attr]

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis de ubicaciones no disponible"
        )
    except Exception as e:
        logger.error(f"Error in character location analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/character-archetypes", response_model=ApiResponse)
def get_character_archetypes(
    project_id: int,
    mode: str = "basic",
    llm_model: str = "llama3.2",
):
    """
    Detecta arquetipos de personaje (Jung/Campbell) en el manuscrito.

    Clasifica personajes como Héroe, Sombra, Mentor, Heraldo, Guardián,
    Cambiante, Embaucador, Inocente, Explorador, Sabio, Amante, Gobernante,
    Cuidador, Creador, Bufón o Rebelde.
    """
    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "character_archetypes", allow_stale=True)  # type: ignore[misc]
    if cached:
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress
        from narrative_assistant.analysis.character_archetypes import CharacterArchetypeAnalyzer

        proj_result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if proj_result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener datos de capítulos (arcos, chekhov, etc.)
        progress = analyze_chapter_progress(
            project_id=project_id,
            mode=mode,
            llm_model=llm_model,
        )

        # Obtener entidades
        entities_data = []
        try:
            entities = deps.entity_repository.get_by_project(project_id)  # type: ignore[attr-defined]
            for ent in entities:
                # Convertir entity_type enum a string
                entity_type_raw = ent.entity_type if hasattr(ent, 'entity_type') else "character"
                if hasattr(entity_type_raw, 'value'):
                    entity_type_str = entity_type_raw.value
                else:
                    entity_type_str = str(entity_type_raw)
                # Mapear PERSON -> character para compatibilidad
                if entity_type_str.upper() == "PERSON":
                    entity_type_str = "character"

                # Convertir EntityImportance enum a string para archetype analyzer
                raw_importance = ent.importance if hasattr(ent, 'importance') else "medium"
                if hasattr(raw_importance, 'value'):
                    importance_str = raw_importance.value
                else:
                    importance_str = str(raw_importance)

                ent_dict = {
                    "id": ent.id if hasattr(ent, 'id') else 0,
                    "entity_type": entity_type_str,
                    "name": ent.name if hasattr(ent, 'name') else ent.canonical_name if hasattr(ent, 'canonical_name') else "",
                    "canonical_name": ent.canonical_name if hasattr(ent, 'canonical_name') else "",
                    "importance": importance_str,
                    "mention_count": ent.mention_count if hasattr(ent, 'mention_count') else 0,
                    "chapters_present": len(ent.chapter_appearances) if hasattr(ent, 'chapter_appearances') else 0,
                    "description": ent.description if hasattr(ent, 'description') else "",
                }
                entities_data.append(ent_dict)
        except Exception as e:
            logger.warning(f"Could not load entities for archetype analysis: {e}")

        # Obtener relaciones
        relationships_data = []
        try:
            from narrative_assistant.relationships.repository import (
                get_relationship_repository,  # type: ignore[attr-defined]
            )
            rel_repo = get_relationship_repository()
            rels = rel_repo.get_by_project(project_id)
            for rel in rels:
                relationships_data.append({
                    "entity1_id": rel.source_entity_id if hasattr(rel, 'source_entity_id') else 0,
                    "entity2_id": rel.target_entity_id if hasattr(rel, 'target_entity_id') else 0,
                    "relation_type": rel.relation_type.value if hasattr(rel.relation_type, 'value') else str(rel.relation_type),
                    "subtype": rel.description if hasattr(rel, 'description') else "",
                })
        except Exception as e:
            logger.warning(f"Could not load relationships for archetype analysis: {e}")

        # Arcos de personaje del chapter progress
        character_arcs = [a.to_dict() for a in progress.character_arcs]

        # Obtener perfiles de centralidad narrativa (6 indicadores)
        profiles_data = []
        try:
            from narrative_assistant.analysis.character_profiling import CharacterProfiler
            from narrative_assistant.entities.repository import get_entity_repository
            from narrative_assistant.persistence.chapter import get_chapter_repository

            entity_repo = get_entity_repository()
            all_entities = entity_repo.get_entities_by_project(project_id, active_only=True)
            chapter_repo = get_chapter_repository()
            chapters = chapter_repo.get_by_project(project_id)

            if all_entities and chapters:
                mentions = []
                chapter_id_map = {c.id: c.chapter_number for c in chapters}
                for entity in all_entities:
                    entity_mentions = entity_repo.get_mentions_by_entity(entity.id)  # type: ignore[arg-type]
                    for m in entity_mentions:
                        ch_num = chapter_id_map.get(m.chapter_id, 0)
                        mentions.append({
                            "entity_id": entity.id,
                            "entity_name": entity.canonical_name,
                            "chapter": ch_num,
                        })

                chapter_texts = {c.chapter_number: c.content for c in chapters}
                profiler = CharacterProfiler(total_chapters=len(chapters))
                raw_profiles = profiler.build_profiles(
                    mentions=mentions,
                    chapter_texts=chapter_texts,
                )
                for p in raw_profiles:
                    pd = p.to_dict()
                    profiles_data.append({
                        "character_name": pd["entity_name"],
                        "narrative_relevance": pd["narrative_relevance"],
                        "role": pd["role"],
                        "agency_score": pd.get("actions", {}).get("agency", 0),
                    })
                logger.info(
                    f"[ARCHETYPES] Profiling: {len(profiles_data)} personajes, "
                    f"roles: {[p['role'] for p in profiles_data]}"
                )
        except Exception as e:
            logger.warning(f"Could not build profiles for archetype analysis: {e}")

        # Analizar arquetipos
        analyzer = CharacterArchetypeAnalyzer()
        report = analyzer.analyze(
            entities=entities_data,
            character_arcs=character_arcs,
            relationships=relationships_data,
            interactions=[],  # No hay endpoint de interacciones aún
            total_chapters=progress.total_chapters,
            profiles=profiles_data or None,
        )

        return ApiResponse(success=True, data=report.to_dict())

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(success=False, error="Módulo de arquetipos no disponible")
    except Exception as e:
        logger.error(f"Error analyzing character archetypes: {e}", exc_info=True)
        user_msg = e.user_message if hasattr(e, 'user_message') and e.user_message else "Error interno del análisis"
        return ApiResponse(success=False, error=user_msg)


# ============================================================================
# S6-01: Network Metrics Endpoint
# ============================================================================

@router.get("/api/projects/{project_id}/character-network", response_model=ApiResponse)
def get_character_network(project_id: int):
    """
    Obtiene métricas de red de personajes (centralidad, puentes, evolución).

    Complementa /relationships con métricas de análisis de grafos:
    - Centralidad por personaje (degree, betweenness, closeness)
    - Personajes puente (conectan subgrupos)
    - Evolución temporal de la red
    - Densidad y clustering coefficient

    Returns:
        ApiResponse con CharacterNetworkReport
    """
    logger.info(f"[NETWORK-API] Solicitando red de personajes para proyecto {project_id}")

    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "character_network", allow_stale=True)  # type: ignore[misc]
    if cached:
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.analysis.character_network import CharacterNetworkAnalyzer
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not entities:
            return ApiResponse(success=True, data={"nodes": [], "edges": [], "metrics": {}})

        # Recopilar co-ocurrencias
        entity_names = {e.id: e.canonical_name for e in entities}
        cooccurrences = []

        # Query batch con JOIN — evita N+1 (una query por entidad)
        all_mentions = entity_repo.get_mentions_by_project(project_id)

        chapter_id_to_number = {c.id: c.chapter_number for c in chapters}

        # Detectar co-ocurrencias
        mentions_by_chapter: dict = {}
        for m in all_mentions:
            ch_num = chapter_id_to_number.get(m.get("chapter_id"))
            if ch_num is not None:
                mentions_by_chapter.setdefault(ch_num, []).append(m)

        WINDOW = 500
        for ch_num, ch_mentions in mentions_by_chapter.items():
            ch_mentions.sort(key=lambda x: x["start_char"])
            for i, m1 in enumerate(ch_mentions):
                for m2 in ch_mentions[i+1:]:
                    if m1["entity_id"] == m2["entity_id"]:
                        continue
                    distance = m2["start_char"] - m1["end_char"]
                    if distance > WINDOW:
                        break
                    cooccurrences.append({
                        "entity1_id": min(m1["entity_id"], m2["entity_id"]),
                        "entity2_id": max(m1["entity_id"], m2["entity_id"]),
                        "chapter": ch_num,
                        "distance_chars": distance,
                    })

        analyzer = CharacterNetworkAnalyzer()
        report = analyzer.analyze(
            cooccurrences=cooccurrences,
            entity_names=entity_names,
            total_chapters=len(chapters),
        )

        return ApiResponse(
            success=True,
            data=convert_numpy_types(report.to_dict()),
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"[NETWORK-API] Import error: {e}")
        return ApiResponse(success=False, error="Módulo de red de personajes no disponible")
    except Exception as e:
        logger.error(f"[NETWORK-API] Error: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# ============================================================================
# S6-03: Character Profiles Endpoint
# ============================================================================

# ============================================================================
# S6-02: Timeline of Character Appearances
# ============================================================================

@router.get("/api/projects/{project_id}/character-timeline", response_model=ApiResponse)
def get_character_timeline(project_id: int):
    """
    Obtiene timeline de apariciones de personajes por capítulo.

    Para cada personaje, devuelve en qué capítulos aparece y con cuántas
    menciones. Útil para visualizar la presencia narrativa.

    Returns:
        ApiResponse con datos de timeline por personaje
    """
    logger.info(f"[TIMELINE-API] Solicitando timeline para proyecto {project_id}")

    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "character_timeline", allow_stale=True)  # type: ignore[misc]
    if cached:
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not entities or not chapters:
            return ApiResponse(success=True, data={
                "characters": [],
                "chapters": [],
                "total_chapters": 0,
            })

        chapter_id_to_number = {c.id: c.chapter_number for c in chapters}
        chapter_titles = {c.chapter_number: c.title or f"Cap. {c.chapter_number}" for c in chapters}

        # Construir timeline por personaje — query batch con JOIN (evita N+1)
        all_mentions = entity_repo.get_mentions_by_project(project_id)

        # Pre-agrupar menciones por entity_id y capítulo
        mentions_per_entity: dict[int, dict[int, int]] = {}
        for m in all_mentions:
            ch_num = chapter_id_to_number.get(m["chapter_id"])
            if ch_num is not None:
                mentions_per_entity.setdefault(m["entity_id"], {})
                by_ch = mentions_per_entity[m["entity_id"]]
                by_ch[ch_num] = by_ch.get(ch_num, 0) + 1

        characters_timeline = []

        for entity in entities:
            by_chapter = mentions_per_entity.get(entity.id)
            if not by_chapter:
                continue

            chapters_present = sorted(by_chapter.keys())

            characters_timeline.append({
                "entity_id": entity.id,
                "name": entity.canonical_name,
                "entity_type": entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type),
                "importance": entity.importance.value if hasattr(entity.importance, 'value') else str(entity.importance),
                "total_mentions": sum(by_chapter.values()),
                "chapters_present": len(chapters_present),
                "first_chapter": chapters_present[0],
                "last_chapter": chapters_present[-1],
                "appearances": [
                    {"chapter": ch, "mentions": by_chapter.get(ch, 0)}
                    for ch in range(1, len(chapters) + 1)
                ],
            })

        # Ordenar por total de menciones (más relevantes primero)
        characters_timeline.sort(key=lambda x: x["total_mentions"], reverse=True)

        return ApiResponse(
            success=True,
            data={
                "characters": characters_timeline,
                "chapters": [
                    {"number": c.chapter_number, "title": chapter_titles.get(c.chapter_number, "")}
                    for c in sorted(chapters, key=lambda x: x.chapter_number)
                ],
                "total_chapters": len(chapters),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TIMELINE-API] Error: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/character-profiles", response_model=ApiResponse)
def get_character_profiles(project_id: int):
    """
    Obtiene perfiles de 6 indicadores para todos los personajes.

    Indicadores: presencia, acciones, habla, definición, sentimiento, entornos.
    Incluye rol narrativo estimado y relevancia.

    Returns:
        ApiResponse con lista de CharacterProfile
    """
    logger.info(f"[PROFILES-API] Solicitando perfiles para proyecto {project_id}")

    # Check enrichment cache first (S8a-13)
    from routers._enrichment_cache import get_cached_enrichment
    cached = get_cached_enrichment(deps.get_database(), project_id, "character_profiles", allow_stale=True)  # type: ignore[misc]
    if cached:
        return ApiResponse(success=True, data=cached)

    try:
        from narrative_assistant.analysis.character_profiling import CharacterProfiler
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not entities:
            return ApiResponse(success=True, data={"profiles": [], "count": 0})

        # Construir datos de entrada — query batch con JOIN (evita N+1)
        chapter_id_map = {c.id: c.chapter_number for c in chapters}
        raw_mentions = entity_repo.get_mentions_by_project(project_id)
        mentions = [
            {
                "entity_id": m["entity_id"],
                "entity_name": m["entity_name"],
                "chapter": chapter_id_map.get(m["chapter_id"], 0),
            }
            for m in raw_mentions
        ]

        # Textos de capítulos para acciones/sentimiento
        chapter_texts = {c.chapter_number: c.content for c in chapters}

        profiler = CharacterProfiler(total_chapters=len(chapters))
        profiles = profiler.build_profiles(
            mentions=mentions,
            chapter_texts=chapter_texts,
        )

        return ApiResponse(
            success=True,
            data={
                "profiles": [p.to_dict() for p in profiles],
                "count": len(profiles),
            },
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"[PROFILES-API] Import error: {e}")
        return ApiResponse(success=False, error="Módulo de perfilado no disponible")
    except Exception as e:
        logger.error(f"[PROFILES-API] Error: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/enrichment/stale", response_model=ApiResponse)
def get_stale_enrichments(project_id: int):
    """
    Obtiene el estado de invalidación del proyecto.

    Returns:
        revision: última revisión de invalidación
        stale_types: lista de enrichment types marcados como stale
    """
    try:
        from routers._invalidation import get_project_revision, get_stale_enrichment_types

        db = deps.get_database()  # type: ignore[misc]
        revision = get_project_revision(db, project_id)
        stale_types = get_stale_enrichment_types(db, project_id)

        return ApiResponse(
            success=True,
            data={
                "revision": revision,
                "stale_types": stale_types,
                "has_stale": len(stale_types) > 0,
            },
        )
    except Exception as e:
        logger.error(f"Error getting stale enrichments: {e}")
        return ApiResponse(success=True, data={"revision": 0, "stale_types": [], "has_stale": False})
