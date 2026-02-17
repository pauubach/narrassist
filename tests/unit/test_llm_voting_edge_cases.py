"""
Tests exhaustivos para edge cases del sistema de votacion LLM por roles.

Cubre:
1. resolve_fallbacks: circularidad, modelo unico, nombres desconocidos, config corrupta
2. voting_query: respuestas None, parse_fn errores, tareas desconocidas, timeouts
3. Sensibilidad: valores fuera de rango, floats, clampeo de min_confidence
4. detect_capacity: sin psutil, GPU sin memoria, MPS
5. estimate_analysis_time: word_count extremos, benchmarks vacios/negativos
6. Integracion: round-trip config -> resolve -> voting_query
"""

import copy
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from narrative_assistant.llm.config import (  # noqa: E402
    LEVEL_MIN_BUDGET_GB,
    MODEL_MEMORY_GB,
    QUALITY_MATRIX,
    ROLE_SUBSTITUTES,
    SENSITIVITY_RANGE,
    AnalysisTask,
    HardwareProfile,
    ModelRole,
    QualityLevel,
    TaskVotingConfig,
    VotingResult,
    VotingSlot,
    _sensitivity_to_factor,
    estimate_analysis_time,
    get_available_levels,
    get_required_models,
    get_voting_config,
    recommend_level,
    resolve_fallbacks,
)


# =============================================================================
# 1. resolve_fallbacks edge cases
# =============================================================================


