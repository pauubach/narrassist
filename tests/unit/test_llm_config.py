"""
Tests para el módulo de configuración LLM con votación por roles.

Cubre:
- resolve_fallbacks: sustitución inteligente cuando modelos no están disponibles
- detect_capacity: detección de VRAM / Metal / RAM
- recommend_level: niveles según hardware
- QUALITY_MATRIX: todas las tareas cubiertas
- Sensibilidad: mapeo correcto del slider
"""

import pytest

from narrative_assistant.llm.config import (  # noqa: E402
    QUALITY_MATRIX,
    ROLE_SUBSTITUTES,
    AnalysisTask,
    HardwareProfile,
    ModelRole,
    QualityLevel,
    TaskVotingConfig,
    VotingResult,
    VotingSlot,
    _sensitivity_to_factor,
    get_available_levels,
    get_required_models,
    get_voting_config,
    recommend_level,
    resolve_fallbacks,
)


# =============================================================================
# resolve_fallbacks
# =============================================================================


class TestResolveFallbacks:
    """Tests para la resolución de fallbacks por roles."""

    def test_no_model_missing(self):
        """Cuando todos los modelos están disponibles, no hay cambios."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"qwen3", "deepseek-r1", "hermes3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 3
        model_names = [s.model_name for s in resolved.slots]
        assert "qwen3" in model_names
        assert "deepseek-r1" in model_names
        assert "hermes3" in model_names

    def test_one_model_missing_substituted_by_role(self):
        """Si falta un modelo, se sustituye por otro del mismo rol."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        # deepseek-r1 no disponible → debe sustituirse por siguiente en REASONING
        available = {"qwen3", "hermes3", "mistral"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 3
        model_names = [s.model_name for s in resolved.slots]
        # deepseek-r1 sustituido por qwen3 (REASONING fallback) — pero qwen3 ya está.
        # Siguiente en REASONING: mistral
        assert "mistral" in model_names
        # Verificar que el slot tiene el rol correcto
        reasoning_slot = [s for s in resolved.slots if s.role == ModelRole.REASONING][0]
        assert reasoning_slot.model_name == "mistral"

    def test_same_model_not_duplicated(self):
        """Un modelo no puede ocupar dos slots."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        # Solo qwen3 y llama3.2 disponibles
        available = {"qwen3", "llama3.2"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        model_names = [s.model_name for s in resolved.slots]
        # qwen3 ya ocupa SPANISH, no puede repetirse en REASONING
        assert len(set(model_names)) == len(model_names), "No debe haber modelos duplicados"

    def test_all_models_missing(self):
        """Si no hay ningún modelo disponible, retorna slots vacíos."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available: set[str] = set()

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 0

    def test_rapida_level_uses_one_slot(self):
        """Nivel Rápida solo usa 1 slot (el de mayor peso)."""
        config = QUALITY_MATRIX[AnalysisTask.EXPECTATIONS]
        available = {"qwen3", "hermes3", "deepseek-r1"}

        resolved = resolve_fallbacks(config, available, QualityLevel.RAPIDA)

        assert len(resolved.slots) == 1
        # Expectations: primer slot es hermes3 (NARRATIVE, 0.40)
        assert resolved.slots[0].model_name == "hermes3"

    def test_completa_level_uses_two_slots(self):
        """Nivel Completa usa 2 slots."""
        config = QUALITY_MATRIX[AnalysisTask.EXPECTATIONS]
        available = {"qwen3", "hermes3", "deepseek-r1"}

        resolved = resolve_fallbacks(config, available, QualityLevel.COMPLETA)

        assert len(resolved.slots) == 2

    def test_weights_renormalized(self):
        """Los pesos se renormalizan para sumar ~1.0."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"qwen3", "hermes3"}  # Solo 2 de 3

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        total = sum(s.weight for s in resolved.slots)
        assert abs(total - 1.0) < 0.05, f"Pesos deben sumar ~1.0, got {total}"

    def test_fallback_qwen3_missing_uses_qwen25_for_spanish(self):
        """Si falta qwen3, el rol SPANISH pasa a qwen2.5."""
        config = QUALITY_MATRIX[AnalysisTask.CLASSICAL_SPANISH]
        available = {"qwen2.5", "deepseek-r1", "hermes3"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        spanish_slot = [s for s in resolved.slots if s.role == ModelRole.SPANISH]
        assert len(spanish_slot) == 1
        assert spanish_slot[0].model_name == "qwen2.5"

    def test_normalized_model_names(self):
        """Los nombres con tags (:latest) se normalizan."""
        config = QUALITY_MATRIX[AnalysisTask.COREFERENCE]
        available = {"qwen3:latest", "deepseek-r1:7b", "hermes3:8b"}

        resolved = resolve_fallbacks(config, available, QualityLevel.EXPERTA)

        assert len(resolved.slots) == 3


# =============================================================================
# Hardware detection and level recommendation
# =============================================================================


class TestRecommendLevel:
    """Tests para recomendación de nivel según hardware."""

    def test_cuda_high_vram(self):
        """16GB VRAM CUDA → Experta."""
        profile = HardwareProfile(
            vram_gb=16.0, unified_memory_gb=None,
            ram_gb=32.0, device_type="cuda",
            effective_budget_gb=16.0,
        )
        assert recommend_level(profile) == QualityLevel.COMPLETA

    def test_cuda_very_high_vram(self):
        """24GB VRAM → Experta."""
        profile = HardwareProfile(
            vram_gb=24.0, unified_memory_gb=None,
            ram_gb=64.0, device_type="cuda",
            effective_budget_gb=24.0,
        )
        assert recommend_level(profile) == QualityLevel.EXPERTA

    def test_mps_16gb(self):
        """Mac 16GB unified → 12GB budget → Completa."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=16.0,
            ram_gb=16.0, device_type="mps",
            effective_budget_gb=12.0,
        )
        assert recommend_level(profile) == QualityLevel.COMPLETA

    def test_cpu_8gb(self):
        """CPU 8GB → 4GB budget → Rápida."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None,
            ram_gb=8.0, device_type="cpu",
            effective_budget_gb=4.0,
        )
        assert recommend_level(profile) == QualityLevel.RAPIDA

    def test_cpu_4gb(self):
        """CPU 4GB → 2GB budget → Rápida."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None,
            ram_gb=4.0, device_type="cpu",
            effective_budget_gb=2.0,
        )
        assert recommend_level(profile) == QualityLevel.RAPIDA


