"""
Router: projects
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import UploadFile, File
from fastapi import Body
from typing import Optional, Any
from deps import ProjectResponse, _get_project_stats
from narrative_assistant.alerts.models import AlertStatus

router = APIRouter()

@router.get("/api/projects", response_model=ApiResponse)
async def list_projects():
    """
    Lista todos los proyectos.

    Returns:
        ApiResponse con lista de proyectos
    """
    try:
        if not deps.project_manager:
            # Try to load modules on-demand if not yet loaded
            if not deps.MODULES_LOADED:
                logger.info("list_projects: Attempting on-demand module loading...")
                deps.load_narrative_assistant_modules()
            if not deps.project_manager:
                logger.error("list_projects: deps.project_manager is None")
                return ApiResponse(success=False, error="Project manager not initialized")

        # Verify database is accessible
        if not deps.get_database:
            logger.error("list_projects: deps.get_database is None")
            return ApiResponse(success=False, error="Database module not loaded")

        try:
            db = deps.get_database()
            db_path = str(db.db_path)
            # Verify essential tables exist (auto-repair if needed)
            tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [t['name'] for t in tables]
            logger.debug(f"list_projects: db_path={db_path}, tables={table_names}")
            if 'projects' not in table_names:
                logger.warning(f"list_projects: 'projects' table missing! db_path={db_path}, tables_found={table_names}")
                deps._write_debug(f"list_projects: 'projects' MISSING! db_path={db_path}, tables={table_names}")

                # Log file info for diagnostics
                try:
                    from pathlib import Path as _P
                    _db_file = _P(db_path)
                    if _db_file.exists():
                        deps._write_debug(f"list_projects: DB file exists, size={_db_file.stat().st_size} bytes")
                        logger.warning(f"list_projects: DB file exists at {db_path}, size={_db_file.stat().st_size} bytes")
                    else:
                        deps._write_debug(f"list_projects: DB file DOES NOT EXIST at {db_path}")
                        logger.error(f"list_projects: DB file DOES NOT EXIST at {db_path}")
                except Exception:
                    pass

                # Also check via direct sqlite3 connection (bypass any caching)
                try:
                    import sqlite3 as _sq
                    _direct = _sq.connect(db_path)
                    _direct.execute("PRAGMA wal_checkpoint(FULL)")
                    _direct_tables = _direct.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    _direct_names = [t[0] for t in _direct_tables]
                    deps._write_debug(f"list_projects: direct sqlite3 tables={_direct_names}")
                    logger.warning(f"list_projects: direct sqlite3 connection tables={_direct_names}")
                    _direct.close()
                except Exception as _dex:
                    deps._write_debug(f"list_projects: direct sqlite3 check failed: {_dex}")

                logger.warning("list_projects: attempting schema repair...")
                try:
                    from narrative_assistant.persistence.database import SCHEMA_SQL
                    with db.connection() as conn:
                        conn.executescript(SCHEMA_SQL)
                        conn.commit()
                    # Verify repair worked
                    post_tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
                    post_names = [t['name'] for t in post_tables]
                    deps._write_debug(f"list_projects: post-repair tables={post_names}")
                    logger.info(f"list_projects: Schema repaired, tables now: {post_names}")
                    if 'projects' not in post_names:
                        logger.error(f"list_projects: Schema repair FAILED, still no 'projects' table")
                        deps._write_debug(f"list_projects: repair FAILED, still no 'projects'")
                        return ApiResponse(success=False, error="Database not initialized properly - 'projects' table missing")
                except Exception as repair_err:
                    logger.error(f"list_projects: Schema repair failed: {repair_err}", exc_info=True)
                    deps._write_debug(f"list_projects: Schema repair exception: {repair_err}")
                    return ApiResponse(success=False, error="Database not initialized properly - 'projects' table missing")
        except Exception as db_err:
            logger.error(f"list_projects: Error checking database: {db_err}", exc_info=True)
            deps._write_debug(f"list_projects: DB check exception: {db_err}")

        projects = deps.project_manager.list_all()
        db = deps.get_database()

        projects_data = []
        for p in projects:
            # Obtener estadísticas desde la BD (source of truth)
            stats = _get_project_stats(p.id, db)

            # Determinar severidad más alta de alertas
            highest_severity = None
            if deps.alert_repository:
                alerts_result = deps.alert_repository.get_by_project(p.id)
                if alerts_result.is_success:
                    open_alerts = [a for a in alerts_result.value if a.status == AlertStatus.OPEN]
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
                "document_path": p.document_path,
                "document_format": p.document_format,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "last_modified": p.updated_at.isoformat() if p.updated_at else None,
                "last_opened": p.last_opened_at.isoformat() if p.last_opened_at else None,
                "analysis_status": p.analysis_status,
                "analysis_progress": int(p.analysis_progress * 100) if p.analysis_progress else 0,
                "word_count": stats["word_count"] or p.word_count,
                "chapter_count": stats["chapter_count"],
                "entity_count": stats["entity_count"],
                "open_alerts_count": stats["open_alerts_count"],
                "highest_alert_severity": highest_severity,
            })

        return ApiResponse(success=True, data=projects_data)
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}", response_model=ApiResponse)
async def get_project(project_id: int):
    """
    Obtiene un proyecto por ID.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con datos del proyecto
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Verificar si el estado "analyzing" está atascado (no hay análisis real en progreso)
        # Esto puede ocurrir si el servidor se reinició durante un análisis
        # NOTA: 'pending' NO se incluye aquí porque es el estado inicial legítimo
        # de un proyecto recién creado que aún no ha sido analizado.
        if project.analysis_status in ['analyzing', 'in_progress']:
            # Si no hay análisis activo en memoria, el estado está atascado
            with deps._progress_lock:
                has_active = project_id in deps.analysis_progress_storage
            if not has_active:
                logger.warning(f"Project {project_id} has stuck analysis_status='{project.analysis_status}', resetting to 'pending'")
                project.analysis_status = 'pending'
                project.analysis_progress = 0.0
                try:
                    deps.project_manager.update(project)
                except Exception as e:
                    logger.warning(f"Could not update stuck analysis status: {e}")

        # Obtener estadísticas desde la BD (source of truth)
        db = deps.get_database()
        stats = _get_project_stats(project_id, db)

        # Obtener severidad más alta de alertas
        highest_severity = None
        if deps.alert_repository:
            alerts_result = deps.alert_repository.get_by_project(project.id)
            if alerts_result.is_success:
                open_alerts = [a for a in alerts_result.value if a.status == AlertStatus.OPEN]
                if open_alerts:
                    severity_priority = {"critical": 3, "warning": 2, "info": 1}
                    highest_severity = max(
                        (a.severity.value for a in open_alerts),
                        key=lambda s: severity_priority.get(s, 0)
                    )

        # Extraer document_type (preferir columna DB sobre settings JSON)
        project_settings = project.settings or {}
        document_type = project_settings.get("document_type", "unknown")

        # La columna document_type de la BD es la fuente de verdad (actualizada por FeatureProfileService)
        try:
            with db.connection() as conn:
                dt_row = conn.execute(
                    "SELECT document_type FROM projects WHERE id = ?", (project_id,)
                ).fetchone()
                if dt_row and dt_row[0]:
                    from narrative_assistant.feature_profile.models import _TYPE_CODE_TO_LONG
                    document_type = _TYPE_CODE_TO_LONG.get(dt_row[0], document_type)
        except Exception:
            pass  # Fallback al valor de settings

        document_classification = project_settings.get("document_classification", None)
        recommended_analysis = project_settings.get("recommended_analysis", None)

        project_data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "document_path": project.document_path,
            "document_format": project.document_format,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "last_modified": project.updated_at.isoformat() if project.updated_at else None,
            "last_opened": project.last_opened_at.isoformat() if project.last_opened_at else None,
            "analysis_status": project.analysis_status,
            "analysis_progress": int(project.analysis_progress * 100) if project.analysis_progress else 0,
            "word_count": stats["word_count"] or project.word_count,
            "chapter_count": stats["chapter_count"],
            "entity_count": stats["entity_count"],
            "open_alerts_count": stats["open_alerts_count"],
            "highest_alert_severity": highest_severity,
            # Tipo de documento detectado y análisis recomendado
            "document_type": document_type,
            "document_classification": document_classification,
            "recommended_analysis": recommended_analysis,
        }

        return ApiResponse(success=True, data=project_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/analysis-status", response_model=ApiResponse)
async def get_analysis_status(project_id: int):
    """
    Obtiene el estado de ejecución de las fases de análisis para un proyecto.

    Retorna qué fases se han ejecutado, permitiendo al frontend mostrar
    tabs condicionalmente según el análisis disponible.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con executed (dict de fases ejecutadas) y available (fases disponibles)
    """
    try:
        # Obtener proyecto a través del deps.project_manager (la forma correcta)
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Obtener estadísticas para determinar qué está ejecutado
        db = deps.get_database()
        stats = _get_project_stats(project_id, db)
        settings = project.settings or {}

        # Determinar qué fases están ejecutadas basándose en datos disponibles
        # Esto es una aproximación - idealmente tendríamos un registro de fases ejecutadas
        has_chapters = (stats.get("chapter_count") or 0) > 0
        has_entities = (stats.get("entity_count") or 0) > 0
        has_alerts = (stats.get("open_alerts_count") or 0) > 0

        # Verificar si hay relaciones (puede ser en 'relationships' o 'entity_relationships')
        relationship_count = 0
        has_temporal = False
        with db.connection() as conn:
            # Intentar primero la tabla 'relationships' (schema principal)
            try:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM relationships WHERE project_id = ?",
                    (project_id,)
                )
                relationship_count = cursor.fetchone()[0]
            except Exception:
                # Si no existe, intentar 'entity_relationships' (módulo relationships)
                try:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM entity_relationships WHERE project_id = ?",
                        (project_id,)
                    )
                    relationship_count = cursor.fetchone()[0]
                except Exception:
                    # Ninguna tabla existe, 0 relaciones
                    relationship_count = 0

            # Verificar si hay datos temporales (simplificado - verificar si existen marcadores)
            try:
                cursor = conn.execute(
                    """SELECT COUNT(*) FROM alerts
                       WHERE project_id = ? AND category = 'temporal'""",
                    (project_id,)
                )
                has_temporal = cursor.fetchone()[0] > 0
            except Exception:
                has_temporal = False

        # Construir estado de fases ejecutadas
        executed = {
            "parsing": has_chapters,  # Si hay capítulos, el parsing se ejecutó
            "structure": has_chapters,
            "entities": has_entities,
            "coreference": has_entities,  # Asumimos que si hay entidades, hay correferencias
            "attributes": has_entities,
            "relationships": relationship_count > 0,
            "interactions": False,  # Por implementar
            "spelling": has_alerts,  # Si hay alertas, asumimos que se ejecutó
            "grammar": has_alerts,
            "register": has_alerts,
            "pacing": has_chapters,
            "coherence": has_entities and has_chapters,
            "temporal": has_temporal,
            "emotional": False,  # Por implementar
            "sentiment": False,  # Por implementar
            "focalization": False,  # Por implementar
            "voice_profiles": has_entities and has_chapters,  # Perfiles de voz disponibles
            "voice_deviations": has_entities and has_chapters,  # Desviaciones de voz
            "register_analysis": has_chapters,  # Análisis de registro disponible
            "tension_curve": has_chapters,  # Curva de tensión narrativa
            "sensory_report": has_chapters,  # Reporte sensorial (5 sentidos)
            "sentence_energy": has_chapters,  # Energía de oraciones (voz, verbos, estructura)
            "narrative_templates": has_chapters,  # Plantillas narrativas (diagnóstico)
            "narrative_health": has_chapters and has_entities,  # Salud narrativa (12 dimensiones)
            "character_archetypes": has_entities and has_chapters,  # Arquetipos Jung/Campbell
            "story_bible": has_entities,  # Story Bible / Wiki de entidades
            "speaker_attribution": has_entities and has_chapters,  # Atribución de hablantes
        }

        return ApiResponse(
            success=True,
            data={
                "executed": executed,
                "analysis_status": project.analysis_status,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects", response_model=ApiResponse)
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
            # Validar contra path traversal y extensiones permitidas
            try:
                from narrative_assistant.parsers.sanitization import validate_file_path
                document_path = validate_file_path(
                    Path(file_path),
                    must_exist=True,
                    allowed_extensions=set(allowed_extensions),
                )
            except FileNotFoundError:
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo no existe: {file_path}"
                )
            except (ValueError, PermissionError) as e:
                raise HTTPException(status_code=400, detail=str(e))
            file_ext = document_path.suffix.lower()
            stored_path = str(document_path)  # Guardar la ruta resuelta y validada

        elif file and file.filename:
            # Archivo subido: guardarlo permanentemente en el directorio de la app
            file_ext = Path(file.filename).suffix.lower()

            # Crear directorio de documentos
            config = deps.get_config()
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
            document_text = raw_doc.full_text

            if not document_text or not document_text.strip():
                raise HTTPException(status_code=400, detail="El documento está vacío o no se pudo leer el contenido")

            logger.info(f"Document parsed: {len(document_text)} chars, {len(document_text.split())} words")

            # Crear proyecto usando create_from_document (el único método disponible)
            logger.info(f"Creating project '{name}' from: {document_path}")

            project_repo = deps.project_manager
            create_result = project_repo.create_from_document(
                text=document_text,
                name=name,
                document_format=format_str,
                document_path=Path(stored_path),
                description=description or f"Documento: {document_path.name}",
                check_existing=True,
            )

            if create_result.is_failure:
                error = create_result.error
                # Si el documento ya existe, devolver código 409 Conflict
                if error and "already exists" in str(error.message).lower():
                    raise HTTPException(
                        status_code=409,
                        detail=f"Este documento ya existe en el proyecto '{getattr(error, 'existing_project_name', 'existente')}'"
                    )
                raise HTTPException(status_code=500, detail=f"Error creando proyecto: {error}")

            project = create_result.value

            if project is None:
                logger.error(f"create_from_document returned success but value is None")
                raise HTTPException(status_code=500, detail="Error interno: proyecto no creado")

            project_data = ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                document_path=project.document_path,
                document_format=project.document_format,
                created_at=project.created_at.isoformat() if project.created_at else None,
                last_modified=project.updated_at.isoformat() if project.updated_at else None,
                last_opened=project.last_opened_at.isoformat() if project.last_opened_at else None,
                analysis_status=project.analysis_status or "pending",
                analysis_progress=0,
                word_count=project.word_count,  # Ya calculado por create_from_document
                chapter_count=project.chapter_count,
                entity_count=0,
                open_alerts_count=0,
                highest_alert_severity=None,
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


@router.delete("/api/projects/{project_id}", response_model=ApiResponse)
async def delete_project(project_id: int):
    """
    Elimina un proyecto.

    Args:
        project_id: ID del proyecto a eliminar

    Returns:
        ApiResponse con confirmación
    """
    try:
        project_repo = deps.project_manager
        project_repo.delete(project_id)

        # Limpiar progreso de análisis huérfano
        with deps._progress_lock:
            deps.analysis_progress_storage.pop(project_id, None)

        logger.info(f"Deleted project: {project_id}")
        return ApiResponse(success=True, message="Proyecto eliminado exitosamente")
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