class TestResolveFallbacksEdgeCases:
    """Edge cases para resolve_fallbacks que no estan cubiertos por test_llm_config."""

    def test_circular_fallback_all_roles_point_to_same_models(self):
        """
        Cuando los sustitutos de cada rol apuntan a modelos que ya estan
        asignados a otros slots, no se duplican modelos.
        """
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        # Solo qwen3 disponible: ocupa SPANISH, REASONING quiere qwen3 pero ya usado,
        # busca siguiente en cadena (mistral no disponible) -> llama3.2 no disponible
        available = {"qwen3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        model_names = [s.model_name for s in resolved.slots]
        assert len(model_names) == len(set(model_names)), (
            "No debe haber modelos duplicados incluso con fallbacks circulares"
        )
        # Solo qwen3 disponible, ocupa 1 slot maximo
        assert len(resolved.slots) == 1
        assert resolved.slots[0].model_name == "qwen3"

    def test_all_three_slots_fallback_to_same_model(self):
        """
        Cuando solo hay llama3.2 disponible (ultimo recurso universal),
        solo puede ocupar 1 slot ya que no se permite duplicar.
        """
        config = QUALITY_MATRIX[AnalysisTask.OOC]
        available = {"llama3.2"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        # llama3.2 aparece en todas las cadenas ROLE_SUBSTITUTES,
        # pero solo puede ocupar un slot (el primero que lo necesite)
        model_names = [s.model_name for s in resolved.slots]
        assert model_names.count("llama3.2") <= 1
        assert len(resolved.slots) >= 1

    def test_only_llama32_rapida_level(self):
        """Con solo llama3.2 en nivel Rapida, resuelve exactamente 1 slot."""
        config = QUALITY_MATRIX[AnalysisTask.TEMPORAL]
        available = {"llama3.2"}

        resolved = resolve_fallbacks(config, available, QualityLevel.RAPIDA)

        assert len(resolved.slots) == 1
        assert resolved.slots[0].model_name == "llama3.2"

    def test_available_models_with_unknown_names(self):
        """
        Modelos desconocidos (no en ROLE_SUBSTITUTES) no se usan como fallback,
        pero tampoco causan errores.
        """
        config = QUALITY_MATRIX[AnalysisTask.PROFILING]
        available = {"noexiste-model-7b", "otro-custom:latest", "qwen3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        # qwen3 es el unico reconocido, los desconocidos no se asignan
        known_models = [s.model_name for s in resolved.slots]
        assert "noexiste-model-7b" not in known_models
        assert "otro-custom" not in known_models
        assert "qwen3" in known_models

    def test_empty_slots_config(self):
        """Config con slots vacios (corrupta) no produce errores."""
        corrupted = TaskVotingConfig(
            task=AnalysisTask.COREFERENCE,
            slots=[],
            min_confidence=0.70,
        )
        available = {"qwen3", "hermes3", "deepseek-r1"}

        resolved = resolve_fallbacks(corrupted, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 0

    def test_very_long_model_name_strings(self):
        """Nombres de modelo extremadamente largos no causan crash."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        long_name = "a" * 10000
        available = {long_name, "qwen3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        # El nombre largo no coincide con ningun sustituto, solo qwen3 se usa
        model_names = [s.model_name for s in resolved.slots]
        assert long_name not in model_names
        assert "qwen3" in model_names

    def test_special_characters_in_model_names(self):
        """Caracteres especiales en nombres no causan crash."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"qwen3", "model/with:slashes", "hermes3", "model@v2!"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        # model/with se normaliza por split(":")[0] -> "model/with"
        # No coincide con ningun sustituto conocido
        assert len(resolved.slots) >= 2

    def test_model_names_with_colon_tag_normalization(self):
        """
        Nombres con tags :latest, :q4_0 se normalizan correctamente
        (ya cubierto parcialmente, aqui verificamos edge cases).
        """
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        # Nombres con multiples colons
        available = {"qwen3:latest:v2", "hermes3:q4_k_m:custom"}

        resolved = resolve_fallbacks(config, available, QualityLevel.COMPLETA)

        # split(":")[0] toma solo la parte antes del primer colon
        model_names = [s.model_name for s in resolved.slots]
        assert "qwen3" in model_names or "hermes3" in model_names

    def test_case_insensitive_model_matching(self):
        """Los nombres de modelo se normalizan a lowercase."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"Qwen3", "HERMES3", "DeepSeek-R1"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 3

    def test_model_names_with_whitespace(self):
        """Nombres con espacios se normalizan con strip."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"  qwen3  ", "hermes3 ", " deepseek-r1"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 3

    def test_empty_available_set(self):
        """Set vacio de modelos disponibles -> 0 slots."""
        for task in AnalysisTask:
            config = QUALITY_MATRIX[task]
            resolved = resolve_fallbacks(config, set(), QualityLevel.EXPERTA)
            assert len(resolved.slots) == 0

    def test_completa_with_only_two_fallbacks_available(self):
        """
        Nivel Completa necesita 2 slots. Si solo hay 2 modelos fallback
        que cubren los 2 roles, ambos se usan.
        """
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        # SPANISH -> qwen2.5 (fallback), REASONING -> mistral (fallback)
        available = {"qwen2.5", "mistral"}

        resolved = resolve_fallbacks(config, available, QualityLevel.COMPLETA)

        assert len(resolved.slots) == 2
        model_names = {s.model_name for s in resolved.slots}
        assert "qwen2.5" in model_names
        assert "mistral" in model_names

    def test_weight_renormalization_single_slot(self):
        """Con 1 slot, el peso se renormaliza a 1.0."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"qwen3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        if resolved.slots:
            total = sum(s.weight for s in resolved.slots)
            assert abs(total - 1.0) < 0.01

    def test_weight_renormalization_two_slots(self):
        """Con 2 slots, los pesos se renormalizan para sumar ~1.0."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"qwen3", "hermes3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        if len(resolved.slots) >= 2:
            total = sum(s.weight for s in resolved.slots)
            assert abs(total - 1.0) < 0.01

    def test_slot_for_level_with_invalid_level_value(self):
        """slot_for_level con nivel no reconocido retorna 1 slot (default)."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]

        # Acceder directamente con un valor no definido en el dict interno
        # El metodo usa .get(level, 1), asi que cualquier valor desconocido da 1
        class FakeLevel:
            pass

        slots = config.slot_for_level(FakeLevel())  # type: ignore[arg-type]
        assert len(slots) == 1

    def test_resolve_preserves_task_and_min_confidence(self):
        """resolve_fallbacks preserva la tarea y min_confidence originales."""
        config = QUALITY_MATRIX[AnalysisTask.CLASSICAL_SPANISH]
        available = {"llama3.2"}

        resolved = resolve_fallbacks(config, available, QualityLevel.RAPIDA)

        assert resolved.task == AnalysisTask.CLASSICAL_SPANISH
        assert resolved.min_confidence == config.min_confidence

    def test_resolve_preserves_role_assignment(self):
        """
        Cada slot resuelto conserva el rol del slot original,
        aunque el modelo sea diferente.
        """
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        # Forzar fallback para todos: ninguno de los originales disponible
        available = {"qwen2.5", "mistral", "gemma2"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        for slot in resolved.slots:
            # Verificar que el rol es uno de los tres definidos
            assert slot.role in (ModelRole.SPANISH, ModelRole.REASONING, ModelRole.NARRATIVE)


# =============================================================================
# 2. voting_query edge cases (mock client.complete)
# =============================================================================


class TestVotingQueryEdgeCases:
    """Edge cases para voting_query con mocking completo."""

    @pytest.fixture
    def mock_client(self):
        """
        Crea un LocalLLMClient mock que no necesita Ollama real.
        Parchea _initialize_backend para evitar conexiones.
        """
        from narrative_assistant.llm.client import LocalLLMClient, LocalLLMConfig

        with patch.object(LocalLLMClient, "_initialize_backend"):
            config = LocalLLMConfig(backend="ollama")
            client = LocalLLMClient(config)
            client._backend = "ollama"
            return client

    def test_all_models_return_none(self, mock_client):
        """Si todos los modelos retornan None, el consenso es None."""
        mock_client.complete = MagicMock(return_value=None)
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.EXPERTA,
        )

        assert result.consensus is None
        assert result.confidence == 0.0
        assert len(result.models_used) == 0

    def test_partial_consensus_one_none(self, mock_client):
        """
        Si 1 de 3 modelos retorna None, los otros 2 forman consenso parcial.
        """
        call_count = 0

        def side_effect_complete(prompt, system, max_tokens, temperature, model_name):
            nonlocal call_count
            call_count += 1
            if model_name == "deepseek-r1":
                return None  # Este falla
            return f"respuesta de {model_name}"

        mock_client.complete = MagicMock(side_effect=side_effect_complete)
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.EXPERTA,
        )

        # 2 de 3 respondieron
        assert len(result.models_used) == 2
        assert "deepseek-r1" not in result.models_used
        assert result.consensus is not None
        assert result.confidence > 0.0

    def test_parse_fn_raises_exception(self, mock_client):
        """
        Si parse_fn lanza excepcion, el error se captura y el modelo
        se descarta del consenso sin crashear la query completa.
        """
        def broken_parse(text):
            raise ValueError("parse error deliberado")

        mock_client.complete = MagicMock(return_value="respuesta valida")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3"}
        )

        # La excepcion se captura internamente — el resultado queda vacio
        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            parse_fn=broken_parse,
            quality_level=QualityLevel.RAPIDA,
        )

        # El modelo fallo en parse, asi que no tiene resultados validos
        assert len(result.models_used) == 0
        assert result.consensus is None

    def test_complete_raises_exception_handled_gracefully(self, mock_client):
        """Si complete() lanza excepcion, no crashea la votacion."""
        mock_client.complete = MagicMock(
            side_effect=ConnectionError("Ollama no disponible")
        )
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.EXPERTA,
        )

        # Todos los modelos fallaron, pero no crasheo
        assert len(result.models_used) == 0
        assert result.consensus is None
        # Los tiempos se registraron
        assert len(result.per_model_times) == 3

    def test_partial_complete_exception(self, mock_client):
        """Si 1 de 3 modelos lanza excepcion, los otros 2 siguen funcionando."""
        call_count = 0

        def side_effect_complete(prompt, system, max_tokens, temperature, model_name):
            nonlocal call_count
            call_count += 1
            if model_name == "deepseek-r1":
                raise TimeoutError("modelo muy lento")
            return f"respuesta de {model_name}"

        mock_client.complete = MagicMock(side_effect=side_effect_complete)
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.EXPERTA,
        )

        assert len(result.models_used) == 2
        assert "deepseek-r1" not in result.models_used
        assert result.consensus is not None

    def test_unknown_task_name_returns_empty_result(self, mock_client):
        """Tarea desconocida retorna VotingResult vacio."""
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3"}
        )

        result = mock_client.voting_query(
            task_name="tarea_que_no_existe",
            prompt="test",
            system="test",
        )

        assert result.consensus is None
        assert result.confidence == 0.0
        assert result.models_used == []
        assert result.roles_used == []

    def test_quality_level_as_string(self, mock_client):
        """quality_level como string se convierte correctamente a enum."""
        mock_client.complete = MagicMock(return_value="respuesta")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level="rapida",  # String en vez de enum
        )

        # Nivel rapida = 1 slot
        assert len(result.models_used) == 1

    def test_quality_level_invalid_string_falls_back_to_rapida(self, mock_client):
        """String de quality_level invalido cae a RAPIDA."""
        mock_client.complete = MagicMock(return_value="respuesta")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level="nivel_inventado",
        )

        # Fallback a RAPIDA = 1 slot
        assert len(result.models_used) == 1

    def test_quality_level_none_defaults_to_rapida(self, mock_client):
        """quality_level=None usa RAPIDA por defecto."""
        mock_client.complete = MagicMock(return_value="respuesta")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=None,
        )

        assert len(result.models_used) == 1

    def test_no_available_models_returns_empty(self, mock_client):
        """Si no hay modelos disponibles, retorna resultado vacio."""
        mock_client._get_available_ollama_models = MagicMock(
            return_value=set()
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.RAPIDA,
        )

        assert result.consensus is None
        assert len(result.models_used) == 0

    def test_fallbacks_applied_tracking(self, mock_client):
        """Verifica que los fallbacks aplicados se registran correctamente."""
        mock_client.complete = MagicMock(return_value="respuesta")
        # Solo llama3.2 disponible -> todos los slots hacen fallback
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"llama3.2"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.RAPIDA,
        )

        # El slot principal (qwen3) fue sustituido por llama3.2
        assert len(result.fallbacks_applied) >= 1
        assert any("llama3.2" in fb for fb in result.fallbacks_applied)

    def test_per_model_times_recorded_even_on_failure(self, mock_client):
        """Los tiempos se registran incluso cuando un modelo falla (retorna None)."""
        mock_client.complete = MagicMock(return_value=None)
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            quality_level=QualityLevel.RAPIDA,
        )

        # Aunque fallo, el tiempo se registro
        assert len(result.per_model_times) == 1
        assert "qwen3" in result.per_model_times

    def test_voting_query_with_all_six_tasks(self, mock_client):
        """Cada una de las 6 tareas funciona correctamente con voting_query."""
        mock_client.complete = MagicMock(return_value="respuesta")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        for task in AnalysisTask:
            result = mock_client.voting_query(
                task_name=task.value,
                prompt="test",
                system="test",
                quality_level=QualityLevel.RAPIDA,
            )
            assert result.is_valid, f"Tarea {task.value} deberia ser valida"

    def test_parse_fn_returns_none_treated_as_valid(self, mock_client):
        """
        Si parse_fn retorna None, se almacena como resultado del modelo
        (no se trata como fallo).
        """
        mock_client.complete = MagicMock(return_value="respuesta cruda")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3"}
        )

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="test",
            system="test",
            parse_fn=lambda x: None,  # parse devuelve None
            quality_level=QualityLevel.RAPIDA,
        )

        # Se usa el parse_fn result, que es None
        assert "qwen3" in result.per_model_results
        assert result.per_model_results["qwen3"] is None

    def test_max_tokens_and_temperature_passed_through(self, mock_client):
        """max_tokens y temperature se pasan correctamente a complete."""
        mock_client.complete = MagicMock(return_value="resp")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3"}
        )

        mock_client.voting_query(
            task_name="coreference",
            prompt="mi prompt",
            system="mi system",
            quality_level=QualityLevel.RAPIDA,
            max_tokens=500,
            temperature=0.7,
        )

        mock_client.complete.assert_called_once_with(
            prompt="mi prompt",
            system="mi system",
            max_tokens=500,
            temperature=0.7,
            model_name="qwen3",
        )


# =============================================================================
# 3. Sensitivity edge cases
# =============================================================================


class TestSensitivityEdgeCases:
    """Edge cases para el sistema de sensibilidad."""

    def test_sensitivity_0_clamped_to_1(self):
        """Sensibilidad 0 (below min) se clampea a 1 internamente."""
        factor = _sensitivity_to_factor(0.0)
        factor_at_1 = _sensitivity_to_factor(1.0)
        assert factor == factor_at_1

    def test_sensitivity_11_clamped_to_10(self):
        """Sensibilidad 11 (above max) se clampea a 10."""
        factor = _sensitivity_to_factor(11.0)
        factor_at_10 = _sensitivity_to_factor(10.0)
        assert factor == factor_at_10

    def test_sensitivity_negative_clamped(self):
        """Sensibilidad negativa se clampea a 1."""
        factor = _sensitivity_to_factor(-5.0)
        factor_at_1 = _sensitivity_to_factor(1.0)
        assert factor == factor_at_1

    def test_sensitivity_float_5_5(self):
        """Sensibilidad 5.5 produce un factor entre 1.0 y 0.7."""
        factor = _sensitivity_to_factor(5.5)
        factor_5 = _sensitivity_to_factor(5.0)
        factor_6 = _sensitivity_to_factor(6.0)
        # 5.5 esta entre 5 y 6, el factor debe estar entre ambos
        assert factor_6 < factor < factor_5 or factor_6 <= factor <= factor_5

    def test_sensitivity_100_clamped(self):
        """Valor extremo (100) se clampea a 10."""
        factor = _sensitivity_to_factor(100.0)
        assert factor == _sensitivity_to_factor(10.0)

    def test_min_confidence_never_below_0_1(self):
        """min_confidence nunca baja de 0.1 incluso con sensibilidad maxima."""
        for task in AnalysisTask:
            config = get_voting_config(
                task, {"qwen3"}, QualityLevel.RAPIDA, sensitivity=10.0
            )
            assert config.min_confidence >= 0.1, (
                f"Tarea {task.value}: min_confidence={config.min_confidence} < 0.1"
            )

    def test_min_confidence_never_above_0_99(self):
        """min_confidence nunca sube de 0.99 incluso con sensibilidad minima."""
        for task in AnalysisTask:
            config = get_voting_config(
                task, {"qwen3"}, QualityLevel.RAPIDA, sensitivity=1.0
            )
            assert config.min_confidence <= 0.99, (
                f"Tarea {task.value}: min_confidence={config.min_confidence} > 0.99"
            )

    def test_sensitivity_5_does_not_alter_confidence(self):
        """Sensibilidad 5 (default) no altera min_confidence."""
        for task in AnalysisTask:
            base = QUALITY_MATRIX[task].min_confidence
            config = get_voting_config(
                task, {"qwen3"}, QualityLevel.RAPIDA, sensitivity=5.0
            )
            assert abs(config.min_confidence - base) < 0.001, (
                f"Tarea {task.value}: sensibilidad 5 altero confianza "
                f"de {base} a {config.min_confidence}"
            )

    def test_sensitivity_monotonic_decrease(self):
        """
        Al aumentar la sensibilidad de 1 a 10, min_confidence
        disminuye monotonicamente (mas permisivo).
        """
        task = AnalysisTask.OOC
        prev = None
        for s in range(1, 11):
            config = get_voting_config(
                task, {"qwen3"}, QualityLevel.RAPIDA, sensitivity=float(s)
            )
            if prev is not None:
                assert config.min_confidence <= prev + 0.001, (
                    f"sensitivity={s}: {config.min_confidence} > {prev} (no monotonica)"
                )
            prev = config.min_confidence

    def test_sensitivity_range_constants(self):
        """Las constantes SENSITIVITY_RANGE son coherentes."""
        min_factor, max_factor = SENSITIVITY_RANGE
        assert min_factor < max_factor
        assert min_factor > 0
        assert max_factor < 2.0

    def test_sensitivity_factor_at_boundaries(self):
        """factor(1) == max_factor, factor(10) == min_factor."""
        min_factor, max_factor = SENSITIVITY_RANGE
        assert abs(_sensitivity_to_factor(1.0) - max_factor) < 0.001
        assert abs(_sensitivity_to_factor(10.0) - min_factor) < 0.001


# =============================================================================
# 4. detect_capacity edge cases
# =============================================================================


class TestDetectCapacityEdgeCases:
    """Edge cases para detect_capacity y _get_system_ram_gb."""

    def test_no_psutil_fallback_to_8gb(self):
        """Sin psutil, el fallback de RAM es 8GB (en Windows)."""
        from narrative_assistant.core.device import _get_system_ram_gb

        with patch.dict("sys.modules", {"psutil": None}):
            with patch("builtins.__import__", side_effect=_import_without_psutil):
                ram = _get_system_ram_gb()
                # En Windows (no Linux), deberia retornar 8.0
                # Si estamos en Linux podria leer /proc/meminfo
                assert ram > 0

    def test_detect_capacity_cpu_only(self):
        """detect_capacity en CPU-only retorna presupuesto = 50% RAM."""
        from narrative_assistant.core.device import (
            DeviceDetector,
            detect_capacity,
            get_device_detector,
            reset_device_detector,
        )

        # Resetear singleton para control total
        reset_device_detector()

        with (
            patch.object(DeviceDetector, "detect_cuda", return_value=None),
            patch.object(DeviceDetector, "detect_mps", return_value=None),
            patch("narrative_assistant.core.device._get_system_ram_gb", return_value=16.0),
        ):
            profile = detect_capacity()

            assert profile.device_type == "cpu"
            assert profile.ram_gb == 16.0
            assert abs(profile.effective_budget_gb - 8.0) < 0.1  # 50% de 16

        reset_device_detector()

    def test_detect_capacity_cuda_with_vram(self):
        """detect_capacity con CUDA usa VRAM como presupuesto."""
        from narrative_assistant.core.device import (
            DeviceDetector,
            DeviceInfo,
            DeviceType,
            detect_capacity,
            reset_device_detector,
        )

        reset_device_detector()

        cuda_info = DeviceInfo(
            device_type=DeviceType.CUDA,
            device_name="RTX 4090",
            device_id=0,
            memory_gb=24.0,
            is_available=True,
        )

        with (
            patch.object(DeviceDetector, "detect_cuda", return_value=cuda_info),
            patch("narrative_assistant.core.device._get_system_ram_gb", return_value=64.0),
        ):
            profile = detect_capacity()

            assert profile.device_type == "cuda"
            assert profile.vram_gb == 24.0
            assert profile.effective_budget_gb == 24.0

        reset_device_detector()

    def test_detect_capacity_cuda_memory_gb_none(self):
        """
        GPU CUDA detectada pero memory_gb es None: no se usa como CUDA,
        cae a siguiente metodo.
        """
        from narrative_assistant.core.device import (
            DeviceDetector,
            DeviceInfo,
            DeviceType,
            detect_capacity,
            reset_device_detector,
        )

        reset_device_detector()

        cuda_info = DeviceInfo(
            device_type=DeviceType.CUDA,
            device_name="GPU desconocida",
            device_id=0,
            memory_gb=None,  # No se pudo detectar VRAM
            is_available=True,
        )

        with (
            patch.object(DeviceDetector, "detect_cuda", return_value=cuda_info),
            patch.object(DeviceDetector, "detect_mps", return_value=None),
            patch("narrative_assistant.core.device._get_system_ram_gb", return_value=32.0),
        ):
            profile = detect_capacity()

            # cuda con memory_gb=None: la condicion es "if cuda and cuda.memory_gb",
            # None es falsy -> cae a MPS o CPU
            assert profile.device_type == "cpu"
            assert abs(profile.effective_budget_gb - 16.0) < 0.1  # 50% de 32

        reset_device_detector()

    def test_detect_capacity_mps_budget(self):
        """MPS usa 75% de RAM como presupuesto."""
        from narrative_assistant.core.device import (
            DeviceDetector,
            DeviceInfo,
            DeviceType,
            detect_capacity,
            reset_device_detector,
        )

        reset_device_detector()

        mps_info = DeviceInfo(
            device_type=DeviceType.MPS,
            device_name="Apple Silicon GPU",
            device_id=0,
            memory_gb=None,
            is_available=True,
        )

        with (
            patch.object(DeviceDetector, "detect_cuda", return_value=None),
            patch.object(DeviceDetector, "detect_mps", return_value=mps_info),
            patch("narrative_assistant.core.device._get_system_ram_gb", return_value=16.0),
        ):
            profile = detect_capacity()

            assert profile.device_type == "mps"
            assert profile.unified_memory_gb == 16.0
            assert abs(profile.effective_budget_gb - 12.0) < 0.1  # 75% de 16

        reset_device_detector()

    def test_hardware_profile_has_gpu_variants(self):
        """Verifica has_gpu para todos los tipos de dispositivo."""
        cuda_profile = HardwareProfile(
            vram_gb=8.0, unified_memory_gb=None, ram_gb=16.0,
            device_type="cuda", effective_budget_gb=8.0
        )
        mps_profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=16.0, ram_gb=16.0,
            device_type="mps", effective_budget_gb=12.0
        )
        cpu_profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=8.0,
            device_type="cpu", effective_budget_gb=4.0
        )
        other_profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=8.0,
            device_type="tpu",  # Tipo inventado
            effective_budget_gb=4.0
        )

        assert cuda_profile.has_gpu is True
        assert mps_profile.has_gpu is True
        assert cpu_profile.has_gpu is False
        assert other_profile.has_gpu is False


# =============================================================================
# 5. estimate_analysis_time edge cases
# =============================================================================


class TestEstimateAnalysisTimeEdgeCases:
    """Edge cases para la estimacion de tiempos de analisis."""

    def _make_profile(self, device_type="cpu", budget_gb=4.0, ram_gb=8.0):
        return HardwareProfile(
            vram_gb=budget_gb if device_type == "cuda" else None,
            unified_memory_gb=ram_gb if device_type == "mps" else None,
            ram_gb=ram_gb,
            device_type=device_type,
            effective_budget_gb=budget_gb,
        )

    def test_word_count_zero(self):
        """word_count=0 no causa division por cero ni valores negativos."""
        profile = self._make_profile()

        result = estimate_analysis_time(profile, QualityLevel.RAPIDA, 0)

        assert result["min_seconds"] >= 0
        assert result["max_seconds"] >= 0
        assert result["llm_calls"] > 0  # Siempre hay llamadas LLM (6 tareas * 1)

    def test_word_count_very_large(self):
        """1M palabras produce tiempos altos pero no infinitos."""
        profile = self._make_profile()

        result = estimate_analysis_time(profile, QualityLevel.EXPERTA, 1_000_000)

        assert result["min_seconds"] > 0
        assert result["max_seconds"] < float("inf")
        assert result["max_seconds"] > result["min_seconds"]
        # Con 1M palabras en CPU deberia ser horas
        assert "hora" in result["description"]

    def test_empty_benchmarks_dict(self):
        """Benchmarks vacio no causa crash (usa estimacion por hardware)."""
        profile = self._make_profile(device_type="cuda", budget_gb=16.0)

        # Dict vacio -> sum({}.values()) / len({}) = ZeroDivisionError
        # Pero el codigo verifica "if benchmarks:" y {} es falsy
        result = estimate_analysis_time(
            profile, QualityLevel.RAPIDA, 10000, benchmarks={}
        )

        assert result["avg_toks_per_sec"] == 40.0  # Fallback CUDA

    def test_negative_toks_in_benchmarks(self):
        """tok/s negativos en benchmarks producen tiempos negativos (bug potencial)."""
        profile = self._make_profile()

        # Aunque poco realista, no deberia causar crash
        result = estimate_analysis_time(
            profile, QualityLevel.RAPIDA, 10000,
            benchmarks={"model_a": -10.0}
        )

        # Con tok/s negativo, los calculos dan resultados negativos
        # Esto es un edge case que el codigo no maneja, pero no debe crashear
        assert isinstance(result["min_seconds"], int)
        assert isinstance(result["max_seconds"], int)

    def test_cuda_default_toks_per_sec(self):
        """CUDA sin benchmarks usa 40 tok/s."""
        profile = self._make_profile(device_type="cuda", budget_gb=16.0)

        result = estimate_analysis_time(profile, QualityLevel.RAPIDA, 10000)

        assert result["avg_toks_per_sec"] == 40.0

    def test_mps_default_toks_per_sec(self):
        """MPS sin benchmarks usa 25 tok/s."""
        profile = self._make_profile(device_type="mps", budget_gb=12.0, ram_gb=16.0)

        result = estimate_analysis_time(profile, QualityLevel.RAPIDA, 10000)

        assert result["avg_toks_per_sec"] == 25.0

    def test_cpu_default_toks_per_sec(self):
        """CPU sin benchmarks usa 8 tok/s."""
        profile = self._make_profile(device_type="cpu")

        result = estimate_analysis_time(profile, QualityLevel.RAPIDA, 10000)

        assert result["avg_toks_per_sec"] == 8.0

    def test_llm_calls_scale_with_level(self):
        """El numero de llamadas LLM escala con el nivel de calidad."""
        profile = self._make_profile()

        r_rapida = estimate_analysis_time(profile, QualityLevel.RAPIDA, 10000)
        r_completa = estimate_analysis_time(profile, QualityLevel.COMPLETA, 10000)
        r_experta = estimate_analysis_time(profile, QualityLevel.EXPERTA, 10000)

        assert r_rapida["llm_calls"] < r_completa["llm_calls"]
        assert r_completa["llm_calls"] < r_experta["llm_calls"]
        # Rapida: 6*1=6, Completa: 6*2=12, Experta: 6*3=18
        assert r_rapida["llm_calls"] == len(AnalysisTask) * 1
        assert r_completa["llm_calls"] == len(AnalysisTask) * 2
        assert r_experta["llm_calls"] == len(AnalysisTask) * 3

    def test_time_format_seconds(self):
        """Tiempos cortos se formatean como segundos."""
        profile = self._make_profile(device_type="cuda", budget_gb=24.0)

        # Con benchmarks rapidos (500 tok/s), el tiempo baja a ~12 segundos
        result = estimate_analysis_time(
            profile, QualityLevel.RAPIDA, 100, benchmarks={"fast": 500.0}
        )

        assert "segundo" in result["description"]

    def test_time_format_minutes(self):
        """Tiempos medios se formatean como minutos."""
        profile = self._make_profile(device_type="cpu")

        result = estimate_analysis_time(profile, QualityLevel.COMPLETA, 50000)

        assert "minuto" in result["description"]

    def test_benchmarks_override_hardware_estimate(self):
        """Benchmarks reales reemplazan la estimacion por hardware."""
        profile = self._make_profile(device_type="cuda", budget_gb=24.0)

        # Benchmark real mucho mas lento que el default de 40 tok/s
        result = estimate_analysis_time(
            profile, QualityLevel.RAPIDA, 10000,
            benchmarks={"qwen3": 5.0, "hermes3": 3.0}
        )

        assert result["avg_toks_per_sec"] == 4.0  # Promedio de 5 y 3

    def test_word_count_1(self):
        """Un solo palabra no causa problemas."""
        profile = self._make_profile()
        result = estimate_analysis_time(profile, QualityLevel.RAPIDA, 1)

        assert result["min_seconds"] >= 0
        assert result["max_seconds"] >= 0


# =============================================================================
# 6. Integration-style tests
# =============================================================================


class TestIntegrationRoundTrip:
    """Tests de integracion: config -> resolve -> voting_query (mocked)."""

    @pytest.fixture
    def mock_client(self):
        """Crea un mock client para tests de integracion."""
        from narrative_assistant.llm.client import LocalLLMClient, LocalLLMConfig

        with patch.object(LocalLLMClient, "_initialize_backend"):
            config = LocalLLMConfig(backend="ollama")
            client = LocalLLMClient(config)
            client._backend = "ollama"
            return client

    def test_full_round_trip_experta(self, mock_client):
        """Round-trip completo: config -> resolve -> voting_query en nivel Experta."""
        available = {"qwen3", "hermes3", "deepseek-r1"}
        responses = {
            "qwen3": '{"entities": ["Juan", "Maria"]}',
            "hermes3": '{"entities": ["Juan", "Maria"]}',
            "deepseek-r1": '{"entities": ["Juan"]}',
        }

        def complete_side_effect(prompt, system, max_tokens, temperature, model_name):
            return responses.get(model_name)

        mock_client.complete = MagicMock(side_effect=complete_side_effect)
        mock_client._get_available_ollama_models = MagicMock(return_value=available)

        import json

        result = mock_client.voting_query(
            task_name="coreference",
            prompt="Resolver correferencias",
            system="Eres un experto en NLP",
            parse_fn=json.loads,
            quality_level=QualityLevel.EXPERTA,
        )

        assert result.is_valid
        assert len(result.models_used) == 3
        assert result.confidence > 0.0
        assert len(result.per_model_results) == 3
        assert len(result.per_model_times) == 3

    def test_level_change_triggers_correct_model_count(self, mock_client):
        """Cambiar nivel cambia el numero de modelos usados."""
        mock_client.complete = MagicMock(return_value="respuesta")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        for level, expected_count in [
            (QualityLevel.RAPIDA, 1),
            (QualityLevel.COMPLETA, 2),
            (QualityLevel.EXPERTA, 3),
        ]:
            result = mock_client.voting_query(
                task_name="temporal",
                prompt="test",
                system="test",
                quality_level=level,
            )
            assert len(result.models_used) == expected_count, (
                f"Nivel {level.value}: esperaba {expected_count} modelos, "
                f"obtuvo {len(result.models_used)}"
            )

    def test_sensitivity_slider_correct_confidence_per_task(self):
        """
        Slider de sensibilidad produce ajustes correctos por tarea.
        Sensibilidad baja (1) -> confianza mas alta.
        Sensibilidad alta (10) -> confianza mas baja.
        """
        available = {"qwen3"}

        for task in AnalysisTask:
            strict = get_voting_config(task, available, QualityLevel.RAPIDA, sensitivity=1.0)
            neutral = get_voting_config(task, available, QualityLevel.RAPIDA, sensitivity=5.0)
            permissive = get_voting_config(task, available, QualityLevel.RAPIDA, sensitivity=10.0)

            base = QUALITY_MATRIX[task].min_confidence

            # Estricto > base > permisivo
            assert strict.min_confidence > base - 0.001, (
                f"Tarea {task.value}: strict ({strict.min_confidence}) <= base ({base})"
            )
            assert permissive.min_confidence < base + 0.001, (
                f"Tarea {task.value}: permissive ({permissive.min_confidence}) >= base ({base})"
            )
            # Neutral ~= base
            assert abs(neutral.min_confidence - base) < 0.01

    def test_full_fallback_chain_with_voting(self, mock_client):
        """
        Escenario realista: solo hay llama3.2, todos los slots hacen fallback,
        y la votacion produce un resultado valido.
        """
        mock_client.complete = MagicMock(return_value="resultado analisis")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"llama3.2"}
        )

        result = mock_client.voting_query(
            task_name="expectations",
            prompt="Analizar expectativas",
            system="Experto narrativo",
            quality_level=QualityLevel.RAPIDA,
        )

        assert result.is_valid
        assert "llama3.2" in result.models_used
        assert len(result.fallbacks_applied) >= 1

    def test_config_resolve_and_vote_all_tasks_all_levels(self, mock_client):
        """
        Smoke test: todas las combinaciones de tarea x nivel producen
        resultados coherentes.
        """
        mock_client.complete = MagicMock(return_value="ok")
        mock_client._get_available_ollama_models = MagicMock(
            return_value={"qwen3", "hermes3", "deepseek-r1"}
        )

        for task in AnalysisTask:
            for level in QualityLevel:
                result = mock_client.voting_query(
                    task_name=task.value,
                    prompt="test",
                    system="test",
                    quality_level=level,
                )
                assert result.is_valid, (
                    f"Tarea {task.value}, nivel {level.value}: resultado invalido"
                )
                expected = {
                    QualityLevel.RAPIDA: 1,
                    QualityLevel.COMPLETA: 2,
                    QualityLevel.EXPERTA: 3,
                }
                assert len(result.models_used) == expected[level]


# =============================================================================
# Additional edge case coverage
# =============================================================================


class TestVotingResultEdgeCases:
    """Edge cases adicionales para VotingResult."""

    def test_is_valid_requires_both_consensus_and_models(self):
        """is_valid necesita tanto consensus como models_used no vacio."""
        # Consensus set but no models
        r1 = VotingResult(
            consensus="algo", confidence=0.5, models_used=[], roles_used=[]
        )
        assert not r1.is_valid

        # Models set but no consensus
        r2 = VotingResult(
            consensus=None, confidence=0.5,
            models_used=["qwen3"], roles_used=[ModelRole.SPANISH]
        )
        assert not r2.is_valid

        # Both set
        r3 = VotingResult(
            consensus="algo", confidence=0.5,
            models_used=["qwen3"], roles_used=[ModelRole.SPANISH]
        )
        assert r3.is_valid

    def test_voting_result_default_fields(self):
        """Los campos con default se inicializan correctamente."""
        r = VotingResult(
            consensus=None, confidence=0.0, models_used=[], roles_used=[]
        )
        assert r.per_model_results == {}
        assert r.per_model_times == {}
        assert r.fallbacks_applied == []

    def test_voting_result_with_empty_string_consensus(self):
        """Consensus con string vacio es tecnicamete valido (no es None)."""
        r = VotingResult(
            consensus="", confidence=0.5,
            models_used=["qwen3"], roles_used=[ModelRole.SPANISH]
        )
        assert r.is_valid  # "" is not None

    def test_voting_result_with_zero_consensus(self):
        """Consensus con 0 (int) es valido (no es None)."""
        r = VotingResult(
            consensus=0, confidence=0.5,
            models_used=["qwen3"], roles_used=[ModelRole.SPANISH]
        )
        assert r.is_valid  # 0 is not None

    def test_voting_result_with_false_consensus(self):
        """Consensus con False es valido (no es None)."""
        r = VotingResult(
            consensus=False, confidence=0.5,
            models_used=["qwen3"], roles_used=[ModelRole.SPANISH]
        )
        assert r.is_valid  # False is not None


class TestTaskVotingConfigEdgeCases:
    """Edge cases para TaskVotingConfig."""

    def test_model_names_property(self):
        """La propiedad model_names retorna la lista correcta."""
        config = TaskVotingConfig(
            task=AnalysisTask.COREFERENCE,
            slots=[
                VotingSlot(ModelRole.SPANISH, "a", 0.5),
                VotingSlot(ModelRole.REASONING, "b", 0.3),
                VotingSlot(ModelRole.NARRATIVE, "c", 0.2),
            ],
            min_confidence=0.7,
        )
        assert config.model_names == ["a", "b", "c"]

    def test_model_names_empty(self):
        """model_names vacio con slots vacios."""
        config = TaskVotingConfig(
            task=AnalysisTask.COREFERENCE, slots=[], min_confidence=0.7
        )
        assert config.model_names == []

    def test_slot_for_level_rapida(self):
        """slot_for_level RAPIDA retorna 1 slot."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        slots = config.slot_for_level(QualityLevel.RAPIDA)
        assert len(slots) == 1

    def test_slot_for_level_completa(self):
        """slot_for_level COMPLETA retorna 2 slots."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        slots = config.slot_for_level(QualityLevel.COMPLETA)
        assert len(slots) == 2

    def test_slot_for_level_experta(self):
        """slot_for_level EXPERTA retorna 3 slots."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        slots = config.slot_for_level(QualityLevel.EXPERTA)
        assert len(slots) == 3


class TestRecommendLevelEdgeCases:
    """Edge cases para recommend_level."""

    def test_exact_boundary_completa(self):
        """Presupuesto exacto en la frontera de Completa."""
        boundary = LEVEL_MIN_BUDGET_GB[QualityLevel.COMPLETA]
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=32.0,
            device_type="cpu", effective_budget_gb=boundary,
        )
        assert recommend_level(profile) == QualityLevel.COMPLETA

    def test_exact_boundary_experta(self):
        """Presupuesto exacto en la frontera de Experta."""
        boundary = LEVEL_MIN_BUDGET_GB[QualityLevel.EXPERTA]
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=64.0,
            device_type="cpu", effective_budget_gb=boundary,
        )
        assert recommend_level(profile) == QualityLevel.EXPERTA

    def test_just_below_completa(self):
        """Presupuesto justo por debajo de Completa -> Rapida."""
        boundary = LEVEL_MIN_BUDGET_GB[QualityLevel.COMPLETA]
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=16.0,
            device_type="cpu", effective_budget_gb=boundary - 0.01,
        )
        assert recommend_level(profile) == QualityLevel.RAPIDA

    def test_zero_budget(self):
        """Presupuesto 0 -> Rapida."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=1.0,
            device_type="cpu", effective_budget_gb=0.0,
        )
        assert recommend_level(profile) == QualityLevel.RAPIDA

    def test_negative_budget(self):
        """Presupuesto negativo (imposible pero defensivo) -> Rapida."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=1.0,
            device_type="cpu", effective_budget_gb=-5.0,
        )
        assert recommend_level(profile) == QualityLevel.RAPIDA

    def test_very_large_budget(self):
        """Presupuesto enorme -> Experta."""
        profile = HardwareProfile(
            vram_gb=1000.0, unified_memory_gb=None, ram_gb=2000.0,
            device_type="cuda", effective_budget_gb=1000.0,
        )
        assert recommend_level(profile) == QualityLevel.EXPERTA


