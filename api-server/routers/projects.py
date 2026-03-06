"""
Router: projects
"""

from pathlib import Path
from typing import Any, Optional

import deps
from deps import ApiResponse, ProjectResponse, _get_project_stats, logger
from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from narrative_assistant.persistence.document_fingerprint import generate_fingerprint
from narrative_assistant.persistence.manuscript_identity import (
    IDENTITY_DIFFERENT_DOCUMENT,
    IDENTITY_UNCERTAIN,
    ManuscriptIdentityRepository,
    ManuscriptIdentityService,
)

router = APIRouter()


# ── Mapa de requisitos de servicio por método NLP (CR-03 post-MVP) ──────────
_METHOD_SERVICE_MAP: dict[tuple[str, str], str] = {
    # Métodos que requieren Ollama
    ("coreference", "llm"): "ollama",
    ("ner", "llm"): "ollama",
    ("grammar", "llm"): "ollama",
    ("spelling", "llm_arbitrator"): "ollama",
    ("character_knowledge", "llm"): "ollama",
    ("character_knowledge", "hybrid"): "ollama",
    # Métodos que requieren LanguageTool
    ("grammar", "languagetool"): "languagetool",
    ("spelling", "languagetool"): "languagetool",
    # Métodos que requieren GPU
    ("spelling", "beto"): "gpu",
}

# Mensajes de warning por servicio (reutilizables)
_SERVICE_WARNING_TEMPLATES: dict[str, str] = {
    "ollama": (
        "Método '{method}' en '{category}' requiere Ollama, "
        "que no está disponible actualmente. "
        "Se guardará la preferencia y se usará degradación automática."
    ),
    "languagetool": (
        "Método '{method}' en '{category}' requiere LanguageTool, "
        "que no está corriendo actualmente. "
        "Se guardará la preferencia y se usará degradación automática."
    ),
    "gpu": (
        "Método '{method}' en '{category}' requiere GPU, "
        "que no está disponible. "
        "Se guardará la preferencia pero el método se omitirá en el análisis."
    ),
}


def _get_lightweight_capabilities() -> dict:
    """Verificación rápida de servicios para warnings en PATCH settings.

    NO ejecuta detección de hardware costosa (CUDA init ~10s).
    Solo verifica servicios que pueden estar transitorialmente no disponibles:
    - Ollama: corriendo (HTTP check, timeout 1.5s)
    - LanguageTool: corriendo (HTTP check, timeout 1.5s)
    - GPU: valor cacheado de torch (sin re-init)

    Returns:
        dict con keys: ollama_available, languagetool_available, has_gpu
    """
    caps: dict[str, bool] = {
        "ollama_available": False,
        "languagetool_available": False,
        "has_gpu": False,
    }

    # Ollama check
    try:
        from narrative_assistant.llm.ollama_manager import is_ollama_available
        caps["ollama_available"] = is_ollama_available()
    except Exception:
        pass

    # LanguageTool check
    try:
        caps["languagetool_available"] = deps._check_languagetool_available()
    except Exception:
        pass

    # GPU check (cacheado por torch, no re-inicia CUDA)
    try:
        import torch
        caps["has_gpu"] = torch.cuda.is_available()
    except Exception:
        pass

    return caps


def _get_default_analysis_features() -> dict:
    """Defaults seguros para analysis_features (MVP CR-03).

    Devuelve configuración deseada por defecto:
    - pipeline_flags: 11 claves en true (preferencia activada)
    - nlp_methods: por categoría, métodos con default_enabled=true

    No consulta capabilities (lo hace el cliente en validación runtime).
    """
    return {
        "schema_version": 1,
        "pipeline_flags": {
            "character_profiling": True,
            "network_analysis": True,
            "anachronism_detection": True,
            "ooc_detection": True,
            "classical_spanish": True,
            "name_variants": True,
            "multi_model_voting": True,
            "spelling": True,
            "grammar": True,
            "consistency": True,
            "speech_tracking": True,
        },
        "nlp_methods": {
            # Defaults basados en lo más compatible
            "coreference": ["embeddings", "morpho", "heuristics"],
            "ner": ["spacy", "gazetteer"],
            "grammar": ["spacy_rules"],
            "spelling": ["patterns", "symspell", "hunspell", "pyspellchecker"],
            "character_knowledge": ["rules"],
        },
        "voting_thresholds": {
            "inferenceMinConfidence": 55,
            "inferenceMinConsensus": 60,
        },
        "updated_at": None,
        "updated_by": "default",
    }


