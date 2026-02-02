"""
Router: services
"""

from fastapi import APIRouter
import deps
import json
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import Request
from deps import (
    ChatRequest,
    _audience_label,
    _field_label,
    _register_label,
)

router = APIRouter()

@router.get("/api/llm/status", response_model=ApiResponse)
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


@router.post("/api/ollama/start", response_model=ApiResponse)
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


@router.get("/api/ollama/status", response_model=ApiResponse)
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


@router.post("/api/ollama/pull/{model_name}", response_model=ApiResponse)
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
            error=str(e),
            data={"status": "error", "install_url": "https://ollama.com/download"}
        )


@router.get("/api/languagetool/status", response_model=ApiResponse)
async def get_languagetool_status():
    """
    Estado detallado de LanguageTool.

    Returns:
        ApiResponse con estado: not_installed, installing, installed_not_running, running
    """
    try:
        from narrative_assistant.nlp.grammar.languagetool_manager import (
            get_languagetool_manager,
            is_lt_installing,
            get_install_progress,
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
async def install_languagetool_endpoint():
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
        return ApiResponse(success=False, error=str(e))


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
        return ApiResponse(success=False, error=str(e))


@router.post("/api/languagetool/stop", response_model=ApiResponse)
async def stop_languagetool_endpoint():
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
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/chat", response_model=ApiResponse)
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
        if deps.chapter_repository:
            chapters = deps.chapter_repository.get_by_project(project_id)
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


@router.get("/api/correction-presets", response_model=ApiResponse)
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


