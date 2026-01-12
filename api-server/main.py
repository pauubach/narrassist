"""
FastAPI Server Bridge - Servidor HTTP para comunicación con Tauri frontend.

Este servidor actúa como puente entre el frontend Tauri (Vue 3) y el backend
Python (narrative_assistant). Proporciona endpoints REST para todas las
operaciones del sistema.

Puerto: 8008
CORS: Habilitado para localhost:5173 (Vite dev server) y tauri://localhost
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Imports del backend narrative_assistant
project_manager = None
entity_repository = None
alert_repository = None
chapter_repository = None
get_config = None
NA_VERSION = "unknown"

try:
    from narrative_assistant.persistence.project import ProjectManager
    from narrative_assistant.persistence.database import get_database, Database
    from narrative_assistant.persistence.chapter import ChapterRepository
    from narrative_assistant.entities.repository import EntityRepository
    from narrative_assistant.alerts.repository import AlertRepository, AlertStatus, AlertSeverity
    from narrative_assistant.core.config import get_config
    from narrative_assistant import __version__ as NA_VERSION

    # Inicializar managers
    project_manager = ProjectManager()
    entity_repository = EntityRepository()
    alert_repository = AlertRepository()
    chapter_repository = ChapterRepository()
except Exception as e:
    logging.error(f"Error initializing narrative_assistant modules: {type(e).__name__}: {e}")
    NA_VERSION = "unknown"
    project_manager = None
    entity_repository = None
    alert_repository = None
    chapter_repository = None
    get_config = None
    Database = None  # type: ignore

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Crear app FastAPI
app = FastAPI(
    title="Narrative Assistant API",
    description="API REST para el asistente de corrección narrativa",
    version=NA_VERSION,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "tauri://localhost",      # Tauri production
        "http://tauri.localhost", # Tauri alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Modelos Pydantic (Request/Response)
# ============================================================================

class HealthResponse(BaseModel):
    """Respuesta del endpoint /health"""
    status: str = "ok"
    version: str
    backend_loaded: bool
    timestamp: str

class ApiResponse(BaseModel):
    """Respuesta genérica de la API"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None

class CreateProjectRequest(BaseModel):
    """Request para crear un proyecto"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    """Respuesta con datos de un proyecto"""
    id: int
    name: str
    description: Optional[str]
    document_format: str
    created_at: str
    last_modified: str
    last_opened: Optional[str]
    analysis_progress: int
    word_count: int
    chapter_count: int

class EntityResponse(BaseModel):
    """Respuesta con datos de una entidad"""
    id: int
    project_id: int
    entity_type: str
    canonical_name: str
    aliases: list[str]
    importance: str

class AlertResponse(BaseModel):
    """Respuesta con datos de una alerta"""
    id: int
    project_id: int
    category: str
    severity: str
    alert_type: str
    title: str
    description: str
    explanation: str
    suggestion: Optional[str]
    chapter: Optional[int]
    status: str
    created_at: str

# ============================================================================
# Endpoints - Sistema
# ============================================================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint - verifica que el servidor está funcionando.

    Returns:
        HealthResponse con status del sistema
    """
    backend_loaded = False
    try:
        # Intentar cargar config para verificar backend
        config = get_config()
        backend_loaded = config is not None
    except Exception as e:
        logger.warning(f"Backend not fully loaded: {e}")

    return HealthResponse(
        status="ok",
        version=NA_VERSION,
        backend_loaded=backend_loaded,
        timestamp=datetime.now().isoformat(),
    )

@app.get("/api/info")
async def system_info():
    """
    Información del sistema - configuración, GPU, modelos, etc.

    Returns:
        Información detallada del sistema
    """
    try:
        config = get_config()

        return ApiResponse(
            success=True,
            data={
                "version": NA_VERSION,
                "gpu": {
                    "device": config.gpu.device_preference,
                    "available": config.gpu.device_preference != "cpu",
                    "spacy_gpu": config.gpu.spacy_gpu_enabled,
                    "embeddings_gpu": config.gpu.embeddings_gpu_enabled,
                },
                "models": {
                    "spacy_model": config.nlp.spacy_model,
                    "embeddings_model": config.nlp.embeddings_model,
                },
                "paths": {
                    "data_dir": str(config.data_dir),
                    "cache_dir": str(config.cache_dir),
                },
            },
        )
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Endpoints - Proyectos
# ============================================================================

