"""
FastAPI Server Bridge - Servidor HTTP para comunicación con Tauri frontend.

Este servidor actúa como puente entre el frontend Tauri (Vue 3) y el backend
Python (narrative_assistant). Proporciona endpoints REST para todas las
operaciones del sistema.

Puerto: 8008
CORS: Habilitado para localhost:5173 (Vite dev server) y tauri://localhost
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
        # Use environment variable directly - more reliable
        localappdata = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', ''))
        if localappdata:
            debug_file = os.path.join(localappdata, "Narrative Assistant", "early-debug.txt")
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {msg}\n")
                f.flush()
    except Exception as e:
        # Last resort: write to temp
        try:
            import tempfile
            temp_file = os.path.join(tempfile.gettempdir(), "narrative-debug.txt")
            with open(temp_file, 'a', encoding='utf-8') as f:
                f.write(f"{msg} (fallback - error: {e})\n")
                f.flush()
        except:
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

BACKEND_VERSION = "0.3.1"
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
            level=logging.DEBUG,  # DEBUG para ver todo
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(str(log_file), encoding='utf-8', mode='w')  # mode='w' para limpiar cada vez
            ],
            force=True
        )
        print(f"LOGGING TO: {log_file}", flush=True)  # Print para debug
        return log_file
    except Exception as e:
        print(f"ERROR SETTING UP LOGGING: {e}", flush=True)
        # Fallback básico
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
    _early_logger.info(f"sys.path before modifications: {sys.path[:3]}...")  # First 3 entries
    
    # Add user site-packages
    user_site = site.getusersitepackages()
    _write_debug(f"User site: {user_site}")
    _early_logger.info(f"User site-packages: {user_site}")
    if user_site not in sys.path:
        sys.path.insert(0, user_site)
        _write_debug("Added user site to sys.path")
        _early_logger.info(f"✓ Added user site-packages to sys.path")
    
    # Detect if we're using embedded Python (check if python-embed is in executable path)
    using_embedded_python = IS_EMBEDDED_RUNTIME
    
    if using_embedded_python:
        _write_debug("Detected embedded Python - skipping Anaconda detection")
        _early_logger.info("Using embedded Python - Anaconda detection skipped")
    else:
        # Try to find Anaconda/Conda installation only if NOT using embedded Python
        # 1. Check common Anaconda locations
        conda_candidates = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'anaconda3'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'miniconda3'),
            'C:\\ProgramData\\Anaconda3',
            'C:\\ProgramData\\Miniconda3',
        ]
        
        # 2. Also check PATH (but skip Windows Store aliases)
        python_exe = shutil.which("python3") or shutil.which("python")
        if python_exe and 'WindowsApps' not in python_exe:
            conda_candidates.insert(0, os.path.dirname(os.path.dirname(python_exe)))
        
        _write_debug(f"Checking conda candidates: {conda_candidates[:3]}")
        
        for conda_base in conda_candidates:
            conda_site = os.path.join(conda_base, "Lib", "site-packages")
            _write_debug(f"Checking: {conda_site}, exists: {os.path.exists(conda_site)}")
            if os.path.exists(conda_site):
                _write_debug(f"Found Anaconda at: {conda_base}")
                _early_logger.info(f"Detected Anaconda/Conda at: {conda_base}")
                _early_logger.info(f"Conda site-packages: {conda_site}")
                if conda_site not in sys.path:
                    sys.path.insert(0, conda_site)
                    _write_debug("Added conda site to sys.path")
                    _early_logger.info(f"✓ Added Anaconda site-packages to sys.path")
                break
        else:
            _write_debug("No Anaconda installation found")
            _early_logger.info("No Anaconda/Conda installation detected")
    
    _write_debug(f"sys.path after (first 3): {sys.path[:3]}")
    _early_logger.info(f"sys.path after modifications: {sys.path[:3]}...")  # First 3 entries
    
    # Try to detect if numpy is now available
    import importlib.util
    numpy_spec = importlib.util.find_spec("numpy")
    _write_debug(f"numpy found: {numpy_spec is not None}")
    _early_logger.info(f"numpy detection after sys.path setup: {numpy_spec is not None}")
    if numpy_spec:
        _write_debug(f"numpy at: {numpy_spec.origin}")
        _early_logger.info(f"numpy found at: {numpy_spec.origin}")
    
except Exception as e:
    _write_debug(f"ERROR in sys.path setup: {e}")
    _early_logger.error(f"Error during sys.path setup: {e}", exc_info=True)
    pass  # Continue even if this fails

# Now import everything else
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Track installation status
INSTALLING_DEPENDENCIES = False

# Imports del backend narrative_assistant
# NOTA: Estos imports pueden fallar si las dependencias NLP no están instaladas
# El servidor arranca de todas formas y permite instalar las dependencias via API
project_manager = None
entity_repository = None
alert_repository = None
chapter_repository = None
section_repository = None
get_config = None
NA_VERSION = BACKEND_VERSION
Database = None
MODULES_LOADED = False
MODULES_ERROR = None

# Strategy: When frozen (PyInstaller), DON'T load narrative_assistant on startup
# Only load it on-demand after dependencies are installed
# This avoids numpy import conflicts in PyInstaller bundle
if not getattr(sys, 'frozen', False):
    # Not frozen (development mode) - load normally
    try:
        from narrative_assistant.persistence.project import ProjectManager
        from narrative_assistant.persistence.database import get_database, Database
        from narrative_assistant.persistence.chapter import ChapterRepository, SectionRepository
        from narrative_assistant.entities.repository import EntityRepository
        from narrative_assistant.alerts.repository import AlertRepository, AlertStatus, AlertSeverity
        from narrative_assistant.core.config import get_config
        from narrative_assistant.core.result import Result
        from narrative_assistant import __version__ as NA_VERSION

        # Inicializar managers
        project_manager = ProjectManager()
        entity_repository = EntityRepository()
        alert_repository = AlertRepository()
        chapter_repository = ChapterRepository()
        section_repository = SectionRepository()
        MODULES_LOADED = True
        _write_debug("Modules loaded successfully (development mode)")
        
    except Exception as e:
        import logging as _logging
        _logging.basicConfig(level=_logging.INFO)
        _logging.warning(f"NLP modules not loaded: {type(e).__name__}: {e}")
        _logging.info("Server will start in limited mode. Install dependencies via /api/models/download")
        MODULES_ERROR = str(e)
        NA_VERSION = BACKEND_VERSION
else:
    # Frozen (production) - load on demand only
    # Note: In PyInstaller frozen mode, we cannot load narrative_assistant modules
    # that depend on external numpy/scipy/etc due to import conflicts.
    # Solution: User must install full dependencies and they will be available
    # but backend will run in limited mode (no NLP features in frozen bundle)
    _write_debug("Frozen mode: backend will run in API-only mode")
    _write_debug("NLP dependencies should be installed by user but backend operates in limited mode")
    NA_VERSION = BACKEND_VERSION

# Logging already configured at the top of the file in _setup_early_logging()
logger = logging.getLogger(__name__)
logger.info(f"Server starting - NA_VERSION: {NA_VERSION}, MODULES_LOADED: {MODULES_LOADED}")

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
# Helpers
# ============================================================================

def load_narrative_assistant_modules():
    """
    Load narrative_assistant modules on-demand.
    This is called after dependencies are installed in frozen mode.
    
    Returns:
        bool: True if modules loaded successfully, False otherwise
    """
    global MODULES_LOADED, MODULES_ERROR
    global project_manager, entity_repository, alert_repository
    global chapter_repository, section_repository, get_config, Database
    
    if MODULES_LOADED:
        return True
    
    try:
        _write_debug("Attempting to load narrative_assistant modules...")
        
        # Si estamos en modo frozen, limpiar sys.path temporalmente de directorios _MEI
        # para evitar el error "import numpy from its source directory"
        removed_paths = []
        if getattr(sys, 'frozen', False):
            import os
            original_cwd = os.getcwd()
            # Cambiar a un directorio seguro (temp)
            temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
            if os.path.exists(temp_dir):
                os.chdir(temp_dir)
                _write_debug(f"Changed working directory from {original_cwd} to {temp_dir} for import")
            
            # Remover temporalmente _MEI paths
            for path in list(sys.path):
                if "_MEI" in path:
                    sys.path.remove(path)
                    removed_paths.append(path)
            if removed_paths:
                _write_debug(f"Temporarily removed {len(removed_paths)} _MEI paths from sys.path")
                _write_debug(f"sys.path now starts with: {sys.path[:3]}")
        
        try:
            from narrative_assistant.persistence.project import ProjectManager
            from narrative_assistant.persistence.database import get_database, Database as DB
            from narrative_assistant.persistence.chapter import ChapterRepository, SectionRepository
            from narrative_assistant.entities.repository import EntityRepository
            from narrative_assistant.alerts.repository import AlertRepository
            from narrative_assistant.core.config import get_config as get_cfg
            from narrative_assistant import __version__
            
            # Inicializar managers
            _write_debug("Creating ProjectManager...")
            logger.info("Creating ProjectManager...")
            project_manager = ProjectManager()
            _write_debug("ProjectManager created successfully")
            logger.info("ProjectManager created successfully")
            
            # Verificar estado de la base de datos
            try:
                from narrative_assistant.persistence.database import get_database
                db = get_database()
                _write_debug(f"Database path: {db.db_path}")
                logger.info(f"Database path: {db.db_path}")
                # Verificar tablas
                tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [t['name'] for t in tables]
                _write_debug(f"Tables in database: {table_names}")
                logger.info(f"Tables in database: {table_names}")
                if 'projects' not in table_names:
                    _write_debug("WARNING: 'projects' table NOT found!")
                    logger.error("WARNING: 'projects' table NOT found!")
            except Exception as db_check_err:
                _write_debug(f"Error checking database: {db_check_err}")
                logger.error(f"Error checking database: {db_check_err}", exc_info=True)
            
            entity_repository = EntityRepository()
            alert_repository = AlertRepository()
            chapter_repository = ChapterRepository()
            section_repository = SectionRepository()
            get_config = get_cfg
            Database = DB
            MODULES_LOADED = True
            MODULES_ERROR = None
            
            _write_debug("✓ Modules loaded successfully!")
            logger.info("✓ narrative_assistant modules loaded successfully")
        finally:
            # Restaurar sys.path
            if removed_paths:
                sys.path.extend(removed_paths)
                _write_debug(f"Restored {len(removed_paths)} _MEI paths to sys.path")
            # Restaurar directorio de trabajo
            if getattr(sys, 'frozen', False):
                import os
                os.chdir(original_cwd)
                _write_debug(f"Restored working directory to {original_cwd}")

        return True
        
    except Exception as e:
        error_msg = f"Failed to load narrative_assistant modules: {type(e).__name__}: {e}"
        _write_debug(error_msg)
        logger.error(error_msg, exc_info=True)
        MODULES_ERROR = str(e)
        return False


# Minimum required Python version (major, minor)
MIN_PYTHON_VERSION = (3, 10)

def find_python_executable() -> tuple[str | None, str | None, str | None]:
    """
    Encuentra el ejecutable de Python del sistema con version 3.10+.

    Returns:
        Tuple de (python_path, version_string, error_message)
        - Si se encuentra Python valido: (path, version, None)
        - Si no se encuentra: (None, None, error_message)
    """
    if IS_EMBEDDED_RUNTIME:
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        return sys.executable, version_str, None

    import subprocess
    import re

    def check_python_version(python_cmd: str) -> tuple[str | None, str | None]:
        """Verifica si un ejecutable de Python tiene la version requerida."""
        try:
            result = subprocess.run(
                [python_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version from "Python 3.11.5" or similar
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

    # List of Python commands/paths to try
    python_candidates = []

    # 1. Try python3 first (Linux/macOS preferred)
    if python3_path := shutil.which("python3"):
        python_candidates.append(python3_path)

    # 2. Try python (could be Python 3 on many systems)
    if python_path := shutil.which("python"):
        python_candidates.append(python_path)

    # 3. Windows: Try py launcher with version flags
    if sys.platform == 'win32':
        if py_path := shutil.which("py"):
            python_candidates.append(py_path)
            # Also try specific versions via py launcher
            for minor in range(14, 9, -1):  # Try 3.14 down to 3.10
                python_candidates.append(f"py -3.{minor}")

        # 4. Windows: Check common installation paths
        common_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Python',
            Path('C:/Python'),
            Path('C:/Program Files/Python'),
            Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Local' / 'Programs' / 'Python',
        ]

        for base_path in common_paths:
            if base_path.exists():
                # Look for Python3XX directories
                for subdir in sorted(base_path.iterdir(), reverse=True):
                    if subdir.is_dir() and subdir.name.startswith('Python3'):
                        python_exe = subdir / 'python.exe'
                        if python_exe.exists():
                            python_candidates.append(str(python_exe))

    # 5. Check Anaconda/Miniconda paths
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

    # Try each candidate
    for candidate in python_candidates:
        # Handle "py -3.X" format
        if candidate.startswith("py "):
            try:
                parts = candidate.split()
                result = subprocess.run(
                    parts + ["--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_output = result.stdout.strip() or result.stderr.strip()
                    match = re.search(r'Python (\d+)\.(\d+)\.?(\d*)', version_output)
                    if match:
                        major, minor = int(match.group(1)), int(match.group(2))
                        if (major, minor) >= MIN_PYTHON_VERSION:
                            version_str = f"{major}.{minor}"
                            if match.group(3):
                                version_str += f".{match.group(3)}"
                            return candidate, version_str, None
            except Exception:
                continue
        else:
            path, version = check_python_version(candidate)
            if path:
                return path, version, None

    # No suitable Python found
    return None, None, f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ no encontrado. Por favor instala Python desde python.org"


# Cache for Python status (to avoid repeated checks)
_python_status_cache: dict | None = None

def get_python_status() -> dict:
    """
    Obtiene el estado de Python del sistema.

    Returns:
        Dict con: python_available, python_version, python_path, error
    """
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


def convert_numpy_types(obj: Any) -> Any:
    """
    Convierte recursivamente tipos numpy a tipos Python nativos para serialización JSON.

    numpy.bool_ -> bool
    numpy.int64 -> int
    numpy.float64 -> float
    numpy.ndarray -> list
    """
    import numpy as np

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
    relevance_score: Optional[float] = None  # Score de relevancia (0-1) basado en densidad de menciones
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
    excerpt: Optional[str] = None  # Fragmento del texto donde ocurre la alerta
    status: str
    entity_ids: list[int] = []
    confidence: float = 0.0
    created_at: str
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
    extra_data: Optional[dict] = None  # Datos adicionales (sources para inconsistencias, etc.)

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
    return HealthResponse(
        status="ok",
        version=NA_VERSION,
        backend_loaded=MODULES_LOADED,
        timestamp=datetime.now().isoformat(),
    )

@app.get("/api/info")
async def system_info():
    """
    Información del sistema - configuración, GPU, modelos, etc.

    Returns:
        Información detallada del sistema
    """
    if not MODULES_LOADED:
        return ApiResponse(
            success=False,
            message="NLP modules not loaded. Please install dependencies.",
            data={
                "version": NA_VERSION,
                "backend_loaded": False,
                "error": MODULES_ERROR,
            }
        )

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


@app.get("/api/system/python-status")
async def python_status():
    """
    Verifica el estado de Python en el sistema.

    Returns:
        ApiResponse con información de Python disponible
    """
    status = get_python_status()
    return ApiResponse(
        success=True,
        data=status
    )


@app.get("/api/models/status")
async def models_status():
    """
    Verifica el estado de los modelos NLP necesarios.

    Returns:
        ApiResponse con estado de cada modelo (instalado, tamaño, ruta)
    """
    # Obtener estado de Python del sistema
    python_info = get_python_status()

    # Si los módulos no están cargados, retornar estado de dependencias
    if not MODULES_LOADED:
        import importlib.util

        # Log sys.path para debugging
        logger.info(f"=== Checking dependencies ===")
        logger.info(f"MODULES_LOADED: {MODULES_LOADED}")
        logger.info(f"sys.path has {len(sys.path)} entries")
        logger.info(f"First 5 sys.path entries: {sys.path[:5]}")

        deps_status = {}
        for dep in ["numpy", "spacy", "sentence_transformers"]:
            spec = importlib.util.find_spec(dep)
            deps_status[dep] = spec is not None
            if spec:
                logger.info(f"✓ {dep} found at: {spec.origin}")
            else:
                logger.warning(f"✗ {dep} NOT found")

        all_deps_installed = all(deps_status.values())
        
        # EN MODO FROZEN: No auto-cargar módulos, requiere reinicio
        # (evita problemas de import con PyInstaller + numpy)
        needs_restart = False
        if all_deps_installed and getattr(sys, 'frozen', False):
            logger.info("All dependencies detected in frozen mode - restart required to load backend")
            _write_debug("All dependencies detected in frozen mode - restart required to load backend")
            needs_restart = True

        # Si después de intentar cargar, aún no están cargados, retornar estado de dependencias
        if not MODULES_LOADED:
            # Si Python no está disponible, las dependencias no se pueden instalar
            dependencies_needed = True
            python_error = python_info["error"] if not python_info["python_available"] else None

            return ApiResponse(
                success=True,
                data={
                    "backend_loaded": False,
                    "dependencies_needed": dependencies_needed,
                    "dependencies_status": deps_status,
                    "all_installed": all_deps_installed,
                    "needs_restart": needs_restart,
                    "installing": INSTALLING_DEPENDENCIES,
                    "python_available": python_info["python_available"],
                    "python_version": python_info["python_version"],
                    "python_path": python_info["python_path"],
                    "python_error": python_error,
                }
            )
    
    try:
        from narrative_assistant.core.model_manager import get_model_manager

        manager = get_model_manager()
        status = manager.get_all_models_status()

        # Añadir info de Ollama
        import shutil
        import subprocess

        ollama_installed = shutil.which("ollama") is not None
        ollama_models = []

        if ollama_installed:
            try:
                output = subprocess.check_output(
                    ["ollama", "list"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=5
                )
                # Parse output to get model names
                for line in output.strip().split("\n")[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        ollama_models.append(model_name)
            except Exception:
                pass

        return ApiResponse(
            success=True,
            data={
                "nlp_models": status,
                "ollama": {
                    "installed": ollama_installed,
                    "models": ollama_models,
                },
                "all_required_installed": all(
                    info.get("installed", False)
                    for info in status.values()
                ),
            },
        )
    except ImportError:
        return ApiResponse(
            success=False,
            error="Model manager not available",
            data={"all_required_installed": False},
        )
    except Exception as e:
        logger.error(f"Error checking models status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class DownloadModelsRequest(BaseModel):
    """Request para descargar modelos"""
    models: list[str] = Field(default=["spacy", "embeddings"], description="Modelos a descargar")
    force: bool = Field(default=False, description="Forzar re-descarga")


@app.post("/api/dependencies/install")
async def install_dependencies():
    """
    Instala las dependencias Python necesarias (numpy, spacy, sentence-transformers, etc.).

    Este endpoint instala las dependencias y luego intenta recargar los módulos.
    NO requiere reinicio manual de la aplicación.

    Returns:
        ApiResponse indicando que la instalación ha comenzado
    """
    import subprocess
    import importlib

    # Verificar que Python está disponible antes de intentar instalar
    python_info = get_python_status()
    if not python_info["python_available"]:
        raise HTTPException(
            status_code=400,
            detail=python_info["error"] or f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ no encontrado. Por favor instala Python desde python.org"
        )

    def install_task():
        global MODULES_LOADED, MODULES_ERROR, INSTALLING_DEPENDENCIES
        global project_manager, entity_repository, alert_repository
        global chapter_repository, section_repository, get_config, Database

        INSTALLING_DEPENDENCIES = True

        try:
            # Usar el path de Python ya verificado
            python_exe = python_info["python_path"]
            logger.info(f"Starting dependencies installation using: {python_exe} (version {python_info['python_version']})")
            
            # Lista de dependencias necesarias
            dependencies = [
                "numpy>=1.24.0",
                "spacy>=3.7.0",
                "sentence-transformers>=2.2.0",
                "transformers>=4.30.0",
                "torch>=2.0.0",
                "pandas>=2.0.0",
                "scikit-learn>=1.3.0",
            ]
            
            # Configurar subprocess para no mostrar ventana en Windows
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NO_WINDOW

            # Instalar usando pip con --user para evitar problemas de permisos
            for dep in dependencies:
                logger.info(f"Installing {dep}...")
                result = subprocess.run(
                    [python_exe, "-m", "pip", "install", "--user", "--no-cache-dir", dep],
                    capture_output=True,
                    text=True,
                    creationflags=creation_flags
                )
                if result.returncode != 0:
                    logger.error(f"Failed to install {dep}: {result.stderr}")
                    raise Exception(f"Failed to install {dep}: {result.stderr}")
                logger.info(f"✓ {dep} installed")
            
            logger.info("All dependencies installed successfully!")
            logger.info("Attempting to load narrative_assistant modules...")
            
            # Usar la función helper para cargar los módulos
            if load_narrative_assistant_modules():
                INSTALLING_DEPENDENCIES = False
                logger.info("✓ Modules loaded successfully! Backend is now fully functional.")
            else:
                logger.error("Failed to load modules after installation")
                logger.info("You may need to restart the application.")
                raise Exception("Failed to load narrative_assistant modules after installation")
            
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}", exc_info=True)
            INSTALLING_DEPENDENCIES = False
            MODULES_ERROR = str(e)
    
    # Ejecutar en segundo plano
    import threading
    thread = threading.Thread(target=install_task, daemon=True)
    thread.start()
    
    return ApiResponse(
        success=True,
        message="Dependencies installation started. This may take several minutes. Check /api/models/status for progress.",
        data={"installing": True}
    )


@app.post("/api/models/download")
async def download_models(request: DownloadModelsRequest):
    """
    Descarga los modelos NLP necesarios.

    Este endpoint inicia la descarga de modelos en segundo plano.
    El frontend debe hacer polling a /api/models/status para ver el progreso.

    Args:
        request: Modelos a descargar y opciones

    Returns:
        ApiResponse indicando que la descarga ha comenzado
    """
    # Si las dependencias no están instaladas, retornar error específico
    if not MODULES_LOADED:
        raise HTTPException(
            status_code=400,
            detail="Dependencies not installed. Please install dependencies first via /api/dependencies/install"
        )
    
    try:
        from narrative_assistant.core.model_manager import get_model_manager, ModelType
        import threading

        manager = get_model_manager()

        def download_task():
            for model_name in request.models:
                try:
                    if model_name == "spacy":
                        manager.ensure_model(ModelType.SPACY, force_download=request.force)
                    elif model_name == "embeddings":
                        manager.ensure_model(ModelType.EMBEDDINGS, force_download=request.force)
                    logger.info(f"Model {model_name} downloaded successfully")
                except Exception as e:
                    logger.error(f"Error downloading {model_name}: {e}")

        # Ejecutar en segundo plano
        thread = threading.Thread(target=download_task, daemon=True)
        thread.start()

        return ApiResponse(
            success=True,
            message="Model download started",
            data={"models": request.models},
        )

    except ImportError as e:
        logger.error(f"Import error in download_models: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Model manager not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error starting model download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/capabilities")
async def system_capabilities():
    """
    Capacidades del sistema - detección de hardware y métodos disponibles.

    Retorna información detallada sobre:
    - Hardware disponible (GPU, CPU, memoria)
    - Métodos NLP disponibles con defaults recomendados
    - Modelos Ollama disponibles
    - Configuración recomendada según hardware

    Returns:
        ApiResponse con capacidades detalladas del sistema
    """
    try:
        from narrative_assistant.core.device import get_device_detector, DeviceType

        detector = get_device_detector()

        # Detectar dispositivos disponibles
        cuda_device = detector.detect_cuda()
        mps_device = detector.detect_mps()
        cpu_device = detector.get_cpu_info()
        has_cupy = detector.detect_cupy() if cuda_device else False

        # Determinar GPU principal
        gpu_info = None
        gpu_type = "none"
        gpu_memory_gb = None

        if cuda_device:
            gpu_info = {
                "type": "cuda",
                "name": cuda_device.device_name,
                "memory_gb": cuda_device.memory_gb,
                "device_id": cuda_device.device_id,
            }
            gpu_type = "cuda"
            gpu_memory_gb = cuda_device.memory_gb
        elif mps_device:
            gpu_info = {
                "type": "mps",
                "name": "Apple Silicon GPU",
                "memory_gb": None,  # Shared with system
                "device_id": 0,
            }
            gpu_type = "mps"

        # Detectar estado de Ollama (instalado, corriendo, modelos)
        ollama_models = []
        ollama_available = False  # Si está corriendo
        ollama_installed = False  # Si está instalado en el sistema

        # Verificar si está instalado usando el manager (detecta rutas de Windows)
        try:
            from narrative_assistant.llm.ollama_manager import get_ollama_manager
            manager = get_ollama_manager()
            ollama_installed = manager.is_installed
        except Exception:
            import shutil
            ollama_installed = shutil.which("ollama") is not None

        # Verificar si está corriendo y obtener modelos
        import urllib.request
        import urllib.error
        import json as json_module
        try:
            ollama_host = "http://localhost:11434"
            logger.info(f"Verificando Ollama en {ollama_host}/api/tags...")
            req = urllib.request.Request(f"{ollama_host}/api/tags")
            with urllib.request.urlopen(req, timeout=10.0) as response:
                if response.status == 200:
                    ollama_available = True
                    data = json_module.loads(response.read().decode('utf-8'))
                    ollama_models = [
                        {
                            "name": model.get("name", "").split(":")[0],
                            "size": model.get("size", 0),
                            "modified": model.get("modified_at", ""),
                        }
                        for model in data.get("models", [])
                    ]
                    logger.info(f"Ollama detectado: {len(ollama_models)} modelo(s)")
        except urllib.error.URLError as e:
            logger.info(f"Ollama no disponible (conexión): {e.reason}")
        except TimeoutError:
            logger.info("Ollama no disponible (timeout)")
        except Exception as e:
            logger.info(f"Ollama no disponible ({type(e).__name__}): {e}")

        # Verificar LanguageTool (puede intentar iniciarlo si está instalado)
        lt_available = _check_languagetool_available()

        # Definir métodos NLP disponibles
        # Basado en hardware, definir defaults recomendados
        has_gpu = gpu_type in ("cuda", "mps")
        has_high_vram = gpu_memory_gb and gpu_memory_gb >= 6.0

        nlp_methods = {
            "coreference": {
                "embeddings": {
                    "name": "Análisis de significado similar",
                    "description": "Detecta cuándo dos expresiones se refieren a lo mismo por su significado",
                    "weight": 0.30,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
                "llm": {
                    "name": "Analizador inteligente",
                    "description": "Comprende el contexto para resolver referencias complejas",
                    "weight": 0.35,
                    "available": ollama_available and len(ollama_models) > 0,
                    "default_enabled": ollama_available and (has_gpu or len(ollama_models) > 0),
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
                "morpho": {
                    "name": "Análisis de estructura gramatical",
                    "description": "Analiza género, número y concordancia entre palabras",
                    "weight": 0.20,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "heuristics": {
                    "name": "Reglas narrativas",
                    "description": "Patrones comunes en textos narrativos (proximidad, diálogos...)",
                    "weight": 0.15,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
            },
            "ner": {
                "spacy": {
                    "name": "Detector de nombres",
                    "description": "Identifica nombres propios automáticamente en el texto",
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
                "gazetteer": {
                    "name": "Diccionario de nombres",
                    "description": "Lista de nombres propios conocidos (más precisión)",
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "llm": {
                    "name": "Detección inteligente",
                    "description": "Usa contexto para identificar entidades ambiguas",
                    "available": ollama_available,
                    "default_enabled": ollama_available and has_gpu,
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
            },
            "grammar": {
                "spacy_rules": {
                    "name": "Corrector básico",
                    "description": "Reglas gramaticales esenciales del español",
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "languagetool": {
                    "name": "Corrector avanzado",
                    "description": "Más de 2000 reglas gramaticales (requiere Java)",
                    "available": lt_available,
                    "default_enabled": lt_available,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "llm": {
                    "name": "LLM Grammar",
                    "description": "Análisis contextual con LLM",
                    "available": ollama_available,
                    "default_enabled": False,  # Deshabilitado por defecto (lento)
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
            },
            "spelling": {
                "patterns": {
                    "name": "Patrones",
                    "description": "Reglas y patrones comunes de errores ortográficos",
                    "weight": 0.26,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "languagetool": {
                    "name": "LanguageTool",
                    "description": "Servidor de ortografía avanzado (requiere Java)",
                    "weight": 0.24,
                    "available": lt_available,
                    "default_enabled": lt_available,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "symspell": {
                    "name": "SymSpell",
                    "description": "Algoritmo de alta velocidad para corrección",
                    "weight": 0.16,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "hunspell": {
                    "name": "Hunspell",
                    "description": "Diccionario profesional de español",
                    "weight": 0.14,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "pyspellchecker": {
                    "name": "PySpellChecker",
                    "description": "Corrector Python con diccionario incluido",
                    "weight": 0.08,
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "beto": {
                    "name": "BETO ML",
                    "description": "Modelo BERT en español para detección contextual",
                    "weight": 0.12,
                    "available": has_gpu,
                    "default_enabled": has_gpu,
                    "requires_gpu": True,
                    "recommended_gpu": True,
                },
                "llm_arbitrator": {
                    "name": "LLM Arbitrador",
                    "description": "Resuelve conflictos entre correctores con IA",
                    "available": ollama_available,
                    "default_enabled": ollama_available and has_gpu,
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
            },
            "character_knowledge": {
                "rules": {
                    "name": "Reglas",
                    "description": "Extracción basada en patrones y heurísticas",
                    "available": True,
                    "default_enabled": True,
                    "requires_gpu": False,
                    "recommended_gpu": False,
                },
                "llm": {
                    "name": "LLM",
                    "description": "Extracción inteligente con comprensión contextual",
                    "available": ollama_available,
                    "default_enabled": ollama_available and has_gpu,
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
                "hybrid": {
                    "name": "Híbrido",
                    "description": "Combina reglas y LLM para mejor cobertura",
                    "available": ollama_available,
                    "default_enabled": False,
                    "requires_gpu": False,
                    "recommended_gpu": True,
                },
            },
        }

        # Modelos Ollama recomendados según hardware
        ollama_recommendations = []
        if has_high_vram:
            ollama_recommendations = ["qwen2.5", "mistral", "llama3.2"]
        elif has_gpu:
            ollama_recommendations = ["llama3.2", "qwen2.5"]
        else:
            ollama_recommendations = ["llama3.2"]  # 3B funciona en CPU

        return ApiResponse(
            success=True,
            data={
                "hardware": {
                    "gpu": gpu_info,
                    "gpu_type": gpu_type,
                    "has_gpu": has_gpu,
                    "has_high_vram": has_high_vram,
                    "has_cupy": has_cupy,
                    "cpu": {
                        "name": cpu_device.device_name,
                    },
                },
                "ollama": {
                    "installed": ollama_installed,
                    "available": ollama_available,
                    "models": ollama_models,
                    "recommended_models": ollama_recommendations,
                },
                "nlp_methods": nlp_methods,
                "recommended_config": {
                    "device_preference": gpu_type if has_gpu else "cpu",
                    "spacy_gpu_enabled": has_gpu and has_cupy,
                    "embeddings_gpu_enabled": has_gpu,
                    "batch_size": 64 if has_gpu else 16,
                    # Detectores con validación LLM - solo recomendar si hay GPU o modelos rápidos
                    "detectors": {
                        "anacoluto_llm_validation": has_gpu and ollama_available,
                        "pov_llm_validation": has_gpu and ollama_available,
                        "use_llm_review": has_gpu and ollama_available,  # Revisión global LLM
                    },
                },
            },
        )
    except Exception as e:
        logger.error(f"Error getting system capabilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _check_languagetool_available() -> bool:
    """Verifica si LanguageTool está disponible, intentando iniciarlo si está instalado."""
    try:
        import httpx
        response = httpx.get("http://localhost:8081/v2/check", timeout=2.0)
        if response.status_code in (200, 400):  # 400 = missing params but server up
            return True
    except Exception:
        pass

    # Si no está corriendo, intentar iniciarlo
    try:
        from narrative_assistant.nlp.grammar import (
            is_languagetool_installed,
            ensure_languagetool_running,
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


def generate_person_aliases(canonical_name: str, all_canonical_names: set[str]) -> list[str]:
    """
    Genera aliases automáticos para nombres de personas.

    Para nombres compuestos como "María García", extrae partes útiles
    que pueden usarse como alias para búsqueda de menciones.

    Args:
        canonical_name: Nombre canónico de la entidad (ej: "María García")
        all_canonical_names: Set de todos los nombres canónicos para evitar conflictos

    Returns:
        Lista de aliases generados (ej: ["María"])
    """
    aliases = []
    parts = canonical_name.split()

    # Solo procesar nombres con múltiples palabras
    if len(parts) < 2:
        return aliases

    # Extraer el primer nombre como alias si:
    # 1. Tiene al menos 3 caracteres
    # 2. No es un título común (Don, Doña, Señor, etc.)
    # 3. No es ya un nombre canónico de otra entidad
    first_name = parts[0]
    titles = {"don", "doña", "señor", "señora", "sr", "sra", "dr", "dra",
              "doctor", "doctora", "padre", "madre", "hermano", "hermana",
              "el", "la", "los", "las"}

    if (len(first_name) >= 3 and
        first_name.lower() not in titles and
        first_name.lower() not in {n.lower() for n in all_canonical_names}):
        aliases.append(first_name)

    # Para nombres con 3+ partes (ej: "María José García"),
    # también considerar "María José" como alias
    if len(parts) >= 3:
        first_two = " ".join(parts[:2])
        if (first_two.lower() not in {n.lower() for n in all_canonical_names} and
            first_two != canonical_name):
            aliases.append(first_two)

    return aliases


# ============================================================================
# Helper functions - Source of Truth para estadísticas
# ============================================================================

def _get_project_stats(project_id: int, db) -> dict:
    """
    Obtiene estadísticas del proyecto directamente desde la BD.

    Esta es la ÚNICA fuente de verdad para conteos.
    Evita discordancias entre project.chapter_count y conteo real.

    Args:
        project_id: ID del proyecto
        db: Instancia de Database (usa db.fetchone para queries)

    Returns:
        dict con chapter_count, entity_count, alert_count, word_count
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
        # Contar capítulos
        row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM chapters WHERE project_id = ?",
            (project_id,)
        )
        stats["chapter_count"] = row["cnt"] if row else 0

        # Contar entidades
        row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM entities WHERE project_id = ?",
            (project_id,)
        )
        stats["entity_count"] = row["cnt"] if row else 0

        # Contar alertas abiertas
        row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM alerts WHERE project_id = ? AND status = 'open'",
            (project_id,)
        )
        stats["open_alerts_count"] = row["cnt"] if row else 0

        # Sumar palabras de capítulos (más preciso que project.word_count)
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

    Args:
        entity_id: ID de la entidad
        project_id: ID del proyecto

    Returns:
        tuple (entity, error_response):
        - Si es válida: (entity, None)
        - Si hay error: (None, ApiResponse con error)
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

    Args:
        alert_id: ID de la alerta
        project_id: ID del proyecto

    Returns:
        tuple (alert, error_response):
        - Si es válida: (alert, None)
        - Si hay error: (None, ApiResponse con error)
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
            logger.error("list_projects: project_manager is None")
            return ApiResponse(success=False, error="Project manager not initialized")

        # Log database info for debugging
        try:
            db = get_database()
            logger.info(f"list_projects: Database path = {db.db_path}")
            # Check if projects table exists
            tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [t['name'] for t in tables]
            logger.info(f"list_projects: Tables in DB = {table_names}")
            if 'projects' not in table_names:
                logger.error("list_projects: 'projects' table does NOT exist!")
                return ApiResponse(success=False, error="Database not initialized properly - 'projects' table missing")
        except Exception as db_err:
            logger.error(f"list_projects: Error checking database: {db_err}", exc_info=True)

        projects = project_manager.list_all()
        db = get_database()

        projects_data = []
        for p in projects:
            # Obtener estadísticas desde la BD (source of truth)
            stats = _get_project_stats(p.id, db)

            # Determinar severidad más alta de alertas
            highest_severity = None
            if alert_repository:
                alerts_result = alert_repository.get_by_project(p.id)
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

        # Verificar si el estado "analyzing" está atascado (no hay análisis real en progreso)
        # Esto puede ocurrir si el servidor se reinició durante un análisis
        if project.analysis_status in ['analyzing', 'in_progress', 'pending']:
            # Si no hay análisis activo en memoria, el estado está atascado
            if project_id not in analysis_progress_storage:
                logger.warning(f"Project {project_id} has stuck analysis_status='{project.analysis_status}', resetting to 'completed'")
                project.analysis_status = 'completed'
                project.analysis_progress = 1.0
                try:
                    project_manager.update(project)
                except Exception as e:
                    logger.warning(f"Could not update stuck analysis status: {e}")

        # Obtener estadísticas desde la BD (source of truth)
        db = get_database()
        stats = _get_project_stats(project_id, db)

        # Obtener severidad más alta de alertas
        highest_severity = None
        if alert_repository:
            alerts_result = alert_repository.get_by_project(project.id)
            if alerts_result.is_success:
                open_alerts = [a for a in alerts_result.value if a.status == AlertStatus.OPEN]
                if open_alerts:
                    severity_priority = {"critical": 3, "warning": 2, "info": 1}
                    highest_severity = max(
                        (a.severity.value for a in open_alerts),
                        key=lambda s: severity_priority.get(s, 0)
                    )

        # Extraer document_type y recommended_analysis de settings
        project_settings = project.settings or {}
        document_type = project_settings.get("document_type", "unknown")
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


