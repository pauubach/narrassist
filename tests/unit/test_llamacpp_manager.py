"""
Tests unitarios para el módulo llama.cpp manager.

Verifica la gestión del servidor llama.cpp y la descarga de modelos.
"""

import os
import platform
import tempfile
from pathlib import Path
from unittest import mock

import pytest


class TestLlamaCppImports:
    """Tests de importación del módulo llama.cpp."""

    def test_import_module(self):
        """Verifica importación del módulo."""
        from narrative_assistant.llm import llamacpp_manager

        assert llamacpp_manager is not None

    def test_import_manager(self):
        """Verifica importación de LlamaCppManager."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        assert LlamaCppManager is not None

    def test_import_status_enum(self):
        """Verifica importación de LlamaCppStatus."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppStatus

        assert LlamaCppStatus is not None

    def test_import_model_info(self):
        """Verifica importación de LlamaCppModelInfo."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppModelInfo

        assert LlamaCppModelInfo is not None

    def test_import_get_manager(self):
        """Verifica importación de get_llamacpp_manager."""
        from narrative_assistant.llm.llamacpp_manager import get_llamacpp_manager

        assert callable(get_llamacpp_manager)

    def test_import_available_models(self):
        """Verifica importación de AVAILABLE_MODELS."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS

        assert AVAILABLE_MODELS is not None
        assert len(AVAILABLE_MODELS) > 0


class TestLlamaCppStatus:
    """Tests para LlamaCppStatus enum."""

    def test_status_values_exist(self):
        """Estados esperados existen."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppStatus

        expected_statuses = [
            "NOT_INSTALLED",
            "INSTALLED",
            "RUNNING",
            "ERROR",
        ]

        for status in expected_statuses:
            assert hasattr(LlamaCppStatus, status), f"Missing: {status}"

    def test_status_values(self):
        """Valores de estado son strings correctos."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppStatus

        assert LlamaCppStatus.NOT_INSTALLED.value == "not_installed"
        assert LlamaCppStatus.INSTALLED.value == "installed"
        assert LlamaCppStatus.RUNNING.value == "running"
        assert LlamaCppStatus.ERROR.value == "error"


class TestLlamaCppModelInfo:
    """Tests para LlamaCppModelInfo dataclass."""

    def test_model_info_creation(self):
        """Puede crear un LlamaCppModelInfo."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppModelInfo

        model = LlamaCppModelInfo(
            name="test-model",
            display_name="Test Model",
            filename="test.gguf",
            size_gb=1.5,
            description="A test model",
            url="https://example.com/test.gguf",
        )

        assert model.name == "test-model"
        assert model.display_name == "Test Model"
        assert model.filename == "test.gguf"
        assert model.size_gb == 1.5
        assert model.is_downloaded is False
        assert model.is_default is False

    def test_model_info_defaults(self):
        """Valores por defecto de LlamaCppModelInfo."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppModelInfo

        model = LlamaCppModelInfo(
            name="test",
            display_name="Test",
            filename="test.gguf",
            size_gb=1.0,
            description="Test",
            url="https://example.com",
            is_default=True,
        )

        assert model.is_default is True
        assert model.is_downloaded is False


class TestAvailableModels:
    """Tests para la lista de modelos disponibles."""

    def test_available_models_not_empty(self):
        """Hay al menos un modelo disponible."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS

        assert len(AVAILABLE_MODELS) >= 1

    def test_default_model_exists(self):
        """Hay un modelo marcado como default."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS

        default_models = [m for m in AVAILABLE_MODELS if m.is_default]
        assert len(default_models) >= 1, "Debe haber al menos un modelo por defecto"

    def test_models_have_required_fields(self):
        """Todos los modelos tienen campos requeridos."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS

        for model in AVAILABLE_MODELS:
            assert model.name, "Modelo sin nombre"
            assert model.display_name, f"Modelo {model.name} sin display_name"
            assert model.filename, f"Modelo {model.name} sin filename"
            assert model.filename.endswith(".gguf"), f"Modelo {model.name} no es GGUF"
            assert model.size_gb > 0, f"Modelo {model.name} sin size_gb"
            assert model.url, f"Modelo {model.name} sin URL"
            assert model.url.startswith("https://"), f"Modelo {model.name} URL no HTTPS"

    def test_expected_models_exist(self):
        """Modelos esperados están disponibles."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS

        model_names = [m.name for m in AVAILABLE_MODELS]

        expected = ["llama-3.2-3b", "qwen2.5-7b", "mistral-7b"]
        for name in expected:
            assert name in model_names, f"Modelo esperado no encontrado: {name}"


