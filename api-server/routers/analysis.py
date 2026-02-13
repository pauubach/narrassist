"""
Router: analysis
"""

from typing import Optional

import deps
from deps import ApiResponse, logger
from fastapi import APIRouter, File, HTTPException, UploadFile

from routers._partial_analysis import PartialAnalysisRequest

router = APIRouter()


def _start_queued_analysis(queued_entry: dict):
    """
    Re-lanza el análisis de un proyecto encolado con metadata ligera (F-005).
    """
    import asyncio
    import threading

    project_id = queued_entry["project_id"]
    mode = queued_entry.get("mode", "full")
    partial_phases = list(queued_entry.get("partial_phases", []))
    partial_force = bool(queued_entry.get("partial_force", False))
    logger.info(f"Auto-start queued analysis for project {project_id} (mode={mode})")

    def _trigger():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if mode == "partial":
                    if not partial_phases:
                        logger.warning(
                            "Queued partial analysis missing phases for project "
                            f"{project_id}; falling back to full analysis."
                        )
                        loop.run_until_complete(start_analysis(project_id, file=None))
                        return
                    request = PartialAnalysisRequest(phases=partial_phases, force=partial_force)
                    loop.run_until_complete(start_partial_analysis(project_id, request))
                else:
                    loop.run_until_complete(start_analysis(project_id, file=None))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error auto-starting queued project {project_id}: {e}", exc_info=True)
            with deps._progress_lock:
                if project_id in deps.analysis_progress_storage:
                    deps.analysis_progress_storage[project_id]["status"] = "error"
                    deps.analysis_progress_storage[project_id]["error"] = f"Error al iniciar: {e}"

    thread = threading.Thread(target=_trigger, daemon=True)
    thread.start()


