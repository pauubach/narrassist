"""
Helpers compartidos para resolución dinámica de modelos LLM.

Evita hardcodear nombres de modelos en endpoints individuales.
"""

import logging

logger = logging.getLogger(__name__)


def get_configured_level() -> str:
    """Retorna el nivel de calidad configurado en DB (o 'rapida' por defecto)."""
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        with db.connection() as conn:
            row = conn.execute(
                "SELECT quality_level FROM llm_config LIMIT 1"
            ).fetchone()
        return row[0] if row else "rapida"
    except Exception:
        return "rapida"


def get_default_llm_model() -> str | None:
    """
    Retorna el mejor modelo LLM disponible según configuración y hardware.

    Orden de preferencia:
    1. Modelos core del nivel configurado (LEVEL_MODELS)
    2. Modelos fallback del nivel (LEVEL_FALLBACK_MODELS)
    3. Cualquier modelo instalado en Ollama

    Returns:
        Nombre del modelo o None si no hay ninguno disponible.
    """
    try:
        from narrative_assistant.llm.config import (
            LEVEL_FALLBACK_MODELS,
            LEVEL_MODELS,
            QualityLevel,
        )
        from narrative_assistant.llm.ollama_manager import get_ollama_manager

        manager = get_ollama_manager()
        installed = {m.split(":")[0].strip().lower() for m in manager.downloaded_models}

        if not installed:
            return None

        # Nivel configurado
        level_str = get_configured_level()
        try:
            level = QualityLevel(level_str)
        except ValueError:
            level = QualityLevel.RAPIDA

        # 1. Buscar en modelos core del nivel
        for model in LEVEL_MODELS.get(level, []):
            if model in installed:
                return model

        # 2. Buscar en fallbacks del nivel
        for model in LEVEL_FALLBACK_MODELS.get(level, []):
            if model in installed:
                return model

        # 3. Cualquier modelo instalado (último recurso)
        return next(iter(installed))

    except Exception as e:
        logger.debug(f"Error resolviendo modelo LLM por defecto: {e}")
        return None


def check_llm_readiness() -> dict:
    """
    Verifica si el sistema LLM está listo para análisis.

    Returns:
        dict con: ready, ollama_installed, ollama_running, configured_level,
                  missing_models, available_models, has_any_model
    """
    result = {
        "ready": False,
        "ollama_installed": False,
        "ollama_running": False,
        "configured_level": "rapida",
        "missing_models": [],
        "available_models": [],
        "has_any_model": False,
    }

    try:
        from narrative_assistant.llm.ollama_manager import (
            get_ollama_manager,
            is_ollama_available,
        )

        manager = get_ollama_manager()
        result["ollama_installed"] = manager.is_installed
        result["ollama_running"] = is_ollama_available()

        if not result["ollama_running"]:
            return result

        installed = {m.split(":")[0].strip().lower() for m in manager.downloaded_models}
        result["available_models"] = sorted(installed)
        result["has_any_model"] = len(installed) > 0

        # Verificar modelos requeridos por el nivel configurado
        from narrative_assistant.llm.config import (
            LEVEL_FALLBACK_MODELS,
            LEVEL_MODELS,
            QualityLevel,
        )

        level_str = get_configured_level()
        result["configured_level"] = level_str

        try:
            level = QualityLevel(level_str)
        except ValueError:
            level = QualityLevel.RAPIDA

        required = set(LEVEL_MODELS.get(level, []))
        missing = required - installed

        # Si faltan modelos core, verificar si hay fallbacks disponibles
        if missing:
            fallbacks = LEVEL_FALLBACK_MODELS.get(level, [])
            has_usable_fallback = any(f in installed for f in fallbacks)
            # Solo reportar como faltantes los que NO tienen fallback
            if has_usable_fallback:
                # Hay al menos un fallback — el sistema puede funcionar
                result["missing_models"] = sorted(missing)
                result["ready"] = True
            else:
                result["missing_models"] = sorted(missing)
                result["ready"] = False
        else:
            result["ready"] = True

    except ImportError:
        logger.debug("Ollama manager no disponible")
    except Exception as e:
        logger.debug(f"Error verificando readiness LLM: {e}")

    return result