@app.get("/api/projects/{project_id}/analysis-status", response_model=ApiResponse)
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
        # Obtener proyecto a través del project_manager (la forma correcta)
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Obtener estadísticas para determinar qué está ejecutado
        db = get_database()
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
            "register_analysis": has_chapters,  # Análisis de registro disponible
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
            document_text = raw_doc.full_text

            if not document_text or not document_text.strip():
                raise HTTPException(status_code=400, detail="El documento está vacío o no se pudo leer el contenido")

            logger.info(f"Document parsed: {len(document_text)} chars, {len(document_text.split())} words")

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
async def list_entities(
    project_id: int,
    min_relevance: Optional[float] = None,
    min_mentions: Optional[int] = None,
    entity_type: Optional[str] = None,
):
    """
    Lista todas las entidades de un proyecto con filtros opcionales.

    La relevancia se calcula como:
    - Densidad de menciones: (menciones / palabras_documento) * factor_normalizacion
    - Entidades con pocas menciones en documentos largos tienen baja relevancia
    - Entidades con varias menciones en documentos cortos tienen alta relevancia

    Args:
        project_id: ID del proyecto
        min_relevance: Score mínimo de relevancia (0-1) para incluir entidad
        min_mentions: Número mínimo de menciones para incluir entidad
        entity_type: Filtrar por tipo (character, location, object, etc.)

    Returns:
        ApiResponse con lista de entidades
    """
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id)

        # Obtener word_count del proyecto para calcular densidad
        project_result = project_manager.get(project_id)
        project = project_result.value if project_result.is_success else None
        word_count = project.word_count if project and project.word_count else 50000  # Default

        # Obtener capítulos para calcular first_mention_chapter
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        # Crear mapa de posición -> capítulo
        def get_chapter_for_position(pos: int) -> Optional[int]:
            if pos is None:
                return None
            for ch in chapters:
                if ch.start_char <= pos < ch.end_char:
                    return ch.chapter_number
            return 1  # Default al capítulo 1 si no se encuentra

        # Calcular relevance_score para cada entidad
        # Fórmula: menciones / (palabras / 1000) normalizado
        # Una entidad mencionada 5 veces en 1000 palabras es muy relevante
        # Una entidad mencionada 2 veces en 100000 palabras es poco relevante
        words_in_thousands = max(word_count / 1000, 1)

        entities_data = []
        for e in entities:
            mention_count = e.mention_count or 0

            # Calcular relevance_score (0-1)
            # Menciones por cada 1000 palabras, normalizado con sigmoid-like
            mentions_per_k = mention_count / words_in_thousands
            # Sigmoid suave: score = menciones_per_k / (menciones_per_k + 2)
            # Con 2 menciones/1000 palabras -> 0.5
            # Con 5 menciones/1000 palabras -> 0.71
            # Con 10 menciones/1000 palabras -> 0.83
            relevance_score = mentions_per_k / (mentions_per_k + 2) if mention_count > 0 else 0

            # Aplicar filtros
            if min_relevance is not None and relevance_score < min_relevance:
                continue
            if min_mentions is not None and mention_count < min_mentions:
                continue
            if entity_type is not None and e.entity_type.value != entity_type:
                continue

            # Calcular first_mention_chapter desde first_appearance_char
            first_mention_chapter = get_chapter_for_position(e.first_appearance_char)

            entities_data.append(
                EntityResponse(
                    id=e.id,
                    project_id=e.project_id,
                    entity_type=e.entity_type.value,
                    canonical_name=e.canonical_name,
                    aliases=e.aliases or [],
                    importance=e.importance.value,
                    description=e.description,
                    first_appearance_char=e.first_appearance_char,
                    first_mention_chapter=first_mention_chapter,
                    mention_count=mention_count,
                    is_active=e.is_active if hasattr(e, 'is_active') else True,
                    merged_from_ids=e.merged_from_ids or [],
                    relevance_score=round(relevance_score, 3),
                    created_at=e.created_at.isoformat() if hasattr(e, 'created_at') and e.created_at else None,
                    updated_at=e.updated_at.isoformat() if hasattr(e, 'updated_at') and e.updated_at else None,
                )
            )

        return ApiResponse(success=True, data=entities_data)
    except Exception as e:
        logger.error(f"Error listing entities for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/entities/similarity", response_model=ApiResponse)
async def calculate_entity_similarity(project_id: int, request: Request):
    """
    Calcula la similitud semántica entre múltiples entidades.

    Útil para el preview de fusión: muestra qué tan relacionadas están las entidades
    antes de confirmar la fusión.

    Args:
        project_id: ID del proyecto
        request: Body con entity_ids (lista de IDs a comparar)

    Returns:
        ApiResponse con matriz de similitud entre pares de entidades
    """
    try:
        data = await request.json()
        entity_ids = data.get('entity_ids', [])

        if len(entity_ids) < 2:
            return ApiResponse(
                success=False,
                error="Se requieren al menos 2 entidades para calcular similitud"
            )

        entity_repo = entity_repository

        # Obtener las entidades
        entities = []
        for entity_id in entity_ids:
            entity = entity_repo.get_entity(entity_id)
            if entity and entity.project_id == project_id:
                entities.append(entity)

        if len(entities) < 2:
            return ApiResponse(success=False, error="No se encontraron suficientes entidades válidas")

        # Calcular similitud usando SemanticFusionService
        try:
            from narrative_assistant.entities.semantic_fusion import get_semantic_fusion_service
            fusion_service = get_semantic_fusion_service()
        except ImportError:
            # Fallback: similitud basada en nombres (Jaccard)
            fusion_service = None

        similarity_matrix = []

        for i, ent1 in enumerate(entities):
            for j, ent2 in enumerate(entities):
                if i >= j:
                    continue  # Evitar duplicados y compararse consigo mismo

                if fusion_service:
                    # Usar embeddings semánticos
                    similarity = fusion_service.compute_semantic_similarity(ent1, ent2)
                    result = fusion_service.should_merge(ent1, ent2)
                    reason = result.reason
                    method = result.method
                else:
                    # Fallback: similitud basada en nombres
                    name1 = ent1.canonical_name.lower()
                    name2 = ent2.canonical_name.lower()

                    # Jaccard sobre caracteres
                    set1 = set(name1)
                    set2 = set(name2)
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    similarity = intersection / union if union > 0 else 0
                    reason = "Similitud basada en caracteres (fallback)"
                    method = "jaccard"

                similarity_matrix.append({
                    "entity1_id": ent1.id,
                    "entity1_name": ent1.canonical_name,
                    "entity2_id": ent2.id,
                    "entity2_name": ent2.canonical_name,
                    "similarity": round(similarity, 3),
                    "should_merge": similarity >= 0.65,
                    "reason": reason,
                    "method": method
                })

        # Calcular score promedio de fusión
        avg_similarity = sum(s["similarity"] for s in similarity_matrix) / len(similarity_matrix) if similarity_matrix else 0

        return ApiResponse(success=True, data={
            "pairs": similarity_matrix,
            "average_similarity": round(avg_similarity, 3),
            "entity_count": len(entities),
            "recommendation": "merge" if avg_similarity >= 0.5 else "review" if avg_similarity >= 0.3 else "keep_separate"
        })

    except Exception as e:
        logger.error(f"Error calculating entity similarity: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/entities/preview-merge", response_model=ApiResponse)
async def preview_merge_entities(project_id: int, request: Request):
    """
    Preview de fusión de entidades con análisis de similitud detallado y detección de conflictos.

    Proporciona información detallada antes de confirmar la fusión:
    - Scores de similitud (nombre Levenshtein/Jaro-Winkler + semántica)
    - Preview del resultado fusionado
    - Detección de conflictos de atributos contradictorios

    Args:
        project_id: ID del proyecto
        request: Body con entity_ids (lista de IDs a fusionar)

    Returns:
        ApiResponse con preview detallado de la fusión
    """
    try:
        data = await request.json()
        entity_ids = data.get('entity_ids', [])

        if len(entity_ids) < 2:
            return ApiResponse(
                success=False,
                error="Se requieren al menos 2 entidades para previsualizar fusión"
            )

        entity_repo = entity_repository

        # Obtener las entidades
        entities = []
        for entity_id in entity_ids:
            entity = entity_repo.get_entity(entity_id)
            if entity and entity.project_id == project_id:
                entities.append(entity)

        if len(entities) < 2:
            return ApiResponse(success=False, error="No se encontraron suficientes entidades válidas")

        # =====================================================================
        # 1. Calcular similitud detallada entre pares
        # =====================================================================
        try:
            from narrative_assistant.entities.semantic_fusion import get_semantic_fusion_service
            from narrative_assistant.entities.fusion import EntityFusionService
            semantic_service = get_semantic_fusion_service()
            fusion_service = EntityFusionService(repository=entity_repo)
        except ImportError:
            semantic_service = None
            fusion_service = None

        # Calcular similitud por nombre (Levenshtein/SequenceMatcher)
        def compute_name_similarity(name1: str, name2: str) -> dict:
            """Calcula múltiples métricas de similitud por nombre."""
            from difflib import SequenceMatcher
            import unicodedata

            def normalize(s):
                return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()

            n1 = normalize(name1)
            n2 = normalize(name2)

            # SequenceMatcher ratio (similar a Levenshtein normalizado)
            sequence_ratio = SequenceMatcher(None, n1, n2).ratio()

            # Jaro-Winkler approximation (usando quick_ratio para eficiencia)
            quick_ratio = SequenceMatcher(None, n1, n2).quick_ratio()

            # Contención: si un nombre contiene al otro
            containment = 0.0
            if n1 in n2 or n2 in n1:
                shorter = min(len(n1), len(n2))
                longer = max(len(n1), len(n2))
                containment = shorter / longer if longer > 0 else 0

            return {
                "levenshtein": round(sequence_ratio, 3),
                "jaro_winkler": round(quick_ratio, 3),
                "containment": round(containment, 3),
                "combined": round((sequence_ratio * 0.5 + quick_ratio * 0.3 + containment * 0.2), 3)
            }

        similarity_pairs = []
        for i, ent1 in enumerate(entities):
            for j, ent2 in enumerate(entities):
                if i >= j:
                    continue

                # Similitud por nombre
                name_sim = compute_name_similarity(ent1.canonical_name, ent2.canonical_name)

                # Similitud semántica (embeddings)
                semantic_sim = 0.0
                semantic_reason = ""
                if semantic_service:
                    try:
                        semantic_sim = semantic_service.compute_semantic_similarity(ent1, ent2)
                        result = semantic_service.should_merge(ent1, ent2)
                        semantic_reason = result.reason
                    except Exception as e:
                        logger.warning(f"Error computing semantic similarity: {e}")
                        semantic_sim = 0.0

                # Score combinado (40% nombre, 60% semántica si disponible)
                if semantic_sim > 0:
                    combined_score = name_sim["combined"] * 0.4 + semantic_sim * 0.6
                else:
                    combined_score = name_sim["combined"]

                similarity_pairs.append({
                    "entity1_id": ent1.id,
                    "entity1_name": ent1.canonical_name,
                    "entity2_id": ent2.id,
                    "entity2_name": ent2.canonical_name,
                    "name_similarity": name_sim,
                    "semantic_similarity": round(semantic_sim, 3),
                    "semantic_reason": semantic_reason,
                    "combined_score": round(combined_score, 3),
                    "recommendation": "merge" if combined_score >= 0.6 else "review" if combined_score >= 0.4 else "keep_separate"
                })

        # =====================================================================
        # 2. Calcular preview del resultado fusionado
        # =====================================================================

        # Recopilar todos los nombres/aliases
        all_names = set()
        all_aliases = set()
        for entity in entities:
            all_names.add(entity.canonical_name)
            all_aliases.update(entity.aliases)

        # Calcular menciones totales
        total_mentions = sum(e.mention_count for e in entities)

        # Determinar el tipo más común
        type_counts = {}
        for entity in entities:
            t = entity.entity_type.value
            type_counts[t] = type_counts.get(t, 0) + entity.mention_count
        suggested_type = max(type_counts.keys(), key=lambda x: type_counts[x]) if type_counts else entities[0].entity_type.value

        # Sugerir nombre canónico (el más largo que sea nombre propio)
        def score_canonical_name(name: str) -> int:
            score = 0
            words = name.split()
            # Preferir nombres con 2-3 palabras
            if 2 <= len(words) <= 3:
                score += 20
            # Preferir nombres que empiezan con mayúscula
            if name and name[0].isupper():
                score += 30
            # Penalizar si empieza con artículo
            articles = ['el', 'la', 'los', 'las', 'un', 'una']
            if words and words[0].lower() in articles:
                score -= 50
            # Preferir nombres más largos (hasta cierto punto)
            score += min(len(name), 25)
            return score

        suggested_canonical = max(all_names, key=score_canonical_name)
        suggested_aliases = list(all_names - {suggested_canonical}) + list(all_aliases)

        merged_preview = {
            "suggested_canonical_name": suggested_canonical,
            "suggested_aliases": list(set(suggested_aliases)),
            "suggested_type": suggested_type,
            "total_mentions": total_mentions,
            "entities_to_merge": len(entities),
            "all_names": list(all_names),
        }

        # =====================================================================
        # 3. Detectar conflictos de atributos
        # =====================================================================
        conflicts = []
        all_attributes = {}  # {(category, name): [(value, entity_name, entity_id), ...]}

        for entity in entities:
            attrs = entity_repo.get_attributes_by_entity(entity.id)
            for attr in attrs:
                key = (attr.get('attribute_type', attr.get('category', '')),
                       attr.get('attribute_key', attr.get('name', '')))
                value = attr.get('attribute_value', attr.get('value', ''))

                if key not in all_attributes:
                    all_attributes[key] = []
                all_attributes[key].append({
                    "value": value,
                    "entity_name": entity.canonical_name,
                    "entity_id": entity.id,
                    "confidence": attr.get('confidence', 1.0)
                })

        # Detectar conflictos (mismo atributo, diferentes valores)
        for (category, attr_name), values in all_attributes.items():
            unique_values = set(v["value"].lower().strip() for v in values)
            if len(unique_values) > 1:
                conflicts.append({
                    "category": category,
                    "attribute_name": attr_name,
                    "conflicting_values": [
                        {
                            "value": v["value"],
                            "entity_name": v["entity_name"],
                            "entity_id": v["entity_id"],
                            "confidence": v["confidence"]
                        }
                        for v in values
                    ],
                    "severity": "high" if category in ["physical", "identity"] else "medium"
                })

        # Ordenar conflictos por severidad
        severity_order = {"high": 0, "medium": 1, "low": 2}
        conflicts.sort(key=lambda c: severity_order.get(c["severity"], 2))

        # =====================================================================
        # 4. Calcular recomendación general
        # =====================================================================
        avg_similarity = sum(p["combined_score"] for p in similarity_pairs) / len(similarity_pairs) if similarity_pairs else 0
        has_high_conflicts = any(c["severity"] == "high" for c in conflicts)

        if avg_similarity >= 0.6 and not has_high_conflicts:
            recommendation = "merge"
            recommendation_reason = "Alta similitud sin conflictos significativos"
        elif avg_similarity >= 0.4:
            recommendation = "review"
            if has_high_conflicts:
                recommendation_reason = "Similitud aceptable pero hay conflictos de atributos que requieren revisión"
            else:
                recommendation_reason = "Similitud media, revisar antes de fusionar"
        else:
            recommendation = "keep_separate"
            recommendation_reason = "Baja similitud, las entidades podrían ser diferentes"

        return ApiResponse(success=True, data={
            "similarity": {
                "pairs": similarity_pairs,
                "average_score": round(avg_similarity, 3),
            },
            "merged_preview": merged_preview,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "has_critical_conflicts": has_high_conflicts,
            "recommendation": recommendation,
            "recommendation_reason": recommendation_reason,
            "entity_count": len(entities)
        })

    except Exception as e:
        logger.error(f"Error previewing entity merge: {e}", exc_info=True)
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

        # Implementación de la fusión de entidades
        merged_count = 0
        source_entity_ids = []
        source_snapshots = []
        canonical_names_before = []
        combined_aliases = set(primary_entity.aliases)

        for entity_id in entity_ids:
            if entity_id == primary_entity_id:
                continue  # No fusionar consigo misma

            entity = entity_repo.get_entity(entity_id)
            if not entity or entity.project_id != project_id:
                continue

            # Guardar snapshot para historial (permite undo)
            source_entity_ids.append(entity_id)
            source_snapshots.append({
                "id": entity_id,
                "canonical_name": entity.canonical_name,
                "entity_type": entity.entity_type.value,
                "aliases": entity.aliases,
                "mention_count": entity.mention_count,
            })
            canonical_names_before.append(entity.canonical_name)

            # 1. Transferir menciones a la entidad principal
            mentions_moved = entity_repo.move_mentions(entity_id, primary_entity_id)
            logger.debug(f"Moved {mentions_moved} mentions from entity {entity_id} to {primary_entity_id}")

            # 2. Transferir atributos a la entidad principal
            attrs_moved = entity_repo.move_attributes(entity_id, primary_entity_id)
            logger.debug(f"Moved {attrs_moved} attributes from entity {entity_id} to {primary_entity_id}")

            # 3. Combinar aliases (incluir nombre canónico de la entidad fusionada)
            combined_aliases.add(entity.canonical_name)
            combined_aliases.update(entity.aliases)

            # 4. Desactivar la entidad fusionada (soft delete para poder deshacer)
            entity_repo.delete_entity(entity_id, hard_delete=False)

            merged_count += 1

        if merged_count > 0:
            # Actualizar aliases y merged_from_ids en la entidad principal
            combined_aliases.discard(primary_entity.canonical_name)
            new_merged_ids = list(set(primary_entity.merged_from_ids + source_entity_ids))

            entity_repo.update_entity(
                primary_entity_id,
                aliases=list(combined_aliases),
                merged_from_ids=new_merged_ids,
            )

            # Actualizar contador de menciones
            total_mentions = sum(s.get("mention_count", 0) for s in source_snapshots)
            if total_mentions > 0:
                entity_repo.increment_mention_count(primary_entity_id, total_mentions)

            # Registrar fusión en historial (para poder deshacer)
            entity_repo.add_merge_history(
                project_id=project_id,
                result_entity_id=primary_entity_id,
                source_entity_ids=source_entity_ids,
                source_snapshots=source_snapshots,
                canonical_names_before=canonical_names_before,
                merged_by="user",
                note=f"Fusión de {merged_count} entidades en '{primary_entity.canonical_name}'",
            )

        logger.info(f"Merged {merged_count} entities into entity {primary_entity_id} ({primary_entity.canonical_name})")

        # Obtener la entidad actualizada para retornarla
        updated_entity = entity_repo.get_entity(primary_entity_id)

        return ApiResponse(
            success=True,
            data={
                "primary_entity_id": primary_entity_id,
                "merged_count": merged_count,
                "merged_entity_ids": source_entity_ids,
                "result_entity": {
                    "id": updated_entity.id,
                    "canonical_name": updated_entity.canonical_name,
                    "aliases": updated_entity.aliases,
                    "mention_count": updated_entity.mention_count,
                    "merged_from_ids": updated_entity.merged_from_ids,
                } if updated_entity else None
            },
            message=f"Se fusionaron {merged_count} entidades en '{primary_entity.canonical_name}'"
        )

    except Exception as e:
        logger.error(f"Error merging entities for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/entities/merge-history", response_model=ApiResponse)
async def get_merge_history(project_id: int):
    """
    Obtiene el historial de fusiones de entidades del proyecto.

    Returns:
        ApiResponse con lista de fusiones realizadas
    """
    try:
        entity_repo = entity_repository

        # Obtener historial de fusiones
        history = entity_repo.get_merge_history(project_id)

        return ApiResponse(success=True, data={
            "merges": history,
            "total": len(history)
        })

    except Exception as e:
        logger.error(f"Error getting merge history: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/entities/undo-merge/{merge_id}", response_model=ApiResponse)
async def undo_entity_merge(project_id: int, merge_id: int):
    """
    Deshace una fusión de entidades, restaurando las entidades originales.

    Args:
        project_id: ID del proyecto
        merge_id: ID del registro de fusión a deshacer

    Returns:
        ApiResponse con resultado de la operación
    """
    try:
        from narrative_assistant.entities.fusion import EntityFusionService

        fusion_service = EntityFusionService()
        result = fusion_service.undo_merge(merge_id)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={"restored_entity_ids": result.value},
            message="Fusión deshecha exitosamente"
        )

    except Exception as e:
        logger.error(f"Error undoing merge {merge_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/entities/{entity_id}", response_model=ApiResponse)
