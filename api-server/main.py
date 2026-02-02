"""
FastAPI Server Bridge - Servidor HTTP para comunicación con Tauri frontend.

Este servidor actúa como puente entre el frontend Tauri (Vue 3) y el backend
Python (narrative_assistant). Proporciona endpoints REST para todas las
operaciones del sistema.

Puerto: 8008
CORS: Habilitado para localhost:5173 (Vite dev server) y tauri://localhost

Routes are organized in routers/ subdirectory:
  - system.py:        Health, info, debug, models, capabilities, dependencies
  - projects.py:      Project CRUD
  - analysis.py:      Document analysis, progress, cancel, stream
  - entities.py:      Entity CRUD, merge, attributes, filters, coreference
  - alerts.py:        Alert management
  - chapters.py:      Chapters, annotations, style guide, timeline
  - relationships.py: Relationships, character knowledge, character analysis
  - voice_style.py:   Voice profiles, register, dialogue, focalization
  - prose.py:         Prose analysis (pacing, tension, sticky, echo, etc.)
  - editorial.py:     Editorial rules, correction config, document types, scenes
  - content.py:       Glossary, dictionary
  - exports.py:       Document exports
  - license.py:       License management
  - services.py:      LLM, Ollama, LanguageTool, chat
"""

# CRITICAL: Add user site-packages to sys.path BEFORE any imports
# This must be the FIRST thing that runs to allow PyInstaller bundle to find system packages
import os
import sys
from pathlib import Path

# CRITICAL: Write early debug info FIRST
def _write_debug(msg):
    """Write debug message to file"""
    try:
        import os
        from datetime import datetime
        localappdata = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', ''))
        if localappdata:
            debug_file = os.path.join(localappdata, "Narrative Assistant", "early-debug.txt")
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {msg}\n")
                f.flush()
    except Exception as e:
        try:
            import tempfile
            temp_file = os.path.join(tempfile.gettempdir(), "narrative-debug.txt")
            with open(temp_file, 'a', encoding='utf-8') as f:
                f.write(f"{msg} (fallback - error: {e})\n")
                f.flush()
        except Exception:
            pass

_write_debug("="*80)
_write_debug("BACKEND STARTING")
_write_debug(f"sys.executable: {sys.executable}")
_write_debug(f"sys.frozen: {getattr(sys, 'frozen', False)}")
_write_debug(f"sys.path initial (first 3): {sys.path[:3]}")

API_SERVER_DIR = Path(__file__).resolve().parent
BACKEND_ROOT_DIR = API_SERVER_DIR.parent

for extra_path in (BACKEND_ROOT_DIR, API_SERVER_DIR):
    path_str = str(extra_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
        _write_debug(f"Added backend path to sys.path: {path_str}")

_write_debug(f"sys.path after backend insert (first 5): {sys.path[:5]}")

import site
import shutil

# Setup logging IMMEDIATELY for early debugging
import logging

BACKEND_VERSION = "0.3.34"
IS_EMBEDDED_RUNTIME = os.environ.get("NA_EMBEDDED") == "1" or "python-embed" in (sys.executable or "").lower()

# Configure logging FIRST before using any loggers
def _setup_early_logging():
    """Setup logging as early as possible"""
    try:
        if sys.platform == 'win32':
            log_dir = Path.home() / "AppData" / "Local" / "Narrative Assistant"
        elif sys.platform == 'darwin':
            log_dir = Path.home() / "Library" / "Logs" / "Narrative Assistant"
        else:
            log_dir = Path.home() / ".local" / "share" / "narrative-assistant"

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "backend-debug.log"

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(str(log_file), encoding='utf-8', mode='a')
            ],
            force=True
        )
        print(f"LOGGING TO: {log_file}", flush=True)
        return log_file
    except Exception as e:
        print(f"ERROR SETTING UP LOGGING: {e}", flush=True)
        logging.basicConfig(level=logging.DEBUG, force=True)
        return None

