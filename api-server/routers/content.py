"""
Router: content
"""

from typing import Optional

import deps
from deps import ApiResponse, CustomWordRequest, GlossaryEntryRequest, logger
from fastapi import APIRouter, Body, HTTPException, Query

router = APIRouter()

@router.get("/api/projects/{project_id}/glossary", response_model=ApiResponse)
def list_glossary_entries(
    project_id: int,
    category: Optional[str] = None,
    only_technical: bool = False,
    only_invented: bool = False,
    only_for_publication: bool = False,
) -> ApiResponse:
    """
    Lista todas las entradas del glosario de un proyecto.

    Args:
        project_id: ID del proyecto
        category: Filtrar por categoría (personaje, lugar, objeto, concepto, técnico)
        only_technical: Solo términos técnicos
        only_invented: Solo términos inventados
        only_for_publication: Solo para glosario de publicación
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entries = repo.list_by_project(
            project_id=project_id,
            category=category,
            only_technical=only_technical,
            only_invented=only_invented,
            only_for_publication=only_for_publication,
        )

        return ApiResponse(
            success=True,
            data={
                "entries": [entry.to_dict() for entry in entries],
                "total": len(entries),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing glossary entries: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/glossary", response_model=ApiResponse)
def create_glossary_entry(
    project_id: int,
    request: GlossaryEntryRequest,
) -> ApiResponse:
    """
    Crea una nueva entrada en el glosario.
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryEntry, GlossaryRepository

        repo = GlossaryRepository()

        entry = GlossaryEntry(
            project_id=project_id,
            term=request.term,
            definition=request.definition,  # type: ignore[arg-type]
            variants=request.variants,  # type: ignore[attr-defined]
            category=request.category,  # type: ignore[arg-type]
            subcategory=request.subcategory,  # type: ignore[attr-defined]
            context_notes=request.context_notes,  # type: ignore[attr-defined]
            related_terms=request.related_terms,  # type: ignore[attr-defined]
            usage_example=request.usage_example,  # type: ignore[attr-defined]
            is_technical=request.is_technical,  # type: ignore[attr-defined]
            is_invented=request.is_invented,  # type: ignore[attr-defined]
            is_proper_noun=request.is_proper_noun,  # type: ignore[attr-defined]
            include_in_publication_glossary=request.include_in_publication_glossary,  # type: ignore[attr-defined]
        )

        created = repo.create(entry)

        return ApiResponse(
            success=True,
            data=created.to_dict(),
            message=f"Término '{request.term}' añadido al glosario",
        )

    except ValueError:
        # Término duplicado
        return ApiResponse(success=False, error="Error interno del servidor")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# NOTE: Rutas con literal path (/context/llm, /search, /suggestions, etc.)
# DEBEN ir ANTES de rutas con {entry_id} para evitar que FastAPI las
# capture como entry_id (causando 422 al intentar parsear "suggestions" como int).

