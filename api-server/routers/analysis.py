"""
Router: analysis
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import UploadFile, File
from typing import Optional, Any
from deps import generate_person_aliases
from narrative_assistant.core.result import Result

router = APIRouter()

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


@router.post("/api/projects/{project_id}/analyze", response_model=ApiResponse)
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
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = result.value

        # Determinar el archivo a usar
        tmp_path: Path
        use_temp_file = False

        if file and file.filename:
            # Validar tamaño (50 MB máximo)
            MAX_UPLOAD_BYTES = 50 * 1024 * 1024
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                size = 0
                while chunk := file.file.read(8192):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        Path(tmp_file.name).unlink(missing_ok=True)
                        return ApiResponse(success=False, error="El archivo supera el límite de 50 MB")
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
                    {"id": "parsing", "name": "Lectura del documento", "completed": False, "current": False},
                    {"id": "classification", "name": "Clasificando tipo de documento", "completed": False, "current": False},
                    {"id": "structure", "name": "Identificando capítulos", "completed": False, "current": False},
                    {"id": "ner", "name": "Buscando personajes y lugares", "completed": False, "current": False},
                    {"id": "fusion", "name": "Unificando personajes", "completed": False, "current": False},
                    {"id": "attributes", "name": "Analizando características", "completed": False, "current": False},
                    {"id": "consistency", "name": "Verificando coherencia", "completed": False, "current": False},
                    {"id": "grammar", "name": "Revisando gramática y ortografía", "completed": False, "current": False},
                    {"id": "alerts", "name": "Preparando observaciones", "completed": False, "current": False}
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
            """Ejecuta el análisis real usando el pipeline de NLP."""
            start_time = time.time()
            phases = deps.analysis_progress_storage[project_id]["phases"]

            # Pesos relativos de cada fase (no segundos absolutos)
            # Representan qué proporción del tiempo total consume cada fase
            # BENCHMARK CPU (Ollama llama3.2 sin GPU):
            #   - NER: ~50% (LLM + spaCy)
            #   - Fusion + Coref: ~20% (correferencias usan LLM)
            #   - Attributes: ~12% (LLM)
            #   - Grammar: ~8% (spaCy + reglas)
            #   - Resto: ~10%
            phase_weights = {
                "parsing": 0.01,         # ~1% - instantáneo
                "classification": 0.02,  # ~2% - clasificación tipo documento
                "structure": 0.02,       # ~2% - instantáneo
                "ner": 0.44,             # ~44% - LLM + spaCy
                "fusion": 0.21,          # ~21% - incluye correferencias con LLM
                "attributes": 0.12,      # ~12% - LLM
                "consistency": 0.04,     # ~4%
                "grammar": 0.08,         # ~8% - análisis gramatical y ortográfico
                "alerts": 0.06,          # ~6% - generación de alertas
            }
            phase_order = ["parsing", "classification", "structure", "ner", "fusion", "attributes", "consistency", "grammar", "alerts"]
            current_phase_key = "parsing"
            phase_start_times: dict[str, float] = {}
            phase_durations: dict[str, float] = {}  # Tiempos reales medidos

            def get_phase_progress_range(phase_id: str) -> tuple[int, int]:
                """Calcula el rango de progreso (inicio, fin) para una fase basado en pesos."""
                cumulative = 0.0
                for pid in phase_order:
                    weight = phase_weights.get(pid, 0.05)
                    if pid == phase_id:
                        start_pct = int(cumulative * 100)
                        end_pct = int((cumulative + weight) * 100)
                        return (start_pct, end_pct)
                    cumulative += weight
                return (0, 100)

            def update_time_remaining():
                """Calcula tiempo restante usando tiempos reales de fases completadas."""
                nonlocal current_phase_key

                now = time.time()

                # Calcular tiempo transcurrido en la fase actual
                phase_elapsed = 0
                if current_phase_key in phase_start_times:
                    phase_elapsed = now - phase_start_times[current_phase_key]

                # Calcular el peso total completado y el tiempo real usado
                completed_weight = 0.0
                completed_time = 0.0
                for phase_id in phase_order:
                    if phase_id in phase_durations:
                        completed_weight += phase_weights.get(phase_id, 0.05)
                        completed_time += phase_durations[phase_id]
                    elif phase_id == current_phase_key:
                        break

                # Peso restante (fase actual + fases pendientes)
                current_weight = phase_weights.get(current_phase_key, 0.05)
                try:
                    current_idx = phase_order.index(current_phase_key)
                    pending_phases = phase_order[current_idx + 1:]
                    pending_weight = sum(phase_weights.get(p, 0.05) for p in pending_phases)
                except ValueError:
                    pending_weight = 0.3

                remaining_weight = current_weight + pending_weight

                # Calcular tiempo mínimo = suma de tiempos base de fases no iniciadas
                # Esto evita que el tiempo llegue a 0 mientras haya fases pendientes
                base_times_per_phase = {
                    "parsing": 2,
                    "structure": 2,
                    "ner": 30,        # Sin LLM es más rápido
                    "fusion": 10,
                    "attributes": 15,
                    "consistency": 3,
                    "grammar": 5,     # Análisis gramatical
                    "alerts": 3,
                }
                min_time_remaining = sum(
                    base_times_per_phase.get(p, 5)
                    for p in pending_phases
                )

                # Estimar tiempo restante
                # Solo usar proyección basada en velocidad si tenemos datos de fases lentas
                use_measured_speed = completed_weight > 0.10 and completed_time > 5.0

                if use_measured_speed:
                    # Tenemos datos reales significativos: proyectar basado en velocidad
                    speed = completed_time / completed_weight  # segundos por unidad de peso

                    # Estimar cuánto queda de la fase actual
                    if phase_elapsed > 0:
                        estimated_phase_total = speed * current_weight
                        phase_remaining = max(0, estimated_phase_total - phase_elapsed)
                    else:
                        phase_remaining = speed * current_weight

                    future_time = speed * pending_weight
                    total_remaining = int(phase_remaining + future_time)
                else:
                    # Sin datos suficientes: usar estimación basada en palabras
                    # BENCHMARK CPU (sin LLM en coref):
                    #   - NER ~30-60s, fusion ~10s, attrs ~15s
                    # Estimación: ~60s base + 0.2s por palabra
                    word_count = deps.analysis_progress_storage[project_id].get("metrics", {}).get("word_count", 500)
                    base_estimate = 60 + int(word_count * 0.2)

                    # Ajustar según peso restante
                    total_remaining = int(base_estimate * remaining_weight)

                # El tiempo nunca puede ser menor que la suma de fases pendientes
                deps.analysis_progress_storage[project_id]["estimated_seconds_remaining"] = max(min_time_remaining, total_remaining)

                # Guardar timestamp de última actualización para cálculo dinámico
                deps.analysis_progress_storage[project_id]["_last_progress_update"] = time.time()

            def check_cancelled():
                """Verifica si el análisis fue cancelado por el usuario."""
                with deps._progress_lock:
                    cancelled = deps.analysis_progress_storage.get(project_id, {}).get("status") == "cancelled"
                if cancelled:
                    raise Exception("Análisis cancelado por el usuario")

            # Obtener sesión de BD para este thread
            from narrative_assistant.persistence.database import get_database
            db_session = deps.get_database()

            try:
                # ========== SNAPSHOT PRE-REANÁLISIS (BK-05) ==========
                # Capturar estado actual antes de borrar (comparación antes/después)
                try:
                    from narrative_assistant.persistence.snapshot import SnapshotRepository
                    snapshot_repo = SnapshotRepository()
                    snapshot_repo.create_snapshot(project_id)
                    snapshot_repo.cleanup_old_snapshots(project_id)
                    logger.info(f"Pre-reanalysis snapshot created for project {project_id}")
                except Exception as snap_err:
                    logger.warning(f"Snapshot creation failed (continuing): {snap_err}")

                # ========== LIMPIEZA DE DATOS EXISTENTES ==========
                # Antes de re-analizar, eliminar entidades, alertas y capítulos anteriores
                logger.info(f"Clearing existing data for project {project_id}")
                try:
                    with db_session.connection() as conn:
                        # Borrar alertas existentes
                        cursor = conn.execute("DELETE FROM alerts WHERE project_id = ?", (project_id,))
                        alerts_deleted = cursor.rowcount

                        # Borrar menciones de entidades
                        conn.execute("""
                            DELETE FROM entity_mentions
                            WHERE entity_id IN (SELECT id FROM entities WHERE project_id = ?)
                        """, (project_id,))

                        # Borrar atributos de entidades
                        conn.execute("""
                            DELETE FROM entity_attributes
                            WHERE entity_id IN (SELECT id FROM entities WHERE project_id = ?)
                        """, (project_id,))

                        # Borrar entidades existentes
                        cursor = conn.execute("DELETE FROM entities WHERE project_id = ?", (project_id,))
                        entities_deleted = cursor.rowcount

                        # Borrar capítulos existentes
                        cursor = conn.execute("DELETE FROM chapters WHERE project_id = ?", (project_id,))
                        chapters_deleted = cursor.rowcount

                        # Invalidar caché de perfiles de voz
                        conn.execute("DELETE FROM voice_profiles WHERE project_id = ?", (project_id,))

                        conn.commit()

                    logger.info(f"Cleared: {entities_deleted} entities, {alerts_deleted} alerts, {chapters_deleted} chapters")
                except Exception as clear_err:
                    logger.warning(f"Error clearing project data (continuing anyway): {clear_err}")

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

                # ========== FASE 1: PARSING ==========
                current_phase_key = "parsing"
                phase_start_times["parsing"] = time.time()
                pct_start, pct_end = get_phase_progress_range("parsing")
                phases[0]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Leyendo el documento..."

                doc_format = detect_format(tmp_path)
                parser = get_parser(doc_format)
                parse_result = parser.parse(tmp_path)

                if parse_result.is_failure:
                    raise Exception(f"Error parsing document: {parse_result.error}")

                raw_document = parse_result.value
                full_text = raw_document.full_text
                word_count = len(full_text.split())

                deps.analysis_progress_storage[project_id]["progress"] = pct_end
                deps.analysis_progress_storage[project_id]["metrics"]["word_count"] = word_count
                phase_durations["parsing"] = time.time() - phase_start_times["parsing"]
                check_cancelled()  # Verificar cancelación
                phases[0]["completed"] = True
                phases[0]["current"] = False
                phases[0]["duration"] = round(phase_durations["parsing"], 1)
                update_time_remaining()

                # Actualizar word_count del proyecto inmediatamente para que el frontend lo muestre
                try:
                    project.word_count = word_count
                    proj_manager = ProjectManager(db_session)
                    proj_manager.update(project)
                    logger.debug(f"Updated project word_count to {word_count}")
                except Exception as e:
                    logger.warning(f"Could not update project word_count: {e}")

                logger.info(f"Parsing complete: {word_count} words")

                # ========== FASE 2: CLASIFICACIÓN DE DOCUMENTO ==========
                current_phase_key = "classification"
                phase_start_times["classification"] = time.time()
                cls_pct_start, cls_pct_end = get_phase_progress_range("classification")
                phases[1]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = cls_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Clasificando tipo de documento..."

                from narrative_assistant.parsers.document_classifier import classify_document, DocumentType

                doc_title = project.name if project else None
                classification = classify_document(full_text, title=doc_title)  # Usa muestreo múltiple
                document_type = classification.document_type.value
                analysis_settings = classification.recommended_settings

                logger.info(f"Document classified as: {document_type} (confidence: {classification.confidence:.2f})")
                logger.debug(f"Classification indicators: {classification.indicators}")

                # Guardar clasificación en el progreso para uso posterior
                deps.analysis_progress_storage[project_id]["document_type"] = document_type
                deps.analysis_progress_storage[project_id]["document_classification"] = {
                    "type": document_type,
                    "confidence": classification.confidence,
                    "indicators": classification.indicators,
                    "settings": analysis_settings,
                }

                # Actualizar settings del proyecto con el tipo de documento
                try:
                    deps.project_manager = ProjectManager(db_session)
                    project_settings = project.settings or {}
                    project_settings["document_type"] = document_type
                    project_settings["document_classification"] = {
                        "type": document_type,
                        "confidence": classification.confidence,
                        "indicators": classification.indicators,
                    }
                    project_settings["recommended_analysis"] = analysis_settings

                    deps.project_manager.update_project(project_id, {
                        "settings": json.dumps(project_settings)
                    })
                    logger.info(f"Saved document type to project settings: {document_type}")
                except Exception as e:
                    logger.warning(f"Could not save document type to project: {e}")

                # Completar fase de clasificación
                deps.analysis_progress_storage[project_id]["progress"] = cls_pct_end
                phase_durations["classification"] = time.time() - phase_start_times["classification"]
                phases[1]["completed"] = True
                phases[1]["current"] = False
                phases[1]["duration"] = round(phase_durations["classification"], 1)
                update_time_remaining()
                check_cancelled()

                # ========== FASE 3: ESTRUCTURA ==========
                current_phase_key = "structure"
                phase_start_times["structure"] = time.time()
                pct_start, pct_end = get_phase_progress_range("structure")
                phases[2]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Identificando la estructura del documento..."

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
                            # Convertir secciones a diccionarios
                            sections_data = []
                            if hasattr(ch, 'sections') and ch.sections:
                                sections_data = [s.to_dict() for s in ch.sections]
                                logger.debug(f"Capítulo {ch.number}: {len(sections_data)} secciones detectadas")
                            chapters_data.append({
                                "project_id": project_id,
                                "chapter_number": ch.number,
                                "title": ch.title,
                                "content": content,
                                "start_char": ch.start_char,
                                "end_char": ch.end_char,
                                "word_count": ch_word_count,
                                "structure_type": ch.structure_type.value if hasattr(ch.structure_type, 'value') else str(ch.structure_type),
                                "sections": sections_data
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
                        "structure_type": "chapter",
                        "sections": []
                    })
                    chapters_count = 1

                # Persistir capítulos
                _persist_chapters_to_db(chapters_data, project_id, db_session)

                # Cargar capítulos de la BD con sus IDs para mapear menciones
                chapters_with_ids = []
                if deps.chapter_repository:
                    chapters_with_ids = deps.chapter_repository.get_by_project(project_id)
                    logger.debug(f"Loaded {len(chapters_with_ids)} chapters with IDs for mention mapping")

                # Helper para encontrar chapter_id basado en posición de carácter
                def find_chapter_id_for_position(char_position: int) -> int | None:
                    """Encuentra el chapter_id que contiene la posición de carácter dada."""
                    for ch in chapters_with_ids:
                        if ch.start_char <= char_position <= ch.end_char:
                            return ch.id
                    return None

                deps.analysis_progress_storage[project_id]["progress"] = pct_end
                deps.analysis_progress_storage[project_id]["metrics"]["chapters_found"] = chapters_count
                phase_durations["structure"] = time.time() - phase_start_times["structure"]
                phases[2]["completed"] = True
                phases[2]["current"] = False
                phases[2]["duration"] = round(phase_durations["structure"], 1)
                update_time_remaining()

                logger.info(f"Structure detection complete: {chapters_count} chapters")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 4: NER ==========
                current_phase_key = "ner"
                phase_start_times["ner"] = time.time()
                ner_pct_start, ner_pct_end = get_phase_progress_range("ner")
                phases[3]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = ner_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Buscando personajes, lugares y otros elementos..."

                # Callback para actualizar progreso durante NER
                def ner_progress_callback(fase: str, pct: float, msg: str):
                    """Actualiza el progreso del análisis durante NER."""
                    # NER va de ner_pct_start a ner_pct_end
                    ner_range = ner_pct_end - ner_pct_start
                    ner_progress = ner_pct_start + int(pct * ner_range)
                    deps.analysis_progress_storage[project_id]["progress"] = ner_progress
                    deps.analysis_progress_storage[project_id]["current_action"] = msg
                    update_time_remaining()

                # Verificar si el modelo transformer NER necesita descargarse
                # y actualizar progreso para informar al usuario
                try:
                    from narrative_assistant.core.model_manager import ModelType, get_model_manager
                    manager = get_model_manager()
                    if not manager.get_model_path(ModelType.TRANSFORMER_NER):
                        deps.analysis_progress_storage[project_id]["current_phase"] = "Descargando modelo NER (~500 MB, solo la primera vez)..."
                        deps.analysis_progress_storage[project_id]["current_action"] = "Esto puede tardar unos minutos..."
                except Exception:
                    pass  # No bloquear análisis si falla la verificación

                # Habilitar preprocesamiento con LLM para mejor detección de entidades
                ner_extractor = NERExtractor(use_llm_preprocessing=True)
                ner_result = ner_extractor.extract_entities(
                    full_text,
                    progress_callback=ner_progress_callback,
                )

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

                    # PRE-PROCESAMIENTO: Eliminar entidades solapadas, preferir la más larga
                    # Ej: si tenemos "Laura" y "Laura Garcia" en la misma posición, quedarnos con "Laura Garcia"
                    def filter_overlapping_entities(entities):
                        if not entities:
                            return []
                        # Ordenar por posición y luego por longitud (más larga primero)
                        sorted_ents = sorted(entities, key=lambda e: (e.start_char, -(e.end_char - e.start_char)))
                        result = []
                        for ent in sorted_ents:
                            # Verificar si se solapa con alguna entidad ya aceptada
                            overlaps = False
                            for accepted in result:
                                # Solapamiento: no son disjuntas
                                if not (ent.end_char <= accepted.start_char or ent.start_char >= accepted.end_char):
                                    overlaps = True
                                    break
                            if not overlaps:
                                result.append(ent)
                        return result

                    raw_entities = filter_overlapping_entities(raw_entities)
                    logger.info(f"After overlap filtering: {len(raw_entities)} entities")

                    # Agrupar entidades por nombre canónico para contar menciones
                    # IMPORTANTE: Agrupar solo por nombre, no por label, para unificar
                    # menciones de la misma entidad con diferentes etiquetas (PER vs MISC)
                    #
                    # ESTRATEGIA DE AGRUPACIÓN:
                    # 1. Normalizar a minúsculas SOLO para comparación
                    # 2. Pero preservar el texto original con mayúsculas para el nombre canónico
                    # 3. "Juan García" y "Juan" son entidades DIFERENTES
                    # 4. "Papa" y "papa" serían la misma clave (pero spaCy raramente detecta "papa" como NER)
                    entity_mentions: dict[str, list] = {}  # normalized_name -> [ExtractedEntity, ...]
                    for ent in raw_entities:
                        # Normalizar para agrupación: minúsculas + espacios normalizados
                        normalized = ' '.join(ent.text.strip().lower().split())
                        # Usar nombre normalizado como clave de agrupación
                        key = normalized
                        if key not in entity_mentions:
                            entity_mentions[key] = []
                        entity_mentions[key].append(ent)

                    # DEBUG: Log de agrupación de menciones
                    logger.info(f"DEBUG NER grouping: {len(raw_entities)} raw mentions -> {len(entity_mentions)} unique entities")
                    # Mostrar top 10 entidades por menciones
                    sorted_entities = sorted(entity_mentions.items(), key=lambda x: len(x[1]), reverse=True)[:10]
                    for key, mentions in sorted_entities:
                        logger.info(f"  Entity '{key}': {len(mentions)} mentions")

                    # NOTA: Ya no se filtra por mínimo de menciones.
                    # El filtrado de falsos positivos se hace en NERExtractor._is_valid_entity()
                    # Un personaje puede aparecer solo 1 vez y sigue siendo válido.

                    logger.info(f"NER: {len(raw_entities)} menciones totales, {len(entity_mentions)} entidades únicas")

                    # Recolectar todos los nombres canónicos para evitar conflictos de aliases
                    all_canonical_names = set()
                    for key, mentions_list in entity_mentions.items():
                        first_mention = mentions_list[0]
                        best_mentions = [m for m in mentions_list if m.label == EntityLabel.PER]
                        canonical_text = best_mentions[0].text if best_mentions else first_mention.text
                        all_canonical_names.add(canonical_text)

                    # Crear entidades únicas con conteo de menciones
                    total_entities_to_create = len(entity_mentions)
                    entities_created = 0
                    for key, mentions_list in entity_mentions.items():
                        first_mention = mentions_list[0]
                        mention_count = len(mentions_list)

                        # Calcular importancia basada en número de menciones
                        if mention_count >= 20:
                            importance = EntityImportance.PRINCIPAL
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

                        # Determinar el tipo de entidad por votación (label más común)
                        # PER tiene prioridad sobre MISC para personajes
                        from collections import Counter
                        label_counts = Counter(m.label for m in mentions_list)
                        # Priorizar PER sobre MISC si hay ambos
                        if EntityLabel.PER in label_counts and EntityLabel.MISC in label_counts:
                            best_label = EntityLabel.PER
                        else:
                            best_label = label_counts.most_common(1)[0][0]

                        # Usar el texto de la primera mención con el mejor label, si existe
                        best_mentions = [m for m in mentions_list if m.label == best_label]
                        canonical_text = best_mentions[0].text if best_mentions else first_mention.text

                        # Generar aliases automáticos para personajes con nombres compuestos
                        entity_type = label_to_type.get(best_label, EntityType.CONCEPT)
                        auto_aliases = []
                        if entity_type == EntityType.CHARACTER:
                            auto_aliases = generate_person_aliases(canonical_text, all_canonical_names)
                            if auto_aliases:
                                logger.debug(f"Generated aliases for '{canonical_text}': {auto_aliases}")

                        # Crear objeto Entity
                        entity = Entity(
                            project_id=project_id,
                            entity_type=entity_type,
                            canonical_name=canonical_text,  # Usar texto de mejor mención
                            aliases=auto_aliases,
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

                            # Crear menciones en BD - usar batch para eficiencia
                            mentions_to_create = []
                            for ent in mentions_list:
                                # Encontrar chapter_id basado en posición
                                mention_chapter_id = find_chapter_id_for_position(ent.start_char)

                                mention = EntityMention(
                                    entity_id=entity_id,
                                    surface_form=ent.text,
                                    start_char=ent.start_char,
                                    end_char=ent.end_char,
                                    chapter_id=mention_chapter_id,
                                    confidence=ent.confidence,
                                    source=ent.source,
                                )
                                mentions_to_create.append(mention)

                            # Log detallado de menciones a crear (para debug)
                            if len(mentions_to_create) >= 5:
                                sample_forms = [m.surface_form for m in mentions_to_create[:5]]
                                logger.info(f"Entity '{entity.canonical_name}': Creating {len(mentions_to_create)} mentions. Sample surface forms: {sample_forms}")

                            # Insertar todas las menciones en batch
                            try:
                                mentions_created = entity_repo.create_mentions_batch(mentions_to_create)
                                logger.debug(f"Entity '{entity.canonical_name}': Batch created {mentions_created} mentions")
                            except Exception as batch_err:
                                logger.warning(f"Batch insert failed for {entity.canonical_name}, falling back to individual: {batch_err}")
                                # Fallback a inserción individual
                                mentions_created = 0
                                for mention in mentions_to_create:
                                    try:
                                        entity_repo.create_mention(mention)
                                        mentions_created += 1
                                    except Exception as me:
                                        logger.warning(f"Error creating mention for {entity.canonical_name} at {mention.start_char}: {me}")

                            # Log si se crearon menos menciones de las esperadas
                            if mentions_created != len(mentions_list):
                                logger.warning(f"Entity '{entity.canonical_name}': Created {mentions_created}/{len(mentions_list)} mentions - MISMATCH!")
                            else:
                                logger.info(f"Entity '{entity.canonical_name}': Successfully created {mentions_created} mentions")

                            # Actualizar progreso cada 5 entidades
                            entities_created += 1
                            if entities_created % 5 == 0 and total_entities_to_create > 0:
                                # Sub-progreso dentro del rango de NER
                                sub_pct = entities_created / total_entities_to_create
                                sub_progress = ner_pct_start + int(sub_pct * (ner_pct_end - ner_pct_start))
                                deps.analysis_progress_storage[project_id]["progress"] = min(ner_pct_end, sub_progress)
                                update_time_remaining()

                        except Exception as e:
                            logger.warning(f"Error creating entity {first_mention.text}: {e}")

                deps.analysis_progress_storage[project_id]["progress"] = ner_pct_end
                # No actualizar entities_found aquí - se actualiza después de fusión
                phase_durations["ner"] = time.time() - phase_start_times["ner"]
                phases[3]["completed"] = True
                phases[3]["current"] = False
                phases[3]["duration"] = round(phase_durations["ner"], 1)
                update_time_remaining()

                logger.info(f"NER complete: {len(entities)} entities")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 3.25: VALIDACIÓN DE ENTIDADES CON LLM ==========
                # Filtrar entidades que no son válidas (descripciones, frases, etc.)
                deps.analysis_progress_storage[project_id]["current_action"] = "Verificando personajes detectados..."
                try:
                    from narrative_assistant.llm.client import get_llm_client
                    import json as json_module

                    llm_client = get_llm_client()
                    if llm_client and llm_client.is_available and len(entities) > 0:
                        # Preparar lista de entidades para validar
                        entities_to_validate = [
                            {"name": e.canonical_name, "type": e.entity_type.value}
                            for e in entities
                        ]

                        validation_prompt = f"""Revisa esta lista de entidades extraídas de un texto narrativo.