def _validate_analysis_features(
    features: dict,
    capabilities: Optional[dict] = None,
    updated_by: str = "ui"
) -> tuple[dict, list[str]]:
    """Valida y sanea analysis_features contra schema conocido.

    Reglas MVP CR-03:
    - Eliminar keys desconocidas con warning
    - Toda no disponibilidad se trata como transitoria (no borrar de desired)
    - Degradación solo en ejecución, no en persistido

    Args:
        features: analysis_features enviado por cliente
        capabilities: dict de capabilities (opcional para validación básica)
        updated_by: fuente del cambio (ui | api | migration), default "ui"

    Returns:
        tuple (sanitized_features, warnings)

    Raises:
        ValueError: Si el payload tiene estructura inválida
    """
    warnings = []
    sanitized = {}

    # P1: Type guard - features debe ser dict
    if not isinstance(features, dict):
        raise ValueError(f"analysis_features debe ser un objeto, recibido: {type(features).__name__}")

    # Schema version
    schema_ver = features.get("schema_version", 1)
    if not isinstance(schema_ver, int):
        raise ValueError(f"schema_version debe ser número entero, recibido: {type(schema_ver).__name__}")
    sanitized["schema_version"] = schema_ver

    # Validar pipeline_flags
    known_flags = {
        "character_profiling", "network_analysis", "anachronism_detection",
        "ooc_detection", "classical_spanish", "name_variants",
        "multi_model_voting", "spelling", "grammar", "consistency",
        "speech_tracking"
    }

    pipeline_flags = features.get("pipeline_flags", {})
    # P1: Type guard - pipeline_flags debe ser dict
    if not isinstance(pipeline_flags, dict):
        raise ValueError(f"pipeline_flags debe ser un objeto, recibido: {type(pipeline_flags).__name__}")

    sanitized_flags = {}
    for key, value in pipeline_flags.items():
        if key not in known_flags:
            warnings.append(f"Flag '{key}' desconocido, se omitirá")
            continue
        # P1: Validación estricta de booleanos (no coerción permisiva)
        if not isinstance(value, bool):
            raise ValueError(f"Flag '{key}' debe ser booleano (true/false), recibido: {type(value).__name__}")
        sanitized_flags[key] = value

    sanitized["pipeline_flags"] = sanitized_flags

    # Validar nlp_methods
    known_categories = {"coreference", "ner", "grammar", "spelling", "character_knowledge"}
    # Métodos conocidos por categoría (schema MVP CR-03)
    known_methods = {
        "coreference": {"embeddings", "llm", "morpho", "heuristics"},
        "ner": {"spacy", "gazetteer", "llm"},
        "grammar": {"spacy_rules", "languagetool", "llm"},
        "spelling": {"patterns", "symspell", "hunspell", "pyspellchecker", "languagetool", "beto", "llm_arbitrator"},
        "character_knowledge": {"rules", "llm", "hybrid"}
    }

    nlp_methods = features.get("nlp_methods", {})
    # P1: Type guard - nlp_methods debe ser dict
    if not isinstance(nlp_methods, dict):
        raise ValueError(f"nlp_methods debe ser un objeto, recibido: {type(nlp_methods).__name__}")

    sanitized_methods = {}

    for category, methods in nlp_methods.items():
        if category not in known_categories:
            warnings.append(f"Categoría NLP '{category}' desconocida, se omitirá")
            continue

        if not isinstance(methods, list):
            warnings.append(f"Categoría '{category}' debe ser lista, se omitirá")
            continue

        # Validar métodos contra schema conocido
        valid_methods = []
        for method in methods:
            method_str = str(method)
            if method_str in known_methods.get(category, set()):
                valid_methods.append(method_str)
            else:
                warnings.append(f"Método '{method_str}' desconocido en categoría '{category}', se omitirá")

        sanitized_methods[category] = valid_methods

    sanitized["nlp_methods"] = sanitized_methods

    # Validar voting_thresholds (0-100)
    voting_thresholds = features.get("voting_thresholds")
    if voting_thresholds is not None:
        if not isinstance(voting_thresholds, dict):
            raise ValueError(
                f"voting_thresholds debe ser un objeto, recibido: {type(voting_thresholds).__name__}"
            )

        known_thresholds = {"inferenceMinConfidence", "inferenceMinConsensus"}
        sanitized_thresholds: dict[str, int | float] = {}

        for key, value in voting_thresholds.items():
            if key not in known_thresholds:
                warnings.append(f"Umbral '{key}' desconocido, se omitirá")
                continue
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Umbral '{key}' debe ser numérico (0-100), recibido: {type(value).__name__}"
                )
            numeric = float(value)
            if numeric < 0 or numeric > 100:
                raise ValueError(f"Umbral '{key}' fuera de rango (0-100): {numeric}")
            sanitized_thresholds[key] = numeric

        sanitized["voting_thresholds"] = sanitized_thresholds

    # Warnings de capabilities (CR-03 post-MVP)
    if capabilities:
        _caps_check = {
            "ollama": capabilities.get("ollama_available", False),
            "languagetool": capabilities.get("languagetool_available", False),
            "gpu": capabilities.get("has_gpu", False),
        }
        for (cat, method), service in _METHOD_SERVICE_MAP.items():
            if method in sanitized_methods.get(cat, []) and not _caps_check.get(service, False):
                template = _SERVICE_WARNING_TEMPLATES.get(service, "")
                if template:
                    warnings.append(template.format(method=method, category=cat))

    # Metadatos
    import datetime
    sanitized["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    sanitized["updated_by"] = updated_by

    return sanitized, warnings


def _get_license_subject() -> str:
    """Obtiene un identificador estable de licencia para controles de riesgo."""
    try:
        from routers.license import get_license_verifier

        verifier = get_license_verifier()
        if not verifier:
            return "no_license"
        result = verifier.verify()
        if result.is_failure or not result.value or not result.value.license:
            return "no_license"
        license_obj = result.value.license
        if getattr(license_obj, "id", None):
            return f"license:{license_obj.id}"
        if getattr(license_obj, "license_key", None):
            return f"license_key:{license_obj.license_key}"
    except Exception:
        pass
    return "no_license"


def _resolve_document_path(
    file_path: Optional[str],
    file: Optional[UploadFile],
    allowed_extensions: set[str],
) -> tuple[Path, bool]:
    """
    Resuelve y valida el path de documento.

    Returns:
        (path_resuelto, is_temp_upload)
    """
    import uuid

    if file_path:
        from narrative_assistant.parsers.sanitization import validate_file_path

        return (
            validate_file_path(
                Path(file_path),
                must_exist=True,
                allowed_extensions=allowed_extensions,
            ),
            False,
        )

    if file and file.filename:
        config = deps.get_config()
        documents_dir = config.data_dir / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        permanent_path = documents_dir / unique_filename
        max_upload_bytes = 50 * 1024 * 1024
        total = 0
        with open(permanent_path, "wb") as output:
            while chunk := file.file.read(8192):
                total += len(chunk)
                if total > max_upload_bytes:
                    permanent_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400, detail="El archivo supera el límite de 50 MB"
                    )
                output.write(chunk)
        return permanent_path, True

    raise HTTPException(status_code=400, detail="Se requiere file_path o file")


def _parse_document(path: Path) -> tuple[str, str]:
    """Parsea documento y devuelve (texto, formato_str)."""
    from narrative_assistant.parsers import get_parser
    from narrative_assistant.parsers.base import detect_format

    doc_format = detect_format(path)
    format_str = (
        doc_format.value if hasattr(doc_format, "value") else str(doc_format).split(".")[-1].upper()
    )
    parser = get_parser(path)
    parse_result = parser.parse(path)
    if parse_result.is_failure:
        raise HTTPException(
            status_code=400, detail=f"Error leyendo documento: {parse_result.error}"
        )
    raw_doc = parse_result.value
    text = raw_doc.full_text if raw_doc else ""
    if not text or not text.strip():
        raise HTTPException(
            status_code=400, detail="El documento está vacío o no se pudo leer el contenido"
        )
    return text, format_str


