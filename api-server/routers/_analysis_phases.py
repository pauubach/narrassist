"""
Funciones de fase extraídas de run_real_analysis().

Cada función recibe un contexto compartido (dict) y un ProgressTracker.
Las fases mutan el contexto añadiendo resultados que fases posteriores necesitan.

S8a-14: Refactor monolito → funciones standalone.
"""

import json
import threading
import time
from collections import Counter
from typing import Any

import deps
from deps import generate_person_aliases, logger


class AnalysisCancelledError(Exception):
    """Excepción tipada para cancelación de análisis por el usuario."""

    pass


# ============================================================================
# Cache Serialization/Deserialization Helpers (v0.10.15)
# ============================================================================


def _serialize_entities_for_cache(entities: list, entity_repo) -> str:
    """
    Serializa entidades + menciones a JSON para cache.

    Args:
        entities: Lista de Entity objects
        entity_repo: Repositorio de entidades para obtener menciones

    Returns:
        JSON string con [{entity_data, mentions: [...]}]
    """
    cache_data = []

    for entity in entities:
        # Obtener menciones de DB
        mentions = entity_repo.get_mentions_for_entity(entity.id)

        entity_dict = {
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
            "aliases": entity.aliases if entity.aliases else [],
            "importance": entity.importance.value if hasattr(entity.importance, "value") else str(entity.importance),
            "first_appearance_char": entity.first_appearance_char,
            "mention_count": entity.mention_count,
            "mentions": [
                {
                    "surface_form": m.surface_form,
                    "start_char": m.start_char,
                    "end_char": m.end_char,
                    "chapter_id": m.chapter_id,
                    "confidence": m.confidence,
                    "source": m.source,
                }
                for m in mentions
            ],
        }

        cache_data.append(entity_dict)

    return json.dumps(cache_data, ensure_ascii=False)


def _restore_entities_from_cache(
    entities_json: str,
    project_id: int,
    find_chapter_id_for_position,
) -> list:
    """
    Restaura entidades + menciones desde JSON de cache.

    Args:
        entities_json: JSON string de entidades serializadas
        project_id: ID del proyecto
        find_chapter_id_for_position: Función para mapear char → chapter_id

    Returns:
        Lista de Entity objects con menciones creadas en DB
    """
    from narrative_assistant.entities.models import (
        Entity,
        EntityImportance,
        EntityMention,
        EntityType,
    )
    from narrative_assistant.entities.repository import get_entity_repository

    cache_data = json.loads(entities_json)
    entity_repo = get_entity_repository()
    entities = []

    for entity_dict in cache_data:
        # Restaurar entity
        entity_type_str = entity_dict["entity_type"]
        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            entity_type = EntityType.CONCEPT  # Fallback

        importance_str = entity_dict["importance"]
        try:
            importance = EntityImportance(importance_str)
        except ValueError:
            importance = EntityImportance.MINIMAL

        entity = Entity(
            id=None,  # Will be assigned by DB
            project_id=project_id,
            canonical_name=entity_dict["canonical_name"],
            entity_type=entity_type,
            aliases=entity_dict.get("aliases", []),
            importance=importance,
            first_appearance_char=entity_dict.get("first_appearance_char", 0),
            mention_count=entity_dict.get("mention_count", 0),
            description=None,
            merged_from_ids=[],
            is_active=True,
        )

        # Crear en DB
        entity_id = entity_repo.create_entity(entity)
        entity.id = entity_id

        # Restaurar menciones
        mentions_to_create = []
        for mention_dict in entity_dict.get("mentions", []):
            mention = EntityMention(
                entity_id=entity_id,
                surface_form=mention_dict["surface_form"],
                start_char=mention_dict["start_char"],
                end_char=mention_dict["end_char"],
                chapter_id=mention_dict.get("chapter_id"),
                confidence=mention_dict.get("confidence", 0.9),
                source=mention_dict.get("source", "cache"),
            )
            mentions_to_create.append(mention)

        if mentions_to_create:
            entity_repo.create_mentions_batch(mentions_to_create)

        entities.append(entity)

    return entities


# ============================================================================
# Thread-safe progress helper (F-006)
# ============================================================================


def _ensure_storage_exists(project_id: int) -> None:
    """
    Asegura que existe progress storage para el proyecto.

    Si no existe (por reinicio de servidor o limpieza), lo crea con valores por defecto.
    Esto previene que las fases heavy pierdan feedback visual.
    """
    import time

    with deps._progress_lock:
        if project_id in deps.analysis_progress_storage:
            return  # Ya existe

        # Crear storage mínimo para fases heavy
        deps.analysis_progress_storage[project_id] = {
            "project_id": project_id,
            "status": "running",
            "progress": 0,
            "current_phase": "Procesando análisis profundo...",
            "current_action": "",
            "last_update": time.time(),
            "phases": [],
            "metrics": {},
        }
        logger.info(f"[STORAGE] Created missing progress storage for project {project_id}")


def _update_storage(
    project_id: int, *, metrics_update: dict[str, Any] | None = None, **updates
) -> None:
    """Thread-safe update de progress storage para código sin tracker."""
    import time

    with deps._progress_lock:
        storage = deps.analysis_progress_storage.get(project_id)
        if not storage:
            return
        if metrics_update:
            storage.setdefault("metrics", {}).update(metrics_update)
        if updates:
            storage.update(updates)
        # Actualizar timestamp para detección de análisis bloqueado
        storage["last_update"] = time.time()


# ============================================================================
# ProgressTracker: encapsula toda la lógica de progreso
# ============================================================================


class ProgressTracker:
    """Encapsula la lógica de progreso, time-estimation y cancelación.

    Todas las escrituras a analysis_progress_storage pasan por _write()
    que adquiere deps._progress_lock para thread-safety (F-006).
    """

    def __init__(
        self,
        project_id: int,
        phases: list[dict],
        phase_weights: dict[str, float],
        phase_order: list[str],
        db_session: Any,
    ):
        self.project_id = project_id
        self.phases = phases
        self.phase_weights = phase_weights
        self.phase_order = phase_order
        self.db_session = db_session
        self.current_phase_key = "parsing"
        self.phase_start_times: dict[str, float] = {}
        self.phase_durations: dict[str, float] = {}

    def _write(self, **updates):
        """Thread-safe update de progress storage (F-006)."""
        with deps._progress_lock:
            storage = deps.analysis_progress_storage.get(self.project_id)
            if storage:
                for key, value in updates.items():
                    if key == "metrics_update" and isinstance(value, dict):
                        storage.setdefault("metrics", {}).update(value)
                    else:
                        storage[key] = value

    def get_phase_progress_range(self, phase_id: str) -> tuple[int, int]:
        """Calcula el rango de progreso (inicio, fin) para una fase basado en pesos."""
        cumulative = 0.0
        for pid in self.phase_order:
            weight = self.phase_weights.get(pid, 0.05)
            if pid == phase_id:
                start_pct = int(cumulative * 100)
                end_pct = int((cumulative + weight) * 100)
                return (start_pct, end_pct)
            cumulative += weight
        return (0, 100)

    def start_phase(self, phase_key: str, phase_index: int, message: str):
        """Marca el inicio de una fase."""
        self.current_phase_key = phase_key
        self.phase_start_times[phase_key] = time.time()
        pct_start, _ = self.get_phase_progress_range(phase_key)
        self.phases[phase_index]["current"] = True
        self._write(progress=pct_start, current_phase=message)

    def end_phase(self, phase_key: str, phase_index: int):
        """Marca el fin de una fase."""
        _, pct_end = self.get_phase_progress_range(phase_key)
        self.phase_durations[phase_key] = time.time() - self.phase_start_times[phase_key]
        self._write(progress=pct_end)
        self.phases[phase_index]["completed"] = True
        self.phases[phase_index]["current"] = False
        self.phases[phase_index]["duration"] = round(self.phase_durations[phase_key], 1)
        self.check_cancelled()
        self.update_time_remaining()
        self.persist_progress()

    def update_progress(self, phase_key: str, fraction: float, message: str):
        """Update progress within a phase (fraction 0.0 to 1.0)."""
        pct_start, pct_end = self.get_phase_progress_range(phase_key)
        pct = int(pct_start + (pct_end - pct_start) * fraction)
        self._write(progress=pct, current_action=message)

    def complete_phase(self, phase_key: str, phase_index: int):
        """Alias for end_phase."""
        self.end_phase(phase_key, phase_index)

    def _resolve_index(self, phase_key: str) -> int:
        """Resolve phase index from phase_order (for partial analysis)."""
        try:
            return self.phase_order.index(phase_key)
        except ValueError:
            return 0

    def start_phase_by_key(self, phase_key: str, message: str):
        """Start a phase resolving index from phase_order (partial analysis)."""
        self.start_phase(phase_key, self._resolve_index(phase_key), message)

    def end_phase_by_key(self, phase_key: str):
        """End a phase resolving index from phase_order (partial analysis)."""
        self.end_phase(phase_key, self._resolve_index(phase_key))

    def complete_phase_by_key(self, phase_key: str):
        """Alias for end_phase_by_key."""
        self.end_phase_by_key(phase_key)

    def set_progress(self, pct: int):
        """Establece el porcentaje de progreso."""
        self._write(progress=pct)

    def set_message(self, message: str):
        """Establece el mensaje de fase actual."""
        self._write(current_phase=message)

    def set_action(self, action: str):
        """Establece la acción actual (sub-tarea)."""
        self._write(current_action=action)

    def set_metric(self, key: str, value: Any):
        """Establece una métrica en el storage."""
        self._write(metrics_update={key: value})

    def set_status(self, status: str, **extra):
        """Establece el status (thread-safe, para transiciones críticas)."""
        self._write(status=status, **extra)

    def mark_phase_completed(self, phase_key: str):
        """Marca una sub-fase virtual como completada (para alertas incrementales).

        Añade la fase al array de fases si no existe, o la marca como completed.
        El frontend usa esto para desbloquear tabs progresivamente.
        """
        with deps._progress_lock:
            storage = deps.analysis_progress_storage.get(self.project_id)
            if not storage:
                return
            phases_list = storage.get("phases", [])
            existing = next((p for p in phases_list if p.get("id") == phase_key), None)
            if existing:
                existing["completed"] = True
                existing["current"] = False
            else:
                phases_list.append({
                    "id": phase_key,
                    "name": phase_key,
                    "completed": True,
                    "current": False,
                })

    def update_time_remaining(self):
        """Calcula tiempo restante usando tiempos reales de fases completadas."""
        now = time.time()

        # Calcular tiempo transcurrido en la fase actual
        phase_elapsed = 0
        if self.current_phase_key in self.phase_start_times:
            phase_elapsed = now - self.phase_start_times[self.current_phase_key]

        # Calcular peso completado y tiempo total de fases completadas
        completed_weight = 0.0
        completed_time = 0.0
        pending_weight = 0.0
        current_weight = self.phase_weights.get(self.current_phase_key, 0.05)
        found_current = False
        min_time_remaining = 0

        for phase_id in self.phase_order:
            w = self.phase_weights.get(phase_id, 0.05)
            if phase_id == self.current_phase_key:
                found_current = True
                continue
            if not found_current:
                # Ya completada
                if phase_id in self.phase_durations:
                    completed_weight += w
                    completed_time += self.phase_durations[phase_id]
            else:
                # Pendiente
                pending_weight += w
                base_times = {
                    "parsing": 2,
                    "structure": 2,
                    "ner": 30,
                    "fusion": 10,
                    "attributes": 15,
                    "consistency": 3,
                    "grammar": 5,
                    "alerts": 3,
                    "relationships": 8,
                    "voice": 10,
                    "prose": 10,
                    "health": 8,
                }
                min_time_remaining += base_times.get(phase_id, 5)

        remaining_weight = current_weight + pending_weight

        # Estimar tiempo restante
        use_measured_speed = completed_weight > 0.10 and completed_time > 5.0

        if use_measured_speed:
            speed = completed_time / completed_weight
            if phase_elapsed > 0:
                estimated_phase_total = speed * current_weight
                phase_remaining = max(0, estimated_phase_total - phase_elapsed)
            else:
                phase_remaining = speed * current_weight
            future_time = speed * pending_weight
            total_remaining = int(phase_remaining + future_time)
        else:
            with deps._progress_lock:
                word_count = (
                    deps.analysis_progress_storage.get(self.project_id, {})
                    .get("metrics", {})
                    .get("word_count", 500)
                )
            base_estimate = 60 + int(word_count * 0.2)
            total_remaining = int(base_estimate * remaining_weight)

        self._write(
            estimated_seconds_remaining=max(min_time_remaining, total_remaining),
            _last_progress_update=time.time(),
        )
        self.persist_progress()

    def check_cancelled(self):
        """Verifica si el análisis fue cancelado por el usuario."""
        with deps._progress_lock:
            # Check dedicated cancellation flag (primary) or status (fallback)
            cancelled = (
                deps.analysis_cancellation_flags.get(self.project_id, False)
                or deps.analysis_progress_storage.get(self.project_id, {}).get("status") == "cancelled"
            )
        if cancelled:
            raise AnalysisCancelledError("Análisis cancelado por el usuario")

    def persist_progress(self):
        """Persiste el progreso actual en la BD."""
        try:
            with deps._progress_lock:
                pct = deps.analysis_progress_storage.get(self.project_id, {}).get("progress", 0)
            normalized = round(pct / 100.0, 2)
            with self.db_session.connection() as conn:
                conn.execute(
                    "UPDATE projects SET analysis_progress = ? WHERE id = ?",
                    (normalized, self.project_id),
                )
        except Exception as e:
            logger.debug(f"Could not persist progress: {e}")


# ============================================================================
# Database helpers (moved from analysis.py to avoid circular import)
# ============================================================================


