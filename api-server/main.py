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
  - history.py:       Undo/redo universal, historial de cambios
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

        # Platform-specific debug paths
        if sys.platform == 'darwin':  # macOS
            debug_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Logs', 'Narrative Assistant')
        elif sys.platform == 'win32':  # Windows
            localappdata = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', ''))
            if not localappdata:
                raise Exception("No LOCALAPPDATA or TEMP")
            debug_dir = os.path.join(localappdata, 'Narrative Assistant')
        else:  # Linux
            debug_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'narrative-assistant')

        debug_file = os.path.join(debug_dir, "early-debug.txt")
        os.makedirs(debug_dir, exist_ok=True)
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

# CRITICAL: Configure SSL with certifi BEFORE any network operations
# This fixes SSL certificate errors in embedded Python on macOS
def _configure_ssl_with_certifi():
    """Configure SSL to use certifi certificates globally."""
    try:
        import ssl

        import certifi

        # Create default context with certifi
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Monkey-patch urllib.request.urlopen to use certifi
        import urllib.request
        _original_urlopen = urllib.request.urlopen

        def _patched_urlopen(url, data=None, timeout=None, **kwargs):
            if timeout is None:
                timeout = 30
            if 'context' not in kwargs:
                url_str = url if isinstance(url, str) else getattr(url, 'full_url', str(url))
                if isinstance(url_str, str) and url_str.startswith('https://'):
                    kwargs['context'] = ssl_context
            return _original_urlopen(url, data=data, timeout=timeout, **kwargs)

        urllib.request.urlopen = _patched_urlopen
        _write_debug(f"SSL configured with certifi: {certifi.where()}")
    except Exception as e:
        _write_debug(f"SSL configuration failed: {e}")

_configure_ssl_with_certifi()

# Setup logging IMMEDIATELY for early debugging
import logging
import shutil
import site


# Version: read from pyproject.toml or narrative_assistant package
def _get_version():
    # Try reading from pyproject.toml first (most accurate for dev)
    try:
        import tomllib
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                v = data.get("project", {}).get("version")
                if v:
                    return v
    except Exception:
        pass
    # Try importlib.metadata (installed package)
    try:
        from importlib.metadata import version
        return version("narrative-assistant")
    except Exception:
        pass
    return "dev"

BACKEND_VERSION = _get_version()
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
    _early_logger.info("=== Initial sys.path setup ===")
    _early_logger.info(f"Python executable: {sys.executable}")
    _early_logger.info(f"sys.path before modifications: {sys.path[:3]}...")

    using_embedded_python = IS_EMBEDDED_RUNTIME

    if using_embedded_python:
        embed_dir = os.path.dirname(sys.executable)

        # En Windows: python-embed/Lib/site-packages
        # En macOS: python-embed/Python.framework/Versions/3.12/lib/python3.12/site-packages
        if sys.platform == 'win32':
            embed_site = os.path.join(embed_dir, "Lib", "site-packages")
        elif sys.platform == 'darwin':
            # sys.executable es python-embed/python3, buscar site-packages del framework
            framework_dir = os.path.join(embed_dir, "Python.framework", "Versions", "3.12")
            embed_site = os.path.join(framework_dir, "lib", "python3.12", "site-packages")
        else:
            # Linux fallback
            embed_site = os.path.join(embed_dir, "lib", "python3.12", "site-packages")

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
                _early_logger.info("Added user site-packages to sys.path")
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
                    _early_logger.info("Added Anaconda site-packages to sys.path")
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
    from narrative_assistant import __version__ as NA_VERSION  # noqa: N812
    from narrative_assistant.core.config import get_config
    from narrative_assistant.persistence.chapter import ChapterRepository, SectionRepository
    from narrative_assistant.persistence.database import Database, get_database
    from narrative_assistant.persistence.project import ProjectManager
    _DB_MODULES_LOADED = True
    # Only override if pyproject.toml read failed (BACKEND_VERSION == "dev").
    # pyproject.toml is authoritative; importlib.metadata can be stale
    # after version bumps without `pip install -e .`.
    if BACKEND_VERSION == "dev":
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
        deps.project_manager = ProjectManager()  # type: ignore[assignment]
        deps.chapter_repository = ChapterRepository()  # type: ignore[assignment]
        deps.section_repository = SectionRepository()  # type: ignore[assignment]
        deps.get_config = get_config  # type: ignore[assignment]
        deps.get_database = get_database  # type: ignore[assignment]
        deps.Database = Database  # type: ignore[assignment]

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
            deps.project_manager = ProjectManager()  # type: ignore[assignment]
            deps.chapter_repository = ChapterRepository()  # type: ignore[assignment]
            deps.section_repository = SectionRepository()  # type: ignore[assignment]
            deps.get_config = get_config  # type: ignore[assignment]
            deps.get_database = get_database  # type: ignore[assignment]
            deps.Database = Database  # type: ignore[assignment]
        except Exception as repair_err:
            _write_debug(f"All repair attempts failed: {repair_err}")
            _early_logger.error(f"All DB repair attempts failed: {repair_err}", exc_info=True)