Marca como INVÁLIDAS las que NO sean entidades reales:
- Descripciones físicas ("Sus ojos verdes", "cabello negro")
- Frases incompletas o fragmentos
- Pronombres solos ("él", "ella") - a menos que sean nombres propios
- Adjetivos o expresiones genéricas

ENTIDADES A VALIDAR:
{json_module.dumps(entities_to_validate, ensure_ascii=False, indent=2)}

Responde SOLO con JSON:
{{"invalid": ["nombre1", "nombre2", ...]}}

Si todas son válidas, responde: {{"invalid": []}}

JSON:"""

                        response = llm_client.complete(
                            validation_prompt,
                            system="Eres un experto en NER. Identifica entidades inválidas (no son personajes, lugares u organizaciones reales).",
                            temperature=0.1,
                        )

                        if response:
                            # Parsear respuesta
                            try:
                                # Limpiar respuesta
                                cleaned = response.strip()
                                if cleaned.startswith("```"):
                                    lines = cleaned.split("\n")
                                    lines = [l for l in lines if not l.startswith("```")]
                                    cleaned = "\n".join(lines)
                                start_idx = cleaned.find("{")
                                end_idx = cleaned.rfind("}") + 1
                                if start_idx != -1 and end_idx > start_idx:
                                    cleaned = cleaned[start_idx:end_idx]
                                data = json_module.loads(cleaned)
                                invalid_names = set(n.lower() for n in data.get("invalid", []))

                                if invalid_names:
                                    # Filtrar entidades inválidas
                                    before_count = len(entities)
                                    entities_to_remove = []
                                    for ent in entities:
                                        if ent.canonical_name.lower() in invalid_names:
                                            entities_to_remove.append(ent)
                                            # Desactivar en BD
                                            try:
                                                entity_repo.delete_entity(ent.id, hard_delete=False)
                                            except Exception:
                                                pass

                                    entities = [e for e in entities if e not in entities_to_remove]
                                    removed_count = before_count - len(entities)

                                    if removed_count > 0:
                                        logger.info(
                                            f"Validación LLM: {removed_count} entidades inválidas removidas: "
                                            f"{[e.canonical_name for e in entities_to_remove]}"
                                        )
                            except Exception as e:
                                logger.debug(f"Error parseando validación LLM: {e}")

                except Exception as e:
                    logger.warning(f"Error en validación de entidades con LLM (continuando): {e}")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 3.5: FUSIÓN DE ENTIDADES ==========
                # Esta fase fusiona entidades que son la misma persona/lugar
                # por ejemplo: "María" y "María Sánchez", "Juan" y "Juan Pérez"
                # También resuelve correferencias: "Él" → "Juan"
                current_phase_key = "fusion"
                phase_start_times["fusion"] = time.time()
                fusion_pct_start, fusion_pct_end = get_phase_progress_range("fusion")
                phases[4]["current"] = True  # Marcar fase fusion como activa en UI
                deps.analysis_progress_storage[project_id]["progress"] = fusion_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Unificando personajes mencionados de diferentes formas..."
                deps.analysis_progress_storage[project_id]["current_action"] = "Preparando unificación..."

                try:
                    from narrative_assistant.entities.semantic_fusion import get_semantic_fusion_service
                    from narrative_assistant.nlp.coref import resolve_coreferences
                    from narrative_assistant.entities.models import EntityType

                    fusion_service = get_semantic_fusion_service()
                    entity_repo = get_entity_repository()

                    deps.analysis_progress_storage[project_id]["current_action"] = f"Comparando {len(entities)} entidades..."

                    # 1. Aplicar fusión semántica a entidades del mismo tipo
                    entities_by_type: dict[EntityType, list] = {}
                    for ent in entities:
                        if ent.entity_type not in entities_by_type:
                            entities_by_type[ent.entity_type] = []
                        entities_by_type[ent.entity_type].append(ent)

                    fusion_pairs: list[tuple] = []  # (entity_to_keep, entity_to_merge)

                    # Helper function to check if one name contains another as a word subset
                    def is_name_subset(short_name: str, long_name: str) -> bool:
                        """Check if short_name's words are a subset of long_name's words."""
                        short_words = set(short_name.lower().split())
                        long_words = set(long_name.lower().split())
                        return short_words and long_words and short_words < long_words

                    for entity_type, type_entities in entities_by_type.items():
                        # Solo fusionar si hay más de una entidad del mismo tipo
                        if len(type_entities) < 2:
                            continue

                        # Log entities for debugging fusion issues
                        entity_names = [e.canonical_name for e in type_entities]
                        logger.info(f"Fusion check: {entity_type.value} entities = {entity_names}")

                        # Comparar cada par de entidades
                        for i, ent1 in enumerate(type_entities):
                            for j, ent2 in enumerate(type_entities):
                                if i >= j:  # Evitar duplicados y compararse consigo mismo
                                    continue

                                # PRE-CHECK: If one name is a word subset of another, they should merge
                                # This handles cases like "Juan" ⊂ "Juan Pérez"
                                name1 = ent1.canonical_name
                                name2 = ent2.canonical_name
                                force_merge = is_name_subset(name1, name2) or is_name_subset(name2, name1)

                                if force_merge:
                                    logger.info(
                                        f"Fusión forzada por nombre contenido: '{name1}' ↔ '{name2}'"
                                    )

                                # Calcular si deben fusionarse
                                result = fusion_service.should_merge(ent1, ent2)

                                # Merge if semantic service says so OR if name containment detected
                                if result.should_merge or force_merge:
                                    merge_reason = (
                                        f"nombre contenido ({name1} ⊂ {name2} o viceversa)"
                                        if force_merge and not result.should_merge
                                        else result.reason
                                    )
                                    logger.info(
                                        f"Fusión sugerida: '{ent1.canonical_name}' + '{ent2.canonical_name}' "
                                        f"(similaridad: {result.similarity:.2f}, razón: {merge_reason})"
                                    )
                                    # Priorizar el nombre más descriptivo (nombre propio > pronombre)
                                    # Criterios:
                                    # 1. Nombre más largo generalmente es más descriptivo
                                    # 2. Nombre con mayúscula inicial es más probable que sea nombre propio
                                    # 3. Evitar pronombres como nombre canónico
                                    def name_score(ent):
                                        name = ent.canonical_name
                                        score = 0
                                        # Longitud: nombres más largos son más descriptivos
                                        score += len(name) * 2
                                        # Nombre propio (empieza con mayúscula)
                                        if name and name[0].isupper():
                                            score += 20
                                        # Tiene múltiples palabras (apellido)
                                        if ' ' in name:
                                            score += 30
                                        # Penalizar pronombres
                                        lower_name = name.lower()
                                        pronouns = {'él', 'ella', 'ellos', 'ellas', 'este', 'esta', 'ese', 'esa'}
                                        if lower_name in pronouns:
                                            score -= 100
                                        return score

                                    score1 = name_score(ent1)
                                    score2 = name_score(ent2)

                                    if score1 >= score2:
                                        fusion_pairs.append((ent1, ent2))
                                    else:
                                        fusion_pairs.append((ent2, ent1))

                    # Ejecutar las fusiones
                    merged_entity_ids = set()
                    if fusion_pairs:
                        deps.analysis_progress_storage[project_id]["current_action"] = f"Unificando {len(fusion_pairs)} pares de nombres similares..."

                    for idx, (keep_entity, merge_entity) in enumerate(fusion_pairs):
                        if merge_entity.id in merged_entity_ids:
                            continue  # Ya fue fusionada

                        try:
                            # Añadir como alias
                            if keep_entity.aliases is None:
                                keep_entity.aliases = []
                            if merge_entity.canonical_name not in keep_entity.aliases:
                                keep_entity.aliases.append(merge_entity.canonical_name)

                            # Sumar menciones
                            keep_entity.mention_count = (keep_entity.mention_count or 0) + (merge_entity.mention_count or 0)

                            # Registrar fusión
                            if keep_entity.merged_from_ids is None:
                                keep_entity.merged_from_ids = []
                            if merge_entity.id:
                                keep_entity.merged_from_ids.append(merge_entity.id)

                            # Actualizar entidad en BD
                            entity_repo.update_entity(
                                entity_id=keep_entity.id,
                                aliases=keep_entity.aliases,
                                merged_from_ids=keep_entity.merged_from_ids,
                            )
                            entity_repo.increment_mention_count(keep_entity.id, merge_entity.mention_count or 0)

                            # Recalcular importancia basada en nuevas menciones totales
                            new_mention_count = keep_entity.mention_count
                            if new_mention_count >= 20:
                                new_importance = EntityImportance.PRINCIPAL
                            elif new_mention_count >= 10:
                                new_importance = EntityImportance.HIGH
                            elif new_mention_count >= 5:
                                new_importance = EntityImportance.MEDIUM
                            elif new_mention_count >= 2:
                                new_importance = EntityImportance.LOW
                            else:
                                new_importance = EntityImportance.MINIMAL

                            if new_importance != keep_entity.importance:
                                entity_repo.update_entity(
                                    entity_id=keep_entity.id,
                                    importance=new_importance,
                                )
                                keep_entity.importance = new_importance
                                logger.debug(f"Importancia actualizada: '{keep_entity.canonical_name}' -> {new_importance.value}")

                            # Reasignar menciones de la entidad fusionada
                            if merge_entity.id and keep_entity.id:
                                entity_repo.move_mentions(merge_entity.id, keep_entity.id)

                            # Desactivar entidad fusionada
                            entity_repo.delete_entity(merge_entity.id, hard_delete=False)

                            merged_entity_ids.add(merge_entity.id)

                            logger.info(
                                f"Fusión ejecutada: '{merge_entity.canonical_name}' → '{keep_entity.canonical_name}'"
                            )

                            # Actualizar progreso cada 5 fusiones
                            if (idx + 1) % 5 == 0:
                                deps.analysis_progress_storage[project_id]["current_action"] = f"Unificando nombres: {keep_entity.canonical_name}... ({idx + 1}/{len(fusion_pairs)})"

                        except Exception as e:
                            logger.warning(f"Error fusionando {merge_entity.canonical_name} → {keep_entity.canonical_name}: {e}")

                    # Actualizar lista de entidades activas
                    entities = [e for e in entities if e.id not in merged_entity_ids]

                    if fusion_pairs:
                        deps.analysis_progress_storage[project_id]["current_action"] = f"Unificados {len(merged_entity_ids)} personajes duplicados"

                    # Reconciliar contadores de menciones para garantizar consistencia
                    # Esto asegura que mention_count coincida con las menciones reales en la BD
                    try:
                        reconciled = entity_repo.reconcile_all_mention_counts(project_id)
                        logger.info(f"Reconciliados contadores de menciones para {reconciled} entidades")

                        # Recargar entidades con contadores actualizados
                        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
                    except Exception as recon_err:
                        logger.warning(f"Error reconciliando contadores de menciones: {recon_err}")

                    deps.analysis_progress_storage[project_id]["progress"] = 57
                    update_time_remaining()

                    # 2. Aplicar resolución de correferencias con votación multi-método
                    # Usa: embeddings semánticos, LLM local (Ollama), análisis morfosintáctico, heurísticas
                    deps.analysis_progress_storage[project_id]["current_phase"] = "Identificando referencias cruzadas entre personajes..."

                    coref_result = None  # Inicializar para uso posterior en extracción de atributos
                    try:
                        from narrative_assistant.nlp.coreference_resolver import (
                            resolve_coreferences_voting,
                            CorefConfig,
                            CorefMethod,
                            MentionType as CorefMentionType,
                        )

                        # Configurar métodos de resolución
                        coref_config = CorefConfig(
                            enabled_methods=[
                                CorefMethod.EMBEDDINGS,
                                CorefMethod.LLM,
                                CorefMethod.MORPHO,
                                CorefMethod.HEURISTICS,
                            ],
                            min_confidence=0.5,
                            consensus_threshold=0.6,
                            use_chapter_boundaries=True,
                            ollama_model="llama3.2",
                        )

                        # Resolver con información de capítulos
                        coref_result = resolve_coreferences_voting(
                            text=full_text,
                            chapters=chapters_data,
                            config=coref_config,
                        )

                        logger.info(
                            f"Correferencias (votación): {coref_result.total_chains} cadenas, "
                            f"{coref_result.total_mentions} menciones, "
                            f"{len(coref_result.unresolved)} sin resolver"
                        )

                        # Log de contribución de métodos
                        for method, count in coref_result.method_contributions.items():
                            logger.debug(f"  Método {method.value}: {count} resoluciones")

                        # Vincular cadenas con entidades
                        character_entities = [e for e in entities if e.entity_type == EntityType.CHARACTER]

                        for chain in coref_result.chains:
                            # REGLA: Si la cadena no tiene mención principal (solo pronombres),
                            # no puede vincularse a ninguna entidad - ignorar
                            if not chain.main_mention:
                                logger.debug(
                                    f"Cadena de correferencia ignorada (solo pronombres): "
                                    f"{[m.text for m in chain.mentions[:3]]}..."
                                )
                                continue

                            # Buscar entidad que coincida con la mención principal
                            matching_entity = None

                            for ent in character_entities:
                                # Coincidir por nombre canónico
                                if (ent.canonical_name and chain.main_mention and
                                    ent.canonical_name.lower() == chain.main_mention.lower()):
                                    matching_entity = ent
                                    break

                                # Coincidir por alias
                                if ent.aliases:
                                    for alias in ent.aliases:
                                        if chain.main_mention and alias.lower() == chain.main_mention.lower():
                                            matching_entity = ent
                                            break

                                # Coincidir por cualquier mención en la cadena
                                if not matching_entity:
                                    for mention in chain.mentions:
                                        if (ent.canonical_name and
                                            mention.text.lower() == ent.canonical_name.lower()):
                                            matching_entity = ent
                                            break

                            if matching_entity:
                                # Contar menciones de pronombres en la cadena
                                pronoun_count = sum(
                                    1 for m in chain.mentions
                                    if m.mention_type == CorefMentionType.PRONOUN
                                )

                                if pronoun_count > 0:
                                    try:
                                        entity_repo.increment_mention_count(matching_entity.id, pronoun_count)
                                        matching_entity.mention_count = (matching_entity.mention_count or 0) + pronoun_count

                                        # Recalcular importancia
                                        new_mc = matching_entity.mention_count
                                        if new_mc >= 20:
                                            new_imp = EntityImportance.PRINCIPAL
                                        elif new_mc >= 10:
                                            new_imp = EntityImportance.HIGH
                                        elif new_mc >= 5:
                                            new_imp = EntityImportance.MEDIUM
                                        elif new_mc >= 2:
                                            new_imp = EntityImportance.LOW
                                        else:
                                            new_imp = EntityImportance.MINIMAL

                                        if new_imp != matching_entity.importance:
                                            entity_repo.update_entity(
                                                entity_id=matching_entity.id,
                                                importance=new_imp,
                                            )
                                            matching_entity.importance = new_imp

                                        logger.debug(
                                            f"Correferencia: +{pronoun_count} pronombres → '{matching_entity.canonical_name}'"
                                        )
                                    except Exception as e:
                                        logger.warning(f"Error actualizando correferencias: {e}")

                                # Añadir aliases nuevos
                                new_aliases = []
                                for mention in chain.mentions:
                                    if (mention.mention_type == CorefMentionType.PROPER_NOUN and
                                        mention.text.lower() != matching_entity.canonical_name.lower()):
                                        if matching_entity.aliases is None:
                                            matching_entity.aliases = []
                                        if mention.text not in matching_entity.aliases:
                                            matching_entity.aliases.append(mention.text)
                                            new_aliases.append(mention.text)

                                if new_aliases:
                                    try:
                                        entity_repo.update_entity(
                                            entity_id=matching_entity.id,
                                            aliases=matching_entity.aliases,
                                        )
                                        logger.debug(f"Nuevos aliases para '{matching_entity.canonical_name}': {new_aliases}")
                                    except Exception as e:
                                        logger.warning(f"Error actualizando aliases: {e}")

                    except ImportError as e:
                        logger.warning(f"Módulo de correferencias no disponible: {e}")
                    except Exception as e:
                        logger.warning(f"Error en resolución de correferencias: {e}")

                    phase_durations["fusion"] = time.time() - phase_start_times["fusion"]
                    deps.analysis_progress_storage[project_id]["progress"] = fusion_pct_end
                    # Actualizar con entidades únicas (después de fusión)
                    deps.analysis_progress_storage[project_id]["metrics"]["entities_found"] = len(entities)
                    deps.analysis_progress_storage[project_id]["current_action"] = f"Encontrados {len(entities)} personajes y elementos únicos"
                    # Marcar fase fusion como completada en UI
                    phases[4]["completed"] = True
                    phases[4]["current"] = False
                    phases[4]["duration"] = round(phase_durations["fusion"], 1)
                    update_time_remaining()

                    logger.info(
                        f"Fusión de entidades completada en {phase_durations['fusion']:.1f}s: "
                        f"{len(merged_entity_ids)} entidades fusionadas, "
                        f"{len(entities)} entidades activas"
                    )

                    # ========== BUSCAR MENCIONES ADICIONALES ==========
                    # Después de NER y fusión, buscar menciones adicionales
                    # de nombres conocidos que el NER pudo haber pasado por alto
                    try:
                        from narrative_assistant.nlp.mention_finder import get_mention_finder

                        mention_finder = get_mention_finder()
                        deps.analysis_progress_storage[project_id]["current_action"] = "Buscando menciones adicionales..."

                        # Recopilar nombres y aliases de entidades
                        entity_names = [e.canonical_name for e in entities if e.canonical_name]
                        aliases_dict = {}
                        for e in entities:
                            if e.canonical_name and e.aliases:
                                aliases_dict[e.canonical_name] = e.aliases

                        # Obtener posiciones ya detectadas por NER
                        existing_positions = set()
                        for entity in entities:
                            mentions_db = entity_repo.get_mentions_by_entity(entity.id)
                            for m in mentions_db:
                                existing_positions.add((m.start_char, m.end_char))

                        # Buscar menciones adicionales
                        additional_mentions = mention_finder.find_all_mentions(
                            text=full_text,
                            entity_names=entity_names,
                            aliases=aliases_dict,
                            existing_positions=existing_positions,
                        )

                        # Agrupar menciones por entidad y guardar
                        from narrative_assistant.entities.models import EntityMention as EM
                        mentions_by_entity: dict[str, list] = {}
                        for am in additional_mentions:
                            if am.entity_name not in mentions_by_entity:
                                mentions_by_entity[am.entity_name] = []
                            mentions_by_entity[am.entity_name].append(am)

                        additional_count = 0
                        for entity in entities:
                            name = entity.canonical_name
                            if name in mentions_by_entity:
                                new_mentions = mentions_by_entity[name]
                                for am in new_mentions:
                                    # Encontrar chapter_id
                                    ch_id = find_chapter_id_for_position(am.start_char)
                                    mention = EM(
                                        entity_id=entity.id,
                                        surface_form=am.surface_form,
                                        start_char=am.start_char,
                                        end_char=am.end_char,
                                        chapter_id=ch_id,
                                        confidence=am.confidence,
                                        source="mention_finder",
                                    )
                                    try:
                                        entity_repo.create_mention(mention)
                                        additional_count += 1
                                    except Exception as me:
                                        pass  # Duplicado o error, ignorar

                        if additional_count > 0:
                            logger.info(f"MentionFinder: Added {additional_count} additional mentions")
                            deps.analysis_progress_storage[project_id]["current_action"] = f"Encontradas {additional_count} menciones adicionales"

                    except Exception as mf_err:
                        logger.warning(f"MentionFinder failed (non-critical): {mf_err}")

                    # ========== RECALCULAR IMPORTANCIA FINAL ==========
                    # La importancia se calcula DESPUÉS de fusiones y correferencias
                    # basada en el conteo final de menciones en la BD
                    logger.info("Recalculando importancia de entidades...")
                    db = deps.get_database()
                    for entity in entities:
                        try:
                            # Obtener conteo real de menciones desde la BD
                            with db.connection() as conn:
                                cursor = conn.execute(
                                    "SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?",
                                    (entity.id,)
                                )
                                row = cursor.fetchone()
                                real_mention_count = row[0] if row else 0

                            # Calcular nueva importancia
                            if real_mention_count >= 20:
                                new_importance = EntityImportance.PRINCIPAL
                            elif real_mention_count >= 10:
                                new_importance = EntityImportance.HIGH
                            elif real_mention_count >= 5:
                                new_importance = EntityImportance.MEDIUM
                            elif real_mention_count >= 2:
                                new_importance = EntityImportance.LOW
                            else:
                                new_importance = EntityImportance.MINIMAL

                            # Actualizar si cambió
                            if new_importance != entity.importance or entity.mention_count != real_mention_count:
                                entity_repo.update_entity(
                                    entity_id=entity.id,
                                    importance=new_importance,
                                )
                                # También actualizar mention_count en BD
                                with db.connection() as conn:
                                    conn.execute(
                                        "UPDATE entities SET mention_count = ? WHERE id = ?",
                                        (real_mention_count, entity.id)
                                    )
                                entity.importance = new_importance
                                entity.mention_count = real_mention_count
                                logger.debug(f"'{entity.canonical_name}': {real_mention_count} menciones -> {new_importance.value}")
                        except Exception as e:
                            logger.warning(f"Error recalculando importancia de '{entity.canonical_name}': {e}")

                except Exception as e:
                    logger.warning(f"Error en fusión de entidades (continuando sin fusión): {e}")
                    phase_durations["fusion"] = time.time() - phase_start_times.get("fusion", time.time())
                    # Marcar fusion como completada aunque haya fallado (para continuar UI)
                    phases[4]["completed"] = True
                    phases[4]["current"] = False
                    phases[4]["duration"] = round(phase_durations["fusion"], 1)
                check_cancelled()  # Verificar cancelación

                # ========== FASE 5: ATRIBUTOS ==========
                current_phase_key = "attributes"
                phase_start_times["attributes"] = time.time()
                attr_pct_start, attr_pct_end = get_phase_progress_range("attributes")
                phases[5]["current"] = True  # Index 5 after adding classification at index 1
                deps.analysis_progress_storage[project_id]["progress"] = attr_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Analizando características de los personajes..."

                attributes = []
                if entities:
                    # Detectar si hay GPU disponible para embeddings
                    # Embeddings es muy lento en CPU pero rápido en GPU
                    try:
                        from narrative_assistant.core.device import get_device_detector
                        detector = get_device_detector()
                        has_gpu = detector.device_type.value in ("cuda", "mps")
                    except Exception:
                        has_gpu = False

                    # Habilitar embeddings solo si hay GPU
                    use_embeddings = has_gpu
                    if use_embeddings:
                        logger.info("GPU detectada - habilitando análisis de embeddings para atributos")
                        deps.analysis_progress_storage[project_id]["current_action"] = "Análisis avanzado con GPU activado"
                    else:
                        logger.info("Sin GPU - usando métodos rápidos para atributos (LLM, patrones)")

                    attr_extractor = AttributeExtractor(use_embeddings=use_embeddings)
                    entity_repo = get_entity_repository()

                    # Preparar menciones de entidades para extract_attributes
                    # Format: [(nombre, start_char, end_char)]
                    character_entities = [e for e in entities if e.entity_type.value == "character"]

                    if character_entities:
                        # Extraer atributos del texto completo
                        # El extractor encontrará atributos para todas las entidades mencionadas

                        # IMPORTANTE: Usar TODAS las menciones de cada entidad, no solo first_appearance_char
                        # Esto es crítico porque las entidades pueden fusionarse (María = María Sánchez)
                        # y necesitamos todas sus posiciones para asignar atributos correctamente
                        entity_mentions = []
                        for e in character_entities:
                            if e.id:
                                # Obtener todas las menciones de la BD
                                db_mentions = entity_repo.get_mentions_by_entity(e.id)
                                for m in db_mentions:
                                    entity_mentions.append(
                                        (e.canonical_name, m.start_char, m.end_char)
                                    )
                            # Fallback: si no hay menciones en BD, usar first_appearance_char
                            if not any(name == e.canonical_name for name, _, _ in entity_mentions):
                                entity_mentions.append(
                                    (e.canonical_name, e.first_appearance_char or 0,
                                     (e.first_appearance_char or 0) + len(e.canonical_name or ""))
                                )

                        logger.debug(f"Menciones de BD cargadas: {len(entity_mentions)} para {len(character_entities)} entidades")

                        # Añadir menciones de correferencia (pronombres) para cada entidad
                        # Esto permite detectar atributos en frases como "Mis estudios como lingüista"
                        # cuando sabemos que "Mis" se refiere a Marta (narrador)
                        if coref_result and coref_result.chains:
                            for chain in coref_result.chains:
                                # Buscar entidad que coincida con la cadena
                                matching_entity = next(
                                    (e for e in character_entities
                                     if e.canonical_name and chain.main_mention and
                                     e.canonical_name.lower() == chain.main_mention.lower()),
                                    None
                                )
                                if matching_entity:
                                    # Añadir todas las menciones de la cadena como posiciones de esta entidad
                                    for mention in chain.mentions:
                                        entity_mentions.append(
                                            (matching_entity.canonical_name, mention.start_char, mention.end_char)
                                        )

                        logger.info(f"Extrayendo atributos: {len(entity_mentions)} menciones de entidades")

                        # Procesar personajes en lotes pequeños con progreso visual
                        total_chars = len(character_entities)
                        all_extracted_attrs = []
                        batch_size = 10  # Procesar 10 personajes a la vez

                        for batch_start in range(0, total_chars, batch_size):
                            batch_end = min(batch_start + batch_size, total_chars)
                            batch_chars = character_entities[batch_start:batch_end]

                            # Mostrar qué personajes se están analizando
                            batch_names = [e.canonical_name for e in batch_chars if e.canonical_name][:3]
                            if len(batch_chars) > 3:
                                names_str = ", ".join(batch_names) + "..."
                            else:
                                names_str = ", ".join(batch_names)

                            deps.analysis_progress_storage[project_id]["current_action"] = f"Analizando: {names_str} ({batch_end}/{total_chars})"

                            # Calcular progreso (10% a 45% de la fase)
                            batch_progress = 0.1 + (0.35 * batch_end / max(total_chars, 1))
                            deps.analysis_progress_storage[project_id]["progress"] = attr_pct_start + int((attr_pct_end - attr_pct_start) * batch_progress)

                            # Obtener menciones solo de este lote
                            batch_entity_names = {e.canonical_name.lower() for e in batch_chars if e.canonical_name}
                            batch_mentions = [
                                (name, start, end) for name, start, end in entity_mentions
                                if name and name.lower() in batch_entity_names
                            ]

                            if batch_mentions:
                                try:
                                    # Usar timeout de 30 segundos por lote
                                    import concurrent.futures
                                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                        future = executor.submit(
                                            attr_extractor.extract_attributes,
                                            full_text,
                                            batch_mentions,
                                            None,  # chapter_id
                                        )
                                        try:
                                            batch_result = future.result(timeout=30)
                                            if batch_result.is_success and batch_result.value:
                                                all_extracted_attrs.extend(batch_result.value.attributes)
                                        except concurrent.futures.TimeoutError:
                                            logger.warning(f"Timeout extrayendo atributos para: {names_str}")
                                except Exception as e:
                                    logger.warning(f"Error extrayendo atributos para {names_str}: {e}")

                            check_cancelled()  # Permitir cancelación entre lotes

                        # Crear resultado combinado
                        from narrative_assistant.nlp.attributes import AttributeExtractionResult
                        attr_result = Result.success(AttributeExtractionResult(attributes=all_extracted_attrs))
                        logger.info(f"Atributos extraídos: {len(all_extracted_attrs)}")

                        # Actualizar progreso a 50% de la fase (extracción completada)
                        deps.analysis_progress_storage[project_id]["progress"] = attr_pct_start + int((attr_pct_end - attr_pct_start) * 0.5)
                        deps.analysis_progress_storage[project_id]["current_action"] = "Registrando características encontradas..."

                        if attr_result.is_success and attr_result.value:
                            # Resolver atributos con correferencias para asignar
                            # atributos de pronombres a la entidad correcta
                            # Ej: "Ella.hair_color = rubio" -> "María.hair_color = rubio"
                            extracted_attrs = attr_result.value.attributes

                            # ========== ASIGNAR CAPÍTULO A CADA ATRIBUTO ==========
                            # Esto es CRÍTICO para detectar inconsistencias entre capítulos
                            # (ej: "ojos azules" en cap 1 vs "ojos verdes" en cap 2)
                            if chapters_data:
                                def find_chapter_number_for_position(char_pos: int) -> int | None:
                                    """Encuentra el número de capítulo que contiene la posición."""
                                    for ch in chapters_data:
                                        if ch["start_char"] <= char_pos <= ch["end_char"]:
                                            return ch["chapter_number"]
                                    return None

                                attrs_with_chapter = 0
                                for attr in extracted_attrs:
                                    if attr.start_char is not None and attr.start_char > 0:
                                        chapter_num = find_chapter_number_for_position(attr.start_char)
                                        if chapter_num is not None:
                                            attr.chapter_id = chapter_num
                                            attrs_with_chapter += 1

                                logger.info(f"Asignados capítulos a {attrs_with_chapter}/{len(extracted_attrs)} atributos")

                            if coref_result and coref_result.chains:
                                try:
                                    from narrative_assistant.nlp.attributes import resolve_attributes_with_coreferences

                                    # Contar atributos con pronombres antes de resolver
                                    pronouns = {"él", "ella", "ellos", "ellas", "su", "sus", "este", "esta", "ese", "esa"}
                                    pronoun_attrs_before = sum(
                                        1 for a in extracted_attrs
                                        if a.entity_name and a.entity_name.lower() in pronouns
                                    )

                                    resolved_attrs = resolve_attributes_with_coreferences(
                                        attributes=extracted_attrs,
                                        coref_chains=coref_result.chains,
                                        text=full_text,
                                    )

                                    # Contar atributos con pronombres después de resolver
                                    pronoun_attrs_after = sum(
                                        1 for a in resolved_attrs
                                        if a.entity_name and a.entity_name.lower() in pronouns
                                    )

                                    resolved_count = pronoun_attrs_before - pronoun_attrs_after
                                    if resolved_count > 0:
                                        logger.info(
                                            f"Correferencia de atributos: {resolved_count} atributos de pronombres "
                                            f"resueltos a entidades ({pronoun_attrs_before} → {pronoun_attrs_after} sin resolver)"
                                        )
                                    elif pronoun_attrs_before > 0:
                                        logger.warning(
                                            f"Correferencia de atributos: {pronoun_attrs_before} atributos con pronombres "
                                            f"no pudieron resolverse (sin antecedente en cadenas de correferencia)"
                                        )

                                    extracted_attrs = resolved_attrs
                                except Exception as e:
                                    logger.warning(f"Error resolviendo atributos con correferencias: {e}", exc_info=True)
                            else:
                                logger.info("Sin cadenas de correferencia - atributos de pronombres no se resolverán")

                            total_attrs = len(extracted_attrs)
                            attrs_processed = 0
                            for attr in extracted_attrs:
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

                                # Actualizar progreso cada 10 atributos
                                attrs_processed += 1
                                if attrs_processed % 10 == 0 or attrs_processed == total_attrs:
                                    # Progreso de 60% a 95% durante el guardado
                                    save_progress = 0.6 + (0.35 * attrs_processed / max(total_attrs, 1))
                                    deps.analysis_progress_storage[project_id]["progress"] = attr_pct_start + int((attr_pct_end - attr_pct_start) * save_progress)
                                    deps.analysis_progress_storage[project_id]["current_action"] = f"Guardando características... ({attrs_processed}/{total_attrs})"

                phase_durations["attributes"] = time.time() - phase_start_times["attributes"]
                deps.analysis_progress_storage[project_id]["progress"] = attr_pct_end
                update_time_remaining()
                deps.analysis_progress_storage[project_id]["metrics"]["attributes_extracted"] = len(attributes)
                phases[5]["completed"] = True
                phases[5]["current"] = False
                phases[5]["duration"] = round(phase_durations["attributes"], 1)

                logger.info(f"Attribute extraction complete: {len(attributes)} attributes")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 6: CONSISTENCIA ==========
                current_phase_key = "consistency"
                phase_start_times["consistency"] = time.time()
                cons_pct_start, cons_pct_end = get_phase_progress_range("consistency")
                phases[6]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = cons_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Verificando la coherencia del relato..."

                inconsistencies = []
                if attributes:
                    checker = AttributeConsistencyChecker()
                    check_result = checker.check_consistency(attributes)
                    if check_result.is_success:
                        inconsistencies = check_result.value or []

                # ========== SUB-FASE 5.1: ESTADO VITAL ==========
                # Detecta muertes de personajes y apariciones post-mortem
                vital_status_report = None
                location_report = None
                chapter_progress_report = None

                deps.analysis_progress_storage[project_id]["current_action"] = "Verificando estado vital de personajes..."

                try:
                    from narrative_assistant.analysis.vital_status import analyze_vital_status

                    # Preparar datos en el formato esperado
                    chapters_for_analysis = [
                        {
                            "number": ch["chapter_number"],
                            "content": ch["content"],
                            "text": ch["content"],  # Alias
                            "start_char": ch["start_char"],
                        }
                        for ch in chapters_data
                    ]

                    entities_for_analysis = [
                        {
                            "id": e.id,
                            "canonical_name": e.canonical_name,
                            "entity_type": e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type),
                            "aliases": e.aliases if hasattr(e, 'aliases') else [],
                        }
                        for e in entities
                    ]

                    vital_result = analyze_vital_status(
                        project_id=project_id,
                        chapters=chapters_for_analysis,
                        entities=entities_for_analysis,
                    )

                    if vital_result.is_success:
                        vital_status_report = vital_result.value
                        logger.info(f"Vital status analysis: {len(vital_status_report.death_events)} deaths, "
                                   f"{len(vital_status_report.post_mortem_appearances)} post-mortem appearances")

                        # Añadir inconsistencias de estado vital a la lista
                        for appearance in vital_status_report.post_mortem_appearances:
                            if not appearance.is_valid:  # Solo apariciones problemáticas
                                # Se agregarán alertas en FASE 7
                                pass
                    else:
                        logger.warning(f"Vital status analysis failed: {vital_result.error}")

                except ImportError as e:
                    logger.warning(f"Vital status module not available: {e}")
                except Exception as e:
                    logger.warning(f"Error in vital status analysis: {e}", exc_info=True)

                check_cancelled()

                # ========== SUB-FASE 5.2: UBICACIONES DE PERSONAJES ==========
                # Detecta inconsistencias de ubicación (personaje en dos lugares)
                deps.analysis_progress_storage[project_id]["current_action"] = "Verificando ubicaciones de personajes..."

                try:
                    from narrative_assistant.analysis.character_location import analyze_character_locations

                    location_result = analyze_character_locations(
                        project_id=project_id,
                        chapters=chapters_for_analysis,
                        entities=entities_for_analysis,
                    )

                    if location_result.is_success:
                        location_report = location_result.value
                        inconsistency_count = len(location_report.inconsistencies) if hasattr(location_report, 'inconsistencies') else 0
                        logger.info(f"Character location analysis: {len(location_report.location_events)} events, "
                                   f"{inconsistency_count} inconsistencies")
                    else:
                        logger.warning(f"Character location analysis failed: {location_result.error}")

                except ImportError as e:
                    logger.warning(f"Character location module not available: {e}")
                except Exception as e:
                    logger.warning(f"Error in character location analysis: {e}", exc_info=True)

                check_cancelled()

                # ========== SUB-FASE 5.3: RESUMEN POR CAPÍTULO ==========
                # Genera resumen de avance narrativo (usa modo básico para no bloquear)
                deps.analysis_progress_storage[project_id]["current_action"] = "Generando resumen de avance narrativo..."

                try:
                    from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress

                    chapter_progress_report = analyze_chapter_progress(
                        project_id=project_id,
                        db_path=None,  # Usa la BD por defecto
                        mode="basic",  # Modo rápido sin LLM para no bloquear
                    )

                    if chapter_progress_report:
                        logger.info(f"Chapter progress analysis: {len(chapter_progress_report.chapters)} chapters analyzed")

                except ImportError as e:
                    logger.warning(f"Chapter summary module not available: {e}")
                except Exception as e:
                    logger.warning(f"Error in chapter progress analysis: {e}", exc_info=True)

                check_cancelled()

                # Guardar métricas de análisis adicionales
                deps.analysis_progress_storage[project_id]["metrics"]["vital_status_deaths"] = (
                    len(vital_status_report.death_events) if vital_status_report else 0
                )
                deps.analysis_progress_storage[project_id]["metrics"]["location_events"] = (
                    len(location_report.location_events) if location_report else 0
                )

                phase_durations["consistency"] = time.time() - phase_start_times["consistency"]
                deps.analysis_progress_storage[project_id]["progress"] = cons_pct_end
                update_time_remaining()
                deps.analysis_progress_storage[project_id]["metrics"]["inconsistencies_found"] = len(inconsistencies)
                phases[6]["completed"] = True
                phases[6]["current"] = False
                phases[6]["duration"] = round(phase_durations["consistency"], 1)

                logger.info(f"Consistency analysis complete: {len(inconsistencies)} inconsistencies")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 7: ANÁLISIS GRAMATICAL ==========
                current_phase_key = "grammar"
                phase_start_times["grammar"] = time.time()
                grammar_pct_start, grammar_pct_end = get_phase_progress_range("grammar")
                phases[7]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = grammar_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Revisando la redacción..."

                grammar_issues = []
                spelling_issues = []
                try:
                    from narrative_assistant.nlp.grammar import (
                        get_grammar_checker,
                        ensure_languagetool_running,
                        is_languagetool_installed,
                    )

                    # Intentar iniciar LanguageTool si está instalado
                    if is_languagetool_installed():
                        lt_started = ensure_languagetool_running()
                        if lt_started:
                            logger.info("LanguageTool server started successfully")

                    grammar_checker = get_grammar_checker()

                    # Refrescar disponibilidad de LT por si acaba de iniciarse
                    if not grammar_checker.languagetool_available:
                        grammar_checker.reload_languagetool()
                        if grammar_checker.languagetool_available:
                            logger.info("LanguageTool now available after reload")

                    grammar_result = grammar_checker.check(full_text)

                    if grammar_result.is_success:
                        grammar_report = grammar_result.value
                        grammar_issues = grammar_report.issues
                        logger.info(f"Grammar check found {len(grammar_issues)} issues")
                    else:
                        logger.warning(f"Grammar check failed: {grammar_result.error}")

                except ImportError as e:
                    logger.warning(f"Grammar module not available: {e}")
                except Exception as e:
                    logger.warning(f"Error in grammar analysis: {e}")

                # --- ANÁLISIS DE CORRECCIONES EDITORIALES ---
                # Tipografía, repeticiones, concordancia
                correction_issues = []
                try:
                    deps.analysis_progress_storage[project_id]["current_phase"] = "Buscando repeticiones y errores tipográficos..."

                    from narrative_assistant.corrections import CorrectionConfig
                    from narrative_assistant.corrections.orchestrator import CorrectionOrchestrator

                    # Usar configuración por defecto (configurable en futuro)
                    correction_config = CorrectionConfig.default()
                    orchestrator = CorrectionOrchestrator(config=correction_config)

                    # Analizar el texto completo
                    # Nota: spacy_doc puede pasarse para mejorar detección
                    correction_issues = orchestrator.analyze(
                        text=full_text,
                        chapter_index=None,
                        spacy_doc=None,  # TODO: pasar doc de spaCy si está disponible
                    )

                    logger.info(f"Corrections analysis found {len(correction_issues)} suggestions")

                except ImportError as e:
                    logger.warning(f"Corrections module not available: {e}")
                except Exception as e:
                    logger.warning(f"Error in corrections analysis: {e}")

                phase_durations["grammar"] = time.time() - phase_start_times["grammar"]
                deps.analysis_progress_storage[project_id]["progress"] = grammar_pct_end
                deps.analysis_progress_storage[project_id]["metrics"]["grammar_issues_found"] = len(grammar_issues)
                deps.analysis_progress_storage[project_id]["metrics"]["correction_suggestions"] = len(correction_issues)
                phases[7]["completed"] = True
                phases[7]["current"] = False
                phases[7]["duration"] = round(phase_durations["grammar"], 1)
                update_time_remaining()

                logger.info(f"Grammar analysis complete: {len(grammar_issues)} grammar issues, {len(correction_issues)} correction suggestions")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 8: ALERTAS ==========
                current_phase_key = "alerts"
                phase_start_times["alerts"] = time.time()
                alerts_pct_start, alerts_pct_end = get_phase_progress_range("alerts")
                phases[8]["current"] = True
                deps.analysis_progress_storage[project_id]["progress"] = alerts_pct_start
                deps.analysis_progress_storage[project_id]["current_phase"] = "Preparando observaciones y sugerencias..."

                alerts_created = 0
                alert_engine = get_alert_engine()

                # Alertas de inconsistencias de atributos
                if inconsistencies:
                    for inc in inconsistencies:
                        try:
                            alert_result = alert_engine.create_from_attribute_inconsistency(
                                project_id=project_id,
                                entity_name=inc.entity_name,
                                entity_id=inc.entity_id,
                                attribute_key=inc.attribute_key.value if hasattr(inc.attribute_key, 'value') else str(inc.attribute_key),
                                value1=inc.value1,
                                value2=inc.value2,
                                value1_source={
                                    "chapter": inc.value1_chapter,
                                    "excerpt": inc.value1_excerpt,
                                    "start_char": inc.value1_position,
                                },
                                value2_source={
                                    "chapter": inc.value2_chapter,
                                    "excerpt": inc.value2_excerpt,
                                    "start_char": inc.value2_position,
                                },
                                explanation=inc.explanation,
                                confidence=inc.confidence,
                            )
                            if alert_result.is_success:
                                alerts_created += 1
                        except Exception as e:
                            logger.warning(f"Error creating attribute inconsistency alert: {e}")

                # Alertas de errores gramaticales
                if grammar_issues:
                    for issue in grammar_issues:
                        try:
                            alert_result = alert_engine.create_from_grammar_issue(
                                project_id=project_id,
                                text=issue.text,
                                start_char=issue.start_char,
                                end_char=issue.end_char,
                                sentence=issue.sentence,
                                error_type=issue.error_type.value if hasattr(issue.error_type, 'value') else str(issue.error_type),
                                suggestion=issue.suggestion,
                                confidence=issue.confidence,
                                explanation=issue.explanation,
                                rule_id=issue.rule_id if hasattr(issue, 'rule_id') else "",
                            )
                            if alert_result.is_success:
                                alerts_created += 1
                        except Exception as e:
                            logger.warning(f"Error creating grammar alert: {e}")

                # Alertas de correcciones editoriales (tipografía, repeticiones, concordancia)
                if correction_issues:
                    for issue in correction_issues:
                        try:
                            alert_result = alert_engine.create_from_correction_issue(
                                project_id=project_id,
                                category=issue.category,
                                issue_type=issue.issue_type,
                                text=issue.text,
                                start_char=issue.start_char,
                                end_char=issue.end_char,
                                explanation=issue.explanation,
                                suggestion=issue.suggestion,
                                confidence=issue.confidence,
                                context=issue.context,
                                chapter=issue.chapter_index,
                                rule_id=issue.rule_id or "",
                                extra_data=issue.extra_data,
                            )
                            if alert_result.is_success:
                                alerts_created += 1
                        except Exception as e:
                            logger.warning(f"Error creating correction alert: {e}")

                # Alertas de estado vital (personajes fallecidos que reaparecen)
                if vital_status_report and hasattr(vital_status_report, 'post_mortem_appearances'):
                    for appearance in vital_status_report.post_mortem_appearances:
                        if appearance.is_valid:
                            continue  # Ignorar apariciones válidas (flashbacks, recuerdos)
                        try:
                            alert_result = alert_engine.create_from_deceased_reappearance(
                                project_id=project_id,
                                entity_id=appearance.entity_id,
                                entity_name=appearance.entity_name,
                                death_chapter=appearance.death_chapter,
                                appearance_chapter=appearance.appearance_chapter,
                                appearance_start_char=appearance.appearance_start_char,
                                appearance_end_char=appearance.appearance_end_char,
                                appearance_excerpt=appearance.appearance_excerpt,
                                appearance_type=appearance.appearance_type,
                                confidence=appearance.confidence,
                            )
                            if alert_result.is_success:
                                alerts_created += 1
                        except Exception as e:
                            logger.warning(f"Error creating deceased reappearance alert: {e}")

                # Alertas de inconsistencias de ubicación
                if location_report and hasattr(location_report, 'inconsistencies'):
                    for loc_inc in location_report.inconsistencies:
                        try:
                            # Usar create_alert genérico para ubicaciones
                            from narrative_assistant.alerts.engine import AlertCategory, AlertSeverity
                            alert_result = alert_engine.create_alert(
                                project_id=project_id,
                                category=AlertCategory.CONSISTENCY,
                                severity=AlertSeverity.WARNING,
                                alert_type="location_inconsistency",
                                title=f"Inconsistencia de ubicación: {loc_inc.entity_name}",
                                description=(
                                    f"{loc_inc.entity_name} aparece en {loc_inc.location1_name} (cap {loc_inc.location1_chapter}) "
                                    f"y en {loc_inc.location2_name} (cap {loc_inc.location2_chapter})"
                                ),
                                explanation=loc_inc.explanation,
                                confidence=loc_inc.confidence,
                            )
                            if alert_result.is_success:
                                alerts_created += 1
                        except Exception as e:
                            logger.warning(f"Error creating location inconsistency alert: {e}")

                phase_durations["alerts"] = time.time() - phase_start_times["alerts"]
                deps.analysis_progress_storage[project_id]["progress"] = 100
                deps.analysis_progress_storage[project_id]["metrics"]["alerts_generated"] = alerts_created
                phases[8]["completed"] = True
                phases[8]["current"] = False
                phases[8]["duration"] = round(phase_durations["alerts"], 1)

                # ========== RECONCILIACIÓN FINAL DE CONTADORES ==========
                # Sincronizar mention_count de todas las entidades con las filas reales
                # en entity_mentions. Esto es crítico porque:
                # 1. NER crea menciones pero no actualiza mention_count
                # 2. MentionFinder crea menciones adicionales
                # 3. Las reconciliaciones anteriores pueden haberse saltado por excepciones
                try:
                    entity_repo = get_entity_repository()
                    reconciled_count = entity_repo.reconcile_all_mention_counts(project_id)
                    logger.info(f"Reconciliación final: {reconciled_count} entidades sincronizadas")
                except Exception as recon_err:
                    logger.warning(f"Error en reconciliación final de mention_count: {recon_err}")

                # ========== COMPLETADO ==========
                deps.analysis_progress_storage[project_id]["status"] = "completed"
                deps.analysis_progress_storage[project_id]["current_phase"] = "Análisis completado"
                deps.analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 0

                total_duration = round(time.time() - start_time, 1)
                deps.analysis_progress_storage[project_id]["metrics"]["total_duration_seconds"] = total_duration

                # Preparar stats para el frontend (UI-friendly names)
                metrics = deps.analysis_progress_storage[project_id]["metrics"]
                deps.analysis_progress_storage[project_id]["stats"] = {
                    "entities": metrics.get("entities_found", len(entities)),
                    "alerts": metrics.get("alerts_generated", alerts_created),
                    "chapters": metrics.get("chapters_found", chapters_count),
                    "corrections": metrics.get("correction_suggestions", 0),
                    "grammar": metrics.get("grammar_issues_found", 0),
                    "attributes": metrics.get("attributes_extracted", len(attributes)),
                    "words": metrics.get("word_count", word_count),
                    "duration": total_duration,
                }

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
                deps.analysis_progress_storage[project_id]["status"] = "error"

                # Mensaje de error amigable según el tipo de excepción
                err_str = str(e)
                from narrative_assistant.core.errors import ModelNotLoadedError
                if isinstance(e, ModelNotLoadedError) or "not loaded" in err_str.lower() or "not found" in err_str.lower():
                    user_msg = (
                        "Modelo de análisis no disponible. "
                        "Reinicia la aplicación para que se descarguen los modelos necesarios."
                    )
                else:
                    user_msg = f"Error en el análisis: {err_str}"
                deps.analysis_progress_storage[project_id]["current_phase"] = user_msg
                deps.analysis_progress_storage[project_id]["error"] = user_msg

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

                # Limpiar progreso después de un delay para que el frontend lea el estado final
                def _cleanup_progress(pid: int):
                    deps.analysis_progress_storage.pop(pid, None)

                cleanup_timer = threading.Timer(300, _cleanup_progress, args=[project_id])
                cleanup_timer.daemon = True
                cleanup_timer.start()

        def _persist_chapters_to_db(chapters_data: list, proj_id: int, db):
            """Persiste los capítulos y secciones en la base de datos."""
            try:
                # Usar transacción para asegurar atomicidad
                with db.transaction() as conn:
                    # Primero eliminar secciones existentes (antes de capítulos por FK)
                    conn.execute("DELETE FROM sections WHERE project_id = ?", (proj_id,))
                    # Eliminar capítulos existentes
                    conn.execute("DELETE FROM chapters WHERE project_id = ?", (proj_id,))

                    total_sections = 0
                    for ch in chapters_data:
                        # Insertar capítulo
                        cursor = conn.execute(
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
                        chapter_id = cursor.lastrowid

                        # Insertar secciones de este capítulo
                        sections = ch.get("sections", [])
                        if sections:
                            sections_created = _persist_sections_recursive(
                                conn, sections, proj_id, chapter_id, None
                            )
                            total_sections += sections_created

                logger.info(f"Persisted {len(chapters_data)} chapters and {total_sections} sections to database")
            except Exception as e:
                logger.error(f"Error persisting chapters: {e}", exc_info=True)

        def _persist_sections_recursive(conn, sections: list, proj_id: int, chapter_id: int, parent_id: int | None) -> int:
            """Persiste secciones recursivamente con sus subsecciones."""
            count = 0
            for idx, s in enumerate(sections):
                cursor = conn.execute(
                    """
                    INSERT INTO sections (
                        project_id, chapter_id, parent_section_id, section_number,
                        title, heading_level, start_char, end_char
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        proj_id,
                        chapter_id,
                        parent_id,
                        s.get("number", idx + 1),
                        s.get("title"),
                        s.get("heading_level", 2),
                        s.get("start_char", 0),
                        s.get("end_char", 0)
                    )
                )
                section_id = cursor.lastrowid
                count += 1

                # Recursivamente insertar subsecciones
                subsections = s.get("subsections", [])
                if subsections:
                    count += _persist_sections_recursive(conn, subsections, proj_id, chapter_id, section_id)

            return count

        # Pre-check: verificar que los modelos críticos están disponibles
        # antes de lanzar el thread, para dar un error claro al usuario
        try:
            from narrative_assistant.core.model_manager import ModelType, get_model_manager
            mm = get_model_manager()
            missing_models = []
            model_labels = {
                ModelType.SPACY: "Análisis lingüístico (spaCy)",
                ModelType.EMBEDDINGS: "Similitud semántica (embeddings)",
                ModelType.TRANSFORMER_NER: "Reconocimiento de entidades (NER)",
            }
            for mt, label in model_labels.items():
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
                          "Reinicia la aplicación para que se descarguen automáticamente."
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
            data={"project_id": project_id, "status": "running"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


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
                        "phases": []
                    }
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
                            deps.analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 45
                            deps.analysis_progress_storage[project_id]["_last_progress_update"] = now
                            progress["estimated_seconds_remaining"] = 45

        return ApiResponse(success=True, data=progress)

    except Exception as e:
        logger.error(f"Error getting analysis progress for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


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
            if project_id not in deps.analysis_progress_storage:
                return ApiResponse(
                    success=False,
                    error="No hay análisis en curso para este proyecto"
                )

            current_status = deps.analysis_progress_storage[project_id].get("status")
            if current_status in ("completed", "error", "cancelled"):
                return ApiResponse(
                    success=False,
                    error=f"El análisis ya ha terminado con estado: {current_status}"
                )

            # Marcar como cancelado
            deps.analysis_progress_storage[project_id]["status"] = "cancelled"
            deps.analysis_progress_storage[project_id]["current_phase"] = "Análisis cancelado por el usuario"

        logger.info(f"Analysis cancelled for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "status": "cancelled",
                "message": "Análisis cancelado exitosamente"
            }
        )

    except Exception as e:
        logger.error(f"Error cancelling analysis for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


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
        max_wait_time = 600  # 10 minutos máximo

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
                    progress_data = deps.analysis_progress_storage[project_id].copy() if has_progress else None

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
                        "estimated_seconds_remaining": progress_data.get("estimated_seconds_remaining"),
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