async def get_entity(project_id: int, entity_id: int):
    """
    Obtiene una entidad por su ID.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con los datos de la entidad
    """
    try:
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        # Calcular first_mention_chapter desde first_appearance_char
        first_mention_chapter = None
        if entity.first_appearance_char is not None:
            chapter_repo = get_chapter_repository()
            chapters = chapter_repo.get_by_project(project_id)
            for ch in chapters:
                if ch.start_char <= entity.first_appearance_char < ch.end_char:
                    first_mention_chapter = ch.chapter_number
                    break

        entity_data = EntityResponse(
            id=entity.id,
            project_id=entity.project_id,
            entity_type=entity.entity_type.value,
            canonical_name=entity.canonical_name,
            aliases=entity.aliases or [],
            importance=entity.importance.value,
            description=entity.description,
            first_appearance_char=entity.first_appearance_char,
            first_mention_chapter=first_mention_chapter,
            mention_count=entity.mention_count or 0,
            is_active=entity.is_active if hasattr(entity, 'is_active') else True,
            merged_from_ids=entity.merged_from_ids or [],
            relevance_score=None,  # Calculate if needed
            created_at=entity.created_at.isoformat() if hasattr(entity, 'created_at') and entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if hasattr(entity, 'updated_at') and entity.updated_at else None,
        )

        return ApiResponse(success=True, data=entity_data)

    except Exception as e:
        logger.error(f"Error getting entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.put("/api/projects/{project_id}/entities/{entity_id}", response_model=ApiResponse)
async def update_entity(project_id: int, entity_id: int, request: Request):
    """
    Actualiza una entidad existente.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad a actualizar
        request: Body con campos a actualizar (name, type, importance, aliases)

    Returns:
        ApiResponse con la entidad actualizada
    """
    try:
        data = await request.json()

        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        # Mapear campos del request a parámetros del repositorio
        canonical_name = data.get('name') or data.get('canonical_name')
        aliases = data.get('aliases')
        importance_str = data.get('importance')
        description = data.get('description')

        # Convertir importance string a enum si se proporciona
        importance = None
        if importance_str:
            from narrative_assistant.entities.models import EntityImportance
            importance_map = {
                'main': EntityImportance.MAIN,
                'secondary': EntityImportance.SECONDARY,
                'minor': EntityImportance.MINOR,
            }
            importance = importance_map.get(importance_str.lower())

        # Actualizar la entidad
        updated = entity_repo.update_entity(
            entity_id=entity_id,
            canonical_name=canonical_name,
            aliases=aliases,
            importance=importance,
            description=description,
        )

        if not updated:
            return ApiResponse(success=False, error="No se pudo actualizar la entidad")

        # Obtener la entidad actualizada
        updated_entity = entity_repo.get_entity(entity_id)

        logger.info(f"Updated entity {entity_id} ({updated_entity.canonical_name})")

        return ApiResponse(
            success=True,
            data={
                "id": updated_entity.id,
                "canonical_name": updated_entity.canonical_name,
                "entity_type": updated_entity.entity_type.value,
                "importance": updated_entity.importance.value,
                "aliases": updated_entity.aliases,
                "description": updated_entity.description,
                "mention_count": updated_entity.mention_count,
            },
            message="Entidad actualizada correctamente"
        )

    except Exception as e:
        logger.error(f"Error updating entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/entities/{entity_id}", response_model=ApiResponse)
async def delete_entity(project_id: int, entity_id: int, hard_delete: bool = False):
    """
    Elimina (o desactiva) una entidad.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad a eliminar
        hard_delete: Si True, elimina permanentemente. Si False, solo desactiva (default).

    Returns:
        ApiResponse con resultado de la eliminación
    """
    try:
        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        entity_name = entity.canonical_name

        # Eliminar o desactivar la entidad
        entity_repo = entity_repository
        deleted = entity_repo.delete_entity(entity_id, hard_delete=hard_delete)

        if not deleted:
            return ApiResponse(success=False, error="No se pudo eliminar la entidad")

        action = "eliminada permanentemente" if hard_delete else "desactivada"
        logger.info(f"Entity {entity_id} ({entity_name}) {action}")

        return ApiResponse(
            success=True,
            data={"id": entity_id, "name": entity_name, "hard_delete": hard_delete},
            message=f"Entidad '{entity_name}' {action}"
        )

    except Exception as e:
        logger.error(f"Error deleting entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/entities/{entity_id}/timeline", response_model=ApiResponse)
async def get_entity_timeline(project_id: int, entity_id: int):
    """
    Obtiene la línea temporal de una entidad basada en sus menciones.

    Agrupa las menciones por capítulo y genera eventos con:
    - Primera aparición en cada capítulo
    - Cambios de atributos detectados
    - Número de menciones por capítulo

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con timeline de eventos:
        - chapter: Número de capítulo
        - description: Descripción del evento
        - type: Tipo de evento (appearance, attribute_change, mention_count)
        - mentionCount: Número de menciones en ese capítulo
    """
    try:
        # Verificar que la entidad existe y pertenece al proyecto
        entity, error = _verify_entity_ownership(entity_id, project_id)
        if error:
            return error

        # Obtener menciones de la entidad
        entity_repo = entity_repository
        mentions = entity_repo.get_mentions_by_entity(entity_id)

        if not mentions:
            return ApiResponse(success=True, data=[])

        # Obtener capítulos para mapear chapter_id a chapter_number
        chapters = chapter_repository.get_by_project(project_id) if chapter_repository else []
        chapter_map = {ch.id: ch for ch in chapters}

        # Agrupar menciones por capítulo
        mentions_by_chapter: dict[int, list] = {}
        for mention in mentions:
            ch_id = mention.chapter_id or 0
            if ch_id not in mentions_by_chapter:
                mentions_by_chapter[ch_id] = []
            mentions_by_chapter[ch_id].append(mention)

        # Obtener atributos para detectar cambios
        attributes = entity_repo.get_attributes_by_entity(entity_id)
        attrs_by_chapter: dict[int, list] = {}
        for attr in attributes:
            # Si el atributo tiene chapter_id o first_mention_chapter
            ch = getattr(attr, 'chapter_id', None) or getattr(attr, 'first_mention_chapter', None) or 0
            if ch not in attrs_by_chapter:
                attrs_by_chapter[ch] = []
            attrs_by_chapter[ch].append(attr)

        # Generar timeline
        timeline_events = []
        sorted_chapters = sorted(mentions_by_chapter.keys())

        for idx, ch_id in enumerate(sorted_chapters):
            ch_mentions = mentions_by_chapter[ch_id]
            ch_info = chapter_map.get(ch_id)
            ch_number = ch_info.chapter_number if ch_info else ch_id
            ch_title = ch_info.title if ch_info else f"Capítulo {ch_number}"

            # Primera aparición
            if idx == 0:
                first_mention = ch_mentions[0]
                context = first_mention.context_before or ""
                context += f"**{first_mention.surface_form}**"
                context += first_mention.context_after or ""
                timeline_events.append({
                    "chapter": ch_number,
                    "chapterTitle": ch_title,
                    "description": f"Primera aparición: \"{first_mention.surface_form}\"",
                    "type": "first_appearance",
                    "mentionCount": len(ch_mentions),
                    "context": context[:200] if context else None,
                })
            else:
                # Aparición en capítulo posterior
                timeline_events.append({
                    "chapter": ch_number,
                    "chapterTitle": ch_title,
                    "description": f"{len(ch_mentions)} menciones en este capítulo",
                    "type": "appearance",
                    "mentionCount": len(ch_mentions),
                })

            # Atributos nuevos en este capítulo
            if ch_id in attrs_by_chapter or ch_number in attrs_by_chapter:
                ch_attrs = attrs_by_chapter.get(ch_id, []) + attrs_by_chapter.get(ch_number, [])
                for attr in ch_attrs:
                    attr_name = getattr(attr, 'attribute_key', None) or getattr(attr, 'name', 'atributo')
                    attr_value = getattr(attr, 'attribute_value', None) or getattr(attr, 'value', '')
                    timeline_events.append({
                        "chapter": ch_number,
                        "chapterTitle": ch_title,
                        "description": f"Se menciona: {attr_name} = {attr_value}",
                        "type": "attribute",
                        "mentionCount": 0,
                    })

        # Ordenar por capítulo
        timeline_events.sort(key=lambda x: (x["chapter"], x["type"] != "first_appearance"))

        return ApiResponse(success=True, data=timeline_events)

    except Exception as e:
        logger.error(f"Error getting timeline for entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Menciones de Entidades
# ============================================================================

@app.get("/api/projects/{project_id}/entities/{entity_id}/mentions", response_model=ApiResponse)
async def get_entity_mentions(project_id: int, entity_id: int):
    """
    Obtiene todas las menciones de una entidad en el texto.

    Returns:
        Lista de menciones con posiciones, contexto y capítulo.
    """
    try:
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener menciones de la entidad
        mentions = entity_repo.get_mentions_by_entity(entity_id)

        if not mentions:
            return ApiResponse(success=True, data={"mentions": [], "total": 0})

        # Obtener capítulos para mapear chapter_id a chapter_number y título
        chapters = chapter_repository.get_by_project(project_id) if chapter_repository else []
        chapter_map = {ch.id: ch for ch in chapters}

        # Serializar menciones con información de capítulo
        mentions_data = []
        for mention in mentions:
            ch_info = chapter_map.get(mention.chapter_id) if mention.chapter_id else None
            mentions_data.append({
                "id": mention.id,
                "entityId": entity_id,
                "surfaceForm": mention.surface_form,
                "startChar": mention.start_char,
                "endChar": mention.end_char,
                "chapterId": mention.chapter_id,
                "chapterNumber": ch_info.chapter_number if ch_info else None,
                "chapterTitle": ch_info.title if ch_info else None,
                "contextBefore": mention.context_before,
                "contextAfter": mention.context_after,
                "confidence": mention.confidence,
                "source": mention.source,
            })

        # Ordenar por posición (start_char)
        mentions_data.sort(key=lambda m: (m["chapterNumber"] or 0, m["startChar"]))

        logger.info(f"Entity {entity_id} ({entity.canonical_name}): Found {len(mentions_data)} raw mentions from DB (entity.mention_count={entity.mention_count})")

        # Log muestra de posiciones para debug
        if mentions_data:
            sample = mentions_data[:5]
            logger.info(f"Entity {entity_id}: Sample positions: {[(m['chapterId'], m['startChar'], m['endChar']) for m in sample]}")

        # Filtrar duplicados: menciones que se solapan
        # Estrategia conservadora basada en discusión de expertos:
        # 1. Límites duros: puntuación indica que hemos ido demasiado lejos
        # 2. Artículo + sustantivo común no es parte del nombre
        # 3. Preferir nombre más largo SOLO si es estructura válida de nombre
        # 4. Preferir más larga solo si confianza >= 85% de la corta
        import re

        def has_invalid_extension(text: str) -> bool:
            """Detecta si el texto contiene patrones inválidos para un nombre."""
            # Puntuación que indica límite de nombre
            if re.search(r'[,;:\.\!\?]', text):
                return True
            # Artículo + sustantivo común (aposición)
            # "María la vecina", "Pedro el viejo"
            if re.search(r'\s+(el|la|los|las)\s+[a-záéíóúñ]+$', text, re.IGNORECASE):
                # Excepciones: partículas de apellido válidas
                valid_particles = ['de la', 'del', 'de los', 'de las', 'de']
                text_lower = text.lower()
                if not any(f' {p} ' in text_lower or text_lower.endswith(f' {p}') for p in valid_particles):
                    return True
            return False

        def is_valid_name_extension(short_text: str, long_text: str) -> bool:
            """Verifica si la extensión del nombre corto al largo es válida."""
            extension = long_text[len(short_text):].strip()
            if not extension:
                return True
            # Partículas de apellido válidas
            if re.match(r'^(de la|del|de los|de las|de)\s+[A-ZÁÉÍÓÚÑ]', extension):
                return True
            # Apellido simple (empieza con mayúscula, sin puntuación)
            if re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?$', extension):
                return True
            return False

        filtered_mentions = []
        removed_count = 0

        for mention in mentions_data:
            dominated = False
            to_remove = None

            for existing in filtered_mentions:
                # Solo filtrar si están en el mismo capítulo
                if existing["chapterId"] != mention["chapterId"]:
                    continue

                # Verificar solapamiento de posiciones
                overlaps = not (
                    mention["endChar"] <= existing["startChar"] or
                    mention["startChar"] >= existing["endChar"]
                )

                # Deduplicar menciones con mismo texto muy cercanas (< 10 chars)
                # Esto captura menciones duplicadas que no se solapan exactamente
                same_text = existing["surfaceForm"].lower() == mention["surfaceForm"].lower()
                distance = min(
                    abs(mention["startChar"] - existing["endChar"]),
                    abs(existing["startChar"] - mention["endChar"])
                )
                very_close = same_text and distance < 10

                if very_close and not overlaps:
                    # Son la misma mención con posiciones ligeramente diferentes
                    dominated = True
                    removed_count += 1
                    break

                if overlaps:
                    # Determinar cuál es más larga y cuál más corta
                    if len(mention["surfaceForm"]) > len(existing["surfaceForm"]):
                        longer, shorter = mention, existing
                        longer_is_new = True
                    else:
                        longer, shorter = existing, mention
                        longer_is_new = False

                    # Mismo texto (ignorando mayúsculas) → duplicado exacto
                    if existing["surfaceForm"].lower() == mention["surfaceForm"].lower():
                        dominated = True
                        if mention["confidence"] > existing["confidence"]:
                            to_remove = existing
                        removed_count += 1
                        break

                    # Verificar si la extensión es válida
                    longer_has_invalid = has_invalid_extension(longer["surfaceForm"])
                    extension_valid = is_valid_name_extension(
                        shorter["surfaceForm"], longer["surfaceForm"]
                    )

                    # Si la larga tiene patrones inválidos → preferir corta
                    if longer_has_invalid or not extension_valid:
                        if longer_is_new:
                            dominated = True  # Descartar la nueva (larga)
                        else:
                            to_remove = existing  # Reemplazar existente (larga) por nueva (corta)
                        removed_count += 1
                        break

                    # La larga es válida → verificar confianza (85% threshold)
                    confidence_ok = longer["confidence"] >= shorter["confidence"] * 0.85
                    if confidence_ok:
                        # Preferir la más larga
                        if longer_is_new:
                            to_remove = existing
                        else:
                            dominated = True
                    else:
                        # Confianza insuficiente → preferir corta
                        if longer_is_new:
                            dominated = True
                        else:
                            to_remove = existing
                    removed_count += 1
                    break

            if to_remove:
                filtered_mentions.remove(to_remove)
                filtered_mentions.append(mention)
            elif not dominated:
                filtered_mentions.append(mention)

        # Re-ordenar después de filtrar
        filtered_mentions.sort(key=lambda m: (m["chapterNumber"] or 0, m["startChar"]))

        if removed_count > 0:
            logger.info(f"Entity {entity_id} ({entity.canonical_name}): Filtered {removed_count} overlapping mentions, returning {len(filtered_mentions)}")

        return ApiResponse(success=True, data={
            "mentions": filtered_mentions,
            "total": len(filtered_mentions),
            "entityName": entity.canonical_name,
            "entityType": entity.entity_type.value if entity.entity_type else None,
            # Debug info
            "_debug": {
                "raw_mentions_in_db": len(mentions),
                "after_serialization": len(mentions_data),
                "after_filtering": len(filtered_mentions),
                "entity_mention_count_field": entity.mention_count,
            }
        })

    except Exception as e:
        logger.error(f"Error getting mentions for entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/entities/{entity_id}/coreference", response_model=ApiResponse)
async def get_entity_coreference_info(project_id: int, entity_id: int):
    """
    Obtiene información de correferencia para una entidad.

    Retorna datos sobre cómo se resolvieron las menciones de la entidad,
    incluyendo la contribución de cada método de detección.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con información de correferencia:
        - methodContributions: Contribución de cada método
        - mentionsByType: Menciones agrupadas por tipo
        - overallConfidence: Confianza promedio
        - totalMentions: Total de menciones
    """
    try:
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener menciones de la entidad
        mentions = entity_repo.get_mentions_by_entity(entity_id)

        if not mentions:
            return ApiResponse(success=True, data={
                "entityId": entity_id,
                "entityName": entity.canonical_name,
                "methodContributions": [],
                "mentionsByType": {},
                "overallConfidence": 0.0,
                "totalMentions": 0,
            })

        # Agrupar menciones por fuente/método de detección
        method_counts: dict[str, int] = {}
        type_mentions: dict[str, list] = {}
        total_confidence = 0.0
        confidence_count = 0

        # Mapeo de fuentes del backend a nombres legibles
        source_labels = {
            "ner": "NER (spaCy)",
            "spacy": "NER (spaCy)",
            "embeddings": "Embeddings",
            "llm": "LLM (Ollama)",
            "morpho": "Morfosintáctico",
            "heuristics": "Heurísticas",
            "coreference": "Correferencia",
            "coref": "Correferencia",
            "manual": "Manual",
            "fusion": "Fusión",
            "pronoun": "Pronombre resuelto",
        }

        for mention in mentions:
            source = mention.source or "unknown"
            source_lower = source.lower()

            # Contar por método
            method_counts[source_lower] = method_counts.get(source_lower, 0) + 1

            # Agrupar por tipo de mención (basado en el texto)
            surface = mention.surface_form or ""
            mention_type = _classify_mention_type(surface)

            if mention_type not in type_mentions:
                type_mentions[mention_type] = []
            type_mentions[mention_type].append({
                "text": surface,
                "confidence": mention.confidence,
                "source": source,
            })

            # Sumar confianza para promedio
            if mention.confidence is not None:
                total_confidence += mention.confidence
                confidence_count += 1

        # Calcular contribuciones con formato para MethodVotingBar
        total_mentions = len(mentions)
        method_contributions = []

        for source, count in sorted(method_counts.items(), key=lambda x: -x[1]):
            percentage = (count / total_mentions * 100) if total_mentions > 0 else 0
            method_contributions.append({
                "name": source_labels.get(source, source.capitalize()),
                "method": source,
                "count": count,
                "score": percentage / 100,  # Normalizado 0-1 para MethodVotingBar
                "agreed": percentage >= 20,  # Consideramos "de acuerdo" si aporta >= 20%
            })

        # Calcular confianza promedio
        overall_confidence = (total_confidence / confidence_count) if confidence_count > 0 else 0.0

        return ApiResponse(success=True, data={
            "entityId": entity_id,
            "entityName": entity.canonical_name,
            "methodContributions": method_contributions,
            "mentionsByType": type_mentions,
            "overallConfidence": overall_confidence,
            "totalMentions": total_mentions,
        })

    except Exception as e:
        logger.error(f"Error getting coreference info for entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


def _classify_mention_type(surface_form: str) -> str:
    """
    Clasifica el tipo de mención basándose en el texto.

    Args:
        surface_form: Texto de la mención

    Returns:
        Tipo de mención: 'proper_noun', 'pronoun', 'definite_np', etc.
    """
    text_lower = surface_form.lower().strip()

    # Pronombres personales
    pronouns = {
        "él", "ella", "ellos", "ellas", "yo", "tú", "nosotros", "nosotras",
        "lo", "la", "los", "las", "le", "les", "se",
        "me", "te", "nos", "os",
    }
    if text_lower in pronouns:
        return "pronoun"

    # Demostrativos
    demonstratives = {
        "este", "esta", "esto", "estos", "estas",
        "ese", "esa", "eso", "esos", "esas",
        "aquel", "aquella", "aquello", "aquellos", "aquellas",
    }
    if text_lower in demonstratives:
        return "demonstrative"

    # Posesivos (cuando son el sujeto completo)
    possessives = {"su", "sus", "suyo", "suya", "suyos", "suyas"}
    if text_lower in possessives:
        return "possessive"

    # Sintagma nominal definido (empieza con artículo + sustantivo)
    articles = {"el", "la", "los", "las"}
    words = text_lower.split()
    if len(words) >= 2 and words[0] in articles:
        return "definite_np"

    # Por defecto, nombre propio
    return "proper_noun"


# ============================================================================
# Endpoints - Validación y Rechazo de Entidades
# ============================================================================

@app.get("/api/projects/{project_id}/entities/rejected", response_model=ApiResponse)
async def list_rejected_entities(project_id: int):
    """
    Lista las entidades rechazadas por el usuario para un proyecto.

    Las entidades rechazadas no se volverán a detectar en futuros análisis.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de entidades rechazadas
    """
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        rows = db.fetchall(
            """
            SELECT id, entity_text, rejection_reason, created_at
            FROM rejected_entities
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            (project_id,)
        )

        rejected = [
            {
                "id": row["id"],
                "text": row["entity_text"],
                "reason": row["rejection_reason"],
                "rejectedAt": row["created_at"],
            }
            for row in rows
        ]

        return ApiResponse(success=True, data=rejected)

    except Exception as e:
        logger.error(f"Error listing rejected entities for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/entities/reject", response_model=ApiResponse)
async def reject_entity_text(project_id: int, request: Request):
    """
    Rechaza un texto de entidad para que no se vuelva a detectar.

    El texto rechazado se guarda normalizado (lowercase) y se aplicará
    en futuros análisis NER del proyecto.

    Args:
        project_id: ID del proyecto
        request: Body con entity_text (texto a rechazar) y reason (opcional)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.nlp.entity_validator import get_entity_validator
        from narrative_assistant.persistence.database import get_database

        data = await request.json()
        entity_text = data.get('entity_text', '').strip()
        reason = data.get('reason', '')

        if not entity_text:
            return ApiResponse(success=False, error="entity_text es requerido")

        # Usar el validador para rechazar la entidad
        validator = get_entity_validator(db=get_database())
        success = validator.reject_entity(project_id, entity_text)

        if success:
            # Guardar razón si se proporcionó
            if reason:
                db = get_database()
                db.execute(
                    """
                    UPDATE rejected_entities
                    SET rejection_reason = ?
                    WHERE project_id = ? AND entity_text = ?
                    """,
                    (reason, project_id, entity_text.lower().strip())
                )

            return ApiResponse(
                success=True,
                data={"message": f"Entidad '{entity_text}' rechazada correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Error al rechazar entidad")

    except Exception as e:
        logger.error(f"Error rejecting entity for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/entities/reject/{entity_text}", response_model=ApiResponse)
async def unreject_entity_text(project_id: int, entity_text: str):
    """
    Quita un texto de entidad de la lista de rechazadas.

    La entidad podrá volver a detectarse en futuros análisis.

    Args:
        project_id: ID del proyecto
        entity_text: Texto de la entidad a des-rechazar (URL encoded)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.nlp.entity_validator import get_entity_validator
        from narrative_assistant.persistence.database import get_database

        if not entity_text:
            return ApiResponse(success=False, error="entity_text es requerido")

        # Usar el validador para des-rechazar la entidad
        validator = get_entity_validator(db=get_database())
        success = validator.unreject_entity(project_id, entity_text)

        if success:
            return ApiResponse(
                success=True,
                data={"message": f"Entidad '{entity_text}' restaurada correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Entidad no encontrada en lista de rechazadas")

    except Exception as e:
        logger.error(f"Error unrejecting entity for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Sistema Híbrido de Filtros de Entidades
# ============================================================================

@app.get("/api/entity-filters/stats", response_model=ApiResponse)
async def get_filter_stats(project_id: Optional[int] = None):
    """
    Obtiene estadísticas del sistema de filtros de entidades.

    Args:
        project_id: ID del proyecto (opcional, para stats por proyecto)

    Returns:
        ApiResponse con estadísticas de filtros
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        stats = repo.get_filter_stats(project_id)

        return ApiResponse(success=True, data=stats)

    except Exception as e:
        logger.error(f"Error getting filter stats: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/entity-filters/system-patterns", response_model=ApiResponse)
async def list_system_patterns(language: str = "es", only_active: bool = False):
    """
    Lista los patrones de falsos positivos del sistema.

    Estos son patrones predefinidos para filtrar expresiones comunes
    que no son entidades (artículos, marcadores temporales, etc.).

    Args:
        language: Idioma (default: "es")
        only_active: Si True, solo retorna patrones activos

    Returns:
        ApiResponse con lista de patrones del sistema
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        patterns = repo.get_system_patterns(language, only_active)

        # Agrupar por categoría para la UI
        by_category: dict = {}
        for pattern in patterns:
            cat = pattern.category or "other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "id": pattern.id,
                "pattern": pattern.pattern,
                "patternType": pattern.pattern_type.value,
                "entityType": pattern.entity_type,
                "description": pattern.description,
                "isActive": pattern.is_active,
            })

        return ApiResponse(success=True, data={
            "patterns": [
                {
                    "id": p.id,
                    "pattern": p.pattern,
                    "patternType": p.pattern_type.value,
                    "entityType": p.entity_type,
                    "category": p.category,
                    "description": p.description,
                    "isActive": p.is_active,
                }
                for p in patterns
            ],
            "byCategory": by_category,
            "totalCount": len(patterns),
            "activeCount": sum(1 for p in patterns if p.is_active),
        })

    except Exception as e:
        logger.error(f"Error listing system patterns: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.patch("/api/entity-filters/system-patterns/{pattern_id}", response_model=ApiResponse)
async def toggle_system_pattern(pattern_id: int, request: Request):
    """
    Activa o desactiva un patrón del sistema.

    Args:
        pattern_id: ID del patrón
        request: Body con is_active (bool)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        data = await request.json()
        is_active = data.get('is_active', True)

        repo = get_filter_repository()
        success = repo.toggle_system_pattern(pattern_id, is_active)

        if success:
            return ApiResponse(
                success=True,
                data={"message": f"Patrón {'activado' if is_active else 'desactivado'} correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Patrón no encontrado")

    except Exception as e:
        logger.error(f"Error toggling system pattern {pattern_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/entity-filters/user-rejections", response_model=ApiResponse)
async def list_user_rejections():
    """
    Lista los rechazos globales del usuario.

    Estas son entidades que el usuario ha rechazado y que se filtrarán
    en todos sus proyectos.

    Returns:
        ApiResponse con lista de rechazos globales
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        rejections = repo.get_user_rejections()

        return ApiResponse(success=True, data=[
            {
                "id": r.id,
                "entityName": r.entity_name,
                "entityType": r.entity_type,
                "reason": r.reason,
                "rejectedAt": r.rejected_at,
            }
            for r in rejections
        ])

    except Exception as e:
        logger.error(f"Error listing user rejections: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/entity-filters/user-rejections", response_model=ApiResponse)
async def add_user_rejection(request: Request):
    """
    Añade un rechazo global del usuario.

    La entidad se filtrará en todos los proyectos del usuario.

    Args:
        request: Body con entity_name, entity_type (opcional), reason (opcional)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        data = await request.json()
        entity_name = data.get('entity_name', '').strip()
        entity_type = data.get('entity_type')
        reason = data.get('reason')

        if not entity_name:
            return ApiResponse(success=False, error="entity_name es requerido")

        repo = get_filter_repository()
        rejection_id = repo.add_user_rejection(entity_name, entity_type, reason)

        return ApiResponse(
            success=True,
            data={
                "id": rejection_id,
                "message": f"Entidad '{entity_name}' añadida a filtros globales"
            }
        )

    except Exception as e:
        logger.error(f"Error adding user rejection: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/entity-filters/user-rejections/{rejection_id}", response_model=ApiResponse)
async def remove_user_rejection(rejection_id: int):
    """
    Elimina un rechazo global del usuario.

    La entidad podrá volver a detectarse en todos los proyectos.

    Args:
        rejection_id: ID del rechazo a eliminar

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository
        from narrative_assistant.persistence.database import get_database

        # Primero obtener el nombre de la entidad
        db = get_database()
        row = db.fetchone(
            "SELECT entity_name, entity_type FROM user_rejected_entities WHERE id = ?",
            (rejection_id,)
        )

        if not row:
            return ApiResponse(success=False, error="Rechazo no encontrado")

        repo = get_filter_repository()
        success = repo.remove_user_rejection(row["entity_name"], row["entity_type"])

        if success:
            return ApiResponse(
                success=True,
                data={"message": "Rechazo eliminado correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Error eliminando rechazo")

    except Exception as e:
        logger.error(f"Error removing user rejection {rejection_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/entity-filters/overrides", response_model=ApiResponse)
async def list_project_overrides(project_id: int):
    """
    Lista los overrides de entidades de un proyecto.

    Estos son ajustes específicos del proyecto que tienen la máxima prioridad:
    - force_include: Fuerza que una entidad se incluya aunque esté filtrada globalmente
    - reject: Rechaza una entidad solo en este proyecto

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de overrides
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        repo = get_filter_repository()
        overrides = repo.get_project_overrides(project_id)

        return ApiResponse(success=True, data=[
            {
                "id": o.id,
                "entityName": o.entity_name,
                "entityType": o.entity_type,
                "action": o.action.value,
                "reason": o.reason,
                "createdAt": o.created_at,
            }
            for o in overrides
        ])

    except Exception as e:
        logger.error(f"Error listing project overrides for {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/entity-filters/overrides", response_model=ApiResponse)
async def add_project_override(project_id: int, request: Request):
    """
    Añade un override de entidad para un proyecto.

    Args:
        project_id: ID del proyecto
        request: Body con entity_name, action ('reject' o 'force_include'),
                 entity_type (opcional), reason (opcional)

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository, FilterAction

        data = await request.json()
        entity_name = data.get('entity_name', '').strip()
        action = data.get('action', 'reject')
        entity_type = data.get('entity_type')
        reason = data.get('reason')

        if not entity_name:
            return ApiResponse(success=False, error="entity_name es requerido")

        if action not in ('reject', 'force_include'):
            return ApiResponse(success=False, error="action debe ser 'reject' o 'force_include'")

        repo = get_filter_repository()
        override_id = repo.add_project_override(
            project_id=project_id,
            entity_name=entity_name,
            action=FilterAction(action),
            entity_type=entity_type,
            reason=reason
        )

        action_text = "rechazada en este proyecto" if action == "reject" else "forzada a incluir"
        return ApiResponse(
            success=True,
            data={
                "id": override_id,
                "message": f"Entidad '{entity_name}' {action_text}"
            }
        )

    except Exception as e:
        logger.error(f"Error adding project override for {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/entity-filters/overrides/{override_id}", response_model=ApiResponse)
async def remove_project_override(project_id: int, override_id: int):
    """
    Elimina un override de entidad de un proyecto.

    Args:
        project_id: ID del proyecto
        override_id: ID del override a eliminar

    Returns:
        ApiResponse con confirmación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository
        from narrative_assistant.persistence.database import get_database

        # Primero obtener el nombre de la entidad
        db = get_database()
        row = db.fetchone(
            """SELECT entity_name, entity_type FROM project_entity_overrides
               WHERE id = ? AND project_id = ?""",
            (override_id, project_id)
        )

        if not row:
            return ApiResponse(success=False, error="Override no encontrado")

        repo = get_filter_repository()
        success = repo.remove_project_override(project_id, row["entity_name"], row["entity_type"])

        if success:
            return ApiResponse(
                success=True,
                data={"message": "Override eliminado correctamente"}
            )
        else:
            return ApiResponse(success=False, error="Error eliminando override")

    except Exception as e:
        logger.error(f"Error removing project override {override_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/entity-filters/check", response_model=ApiResponse)
async def check_entity_filter(request: Request):
    """
    Verifica si una entidad sería filtrada por el sistema.

    Útil para debug y para mostrar al usuario por qué una entidad
    no aparece en los resultados.

    Args:
        request: Body con entity_name, entity_type (opcional), project_id (opcional)

    Returns:
        ApiResponse con resultado de la evaluación
    """
    try:
        from narrative_assistant.entities.filters import get_filter_repository

        data = await request.json()
        entity_name = data.get('entity_name', '').strip()
        entity_type = data.get('entity_type')
        project_id = data.get('project_id')

        if not entity_name:
            return ApiResponse(success=False, error="entity_name es requerido")

        repo = get_filter_repository()
        decision = repo.should_filter_entity(entity_name, entity_type, project_id)

        return ApiResponse(success=True, data={
            "shouldFilter": decision.should_filter,
            "reason": decision.reason,
            "level": decision.level,
            "ruleId": decision.rule_id,
        })

    except Exception as e:
        logger.error(f"Error checking entity filter: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Atributos de Entidades
# ============================================================================

@app.get("/api/projects/{project_id}/entities/{entity_id}/attributes", response_model=ApiResponse)
async def list_entity_attributes(project_id: int, entity_id: int):
    """
    Lista todos los atributos de una entidad.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad

    Returns:
        ApiResponse con lista de atributos
    """
    try:
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener atributos
        attributes = entity_repo.get_attributes_by_entity(entity_id)

        return ApiResponse(success=True, data=attributes)

    except Exception as e:
        logger.error(f"Error listing attributes for entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/entities/{entity_id}/attributes", response_model=ApiResponse)
async def create_entity_attribute(project_id: int, entity_id: int, request: Request):
    """
    Crea un nuevo atributo para una entidad.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        request: Body con category, name, value

    Returns:
        ApiResponse con el atributo creado
    """
    try:
        data = await request.json()
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Extraer datos del request
        category = data.get('category', 'physical')
        name = data.get('name')
        value = data.get('value')
        confidence = data.get('confidence', 1.0)

        if not name or not value:
            return ApiResponse(success=False, error="Se requieren 'name' y 'value'")

        # Crear atributo
        attribute_id = entity_repo.create_attribute(
            entity_id=entity_id,
            attribute_type=category,
            attribute_key=name,
            attribute_value=value,
            confidence=confidence,
        )

        logger.info(f"Created attribute {attribute_id} for entity {entity_id}: {name}={value}")

        return ApiResponse(
            success=True,
            data={
                "id": attribute_id,
                "entity_id": entity_id,
                "category": category,
                "name": name,
                "value": value,
                "confidence": confidence,
            },
            message="Atributo creado correctamente"
        )

    except Exception as e:
        logger.error(f"Error creating attribute for entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.put("/api/projects/{project_id}/entities/{entity_id}/attributes/{attribute_id}", response_model=ApiResponse)
async def update_entity_attribute(project_id: int, entity_id: int, attribute_id: int, request: Request):
    """
    Actualiza un atributo existente.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        attribute_id: ID del atributo
        request: Body con name, value, is_verified

    Returns:
        ApiResponse con el atributo actualizado
    """
    try:
        data = await request.json()
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Actualizar atributo
        updated = entity_repo.update_attribute(
            attribute_id=attribute_id,
            attribute_key=data.get('name'),
            attribute_value=data.get('value'),
            is_verified=data.get('is_verified'),
        )

        if not updated:
            return ApiResponse(success=False, error="No se pudo actualizar el atributo")

        logger.info(f"Updated attribute {attribute_id} for entity {entity_id}")

        return ApiResponse(
            success=True,
            data={"id": attribute_id},
            message="Atributo actualizado correctamente"
        )

    except Exception as e:
        logger.error(f"Error updating attribute {attribute_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/entities/{entity_id}/attributes/{attribute_id}", response_model=ApiResponse)
async def delete_entity_attribute(project_id: int, entity_id: int, attribute_id: int):
    """
    Elimina un atributo.

    Args:
        project_id: ID del proyecto
        entity_id: ID de la entidad
        attribute_id: ID del atributo

    Returns:
        ApiResponse con resultado de la eliminación
    """
    try:
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Eliminar atributo
        deleted = entity_repo.delete_attribute(attribute_id)

        if not deleted:
            return ApiResponse(success=False, error="No se pudo eliminar el atributo")

        logger.info(f"Deleted attribute {attribute_id} from entity {entity_id}")

        return ApiResponse(
            success=True,
            data={"id": attribute_id},
            message="Atributo eliminado correctamente"
        )

    except Exception as e:
        logger.error(f"Error deleting attribute {attribute_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Alertas
# ============================================================================

@app.get("/api/projects/{project_id}/alerts", response_model=ApiResponse)
async def list_alerts(
    project_id: int,
    status: Optional[str] = None,
    current_chapter: Optional[int] = None,
):
    """
    Lista todas las alertas de un proyecto, opcionalmente priorizadas.

    Args:
        project_id: ID del proyecto
        status: Filtrar por estado (open, resolved, dismissed)
        current_chapter: Capítulo actual para priorizar alertas cercanas

    Returns:
        ApiResponse con lista de alertas (priorizadas si current_chapter se especifica)
    """
    try:
        alert_repo = alert_repository

        # Obtener alertas - usar método priorizado si se especifica capítulo
        if current_chapter is not None:
            result = alert_repo.get_by_project_prioritized(project_id, current_chapter=current_chapter)
        else:
            result = alert_repo.get_by_project(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo alertas")

        all_alerts = result.value

        # Filtrar por status si se especifica
        if status:
            status_value = status.lower()
            if status_value == 'open':
                # "open" incluye todos los estados no resueltos/descartados
                open_statuses = {'new', 'open', 'acknowledged', 'in_progress'}
                alerts = [a for a in all_alerts if a.status.value in open_statuses]
            else:
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
                start_char=getattr(a, 'start_char', None),
                end_char=getattr(a, 'end_char', None),
                excerpt=getattr(a, 'excerpt', None) or '',
                status=a.status.value if hasattr(a.status, 'value') else str(a.status),
                entity_ids=getattr(a, 'entity_ids', []) or [],
                confidence=getattr(a, 'confidence', 0.0) or 0.0,
                created_at=a.created_at.isoformat() if hasattr(a.created_at, 'isoformat') else str(a.created_at),
                updated_at=a.updated_at.isoformat() if hasattr(a, 'updated_at') and a.updated_at else None,
                resolved_at=a.resolved_at.isoformat() if hasattr(a, 'resolved_at') and a.resolved_at else None,
                extra_data=getattr(a, 'extra_data', None) or {},
            )
            for a in alerts
        ]

        return ApiResponse(success=True, data=alerts_data)
    except Exception as e:
        logger.error(f"Error listing alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.patch("/api/projects/{project_id}/alerts/{alert_id}/status", response_model=ApiResponse)
async def update_alert_status(project_id: int, alert_id: int, request: Request):
    """
    Actualiza el status de una alerta.

    Args:
        project_id: ID del proyecto
        alert_id: ID de la alerta
        request: Body con {"status": "resolved"|"dismissed"|"open"}

    Returns:
        ApiResponse confirmando el cambio
    """
    try:
        data = await request.json()
        new_status_str = data.get('status', '').lower()

        # Mapear status string a enum
        status_map = {
            'resolved': AlertStatus.RESOLVED,
            'dismissed': AlertStatus.DISMISSED,
            'open': AlertStatus.OPEN,
            'active': AlertStatus.OPEN,  # alias
            'reopen': AlertStatus.OPEN,  # alias
        }

        if new_status_str not in status_map:
            return ApiResponse(
                success=False,
                error=f"Status inválido: {new_status_str}. Valores válidos: resolved, dismissed, open"
            )

        # Verificar que la alerta existe y pertenece al proyecto
        alert, error = _verify_alert_ownership(alert_id, project_id)
        if error:
            return error

        # Actualizar el status
        alert.status = status_map[new_status_str]
        alert_repository.update(alert)

        status_messages = {
            'resolved': 'Alerta marcada como resuelta',
            'dismissed': 'Alerta descartada',
            'open': 'Alerta reabierta',
            'active': 'Alerta reabierta',
            'reopen': 'Alerta reabierta',
        }

        logger.info(f"Alert {alert_id} status changed to {new_status_str}")

        return ApiResponse(
            success=True,
            data={"id": alert_id, "status": new_status_str},
            message=status_messages[new_status_str]
        )
    except Exception as e:
        logger.error(f"Error updating alert {alert_id} status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# Endpoints legacy para compatibilidad (redirigen al nuevo endpoint unificado)
@app.post("/api/projects/{project_id}/alerts/{alert_id}/resolve", response_model=ApiResponse)
async def resolve_alert(project_id: int, alert_id: int):
    """Marca una alerta como resuelta. [DEPRECATED: usar PATCH /status]"""
    alert, error = _verify_alert_ownership(alert_id, project_id)
    if error:
        return error
    alert.status = AlertStatus.RESOLVED
    alert_repository.update(alert)
    return ApiResponse(success=True, message="Alerta marcada como resuelta")


@app.post("/api/projects/{project_id}/alerts/{alert_id}/dismiss", response_model=ApiResponse)
async def dismiss_alert(project_id: int, alert_id: int):
    """Descarta una alerta. [DEPRECATED: usar PATCH /status]"""
    alert, error = _verify_alert_ownership(alert_id, project_id)
    if error:
        return error
    alert.status = AlertStatus.DISMISSED
    alert_repository.update(alert)
    return ApiResponse(success=True, message="Alerta descartada")


@app.post("/api/projects/{project_id}/alerts/{alert_id}/reopen", response_model=ApiResponse)
async def reopen_alert(project_id: int, alert_id: int):
    """Reabre una alerta. [DEPRECATED: usar PATCH /status]"""
    alert, error = _verify_alert_ownership(alert_id, project_id)
    if error:
        return error
    alert.status = AlertStatus.OPEN
    alert_repository.update(alert)
    return ApiResponse(success=True, message="Alerta reabierta")

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

        # Función helper para convertir secciones a dict recursivamente
        def section_to_dict(section) -> dict:
            return {
                "id": section.id,
                "project_id": section.project_id,
                "chapter_id": section.chapter_id,
                "parent_section_id": section.parent_section_id,
                "section_number": section.section_number,
                "title": section.title,
                "heading_level": section.heading_level,
                "start_char": section.start_char,
                "end_char": section.end_char,
                "subsections": [section_to_dict(s) for s in section.subsections]
            }

        # Convertir a formato de respuesta con secciones
        chapters_data = []
        for ch in chapters:
            # Obtener secciones jerárquicas de este capítulo
            sections = []
            if section_repository:
                sections = section_repository.get_by_chapter_hierarchical(ch.id)

            chapters_data.append({
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
                "updated_at": ch.updated_at,
                "sections": [section_to_dict(s) for s in sections]
            })

        return ApiResponse(success=True, data=chapters_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing chapters for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/chapters/{chapter_number}/annotations", response_model=ApiResponse)
async def get_chapter_annotations(project_id: int, chapter_number: int):
    """
    Obtiene anotaciones de gramática y ortografía para un capítulo.

    Devuelve errores gramaticales y ortográficos con posiciones para
    resaltar en el visor de documento.

    Args:
        project_id: ID del proyecto
        chapter_number: Número de capítulo

    Returns:
        ApiResponse con lista de anotaciones (errores gramaticales/ortográficos)
    """
    try:
        if not alert_repository:
            return ApiResponse(success=False, error="Alert repository not initialized")

        # Obtener alertas de gramática y ortografía para este capítulo
        alerts_result = alert_repository.get_by_project(project_id)

        if alerts_result.is_failure:
            return ApiResponse(success=False, error=str(alerts_result.error))

        all_alerts = alerts_result.value

        # Filtrar por categoría y capítulo
        annotations = []
        grammar_categories = {'grammar', 'orthography', 'spelling'}
        active_statuses = {AlertStatus.NEW, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS}

        for alert in all_alerts:
            # Solo incluir alertas de gramática/ortografía
            category_value = alert.category.value if hasattr(alert.category, 'value') else str(alert.category)
            if category_value not in grammar_categories:
                continue

            # Solo incluir alertas de este capítulo
            if alert.chapter != chapter_number:
                continue

            # Solo alertas activas
            if alert.status not in active_statuses:
                continue

            annotations.append({
                "id": alert.id,
                "type": category_value,
                "severity": alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),
                "title": alert.title,
                "description": alert.description,
                "start_char": getattr(alert, 'start_char', None),
                "end_char": getattr(alert, 'end_char', None),
                "suggestion": alert.suggestion,
                "excerpt": getattr(alert, 'excerpt', None),
            })

        return ApiResponse(success=True, data={
            "chapter_number": chapter_number,
            "annotations": annotations,
            "total_count": len(annotations)
        })

    except Exception as e:
        logger.error(f"Error getting chapter annotations: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Exportación Style Guide
# ============================================================================

@app.get("/api/projects/{project_id}/style-guide", response_model=ApiResponse)
async def get_style_guide(project_id: int, format: str = "json", preview: bool = False):
    """
    Genera y devuelve la guía de estilo del proyecto.

    La guía incluye:
    - Decisiones de grafía (variantes de nombres, acentos)
    - Lista de entidades canónicas (personajes, lugares, organizaciones)
    - Análisis estilístico (diálogos, puntuación, números)
    - Estadísticas del texto
    - Inconsistencias y recomendaciones

    Args:
        project_id: ID del proyecto
        format: Formato de respuesta ('json', 'markdown' o 'pdf')
        preview: Si es True, devuelve un resumen para previsualización

    Returns:
        ApiResponse con la guía de estilo
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Obtener proyecto
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Obtener texto completo para análisis estilístico
        full_text = ""
        if chapter_repository:
            chapters = chapter_repository.get_by_project(project_id)
            full_text = "\n\n".join(ch.content for ch in chapters if ch.content)

        # Generar guía de estilo
        from narrative_assistant.exporters.style_guide import generate_style_guide

        style_result = generate_style_guide(
            project_id=project_id,
            project_name=project.name,
            text=full_text
        )

        if style_result.is_failure:
            return ApiResponse(success=False, error=str(style_result.error))

        style_guide = style_result.value

        # Si es preview, devolver resumen simplificado
        if preview:
            preview_data = {
                "project_name": project.name,
                "generated_date": style_guide.generated_date,
                "total_entities": style_guide.total_entities,
                "total_spelling_variants": style_guide.total_spelling_variants,
                "characters_count": len(style_guide.characters),
                "locations_count": len(style_guide.locations),
                "organizations_count": len(style_guide.organizations),
                "has_style_analysis": style_guide.style_analysis is not None,
                "spelling_decisions_preview": [
                    {
                        "canonical_form": d.canonical_form,
                        "variants_count": len(d.variants)
                    }
                    for d in style_guide.spelling_decisions[:5]
                ],
                "characters_preview": [
                    {
                        "name": c.canonical_name,
                        "importance": c.importance,
                        "aliases_count": len(c.aliases)
                    }
                    for c in sorted(
                        style_guide.characters,
                        key=lambda x: {"principal": 0, "critical": 0, "high": 1, "medium": 2, "low": 3, "minimal": 4}.get(x.importance, 5)
                    )[:10]
                ],
                "style_summary": None
            }

            if style_guide.style_analysis:
                sa = style_guide.style_analysis
                preview_data["style_summary"] = {
                    "dialogue_style": sa.dialogue_style,
                    "number_style": sa.number_style,
                    "total_words": sa.statistics.total_words,
                    "total_sentences": sa.statistics.total_sentences,
                    "consistency_issues_count": len(sa.consistency_issues),
                    "recommendations_count": len(sa.recommendations)
                }

            return ApiResponse(success=True, data={
                "format": "preview",
                "preview": preview_data,
                "project_name": project.name
            })

        # Devolver en el formato solicitado
        if format == "markdown":
            return ApiResponse(success=True, data={
                "format": "markdown",
                "content": style_guide.to_markdown(),
                "project_name": project.name
            })
        elif format == "pdf":
            # Generar PDF como base64 string
            import base64
            import io

            try:
                # Intentar usar reportlab si está disponible
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import cm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib import colors

                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
                styles = getSampleStyleSheet()

                # Estilos personalizados
                title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=20)
                heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=10, spaceBefore=15)
                normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)

                elements = []

                # Título
                elements.append(Paragraph(f"Guía de Estilo - {style_guide.project_name}", title_style))
                elements.append(Paragraph(f"Generado: {style_guide.generated_date}", normal_style))
                elements.append(Spacer(1, 20))

                # Resumen
                elements.append(Paragraph("Resumen", heading_style))
                summary_data = [
                    ["Total de entidades", str(style_guide.total_entities)],
                    ["Personajes", str(len(style_guide.characters))],
                    ["Ubicaciones", str(len(style_guide.locations))],
                    ["Organizaciones", str(len(style_guide.organizations))],
                    ["Variaciones de grafía", str(style_guide.total_spelling_variants)],
                ]
                summary_table = Table(summary_data, colWidths=[8*cm, 4*cm])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 15))

                # Personajes principales
                if style_guide.characters:
                    elements.append(Paragraph("Personajes Principales", heading_style))
                    main_chars = [c for c in style_guide.characters if c.importance in ("principal", "critical", "high")][:10]
                    for char in main_chars:
                        char_text = f"<b>{char.canonical_name}</b>"
                        if char.aliases:
                            char_text += f" (también: {', '.join(char.aliases[:3])})"
                        elements.append(Paragraph(char_text, normal_style))
                    elements.append(Spacer(1, 10))

                # Decisiones de grafía
                if style_guide.spelling_decisions:
                    elements.append(Paragraph("Decisiones de Grafía", heading_style))
                    for decision in style_guide.spelling_decisions[:10]:
                        decision_text = f"<b>{decision.canonical_form}</b>: {', '.join(decision.variants) if decision.variants else 'Sin variantes'}"
                        elements.append(Paragraph(decision_text, normal_style))
                    elements.append(Spacer(1, 10))

                # Análisis estilístico
                if style_guide.style_analysis:
                    sa = style_guide.style_analysis
                    elements.append(Paragraph("Análisis Estilístico", heading_style))
                    style_info = [
                        f"Estilo de diálogos: {sa.dialogue_style}",
                        f"Estilo de números: {sa.number_style}",
                        f"Total de palabras: {sa.statistics.total_words:,}",
                        f"Total de oraciones: {sa.statistics.total_sentences:,}",
                    ]
                    for info in style_info:
                        elements.append(Paragraph(info, normal_style))

                    if sa.consistency_issues:
                        elements.append(Spacer(1, 10))
                        elements.append(Paragraph("Inconsistencias detectadas:", normal_style))
                        for issue in sa.consistency_issues[:5]:
                            elements.append(Paragraph(f"• {issue}", normal_style))

                # Construir PDF
                doc.build(elements)
                pdf_bytes = buffer.getvalue()
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

                return ApiResponse(success=True, data={
                    "format": "pdf",
                    "content": pdf_base64,
                    "content_type": "application/pdf",
                    "filename": f"guia_estilo_{project.name}.pdf",
                    "project_name": project.name
                })

            except ImportError:
                # Si reportlab no está disponible, devolver error con sugerencia
                return ApiResponse(
                    success=False,
                    error="Exportación PDF no disponible. Instale reportlab: pip install reportlab",
                    data={
                        "format": "pdf",
                        "fallback_format": "markdown",
                        "content": style_guide.to_markdown(),
                        "project_name": project.name
                    }
                )
        else:
            return ApiResponse(success=True, data={
                "format": "json",
                "content": style_guide.to_dict(),
                "project_name": project.name
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating style guide for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Timeline Temporal
# ============================================================================

@app.get("/api/projects/{project_id}/timeline", response_model=ApiResponse)
async def get_project_timeline(project_id: int, force_refresh: bool = False):
    """
    Obtiene el timeline temporal del proyecto.

    Lee el timeline desde la base de datos si ya fue analizado.
    Solo recalcula si no hay datos o se fuerza el refresh.

    Args:
        project_id: ID del proyecto
        force_refresh: Si True, recalcula el timeline ignorando el caché

    Returns:
        ApiResponse con datos del timeline:
        - events: Lista de eventos temporales
        - markers_count: Número de marcadores detectados
        - anchor_count: Número de anclas temporales (fechas absolutas)
        - time_span: Rango temporal de la historia (si se puede determinar)
        - mermaid: Diagrama Mermaid del timeline
    """
    try:
        if not chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        # Verificar que el proyecto existe
        if project_manager:
            result = project_manager.get(project_id)
            if result.is_failure:
                raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Intentar leer timeline desde la base de datos
        from narrative_assistant.persistence.timeline import TimelineRepository

        timeline_repo = TimelineRepository()

        if not force_refresh and timeline_repo.has_timeline(project_id):
            # Leer desde BD (rápido)
            events = timeline_repo.get_events(project_id)
            markers_count = timeline_repo.get_markers_count(project_id)

            # Contar tipos de eventos
            anchor_count = sum(1 for e in events if e.story_date_resolution in ("EXACT_DATE", "MONTH", "YEAR"))
            analepsis_count = sum(1 for e in events if e.narrative_order == "ANALEPSIS")
            prolepsis_count = sum(1 for e in events if e.narrative_order == "PROLEPSIS")

            # Convertir a formato esperado por el frontend
            events_data = [e.to_dict() for e in events]

            logger.info(f"Timeline loaded from DB for project {project_id}: {len(events)} events")

            return ApiResponse(
                success=True,
                data={
                    "events": events_data,
                    "markers_count": markers_count,
                    "anchor_count": anchor_count,
                    "analepsis_count": analepsis_count,
                    "prolepsis_count": prolepsis_count,
                    "time_span": None,  # No disponible desde BD
                    "mermaid": None,  # No disponible desde BD
                    "inconsistencies": [],  # Las inconsistencias están en alerts
                    "from_cache": True,
                },
                message="Timeline cargado desde base de datos"
            )

        # Si no hay datos en BD o se fuerza refresh, calcular
        chapters = chapter_repository.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "events": [],
                    "markers_count": 0,
                    "anchor_count": 0,
                    "time_span": None,
                    "mermaid": "No hay capítulos para analizar.",
                    "inconsistencies": [],
                },
                message="El proyecto no tiene capítulos para analizar"
            )

        # Importar módulo temporal
        from narrative_assistant.temporal import (
            TemporalMarkerExtractor,
            TimelineBuilder,
            TemporalConsistencyChecker,
        )

        # Extraer marcadores temporales
        marker_extractor = TemporalMarkerExtractor()
        all_markers = []

        for chapter in chapters:
            chapter_markers = marker_extractor.extract(
                text=chapter.content,
                chapter=chapter.chapter_number,
            )
            all_markers.extend(chapter_markers)
            logger.debug(f"Chapter {chapter.chapter_number}: {len(chapter_markers)} markers, text length: {len(chapter.content)}")

        logger.info(f"Timeline extraction: {len(chapters)} chapters, {len(all_markers)} total markers")

        # Construir timeline
        builder = TimelineBuilder()
        chapter_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "start_position": ch.start_char,
            }
            for ch in chapters
        ]

        timeline = builder.build_from_markers(all_markers, chapter_data)

        # Verificar consistencia
        checker = TemporalConsistencyChecker()
        inconsistencies = checker.check(timeline, all_markers)

        # Exportar datos
        json_data = builder.export_to_json()
        mermaid = builder.export_to_mermaid()

        # Persistir timeline si se calculó
        try:
            from narrative_assistant.persistence.timeline import (
                TimelineEventData,
                TemporalMarkerData,
            )

            events_data = []
            for event in timeline.events:
                story_date_str = event.story_date.isoformat() if event.story_date else None
                events_data.append(TimelineEventData(
                    id=None,
                    project_id=project_id,
                    event_id=event.id,
                    chapter=event.chapter,
                    paragraph=event.paragraph,
                    description=event.description,
                    story_date=story_date_str,
                    story_date_resolution=event.story_date_resolution.value if event.story_date_resolution else "UNKNOWN",
                    narrative_order=event.narrative_order.value if event.narrative_order else "CHRONOLOGICAL",
                    discourse_position=event.discourse_position,
                    confidence=event.confidence,
                ))

            markers_data = []
            for marker in all_markers:
                markers_data.append(TemporalMarkerData(
                    id=None,
                    project_id=project_id,
                    chapter=marker.chapter,
                    marker_type=marker.marker_type.value if hasattr(marker.marker_type, 'value') else str(marker.marker_type),
                    text=marker.text,
                    start_char=marker.start_char,
                    end_char=marker.end_char,
                    confidence=marker.confidence,
                    year=marker.year,
                    month=marker.month,
                    day=marker.day,
                    direction=marker.direction.value if hasattr(marker, 'direction') and marker.direction and hasattr(marker.direction, 'value') else getattr(marker, 'direction', None),
                    quantity=getattr(marker, 'quantity', None),
                    magnitude=getattr(marker, 'magnitude', None),
                    age=getattr(marker, 'age', None),
                    entity_id=getattr(marker, 'entity_id', None),
                ))

            timeline_repo.save_events(project_id, events_data)
            timeline_repo.save_markers(project_id, markers_data)
            logger.info(f"Timeline persisted for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to persist timeline: {e}")

        # Formatear inconsistencias
        inconsistencies_data = [
            {
                "type": inc.inconsistency_type.value,
                "severity": inc.severity.value,
                "description": inc.description,
                "chapter": inc.chapter,
                "expected": inc.expected,
                "found": inc.found,
                "suggestion": inc.suggestion,
                "confidence": inc.confidence,
            }
            for inc in inconsistencies
        ]

        return ApiResponse(
            success=True,
            data={
                "events": json_data["events"],
                "markers_count": len(all_markers),
                "anchor_count": json_data["anchor_events"],
                "analepsis_count": json_data["analepsis_count"],
                "prolepsis_count": json_data["prolepsis_count"],
                "time_span": json_data["time_span"],
                "mermaid": mermaid,
                "inconsistencies": inconsistencies_data,
                "from_cache": False,
            }
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Temporal module not available: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis temporal no disponible"
        )
    except Exception as e:
        logger.error(f"Error getting timeline for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/temporal-markers", response_model=ApiResponse)
async def get_temporal_markers(project_id: int, chapter: Optional[int] = None):
    """
    Obtiene los marcadores temporales detectados en el proyecto.

    Args:
        project_id: ID del proyecto
        chapter: Filtrar por número de capítulo (opcional)

    Returns:
        ApiResponse con lista de marcadores temporales
    """
    try:
        if not chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        # Obtener capítulos
        chapters = chapter_repository.get_by_project(project_id)

        if chapter is not None:
            chapters = [ch for ch in chapters if ch.chapter_number == chapter]

        if not chapters:
            return ApiResponse(
                success=True,
                data=[],
                message="No se encontraron capítulos"
            )

        # Importar y extraer marcadores
        from narrative_assistant.temporal import TemporalMarkerExtractor

        extractor = TemporalMarkerExtractor()
        all_markers = []

        for ch in chapters:
            markers = extractor.extract(ch.content, chapter=ch.chapter_number)
            for m in markers:
                all_markers.append({
                    "text": m.text,
                    "type": m.marker_type.value,
                    "chapter": m.chapter,
                    "start_char": m.start_char,
                    "end_char": m.end_char,
                    "direction": m.direction,
                    "magnitude": m.magnitude,
                    "quantity": m.quantity,
                    "age": m.age,
                    "year": m.year,
                    "month": m.month,
                    "day": m.day,
                    "confidence": m.confidence,
                })

        return ApiResponse(success=True, data=all_markers)

    except Exception as e:
        logger.error(f"Error getting temporal markers: {e}", exc_info=True)
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

        # Actualizar estado del proyecto a "analyzing" en la BD
        project.analysis_status = "analyzing"
        project.analysis_progress = 0.0
        project_manager.update(project)

        # Inicializar progreso
        import time as time_module
        now = time_module.time()
        analysis_progress_storage[project_id] = {
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
            phases = analysis_progress_storage[project_id]["phases"]

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
                    word_count = analysis_progress_storage[project_id].get("metrics", {}).get("word_count", 500)
                    base_estimate = 60 + int(word_count * 0.2)

                    # Ajustar según peso restante
                    total_remaining = int(base_estimate * remaining_weight)

                # El tiempo nunca puede ser menor que la suma de fases pendientes
                analysis_progress_storage[project_id]["estimated_seconds_remaining"] = max(min_time_remaining, total_remaining)

                # Guardar timestamp de última actualización para cálculo dinámico
                analysis_progress_storage[project_id]["_last_progress_update"] = time.time()

            def check_cancelled():
                """Verifica si el análisis fue cancelado por el usuario."""
                if analysis_progress_storage.get(project_id, {}).get("status") == "cancelled":
                    raise Exception("Análisis cancelado por el usuario")

            # Obtener sesión de BD para este thread
            from narrative_assistant.persistence.database import get_database
            db_session = get_database()

            try:
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
                analysis_progress_storage[project_id]["progress"] = pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Leyendo el documento..."

                doc_format = detect_format(tmp_path)
                parser = get_parser(doc_format)
                parse_result = parser.parse(tmp_path)

                if parse_result.is_failure:
                    raise Exception(f"Error parsing document: {parse_result.error}")

                raw_document = parse_result.value
                full_text = raw_document.full_text
                word_count = len(full_text.split())

                analysis_progress_storage[project_id]["progress"] = pct_end
                analysis_progress_storage[project_id]["metrics"]["word_count"] = word_count
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
                analysis_progress_storage[project_id]["progress"] = cls_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Clasificando tipo de documento..."

                from narrative_assistant.parsers.document_classifier import classify_document, DocumentType

                doc_title = project.name if project else None
                classification = classify_document(full_text, title=doc_title)  # Usa muestreo múltiple
                document_type = classification.document_type.value
                analysis_settings = classification.recommended_settings

                logger.info(f"Document classified as: {document_type} (confidence: {classification.confidence:.2f})")
                logger.debug(f"Classification indicators: {classification.indicators}")

                # Guardar clasificación en el progreso para uso posterior
                analysis_progress_storage[project_id]["document_type"] = document_type
                analysis_progress_storage[project_id]["document_classification"] = {
                    "type": document_type,
                    "confidence": classification.confidence,
                    "indicators": classification.indicators,
                    "settings": analysis_settings,
                }

                # Actualizar settings del proyecto con el tipo de documento
                try:
                    project_manager = ProjectManager(db_session)
                    project_settings = project.settings or {}
                    project_settings["document_type"] = document_type
                    project_settings["document_classification"] = {
                        "type": document_type,
                        "confidence": classification.confidence,
                        "indicators": classification.indicators,
                    }
                    project_settings["recommended_analysis"] = analysis_settings

                    project_manager.update_project(project_id, {
                        "settings": json.dumps(project_settings)
                    })
                    logger.info(f"Saved document type to project settings: {document_type}")
                except Exception as e:
                    logger.warning(f"Could not save document type to project: {e}")

                # Completar fase de clasificación
                analysis_progress_storage[project_id]["progress"] = cls_pct_end
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
                analysis_progress_storage[project_id]["progress"] = pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Identificando la estructura del documento..."

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
                if chapter_repository:
                    chapters_with_ids = chapter_repository.get_by_project(project_id)
                    logger.debug(f"Loaded {len(chapters_with_ids)} chapters with IDs for mention mapping")

                # Helper para encontrar chapter_id basado en posición de carácter
                def find_chapter_id_for_position(char_position: int) -> int | None:
                    """Encuentra el chapter_id que contiene la posición de carácter dada."""
                    for ch in chapters_with_ids:
                        if ch.start_char <= char_position <= ch.end_char:
                            return ch.id
                    return None

                analysis_progress_storage[project_id]["progress"] = pct_end
                analysis_progress_storage[project_id]["metrics"]["chapters_found"] = chapters_count
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
                analysis_progress_storage[project_id]["progress"] = ner_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Buscando personajes, lugares y otros elementos..."

                # Callback para actualizar progreso durante NER
                def ner_progress_callback(fase: str, pct: float, msg: str):
                    """Actualiza el progreso del análisis durante NER."""
                    # NER va de ner_pct_start a ner_pct_end
                    ner_range = ner_pct_end - ner_pct_start
                    ner_progress = ner_pct_start + int(pct * ner_range)
                    analysis_progress_storage[project_id]["progress"] = ner_progress
                    analysis_progress_storage[project_id]["current_action"] = msg
                    update_time_remaining()

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
                                analysis_progress_storage[project_id]["progress"] = min(ner_pct_end, sub_progress)
                                update_time_remaining()

                        except Exception as e:
                            logger.warning(f"Error creating entity {first_mention.text}: {e}")

                analysis_progress_storage[project_id]["progress"] = ner_pct_end
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
                analysis_progress_storage[project_id]["current_action"] = "Verificando personajes detectados..."
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
                analysis_progress_storage[project_id]["progress"] = fusion_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Unificando personajes mencionados de diferentes formas..."
                analysis_progress_storage[project_id]["current_action"] = "Preparando unificación..."

                try:
                    from narrative_assistant.entities.semantic_fusion import get_semantic_fusion_service
                    from narrative_assistant.nlp.coref import resolve_coreferences
                    from narrative_assistant.entities.models import EntityType

                    fusion_service = get_semantic_fusion_service()
                    entity_repo = get_entity_repository()

                    analysis_progress_storage[project_id]["current_action"] = f"Comparando {len(entities)} entidades..."

                    # 1. Aplicar fusión semántica a entidades del mismo tipo
                    entities_by_type: dict[EntityType, list] = {}
                    for ent in entities:
                        if ent.entity_type not in entities_by_type:
                            entities_by_type[ent.entity_type] = []
                        entities_by_type[ent.entity_type].append(ent)

                    fusion_pairs: list[tuple] = []  # (entity_to_keep, entity_to_merge)

                    for entity_type, type_entities in entities_by_type.items():
                        # Solo fusionar si hay más de una entidad del mismo tipo
                        if len(type_entities) < 2:
                            continue

                        # Comparar cada par de entidades
                        for i, ent1 in enumerate(type_entities):
                            for j, ent2 in enumerate(type_entities):
                                if i >= j:  # Evitar duplicados y compararse consigo mismo
                                    continue

                                # Calcular si deben fusionarse
                                result = fusion_service.should_merge(ent1, ent2)

                                if result.should_merge:
                                    logger.info(
                                        f"Fusión sugerida: '{ent1.canonical_name}' + '{ent2.canonical_name}' "
                                        f"(similaridad: {result.similarity:.2f}, razón: {result.reason})"
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
                        analysis_progress_storage[project_id]["current_action"] = f"Unificando {len(fusion_pairs)} pares de nombres similares..."

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
                                analysis_progress_storage[project_id]["current_action"] = f"Unificando nombres: {keep_entity.canonical_name}... ({idx + 1}/{len(fusion_pairs)})"

                        except Exception as e:
                            logger.warning(f"Error fusionando {merge_entity.canonical_name} → {keep_entity.canonical_name}: {e}")

                    # Actualizar lista de entidades activas
                    entities = [e for e in entities if e.id not in merged_entity_ids]

                    if fusion_pairs:
                        analysis_progress_storage[project_id]["current_action"] = f"Unificados {len(merged_entity_ids)} personajes duplicados"

                    analysis_progress_storage[project_id]["progress"] = 57
                    update_time_remaining()

                    # 2. Aplicar resolución de correferencias con votación multi-método
                    # Usa: embeddings semánticos, LLM local (Ollama), análisis morfosintáctico, heurísticas
                    analysis_progress_storage[project_id]["current_phase"] = "Identificando referencias cruzadas entre personajes..."

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
                    analysis_progress_storage[project_id]["progress"] = fusion_pct_end
                    # Actualizar con entidades únicas (después de fusión)
                    analysis_progress_storage[project_id]["metrics"]["entities_found"] = len(entities)
                    analysis_progress_storage[project_id]["current_action"] = f"Encontrados {len(entities)} personajes y elementos únicos"
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
                        analysis_progress_storage[project_id]["current_action"] = "Buscando menciones adicionales..."

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
                            analysis_progress_storage[project_id]["current_action"] = f"Encontradas {additional_count} menciones adicionales"

                    except Exception as mf_err:
                        logger.warning(f"MentionFinder failed (non-critical): {mf_err}")

                    # ========== RECALCULAR IMPORTANCIA FINAL ==========
                    # La importancia se calcula DESPUÉS de fusiones y correferencias
                    # basada en el conteo final de menciones en la BD
                    logger.info("Recalculando importancia de entidades...")
                    db = get_database()
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
                analysis_progress_storage[project_id]["progress"] = attr_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Analizando características de los personajes..."

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
                        analysis_progress_storage[project_id]["current_action"] = "Análisis avanzado con GPU activado"
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

                            analysis_progress_storage[project_id]["current_action"] = f"Analizando: {names_str} ({batch_end}/{total_chars})"

                            # Calcular progreso (10% a 45% de la fase)
                            batch_progress = 0.1 + (0.35 * batch_end / max(total_chars, 1))
                            analysis_progress_storage[project_id]["progress"] = attr_pct_start + int((attr_pct_end - attr_pct_start) * batch_progress)

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
                        analysis_progress_storage[project_id]["progress"] = attr_pct_start + int((attr_pct_end - attr_pct_start) * 0.5)
                        analysis_progress_storage[project_id]["current_action"] = "Registrando características encontradas..."

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
                                    analysis_progress_storage[project_id]["progress"] = attr_pct_start + int((attr_pct_end - attr_pct_start) * save_progress)
                                    analysis_progress_storage[project_id]["current_action"] = f"Guardando características... ({attrs_processed}/{total_attrs})"

                phase_durations["attributes"] = time.time() - phase_start_times["attributes"]
                analysis_progress_storage[project_id]["progress"] = attr_pct_end
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["attributes_extracted"] = len(attributes)
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
                analysis_progress_storage[project_id]["progress"] = cons_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Verificando la coherencia del relato..."

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

                analysis_progress_storage[project_id]["current_action"] = "Verificando estado vital de personajes..."

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
                analysis_progress_storage[project_id]["current_action"] = "Verificando ubicaciones de personajes..."

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
                        logger.info(f"Character location analysis: {len(location_report.events)} events, "
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
                analysis_progress_storage[project_id]["current_action"] = "Generando resumen de avance narrativo..."

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
                analysis_progress_storage[project_id]["metrics"]["vital_status_deaths"] = (
                    len(vital_status_report.death_events) if vital_status_report else 0
                )
                analysis_progress_storage[project_id]["metrics"]["location_events"] = (
                    len(location_report.events) if location_report else 0
                )

                phase_durations["consistency"] = time.time() - phase_start_times["consistency"]
                analysis_progress_storage[project_id]["progress"] = cons_pct_end
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["inconsistencies_found"] = len(inconsistencies)
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
                analysis_progress_storage[project_id]["progress"] = grammar_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Revisando la redacción..."

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
                    analysis_progress_storage[project_id]["current_phase"] = "Buscando repeticiones y errores tipográficos..."

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
                analysis_progress_storage[project_id]["progress"] = grammar_pct_end
                analysis_progress_storage[project_id]["metrics"]["grammar_issues_found"] = len(grammar_issues)
                analysis_progress_storage[project_id]["metrics"]["correction_suggestions"] = len(correction_issues)
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
                analysis_progress_storage[project_id]["progress"] = alerts_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Preparando observaciones y sugerencias..."

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
                analysis_progress_storage[project_id]["progress"] = 100
                analysis_progress_storage[project_id]["metrics"]["alerts_generated"] = alerts_created
                phases[8]["completed"] = True
                phases[8]["current"] = False
                phases[8]["duration"] = round(phase_durations["alerts"], 1)

                # ========== COMPLETADO ==========
                analysis_progress_storage[project_id]["status"] = "completed"
                analysis_progress_storage[project_id]["current_phase"] = "Análisis completado"
                analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 0

                total_duration = round(time.time() - start_time, 1)
                analysis_progress_storage[project_id]["metrics"]["total_duration_seconds"] = total_duration

                # Preparar stats para el frontend (UI-friendly names)
                metrics = analysis_progress_storage[project_id]["metrics"]
                analysis_progress_storage[project_id]["stats"] = {
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
    import time

    try:
        if project_id not in analysis_progress_storage:
            # No hay análisis en curso, devolver estado "idle" para que el frontend
            # sepa que debe detener el polling
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

        progress = analysis_progress_storage[project_id].copy()

        # Recalcular tiempo restante dinámicamente
        # Esto evita que el tiempo se quede "congelado" durante fases largas
        if progress.get("status") == "running":
            start_time = progress.get("_start_time")
            last_update = progress.get("_last_progress_update")
            base_estimate = progress.get("estimated_seconds_remaining", 60)

            if start_time and last_update:
                now = time.time()
                time_since_update = now - last_update

                # Si ha pasado tiempo desde la última actualización,
                # decrementar el tiempo estimado (mínimo 10s para no llegar a 0)
                if time_since_update > 1:
                    adjusted_estimate = max(10, base_estimate - int(time_since_update))
                    progress["estimated_seconds_remaining"] = adjusted_estimate

                    # Si el tiempo estimado se acerca a 0, añadir más tiempo
                    # (indica que la estimación fue muy optimista)
                    if adjusted_estimate <= 15:
                        # Añadir 30s extra y actualizar la base
                        analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 45
                        analysis_progress_storage[project_id]["_last_progress_update"] = now
                        progress["estimated_seconds_remaining"] = 45

        return ApiResponse(success=True, data=progress)

    except Exception as e:
        logger.error(f"Error getting analysis progress for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/analysis/cancel", response_model=ApiResponse)
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
        if project_id not in analysis_progress_storage:
            return ApiResponse(
                success=False,
                error="No hay análisis en curso para este proyecto"
            )

        current_status = analysis_progress_storage[project_id].get("status")
        if current_status in ("completed", "error", "cancelled"):
            return ApiResponse(
                success=False,
                error=f"El análisis ya ha terminado con estado: {current_status}"
            )

        # Marcar como cancelado
        analysis_progress_storage[project_id]["status"] = "cancelled"
        analysis_progress_storage[project_id]["current_phase"] = "Análisis cancelado por el usuario"

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


@app.get("/api/projects/{project_id}/analysis/stream")
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

                # Obtener progreso actual
                if project_id not in analysis_progress_storage:
                    # Esperar a que inicie el análisis
                    await asyncio.sleep(0.5)

                    # Enviar keepalive si es necesario
                    if time.time() - last_keepalive > keepalive_interval:
                        yield f"event: keepalive\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                        last_keepalive = time.time()
                    continue

                progress_data = analysis_progress_storage[project_id].copy()
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
                    "entity_count": 0,
                    "entities": [],
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

        # Ajustar umbrales según tamaño del documento
        # Para documentos pequeños (<10k palabras), ser más permisivo
        # Para documentos grandes (>50k palabras), ser más estricto
        total_mentions = len(all_mentions)
        total_chars = sum(len(c.content) for c in chapters)

        if total_mentions < 20 or total_chars < 20000:
            # Documento pequeño: umbral mínimo de 1 co-ocurrencia
            clustering_engine.COOCCURRENCE_THRESHOLD = 1
            clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.2
        elif total_mentions < 100 or total_chars < 100000:
            # Documento mediano
            clustering_engine.COOCCURRENCE_THRESHOLD = 2
            clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.3
        else:
            # Documento grande
            clustering_engine.COOCCURRENCE_THRESHOLD = 3
            clustering_engine.RELATION_CONFIDENCE_THRESHOLD = 0.4

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

        # Construir respuesta y convertir tipos numpy a Python nativos
        response_data = {
            "project_id": project_id,
            "entity_count": len(entities),
            # Incluir entidades para el grafo del frontend
            "entities": [
                {
                    "id": e.id,
                    "name": e.canonical_name,
                    "type": e.entity_type.value,
                    "importance": e.importance or 1,
                    "mentionCount": e.mention_count or 0,
                }
                for e in entities
            ],
            "relations": clustering_result.get("relations", []),
            "clusters": clustering_result.get("clusters", []),
            "dendrogram_data": clustering_result.get("dendrogram_data"),
            "mentions": [m.to_dict() for m in knowledge_analyzer.get_all_mentions()],
            "opinions": [o.to_dict() for o in knowledge_analyzer.get_all_opinions()],
            "intentions": [i.to_dict() for i in knowledge_analyzer.get_all_intentions()],
            "asymmetries": asymmetries,
        }

        return ApiResponse(
            success=True,
            data=convert_numpy_types(response_data)
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


@app.get("/api/projects/{project_id}/characters/{entity_id}/knowledge", response_model=ApiResponse)
async def get_character_knowledge(
    project_id: int,
    entity_id: int,
    mode: str = Query("auto", description="Modo: auto, rules, llm, hybrid")
):
    """
    Obtiene el conocimiento que un personaje tiene sobre otros.

    Analiza el texto para detectar qué sabe el personaje sobre otros personajes:
    - Atributos físicos/psicológicos
    - Ubicación
    - Secretos
    - Historia pasada

    Args:
        project_id: ID del proyecto
        entity_id: ID del personaje
        mode: Modo de extracción (auto, rules, llm, hybrid)

    Returns:
        ApiResponse con hechos de conocimiento del personaje
    """
    try:
        from narrative_assistant.analysis.character_knowledge import (
            CharacterKnowledgeAnalyzer,
            KnowledgeExtractionMode,
        )
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener entidad
        entity_repo = get_entity_repository()
        entity = entity_repo.get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Personaje {entity_id} no encontrado")

        # Determinar modo
        mode_map = {
            "auto": None,
            "rules": KnowledgeExtractionMode.RULES,
            "llm": KnowledgeExtractionMode.LLM,
            "hybrid": KnowledgeExtractionMode.HYBRID,
        }
        extraction_mode = mode_map.get(mode.lower())

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "entity_id": entity_id,
                    "entity_name": entity.canonical_name,
                    "knowledge_facts": [],
                    "message": "No hay capítulos para analizar"
                }
            )

        # Analizar conocimiento
        analyzer = CharacterKnowledgeAnalyzer(project_id=project_id)

        # Registrar todas las entidades del proyecto
        all_entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        for e in all_entities:
            analyzer.register_entity(e.id, e.canonical_name, e.aliases)

        # Analizar capítulos
        for chapter in chapters:
            analyzer.analyze_narration(
                chapter.content,
                chapter.chapter_number,
                chapter.start_char,
                extraction_mode=extraction_mode
            )

        # Filtrar hechos donde este personaje es el "knower"
        all_knowledge = analyzer.get_all_knowledge()
        character_knowledge = [
            k for k in all_knowledge
            if k.knower_entity_id == entity_id
        ]

        # También obtener qué otros saben de este personaje
        knowledge_about = [
            k for k in all_knowledge
            if k.known_entity_id == entity_id
        ]

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "entity_id": entity_id,
                "entity_name": entity.canonical_name,
                "knows_about_others": [k.to_dict() for k in character_knowledge],
                "others_know_about": [k.to_dict() for k in knowledge_about],
                "stats": {
                    "facts_known": len(character_knowledge),
                    "facts_about": len(knowledge_about),
                    "chapters_analyzed": len(chapters),
                    "extraction_mode": mode,
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character knowledge: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/relationships", response_model=ApiResponse)
async def create_relationship(project_id: int, request: Request):
    """
    Crea una nueva relación entre dos entidades.

    Body JSON:
        source_entity_id: ID de la entidad origen
        target_entity_id: ID de la entidad destino
        relation_type: Tipo de relación (ej: "friend", "family", "enemy", "love", "colleague")
        description: Descripción opcional de la relación
        bidirectional: Si la relación es bidireccional (default: true)

    Returns:
        ApiResponse con la relación creada
    """
    try:
        from narrative_assistant.relationships.repository import get_relationship_repository
        from narrative_assistant.relationships.models import EntityRelationship, RelationType
        from narrative_assistant.entities.repository import get_entity_repository
        import uuid
        from datetime import datetime

        body = await request.json()

        source_entity_id = body.get("source_entity_id")
        target_entity_id = body.get("target_entity_id")
        relation_type_str = body.get("relation_type", "other")
        description = body.get("description", "")
        bidirectional = body.get("bidirectional", True)

        if not source_entity_id or not target_entity_id:
            return ApiResponse(success=False, error="source_entity_id y target_entity_id son requeridos")

        # Obtener nombres de entidades
        entity_repo = get_entity_repository()
        source_entity = entity_repo.get_entity(source_entity_id)
        target_entity = entity_repo.get_entity(target_entity_id)

        if not source_entity or not target_entity:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Mapear tipo de relación
        type_mapping = {
            "friend": RelationType.FRIEND,
            "family": RelationType.FAMILY,
            "enemy": RelationType.ENEMY,
            "love": RelationType.LOVE,
            "colleague": RelationType.COLLEAGUE,
            "mentor": RelationType.MENTOR,
            "rival": RelationType.RIVAL,
            "ally": RelationType.ALLY,
            "acquaintance": RelationType.ACQUAINTANCE,
        }
        relation_type = type_mapping.get(relation_type_str.lower(), RelationType.OTHER)

        # Crear relación
        relationship = EntityRelationship(
            id=str(uuid.uuid4()),
            project_id=project_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            source_entity_name=source_entity.canonical_name,
            target_entity_name=target_entity.canonical_name,
            relation_type=relation_type,
            bidirectional=bidirectional,
            confidence=1.0,  # Relación manual, confianza total
            user_confirmed=True,
            evidence_texts=[description] if description else [],
            created_at=datetime.now(),
        )

        rel_repo = get_relationship_repository()
        rel_id = rel_repo.create_relationship(relationship)

        return ApiResponse(
            success=True,
            data={
                "id": rel_id,
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relation_type": relation_type.value,
                "description": description,
                "bidirectional": bidirectional,
            }
        )

    except Exception as e:
        logger.error(f"Error creating relationship: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/relationships/{relationship_id}", response_model=ApiResponse)
async def delete_relationship(project_id: int, relationship_id: str):
    """
    Elimina una relación entre entidades.

    Args:
        project_id: ID del proyecto
        relationship_id: ID de la relación a eliminar

    Returns:
        ApiResponse con resultado de la eliminación
    """
    try:
        from narrative_assistant.relationships.repository import get_relationship_repository

        rel_repo = get_relationship_repository()
        success = rel_repo.delete_relationship(relationship_id)

        if success:
            return ApiResponse(success=True, data={"deleted": relationship_id})
        else:
            return ApiResponse(success=False, error="Relación no encontrada")

    except Exception as e:
        logger.error(f"Error deleting relationship {relationship_id}: {e}", exc_info=True)
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


@app.post("/api/ollama/start", response_model=ApiResponse)
async def start_ollama_service():
    """
    Inicia el servicio de Ollama si está instalado pero no corriendo.

    Returns:
        ApiResponse con resultado de la operación
    """
    try:
        from narrative_assistant.llm.ollama_manager import get_ollama_manager, OllamaStatus

        manager = get_ollama_manager()
        logger.info(f"Iniciando Ollama - installed: {manager.is_installed}, running: {manager.is_running}")

        # Verificar si está instalado
        if not manager.is_installed:
            return ApiResponse(
                success=False,
                error="Ollama no está instalado",
                data={
                    "status": OllamaStatus.NOT_INSTALLED.value,
                    "action_required": "install",
                    "install_url": "https://ollama.com/download"
                }
            )

        # Verificar si ya está corriendo
        if manager.is_running:
            return ApiResponse(
                success=True,
                data={
                    "status": OllamaStatus.RUNNING.value,
                    "message": "Ollama ya está corriendo"
                }
            )

        # Intentar iniciar
        logger.info("Llamando a start_service()...")
        success, message = manager.start_service()
        logger.info(f"start_service() retornó: success={success}, message={message}")

        if success:
            return ApiResponse(
                success=True,
                data={
                    "status": OllamaStatus.RUNNING.value,
                    "message": message
                }
            )
        else:
            return ApiResponse(
                success=False,
                error=message,
                data={
                    "status": OllamaStatus.ERROR.value
                }
            )

    except Exception as e:
        logger.error(f"Error starting Ollama: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/ollama/status", response_model=ApiResponse)
async def get_ollama_status():
    """
    Obtiene el estado detallado de Ollama.

    Returns:
        ApiResponse con estado de instalación, servicio y modelos
    """
    try:
        from narrative_assistant.llm.ollama_manager import get_ollama_manager, OllamaStatus

        manager = get_ollama_manager()
        status = manager.status

        return ApiResponse(
            success=True,
            data={
                "status": status.value,
                "is_installed": manager.is_installed,
                "is_running": manager.is_running,
                "version": manager.get_version() if manager.is_installed else None,
                "downloaded_models": manager.downloaded_models,
                "available_models": [
                    {
                        "name": m.name,
                        "display_name": m.display_name,
                        "size_gb": m.size_gb,
                        "description": m.description,
                        "is_downloaded": m.is_downloaded,
                        "is_default": m.is_default
                    }
                    for m in manager.available_models
                ],
                "install_url": "https://ollama.com/download"
            }
        )

    except Exception as e:
        logger.error(f"Error getting Ollama status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/ollama/pull/{model_name}", response_model=ApiResponse)
async def pull_ollama_model(model_name: str):
    """
    Descarga un modelo de Ollama.

    Args:
        model_name: Nombre del modelo a descargar (ej: llama3.2)

    Returns:
        ApiResponse con resultado de la operación
    """
    try:
        from narrative_assistant.llm.ollama_manager import get_ollama_manager

        manager = get_ollama_manager()

        if not manager.is_installed:
            return ApiResponse(
                success=False,
                error="Ollama no está instalado"
            )

        if not manager.is_running:
            # Intentar iniciar primero
            success, msg = manager.start_service()
            if not success:
                return ApiResponse(
                    success=False,
                    error=f"No se pudo iniciar Ollama: {msg}"
                )

        # Descargar modelo
        success, message = manager.download_model(model_name)

        return ApiResponse(
            success=success,
            data={"message": message} if success else None,
            error=message if not success else None
        )

    except Exception as e:
        logger.error(f"Error pulling model {model_name}: {e}", exc_info=True)
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
# Emotional Analysis Endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/emotional-analysis", response_model=ApiResponse)
async def get_emotional_analysis(project_id: int):
    """
    Obtiene el análisis de coherencia emocional de un proyecto.

    Devuelve las incoherencias emocionales detectadas:
    - Diálogos incoherentes con el estado emocional declarado
    - Acciones incoherentes con el estado emocional
    - Cambios emocionales abruptos sin justificación narrativa
    """
    try:
        from narrative_assistant.analysis.emotional_coherence import (
            get_emotional_coherence_checker,
            EmotionalIncoherence,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Obtener capítulos del proyecto
        chapters = chapter_repository.get_by_project(project_id)
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "incoherences": [],
                    "stats": {"total": 0}
                },
                message="No hay capítulos para analizar"
            )

        # Obtener entidades (personajes)
        entities = entity_repository.get_entities_by_project(project_id)
        character_names = [
            e.canonical_name for e in entities if e.entity_type == "PER"
        ]

        if not character_names:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "incoherences": [],
                    "stats": {"total": 0}
                },
                message="No hay personajes para analizar"
            )

        # Ejecutar análisis
        checker = get_emotional_coherence_checker()
        all_incoherences = []

        for chapter in chapters:
            # Extraer diálogos
            dialogue_result = detect_dialogues(chapter.content)
            if dialogue_result.is_success:
                dialogues = [
                    (
                        d.speaker_hint or "desconocido",
                        d.text,
                        d.start_char,
                        d.end_char,
                    )
                    for d in dialogue_result.value.dialogues
                ]
            else:
                dialogues = []

            # Analizar capítulo
            chapter_incoherences = checker.analyze_chapter(
                chapter_text=chapter.content,
                entity_names=character_names,
                dialogues=dialogues,
                chapter_id=chapter.chapter_number,
            )
            all_incoherences.extend(chapter_incoherences)

        # Agrupar por tipo
        by_type = {}
        for inc in all_incoherences:
            inc_type = inc.incoherence_type.value
            if inc_type not in by_type:
                by_type[inc_type] = 0
            by_type[inc_type] += 1

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "incoherences": [inc.to_dict() for inc in all_incoherences],
                "stats": {
                    "total": len(all_incoherences),
                    "by_type": by_type,
                    "chapters_analyzed": len(chapters),
                }
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis emocional no disponible"
        )
    except Exception as e:
        logger.error(f"Error in emotional analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/chapters/{chapter_number}/emotional-analysis", response_model=ApiResponse)
async def get_chapter_emotional_analysis(project_id: int, chapter_number: int):
    """
    Obtiene el análisis emocional de un capítulo específico.
    """
    try:
        from narrative_assistant.analysis.emotional_coherence import (
            get_emotional_coherence_checker,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Obtener el capítulo
        chapter = chapter_repository.get_chapter(project_id, chapter_number)
        if not chapter:
            return ApiResponse(
                success=False,
                error=f"Capítulo {chapter_number} no encontrado"
            )

        # Obtener personajes
        entities = entity_repository.get_entities_by_project(project_id)
        character_names = [
            e.canonical_name for e in entities if e.entity_type == "PER"
        ]

        # Extraer diálogos
        dialogue_result = detect_dialogues(chapter.content)
        if dialogue_result.is_success:
            dialogues = [
                (
                    d.speaker_hint or "desconocido",
                    d.text,
                    d.start_char,
                    d.end_char,
                )
                for d in dialogue_result.value.dialogues
            ]
        else:
            dialogues = []

        # Analizar
        checker = get_emotional_coherence_checker()
        incoherences = checker.analyze_chapter(
            chapter_text=chapter.content,
            entity_names=character_names,
            dialogues=dialogues,
            chapter_id=chapter_number,
        )

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_number": chapter_number,
                "incoherences": [inc.to_dict() for inc in incoherences],
                "dialogues_analyzed": len(dialogues),
                "characters_checked": len(character_names),
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis emocional no disponible"
        )
    except Exception as e:
        logger.error(f"Error in chapter emotional analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/characters/{character_name}/emotional-profile", response_model=ApiResponse)
async def get_character_emotional_profile(project_id: int, character_name: str):
    """
    Obtiene el perfil emocional de un personaje específico.

    Incluye:
    - Estados emocionales declarados a lo largo del texto
    - Evolución emocional por capítulo
    - Incoherencias relacionadas con el personaje
    """
    try:
        from narrative_assistant.nlp.sentiment import get_sentiment_analyzer
        from narrative_assistant.analysis.emotional_coherence import (
            get_emotional_coherence_checker,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Obtener capítulos
        chapters = chapter_repository.get_by_project(project_id)
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "character_name": character_name,
                    "emotional_states": [],
                    "evolution": [],
                    "incoherences": [],
                }
            )

        sentiment_analyzer = get_sentiment_analyzer()
        checker = get_emotional_coherence_checker()

        all_states = []
        all_incoherences = []
        evolution = []

        for chapter in chapters:
            # Extraer estados emocionales declarados del personaje
            states = sentiment_analyzer.extract_declared_emotions(
                text=chapter.content,
                entity_names=[character_name],
                chapter_id=chapter.chapter_number,
            )

            chapter_states = [s for s in states if s.entity_name.lower() == character_name.lower()]
            all_states.extend(chapter_states)

            # Analizar incoherencias
            dialogue_result = detect_dialogues(chapter.content)
            dialogues = []
            if dialogue_result.is_success:
                dialogues = [
                    (d.speaker_hint or "desconocido", d.text, d.start_char, d.end_char)
                    for d in dialogue_result.value.dialogues
                ]

            chapter_incoherences = checker.analyze_chapter(
                chapter_text=chapter.content,
                entity_names=[character_name],
                dialogues=dialogues,
                chapter_id=chapter.chapter_number,
            )
            all_incoherences.extend(chapter_incoherences)

            # Evolución emocional
            if chapter_states:
                dominant_emotion = max(
                    set(s.emotion_keyword for s in chapter_states),
                    key=lambda x: sum(1 for s in chapter_states if s.emotion_keyword == x)
                )
                evolution.append({
                    "chapter": chapter.chapter_number,
                    "dominant_emotion": dominant_emotion,
                    "emotion_count": len(chapter_states),
                    "has_incoherences": len(chapter_incoherences) > 0,
                })

        return ApiResponse(
            success=True,
            data={
                "character_name": character_name,
                "emotional_states": [
                    {
                        "emotion": s.emotion_keyword,
                        "intensity": s.intensity.value if hasattr(s, 'intensity') else "medium",
                        "chapter": s.chapter_id,
                        "position": s.position,
                        "context": s.context_text[:100] if hasattr(s, 'context_text') else "",
                    }
                    for s in all_states
                ],
                "evolution": evolution,
                "incoherences": [inc.to_dict() for inc in all_incoherences],
                "stats": {
                    "total_states": len(all_states),
                    "total_incoherences": len(all_incoherences),
                    "chapters_with_presence": len(evolution),
                }
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis emocional no disponible"
        )
    except Exception as e:
        logger.error(f"Error getting emotional profile: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Vital Status Analysis Endpoints (Deceased Character Detection)
# ============================================================================

@app.get("/api/projects/{project_id}/vital-status", response_model=ApiResponse)
async def get_vital_status_analysis(project_id: int):
    """
    Obtiene el análisis de estado vital de personajes.

    Detecta:
    - Eventos de muerte de personajes
    - Reapariciones de personajes fallecidos
    - Inconsistencias narrativas (muerto que actúa)

    Returns:
        Reporte con eventos de muerte y posibles inconsistencias
    """
    try:
        from narrative_assistant.analysis.vital_status import (
            VitalStatusAnalyzer,
            analyze_vital_status,
        )

        # Obtener capítulos
        chapters = chapter_repository.get_by_project(project_id)
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "death_events": [],
                    "post_mortem_appearances": [],
                    "inconsistencies_count": 0,
                    "entities_status": {},
                }
            )

        # Obtener entidades (personajes, animales, criaturas)
        entities_result = entity_repository.get_by_project(project_id)
        if entities_result.is_failure:
            return ApiResponse(success=False, error=str(entities_result.error))

        entities = [
            e.to_dict() for e in entities_result.value
            if e.entity_type.value in ["character", "animal", "creature"]
        ]

        # Preparar datos de capítulos
        chapters_data = [
            {
                "number": ch.chapter_number,
                "content": ch.content,
                "start_char": ch.start_char,
            }
            for ch in chapters
        ]

        # Analizar
        result = analyze_vital_status(
            project_id=project_id,
            chapters=chapters_data,
            entities=entities,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        report = result.value

        return ApiResponse(
            success=True,
            data=report.to_dict()
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis de estado vital no disponible"
        )
    except Exception as e:
        logger.error(f"Error in vital status analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/vital-status/generate-alerts", response_model=ApiResponse)
async def generate_vital_status_alerts(project_id: int):
    """
    Genera alertas a partir del análisis de estado vital.

    Crea alertas para cada reaparición de personaje fallecido
    que no sea una referencia válida (flashback, recuerdo, etc.).
    """
    try:
        from narrative_assistant.analysis.vital_status import analyze_vital_status
        from narrative_assistant.alerts import get_alert_engine

        # Obtener capítulos
        chapters = chapter_repository.get_by_project(project_id)
        if not chapters:
            return ApiResponse(
                success=True,
                data={"alerts_created": 0, "message": "No hay capítulos para analizar"}
            )

        # Obtener entidades
        entities_result = entity_repository.get_by_project(project_id)
        if entities_result.is_failure:
            return ApiResponse(success=False, error=str(entities_result.error))

        entities = [
            e.to_dict() for e in entities_result.value
            if e.entity_type.value in ["character", "animal", "creature"]
        ]

        # Preparar datos de capítulos
        chapters_data = [
            {
                "number": ch.chapter_number,
                "content": ch.content,
                "start_char": ch.start_char,
            }
            for ch in chapters
        ]

        # Analizar
        result = analyze_vital_status(
            project_id=project_id,
            chapters=chapters_data,
            entities=entities,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        report = result.value

        # Generar alertas para inconsistencias
        engine = get_alert_engine()
        alerts_created = 0

        for appearance in report.inconsistencies:
            # Buscar el evento de muerte correspondiente
            death_event = next(
                (e for e in report.death_events if e.entity_id == appearance.entity_id),
                None
            )

            alert_result = engine.create_from_deceased_reappearance(
                project_id=project_id,
                entity_id=appearance.entity_id,
                entity_name=appearance.entity_name,
                death_chapter=appearance.death_chapter,
                appearance_chapter=appearance.appearance_chapter,
                appearance_start_char=appearance.appearance_start_char,
                appearance_end_char=appearance.appearance_end_char,
                appearance_excerpt=appearance.appearance_excerpt,
                appearance_type=appearance.appearance_type,
                death_excerpt=death_event.excerpt if death_event else "",
                confidence=appearance.confidence,
            )

            if alert_result.is_success:
                alerts_created += 1

        return ApiResponse(
            success=True,
            data={
                "alerts_created": alerts_created,
                "death_events_found": len(report.death_events),
                "inconsistencies_found": len(report.inconsistencies),
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis de estado vital no disponible"
        )
    except Exception as e:
        logger.error(f"Error generating vital status alerts: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Character Location Tracking
# ============================================================================

@app.get("/api/projects/{project_id}/character-locations", response_model=ApiResponse)
async def get_character_locations(project_id: int):
    """
    Obtiene el análisis de ubicaciones de personajes.

    Detecta:
    - Movimientos de personajes entre ubicaciones
    - Inconsistencias (personaje en dos lugares a la vez)
    - Última ubicación conocida de cada personaje

    Returns:
        Reporte con eventos de ubicación e inconsistencias
    """
    try:
        from narrative_assistant.analysis.character_location import (
            analyze_character_locations,
        )

        # Obtener capítulos
        chapters = chapter_repository.get_by_project(project_id)
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "location_events": [],
                    "inconsistencies": [],
                    "inconsistencies_count": 0,
                    "current_locations": {},
                    "characters_tracked": 0,
                    "locations_found": 0,
                }
            )

        # Obtener entidades (personajes y ubicaciones)
        entities_result = entity_repository.get_by_project(project_id)
        if entities_result.is_failure:
            return ApiResponse(success=False, error=str(entities_result.error))

        entities = [
            {
                "id": e.id,
                "name": e.canonical_name,
                "entity_type": "PER" if e.entity_type.value in ["character", "animal", "creature"] else
                              "LOC" if e.entity_type.value == "location" else
                              e.entity_type.value,
            }
            for e in entities_result.value
        ]

        # Preparar datos de capítulos
        chapters_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": ch.content,
            }
            for ch in chapters
        ]

        # Analizar
        result = analyze_character_locations(
            project_id=project_id,
            chapters=chapters_data,
            entities=entities,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(success=True, data=result.value.to_dict())

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis de ubicaciones no disponible"
        )
    except Exception as e:
        logger.error(f"Error in character location analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Chapter Progress Summary
# ============================================================================

@app.get("/api/projects/{project_id}/chapter-progress", response_model=ApiResponse)
async def get_chapter_progress(
    project_id: int,
    mode: str = "basic",  # basic, standard, deep
    llm_model: str = "llama3.2",
):
    """
    Obtiene el resumen de avance narrativo por capítulo.

    Incluye:
    - Personajes presentes y sus interacciones por capítulo
    - Eventos significativos detectados (patrones + LLM)
    - Arcos de personajes (trayectoria narrativa)
    - Chekhov's Guns (objetos introducidos sin payoff)
    - Tramas abandonadas (con análisis LLM)

    Modos:
    - basic: Solo patrones, sin LLM (rápido)
    - standard: Análisis LLM con llama3.2
    - deep: Análisis multi-modelo (más preciso, más lento)

    Args:
        project_id: ID del proyecto
        mode: Modo de análisis (basic/standard/deep)
        llm_model: Modelo LLM a usar (llama3.2, qwen2.5, mistral)

    Returns:
        ChapterProgressReport con resúmenes de todos los capítulos
    """
    try:
        from narrative_assistant.analysis.chapter_summary import (
            analyze_chapter_progress,
        )

        # Validar modo
        valid_modes = ["basic", "standard", "deep"]
        if mode not in valid_modes:
            return ApiResponse(
                success=False,
                error=f"Modo inválido. Opciones: {', '.join(valid_modes)}"
            )

        # Analizar
        report = analyze_chapter_progress(
            project_id=project_id,
            mode=mode,
            llm_model=llm_model,
        )

        return ApiResponse(success=True, data=report.to_dict())

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de resumen de capítulos no disponible"
        )
    except Exception as e:
        logger.error(f"Error in chapter progress analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Document Export (DOCX/PDF)
# ============================================================================

@app.get("/api/projects/{project_id}/export/document")
async def export_document(
    project_id: int,
    format: str = "docx",
    include_characters: bool = True,
    include_alerts: bool = True,
    include_timeline: bool = True,
    include_relationships: bool = True,
    include_style_guide: bool = True,
    only_main_characters: bool = True,
    only_open_alerts: bool = True,
):
    """
    Exporta el proyecto completo a DOCX o PDF.

    Genera un documento profesional con:
    - Portada con titulo del proyecto
    - Indice automatico
    - Fichas de personajes
    - Alertas/errores encontrados
    - Timeline narrativo
    - Grafo de relaciones
    - Guia de estilo

    Args:
        project_id: ID del proyecto
        format: Formato de exportacion ('docx' o 'pdf')
        include_characters: Incluir fichas de personajes
        include_alerts: Incluir alertas/errores
        include_timeline: Incluir linea temporal
        include_relationships: Incluir relaciones
        include_style_guide: Incluir guia de estilo
        only_main_characters: Solo personajes principales
        only_open_alerts: Solo alertas abiertas

    Returns:
        Archivo DOCX o PDF para descarga
    """
    from fastapi.responses import Response

    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Validar formato
        format = format.lower()
        if format not in ("docx", "pdf"):
            return ApiResponse(success=False, error="Formato invalido. Use 'docx' o 'pdf'")

        # Importar exportador
        try:
            from narrative_assistant.exporters.document_exporter import (
                DocumentExporter,
                ExportOptions,
                collect_export_data,
            )
        except ImportError as e:
            logger.error(f"Document exporter not available: {e}")
            return ApiResponse(
                success=False,
                error="Modulo de exportacion de documentos no disponible"
            )

        # Configurar opciones
        options = ExportOptions(
            include_cover=True,
            include_toc=True,
            include_character_sheets=include_characters,
            include_alerts=include_alerts,
            include_timeline=include_timeline,
            include_relationships=include_relationships,
            include_style_guide=include_style_guide,
            include_statistics=True,
            only_main_characters=only_main_characters,
            only_open_alerts=only_open_alerts,
        )

        # Recopilar datos del proyecto
        data_result = collect_export_data(
            project_id=project_id,
            project_manager=project_manager,
            entity_repository=entity_repository,
            alert_repository=alert_repository,
            chapter_repository=chapter_repository,
            options=options,
        )

        if data_result.is_failure:
            return ApiResponse(success=False, error=str(data_result.error))

        export_data = data_result.value

        # Crear exportador
        exporter = DocumentExporter()

        # Exportar segun formato
        if format == "docx":
            result = exporter.export_to_docx(export_data, options)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extension = "docx"
        else:
            result = exporter.export_to_pdf(export_data, options)
            content_type = "application/pdf"
            extension = "pdf"

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Generar nombre de archivo
        safe_name = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in export_data.project_name
        ).strip().replace(' ', '_').lower()

        filename = f"informe_{safe_name}.{extension}"

        # Devolver archivo para descarga
        return Response(
            content=result.value,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Error exporting document for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


def _estimate_export_pages(data) -> int:
    """Estima el numero de paginas del documento exportado."""
    pages = 2  # Portada + indice

    # Estadisticas: 1 pagina
    pages += 1

    # Personajes: ~1 pagina por cada 3 personajes
    if data.characters:
        pages += max(1, len(data.characters) // 3)

    # Alertas: ~1 pagina por cada 10 alertas
    if data.alerts:
        pages += max(1, len(data.alerts) // 10)

    # Timeline: ~1 pagina por cada 20 eventos
    if data.timeline_events:
        pages += max(1, len(data.timeline_events) // 20)

    # Relaciones: 1-2 paginas
    if data.relationships:
        pages += max(1, len(data.relationships) // 15)

    # Style guide: 2-3 paginas
    if data.style_guide:
        pages += 2

    return pages


@app.get("/api/projects/{project_id}/export/document/preview", response_model=ApiResponse)
async def preview_document_export(
    project_id: int,
    include_characters: bool = True,
    include_alerts: bool = True,
    include_timeline: bool = True,
    include_relationships: bool = True,
    include_style_guide: bool = True,
    only_main_characters: bool = True,
    only_open_alerts: bool = True,
):
    """
    Previsualiza los datos que se incluiran en la exportacion.

    Util para mostrar al usuario que se va a exportar antes de generar el documento.

    Args:
        project_id: ID del proyecto
        include_characters: Incluir fichas de personajes
        include_alerts: Incluir alertas/errores
        include_timeline: Incluir linea temporal
        include_relationships: Incluir relaciones
        include_style_guide: Incluir guia de estilo
        only_main_characters: Solo personajes principales
        only_open_alerts: Solo alertas abiertas

    Returns:
        ApiResponse con preview de los datos a exportar
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        try:
            from narrative_assistant.exporters.document_exporter import (
                ExportOptions,
                collect_export_data,
            )
        except ImportError as e:
            return ApiResponse(success=False, error="Modulo de exportacion no disponible")

        options = ExportOptions(
            include_cover=True,
            include_toc=True,
            include_character_sheets=include_characters,
            include_alerts=include_alerts,
            include_timeline=include_timeline,
            include_relationships=include_relationships,
            include_style_guide=include_style_guide,
            include_statistics=True,
            only_main_characters=only_main_characters,
            only_open_alerts=only_open_alerts,
        )

        data_result = collect_export_data(
            project_id=project_id,
            project_manager=project_manager,
            entity_repository=entity_repository,
            alert_repository=alert_repository,
            chapter_repository=chapter_repository,
            options=options,
        )

        if data_result.is_failure:
            return ApiResponse(success=False, error=str(data_result.error))

        export_data = data_result.value

        return ApiResponse(
            success=True,
            data={
                "project_name": export_data.project_name,
                "description": export_data.description,
                "sections": {
                    "statistics": {
                        "included": True,
                        "word_count": export_data.word_count,
                        "chapter_count": export_data.chapter_count,
                        "entity_count": export_data.entity_count,
                        "alert_count": export_data.alert_count,
                    },
                    "characters": {
                        "included": include_characters,
                        "count": len(export_data.characters),
                        "names": [c.get("canonical_name", "") for c in export_data.characters[:10]],
                    },
                    "alerts": {
                        "included": include_alerts,
                        "count": len(export_data.alerts),
                        "by_severity": {
                            "critical": len([a for a in export_data.alerts if a.get("severity") == "critical"]),
                            "error": len([a for a in export_data.alerts if a.get("severity") == "error"]),
                            "warning": len([a for a in export_data.alerts if a.get("severity") == "warning"]),
                            "info": len([a for a in export_data.alerts if a.get("severity") == "info"]),
                        }
                    },
                    "timeline": {
                        "included": include_timeline,
                        "event_count": len(export_data.timeline_events),
                    },
                    "relationships": {
                        "included": include_relationships,
                        "count": len(export_data.relationships),
                    },
                    "style_guide": {
                        "included": include_style_guide,
                        "available": export_data.style_guide is not None,
                    }
                },
                "estimated_pages": _estimate_export_pages(export_data),
            }
        )

    except Exception as e:
        logger.error(f"Error previewing document export: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/export/corrected")
async def export_corrected_document(
    project_id: int,
    min_confidence: float = 0.5,
    categories: Optional[str] = None,
    as_track_changes: bool = True,
):
    """
    Exporta el documento original con correcciones como Track Changes.

    A diferencia de /export/document que genera un informe, este endpoint
    devuelve el documento original con las correcciones aplicadas como
    revisiones de Word que el autor puede aceptar/rechazar.

    Args:
        project_id: ID del proyecto
        min_confidence: Confianza mínima para incluir correcciones (0.0-1.0)
        categories: Categorías a incluir (separadas por coma), None = todas
        as_track_changes: Si True, aplica como Track Changes; si False, aplica directamente

    Returns:
        Archivo DOCX con correcciones aplicadas
    """
    from fastapi.responses import Response

    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Obtener proyecto
        result = project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=f"Proyecto {project_id} no encontrado")
        project = result.value

        # Verificar que es un documento Word
        if not project.source_path:
            return ApiResponse(
                success=False,
                error="El proyecto no tiene documento fuente asociado"
            )

        source_path = Path(project.source_path)
        if not source_path.exists():
            return ApiResponse(
                success=False,
                error=f"El documento fuente no existe: {source_path}"
            )

        if source_path.suffix.lower() != ".docx":
            return ApiResponse(
                success=False,
                error="Solo se admiten archivos .docx para exportación con Track Changes"
            )

        # Importar exportador
        try:
            from narrative_assistant.exporters.corrected_document_exporter import (
                CorrectedDocumentExporter,
                TrackChangeOptions,
            )
            from narrative_assistant.corrections.base import CorrectionIssue
        except ImportError as e:
            logger.error(f"Corrected document exporter not available: {e}")
            return ApiResponse(
                success=False,
                error="Módulo de exportación de correcciones no disponible"
            )

        # Obtener correcciones del proyecto
        corrections = []

        # Buscar correcciones almacenadas en alertas
        if alert_repository:
            alerts = alert_repository.get_by_project(project_id)
            correction_categories = {
                "typography", "repetition", "agreement", "terminology",
                "regional", "clarity", "grammar"
            }

            for alert in alerts:
                # Solo incluir alertas de corrección con sugerencia
                if alert.category.value.lower() in correction_categories and alert.suggestion:
                    corrections.append(CorrectionIssue(
                        category=alert.category.value.lower(),
                        issue_type=alert.alert_type or "unknown",
                        start_char=alert.start_char or 0,
                        end_char=alert.end_char or 0,
                        text=alert.excerpt or "",
                        explanation=alert.description,
                        suggestion=alert.suggestion,
                        confidence=alert.confidence,
                        context=alert.excerpt or "",
                        chapter_index=alert.chapter,
                        rule_id=None,
                        extra_data={},
                    ))

        if not corrections:
            return ApiResponse(
                success=False,
                error="No hay correcciones para aplicar. Ejecute primero el análisis de correcciones."
            )

        # Parsear categorías
        category_list = None
        if categories:
            category_list = [c.strip().lower() for c in categories.split(",")]

        # Configurar opciones
        options = TrackChangeOptions(
            author="Narrative Assistant",
            include_comments=True,
            min_confidence=min_confidence,
            categories=category_list,
            as_track_changes=as_track_changes,
        )

        # Exportar
        exporter = CorrectedDocumentExporter()
        result = exporter.export(source_path, corrections, options)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Generar nombre de archivo
        safe_name = source_path.stem
        filename = f"{safe_name}_corregido.docx"

        # Devolver archivo
        return Response(
            content=result.value,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Error exporting corrected document for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/export/review-report")
async def export_review_report(
    project_id: int,
    format: str = "docx",
    min_confidence: float = 0.0,
    include_context: bool = True,
    include_suggestions: bool = True,
    max_issues_per_category: int = 50,
):
    """
    Exporta un informe de revisión editorial a DOCX o PDF.

    Genera un informe detallado con estadísticas de los problemas
    detectados por los 14 detectores de corrección.

    Incluye:
    - Resumen ejecutivo con totales por categoría
    - Distribución por confianza
    - Desglose por capítulo
    - Listado detallado de observaciones
    - Recomendaciones de estilo

    Args:
        project_id: ID del proyecto
        format: Formato de exportación ('docx' o 'pdf')
        min_confidence: Confianza mínima para incluir (0.0-1.0)
        include_context: Incluir contexto de cada observación
        include_suggestions: Incluir sugerencias de corrección
        max_issues_per_category: Máximo de observaciones por categoría

    Returns:
        Archivo DOCX o PDF para descarga
    """
    from fastapi.responses import Response

    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Validar formato
        format = format.lower()
        if format not in ("docx", "pdf"):
            return ApiResponse(success=False, error="Formato inválido. Use 'docx' o 'pdf'")

        # Obtener proyecto
        result = project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        project = result.value

        # Importar módulos necesarios
        try:
            from narrative_assistant.exporters.review_report_exporter import (
                ReviewReportExporter,
                ReviewReportOptions,
            )
            from narrative_assistant.corrections.base import CorrectionIssue
        except ImportError as e:
            logger.error(f"Review report exporter not available: {e}")
            return ApiResponse(
                success=False,
                error="Módulo de informes de revisión no disponible"
            )

        # Obtener alertas del proyecto que son de tipo correction
        correction_categories = {
            "typography", "repetition", "agreement", "punctuation",
            "terminology", "regional", "clarity", "grammar",
            "anglicisms", "crutch_words", "glossary", "anacoluto",
            "pov", "orthography"
        }

        # Convertir alertas a CorrectionIssue
        issues = []
        if alert_repository:
            alerts = alert_repository.get_by_project(project_id)
            for alert in alerts:
                category = alert.category.value.lower() if hasattr(alert.category, 'value') else str(alert.category).lower()
                if category in correction_categories:
                    issues.append(CorrectionIssue(
                        category=category,
                        issue_type=alert.alert_type or "unknown",
                        start_char=0,
                        end_char=0,
                        text=alert.excerpt or "",
                        explanation=alert.explanation or alert.description or "",
                        suggestion=alert.suggestion,
                        confidence=alert.confidence or 0.5,
                        context=alert.excerpt or "",
                        chapter_index=alert.chapter,
                        rule_id=None,
                    ))

        if not issues:
            return ApiResponse(
                success=False,
                error="No hay observaciones de corrección para generar el informe. Ejecute primero el análisis del documento."
            )

        # Configurar opciones
        options = ReviewReportOptions(
            document_title=project.name,
            min_confidence=min_confidence,
            include_context=include_context,
            include_suggestions=include_suggestions,
            max_issues_per_category=max_issues_per_category,
        )

        # Crear exportador
        exporter = ReviewReportExporter()

        # Exportar según formato
        if format == "docx":
            result = exporter.export_to_docx(issues, options)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extension = "docx"
        else:
            result = exporter.export_to_pdf(issues, options)
            content_type = "application/pdf"
            extension = "pdf"

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Generar nombre de archivo
        safe_name = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in project.name
        ).strip().replace(' ', '_').lower()

        filename = f"informe_revision_{safe_name}.{extension}"

        # Devolver archivo para descarga
        return Response(
            content=result.value,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Error exporting review report for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/export/review-report/preview", response_model=ApiResponse)
async def preview_review_report(project_id: int):
    """
    Previsualiza los datos que se incluirán en el informe de revisión.

    Útil para mostrar al usuario estadísticas antes de generar el documento.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con preview de las estadísticas del informe
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Obtener proyecto
        result = project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        project = result.value

        # Importar módulos
        try:
            from narrative_assistant.exporters.review_report_exporter import (
                ReviewReportExporter,
                ReviewReportOptions,
            )
            from narrative_assistant.corrections.base import CorrectionIssue
        except ImportError as e:
            return ApiResponse(success=False, error="Módulo de informes no disponible")

        # Obtener alertas de corrección
        correction_categories = {
            "typography", "repetition", "agreement", "punctuation",
            "terminology", "regional", "clarity", "grammar",
            "anglicisms", "crutch_words", "glossary", "anacoluto",
            "pov", "orthography"
        }

        issues = []
        if alert_repository:
            alerts = alert_repository.get_by_project(project_id)
            for alert in alerts:
                category = alert.category.value.lower() if hasattr(alert.category, 'value') else str(alert.category).lower()
                if category in correction_categories:
                    issues.append(CorrectionIssue(
                        category=category,
                        issue_type=alert.alert_type or "unknown",
                        start_char=0,
                        end_char=0,
                        text=alert.excerpt or "",
                        explanation=alert.explanation or alert.description or "",
                        suggestion=alert.suggestion,
                        confidence=alert.confidence or 0.5,
                        context=alert.excerpt or "",
                        chapter_index=alert.chapter,
                    ))

        if not issues:
            return ApiResponse(
                success=True,
                data={
                    "document_title": project.name,
                    "total_issues": 0,
                    "categories": [],
                    "by_confidence": {"high": 0, "medium": 0, "low": 0},
                    "by_chapter": {},
                    "can_export": False,
                    "message": "No hay observaciones de corrección. Ejecute primero el análisis."
                }
            )

        # Preparar datos del informe
        exporter = ReviewReportExporter()
        options = ReviewReportOptions(document_title=project.name)
        data = exporter.prepare_report_data(issues, options)

        # Convertir a diccionario serializable
        categories_preview = [
            {
                "category": cat.category,
                "display_name": cat.display_name,
                "total": cat.total,
                "high_confidence": cat.high_confidence,
                "medium_confidence": cat.medium_confidence,
                "low_confidence": cat.low_confidence,
                "types": dict(cat.by_type),
            }
            for cat in data.categories
        ]

        return ApiResponse(
            success=True,
            data={
                "document_title": data.document_title,
                "total_issues": data.total_issues,
                "categories": categories_preview,
                "by_confidence": data.total_by_confidence,
                "by_chapter": data.by_chapter,
                "top_issues": [
                    {"category": cat, "type": typ, "count": cnt}
                    for cat, typ, cnt in data.top_issues_by_type
                ],
                "can_export": data.total_issues > 0,
            }
        )

    except Exception as e:
        logger.error(f"Error previewing review report for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Licensing Endpoints
# ============================================================================

# Lazy import licensing modules
license_verifier = None

def get_license_verifier():
    """Obtiene el verificador de licencias de forma lazy."""
    global license_verifier
    if license_verifier is None:
        try:
            from narrative_assistant.licensing.verification import LicenseVerifier
            license_verifier = LicenseVerifier()
        except ImportError:
            pass
    return license_verifier


class LicenseActivationRequest(BaseModel):
    """Request para activar una licencia."""
    license_key: str = Field(..., description="Clave de licencia")


class DeviceDeactivationRequest(BaseModel):
    """Request para desactivar un dispositivo."""
    device_fingerprint: str = Field(..., description="Fingerprint del dispositivo a desactivar")


@app.get("/api/license/status", response_model=ApiResponse)
async def get_license_status():
    """
    Obtiene el estado actual de la licencia.

    Returns:
        ApiResponse con informacion de la licencia activa
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(
                success=True,
                data={
                    "status": "no_license",
                    "tier": None,
                    "modules": [],
                    "devices_used": 0,
                    "devices_max": 0,
                    "manuscripts_used": 0,
                    "manuscripts_max": 0,
                    "expires_at": None,
                    "is_trial": False,
                    "offline_days_remaining": None,
                }
            )

        result = verifier.get_current_license()

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "status": "no_license",
                    "error": str(result.error),
                    "tier": None,
                    "modules": [],
                }
            )

        license_info = result.value
        return ApiResponse(
            success=True,
            data={
                "status": "active" if license_info.is_active else "expired",
                "tier": license_info.tier.value if license_info.tier else None,
                "modules": [m.value for m in license_info.modules] if license_info.modules else [],
                "devices_used": license_info.devices_used,
                "devices_max": license_info.max_devices,
                "manuscripts_used": license_info.manuscripts_used_this_period,
                "manuscripts_max": license_info.manuscripts_per_month,
                "expires_at": license_info.expires_at.isoformat() if license_info.expires_at else None,
                "is_trial": license_info.is_trial,
                "offline_days_remaining": license_info.offline_grace_days_remaining,
            }
        )

    except Exception as e:
        logger.error(f"Error getting license status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/license/activate", response_model=ApiResponse)
async def activate_license(request: LicenseActivationRequest):
    """
    Activa una licencia con la clave proporcionada.

    Args:
        request: Clave de licencia

    Returns:
        ApiResponse con resultado de la activacion
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.activate_license(request.license_key)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        license_info = result.value
        return ApiResponse(
            success=True,
            data={
                "message": "Licencia activada correctamente",
                "tier": license_info.tier.value if license_info.tier else None,
                "modules": [m.value for m in license_info.modules] if license_info.modules else [],
            }
        )

    except Exception as e:
        logger.error(f"Error activating license: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/license/verify", response_model=ApiResponse)
async def verify_license():
    """
    Verifica la licencia actual (online si es posible).

    Returns:
        ApiResponse con resultado de la verificacion
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.verify_license()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "valid": result.value.is_valid,
                "message": result.value.message,
                "verified_online": result.value.verified_online,
            }
        )

    except Exception as e:
        logger.error(f"Error verifying license: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/license/devices", response_model=ApiResponse)
async def get_license_devices():
    """
    Obtiene la lista de dispositivos registrados en la licencia.

    Returns:
        ApiResponse con lista de dispositivos
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.get_devices()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        devices = result.value
        return ApiResponse(
            success=True,
            data={
                "devices": [
                    {
                        "fingerprint": d.fingerprint[:8] + "...",  # Parcial por privacidad
                        "name": d.name,
                        "status": d.status.value,
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                        "is_current": d.is_current,
                    }
                    for d in devices
                ],
                "max_devices": verifier.max_devices,
            }
        )

    except Exception as e:
        logger.error(f"Error getting devices: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/license/devices/deactivate", response_model=ApiResponse)
async def deactivate_device(request: DeviceDeactivationRequest):
    """
    Desactiva un dispositivo de la licencia.

    Args:
        request: Fingerprint del dispositivo a desactivar

    Returns:
        ApiResponse con resultado de la desactivacion
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.deactivate_device(request.device_fingerprint)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "message": "Dispositivo desactivado",
                "cooldown_hours": 48,
            }
        )

    except Exception as e:
        logger.error(f"Error deactivating device: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/license/usage", response_model=ApiResponse)
async def get_license_usage():
    """
    Obtiene el uso de la licencia en el periodo actual.

    Returns:
        ApiResponse con estadisticas de uso
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.get_usage()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        usage = result.value
        return ApiResponse(
            success=True,
            data={
                "period_start": usage.period_start.isoformat(),
                "period_end": usage.period_end.isoformat(),
                "manuscripts_used": usage.manuscripts_used,
                "manuscripts_limit": usage.manuscripts_limit,
                "manuscripts_remaining": max(0, usage.manuscripts_limit - usage.manuscripts_used),
                "unlimited": usage.manuscripts_limit == -1,
            }
        )

    except Exception as e:
        logger.error(f"Error getting usage: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/license/record-manuscript", response_model=ApiResponse)
async def record_manuscript_usage(project_id: int = Body(..., embed=True)):
    """
    Registra el uso de un manuscrito contra la cuota.

    Args:
        project_id: ID del proyecto/manuscrito

    Returns:
        ApiResponse con resultado del registro
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            # Sin verificador, permitir uso (desarrollo)
            return ApiResponse(success=True, data={"allowed": True})

        result = verifier.record_manuscript_usage(project_id)

        if result.is_failure:
            error = result.error
            return ApiResponse(
                success=False,
                error=str(error),
                data={"allowed": False, "reason": error.__class__.__name__}
            )

        return ApiResponse(
            success=True,
            data={
                "allowed": True,
                "manuscripts_remaining": result.value.manuscripts_remaining,
            }
        )

    except Exception as e:
        logger.error(f"Error recording manuscript usage: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/license/check-module/{module_name}", response_model=ApiResponse)
async def check_module_access(module_name: str):
    """
    Verifica si el usuario tiene acceso a un modulo especifico.

    Args:
        module_name: Nombre del modulo (CORE, NARRATIVA, VOZ_ESTILO, AVANZADO)

    Returns:
        ApiResponse indicando si tiene acceso
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            # Sin verificador, permitir todo (desarrollo)
            return ApiResponse(success=True, data={"has_access": True})

        result = verifier.check_module_access(module_name)

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "has_access": False,
                    "reason": str(result.error),
                }
            )

        return ApiResponse(
            success=True,
            data={
                "has_access": True,
                "module": module_name,
            }
        )

    except Exception as e:
        logger.error(f"Error checking module access: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Editorial Rules Endpoints
# ============================================================================

class EditorialRulesRequest(BaseModel):
    """Request para guardar reglas editoriales."""
    rules_text: str = Field(..., description="Texto libre con las reglas editoriales")
    enabled: bool = Field(default=True, description="Si las reglas estan habilitadas")


@app.get("/api/projects/{project_id}/editorial-rules", response_model=ApiResponse)
async def get_editorial_rules(project_id: int):
    """
    Obtiene las reglas editoriales de un proyecto.

    Las reglas son texto libre que el corrector define para el manuscrito.
    Ejemplos:
    - "nuestros corazones" -> "nuestro corazon" (organos unicos en singular)
    - "quizas" -> "quiza" (preferencia editorial)
    - edades con numeros, anos con letra

    Returns:
        ApiResponse con las reglas del proyecto
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar que el proyecto existe
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener reglas de la base de datos
        db = project_manager.db
        with db.connection() as conn:
            cursor = conn.execute(
                "SELECT rules_text, enabled, created_at, updated_at FROM editorial_rules WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()

            if row:
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "rules_text": row["rules_text"],
                        "enabled": bool(row["enabled"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )
            else:
                # No hay reglas definidas - devolver defaults vacios
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "rules_text": "",
                        "enabled": True,
                        "created_at": None,
                        "updated_at": None,
                    }
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting editorial rules: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/editorial-rules", response_model=ApiResponse)
async def save_editorial_rules(project_id: int, request: EditorialRulesRequest):
    """
    Guarda las reglas editoriales de un proyecto.

    Las reglas se interpretan durante el analisis de estilo para detectar
    problemas especificos de la editorial o corrector.

    Args:
        project_id: ID del proyecto
        request: Texto de reglas y estado de habilitacion

    Returns:
        ApiResponse confirmando el guardado
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar que el proyecto existe
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Guardar o actualizar reglas
        db = project_manager.db
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO editorial_rules (project_id, rules_text, enabled, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(project_id) DO UPDATE SET
                    rules_text = excluded.rules_text,
                    enabled = excluded.enabled,
                    updated_at = datetime('now')
                """,
                (project_id, request.rules_text, int(request.enabled))
            )
            conn.commit()

        logger.info(f"Editorial rules saved for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "rules_text": request.rules_text,
                "enabled": request.enabled,
                "message": "Reglas editoriales guardadas correctamente"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving editorial rules: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/editorial-rules/check", response_model=ApiResponse)
async def check_editorial_rules(project_id: int, text: str = Body(..., embed=True)):
    """
    Aplica las reglas editoriales a un texto y devuelve los problemas encontrados.

    Este endpoint permite verificar un fragmento de texto contra las reglas
    definidas para el proyecto.

    Args:
        project_id: ID del proyecto
        text: Texto a verificar

    Returns:
        ApiResponse con los problemas encontrados
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar proyecto
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener reglas del proyecto
        db = project_manager.db
        with db.connection() as conn:
            cursor = conn.execute(
                "SELECT rules_text, enabled FROM editorial_rules WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()

        # Aplicar verificador de reglas editoriales
        from narrative_assistant.nlp.style.editorial_rules import check_with_user_rules

        # Obtener reglas del usuario (si existen)
        user_rules_text = ""
        if row and row["enabled"] and row["rules_text"]:
            user_rules_text = row["rules_text"]

        # Verificar texto con reglas predefinidas + reglas del usuario
        report = check_with_user_rules(
            text=text,
            user_rules_text=user_rules_text,
            include_predefined=True  # Siempre incluir reglas base
        )

        return ApiResponse(
            success=True,
            data={
                "issues": report.to_dict()["issues"],
                "rules_applied": report.rules_applied,
                "issue_count": report.issue_count,
                "has_user_rules": bool(user_rules_text),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking editorial rules: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Mantenimiento
# ============================================================================

@app.post("/api/maintenance/clear-cache", response_model=ApiResponse)
async def clear_cache():
    """
    Limpia archivos temporales y caché del sistema.

    Elimina:
    - Archivos temporales de análisis
    - Caché de modelos NLP (si existe)
    - Archivos huérfanos

    Returns:
        ApiResponse con estadísticas de limpieza
    """
    import shutil
    import tempfile

    cleared_files = 0
    cleared_bytes = 0
    errors = []

    try:
        # 1. Limpiar directorio temporal de análisis
        temp_analysis_dir = Path(tempfile.gettempdir()) / "narrative_assistant"
        if temp_analysis_dir.exists():
            for item in temp_analysis_dir.iterdir():
                try:
                    if item.is_file():
                        size = item.stat().st_size
                        item.unlink()
                        cleared_files += 1
                        cleared_bytes += size
                    elif item.is_dir():
                        size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                        shutil.rmtree(item)
                        cleared_files += 1
                        cleared_bytes += size
                except Exception as e:
                    errors.append(f"Error limpiando {item.name}: {str(e)}")

        # 2. Limpiar caché de HuggingFace (solo archivos temporales, no modelos)
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub" / ".locks"
        if hf_cache.exists():
            for lock_file in hf_cache.glob("*.lock"):
                try:
                    size = lock_file.stat().st_size
                    lock_file.unlink()
                    cleared_files += 1
                    cleared_bytes += size
                except Exception:
                    pass  # Los locks pueden estar en uso

        # 3. Limpiar archivos __pycache__ del proyecto (opcional, solo en desarrollo)
        # No lo hacemos en producción

        # Formatear bytes
        if cleared_bytes < 1024:
            size_str = f"{cleared_bytes} bytes"
        elif cleared_bytes < 1024 * 1024:
            size_str = f"{cleared_bytes / 1024:.1f} KB"
        else:
            size_str = f"{cleared_bytes / (1024 * 1024):.1f} MB"

        return ApiResponse(
            success=True,
            data={
                "files_cleared": cleared_files,
                "bytes_cleared": cleared_bytes,
                "size_cleared": size_str,
                "errors": errors if errors else None,
            },
            message=f"Se eliminaron {cleared_files} archivo(s) ({size_str})"
        )

    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/maintenance/data-location", response_model=ApiResponse)
async def get_data_location():
    """
    Obtiene la ubicación actual de almacenamiento de datos.

    Returns:
        ApiResponse con la ruta del directorio de datos
    """
    try:
        if get_config:
            config = get_config()
            data_dir = config.data_dir
        else:
            # Fallback si no hay config
            data_dir = Path.home() / ".narrative_assistant"

        return ApiResponse(
            success=True,
            data={
                "path": str(data_dir),
                "exists": data_dir.exists(),
                "writable": data_dir.exists() and data_dir.is_dir(),
            }
        )
    except Exception as e:
        logger.error(f"Error getting data location: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


class ChangeDataLocationRequest(BaseModel):
    """Request para cambiar la ubicación de datos"""
    new_path: str = Field(..., min_length=1)
    migrate_data: bool = Field(default=False, description="Si se deben migrar los datos existentes")


@app.post("/api/maintenance/data-location", response_model=ApiResponse)
async def change_data_location(request: ChangeDataLocationRequest):
    """
    Cambia la ubicación de almacenamiento de datos.

    Args:
        request: Nueva ruta y opciones de migración

    Returns:
        ApiResponse con el resultado de la operación
    """
    import shutil
    import os

    try:
        new_path = Path(request.new_path).expanduser().resolve()

        # Validar que la ruta sea válida
        if not new_path.parent.exists():
            return ApiResponse(
                success=False,
                error=f"El directorio padre no existe: {new_path.parent}"
            )

        # Obtener la ubicación actual
        if get_config:
            config = get_config()
            old_path = config.data_dir
        else:
            old_path = Path.home() / ".narrative_assistant"

        # No hacer nada si es la misma ruta
        if new_path.resolve() == old_path.resolve():
            return ApiResponse(
                success=True,
                message="La ubicación ya es la actual",
                data={"path": str(new_path)}
            )

        # Crear el nuevo directorio si no existe
        new_path.mkdir(parents=True, exist_ok=True)

        # Verificar que podemos escribir en el nuevo directorio
        test_file = new_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            return ApiResponse(
                success=False,
                error=f"No se puede escribir en el directorio: {e}"
            )

        migrated_items = []

        # Migrar datos si se solicita
        if request.migrate_data and old_path.exists():
            items_to_migrate = ["projects.db", "projects", "cache"]

            for item in items_to_migrate:
                old_item = old_path / item
                new_item = new_path / item

                if old_item.exists():
                    try:
                        if old_item.is_file():
                            shutil.copy2(old_item, new_item)
                        else:
                            if new_item.exists():
                                shutil.rmtree(new_item)
                            shutil.copytree(old_item, new_item)
                        migrated_items.append(item)
                    except Exception as e:
                        logger.warning(f"Error migrating {item}: {e}")

        # Guardar la nueva ubicación en un archivo de configuración del usuario
        config_file = Path.home() / ".narrative_assistant_config"
        try:
            config_file.write_text(f"data_dir={new_path}\n")
        except Exception as e:
            logger.warning(f"Could not save config file: {e}")

        # Actualizar variable de entorno para la sesión actual
        os.environ["NA_DATA_DIR"] = str(new_path)

        return ApiResponse(
            success=True,
            message="Ubicación de datos actualizada correctamente",
            data={
                "old_path": str(old_path),
                "new_path": str(new_path),
                "migrated_items": migrated_items,
                "restart_required": True
            }
        )

    except Exception as e:
        logger.error(f"Error changing data location: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Chat / Asistente LLM
# ============================================================================

class ChatRequest(BaseModel):
    """Request para chat con LLM"""
    message: str = Field(..., min_length=1, max_length=10000)
    history: Optional[list] = Field(default=None, description="Historial de mensajes previos")


@app.post("/api/projects/{project_id}/chat", response_model=ApiResponse)
async def chat_with_assistant(project_id: int, request: ChatRequest):
    """
    Chat con el asistente LLM usando el documento como contexto.

    El asistente puede responder preguntas sobre el manuscrito usando RAG
    (Retrieval-Augmented Generation) para incluir fragmentos relevantes
    del documento como contexto.

    Args:
        project_id: ID del proyecto
        request: Mensaje del usuario y historial opcional

    Returns:
        ApiResponse con la respuesta del LLM
    """
    try:
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar que el proyecto existe
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Verificar que Ollama está disponible
        try:
            from narrative_assistant.llm import get_llm_client, is_llm_available

            if not is_llm_available():
                return ApiResponse(
                    success=False,
                    error="LLM no disponible. Asegúrate de que Ollama esté corriendo (ollama serve)"
                )

            llm_client = get_llm_client()
            if not llm_client or not llm_client.is_available:
                return ApiResponse(
                    success=False,
                    error="Cliente LLM no disponible"
                )
        except ImportError as e:
            logger.error(f"LLM module import error: {e}")
            return ApiResponse(
                success=False,
                error="Módulo LLM no disponible"
            )

        # Obtener capítulos del proyecto para contexto
        chapters_content = []
        if chapter_repository:
            chapters = chapter_repository.get_by_project(project_id)
            for ch in chapters:
                if ch.content:
                    chapters_content.append({
                        "title": ch.title or f"Capítulo {ch.chapter_number}",
                        "content": ch.content[:5000]  # Limitar para no sobrecargar contexto
                    })

        # Construir contexto del documento (RAG básico por keywords)
        user_message = request.message.lower()
        relevant_context = []

        # Buscar fragmentos relevantes (keywords simples)
        keywords = [word for word in user_message.split() if len(word) > 3]

        for chapter in chapters_content:
            chapter_lower = chapter["content"].lower()
            relevance_score = sum(1 for kw in keywords if kw in chapter_lower)

            if relevance_score > 0:
                # Extraer fragmento relevante (primeros 1000 chars con keywords)
                relevant_context.append({
                    "source": chapter["title"],
                    "content": chapter["content"][:1500],
                    "score": relevance_score
                })

        # Ordenar por relevancia y tomar los mejores
        relevant_context.sort(key=lambda x: x["score"], reverse=True)
        top_context = relevant_context[:3]  # Máximo 3 fragmentos

        # Construir prompt con contexto
        context_text = ""
        context_sources = []
        if top_context:
            context_text = "\n\n### Contexto del documento:\n"
            for ctx in top_context:
                context_text += f"\n**{ctx['source']}:**\n{ctx['content'][:1000]}...\n"
                context_sources.append(ctx["source"])

        # Construir historial de conversación
        history_text = ""
        if request.history:
            history_text = "\n\n### Conversación previa:\n"
            for msg in request.history[-5:]:  # Últimos 5 mensajes
                role = "Usuario" if msg.get("role") == "user" else "Asistente"
                history_text += f"{role}: {msg.get('content', '')}\n"

        # Prompt del sistema
        system_prompt = f"""Eres un asistente experto en análisis literario y corrección de textos.
Estás ayudando a analizar el manuscrito "{project.name}".

Tu rol es:
- Responder preguntas sobre el contenido del documento
- Ayudar a identificar personajes, lugares y eventos
- Señalar posibles inconsistencias si se te pregunta
- Dar sugerencias de mejora cuando sea apropiado

Responde de forma concisa y profesional. Si no tienes información suficiente
en el contexto proporcionado, indícalo claramente.
{context_text}
{history_text}"""

        # Llamar al LLM
        try:
            response = llm_client.complete(
                prompt=request.message,
                system=system_prompt,
                max_tokens=1000,
                temperature=0.7
            )

            if response and response.strip():
                return ApiResponse(
                    success=True,
                    data={
                        "response": response.strip(),
                        "contextUsed": context_sources,
                        "model": getattr(llm_client, 'model', 'unknown')
                    }
                )
            else:
                return ApiResponse(
                    success=False,
                    error="El LLM no generó una respuesta"
                )

        except Exception as e:
            logger.error(f"Error calling LLM: {e}", exc_info=True)
            return ApiResponse(
                success=False,
                error=f"Error al comunicarse con el LLM: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Correction Configuration Endpoints
# ============================================================================

@app.get("/api/correction-presets", response_model=ApiResponse)
async def get_correction_presets() -> ApiResponse:
    """
    Obtiene los presets de configuración de corrección disponibles.

    Retorna una lista de presets con su nombre, descripción y configuración.
    """
    try:
        from narrative_assistant.corrections.config import (
            CorrectionConfig,
            DocumentField,
            RegisterLevel,
            AudienceType,
        )

        presets = [
            {
                "id": "default",
                "name": "Por defecto",
                "description": "Configuración estándar para documentos generales",
                "config": CorrectionConfig.default().to_dict(),
            },
            {
                "id": "novel",
                "name": "Novela literaria",
                "description": "Optimizado para ficción: diálogos, estilo cuidado, repeticiones estrictas",
                "config": CorrectionConfig.for_novel().to_dict(),
            },
            {
                "id": "technical",
                "name": "Manual técnico",
                "description": "Permite repetición técnica, vocabulario especializado",
                "config": CorrectionConfig.for_technical().to_dict(),
            },
            {
                "id": "legal",
                "name": "Texto jurídico",
                "description": "Muy permisivo con repeticiones, terminología legal permitida",
                "config": CorrectionConfig.for_legal().to_dict(),
            },
            {
                "id": "medical",
                "name": "Texto médico",
                "description": "Terminología médica permitida, registro formal",
                "config": CorrectionConfig.for_medical().to_dict(),
            },
            {
                "id": "journalism",
                "name": "Periodismo",
                "description": "Equilibrado, sugiere alternativas accesibles",
                "config": CorrectionConfig.for_journalism().to_dict(),
            },
            {
                "id": "selfhelp",
                "name": "Autoayuda",
                "description": "Registro coloquial, cercano al lector",
                "config": CorrectionConfig.for_selfhelp().to_dict(),
            },
        ]

        # También incluir opciones de configuración
        options = {
            "document_fields": [
                {"value": f.value, "label": _field_label(f)} for f in DocumentField
            ],
            "register_levels": [
                {"value": r.value, "label": _register_label(r)} for r in RegisterLevel
            ],
            "audience_types": [
                {"value": a.value, "label": _audience_label(a)} for a in AudienceType
            ],
            "regions": [
                {"value": "es_ES", "label": "España"},
                {"value": "es_MX", "label": "México"},
                {"value": "es_AR", "label": "Argentina"},
                {"value": "es_CO", "label": "Colombia"},
                {"value": "es_CL", "label": "Chile"},
                {"value": "es_PE", "label": "Perú"},
            ],
            "quote_styles": [
                {"value": "angular", "label": "Angulares «»"},
                {"value": "curly", "label": "Tipográficas """},
                {"value": "straight", "label": "Rectas \"\""},
            ],
            "dialogue_dashes": [
                {"value": "em", "label": "Raya (—)"},
                {"value": "en", "label": "Semiraya (–)"},
                {"value": "hyphen", "label": "Guion (-)"},
            ],
            "sensitivity_levels": [
                {"value": "low", "label": "Baja"},
                {"value": "medium", "label": "Media"},
                {"value": "high", "label": "Alta"},
            ],
        }

        return ApiResponse(
            success=True,
            data={
                "presets": presets,
                "options": options,
            }
        )

    except Exception as e:
        logger.error(f"Error getting correction presets: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


def _field_label(field) -> str:
    """Etiqueta legible para campo de documento."""
    from narrative_assistant.corrections.config import DocumentField
    labels = {
        DocumentField.GENERAL: "General",
        DocumentField.LITERARY: "Literario (novela, cuento)",
        DocumentField.JOURNALISTIC: "Periodístico",
        DocumentField.ACADEMIC: "Académico (ensayo, tesis)",
        DocumentField.TECHNICAL: "Técnico/Informático",
        DocumentField.LEGAL: "Jurídico",
        DocumentField.MEDICAL: "Médico/Científico",
        DocumentField.BUSINESS: "Empresarial",
        DocumentField.SELFHELP: "Autoayuda",
        DocumentField.CULINARY: "Gastronomía",
    }
    return labels.get(field, field.value)


def _register_label(register) -> str:
    """Etiqueta legible para nivel de registro."""
    from narrative_assistant.corrections.config import RegisterLevel
    labels = {
        RegisterLevel.FORMAL: "Formal/Académico",
        RegisterLevel.NEUTRAL: "Neutro/Estándar",
        RegisterLevel.COLLOQUIAL: "Coloquial/Informal",
        RegisterLevel.VULGAR: "Vulgar (intencional)",
    }
    return labels.get(register, register.value)


def _audience_label(audience) -> str:
    """Etiqueta legible para tipo de audiencia."""
    from narrative_assistant.corrections.config import AudienceType
    labels = {
        AudienceType.GENERAL: "Público general",
        AudienceType.CHILDREN: "Infantil/Juvenil",
        AudienceType.ADULT: "Adultos",
        AudienceType.SPECIALIST: "Especialistas",
        AudienceType.MIXED: "Mixta",
    }
    return labels.get(audience, audience.value)


@app.get("/api/projects/{project_id}/correction-config", response_model=ApiResponse)
async def get_project_correction_config(project_id: str) -> ApiResponse:
    """
    Obtiene la configuración de corrección para un proyecto.

    Si el proyecto no tiene configuración personalizada, retorna la por defecto.
    """
    try:
        result = project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import CorrectionConfig

        # Cargar configuración desde settings del proyecto
        logger.info(f"Loading correction config for project {project_id}: settings has {len(project.settings)} keys")
        config_data = project.settings.get("correction_config")
        has_custom = config_data is not None
        logger.info(f"Has custom config: {has_custom}")

        if config_data:
            config = CorrectionConfig.from_dict(config_data)
        else:
            # Usar preset por defecto
            config = CorrectionConfig.default()

        # Obtener preset seleccionado
        selected_preset = project.settings.get("correction_preset", "default")
        logger.info(f"Loaded correction config with preset: {selected_preset}")

        return ApiResponse(
            success=True,
            data={
                "config": config.to_dict(),
                "hasCustomConfig": has_custom,
                "selectedPreset": selected_preset,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


class CorrectionConfigUpdate(BaseModel):
    """Modelo para actualizar configuración de corrección."""
    config: dict
    selectedPreset: Optional[str] = None


@app.put("/api/projects/{project_id}/correction-config", response_model=ApiResponse)
async def update_project_correction_config(
    project_id: str,
    update: CorrectionConfigUpdate,
) -> ApiResponse:
    """
    Actualiza la configuración de corrección de un proyecto.
    """
    try:
        result = project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import CorrectionConfig

        # Validar la configuración
        try:
            config = CorrectionConfig.from_dict(update.config)
        except Exception as e:
            return ApiResponse(
                success=False,
                error=f"Configuración inválida: {str(e)}"
            )

        # Guardar configuración en settings del proyecto
        project.settings["correction_config"] = config.to_dict()
        project.settings["correction_preset"] = update.selectedPreset
        logger.info(f"Saving correction config for project {project_id}: preset={update.selectedPreset}, settings has {len(project.settings)} keys")
        update_result = project_manager.update(project)
        if update_result.is_failure:
            logger.error(f"Failed to update project {project_id}: {update_result.errors}")
            return ApiResponse(success=False, error="Error al guardar configuración")

        logger.info(f"Successfully updated correction config for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "config": config.to_dict(),
                "message": "Configuración guardada correctamente",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/correction-config/apply-preset", response_model=ApiResponse)
async def apply_correction_preset(
    project_id: str,
    preset_id: str = Query(..., description="ID del preset a aplicar"),
) -> ApiResponse:
    """
    Aplica un preset de configuración a un proyecto.
    """
    try:
        result = project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import CorrectionConfig

        # Obtener el preset
        presets = {
            "default": CorrectionConfig.default,
            "novel": CorrectionConfig.for_novel,
            "technical": CorrectionConfig.for_technical,
            "legal": CorrectionConfig.for_legal,
            "medical": CorrectionConfig.for_medical,
            "journalism": CorrectionConfig.for_journalism,
            "selfhelp": CorrectionConfig.for_selfhelp,
        }

        if preset_id not in presets:
            return ApiResponse(
                success=False,
                error=f"Preset '{preset_id}' no encontrado"
            )

        config = presets[preset_id]()

        # Guardar configuración en settings del proyecto
        project.settings["correction_config"] = config.to_dict()
        project.settings["correction_preset"] = preset_id
        update_result = project_manager.update(project)
        if update_result.is_failure:
            return ApiResponse(success=False, error="Error al guardar configuración")

        logger.info(f"Applied preset '{preset_id}' to project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "config": config.to_dict(),
                "preset": preset_id,
                "message": f"Preset '{preset_id}' aplicado correctamente",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying preset: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/correction-config", response_model=ApiResponse)
async def reset_project_correction_config(project_id: str) -> ApiResponse:
    """
    Elimina la configuración personalizada y vuelve a la por defecto.
    """
    try:
        result = project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import CorrectionConfig

        # Eliminar configuración de settings del proyecto
        needs_update = False
        if "correction_config" in project.settings:
            del project.settings["correction_config"]
            needs_update = True
        if "correction_preset" in project.settings:
            del project.settings["correction_preset"]
            needs_update = True

        if needs_update:
            update_result = project_manager.update(project)
            if update_result.is_failure:
                return ApiResponse(success=False, error="Error al guardar configuración")
            logger.info(f"Deleted custom correction config for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "config": CorrectionConfig.default().to_dict(),
                "message": "Configuración restaurada a valores por defecto",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/correction-config/detect", response_model=ApiResponse)
async def detect_document_profile(project_id: str) -> ApiResponse:
    """
    Analiza el documento y sugiere un perfil de configuración.

    Detecta automáticamente:
    - Tipo de documento (literario, técnico, jurídico, etc.)
    - Nivel de registro (formal, coloquial)
    - Variante regional predominante
    - Presencia de diálogos
    """
    try:
        result = project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import (
            CorrectionConfig,
            DocumentField,
            RegisterLevel,
            AudienceType,
        )
        from narrative_assistant.corrections.detectors.regional import RegionalDetector
        from narrative_assistant.corrections.detectors.field_terminology import BUILTIN_FIELD_TERMS

        # Obtener texto del documento (primeros capítulos)
        chapters = chapter_repository.get_by_project(int(project_id)) if chapter_repository else []
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "detected": False,
                    "reason": "No hay capítulos analizados",
                    "suggested_preset": "default",
                }
            )

        # Tomar muestra de texto (primeros 3 capítulos o 50000 chars)
        sample_text = ""
        for chapter in chapters[:3]:
            sample_text += (chapter.content or "") + "\n\n"
            if len(sample_text) > 50000:
                break
        sample_text = sample_text[:50000].lower()

        # === Detección de características ===

        # 1. Detectar diálogos (rayas, comillas con verbos de habla)
        dialogue_indicators = [
            "—", "–",  # Rayas de diálogo
            "dijo", "preguntó", "respondió", "exclamó", "susurró",
            "murmuró", "gritó", "contestó", "añadió", "explicó",
        ]
        dialogue_count = sum(sample_text.count(ind) for ind in dialogue_indicators)
        has_dialogues = dialogue_count > 10

        # 2. Detectar registro (formal vs coloquial)
        formal_indicators = [
            "asimismo", "no obstante", "cabe destacar", "en consecuencia",
            "por consiguiente", "dicho lo cual", "en virtud de", "habida cuenta",
        ]
        colloquial_indicators = [
            "vale", "tío", "mola", "guay", "flipar", "curro", "pasta",
            "joder", "hostia", "coño", "gilipollas", "mierda",
        ]
        formal_count = sum(sample_text.count(ind) for ind in formal_indicators)
        colloquial_count = sum(sample_text.count(ind) for ind in colloquial_indicators)

        if formal_count > colloquial_count * 2:
            detected_register = "formal"
        elif colloquial_count > formal_count * 2:
            detected_register = "colloquial"
        else:
            detected_register = "neutral"

        # 3. Detectar campo/dominio por terminología
        field_scores = {field: 0 for field in DocumentField}

        for term, info in BUILTIN_FIELD_TERMS.items():
            if term in sample_text:
                field = info["field"]
                field_scores[field] += sample_text.count(term)

        # Detectar términos jurídicos específicos
        legal_terms = ["demandante", "demandado", "sentencia", "recurso", "tribunal",
                      "jurisprudencia", "ley", "artículo", "código", "contrato"]
        for term in legal_terms:
            if term in sample_text:
                field_scores[DocumentField.LEGAL] += sample_text.count(term) * 2

        # Detectar términos médicos específicos
        medical_terms = ["paciente", "diagnóstico", "tratamiento", "síntoma",
                        "enfermedad", "medicamento", "dosis", "clínico"]
        for term in medical_terms:
            if term in sample_text:
                field_scores[DocumentField.MEDICAL] += sample_text.count(term) * 2

        # Detectar términos técnicos/informáticos
        tech_terms = ["código", "programa", "sistema", "datos", "servidor",
                     "aplicación", "usuario", "interfaz", "algoritmo"]
        for term in tech_terms:
            if term in sample_text:
                field_scores[DocumentField.TECHNICAL] += sample_text.count(term)

        # El campo con mayor puntuación
        max_field = max(field_scores.keys(), key=lambda f: field_scores[f])
        max_score = field_scores[max_field]

        # Si tiene diálogos y no hay campo técnico dominante, es literario
        if has_dialogues and max_score < 20:
            detected_field = DocumentField.LITERARY
        elif max_score > 15:
            detected_field = max_field
        else:
            detected_field = DocumentField.GENERAL

        # 4. Detectar variante regional
        region_scores = {"es_ES": 0, "es_MX": 0, "es_AR": 0}

        for term, info in RegionalDetector.BUILTIN_REGIONAL_TERMS.items():
            if term in sample_text:
                region = info["region"]
                if region in region_scores:
                    region_scores[region] += sample_text.count(term)

        detected_region = max(region_scores.keys(), key=lambda r: region_scores[r])
        if region_scores[detected_region] < 3:
            detected_region = "es_ES"  # Default si no hay suficiente evidencia

        # === Seleccionar preset recomendado ===
        preset_map = {
            DocumentField.LITERARY: "novel",
            DocumentField.TECHNICAL: "technical",
            DocumentField.LEGAL: "legal",
            DocumentField.MEDICAL: "medical",
            DocumentField.JOURNALISTIC: "journalism",
            DocumentField.SELFHELP: "selfhelp",
            DocumentField.ACADEMIC: "technical",  # Similar a técnico
            DocumentField.BUSINESS: "technical",
            DocumentField.GENERAL: "default",
            DocumentField.CULINARY: "default",
        }
        suggested_preset = preset_map.get(detected_field, "default")

        # Obtener la config del preset
        preset_configs = {
            "default": CorrectionConfig.default,
            "novel": CorrectionConfig.for_novel,
            "technical": CorrectionConfig.for_technical,
            "legal": CorrectionConfig.for_legal,
            "medical": CorrectionConfig.for_medical,
            "journalism": CorrectionConfig.for_journalism,
            "selfhelp": CorrectionConfig.for_selfhelp,
        }
        suggested_config = preset_configs[suggested_preset]()

        # Ajustar la config según detección
        config_dict = suggested_config.to_dict()
        config_dict["profile"]["region"] = detected_region
        config_dict["profile"]["register"] = detected_register
        config_dict["regional"]["target_region"] = detected_region

        # Construir explicación
        detection_reasons = []
        if has_dialogues:
            detection_reasons.append(f"Diálogos detectados ({dialogue_count} indicadores)")
        if detected_field != DocumentField.GENERAL:
            detection_reasons.append(f"Terminología de {_field_label(detected_field).lower()}")
        if detected_register != "neutral":
            reg_label = "formal" if detected_register == "formal" else "coloquial"
            detection_reasons.append(f"Registro {reg_label}")
        if region_scores[detected_region] >= 3:
            detection_reasons.append(f"Variante regional: {detected_region}")

        return ApiResponse(
            success=True,
            data={
                "detected": True,
                "suggested_preset": suggested_preset,
                "suggested_config": config_dict,
                "detection": {
                    "field": detected_field.value,
                    "field_label": _field_label(detected_field),
                    "register": detected_register,
                    "region": detected_region,
                    "has_dialogues": has_dialogues,
                    "dialogue_count": dialogue_count,
                    "field_scores": {f.value: s for f, s in field_scores.items() if s > 0},
                    "region_scores": region_scores,
                },
                "reasons": detection_reasons,
                "confidence": min(0.9, 0.5 + (max_score / 50) + (0.2 if has_dialogues else 0)),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting document profile: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Glossary Endpoints
# ============================================================================

# Pydantic models for glossary
class GlossaryEntryRequest(BaseModel):
    """Request para crear/actualizar entrada de glosario"""
    term: str = Field(..., min_length=1, max_length=200)
    definition: str = Field(..., min_length=1)
    variants: list[str] = []
    category: str = "general"
    subcategory: Optional[str] = None
    context_notes: str = ""
    related_terms: list[str] = []
    usage_example: str = ""
    is_technical: bool = False
    is_invented: bool = False
    is_proper_noun: bool = False
    include_in_publication_glossary: bool = False


class GlossaryEntryResponse(BaseModel):
    """Respuesta con datos de una entrada de glosario"""
    id: int
    project_id: int
    term: str
    definition: str
    variants: list[str]
    category: str
    subcategory: Optional[str]
    context_notes: str
    related_terms: list[str]
    usage_example: str
    is_technical: bool
    is_invented: bool
    is_proper_noun: bool
    include_in_publication_glossary: bool
    usage_count: int
    first_chapter: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


@app.get("/api/projects/{project_id}/glossary", response_model=ApiResponse)
async def list_glossary_entries(
    project_id: str,
    category: Optional[str] = None,
    only_technical: bool = False,
    only_invented: bool = False,
    only_for_publication: bool = False,
) -> ApiResponse:
    """
    Lista todas las entradas del glosario de un proyecto.

    Args:
        project_id: ID del proyecto
        category: Filtrar por categoría (personaje, lugar, objeto, concepto, técnico)
        only_technical: Solo términos técnicos
        only_invented: Solo términos inventados
        only_for_publication: Solo para glosario de publicación
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entries = repo.list_by_project(
            project_id=int(project_id),
            category=category,
            only_technical=only_technical,
            only_invented=only_invented,
            only_for_publication=only_for_publication,
        )

        return ApiResponse(
            success=True,
            data={
                "entries": [entry.to_dict() for entry in entries],
                "total": len(entries),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing glossary entries: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/glossary", response_model=ApiResponse)
async def create_glossary_entry(
    project_id: str,
    request: GlossaryEntryRequest,
) -> ApiResponse:
    """
    Crea una nueva entrada en el glosario.
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryEntry, GlossaryRepository

        repo = GlossaryRepository()

        entry = GlossaryEntry(
            project_id=int(project_id),
            term=request.term,
            definition=request.definition,
            variants=request.variants,
            category=request.category,
            subcategory=request.subcategory,
            context_notes=request.context_notes,
            related_terms=request.related_terms,
            usage_example=request.usage_example,
            is_technical=request.is_technical,
            is_invented=request.is_invented,
            is_proper_noun=request.is_proper_noun,
            include_in_publication_glossary=request.include_in_publication_glossary,
        )

        created = repo.create(entry)

        return ApiResponse(
            success=True,
            data=created.to_dict(),
            message=f"Término '{request.term}' añadido al glosario",
        )

    except ValueError as e:
        # Término duplicado
        return ApiResponse(success=False, error=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/glossary/{entry_id}", response_model=ApiResponse)
async def get_glossary_entry(
    project_id: str,
    entry_id: int,
) -> ApiResponse:
    """
    Obtiene una entrada específica del glosario.
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entry = repo.get(entry_id)

        if not entry or entry.project_id != int(project_id):
            raise HTTPException(status_code=404, detail="Glossary entry not found")

        return ApiResponse(success=True, data=entry.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.put("/api/projects/{project_id}/glossary/{entry_id}", response_model=ApiResponse)
async def update_glossary_entry(
    project_id: str,
    entry_id: int,
    request: GlossaryEntryRequest,
) -> ApiResponse:
    """
    Actualiza una entrada existente del glosario.
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        existing = repo.get(entry_id)

        if not existing or existing.project_id != int(project_id):
            raise HTTPException(status_code=404, detail="Glossary entry not found")

        # Actualizar campos
        existing.term = request.term
        existing.definition = request.definition
        existing.variants = request.variants
        existing.category = request.category
        existing.subcategory = request.subcategory
        existing.context_notes = request.context_notes
        existing.related_terms = request.related_terms
        existing.usage_example = request.usage_example
        existing.is_technical = request.is_technical
        existing.is_invented = request.is_invented
        existing.is_proper_noun = request.is_proper_noun
        existing.include_in_publication_glossary = request.include_in_publication_glossary

        repo.update(existing)

        return ApiResponse(
            success=True,
            data=existing.to_dict(),
            message=f"Término '{request.term}' actualizado",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/glossary/{entry_id}", response_model=ApiResponse)
async def delete_glossary_entry(
    project_id: str,
    entry_id: int,
) -> ApiResponse:
    """
    Elimina una entrada del glosario.
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        existing = repo.get(entry_id)

        if not existing or existing.project_id != int(project_id):
            raise HTTPException(status_code=404, detail="Glossary entry not found")

        term = existing.term
        repo.delete(entry_id)

        return ApiResponse(
            success=True,
            message=f"Término '{term}' eliminado del glosario",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting glossary entry: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/glossary/context/llm", response_model=ApiResponse)
async def get_glossary_llm_context(
    project_id: str,
    max_entries: int = 50,
    categories: Optional[str] = None,
) -> ApiResponse:
    """
    Genera el contexto del glosario para el LLM.

    Args:
        project_id: ID del proyecto
        max_entries: Máximo de entradas a incluir
        categories: Categorías a incluir (separadas por coma)
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()

        category_list = None
        if categories:
            category_list = [c.strip() for c in categories.split(",")]

        context = repo.generate_llm_context(
            project_id=int(project_id),
            max_entries=max_entries,
            categories=category_list,
        )

        return ApiResponse(
            success=True,
            data={
                "context": context,
                "length": len(context),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating glossary LLM context: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/glossary/export/publication", response_model=ApiResponse)
async def export_glossary_for_publication(project_id: str) -> ApiResponse:
    """
    Exporta el glosario formateado para incluir en la publicación.

    Solo incluye términos marcados para publicación.
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        content = repo.export_for_publication(int(project_id))

        return ApiResponse(
            success=True,
            data={
                "content": content,
                "format": "markdown",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting glossary: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/glossary/import", response_model=ApiResponse)
async def import_glossary(
    project_id: str,
    entries: list[dict] = Body(...),
    merge: bool = True,
) -> ApiResponse:
    """
    Importa entradas al glosario desde una lista JSON.

    Args:
        project_id: ID del proyecto
        entries: Lista de entradas con formato {term, definition, variants?, category?, ...}
        merge: Si True, actualiza existentes; si False, salta duplicados
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        created, updated = repo.import_from_dict(int(project_id), entries, merge=merge)

        return ApiResponse(
            success=True,
            data={
                "created": created,
                "updated": updated,
                "total_processed": len(entries),
            },
            message=f"Importados {created} términos nuevos, actualizados {updated}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing glossary: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/glossary/search", response_model=ApiResponse)
async def search_glossary(
    project_id: str,
    q: str = Query(..., min_length=1, description="Término a buscar"),
) -> ApiResponse:
    """
    Busca un término en el glosario (por término principal o variantes).
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entry = repo.find_by_term_or_variant(int(project_id), q)

        if entry:
            return ApiResponse(
                success=True,
                data={
                    "found": True,
                    "entry": entry.to_dict(),
                }
            )
        else:
            return ApiResponse(
                success=True,
                data={
                    "found": False,
                    "entry": None,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching glossary: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/glossary/summary", response_model=ApiResponse)
async def get_glossary_summary(project_id: str) -> ApiResponse:
    """
    Obtiene un resumen del glosario del proyecto.
    """
    try:
        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.persistence.glossary import GlossaryRepository

        repo = GlossaryRepository()
        entries = repo.list_by_project(int(project_id))

        # Calcular estadísticas
        by_category = {}
        technical_count = 0
        invented_count = 0
        for_publication = 0

        for entry in entries:
            cat = entry.category or "general"
            by_category[cat] = by_category.get(cat, 0) + 1
            if entry.is_technical:
                technical_count += 1
            if entry.is_invented:
                invented_count += 1
            if entry.include_in_publication_glossary:
                for_publication += 1

        return ApiResponse(
            success=True,
            data={
                "total_entries": len(entries),
                "by_category": by_category,
                "technical_count": technical_count,
                "invented_count": invented_count,
                "for_publication_count": for_publication,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting glossary summary: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Dictionary Endpoints (Diccionarios Offline)
# ============================================================================

@app.get("/api/dictionary/lookup/{word}", response_model=ApiResponse)
async def dictionary_lookup(word: str):
    """
    Busca una palabra en los diccionarios locales.

    Consulta múltiples fuentes (Wiktionary, sinónimos, personalizado)
    y devuelve información combinada.

    Args:
        word: Palabra a buscar

    Returns:
        ApiResponse con la entrada del diccionario
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.lookup(word)

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "found": False,
                    "word": word,
                    "message": str(result.error.user_message) if result.error else "No encontrado",
                    "external_links": manager.get_all_external_links(word),
                }
            )

        entry = result.value
        return ApiResponse(
            success=True,
            data={
                "found": True,
                "entry": entry.to_dict(),
                "external_links": manager.get_all_external_links(word),
            }
        )

    except Exception as e:
        logger.error(f"Error looking up word '{word}': {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/dictionary/synonyms/{word}", response_model=ApiResponse)
async def get_synonyms(word: str):
    """
    Obtiene sinónimos de una palabra.

    Args:
        word: Palabra a buscar

    Returns:
        ApiResponse con lista de sinónimos
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        synonyms = manager.get_synonyms(word)
        antonyms = manager.get_antonyms(word)

        return ApiResponse(
            success=True,
            data={
                "word": word,
                "synonyms": synonyms,
                "antonyms": antonyms,
            }
        )

    except Exception as e:
        logger.error(f"Error getting synonyms for '{word}': {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/dictionary/search", response_model=ApiResponse)
async def dictionary_search(prefix: str, limit: int = 20):
    """
    Busca palabras que empiecen con un prefijo.

    Útil para autocompletado.

    Args:
        prefix: Prefijo a buscar
        limit: Máximo de resultados (default: 20)

    Returns:
        ApiResponse con lista de palabras
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        words = manager.search_prefix(prefix, limit)

        return ApiResponse(
            success=True,
            data={
                "prefix": prefix,
                "words": words,
                "count": len(words),
            }
        )

    except Exception as e:
        logger.error(f"Error searching prefix '{prefix}': {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/dictionary/status", response_model=ApiResponse)
async def dictionary_status():
    """
    Obtiene el estado de los diccionarios.

    Returns:
        ApiResponse con información de cada fuente de diccionario
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        status = manager.get_status()

        return ApiResponse(
            success=True,
            data={
                "sources": status,
                "data_dir": str(manager.data_dir),
            }
        )

    except Exception as e:
        logger.error(f"Error getting dictionary status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/dictionary/initialize", response_model=ApiResponse)
async def initialize_dictionaries():
    """
    Inicializa los diccionarios si no existen.

    Crea las bases de datos con datos básicos.
    En el futuro, esto podría descargar datos completos.

    Returns:
        ApiResponse indicando éxito
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.ensure_dictionaries()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "message": "Diccionarios inicializados correctamente",
                "status": manager.get_status(),
            }
        )

    except Exception as e:
        logger.error(f"Error initializing dictionaries: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


class CustomWordRequest(BaseModel):
    """Request para añadir palabra personalizada."""
    word: str = Field(..., description="Palabra a añadir")
    definition: str = Field(..., description="Definición")
    category: Optional[str] = Field(None, description="Categoría gramatical")
    synonyms: Optional[list[str]] = Field(None, description="Sinónimos")
    antonyms: Optional[list[str]] = Field(None, description="Antónimos")


@app.post("/api/dictionary/custom", response_model=ApiResponse)
async def add_custom_word(request: CustomWordRequest):
    """
    Añade una palabra al diccionario personalizado.

    Args:
        request: Datos de la palabra

    Returns:
        ApiResponse indicando éxito
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.add_custom_word(
            word=request.word,
            definition=request.definition,
            category=request.category,
            synonyms=request.synonyms,
            antonyms=request.antonyms,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "message": f"Palabra '{request.word}' añadida correctamente",
                "word": request.word,
            }
        )

    except Exception as e:
        logger.error(f"Error adding custom word: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/dictionary/custom/{word}", response_model=ApiResponse)
async def remove_custom_word(word: str):
    """
    Elimina una palabra del diccionario personalizado.

    Args:
        word: Palabra a eliminar

    Returns:
        ApiResponse indicando éxito
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        result = manager.remove_custom_word(word)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        removed = result.value
        if removed:
            return ApiResponse(
                success=True,
                data={"message": f"Palabra '{word}' eliminada", "removed": True}
            )
        else:
            return ApiResponse(
                success=True,
                data={"message": f"Palabra '{word}' no existía", "removed": False}
            )

    except Exception as e:
        logger.error(f"Error removing custom word: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/dictionary/custom", response_model=ApiResponse)
async def list_custom_words():
    """
    Lista todas las palabras del diccionario personalizado.

    Returns:
        ApiResponse con lista de palabras
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager

        manager = get_dictionary_manager()
        words = manager.list_custom_words()

        return ApiResponse(
            success=True,
            data={
                "words": words,
                "count": len(words),
            }
        )

    except Exception as e:
        logger.error(f"Error listing custom words: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/dictionary/external-links/{word}", response_model=ApiResponse)
async def get_external_dictionary_links(word: str):
    """
    Obtiene enlaces a diccionarios externos para una palabra.

    Args:
        word: Palabra a buscar

    Returns:
        ApiResponse con enlaces a diccionarios externos
    """
    try:
        from narrative_assistant.dictionaries import get_dictionary_manager
        from narrative_assistant.dictionaries.models import EXTERNAL_DICTIONARIES

        manager = get_dictionary_manager()
        links = manager.get_all_external_links(word)

        # Añadir información adicional de cada diccionario
        detailed_links = []
        for name, url in links.items():
            ext_dict = EXTERNAL_DICTIONARIES.get(name)
            if ext_dict:
                detailed_links.append({
                    "name": ext_dict.name,
                    "id": name,
                    "url": url,
                    "description": ext_dict.description,
                    "requires_license": ext_dict.requires_license,
                })

        return ApiResponse(
            success=True,
            data={
                "word": word,
                "links": detailed_links,
            }
        )

    except Exception as e:
        logger.error(f"Error getting external links for '{word}': {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Voice Analysis Endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/voice-profiles", response_model=ApiResponse)
async def get_voice_profiles(project_id: int):
    """
    Obtiene perfiles de voz de los personajes del proyecto.

    Construye perfiles estilísticos basados en los diálogos de cada personaje,
    incluyendo métricas como longitud de intervención, riqueza léxica (TTR),
    formalidad, muletillas y patrones de puntuación.

    Returns:
        ApiResponse con perfiles de voz por personaje
    """
    try:
        from narrative_assistant.voice.profiles import VoiceProfileBuilder
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener entidades (solo personajes)
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if e.entity_type == "PER"]

        if not characters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "profiles": [],
                    "message": "No hay personajes para analizar"
                }
            )

        # Obtener capítulos y extraer diálogos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        dialogues = []
        for chapter in chapters:
            dialogue_result = detect_dialogues(chapter.content)
            if dialogue_result.is_success:
                for d in dialogue_result.value.dialogues:
                    dialogues.append({
                        "text": d.text,
                        "speaker_id": d.speaker_id,
                        "speaker_hint": d.speaker_hint,
                        "chapter": chapter.chapter_number,
                        "position": d.start_char,
                    })

        if not dialogues:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "profiles": [],
                    "message": "No se encontraron diálogos para analizar"
                }
            )

        # Construir perfiles de voz
        entity_data = [
            {"id": e.id, "name": e.canonical_name, "aliases": e.aliases}
            for e in characters
        ]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entity_data)

        # Serializar perfiles
        profiles_data = []
        for profile in profiles:
            profile_dict = profile.to_dict()
            profiles_data.append(profile_dict)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "profiles": profiles_data,
                "stats": {
                    "characters_analyzed": len(profiles_data),
                    "total_dialogues": len(dialogues),
                    "chapters_analyzed": len(chapters),
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice profiles: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/register-analysis", response_model=ApiResponse)
async def get_register_analysis(
    project_id: int,
    min_severity: str = Query("medium", description="Severidad mínima: low, medium, high")
):
    """
    Analiza el registro narrativo del proyecto.

    Detecta cambios de registro narrativo (formal/informal, técnico/coloquial)
    que pueden indicar inconsistencias en la voz del narrador o entre escenas.

    Returns:
        ApiResponse con análisis de registro y cambios detectados
    """
    try:
        from narrative_assistant.voice.register import (
            RegisterChangeDetector,
            RegisterAnalyzer,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "analyses": [],
                    "changes": [],
                    "summary": {},
                    "message": "No hay capítulos para analizar"
                }
            )

        # Construir segmentos: (texto, capítulo, posición, es_diálogo)
        segments = []
        for chapter in chapters:
            # Detectar diálogos para separar narración de diálogo
            dialogue_result = detect_dialogues(chapter.content)
            dialogue_ranges = []
            if dialogue_result.is_success:
                dialogue_ranges = [
                    (d.start_char, d.end_char)
                    for d in dialogue_result.value.dialogues
                ]

            # Dividir contenido en párrafos
            paragraphs = chapter.content.split('\n\n')
            position = 0

            for para in paragraphs:
                if para.strip():
                    # Determinar si es diálogo
                    is_dialogue = any(
                        start <= position <= end
                        for start, end in dialogue_ranges
                    )
                    segments.append((
                        para.strip(),
                        chapter.chapter_number,
                        position,
                        is_dialogue
                    ))
                position += len(para) + 2  # +2 por '\n\n'

        if not segments:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "analyses": [],
                    "changes": [],
                    "summary": {},
                    "message": "No hay segmentos para analizar"
                }
            )

        # Analizar registro
        detector = RegisterChangeDetector()
        analyses = detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity)
        summary = detector.get_summary()

        # Serializar resultados
        analyses_data = [
            {
                "segment_index": i,
                "chapter": segments[i][1],
                "is_dialogue": segments[i][3],
                "primary_register": a.primary_register.value,
                "register_scores": {k.value: v for k, v in a.register_scores.items()},
                "confidence": a.confidence,
                "formal_indicators": list(a.formal_indicators)[:5],
                "colloquial_indicators": list(a.colloquial_indicators)[:5],
            }
            for i, a in enumerate(analyses)
        ]

        changes_data = [
            {
                "from_segment": c.from_segment_index,
                "to_segment": c.to_segment_index,
                "from_register": c.from_register.value,
                "to_register": c.to_register.value,
                "severity": c.severity,
                "explanation": c.explanation,
                "chapter": segments[c.to_segment_index][1] if c.to_segment_index < len(segments) else None,
            }
            for c in changes
        ]

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "analyses": analyses_data,
                "changes": changes_data,
                "summary": summary,
                "stats": {
                    "segments_analyzed": len(analyses),
                    "changes_detected": len(changes),
                    "chapters_analyzed": len(chapters),
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing register: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/chapters/{chapter_num}/dialogue-attributions", response_model=ApiResponse)
async def get_dialogue_attributions(project_id: int, chapter_num: int):
    """
    Obtiene atribución de hablantes para los diálogos de un capítulo.

    Utiliza múltiples estrategias para identificar quién habla cada diálogo:
    - Detección explícita (verbo de habla + nombre)
    - Alternancia (patrón A-B-A-B)
    - Perfil de voz (comparación estilística)
    - Proximidad (entidad mencionada cerca)

    Returns:
        ApiResponse con atribuciones de diálogos y estadísticas
    """
    try:
        from narrative_assistant.voice.speaker_attribution import SpeakerAttributor
        from narrative_assistant.voice.profiles import VoiceProfileBuilder
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar proyecto
        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener capítulo específico
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        chapter = next((c for c in chapters if c.chapter_number == chapter_num), None)

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Capítulo {chapter_num} no encontrado")

        # Obtener entidades (personajes)
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if e.entity_type == "PER"]

        # Obtener menciones de entidades en el capítulo
        entity_mentions = []
        for entity in characters:
            mentions = entity_repo.get_mentions_by_entity(entity.id)
            for m in mentions:
                if m.chapter_id == chapter.id:
                    entity_mentions.append((entity.id, m.start_char, m.end_char))

        # Detectar diálogos
        dialogue_result = detect_dialogues(chapter.content)
        if dialogue_result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "chapter_num": chapter_num,
                    "attributions": [],
                    "stats": {},
                    "message": "No se pudieron detectar diálogos"
                }
            )

        dialogues = dialogue_result.value.dialogues
        if not dialogues:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "chapter_num": chapter_num,
                    "attributions": [],
                    "stats": {},
                    "message": "No hay diálogos en este capítulo"
                }
            )

        # Preparar datos de entidades para el atribuidor
        entity_data = [
            type('Entity', (), {
                'id': e.id,
                'canonical_name': e.canonical_name,
                'aliases': e.aliases or []
            })()
            for e in characters
        ]

        # Construir perfiles de voz (opcional, mejora precisión)
        voice_profiles = None
        try:
            # Obtener todos los diálogos del proyecto para perfiles
            all_dialogues = []
            for ch in chapters:
                ch_dialogue_result = detect_dialogues(ch.content)
                if ch_dialogue_result.is_success:
                    for d in ch_dialogue_result.value.dialogues:
                        all_dialogues.append({
                            "text": d.text,
                            "speaker_id": d.speaker_id,
                            "chapter": ch.chapter_number,
                            "position": d.start_char,
                        })

            if all_dialogues:
                entity_dict_data = [
                    {"id": e.id, "name": e.canonical_name, "aliases": e.aliases}
                    for e in characters
                ]
                builder = VoiceProfileBuilder()
                profiles = builder.build_profiles(all_dialogues, entity_dict_data)
                voice_profiles = {p.entity_id: p for p in profiles}
        except Exception as e:
            logger.warning(f"Could not build voice profiles: {e}")

        # Atribuir hablantes
        attributor = SpeakerAttributor(entity_data, voice_profiles)
        attributions = attributor.attribute_dialogues(
            dialogues, entity_mentions, chapter.content
        )
        stats = attributor.get_attribution_stats(attributions)

        # Serializar atribuciones
        attributions_data = [
            {
                "dialogue_index": i,
                "text": dialogues[i].text[:100] + "..." if len(dialogues[i].text) > 100 else dialogues[i].text,
                "start_char": dialogues[i].start_char,
                "end_char": dialogues[i].end_char,
                "speaker_id": attr.speaker_id,
                "speaker_name": attr.speaker_name,
                "confidence": attr.confidence.value,
                "method": attr.attribution_method.value,
                "speech_verb": attr.speech_verb,
                "alternatives": [
                    {"id": alt[0], "name": alt[1], "score": alt[2]}
                    for alt in (attr.alternative_speakers or [])[:3]
                ],
            }
            for i, attr in enumerate(attributions)
        ]

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_num": chapter_num,
                "attributions": attributions_data,
                "stats": stats,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error attributing speakers: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Focalization - Declaración y Detección de Violaciones
# ============================================================================

@app.get("/api/projects/{project_id}/focalization", response_model=ApiResponse)
async def get_project_focalizations(project_id: int):
    """Obtiene todas las declaraciones de focalización de un proyecto."""
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        declarations = service.get_all_declarations(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "declarations": [d.to_dict() for d in declarations],
                "total": len(declarations),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting focalizations: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/focalization", response_model=ApiResponse)
async def create_focalization(project_id: int, data: dict):
    """Crea una nueva declaración de focalización para un capítulo/escena."""
    try:
        from narrative_assistant.focalization import (
            FocalizationType,
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter = data.get("chapter")
        if not chapter:
            return ApiResponse(success=False, error="Se requiere número de capítulo")

        foc_type_str = data.get("focalization_type", "zero")
        try:
            foc_type = FocalizationType(foc_type_str)
        except ValueError:
            return ApiResponse(success=False, error=f"Tipo de focalización inválido: {foc_type_str}")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        declaration = service.declare_focalization(
            project_id=project_id,
            chapter=chapter,
            focalization_type=foc_type,
            focalizer_ids=data.get("focalizer_ids", []),
            scene=data.get("scene"),
            notes=data.get("notes", ""),
        )

        return ApiResponse(success=True, data=declaration.to_dict())
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.put("/api/projects/{project_id}/focalization/{declaration_id}", response_model=ApiResponse)
async def update_focalization(project_id: int, declaration_id: int, data: dict):
    """Actualiza una declaración de focalización existente."""
    try:
        from narrative_assistant.focalization import (
            FocalizationType,
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        foc_type = None
        if "focalization_type" in data:
            try:
                foc_type = FocalizationType(data["focalization_type"])
            except ValueError:
                return ApiResponse(success=False, error=f"Tipo inválido: {data['focalization_type']}")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        declaration = service.update_focalization(
            declaration_id=declaration_id,
            focalization_type=foc_type,
            focalizer_ids=data.get("focalizer_ids"),
            notes=data.get("notes"),
        )

        return ApiResponse(success=True, data=declaration.to_dict())
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/focalization/{declaration_id}", response_model=ApiResponse)
async def delete_focalization(project_id: int, declaration_id: int):
    """Elimina una declaración de focalización."""
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        deleted = service.delete_focalization(declaration_id)

        if deleted:
            return ApiResponse(success=True, message="Declaración eliminada")
        return ApiResponse(success=False, error="Declaración no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/focalization/violations", response_model=ApiResponse)
async def detect_focalization_violations(project_id: int):
    """Detecta violaciones de focalización en todo el proyecto."""
    try:
        from narrative_assistant.focalization import (
            FocalizationDeclarationService,
            FocalizationViolationDetector,
            SQLiteFocalizationRepository,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository
        from narrative_assistant.entities.repository import get_entity_repository

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        if not chapters:
            return ApiResponse(success=True, data={"violations": [], "stats": {"total": 0}})

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if e.entity_type == "PER"]

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        detector = FocalizationViolationDetector(service, characters)

        all_violations = []
        by_chapter = {}

        for chapter in chapters:
            violations = detector.detect_violations(
                project_id=project_id,
                text=chapter.content,
                chapter=chapter.chapter_number,
            )
            by_chapter[chapter.chapter_number] = {
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "violations_count": len(violations),
                "violations": [v.to_dict() for v in violations],
            }
            all_violations.extend([v.to_dict() for v in violations])

        stats = {
            "total": len(all_violations),
            "by_type": {},
            "by_severity": {},
            "chapters_with_violations": sum(1 for ch in by_chapter.values() if ch["violations_count"] > 0),
        }
        for v in all_violations:
            stats["by_type"][v["violation_type"]] = stats["by_type"].get(v["violation_type"], 0) + 1
            stats["by_severity"][v["severity"]] = stats["by_severity"].get(v["severity"], 0) + 1

        return ApiResponse(success=True, data={"violations": all_violations, "by_chapter": by_chapter, "stats": stats})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting focalization violations: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/chapters/{chapter_number}/focalization/suggest", response_model=ApiResponse)
async def suggest_chapter_focalization(project_id: int, chapter_number: int):
    """Sugiere la focalización más probable para un capítulo."""
    try:
        from narrative_assistant.focalization import FocalizationDeclarationService, SQLiteFocalizationRepository
        from narrative_assistant.persistence.chapter import get_chapter_repository
        from narrative_assistant.entities.repository import get_entity_repository

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        chapter = next((c for c in chapters if c.chapter_number == chapter_number), None)

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Capítulo {chapter_number} no encontrado")

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if e.entity_type == "PER"]

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        suggestion = service.suggest_focalization(project_id, chapter_number, chapter.content, characters)

        focalizer_names = []
        for fid in suggestion.get("suggested_focalizers", []):
            entity = next((e for e in characters if e.id == fid), None)
            if entity:
                focalizer_names.append({"id": fid, "name": entity.canonical_name or entity.name})

        return ApiResponse(
            success=True,
            data={
                "chapter_number": chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter_number}",
                "suggested_type": suggestion["suggested_type"].value if suggestion["suggested_type"] else None,
                "suggested_focalizers": focalizer_names,
                "confidence": suggestion["confidence"],
                "evidence": suggestion["evidence"],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suggesting focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Scenes - Gestión de Escenas y Etiquetado
# ============================================================================

@app.get("/api/projects/{project_id}/scenes", response_model=ApiResponse)
async def get_project_scenes(project_id: int):
    """
    Obtiene todas las escenas de un proyecto con sus etiquetas.

    Incluye metadata para determinar si mostrar la UI de escenas.
    """
    try:
        from narrative_assistant.scenes import SceneService

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        scenes = service.get_scenes(project_id)
        stats = service.get_stats(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "has_scenes": stats.has_scenes,
                "total_scenes": stats.total_scenes,
                "stats": {
                    "chapters_with_scenes": stats.chapters_with_scenes,
                    "tagged_scenes": stats.tagged_scenes,
                    "untagged_scenes": stats.untagged_scenes,
                    "scenes_by_type": stats.scenes_by_type,
                    "scenes_by_tone": stats.scenes_by_tone,
                    "custom_tags_used": stats.custom_tags_used,
                },
                "scenes": [
                    {
                        "id": s.scene.id,
                        "chapter_id": s.scene.chapter_id,
                        "chapter_number": s.chapter_number,
                        "chapter_title": s.chapter_title,
                        "scene_number": s.scene.scene_number,
                        "start_char": s.scene.start_char,
                        "end_char": s.scene.end_char,
                        "word_count": s.scene.word_count,
                        "separator_type": s.scene.separator_type,
                        "excerpt": s.excerpt,
                        "tags": {
                            "scene_type": s.tags.scene_type.value if s.tags and s.tags.scene_type else None,
                            "tone": s.tags.tone.value if s.tags and s.tags.tone else None,
                            "location_entity_id": s.tags.location_entity_id if s.tags else None,
                            "location_name": s.location_name,
                            "participant_ids": s.tags.participant_ids if s.tags else [],
                            "participant_names": s.participant_names,
                            "summary": s.tags.summary if s.tags else None,
                            "notes": s.tags.notes if s.tags else None,
                        } if s.tags else None,
                        "custom_tags": [
                            {"name": ct.tag_name, "color": ct.tag_color}
                            for ct in s.custom_tags
                        ],
                    }
                    for s in scenes
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scenes: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/scenes/stats", response_model=ApiResponse)
async def get_scenes_stats(project_id: int):
    """
    Obtiene solo las estadísticas de escenas (lightweight).

    Útil para determinar si mostrar el tab de escenas en la UI.
    """
    try:
        from narrative_assistant.scenes import SceneService

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        stats = service.get_stats(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "has_scenes": stats.has_scenes,
                "total_scenes": stats.total_scenes,
                "chapters_with_scenes": stats.chapters_with_scenes,
                "tagged_scenes": stats.tagged_scenes,
                "untagged_scenes": stats.untagged_scenes,
                "scenes_by_type": stats.scenes_by_type,
                "scenes_by_tone": stats.scenes_by_tone,
                "custom_tags_used": stats.custom_tags_used,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scene stats: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/chapters/{chapter_number}/scenes", response_model=ApiResponse)
async def get_chapter_scenes(project_id: int, chapter_number: int):
    """Obtiene las escenas de un capítulo específico."""
    try:
        from narrative_assistant.scenes import SceneService

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        scenes = service.get_scenes_by_chapter(project_id, chapter_number)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_number": chapter_number,
                "scenes": [
                    {
                        "id": s.scene.id,
                        "scene_number": s.scene.scene_number,
                        "start_char": s.scene.start_char,
                        "end_char": s.scene.end_char,
                        "word_count": s.scene.word_count,
                        "excerpt": s.excerpt,
                        "tags": {
                            "scene_type": s.tags.scene_type.value if s.tags and s.tags.scene_type else None,
                            "tone": s.tags.tone.value if s.tags and s.tags.tone else None,
                            "location_name": s.location_name,
                            "participant_names": s.participant_names,
                            "summary": s.tags.summary if s.tags else None,
                        } if s.tags else None,
                        "custom_tags": [ct.tag_name for ct in s.custom_tags],
                    }
                    for s in scenes
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chapter scenes: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.put("/api/projects/{project_id}/scenes/{scene_id}/tags", response_model=ApiResponse)
async def tag_scene(project_id: int, scene_id: int, data: dict):
    """
    Asigna etiquetas predefinidas a una escena.

    Body:
        - scene_type: tipo de escena (action, dialogue, exposition, etc.)
        - tone: tono emocional (tense, calm, happy, etc.)
        - location_entity_id: ID de la entidad de ubicación
        - participant_ids: lista de IDs de entidades participantes
        - summary: resumen breve
        - notes: notas del usuario
    """
    try:
        from narrative_assistant.scenes import SceneService, SceneType, SceneTone

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()

        # Parse scene_type
        scene_type = None
        if data.get("scene_type"):
            try:
                scene_type = SceneType(data["scene_type"])
            except ValueError:
                return ApiResponse(success=False, error=f"Tipo de escena inválido: {data['scene_type']}")

        # Parse tone
        tone = None
        if data.get("tone"):
            try:
                tone = SceneTone(data["tone"])
            except ValueError:
                return ApiResponse(success=False, error=f"Tono inválido: {data['tone']}")

        success = service.tag_scene(
            scene_id=scene_id,
            scene_type=scene_type,
            tone=tone,
            location_entity_id=data.get("location_entity_id"),
            participant_ids=data.get("participant_ids", []),
            summary=data.get("summary"),
            notes=data.get("notes"),
        )

        if success:
            return ApiResponse(success=True, message="Escena etiquetada correctamente")
        return ApiResponse(success=False, error="Escena no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tagging scene: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/scenes/{scene_id}/custom-tags", response_model=ApiResponse)
async def add_custom_tag(project_id: int, scene_id: int, data: dict):
    """
    Añade una etiqueta personalizada a una escena.

    Body:
        - tag_name: nombre de la etiqueta
        - tag_color: color hex opcional (#FF5733)
    """
    try:
        from narrative_assistant.scenes import SceneService

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        tag_name = data.get("tag_name", "").strip()
        if not tag_name:
            return ApiResponse(success=False, error="Se requiere nombre de etiqueta")

        service = SceneService()
        success = service.add_custom_tag(
            scene_id=scene_id,
            tag_name=tag_name,
            tag_color=data.get("tag_color"),
        )

        if success:
            return ApiResponse(success=True, message=f"Etiqueta '{tag_name}' añadida")
        return ApiResponse(success=False, error="Escena no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding custom tag: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.delete("/api/projects/{project_id}/scenes/{scene_id}/custom-tags/{tag_name}", response_model=ApiResponse)
async def remove_custom_tag(project_id: int, scene_id: int, tag_name: str):
    """Elimina una etiqueta personalizada de una escena."""
    try:
        from narrative_assistant.scenes import SceneService

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        success = service.remove_custom_tag(scene_id, tag_name)

        if success:
            return ApiResponse(success=True, message=f"Etiqueta '{tag_name}' eliminada")
        return ApiResponse(success=False, error="Etiqueta no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing custom tag: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/scenes/tag-catalog", response_model=ApiResponse)
async def get_tag_catalog(project_id: int):
    """Obtiene el catálogo de etiquetas personalizadas disponibles en el proyecto."""
    try:
        from narrative_assistant.scenes import SceneService

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        catalog = service.get_tag_catalog(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "tags": catalog,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tag catalog: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/scenes/filter", response_model=ApiResponse)
async def filter_scenes(
    project_id: int,
    scene_type: Optional[str] = None,
    tone: Optional[str] = None,
    custom_tag: Optional[str] = None,
    location_id: Optional[int] = None,
    participant_id: Optional[int] = None,
):
    """
    Filtra escenas por criterios.

    Query params:
        - scene_type: filtrar por tipo (action, dialogue, etc.)
        - tone: filtrar por tono (tense, calm, etc.)
        - custom_tag: filtrar por etiqueta personalizada
        - location_id: filtrar por ubicación
        - participant_id: filtrar por participante
    """
    try:
        from narrative_assistant.scenes import SceneService, SceneType, SceneTone

        if not project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Parse filters
        parsed_type = None
        if scene_type:
            try:
                parsed_type = SceneType(scene_type)
            except ValueError:
                return ApiResponse(success=False, error=f"Tipo de escena inválido: {scene_type}")

        parsed_tone = None
        if tone:
            try:
                parsed_tone = SceneTone(tone)
            except ValueError:
                return ApiResponse(success=False, error=f"Tono inválido: {tone}")

        service = SceneService()
        scenes = service.filter_scenes(
            project_id=project_id,
            scene_type=parsed_type,
            tone=parsed_tone,
            custom_tag=custom_tag,
            location_id=location_id,
            participant_id=participant_id,
        )

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "filters": {
                    "scene_type": scene_type,
                    "tone": tone,
                    "custom_tag": custom_tag,
                    "location_id": location_id,
                    "participant_id": participant_id,
                },
                "count": len(scenes),
                "scenes": [
                    {
                        "id": s.scene.id,
                        "chapter_number": s.chapter_number,
                        "scene_number": s.scene.scene_number,
                        "excerpt": s.excerpt,
                        "tags": {
                            "scene_type": s.tags.scene_type.value if s.tags and s.tags.scene_type else None,
                            "tone": s.tags.tone.value if s.tags and s.tags.tone else None,
                        } if s.tags else None,
                    }
                    for s in scenes
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering scenes: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Endpoints - Feature Profiles y Tipos de Documento
# ============================================================================

@app.get("/api/document-types", response_model=ApiResponse)
async def get_document_types():
    """
    Lista todos los tipos de documento disponibles.

    Returns:
        ApiResponse con lista de tipos y sus subtipos
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        types = service.get_document_types()

        return ApiResponse(success=True, data=types)
    except Exception as e:
        logger.error(f"Error getting document types: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/document-type", response_model=ApiResponse)
async def get_project_document_type(project_id: int):
    """
    Obtiene el tipo de documento actual de un proyecto.

    Returns:
        ApiResponse con tipo, subtipo, confirmación y detección
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        doc_type = service.get_project_document_type(project_id)

        if not doc_type:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        return ApiResponse(success=True, data=doc_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document type for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.put("/api/projects/{project_id}/document-type", response_model=ApiResponse)
async def set_project_document_type(
    project_id: int,
    document_type: str = Body(..., embed=True),
    document_subtype: Optional[str] = Body(None, embed=True),
):
    """
    Establece el tipo de documento de un proyecto.

    Args:
        project_id: ID del proyecto
        document_type: Código del tipo (FIC, MEM, etc.)
        document_subtype: Código del subtipo (opcional)

    Returns:
        ApiResponse con el perfil actualizado
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        success = service.set_project_document_type(
            project_id=project_id,
            document_type=document_type,
            document_subtype=document_subtype,
            confirmed=True,
        )

        if not success:
            return ApiResponse(
                success=False,
                error=f"Tipo de documento inválido: {document_type}"
            )

        # Retornar el perfil actualizado
        doc_type = service.get_project_document_type(project_id)
        profile = service.get_project_profile(project_id)

        return ApiResponse(
            success=True,
            data={
                "document_type": doc_type,
                "feature_profile": profile.to_dict() if profile else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting document type for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/feature-profile", response_model=ApiResponse)
async def get_project_feature_profile(project_id: int):
    """
    Obtiene el perfil de features para un proyecto.

    Retorna qué features están habilitadas, opcionales o deshabilitadas
    según el tipo de documento del proyecto.

    Returns:
        ApiResponse con el perfil de features
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        profile = service.get_project_profile(project_id)

        if not profile:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        return ApiResponse(success=True, data=profile.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature profile for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/feature-availability/{feature}", response_model=ApiResponse)
async def get_feature_availability(project_id: int, feature: str):
    """
    Comprueba la disponibilidad de una feature específica.

    Args:
        project_id: ID del proyecto
        feature: Nombre de la feature (characters, timeline, scenes, etc.)

    Returns:
        ApiResponse con el nivel de disponibilidad (enabled, optional, disabled)
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        availability = service.get_feature_availability(project_id, feature)

        return ApiResponse(
            success=True,
            data={
                "feature": feature,
                "availability": availability,
                "is_enabled": availability == "enabled",
                "is_available": availability in ("enabled", "optional"),
            }
        )
    except Exception as e:
        logger.error(f"Error checking feature availability: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.post("/api/projects/{project_id}/detect-document-type", response_model=ApiResponse)
async def detect_document_type(project_id: int):
    """
    Detecta automáticamente el tipo de documento basándose en el contenido.

    No cambia el tipo actual, solo registra la sugerencia.

    Returns:
        ApiResponse con el tipo detectado y si hay discrepancia
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()

        # Detectar tipo
        detected = service.detect_document_type(project_id)
        if not detected:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Guardar detección
        service.set_detected_document_type(project_id, detected)

        # Obtener información actual para comparar
        current = service.get_project_document_type(project_id)

        return ApiResponse(
            success=True,
            data={
                "detected_type": detected,
                "detected_type_info": service.get_document_type_info(detected),
                "current_type": current["type"] if current else None,
                "has_mismatch": current and current["type"] != detected,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting document type: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Style Analysis Endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/sticky-sentences", response_model=ApiResponse)
async def get_sticky_sentences(
    project_id: int,
    threshold: float = Query(0.40, ge=0.0, le=1.0, description="Umbral de glue words (0.0-1.0)")
):
    """
    Analiza oraciones pesadas (sticky sentences) en el proyecto.

    Las oraciones pesadas son aquellas con alto porcentaje de palabras funcionales
    (artículos, preposiciones, conjunciones) que dificultan la lectura.
    """
    try:
        from narrative_assistant.nlp.style.sticky_sentences import get_sticky_sentence_detector
        from narrative_assistant.persistence import ProjectManager

        pm = ProjectManager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener texto de todos los capítulos
        chapters_data = []
        chapters = pm.get_chapters(project_id)

        detector = get_sticky_sentence_detector()
        global_sticky = []
        global_total_sentences = 0
        global_total_glue = 0
        by_severity = {"critical": 0, "high": 0, "medium": 0}

        for chapter in chapters:
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = detector.analyze(chapter_text, threshold=threshold)
            if result.is_failure:
                continue

            report = result.value
            chapter_sticky = []
            chapter_dist = {"clean": 0, "borderline": 0, "sticky": 0}
            chapter_severity = {"critical": 0, "high": 0, "medium": 0}

            for sent in report.sticky_sentences:
                severity = "medium"
                if sent.glue_percentage >= 0.55:
                    severity = "critical"
                    by_severity["critical"] += 1
                    chapter_severity["critical"] += 1
                elif sent.glue_percentage >= 0.50:
                    severity = "high"
                    by_severity["high"] += 1
                    chapter_severity["high"] += 1
                else:
                    by_severity["medium"] += 1
                    chapter_severity["medium"] += 1

                chapter_sticky.append({
                    "text": sent.text,
                    "glue_percentage": round(sent.glue_percentage * 100, 1),
                    "glue_percentage_display": f"{round(sent.glue_percentage * 100)}%",
                    "glue_words": sent.glue_word_count,
                    "total_words": sent.total_words,
                    "glue_word_list": sent.glue_words[:10],  # Limit to 10
                    "severity": severity,
                    "recommendation": _get_sticky_recommendation(sent.glue_percentage),
                })

            # Distribución de oraciones
            for _ in range(report.total_sentences - len(report.sticky_sentences)):
                chapter_dist["clean"] += 1
            for sent in report.sticky_sentences:
                if sent.glue_percentage >= threshold and sent.glue_percentage < threshold + 0.05:
                    chapter_dist["borderline"] += 1
                else:
                    chapter_dist["sticky"] += 1

            global_sticky.extend(chapter_sticky)
            global_total_sentences += report.total_sentences
            global_total_glue += sum(s["glue_percentage"] for s in chapter_sticky)

            chapters_data.append({
                "chapter_number": chapter.number,
                "chapter_title": chapter.title or f"Capítulo {chapter.number}",
                "sticky_sentences": chapter_sticky,
                "sticky_count": len(chapter_sticky),
                "total_sentences": report.total_sentences,
                "avg_glue_percentage": round(report.avg_glue_percentage * 100, 1) if report.avg_glue_percentage else 0,
                "distribution": chapter_dist,
                "by_severity": chapter_severity,
            })

        # Calcular estadísticas globales
        avg_glue = (global_total_glue / len(global_sticky)) if global_sticky else 0

        recommendations = []
        if by_severity["critical"] > 0:
            recommendations.append(f"Hay {by_severity['critical']} oraciones críticas (>55% glue words). Prioriza su revisión.")
        if len(global_sticky) > global_total_sentences * 0.2:
            recommendations.append("Más del 20% de las oraciones son pesadas. Considera simplificar el estilo.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_sticky_sentences": len(global_sticky),
                    "total_sentences": global_total_sentences,
                    "avg_glue_percentage": round(avg_glue, 1),
                    "by_severity": by_severity,
                },
                "chapters": chapters_data,
                "recommendations": recommendations,
                "threshold_used": threshold,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sticky sentences: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


def _get_sticky_recommendation(glue_percentage: float) -> str:
    """Genera recomendación según el porcentaje de glue words."""
    if glue_percentage >= 0.55:
        return "Esta oración es muy difícil de leer. Divídela en dos o elimina palabras innecesarias."
    elif glue_percentage >= 0.50:
        return "Oración pesada. Considera simplificar la estructura o usar verbos más directos."
    else:
        return "Revisa si puedes eliminar algún artículo, preposición o conjunción innecesaria."


@app.get("/api/projects/{project_id}/echo-report", response_model=ApiResponse)
async def get_echo_report(
    project_id: int,
    min_distance: int = Query(50, ge=10, le=500, description="Distancia mínima entre repeticiones"),
    include_semantic: bool = Query(False, description="Incluir repeticiones semánticas")
):
    """
    Analiza repeticiones (ecos) de palabras en el proyecto.

    Detecta palabras repetidas en proximidad que afectan la fluidez del texto.
    """
    try:
        from narrative_assistant.nlp.style.repetition_detector import get_repetition_detector
        from narrative_assistant.persistence import ProjectManager

        pm = ProjectManager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        detector = get_repetition_detector()
        chapters = pm.get_chapters(project_id)

        chapters_data = []
        global_repetitions = []
        global_word_counts = {}
        global_total_words = 0
        by_severity = {"high": 0, "medium": 0, "low": 0}

        for chapter in chapters:
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            # Análisis léxico
            result = detector.detect_lexical(chapter_text, min_distance=min_distance)
            if result.is_failure:
                continue

            report = result.value
            chapter_reps = []
            chapter_severity = {"high": 0, "medium": 0, "low": 0}

            for rep in report.repetitions:
                severity = "medium"
                if rep.min_distance < min_distance // 2:
                    severity = "high"
                    by_severity["high"] += 1
                    chapter_severity["high"] += 1
                else:
                    by_severity["medium"] += 1
                    chapter_severity["medium"] += 1

                # Agregar al conteo global
                word = rep.word.lower()
                global_word_counts[word] = global_word_counts.get(word, 0) + rep.count

                chapter_reps.append({
                    "word": rep.word,
                    "count": rep.count,
                    "min_distance": rep.min_distance,
                    "type": "lexical",
                    "severity": severity,
                    "occurrences": [
                        {"text": occ.context, "position": occ.position}
                        for occ in rep.occurrences[:5]
                    ],
                })

            # Análisis semántico si se solicita
            if include_semantic:
                sem_result = detector.detect_semantic(chapter_text, min_distance=min_distance * 2)
                if sem_result.is_success:
                    for rep in sem_result.value.repetitions:
                        chapter_reps.append({
                            "word": rep.word,
                            "count": rep.count,
                            "min_distance": rep.min_distance,
                            "type": "semantic",
                            "severity": "low",
                            "occurrences": [
                                {"text": occ.context, "position": occ.position}
                                for occ in rep.occurrences[:5]
                            ],
                        })
                        by_severity["low"] += 1
                        chapter_severity["low"] += 1

            global_repetitions.extend(chapter_reps)
            global_total_words += report.total_words

            chapters_data.append({
                "chapter_number": chapter.number,
                "chapter_title": chapter.title or f"Capítulo {chapter.number}",
                "repetitions": chapter_reps,
                "repetition_count": len(chapter_reps),
                "total_words": report.total_words,
                "by_severity": chapter_severity,
            })

        # Top palabras repetidas
        top_words = sorted(global_word_counts.items(), key=lambda x: x[1], reverse=True)[:20]

        recommendations = []
        if by_severity["high"] > 5:
            recommendations.append(f"Hay {by_severity['high']} repeticiones muy cercanas. Usa sinónimos o reestructura las oraciones.")
        if len(global_repetitions) > 50:
            recommendations.append("Texto con muchas repeticiones. Considera revisar el vocabulario.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_repetitions": len(global_repetitions),
                    "total_words": global_total_words,
                    "by_severity": by_severity,
                    "top_repeated_words": [{"word": w, "count": c} for w, c in top_words],
                },
                "chapters": chapters_data,
                "recommendations": recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing echo report: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/sentence-variation", response_model=ApiResponse)
async def get_sentence_variation(project_id: int):
    """
    Analiza la variación en la longitud de las oraciones.

    Proporciona métricas de legibilidad y distribución de oraciones.
    """
    try:
        from narrative_assistant.nlp.style.readability import get_readability_analyzer
        from narrative_assistant.persistence import ProjectManager

        pm = ProjectManager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        analyzer = get_readability_analyzer()
        chapters = pm.get_chapters(project_id)

        chapters_data = []
        global_stats = {
            "total_sentences": 0,
            "total_words": 0,
            "flesch_scores": [],
        }
        global_distribution = {"short": 0, "medium": 0, "long": 0, "very_long": 0}

        for chapter in chapters:
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = analyzer.analyze(chapter_text)
            if result.is_failure:
                continue

            report = result.value

            chapters_data.append({
                "chapter_number": chapter.number,
                "chapter_title": chapter.title or f"Capítulo {chapter.number}",
                "flesch_szigriszt": round(report.flesch_szigriszt, 1),
                "level": report.level.value,
                "level_description": report.level_description,
                "statistics": {
                    "total_sentences": report.total_sentences,
                    "total_words": report.total_words,
                    "avg_words_per_sentence": round(report.avg_words_per_sentence, 1),
                    "avg_syllables_per_word": round(report.avg_syllables_per_word, 2),
                },
                "distribution": {
                    "short": report.short_sentences,
                    "medium": report.medium_sentences,
                    "long": report.long_sentences,
                    "very_long": report.very_long_sentences,
                },
                "target_audience": report.target_audience,
            })

            global_stats["total_sentences"] += report.total_sentences
            global_stats["total_words"] += report.total_words
            global_stats["flesch_scores"].append(report.flesch_szigriszt)
            global_distribution["short"] += report.short_sentences
            global_distribution["medium"] += report.medium_sentences
            global_distribution["long"] += report.long_sentences
            global_distribution["very_long"] += report.very_long_sentences

        # Calcular promedios globales
        avg_flesch = sum(global_stats["flesch_scores"]) / len(global_stats["flesch_scores"]) if global_stats["flesch_scores"] else 0
        avg_wps = global_stats["total_words"] / global_stats["total_sentences"] if global_stats["total_sentences"] else 0

        recommendations = []
        if global_distribution["very_long"] > global_stats["total_sentences"] * 0.15:
            recommendations.append("Muchas oraciones muy largas (>35 palabras). Considera dividirlas.")
        if global_distribution["short"] > global_stats["total_sentences"] * 0.6:
            recommendations.append("Texto con predominio de oraciones cortas. Varía la longitud para mejor ritmo.")
        if avg_flesch < 40:
            recommendations.append("El texto es difícil de leer. Simplifica el vocabulario y la estructura.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "total_sentences": global_stats["total_sentences"],
                    "total_words": global_stats["total_words"],
                    "avg_words_per_sentence": round(avg_wps, 1),
                    "avg_flesch_szigriszt": round(avg_flesch, 1),
                },
                "distribution": global_distribution,
                "chapters": chapters_data,
                "recommendations": recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentence variation: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@app.get("/api/projects/{project_id}/pacing-analysis", response_model=ApiResponse)
async def get_pacing_analysis(project_id: int):
    """
    Analiza el ritmo narrativo del proyecto.

    Detecta variaciones en el pacing a través de capítulos/escenas.
    """
    try:
        from narrative_assistant.analysis.pacing import get_pacing_analyzer
        from narrative_assistant.persistence import ProjectManager

        pm = ProjectManager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        analyzer = get_pacing_analyzer()
        chapters = pm.get_chapters(project_id)

        chapters_data = []

        for chapter in chapters:
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            result = analyzer.analyze(chapter_text)
            if result.is_failure:
                continue

            report = result.value

            chapters_data.append({
                "chapter_number": chapter.number,
                "chapter_title": chapter.title or f"Capítulo {chapter.number}",
                "pacing_score": round(report.overall_pacing, 2),
                "pacing_label": _get_pacing_label(report.overall_pacing),
                "metrics": {
                    "dialogue_ratio": round(report.dialogue_ratio, 3),
                    "action_ratio": round(report.action_ratio, 3),
                    "description_ratio": round(report.description_ratio, 3),
                    "avg_sentence_length": round(report.avg_sentence_length, 1),
                },
                "segments": [
                    {
                        "type": seg.segment_type.value,
                        "start": seg.start_position,
                        "end": seg.end_position,
                        "pacing": round(seg.pacing_score, 2),
                    }
                    for seg in report.segments[:20]  # Limit segments
                ],
            })

        # Calcular variación de pacing
        pacing_scores = [ch["pacing_score"] for ch in chapters_data]
        pacing_variation = max(pacing_scores) - min(pacing_scores) if pacing_scores else 0

        recommendations = []
        if pacing_variation < 0.2:
            recommendations.append("El ritmo es muy uniforme. Considera variar entre escenas de acción y reflexión.")
        if all(ch["pacing_score"] < 0.4 for ch in chapters_data):
            recommendations.append("El ritmo general es lento. Añade más diálogo o escenas de acción.")
        if all(ch["pacing_score"] > 0.7 for ch in chapters_data):
            recommendations.append("El ritmo es muy acelerado. Incluye momentos de pausa para el lector.")

        return ApiResponse(
            success=True,
            data={
                "global_stats": {
                    "avg_pacing": round(sum(pacing_scores) / len(pacing_scores), 2) if pacing_scores else 0,
                    "pacing_variation": round(pacing_variation, 2),
                    "chapter_count": len(chapters_data),
                },
                "chapters": chapters_data,
                "recommendations": recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing pacing: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


def _get_pacing_label(score: float) -> str:
    """Obtiene etiqueta de pacing según puntuación."""
    if score >= 0.7:
        return "fast"
    elif score >= 0.4:
        return "moderate"
    else:
        return "slow"


@app.get("/api/projects/{project_id}/age-readability", response_model=ApiResponse)
async def get_age_readability(
    project_id: int,
    target_age_group: Optional[str] = Query(None, description="Grupo de edad objetivo (board_book, picture_book, early_reader, chapter_book, middle_grade, young_adult)")
):
    """
    Analiza la legibilidad orientada a grupos de edad infantil/juvenil.

    Proporciona métricas específicas para literatura infantil como:
    - Proporción de palabras de alta frecuencia (sight words)
    - Complejidad del vocabulario
    - Estimación de edad lectora
    """
    try:
        from narrative_assistant.nlp.style.readability import get_readability_analyzer, AgeGroup
        from narrative_assistant.persistence import ProjectManager

        pm = ProjectManager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        analyzer = get_readability_analyzer()
        chapters = pm.get_chapters(project_id)

        # Parsear grupo de edad objetivo
        target_group = None
        if target_age_group:
            try:
                target_group = AgeGroup(target_age_group)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Grupo de edad inválido: {target_age_group}. Valores válidos: board_book, picture_book, early_reader, chapter_book, middle_grade, young_adult"
                )

        # Combinar todo el texto para análisis global
        full_text = "\n\n".join(ch.content or "" for ch in chapters if ch.content)

        if not full_text.strip():
            return ApiResponse(
                success=True,
                data={
                    "message": "No hay contenido para analizar",
                    "estimated_age_group": None,
                }
            )

        result = analyzer.analyze_for_age(full_text, target_age_group=target_group)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        report = result.value

        # Análisis por capítulo
        chapters_data = []
        for chapter in chapters:
            chapter_text = chapter.content or ""
            if not chapter_text.strip():
                continue

            ch_result = analyzer.analyze_for_age(chapter_text, target_age_group=target_group)
            if ch_result.is_success:
                ch_report = ch_result.value
                chapters_data.append({
                    "chapter_number": chapter.number,
                    "chapter_title": chapter.title or f"Capítulo {chapter.number}",
                    "estimated_age_group": ch_report.estimated_age_group.value,
                    "estimated_age_range": ch_report.estimated_age_range,
                    "appropriateness_score": round(ch_report.appropriateness_score, 1),
                    "is_appropriate": ch_report.is_appropriate,
                    "metrics": {
                        "avg_words_per_sentence": round(ch_report.avg_words_per_sentence, 1),
                        "avg_syllables_per_word": round(ch_report.avg_syllables_per_word, 2),
                        "sight_word_ratio": round(ch_report.sight_word_ratio * 100, 1),
                    },
                })

        return ApiResponse(
            success=True,
            data={
                **report.to_dict(),
                "chapters": chapters_data,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing age readability: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys
    import uvicorn
    import traceback
    
    # Fix para PyInstaller: DEBE ir ANTES de cualquier otra cosa
    # Asegurar que stdout/stderr/stdin existen y tienen isatty()
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
        logger.info(f"Starting Narrative Assistant API Server v{NA_VERSION}")
        logger.info("Server will be available at http://localhost:8008")

        # Detectar si estamos en un ejecutable empaquetado
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            # Modo empaquetado: deshabilitar reload y usar configuración simplificada
            uvicorn.run(
                app,  # Usar la instancia directa, no el string
                host="127.0.0.1",
                port=8008,
                reload=False,
                log_level="info",
                access_log=True,
            )
        else:
            # Modo desarrollo: también usar instancia directa para compatibilidad con Python embebido
            uvicorn.run(
                app,  # Usar instancia directa, no "main:app" string
                host="127.0.0.1",
                port=8008,
                reload=False,  # Disabled for embedded Python and auto-reload compatibility
                log_level="info",
            )
    except Exception as e:
        # En modo empaquetado, mostrar el error
        error_msg = f"\n\n===== ERROR FATAL =====\n"
        error_msg += f"Error type: {type(e).__name__}\n"
        error_msg += f"Error message: {e}\n"
        error_msg += f"\nTraceback:\n"
        
        print(error_msg, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Escribir a archivo de log
        try:
            log_dir = get_log_directory()
            log_dir.mkdir(parents=True, exist_ok=True)
            error_file = log_dir / "startup_error.log"
            
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(error_msg)
                traceback.print_exc(file=f)
            
            print(f"\nError guardado en: {error_file}", file=sys.stderr)
        except:
            pass
        
        # Esperar solo si hay stdin disponible
        if sys.stdin and hasattr(sys.stdin, 'read'):
            try:
                print("\nPresiona Enter para cerrar...", file=sys.stderr)
                input()
            except:
                pass
        
        sys.exit(1)