# Phase 2: Entity/Alert repositories
if _DB_MODULES_LOADED:
    _write_debug("=== PHASE 2: Loading entity/alert repositories ===")
    try:
        from narrative_assistant.entities.repository import EntityRepository
        deps.entity_repository = EntityRepository()  # type: ignore[assignment]
        _write_debug("Phase 2a OK: EntityRepository loaded")
    except Exception as e:
        _write_debug(f"Phase 2a: EntityRepository not available: {type(e).__name__}: {e}")
        _early_logger.warning(f"EntityRepository not available: {e}")

    try:
        from narrative_assistant.alerts.repository import AlertRepository
        deps.alert_repository = AlertRepository()  # type: ignore[assignment]
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
        if not _numpy_ok:
            _missing.append("numpy")
        if not _spacy_ok:
            _missing.append("spacy")
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

try:
    _early_logger.info("=== Starting FastAPI initialization ===")
    _write_debug("=== Starting FastAPI initialization ===")

    _early_logger.info("Importing FastAPI...")
    from fastapi import FastAPI
    _early_logger.info("FastAPI imported successfully")

    _early_logger.info("Importing CORSMiddleware...")
    from fastapi.middleware.cors import CORSMiddleware
    _early_logger.info("CORSMiddleware imported successfully")

    logger = logging.getLogger(__name__)
    logger.info(f"Server starting - NA_VERSION: {deps.NA_VERSION}, MODULES_LOADED: {deps.MODULES_LOADED}")
    _early_logger.info("Creating FastAPI app instance...")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(application):
        """Startup/shutdown lifecycle for the FastAPI application."""
        _early_logger.info("=== Startup event triggered ===")

        # S7c-01: Reset stuck "analyzing"/"queued" projects from previous crash
        try:
            db = deps.get_database()
            stuck = db.fetchall(
                "SELECT id, name FROM projects WHERE analysis_status IN ('analyzing', 'queued')"
            )
            if stuck:
                for row in stuck:
                    db.execute(
                        "UPDATE projects SET analysis_status = 'pending', "
                        "analysis_progress = 0 WHERE id = ?",
                        (row['id'],)
                    )
                logger.info(f"Startup: reset {len(stuck)} stuck projects to 'pending': {[r['name'] for r in stuck]}")
        except Exception as e:
            logger.debug(f"Startup: could not reset stuck projects: {e}")

        if not deps.MODULES_LOADED:
            logger.info("Startup: attempting to load narrative_assistant modules...")
            _early_logger.info("Startup: attempting to load narrative_assistant modules...")
            deps.load_narrative_assistant_modules()
            if deps.MODULES_LOADED:
                logger.info("Startup: modules loaded successfully")
                _early_logger.info("Startup: modules loaded successfully")
            else:
                logger.warning(f"Startup: modules not loaded - {deps.MODULES_ERROR}")
                _early_logger.warning(f"Startup: modules not loaded - {deps.MODULES_ERROR}")
        else:
            _early_logger.info("Startup: modules already loaded")

        yield

    app = FastAPI(
        title="Narrative Assistant API",
        description="API REST para el asistente de corrección narrativa",
        version=deps.NA_VERSION,
        lifespan=lifespan,
    )
    _early_logger.info("FastAPI app created successfully")

    # Configure CORS
    _early_logger.info("Adding CORS middleware...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",   # Vite dev server
            "tauri://localhost",       # Tauri production
            "http://tauri.localhost",  # Tauri alternative
        ],
        allow_credentials=True,
        # Métodos HTTP explícitamente permitidos (solo los que usa la API)
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        # Headers comunes para API REST
        allow_headers=[
            "Content-Type",
            "Accept",
            "Accept-Language",
            "Authorization",
            "X-Requested-With",
        ],
    )
    _early_logger.info("CORS middleware added successfully")

    # Middlewares de seguridad: Rate Limiting y CSRF Protection
    # Nota: los middlewares se ejecutan en orden inverso al de registro,
    # así que CSRF se registra último para ejecutarse primero.
    _early_logger.info("Adding security middlewares (rate limiting + CSRF)...")
    try:
        from middleware import CSRFProtectionMiddleware, RateLimitMiddleware

        # Rate limiting: 10 req/min para análisis, 100 req/min para el resto
        app.add_middleware(
            RateLimitMiddleware,
            analysis_rpm=10,
            default_rpm=100,
        )
        # CSRF: validación de Origin/Referer para métodos que modifican estado
        app.add_middleware(CSRFProtectionMiddleware)
        _early_logger.info("Security middlewares added successfully")
    except Exception as mw_err:
        # No es fatal: la app funciona sin estos middlewares
        _early_logger.warning(f"Security middlewares not loaded: {mw_err}")
        _write_debug(f"WARNING: Security middlewares failed: {mw_err}")