@router.post("/api/projects/{project_id}/reanalyze", response_model=ApiResponse)
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
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Verificar que tenemos la ruta del documento
        if not project.document_path:
            return ApiResponse(
                success=False,
                error="No se encontró la ruta del documento original. Por favor, elimine el proyecto y créelo de nuevo.",
            )

        document_path = Path(project.document_path)

        # Verificar que el archivo existe
        if not document_path.exists():
            return ApiResponse(
                success=False,
                error=f"El documento original no se encuentra en: {document_path}. Verifique que el archivo existe.",
            )

        logger.info(
            f"Re-analyzing project '{project.name}' (ID: {project_id}) from: {document_path}"
        )

        # Llamar al endpoint de análisis que tiene el progreso en background
        # El documento ya está guardado en project.document_path
        return await start_analysis(project_id, file=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-analyzing project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/analyze", response_model=ApiResponse)
async def start_analysis(project_id: int, file: Optional[UploadFile] = File(None)):  # noqa: B008
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
        from pathlib import Path

        # Validar que el proyecto existe
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Guard de concurrencia: no permitir doble análisis del mismo proyecto
        if project.analysis_status in ("analyzing", "queued"):
            return ApiResponse(
                success=False,
                error="Ya hay un análisis en curso para este proyecto. Espera a que termine.",
            )

        # Determinar el archivo a usar
        tmp_path: Path
        use_temp_file = False

        if file and file.filename:
            # Validar tamaño (50 MB máximo)
            MAX_UPLOAD_BYTES = 50 * 1024 * 1024
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(file.filename).suffix
            ) as tmp_file:
                size = 0
                while chunk := file.file.read(8192):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        Path(tmp_file.name).unlink(missing_ok=True)
                        return ApiResponse(
                            success=False, error="El archivo supera el límite de 50 MB"
                        )
                    tmp_file.write(chunk)
                tmp_path = Path(tmp_file.name)
            use_temp_file = True
            logger.info(f"Analysis started for project {project_id}")
            logger.info(f"File: {file.filename}, temp path: {tmp_path}")
        elif project.document_path:
            # Usar documento guardado del proyecto
            tmp_path = Path(project.document_path)
            if not tmp_path.exists():
                return ApiResponse(
                    success=False, error=f"El documento no se encuentra: {project.document_path}"
                )
            use_temp_file = False
            logger.info(f"Analysis started for project {project_id}")
            logger.info(f"Using stored document: {tmp_path}")
        else:
            return ApiResponse(
                success=False, error="Se requiere un archivo o que el proyecto tenga document_path"
            )

        # Two-tier concurrency: Phase 1 (parsing/classification/structure) runs immediately
        # for all projects. Only heavy phases (NER+) are exclusive with queue.

        # Actualizar estado del proyecto a "analyzing" en la BD
        project.analysis_status = "analyzing"
        project.analysis_progress = 0.0
        deps.project_manager.update(project)

        # Inicializar progreso (protegido por lock)
        import time as time_module

        now = time_module.time()
        with deps._progress_lock:
            deps.analysis_progress_storage[project_id] = {
                "project_id": project_id,
                "status": "running",
                "progress": 0,
                "current_phase": "Iniciando análisis...",
                "current_action": "Preparando documento",
                "phases": [
                    {
                        "id": "parsing",
                        "name": "Lectura del documento",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "classification",
                        "name": "Clasificando tipo de documento",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "structure",
                        "name": "Identificando capítulos",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "ner",
                        "name": "Buscando personajes y lugares",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "fusion",
                        "name": "Unificando entidades",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "attributes",
                        "name": "Analizando características",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "consistency",
                        "name": "Verificando coherencia",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "grammar",
                        "name": "Revisando gramática y ortografía",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "alerts",
                        "name": "Preparando observaciones",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "relationships",
                        "name": "Analizando relaciones",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "voice",
                        "name": "Perfilando voces",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "prose",
                        "name": "Evaluando escritura",
                        "completed": False,
                        "current": False,
                    },
                    {
                        "id": "health",
                        "name": "Salud narrativa",
                        "completed": False,
                        "current": False,
                    },
                ],
                "metrics": {},
                "estimated_seconds_remaining": 60,
                "_start_time": now,
                "_last_progress_update": now,
            }

        logger.info(f"Analysis started for project {project_id}")
        logger.info(f"File: {file.filename if file else 'stored document'}, temp path: {tmp_path}")

        # Ejecutar análisis REAL en background thread
        import threading
        import time

        def run_real_analysis():
            """Ejecuta el análisis real — orquestador que delega en funciones de fase."""
            from routers._analysis_phases import (
                ProgressTracker,
                apply_license_and_settings,
                claim_heavy_slot_or_queue,
                handle_analysis_error,
                release_heavy_slot,
                run_alerts,
                run_attributes,
                run_classification,
                run_cleanup,
                run_completion,
                run_consistency,
                run_finally_cleanup,
                run_fusion,
                run_grammar,
                run_llm_entity_validation,
                run_ner,
                run_ollama_healthcheck,
                run_parsing,
                run_reconciliation,
                run_snapshot,
                run_structure,
            )
            from routers._enrichment_phases import (
                capture_entity_fingerprint,
                invalidate_enrichment_if_mutated,
                run_health_enrichment,
                run_prose_enrichment,
                run_relationships_enrichment,
                run_voice_enrichment,
            )

            start_time = time.time()
            with deps._progress_lock:
                phases = deps.analysis_progress_storage[project_id]["phases"]

            phase_weights = {
                "parsing": 0.01,
                "classification": 0.01,
                "structure": 0.01,
                "ner": 0.31,
                "fusion": 0.15,
                "attributes": 0.08,
                "consistency": 0.03,
                "grammar": 0.06,
                "alerts": 0.04,
                "relationships": 0.08,
                "voice": 0.08,
                "prose": 0.08,
                "health": 0.06,
            }
            phase_order = [
                "parsing",
                "classification",
                "structure",
                "ner",
                "fusion",
                "attributes",
                "consistency",
                "grammar",
                "alerts",
                "relationships",
                "voice",
                "prose",
                "health",
            ]

            # --- S8a-14: Thin orchestrator using extracted phase functions ---
            db_session = deps.get_database()

            tracker = ProgressTracker(
                project_id=project_id,
                phases=phases,
                phase_weights=phase_weights,
                phase_order=phase_order,
                db_session=db_session,
            )

            # Build shared context dict
            ctx = {
                "project_id": project_id,
                "project": project,
                "db_session": db_session,
                "tmp_path": tmp_path,
                "use_temp_file": use_temp_file,
                "start_time": start_time,
                "queued_for_heavy": False,
                "queue_mode": "full",
            }

            try:
                # Pre-analysis
                run_snapshot(ctx, tracker)
                run_cleanup(ctx, tracker)
                apply_license_and_settings(ctx, tracker)

                # Tier 1: Lightweight phases (run in parallel for all projects)
                run_parsing(ctx, tracker)
                run_classification(ctx, tracker)
                run_structure(ctx, tracker)

                # Tier 2 gate: claim heavy slot or queue
                got_slot = claim_heavy_slot_or_queue(ctx, tracker)
                if not got_slot:
                    ctx["queued_for_heavy"] = True
                    logger.info(
                        f"Project {project_id}: lightweight phases done, "
                        f"queued for heavy (slot busy: #{deps._heavy_analysis_project_id})"
                    )
                    from narrative_assistant.persistence.project import ProjectManager

                    project.analysis_status = "queued"
                    proj_manager = ProjectManager(db_session)
                    proj_manager.update(project)
                    return  # Will be resumed when heavy slot frees

                # Ollama health check before heavy phases
                run_ollama_healthcheck(ctx, tracker)

                # Tier 2: Heavy phases (exclusive — one project at a time)
                run_ner(ctx, tracker)
                run_llm_entity_validation(ctx, tracker)
                run_fusion(ctx, tracker)
                run_attributes(ctx, tracker)
                run_consistency(ctx, tracker)
                run_grammar(ctx, tracker)
                run_alerts(ctx, tracker)

                # S8a-15: Release heavy slot — enrichment is CPU-only,
                # next queued project can start heavy NLP immediately
                release_heavy_slot(ctx)

                # S8a-17: Capture entity fingerprint before enrichment
                entity_fp = capture_entity_fingerprint(ctx["db_session"], project_id)

                # Tier 3: Enrichment phases (CPU-only, no GPU/LLM needed)
                run_relationships_enrichment(ctx, tracker)
                run_voice_enrichment(ctx, tracker)
                run_prose_enrichment(ctx, tracker)
                run_health_enrichment(ctx, tracker)

                # S8a-17: Check for entity mutations during enrichment
                invalidate_enrichment_if_mutated(ctx["db_session"], project_id, entity_fp)

                # Final reconciliation + completion
                run_reconciliation(ctx, tracker)
                run_completion(ctx, tracker)

            except Exception as e:
                handle_analysis_error(ctx, e)

            finally:
                run_finally_cleanup(ctx)

        # Pre-check: verificar que los modelos críticos están disponibles
        # antes de lanzar el thread, para dar un error claro al usuario
        try:
            from narrative_assistant.core.model_manager import (
                KNOWN_MODELS,
                ModelType,
                get_model_manager,
            )

            mm = get_model_manager()
            missing_models = []
            model_labels = {
                ModelType.SPACY: "Análisis lingüístico (spaCy)",
                ModelType.EMBEDDINGS: "Similitud semántica (embeddings)",
                ModelType.TRANSFORMER_NER: "Reconocimiento de entidades (NER)",
            }
            for mt, label in model_labels.items():
                model_info = KNOWN_MODELS.get(mt)
                if model_info and not model_info.required:
                    continue  # No bloquear por modelos opcionales
                if not mm.get_model_path(mt):
                    missing_models.append(label)

            if missing_models:
                names = ", ".join(missing_models)
                logger.error(f"Modelos no disponibles para análisis: {names}")
                # Limpiar estado de progreso
                with deps._progress_lock:
                    deps.analysis_progress_storage.pop(project_id, None)
                project.analysis_status = "error"
                deps.project_manager.update(project)
                return ApiResponse(
                    success=False,
                    error=f"Modelos no descargados: {names}. "
                    "Descárgalos desde Configuración > Verificar modelos.",
                )
        except Exception as e:
            logger.warning(f"Error en pre-check de modelos: {e}")
            # No bloquear - el thread dará un error más específico

        # Ejecutar análisis real en thread separado
        thread = threading.Thread(target=run_real_analysis, daemon=True)
        thread.start()

        return ApiResponse(
            success=True,
            message="Análisis iniciado correctamente",
            data={"project_id": project_id, "status": "running"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/analyze/partial", response_model=ApiResponse)
async def start_partial_analysis(project_id: int, request: PartialAnalysisRequest):
    """
    Inicia un análisis parcial: ejecuta solo las fases solicitadas.

    A diferencia de /analyze (full analysis con file upload),
    este endpoint acepta JSON con la lista de fases del frontend
    y solo ejecuta las que faltan (o todas si force=True).
    """
    from routers._partial_analysis import (
        build_partial_progress,
        get_completed_phases,
        resolve_backend_phases,
        run_partial_analysis_thread,
    )

    try:
        # Validar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")
        project = result.value

        # Guard: no doble análisis
        if project.analysis_status in ("analyzing", "queued"):
            return ApiResponse(
                success=False, error="Ya hay un análisis en curso para este proyecto."
            )

        # Validate frontend phase names
        from routers._partial_analysis import FRONTEND_TO_BACKEND

        unknown = [p for p in request.phases if p not in FRONTEND_TO_BACKEND]
        if unknown:
            return ApiResponse(success=False, error=f"Fases desconocidas: {', '.join(unknown)}")

        # Resolve backend phases
        db_session = deps.get_database()
        completed = get_completed_phases(db_session, project_id)
        phases_to_run = resolve_backend_phases(request.phases, completed, request.force)

        if not phases_to_run:
            return ApiResponse(
                success=True,
                message="Todas las fases solicitadas ya están completadas.",
                data={"project_id": project_id, "status": "up_to_date"},
            )

        # Verify document exists
        if not project.document_path:
            return ApiResponse(success=False, error="El proyecto no tiene documento asociado.")
        from pathlib import Path

        tmp_path = Path(project.document_path)
        if not tmp_path.exists():
            return ApiResponse(
                success=False, error=f"El documento no se encuentra: {project.document_path}"
            )

        # Update project status
        project.analysis_status = "analyzing"
        project.analysis_progress = 0.0
        deps.project_manager.update(project)

        # Initialize progress (only partial phases)
        import time as time_module

        now = time_module.time()
        progress_phases, partial_weights, partial_order = build_partial_progress(phases_to_run)

        with deps._progress_lock:
            deps.analysis_progress_storage[project_id] = {
                "project_id": project_id,
                "status": "running",
                "progress": 0,
                "current_phase": "Iniciando análisis parcial...",
                "current_action": f"{len(phases_to_run)} fases seleccionadas",
                "phases": progress_phases,
                "metrics": {},
                "estimated_seconds_remaining": 30,
                "_start_time": now,
                "_last_progress_update": now,
            }

        logger.info(
            f"Partial analysis started for project {project_id}: "
            f"phases={phases_to_run}, force={request.force}"
        )

        # Build context and spawn thread
        import threading

        ctx = {
            "project_id": project_id,
            "project": project,
            "db_session": db_session,
            "tmp_path": tmp_path,
            "use_temp_file": False,
            "start_time": now,
            "queued_for_heavy": False,
            "queue_mode": "partial",
            "partial_frontend_phases": request.phases,
            "partial_force": request.force,
        }

        thread = threading.Thread(
            target=run_partial_analysis_thread,
            args=(ctx, phases_to_run, request.force),
            daemon=True,
        )
        thread.start()

        return ApiResponse(
            success=True,
            message="Análisis parcial iniciado correctamente",
            data={
                "project_id": project_id,
                "status": "running",
                "phases": phases_to_run,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error starting partial analysis for project {project_id}: {e}",
            exc_info=True,
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/analysis/progress", response_model=ApiResponse)
async def get_analysis_progress(project_id: int):
    """
    Obtiene el progreso actual del análisis de un proyecto.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con el estado del progreso
    """
    import time

    try:
        with deps._progress_lock:
            if project_id not in deps.analysis_progress_storage:
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "status": "idle",
                        "progress": 0,
                        "current_phase": "Sin análisis en curso",
                        "phases": [],
                    },
                )

            progress = deps.analysis_progress_storage[project_id].copy()

            # Recalcular tiempo restante dinámicamente
            if progress.get("status") == "running":
                start_time = progress.get("_start_time")
                last_update = progress.get("_last_progress_update")
                base_estimate = progress.get("estimated_seconds_remaining", 60)

                if start_time and last_update:
                    now = time.time()
                    time_since_update = now - last_update

                    if time_since_update > 1:
                        adjusted_estimate = max(10, base_estimate - int(time_since_update))
                        progress["estimated_seconds_remaining"] = adjusted_estimate

                        if adjusted_estimate <= 15:
                            deps.analysis_progress_storage[project_id][
                                "estimated_seconds_remaining"
                            ] = 45
                            deps.analysis_progress_storage[project_id]["_last_progress_update"] = (
                                now
                            )
                            progress["estimated_seconds_remaining"] = 45

        return ApiResponse(success=True, data=progress)

    except Exception as e:
        logger.error(
            f"Error getting analysis progress for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/analysis/cancel", response_model=ApiResponse)
async def cancel_analysis(project_id: int):
    """
    Cancela el análisis en curso de un proyecto.

    Marca el análisis como cancelado para que el proceso en segundo plano
    lo detecte y se detenga de forma limpia.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse indicando si se canceló exitosamente
    """
    try:
        with deps._progress_lock:
            # Check if project is in the heavy analysis queue
            heavy_idx = next(
                (
                    i
                    for i, q in enumerate(deps._heavy_analysis_queue)
                    if q["project_id"] == project_id
                ),
                None,
            )
            if heavy_idx is not None:
                deps._heavy_analysis_queue.pop(heavy_idx)
                deps.analysis_progress_storage.pop(project_id, None)
                logger.info(f"Heavy-queued analysis removed for project {project_id}")
                try:
                    result = deps.project_manager.get(project_id)
                    if result.is_success:
                        project = result.value
                        project.analysis_status = "pending"
                        deps.project_manager.update(project)
                except Exception:
                    pass
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "status": "cancelled",
                        "message": "Análisis en cola cancelado",
                    },
                )

            # Also check legacy queue (backward compatibility)
            queue_idx = next(
                (i for i, q in enumerate(deps._analysis_queue) if q["project_id"] == project_id),
                None,
            )
            if queue_idx is not None:
                deps._analysis_queue.pop(queue_idx)
                deps.analysis_progress_storage.pop(project_id, None)
                logger.info(f"Queued analysis removed for project {project_id}")
                try:
                    result = deps.project_manager.get(project_id)
                    if result.is_success:
                        project = result.value
                        project.analysis_status = "pending"
                        deps.project_manager.update(project)
                except Exception:
                    pass
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "status": "cancelled",
                        "message": "Análisis en cola cancelado",
                    },
                )

            if project_id not in deps.analysis_progress_storage:
                return ApiResponse(
                    success=False, error="No hay análisis en curso para este proyecto"
                )

            current_status = deps.analysis_progress_storage[project_id].get("status")
            if current_status in ("completed", "error", "cancelled"):
                return ApiResponse(
                    success=False, error=f"El análisis ya ha terminado con estado: {current_status}"
                )

            # Marcar como cancelado
            deps.analysis_progress_storage[project_id]["status"] = "cancelled"
            deps.analysis_progress_storage[project_id]["current_phase"] = (
                "Análisis cancelado por el usuario"
            )

        logger.info(f"Analysis cancelled for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "status": "cancelled",
                "message": "Análisis cancelado exitosamente",
            },
        )

    except Exception as e:
        logger.error(f"Error cancelling analysis for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/analysis/stream")
