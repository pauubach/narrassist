"""
Tests para _llm_helpers: resolución dinámica de modelos LLM y readiness check.

Cubre:
- get_default_llm_model(): selección del mejor modelo disponible
- get_configured_level(): lectura del nivel configurado
- check_llm_readiness(): verificación completa del estado LLM
"""

from unittest.mock import MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════════
# Helpers para importar módulos del api-server
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _api_server_path():
    """Agrega api-server al sys.path para importar routers."""
    import sys
    from pathlib import Path
    api_path = str(Path(__file__).parent.parent.parent / "api-server")
    if api_path not in sys.path:
        sys.path.insert(0, api_path)


# ═══════════════════════════════════════════════════════════════════════
# Tests: get_configured_level
# ═══════════════════════════════════════════════════════════════════════

class TestGetConfiguredLevel:
    """Tests para get_configured_level()."""

    def test_returns_rapida_when_no_db(self):
        """Sin base de datos, retorna 'rapida' por defecto."""
        from routers._llm_helpers import get_configured_level

        with patch(
            "narrative_assistant.persistence.database.get_database",
            side_effect=Exception("No DB"),
        ):
            assert get_configured_level() == "rapida"

    def test_returns_configured_level(self):
        """Retorna el nivel configurado en la base de datos."""
        from routers._llm_helpers import get_configured_level

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("completa",)
        mock_db.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        with patch("narrative_assistant.persistence.database.get_database", return_value=mock_db):
            assert get_configured_level() == "completa"

    def test_returns_rapida_when_empty_table(self):
        """Si la tabla está vacía, retorna 'rapida'."""
        from routers._llm_helpers import get_configured_level

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_db.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        with patch("narrative_assistant.persistence.database.get_database", return_value=mock_db):
            assert get_configured_level() == "rapida"


# ═══════════════════════════════════════════════════════════════════════
# Tests: get_default_llm_model
# ═══════════════════════════════════════════════════════════════════════