except Exception as e:
    _early_logger.error(f"FATAL: Error during FastAPI initialization: {type(e).__name__}: {e}", exc_info=True)
    _write_debug(f"FATAL: FastAPI initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Include all route modules
# ============================================================================

try:
    _early_logger.info("=== Loading routers ===")
    _write_debug("=== Loading routers ===")

    _early_logger.info("Importing system router...")
    from routers import system
    _early_logger.info("system router imported")

    _early_logger.info("Importing projects router...")
    from routers import projects
    _early_logger.info("projects router imported")

    _early_logger.info("Importing analysis router...")
    from routers import analysis
    _early_logger.info("analysis router imported")

    _early_logger.info("Importing entities router...")
    from routers import entities
    _early_logger.info("entities router imported")

    _early_logger.info("Importing alerts router...")
    from routers import alerts
    _early_logger.info("alerts router imported")

    _early_logger.info("Importing chapters router...")
    from routers import chapters
    _early_logger.info("chapters router imported")

    _early_logger.info("Importing relationships router...")
    from routers import relationships
    _early_logger.info("relationships router imported")

    _early_logger.info("Importing voice_style router...")
    from routers import voice_style
    _early_logger.info("voice_style router imported")

    _early_logger.info("Importing prose router...")
    from routers import prose
    _early_logger.info("prose router imported")

    _early_logger.info("Importing editorial router...")
    from routers import editorial
    _early_logger.info("editorial router imported")

    _early_logger.info("Importing content router...")
    from routers import content
    _early_logger.info("content router imported")

    _early_logger.info("Importing exports router...")
    from routers import exports
    _early_logger.info("exports router imported")

    _early_logger.info("Importing editorial_work router...")
    from routers import editorial_work
    _early_logger.info("editorial_work router imported")

    _early_logger.info("Importing license router...")
    from routers import license
    _early_logger.info("license router imported")

    _early_logger.info("Importing services router...")
    from routers import collections, services
    _early_logger.info("services router imported")

    _early_logger.info("Importing history router...")
    from routers import history
    _early_logger.info("history router imported")

    _early_logger.info("Importing events router...")
    from routers import events
    _early_logger.info("events router imported")

    _early_logger.info("All routers imported successfully")

except Exception as e:
    _early_logger.error(f"FATAL: Error importing routers: {type(e).__name__}: {e}", exc_info=True)
    _write_debug(f"FATAL: Router import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    _early_logger.info("=== Registering routers with FastAPI app ===")

    _early_logger.info("Registering system router...")
    app.include_router(system.router)

    _early_logger.info("Registering projects router...")
    app.include_router(projects.router)

    _early_logger.info("Registering analysis router...")
    app.include_router(analysis.router)

    _early_logger.info("Registering entities router...")
    app.include_router(entities.router)

    _early_logger.info("Registering alerts router...")
    app.include_router(alerts.router)

    _early_logger.info("Registering chapters router...")
    app.include_router(chapters.router)

    _early_logger.info("Registering relationships router...")
    app.include_router(relationships.router)

    _early_logger.info("Registering voice_style router...")
    app.include_router(voice_style.router)

    _early_logger.info("Registering prose router...")
    app.include_router(prose.router)

    _early_logger.info("Registering editorial router...")
    app.include_router(editorial.router)

    _early_logger.info("Registering content router...")
    app.include_router(content.router)

    _early_logger.info("Registering exports router...")
    app.include_router(exports.router)

    _early_logger.info("Registering editorial_work router...")
    app.include_router(editorial_work.router)

    _early_logger.info("Registering license router...")
    app.include_router(license.router)

    _early_logger.info("Registering services router...")
    app.include_router(services.router)

    _early_logger.info("Registering collections router...")
    app.include_router(collections.router)

    _early_logger.info("Registering history router...")
    app.include_router(history.router)

    _early_logger.info("Registering events router...")
    app.include_router(events.router)

    _early_logger.info("All routers registered successfully")

except Exception as e:
    _early_logger.error(f"FATAL: Error registering routers: {type(e).__name__}: {e}", exc_info=True)
    _write_debug(f"FATAL: Router registration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys
    import traceback

    import uvicorn

    _early_logger.info("=== Main block starting ===")
    _write_debug("=== Main block starting ===")

    # Fix para PyInstaller: DEBE ir ANTES de cualquier otra cosa
    _devnull = 'nul' if sys.platform == 'win32' else '/dev/null'
    if sys.stdout is None:
        sys.stdout = open(_devnull, 'w')  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(_devnull, 'w')  # noqa: SIM115
    if sys.stdin is None:
        sys.stdin = open(_devnull)  # noqa: SIM115

    if not hasattr(sys.stdout, 'isatty'):
        sys.stdout.isatty = lambda: False  # type: ignore[method-assign]
    if not hasattr(sys.stderr, 'isatty'):
        sys.stderr.isatty = lambda: False  # type: ignore[method-assign]
    if not hasattr(sys.stdin, 'isatty'):
        sys.stdin.isatty = lambda: False  # type: ignore[method-assign]

    _early_logger.info("stdio redirects configured")

    try:
        logger.info(f"Starting Narrative Assistant API Server v{deps.NA_VERSION}")
        logger.info("Server will be available at http://localhost:8008")
        _early_logger.info(f"Starting Narrative Assistant API Server v{deps.NA_VERSION}")
        _early_logger.info("Server will be available at http://localhost:8008")

        is_frozen = getattr(sys, 'frozen', False)
        _early_logger.info(f"is_frozen: {is_frozen}")

        _early_logger.info("=== About to call uvicorn.run() ===")
        _write_debug("=== About to call uvicorn.run() ===")

        if is_frozen:
            _early_logger.info("Running in frozen mode (with access_log)")
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=8008,
                reload=False,
                log_level="info",
                access_log=True,
            )
        else:
            _early_logger.info("Running in normal mode")
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=8008,
                reload=False,
                log_level="info",
            )

        _early_logger.info("uvicorn.run() returned (server stopped)")

    except Exception as e:
        error_msg = "\n\n===== ERROR FATAL =====\n"
        error_msg += f"Error type: {type(e).__name__}\n"
        error_msg += f"Error message: {e}\n"
        error_msg += "\nTraceback:\n"

        print(error_msg, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

        _early_logger.error(f"FATAL EXCEPTION in main: {type(e).__name__}: {e}", exc_info=True)
        _write_debug(f"FATAL EXCEPTION: {e}")

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
            _early_logger.info(f"Error saved to: {error_file}")
        except Exception as save_err:
            _early_logger.error(f"Could not save error file: {save_err}")

        if sys.stdin and hasattr(sys.stdin, 'read'):
            try:
                print("\nPresiona Enter para cerrar...", file=sys.stderr)
                input()
            except Exception:
                pass

        sys.exit(1)
