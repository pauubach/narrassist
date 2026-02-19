"""
Shared dependencies for the Narrative Assistant API.

This module contains all shared state, Pydantic models, and helper functions
used across router modules.

IMPORTANT: Mutable globals (project_manager, entity_repository, etc.) are
initialized by main.py during startup. Router modules MUST access them as
`deps.project_manager`, NOT via `from deps import project_manager` (which
would capture the initial None value).
"""

import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("narrative_assistant.api")

# ============================================================================
# Constants
# ============================================================================

BACKEND_VERSION = "0.9.10"
IS_EMBEDDED_RUNTIME = os.environ.get("NA_EMBEDDED") == "1" or "python-embed" in (sys.executable or "").lower()

# Minimum required Python version (major, minor)
MIN_PYTHON_VERSION = (3, 10)

# Set by main.py during early bootstrap
_log_file: Optional[Path] = None

# ============================================================================
# Mutable global state (initialized by main.py)
# ============================================================================

project_manager = None
entity_repository = None
alert_repository = None
dismissal_repository = None
chapter_repository = None
section_repository = None
get_config = None
get_database = None
NA_VERSION = BACKEND_VERSION
Database = None
MODULES_LOADED = False
MODULES_ERROR: Optional[str] = None

# Track installation status
INSTALLING_DEPENDENCIES = False

# Analysis progress storage (protected by _progress_lock)
analysis_progress_storage: dict[int, dict] = {}
_progress_lock = threading.Lock()

# Analysis cancellation flags (protected by _progress_lock)
# Key: project_id, Value: True if cancellation requested
analysis_cancellation_flags: dict[int, bool] = {}

# Analysis queue: only one analysis at a time (protected by _progress_lock)
# Stores the project_id of the currently running analysis, or None
_active_analysis_project_id: int | None = None

# Queue of projects waiting to be analyzed (protected by _progress_lock)
# Each entry is a dict with keys: project_id, file_path, use_temp_file
_analysis_queue: list[dict] = []

# Two-tier concurrency: lightweight phases run in parallel, heavy phases are exclusive
# Heavy analysis (Tier 2: NER, coreference, attributes, grammar, alerts) exclusive lock
_heavy_analysis_project_id: int | None = None
# Timestamp when the heavy slot was claimed (for watchdog timeout — S8a-18)
_heavy_analysis_claimed_at: float | None = None
# Queue of projects that finished Tier 1 (parsing/structure), waiting for heavy slot
# Each entry is a dict with keys: project_id, context (data from Tier 1)
_heavy_analysis_queue: list[dict] = []
# Watchdog timeout in seconds (30 minutes)
HEAVY_SLOT_TIMEOUT_SECONDS: int = 30 * 60

# Cache for Python status
_python_status_cache: dict | None = None


# ============================================================================
# Bootstrap helpers
# ============================================================================

def _write_debug(msg):
    """Write debug message to file (for early startup diagnostics)."""
    try:
        localappdata = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', ''))
        if localappdata:
            debug_file = os.path.join(localappdata, "Narrative Assistant", "early-debug.txt")
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {msg}\n")
                f.flush()
    except Exception:
        pass