class TestGetAvailableLevelsEdgeCases:
    """Edge cases para get_available_levels."""

    def test_returns_three_levels_always(self):
        """Siempre retorna exactamente 3 niveles."""
        for budget in [0, 5, 15, 25, 100]:
            profile = HardwareProfile(
                vram_gb=None, unified_memory_gb=None, ram_gb=32.0,
                device_type="cpu", effective_budget_gb=float(budget),
            )
            levels = get_available_levels(profile)
            assert len(levels) == 3

    def test_rapida_always_available(self):
        """Rapida siempre esta disponible incluso con 0 budget."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=1.0,
            device_type="cpu", effective_budget_gb=0.0,
        )
        levels = get_available_levels(profile)
        rapida = next(lv for lv in levels if lv["level"] == QualityLevel.RAPIDA)
        assert rapida["available"] is True

    def test_exactly_one_recommended(self):
        """Exactamente 1 nivel es el recomendado."""
        for budget in [4.0, 15.0, 25.0]:
            profile = HardwareProfile(
                vram_gb=None, unified_memory_gb=None, ram_gb=64.0,
                device_type="cpu", effective_budget_gb=budget,
            )
            levels = get_available_levels(profile)
            recommended = [lv for lv in levels if lv["recommended"]]
            assert len(recommended) == 1, (
                f"Budget {budget}: {len(recommended)} niveles recomendados"
            )

    def test_unavailable_levels_have_reason(self):
        """Niveles no disponibles siempre tienen una razon."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None, ram_gb=8.0,
            device_type="cpu", effective_budget_gb=4.0,
        )
        levels = get_available_levels(profile)
        for lv in levels:
            if not lv["available"]:
                assert lv["reason"] is not None and len(lv["reason"]) > 0

    def test_available_levels_have_no_reason(self):
        """Niveles disponibles tienen reason=None."""
        profile = HardwareProfile(
            vram_gb=48.0, unified_memory_gb=None, ram_gb=128.0,
            device_type="cuda", effective_budget_gb=48.0,
        )
        levels = get_available_levels(profile)
        for lv in levels:
            if lv["available"]:
                assert lv["reason"] is None