_log_file = _setup_early_logging()
_early_logger = logging.getLogger(__name__)
_early_logger.info("="*80)
_early_logger.info(f"BACKEND STARTING - v{BACKEND_VERSION} DEBUG")
_early_logger.info(f"Python executable: {sys.executable}")
_early_logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
if _log_file:
    _early_logger.info(f"Log file: {_log_file}")
_early_logger.info("="*80)

try:
    _write_debug("=== sys.path setup starting ===")
    _early_logger.info(f"=== Initial sys.path setup ===")
    _early_logger.info(f"Python executable: {sys.executable}")
    _early_logger.info(f"sys.path before modifications: {sys.path[:3]}...")

    using_embedded_python = IS_EMBEDDED_RUNTIME

    if using_embedded_python:
        embed_dir = os.path.dirname(sys.executable)
        embed_site = os.path.join(embed_dir, "Lib", "site-packages")
        if embed_site not in sys.path:
            sys.path.insert(0, embed_site)
            _write_debug(f"Added embedded site-packages: {embed_site}")
            _early_logger.info(f"Added embedded site-packages to sys.path: {embed_site}")
        _early_logger.info("Using embedded Python - external path detection skipped")
    else:
        try:
            user_site = site.getusersitepackages()
            _write_debug(f"User site: {user_site}")
            if user_site and os.path.exists(user_site) and user_site not in sys.path:
                sys.path.append(user_site)
                _write_debug("Added user site to sys.path")
                _early_logger.info(f"Added user site-packages to sys.path")
        except Exception as site_err:
            _write_debug(f"Could not get user site-packages: {site_err}")
            _early_logger.warning(f"Could not get user site-packages: {site_err}")

        conda_candidates = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'anaconda3'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'miniconda3'),
            'C:\\ProgramData\\Anaconda3',
            'C:\\ProgramData\\Miniconda3',
        ]

        python_exe = shutil.which("python3") or shutil.which("python")
        if python_exe and 'WindowsApps' not in python_exe:
            conda_candidates.insert(0, os.path.dirname(os.path.dirname(python_exe)))

        for conda_base in conda_candidates:
            conda_site = os.path.join(conda_base, "Lib", "site-packages")
            if os.path.exists(conda_site):
                _write_debug(f"Found Anaconda at: {conda_base}")
                _early_logger.info(f"Detected Anaconda/Conda at: {conda_base}")
                if conda_site not in sys.path:
                    sys.path.insert(0, conda_site)
                    _write_debug("Added conda site to sys.path")
                    _early_logger.info(f"Added Anaconda site-packages to sys.path")
                break
        else:
            _write_debug("No Anaconda installation found")

    _write_debug(f"sys.path after (first 3): {sys.path[:3]}")

    import importlib.util
    numpy_spec = importlib.util.find_spec("numpy")
    _write_debug(f"numpy found: {numpy_spec is not None}")
    _early_logger.info(f"numpy detection after sys.path setup: {numpy_spec is not None}")
    if numpy_spec:
        _write_debug(f"numpy at: {numpy_spec.origin}")

except Exception as e:
    _write_debug(f"ERROR in sys.path setup: {e}")
    _early_logger.error(f"Error during sys.path setup: {e}", exc_info=True)
    pass

# ============================================================================
# Import deps module and initialize shared state
# ============================================================================

import deps

# Propagate bootstrap values to deps module
deps._log_file = _log_file
deps.NA_VERSION = BACKEND_VERSION
deps.IS_EMBEDDED_RUNTIME = IS_EMBEDDED_RUNTIME

# ============================================================================
# PHASED MODULE LOADING (Phase 1: DB/persistence - always available)
# ============================================================================
_write_debug("=== PHASE 1: Loading persistence modules ===")
_DB_MODULES_LOADED = False
try:
    from narrative_assistant.persistence.project import ProjectManager
    from narrative_assistant.persistence.database import get_database, Database
    from narrative_assistant.persistence.chapter import ChapterRepository, SectionRepository
    from narrative_assistant.core.config import get_config
    from narrative_assistant.core.result import Result
    from narrative_assistant import __version__ as NA_VERSION
    _DB_MODULES_LOADED = True
    deps.NA_VERSION = NA_VERSION
    _write_debug("Phase 1 OK: persistence modules loaded")
    _early_logger.info("Phase 1 OK: persistence modules loaded")