class TestGetDefaultLlmModel:
    """Tests para get_default_llm_model()."""

    def test_returns_none_when_no_models(self):
        """Sin modelos instalados, retorna None."""
        from routers._llm_helpers import get_default_llm_model

        mock_manager = MagicMock()
        mock_manager.downloaded_models = []

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            assert get_default_llm_model() is None

    def test_returns_core_model_when_available(self):
        """Retorna el modelo core del nivel si está disponible."""
        from routers._llm_helpers import get_default_llm_model

        mock_manager = MagicMock()
        mock_manager.downloaded_models = ["qwen3:latest", "llama3.2:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            result = get_default_llm_model()
            assert result == "qwen3"

    def test_returns_fallback_when_core_missing(self):
        """Retorna modelo fallback si el core no está disponible."""
        from routers._llm_helpers import get_default_llm_model

        mock_manager = MagicMock()
        mock_manager.downloaded_models = ["llama3.2:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            result = get_default_llm_model()
            assert result == "llama3.2"

    def test_returns_any_model_when_no_match(self):
        """Retorna cualquier modelo si no hay match en core ni fallback."""
        from routers._llm_helpers import get_default_llm_model

        mock_manager = MagicMock()
        mock_manager.downloaded_models = ["mistral:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            result = get_default_llm_model()
            assert result == "mistral"

    def test_completa_level_prefers_qwen3(self):
        """Nivel 'completa' prefiere qwen3 sobre hermes3."""
        from routers._llm_helpers import get_default_llm_model

        mock_manager = MagicMock()
        mock_manager.downloaded_models = ["hermes3:latest", "qwen3:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("routers._llm_helpers.get_configured_level", return_value="completa"),
        ):
            result = get_default_llm_model()
            assert result == "qwen3"

    def test_handles_import_error(self):
        """Si ollama_manager no se puede importar, retorna None."""
        from routers._llm_helpers import get_default_llm_model

        with patch(
            "narrative_assistant.llm.ollama_manager.get_ollama_manager",
            side_effect=ImportError("No ollama"),
        ):
            assert get_default_llm_model() is None


# ═══════════════════════════════════════════════════════════════════════
# Tests: check_llm_readiness
# ═══════════════════════════════════════════════════════════════════════

class TestCheckLlmReadiness:
    """Tests para check_llm_readiness()."""

    def test_not_ready_when_ollama_not_running(self):
        """Si Ollama no está corriendo, no está ready."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = []

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=False),
        ):
            result = check_llm_readiness()
            assert result["ready"] is False
            assert result["ollama_installed"] is True
            assert result["ollama_running"] is False

    def test_ready_when_all_core_models_present(self):
        """Ready cuando todos los modelos core del nivel están presentes."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = ["qwen3:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=True),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            result = check_llm_readiness()
            assert result["ready"] is True
            assert result["has_any_model"] is True
            assert result["missing_models"] == []

    def test_not_ready_when_core_models_missing_no_fallback(self):
        """No ready cuando faltan modelos core y no hay fallback."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = []  # sin modelos

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=True),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            result = check_llm_readiness()
            assert result["ready"] is False
            assert result["has_any_model"] is False
            assert "qwen3" in result["missing_models"]

    def test_ready_with_fallback_available(self):
        """Ready cuando falta core pero hay un fallback disponible."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = ["llama3.2:latest"]  # fallback para rapida

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=True),
            patch("routers._llm_helpers.get_configured_level", return_value="rapida"),
        ):
            result = check_llm_readiness()
            assert result["ready"] is True  # fallback disponible
            assert result["has_any_model"] is True
            assert "qwen3" in result["missing_models"]  # pero reporta el core como faltante

    def test_completa_reports_multiple_missing(self):
        """Nivel 'completa' reporta múltiples modelos faltantes."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = ["llama3.2:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=True),
            patch("routers._llm_helpers.get_configured_level", return_value="completa"),
        ):
            result = check_llm_readiness()
            # Completa necesita qwen3 + hermes3, solo tiene llama3.2 como fallback
            assert result["ready"] is True  # tiene fallback
            assert "qwen3" in result["missing_models"]
            assert "hermes3" in result["missing_models"]

    def test_experta_reports_three_missing(self):
        """Nivel 'experta' reporta 3 modelos faltantes."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = []

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=True),
            patch("routers._llm_helpers.get_configured_level", return_value="experta"),
        ):
            result = check_llm_readiness()
            assert result["ready"] is False
            assert len(result["missing_models"]) == 3
            assert set(result["missing_models"]) == {"qwen3", "hermes3", "deepseek-r1"}

    def test_not_installed_returns_defaults(self):
        """Si Ollama no está instalado, retorna defaults seguros."""
        from routers._llm_helpers import check_llm_readiness

        with patch(
            "narrative_assistant.llm.ollama_manager.get_ollama_manager",
            side_effect=ImportError("No ollama"),
        ):
            result = check_llm_readiness()
            assert result["ready"] is False
            assert result["ollama_installed"] is False
            assert result["ollama_running"] is False
            assert result["missing_models"] == []

    def test_available_models_reported(self):
        """Reporta los modelos disponibles correctamente."""
        from routers._llm_helpers import check_llm_readiness

        mock_manager = MagicMock()
        mock_manager.is_installed = True
        mock_manager.downloaded_models = ["qwen3:latest", "hermes3:latest", "llama3.2:latest"]

        with (
            patch("narrative_assistant.llm.ollama_manager.get_ollama_manager", return_value=mock_manager),
            patch("narrative_assistant.llm.ollama_manager.is_ollama_available", return_value=True),
            patch("routers._llm_helpers.get_configured_level", return_value="completa"),
        ):
            result = check_llm_readiness()
            assert result["ready"] is True
            assert "qwen3" in result["available_models"]
            assert "hermes3" in result["available_models"]
            assert "llama3.2" in result["available_models"]