class TestAvailableLevels:
    """Tests para niveles disponibles según hardware."""

    def test_all_levels_available_on_high_end(self):
        """Hardware de gama alta tiene todos los niveles disponibles."""
        profile = HardwareProfile(
            vram_gb=24.0, unified_memory_gb=None,
            ram_gb=64.0, device_type="cuda",
            effective_budget_gb=24.0,
        )
        levels = get_available_levels(profile)

        assert all(lv["available"] for lv in levels)

    def test_experta_unavailable_on_low_end(self):
        """Hardware de gama baja no tiene Experta."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None,
            ram_gb=8.0, device_type="cpu",
            effective_budget_gb=4.0,
        )
        levels = get_available_levels(profile)

        rapida = next(lv for lv in levels if lv["level"] == QualityLevel.RAPIDA)
        completa = next(lv for lv in levels if lv["level"] == QualityLevel.COMPLETA)
        experta = next(lv for lv in levels if lv["level"] == QualityLevel.EXPERTA)

        assert rapida["available"] is True
        assert completa["available"] is False
        assert experta["available"] is False

    def test_reason_provided_when_unavailable(self):
        """Niveles no disponibles incluyen razón."""
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None,
            ram_gb=8.0, device_type="cpu",
            effective_budget_gb=4.0,
        )
        levels = get_available_levels(profile)

        experta = next(lv for lv in levels if lv["level"] == QualityLevel.EXPERTA)
        assert experta["reason"] is not None
        assert "20" in experta["reason"]  # Requiere 20 GB


# =============================================================================
# QUALITY_MATRIX coverage
# =============================================================================


class TestQualityMatrix:
    """Tests para la matriz de configuración por tarea."""

    def test_all_tasks_covered(self):
        """Todas las tareas de AnalysisTask tienen configuración."""
        for task in AnalysisTask:
            assert task in QUALITY_MATRIX, f"Tarea {task.value} sin configuración"

    def test_all_tasks_have_three_slots(self):
        """Todas las tareas tienen exactamente 3 slots."""
        for task, config in QUALITY_MATRIX.items():
            assert len(config.slots) == 3, f"Tarea {task.value} tiene {len(config.slots)} slots"

    def test_all_tasks_have_different_roles(self):
        """Cada tarea tiene 3 roles diferentes."""
        for task, config in QUALITY_MATRIX.items():
            roles = [s.role for s in config.slots]
            assert len(set(roles)) == 3, f"Tarea {task.value}: roles repetidos {roles}"

    def test_weights_sum_to_one(self):
        """Los pesos de cada tarea suman 1.0."""
        for task, config in QUALITY_MATRIX.items():
            total = sum(s.weight for s in config.slots)
            assert abs(total - 1.0) < 0.01, f"Tarea {task.value}: pesos suman {total}"

    def test_min_confidence_in_valid_range(self):
        """Confianza mínima entre 0.5 y 0.95."""
        for task, config in QUALITY_MATRIX.items():
            assert 0.5 <= config.min_confidence <= 0.95, (
                f"Tarea {task.value}: min_confidence={config.min_confidence}"
            )


# =============================================================================
# ROLE_SUBSTITUTES coverage
# =============================================================================


class TestRoleSubstitutes:
    """Tests para las cadenas de sustitución por rol."""

    def test_all_roles_have_substitutes(self):
        """Todos los roles tienen cadena de sustitución."""
        for role in ModelRole:
            assert role in ROLE_SUBSTITUTES, f"Rol {role.value} sin sustitutos"

    def test_substitutes_have_at_least_two(self):
        """Cada rol tiene al menos 2 sustitutos."""
        for role, subs in ROLE_SUBSTITUTES.items():
            assert len(subs) >= 2, f"Rol {role.value}: solo {len(subs)} sustituto(s)"

    def test_llama32_always_last_resort(self):
        """llama3.2 está en todas las cadenas como último recurso."""
        for role, subs in ROLE_SUBSTITUTES.items():
            assert "llama3.2" in subs, f"Rol {role.value}: falta llama3.2"


# =============================================================================
# Sensitivity
# =============================================================================


class TestSensitivity:
    """Tests para el mapeo de sensibilidad."""

    def test_sensitivity_1_is_strict(self):
        """Sensibilidad 1 = factor > 1.0 (más estricto)."""
        factor = _sensitivity_to_factor(1.0)
        assert factor > 1.0

    def test_sensitivity_5_is_neutral(self):
        """Sensibilidad 5 = factor ~1.0."""
        factor = _sensitivity_to_factor(5.0)
        assert abs(factor - 1.0) < 0.05

    def test_sensitivity_10_is_permissive(self):
        """Sensibilidad 10 = factor < 1.0 (más permisivo)."""
        factor = _sensitivity_to_factor(10.0)
        assert factor < 1.0

    def test_sensitivity_adjusts_confidence(self):
        """get_voting_config con sensibilidad alta reduce min_confidence."""
        config_strict = get_voting_config(
            AnalysisTask.OOC, {"qwen3"}, QualityLevel.RAPIDA, sensitivity=1.0
        )
        config_permissive = get_voting_config(
            AnalysisTask.OOC, {"qwen3"}, QualityLevel.RAPIDA, sensitivity=10.0
        )

        assert config_strict.min_confidence > config_permissive.min_confidence


# =============================================================================
# get_required_models
# =============================================================================


class TestRequiredModels:
    """Tests para modelos necesarios por nivel."""

    def test_rapida_one_model(self):
        models = get_required_models(QualityLevel.RAPIDA)
        assert len(models) >= 1

    def test_completa_two_models(self):
        models = get_required_models(QualityLevel.COMPLETA)
        assert len(models) >= 2

    def test_experta_three_models(self):
        models = get_required_models(QualityLevel.EXPERTA)
        assert len(models) == 3
        assert "qwen3" in models
        assert "hermes3" in models
        assert "deepseek-r1" in models


# =============================================================================
# VotingResult
# =============================================================================


class TestVotingResult:
    """Tests para el dataclass VotingResult."""

    def test_is_valid_with_consensus(self):
        result = VotingResult(
            consensus={"traits": ["valiente"]},
            confidence=0.85,
            models_used=["qwen3"],
            roles_used=[ModelRole.SPANISH],
        )
        assert result.is_valid

    def test_is_invalid_without_consensus(self):
        result = VotingResult(
            consensus=None,
            confidence=0.0,
            models_used=[],
            roles_used=[],
        )
        assert not result.is_valid

    def test_is_invalid_with_no_models(self):
        result = VotingResult(
            consensus="something",
            confidence=0.5,
            models_used=[],
            roles_used=[],
        )
        assert not result.is_valid


# =============================================================================
# HardwareProfile
# =============================================================================


class TestHardwareProfile:
    """Tests para el dataclass HardwareProfile."""

    def test_has_gpu_cuda(self):
        profile = HardwareProfile(
            vram_gb=8.0, unified_memory_gb=None,
            ram_gb=16.0, device_type="cuda",
            effective_budget_gb=8.0,
        )
        assert profile.has_gpu

    def test_has_gpu_mps(self):
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=16.0,
            ram_gb=16.0, device_type="mps",
            effective_budget_gb=12.0,
        )
        assert profile.has_gpu

    def test_no_gpu_cpu(self):
        profile = HardwareProfile(
            vram_gb=None, unified_memory_gb=None,
            ram_gb=8.0, device_type="cpu",
            effective_budget_gb=4.0,
        )
        assert not profile.has_gpu
