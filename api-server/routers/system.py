"""
Router: system
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import deps
from deps import (
    ApiResponse,
    ChangeDataLocationRequest,
    DownloadModelsRequest,
    HealthResponse,
    _check_languagetool_available,
    get_python_status,
    logger,
)
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint - verifica que el servidor está funcionando.

    Returns:
        HealthResponse con status del sistema
    """
    return HealthResponse(
        status="ok",
        version=deps.NA_VERSION,
        backend_loaded=deps.MODULES_LOADED,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/api/info")
async def system_info():
    """
    Información del sistema - configuración, GPU, modelos, etc.

    Returns:
        Información detallada del sistema
    """
    if not deps.MODULES_LOADED:
        return ApiResponse(
            success=False,
            message="NLP modules not loaded. Please install dependencies.",
            data={
                "version": deps.NA_VERSION,
                "backend_loaded": False,
                "error": deps.MODULES_ERROR,
            }
        )

    try:
        config = deps.get_config()

        # Usar detección real de GPU (no solo config)
        gpu_available = False
        gpu_device_str = "cpu"
        try:
            from narrative_assistant.core.device import DeviceType, get_device_detector
            detector = get_device_detector()
            device = detector.detect_best_device()
            gpu_available = device.device_type in (DeviceType.CUDA, DeviceType.MPS)
            gpu_device_str = device.device_type.name.lower()
        except Exception:
            pass

        return ApiResponse(
            success=True,
            data={
                "version": deps.NA_VERSION,
                "gpu": {
                    "device": gpu_device_str,
                    "available": gpu_available,
                    "spacy_gpu": config.gpu.spacy_gpu_enabled and gpu_available,
                    "embeddings_gpu": config.gpu.embeddings_gpu_enabled and gpu_available,
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


@router.get("/api/debug/diagnostic")
async def debug_diagnostic():
    """
    Diagnóstico detallado del backend - para debugging de problemas.
    Devuelve el estado completo del sistema, paths, DB, módulos.
    """

    diag = {
        "version": deps.BACKEND_VERSION,
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "frozen": getattr(sys, 'frozen', False),
            "is_embedded": deps.IS_EMBEDDED_RUNTIME,
            "platform": sys.platform,
        },
        "environment": {
            "NA_EMBEDDED": os.environ.get("NA_EMBEDDED"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "PYTHONHOME": os.environ.get("PYTHONHOME"),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA"),
        },
        "sys_path_first_10": sys.path[:10],
        "modules": {
            "loaded": deps.MODULES_LOADED,
            "error": deps.MODULES_ERROR,
            "project_manager": deps.project_manager is not None,
            "entity_repository": deps.entity_repository is not None,
            "alert_repository": deps.alert_repository is not None,
            "chapter_repository": deps.chapter_repository is not None,
            "get_database": deps.get_database is not None,
        },
        "database": {},
        "log_file": str(deps._log_file) if deps._log_file else None,
    }

    # deps.Database diagnostics
    try:
        if deps.get_database:
            db = deps.get_database()
            diag["database"]["path"] = str(db.db_path)
            diag["database"]["exists"] = db.db_path.exists() if hasattr(db.db_path, 'exists') else "N/A"
            tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            diag["database"]["tables"] = [t['name'] for t in tables]
            diag["database"]["has_projects_table"] = 'projects' in diag["database"]["tables"]
        else:
            diag["database"]["error"] = "get_database is None"
    except Exception as e:
        diag["database"]["error"] = f"{type(e).__name__}: {e}"

    # Check key packages availability
    packages = ["numpy", "spacy", "sentence_transformers", "torch", "fastapi", "uvicorn", "sqlite3"]
    diag["packages"] = {}
    for pkg in packages:
        try:
            __import__(pkg)
            diag["packages"][pkg] = "available"
        except ImportError:
            diag["packages"][pkg] = "NOT INSTALLED"

    return ApiResponse(success=True, data=diag)


@router.get("/api/debug/log")
async def debug_log():
    """
    Devuelve el contenido del archivo de log del backend.
    El usuario puede compartir esto para diagnosticar problemas.
    """
    log_content = ""
    early_debug_content = ""

    # Read backend-debug.log
    if deps._log_file and Path(deps._log_file).exists():
        try:
            log_content = Path(deps._log_file).read_text(encoding='utf-8', errors='replace')
            # Limit to last 500 lines
            lines = log_content.split('\n')
            if len(lines) > 500:
                log_content = '\n'.join(lines[-500:])
        except Exception as e:
            log_content = f"Error reading log: {e}"

    # Read early-debug.txt
    localappdata = os.environ.get('LOCALAPPDATA', '')
    if localappdata:
        early_debug_path = Path(localappdata) / "Narrative Assistant" / "early-debug.txt"
        if early_debug_path.exists():
            try:
                early_debug_content = early_debug_path.read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                early_debug_content = f"Error reading early debug: {e}"

    return ApiResponse(success=True, data={
        "log_file": str(deps._log_file) if deps._log_file else None,
        "log_content": log_content,
        "early_debug_content": early_debug_content,
    })


# Frontend log file (same directory as backend-debug.log)
_frontend_log_file: Path | None = None
_frontend_logger = None

def _get_frontend_logger():
    """Lazy-init frontend file logger."""
    global _frontend_log_file, _frontend_logger
    if _frontend_logger is not None:
        return _frontend_logger

    import logging as _logging

    _frontend_logger = _logging.getLogger("narrative_assistant.frontend")
    _frontend_logger.setLevel(_logging.DEBUG)
    _frontend_logger.propagate = False

    try:
        if sys.platform == 'win32':
            log_dir = Path.home() / "AppData" / "Local" / "Narrative Assistant"
        elif sys.platform == 'darwin':
            log_dir = Path.home() / "Library" / "Logs" / "Narrative Assistant"
        else:
            log_dir = Path.home() / ".local" / "share" / "narrative-assistant"

        log_dir.mkdir(parents=True, exist_ok=True)
        _frontend_log_file = log_dir / "frontend.log"

        handler = _logging.FileHandler(str(_frontend_log_file), encoding='utf-8', mode='a')
        handler.setFormatter(_logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        _frontend_logger.addHandler(handler)
    except Exception:
        pass

    return _frontend_logger


@router.post("/api/logs/frontend")
async def receive_frontend_logs(request: Request):
    """
    Recibe logs del frontend y los escribe en frontend.log.
    El frontend envía batches de mensajes para minimizar requests.
    """
    try:
        body = await request.json()
        entries = body.get("entries", [])
        if not entries or not isinstance(entries, list):
            return ApiResponse(success=True, data={"written": 0})

        fl = _get_frontend_logger()
        written = 0
        for entry in entries[:200]:  # Max 200 entries per batch
            level = entry.get("level", "info").upper()
            msg = entry.get("message", "")
            tag = entry.get("tag", "")
            if not msg:
                continue
            prefix = f"[{tag}] " if tag else ""
            log_msg = f"{prefix}{msg}"

            if level == "ERROR":
                fl.error(log_msg)
            elif level == "WARN":
                fl.warning(log_msg)
            elif level == "DEBUG":
                fl.debug(log_msg)
            else:
                fl.info(log_msg)
            written += 1

        return ApiResponse(success=True, data={"written": written})
    except Exception as e:
        logger.debug(f"Error receiving frontend logs: {e}")
        return ApiResponse(success=True, data={"written": 0})


@router.get("/api/debug/frontend-log")
async def debug_frontend_log():
    """Devuelve el contenido del log del frontend."""
    _get_frontend_logger()  # Ensure file path is set
    content = ""
    if _frontend_log_file and _frontend_log_file.exists():
        try:
            content = _frontend_log_file.read_text(encoding='utf-8', errors='replace')
            lines = content.split('\n')
            if len(lines) > 500:
                content = '\n'.join(lines[-500:])
        except Exception as e:
            content = f"Error reading frontend log: {e}"

    return ApiResponse(success=True, data={
        "log_file": str(_frontend_log_file) if _frontend_log_file else None,
        "log_content": content,
    })


@router.get("/api/system/python-status")
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


@router.get("/api/models/status")
async def models_status():
    """
    Verifica el estado de los modelos NLP necesarios.

    Returns:
        ApiResponse con estado de cada modelo (instalado, tamaño, ruta)
    """
    # Obtener estado de Python del sistema
    python_info = get_python_status()

    # Si los módulos no están cargados, retornar estado de dependencias
    if not deps.MODULES_LOADED:
        import importlib.util

        # Log sys.path para debugging
        logger.info("=== Checking dependencies ===")
        logger.info(f"MODULES_LOADED: {deps.MODULES_LOADED}")
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
            deps._write_debug("All dependencies detected in frozen mode - restart required to load backend")
            needs_restart = True

        # Si después de intentar cargar, aún no están cargados, retornar estado de dependencias
        if not deps.MODULES_LOADED:
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
                    "installing": deps.INSTALLING_DEPENDENCIES,
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
                    encoding="utf-8",
                    errors="replace",
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
                "backend_loaded": True,
                "dependencies_needed": False,
                "nlp_models": status,
                "ollama": {
                    "installed": ollama_installed,
                    "models": ollama_models,
                },
                "all_required_installed": all(
                    info.get("installed", False)
                    for info in status.values()
                    if info.get("required", True)
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


@router.post("/api/dependencies/install")
async def install_dependencies():
    """
    Instala las dependencias Python necesarias (numpy, spacy, sentence-transformers, etc.).

    Este endpoint instala las dependencias y luego intenta recargar los módulos.
    NO requiere reinicio manual de la aplicación.

    Returns:
        ApiResponse indicando que la instalación ha comenzado
    """
    import importlib
    import subprocess

    # Verificar que Python está disponible antes de intentar instalar
    python_info = get_python_status()
    if not python_info["python_available"]:
        raise HTTPException(
            status_code=400,
            detail=python_info["error"] or f"Python {deps.MIN_PYTHON_VERSION[0]}.{deps.MIN_PYTHON_VERSION[1]}+ no encontrado. Por favor instala Python desde python.org"
        )

    def install_task():
        # Globals managed via deps module
        deps.INSTALLING_DEPENDENCIES = True

        try:
            # Usar el path de Python ya verificado
            python_exe = python_info["python_path"]
            logger.info(f"Starting dependencies installation using: {python_exe} (version {python_info['python_version']})")

            # Lista de dependencias necesarias
            # sentence-transformers ya trae torch, transformers y scikit-learn como dependencias
            # No instalar paquetes redundantes - reduce el tiempo de instalación significativamente
            dependencies = [
                "numpy>=1.24.0",
                "spacy>=3.7.0",
                "sentence-transformers>=2.2.0",
            ]

            # Configurar subprocess para no mostrar ventana en Windows
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NO_WINDOW

            # Determinar argumentos de instalación según el entorno
            pip_install_args = []
            if deps.IS_EMBEDDED_RUNTIME:
                # En Python embebido, --user no funciona (ENABLE_USER_SITE=False).
                # Instalar directamente en el site-packages del Python embebido.
                embed_site_packages = os.path.join(os.path.dirname(python_exe), "Lib", "site-packages")
                pip_install_args.extend(["--target", embed_site_packages])
                logger.info(f"Installing to embedded site-packages: {embed_site_packages}")
            else:
                pip_install_args.append("--user")

            for dep in dependencies:
                logger.info(f"Installing {dep}...")
                result = subprocess.run(
                    [python_exe, "-m", "pip", "install"] + pip_install_args + [dep],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=creation_flags
                )
                if result.returncode != 0:
                    logger.error(f"Failed to install {dep}: {result.stderr}")
                    raise Exception(f"Failed to install {dep}: {result.stderr}")
                logger.info(f"✓ {dep} installed")

            logger.info("All dependencies installed successfully!")

            # Ensure target dir is in sys.path for imports
            if deps.IS_EMBEDDED_RUNTIME and embed_site_packages not in sys.path:
                sys.path.insert(0, embed_site_packages)
                logger.info(f"Added {embed_site_packages} to sys.path")

            # Invalidate import caches so newly installed packages are found
            importlib.invalidate_caches()

            logger.info("Attempting to load narrative_assistant modules...")

            # Usar la función helper para cargar los módulos
            if deps.load_narrative_assistant_modules():
                deps.INSTALLING_DEPENDENCIES = False
                logger.info("✓ Modules loaded successfully! Backend is now fully functional.")
            else:
                logger.error("Failed to load modules after installation")
                logger.info("You may need to restart the application.")
                raise Exception("Failed to load narrative_assistant modules after installation")

        except Exception as e:
            logger.error(f"Error installing dependencies: {e}", exc_info=True)
            deps.INSTALLING_DEPENDENCIES = False
            deps.MODULES_ERROR = str(e)

    # Ejecutar en segundo plano
    import threading
    thread = threading.Thread(target=install_task, daemon=True)
    thread.start()

    return ApiResponse(
        success=True,
        message="Dependencies installation started. This may take several minutes. Check /api/models/status for progress.",
        data={"installing": True}
    )


@router.post("/api/models/download")
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
    if not deps.MODULES_LOADED:
        raise HTTPException(
            status_code=400,
            detail="Dependencies not installed. Please install dependencies first via /api/dependencies/install"
        )

    try:
        import threading

        from narrative_assistant.core.model_manager import ModelType, get_model_manager

        manager = get_model_manager()

        MODEL_TYPE_MAP = {
            "spacy": ModelType.SPACY,
            "embeddings": ModelType.EMBEDDINGS,
            "transformer_ner": ModelType.TRANSFORMER_NER,
        }

        def download_task():
            from concurrent.futures import ThreadPoolExecutor, as_completed

            from narrative_assistant.core.model_manager import (
                _clear_download_progress,
                _update_download_progress,
            )

            models_to_download = []
            for model_name in request.models:
                mt = MODEL_TYPE_MAP.get(model_name)
                if mt:
                    models_to_download.append((model_name, mt))
                    # Clear stale progress from previous attempts
                    _clear_download_progress(mt)

            # Descargas paralelas: spaCy (GitHub CDN) + HF model en paralelo
            # Máximo 2 workers para no saturar red ni RAM
            def _download_one(name_and_type):
                name, mt = name_and_type
                try:
                    result = manager.ensure_model(mt, force_download=request.force)
                    if result.is_success:
                        logger.info(f"Model {name} downloaded successfully")
                        # Mark completed in progress tracker (ensure_model
                        # doesn't update progress when model is found locally)
                        _update_download_progress(mt, phase="completed")
                    else:
                        logger.error(f"Model {name} download failed: {result.error}")
                        _update_download_progress(
                            mt, phase="error",
                            error_message=str(result.error),
                        )
                except Exception as e:
                    logger.error(f"Error downloading {name}: {e}")
                    _update_download_progress(
                        mt, phase="error", error_message=str(e),
                    )

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(_download_one, item): item[0] for item in models_to_download}
                for future in as_completed(futures):
                    model_name = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Download thread error for {model_name}: {e}")

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


@router.get("/api/models/download/progress")
async def download_progress():
    """
    Obtiene el progreso de las descargas de modelos activas.

    Retorna información detallada sobre cada descarga en curso:
    - Fase actual (connecting, downloading, installing, completed, error)
    - Bytes descargados y total
    - Porcentaje de progreso
    - Velocidad de descarga en MB/s
    - Tiempo estimado restante

    Returns:
        ApiResponse con estado de progreso de cada modelo
    """
    if not deps.MODULES_LOADED:
        return ApiResponse(
            success=True,
            data={
                "active_downloads": {},
                "has_active": False,
            }
        )

    try:
        from narrative_assistant.core.model_manager import (
            KNOWN_MODELS,
            get_download_progress,
            get_real_model_sizes,
        )

        progress = get_download_progress()
        has_active = any(
            p.get("phase") not in ("completed", "error", None)
            for p in progress.values()
        ) if progress else False

        # Obtener tamaños reales de modelos
        try:
            real_sizes = get_real_model_sizes()
        except Exception:
            real_sizes = {}
            for mt, mi in KNOWN_MODELS.items():
                real_sizes[mt.value] = mi.size_mb * 1024 * 1024

        return ApiResponse(
            success=True,
            data={
                "active_downloads": progress or {},
                "has_active": has_active,
                "model_sizes": {
                    **dict(real_sizes.items()),
                    "total": sum(real_sizes.values()),
                },
            }
        )
    except ImportError:
        return ApiResponse(
            success=True,
            data={
                "active_downloads": {},
                "has_active": False,
            }
        )
    except Exception as e:
        logger.error(f"Error getting download progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/system/capabilities")
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
        from narrative_assistant.core.device import (
            get_blocked_gpu_info,
            get_device_detector,
        )

        detector = get_device_detector()

        # Detectar dispositivos disponibles
        cuda_device = detector.detect_cuda()
        mps_device = detector.detect_mps()
        cpu_device = detector.get_cpu_info()
        has_cupy = detector.detect_cupy() if cuda_device else False

        # Info de GPU bloqueada por CC < 6.0 (prevención de BSOD)
        blocked_gpu = get_blocked_gpu_info()

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
        import json as json_module
        import urllib.error
        import urllib.request
        try:
            ollama_host = "http://localhost:11434"
            logger.info(f"Verificando Ollama en {ollama_host}/api/tags...")
            req = urllib.request.Request(f"{ollama_host}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as response:  # Reduced from 10s
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
        lt_installed = False
        lt_installing = False
        lt_java_available = False
        try:
            from narrative_assistant.nlp.grammar.languagetool_manager import (
                get_languagetool_manager as _get_lt_mgr,
            )
            from narrative_assistant.nlp.grammar.languagetool_manager import (
                is_lt_installing as _is_lt_installing,
            )
            _lt_mgr = _get_lt_mgr()
            lt_installed = _lt_mgr.is_installed
            lt_installing = _is_lt_installing()
            lt_java_available = _lt_mgr._get_java_command() is not None
        except Exception:
            pass

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
                    "gpu_blocked": blocked_gpu,  # None o {name, compute_capability, min_required}
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
                "languagetool": {
                    "installed": lt_installed,
                    "running": lt_available,
                    "installing": lt_installing,
                    "java_available": lt_java_available,
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


@router.post("/api/system/database/repair", response_model=ApiResponse)
async def repair_database_endpoint():
    """
    Intenta reparar la base de datos sin perder datos.

    Pasos de reparación:
    1. Verifica integridad con PRAGMA integrity_check
    2. Ejecuta VACUUM si hay problemas
    3. Crea tablas faltantes si es necesario

    Returns:
        ApiResponse con resultado de la reparación
    """
    try:
        from narrative_assistant.persistence import repair_database

        success, message = repair_database()

        return ApiResponse(
            success=success,
            message=message,
            data={"repaired": success}
        )
    except Exception as e:
        logger.error(f"Error reparando base de datos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system/database/reset", response_model=ApiResponse)
async def reset_database_endpoint():
    """
    Elimina y recrea la base de datos desde cero.

    ¡CUIDADO! Esta operación elimina TODOS los datos.
    Usar solo si repair no funciona.

    Returns:
        ApiResponse confirmando la operación
    """
    try:
        from narrative_assistant.persistence import delete_and_recreate_database

        delete_and_recreate_database()

        return ApiResponse(
            success=True,
            message="Base de datos eliminada y recreada desde cero",
            data={"reset": True}
        )
    except Exception as e:
        logger.error(f"Error reseteando base de datos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/maintenance/clear-cache", response_model=ApiResponse)
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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/maintenance/data-location", response_model=ApiResponse)
async def get_data_location():
    """
    Obtiene la ubicación actual de almacenamiento de datos.

    Returns:
        ApiResponse con la ruta del directorio de datos
    """
    try:
        if deps.get_config:
            config = deps.get_config()
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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/system/resources", response_model=ApiResponse)
async def get_resource_status():
    """
    Estado del gestor de recursos del sistema.

    Retorna información detallada sobre:
    - Capacidades del sistema (CPU, RAM, GPU, tier)
    - Recomendaciones de configuración según recursos
    - Tareas pesadas en ejecución
    - Configuración de análisis semántico

    Returns:
        ApiResponse con estado completo de recursos
    """
    try:
        from narrative_assistant.core import get_config, get_resource_manager

        rm = get_resource_manager()
        config = get_config()

        # Refrescar capacidades
        capabilities = rm.refresh_capabilities()

        return ApiResponse(
            success=True,
            data={
                "capabilities": {
                    "cpu_cores_logical": capabilities.cpu_cores_logical,
                    "cpu_cores_physical": capabilities.cpu_cores_physical,
                    "ram_total_mb": capabilities.ram_total_mb,
                    "ram_available_mb": capabilities.ram_available_mb,
                    "gpu_available": capabilities.gpu_available,
                    "gpu_vram_total_mb": capabilities.gpu_vram_total_mb,
                    "gpu_is_low_vram": capabilities.gpu_is_low_vram,
                    "tier": capabilities.tier.value,
                },
                "recommendation": {
                    "max_workers": rm.recommendation.max_workers,
                    "batch_size_embeddings": rm.recommendation.batch_size_embeddings,
                    "use_gpu_for_embeddings": rm.recommendation.use_gpu_for_embeddings,
                    "enable_semantic_redundancy": rm.recommendation.enable_semantic_redundancy,
                    "max_concurrent_heavy_tasks": rm.recommendation.max_concurrent_heavy_tasks,
                },
                "heavy_tasks": {
                    "running": list(rm._running_tasks),
                    "semaphore_available": rm._heavy_task_semaphore.available,
                    "semaphore_max": rm.recommendation.max_concurrent_heavy_tasks,
                },
                "semantic_redundancy": {
                    "enabled": config.nlp.semantic_redundancy_enabled,
                    "threshold": config.nlp.semantic_redundancy_threshold,
                    "mode": config.nlp.semantic_redundancy_mode,
                },
            }
        )
    except ImportError as e:
        logger.warning(f"ResourceManager not available: {e}")
        return ApiResponse(
            success=True,
            data={
                "capabilities": None,
                "recommendation": None,
                "message": "ResourceManager not available",
            }
        )
    except Exception as e:
        logger.error(f"Error getting resource status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/maintenance/data-location", response_model=ApiResponse)
async def change_data_location(request: ChangeDataLocationRequest):
    """
    Cambia la ubicación de almacenamiento de datos.

    Args:
        request: Nueva ruta y opciones de migración

    Returns:
        ApiResponse con el resultado de la operación
    """
    import os
    import shutil

    try:
        new_path = Path(request.new_path).expanduser().resolve()

        # Bloquear path traversal: rechazar rutas con ".."
        if ".." in request.new_path:
            return ApiResponse(
                success=False,
                error="Ruta no permitida: contiene componentes de path traversal"
            )

        # Bloquear directorios de sistema sensibles
        _blocked = [Path("/etc"), Path("/usr"), Path("/bin"), Path("C:/Windows"), Path("C:/Program Files")]
        if any(str(new_path).startswith(str(b)) for b in _blocked):
            return ApiResponse(
                success=False,
                error="No se puede usar un directorio de sistema como ubicación de datos"
            )

        # Validar que la ruta sea válida
        if not new_path.parent.exists():
            return ApiResponse(
                success=False,
                error=f"El directorio padre no existe: {new_path.parent}"
            )

        # Obtener la ubicación actual
        if deps.get_config:
            config = deps.get_config()
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
        return ApiResponse(success=False, error="Error interno del servidor")