@router.get("/api/projects/{project_id}/glossary/context/llm", response_model=ApiResponse)
def get_glossary_llm_context(
    project_id: int,
    max_entries: int = 50,
    categories: Optional[str] = None,
) -> ApiResponse:
    """
    Genera el contexto del glosario para el LLM.

    Args:
        project_id: ID del proyecto
        max_entries: Máximo de entradas a incluir
        categories: Categorías a incluir (separadas por coma)
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()

        category_list = None
        if categories:
            category_list = [c.strip() for c in categories.split(",")]

        context = repo.generate_llm_context(
            project_id=project_id,
            max_entries=max_entries,
            categories=category_list,
        )

        return ApiResponse(
            success=True,
            data={
                "context": context,
                "length": len(context),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating glossary LLM context: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/glossary/export/publication", response_model=ApiResponse)
def export_glossary_for_publication(project_id: int) -> ApiResponse:
    """
    Exporta el glosario formateado para incluir en la publicación.

    Solo incluye términos marcados para publicación.
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        content = repo.export_for_publication(project_id)

        return ApiResponse(
            success=True,
            data={
                "content": content,
                "format": "markdown",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting glossary: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/glossary/import", response_model=ApiResponse)
def import_glossary(
    project_id: int,
    entries: list[dict] = Body(...),  # noqa: B008
    merge: bool = True,
) -> ApiResponse:
    """
    Importa entradas al glosario desde una lista JSON.

    Args:
        project_id: ID del proyecto
        entries: Lista de entradas con formato {term, definition, variants?, category?, ...}
        merge: Si True, actualiza existentes; si False, salta duplicados
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        created, updated = repo.import_from_dict(project_id, entries, merge=merge)

        return ApiResponse(
            success=True,
            data={
                "created": created,
                "updated": updated,
                "total_processed": len(entries),
            },
            message=f"Importados {created} términos nuevos, actualizados {updated}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing glossary: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/glossary/search", response_model=ApiResponse)
def search_glossary(
    project_id: int,
    q: str = Query(..., min_length=1, description="Término a buscar"),
) -> ApiResponse:
    """
    Busca un término en el glosario (por término principal o variantes).
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entry = repo.find_by_term_or_variant(project_id, q)

        if entry:
            return ApiResponse(
                success=True,
                data={
                    "found": True,
                    "entry": entry.to_dict(),
                }
            )
        else:
            return ApiResponse(
                success=True,
                data={
                    "found": False,
                    "entry": None,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching glossary: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/glossary/summary", response_model=ApiResponse)
def get_glossary_summary(project_id: int) -> ApiResponse:
    """
    Obtiene un resumen del glosario del proyecto.
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entries = repo.list_by_project(project_id)

        # Calcular estadísticas
        by_category = {}  # type: ignore[var-annotated]
        technical_count = 0
        invented_count = 0
        for_publication = 0

        for entry in entries:
            cat = entry.category or "general"
            by_category[cat] = by_category.get(cat, 0) + 1
            if entry.is_technical:
                technical_count += 1
            if entry.is_invented:
                invented_count += 1
            if entry.include_in_publication_glossary:
                for_publication += 1

        return ApiResponse(
            success=True,
            data={
                "total_entries": len(entries),
                "by_category": by_category,
                "technical_count": technical_count,
                "invented_count": invented_count,
                "for_publication_count": for_publication,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting glossary summary: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/glossary/suggestions", response_model=ApiResponse)
def get_glossary_suggestions(
    project_id: int,
    min_frequency: int = Query(2, ge=1, le=10, description="Frecuencia mínima"),
    max_frequency: int = Query(50, ge=5, le=200, description="Frecuencia máxima"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Confianza mínima"),
    use_entities: bool = Query(True, description="Usar entidades del NER"),
    max_suggestions: int = Query(50, ge=10, le=200, description="Máximo de sugerencias"),
) -> ApiResponse:
    """
    Extrae automáticamente términos candidatos para el glosario.

    Analiza el contenido del manuscrito para detectar:
    - Nombres propios no comunes (posibles personajes/lugares inventados)
    - Términos técnicos (acrónimos, terminología especializada)
    - Neologismos (palabras no reconocidas por el diccionario)
    - Entidades del NER con frecuencia significativa

    Args:
        project_id: ID del proyecto
        min_frequency: Frecuencia mínima para considerar un término (default: 2)
        max_frequency: Frecuencia máxima (términos muy comunes se ignoran) (default: 50)
        min_confidence: Confianza mínima para incluir en sugerencias (default: 0.5)
        use_entities: Usar entidades extraídas del NER (default: True)
        max_suggestions: Máximo de sugerencias a devolver (default: 50)
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        # Obtener términos existentes en el glosario para excluirlos
        from narrative_assistant.analysis.glossary_extractor import GlossaryExtractor
        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        existing_terms = repo.get_all_terms(project_id)

        # Obtener capítulos del proyecto
        chapters_result = project.get_chapters()
        if chapters_result.is_failure:
            return ApiResponse(
                success=False,
                error="No se pudieron obtener los capítulos del proyecto"
            )
        chapters = chapters_result.value

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "suggestions": [],
                    "message": "El proyecto no tiene contenido para analizar",
                }
            )

        # Preparar datos de capítulos
        chapters_data = [
            {"number": ch.number, "content": ch.content}
            for ch in chapters
            if ch.content and ch.content.strip()
        ]

        # Obtener entidades del NER si está habilitado
        entities = None
        if use_entities:
            try:
                entities_result = project.get_entities()
                if entities_result.is_success:
                    entities = [
                        {
                            "name": e.name,
                            "type": e.entity_type,
                            "mention_count": e.mention_count,
                            "first_mention_chapter": e.first_mention_chapter,
                        }
                        for e in entities_result.value
                    ]
            except Exception as e:
                logger.warning(f"No se pudieron obtener entidades: {e}")

        # Ejecutar extractor
        extractor = GlossaryExtractor(
            min_frequency=min_frequency,
            max_frequency=max_frequency,
            min_confidence=min_confidence,
            existing_terms=existing_terms,
        )

        extraction_result = extractor.extract(
            chapters=chapters_data,
            entities=entities,
        )

        if extraction_result.is_failure:
            return ApiResponse(
                success=False,
                error=f"Error en extracción: {extraction_result.error}"
            )

        report = extraction_result.value

        # Limitar sugerencias
        limited_suggestions = report.suggestions[:max_suggestions]  # type: ignore[union-attr]

        return ApiResponse(
            success=True,
            data={
                "suggestions": [s.to_dict() for s in limited_suggestions],
                "total_suggestions": len(report.suggestions),  # type: ignore[union-attr]
                "returned_suggestions": len(limited_suggestions),
                "total_unique_words": report.total_unique_words,  # type: ignore[union-attr]
                "chapters_analyzed": report.chapters_analyzed,  # type: ignore[union-attr]
                "proper_nouns_found": report.proper_nouns_found,  # type: ignore[union-attr]
                "technical_terms_found": report.technical_terms_found,  # type: ignore[union-attr]
                "potential_neologisms_found": report.potential_neologisms_found,  # type: ignore[union-attr]
                "existing_glossary_terms": len(existing_terms),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting glossary suggestions: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/glossary/suggestions/accept", response_model=ApiResponse)
def accept_glossary_suggestion(
    project_id: int,
    term: str = Body(..., embed=True),
    definition: str = Body("", embed=True),
    category: str = Body("general", embed=True),
    is_technical: bool = Body(False, embed=True),
    is_invented: bool = Body(False, embed=True),
    is_proper_noun: bool = Body(False, embed=True),
) -> ApiResponse:
    """
    Acepta una sugerencia y la añade al glosario.

    Args:
        project_id: ID del proyecto
        term: Término a añadir
        definition: Definición (puede estar vacía para completar después)
        category: Categoría del término
        is_technical: Es término técnico
        is_invented: Es término inventado
        is_proper_noun: Es nombre propio
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")

        from narrative_assistant.persistence.glossary import GlossaryEntry, GlossaryRepository

        repo = GlossaryRepository()

        # Verificar que no existe
        existing = repo.get_by_term(project_id, term)
        if existing:
            return ApiResponse(
                success=False,
                error=f"El término '{term}' ya existe en el glosario"
            )

        entry = GlossaryEntry(
            project_id=project_id,
            term=term,
            definition=definition or f"(Definición pendiente para '{term}')",
            category=category,
            is_technical=is_technical,
            is_invented=is_invented,
            is_proper_noun=is_proper_noun,
        )

        created = repo.create(entry)

        return ApiResponse(
            success=True,
            data=created.to_dict(),
            message=f"Término '{term}' añadido al glosario",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting glossary suggestion: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# Rutas con {entry_id} van AL FINAL de las rutas de glossary
# para no capturar rutas literales como /suggestions, /search, etc.

@router.get("/api/projects/{project_id}/glossary/{entry_id}", response_model=ApiResponse)
def get_glossary_entry(
    project_id: int,
    entry_id: int,
) -> ApiResponse:
    """
    Obtiene una entrada específica del glosario.
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entry = repo.get(entry_id)

        if not entry or entry.project_id != project_id:
            raise HTTPException(status_code=404, detail="Glossary entry not found")

        return ApiResponse(success=True, data=entry.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.put("/api/projects/{project_id}/glossary/{entry_id}", response_model=ApiResponse)
def update_glossary_entry(
    project_id: int,
    entry_id: int,
    request: GlossaryEntryRequest,
) -> ApiResponse:
    """
    Actualiza una entrada existente del glosario.
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        existing = repo.get(entry_id)

        if not existing or existing.project_id != project_id:
            raise HTTPException(status_code=404, detail="Glossary entry not found")

        # Actualizar campos
        existing.term = request.term
        existing.definition = request.definition  # type: ignore[assignment]
        existing.variants = request.variants  # type: ignore[attr-defined]
        existing.category = request.category  # type: ignore[assignment]
        existing.subcategory = request.subcategory  # type: ignore[attr-defined]
        existing.context_notes = request.context_notes  # type: ignore[attr-defined]
        existing.related_terms = request.related_terms  # type: ignore[attr-defined]
        existing.usage_example = request.usage_example  # type: ignore[attr-defined]
        existing.is_technical = request.is_technical  # type: ignore[attr-defined]
        existing.is_invented = request.is_invented  # type: ignore[attr-defined]
        existing.is_proper_noun = request.is_proper_noun  # type: ignore[attr-defined]
        existing.include_in_publication_glossary = request.include_in_publication_glossary  # type: ignore[attr-defined]

        repo.update(existing)

        return ApiResponse(
            success=True,
            data=existing.to_dict(),
            message=f"Término '{request.term}' actualizado",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/projects/{project_id}/glossary/{entry_id}", response_model=ApiResponse)
def delete_glossary_entry(
    project_id: int,
    entry_id: int,
) -> ApiResponse:
    """
    Elimina una entrada del glosario.
    """
    try:
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        _ = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        existing = repo.get(entry_id)

        if not existing or existing.project_id != project_id:
            raise HTTPException(status_code=404, detail="Glossary entry not found")

        term = existing.term
        repo.delete(entry_id)

        return ApiResponse(
            success=True,
            message=f"Término '{term}' eliminado del glosario",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/dictionary/lookup/{word}", response_model=ApiResponse)
def dictionary_lookup(word: str):
    """
    Busca una palabra en los diccionarios locales.

    Consulta múltiples fuentes (Wiktionary, sinónimos, personalizado)
    y devuelve información combinada.

    Args:
        word: Palabra a buscar

    Returns:
        ApiResponse con la entrada del diccionario
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.lookup(word)

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "found": False,
                    "word": word,
                    "message": str(result.error.user_message) if result.error else "No encontrado",
                    "external_links": manager.get_all_external_links(word),
                }
            )

        entry = result.value
        return ApiResponse(
            success=True,
            data={
                "found": True,
                "entry": entry.to_dict(),  # type: ignore[union-attr]
                "external_links": manager.get_all_external_links(word),
            }
        )

    except Exception as e:
        logger.error(f"Error looking up word '{word}': {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/dictionary/synonyms/{word}", response_model=ApiResponse)
def get_synonyms(word: str):
    """
    Obtiene sinónimos de una palabra.

    Args:
        word: Palabra a buscar

    Returns:
        ApiResponse con lista de sinónimos
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        synonyms = manager.get_synonyms(word)
        antonyms = manager.get_antonyms(word)

        return ApiResponse(
            success=True,
            data={
                "word": word,
                "synonyms": synonyms,
                "antonyms": antonyms,
            }
        )

    except Exception as e:
        logger.error(f"Error getting synonyms for '{word}': {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/dictionary/search", response_model=ApiResponse)
def dictionary_search(prefix: str, limit: int = 20):
    """
    Busca palabras que empiecen con un prefijo.

    Útil para autocompletado.

    Args:
        prefix: Prefijo a buscar
        limit: Máximo de resultados (default: 20)

    Returns:
        ApiResponse con lista de palabras
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        words = manager.search_prefix(prefix, limit)

        return ApiResponse(
            success=True,
            data={
                "prefix": prefix,
                "words": words,
                "count": len(words),
            }
        )

    except Exception as e:
        logger.error(f"Error searching prefix '{prefix}': {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/dictionary/status", response_model=ApiResponse)
def dictionary_status():
    """
    Obtiene el estado de los diccionarios.

    Returns:
        ApiResponse con información de cada fuente de diccionario
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        status = manager.get_status()

        return ApiResponse(
            success=True,
            data={
                "sources": status,
                "data_dir": str(manager.data_dir),
            }
        )

    except Exception as e:
        logger.error(f"Error getting dictionary status: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/dictionary/initialize", response_model=ApiResponse)
def initialize_dictionaries():
    """
    Inicializa los diccionarios si no existen.

    Crea las bases de datos con datos básicos.
    En el futuro, esto podría descargar datos completos.

    Returns:
        ApiResponse indicando éxito
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.ensure_dictionaries()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "message": "Diccionarios inicializados correctamente",
                "status": manager.get_status(),
            }
        )

    except Exception as e:
        logger.error(f"Error initializing dictionaries: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/dictionary/custom", response_model=ApiResponse)
def add_custom_word(request: CustomWordRequest):
    """
    Añade una palabra al diccionario personalizado.

    Args:
        request: Datos de la palabra

    Returns:
        ApiResponse indicando éxito
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.add_custom_word(
            word=request.word,
            definition=request.definition,  # type: ignore[attr-defined]
            category=request.category,  # type: ignore[attr-defined]
            synonyms=request.synonyms,  # type: ignore[attr-defined]
            antonyms=request.antonyms,  # type: ignore[attr-defined]
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "message": f"Palabra '{request.word}' añadida correctamente",
                "word": request.word,
            }
        )

    except Exception as e:
        logger.error(f"Error adding custom word: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/dictionary/custom/{word}", response_model=ApiResponse)
def remove_custom_word(word: str):
    """
    Elimina una palabra del diccionario personalizado.

    Args:
        word: Palabra a eliminar

    Returns:
        ApiResponse indicando éxito
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.remove_custom_word(word)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        removed = result.value
        if removed:
            return ApiResponse(
                success=True,
                data={"message": f"Palabra '{word}' eliminada", "removed": True}
            )
        else:
            return ApiResponse(
                success=True,
                data={"message": f"Palabra '{word}' no existía", "removed": False}
            )

    except Exception as e:
        logger.error(f"Error removing custom word: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/dictionary/custom", response_model=ApiResponse)
def list_custom_words():
    """
    Lista todas las palabras del diccionario personalizado.

    Returns:
        ApiResponse con lista de palabras
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        words = manager.list_custom_words()

        return ApiResponse(
            success=True,
            data={
                "words": words,
                "count": len(words),
            }
        )

    except Exception as e:
        logger.error(f"Error listing custom words: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/dictionary/external-links/{word}", response_model=ApiResponse)
def get_external_dictionary_links(word: str):
    """
    Obtiene enlaces a diccionarios externos para una palabra.

    Args:
        word: Palabra a buscar

    Returns:
        ApiResponse con enlaces a diccionarios externos
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager
        from narrative_assistant.dictionaries.models import EXTERNAL_DICTIONARIES

        manager = get_dictionary_manager()
        links = manager.get_all_external_links(word)

        # Añadir información adicional de cada diccionario
        detailed_links = []
        for name, url in links.items():
            ext_dict = EXTERNAL_DICTIONARIES.get(name)
            if ext_dict:
                detailed_links.append({
                    "name": ext_dict.name,
                    "id": name,
                    "url": url,
                    "description": ext_dict.description,
                    "requires_license": ext_dict.requires_license,
                })

        return ApiResponse(
            success=True,
            data={
                "word": word,
                "links": detailed_links,
            }
        )

    except Exception as e:
        logger.error(f"Error getting external links for '{word}': {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/search/similar", response_model=ApiResponse)
def search_similar_text(
    project_id: int,
    query: str = Body(..., embed=True, min_length=1, description="Texto a buscar"),
    limit: int = Body(10, embed=True, ge=1, le=50, description="Máximo de resultados"),
    min_similarity: float = Body(0.5, embed=True, ge=0.0, le=1.0, description="Similaridad mínima"),
) -> ApiResponse:
    """
    Busca fragmentos de texto similares al query usando embeddings semánticos.

    Devuelve fragmentos del manuscrito ordenados por similaridad semántica.

    Args:
        project_id: ID del proyecto
        query: Texto de búsqueda (min 1 char)
        limit: Máximo de resultados (1-50, default 10)
        min_similarity: Umbral mínimo de similaridad (0.0-1.0, default 0.5)

    Returns:
        Lista de fragmentos con sus posiciones, capítulos y scores de similaridad
    """
    try:
        # Validar proyecto
        result = deps.project_manager.get(project_id)  # type: ignore[attr-defined]
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        # Cargar texto completo desde capítulos
        if not deps.chapter_repository:
            raise HTTPException(status_code=500, detail="Chapter repository not initialized")

        chapters = deps.chapter_repository.get_by_project(project_id)
        full_text = "\n\n".join(ch.content for ch in chapters if ch.content)

        if not full_text.strip():
            return ApiResponse(
                success=True,
                data={"matches": [], "query": query, "count": 0}
            )

        # Cargar modelo de embeddings
        from narrative_assistant.nlp.embeddings import get_embeddings_model
        model = get_embeddings_model()

        # Split en fragmentos (ventanas de ~200 palabras con overlap)
        from narrative_assistant.nlp.chunking import TextChunker
        chunker = TextChunker(chunk_size=200, overlap=50)
        chunks = chunker.chunk_text(full_text)

        # Compute embeddings para query y chunks
        query_emb = model.encode([query])[0]
        chunk_texts = [c.text for c in chunks]
        chunk_embs = model.encode(chunk_texts)

        # Calcular similaridades coseno manualmente
        import numpy as np

        def cosine_similarity_single(a, b):
            """Calcula similaridad coseno entre un vector y una matriz de vectores."""
            # Normalizar query
            a_norm = a / np.linalg.norm(a)
            # Normalizar chunks (por filas)
            b_norms = np.linalg.norm(b, axis=1, keepdims=True)
            b_normalized = b / (b_norms + 1e-8)
            # Producto punto
            return np.dot(b_normalized, a_norm)

        similarities = cosine_similarity_single(query_emb, chunk_embs)

        # Filtrar por umbral y ordenar
        matches = []
        for i, (chunk, score) in enumerate(zip(chunks, similarities, strict=False)):
            if score >= min_similarity:
                matches.append({
                    "text": chunk.text,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "similarity": float(score),
                    "chapter_id": None,  # TODO: mapear a capítulo
                })

        # Ordenar por similaridad descendente
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        matches = matches[:limit]

        # Mapear a capítulos si existen
        if project.chapter_count > 0:
            from narrative_assistant.persistence.chapter import get_chapter_repository
            ch_repo = get_chapter_repository()
            chapters_result = ch_repo.get_all_by_project(project_id)

            if chapters_result.is_success:
                chapters = chapters_result.value
                # Ordenar capítulos por posición
                chapters_sorted = sorted(chapters, key=lambda c: c.position)

                # Mapear cada match a su capítulo
                for match in matches:
                    start = match["start_char"]
                    cumulative = 0

                    for chapter in chapters_sorted:
                        ch_len = len(chapter.content) if chapter.content else 0
                        if cumulative <= start < cumulative + ch_len:
                            match["chapter_id"] = chapter.id
                            match["chapter_title"] = chapter.title
                            match["start_char_in_chapter"] = start - cumulative
                            break
                        cumulative += ch_len

        return ApiResponse(
            success=True,
            data={
                "matches": matches,
                "query": query,
                "count": len(matches),
                "total_chunks": len(chunks),
            }
        )

    except Exception as e:
        logger.error(f"Error searching similar text: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error en búsqueda: {str(e)}")


