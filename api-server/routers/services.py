"""
Router: services
"""


from collections.abc import Iterable

import deps
from deps import (
    ApiResponse,
    ChatRequest,
    _audience_label,
    _field_label,
    _register_label,
    logger,
)
from fastapi import APIRouter, HTTPException

router = APIRouter()

_MODEL_SPEED_ORDER = ["llama3.2", "qwen2.5", "mistral", "gemma2"]
_MODEL_QUALITY_ORDER = ["gemma2", "mistral", "qwen2.5", "llama3.2"]


def _normalize_model_name(model_name: str) -> str:
    return (model_name or "").split(":")[0].strip().lower()


def _sorted_models(
    models: Iterable[str],
    prioritize_speed: bool,
) -> list[str]:
    ranking = _MODEL_SPEED_ORDER if prioritize_speed else _MODEL_QUALITY_ORDER
    order_map = {name: idx for idx, name in enumerate(ranking)}
    return sorted(
        {_normalize_model_name(m) for m in models if m},
        key=lambda m: order_map.get(m, len(order_map)),
    )

@router.get("/api/llm/status", response_model=ApiResponse)
def get_llm_status():
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
        from narrative_assistant.llm import get_llm_client, is_llm_available

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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/ollama/start", response_model=ApiResponse)
def start_ollama_service():
    """
    Inicia el servicio de Ollama si está instalado pero no corriendo.

    Returns:
        ApiResponse con resultado de la operación
    """
    try:
        from narrative_assistant.llm.ollama_manager import OllamaStatus, get_ollama_manager

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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/ollama/status", response_model=ApiResponse)
def get_ollama_status():
    """
    Obtiene el estado detallado de Ollama.

    Returns:
        ApiResponse con estado de instalación, servicio y modelos
    """
    try:
        from narrative_assistant.llm.ollama_manager import get_ollama_manager

        manager = get_ollama_manager()
        status = manager.status

        # Include download progress if a download is in progress
        download_progress = None
        if manager.download_progress is not None:
            dp = manager.download_progress
            download_progress = {
                "percentage": dp.percentage,
                "status": dp.status,
                "model_name": manager.downloading_model,
                "error": dp.error,
            }

        return ApiResponse(
            success=True,
            data={
                "status": status.value,
                "is_installed": manager.is_installed,
                "is_running": manager.is_running,
                "is_downloading": manager.is_downloading,
                "version": manager.get_version() if manager.is_installed else None,
                "downloaded_models": manager.downloaded_models,
                "download_progress": download_progress,
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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/ollama/pull/{model_name}", response_model=ApiResponse)
def pull_ollama_model(model_name: str):
    """
    Inicia descarga de un modelo de Ollama en segundo plano.

    La descarga se ejecuta en un hilo de fondo. El progreso se puede
    consultar via GET /api/ollama/status (campo download_progress).

    Args:
        model_name: Nombre del modelo a descargar (ej: llama3.2)

    Returns:
        ApiResponse con resultado del inicio de la operación
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

        # Iniciar descarga en segundo plano
        started = manager.start_download_async(model_name)

        if not started:
            return ApiResponse(
                success=False,
                error="Ya hay una descarga en curso"
            )

        return ApiResponse(
            success=True,
            data={"message": f"Descarga de {model_name} iniciada"}
        )

    except Exception as e:
        logger.error(f"Error pulling model {model_name}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/ollama/model/{model_name}", response_model=ApiResponse)
def delete_ollama_model(model_name: str):
    """
    Elimina un modelo de Ollama.

    Regla de seguridad UX: debe quedar al menos 1 modelo instalado.
    """
    try:
        from narrative_assistant.llm.ollama_manager import get_ollama_manager

        manager = get_ollama_manager()
        normalized = _normalize_model_name(model_name)

        if not manager.is_installed:
            return ApiResponse(success=False, error="Ollama no está instalado")

        success, message = manager.ensure_running()
        if not success:
            return ApiResponse(success=False, error=f"No se pudo iniciar Ollama: {message}")

        downloaded = {_normalize_model_name(m) for m in manager.downloaded_models}
        if normalized not in downloaded:
            return ApiResponse(success=False, error=f"El modelo '{normalized}' no está instalado")

        if len(downloaded) <= 1:
            return ApiResponse(
                success=False,
                error="Debe quedar al menos 1 modelo instalado",
                data={"min_models_required": 1, "installed_models": sorted(downloaded)},
            )

        success, message = manager.delete_model(normalized)
        if not success:
            return ApiResponse(success=False, error=message)

        return ApiResponse(
            success=True,
            data={
                "message": message,
                "remaining_models": sorted({_normalize_model_name(m) for m in manager.downloaded_models}),
            },
        )
    except Exception as e:
        logger.error(f"Error deleting model {model_name}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/ollama/install", response_model=ApiResponse)
async def install_ollama_endpoint():
    """
    Instala Ollama de forma silenciosa.

    Returns:
        ApiResponse con resultado de la instalación
    """
    try:
        from narrative_assistant.llm.ollama_manager import get_ollama_manager

        manager = get_ollama_manager()

        if manager.is_installed:
            return ApiResponse(
                success=True,
                data={"message": "Ollama ya está instalado", "status": "already_installed"}
            )

        import asyncio
        success, msg = await asyncio.to_thread(manager.install_ollama, None, True)

        if success:
            return ApiResponse(
                success=True,
                data={"message": msg, "status": "installed"}
            )
        else:
            return ApiResponse(
                success=False,
                error=msg,
                data={"status": "error", "install_url": "https://ollama.com/download"}
            )

    except Exception as e:
        logger.error(f"Error installing Ollama: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            error="Error interno del servidor",
            data={"status": "error", "install_url": "https://ollama.com/download"}
        )


@router.get("/api/languagetool/status", response_model=ApiResponse)
def get_languagetool_status():
    """
    Estado detallado de LanguageTool.

    Returns:
        ApiResponse con estado: not_installed, installing, installed_not_running, running
    """
    try:
        from narrative_assistant.nlp.grammar.languagetool_manager import (
            get_install_progress,
            get_languagetool_manager,
            is_lt_installing,
        )

        manager = get_languagetool_manager()
        installing = is_lt_installing()
        progress = get_install_progress()

        if installing:
            status = "installing"
        elif not manager.is_installed:
            status = "not_installed"
        elif manager.is_running:
            status = "running"
        else:
            status = "installed_not_running"

        data = {
            "status": status,
            "is_installed": manager.is_installed,
            "is_running": manager.is_running if not installing else False,
            "is_installing": installing,
            "java_available": manager._get_java_command() is not None,
            "install_progress": None,
        }

        # Siempre devolver progreso si existe (incluso tras fallo)
        # para que el frontend pueda mostrar el error.
        if progress:
            data["install_progress"] = {
                "phase": progress.phase,
                "phase_label": progress.phase_label,
                "percentage": progress.percentage,
                "detail": progress.detail,
                "error": progress.error,
            }

        return ApiResponse(success=True, data=data)

    except Exception as e:
        logger.error(f"Error checking LanguageTool status: {e}", exc_info=True)
        return ApiResponse(success=True, data={
            "status": "not_installed",
            "is_installed": False,
            "is_running": False,
            "is_installing": False,
            "java_available": False,
            "install_progress": None,
        })


@router.post("/api/languagetool/install", response_model=ApiResponse)
def install_languagetool_endpoint():
    """
    Inicia instalación de LanguageTool + Java en background.

    Returns:
        ApiResponse con estado de la operación
    """
    try:
        from narrative_assistant.nlp.grammar.languagetool_manager import (
            is_lt_installing,
            start_lt_installation,
        )

        if is_lt_installing():
            return ApiResponse(
                success=False,
                error="Ya hay una instalación en curso"
            )

        success, msg = start_lt_installation()
        return ApiResponse(
            success=success,
            data={"message": msg} if success else None,
            error=msg if not success else None,
        )

    except Exception as e:
        logger.error(f"Error starting LanguageTool install: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/languagetool/start", response_model=ApiResponse)
async def start_languagetool_endpoint():
    """
    Inicia el servidor LanguageTool.

    Returns:
        ApiResponse con resultado
    """
    try:
        from narrative_assistant.nlp.grammar.languagetool_manager import (
            get_languagetool_manager,
        )

        manager = get_languagetool_manager()

        if not manager.is_installed:
            return ApiResponse(
                success=False,
                error="LanguageTool no está instalado"
            )

        if manager.is_running:
            return ApiResponse(
                success=True,
                data={"message": "LanguageTool ya está corriendo"}
            )

        import asyncio
        success = await asyncio.to_thread(manager.start)

        if success:
            return ApiResponse(
                success=True,
                data={"message": "LanguageTool iniciado correctamente"}
            )
        else:
            return ApiResponse(
                success=False,
                error="No se pudo iniciar LanguageTool. Verifica que Java está disponible."
            )

    except Exception as e:
        logger.error(f"Error starting LanguageTool: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/languagetool/stop", response_model=ApiResponse)
def stop_languagetool_endpoint():
    """
    Detiene el servidor LanguageTool.

    Returns:
        ApiResponse con resultado
    """
    try:
        from narrative_assistant.nlp.grammar.languagetool_manager import (
            get_languagetool_manager,
        )

        manager = get_languagetool_manager()
        success = manager.stop()

        return ApiResponse(
            success=success,
            data={"message": "LanguageTool detenido"} if success else None,
            error="No se pudo detener LanguageTool" if not success else None,
        )

    except Exception as e:
        logger.error(f"Error stopping LanguageTool: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/chat", response_model=ApiResponse)
def chat_with_assistant(project_id: int, request: ChatRequest):
    """
    Chat con el asistente LLM usando el documento como contexto.

    Usa RAG exhaustivo: busca TODAS las ocurrencias relevantes en TODO el
    manuscrito y devuelve referencias navegables [REF:N] en la respuesta.

    Args:
        project_id: ID del proyecto
        request: Mensaje del usuario, historial, y texto seleccionado opcional

    Returns:
        ApiResponse con la respuesta del LLM y referencias navegables
    """
    from ._chat_rag import (
        build_chat_system_prompt,
        build_numbered_context,
        build_reference_index,
        build_selection_context,
        exhaustive_search,
        extract_search_terms,
        rank_and_select,
    )

    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar que el proyecto existe
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Verificar que Ollama está disponible
        try:
            from narrative_assistant.llm import get_llm_client, is_llm_available

            if not is_llm_available():
                logger.warning("LLM not available - Ollama might not be running")
                return ApiResponse(
                    success=False,
                    error="El asistente necesita Ollama para funcionar. Inícialo desde Ajustes > LLM."
                )

            llm_client = get_llm_client()
            if not llm_client:
                return ApiResponse(
                    success=False,
                    error="No se pudo conectar con Ollama. Reinícialo desde Ajustes > LLM."
                )

            if not llm_client.is_available:
                return ApiResponse(
                    success=False,
                    error="Ollama está activo pero falta el modelo. Descárgalo desde Ajustes > LLM."
                )
        except ImportError as e:
            logger.error(f"LLM module import error: {e}")
            return ApiResponse(
                success=False,
                error="Módulo LLM no instalado correctamente"
            )
        except Exception as e:
            logger.error(f"Error checking LLM availability: {e}")
            return ApiResponse(
                success=False,
                error=f"Error al verificar Ollama: {str(e)}"
            )

        # ================================================================
        # RAG exhaustivo
        # ================================================================

        # 1. Obtener TODOS los capítulos (contenido completo)
        chapters_data: list[dict] = []
        if deps.chapter_repository:
            chapters = deps.chapter_repository.get_by_project(project_id)
            for ch in chapters:
                if ch.content:
                    chapters_data.append({
                        "number": ch.chapter_number,
                        "title": ch.title or f"Capítulo {ch.chapter_number}",
                        "content": ch.content,
                        "start_char": ch.start_char,
                        "end_char": ch.end_char,
                        "id": ch.id,
                    })

        # 2. Obtener entidades para keyword expansion
        entities = []
        if deps.entity_repository:
            try:
                entities = deps.entity_repository.get_entities_by_project(project_id)
            except Exception as e:
                logger.warning(f"Could not load entities for chat RAG: {e}")

        # 3. Extraer términos de búsqueda enriquecidos
        search_terms = extract_search_terms(request.message, entities)

        # 4. Búsqueda exhaustiva en todo el manuscrito
        all_matches = exhaustive_search(search_terms, chapters_data)

        # 5. Ranking y selección con budget de tokens
        selected_excerpts = rank_and_select(all_matches, max_chars=2000, max_excerpts=8)

        # 6. Construir contexto numerado
        context_text, ref_map = build_numbered_context(selected_excerpts)
        context_sources = list({e["chapter_title"] for e in selected_excerpts})

        # 7. Contexto de texto seleccionado
        selection_context = ""
        if request.selected_text:
            ch_title = None
            if request.selected_text_chapter:
                for cd in chapters_data:
                    if cd["number"] == request.selected_text_chapter:
                        ch_title = cd["title"]
                        break
            selection_context = build_selection_context(
                request.selected_text, ch_title
            )

        # 8. Historial de conversación
        history_text = ""
        if request.history:
            history_text = "\n\n### Conversación previa:\n"
            for msg in request.history[-5:]:
                role = "Usuario" if msg.get("role") == "user" else "Asistente"
                history_text += f"{role}: {msg.get('content', '')}\n"

        # 9. System prompt completo
        system_prompt = build_chat_system_prompt(
            project_name=project.name,
            context_text=context_text,
            selection_context=selection_context,
            history_text=history_text,
        )

        # ================================================================
        # Selección de modelo (misma lógica existente)
        # ================================================================
        ctx = request.context if isinstance(request.context, dict) else {}
        selected_models_raw = ctx.get("enabledInferenceMethods", [])
        prioritize_speed = bool(ctx.get("prioritizeSpeed", True))

        selected_models = []
        if isinstance(selected_models_raw, list):
            selected_models = [
                _normalize_model_name(str(m))
                for m in selected_models_raw
                if isinstance(m, str) and m.strip()
            ]

        installed_models: list[str] = []
        try:
            from narrative_assistant.llm.ollama_manager import get_ollama_manager
            manager = get_ollama_manager()
            installed_models = [_normalize_model_name(m) for m in manager.downloaded_models]
        except Exception:
            installed_models = []

        selected_installed = [
            m for m in selected_models if m in set(installed_models)
        ]
        default_model = _normalize_model_name(llm_client.model_name)
        if selected_installed:
            candidate_models = _sorted_models(selected_installed, prioritize_speed)
        else:
            candidate_models = _sorted_models([default_model], True)

        # ================================================================
        # Llamar al LLM
        # ================================================================
        try:
            from narrative_assistant.llm.client import get_llm_scheduler
            response = None
            used_model = None

            with get_llm_scheduler().chat_priority():
                for model_name in candidate_models:
                    response = llm_client.complete(
                        prompt=request.message,
                        system=system_prompt,
                        max_tokens=1000,
                        temperature=0.35,
                        model_name=model_name,
                    )
                    if response and response.strip():
                        used_model = model_name
                        break

            if response and response.strip():
                # Parsear referencias [REF:N]
                references = build_reference_index(response, ref_map)

                using_cpu = getattr(llm_client, '_ollama_num_gpu', None) == 0
                return ApiResponse(
                    success=True,
                    data={
                        "response": response.strip(),
                        "references": references,
                        "contextUsed": context_sources,
                        "model": used_model or llm_client.model_name,
                        "usingCpu": using_cpu,
                        "candidateModels": candidate_models,
                    }
                )
            else:
                logger.warning(f"LLM returned empty response for project {project_id}")
                return ApiResponse(
                    success=False,
                    error="El modelo no generó respuesta. Reinicia Ollama desde Ajustes > LLM."
                )

        except Exception as e:
            logger.error(f"Error calling LLM: {e}", exc_info=True)
            error_lower = str(e).lower()
            if any(p in error_lower for p in ("terminated", "exit status", "memory", "allocate")):
                return ApiResponse(
                    success=False,
                    error="Ollama se quedó sin memoria GPU. Reinícialo desde Ajustes > LLM en modo CPU."
                )
            return ApiResponse(
                success=False,
                error=f"Error al comunicarse con el LLM: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/correction-presets", response_model=ApiResponse)
def get_correction_presets() -> ApiResponse:
    """
    Obtiene los presets de configuración de corrección disponibles.

    Retorna una lista de presets con su nombre, descripción y configuración.
    """
    try:
        from narrative_assistant.corrections.config import (
            AudienceType,
            CorrectionConfig,
            DocumentField,
            RegisterLevel,
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
                {"value": f.value, "label": _field_label(f.value)} for f in DocumentField
            ],
            "register_levels": [
                {"value": r.value, "label": _register_label(r.value)} for r in RegisterLevel
            ],
            "audience_types": [
                {"value": a.value, "label": _audience_label(a.value)} for a in AudienceType
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
        return ApiResponse(success=False, error="Error interno del servidor")