async def stream_analysis_progress(project_id: int):
    """
    Stream SSE del progreso de análisis en tiempo real.

    Envía eventos Server-Sent Events (SSE) con actualizaciones del progreso.
    El cliente debe usar EventSource para consumir este endpoint.

    Eventos emitidos:
    - progress: Actualización del progreso (progress, phase, action)
    - phase_complete: Una fase ha terminado
    - complete: Análisis completado exitosamente
    - error: Error durante el análisis
    - keepalive: Heartbeat para mantener la conexión (cada 15s)

    Args:
        project_id: ID del proyecto

    Returns:
        StreamingResponse con eventos SSE
    """
    import asyncio
    import json

    from fastapi.responses import StreamingResponse

    async def event_generator():
        """Generador de eventos SSE."""
        import time

        last_progress = -1
        last_phase = ""
        keepalive_interval = 15  # segundos
        last_keepalive = time.time()
        max_wait_time = deps.HEAVY_SLOT_TIMEOUT_SECONDS  # alineado con heavy slot

        start_time = time.time()

        while True:
            try:
                # Verificar timeout
                if time.time() - start_time > max_wait_time:
                    yield f"event: error\ndata: {json.dumps({'error': 'Timeout: análisis demasiado largo'})}\n\n"
                    break

                # Obtener progreso actual (lectura protegida)
                with deps._progress_lock:
                    has_progress = project_id in deps.analysis_progress_storage
                    progress_data = (
                        deps.analysis_progress_storage[project_id].copy() if has_progress else None
                    )

                if not has_progress:
                    await asyncio.sleep(0.5)

                    if time.time() - last_keepalive > keepalive_interval:
                        yield f"event: keepalive\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                        last_keepalive = time.time()
                    continue
                status = progress_data.get("status", "pending")
                current_progress = progress_data.get("progress", 0)
                current_phase = progress_data.get("current_phase", "")
                current_action = progress_data.get("current_action", "")

                # Emitir evento si hay cambios
                if current_progress != last_progress or current_phase != last_phase:
                    event_data = {
                        "project_id": project_id,
                        "status": status,
                        "progress": current_progress,
                        "phase": current_phase,
                        "action": current_action,
                        "phases": progress_data.get("phases", []),
                        "estimated_seconds_remaining": progress_data.get(
                            "estimated_seconds_remaining"
                        ),
                    }
                    yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"
                    last_progress = current_progress
                    last_phase = current_phase

                # Verificar si completó
                if status == "completed":
                    complete_data = {
                        "project_id": project_id,
                        "status": "completed",
                        "stats": progress_data.get("stats", {}),
                    }
                    yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"
                    break

                # Verificar si hubo error
                if status == "failed":
                    error_data = {
                        "project_id": project_id,
                        "status": "failed",
                        "error": progress_data.get("error", "Error desconocido"),
                    }
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    break

                # Enviar keepalive periódicamente
                if time.time() - last_keepalive > keepalive_interval:
                    yield f"event: keepalive\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                    last_keepalive = time.time()

                # Esperar antes de siguiente check
                await asyncio.sleep(0.3)

            except asyncio.CancelledError:
                logger.info(f"SSE stream cancelled for project {project_id}")
                break
            except Exception as e:
                logger.error(f"Error in SSE stream for project {project_id}: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Deshabilitar buffering en nginx
        },
    )