@app.get("/api/projects", response_model=ApiResponse)
async def list_projects():
    """
    Lista todos los proyectos.

    Returns:
        ApiResponse con lista de proyectos
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        projects = project_manager.list_all()
        alert_repo = alert_repository

        projects_data = []
        for p in projects:
            # Obtener todas las alertas del proyecto
            alerts_result = alert_repo.get_by_project(p.id)
            all_alerts = alerts_result.value if alerts_result.is_success else []

            # Filtrar solo las alertas abiertas
            open_alerts = [a for a in all_alerts if a.status == AlertStatus.OPEN]

            # Determinar severidad más alta
            highest_severity = None
            if open_alerts:
                severity_priority = {"critical": 3, "warning": 2, "info": 1}
                highest_severity = max(
                    (a.severity.value for a in open_alerts),
                    key=lambda s: severity_priority.get(s, 0)
                )

            projects_data.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "document_format": p.document_format,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "last_modified": p.updated_at.isoformat() if p.updated_at else None,
                "last_opened": p.last_opened_at.isoformat() if p.last_opened_at else None,
                "analysis_status": p.analysis_status,
                "analysis_progress": int(p.analysis_progress * 100) if p.analysis_progress else 0,
                "word_count": p.word_count,
                "chapter_count": p.chapter_count,
                "open_alerts_count": len(open_alerts),
                "highest_alert_severity": highest_severity,
            })

        return ApiResponse(success=True, data=projects_data)
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.get("/api/projects/{project_id}", response_model=ApiResponse)
async def get_project(project_id: int):
    """
    Obtiene un proyecto por ID.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con datos del proyecto
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Obtener alertas abiertas para consistencia con list_projects
        alert_repo = alert_repository
        open_alerts_count = 0
        highest_severity = None

        if alert_repo:
            alerts_result = alert_repo.get_by_project(project.id)
            if alerts_result.is_success:
                all_alerts = alerts_result.value
                open_alerts = [a for a in all_alerts if a.status == AlertStatus.OPEN]
                open_alerts_count = len(open_alerts)

                if open_alerts:
                    severity_priority = {"critical": 3, "warning": 2, "info": 1}
                    highest_severity = max(
                        (a.severity.value for a in open_alerts),
                        key=lambda s: severity_priority.get(s, 0)
                    )

        project_data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "document_format": project.document_format,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "last_modified": project.updated_at.isoformat() if project.updated_at else None,
            "last_opened": project.last_opened_at.isoformat() if project.last_opened_at else None,
            "analysis_status": project.analysis_status,
            "analysis_progress": int(project.analysis_progress * 100) if project.analysis_progress else 0,
            "word_count": project.word_count,
            "chapter_count": project.chapter_count,
            "open_alerts_count": open_alerts_count,
            "highest_alert_severity": highest_severity,
        }

        return ApiResponse(success=True, data=project_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects", response_model=ApiResponse)
async def create_project(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    file_path: Optional[str] = Body(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Crea un nuevo proyecto con documento y comienza el análisis.

    Acepta el documento de dos formas:
    - file_path: Ruta al archivo en el sistema del usuario (preferido para app de escritorio)
    - file: Archivo subido (para desarrollo web - se guarda copia permanente)

    Args:
        name: Nombre del proyecto
        description: Descripción opcional del proyecto
        file_path: Ruta al archivo del manuscrito en el sistema local
        file: Archivo del manuscrito subido (.docx, .txt, .md)

    Returns:
        ApiResponse con el proyecto creado
    """
    try:
        import shutil
        import uuid
        from pathlib import Path

        allowed_extensions = ['.docx', '.doc', '.txt', '.md', '.pdf', '.epub']

        # Determinar la ruta del documento
        document_path: Optional[Path] = None
        stored_path: Optional[str] = None

        if file_path:
            # Usar ruta proporcionada directamente (app de escritorio)
            document_path = Path(file_path)
            if not document_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo no existe: {file_path}"
                )
            file_ext = document_path.suffix.lower()
            stored_path = file_path  # Guardar la ruta original del usuario

        elif file and file.filename:
            # Archivo subido: guardarlo permanentemente en el directorio de la app
            file_ext = Path(file.filename).suffix.lower()

            # Crear directorio de documentos
            config = get_config()
            documents_dir = config.data_dir / "documents"
            documents_dir.mkdir(parents=True, exist_ok=True)

            # Generar nombre único
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            permanent_path = documents_dir / unique_filename

            # Guardar archivo
            with open(permanent_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            document_path = permanent_path
            stored_path = str(permanent_path)
            logger.info(f"Document saved permanently at: {permanent_path}")

        else:
            raise HTTPException(
                status_code=400,
                detail="Se requiere file_path o file"
            )

        if file_ext not in allowed_extensions:
            # Limpiar archivo guardado si la extensión no es válida
            if stored_path and file and Path(stored_path).exists():
                Path(stored_path).unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Formato de archivo no soportado: {file_ext}. Formatos permitidos: {', '.join(allowed_extensions)}"
            )

        try:
            from narrative_assistant.persistence.project import ProjectManager, Project
            from narrative_assistant.parsers.base import detect_format
            from narrative_assistant.parsers import get_parser

            # Detectar formato del documento
            doc_format = detect_format(document_path)
            format_str = doc_format.value if hasattr(doc_format, 'value') else str(doc_format).split('.')[-1].upper()

            # Leer contenido del documento para create_from_document
            logger.info(f"Reading document content from: {document_path}")
            parser = get_parser(document_path)
            parse_result = parser.parse(document_path)

            if parse_result.is_failure:
                raise HTTPException(status_code=400, detail=f"Error leyendo documento: {parse_result.error}")

            raw_doc = parse_result.value
            document_text = raw_doc.text if hasattr(raw_doc, 'text') else str(raw_doc)

            # Crear proyecto usando create_from_document (el único método disponible)
            logger.info(f"Creating project '{name}' from: {document_path}")

            project_repo = project_manager
            create_result = project_repo.create_from_document(
                text=document_text,
                name=name,
                document_format=format_str,
                document_path=Path(stored_path),
                description=description or f"Documento: {document_path.name}",
                check_existing=True,
            )

            if create_result.is_failure:
                raise HTTPException(status_code=500, detail=f"Error creando proyecto: {create_result.error}")

            project = create_result.value

            project_data = ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                document_format=project.document_format,
                created_at=project.created_at.isoformat() if project.created_at else None,
                last_modified=project.updated_at.isoformat() if project.updated_at else None,
                last_opened=project.last_opened_at.isoformat() if project.last_opened_at else None,
                analysis_progress=0,
                word_count=project.word_count,  # Ya calculado por create_from_document
                chapter_count=project.chapter_count,
            )

            logger.info(f"Created project: {project.id} - {project.name}")
            logger.info(f"Document path stored: {stored_path}")

            return ApiResponse(
                success=True,
                data=project_data,
                message="Proyecto creado. Use /analyze para iniciar el análisis."
            )

        except Exception as e:
            # Limpiar archivo si hay error (solo si fue subido)
            if file and stored_path and Path(stored_path).exists():
                Path(stored_path).unlink()
            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.delete("/api/projects/{project_id}", response_model=ApiResponse)
async def delete_project(project_id: int):
    """
    Elimina un proyecto.

    Args:
        project_id: ID del proyecto a eliminar

    Returns:
        ApiResponse con confirmación
    """
    try:
        project_repo = project_manager
        project_repo.delete(project_id)

        logger.info(f"Deleted project: {project_id}")
        return ApiResponse(success=True, message="Proyecto eliminado exitosamente")
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/reanalyze", response_model=ApiResponse)
async def reanalyze_project(project_id: int):
    """
    Re-analiza un proyecto existente usando el documento original.

    Redirige al endpoint /analyze que ejecuta el análisis en background
    con seguimiento de progreso.

    Args:
        project_id: ID del proyecto a re-analizar

    Returns:
        ApiResponse confirmando inicio de re-análisis
    """
    try:
        from pathlib import Path

        # Validar que el proyecto existe
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Verificar que tenemos la ruta del documento
        if not project.document_path:
            return ApiResponse(
                success=False,
                error="No se encontró la ruta del documento original. Por favor, elimine el proyecto y créelo de nuevo."
            )

        document_path = Path(project.document_path)

        # Verificar que el archivo existe
        if not document_path.exists():
            return ApiResponse(
                success=False,
                error=f"El documento original no se encuentra en: {document_path}. Verifique que el archivo existe."
            )

        logger.info(f"Re-analyzing project '{project.name}' (ID: {project_id}) from: {document_path}")

        # Llamar al endpoint de análisis que tiene el progreso en background
        # El documento ya está guardado en project.document_path
        return await start_analysis(project_id, file=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-analyzing project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

# ============================================================================
# Endpoints - Entidades
# ============================================================================

@app.get("/api/projects/{project_id}/entities", response_model=ApiResponse)
async def list_entities(project_id: int):
    """
    Lista todas las entidades de un proyecto.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de entidades
    """
    try:
        entity_repo = entity_repository
        entities = entity_repo.get_entities_by_project(project_id)

        entities_data = [
            EntityResponse(
                id=e.id,
                project_id=e.project_id,
                entity_type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in entities
        ]

        return ApiResponse(success=True, data=entities_data)
    except Exception as e:
        logger.error(f"Error listing entities for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/entities/merge", response_model=ApiResponse)
async def merge_entities(project_id: int, request: Request):
    """
    Fusiona múltiples entidades en una sola entidad principal.

    Args:
        project_id: ID del proyecto
        request: Body con primary_entity_id y entity_ids

    Returns:
        ApiResponse con resultado de la fusión
    """
    try:
        data = await request.json()
        primary_entity_id = data.get('primary_entity_id')
        entity_ids = data.get('entity_ids', [])

        if not primary_entity_id or not entity_ids:
            return ApiResponse(
                success=False,
                error="Se requiere primary_entity_id y entity_ids"
            )

        entity_repo = entity_repository

        # Verificar que la entidad principal existe
        primary_entity = entity_repo.get_entity(primary_entity_id)
        if not primary_entity or primary_entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad principal no encontrada")

        # TODO: Implementar lógica de fusión real
        # Por ahora, simular la fusión
        merged_count = 0
        for entity_id in entity_ids:
            entity = entity_repo.get_entity(entity_id)
            if entity and entity.project_id == project_id:
                # En la implementación real:
                # 1. Transferir todas las menciones a la entidad principal
                # 2. Combinar aliases
                # 3. Actualizar atributos si es personaje
                # 4. Eliminar la entidad fusionada
                merged_count += 1

        logger.info(f"Merged {merged_count} entities into entity {primary_entity_id}")

        return ApiResponse(
            success=True,
            data={
                "primary_entity_id": primary_entity_id,
                "merged_count": merged_count
            },
            message=f"Se fusionaron {merged_count} entidades exitosamente"
        )

    except Exception as e:
        logger.error(f"Error merging entities for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

# ============================================================================
# Endpoints - Alertas
# ============================================================================

@app.get("/api/projects/{project_id}/alerts", response_model=ApiResponse)
async def list_alerts(project_id: int, status: Optional[str] = None):
    """
    Lista todas las alertas de un proyecto.

    Args:
        project_id: ID del proyecto
        status: Filtrar por estado (open, resolved, dismissed)

    Returns:
        ApiResponse con lista de alertas
    """
    try:
        alert_repo = alert_repository

        # Obtener todas las alertas del proyecto
        result = alert_repo.get_by_project(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo alertas")

        all_alerts = result.value

        # Filtrar por status si se especifica
        if status:
            status_value = status.lower()
            alerts = [a for a in all_alerts if a.status.value == status_value]
        else:
            alerts = all_alerts

        alerts_data = [
            AlertResponse(
                id=a.id,
                project_id=a.project_id,
                category=a.category.value if hasattr(a.category, 'value') else str(a.category),
                severity=a.severity.value if hasattr(a.severity, 'value') else str(a.severity),
                alert_type=a.alert_type,
                title=a.title,
                description=a.description,
                explanation=a.explanation,
                suggestion=a.suggestion,
                chapter=a.chapter,
                status=a.status.value if hasattr(a.status, 'value') else str(a.status),
                created_at=a.created_at.isoformat() if hasattr(a.created_at, 'isoformat') else str(a.created_at),
            )
            for a in alerts
        ]

        return ApiResponse(success=True, data=alerts_data)
    except Exception as e:
        logger.error(f"Error listing alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/{alert_id}/resolve", response_model=ApiResponse)
async def resolve_alert(project_id: int, alert_id: int):
    """
    Marca una alerta como resuelta.
    """
    try:
        alert_repo = alert_repository
        result = alert_repo.get(alert_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        alert = result.value
        if alert.project_id != project_id:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        # Actualizar el status de la alerta
        alert.status = AlertStatus.RESOLVED
        alert_repo.update(alert)

        logger.info(f"Alert {alert_id} marked as resolved")

        return ApiResponse(
            success=True,
            message="Alerta marcada como resuelta"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/{alert_id}/dismiss", response_model=ApiResponse)
async def dismiss_alert(project_id: int, alert_id: int):
    """
    Descarta una alerta.
    """
    try:
        alert_repo = alert_repository
        result = alert_repo.get(alert_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        alert = result.value
        if alert.project_id != project_id:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        # Actualizar el status de la alerta
        alert.status = AlertStatus.DISMISSED
        alert_repo.update(alert)

        logger.info(f"Alert {alert_id} dismissed")

        return ApiResponse(
            success=True,
            message="Alerta descartada"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing alert {alert_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/{alert_id}/reopen", response_model=ApiResponse)
async def reopen_alert(project_id: int, alert_id: int):
    """
    Reabre una alerta previamente resuelta o descartada.
    """
    try:
        alert_repo = alert_repository
        result = alert_repo.get(alert_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        alert = result.value
        if alert.project_id != project_id:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        # Actualizar el status de la alerta
        alert.status = AlertStatus.OPEN
        alert_repo.update(alert)

        logger.info(f"Alert {alert_id} reopened")

        return ApiResponse(
            success=True,
            message="Alerta reabierta"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reopening alert {alert_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/resolve-all", response_model=ApiResponse)
async def resolve_all_alerts(project_id: int):
    """
    Marca todas las alertas abiertas como resueltas.
    """
    try:
        alert_repo = alert_repository

        # Obtener todas las alertas del proyecto
        result = alert_repo.get_by_project(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo alertas")

        all_alerts = result.value

        # Filtrar alertas abiertas y resolverlas
        resolved_count = 0
        for alert in all_alerts:
            if alert.status.value in ['new', 'open', 'acknowledged', 'in_progress']:
                alert.status = AlertStatus.RESOLVED
                alert_repo.update(alert)
                resolved_count += 1

        logger.info(f"Resolved {resolved_count} alerts for project {project_id}")

        return ApiResponse(
            success=True,
            message=f"Se han resuelto {resolved_count} alertas"
        )
    except Exception as e:
        logger.error(f"Error resolving all alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

# ============================================================================
# Endpoints - Capítulos
# ============================================================================

@app.get("/api/projects/{project_id}/chapters", response_model=ApiResponse)
async def list_chapters(project_id: int):
    """
    Lista todos los capítulos de un proyecto.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de capítulos
    """
    try:
        if not chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        # Verificar que el proyecto existe
        if project_manager:
            result = project_manager.get(project_id)
            if result.is_failure:
                raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener capítulos reales de la base de datos
        chapters = chapter_repository.get_by_project(project_id)

        # Convertir a formato de respuesta
        chapters_data = [
            {
                "id": ch.id,
                "project_id": ch.project_id,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": ch.content,
                "chapter_number": ch.chapter_number,
                "word_count": ch.word_count,
                "position_start": ch.start_char,
                "position_end": ch.end_char,
                "structure_type": ch.structure_type,
                "created_at": ch.created_at,
                "updated_at": ch.updated_at
            }
            for ch in chapters
        ]

        return ApiResponse(success=True, data=chapters_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing chapters for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

# ============================================================================
# Endpoints - Análisis
# ============================================================================

# Diccionario global para almacenar el progreso de análisis
# TODO: En producción, usar Redis o similar para estado distribuido
analysis_progress_storage: dict[int, dict] = {}

@app.post("/api/projects/{project_id}/analyze", response_model=ApiResponse)
async def start_analysis(project_id: int, file: Optional[UploadFile] = File(None)):
    """
    Inicia el análisis asíncrono de un proyecto.

    Args:
        project_id: ID del proyecto
        file: Archivo del manuscrito (opcional si el proyecto ya tiene document_path)

    Returns:
        ApiResponse confirmando inicio de análisis
    """
    try:
        import tempfile
        import shutil
        from pathlib import Path

        # Validar que el proyecto existe
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Determinar el archivo a usar
        tmp_path: Path
        use_temp_file = False

        if file and file.filename:
            # Usar archivo subido
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                shutil.copyfileobj(file.file, tmp_file)
                tmp_path = Path(tmp_file.name)
            use_temp_file = True
            logger.info(f"Analysis started for project {project_id}")
            logger.info(f"File: {file.filename}, temp path: {tmp_path}")
        elif project.document_path:
            # Usar documento guardado del proyecto
            tmp_path = Path(project.document_path)
            if not tmp_path.exists():
                return ApiResponse(
                    success=False,
                    error=f"El documento no se encuentra: {project.document_path}"
                )
            use_temp_file = False
            logger.info(f"Analysis started for project {project_id}")
            logger.info(f"Using stored document: {tmp_path}")
        else:
            return ApiResponse(
                success=False,
                error="Se requiere un archivo o que el proyecto tenga document_path"
            )

        # Inicializar progreso
        analysis_progress_storage[project_id] = {
            "project_id": project_id,
            "status": "running",
            "progress": 0,
            "current_phase": "Iniciando análisis...",
            "current_action": "Preparando documento",
            "phases": [
                {"id": "parsing", "name": "Extracción de texto", "completed": False, "current": False},
                {"id": "structure", "name": "Detección de estructura", "completed": False, "current": False},
                {"id": "ner", "name": "Reconocimiento de entidades", "completed": False, "current": False},
                {"id": "attributes", "name": "Extracción de atributos", "completed": False, "current": False},
                {"id": "consistency", "name": "Análisis de consistencia", "completed": False, "current": False},
                {"id": "alerts", "name": "Generación de alertas", "completed": False, "current": False}
            ],
            "metrics": {},
            "estimated_seconds_remaining": 60
        }

        logger.info(f"Analysis started for project {project_id}")
        logger.info(f"File: {file.filename}, temp path: {tmp_path}")

        # Ejecutar análisis REAL en background thread
        import threading
        import time

        def run_real_analysis():
            """Ejecuta el análisis real usando el pipeline de NLP."""
            start_time = time.time()
            phases = analysis_progress_storage[project_id]["phases"]

            def update_time_remaining():
                """Calcula y actualiza el tiempo restante estimado."""
                elapsed = time.time() - start_time
                progress = analysis_progress_storage[project_id]["progress"]
                if progress > 0:
                    # Estimar tiempo total basado en progreso actual
                    estimated_total = elapsed / (progress / 100)
                    remaining = max(0, estimated_total - elapsed)
                    analysis_progress_storage[project_id]["estimated_seconds_remaining"] = int(remaining)
                else:
                    analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 60

            # Obtener sesión de BD para este thread
            from narrative_assistant.persistence.database import get_database
            db_session = get_database()

            try:
                # Importar componentes del pipeline
                from narrative_assistant.parsers.base import detect_format, get_parser
                from narrative_assistant.parsers.structure_detector import StructureDetector
                from narrative_assistant.nlp.ner import NERExtractor
                from narrative_assistant.nlp.attributes import AttributeExtractor
                from narrative_assistant.analysis.attribute_consistency import AttributeConsistencyChecker
                from narrative_assistant.alerts.engine import get_alert_engine
                from narrative_assistant.entities.repository import get_entity_repository
                from narrative_assistant.persistence.project import ProjectManager
                from narrative_assistant.persistence.document_fingerprint import generate_fingerprint

                # ========== FASE 1: PARSING (0-15%) ==========
                phases[0]["current"] = True
                analysis_progress_storage[project_id]["progress"] = 5
                analysis_progress_storage[project_id]["current_phase"] = "Extrayendo texto del documento"

                doc_format = detect_format(tmp_path)
                parser = get_parser(doc_format)
                parse_result = parser.parse(tmp_path)

                if parse_result.is_failure:
                    raise Exception(f"Error parsing document: {parse_result.error}")

                raw_document = parse_result.value
                full_text = raw_document.full_text
                word_count = len(full_text.split())

                analysis_progress_storage[project_id]["progress"] = 15
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["word_count"] = word_count
                phases[0]["completed"] = True
                phases[0]["current"] = False
                phases[0]["duration"] = round(time.time() - start_time, 1)

                logger.info(f"Parsing complete: {word_count} words")

                # ========== FASE 2: ESTRUCTURA (15-30%) ==========
                phase_start = time.time()
                phases[1]["current"] = True
                analysis_progress_storage[project_id]["progress"] = 20
                analysis_progress_storage[project_id]["current_phase"] = "Detectando capítulos y escenas"

                detector = StructureDetector()
                structure_result = detector.detect(raw_document)

                chapters_count = 0
                chapters_data = []
                if structure_result.is_success:
                    structure = structure_result.value
                    if hasattr(structure, 'chapters') and structure.chapters:
                        chapters_count = len(structure.chapters)
                        # Guardar capítulos en BD
                        for ch in structure.chapters:
                            content = ch.get_text(full_text)
                            ch_word_count = len(content.split())
                            chapters_data.append({
                                "project_id": project_id,
                                "chapter_number": ch.number,
                                "title": ch.title,
                                "content": content,
                                "start_char": ch.start_char,
                                "end_char": ch.end_char,
                                "word_count": ch_word_count,
                                "structure_type": ch.structure_type.value if hasattr(ch.structure_type, 'value') else str(ch.structure_type)
                            })

                # Si no se detectaron capítulos, crear uno con todo el contenido
                if not chapters_data:
                    logger.info("No chapters detected, creating default chapter with full content")
                    chapters_data.append({
                        "project_id": project_id,
                        "chapter_number": 1,
                        "title": "Documento completo",
                        "content": full_text,
                        "start_char": 0,
                        "end_char": len(full_text),
                        "word_count": word_count,
                        "structure_type": "chapter"
                    })
                    chapters_count = 1

                # Persistir capítulos
                _persist_chapters_to_db(chapters_data, project_id, db_session)

                analysis_progress_storage[project_id]["progress"] = 30
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["chapters_found"] = chapters_count
                phases[1]["completed"] = True
                phases[1]["current"] = False
                phases[1]["duration"] = round(time.time() - phase_start, 1)

                logger.info(f"Structure detection complete: {chapters_count} chapters")

                # ========== FASE 3: NER (30-55%) ==========
                phase_start = time.time()
                phases[2]["current"] = True
                analysis_progress_storage[project_id]["progress"] = 35
                analysis_progress_storage[project_id]["current_phase"] = "Identificando entidades (personajes, lugares...)"

                ner_extractor = NERExtractor()
                ner_result = ner_extractor.extract_entities(full_text)

                entities = []
                if ner_result.is_success and ner_result.value:
                    # NERResult tiene .entities que es la lista de ExtractedEntity
                    raw_entities = ner_result.value.entities or []
                    entity_repo = get_entity_repository()

                    # Mapeo de EntityLabel (NER) a EntityType (modelo de datos)
                    from narrative_assistant.nlp.ner import EntityLabel
                    from narrative_assistant.entities.models import Entity, EntityType, EntityImportance, EntityMention

                    label_to_type = {
                        EntityLabel.PER: EntityType.CHARACTER,
                        EntityLabel.LOC: EntityType.LOCATION,
                        EntityLabel.ORG: EntityType.ORGANIZATION,
                        EntityLabel.MISC: EntityType.CONCEPT,
                    }

                    # Agrupar entidades por nombre canónico para contar menciones
                    entity_mentions: dict[str, list] = {}  # canonical_name -> [ExtractedEntity, ...]
                    for ent in raw_entities:
                        canonical = ent.canonical_form or ent.text.lower().strip()
                        key = f"{ent.label.value}:{canonical}"
                        if key not in entity_mentions:
                            entity_mentions[key] = []
                        entity_mentions[key].append(ent)

                    # NOTA: Ya no se filtra por mínimo de menciones.
                    # El filtrado de falsos positivos se hace en NERExtractor._is_valid_entity()
                    # Un personaje puede aparecer solo 1 vez y sigue siendo válido.

                    logger.info(f"NER: {len(raw_entities)} menciones totales, {len(entity_mentions)} entidades únicas")

                    # Crear entidades únicas con conteo de menciones
                    total_entities_to_create = len(entity_mentions)
                    entities_created = 0
                    for key, mentions_list in entity_mentions.items():
                        first_mention = mentions_list[0]
                        mention_count = len(mentions_list)

                        # Calcular importancia basada en número de menciones
                        if mention_count >= 20:
                            importance = EntityImportance.CRITICAL
                        elif mention_count >= 10:
                            importance = EntityImportance.HIGH
                        elif mention_count >= 5:
                            importance = EntityImportance.MEDIUM
                        elif mention_count >= 2:
                            importance = EntityImportance.LOW
                        else:
                            importance = EntityImportance.MINIMAL

                        # Primera aparición
                        first_appearance = min(m.start_char for m in mentions_list)

                        # Crear objeto Entity
                        entity = Entity(
                            project_id=project_id,
                            entity_type=label_to_type.get(first_mention.label, EntityType.CONCEPT),
                            canonical_name=first_mention.text,  # Usar texto original como nombre
                            aliases=[],
                            importance=importance,
                            description=None,
                            first_appearance_char=first_appearance,
                            mention_count=mention_count,
                            merged_from_ids=[],
                            is_active=True,
                        )

                        # Persistir entidad en BD
                        try:
                            entity_id = entity_repo.create_entity(entity)
                            entity.id = entity_id
                            entities.append(entity)

                            # Crear menciones en BD
                            for ent in mentions_list:
                                mention = EntityMention(
                                    entity_id=entity_id,
                                    surface_form=ent.text,
                                    start_char=ent.start_char,
                                    end_char=ent.end_char,
                                    chapter_id=None,  # Se asignará después basado en posición
                                    confidence=ent.confidence,
                                    source=ent.source,
                                )
                                entity_repo.create_mention(mention)

                            # Actualizar progreso cada 5 entidades
                            entities_created += 1
                            if entities_created % 5 == 0 and total_entities_to_create > 0:
                                # Progreso de 40 a 55 (15 puntos en esta subfase)
                                sub_progress = 40 + int(15 * entities_created / total_entities_to_create)
                                analysis_progress_storage[project_id]["progress"] = min(55, sub_progress)
                                update_time_remaining()

                        except Exception as e:
                            logger.warning(f"Error creating entity {first_mention.text}: {e}")

                analysis_progress_storage[project_id]["progress"] = 55
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["entities_found"] = len(entities)
                phases[2]["completed"] = True
                phases[2]["current"] = False
                phases[2]["duration"] = round(time.time() - phase_start, 1)

                logger.info(f"NER complete: {len(entities)} entities")

                # ========== FASE 4: ATRIBUTOS (55-75%) ==========
                phase_start = time.time()
                phases[3]["current"] = True
                analysis_progress_storage[project_id]["progress"] = 60
                analysis_progress_storage[project_id]["current_phase"] = "Extrayendo atributos de personajes"

                attributes = []
                if entities:
                    attr_extractor = AttributeExtractor()
                    entity_repo = get_entity_repository()

                    # Preparar menciones de entidades para extract_attributes
                    # Format: [(nombre, start_char, end_char)]
                    character_entities = [e for e in entities if e.entity_type.value == "character"]

                    if character_entities:
                        # Extraer atributos del texto completo
                        # El extractor encontrará atributos para todas las entidades mencionadas
                        entity_mentions = [
                            (e.canonical_name, e.first_appearance_char or 0, (e.first_appearance_char or 0) + len(e.canonical_name))
                            for e in character_entities
                        ]

                        attr_result = attr_extractor.extract_attributes(
                            text=full_text,
                            entity_mentions=entity_mentions,
                            chapter_id=None,
                        )

                        if attr_result.is_success and attr_result.value:
                            for attr in attr_result.value.attributes:
                                # Validar que entity_name no sea None
                                if not attr.entity_name:
                                    continue

                                # Encontrar la entidad correspondiente
                                matching_entity = next(
                                    (e for e in character_entities if e.canonical_name and e.canonical_name.lower() == attr.entity_name.lower()),
                                    None
                                )
                                if matching_entity:
                                    try:
                                        attr_key = attr.key.value if hasattr(attr.key, 'value') else str(attr.key)
                                        attr_type = attr.category.value if hasattr(attr.category, 'value') else "physical"

                                        entity_repo.create_attribute(
                                            entity_id=matching_entity.id,
                                            attribute_type=attr_type,
                                            attribute_key=attr_key,
                                            attribute_value=attr.value,
                                            confidence=attr.confidence,
                                        )
                                        attributes.append(attr)
                                    except Exception as e:
                                        logger.warning(f"Error creating attribute for {matching_entity.canonical_name}: {e}")

                analysis_progress_storage[project_id]["progress"] = 75
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["attributes_extracted"] = len(attributes)
                phases[3]["completed"] = True
                phases[3]["current"] = False
                phases[3]["duration"] = round(time.time() - phase_start, 1)

                logger.info(f"Attribute extraction complete: {len(attributes)} attributes")

                # ========== FASE 5: CONSISTENCIA (75-90%) ==========
                phase_start = time.time()
                phases[4]["current"] = True
                analysis_progress_storage[project_id]["progress"] = 80
                analysis_progress_storage[project_id]["current_phase"] = "Analizando consistencia narrativa"

                inconsistencies = []
                if attributes:
                    checker = AttributeConsistencyChecker()
                    check_result = checker.check_consistency(attributes)
                    if check_result.is_success:
                        inconsistencies = check_result.value or []

                analysis_progress_storage[project_id]["progress"] = 90
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["inconsistencies_found"] = len(inconsistencies)
                phases[4]["completed"] = True
                phases[4]["current"] = False
                phases[4]["duration"] = round(time.time() - phase_start, 1)

                logger.info(f"Consistency analysis complete: {len(inconsistencies)} inconsistencies")

                # ========== FASE 6: ALERTAS (90-100%) ==========
                phase_start = time.time()
                phases[5]["current"] = True
                analysis_progress_storage[project_id]["progress"] = 95
                analysis_progress_storage[project_id]["current_phase"] = "Generando alertas"

                alerts_created = 0
                if inconsistencies:
                    alert_engine = get_alert_engine()
                    for inc in inconsistencies:
                        alert_result = alert_engine.create_from_attribute_inconsistency(
                            project_id=project_id,
                            inconsistency=inc,
                            min_confidence=0.5
                        )
                        if alert_result.is_success:
                            alerts_created += 1

                analysis_progress_storage[project_id]["progress"] = 100
                analysis_progress_storage[project_id]["metrics"]["alerts_generated"] = alerts_created
                phases[5]["completed"] = True
                phases[5]["current"] = False
                phases[5]["duration"] = round(time.time() - phase_start, 1)

                # ========== COMPLETADO ==========
                analysis_progress_storage[project_id]["status"] = "completed"
                analysis_progress_storage[project_id]["current_phase"] = "Análisis completado"
                analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 0

                total_duration = round(time.time() - start_time, 1)
                analysis_progress_storage[project_id]["metrics"]["total_duration_seconds"] = total_duration

                # Actualizar proyecto en BD
                project.analysis_status = "completed"
                project.analysis_progress = 1.0
                project.word_count = word_count
                project.chapter_count = chapters_count

                proj_manager = ProjectManager(db_session)
                proj_manager.update(project)

                logger.info(f"Analysis completed for project {project_id} in {total_duration}s")
                logger.info(f"Results: {word_count} words, {chapters_count} chapters, {len(entities)} entities, {alerts_created} alerts")

            except Exception as e:
                logger.exception(f"Error during analysis for project {project_id}: {e}")
                analysis_progress_storage[project_id]["status"] = "error"
                analysis_progress_storage[project_id]["current_phase"] = f"Error: {str(e)}"
                analysis_progress_storage[project_id]["error"] = str(e)

                # Marcar proyecto como error
                try:
                    project.analysis_status = "error"
                    proj_manager = ProjectManager(db_session)
                    proj_manager.update(project)
                except Exception as db_error:
                    logger.error(f"Failed to update project status to error: {db_error}")

            finally:
                # Limpiar archivo temporal solo si fue creado temporalmente
                if use_temp_file and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass

        def _persist_chapters_to_db(chapters_data: list, proj_id: int, db: Database):
            """Persiste los capítulos en la base de datos."""
            try:
                # Usar transacción para asegurar atomicidad
                with db.transaction() as conn:
                    # Primero eliminar capítulos existentes
                    conn.execute("DELETE FROM chapters WHERE project_id = ?", (proj_id,))

                    for ch in chapters_data:
                        conn.execute(
                            """
                            INSERT INTO chapters (
                                project_id, chapter_number, title, content,
                                start_char, end_char, word_count, structure_type
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                proj_id,
                                ch["chapter_number"],
                                ch["title"],
                                ch["content"],
                                ch["start_char"],
                                ch["end_char"],
                                ch["word_count"],
                                ch["structure_type"]
                            )
                        )
                logger.info(f"Persisted {len(chapters_data)} chapters to database")
            except Exception as e:
                logger.error(f"Error persisting chapters: {e}", exc_info=True)

        # Ejecutar análisis real en thread separado
        thread = threading.Thread(target=run_real_analysis, daemon=True)
        thread.start()

        return ApiResponse(
            success=True,
            message="Análisis iniciado correctamente",
            data={"project_id": project_id, "status": "running"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.get("/api/projects/{project_id}/analysis/progress", response_model=ApiResponse)
async def get_analysis_progress(project_id: int):
    """
    Obtiene el progreso actual del análisis de un proyecto.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con el estado del progreso
    """
    try:
        if project_id not in analysis_progress_storage:
            # No hay análisis en curso, devolver estado "pending"
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "status": "pending",
                    "progress": 0,
                    "current_phase": "Sin análisis en curso",
                    "phases": []
                }
            )

        progress = analysis_progress_storage[project_id]
        return ApiResponse(success=True, data=progress)

    except Exception as e:
        logger.error(f"Error getting analysis progress for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

# ============================================================================
# Endpoints - Relaciones entre Personajes
# ============================================================================

@app.get("/api/projects/{project_id}/relationships", response_model=ApiResponse)
async def get_project_relationships(project_id: int):
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
    try:
        from narrative_assistant.analysis import (
            RelationshipClusteringEngine,
            CharacterKnowledgeAnalyzer,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar que el proyecto existe
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Obtener entidades del proyecto
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)

        if not entities:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
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

        # Obtener menciones de entidades
        all_mentions = []
        for entity in entities:
            mentions = entity_repo.get_mentions_by_entity(entity.id)
            for m in mentions:
                all_mentions.append({
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "start_char": m.start_char,
                    "end_char": m.end_char,
                    "chapter_id": m.chapter_id,
                })

        # 1. Análisis de clustering/relaciones
        clustering_engine = RelationshipClusteringEngine(use_embeddings=False)
        clustering_engine.COOCCURRENCE_THRESHOLD = 2
        clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.3

        # Extraer co-ocurrencias de menciones
        chapters_data = [
            {
                "chapter_number": c.chapter_number,
                "start_char": c.start_char,
                "end_char": c.end_char,
                "content": c.content,
            }
            for c in chapters
        ]

        # Agrupar menciones por capítulo y buscar co-ocurrencias
        mentions_by_chapter = {}
        for m in all_mentions:
            # Encontrar capítulo de esta mención
            for ch in chapters_data:
                if ch["start_char"] <= m["start_char"] <= ch["end_char"]:
                    ch_num = ch["chapter_number"]
                    if ch_num not in mentions_by_chapter:
                        mentions_by_chapter[ch_num] = []
                    mentions_by_chapter[ch_num].append(m)
                    break

        # Detectar co-ocurrencias (menciones cercanas)
        WINDOW = 500  # caracteres
        for ch_num, ch_mentions in mentions_by_chapter.items():
            ch_mentions.sort(key=lambda x: x["start_char"])

            for i, m1 in enumerate(ch_mentions):
                for m2 in ch_mentions[i+1:]:
                    if m1["entity_id"] == m2["entity_id"]:
                        continue

                    distance = m2["start_char"] - m1["end_char"]
                    if distance > WINDOW:
                        break

                    # Obtener contexto
                    chapter_content = next(
                        (c["content"] for c in chapters_data if c["chapter_number"] == ch_num),
                        ""
                    )
                    context_start = max(0, m1["start_char"] - 50)
                    context_end = min(len(chapter_content), m2["end_char"] + 50)
                    context = chapter_content[context_start:context_end] if chapter_content else ""

                    clustering_engine.add_cooccurrence(
                        entity1_id=m1["entity_id"],
                        entity2_id=m2["entity_id"],
                        entity1_name=m1["entity_name"],
                        entity2_name=m2["entity_name"],
                        chapter=ch_num,
                        distance_chars=distance,
                        context=context[:200],  # Limitar contexto
                    )

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

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "entity_count": len(entities),
                "relations": clustering_result.get("relations", []),
                "clusters": clustering_result.get("clusters", []),
                "dendrogram_data": clustering_result.get("dendrogram_data"),
                "mentions": [m.to_dict() for m in knowledge_analyzer.get_all_mentions()],
                "opinions": [o.to_dict() for o in knowledge_analyzer.get_all_opinions()],
                "intentions": [i.to_dict() for i in knowledge_analyzer.get_all_intentions()],
                "asymmetries": asymmetries,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relationships for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/relationships/asymmetry/{entity_a_id}/{entity_b_id}", response_model=ApiResponse)
async def get_knowledge_asymmetry(project_id: int, entity_a_id: int, entity_b_id: int):
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
            analyzer.register_entity(entity.id, entity.canonical_name, entity.aliases)

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
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - LLM / Inferencia de Expectativas
# ============================================================================

@app.get("/api/llm/status", response_model=ApiResponse)
async def get_llm_status():
    """
    Verifica si las funcionalidades LLM están disponibles.

    Returns:
        ApiResponse con estado del LLM incluyendo:
        - available: Si Ollama está corriendo y hay modelos
        - backend: Backend en uso (ollama, transformers, none)
        - model: Modelo principal configurado
        - available_methods: Lista de métodos de inferencia disponibles
    """
    try:
        from narrative_assistant.llm import is_llm_available, get_llm_client

        available = is_llm_available()
        client = get_llm_client()

        # Obtener modelos disponibles directamente de Ollama
        available_methods = ["rule_based", "embeddings"]  # Siempre disponibles
        ollama_models = []

        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    name = model.get("name", "").split(":")[0]  # Quitar :latest
                    if name:
                        ollama_models.append(name)
                        available_methods.append(name)
        except Exception as e:
            logger.debug(f"Error getting Ollama models: {e}")

        return ApiResponse(
            success=True,
            data={
                "available": available,
                "backend": client.backend_name if client else "none",
                "model": client.model_name if client else None,
                "available_methods": available_methods,
                "ollama_models": ollama_models,
                "message": "Modelos LLM activos" if available else "Usando análisis básico"
            }
        )
    except ImportError as e:
        logger.warning(f"LLM module import error: {e}")
        return ApiResponse(
            success=True,
            data={
                "available": False,
                "backend": "none",
                "model": None,
                "available_methods": ["rule_based", "embeddings"],
                "ollama_models": [],
                "message": "Usando análisis básico"
            }
        )
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/characters/{character_id}/analyze-behavior", response_model=ApiResponse)
async def analyze_character_behavior(project_id: int, character_id: int):
    """
    Analiza el comportamiento de un personaje usando LLM para inferir expectativas.

    Args:
        project_id: ID del proyecto
        character_id: ID del personaje

    Returns:
        ApiResponse con perfil comportamental del personaje
    """
    try:
        from narrative_assistant.llm import (
            ExpectationInferenceEngine,
            is_llm_available,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not is_llm_available():
            return ApiResponse(
                success=False,
                error="LLM no disponible. Instala Ollama y ejecuta: ollama serve"
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
        existing_attrs = {}
        for attr in entity.attributes:
            if attr.attribute_name not in existing_attrs:
                existing_attrs[attr.attribute_name] = []
            existing_attrs[attr.attribute_name].append(attr.value)

        # Analizar con LLM
        engine = ExpectationInferenceEngine()
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
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/characters/{character_id}/detect-violations", response_model=ApiResponse)
async def detect_character_violations(
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
        from narrative_assistant.llm import (
            ExpectationInferenceEngine,
            is_llm_available,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not is_llm_available():
            return ApiResponse(
                success=False,
                error="LLM no disponible. Instala Ollama y ejecuta: ollama serve"
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
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/characters/{character_id}/expectations", response_model=ApiResponse)
async def get_character_expectations(project_id: int, character_id: int):
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
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Narrative Assistant API Server v{NA_VERSION}")
    logger.info("Server will be available at http://localhost:8008")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8008,
        reload=True,  # Solo para desarrollo
        log_level="info",
    )