def load_narrative_assistant_modules():
    """
    Load narrative_assistant modules on-demand (phased).

    Phase 1: DB/persistence modules (always available - stdlib only)
    Phase 2: Entity/Alert repositories (may need NLP deps)

    Sets module-level globals directly.
    """
    import importlib.util

    import deps  # self-import to set module globals

    if deps.MODULES_LOADED:
        return True

    _write_debug("=== load_narrative_assistant_modules() called ===")
    logger.info("=== load_narrative_assistant_modules() called ===")

    # Phase 1: DB/persistence
    try:
        _write_debug("On-demand Phase 1: Loading persistence modules...")
        from narrative_assistant.core.config import get_config as get_cfg
        from narrative_assistant.persistence.chapter import ChapterRepository, SectionRepository
        from narrative_assistant.persistence.database import Database as DB  # noqa: N814
        from narrative_assistant.persistence.database import get_database as get_db
        from narrative_assistant.persistence.project import ProjectManager
        _write_debug("On-demand Phase 1 OK: persistence imports succeeded")
    except Exception as e:
        error_msg = f"Phase 1 FAILED (persistence): {type(e).__name__}: {e}"
        _write_debug(error_msg)
        logger.error(error_msg, exc_info=True)
        deps.MODULES_ERROR = str(e)
        return False

    # Phase 1b: Initialize DB managers
    try:
        _write_debug("On-demand Phase 1b: Initializing DB managers...")
        deps.project_manager = ProjectManager()
        deps.chapter_repository = ChapterRepository()
        deps.section_repository = SectionRepository()
        deps.get_config = get_cfg
        deps.get_database = get_db
        deps.Database = DB

        db = get_db()
        _write_debug(f"Database path: {db.db_path}")
        tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t['name'] for t in tables]
        if 'projects' not in table_names:
            _write_debug("WARNING: 'projects' table NOT found after init!")
            logger.error("WARNING: 'projects' table NOT found after init!")

    except Exception as db_init_err:
        _write_debug(f"Phase 1b: DB init failed: {db_init_err}")
        logger.warning(f"Database initialization failed: {db_init_err}", exc_info=True)
        try:
            from narrative_assistant.persistence import repair_database, reset_database
            from narrative_assistant.persistence.database import delete_and_recreate_database
            _write_debug("Attempting repair...")
            success, msg = repair_database()
            if success:
                _write_debug(f"DB repaired: {msg}")
                reset_database()
            else:
                _write_debug(f"Repair failed: {msg}. Nuclear option: delete and recreate...")
                delete_and_recreate_database()
            # Re-initialize after repair
            deps.project_manager = ProjectManager()
            deps.chapter_repository = ChapterRepository()
            deps.section_repository = SectionRepository()
            deps.get_config = get_cfg
            deps.get_database = get_db
            deps.Database = DB
        except Exception as repair_err:
            _write_debug(f"All repair attempts failed: {repair_err}")
            logger.error(f"All DB repair attempts failed: {repair_err}", exc_info=True)
            deps.MODULES_ERROR = f"DB init: {repair_err}"
            return False

    # Phase 2: Entity/Alert repos
    try:
        from narrative_assistant.entities.repository import EntityRepository
        deps.entity_repository = EntityRepository()
        _write_debug("Phase 2a OK: EntityRepository loaded")
    except Exception as e:
        _write_debug(f"Phase 2a: EntityRepository not available: {type(e).__name__}: {e}")
        logger.warning(f"EntityRepository not available: {e}")

    try:
        from narrative_assistant.alerts.repository import AlertRepository
        deps.alert_repository = AlertRepository()
        _write_debug("Phase 2b OK: AlertRepository loaded")
    except Exception as e:
        _write_debug(f"Phase 2b: AlertRepository not available: {type(e).__name__}: {e}")
        logger.warning(f"AlertRepository not available: {e}")

    try:
        from narrative_assistant.persistence.dismissal_repository import DismissalRepository
        deps.dismissal_repository = DismissalRepository()
        _write_debug("Phase 2c OK: DismissalRepository loaded")
    except Exception as e:
        _write_debug(f"Phase 2c: DismissalRepository not available: {type(e).__name__}: {e}")
        logger.warning(f"DismissalRepository not available: {e}")

    # Check NLP deps
    if deps.project_manager is not None:
        _spacy_ok = importlib.util.find_spec("spacy") is not None
        _numpy_ok = importlib.util.find_spec("numpy") is not None
        if _spacy_ok and _numpy_ok:
            deps.MODULES_LOADED = True
            deps.MODULES_ERROR = None
            _write_debug("=== load_narrative_assistant_modules() SUCCESS ===")
            logger.info("Modules loaded successfully (on-demand, NLP deps available)")
            return True
        else:
            _missing = []
            if not _numpy_ok:
                _missing.append("numpy")
            if not _spacy_ok:
                _missing.append("spacy")
            deps.MODULES_LOADED = False
            deps.MODULES_ERROR = f"NLP dependencies missing: {', '.join(_missing)}"
            _write_debug(f"=== load_narrative_assistant_modules() PARTIAL: {deps.MODULES_ERROR} ===")
            logger.warning(f"Modules partially loaded, NLP deps missing: {deps.MODULES_ERROR}")
            return False
    else:
        _write_debug("=== load_narrative_assistant_modules() FAILED: project_manager is None ===")
        return False


# ============================================================================
# Pydantic models (Request/Response)
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
    document_path: Optional[str] = None
    document_format: str
    created_at: str
    last_modified: str
    last_opened: Optional[str]
    analysis_status: str = "completed"
    analysis_progress: int
    word_count: int
    chapter_count: int
    entity_count: int = 0
    open_alerts_count: int = 0
    highest_alert_severity: Optional[str] = None