def persist_chapters_to_db(chapters_data: list, project_id: int, db):
    """Persiste los capítulos y secciones en la base de datos."""
    try:
        with db.transaction() as conn:
            conn.execute("DELETE FROM sections WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM chapters WHERE project_id = ?", (project_id,))

            total_sections = 0
            for ch in chapters_data:
                cursor = conn.execute(
                    """
                    INSERT INTO chapters (
                        project_id, chapter_number, title, content,
                        start_char, end_char, word_count, structure_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        ch["chapter_number"],
                        ch["title"],
                        ch["content"],
                        ch["start_char"],
                        ch["end_char"],
                        ch["word_count"],
                        ch["structure_type"],
                    ),
                )
                chapter_id = cursor.lastrowid

                sections = ch.get("sections", [])
                if sections:
                    sections_created = _persist_sections_recursive(
                        conn, sections, project_id, chapter_id, None
                    )
                    total_sections += sections_created

        logger.info(
            f"Persisted {len(chapters_data)} chapters and {total_sections} sections to database"
        )
    except Exception as e:
        logger.error(f"Error persisting chapters: {e}", exc_info=True)
        raise  # S7c-05: Don't silently swallow — chapters are needed for NER


def _persist_sections_recursive(
    conn, sections: list, project_id: int, chapter_id: int, parent_id: int | None
) -> int:
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
                project_id,
                chapter_id,
                parent_id,
                s.get("number", idx + 1),
                s.get("title"),
                s.get("heading_level", 2),
                s.get("start_char", 0),
                s.get("end_char", 0),
            ),
        )
        section_id = cursor.lastrowid
        count += 1

        subsections = s.get("subsections", [])
        if subsections:
            count += _persist_sections_recursive(
                conn, subsections, project_id, chapter_id, section_id
            )

    return count


# ============================================================================
# Pre-analysis steps
# ============================================================================


def run_snapshot(ctx: dict, tracker: ProgressTracker):
    """Captura snapshot pre-reanálisis (BK-05)."""
    try:
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        snapshot_repo = SnapshotRepository()
        snapshot_repo.create_snapshot(ctx["project_id"])
        snapshot_repo.cleanup_old_snapshots(ctx["project_id"])
        logger.info(f"Pre-reanalysis snapshot created for project {ctx['project_id']}")
    except Exception as snap_err:
        logger.warning(f"Snapshot creation failed (continuing): {snap_err}")


def run_cleanup(ctx: dict, tracker: ProgressTracker):
    """Limpia datos existentes antes de re-analizar."""
    project_id = ctx["project_id"]
    db_session = ctx["db_session"]
    logger.info(f"Clearing existing data for project {project_id}")
    try:
        with db_session.connection() as conn:
            # Borrar alertas existentes
            conn.execute("DELETE FROM alerts WHERE project_id = ?", (project_id,))
            # Borrar historial de revisión
            # SP-1: Preservar entity_merged en review_history (instrucciones de merge del usuario)
            conn.execute(
                "DELETE FROM review_history WHERE project_id = ? AND action_type != 'entity_merged'",
                (project_id,),
            )
            # SP-1: Guardar atributos verificados antes de borrar
            verified_attrs = conn.execute(
                "SELECT e.canonical_name, ea.attribute_key, ea.attribute_value, "
                "ea.attribute_type, ea.confidence "
                "FROM entity_attributes ea "
                "JOIN entities e ON ea.entity_id = e.id "
                "WHERE e.project_id = ? AND ea.is_verified = 1",
                (project_id,),
            ).fetchall()
            if verified_attrs:
                ctx["_sp1_verified_attrs"] = [
                    {
                        "entity_name": r["canonical_name"],
                        "attribute_key": r["attribute_key"],
                        "attribute_value": r["attribute_value"],
                        "attribute_type": r["attribute_type"],
                        "confidence": r["confidence"],
                    }
                    for r in verified_attrs
                ]
                logger.info(
                    f"SP-1: Saved {len(verified_attrs)} verified attributes for restoration"
                )

            # Borrar atributos y evidencias
            conn.execute(
                "DELETE FROM attribute_evidences WHERE attribute_id IN "
                "(SELECT id FROM entity_attributes WHERE entity_id IN "
                "(SELECT id FROM entities WHERE project_id = ?))",
                (project_id,),
            )
            conn.execute(
                "DELETE FROM entity_attributes WHERE entity_id IN "
                "(SELECT id FROM entities WHERE project_id = ?)",
                (project_id,),
            )
            # Borrar menciones
            conn.execute(
                "DELETE FROM entity_mentions WHERE entity_id IN "
                "(SELECT id FROM entities WHERE project_id = ?)",
                (project_id,),
            )
            # Borrar entidades
            conn.execute("DELETE FROM entities WHERE project_id = ?", (project_id,))
            # Borrar relaciones y interacciones
            conn.execute("DELETE FROM interactions WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM relationships WHERE project_id = ?", (project_id,))
            # Borrar timeline
            conn.execute("DELETE FROM timeline_events WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM temporal_markers WHERE project_id = ?", (project_id,))
            # Borrar escenas
            conn.execute(
                "DELETE FROM scene_tags WHERE scene_id IN (SELECT id FROM scenes WHERE project_id = ?)",
                (project_id,),
            )
            conn.execute("DELETE FROM scenes WHERE project_id = ?", (project_id,))
            # Borrar datos de voz y pacing
            conn.execute("DELETE FROM register_changes WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM pacing_metrics WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM emotional_arcs WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM voice_profiles WHERE project_id = ?", (project_id,))
            # Borrar vital status events (S8a-03)
            conn.execute("DELETE FROM vital_status_events WHERE project_id = ?", (project_id,))
            # Borrar character location events (S8a-04)
            conn.execute(
                "DELETE FROM character_location_events WHERE project_id = ?", (project_id,)
            )
            # Borrar OOC events (S8a-05)
            conn.execute("DELETE FROM ooc_events WHERE project_id = ?", (project_id,))
            # SP-1: Preservar trabajo editorial del usuario entre re-análisis:
            # - focalization_declarations: declaraciones manuales de POV
            # - coreference_corrections: correcciones manuales de correferencia
            # - speaker_corrections: correcciones manuales de speaker
            # - alert_dismissals: alertas descartadas por content_hash
            # - suppression_rules: reglas de supresión del usuario
            # - project_detector_weights: pesos adaptativos nivel 3 (acumulan feedback)
            # - detector_calibration: se recomputa, pero no se borra
            # Estas tablas NO se borran.
            # Borrar analysis phases
            conn.execute(
                "DELETE FROM analysis_phases WHERE run_id IN (SELECT id FROM analysis_runs WHERE project_id = ?)",
                (project_id,),
            )
            conn.execute("DELETE FROM analysis_runs WHERE project_id = ?", (project_id,))
            # Borrar enrichment cache (S8a-16)
            conn.execute("DELETE FROM enrichment_cache WHERE project_id = ?", (project_id,))

        logger.info(f"Cleared existing data for project {project_id}")
    except Exception as clear_err:
        logger.warning(f"Error clearing existing data (continuing): {clear_err}")


def apply_license_and_settings(ctx: dict, tracker: ProgressTracker):
    """Aplica license gating y project settings al análisis."""
    from narrative_assistant.licensing.gating import apply_license_gating, is_licensing_enabled
    from narrative_assistant.pipelines.unified_analysis import UnifiedConfig

    analysis_config = UnifiedConfig.standard()
    if is_licensing_enabled():
        try:
            from narrative_assistant.licensing.verification import get_cached_license

            cached = get_cached_license()
            tier = cached.tier if cached else None
            analysis_config = apply_license_gating(analysis_config, tier)
            logger.info(f"License gating applied (tier={tier})")
        except Exception as lic_err:
            logger.warning(f"License gating check failed, using defaults: {lic_err}")
    else:
        logger.debug("Licensing disabled (NA_LICENSING_ENABLED=false), all features enabled")

    # Apply project settings
    try:
        import json

        project = ctx["project"]
        project_settings = (
            project.settings
            if isinstance(project.settings, dict)
            else (json.loads(project.settings) if project.settings else {})
        )
        analysis_features = project_settings.get("analysis_features", {})
        if analysis_features:
            _SETTINGS_MAP = {
                "character_profiling": "run_character_profiling",
                "network_analysis": "run_network_analysis",
                "anachronism_detection": "run_anachronism_detection",
                "ooc_detection": "run_ooc_detection",
                "classical_spanish": "run_classical_spanish",
                "name_variants": "run_name_variants",
                "multi_model_voting": "run_multi_model_voting",
                "spelling": "run_spelling",
                "grammar": "run_grammar",
                "consistency": "run_consistency",
                "speech_tracking": "run_speech_tracking",
            }
            for feat_key, config_field in _SETTINGS_MAP.items():
                if feat_key in analysis_features and hasattr(analysis_config, config_field):
                    user_val = bool(analysis_features[feat_key])
                    if not user_val:
                        setattr(analysis_config, config_field, False)
            logger.info(f"Applied project analysis settings: {analysis_features}")
    except Exception as settings_err:
        logger.debug(f"Could not apply project analysis settings: {settings_err}")

    ctx["analysis_config"] = analysis_config

    # Extraer configuración LLM (quality_level + sensitivity) de la tabla llm_config
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT quality_level, sensitivity FROM llm_config LIMIT 1"
            ).fetchone()
        if row:
            ctx["quality_level"] = row[0] or "rapida"
            ctx["sensitivity"] = float(row[1]) if row[1] is not None else 5.0
        else:
            ctx["quality_level"] = "rapida"
            ctx["sensitivity"] = 5.0
    except Exception:
        ctx["quality_level"] = "rapida"
        ctx["sensitivity"] = 5.0


# ============================================================================
# Phase 1: Parsing
# ============================================================================


def run_parsing(ctx: dict, tracker: ProgressTracker):
    """Fase 1: Lee y parsea el documento."""
    from narrative_assistant.parsers.base import detect_format, get_parser
    from narrative_assistant.persistence.project import ProjectManager

    tmp_path = ctx["tmp_path"]

    tracker.start_phase("parsing", 0, "Leyendo el documento...")

    doc_format = detect_format(tmp_path)
    parser = get_parser(doc_format)
    parse_result = parser.parse(tmp_path)

    if parse_result.is_failure:
        raise Exception(f"Error parsing document: {parse_result.error}")

    raw_document = parse_result.value
    full_text = raw_document.full_text  # type: ignore[union-attr]
    word_count = len(full_text.split())

    # S7c-03: Validar documento vacío
    if not full_text or not full_text.strip():
        raise Exception(
            "El documento está vacío o no contiene texto legible. "
            "Verifica que el archivo no esté corrupto."
        )

    tracker.set_metric("word_count", word_count)
    tracker.end_phase("parsing", 0)

    # Actualizar word_count del proyecto inmediatamente
    try:
        project = ctx["project"]
        project.word_count = word_count
        proj_manager = ProjectManager(ctx["db_session"])
        proj_manager.update(project)
        logger.debug(f"Updated project word_count to {word_count}")
    except Exception as e:
        logger.warning(f"Could not update project word_count: {e}")

    logger.info(f"Parsing complete: {word_count} words")

    # Store results in context
    ctx["raw_document"] = raw_document
    ctx["full_text"] = full_text
    ctx["word_count"] = word_count


# ============================================================================
# Phase 2: Classification
# ============================================================================


def run_classification(ctx: dict, tracker: ProgressTracker):
    """Fase 2: Clasifica el tipo de documento."""
    full_text = ctx["full_text"]

    tracker.start_phase("classification", 1, "Clasificando tipo de documento...")

    try:
        from narrative_assistant.feature_profile.models import normalize_document_type
        from narrative_assistant.parsers.document_classifier import DocumentClassifier

        classifier = DocumentClassifier()
        classification = classifier.classify(full_text)

        if classification:
            doc_type = classification.document_type
            # Enum → str largo → código corto (FIC, MEM, etc.) para BD
            long_str = doc_type.value if hasattr(doc_type, "value") else str(doc_type)
            document_type_str = normalize_document_type(long_str)
        else:
            document_type_str = "FIC"  # Default coherente con Project.document_type

        ctx["classification"] = classification
        ctx["document_type"] = document_type_str

        logger.info(f"Document classified as: {document_type_str}")
        if classification:
            logger.info(f"  Confidence: {classification.confidence:.2f}")
            logger.info(f"  Type: {document_type_str}")

        # Guardar en proyecto
        try:
            project = ctx["project"]
            if hasattr(project, "document_type"):
                project.document_type = document_type_str
            from narrative_assistant.persistence.project import ProjectManager

            proj_manager = ProjectManager(ctx["db_session"])
            proj_manager.update(project)
        except Exception as e:
            logger.debug(f"Could not persist document_type: {e}")

    except Exception as e:
        logger.warning(f"Document classification failed (continuing): {e}")
        ctx["classification"] = None
        ctx["document_type"] = "FIC"  # Default coherente con Project.document_type

    tracker.end_phase("classification", 1)


# ============================================================================
# Phase 3: Structure
# ============================================================================


def run_structure(ctx: dict, tracker: ProgressTracker):
    """Fase 3: Detecta la estructura del documento (capítulos, secciones)."""
    project_id = ctx["project_id"]
    full_text = ctx["full_text"]
    raw_document = ctx["raw_document"]
    db_session = ctx["db_session"]

    tracker.start_phase("structure", 2, "Identificando la estructura del documento...")

    from narrative_assistant.parsers.structure_detector import StructureDetector

    detector = StructureDetector()

    # Detectar estructura pasando el RawDocument completo
    structure_result = detector.detect(raw_document)

    chapters_data = []
    if structure_result.is_success and structure_result.value.chapters:  # type: ignore[union-attr]
        for ch in structure_result.value.chapters:  # type: ignore[union-attr]
            content = ch.get_text(full_text)
            sections_data = []
            for sec in ch.sections:
                sections_data.append(
                    {
                        "title": sec.title,
                        "level": sec.level,  # type: ignore[union-attr]
                        "start_char": sec.start_char,
                        "end_char": sec.end_char,
                    }
                )
            chapters_data.append(
                {
                    "chapter_number": ch.number,
                    "title": ch.title or f"Capítulo {ch.number}",
                    "content": content,
                    "start_char": ch.start_char,
                    "end_char": ch.end_char,
                    "word_count": len(content.split()),
                    "structure_type": ch.structure_type.value
                    if hasattr(ch.structure_type, "value")
                    else str(ch.structure_type),
                    "sections": sections_data,
                }
            )

    chapters_count = len(chapters_data)

    if chapters_count == 0:
        # Crear un capítulo único con todo el texto
        chapters_data = [
            {
                "chapter_number": 1,
                "title": "Documento completo",
                "start_char": 0,
                "end_char": len(full_text),
                "content": full_text,
                "word_count": ctx["word_count"],
                "structure_type": "flat",
                "sections": [],
            }
        ]
        chapters_count = 1

    # Persistir capítulos en BD
    persist_chapters_to_db(chapters_data, project_id, db_session)

    # Cargar capítulos con IDs de BD
    from narrative_assistant.persistence.chapter import ChapterRepository

    chapter_repo = ChapterRepository(db_session)
    chapters_with_ids = chapter_repo.get_by_project(project_id)

    def find_chapter_id_for_position(start_char: int) -> int | None:
        """Busca el chapter_id para una posición de carácter dada."""
        for ch in chapters_with_ids:
            if ch.start_char <= start_char < ch.end_char:
                return ch.id
        # Fallback: capítulo más cercano
        if chapters_with_ids:
            closest = min(chapters_with_ids, key=lambda c: abs(c.start_char - start_char))
            return closest.id
        return None

    # S8a-02: Compute and persist chapter metrics (lightweight, regex-based)
    try:
        from narrative_assistant.persistence.chapter import compute_chapter_metrics

        metrics_computed = 0
        for ch_db in chapters_with_ids:
            ch_data = next(
                (c for c in chapters_data if c["chapter_number"] == ch_db.chapter_number),
                None,
            )
            if ch_data and ch_data.get("content"):
                metrics = compute_chapter_metrics(ch_data["content"])
                if metrics:
                    chapter_repo.update_metrics(ch_db.id, metrics)  # type: ignore[arg-type]
                    metrics_computed += 1
        logger.info(f"Chapter metrics computed for {metrics_computed}/{chapters_count} chapters")
    except Exception as e:
        logger.warning(f"Error computing chapter metrics (continuing): {e}")

    # S16: Detect and persist dialogues
    try:
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.persistence.dialogue import DialogueData, get_dialogue_repository

        dialogue_repo = get_dialogue_repository(db_session)
        # Limpiar diálogos anteriores (en caso de re-análisis)
        dialogue_repo.delete_by_project(project_id)

        dialogues_total = 0
        for ch_db in chapters_with_ids:
            ch_data = next(
                (c for c in chapters_data if c["chapter_number"] == ch_db.chapter_number),
                None,
            )
            if ch_data and ch_data.get("content"):
                dialogue_result = detect_dialogues(ch_data["content"])
                if dialogue_result.is_success and dialogue_result.value.dialogues:
                    # Convertir DialogueSpan a DialogueData
                    dialogues_to_save = []
                    for dlg_span in dialogue_result.value.dialogues:
                        dialogue_data = DialogueData(
                            id=None,
                            project_id=project_id,
                            chapter_id=ch_db.id,
                            start_char=dlg_span.start_char,
                            end_char=dlg_span.end_char,
                            text=dlg_span.text,
                            dialogue_type=dlg_span.dialogue_type.value,
                            original_format=dlg_span.original_format,
                            attribution_text=dlg_span.attribution_text,
                            speaker_hint=dlg_span.speaker_hint,
                            confidence=dlg_span.confidence,
                        )
                        dialogues_to_save.append(dialogue_data)

                    dialogue_repo.create_batch(dialogues_to_save)
                    dialogues_total += len(dialogues_to_save)

        logger.info(f"Dialogues detected and persisted: {dialogues_total} dialogues across {chapters_count} chapters")

        # S16b: Inicializar dialogue_style_preference desde correction_config
        try:
            from narrative_assistant.nlp.dialogue_config_mapper import (
                map_correction_config_to_dialogue_preference,
            )
            from narrative_assistant.persistence.project import ProjectManager

            proj_manager = ProjectManager(db_session)
            project = proj_manager.get_by_id(project_id)

            if project and project.settings_json:
                correction_config = project.settings_json.get("correction_config", {})
                dialogue_dash = correction_config.get("dialogue_dash")
                quote_style = correction_config.get("quote_style")

                # Mapear a preferencia de diálogo
                preference = map_correction_config_to_dialogue_preference(dialogue_dash, quote_style)

                # Guardar en settings
                if "dialogue_style_preference" not in project.settings_json:
                    project.settings_json["dialogue_style_preference"] = preference
                    proj_manager.update(project)
                    logger.info(f"Initialized dialogue_style_preference={preference} from correction_config")
        except Exception as pref_err:
            logger.warning(f"Error initializing dialogue_style_preference (continuing): {pref_err}")
    except Exception as e:
        logger.warning(f"Error detecting/persisting dialogues (continuing): {e}")

    tracker.set_metric("chapters_found", chapters_count)
    tracker.end_phase("structure", 2)

    logger.info(f"Structure detection complete: {chapters_count} chapters")

    # Store results
    ctx["chapters_data"] = chapters_data
    ctx["chapters_count"] = chapters_count
    ctx["chapters_with_ids"] = chapters_with_ids
    ctx["find_chapter_id_for_position"] = find_chapter_id_for_position


# ============================================================================
# Tier 2 gate: Claim heavy analysis slot
# ============================================================================


def claim_heavy_slot_or_queue(ctx: dict, tracker: ProgressTracker) -> bool:
    """
    Intenta reclamar el slot de análisis pesado.

    Returns:
        True si se reclamó el slot (continuar con fases pesadas).
        False si el proyecto fue encolado (detener aquí).
    """

    project_id = ctx["project_id"]
    with deps._progress_lock:
        # S8a-18: Check watchdog timeout — if heavy slot has been held too long, force-release
        if (
            deps._heavy_analysis_project_id is not None
            and deps._heavy_analysis_claimed_at is not None
        ):
            elapsed = time.time() - deps._heavy_analysis_claimed_at
            if elapsed > deps.HEAVY_SLOT_TIMEOUT_SECONDS:
                stale_pid = deps._heavy_analysis_project_id
                logger.warning(
                    f"Watchdog: heavy slot held by project {stale_pid} for "
                    f"{elapsed:.0f}s (>{deps.HEAVY_SLOT_TIMEOUT_SECONDS}s). Force-releasing."
                )
                deps._heavy_analysis_project_id = None
                deps._heavy_analysis_claimed_at = None
                # Mark stale project as error
                stale_storage = deps.analysis_progress_storage.get(stale_pid)
                if stale_storage:
                    stale_storage["status"] = "error"
                    stale_storage["error"] = "Análisis excedió el tiempo máximo"

        if deps._heavy_analysis_project_id is not None:
            # Heavy slot busy — queue lightweight metadata only (F-005)
            queue_entry: dict[str, Any] = {
                "project_id": project_id,
                "mode": ctx.get("queue_mode", "full"),
            }
            if queue_entry["mode"] == "partial":
                queue_entry["partial_phases"] = list(ctx.get("partial_frontend_phases", []))
                queue_entry["partial_force"] = bool(ctx.get("partial_force", False))

            deps._heavy_analysis_queue.append(queue_entry)
            deps.analysis_progress_storage[project_id]["status"] = "queued_for_heavy"
            deps.analysis_progress_storage[project_id]["current_phase"] = (
                "Estructura lista — en cola para análisis profundo"
            )
            deps.analysis_progress_storage[project_id]["current_action"] = ""
            return False
        else:
            deps._heavy_analysis_project_id = project_id
            deps._heavy_analysis_claimed_at = time.time()
            return True


def run_ollama_healthcheck(ctx: dict, tracker: ProgressTracker):
    """S7c-04: Health check de Ollama antes de fases pesadas."""
    analysis_config = ctx["analysis_config"]
    if not analysis_config.use_llm:
        return

    try:
        from narrative_assistant.llm.ollama_manager import is_ollama_available

        ollama_available = is_ollama_available()
        if not ollama_available:
            logger.warning("Ollama no disponible, continuando sin LLM")
            analysis_config.use_llm = False
    except ImportError:
        logger.debug("Ollama manager not available")
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        analysis_config.use_llm = False


# ============================================================================
# Phase 4: NER
# ============================================================================


def _filter_overlapping_entities(raw_entities: list) -> list:
    """Elimina entidades solapadas, prefiriendo la más larga."""
    if not raw_entities:
        return []
    sorted_ents = sorted(raw_entities, key=lambda e: (e.start_char, -(e.end_char - e.start_char)))
    result = []
    for ent in sorted_ents:
        overlaps = False
        for accepted in result:
            if not (ent.end_char <= accepted.start_char or ent.start_char >= accepted.end_char):
                overlaps = True
                break
        if not overlaps:
            result.append(ent)
    return result


def run_ner(ctx: dict, tracker: ProgressTracker):
    """Fase 4: Extracción de entidades con NER."""
    # Asegurar que existe progress storage (puede haberse perdido tras reinicio)
    project_id = ctx["project_id"]
    _ensure_storage_exists(project_id)

    from narrative_assistant.entities.models import (
        Entity,
        EntityImportance,
        EntityMention,
        EntityType,
    )
    from narrative_assistant.entities.repository import get_entity_repository
    from narrative_assistant.nlp.ner import EntityLabel, NERExtractor
    from narrative_assistant.persistence.analysis_cache import get_analysis_cache

    project_id = ctx["project_id"]
    full_text = ctx["full_text"]
    find_chapter_id_for_position = ctx["find_chapter_id_for_position"]
    # Obtener fingerprint del proyecto (campo de BD, NO de ctx)
    _fp_project = ctx.get("project")
    document_fingerprint = getattr(_fp_project, "document_fingerprint", "") if _fp_project else ""
    analysis_config = ctx.get("analysis_config")

    tracker.start_phase("ner", 3, "Buscando personajes, lugares y otros elementos...")

    # ========================================================================
    # Cache Check: Skip expensive NER if document unchanged
    # ========================================================================
    cache = get_analysis_cache()
    config_hash = cache.compute_ner_config_hash(analysis_config) if analysis_config else "default"

    logger.info(
        f"[NER_CACHE] Checking: project={project_id}, "
        f"fp={'...' + document_fingerprint[-16:] if document_fingerprint else 'EMPTY'}, "
        f"config={config_hash}"
    )

    cached_data = cache.get_ner_results(project_id, document_fingerprint, config_hash)
    if cached_data is not None:
        logger.info(
            f"[NER] Using cached results: {cached_data['entity_count']} entities, "
            f"{cached_data['mention_count']} mentions (SKIP NER)"
        )

        # Deserialize entities from cache
        try:
            entities = _restore_entities_from_cache(
                cached_data["entities_json"],
                project_id,
                find_chapter_id_for_position,
            )

            ctx["entities"] = entities
            tracker.set_metric("entities_found", len(entities))
            tracker.end_phase("ner", 3)

            logger.info(f"[NER] Cache restore complete: {len(entities)} entities")
            return  # Skip NER computation

        except Exception as e:
            logger.warning(f"[NER] Cache restore failed, re-running NER: {e}")
            # Continue to normal NER execution
    # ========================================================================

    ner_pct_start, ner_pct_end = tracker.get_phase_progress_range("ner")

    # Callback para actualizar progreso durante NER
    def ner_progress_callback(fase: str, pct: float, msg: str):
        ner_range = ner_pct_end - ner_pct_start
        ner_progress = ner_pct_start + int(pct * ner_range)
        _update_storage(project_id, progress=ner_progress, current_action=msg)
        tracker.update_time_remaining()

    # Verificar si el modelo transformer NER necesita descargarse
    try:
        from narrative_assistant.core.model_manager import ModelType, get_model_manager

        manager = get_model_manager()
        if not manager.get_model_path(ModelType.TRANSFORMER_NER):
            _update_storage(
                project_id,
                current_phase="Descargando modelo NER (~500 MB, solo la primera vez)...",
                current_action="Esto puede tardar unos minutos...",
            )
    except Exception:
        pass

    # Habilitar preprocesamiento con LLM para mejor detección de entidades
    ner_extractor = NERExtractor(use_llm_preprocessing=True)
    ner_result = ner_extractor.extract_entities(
        full_text,
        progress_callback=ner_progress_callback,
    )

    entities = []
    entity_repo = get_entity_repository()

    if ner_result.is_success and ner_result.value:
        raw_entities = ner_result.value.entities or []

        label_to_type = {
            EntityLabel.PER: EntityType.CHARACTER,
            EntityLabel.LOC: EntityType.LOCATION,
            EntityLabel.ORG: EntityType.ORGANIZATION,
            EntityLabel.MISC: EntityType.CONCEPT,
        }

        raw_entities = _filter_overlapping_entities(raw_entities)
        logger.info(f"After overlap filtering: {len(raw_entities)} entities")

        # Agrupar entidades por nombre canónico
        entity_mentions: dict[str, list] = {}
        for ent in raw_entities:
            normalized = " ".join(ent.text.strip().lower().split())
            key = normalized
            if key not in entity_mentions:
                entity_mentions[key] = []
            entity_mentions[key].append(ent)

        logger.info(
            f"DEBUG NER grouping: {len(raw_entities)} raw mentions -> "
            f"{len(entity_mentions)} unique entities"
        )
        sorted_entities = sorted(entity_mentions.items(), key=lambda x: len(x[1]), reverse=True)[
            :10
        ]
        for key, mentions in sorted_entities:
            logger.info(f"  Entity '{key}': {len(mentions)} mentions")

        logger.info(
            f"NER: {len(raw_entities)} menciones totales, {len(entity_mentions)} entidades únicas"
        )

        # Recolectar nombres canónicos para evitar conflictos de aliases
        all_canonical_names = set()
        for key, mentions_list in entity_mentions.items():
            first_mention = mentions_list[0]
            best_mentions = [m for m in mentions_list if m.label == EntityLabel.PER]
            canonical_text = best_mentions[0].text if best_mentions else first_mention.text
            all_canonical_names.add(canonical_text)

        # Crear entidades únicas
        total_entities_to_create = len(entity_mentions)
        entities_created = 0
        for key, mentions_list in entity_mentions.items():
            # Check for cancellation every entity
            tracker.check_cancelled()
            first_mention = mentions_list[0]
            mention_count = len(mentions_list)

            # Calcular importancia
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

            first_appearance = min(m.start_char for m in mentions_list)

            # Determinar tipo por votación
            label_counts = Counter(m.label for m in mentions_list)
            if EntityLabel.PER in label_counts and EntityLabel.MISC in label_counts:
                best_label = EntityLabel.PER
            else:
                best_label = label_counts.most_common(1)[0][0]

            best_mentions = [m for m in mentions_list if m.label == best_label]
            canonical_text = best_mentions[0].text if best_mentions else first_mention.text

            entity_type = label_to_type.get(best_label, EntityType.CONCEPT)
            auto_aliases = []
            if entity_type == EntityType.CHARACTER:
                auto_aliases = generate_person_aliases(canonical_text, all_canonical_names)
                if auto_aliases:
                    logger.debug(f"Generated aliases for '{canonical_text}': {auto_aliases}")

            entity = Entity(
                project_id=project_id,
                entity_type=entity_type,
                canonical_name=canonical_text,
                aliases=auto_aliases,
                importance=importance,
                description=None,
                first_appearance_char=first_appearance,
                mention_count=mention_count,
                merged_from_ids=[],
                is_active=True,
            )

            try:
                entity_id = entity_repo.create_entity(entity)
                entity.id = entity_id
                entities.append(entity)

                # Crear menciones en BD
                mentions_to_create = []
                for ent in mentions_list:
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

                if len(mentions_to_create) >= 5:
                    sample_forms = [m.surface_form for m in mentions_to_create[:5]]
                    logger.info(
                        f"Entity '{entity.canonical_name}': Creating "
                        f"{len(mentions_to_create)} mentions. "
                        f"Sample surface forms: {sample_forms}"
                    )

                try:
                    mentions_created = entity_repo.create_mentions_batch(mentions_to_create)
                    logger.debug(
                        f"Entity '{entity.canonical_name}': "
                        f"Batch created {mentions_created} mentions"
                    )
                except Exception as batch_err:
                    logger.warning(
                        f"Batch insert failed for {entity.canonical_name}, "
                        f"falling back to individual: {batch_err}"
                    )
                    mentions_created = 0
                    for mention in mentions_to_create:
                        try:
                            entity_repo.create_mention(mention)
                            mentions_created += 1
                        except Exception as me:
                            logger.warning(
                                f"Error creating mention for "
                                f"{entity.canonical_name} at {mention.start_char}: {me}"
                            )

                if mentions_created != len(mentions_list):
                    logger.warning(
                        f"Entity '{entity.canonical_name}': Created "
                        f"{mentions_created}/{len(mentions_list)} mentions - MISMATCH!"
                    )
                else:
                    logger.info(
                        f"Entity '{entity.canonical_name}': Successfully created "
                        f"{mentions_created} mentions"
                    )

                # Actualizar progreso cada 5 entidades
                entities_created += 1
                if entities_created % 5 == 0 and total_entities_to_create > 0:
                    sub_pct = entities_created / total_entities_to_create
                    sub_progress = ner_pct_start + int(sub_pct * (ner_pct_end - ner_pct_start))
                    _update_storage(project_id, progress=min(ner_pct_end, sub_progress))
                    tracker.update_time_remaining()

            except Exception as e:
                logger.warning(f"Error creating entity {first_mention.text}: {e}")

    tracker.end_phase("ner", 3)
    logger.info(f"NER complete: {len(entities)} entities")

    ctx["entities"] = entities
    ctx["entity_repo"] = entity_repo

    # ========================================================================
    # Cache Write: Save NER results for future re-analysis
    # ========================================================================
    try:
        if document_fingerprint and entities:
            entities_json = _serialize_entities_for_cache(entities, entity_repo)
            total_mentions = sum(e.mention_count or 0 for e in entities)

            cache.set_ner_results(
                project_id=project_id,
                document_fingerprint=document_fingerprint,
                config_hash=config_hash,
                entities_json=entities_json,
                entity_count=len(entities),
                mention_count=total_mentions,
                processed_chars=len(full_text),
            )
    except Exception as cache_err:
        logger.warning(f"[NER] Cache write failed (continuing): {cache_err}")
    # ========================================================================


# ============================================================================
# Phase 3.25: LLM validation of entities
# ============================================================================


def run_llm_entity_validation(ctx: dict, tracker: ProgressTracker):
    """Fase 3.25: Filtra entidades inválidas usando LLM."""
    project_id = ctx["project_id"]
    entities = ctx["entities"]
    entity_repo = ctx["entity_repo"]

    _update_storage(project_id, current_action="Verificando personajes detectados...")
    try:
        from narrative_assistant.llm.client import get_llm_client

        llm_client = get_llm_client()
        if not (llm_client and llm_client.is_available and len(entities) > 0):
            return

        entities_to_validate = [
            {"name": e.canonical_name, "type": e.entity_type.value} for e in entities
        ]

        validation_prompt = f"""Revisa esta lista de entidades extraídas de un texto narrativo.
Marca como INVÁLIDAS las que NO sean entidades reales:
- Descripciones físicas ("Sus ojos verdes", "cabello negro")
- Frases incompletas o fragmentos
- Pronombres solos ("él", "ella") - a menos que sean nombres propios
- Adjetivos o expresiones genéricas

ENTIDADES A VALIDAR:
{json.dumps(entities_to_validate, ensure_ascii=False, indent=2)}

Responde SOLO con JSON:
{{"invalid": ["nombre1", "nombre2", ...]}}

Si todas son válidas, responde: {{"invalid": []}}

JSON:"""

        response = llm_client.complete(
            validation_prompt,
            system=(
                "Eres un experto en NER. Identifica entidades inválidas "
                "(no son personajes, lugares u organizaciones reales)."
            ),
            temperature=0.1,
        )

        if response:
            try:
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    lines = [line for line in lines if not line.startswith("```")]
                    cleaned = "\n".join(lines)
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    cleaned = cleaned[start_idx:end_idx]
                data = json.loads(cleaned)
                invalid_names = set(n.lower() for n in data.get("invalid", []))

                if invalid_names:
                    before_count = len(entities)
                    entities_to_remove = []
                    for ent in entities:
                        if ent.canonical_name.lower() in invalid_names:
                            entities_to_remove.append(ent)
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

    tracker.check_cancelled()
    ctx["entities"] = entities


# ============================================================================
# Phase 3.5: Entity Fusion + Coreference
# ============================================================================


def _name_score(ent) -> int:
    """Calcula un score para decidir cuál nombre es más descriptivo."""
    name = ent.canonical_name
    score = 0
    score += len(name) * 2
    if name and name[0].isupper():
        score += 20
    if " " in name:
        score += 30
    lower_name = name.lower()
    pronouns = {"él", "ella", "ellos", "ellas", "este", "esta", "ese", "esa"}
    if lower_name in pronouns:
        score -= 100
    return score


def _is_name_subset(short_name: str, long_name: str) -> bool:
    """Check if short_name's words are a subset of long_name's words."""
    short_words = set(short_name.lower().split())
    long_words = set(long_name.lower().split())
    return bool(short_words) and bool(long_words) and short_words < long_words


def run_fusion(ctx: dict, tracker: ProgressTracker):
    """Fase 3.5: Fusión de entidades + correferencias."""
    from narrative_assistant.entities.models import EntityImportance, EntityType
    from narrative_assistant.entities.repository import get_entity_repository

    project_id = ctx["project_id"]
    _ensure_storage_exists(project_id)
    full_text = ctx["full_text"]
    chapters_data = ctx["chapters_data"]
    entities = ctx["entities"]
    find_chapter_id_for_position = ctx["find_chapter_id_for_position"]

    tracker.start_phase("fusion", 4, "Unificando entidades mencionadas de diferentes formas...")
    _update_storage(project_id, current_action="Preparando unificación...")

    fusion_pct_start, fusion_pct_end = tracker.get_phase_progress_range("fusion")
    coref_result = None
    merged_entity_ids = set()

    try:
        from narrative_assistant.entities.semantic_fusion import get_semantic_fusion_service

        fusion_service = get_semantic_fusion_service()
        entity_repo = get_entity_repository()
        ctx["entity_repo"] = entity_repo

        _update_storage(project_id, current_action=f"Comparando {len(entities)} entidades...")

        # 1. Fusión semántica por tipo
        entities_by_type: dict[EntityType, list] = {}
        for ent in entities:
            if ent.entity_type not in entities_by_type:
                entities_by_type[ent.entity_type] = []
            entities_by_type[ent.entity_type].append(ent)

        fusion_pairs: list[tuple] = []

        for entity_type, type_entities in entities_by_type.items():
            if len(type_entities) < 2:
                continue

            entity_names = [e.canonical_name for e in type_entities]
            logger.info(f"Fusion check: {entity_type.value} entities = {entity_names}")

            for i, ent1 in enumerate(type_entities):
                for j, ent2 in enumerate(type_entities):
                    if i >= j:
                        continue

                    name1 = ent1.canonical_name
                    name2 = ent2.canonical_name
                    force_merge = _is_name_subset(name1, name2) or _is_name_subset(name2, name1)

                    if force_merge:
                        logger.info(f"Fusión forzada por nombre contenido: '{name1}' ↔ '{name2}'")

                    result = fusion_service.should_merge(ent1, ent2)

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

                        score1 = _name_score(ent1)
                        score2 = _name_score(ent2)
                        if score1 >= score2:
                            fusion_pairs.append((ent1, ent2))
                        else:
                            fusion_pairs.append((ent2, ent1))

        # Ejecutar fusiones
        if fusion_pairs:
            _update_storage(
                project_id,
                current_action=f"Unificando {len(fusion_pairs)} pares de nombres similares...",
            )

        for idx, (keep_entity, merge_entity) in enumerate(fusion_pairs):
            # Check for cancellation every 10 pairs
            if idx % 10 == 0:
                tracker.check_cancelled()

            if merge_entity.id in merged_entity_ids:
                continue

            try:
                if keep_entity.aliases is None:
                    keep_entity.aliases = []
                if merge_entity.canonical_name not in keep_entity.aliases:
                    keep_entity.aliases.append(merge_entity.canonical_name)

                keep_entity.mention_count = (keep_entity.mention_count or 0) + (
                    merge_entity.mention_count or 0
                )

                if keep_entity.merged_from_ids is None:
                    keep_entity.merged_from_ids = []
                if merge_entity.id:
                    keep_entity.merged_from_ids.append(merge_entity.id)

                entity_repo.update_entity(
                    entity_id=keep_entity.id,
                    aliases=keep_entity.aliases,
                    merged_from_ids=keep_entity.merged_from_ids,
                )
                entity_repo.increment_mention_count(keep_entity.id, merge_entity.mention_count or 0)

                # Recalcular importancia
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
                    logger.debug(
                        f"Importancia actualizada: '{keep_entity.canonical_name}' "
                        f"-> {new_importance.value}"
                    )

                if merge_entity.id and keep_entity.id:
                    entity_repo.move_mentions(merge_entity.id, keep_entity.id)

                entity_repo.delete_entity(merge_entity.id, hard_delete=False)
                merged_entity_ids.add(merge_entity.id)

                logger.info(
                    f"Fusión ejecutada: '{merge_entity.canonical_name}' → "
                    f"'{keep_entity.canonical_name}'"
                )

                if (idx + 1) % 5 == 0:
                    _update_storage(
                        project_id,
                        current_action=(
                            f"Unificando nombres: {keep_entity.canonical_name}... "
                            f"({idx + 1}/{len(fusion_pairs)})"
                        ),
                    )

            except Exception as e:
                logger.warning(
                    f"Error fusionando {merge_entity.canonical_name} → "
                    f"{keep_entity.canonical_name}: {e}"
                )

        entities = [e for e in entities if e.id not in merged_entity_ids]

        if fusion_pairs:
            _update_storage(
                project_id,
                current_action=f"Unificados {len(merged_entity_ids)} personajes duplicados",
            )

        # Reconciliar contadores
        try:
            reconciled = entity_repo.reconcile_all_mention_counts(project_id)
            logger.info(f"Reconciliados contadores de menciones para {reconciled} entidades")
            entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        except Exception as recon_err:
            logger.warning(f"Error reconciliando contadores de menciones: {recon_err}")

        # SP-1: Re-aplicar merges de usuario que no haya descubierto la fusión automática
        _reapply_user_merges(project_id, entity_repo, entities)

        _update_storage(project_id, progress=57)
        tracker.update_time_remaining()

        # 2. Resolución de correferencias
        _update_storage(
            project_id,
            current_phase="Identificando referencias cruzadas entre personajes...",
        )

        try:
            from narrative_assistant.nlp.coreference_resolver import (
                CorefConfig,
                CorefMethod,
                resolve_coreferences_voting,
            )
            from narrative_assistant.nlp.coreference_resolver import (
                MentionType as CorefMentionType,
            )

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
                quality_level=ctx.get("quality_level", "rapida"),
                sensitivity=ctx.get("sensitivity", 5.0),
            )

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

            for method, count in coref_result.method_contributions.items():
                logger.debug(f"  Método {method.value}: {count} resoluciones")

            # Vincular cadenas con entidades
            character_entities = [e for e in entities if e.entity_type == EntityType.CHARACTER]

            for chain in coref_result.chains:
                if not chain.main_mention:
                    logger.debug(
                        f"Cadena de correferencia ignorada (solo pronombres): "
                        f"{[m.text for m in chain.mentions[:3]]}..."
                    )
                    continue

                matching_entity = None
                for ent in character_entities:
                    if (
                        ent.canonical_name
                        and chain.main_mention
                        and ent.canonical_name.lower() == chain.main_mention.lower()
                    ):
                        matching_entity = ent
                        break
                    if ent.aliases:
                        for alias in ent.aliases:
                            if chain.main_mention and alias.lower() == chain.main_mention.lower():
                                matching_entity = ent
                                break
                    if not matching_entity:
                        for mention in chain.mentions:
                            if (
                                ent.canonical_name
                                and mention.text.lower() == ent.canonical_name.lower()
                            ):
                                matching_entity = ent
                                break

                if matching_entity:
                    pronoun_count = sum(
                        1 for m in chain.mentions if m.mention_type == CorefMentionType.PRONOUN
                    )

                    if pronoun_count > 0:
                        try:
                            entity_repo.increment_mention_count(matching_entity.id, pronoun_count)
                            matching_entity.mention_count = (
                                matching_entity.mention_count or 0
                            ) + pronoun_count

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
                                f"Correferencia: +{pronoun_count} pronombres → "
                                f"'{matching_entity.canonical_name}'"
                            )
                        except Exception as e:
                            logger.warning(f"Error actualizando correferencias: {e}")

                    # Añadir aliases nuevos
                    new_aliases = []
                    for mention in chain.mentions:
                        if (
                            mention.mention_type == CorefMentionType.PROPER_NOUN
                            and mention.text.lower() != matching_entity.canonical_name.lower()
                        ):
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
                            logger.debug(
                                f"Nuevos aliases para '{matching_entity.canonical_name}': "
                                f"{new_aliases}"
                            )
                        except Exception as e:
                            logger.warning(f"Error actualizando aliases: {e}")

        except ImportError as e:
            logger.warning(f"Módulo de correferencias no disponible: {e}")
        except Exception as e:
            logger.warning(f"Error en resolución de correferencias: {e}")

        # Marcar fin de fase (entities_found se marca más abajo, después de MentionFinder)
        _update_storage(
            project_id,
            progress=fusion_pct_end,
            current_action=f"Encontrados {len(entities)} personajes y elementos únicos",
        )
        tracker.end_phase("fusion", 4)

        logger.info(
            f"Fusión de entidades completada en "
            f"{tracker.phase_durations.get('fusion', 0):.1f}s: "
            f"{len(merged_entity_ids)} entidades fusionadas, "
            f"{len(entities)} entidades activas"
        )

        # Buscar menciones adicionales
        try:
            from narrative_assistant.nlp.mention_finder import get_mention_finder

            mention_finder = get_mention_finder()
            _update_storage(project_id, current_action="Buscando menciones adicionales...")

            entity_names = [e.canonical_name for e in entities if e.canonical_name]
            aliases_dict = {}
            for e in entities:
                if e.canonical_name and e.aliases:
                    aliases_dict[e.canonical_name] = e.aliases

            existing_positions = set()
            for entity in entities:
                mentions_db = entity_repo.get_mentions_by_entity(entity.id)
                for m in mentions_db:
                    existing_positions.add((m.start_char, m.end_char))

            additional_mentions = mention_finder.find_all_mentions(
                text=full_text,
                entity_names=entity_names,
                aliases=aliases_dict,
                existing_positions=existing_positions,
            )

            from narrative_assistant.entities.models import EntityMention as EntityMentionModel

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
                        ch_id = find_chapter_id_for_position(am.start_char)
                        mention = EntityMentionModel(  # type: ignore[assignment]
                            entity_id=entity.id,
                            surface_form=am.surface_form,
                            start_char=am.start_char,
                            end_char=am.end_char,
                            chapter_id=ch_id,
                            confidence=am.confidence,
                            source="mention_finder",
                        )
                        try:
                            entity_repo.create_mention(mention)  # type: ignore[arg-type]
                            additional_count += 1
                        except Exception:
                            pass

            if additional_count > 0:
                logger.info(f"MentionFinder: Added {additional_count} additional mentions")
                _update_storage(
                    project_id,
                    current_action=f"Encontradas {additional_count} menciones adicionales",
                )

        except Exception as mf_err:
            logger.warning(f"MentionFinder failed (non-critical): {mf_err}")

        # Recalcular importancia final
        logger.info("Recalculando importancia de entidades...")
        db = deps.get_database()
        for entity in entities:
            try:
                with db.connection() as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?",
                        (entity.id,),
                    )
                    row = cursor.fetchone()
                    real_mention_count = row[0] if row else 0

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

                if (
                    new_importance != entity.importance
                    or entity.mention_count != real_mention_count
                ):
                    entity_repo.update_entity(
                        entity_id=entity.id,
                        importance=new_importance,
                    )
                    with db.connection() as conn:
                        conn.execute(
                            "UPDATE entities SET mention_count = ? WHERE id = ?",
                            (real_mention_count, entity.id),
                        )
                    entity.importance = new_importance
                    entity.mention_count = real_mention_count
                    logger.debug(
                        f"'{entity.canonical_name}': {real_mention_count} menciones "
                        f"-> {new_importance.value}"
                    )
            except Exception as e:
                logger.warning(f"Error recalculando importancia de '{entity.canonical_name}': {e}")

        # AHORA sí: marcar entities_found después de MentionFinder + recalcular importancia
        _update_storage(
            project_id,
            metrics_update={"entities_found": len(entities)},
        )

    except Exception as e:
        logger.warning(f"Error en fusión de entidades (continuando sin fusión): {e}")
        tracker.phase_durations["fusion"] = time.time() - tracker.phase_start_times.get(
            "fusion", time.time()
        )
        tracker.phases[4]["completed"] = True
        tracker.phases[4]["current"] = False
        tracker.phases[4]["duration"] = round(tracker.phase_durations["fusion"], 1)

    tracker.check_cancelled()

    ctx["entities"] = entities
    ctx["coref_result"] = coref_result


# ============================================================================
# Phase 4.5: Timeline Construction
# ============================================================================


def run_timeline(ctx: dict, tracker: ProgressTracker):
    """
    Fase 4.5: Construcción de Timeline Temporal.

    Extrae marcadores temporales y construye la timeline.
    Requiere: capítulos + entidades (disponibles después de fusion).
    """
    from narrative_assistant.persistence.timeline import TimelineRepository
    from narrative_assistant.temporal import (
        TemporalConsistencyChecker,
        TemporalMarkerExtractor,
        TimelineBuilder,
    )
    from narrative_assistant.temporal.entity_mentions import load_entity_mentions_by_chapter

    project_id = ctx["project_id"]
    chapters_with_ids = ctx["chapters_with_ids"]
    entities = ctx["entities"]
    entity_repo = ctx.get("entity_repo")

    tracker.start_phase("timeline", 5, "Construyendo línea temporal...")

    try:
        timeline_repo = TimelineRepository()

        # Extraer marcadores temporales
        marker_extractor = TemporalMarkerExtractor()
        all_markers = []

        # Cargar menciones de personajes por capítulo para asociar edades
        entity_mentions_by_chapter: dict[int, list[tuple[int, int, int]]] = {}
        try:
            if entity_repo:
                entity_mentions_by_chapter = load_entity_mentions_by_chapter(
                    entities, chapters_with_ids, entity_repo
                )
        except Exception as e:
            logger.debug(f"Could not load entity mentions for temporal extraction: {e}")

        # Extraer por capítulo
        for chapter in chapters_with_ids:
            chapter_mentions = entity_mentions_by_chapter.get(chapter.chapter_number, [])
            if chapter_mentions:
                chapter_markers = marker_extractor.extract_with_entities(
                    text=chapter.content,
                    entity_mentions=chapter_mentions,
                    chapter=chapter.chapter_number,
                )
            else:
                chapter_markers = marker_extractor.extract(
                    text=chapter.content, chapter=chapter.chapter_number
                )
            all_markers.extend(chapter_markers)

        logger.info(
            f"Timeline: {len(chapters_with_ids)} chapters, {len(all_markers)} markers"
        )

        # Construir timeline
        builder = TimelineBuilder()
        chapter_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "start_position": ch.start_char,
                "content": ch.content,
            }
            for ch in chapters_with_ids
        ]

        timeline = builder.build_from_markers(all_markers, chapter_data)

        # Verificar consistencia temporal
        checker = TemporalConsistencyChecker()
        inconsistencies = checker.check(timeline, all_markers)

        logger.info(
            f"Timeline built: {len(timeline.events)} events, "
            f"{len(inconsistencies)} inconsistencies"
        )

        # Persistir timeline en BD
        try:
            # Limpiar timeline anterior si existe
            timeline_repo.clear_timeline(project_id)

            # Guardar marcadores
            from narrative_assistant.temporal.models import TemporalMarker

            markers_to_save = []
            for m in all_markers:
                if isinstance(m, dict):
                    # Ya es dict
                    markers_to_save.append(m)
                elif isinstance(m, TemporalMarker):
                    markers_to_save.append(m.to_dict())
                elif hasattr(m, "to_dict"):
                    markers_to_save.append(m.to_dict())
                else:
                    # Fallback: convertir a dict básico
                    markers_to_save.append(
                        {
                            "text": getattr(m, "text", ""),
                            "marker_type": getattr(m, "marker_type", "UNKNOWN"),
                            "start_char": getattr(m, "start_char", 0),
                            "end_char": getattr(m, "end_char", 0),
                            "chapter": getattr(m, "chapter", 0),
                        }
                    )

            timeline_repo.save_markers(project_id, markers_to_save)

            # Guardar eventos
            from narrative_assistant.temporal.models import TimelineEvent

            events_saved = 0
            for event in timeline.events:
                event_dict = event.to_dict() if hasattr(event, "to_dict") else event
                event_model = TimelineEvent.from_dict(event_dict)
                event_model.project_id = project_id
                timeline_repo.save_event(event_model)
                events_saved += 1

            logger.info(
                f"Timeline persisted: {len(markers_to_save)} markers, {events_saved} events"
            )

        except Exception as persist_err:
            logger.warning(f"Failed to persist timeline (non-critical): {persist_err}")

        # Guardar en contexto para fases posteriores
        ctx["timeline"] = timeline
        ctx["temporal_markers"] = all_markers
        ctx["temporal_inconsistencies"] = inconsistencies

        tracker.end_phase("timeline", 5)

    except Exception as e:
        logger.warning(f"Timeline construction failed (non-critical): {e}")
        # No bloquear el análisis si falla la timeline
        tracker.end_phase("timeline", 5)


# ============================================================================
# Phase 5: Attributes
# ============================================================================


def run_attributes(ctx: dict, tracker: ProgressTracker):
    """Fase 5: Extracción de atributos de personajes."""
    project_id = ctx["project_id"]
    _ensure_storage_exists(project_id)

    from narrative_assistant.core.result import Result
    from narrative_assistant.entities.repository import get_entity_repository
    from narrative_assistant.nlp.attributes import AttributeExtractor

    project_id = ctx["project_id"]
    full_text = ctx["full_text"]
    chapters_data = ctx["chapters_data"]
    entities = ctx["entities"]
    coref_result = ctx.get("coref_result")

    tracker.start_phase("attributes", 5, "Analizando características de los personajes...")

    attr_pct_start, attr_pct_end = tracker.get_phase_progress_range("attributes")
    attributes = []

    if entities:
        # Detectar GPU
        try:
            from narrative_assistant.core.device import get_device_detector

            detector = get_device_detector()
            has_gpu = detector.device_type.value in ("cuda", "mps")
        except Exception:
            has_gpu = False

        use_embeddings = has_gpu
        if use_embeddings:
            logger.info("GPU detectada - habilitando análisis de embeddings para atributos")
            _update_storage(project_id, current_action="Análisis avanzado con GPU activado")
        else:
            logger.info("Sin GPU - usando métodos rápidos para atributos (LLM, patrones)")

        attr_extractor = AttributeExtractor(use_embeddings=use_embeddings)
        entity_repo = get_entity_repository()

        # Preparar menciones
        character_entities = [e for e in entities if e.entity_type.value == "character"]

        if character_entities:
            entity_mentions = []
            for e in character_entities:
                if e.id:
                    db_mentions = entity_repo.get_mentions_by_entity(e.id)
                    for m in db_mentions:
                        entity_mentions.append((e.canonical_name, m.start_char, m.end_char))
                if not any(name == e.canonical_name for name, _, _ in entity_mentions):
                    entity_mentions.append(
                        (
                            e.canonical_name,
                            e.first_appearance_char or 0,
                            (e.first_appearance_char or 0) + len(e.canonical_name or ""),
                        )
                    )

            logger.debug(
                f"Menciones de BD cargadas: {len(entity_mentions)} "
                f"para {len(character_entities)} entidades"
            )

            # Añadir menciones de correferencia
            if coref_result and coref_result.chains:
                for chain in coref_result.chains:
                    matching_entity = next(
                        (
                            e
                            for e in character_entities
                            if e.canonical_name
                            and chain.main_mention
                            and e.canonical_name.lower() == chain.main_mention.lower()
                        ),
                        None,
                    )
                    if matching_entity:
                        for mention in chain.mentions:
                            entity_mentions.append(
                                (
                                    matching_entity.canonical_name,
                                    mention.start_char,
                                    mention.end_char,
                                )
                            )

            logger.info(f"Extrayendo atributos: {len(entity_mentions)} menciones de entidades")

            # Procesar en lotes
            total_chars = len(character_entities)
            all_extracted_attrs = []
            batch_size = 10

            for batch_start in range(0, total_chars, batch_size):
                # Ceder turno al chat interactivo si hay uno esperando
                try:
                    from narrative_assistant.llm.client import get_llm_scheduler
                    get_llm_scheduler().yield_to_chat()
                except Exception:
                    pass

                batch_end = min(batch_start + batch_size, total_chars)
                batch_chars = character_entities[batch_start:batch_end]

                batch_names = [e.canonical_name for e in batch_chars if e.canonical_name][:3]
                if len(batch_chars) > 3:
                    names_str = ", ".join(batch_names) + "..."
                else:
                    names_str = ", ".join(batch_names)

                _update_storage(
                    project_id,
                    current_action=f"Analizando: {names_str} ({batch_end}/{total_chars})",
                )

                batch_progress = 0.1 + (0.35 * batch_end / max(total_chars, 1))
                _update_storage(
                    project_id,
                    progress=attr_pct_start + int((attr_pct_end - attr_pct_start) * batch_progress),
                )

                batch_entity_names = {
                    e.canonical_name.lower() for e in batch_chars if e.canonical_name
                }
                batch_mentions = [
                    (name, start, end)
                    for name, start, end in entity_mentions
                    if name and name.lower() in batch_entity_names
                ]

                if batch_mentions:
                    try:
                        batch_result = attr_extractor.extract_attributes(
                            full_text,
                            batch_mentions,
                            None,
                        )
                        if batch_result.is_success and batch_result.value:
                            all_extracted_attrs.extend(batch_result.value.attributes)
                    except Exception as e:
                        logger.warning(f"Error extrayendo atributos para {names_str}: {e}")

                tracker.check_cancelled()

            # Resultado combinado
            from narrative_assistant.nlp.attributes import AttributeExtractionResult

            attr_result = Result.success(AttributeExtractionResult(attributes=all_extracted_attrs))
            logger.info(f"Atributos extraídos: {len(all_extracted_attrs)}")

            _update_storage(
                project_id,
                progress=attr_pct_start + int((attr_pct_end - attr_pct_start) * 0.5),
                current_action="Registrando características encontradas...",
            )

            if attr_result.is_success and attr_result.value:
                extracted_attrs = attr_result.value.attributes

                # Asignar capítulo a cada atributo
                if chapters_data:

                    def find_chapter_number_for_position(char_pos: int) -> int | None:
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

                    logger.info(
                        f"Asignados capítulos a {attrs_with_chapter}/"
                        f"{len(extracted_attrs)} atributos"
                    )

                # Resolver con correferencias
                if coref_result and coref_result.chains:
                    try:
                        from narrative_assistant.nlp.attributes import (
                            resolve_attributes_with_coreferences,
                        )

                        pronouns = {
                            "él",
                            "ella",
                            "ellos",
                            "ellas",
                            "su",
                            "sus",
                            "este",
                            "esta",
                            "ese",
                            "esa",
                        }
                        pronoun_attrs_before = sum(
                            1
                            for a in extracted_attrs
                            if a.entity_name and a.entity_name.lower() in pronouns
                        )

                        resolved_attrs = resolve_attributes_with_coreferences(
                            attributes=extracted_attrs,
                            coref_chains=coref_result.chains,
                            text=full_text,
                        )

                        pronoun_attrs_after = sum(
                            1
                            for a in resolved_attrs
                            if a.entity_name and a.entity_name.lower() in pronouns
                        )

                        resolved_count = pronoun_attrs_before - pronoun_attrs_after
                        if resolved_count > 0:
                            logger.info(
                                f"Correferencia de atributos: {resolved_count} atributos "
                                f"de pronombres resueltos a entidades "
                                f"({pronoun_attrs_before} → {pronoun_attrs_after} sin resolver)"
                            )
                        elif pronoun_attrs_before > 0:
                            logger.warning(
                                f"Correferencia de atributos: {pronoun_attrs_before} "
                                f"atributos con pronombres no pudieron resolverse"
                            )

                        extracted_attrs = resolved_attrs
                    except Exception as e:
                        logger.warning(
                            f"Error resolviendo atributos con correferencias: {e}",
                            exc_info=True,
                        )
                else:
                    logger.info(
                        "Sin cadenas de correferencia - atributos de pronombres no se resolverán"
                    )

                # Persistir atributos
                total_attrs = len(extracted_attrs)
                attrs_processed = 0
                for attr in extracted_attrs:
                    if not attr.entity_name:
                        continue

                    # Buscar entidad: primero match exacto, luego parcial (primer nombre)
                    attr_name_lower = attr.entity_name.lower()
                    matching_entity = next(
                        (
                            e
                            for e in character_entities
                            if e.canonical_name
                            and e.canonical_name.lower() == attr_name_lower
                        ),
                        None,
                    )
                    if not matching_entity:
                        # Fallback: match por primer nombre (LLM suele devolver "María"
                        # cuando el canónico es "María Sánchez")
                        matching_entity = next(
                            (
                                e
                                for e in character_entities
                                if e.canonical_name
                                and (
                                    e.canonical_name.lower().startswith(attr_name_lower + " ")
                                    or e.canonical_name.lower().split()[0] == attr_name_lower
                                )
                            ),
                            None,
                        )
                    if matching_entity:
                        try:
                            attr_key = (
                                attr.key.value if hasattr(attr.key, "value") else str(attr.key)
                            )
                            attr_type = (
                                attr.category.value
                                if hasattr(attr.category, "value")
                                else "physical"
                            )

                            entity_repo.create_attribute(
                                entity_id=matching_entity.id,
                                attribute_type=attr_type,
                                attribute_key=attr_key,
                                attribute_value=attr.value,
                                confidence=attr.confidence,
                                chapter_id=getattr(attr, "chapter_id", None),
                            )
                            attributes.append(attr)
                        except Exception as e:
                            logger.warning(
                                f"Error creating attribute for "
                                f"{matching_entity.canonical_name}: {e}"
                            )

                    attrs_processed += 1
                    if attrs_processed % 10 == 0 or attrs_processed == total_attrs:
                        save_progress = 0.6 + (0.35 * attrs_processed / max(total_attrs, 1))
                        _update_storage(
                            project_id,
                            progress=attr_pct_start
                            + int((attr_pct_end - attr_pct_start) * save_progress),
                            current_action=(
                                f"Guardando características... ({attrs_processed}/{total_attrs})"
                            ),
                        )

    # SP-1: Restaurar is_verified en atributos que el usuario verificó antes
    _restore_verified_attributes(ctx)

    tracker.end_phase("attributes", 5)
    _update_storage(project_id, metrics_update={"attributes_extracted": len(attributes)})
    logger.info(f"Attribute extraction complete: {len(attributes)} attributes")

    ctx["attributes"] = attributes


# ============================================================================
# Phase 6: Consistency (+ vital status, locations, OOC, anachronisms, classical)
# ============================================================================


def run_consistency(ctx: dict, tracker: ProgressTracker):
    """Fase 6: Verificación de consistencia y sub-análisis."""
    from narrative_assistant.analysis.attribute_consistency import AttributeConsistencyChecker

    project_id = ctx["project_id"]
    full_text = ctx["full_text"]
    chapters_data = ctx["chapters_data"]
    entities = ctx["entities"]
    attributes = ctx["attributes"]
    analysis_config = ctx["analysis_config"]

    tracker.start_phase("consistency", 6, "Verificando la coherencia del relato...")

    cons_pct_start, cons_pct_end = tracker.get_phase_progress_range("consistency")

    # Consistencia de atributos
    inconsistencies = []
    if attributes:
        checker = AttributeConsistencyChecker()
        check_result = checker.check_consistency(attributes)
        if check_result.is_success:
            inconsistencies = check_result.value or []

    # Sub-fase 5.1: Estado vital
    vital_status_report = None
    location_report = None
    chapter_progress_report = None

    _update_storage(project_id, current_action="Verificando estado vital de personajes...")

    # Preparar datos para sub-fases
    chapters_for_analysis = [
        {
            "number": ch["chapter_number"],
            "content": ch["content"],
            "text": ch["content"],
            "start_char": ch["start_char"],
        }
        for ch in chapters_data
    ]

    entities_for_analysis = [
        {
            "id": e.id,
            "canonical_name": e.canonical_name,
            "entity_type": (
                e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type)
            ),
            "aliases": e.aliases if hasattr(e, "aliases") else [],
        }
        for e in entities
    ]

    # BK-08: Construir TemporalMap para narrativas no lineales
    temporal_map = None
    try:
        from narrative_assistant.temporal.temporal_map import TemporalMap

        timeline = ctx.get("timeline")
        if timeline is not None:
            temporal_map = TemporalMap.from_timeline(timeline)
            logger.info(f"Built TemporalMap with {len(temporal_map._slices)} slices")
    except Exception as e:
        logger.warning(f"Failed to build TemporalMap: {e}. Falling back to chapter comparison.")

    try:
        from narrative_assistant.analysis.vital_status import analyze_vital_status

        vital_result = analyze_vital_status(
            project_id=project_id,
            chapters=chapters_for_analysis,
            entities=entities_for_analysis,
            temporal_map=temporal_map,
        )

        if vital_result.is_success:
            vital_status_report = vital_result.value
            logger.info(
                f"Vital status analysis: {len(vital_status_report.death_events)} deaths, "  # type: ignore[union-attr]
                f"{len(vital_status_report.post_mortem_appearances)} post-mortem appearances"  # type: ignore[union-attr]
            )

            # S8a-03: Persist vital status events to DB
            try:
                db = ctx["db_session"]
                with db.connection() as conn:
                    # Limpiar eventos anteriores
                    conn.execute(
                        "DELETE FROM vital_status_events WHERE project_id = ?",
                        (project_id,),
                    )
                    # Insertar death events
                    for de in vital_status_report.death_events:  # type: ignore[union-attr]
                        conn.execute(
                            """INSERT INTO vital_status_events
                            (project_id, entity_id, entity_name, event_type,
                             chapter, start_char, end_char, excerpt,
                             confidence, death_type)
                            VALUES (?, ?, ?, 'death', ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                de.entity_id,
                                de.entity_name,
                                de.chapter,
                                de.start_char,
                                de.end_char,
                                de.excerpt,
                                de.confidence,
                                de.death_type,
                            ),
                        )
                    # Insertar post-mortem appearances
                    for pm in vital_status_report.post_mortem_appearances:  # type: ignore[union-attr]
                        conn.execute(
                            """INSERT INTO vital_status_events
                            (project_id, entity_id, entity_name, event_type,
                             chapter, start_char, end_char, excerpt,
                             confidence, death_chapter, appearance_type, is_valid)
                            VALUES (?, ?, ?, 'post_mortem_appearance', ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                pm.entity_id,
                                pm.entity_name,
                                pm.appearance_chapter,
                                pm.appearance_start_char,
                                pm.appearance_end_char,
                                pm.appearance_excerpt,
                                pm.confidence,
                                pm.death_chapter,
                                pm.appearance_type,
                                1 if pm.is_valid else 0,
                            ),
                        )
                persisted = len(vital_status_report.death_events) + len(  # type: ignore[union-attr]
                    vital_status_report.post_mortem_appearances  # type: ignore[union-attr]
                )
                logger.info(f"Persisted {persisted} vital status events to DB")
            except Exception as persist_err:
                logger.warning(f"Error persisting vital status (continuing): {persist_err}")

        else:
            logger.warning(f"Vital status analysis failed: {vital_result.error}")

    except ImportError as e:
        logger.warning(f"Vital status module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in vital status analysis: {e}", exc_info=True)

    tracker.check_cancelled()

    # Sub-fase 5.2: Ubicaciones
    _update_storage(project_id, current_action="Verificando ubicaciones de personajes...")

    try:
        from narrative_assistant.analysis.character_location import (
            analyze_character_locations,
        )

        location_result = analyze_character_locations(
            project_id=project_id,
            chapters=chapters_for_analysis,
            entities=entities_for_analysis,
        )

        if location_result.is_success:
            location_report = location_result.value
            inconsistency_count = (
                len(location_report.inconsistencies)  # type: ignore[union-attr]
                if hasattr(location_report, "inconsistencies")
                else 0
            )
            logger.info(
                f"Character location analysis: {len(location_report.location_events)} events, "  # type: ignore[union-attr]
                f"{inconsistency_count} inconsistencies"
            )

            # S8a-04: Persist character location events to DB
            try:
                db = ctx["db_session"]
                with db.connection() as conn:
                    conn.execute(
                        "DELETE FROM character_location_events WHERE project_id = ?",
                        (project_id,),
                    )
                    for le in location_report.location_events:  # type: ignore[union-attr]
                        conn.execute(
                            """INSERT INTO character_location_events
                            (project_id, entity_id, entity_name, location_name,
                             chapter, start_char, end_char, excerpt,
                             change_type, confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                project_id,
                                le.entity_id,
                                le.entity_name,
                                le.location_name,
                                le.chapter,
                                le.start_char,
                                le.end_char,
                                le.excerpt,
                                le.change_type.value
                                if hasattr(le.change_type, "value")
                                else str(le.change_type),
                                le.confidence,
                            ),
                        )
                logger.info(
                    f"Persisted {len(location_report.location_events)} "  # type: ignore[union-attr]
                    f"character location events to DB"
                )
            except Exception as persist_err:
                logger.warning(f"Error persisting character locations (continuing): {persist_err}")

        else:
            logger.warning(f"Character location analysis failed: {location_result.error}")

    except ImportError as e:
        logger.warning(f"Character location module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in character location analysis: {e}", exc_info=True)

    tracker.check_cancelled()

    # Sub-fase 5.3: Resumen por capítulo
    _update_storage(project_id, current_action="Generando resumen de avance narrativo...")

    try:
        from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress

        chapter_progress_report = analyze_chapter_progress(
            project_id=project_id,
            db_path=None,
            mode="basic",
        )

        if chapter_progress_report:
            logger.info(
                f"Chapter progress analysis: "
                f"{len(chapter_progress_report.chapters)} chapters analyzed"
            )

    except ImportError as e:
        logger.warning(f"Chapter summary module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in chapter progress analysis: {e}", exc_info=True)

    tracker.check_cancelled()

    # Sub-fase 5.4: Out-of-character
    ooc_report = None
    if analysis_config.run_ooc_detection:
        _update_storage(
            project_id,
            current_action="Detectando comportamiento fuera de personaje...",
        )
        try:
            from narrative_assistant.analysis.character_profiling import CharacterProfiler
            from narrative_assistant.analysis.out_of_character import OutOfCharacterDetector

            profiler = CharacterProfiler()
            character_entities = [
                e
                for e in entities
                if (
                    hasattr(e.entity_type, "value")
                    and e.entity_type.value in ("character", "PER", "PERSON")
                )
                or (
                    isinstance(e.entity_type, str)
                    and e.entity_type in ("character", "PER", "PERSON")
                )
            ]
            if character_entities:
                chapter_texts = {ch["chapter_number"]: ch["content"] for ch in chapters_data}
                profiles = profiler.build_profiles(character_entities, chapters_data, chapter_texts)  # type: ignore[arg-type]
                if profiles:
                    ooc_detector = OutOfCharacterDetector()
                    ooc_report = ooc_detector.detect(
                        profiles=profiles,
                        chapter_texts=chapter_texts,
                    )
                    logger.info(f"OOC detection: {len(ooc_report.events)} events found")

                    # S8a-05: Persist OOC events to DB
                    try:
                        db = ctx["db_session"]
                        with db.connection() as conn:
                            conn.execute(
                                "DELETE FROM ooc_events WHERE project_id = ?",
                                (project_id,),
                            )
                            for ev in ooc_report.events:
                                conn.execute(
                                    """INSERT INTO ooc_events
                                    (project_id, entity_id, entity_name,
                                     deviation_type, severity, description,
                                     expected, actual, chapter, excerpt,
                                     confidence, is_intentional)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                    (
                                        project_id,
                                        ev.entity_id,
                                        ev.entity_name,
                                        ev.deviation_type.value
                                        if hasattr(ev.deviation_type, "value")
                                        else str(ev.deviation_type),
                                        ev.severity.value
                                        if hasattr(ev.severity, "value")
                                        else str(ev.severity),
                                        ev.description,
                                        ev.expected,
                                        ev.actual,
                                        ev.chapter,
                                        ev.excerpt,
                                        ev.confidence,
                                        1 if ev.is_intentional else 0,
                                    ),
                                )
                        logger.info(f"Persisted {len(ooc_report.events)} OOC events to DB")
                    except Exception as persist_err:
                        logger.warning(f"Error persisting OOC events (continuing): {persist_err}")

        except ImportError as e:
            logger.warning(f"OOC detection module not available: {e}")
        except Exception as e:
            logger.warning(f"Error in OOC detection: {e}", exc_info=True)

        tracker.check_cancelled()

    # Sub-fase 5.5: Anacronismos
    anachronism_report = None
    if analysis_config.run_anachronism_detection:
        _update_storage(project_id, current_action="Detectando anacronismos...")
        try:
            from narrative_assistant.temporal.anachronisms import AnachronismDetector

            anach_detector = AnachronismDetector()
            anachronism_report = anach_detector.detect(full_text)
            if anachronism_report and anachronism_report.anachronisms:
                logger.info(
                    f"Anachronism detection: "
                    f"{len(anachronism_report.anachronisms)} anachronisms found"
                )
            else:
                logger.info(
                    "Anachronism detection: no anachronisms found (period may not be detected)"
                )
        except ImportError as e:
            logger.warning(f"Anachronism detection module not available: {e}")
        except Exception as e:
            logger.warning(f"Error in anachronism detection: {e}", exc_info=True)

        tracker.check_cancelled()

    # Sub-fase 5.6: Español clásico
    classical_normalization = None
    if analysis_config.run_classical_spanish:
        _update_storage(project_id, current_action="Detectando español clásico...")
        try:
            from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

            normalizer = ClassicalSpanishNormalizer()
            period = normalizer.detect_period(full_text)
            if period != "modern":
                classical_normalization = normalizer.normalize(full_text)
                logger.info(
                    f"Classical Spanish: period={period}, "
                    f"{len(classical_normalization.replacements)} normalizations"
                )
            else:
                logger.debug("Classical Spanish: modern text, skipping normalization")
        except ImportError as e:
            logger.warning(f"Classical Spanish module not available: {e}")
        except Exception as e:
            logger.warning(f"Error in classical Spanish detection: {e}", exc_info=True)

        tracker.check_cancelled()

    # Sub-fase 5.7: Speech consistency tracking (v0.10.14)
    speech_change_count = 0
    if analysis_config.run_speech_tracking:
        _update_storage(project_id, current_action="Analizando consistencia del habla...")
        try:
            from narrative_assistant.analysis.speech_tracking import (
                ContextualAnalyzer,
                SpeechTracker,
            )
            from narrative_assistant.entities.models import EntityType

            tracker_speech = SpeechTracker(
                window_size=3,  # 3 capítulos por ventana
                overlap=1,  # Solapamiento de 1 capítulo
                min_words_per_window=200,  # Mínimo 200 palabras
                min_confidence=0.6,  # Confianza mínima 60%
            )

            context_analyzer = ContextualAnalyzer()

            # Filtrar solo personajes principales (>50 palabras de diálogo total)
            main_characters = []
            for entity in entities:
                if entity.entity_type not in (
                    EntityType.CHARACTER,
                    EntityType.ANIMAL,
                    EntityType.CREATURE,
                ):
                    continue

                # Estimar palabras totales de diálogo
                total_mentions = entity.mention_count or 0
                estimated_dialogue_words = total_mentions * 10  # ~10 palabras por mención

                if estimated_dialogue_words >= 50:
                    main_characters.append(entity)

            logger.info(
                f"Speech tracking: analyzing {len(main_characters)} main characters "
                f"(of {len(entities)} total)"
            )

            # Analizar cada personaje
            all_speech_alerts = []
            for entity in main_characters:
                try:
                    # Obtener spaCy NLP si está disponible
                    spacy_nlp = ctx.get("spacy_nlp")

                    # Obtener document fingerprint
                    # Obtener fingerprint del proyecto (campo de BD, NO de ctx)
                    _fp_project = ctx.get("project")
                    document_fingerprint = getattr(_fp_project, "document_fingerprint", "") if _fp_project else ""

                    speech_alerts = tracker_speech.detect_changes(
                        character_id=entity.id,
                        character_name=entity.canonical_name,
                        chapters=chapters_data,
                        spacy_nlp=spacy_nlp,
                        narrative_context_analyzer=context_analyzer,
                        document_fingerprint=document_fingerprint,
                    )

                    all_speech_alerts.extend(speech_alerts)

                    if speech_alerts:
                        logger.info(
                            f"Speech tracking: {entity.canonical_name} → "
                            f"{len(speech_alerts)} change(s) detected"
                        )

                except Exception as e:
                    logger.warning(f"Speech tracking failed for {entity.canonical_name}: {e}")
                    continue

            speech_change_count = len(all_speech_alerts)
            logger.info(
                f"Speech tracking: {speech_change_count} total changes detected "
                f"across {len(main_characters)} characters"
            )

            # Guardar alertas en contexto
            ctx["speech_change_alerts"] = all_speech_alerts

        except ImportError as e:
            logger.debug(f"Speech tracking module not available: {e}")
        except Exception as e:
            logger.warning(f"Speech consistency tracking failed: {e}", exc_info=True)

        tracker.check_cancelled()

    # Guardar métricas
    _update_storage(
        project_id,
        metrics_update={
            "vital_status_deaths": (
                len(vital_status_report.death_events) if vital_status_report else 0
            ),
            "location_events": (len(location_report.location_events) if location_report else 0),
            "ooc_events": len(ooc_report.events) if ooc_report else 0,
            "anachronisms_found": (
                len(anachronism_report.anachronisms)
                if anachronism_report and anachronism_report.anachronisms
                else 0
            ),
            "speech_changes": speech_change_count,
        },
    )

    tracker.end_phase("consistency", 6)
    _update_storage(project_id, metrics_update={"inconsistencies_found": len(inconsistencies)})
    logger.info(f"Consistency analysis complete: {len(inconsistencies)} inconsistencies")

    ctx["inconsistencies"] = inconsistencies
    ctx["vital_status_report"] = vital_status_report
    ctx["location_report"] = location_report
    ctx["chapter_progress_report"] = chapter_progress_report
    ctx["ooc_report"] = ooc_report
    ctx["anachronism_report"] = anachronism_report
    ctx["classical_normalization"] = classical_normalization


# ============================================================================
# Phase 6b: Event Detection & Persistence (silent — no UI phase)
# ============================================================================


def run_events(ctx: dict, tracker: ProgressTracker):
    """
    Detecta eventos narrativos y los persiste en narrative_events.

    Se ejecuta después de consistency. No tiene fase UI propia
    (es background work). Borra eventos previos y re-detecta.
    """
    from narrative_assistant.analysis.event_detection import detect_events_in_chapter
    from narrative_assistant.analysis.event_types import EVENT_TIER_MAP
    from narrative_assistant.persistence.event_repository import get_event_repository

    project_id = ctx["project_id"]
    chapters_data = ctx["chapters_data"]
    nlp = ctx.get("nlp")

    if not chapters_data:
        logger.info(f"run_events: no chapters for project {project_id}, skipping")
        return

    # Cargar spaCy si no está en contexto
    if nlp is None:
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model
        nlp = load_spacy_model()

    event_repo = get_event_repository()

    # Borrar eventos previos de este proyecto
    delete_result = event_repo.delete_by_project(project_id)
    if delete_result.is_success and delete_result.value:
        logger.info(f"run_events: deleted {delete_result.value} old events for project {project_id}")

    # Detectar eventos por capítulo
    all_events = []
    prev_chapter_text = None
    sorted_chapters = sorted(chapters_data, key=lambda c: c["chapter_number"])

    for ch in sorted_chapters:
        ch_num = ch["chapter_number"]
        content = ch["content"]

        detected = detect_events_in_chapter(
            text=content,
            chapter_number=ch_num,
            nlp=nlp,
            enable_llm=False,  # Sin LLM para no bloquear pipeline
            prev_chapter_text=prev_chapter_text,
        )

        for event in detected:
            tier = EVENT_TIER_MAP.get(event.event_type)
            all_events.append({
                "event_type": event.event_type.value,
                "tier": tier.value if tier else 1,
                "description": event.description,
                "chapter": ch_num,
                "start_char": event.start_char,
                "end_char": event.end_char,
                "entity_ids": event.entity_ids,
                "confidence": event.confidence,
                "metadata": event.metadata,
            })

        prev_chapter_text = content

    # Persistir en batch
    if all_events:
        save_result = event_repo.save_events(project_id, all_events)
        if save_result.is_success:
            logger.info(f"run_events: persisted {save_result.value} events for project {project_id}")
        else:
            logger.error(f"run_events: failed to save events: {save_result.error}")
    else:
        logger.info(f"run_events: no events detected for project {project_id}")


# ============================================================================
# Phase 7: Grammar
# ============================================================================


def run_grammar(ctx: dict, tracker: ProgressTracker):
    """Fase 7: Análisis gramatical y correcciones editoriales."""
    project_id = ctx["project_id"]
    full_text = ctx["full_text"]
    project = ctx["project"]

    tracker.start_phase("grammar", 7, "Revisando la redacción...")

    grammar_issues = []
    spelling_issues = []
    try:
        from narrative_assistant.nlp.grammar import (
            ensure_languagetool_running,
            get_grammar_checker,
            is_languagetool_installed,
        )

        if is_languagetool_installed():
            lt_started = ensure_languagetool_running()
            if lt_started:
                logger.info("LanguageTool server started successfully")

        grammar_checker = get_grammar_checker()

        if not grammar_checker.languagetool_available:
            grammar_checker.reload_languagetool()
            if grammar_checker.languagetool_available:
                logger.info("LanguageTool now available after reload")

        grammar_result = grammar_checker.check(full_text)

        if grammar_result.is_success:
            grammar_report = grammar_result.value
            grammar_issues = grammar_report.issues  # type: ignore[union-attr]
            logger.info(f"Grammar check found {len(grammar_issues)} issues")
        else:
            logger.warning(f"Grammar check failed: {grammar_result.error}")

    except ImportError as e:
        logger.warning(f"Grammar module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in grammar analysis: {e}")

    # Correcciones editoriales
    correction_issues = []
    try:
        _update_storage(project_id, current_phase="Buscando repeticiones y errores tipográficos...")

        from narrative_assistant.corrections import CorrectionConfig
        from narrative_assistant.corrections.orchestrator import CorrectionOrchestrator

        correction_config = CorrectionConfig.default()
        try:
            project_settings = project.settings or {}
            # New system: correction_customizations (CorrectionConfigModal)
            # Legacy: correction_config (old presets)
            cc = project_settings.get("correction_customizations") or project_settings.get("correction_config", {})
            dialog_cfg = cc.get("dialog", {})
            dash_val = dialog_cfg.get("spoken_dialogue_dash", "")
            dash_map = {"em_dash": "em", "en_dash": "en", "hyphen": "hyphen"}
            if dash_val in dash_map:
                correction_config.typography.dialogue_dash = dash_map[dash_val]  # type: ignore[assignment]
            quote_val = dialog_cfg.get("nested_dialogue_quote", "")
            quote_map = {"angular": "angular", "double": "curly", "single": "straight"}
            if quote_val in quote_map:
                correction_config.typography.quote_style = quote_map[quote_val]  # type: ignore[assignment]
            logger.info(f"Correction config loaded: dialogue_dash={correction_config.typography.dialogue_dash}, quote_style={correction_config.typography.quote_style}")
        except Exception as cfg_err:
            logger.debug(f"Could not load project correction config: {cfg_err}")

        # Activar style_register según tipo de documento clasificado
        # ctx["document_type"] es código corto (FIC, MEM, etc.)
        _STYLE_REGISTER_PROFILES = {
            "TEC": ("strict", True),
            "ENS": ("formal", True),
            "DIV": ("strict", True),
            "MEM": ("moderate", True),
            "AUT": ("moderate", True),
            "BIO": ("moderate", True),
            "CEL": ("moderate", True),
            "PRA": ("moderate", True),
            "FIC": ("free", False),
            "DRA": ("free", False),
            "INF": ("free", False),
            "GRA": ("free", False),
        }
        doc_type_code = ctx.get("document_type", "FIC")
        profile, enabled = _STYLE_REGISTER_PROFILES.get(doc_type_code, ("moderate", False))
        from narrative_assistant.corrections.config import (
            AcronymConfig,
            CoherenceConfig,
            ReferencesConfig,
            StructureConfig,
            StyleRegisterConfig,
        )
        correction_config.style_register = StyleRegisterConfig(enabled=enabled, profile=profile)

        # Activar detectores científicos/académicos según tipo de documento
        _SCIENTIFIC_DETECTORS: dict[str, tuple[str, bool]] = {
            # (structure_profile, coherence_use_llm)
            "TEC": ("scientific", True),
            "ENS": ("essay", True),
            "DIV": ("essay", False),  # Sin LLM para divulgación
        }
        sci_config = _SCIENTIFIC_DETECTORS.get(doc_type_code)
        if sci_config:
            structure_profile, coherence_use_llm = sci_config
            correction_config.references = ReferencesConfig(enabled=True)
            correction_config.acronyms = AcronymConfig(enabled=True)
            correction_config.structure = StructureConfig(
                enabled=True, profile=structure_profile
            )
            correction_config.coherence = CoherenceConfig(
                enabled=True, use_llm=coherence_use_llm
            )

        orchestrator = CorrectionOrchestrator(config=correction_config)

        correction_issues = orchestrator.analyze(
            text=full_text,
            chapter_index=None,
            spacy_doc=ctx.get("spacy_doc"),
        )

        logger.info(f"Corrections analysis found {len(correction_issues)} suggestions")

    except ImportError as e:
        logger.warning(f"Corrections module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in corrections analysis: {e}")

    tracker.end_phase("grammar", 7)
    _update_storage(
        project_id,
        metrics_update={
            "grammar_issues_found": len(grammar_issues),
            "correction_suggestions": len(correction_issues),
        },
    )
    logger.info(
        f"Grammar analysis complete: {len(grammar_issues)} grammar issues, "
        f"{len(correction_issues)} correction suggestions"
    )

    ctx["grammar_issues"] = grammar_issues
    ctx["spelling_issues"] = spelling_issues
    ctx["correction_issues"] = correction_issues


# ============================================================================
# Phase 8: Alerts
# ============================================================================


def _emit_grammar_alerts(ctx: dict, tracker: ProgressTracker):
    """Emite alertas de gramática y correcciones editoriales (parcial, tras run_grammar)."""
    from narrative_assistant.alerts.engine import get_alert_engine

    project_id = ctx["project_id"]
    grammar_issues = ctx.get("grammar_issues", [])
    correction_issues = ctx.get("correction_issues", [])

    alerts_created = 0
    alert_engine = get_alert_engine()

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
                    error_type=(
                        issue.error_type.value
                        if hasattr(issue.error_type, "value")
                        else str(issue.error_type)
                    ),
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                    explanation=issue.explanation,
                    rule_id=issue.rule_id if hasattr(issue, "rule_id") else "",
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating grammar alert: {e}")

    # Alertas de correcciones editoriales
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

    # No marcar fase aquí: run_alerts() gestiona el ciclo de la fase "alerts"
    _update_storage(project_id, metrics_update={"alerts_generated": alerts_created})
    logger.info(f"Grammar alerts emitted: {alerts_created} alerts")

    ctx.setdefault("alerts_created", 0)
    ctx["alerts_created"] += alerts_created
    ctx["_grammar_alerts_emitted"] = True


def _emit_consistency_alerts(ctx: dict, tracker: ProgressTracker):
    """Emite alertas de consistencia narrativa (tras run_consistency)."""
    from narrative_assistant.alerts.engine import AlertCategory, AlertSeverity, get_alert_engine

    project_id = ctx["project_id"]
    inconsistencies = ctx.get("inconsistencies", [])
    vital_status_report = ctx.get("vital_status_report")
    location_report = ctx.get("location_report")
    ooc_report = ctx.get("ooc_report")
    anachronism_report = ctx.get("anachronism_report")

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
                    attribute_key=(
                        inc.attribute_key.value
                        if hasattr(inc.attribute_key, "value")
                        else str(inc.attribute_key)
                    ),
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

    # Alertas de estado vital
    if vital_status_report and hasattr(vital_status_report, "post_mortem_appearances"):
        for appearance in vital_status_report.post_mortem_appearances:
            if appearance.is_valid:
                continue
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
    if location_report and hasattr(location_report, "inconsistencies"):
        for loc_inc in location_report.inconsistencies:
            try:
                alert_result = alert_engine.create_alert(
                    project_id=project_id,
                    category=AlertCategory.CONSISTENCY,
                    severity=AlertSeverity.WARNING,
                    alert_type="location_inconsistency",
                    title=f"Inconsistencia de ubicación: {loc_inc.entity_name}",
                    description=(
                        f"{loc_inc.entity_name} aparece en {loc_inc.location1_name} "
                        f"(cap {loc_inc.location1_chapter}) "
                        f"y en {loc_inc.location2_name} "
                        f"(cap {loc_inc.location2_chapter})"
                    ),
                    explanation=loc_inc.explanation,
                    confidence=loc_inc.confidence,
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating location inconsistency alert: {e}")

    # Alertas OOC
    if ooc_report and hasattr(ooc_report, "events"):
        for event in ooc_report.events:
            try:
                severity = (
                    AlertSeverity.WARNING if event.severity.value == "high" else AlertSeverity.INFO
                )
                alert_result = alert_engine.create_alert(
                    project_id=project_id,
                    category=AlertCategory.CONSISTENCY,
                    severity=severity,
                    alert_type="out_of_character",
                    title=f"Comportamiento atípico: {event.character_name}",
                    description=event.description,
                    explanation=event.explanation,
                    confidence=event.confidence,
                    chapter=(event.chapter_number if hasattr(event, "chapter_number") else None),
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating OOC alert: {e}")

    # Alertas de anacronismos
    if anachronism_report and anachronism_report.anachronisms:
        for anach in anachronism_report.anachronisms:
            try:
                alert_result = alert_engine.create_alert(
                    project_id=project_id,
                    category=AlertCategory.TIMELINE_ISSUE,
                    severity=AlertSeverity.WARNING,
                    alert_type="anachronism",
                    title=f"Posible anacronismo: {anach.term}",
                    description=(
                        f"'{anach.term}' aparece en un contexto temporal donde no existía "
                        f"({anach.expected_period})"
                    ),
                    explanation=anach.explanation,
                    confidence=anach.confidence,
                )
                if alert_result.is_success:
                    alerts_created += 1
            except Exception as e:
                logger.warning(f"Error creating anachronism alert: {e}")

    # No marcar fase aquí: run_alerts() gestiona el ciclo de la fase "alerts"

    ctx.setdefault("alerts_created", 0)
    ctx["alerts_created"] += alerts_created
    ctx["_consistency_alerts_emitted"] = True
    logger.info(f"Consistency alerts emitted: {alerts_created} alerts")


def run_alerts(ctx: dict, tracker: ProgressTracker):
    """Fase 8: Finaliza emisión de alertas y aplica reglas post-procesamiento."""
    project_id = ctx["project_id"]

    tracker.start_phase("alerts", 8, "Finalizando alertas...")

    # Emitir alertas de gramática si no se emitieron antes (ejecución secuencial legacy)
    if not ctx.get("_grammar_alerts_emitted"):
        _emit_grammar_alerts(ctx, tracker)

    # Emitir alertas de consistencia si no se emitieron antes
    if not ctx.get("_consistency_alerts_emitted"):
        _emit_consistency_alerts(ctx, tracker)

    tracker.end_phase("alerts", 8)
    total = ctx.get("alerts_created", 0)
    _update_storage(project_id, metrics_update={"alerts_generated": total})
    logger.info(f"Alerts phase complete: {total} total alerts")

    # SP-1: Auto-descartar alertas que el usuario ya había descartado
    _apply_saved_dismissals(project_id)


def _restore_verified_attributes(ctx: dict):
    """
    SP-1: Restaura is_verified=1 en atributos que el usuario había verificado.

    Busca en los atributos recién creados aquellos que coinciden con los
    que el usuario verificó en el análisis anterior (guardados en ctx por run_cleanup).
    """
    verified_attrs = ctx.get("_sp1_verified_attrs")
    if not verified_attrs:
        return

    project_id = ctx["project_id"]
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        restored = 0

        for va in verified_attrs:
            entity_name = va["entity_name"]
            attr_key = va["attribute_key"]
            attr_value = va["attribute_value"]

            with db.connection() as conn:
                # Buscar el atributo recién creado que coincida
                row = conn.execute(
                    "SELECT ea.id FROM entity_attributes ea "
                    "JOIN entities e ON ea.entity_id = e.id "
                    "WHERE e.project_id = ? AND e.canonical_name = ? "
                    "AND ea.attribute_key = ? AND ea.attribute_value = ? "
                    "AND ea.is_verified = 0 "
                    "LIMIT 1",
                    (project_id, entity_name, attr_key, attr_value),
                ).fetchone()

            if row:
                with db.transaction() as conn:
                    conn.execute(
                        "UPDATE entity_attributes SET is_verified = 1 WHERE id = ?",
                        (row["id"],),
                    )
                restored += 1

        if restored > 0:
            logger.info(
                f"SP-1: Restored is_verified on {restored}/{len(verified_attrs)} attributes"
            )

    except Exception as e:
        logger.warning(f"SP-1: Error restoring verified attributes: {e}")


def _reapply_user_merges(project_id: int, entity_repo, entities: list):
    """
    SP-1: Re-aplica fusiones de usuario preservadas en review_history.

    Después de NER + fusión automática, verifica si hay merges de usuario
    previos (action_type='entity_merged') que la fusión automática no descubrió.
    Si ambas entidades existen con sus canonical_names originales, las fusiona.
    """
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        with db.connection() as conn:
            rows = conn.execute(
                "SELECT old_value_json, new_value_json, note FROM review_history "
                "WHERE project_id = ? AND action_type = 'entity_merged' "
                "ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()

        if not rows:
            return

        # Construir índice de entidades actuales por nombre
        entities_by_name = {}
        for ent in entities:
            if ent.canonical_name:
                entities_by_name[ent.canonical_name.lower()] = ent

        reapplied = 0
        for row in rows:
            try:
                # SP-1: Saltar fusiones deshechas por el usuario
                note = row["note"] or ""
                if "[UNDONE" in note:
                    logger.debug(f"SP-1: Skipping undone merge: {note}")
                    continue

                old_data = json.loads(row["old_value_json"])
                names_before = old_data.get("canonical_names_before", [])

                if len(names_before) < 2:
                    continue

                # Buscar si las entidades que fueron fusionadas antes existen ahora
                # como entidades separadas (la fusión automática no las unió)
                primary_name = names_before[0].lower()
                primary = entities_by_name.get(primary_name)

                for secondary_name_raw in names_before[1:]:
                    secondary_name = secondary_name_raw.lower()
                    secondary = entities_by_name.get(secondary_name)

                    if not primary or not secondary or primary.id == secondary.id:
                        continue

                    # Verificar que la fusión automática no las unió ya
                    if secondary.canonical_name in (primary.aliases or []):
                        continue

                    # Re-aplicar el merge
                    if primary.aliases is None:
                        primary.aliases = []
                    if secondary.canonical_name not in primary.aliases:
                        primary.aliases.append(secondary.canonical_name)

                    if primary.merged_from_ids is None:
                        primary.merged_from_ids = []
                    if secondary.id and secondary.id not in primary.merged_from_ids:
                        primary.merged_from_ids.append(secondary.id)

                    entity_repo.update_entity(
                        entity_id=primary.id,
                        aliases=primary.aliases,
                        merged_from_ids=primary.merged_from_ids,
                    )
                    entity_repo.move_mentions(secondary.id, primary.id)
                    entity_repo.delete_entity(secondary.id, hard_delete=False)

                    # Remover del índice
                    entities_by_name.pop(secondary_name, None)

                    logger.info(
                        f"SP-1: Re-applied user merge: '{secondary.canonical_name}' → "
                        f"'{primary.canonical_name}'"
                    )
                    reapplied += 1

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"SP-1: Skip malformed merge history entry: {e}")

        if reapplied > 0:
            logger.info(f"SP-1: Re-applied {reapplied} user merges from previous analysis")

    except Exception as e:
        logger.warning(f"SP-1: Error reapplying user merges: {e}")


def _apply_saved_dismissals(project_id: int):
    """Aplica dismissals y suppression rules guardados a alertas recién generadas."""
    try:
        from narrative_assistant.alerts.repository import get_alert_repository
        from narrative_assistant.persistence.dismissal_repository import get_dismissal_repository

        alert_repo = get_alert_repository()
        dismissal_repo = get_dismissal_repository()

        # 1. Aplicar dismissals por content_hash
        result = alert_repo.apply_dismissals(project_id)
        if result.is_success and result.value > 0:  # type: ignore[operator]
            logger.info(f"SP-1: Auto-dismissed {result.value} alerts from saved dismissals")

        # 2. Aplicar suppression rules
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        rules_result = dismissal_repo.get_suppression_rules(project_id, active_only=True)
        if rules_result.is_failure:
            return

        rules = rules_result.value
        if not rules:
            return

        # Obtener alertas activas y comprobar contra reglas
        suppressed_count = 0
        with db.connection() as conn:
            rows = conn.execute(
                "SELECT id, alert_type, source_module, content_hash FROM alerts "
                "WHERE project_id = ? AND status NOT IN ('dismissed', 'resolved', 'auto_resolved')",
                (project_id,),
            ).fetchall()

        for row in rows:
            if dismissal_repo.is_suppressed(
                project_id,
                alert_type=row["alert_type"] or "",
                source_module=row["source_module"] or "",
            ):
                with db.transaction() as conn:
                    conn.execute(
                        "UPDATE alerts SET status = 'dismissed', "
                        "resolution_note = 'Auto-suprimida por regla de supresión' "
                        "WHERE id = ?",
                        (row["id"],),
                    )
                suppressed_count += 1

        if suppressed_count > 0:
            logger.info(f"SP-1: Suppressed {suppressed_count} alerts from active rules")

    except Exception as e:
        logger.warning(f"SP-1: Error applying saved dismissals: {e}")


# ============================================================================
# Reconciliation + Completion
# ============================================================================


def run_reconciliation(ctx: dict, tracker: ProgressTracker):
    """Reconciliación final de contadores de menciones."""
    from narrative_assistant.entities.repository import get_entity_repository

    project_id = ctx["project_id"]

    try:
        entity_repo = get_entity_repository()
        reconciled_count = entity_repo.reconcile_all_mention_counts(project_id)
        logger.info(f"Reconciliación final: {reconciled_count} entidades sincronizadas")
    except Exception as recon_err:
        logger.warning(f"Error en reconciliación final de mention_count: {recon_err}")


def run_completion(ctx: dict, tracker: ProgressTracker):
    """Marca el análisis como completado y actualiza el proyecto."""
    from narrative_assistant.persistence.project import ProjectManager

    project_id = ctx["project_id"]
    project = ctx["project"]
    entities = ctx.get("entities", [])
    attributes = ctx.get("attributes", [])
    alerts_created = ctx.get("alerts_created", 0)
    word_count = ctx["word_count"]
    chapters_count = ctx["chapters_count"]
    start_time = ctx["start_time"]

    total_duration = round(time.time() - start_time, 1)

    # F-006: Atomic status transition — lock protects against cancel race
    with deps._progress_lock:
        storage = deps.analysis_progress_storage.get(project_id, {})
        storage["status"] = "completed"
        storage["current_phase"] = "Análisis completado"
        storage["estimated_seconds_remaining"] = 0
        storage.setdefault("metrics", {})["total_duration_seconds"] = total_duration
        metrics = storage.get("metrics", {})
        storage["stats"] = {
            "entities": metrics.get("entities_found", len(entities)),
            "alerts": metrics.get("alerts_generated", alerts_created),
            "chapters": metrics.get("chapters_found", chapters_count),
            "corrections": metrics.get("correction_suggestions", 0),
            "grammar": metrics.get("grammar_issues_found", 0),
            "attributes": metrics.get("attributes_extracted", len(attributes)),
            "words": metrics.get("word_count", word_count),
            "duration": total_duration,
        }

    project.analysis_status = "completed"
    project.analysis_progress = 1.0
    project.word_count = word_count
    project.chapter_count = chapters_count

    proj_manager = ProjectManager(ctx["db_session"])
    proj_manager.update(project)

    # Formatear duración en minutos si es > 60s
    duration_str = f"{total_duration}s"
    if total_duration >= 60:
        minutes = int(total_duration // 60)
        seconds = int(total_duration % 60)
        duration_str = f"{minutes}m {seconds}s ({total_duration}s)"

    logger.info("=" * 80)
    logger.info(f"✓ ANÁLISIS COMPLETADO - Proyecto {project_id}")
    logger.info(f"  Duración total: {duration_str}")
    logger.info(
        f"  Resultados: {word_count} palabras, {chapters_count} capítulos, "
        f"{len(entities)} entidades, {alerts_created} alertas"
    )
    logger.info("=" * 80)

    # Auto-sugerir focalizacion para capitulos sin declaracion
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        characters = [e for e in entities if getattr(e, "entity_type", None) in ("person", "PERSON", "PER", "CHARACTER") or (hasattr(e, "entity_type") and hasattr(e.entity_type, "value") and e.entity_type.value in ("person", "PERSON", "PER", "CHARACTER"))]

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        existing = service.get_all_declarations(project_id)
        declared_chapters = {d.chapter for d in existing}

        auto_count = 0
        for ch in chapters:
            if ch.chapter_number in declared_chapters:
                continue
            if not ch.content or len(ch.content.strip()) < 50:
                continue
            suggestion = service.suggest_focalization(
                project_id, ch.chapter_number, ch.content, characters
            )
            if suggestion["suggested_type"] and suggestion["confidence"] >= 0.65:
                service.declare_focalization(
                    project_id=project_id,
                    chapter=ch.chapter_number,
                    focalization_type=suggestion["suggested_type"],
                    focalizer_ids=suggestion.get("suggested_focalizers", []),
                    declared_by="system_suggestion",
                    notes=f"Auto-sugerido (confianza: {suggestion['confidence']:.0%})",
                )
                auto_count += 1

        if auto_count:
            logger.info(f"Focalization: auto-suggested {auto_count} chapter declarations")
    except Exception as foc_err:
        logger.warning(f"Error auto-suggesting focalization: {foc_err}")


# ============================================================================
# Error handling
# ============================================================================


def handle_analysis_error(ctx: dict, error: Exception):
    """Maneja errores durante el análisis."""
    from narrative_assistant.core.errors import ModelNotLoadedError
    from narrative_assistant.persistence.project import ProjectManager

    project_id = ctx["project_id"]
    project = ctx["project"]

    # Cancelación por el usuario: no es un error, es una acción intencional
    if isinstance(error, AnalysisCancelledError):
        logger.info(f"Analysis cancelled by user for project {project_id}")
        with deps._progress_lock:
            storage = deps.analysis_progress_storage.get(project_id, {})
            storage["status"] = "cancelled"
            storage["current_phase"] = "Análisis cancelado por el usuario"
            # Clear cancellation flag
            deps.analysis_cancellation_flags.pop(project_id, None)
        try:
            # Resetear a 'cancelled' en DB para que el frontend sepa que fue cancelado
            project.analysis_status = "cancelled"
            project.analysis_progress = 0.0
            proj_manager = ProjectManager(ctx["db_session"])
            proj_manager.update(project)
            logger.info(f"Project {project_id} status set to 'cancelled'")
        except Exception as db_error:
            logger.error(f"Failed to update project status after cancellation: {db_error}")
        return

    logger.exception(f"Error during analysis for project {project_id}: {error}")

    err_str = str(error)
    if (
        isinstance(error, ModelNotLoadedError)
        or "not loaded" in err_str.lower()
        or "not found" in err_str.lower()
    ):
        user_msg = (
            "Modelo de análisis no disponible. "
            "Reinicia la aplicación para que se descarguen los modelos necesarios."
        )
    else:
        user_msg = f"Error en el análisis: {err_str}"

    with deps._progress_lock:
        storage = deps.analysis_progress_storage.get(project_id, {})
        storage["status"] = "error"
        storage["current_phase"] = user_msg
        storage["error"] = user_msg

    try:
        project.analysis_status = "error"
        proj_manager = ProjectManager(ctx["db_session"])
        proj_manager.update(project)
    except Exception as db_error:
        logger.error(f"Failed to update project status to error: {db_error}")


# ============================================================================
# Finally block: cleanup + queue management
# ============================================================================


def _release_heavy_and_start_next(project_id: int, ctx: dict | None = None) -> None:
    """Release heavy slot and auto-start next queued project.

    Unified helper used by both release_heavy_slot and run_finally_cleanup
    to avoid duplicated slot-release + queue-pop logic.
    """
    next_heavy = None
    with deps._progress_lock:
        if deps._heavy_analysis_project_id == project_id:
            deps._heavy_analysis_project_id = None
            deps._heavy_analysis_claimed_at = None
            if ctx is not None:
                ctx["heavy_slot_released"] = True
            logger.info(f"Project {project_id}: released heavy slot")
        if deps._heavy_analysis_queue:
            next_heavy = deps._heavy_analysis_queue.pop(0)

    # Auto-start next queued project
    if next_heavy:
        from routers.analysis import _start_queued_analysis

        _start_queued_analysis(next_heavy)


def release_heavy_slot(ctx: dict):
    """S8a-15: Release heavy slot early so next project can start heavy phases.

    Called between Tier 2 (heavy NLP) and Tier 3 (enrichment).
    Enrichment is CPU-only and doesn't compete for GPU/LLM resources.
    """
    if ctx.get("heavy_slot_released"):
        return  # Already released
    _release_heavy_and_start_next(ctx["project_id"], ctx)


def run_finally_cleanup(ctx: dict):
    """Limpieza final: archivo temporal, slot pesado, cola."""
    project_id = ctx["project_id"]
    queued_for_heavy = ctx.get("queued_for_heavy", False)

    if queued_for_heavy:
        return

    # Limpiar archivo temporal
    tmp_path = ctx.get("tmp_path")
    use_temp_file = ctx.get("use_temp_file", False)
    if use_temp_file and tmp_path and tmp_path.exists():
        try:
            tmp_path.unlink()
        except Exception:
            pass

    # Liberar slot pesado y auto-start next (if not already released)
    if not ctx.get("heavy_slot_released"):
        _release_heavy_and_start_next(project_id, ctx)

    # Limpiar progreso después de delay
    def _cleanup_progress(pid: int):
        with deps._progress_lock:
            stored = deps.analysis_progress_storage.get(pid)
            if stored and stored.get("status") in ("completed", "error", "failed", "cancelled"):
                deps.analysis_progress_storage.pop(pid, None)

    cleanup_timer = threading.Timer(300, _cleanup_progress, args=[project_id])
    cleanup_timer.daemon = True
    cleanup_timer.start()