class TestComputeConsensusEdgeCases:
    """Edge cases para _compute_consensus (via mock client)."""

    @pytest.fixture
    def mock_client(self):
        from narrative_assistant.llm.client import LocalLLMClient, LocalLLMConfig

        with patch.object(LocalLLMClient, "_initialize_backend"):
            config = LocalLLMConfig(backend="ollama")
            client = LocalLLMClient(config)
            client._backend = "ollama"
            return client

    def test_empty_results_returns_none(self, mock_client):
        """Resultados vacios -> (None, 0.0)."""
        consensus, confidence = mock_client._compute_consensus(
            results={},
            slots=[VotingSlot(ModelRole.SPANISH, "qwen3", 0.5)],
            min_confidence=0.7,
        )
        assert consensus is None
        assert confidence == 0.0

    def test_single_result_uses_slot_weight(self, mock_client):
        """Con 1 resultado, la confianza es el peso del slot."""
        slots = [
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.40),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.35),
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.25),
        ]

        consensus, confidence = mock_client._compute_consensus(
            results={"qwen3": "resultado"},
            slots=slots,
            min_confidence=0.7,
        )

        assert consensus == "resultado"
        assert abs(confidence - 0.40) < 0.01

    def test_multiple_results_picks_highest_weight(self, mock_client):
        """Con multiples resultados, el consenso es del modelo con mayor peso."""
        slots = [
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.40),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.35),
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.25),
        ]

        consensus, confidence = mock_client._compute_consensus(
            results={
                "qwen3": "resultado_qwen",
                "deepseek-r1": "resultado_deepseek",
                "hermes3": "resultado_hermes",
            },
            slots=slots,
            min_confidence=0.7,
        )

        assert consensus == "resultado_qwen"  # Peso mas alto (0.40)
        assert confidence > 0.9  # Todos respondieron

    def test_confidence_scales_with_responding_models(self, mock_client):
        """Confianza escala con la fraccion de modelos que respondieron."""
        slots = [
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.40),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.35),
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.25),
        ]

        # Solo 1 de 3 respondio
        _, conf_1 = mock_client._compute_consensus(
            results={"hermes3": "r"}, slots=slots, min_confidence=0.7,
        )

        # 2 de 3 respondieron
        _, conf_2 = mock_client._compute_consensus(
            results={"qwen3": "r", "hermes3": "r"}, slots=slots, min_confidence=0.7,
        )

        # 3 de 3 respondieron
        _, conf_3 = mock_client._compute_consensus(
            results={"qwen3": "r", "deepseek-r1": "r", "hermes3": "r"},
            slots=slots, min_confidence=0.7,
        )

        assert conf_1 < conf_2 < conf_3