class EntityResponse(BaseModel):
    """Respuesta con datos de una entidad"""
    id: int
    project_id: int
    entity_type: str
    canonical_name: str
    aliases: list[str]
    importance: str
    description: Optional[str] = None
    first_appearance_char: Optional[int] = None
    first_mention_chapter: Optional[int] = None
    mention_count: int = 0
    is_active: bool = True
    merged_from_ids: list[int] = []
    relevance_score: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    excerpt: Optional[str] = None
    status: str
    entity_ids: list[int] = []
    confidence: float = 0.0
    content_hash: str = ""
    created_at: str
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
    extra_data: Optional[dict] = None
    # S14: Revision Intelligence fields
    previous_alert_summary: Optional[str] = None
    match_confidence: Optional[float] = None
    resolution_reason: Optional[str] = None


class MarkResolvedRequest(BaseModel):
    """Request para confirmar resolución manual de alerta."""
    resolution_reason: Optional[str] = "manual"


class DownloadModelsRequest(BaseModel):
    """Request para descargar modelos"""
    models: list[str] = ["spacy", "embeddings", "transformer_ner"]
    force: bool = False


class LicenseActivationRequest(BaseModel):
    license_key: str


class DeviceDeactivationRequest(BaseModel):
    device_fingerprint: str


class EditorialRulesRequest(BaseModel):
    rules: dict


class ChangeDataLocationRequest(BaseModel):
    new_location: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    history: Optional[list] = None
    selected_text: Optional[str] = None
    selected_text_chapter: Optional[int] = None
    selected_text_start: Optional[int] = None
    selected_text_end: Optional[int] = None


class GlossaryEntryRequest(BaseModel):
    term: str
    definition: Optional[str] = None
    context: Optional[str] = None
    category: Optional[str] = None


class CustomWordRequest(BaseModel):
    word: str
    language: Optional[str] = "es"


class DefaultOverrideRequest(BaseModel):
    overrides: dict


# --- Request models for endpoints that used raw request.json() ---

class AlertStatusRequest(BaseModel):
    """PUT /api/projects/{id}/alerts/{id}/status"""
    status: str = Field(..., pattern=r"^(resolved|dismissed|open|active|reopen)$")
    reason: str = ""
    scope: str = "instance"


class BatchDismissRequest(BaseModel):
    """POST /api/projects/{id}/alerts/batch-dismiss"""
    alert_ids: list[int] = Field(..., min_length=1)
    reason: str = ""
    scope: str = "instance"


class ResolveAmbiguousAttributeRequest(BaseModel):
    """POST /api/projects/{id}/alerts/{id}/resolve-attribute"""
    entity_id: Optional[int] = None  # None = "No asignar"


class AmbiguousAttributeResolution(BaseModel):
    """Resolución individual para batch resolve de alertas ambiguas"""
    alert_id: int
    entity_id: Optional[int] = None  # None = "No asignar"


class BatchResolveAmbiguousAttributesRequest(BaseModel):
    """POST /api/projects/{id}/alerts/batch-resolve-attributes"""
    resolutions: list[AmbiguousAttributeResolution] = Field(..., min_length=1)


class SuppressionRuleRequest(BaseModel):
    """POST /api/projects/{id}/alerts/suppression-rules"""
    rule_type: str = Field(..., pattern=r"^(alert_type|category|entity|source_module)$")
    pattern: str = Field(..., min_length=1)
    entity_name: Optional[str] = None
    reason: Optional[str] = None


class EntityIdsRequest(BaseModel):
    """POST merge-preview / merge"""
    entity_ids: list[int] = Field(..., min_length=2)


class AttributeResolution(BaseModel):
    """Resolución de un conflicto de atributo durante merge."""
    attribute_name: str
    chosen_value: str  # Valor elegido (puede ser custom)

class MergeEntitiesRequest(BaseModel):
    """POST /api/projects/{id}/entities/merge"""
    primary_entity_id: int
    entity_ids: list[int] = Field(..., min_length=1)
    attribute_resolutions: Optional[list[AttributeResolution]] = None


