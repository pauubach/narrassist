"""
Router de colecciones / sagas (BK-07) + comparación antes/después (BK-05).

Endpoints:
- CRUD colecciones
- Gestión de proyectos en colecciones
- Entity links entre libros
- Sugerencias de links
- Análisis cross-book
- Comparación antes/después
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["collections"])


# ==================== Pydantic models ====================

class CreateCollectionRequest(BaseModel):
    name: str
    description: str = ""


class UpdateCollectionRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class CreateEntityLinkRequest(BaseModel):
    source_entity_id: int
    target_entity_id: int
    source_project_id: int
    target_project_id: int
    similarity: float = Field(default=1.0, ge=0.0, le=1.0)
    match_type: str = "manual"


# ==================== Helpers ====================

def _get_collection_repo():
    from narrative_assistant.persistence.collection import CollectionRepository
    return CollectionRepository()


def _get_comparison_service():
    from narrative_assistant.analysis.comparison import ComparisonService
    return ComparisonService()


def _get_cross_book_analyzer():
    from narrative_assistant.analysis.cross_book import CrossBookAnalyzer
    return CrossBookAnalyzer()


# ==================== BK-05: Comparación antes/después ====================

@router.get("/projects/{project_id}/comparison")
async def get_comparison(project_id: int):
    """Compara el estado actual contra el último snapshot pre-reanálisis."""
    service = _get_comparison_service()
    report = service.compare(project_id)
    if report is None:
        return {"message": "No hay análisis previo para comparar", "has_comparison": False}
    return {"has_comparison": True, **report.to_dict()}


# ==================== BK-07: Collections CRUD ====================

@router.post("/collections")
async def create_collection(request: CreateCollectionRequest):
    """Crea una nueva colección (saga/serie)."""
    repo = _get_collection_repo()
    collection_id = repo.create(request.name, request.description)
    return {"id": collection_id, "name": request.name}


@router.get("/collections")
async def list_collections():
    """Lista todas las colecciones."""
    repo = _get_collection_repo()
    collections = repo.list_all()
    return [
        {"id": c.id, "name": c.name, "description": c.description,
         "project_count": c.project_count, "created_at": c.created_at}
        for c in collections
    ]


@router.get("/collections/{collection_id}")
async def get_collection(collection_id: int):
    """Obtiene una colección con sus proyectos."""
    repo = _get_collection_repo()
    collection = repo.get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    projects = repo.get_projects(collection_id)
    links = repo.get_entity_links(collection_id)

    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "project_count": collection.project_count,
        "created_at": collection.created_at,
        "projects": projects,
        "entity_link_count": len(links),
    }


@router.put("/collections/{collection_id}")
async def update_collection(collection_id: int, request: UpdateCollectionRequest):
    """Actualiza nombre y/o descripción de una colección."""
    repo = _get_collection_repo()
    repo.update(collection_id, request.name, request.description)
    return {"success": True}


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: int):
    """Elimina una colección (los proyectos se desvinculan, no se borran)."""
    repo = _get_collection_repo()
    repo.delete(collection_id)
    return {"success": True}


# ==================== Project membership ====================

@router.post("/collections/{collection_id}/projects/{project_id}")
async def add_project_to_collection(collection_id: int, project_id: int, order: int = 0):
    """Añade un proyecto a la colección."""
    repo = _get_collection_repo()
    result = repo.add_project(collection_id, project_id, order)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    return result


@router.delete("/collections/{collection_id}/projects/{project_id}")
async def remove_project_from_collection(collection_id: int, project_id: int):
    """Quita un proyecto de la colección (limpia entity links asociados)."""
    repo = _get_collection_repo()
    repo.remove_project(collection_id, project_id)
    return {"success": True}


# ==================== Entity links ====================

@router.get("/collections/{collection_id}/entity-links")
async def get_entity_links(collection_id: int):
    """Lista todos los enlaces de entidades de la colección."""
    repo = _get_collection_repo()
    links = repo.get_entity_links(collection_id)
    return [
        {
            "id": l.id, "collection_id": l.collection_id,
            "source_entity_id": l.source_entity_id,
            "target_entity_id": l.target_entity_id,
            "source_project_id": l.source_project_id,
            "target_project_id": l.target_project_id,
            "source_entity_name": l.source_entity_name,
            "target_entity_name": l.target_entity_name,
            "source_project_name": l.source_project_name,
            "target_project_name": l.target_project_name,
            "similarity": l.similarity,
            "match_type": l.match_type,
        }
        for l in links
    ]


@router.post("/collections/{collection_id}/entity-links")
async def create_entity_link(collection_id: int, request: CreateEntityLinkRequest):
    """Crea un enlace entre entidades de distintos libros."""
    repo = _get_collection_repo()
    result = repo.create_entity_link(
        collection_id=collection_id,
        source_entity_id=request.source_entity_id,
        target_entity_id=request.target_entity_id,
        source_project_id=request.source_project_id,
        target_project_id=request.target_project_id,
        similarity=request.similarity,
        match_type=request.match_type,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    return result


@router.delete("/collections/{collection_id}/entity-links/{link_id}")
async def delete_entity_link(collection_id: int, link_id: int):
    """Elimina un enlace de entidades."""
    repo = _get_collection_repo()
    repo.delete_entity_link(link_id)
    return {"success": True}


@router.get("/collections/{collection_id}/entity-link-suggestions")
async def get_link_suggestions(collection_id: int, threshold: float = Query(default=0.7, ge=0.0, le=1.0)):
    """Sugiere posibles enlaces entre entidades de distintos libros."""
    repo = _get_collection_repo()
    suggestions = repo.get_link_suggestions(collection_id, threshold)
    return [
        {
            "source_entity_id": s.source_entity_id,
            "source_entity_name": s.source_entity_name,
            "source_entity_type": s.source_entity_type,
            "source_project_id": s.source_project_id,
            "source_project_name": s.source_project_name,
            "target_entity_id": s.target_entity_id,
            "target_entity_name": s.target_entity_name,
            "target_entity_type": s.target_entity_type,
            "target_project_id": s.target_project_id,
            "target_project_name": s.target_project_name,
            "similarity": s.similarity,
            "match_type": s.match_type,
        }
        for s in suggestions
    ]


# ==================== Cross-book analysis ====================

@router.get("/collections/{collection_id}/cross-book-analysis")
async def cross_book_analysis(collection_id: int):
    """Ejecuta análisis cross-book: compara atributos de entidades enlazadas."""
    analyzer = _get_cross_book_analyzer()
    report = analyzer.analyze(collection_id)
    return report.to_dict()