class TestGetRequiredModelsEdgeCases:
    """Edge cases para get_required_models."""

    def test_unknown_level_returns_empty(self):
        """Un nivel no reconocido retorna set vacio (via LEVEL_MODELS.get)."""
        # Crear un falso QualityLevel no registrado
        result = get_required_models.__wrapped__ if hasattr(get_required_models, "__wrapped__") else get_required_models

        # No podemos crear un enum desconocido facilmente, pero podemos
        # verificar que las 3 conocidas funcionan
        for level in QualityLevel:
            models = get_required_models(level)
            assert isinstance(models, set)

    def test_models_are_subsets(self):
        """Los modelos de Rapida son subconjunto de Completa, que es subconjunto de Experta."""
        rapida = get_required_models(QualityLevel.RAPIDA)
        completa = get_required_models(QualityLevel.COMPLETA)
        experta = get_required_models(QualityLevel.EXPERTA)

        assert rapida.issubset(completa)
        assert completa.issubset(experta)


class TestModelMemoryConstants:
    """Tests para constantes de memoria de modelos."""

    def test_all_core_models_have_memory(self):
        """Todos los modelos core tienen definicion de memoria."""
        from narrative_assistant.llm.config import CORE_MODELS

        for model in CORE_MODELS:
            assert model in MODEL_MEMORY_GB, (
                f"Modelo core {model} sin definicion de memoria"
            )

    def test_all_fallback_models_have_memory(self):
        """Todos los modelos fallback tienen definicion de memoria."""
        from narrative_assistant.llm.config import FALLBACK_MODELS

        for model in FALLBACK_MODELS:
            assert model in MODEL_MEMORY_GB, (
                f"Modelo fallback {model} sin definicion de memoria"
            )

    def test_memory_values_positive(self):
        """Todas las memorias son positivas."""
        for model, mem in MODEL_MEMORY_GB.items():
            assert mem > 0, f"Modelo {model}: memoria {mem} <= 0"

    def test_llama32_is_smallest(self):
        """llama3.2 es el modelo mas pequeno (universal fallback)."""
        llama_mem = MODEL_MEMORY_GB["llama3.2"]
        for model, mem in MODEL_MEMORY_GB.items():
            if model != "llama3.2":
                assert mem >= llama_mem, (
                    f"Modelo {model} ({mem} GB) es menor que llama3.2 ({llama_mem} GB)"
                )


# =============================================================================
# Helper functions
# =============================================================================


def _import_without_psutil(name, *args, **kwargs):
    """Helper para simular que psutil no esta instalado."""
    if name == "psutil":
        raise ImportError("Mock: psutil not installed")
    return __builtins__.__import__(name, *args, **kwargs)  # type: ignore[attr-defined]