class UpdateEntityRequest(BaseModel):
    """PUT /api/projects/{id}/entities/{id}"""
    name: Optional[str] = None
    canonical_name: Optional[str] = None
    aliases: Optional[list[str]] = None
    importance: Optional[str] = None
    description: Optional[str] = None


class CoreferenceCorrectionRequest(BaseModel):
    """POST /api/projects/{id}/entities/coreference-corrections"""
    mention_start_char: int
    mention_end_char: int
    mention_text: str = ""
    chapter_number: Optional[int] = None
    original_entity_id: Optional[int] = None
    corrected_entity_id: Optional[int] = None
    correction_type: str = Field("reassign", pattern=r"^(reassign|unlink|confirm)$")
    notes: Optional[str] = None


class RejectEntityRequest(BaseModel):
    """POST /api/projects/{id}/entities/reject"""
    entity_text: str = Field(..., min_length=1)
    reason: str = ""


class TogglePatternRequest(BaseModel):
    """PATCH /api/entity-filters/system-patterns/{id}"""
    is_active: bool = True


class UserRejectionRequest(BaseModel):
    """POST /api/entity-filters/user-rejections"""
    entity_name: str = Field(..., min_length=1)
    entity_type: Optional[str] = None
    reason: Optional[str] = None


class ProjectOverrideRequest(BaseModel):
    """POST /api/projects/{id}/entity-overrides"""
    entity_name: str = Field(..., min_length=1)
    action: str = Field("reject", pattern=r"^(reject|force_include)$")
    entity_type: Optional[str] = None
    reason: Optional[str] = None


class CheckFilterRequest(BaseModel):
    """POST /api/entity-filters/check"""
    entity_name: str = Field(..., min_length=1)
    entity_type: Optional[str] = None
    project_id: Optional[int] = None


class CreateAttributeRequest(BaseModel):
    """POST /api/projects/{id}/entities/{id}/attributes"""
    category: str = "physical"
    name: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    confidence: float = 1.0


class UpdateAttributeRequest(BaseModel):
    """PUT /api/projects/{id}/entities/{id}/attributes/{id}"""
    name: Optional[str] = None
    value: Optional[str] = None
    is_verified: Optional[bool] = None


class CreateRelationshipRequest(BaseModel):
    """POST /api/projects/{id}/relationships"""
    source_entity_id: int
    target_entity_id: int
    relation_type: str = "other"
    description: str = ""
    bidirectional: bool = True


class DialogueCorrectionRequest(BaseModel):
    """POST /api/projects/{id}/voice-style/dialogue-corrections"""
    chapter_number: int
    dialogue_start_char: int
    dialogue_end_char: int
    dialogue_text: str = ""
    original_speaker_id: Optional[int] = None
    corrected_speaker_id: Optional[int] = None
    notes: Optional[str] = None


class CorrectionConfigUpdate(BaseModel):
    """Modelo para actualizar configuración de corrección."""
    customizations: Optional[dict] = None  # Solo los parámetros personalizados
    config: Optional[dict] = None  # Compat: config completa (legacy)
    selectedPreset: Optional[str] = None  # noqa: N815


# Categorías permitidas por tipo de entidad (alineado con frontend).
ATTRIBUTE_CATEGORIES_BY_ENTITY_TYPE: dict[str, set[str]] = {
    "character": {"physical", "psychological", "social", "ability"},
    "animal": {"physical", "behavior", "social"},
    "creature": {"physical", "ability", "social"},
    "location": {"geographic", "architectural"},
    "building": {"architectural", "state"},
    "region": {"geographic", "history"},
    "object": {"material", "appearance", "state", "function"},
    "vehicle": {"material", "appearance", "state", "function"},
    "organization": {"structure", "purpose", "history"},
    "faction": {"structure", "purpose", "history"},
    "family": {"structure", "history", "social"},
    "event": {"temporal", "participants", "consequences"},
    "time_period": {"temporal", "history"},
    "concept": {"definition", "examples", "related"},
    "religion": {"definition", "history", "social"},
    "magic_system": {"definition", "function", "history"},
    "work": {"appearance", "history", "definition"},
    "title": {"social", "history"},
    "language": {"definition", "history"},
    "custom": {"definition", "history", "social"},
}

# Fallback seguro (tipo desconocido): subconjunto transversal mínimo.
DEFAULT_ATTRIBUTE_CATEGORIES: set[str] = {
    "physical",
    "social",
    "state",
    "other",
}