def _load_project_text_from_db(project_id: int) -> str:
    """Carga texto previo desde capítulos persistidos si el archivo original no se puede parsear."""
    try:
        db = deps.get_database()
        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT content
                FROM chapters
                WHERE project_id = ?
                ORDER BY chapter_number
                """,
                (project_id,),
            ).fetchall()
        parts = [str(r["content"] or "").strip() for r in rows if r["content"]]
        return "\n\n".join(p for p in parts if p)
    except Exception:
        return ""


@router.get("/api/projects", response_model=ApiResponse)
def list_projects():
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
            table_names = [t["name"] for t in tables]
            logger.debug(f"list_projects: db_path={db_path}, tables={table_names}")
            if "projects" not in table_names:
                logger.warning(
                    f"list_projects: 'projects' table missing! db_path={db_path}, tables_found={table_names}"
                )
                deps._write_debug(
                    f"list_projects: 'projects' MISSING! db_path={db_path}, tables={table_names}"
                )

                # Log file info for diagnostics
                try:
                    from pathlib import Path as _P  # noqa: N814

                    _db_file = _P(db_path)
                    if _db_file.exists():
                        deps._write_debug(
                            f"list_projects: DB file exists, size={_db_file.stat().st_size} bytes"
                        )
                        logger.warning(
                            f"list_projects: DB file exists at {db_path}, size={_db_file.stat().st_size} bytes"
                        )
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
                    _direct_tables = _direct.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                    _direct_names = [t[0] for t in _direct_tables]
                    deps._write_debug(f"list_projects: direct sqlite3 tables={_direct_names}")
                    logger.warning(
                        f"list_projects: direct sqlite3 connection tables={_direct_names}"
                    )
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
                    post_names = [t["name"] for t in post_tables]
                    deps._write_debug(f"list_projects: post-repair tables={post_names}")
                    logger.info(f"list_projects: Schema repaired, tables now: {post_names}")
                    if "projects" not in post_names:
                        logger.error(
                            "list_projects: Schema repair FAILED, still no 'projects' table"
                        )
                        deps._write_debug("list_projects: repair FAILED, still no 'projects'")
                        return ApiResponse(
                            success=False,
                            error="Database not initialized properly - 'projects' table missing",
                        )
                except Exception as repair_err:
                    logger.error(
                        f"list_projects: Schema repair failed: {repair_err}", exc_info=True
                    )
                    deps._write_debug(f"list_projects: Schema repair exception: {repair_err}")
                    return ApiResponse(
                        success=False,
                        error="Database not initialized properly - 'projects' table missing",
                    )
        except Exception as db_err:
            logger.error(f"list_projects: Error checking database: {db_err}", exc_info=True)
            deps._write_debug(f"list_projects: DB check exception: {db_err}")

        projects = deps.project_manager.list_all()
        db = deps.get_database()

        projects_data = []
        for p in projects:
            # Obtener estadísticas desde la BD (source of truth)
            stats = _get_project_stats(p.id, db)

            # Determinar severidad más alta de alertas (SQL directo)
            highest_severity = None
            try:
                sev_row = db.fetchone(
                    """SELECT severity FROM alerts
                       WHERE project_id = ? AND status = 'open'
                       ORDER BY CASE severity
                           WHEN 'critical' THEN 3 WHEN 'warning' THEN 2 ELSE 1
                       END DESC LIMIT 1""",
                    (p.id,),
                )
                if sev_row:
                    highest_severity = sev_row["severity"]
            except Exception:
                pass

            projects_data.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "document_path": p.document_path,
                    "document_format": p.document_format,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "last_modified": p.updated_at.isoformat() if p.updated_at else None,
                    "last_opened": p.last_opened_at.isoformat() if p.last_opened_at else None,
                    "analysis_status": p.analysis_status,
                    "analysis_progress": int(p.analysis_progress * 100)
                    if p.analysis_progress
                    else 0,
                    "word_count": stats["word_count"] or p.word_count,
                    "chapter_count": stats["chapter_count"],
                    "entity_count": stats["entity_count"],
                    "open_alerts_count": stats["open_alerts_count"],
                    "highest_alert_severity": highest_severity,
                }
            )

        return ApiResponse(success=True, data=projects_data)
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}", response_model=ApiResponse)
def get_project(project_id: int):
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

        # Verificar si el estado está atascado (no hay análisis real en progreso)
        # Esto puede ocurrir si:
        # - El servidor se reinició durante un análisis
        # - El análisis fue cancelado pero el estado no se limpió correctamente
        # - El análisis está en cola pero el proceso murió
        # NOTA: 'pending' NO se incluye aquí porque es el estado inicial legítimo
        # de un proyecto recién creado que aún no ha sido analizado.
        if project.analysis_status in ["analyzing", "in_progress", "queued", "cancelled"]:
            # Si no hay análisis activo en memoria, el estado está atascado
            with deps._progress_lock:
                has_active = project_id in deps.analysis_progress_storage
            if not has_active:
                logger.warning(
                    f"Project {project_id} has stuck analysis_status='{project.analysis_status}', resetting to 'pending'"
                )
                project.analysis_status = "pending"
                project.analysis_progress = 0.0
                try:
                    deps.project_manager.update(project)
                except Exception as e:
                    logger.warning(f"Could not update stuck analysis status: {e}")

        # Obtener estadísticas desde la BD (source of truth)
        db = deps.get_database()
        stats = _get_project_stats(project_id, db)

        # Obtener severidad más alta de alertas (SQL directo, sin cargar todas)
        highest_severity = None
        try:
            sev_row = db.fetchone(
                """SELECT severity FROM alerts
                   WHERE project_id = ? AND status = 'open'
                   ORDER BY CASE severity
                       WHEN 'critical' THEN 3 WHEN 'warning' THEN 2 ELSE 1
                   END DESC LIMIT 1""",
                (project_id,),
            )
            if sev_row:
                highest_severity = sev_row["severity"]
        except Exception:
            pass

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
                    from narrative_assistant.feature_profile.models import (
                        _TYPE_CODE_TO_LONG,
                        normalize_document_type,
                    )

                    code = normalize_document_type(dt_row[0])
                    document_type = _TYPE_CODE_TO_LONG.get(code, document_type)
        except Exception:
            pass  # Fallback al valor de settings

        document_classification = project_settings.get("document_classification", None)
        recommended_analysis = project_settings.get("recommended_analysis", None)

        # CR-03: analysis_features (devolver defaults si no existe)
        analysis_features = project_settings.get("analysis_features")
        if not analysis_features:
            analysis_features = _get_default_analysis_features()

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
            "analysis_progress": int(project.analysis_progress * 100)
            if project.analysis_progress
            else 0,
            "word_count": stats["word_count"] or project.word_count,
            "chapter_count": stats["chapter_count"],
            "entity_count": stats["entity_count"],
            "open_alerts_count": stats["open_alerts_count"],
            "highest_alert_severity": highest_severity,
            # Tipo de documento detectado y análisis recomendado
            "document_type": document_type,
            "document_classification": document_classification,
            "recommended_analysis": recommended_analysis,
            # CR-03: settings por proyecto
            "settings": {
                "analysis_features": analysis_features
            },
        }

        return ApiResponse(success=True, data=project_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/analysis-status", response_model=ApiResponse)
def get_analysis_status(project_id: int):
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

        db = deps.get_database()

        # Fuente primaria: run ledger (registro real de fases ejecutadas)
        ledger_phases: dict[str, bool] = {}
        try:
            from narrative_assistant.persistence.analysis import AnalysisRepository

            analysis_repo = AnalysisRepository(db)
            ledger_phases = analysis_repo.get_executed_phases(project_id)
        except Exception:
            pass

        # Mapeo de fases backend (run_*) → claves frontend para el endpoint
        _BACKEND_TO_FRONTEND: dict[str, list[str]] = {
            "parsing": ["parsing"],
            "structure": ["structure"],
            "classification": ["structure"],
            "ner": ["entities"],
            "llm_validation": ["entities"],
            "fusion": ["coreference"],
            "timeline": ["timeline", "temporal"],
            "attributes": ["attributes"],
            "consistency": ["coherence"],
            "grammar": ["grammar", "grammar_alerts", "spelling", "register"],
            "alerts": ["alerts"],
            "events": ["pacing"],
        }

        if ledger_phases:
            # Usar registro real: construir executed a partir del ledger
            executed: dict[str, bool] = {}
            for backend_phase, frontend_keys in _BACKEND_TO_FRONTEND.items():
                phase_ran = ledger_phases.get(backend_phase, False)
                for fk in frontend_keys:
                    if phase_ran:
                        executed[fk] = True
                    else:
                        executed.setdefault(fk, False)

            # Enrichment/derivados: verificar datos existentes en DB
            stats = _get_project_stats(project_id, db)
            has_entities = (stats.get("entity_count") or 0) > 0
            has_chapters = (stats.get("chapter_count") or 0) > 0

            # Claves que dependen de enrichment (no están en run ledger)
            if has_entities and has_chapters:
                for fk in [
                    "voice_profiles", "voice_deviations",
                    "narrative_health", "character_archetypes", "speaker_attribution",
                ]:
                    executed.setdefault(fk, True)
            if has_chapters:
                for fk in [
                    "tension_curve", "sensory_report", "sentence_energy",
                    "narrative_templates", "register_analysis",
                ]:
                    executed.setdefault(fk, True)
            if has_entities:
                executed.setdefault("story_bible", True)

            # Verificar relaciones desde DB
            with db.connection() as conn:
                try:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM relationships WHERE project_id = ?", (project_id,)
                    )
                    executed["relationships"] = cursor.fetchone()[0] > 0
                except Exception:
                    executed.setdefault("relationships", False)

            # Defaults para fases no implementadas
            for fk in ["interactions", "emotional", "sentiment", "focalization"]:
                executed.setdefault(fk, False)
        else:
            # Fallback: heurísticas legacy (proyectos analizados antes del run ledger)
            stats = _get_project_stats(project_id, db)
            has_chapters = (stats.get("chapter_count") or 0) > 0
            has_entities = (stats.get("entity_count") or 0) > 0
            has_alerts = (stats.get("open_alerts_count") or 0) > 0
            has_timeline = False

            with db.connection() as conn:
                try:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM timeline_events WHERE project_id = ?", (project_id,)
                    )
                    has_timeline = cursor.fetchone()[0] > 0
                except Exception:
                    pass

            executed = {
                "parsing": has_chapters,
                "structure": has_chapters,
                "entities": has_entities,
                "coreference": has_entities,
                "attributes": has_entities,
                "relationships": False,
                "interactions": False,
                "alerts": has_alerts,
                "grammar_alerts": has_alerts,
                "spelling": has_alerts,
                "grammar": has_alerts,
                "register": has_alerts,
                "pacing": has_chapters,
                "coherence": has_entities and has_chapters,
                "temporal": has_timeline,
                "timeline": has_timeline,
                "emotional": False,
                "sentiment": False,
                "focalization": False,
                "voice_profiles": has_entities and has_chapters,
                "voice_deviations": has_entities and has_chapters,
                "register_analysis": has_chapters,
                "tension_curve": has_chapters,
                "sensory_report": has_chapters,
                "sentence_energy": has_chapters,
                "narrative_templates": has_chapters,
                "narrative_health": has_chapters and has_entities,
                "character_archetypes": has_entities and has_chapters,
                "story_bible": has_entities,
                "speaker_attribution": has_entities and has_chapters,
            }

        return ApiResponse(
            success=True,
            data={
                "executed": executed,
                "analysis_status": project.analysis_status,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.patch("/api/projects/{project_id}/settings", response_model=ApiResponse)
def update_project_settings(
    project_id: int,
    settings: dict = Body(...),  # noqa: B008
):
    """
    Actualiza configuración de análisis del proyecto (CR-03).

    Args:
        project_id: ID del proyecto
        settings: dict con analysis_features y otras configuraciones

    Returns:
        ApiResponse con settings saneados y warnings de degradación
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Obtener settings actuales
        import json
        current_settings = (
            project.settings
            if isinstance(project.settings, dict)
            else (json.loads(project.settings) if project.settings else {})
        )

        runtime_warnings = []

        # Validar y sanear analysis_features si se envían
        if "analysis_features" in settings:
            try:
                sanitized_features, warnings = _validate_analysis_features(
                    settings["analysis_features"],
                    capabilities=_get_lightweight_capabilities(),
                    updated_by="api"
                )
                settings["analysis_features"] = sanitized_features
                runtime_warnings.extend(warnings)
            except ValueError as val_err:
                # P1: Retornar 400 para payload malformado
                raise HTTPException(status_code=400, detail=str(val_err))

        # P2: Whitelist de ramas permitidas en settings
        ALLOWED_SETTINGS_KEYS = {"analysis_features"}
        for key in list(settings.keys()):
            if key not in ALLOWED_SETTINGS_KEYS:
                runtime_warnings.append(f"Clave '{key}' no permitida en settings, se omitirá")
                del settings[key]

        # Merge profundo: preservar otras ramas de settings
        # Solo actualizar las claves enviadas
        for key, value in settings.items():
            if key == "analysis_features":
                # Merge profundo dentro de analysis_features
                # Si no existe, inicializar con defaults
                if "analysis_features" not in current_settings:
                    current_settings["analysis_features"] = _get_default_analysis_features()

                af_current = current_settings["analysis_features"]
                af_new = value

                # Merge pipeline_flags (preservar flags existentes)
                if "pipeline_flags" in af_new:
                    if "pipeline_flags" not in af_current:
                        # Inicializar con defaults
                        defaults = _get_default_analysis_features()
                        af_current["pipeline_flags"] = defaults["pipeline_flags"]
                    af_current["pipeline_flags"].update(af_new["pipeline_flags"])

                # Merge nlp_methods (reemplazo completo por categoría)
                if "nlp_methods" in af_new:
                    if "nlp_methods" not in af_current:
                        # Inicializar con defaults
                        defaults = _get_default_analysis_features()
                        af_current["nlp_methods"] = defaults["nlp_methods"]
                    for cat, methods in af_new["nlp_methods"].items():
                        af_current["nlp_methods"][cat] = methods  # reemplazo completo

                # Merge voting_thresholds (merge por clave)
                if "voting_thresholds" in af_new:
                    if "voting_thresholds" not in af_current:
                        defaults = _get_default_analysis_features()
                        af_current["voting_thresholds"] = defaults["voting_thresholds"]
                    af_current["voting_thresholds"].update(af_new["voting_thresholds"])

                # Metadatos ya vienen de _validate_analysis_features (schema_version, updated_at, updated_by)
                for key in ["schema_version", "updated_at", "updated_by"]:
                    if key in af_new:
                        af_current[key] = af_new[key]

                current_settings["analysis_features"] = af_current
            else:
                # Otras ramas: merge directo
                current_settings[key] = value

        # Persistir
        project.settings = current_settings
        update_result = deps.project_manager.update(project)

        if update_result.is_failure:
            logger.error(f"Failed to update project settings: {update_result.error}")
            return ApiResponse(success=False, error="Error al guardar configuración")

        return ApiResponse(
            success=True,
            data={
                "settings": {
                    "analysis_features": current_settings.get("analysis_features")
                },
                "runtime_warnings": runtime_warnings
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects", response_model=ApiResponse)
def create_project(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    file_path: Optional[str] = Body(None),
    file: Optional[UploadFile] = File(None),  # noqa: B008
    is_demo: Optional[bool] = Body(False),
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
        import uuid
        from pathlib import Path

        allowed_extensions = [".docx", ".doc", ".txt", ".md", ".pdf", ".epub"]

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
                raise HTTPException(status_code=400, detail=f"El archivo no existe: {file_path}")
            except (ValueError, PermissionError) as e:
                raise HTTPException(status_code=400, detail=str(e))
            file_ext = document_path.suffix.lower()  # type: ignore[union-attr]
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

            # Guardar archivo con validación de tamaño (50 MB máximo)
            MAX_UPLOAD_BYTES = 50 * 1024 * 1024
            size = 0
            with open(permanent_path, "wb") as f:
                while chunk := file.file.read(8192):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        permanent_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=400, detail="El archivo supera el límite de 50 MB"
                        )
                    f.write(chunk)

            document_path = permanent_path
            stored_path = str(permanent_path)
            logger.info(f"Document saved permanently at: {permanent_path}")

        else:
            raise HTTPException(status_code=400, detail="Se requiere file_path o file")

        if file_ext not in allowed_extensions:
            # Limpiar archivo guardado si la extensión no es válida
            if stored_path and file and Path(stored_path).exists():
                Path(stored_path).unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Formato de archivo no soportado: {file_ext}. Formatos permitidos: {', '.join(allowed_extensions)}",
            )

        try:
            from narrative_assistant.parsers import get_parser
            from narrative_assistant.parsers.base import detect_format

            # Detectar formato del documento
            doc_format = detect_format(document_path)  # type: ignore[arg-type]
            format_str = (
                doc_format.value
                if hasattr(doc_format, "value")
                else str(doc_format).split(".")[-1].upper()
            )

            # Leer contenido del documento para create_from_document
            logger.info(f"Reading document content from: {document_path}")
            parser = get_parser(document_path)  # type: ignore[arg-type]
            parse_result = parser.parse(document_path)  # type: ignore[arg-type]

            if parse_result.is_failure:
                raise HTTPException(
                    status_code=400, detail=f"Error leyendo documento: {parse_result.error}"
                )

            raw_doc = parse_result.value
            document_text = raw_doc.full_text  # type: ignore[union-attr]

            if not document_text or not document_text.strip():
                raise HTTPException(
                    status_code=400, detail="El documento está vacío o no se pudo leer el contenido"
                )

            logger.info(
                f"Document parsed: {len(document_text)} chars, {len(document_text.split())} words"
            )

            # Crear proyecto usando create_from_document (el único método disponible)
            logger.info(f"Creating project '{name}' from: {document_path}")

            project_repo = deps.project_manager
            create_result = project_repo.create_from_document(
                text=document_text,
                name=name,
                document_format=format_str,
                document_path=Path(stored_path),
                description=description or f"Documento: {document_path.name}",  # type: ignore[union-attr]
                check_existing=True,
                is_demo=bool(is_demo),
            )

            if create_result.is_failure:
                error = create_result.error
                # Si el documento ya existe, devolver código 409 Conflict
                if error and "already exists" in str(error.message).lower():
                    raise HTTPException(
                        status_code=409,
                        detail=f"Este documento ya existe en el proyecto '{getattr(error, 'existing_project_name', 'existente')}'",
                    )
                raise HTTPException(status_code=500, detail=f"Error creando proyecto: {error}")

            project = create_result.value

            if project is None:
                logger.error("create_from_document returned success but value is None")
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
                message="Proyecto creado. Use /analyze para iniciar el análisis.",
            )

        except Exception:
            # Limpiar archivo si hay error (solo si fue subido)
            if file and stored_path and Path(stored_path).exists():
                Path(stored_path).unlink()
            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/projects/{project_id}", response_model=ApiResponse)