except Exception as e:
    _write_debug(f"Phase 1 FAILED: {type(e).__name__}: {e}")
    _early_logger.error(f"Phase 1 FAILED: {type(e).__name__}: {e}", exc_info=True)
    deps.MODULES_ERROR = f"Phase 1 (DB): {e}"
    NA_VERSION = BACKEND_VERSION

# Phase 1b: Initialize database and project manager
if _DB_MODULES_LOADED:
    _write_debug("=== PHASE 1b: Initializing database ===")
    try:
        deps.project_manager = ProjectManager()
        deps.chapter_repository = ChapterRepository()
        deps.section_repository = SectionRepository()
        deps.get_config = get_config
        deps.get_database = get_database
        deps.Database = Database

        db = get_database()
        _write_debug(f"Database path: {db.db_path}")
        _early_logger.info(f"Database path: {db.db_path}")
        tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t['name'] for t in tables]
        _write_debug(f"Tables in database: {table_names}")

        if 'projects' not in table_names:
            _write_debug("WARNING: 'projects' table NOT found after init!")
            _early_logger.error("WARNING: 'projects' table NOT found after init!")

    except Exception as db_init_err:
        _write_debug(f"Phase 1b: DB init failed: {db_init_err}")
        _early_logger.warning(f"Database initialization failed: {db_init_err}", exc_info=True)
        try:
            from narrative_assistant.persistence import repair_database, reset_database
            from narrative_assistant.persistence.database import delete_and_recreate_database
            _write_debug("Attempting repair...")
            success, msg = repair_database()
            if success:
                _write_debug(f"DB repaired: {msg}")
                reset_database()
            else:
                _write_debug(f"Repair failed: {msg}. Nuclear option...")
                delete_and_recreate_database()
            deps.project_manager = ProjectManager()
            deps.chapter_repository = ChapterRepository()
            deps.section_repository = SectionRepository()
            deps.get_config = get_config
            deps.get_database = get_database
            deps.Database = Database
        except Exception as repair_err:
            _write_debug(f"All repair attempts failed: {repair_err}")
            _early_logger.error(f"All DB repair attempts failed: {repair_err}", exc_info=True)

# Phase 2: Entity/Alert repositories
if _DB_MODULES_LOADED:
    _write_debug("=== PHASE 2: Loading entity/alert repositories ===")
    try:
        from narrative_assistant.entities.repository import EntityRepository
        deps.entity_repository = EntityRepository()
        _write_debug("Phase 2a OK: EntityRepository loaded")
    except Exception as e:
        _write_debug(f"Phase 2a: EntityRepository not available: {type(e).__name__}: {e}")
        _early_logger.warning(f"EntityRepository not available: {e}")

    try:
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.alerts.models import AlertStatus, AlertSeverity
        deps.alert_repository = AlertRepository()
        _write_debug("Phase 2b OK: AlertRepository loaded")
    except Exception as e:
        _write_debug(f"Phase 2b: AlertRepository not available: {type(e).__name__}: {e}")
        _early_logger.warning(f"AlertRepository not available: {e}")

# Phase 3: Check if all NLP core deps are available
if deps.project_manager is not None:
    import importlib.util
    _spacy_ok = importlib.util.find_spec("spacy") is not None
    _numpy_ok = importlib.util.find_spec("numpy") is not None
    if _spacy_ok and _numpy_ok:
        deps.MODULES_LOADED = True
        deps.MODULES_ERROR = None
        _write_debug("=== Modules loaded successfully ===")
        _early_logger.info("Modules loaded successfully (NLP deps available)")
    else:
        _missing = []
        if not _numpy_ok: _missing.append("numpy")
        if not _spacy_ok: _missing.append("spacy")
        deps.MODULES_ERROR = f"NLP dependencies missing: {', '.join(_missing)}"
        _write_debug(f"Modules partially loaded: {deps.MODULES_ERROR}")
        _early_logger.warning(f"Modules partially loaded: {deps.MODULES_ERROR}")