def get_allowed_attribute_categories(entity_type: str | None) -> set[str]:
    """Retorna categorías válidas para el tipo de entidad."""
    if not entity_type:
        return DEFAULT_ATTRIBUTE_CATEGORIES
    normalized = entity_type.lower()
    return ATTRIBUTE_CATEGORIES_BY_ENTITY_TYPE.get(normalized, DEFAULT_ATTRIBUTE_CATEGORIES)


def is_valid_attribute_category(entity_type: str | None, category: str) -> bool:
    """Valida categoría de atributo según tipo de entidad."""
    if not category:
        return False
    return category.lower() in get_allowed_attribute_categories(entity_type)


# ============================================================================
# Helper functions
# ============================================================================

def convert_numpy_types(obj: Any) -> Any:
    """
    Convierte recursivamente tipos numpy a tipos Python nativos para serialización JSON.
    """
    try:
        import numpy as np
    except ImportError:
        return obj

    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj



def generate_person_aliases(canonical_name: str, all_canonical_names: set[str]) -> list[str]:
    """
    Genera aliases automáticos para nombres de personas.

    Para nombres compuestos como "María García", extrae partes útiles
    que pueden usarse como alias para búsqueda de menciones.
    """
    aliases = []  # type: ignore[var-annotated]
    parts = canonical_name.split()

    if len(parts) < 2:
        return aliases

    first_name = parts[0]
    titles = {"don", "doña", "señor", "señora", "sr", "sra", "dr", "dra",
              "doctor", "doctora", "padre", "madre", "hermano", "hermana",
              "el", "la", "los", "las"}

    if (len(first_name) >= 3 and
        first_name.lower() not in titles and
        first_name.lower() not in {n.lower() for n in all_canonical_names}):
        aliases.append(first_name)

    if len(parts) >= 3:
        first_two = " ".join(parts[:2])
        if (first_two.lower() not in {n.lower() for n in all_canonical_names} and
            first_two != canonical_name):
            aliases.append(first_two)

    return aliases


def _get_project_stats(project_id: int, db) -> dict:
    """
    Obtiene estadísticas del proyecto directamente desde la BD.
    Esta es la ÚNICA fuente de verdad para conteos.
    """
    stats = {
        "chapter_count": 0,
        "entity_count": 0,
        "open_alerts_count": 0,
        "word_count": 0,
    }

    if not db:
        return stats

    try:
        row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM chapters WHERE project_id = ?",
            (project_id,)
        )
        stats["chapter_count"] = row["cnt"] if row else 0

        row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM entities WHERE project_id = ?",
            (project_id,)
        )
        stats["entity_count"] = row["cnt"] if row else 0

        row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM alerts WHERE project_id = ? AND status = 'open'",
            (project_id,)
        )
        stats["open_alerts_count"] = row["cnt"] if row else 0

        row = db.fetchone(
            "SELECT COALESCE(SUM(word_count), 0) as total FROM chapters WHERE project_id = ?",
            (project_id,)
        )
        stats["word_count"] = row["total"] if row else 0

    except Exception as e:
        logger.warning(f"Error getting project stats: {e}")

    return stats


def _verify_entity_ownership(entity_id: int, project_id: int) -> tuple[Any, Optional[ApiResponse]]:
    """
    Verifica que una entidad existe y pertenece al proyecto especificado.
    """
    entity_repo = entity_repository
    if not entity_repo:
        return None, ApiResponse(success=False, error="Entity repository not initialized")

    entity = entity_repo.get_entity(entity_id)
    if not entity or entity.project_id != project_id:
        return None, ApiResponse(success=False, error="Entidad no encontrada")

    return entity, None


def _verify_alert_ownership(alert_id: int, project_id: int) -> tuple[Any, Optional[ApiResponse]]:
    """
    Verifica que una alerta existe y pertenece al proyecto especificado.
    """
    if not alert_repository:
        return None, ApiResponse(success=False, error="Alert repository not initialized")

    result = alert_repository.get(alert_id)
    if result.is_failure:
        return None, ApiResponse(success=False, error="Alerta no encontrada")

    alert = result.value
    if alert.project_id != project_id:
        return None, ApiResponse(success=False, error="Alerta no encontrada")

    return alert, None