def delete_project(project_id: int):
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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/document/replace", response_model=ApiResponse)
def replace_project_document(
    project_id: int,
    file_path: Optional[str] = Body(None),
    file: Optional[UploadFile] = File(None),  # noqa: B008
):
    """
    Reemplaza el documento del proyecto validando identidad de manuscrito.

    Política:
    - same_document: permitir reemplazo
    - uncertain: permitir hasta umbral de riesgo por licencia
    - different_document: bloquear y pedir crear proyecto nuevo
    """
    temp_upload_path: Optional[Path] = None
    retain_uploaded_file = False
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        project_result = deps.project_manager.get(project_id)
        if project_result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        project = project_result.value
        if project.analysis_status in ("analyzing", "queued"):
            return ApiResponse(
                success=False,
                error="No se puede reemplazar el documento durante un análisis en curso.",
            )

        allowed_extensions = {".docx", ".doc", ".txt", ".md", ".pdf", ".epub"}
        candidate_path, is_temp_upload = _resolve_document_path(
            file_path=file_path,
            file=file,
            allowed_extensions=allowed_extensions,
        )
        if is_temp_upload:
            temp_upload_path = candidate_path

        if candidate_path.suffix.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Formato de archivo no soportado: {candidate_path.suffix}. "
                    f"Formatos permitidos: {', '.join(sorted(allowed_extensions))}"
                ),
            )

        candidate_text, candidate_format = _parse_document(candidate_path)
        candidate_fingerprint = generate_fingerprint(candidate_text).full_hash

        previous_text = ""
        previous_path = Path(project.document_path) if project.document_path else None
        if previous_path and previous_path.exists():
            try:
                previous_text, _ = _parse_document(previous_path)
            except Exception as parse_old_err:
                logger.warning(
                    "No se pudo parsear documento previo de proyecto %s: %s",
                    project_id,
                    parse_old_err,
                )
        if not previous_text:
            previous_text = _load_project_text_from_db(project_id)
            if previous_text:
                logger.info(
                    "replace_project_document: usando capítulos persistidos como baseline para proyecto %s",
                    project_id,
                )

        identity_service = ManuscriptIdentityService()
        if previous_text:
            decision = identity_service.classify(previous_text, candidate_text)
        else:
            # Fallback conservador si no existe texto previo parseable.
            if (
                project.document_fingerprint
                and project.document_fingerprint == candidate_fingerprint
            ):
                decision = identity_service.classify(candidate_text, candidate_text)
            else:
                decision = identity_service.classify("", candidate_text)

        db = deps.get_database()
        identity_repo = ManuscriptIdentityRepository(db)
        license_subject = _get_license_subject()
        identity_repo.record_check(
            project_id=project_id,
            license_subject=license_subject,
            previous_fingerprint=project.document_fingerprint or "",
            candidate_fingerprint=candidate_fingerprint,
            decision=decision,
        )
        if decision.classification == IDENTITY_UNCERTAIN:
            identity_repo.append_risk_event(
                license_subject=license_subject,
                event_type="uncertain_detected",
                details={
                    "project_id": project_id,
                    "confidence": round(decision.confidence, 4),
                },
            )

        uncertain_limit = 3
        try:
            config = deps.get_config()
            uncertain_limit = int(config.persistence.identity_uncertain_limit_30d or 3)
        except Exception:
            uncertain_limit = 3

        uncertain_count_30d = identity_repo.uncertain_count_rolling(license_subject, days=30)
        review_required = uncertain_count_30d > uncertain_limit
        identity_repo.upsert_risk_state(
            license_subject=license_subject,
            uncertain_count_30d=uncertain_count_30d,
            review_required=review_required,
        )
        if review_required:
            identity_repo.append_risk_event(
                license_subject=license_subject,
                event_type="uncertain_threshold_exceeded",
                details={
                    "uncertain_count_30d": uncertain_count_30d,
                    "threshold": uncertain_limit,
                },
            )

        if decision.classification == IDENTITY_DIFFERENT_DOCUMENT:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": (
                        "El documento no parece una nueva versión del manuscrito actual. "
                        "Crea un proyecto nuevo para analizar este documento."
                    ),
                },
            )

        if decision.classification == IDENTITY_UNCERTAIN and review_required:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": (
                        "No se pudo confirmar con suficiente certeza que sea el mismo manuscrito. "
                        "Crea un proyecto nuevo para continuar."
                    ),
                },
            )

        project.document_path = str(candidate_path)
        project.document_fingerprint = candidate_fingerprint
        project.document_format = candidate_format
        project.word_count = len(candidate_text.split())
        project.analysis_status = "pending"
        project.analysis_progress = 0.0
        update_result = deps.project_manager.update(project)
        if update_result.is_failure:
            return ApiResponse(success=False, error="No se pudo actualizar el proyecto.")

        if temp_upload_path is not None:
            retain_uploaded_file = True

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "classification": decision.classification,
                "confidence": round(decision.confidence, 4),
                "recommended_full_run": decision.recommended_full_run,
            },
            message="Manuscrito actualizado correctamente. Ejecuta un nuevo análisis.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing document for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")
    finally:
        if temp_upload_path and temp_upload_path.exists() and not retain_uploaded_file:
            try:
                temp_upload_path.unlink(missing_ok=True)
            except Exception:
                logger.debug(
                    "replace_project_document: no se pudo eliminar upload temporal %s",
                    temp_upload_path,
                )