else:
    if not deps.MODULES_ERROR:
        deps.MODULES_ERROR = "project_manager is None"
    _early_logger.error("Modules not loaded: project_manager is None")

# ============================================================================
# Create FastAPI app and include routers
# ============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
logger.info(f"Server starting - NA_VERSION: {deps.NA_VERSION}, MODULES_LOADED: {deps.MODULES_LOADED}")

app = FastAPI(
    title="Narrative Assistant API",
    description="API REST para el asistente de corrección narrativa",
    version=deps.NA_VERSION,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "tauri://localhost",       # Tauri production
        "http://tauri.localhost",  # Tauri alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Include all route modules
# ============================================================================

from routers import (
    alerts,
    analysis,
    chapters,
    content,
    editorial,
    entities,
    exports,
    license,
    projects,
    prose,
    relationships,
    services,
    system,
    voice_style,
)

app.include_router(system.router)
app.include_router(projects.router)
app.include_router(analysis.router)
app.include_router(entities.router)
app.include_router(alerts.router)
app.include_router(chapters.router)
app.include_router(relationships.router)
app.include_router(voice_style.router)
app.include_router(prose.router)
app.include_router(editorial.router)
app.include_router(content.router)
app.include_router(exports.router)
app.include_router(license.router)
app.include_router(services.router)

# ============================================================================
# Startup event
# ============================================================================

@app.on_event("startup")
async def startup_load_modules():
    """Try to load narrative_assistant modules on server startup."""
    if not deps.MODULES_LOADED:
        logger.info("Startup: attempting to load narrative_assistant modules...")
        deps.load_narrative_assistant_modules()
        if deps.MODULES_LOADED:
            logger.info("Startup: modules loaded successfully")
        else:
            logger.warning(f"Startup: modules not loaded - {deps.MODULES_ERROR}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys
    import uvicorn
    import traceback

    # Fix para PyInstaller: DEBE ir ANTES de cualquier otra cosa
    if sys.stdout is None:
        sys.stdout = open('nul', 'w') if sys.platform == 'win32' else open('/dev/null', 'w')
    if sys.stderr is None:
        sys.stderr = open('nul', 'w') if sys.platform == 'win32' else open('/dev/null', 'w')
    if sys.stdin is None:
        sys.stdin = open('nul', 'r') if sys.platform == 'win32' else open('/dev/null', 'r')

    if not hasattr(sys.stdout, 'isatty'):
        sys.stdout.isatty = lambda: False
    if not hasattr(sys.stderr, 'isatty'):
        sys.stderr.isatty = lambda: False
    if not hasattr(sys.stdin, 'isatty'):
        sys.stdin.isatty = lambda: False

    try:
        logger.info(f"Starting Narrative Assistant API Server v{deps.NA_VERSION}")
        logger.info("Server will be available at http://localhost:8008")

        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen:
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=8008,
                reload=False,
                log_level="info",
                access_log=True,
            )
        else:
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=8008,
                reload=False,
                log_level="info",
            )
    except Exception as e:
        error_msg = f"\n\n===== ERROR FATAL =====\n"
        error_msg += f"Error type: {type(e).__name__}\n"
        error_msg += f"Error message: {e}\n"
        error_msg += f"\nTraceback:\n"

        print(error_msg, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

        try:
            if sys.platform == 'win32':
                log_dir = Path.home() / "AppData" / "Local" / "Narrative Assistant"
            elif sys.platform == 'darwin':
                log_dir = Path.home() / "Library" / "Logs" / "Narrative Assistant"
            else:
                log_dir = Path.home() / ".local" / "share" / "narrative-assistant"
            log_dir.mkdir(parents=True, exist_ok=True)
            error_file = log_dir / "startup_error.log"

            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(error_msg)
                traceback.print_exc(file=f)

            print(f"\nError guardado en: {error_file}", file=sys.stderr)
        except Exception:
            pass

        if sys.stdin and hasattr(sys.stdin, 'read'):
            try:
                print("\nPresiona Enter para cerrar...", file=sys.stderr)
                input()
            except Exception:
                pass

        sys.exit(1)