def _check_languagetool_available(auto_start: bool = False) -> bool:
    """Verifica si LanguageTool está disponible."""
    try:
        import httpx
        response = httpx.get("http://localhost:8081/v2/check", timeout=1.5)
        if response.status_code in (200, 400):
            return True
    except Exception:
        pass

    if auto_start:
        try:
            from narrative_assistant.nlp.grammar import (
                ensure_languagetool_running,
                is_languagetool_installed,
            )
            if is_languagetool_installed():
                logger.info("LanguageTool instalado pero no corriendo, intentando iniciar...")
                if ensure_languagetool_running():
                    logger.info("LanguageTool iniciado correctamente")
                    return True
                else:
                    logger.warning("No se pudo iniciar LanguageTool")
        except Exception as e:
            logger.debug(f"Error verificando/iniciando LanguageTool: {e}")

    return False


def find_python_executable() -> tuple[str | None, str | None, str | None]:
    """
    Encuentra el ejecutable de Python del sistema con version 3.10+.
    """
    import os
    import shutil
    import sys

    IS_EMBEDDED_RUNTIME = os.environ.get("NA_EMBEDDED") == "1" or "python-embed" in (sys.executable or "").lower()

    if IS_EMBEDDED_RUNTIME:
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        return sys.executable, version_str, None

    import re
    import subprocess
    from pathlib import Path

    def check_python_version(python_cmd: str) -> tuple[str | None, str | None]:
        try:
            result = subprocess.run(
                [python_cmd, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5
            )
            if result.returncode == 0:
                version_output = result.stdout.strip() or result.stderr.strip()
                match = re.search(r'Python (\d+)\.(\d+)\.?(\d*)', version_output)
                if match:
                    major, minor = int(match.group(1)), int(match.group(2))
                    version_str = f"{major}.{minor}"
                    if match.group(3):
                        version_str += f".{match.group(3)}"
                    if (major, minor) >= MIN_PYTHON_VERSION:
                        return python_cmd, version_str
                    else:
                        logger.debug(f"Python at {python_cmd} is version {version_str}, need {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"Could not check Python at {python_cmd}: {e}")
        return None, None

    python_candidates = []

    if python3_path := shutil.which("python3"):
        python_candidates.append(python3_path)

    if python_path := shutil.which("python"):
        python_candidates.append(python_path)

    if sys.platform == 'win32':
        if py_path := shutil.which("py"):
            python_candidates.append(py_path)
            for minor_ver in range(14, 9, -1):
                python_candidates.append(f"py -3.{minor_ver}")

        common_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Python',
            Path('C:/Python'),
            Path('C:/Program Files/Python'),
            Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Local' / 'Programs' / 'Python',
        ]

        for base_path in common_paths:
            if base_path.exists():
                for subdir in sorted(base_path.iterdir(), reverse=True):
                    if subdir.is_dir() and subdir.name.startswith('Python3'):
                        python_exe = subdir / 'python.exe'
                        if python_exe.exists():
                            python_candidates.append(str(python_exe))

    conda_base_paths = []
    if sys.platform == 'win32':
        conda_base_paths = [
            Path(os.environ.get('USERPROFILE', '')) / 'anaconda3',
            Path(os.environ.get('USERPROFILE', '')) / 'miniconda3',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'anaconda3',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'miniconda3',
            Path('C:/ProgramData/anaconda3'),
            Path('C:/ProgramData/miniconda3'),
        ]
    else:
        conda_base_paths = [
            Path.home() / 'anaconda3',
            Path.home() / 'miniconda3',
            Path('/opt/anaconda3'),
            Path('/opt/miniconda3'),
        ]

    for conda_path in conda_base_paths:
        if sys.platform == 'win32':
            python_exe = conda_path / 'python.exe'
        else:
            python_exe = conda_path / 'bin' / 'python'
        if python_exe.exists():
            python_candidates.append(str(python_exe))

    for candidate in python_candidates:
        if candidate.startswith("py "):
            try:
                parts = candidate.split()
                result = subprocess.run(
                    parts + ["--version"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5
                )
                if result.returncode == 0:
                    version_output = result.stdout.strip() or result.stderr.strip()
                    match = re.search(r'Python (\d+)\.(\d+)\.?(\d*)', version_output)
                    if match:
                        major, minor_ver = int(match.group(1)), int(match.group(2))
                        if (major, minor_ver) >= MIN_PYTHON_VERSION:
                            version_str = f"{major}.{minor_ver}"
                            if match.group(3):
                                version_str += f".{match.group(3)}"
                            return candidate, version_str, None
            except Exception:
                continue
        else:
            path, version = check_python_version(candidate)
            if path:
                return path, version, None

    return None, None, f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ no encontrado. Por favor instala Python desde python.org"


def get_python_status() -> dict:
    """Obtiene el estado de Python del sistema."""
    global _python_status_cache

    if _python_status_cache is not None:
        return _python_status_cache

    python_path, python_version, error = find_python_executable()

    _python_status_cache = {
        "python_available": python_path is not None,
        "python_version": python_version,
        "python_path": python_path,
        "error": error
    }

    return _python_status_cache


def _classify_mention_type(surface_form: str) -> str:
    """Clasifica el tipo de mención de una entidad."""
    lower = surface_form.lower().strip()
    pronouns = {
        "él", "ella", "ellos", "ellas", "le", "les", "lo", "la", "los", "las",
        "se", "sí", "consigo", "su", "sus", "suyo", "suya", "suyos", "suyas",
        "este", "esta", "ese", "esa", "aquel", "aquella",
        "quien", "quienes", "cual", "cuales",
    }
    if lower in pronouns:
        return "pronoun"
    descriptors = {"el hombre", "la mujer", "el chico", "la chica", "el joven", "la joven",
                   "el niño", "la niña", "el anciano", "la anciana", "el señor", "la señora"}
    if lower in descriptors:
        return "descriptor"
    return "name"


def _field_label(field: str) -> str:
    """Etiqueta legible para campos de documento."""
    labels = {
        "general": "General",
        "literary": "Literario",
        "journalistic": "Periodístico",
        "academic": "Académico",
        "technical": "Técnico",
        "legal": "Jurídico",
        "medical": "Médico",
        "business": "Empresarial",
        "selfhelp": "Autoayuda",
        "culinary": "Culinario",
    }
    field_str = field.value if hasattr(field, "value") else str(field)
    return labels.get(field_str, field_str.replace("_", " ").title())


def _register_label(register: str) -> str:
    """Etiqueta legible para tipo de registro."""
    labels = {
        "formal": "Formal",
        "neutral": "Neutro",
        "colloquial": "Coloquial",
        "vulgar": "Vulgar",
    }
    reg_str = register.value if hasattr(register, "value") else str(register)
    return labels.get(reg_str, reg_str.title())


def _audience_label(audience: str) -> str:
    """Etiqueta legible para tipo de audiencia."""
    labels = {
        "general": "General",
        "children": "Infantil",
        "adult": "Adulto",
        "specialist": "Especialista",
        "mixed": "Mixta",
    }
    aud_str = audience.value if hasattr(audience, "value") else str(audience)
    return labels.get(aud_str, aud_str.replace("_", " ").title())


def _get_sticky_recommendation(glue_percentage: float) -> str:
    """Texto de recomendación para frases pegajosas."""
    if glue_percentage > 60:
        return "El texto tiene un porcentaje alto de palabras de unión. Considera reformular algunas frases para mayor impacto."
    elif glue_percentage > 50:
        return "El porcentaje de palabras de unión está ligeramente por encima del ideal. Revisa las frases marcadas."
    else:
        return "El porcentaje de palabras de unión está dentro del rango normal."


def _get_pacing_label(score: float) -> str:
    """Etiqueta para puntuación de ritmo."""
    if score >= 0.8:
        return "Muy rápido"
    elif score >= 0.6:
        return "Rápido"
    elif score >= 0.4:
        return "Moderado"
    elif score >= 0.2:
        return "Lento"
    else:
        return "Muy lento"


def _estimate_export_pages(data) -> int:
    """Estima el número de páginas para exportaciones."""
    word_count = 0
    if isinstance(data, dict):
        word_count = data.get("word_count", 0) or 0
    elif hasattr(data, "word_count"):
        word_count = data.word_count or 0
    return max(1, word_count // 250)


def is_character_entity(entity) -> bool:
    """
    Verifica si una entidad es un personaje (character, animal, creature).

    Maneja tanto entity_type como enum (con .value) como string directo.
    Compatible con entidades spaCy (PER) y tipos internos (character).
    """
    character_types = {"character", "animal", "creature", "PER", "PERSON"}

    if hasattr(entity, 'entity_type'):
        etype = entity.entity_type
        if hasattr(etype, 'value'):
            return etype.value in character_types
        return etype in character_types
    return False