@router.get("/api/projects/{project_id}/identity/last-check", response_model=ApiResponse)
def get_last_identity_check(project_id: int):
    """Retorna el último check de identidad registrado para un proyecto."""
    try:
        db = deps.get_database()
        identity_repo = ManuscriptIdentityRepository(db)
        row = identity_repo.get_last_check(project_id)
        if not row:
            return ApiResponse(success=True, data=None)
        return ApiResponse(success=True, data=row)
    except Exception as e:
        logger.error(f"Error getting identity check for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# ============================================================================
# S15: Version Tracking (BK-28)
# ============================================================================


@router.get("/api/projects/{project_id}/versions", response_model=ApiResponse)
def list_versions(project_id: int, limit: int = Query(50, ge=1, le=200)):
    """S15-02: Lista versiones con métricas para un proyecto.

    Returns:
        Lista de version_metrics ordenadas por version_num descendente.
    """
    try:
        db = deps.get_database()
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT vm.id, vm.project_id, vm.version_num, vm.snapshot_id,
                          vm.alert_count, vm.word_count, vm.entity_count, vm.chapter_count,
                          vm.health_score, vm.formality_avg, vm.dialogue_ratio, vm.created_at,
                          vm.alerts_new_count, vm.alerts_resolved_count, vm.alerts_unchanged_count,
                          vm.critical_count, vm.warning_count, vm.info_count,
                          vm.entities_new_count, vm.entities_removed_count, vm.entities_renamed_count,
                          vm.chapter_added_count, vm.chapter_removed_count, vm.chapter_reordered_count,
                          vm.run_mode, vm.duration_total_sec, vm.phase_durations_json,
                          vd.modified_chapters, vd.added_chapters, vd.removed_chapters,
                          vd.chapter_change_ratio, vd.renamed_entities,
                          vd.new_entities, vd.removed_entities
                   FROM version_metrics vm
                   LEFT JOIN version_diffs vd
                          ON vd.project_id = vm.project_id AND vd.version_num = vm.version_num
                   WHERE vm.project_id = ?
                   ORDER BY vm.version_num DESC
                   LIMIT ?""",
                (project_id, limit),
            ).fetchall()
            versions = []
            for r in rows:
                top_entity_renames: list[dict[str, Any]] = []
                snapshot_id = r[3]
                if snapshot_id:
                    rename_rows = conn.execute(
                        """
                        SELECT old_name, new_name, confidence
                        FROM entity_version_links
                        WHERE project_id = ? AND snapshot_id = ? AND link_type = 'renamed'
                        ORDER BY confidence DESC, id ASC
                        LIMIT 5
                        """,
                        (project_id, int(snapshot_id)),
                    ).fetchall()
                    top_entity_renames = [
                        {
                            "old_name": rr["old_name"] or "",
                            "new_name": rr["new_name"] or "",
                            "confidence": float(rr["confidence"] or 0.0),
                        }
                        for rr in rename_rows
                    ]

                versions.append(
                    {
                        "id": r[0],
                        "project_id": r[1],
                        "version_num": r[2],
                        "snapshot_id": r[3],
                        "alert_count": r[4],
                        "word_count": r[5],
                        "entity_count": r[6],
                        "chapter_count": r[7],
                        "health_score": r[8],
                        "formality_avg": r[9],
                        "dialogue_ratio": r[10],
                        "created_at": r[11],
                        "alerts_new_count": r[12] or 0,
                        "alerts_resolved_count": r[13] or 0,
                        "alerts_unchanged_count": r[14] or 0,
                        "critical_count": r[15] or 0,
                        "warning_count": r[16] or 0,
                        "info_count": r[17] or 0,
                        "entities_new_count": r[18] or 0,
                        "entities_removed_count": r[19] or 0,
                        "entities_renamed_count": r[20] or 0,
                        "chapter_added_count": r[21] or 0,
                        "chapter_removed_count": r[22] or 0,
                        "chapter_reordered_count": r[23] or 0,
                        "run_mode": r[24] or "full",
                        "duration_total_sec": float(r[25] or 0.0),
                        "phase_durations_json": r[26] or "{}",
                        "modified_chapters": r[27] or 0,
                        "added_chapters": r[28] or 0,
                        "removed_chapters": r[29] or 0,
                        "chapter_change_ratio": float(r[30] or 0.0),
                        "renamed_entities": r[31] or 0,
                        "new_entities": r[32] or 0,
                        "removed_entities": r[33] or 0,
                        "top_entity_renames": top_entity_renames,
                    }
                )

        return ApiResponse(success=True, data=versions)
    except Exception as e:
        logger.error(f"Error listing versions for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/versions/trend", response_model=ApiResponse)
def get_version_trend(project_id: int, limit: int = Query(10, ge=2, le=50)):
    """S15-02: Serie temporal simplificada para sparkline.

    Returns:
        Lista de {version_num, alert_count, health_score, created_at} para las
        últimas N versiones, ordenadas cronológicamente (ASC).
    """
    try:
        db = deps.get_database()
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT version_num, alert_count, health_score, word_count, created_at,
                          alerts_new_count, alerts_resolved_count, run_mode, duration_total_sec
                   FROM version_metrics
                   WHERE project_id = ?
                   ORDER BY version_num DESC
                   LIMIT ?""",
                (project_id, limit),
            ).fetchall()

        # Revert to chronological order (ASC) for sparkline rendering
        trend = []
        for r in reversed(rows):
            trend.append(
                {
                    "version_num": r[0],
                    "alert_count": r[1],
                    "health_score": r[2],
                    "word_count": r[3],
                    "created_at": r[4],
                    "alerts_new_count": r[5] or 0,
                    "alerts_resolved_count": r[6] or 0,
                    "run_mode": r[7] or "full",
                    "duration_total_sec": float(r[8] or 0.0),
                }
            )

        # Calculate deltas if at least 2 versions
        delta = None
        if len(trend) >= 2:
            latest = trend[-1]
            prev = trend[-2]
            delta = {
                "alert_count": latest["alert_count"] - prev["alert_count"],
                "health_score": (
                    round(latest["health_score"] - prev["health_score"], 2)
                    if latest["health_score"] is not None and prev["health_score"] is not None
                    else None
                ),
                "word_count": latest["word_count"] - prev["word_count"],
            }

        return ApiResponse(success=True, data={"trend": trend, "delta": delta})
    except Exception as e:
        logger.error(f"Error getting version trend for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/versions/summary", response_model=ApiResponse)