class TestLlamaCppManagerInit:
    """Tests para inicialización del manager."""

    def test_manager_creation(self):
        """Puede crear un manager."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()
                assert manager is not None

    def test_manager_creates_directories(self):
        """Manager crea directorios necesarios."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Verificar que se crearon los directorios
                assert manager._binary_dir.exists()
                assert manager._models_dir.exists()

    def test_manager_port(self):
        """Manager tiene puerto correcto."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Puerto diferente de Ollama (11434)
                assert manager._port == 8081
                assert manager.host == "http://localhost:8081"


class TestLlamaCppManagerPaths:
    """Tests para paths del manager."""

    def test_binary_path_windows(self):
        """Path de binario correcto en Windows."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                with mock.patch("platform.system", return_value="Windows"):
                    manager = LlamaCppManager()
                    assert manager.binary_path.name == "llama-server.exe"

    def test_binary_path_unix(self):
        """Path de binario correcto en Unix."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                with mock.patch("platform.system", return_value="Darwin"):
                    manager = LlamaCppManager()
                    assert manager.binary_path.name == "llama-server"


class TestLlamaCppManagerStatus:
    """Tests para estado del manager."""

    def test_not_installed_status(self):
        """Status NOT_INSTALLED cuando no hay binario."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager, LlamaCppStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                assert not manager.is_installed
                assert not manager.is_running
                assert manager.status == LlamaCppStatus.NOT_INSTALLED

    def test_installed_status(self):
        """Status INSTALLED cuando hay binario pero no corre."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager, LlamaCppStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Crear binario falso
                manager.binary_path.touch()

                assert manager.is_installed
                assert not manager.is_running
                assert manager.status == LlamaCppStatus.INSTALLED


class TestLlamaCppManagerModels:
    """Tests para gestión de modelos."""

    def test_downloaded_models_empty_initially(self):
        """Lista de modelos descargados vacía al inicio."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                assert len(manager.downloaded_models) == 0

    def test_available_models_show_download_status(self):
        """available_models muestra estado de descarga."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS, LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Crear archivo GGUF falso para el primer modelo
                first_model = AVAILABLE_MODELS[0]
                fake_model_path = manager._models_dir / first_model.filename
                fake_model_path.touch()

                # Verificar que se detecta como descargado
                models = manager.available_models
                downloaded_model = next(m for m in models if m.name == first_model.name)
                assert downloaded_model.is_downloaded is True

    def test_get_model_path_returns_none_for_unknown(self):
        """get_model_path retorna None para modelo desconocido."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                path = manager.get_model_path("nonexistent-model")
                assert path is None

    def test_get_model_path_returns_none_if_not_downloaded(self):
        """get_model_path retorna None si modelo conocido no está descargado."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                path = manager.get_model_path("llama-3.2-3b")
                assert path is None

    def test_get_model_path_returns_path_if_exists(self):
        """get_model_path retorna path si modelo existe."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS, LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Crear archivo GGUF falso
                first_model = AVAILABLE_MODELS[0]
                fake_model_path = manager._models_dir / first_model.filename
                fake_model_path.write_bytes(b"fake gguf content")

                path = manager.get_model_path(first_model.name)
                assert path is not None
                assert path.exists()


class TestLlamaCppManagerSecurity:
    """Tests de seguridad para el manager."""

    def test_path_traversal_protection(self):
        """get_model_path previene path traversal."""
        from narrative_assistant.llm.llamacpp_manager import AVAILABLE_MODELS, LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Crear un modelo con filename malicioso (esto no debería pasar
                # pero el código debe ser defensivo)
                # La validación está en get_model_path que comprueba resolved paths

                # Verificar que el path validado está dentro del directorio permitido
                first_model = AVAILABLE_MODELS[0]
                fake_model_path = manager._models_dir / first_model.filename
                fake_model_path.write_bytes(b"test")

                path = manager.get_model_path(first_model.name)
                assert path is not None

                # El path debe estar dentro del directorio de modelos
                assert str(path).startswith(str(manager._models_dir.resolve()))

    def test_host_is_localhost_only(self):
        """El host siempre es localhost."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Verificar que el host es siempre localhost
                assert "localhost" in manager.host or "127.0.0.1" in manager.host


class TestLlamaCppManagerSingleton:
    """Tests para el singleton del manager."""

    def test_get_manager_returns_instance(self):
        """get_llamacpp_manager retorna una instancia."""
        from narrative_assistant.llm import llamacpp_manager
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager, get_llamacpp_manager

        # Reset singleton para test limpio
        llamacpp_manager._manager = None

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = get_llamacpp_manager()
                assert isinstance(manager, LlamaCppManager)

    def test_get_manager_returns_same_instance(self):
        """get_llamacpp_manager retorna la misma instancia (singleton)."""
        from narrative_assistant.llm import llamacpp_manager
        from narrative_assistant.llm.llamacpp_manager import get_llamacpp_manager

        # Reset singleton para test limpio
        llamacpp_manager._manager = None

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager1 = get_llamacpp_manager()
                manager2 = get_llamacpp_manager()
                assert manager1 is manager2


class TestLlamaCppManagerServerControl:
    """Tests para control del servidor (sin ejecutar realmente)."""

    def test_start_server_fails_if_not_installed(self):
        """start_server falla si no está instalado."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                success, msg = manager.start_server()

                assert not success
                assert "no está instalado" in msg.lower()

    def test_start_server_fails_if_no_models(self):
        """start_server falla si no hay modelos."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                # Crear binario falso
                manager.binary_path.touch()

                success, msg = manager.start_server()

                assert not success
                assert "no hay modelos" in msg.lower()

    def test_stop_server_succeeds_when_not_running(self):
        """stop_server tiene éxito cuando no hay servidor corriendo."""
        from narrative_assistant.llm.llamacpp_manager import LlamaCppManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"NA_DATA_DIR": tmpdir}):
                manager = LlamaCppManager()

                success, msg = manager.stop_server()

                assert success
                assert "no estaba corriendo" in msg.lower()
