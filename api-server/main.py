"""
FastAPI Server Bridge - Servidor HTTP para comunicación con Tauri frontend.

Este servidor actúa como puente entre el frontend Tauri (Vue 3) y el backend
Python (narrative_assistant). Proporciona endpoints REST para todas las
operaciones del sistema.

Puerto: 8008
CORS: Habilitado para localhost:5173 (Vite dev server) y tauri://localhost
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Imports del backend narrative_assistant
project_manager = None
entity_repository = None
alert_repository = None
chapter_repository = None
section_repository = None
get_config = None
NA_VERSION = "unknown"

try:
    from narrative_assistant.persistence.project import ProjectManager
    from narrative_assistant.persistence.database import get_database, Database
    from narrative_assistant.persistence.chapter import ChapterRepository, SectionRepository
    from narrative_assistant.entities.repository import EntityRepository
    from narrative_assistant.alerts.repository import AlertRepository, AlertStatus, AlertSeverity
    from narrative_assistant.core.config import get_config
    from narrative_assistant import __version__ as NA_VERSION

    # Inicializar managers
    project_manager = ProjectManager()
    entity_repository = EntityRepository()
    alert_repository = AlertRepository()
    chapter_repository = ChapterRepository()
    section_repository = SectionRepository()
except Exception as e:
    logging.error(f"Error initializing narrative_assistant modules: {type(e).__name__}: {e}")
    NA_VERSION = "unknown"
    project_manager = None
    entity_repository = None
    alert_repository = None
    chapter_repository = None
    section_repository = None
    get_config = None
    Database = None  # type: ignore

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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
    backend_loaded = False
    try:
        # Intentar cargar config para verificar backend
        config = get_config()
        backend_loaded = config is not None
    except Exception as e:
        logger.warning(f"Backend not fully loaded: {e}")

    return HealthResponse(
        status="ok",
        version=NA_VERSION,
        backend_loaded=backend_loaded,
        timestamp=datetime.now().isoformat(),
    )

@app.get("/api/info")
async def system_info():
    """
    Información del sistema - configuración, GPU, modelos, etc.

    Returns:
        Información detallada del sistema
    """
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


@app.get("/api/models/status")
async def models_status():
    """
    Verifica el estado de los modelos NLP necesarios.

    Returns:
        ApiResponse con estado de cada modelo (instalado, tamaño, ruta)
    """
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

    except ImportError:
        raise HTTPException(status_code=500, detail="Model manager not available")
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
            return ApiResponse(success=False, error="Project manager not initialized")

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
            "voice_profiles": False,  # Por implementar
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
            document_text = raw_doc.text if hasattr(raw_doc, 'text') else str(raw_doc)

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
                raise HTTPException(status_code=500, detail=f"Error creando proyecto: {create_result.error}")

            project = create_result.value

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
        entity_repo = entity_repository
        from narrative_assistant.persistence.chapter import get_chapter_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

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

        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

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
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        entity_name = entity.canonical_name

        # Eliminar o desactivar la entidad
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
        entity_repo = entity_repository

        # Verificar que la entidad existe y pertenece al proyecto
        entity = entity_repo.get_entity(entity_id)
        if not entity or entity.project_id != project_id:
            return ApiResponse(success=False, error="Entidad no encontrada")

        # Obtener menciones de la entidad
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

        # Filtrar menciones solapadas (mantener la más larga si hay solapamiento)
        # Esto evita que "María" y "María Sánchez" en la misma posición se muestren ambas
        filtered_mentions = []
        for mention in mentions_data:
            # Verificar si esta mención se solapa con alguna ya añadida
            is_overlapping = False
            for existing in filtered_mentions:
                # Mismo capítulo y posiciones que se solapan
                if existing["chapterNumber"] == mention["chapterNumber"]:
                    # Verificar solapamiento: [start1, end1] vs [start2, end2]
                    if not (mention["endChar"] <= existing["startChar"] or
                            existing["endChar"] <= mention["startChar"]):
                        is_overlapping = True
                        # Si la nueva es más larga, reemplazar
                        if (mention["endChar"] - mention["startChar"]) > (existing["endChar"] - existing["startChar"]):
                            filtered_mentions.remove(existing)
                            filtered_mentions.append(mention)
                        break

            if not is_overlapping:
                filtered_mentions.append(mention)

        # Re-ordenar después de filtrar
        filtered_mentions.sort(key=lambda m: (m["chapterNumber"] or 0, m["startChar"]))

        return ApiResponse(success=True, data={
            "mentions": filtered_mentions,
            "total": len(filtered_mentions),
            "entityName": entity.canonical_name,
            "entityType": entity.entity_type.value if entity.entity_type else None,
        })

    except Exception as e:
        logger.error(f"Error getting mentions for entity {entity_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


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
            )
            for a in alerts
        ]

        return ApiResponse(success=True, data=alerts_data)
    except Exception as e:
        logger.error(f"Error listing alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/{alert_id}/resolve", response_model=ApiResponse)
async def resolve_alert(project_id: int, alert_id: int):
    """
    Marca una alerta como resuelta.
    """
    try:
        alert_repo = alert_repository
        result = alert_repo.get(alert_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        alert = result.value
        if alert.project_id != project_id:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        # Actualizar el status de la alerta
        alert.status = AlertStatus.RESOLVED
        alert_repo.update(alert)

        logger.info(f"Alert {alert_id} marked as resolved")

        return ApiResponse(
            success=True,
            message="Alerta marcada como resuelta"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/{alert_id}/dismiss", response_model=ApiResponse)
async def dismiss_alert(project_id: int, alert_id: int):
    """
    Descarta una alerta.
    """
    try:
        alert_repo = alert_repository
        result = alert_repo.get(alert_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        alert = result.value
        if alert.project_id != project_id:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        # Actualizar el status de la alerta
        alert.status = AlertStatus.DISMISSED
        alert_repo.update(alert)

        logger.info(f"Alert {alert_id} dismissed")

        return ApiResponse(
            success=True,
            message="Alerta descartada"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing alert {alert_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

@app.post("/api/projects/{project_id}/alerts/{alert_id}/reopen", response_model=ApiResponse)
async def reopen_alert(project_id: int, alert_id: int):
    """
    Reabre una alerta previamente resuelta o descartada.
    """
    try:
        alert_repo = alert_repository
        result = alert_repo.get(alert_id)

        if result.is_failure:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        alert = result.value
        if alert.project_id != project_id:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        # Actualizar el status de la alerta
        alert.status = AlertStatus.OPEN
        alert_repo.update(alert)

        logger.info(f"Alert {alert_id} reopened")

        return ApiResponse(
            success=True,
            message="Alerta reabierta"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reopening alert {alert_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))

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
                {"id": "parsing", "name": "Extracción de texto", "completed": False, "current": False},
                {"id": "structure", "name": "Detección de estructura", "completed": False, "current": False},
                {"id": "ner", "name": "Reconocimiento de entidades", "completed": False, "current": False},
                {"id": "fusion", "name": "Fusión semántica", "completed": False, "current": False},
                {"id": "attributes", "name": "Extracción de atributos", "completed": False, "current": False},
                {"id": "consistency", "name": "Análisis de consistencia", "completed": False, "current": False},
                {"id": "grammar", "name": "Análisis gramatical", "completed": False, "current": False},
                {"id": "alerts", "name": "Generación de alertas", "completed": False, "current": False}
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
                "parsing": 0.01,      # ~1% - instantáneo
                "structure": 0.02,    # ~2% - instantáneo
                "ner": 0.45,          # ~45% - LLM + spaCy
                "fusion": 0.22,       # ~22% - incluye correferencias con LLM
                "attributes": 0.12,   # ~12% - LLM
                "consistency": 0.04,  # ~4%
                "grammar": 0.08,      # ~8% - análisis gramatical y ortográfico
                "alerts": 0.06,       # ~6% - generación de alertas
            }
            phase_order = ["parsing", "structure", "ner", "fusion", "attributes", "consistency", "grammar", "alerts"]
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
                analysis_progress_storage[project_id]["current_phase"] = "Extrayendo texto del documento"

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

                # ========== CLASIFICACIÓN DE DOCUMENTO ==========
                # Detectar el tipo de documento para ajustar análisis
                from narrative_assistant.parsers.document_classifier import classify_document, DocumentType

                doc_title = project.name if project else None
                classification = classify_document(full_text[:10000], title=doc_title)
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

                # ========== FASE 2: ESTRUCTURA ==========
                current_phase_key = "structure"
                phase_start_times["structure"] = time.time()
                pct_start, pct_end = get_phase_progress_range("structure")
                phases[1]["current"] = True
                analysis_progress_storage[project_id]["progress"] = pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Detectando capítulos y escenas"

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
                phases[1]["completed"] = True
                phases[1]["current"] = False
                phases[1]["duration"] = round(phase_durations["structure"], 1)
                update_time_remaining()

                logger.info(f"Structure detection complete: {chapters_count} chapters")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 3: NER ==========
                current_phase_key = "ner"
                phase_start_times["ner"] = time.time()
                ner_pct_start, ner_pct_end = get_phase_progress_range("ner")
                phases[2]["current"] = True
                analysis_progress_storage[project_id]["progress"] = ner_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Identificando entidades (personajes, lugares...)"

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

                    # Agrupar entidades por nombre canónico para contar menciones
                    entity_mentions: dict[str, list] = {}  # canonical_name -> [ExtractedEntity, ...]
                    for ent in raw_entities:
                        canonical = ent.canonical_form or ent.text.lower().strip()
                        key = f"{ent.label.value}:{canonical}"
                        if key not in entity_mentions:
                            entity_mentions[key] = []
                        entity_mentions[key].append(ent)

                    # NOTA: Ya no se filtra por mínimo de menciones.
                    # El filtrado de falsos positivos se hace en NERExtractor._is_valid_entity()
                    # Un personaje puede aparecer solo 1 vez y sigue siendo válido.

                    logger.info(f"NER: {len(raw_entities)} menciones totales, {len(entity_mentions)} entidades únicas")

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

                        # Crear objeto Entity
                        entity = Entity(
                            project_id=project_id,
                            entity_type=label_to_type.get(first_mention.label, EntityType.CONCEPT),
                            canonical_name=first_mention.text,  # Usar texto original como nombre
                            aliases=[],
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

                            # Crear menciones en BD
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
                                entity_repo.create_mention(mention)

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
                phases[2]["completed"] = True
                phases[2]["current"] = False
                phases[2]["duration"] = round(phase_durations["ner"], 1)
                update_time_remaining()

                logger.info(f"NER complete: {len(entities)} entities")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 3.25: VALIDACIÓN DE ENTIDADES CON LLM ==========
                # Filtrar entidades que no son válidas (descripciones, frases, etc.)
                analysis_progress_storage[project_id]["current_action"] = "Validando entidades..."
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
                phases[3]["current"] = True  # Marcar fase fusion como activa en UI
                analysis_progress_storage[project_id]["progress"] = fusion_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Fusionando entidades similares y resolviendo correferencias"

                try:
                    from narrative_assistant.entities.semantic_fusion import get_semantic_fusion_service
                    from narrative_assistant.nlp.coref import resolve_coreferences
                    from narrative_assistant.entities.models import EntityType

                    fusion_service = get_semantic_fusion_service()
                    entity_repo = get_entity_repository()

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
                    for keep_entity, merge_entity in fusion_pairs:
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
                        except Exception as e:
                            logger.warning(f"Error fusionando {merge_entity.canonical_name} → {keep_entity.canonical_name}: {e}")

                    # Actualizar lista de entidades activas
                    entities = [e for e in entities if e.id not in merged_entity_ids]

                    analysis_progress_storage[project_id]["progress"] = 57
                    update_time_remaining()

                    # 2. Aplicar resolución de correferencias con votación multi-método
                    # Usa: embeddings semánticos, LLM local (Ollama), análisis morfosintáctico, heurísticas
                    analysis_progress_storage[project_id]["current_phase"] = "Resolviendo correferencias (votación multi-método)"

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
                    analysis_progress_storage[project_id]["current_action"] = f"Fusión completada: {len(entities)} entidades únicas"
                    # Marcar fase fusion como completada en UI
                    phases[3]["completed"] = True
                    phases[3]["current"] = False
                    phases[3]["duration"] = round(phase_durations["fusion"], 1)
                    update_time_remaining()

                    logger.info(
                        f"Fusión de entidades completada en {phase_durations['fusion']:.1f}s: "
                        f"{len(merged_entity_ids)} entidades fusionadas, "
                        f"{len(entities)} entidades activas"
                    )

                    # ========== RECALCULAR IMPORTANCIA FINAL ==========
                    # La importancia se calcula DESPUÉS de fusiones y correferencias
                    # basada en el conteo final de menciones en la BD
                    logger.info("Recalculando importancia de entidades...")
                    for entity in entities:
                        try:
                            # Obtener conteo real de menciones desde la BD
                            from sqlalchemy import text
                            db = get_database()
                            result = db.execute(
                                text("SELECT COUNT(*) FROM entity_mentions WHERE entity_id = :eid"),
                                {"eid": entity.id}
                            )
                            real_mention_count = result.scalar() or 0

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
                                db.execute(
                                    text("UPDATE entities SET mention_count = :count WHERE id = :eid"),
                                    {"count": real_mention_count, "eid": entity.id}
                                )
                                db.commit()
                                entity.importance = new_importance
                                entity.mention_count = real_mention_count
                                logger.debug(f"'{entity.canonical_name}': {real_mention_count} menciones -> {new_importance.value}")
                        except Exception as e:
                            logger.warning(f"Error recalculando importancia de '{entity.canonical_name}': {e}")

                except Exception as e:
                    logger.warning(f"Error en fusión de entidades (continuando sin fusión): {e}")
                    phase_durations["fusion"] = time.time() - phase_start_times.get("fusion", time.time())
                    # Marcar fusion como completada aunque haya fallado (para continuar UI)
                    phases[3]["completed"] = True
                    phases[3]["current"] = False
                    phases[3]["duration"] = round(phase_durations["fusion"], 1)
                check_cancelled()  # Verificar cancelación

                # ========== FASE 4: ATRIBUTOS ==========
                current_phase_key = "attributes"
                phase_start_times["attributes"] = time.time()
                attr_pct_start, attr_pct_end = get_phase_progress_range("attributes")
                phases[4]["current"] = True  # Index 4 after adding fusion at index 3
                analysis_progress_storage[project_id]["progress"] = attr_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Extrayendo atributos de personajes"

                attributes = []
                if entities:
                    attr_extractor = AttributeExtractor()
                    entity_repo = get_entity_repository()

                    # Preparar menciones de entidades para extract_attributes
                    # Format: [(nombre, start_char, end_char)]
                    character_entities = [e for e in entities if e.entity_type.value == "character"]

                    if character_entities:
                        # Extraer atributos del texto completo
                        # El extractor encontrará atributos para todas las entidades mencionadas
                        entity_mentions = [
                            (e.canonical_name, e.first_appearance_char or 0, (e.first_appearance_char or 0) + len(e.canonical_name))
                            for e in character_entities
                        ]

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

                        attr_result = attr_extractor.extract_attributes(
                            text=full_text,
                            entity_mentions=entity_mentions,
                            chapter_id=None,
                        )

                        if attr_result.is_failure:
                            logger.warning(f"Error extrayendo atributos: {attr_result.error}")
                        elif attr_result.value:
                            logger.info(f"Atributos extraídos: {len(attr_result.value.attributes)}")

                        if attr_result.is_success and attr_result.value:
                            # Resolver atributos con correferencias para asignar
                            # atributos de pronombres a la entidad correcta
                            # Ej: "Ella.hair_color = rubio" -> "María.hair_color = rubio"
                            extracted_attrs = attr_result.value.attributes

                            if coref_result and coref_result.chains:
                                try:
                                    from narrative_assistant.nlp.attributes import resolve_attributes_with_coreferences

                                    resolved_attrs = resolve_attributes_with_coreferences(
                                        attributes=extracted_attrs,
                                        coref_chains=coref_result.chains,
                                        text=full_text,
                                    )

                                    resolved_count = len(resolved_attrs) - len(extracted_attrs)
                                    if resolved_count > 0:
                                        logger.info(f"Resolución de atributos: {resolved_count} atributos de pronombres resueltos")

                                    extracted_attrs = resolved_attrs
                                except Exception as e:
                                    logger.warning(f"Error resolviendo atributos con correferencias: {e}")

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

                phase_durations["attributes"] = time.time() - phase_start_times["attributes"]
                analysis_progress_storage[project_id]["progress"] = attr_pct_end
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["attributes_extracted"] = len(attributes)
                phases[4]["completed"] = True
                phases[4]["current"] = False
                phases[4]["duration"] = round(phase_durations["attributes"], 1)

                logger.info(f"Attribute extraction complete: {len(attributes)} attributes")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 5: CONSISTENCIA ==========
                current_phase_key = "consistency"
                phase_start_times["consistency"] = time.time()
                cons_pct_start, cons_pct_end = get_phase_progress_range("consistency")
                phases[5]["current"] = True
                analysis_progress_storage[project_id]["progress"] = cons_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Analizando consistencia narrativa"

                inconsistencies = []
                if attributes:
                    checker = AttributeConsistencyChecker()
                    check_result = checker.check_consistency(attributes)
                    if check_result.is_success:
                        inconsistencies = check_result.value or []

                phase_durations["consistency"] = time.time() - phase_start_times["consistency"]
                analysis_progress_storage[project_id]["progress"] = cons_pct_end
                update_time_remaining()
                analysis_progress_storage[project_id]["metrics"]["inconsistencies_found"] = len(inconsistencies)
                phases[5]["completed"] = True
                phases[5]["current"] = False
                phases[5]["duration"] = round(phase_durations["consistency"], 1)

                logger.info(f"Consistency analysis complete: {len(inconsistencies)} inconsistencies")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 6: ANÁLISIS GRAMATICAL ==========
                current_phase_key = "grammar"
                phase_start_times["grammar"] = time.time()
                grammar_pct_start, grammar_pct_end = get_phase_progress_range("grammar")
                phases[6]["current"] = True
                analysis_progress_storage[project_id]["progress"] = grammar_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Analizando gramática y ortografía"

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

                phase_durations["grammar"] = time.time() - phase_start_times["grammar"]
                analysis_progress_storage[project_id]["progress"] = grammar_pct_end
                analysis_progress_storage[project_id]["metrics"]["grammar_issues_found"] = len(grammar_issues)
                phases[6]["completed"] = True
                phases[6]["current"] = False
                phases[6]["duration"] = round(phase_durations["grammar"], 1)
                update_time_remaining()

                logger.info(f"Grammar analysis complete: {len(grammar_issues)} grammar issues")
                check_cancelled()  # Verificar cancelación

                # ========== FASE 7: ALERTAS ==========
                current_phase_key = "alerts"
                phase_start_times["alerts"] = time.time()
                alerts_pct_start, alerts_pct_end = get_phase_progress_range("alerts")
                phases[7]["current"] = True
                analysis_progress_storage[project_id]["progress"] = alerts_pct_start
                analysis_progress_storage[project_id]["current_phase"] = "Generando alertas"

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

                phase_durations["alerts"] = time.time() - phase_start_times["alerts"]
                analysis_progress_storage[project_id]["progress"] = 100
                analysis_progress_storage[project_id]["metrics"]["alerts_generated"] = alerts_created
                phases[7]["completed"] = True
                phases[7]["current"] = False
                phases[7]["duration"] = round(phase_durations["alerts"], 1)

                # ========== COMPLETADO ==========
                analysis_progress_storage[project_id]["status"] = "completed"
                analysis_progress_storage[project_id]["current_phase"] = "Análisis completado"
                analysis_progress_storage[project_id]["estimated_seconds_remaining"] = 0

                total_duration = round(time.time() - start_time, 1)
                analysis_progress_storage[project_id]["metrics"]["total_duration_seconds"] = total_duration

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
            # No hay análisis en curso, devolver estado "pending"
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "status": "pending",
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
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Narrative Assistant API Server v{NA_VERSION}")
    logger.info("Server will be available at http://localhost:8008")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8008,
        reload=True,  # Solo para desarrollo
        log_level="info",
    )