def get_version_summary(project_id: int):
    """
    Resumen compacto de evolución de versiones + último check de identidad.
    """
    try:
        db = deps.get_database()
        with db.connection() as conn:
            latest = conn.execute(
                """
                SELECT vm.version_num, vm.alert_count, vm.health_score, vm.created_at, vm.snapshot_id,
                       vd.modified_chapters, vd.chapter_change_ratio,
                       vd.renamed_entities, vd.new_entities, vd.removed_entities
                FROM version_metrics vm
                LEFT JOIN version_diffs vd
                       ON vd.project_id = vm.project_id AND vd.version_num = vm.version_num
                WHERE vm.project_id = ?
                ORDER BY vm.version_num DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            previous = conn.execute(
                """
                SELECT version_num, alert_count, health_score
                FROM version_metrics
                WHERE project_id = ?
                ORDER BY version_num DESC
                LIMIT 1 OFFSET 1
                """,
                (project_id,),
            ).fetchone()

            identity = conn.execute(
                """
                SELECT classification, confidence, score, created_at
                FROM manuscript_identity_checks
                WHERE project_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            top_entity_renames: list[dict[str, Any]] = []
            latest_snapshot_id = int(latest["snapshot_id"] or 0) if latest else 0
            if latest_snapshot_id > 0:
                rename_rows = conn.execute(
                    """
                    SELECT old_name, new_name, confidence
                    FROM entity_version_links
                    WHERE project_id = ? AND snapshot_id = ? AND link_type = 'renamed'
                    ORDER BY confidence DESC, id ASC
                    LIMIT 5
                    """,
                    (project_id, latest_snapshot_id),
                ).fetchall()
                top_entity_renames = [
                    {
                        "old_name": rr["old_name"] or "",
                        "new_name": rr["new_name"] or "",
                        "confidence": float(rr["confidence"] or 0.0),
                    }
                    for rr in rename_rows
                ]

        if not latest:
            return ApiResponse(success=True, data=None)

        delta = {
            "alert_count": 0,
            "health_score": 0.0,
        }
        if previous:
            delta["alert_count"] = int(latest["alert_count"] or 0) - int(
                previous["alert_count"] or 0
            )
            if latest["health_score"] is not None and previous["health_score"] is not None:
                delta["health_score"] = round(
                    float(latest["health_score"]) - float(previous["health_score"]),
                    3,
                )

        data = {
            "latest_version": int(latest["version_num"]),
            "created_at": latest["created_at"],
            "alert_count": int(latest["alert_count"] or 0),
            "health_score": float(latest["health_score"] or 0.0),
            "delta": delta,
            "chapter_diff": {
                "modified_chapters": int(latest["modified_chapters"] or 0),
                "chapter_change_ratio": float(latest["chapter_change_ratio"] or 0.0),
            },
            "entity_diff": {
                "renamed_entities": int(latest["renamed_entities"] or 0),
                "new_entities": int(latest["new_entities"] or 0),
                "removed_entities": int(latest["removed_entities"] or 0),
            },
            "top_entity_renames": top_entity_renames,
            "identity_last_check": (
                {
                    "classification": identity["classification"],
                    "confidence": float(identity["confidence"] or 0.0),
                    "score": float(identity["score"] or 0.0),
                    "created_at": identity["created_at"],
                }
                if identity
                else None
            ),
        }
        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"Error getting version summary for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get(
    "/api/projects/{project_id}/versions/{version_num}/entity-links", response_model=ApiResponse
)
def get_version_entity_links(project_id: int, version_num: int):
    """Detalle de continuidad de entidades para una versión."""
    try:
        db = deps.get_database()
        with db.connection() as conn:
            row = conn.execute(
                """
                SELECT snapshot_id
                FROM version_diffs
                WHERE project_id = ? AND version_num = ?
                """,
                (project_id, version_num),
            ).fetchone()
            if not row or not row["snapshot_id"]:
                return ApiResponse(success=True, data=[])

            snapshot_id = int(row["snapshot_id"])
            links = conn.execute(
                """
                SELECT old_entity_id, new_entity_id, old_name, new_name,
                       link_type, confidence, reason_json, created_at
                FROM entity_version_links
                WHERE project_id = ? AND snapshot_id = ?
                ORDER BY confidence DESC, id ASC
                """,
                (project_id, snapshot_id),
            ).fetchall()

        data = []
        for link in links:
            data.append(
                {
                    "old_entity_id": link["old_entity_id"],
                    "new_entity_id": link["new_entity_id"],
                    "old_name": link["old_name"],
                    "new_name": link["new_name"],
                    "link_type": link["link_type"],
                    "confidence": float(link["confidence"] or 0.0),
                    "reason_json": link["reason_json"] or "{}",
                    "created_at": link["created_at"],
                }
            )
        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(
            f"Error getting entity links for project {project_id} version {version_num}: {e}",
            exc_info=True,
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/versions/compare", response_model=ApiResponse)
def compare_versions(
    project_id: int, from_version: int = Query(..., ge=1), to_version: int = Query(..., ge=1)
):
    """Comparativa detallada entre dos versiones."""
    try:
        db = deps.get_database()
        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT version_num, alert_count, word_count, entity_count, chapter_count,
                       health_score, alerts_new_count, alerts_resolved_count,
                       entities_new_count, entities_removed_count, entities_renamed_count,
                       chapter_added_count, chapter_removed_count, run_mode, duration_total_sec
                FROM version_metrics
                WHERE project_id = ? AND version_num IN (?, ?)
                """,
                (project_id, from_version, to_version),
            ).fetchall()
            if len(rows) != 2:
                return ApiResponse(
                    success=False, error="No se encontraron ambas versiones para comparar."
                )

        ordered = sorted(rows, key=lambda x: int(x["version_num"]))
        older = ordered[0]
        newer = ordered[1]

        def _delta_num(key: str) -> float:
            return float(newer[key] or 0) - float(older[key] or 0)

        return ApiResponse(
            success=True,
            data={
                "from_version": int(older["version_num"]),
                "to_version": int(newer["version_num"]),
                "from": dict(older),
                "to": dict(newer),
                "delta": {
                    "alert_count": int(_delta_num("alert_count")),
                    "word_count": int(_delta_num("word_count")),
                    "entity_count": int(_delta_num("entity_count")),
                    "chapter_count": int(_delta_num("chapter_count")),
                    "health_score": round(_delta_num("health_score"), 3),
                    "alerts_new_count": int(_delta_num("alerts_new_count")),
                    "alerts_resolved_count": int(_delta_num("alerts_resolved_count")),
                    "entities_new_count": int(_delta_num("entities_new_count")),
                    "entities_removed_count": int(_delta_num("entities_removed_count")),
                    "entities_renamed_count": int(_delta_num("entities_renamed_count")),
                    "chapter_added_count": int(_delta_num("chapter_added_count")),
                    "chapter_removed_count": int(_delta_num("chapter_removed_count")),
                    "duration_total_sec": round(_delta_num("duration_total_sec"), 3),
                },
            },
        )
    except Exception as e:
        logger.error(
            f"Error comparing versions for project {project_id} ({from_version} vs {to_version}): {e}",
            exc_info=True,
        )
        return ApiResponse(success=False, error="Error interno del servidor")


# ============================================================================
# Dialogue Style Preferences
# ============================================================================


@router.get("/api/projects/{project_id}/dialogue-style-summary", response_model=ApiResponse)
def get_dialogue_style_summary(project_id: int):
    """
    Obtiene resumen del estilo de diálogo en el proyecto.

    Returns:
        ApiResponse con:
        - total_dialogues: int
        - by_type: dict[str, int]  # Conteo por tipo
        - predominant_style: str
        - compliance_ratio: float  # 0.0-1.0
        - non_compliant_count: int
        - user_preference: str | None
    """
    try:
        from narrative_assistant.nlp.dialogue_style_checker import get_dialogue_style_checker

        checker = get_dialogue_style_checker()
        result = checker.get_summary(project_id)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.errors[0]))

        summary = result.value
        return ApiResponse(
            success=True,
            data={
                "total_dialogues": summary.total_dialogues,
                "by_type": summary.by_type,
                "predominant_style": summary.predominant_style,
                "compliance_ratio": summary.compliance_ratio,
                "non_compliant_count": summary.non_compliant_count,
                "user_preference": summary.user_preference,
            },
        )

    except Exception as e:
        logger.error(
            f"Error getting dialogue style summary for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/dialogue-style-preference", response_model=ApiResponse)
def update_dialogue_style_preference(
    project_id: int,
    preference: str = Body(..., embed=True),
    min_severity: str = Body("info", embed=True),
):
    """
    Actualiza la preferencia de estilo de diálogo y regenera alertas.

    Args:
        project_id: ID del proyecto
        preference: Nueva preferencia (dash, guillemets, quotes, quotes_typographic, no_check)
        min_severity: Severidad mínima para alertas (info, warning, error)

    Returns:
        ApiResponse con:
        - preference: str
        - alerts_created: int
        - alerts_invalidated: int
    """
    try:
        # Validar preferencia
        valid_preferences = {"dash", "guillemets", "quotes", "quotes_typographic", "no_check"}
        if preference not in valid_preferences:
            return ApiResponse(
                success=False,
                error=f"Invalid preference. Must be one of: {', '.join(valid_preferences)}",
            )

        from narrative_assistant.nlp.dialogue_preference_manager import get_preference_manager

        manager = get_preference_manager()
        result = manager.update_preference(project_id, preference, min_severity)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.errors[0]))

        return ApiResponse(success=True, data=result.value)

    except Exception as e:
        logger.error(
            f"Error updating dialogue style preference for project {project_id}: {e}",
            exc_info=True,
        )
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/validate-dialogue-style", response_model=ApiResponse)
def validate_dialogue_style(
    project_id: int,
    min_severity: str = Body("info", embed=True),
):
    """
    Valida estilo de diálogo y crea alertas (sin cambiar preferencia).

    Útil para re-ejecutar validación después de ediciones.

    Args:
        project_id: ID del proyecto
        min_severity: Severidad mínima para alertas

    Returns:
        ApiResponse con número de alertas creadas
    """
    try:
        from narrative_assistant.nlp.dialogue_style_checker import get_dialogue_style_checker

        checker = get_dialogue_style_checker()
        result = checker.validate_and_create_alerts(project_id, min_severity)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.errors[0]))

        return ApiResponse(
            success=True,
            data={"alerts_created": result.value},
        )

    except Exception as e:
        logger.error(
            f"Error validating dialogue style for project {project_id}: {e}", exc_info=True
        )
        return ApiResponse(success=False, error="Error interno del servidor")


# ============================================================================
# Guardar / Abrir proyecto (.nra)
# ============================================================================


@router.post("/api/projects/{project_id}/save-file", response_model=ApiResponse)
def save_project_file(
    project_id: int,
    file_path: str = Body(..., embed=True),
):
    """
    Guarda un proyecto como archivo .nra portátil.

    Args:
        project_id: ID del proyecto a exportar.
        file_path: Ruta destino para el archivo .nra.

    Returns:
        ApiResponse con { path, size_bytes }
    """
    try:
        from narrative_assistant.persistence.project_file import NraExporter

        db = deps.get_database()
        exporter = NraExporter(db)
        result = exporter.export_project(project_id, Path(file_path))

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        output_path = result.value
        return ApiResponse(
            success=True,
            data={
                "path": str(output_path),
                "size_bytes": output_path.stat().st_size,
            },
            message="Proyecto guardado correctamente.",
        )
    except Exception as e:
        logger.error(f"Error saving project {project_id} to file: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/open-file", response_model=ApiResponse)
def open_project_file(
    file_path: str = Body(..., embed=True),
):
    """
    Abre un proyecto desde un archivo .nra.

    Args:
        file_path: Ruta al archivo .nra a importar.

    Returns:
        ApiResponse con { project_id, project_name, warnings }
    """
    try:
        from narrative_assistant.persistence.project_file import NraImporter

        nra_path = Path(file_path)

        db = deps.get_database()
        importer = NraImporter(db)
        result = importer.import_project(nra_path)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        new_project_id = result.value
        warnings = result.warnings or []

        # Obtener nombre del proyecto importado
        project_name = None
        try:
            row = db.fetchone("SELECT name FROM projects WHERE id = ?", (new_project_id,))
            if row:
                project_name = row["name"]
        except Exception:
            pass

        return ApiResponse(
            success=True,
            data={
                "project_id": new_project_id,
                "project_name": project_name,
                "warnings": warnings,
            },
            message="Proyecto abierto correctamente.",
        )
    except Exception as e:
        logger.error(f"Error opening project file {file_path}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")
